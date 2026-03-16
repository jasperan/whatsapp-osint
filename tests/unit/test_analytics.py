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
