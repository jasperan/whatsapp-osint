import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = 'data/victims_logs.db') -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()

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

                cutoff = datetime.strptime(
                    f"{cutoff_parts['date']} {cutoff_parts['hour']}:{cutoff_parts['minute']}:{cutoff_parts['second']}",
                    '%Y-%m-%d %H:%M:%S',
                )
                closed = 0
                for row in open_sessions:
                    start = datetime.strptime(
                        f"{row[1]} {row[2]}:{row[3]}:{row[4]}",
                        '%Y-%m-%d %H:%M:%S',
                    )
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
                    rows.append({
                        'user_name': row[0],
                        'observed_at': row[1],
                        'status_kind': row[2],
                        'status_text': row[3],
                        'last_seen': row[4],
                    })
        except sqlite3.Error as e:
            logger.error(f"Error reading presence history: {e}")
        return rows

    def get_latest_presence_by_user(self) -> Dict[str, Dict[str, str]]:
        """Returns the most recent presence observation per contact."""
        latest: Dict[str, Dict[str, str]] = {}
        for row in self.get_presence_history():
            latest[row['user_name']] = row
        return latest
