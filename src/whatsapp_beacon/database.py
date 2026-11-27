import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .private_files import make_private_dir

logger = logging.getLogger(__name__)

# Columns of a presence observation as read by the shared presence queries.
_PRESENCE_COLUMNS = ('user_name', 'observed_at', 'status_kind', 'status_text', 'last_seen')


def compose_session_datetime(date: str, hour: str, minute: str, second: str) -> datetime:
    """Composes the schema's separate date/hour/minute/second parts into a datetime."""
    # Building the datetime from ints is ~15x faster than strptime, which matters
    # because analytics composes two per stored session. strptime stays as the
    # fallback so malformed rows raise the same ValueError as before.
    try:
        year, month, day = date.split('-')
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    except (AttributeError, TypeError, ValueError):
        return datetime.strptime(
            f"{date} {hour}:{minute}:{second}",
            '%Y-%m-%d %H:%M:%S',
        )


class Database:
    def __init__(self, db_path: str = 'data/victims_logs.db') -> None:
        self.db_path = Path(db_path)
        make_private_dir(self.db_path.parent)
        self.create_tables()
        self._restrict_permissions()

    def _restrict_permissions(self) -> None:
        """Keep the tracking database owner-only; it holds private presence history."""
        try:
            self.db_path.chmod(0o600)
        except OSError:
            # Some mounted filesystems do not support chmod; not fatal for operation.
            pass

    def _get_connection(self) -> sqlite3.Connection:
        """Retrieves a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def create_tables(self) -> None:
        """Creates the Users and Sessions tables if they do not exist."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE IF NOT EXISTS Users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_name TEXT UNIQUE
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS Sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        start_date TEXT,
                        start_hour TEXT,
                        start_minute TEXT,
                        start_second TEXT,
                        end_date TEXT,
                        end_hour TEXT,
                        end_minute TEXT,
                        end_second TEXT,
                        time_connected TEXT,
                        FOREIGN KEY (user_id) REFERENCES Users(id)
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS Presence (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        observed_at TEXT,
                        status_kind TEXT,
                        status_text TEXT,
                        last_seen TEXT,
                        FOREIGN KEY (user_id) REFERENCES Users(id)
                    )
                ''')
                # Presence grows by a row every 30 s per tracked contact; the
                # per-contact "latest" lookups below would otherwise scan it all.
                c.execute(
                    'CREATE INDEX IF NOT EXISTS idx_presence_user_observed '
                    'ON Presence (user_id, observed_at)'
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")

    def get_or_create_user(self, user_name: str) -> int:
        """Gets the user ID if it exists, otherwise creates a new user and returns its ID."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT id FROM Users WHERE user_name = ?', (user_name,))
                result = c.fetchone()
                if result:
                    return result[0]
                c.execute('INSERT INTO Users (user_name) VALUES (?)', (user_name,))
                conn.commit()
                return c.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error getting/creating user {user_name}: {e}")
            return -1

    def insert_session_start(self, user_id: int, start_time: Dict[str, str]) -> Optional[int]:
        """Inserts a new session start into the Sessions table."""
        fields = ['user_id', 'start_date', 'start_hour', 'start_minute', 'start_second']
        values = (user_id, start_time['date'], start_time['hour'], start_time['minute'], start_time['second'])
        query = f'INSERT INTO Sessions ({", ".join(fields)}) VALUES (?, ?, ?, ?, ?)'

        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(query, values)
                conn.commit()
                return c.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error inserting session start: {e}")
            return None

    def update_session_end(self, session_id: int, end_time: Dict[str, str], time_connected: str) -> None:
        query = '''
            UPDATE Sessions
            SET end_date = ?, end_hour = ?, end_minute = ?, end_second = ?, time_connected = ?
            WHERE id = ?
        '''
        values = (end_time['date'], end_time['hour'], end_time['minute'], end_time['second'], time_connected, session_id)

        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(query, values)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating session end: {e}")

    def close_open_sessions(self, cutoff_parts: Dict[str, str]) -> int:
        """Closes sessions that never received an end timestamp.

        A tracker process that is killed (or crashes) while a contact is still
        online leaves a session with a NULL end_* row. Those "zombie" sessions
        would otherwise keep growing forever in analytics (which substitutes
        "now" for the missing end). On startup we close them at the supplied
        cutoff so the history stays truthful.

        Returns the number of sessions closed.
        """
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    'SELECT id, start_date, start_hour, start_minute, start_second '
                    'FROM Sessions WHERE end_date IS NULL'
                )
                open_sessions = c.fetchall()

                cutoff = compose_session_datetime(
                    cutoff_parts['date'], cutoff_parts['hour'],
                    cutoff_parts['minute'], cutoff_parts['second'],
                )
                closed = 0
                for row in open_sessions:
                    start = compose_session_datetime(row[1], row[2], row[3], row[4])
                    seconds = max(int((cutoff - start).total_seconds()), 0)
                    c.execute(
                        'UPDATE Sessions SET end_date = ?, end_hour = ?, end_minute = ?, '
                        'end_second = ?, time_connected = ? WHERE id = ?',
                        (
                            cutoff_parts['date'],
                            cutoff_parts['hour'],
                            cutoff_parts['minute'],
                            cutoff_parts['second'],
                            str(seconds),
                            row[0],
                        ),
                    )
                    closed += 1
                conn.commit()
                if closed:
                    logger.warning(f"Closed {closed} orphaned open session(s) at startup.")
                return closed
        except sqlite3.Error as e:
            logger.error(f"Error closing open sessions: {e}")
            return 0

    # ------------------------------------------------------------------
    # Presence signal recording
    # ------------------------------------------------------------------

    def insert_presence(
        self,
        user_id: int,
        observed_at: str,
        status_kind: str,
        status_text: str,
        last_seen: Optional[str] = None,
    ) -> Optional[int]:
        """Records one observed presence signal."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    'INSERT INTO Presence (user_id, observed_at, status_kind, status_text, last_seen) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (user_id, observed_at, status_kind, status_text, last_seen),
                )
                conn.commit()
                return c.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error inserting presence signal: {e}")
            return None

    def get_presence_history(self, user_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Returns presence observations joined with the contact name.

        Ordered oldest → newest; pass ``limit`` to cap the result.
        """
        query = '''
            SELECT
                u.user_name,
                p.observed_at,
                p.status_kind,
                p.status_text,
                p.last_seen
            FROM Presence p
            JOIN Users u ON p.user_id = u.id
        '''
        params: List = []
        if user_id is not None:
            query += ' WHERE p.user_id = ?'
            params.append(user_id)
        query += ' ORDER BY p.observed_at ASC, p.id ASC'
        if limit is not None:
            query += ' LIMIT ?'
            params.append(limit)

        rows: List[Dict[str, str]] = []
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(query, params)
                for row in c.fetchall():
                    rows.append(dict(zip(_PRESENCE_COLUMNS, row)))
        except sqlite3.Error as e:
            logger.error(f"Error reading presence history: {e}")
        return rows

    def get_presence_summary(
        self, trail_limit: int = 25
    ) -> Tuple[Dict[str, int], Dict[str, Dict[str, str]], List[Dict[str, str]]]:
        """Aggregates presence for the dashboard without loading the full history.

        Returns ``(counts, latest_evidence, trail)``: observations per contact, each
        contact's newest ``online``/``last_seen`` row, and the newest ``trail_limit``
        rows ordered oldest → newest. "Newest" follows the same
        ``observed_at, id`` order as :meth:`get_presence_history`.
        """
        columns = 'u.user_name, p.observed_at, p.status_kind, p.status_text, p.last_seen'
        counts: Dict[str, int] = {}
        latest: Dict[str, Dict[str, str]] = {}
        trail: List[Dict[str, str]] = []
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    'SELECT u.user_name, COUNT(*) FROM Presence p '
                    'JOIN Users u ON p.user_id = u.id GROUP BY p.user_id'
                )
                counts = dict(c.fetchall())
                # One indexed lookup per contact instead of a pass over the history.
                c.execute(
                    f'SELECT {columns} FROM Users u JOIN Presence p ON p.id = ('
                    '    SELECT p2.id FROM Presence p2'
                    "    WHERE p2.user_id = u.id AND p2.status_kind IN ('online', 'last_seen')"
                    '    ORDER BY p2.observed_at DESC, p2.id DESC LIMIT 1'
                    ')'
                )
                for row in c.fetchall():
                    latest[row[0]] = dict(zip(_PRESENCE_COLUMNS, row))
                c.execute(
                    f'SELECT {columns} FROM Presence p JOIN Users u ON p.user_id = u.id '
                    'ORDER BY p.observed_at DESC, p.id DESC LIMIT ?',
                    (trail_limit,),
                )
                trail = [dict(zip(_PRESENCE_COLUMNS, row)) for row in reversed(c.fetchall())]
        except sqlite3.Error as e:
            logger.error(f"Error summarising presence: {e}")
        return counts, latest, trail

    def get_latest_presence_by_user(self) -> Dict[str, Dict[str, str]]:
        """Returns the most recent presence observation per contact."""
        query = '''
            SELECT
                u.user_name,
                p.observed_at,
                p.status_kind,
                p.status_text,
                p.last_seen
            FROM Presence p
            JOIN Users u ON p.user_id = u.id
            WHERE p.id = (
                SELECT MAX(p2.id) FROM Presence p2 WHERE p2.user_id = p.user_id
            )
        '''
        latest: Dict[str, Dict[str, str]] = {}
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(query)
                for row in c.fetchall():
                    latest[row[0]] = dict(zip(_PRESENCE_COLUMNS, row))
        except sqlite3.Error as e:
            logger.error(f"Error reading latest presence: {e}")
        return latest
