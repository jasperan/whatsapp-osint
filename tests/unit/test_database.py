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


def test_close_open_sessions_closes_zombies(db):
    user_id = db.get_or_create_user("Alice")
    # A session that never received an end timestamp (crashed tracker run).
    session_id = db.insert_session_start(user_id, {
        'date': '2026-08-01', 'hour': '09', 'minute': '00', 'second': '00'
    })

    closed = db.close_open_sessions({
        'date': '2026-08-01', 'hour': '09', 'minute': '15', 'second': '00'
    })

    assert closed == 1
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT end_date, end_hour, end_minute, end_second, time_connected FROM Sessions WHERE id=?", (session_id,))
        end_date, end_hour, end_minute, end_second, time_connected = c.fetchone()
        assert (end_date, end_hour, end_minute, end_second) == ('2026-08-01', '09', '15', '00')
        assert time_connected == '900'


def test_close_open_sessions_is_idempotent_and_skips_closed(db):
    user_id = db.get_or_create_user("Bob")
    session_id = db.insert_session_start(user_id, {
        'date': '2026-08-01', 'hour': '09', 'minute': '00', 'second': '00'
    })
    db.update_session_end(session_id, {
        'date': '2026-08-01', 'hour': '09', 'minute': '10', 'second': '00'
    }, "600")

    # No open sessions -> nothing to close.
    assert db.close_open_sessions({
        'date': '2026-08-02', 'hour': '00', 'minute': '00', 'second': '00'
    }) == 0
    # A second run over the same open session is harmless (idempotent).
    db.insert_session_start(user_id, {
        'date': '2026-08-02', 'hour': '10', 'minute': '00', 'second': '00'
    })
    assert db.close_open_sessions({
        'date': '2026-08-02', 'hour': '10', 'minute': '30', 'second': '00'
    }) == 1


def test_insert_and_read_presence(db):
    user_id = db.get_or_create_user("Alice")
    presence_id = db.insert_presence(
        user_id=user_id,
        observed_at='2026-08-14 07:00:01',
        status_kind='last_seen',
        status_text='last seen today at 07:00',
        last_seen='2026-08-14 07:00:00',
    )
    assert presence_id is not None

    history = db.get_presence_history()
    assert len(history) == 1
    assert history[0]['user_name'] == 'Alice'
    assert history[0]['status_kind'] == 'last_seen'
    assert history[0]['last_seen'] == '2026-08-14 07:00:00'

    filtered = db.get_presence_history(user_id=user_id)
    assert len(filtered) == 1
    assert len(db.get_presence_history(user_id=9999)) == 0


def test_get_latest_presence_by_user_returns_most_recent(db):
    user_id = db.get_or_create_user("Alice")
    db.insert_presence(user_id, '2026-08-14 07:00:00', 'last_seen', 'last seen today at 06:59', '2026-08-14 06:59:00')
    db.insert_presence(user_id, '2026-08-14 08:00:00', 'online', 'online', None)

    bob_id = db.get_or_create_user("Bob")
    db.insert_presence(bob_id, '2026-08-14 09:00:00', 'last_seen', 'last seen yesterday at 22:00', '2026-08-13 22:00:00')

    latest = db.get_latest_presence_by_user()
    assert set(latest) == {'Alice', 'Bob'}
    assert latest['Alice']['status_kind'] == 'online'
    assert latest['Alice']['observed_at'] == '2026-08-14 08:00:00'
    assert latest['Bob']['last_seen'] == '2026-08-13 22:00:00'


def test_compose_session_datetime_combines_parts():
    from src.whatsapp_beacon.database import compose_session_datetime

    dt = compose_session_datetime('2026-08-14', '07', '05', '09')
    assert dt.strftime('%Y-%m-%d %H:%M:%S') == '2026-08-14 07:05:09'


def test_get_latest_presence_by_user_uses_single_row_per_user(db):
    alice = db.get_or_create_user("Alice")
    db.insert_presence(alice, '2026-08-14 07:00:00', 'last_seen', 'last seen today at 06:59', '2026-08-14 06:59:00')
    db.insert_presence(alice, '2026-08-14 08:00:00', 'online', 'online', None)
    # A later insert for Alice must win, and Bob's own latest must be returned.
    bob = db.get_or_create_user("Bob")
    db.insert_presence(bob, '2026-08-14 09:00:00', 'typing', 'typing…', None)

    latest = db.get_latest_presence_by_user()
    assert set(latest) == {'Alice', 'Bob'}
    assert latest['Alice']['observed_at'] == '2026-08-14 08:00:00'
    assert latest['Bob']['status_kind'] == 'typing'
