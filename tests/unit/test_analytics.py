import json

from src.whatsapp_beacon.analytics import AnalyticsDashboard
from src.whatsapp_beacon.database import Database


def _time_parts(date, hour, minute, second):
    return {
        'date': date,
        'hour': f'{hour:02d}',
        'minute': f'{minute:02d}',
        'second': f'{second:02d}',
    }


def _insert_session(db, user_name, start_parts, end_parts, duration_seconds):
    user_id = db.get_or_create_user(user_name)
    session_id = db.insert_session_start(user_id, start_parts)
    db.update_session_end(session_id, end_parts, str(duration_seconds))


def test_build_payload_summarizes_sessions(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    _insert_session(db, 'Alice', _time_parts('2025-03-01', 10, 0, 0), _time_parts('2025-03-01', 10, 5, 0), 300)
    _insert_session(db, 'Alice', _time_parts('2025-03-01', 14, 0, 0), _time_parts('2025-03-01', 14, 2, 0), 120)
    _insert_session(db, 'Bob', _time_parts('2025-03-02', 9, 30, 0), _time_parts('2025-03-02', 9, 45, 0), 900)

    dashboard = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db'), output_file=str(tmp_path / 'analytics.html'))
    payload = dashboard.build_payload()

    assert payload['summary']['total_sessions'] == 3
    assert payload['summary']['total_contacts'] == 2
    assert payload['summary']['total_seconds'] == 1320
    assert payload['summary']['average_seconds'] == 440
    assert payload['summary']['longest_seconds'] == 900

    assert [user['user_name'] for user in payload['users']] == ['Bob', 'Alice']
    assert payload['users'][0]['total_seconds'] == 900
    assert payload['users'][1]['total_seconds'] == 420

    daily = {entry['date']: entry for entry in payload['daily_activity']}
    assert daily['2025-03-01']['total_seconds'] == 420
    assert daily['2025-03-01']['session_count'] == 2
    assert daily['2025-03-02']['total_seconds'] == 900
    assert daily['2025-03-02']['session_count'] == 1

    assert len(payload['hourly_heatmap']) == 7
    assert len(payload['hourly_heatmap'][0]['hours']) == 24
    assert payload['recent_sessions'][0]['user_name'] == 'Bob'


def test_export_writes_self_contained_html(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    _insert_session(db, 'Alice', _time_parts('2025-03-01', 10, 0, 0), _time_parts('2025-03-01', 10, 5, 0), 300)

    output_file = tmp_path / 'reports' / 'analytics.html'
    dashboard = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db'), output_file=str(output_file))
    written_path = dashboard.export()

    assert written_path == output_file
    assert output_file.exists()

    content = output_file.read_text(encoding='utf-8')
    assert 'WhatsApp Beacon Analytics' in content
    assert 'dashboardData' in content
    assert 'Alice' in content
    assert 'const dashboardData =' in content

    json_blob = content.split('const dashboardData = ', 1)[1].split('\n    const state', 1)[0].rstrip(';')
    parsed = json.loads(json_blob)
    assert parsed['summary']['total_sessions'] == 1


def _insert_presence(db, user_name, observed_at, kind, text, last_seen=None):
    user_id = db.get_or_create_user(user_name)
    db.insert_presence(user_id, observed_at, kind, text, last_seen)


def test_build_payload_includes_presence_trail_and_last_seen(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    _insert_session(db, 'Alice', _time_parts('2025-03-01', 10, 0, 0), _time_parts('2025-03-01', 10, 5, 0), 300)
    _insert_presence(db, 'Alice', '2025-03-02 08:00:00', 'last_seen', 'last seen yesterday at 22:00', '2025-03-01 22:00:00')
    _insert_presence(db, 'Alice', '2025-03-02 08:30:00', 'online', 'online', None)

    dashboard = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db'))
    payload = dashboard.build_payload()

    alice = payload['users'][0]
    assert alice['presence_count'] == 2
    # Latest evidence is the 'online' observation.
    assert alice['last_seen_label'] == 'Online 2025-03-02 08:30:00'

    assert len(payload['presence_trail']) == 2
    assert payload['presence_trail'][-1]['status_text'] == 'online'
    assert payload['presence_trail'][0]['user_name'] == 'Alice'


def test_last_seen_label_uses_latest_last_seen(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    _insert_session(db, 'Alice', _time_parts('2025-03-01', 10, 0, 0), _time_parts('2025-03-01', 10, 5, 0), 300)
    _insert_presence(db, 'Alice', '2025-03-02 08:00:00', 'last_seen', 'last seen today at 07:45', '2025-03-02 07:45:00')

    payload = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db')).build_payload()
    assert payload['users'][0]['last_seen_label'] == 'Last seen 2025-03-02 07:45:00'


def test_last_seen_label_falls_back_to_last_session(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    _insert_session(db, 'Alice', _time_parts('2025-03-01', 10, 0, 0), _time_parts('2025-03-01', 10, 5, 0), 300)

    payload = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db')).build_payload()
    user = payload['users'][0]
    assert user['presence_count'] == 0
    assert user['last_seen_label'] is not None
    assert user['last_seen_label'].startswith('Last session ')


def test_regularity_score_high_for_consistent_schedule(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    for day in range(1, 8):
        _insert_session(
            db, 'Alice',
            _time_parts(f'2025-03-{day:02d}', 9, 2, 0),
            _time_parts(f'2025-03-{day:02d}', 9, 30, 0),
            1680,
        )
    payload = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db')).build_payload()
    alice = payload['users'][0]
    assert alice['regularity_score'] == 100
    assert alice['active_days'] == 7


def test_regularity_score_low_for_scattered_schedule(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    starts = [(9, 0), (14, 30), (3, 45), (22, 10), (12, 20), (6, 5), (19, 55)]
    for index, (hour, minute) in enumerate(starts, start=1):
        _insert_session(
            db, 'Alice',
            _time_parts(f'2025-03-{index:02d}', hour, minute, 0),
            _time_parts(f'2025-03-{index:02d}', hour, min(minute + 5, 59), 0),
            300,
        )
    payload = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db')).build_payload()
    assert payload['users'][0]['regularity_score'] <= 20


def test_regularity_score_none_for_single_day(tmp_path):
    db = Database(db_path=str(tmp_path / 'analytics.db'))
    _insert_session(db, 'Alice', _time_parts('2025-03-01', 10, 0, 0), _time_parts('2025-03-01', 10, 5, 0), 300)
    payload = AnalyticsDashboard(db_path=str(tmp_path / 'analytics.db')).build_payload()
    assert payload['users'][0]['regularity_score'] is None


def test_build_payload_handles_legacy_db_without_presence_table(tmp_path):
    """Dashboards must still build when the DB predates the Presence feature."""
    import sqlite3

    db_path = tmp_path / 'legacy_analytics.db'
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute('CREATE TABLE Users (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT UNIQUE)')
        conn.execute('''
            CREATE TABLE Sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                start_date TEXT, start_hour TEXT, start_minute TEXT, start_second TEXT,
                end_date TEXT, end_hour TEXT, end_minute TEXT, end_second TEXT,
                time_connected TEXT
            )
        ''')
        conn.execute("INSERT INTO Users (user_name) VALUES ('Alice')")
        conn.execute('''
            INSERT INTO Sessions (user_id, start_date, start_hour, start_minute, start_second,
                end_date, end_hour, end_minute, end_second, time_connected)
            VALUES (1, '2025-03-01', '10', '00', '00', '2025-03-01', '10', '05', '00', '300')
        ''')

    payload = AnalyticsDashboard(db_path=str(db_path)).build_payload()
    assert payload['summary']['total_sessions'] == 1
    assert payload['presence_trail'] == []
    assert payload['users'][0]['presence_count'] == 0
