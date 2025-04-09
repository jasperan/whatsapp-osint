import sqlite3

class Database:
    DB_PATH = 'database/victims_logs.db'

    @staticmethod
    def _get_connection():
        """Devuelve una conexión a la base de datos."""
        return sqlite3.connect(Database.DB_PATH)

    @staticmethod
    def create_tables():
        """Crea las tablas Users y Sessions si no existen."""
        with Database._get_connection() as conn:
            c = conn.cursor()
            # Tabla Users
            c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='Users'")
            if not c.fetchone()[0]:
                c.execute('''
                    CREATE TABLE Users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_name TEXT UNIQUE
                    )
                ''')
            # Tabla Sessions
            c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='Sessions'")
            if not c.fetchone()[0]:
                c.execute('''
                    CREATE TABLE Sessions (
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

    @staticmethod
    def get_or_create_user(user_name: str) -> int:
        """Obtiene o crea un usuario y devuelve su ID."""
        with Database._get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM Users WHERE user_name = ?', (user_name,))
            result = c.fetchone()
            if result:
                return result[0]
            c.execute('INSERT INTO Users (user_name) VALUES (?)', (user_name,))
            conn.commit()
            return c.lastrowid

    @staticmethod
    def insert_session_start(user_id: int, start_time: Dict[str, str]) -> int:
        """Inserta el inicio de una sesión y devuelve su ID."""
        fields = ['user_id', 'start_date', 'start_hour', 'start_minute', 'start_second']
        values = (user_id, start_time['date'], start_time['hour'], start_time['minute'], start_time['second'])
        query = f'INSERT INTO Sessions ({", ".join(fields)}) VALUES (?, ?, ?, ?, ?)'
        
        with Database._get_connection() as conn:
            c = conn.cursor()
            c.execute(query, values)
            conn.commit()
            return c.lastrowid

    @staticmethod
    def update_session_end(session_id: int, end_time: Dict[str, str], time_connected: str):
        """Actualiza una sesión con los datos de desconexión."""
        query = '''
            UPDATE Sessions 
            SET end_date = ?, end_hour = ?, end_minute = ?, end_second = ?, time_connected = ?
            WHERE id = ?
        '''
        values = (end_time['date'], end_time['hour'], end_time['minute'], end_time['second'], time_connected, session_id)
        
        with Database._get_connection() as conn:
            c = conn.cursor()
            c.execute(query, values)
            conn.commit()