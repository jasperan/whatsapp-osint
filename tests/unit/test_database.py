import pytest
import sqlite3
from src.whatsapp_beacon.database import Database

@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test_db.db"
    return Database(db_path=str(db_path))

def test_create_tables(db):
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'")
        assert c.fetchone() is not None
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Sessions'")
        assert c.fetchone() is not None

def test_get_or_create_user(db):
    user_id = db.get_or_create_user("Alice")
    assert user_id > 0

    # Same user should return same ID
    user_id_2 = db.get_or_create_user("Alice")
    assert user_id == user_id_2

    user_id_3 = db.get_or_create_user("Bob")
    assert user_id_3 != user_id

def test_insert_and_update_session(db):
    user_id = db.get_or_create_user("Alice")
    start_time = {
        'date': '2023-01-01', 'hour': '10', 'minute': '00', 'second': '00'
    }

    session_id = db.insert_session_start(user_id, start_time)
    assert session_id is not None

    end_time = {
        'date': '2023-01-01', 'hour': '10', 'minute': '05', 'second': '00'
    }
    db.update_session_end(session_id, end_time, "300")

    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT time_connected FROM Sessions WHERE id=?", (session_id,))
        result = c.fetchone()
        assert result[0] == "300"
