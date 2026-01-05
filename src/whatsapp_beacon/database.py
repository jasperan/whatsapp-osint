import sqlite3
from typing import Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = 'database/victims_logs.db'):
        self.db_path = Path(db_path)
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()

    def _get_connection(self):
        """Retrieves a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        """Creates the Users and Sessions tables if they do not exist."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                # Users Table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS Users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_name TEXT UNIQUE
                    )
                ''')
                # Sessions Table
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

    def update_session_end(self, session_id: int, end_time: Dict[str, str], time_connected: str):
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
