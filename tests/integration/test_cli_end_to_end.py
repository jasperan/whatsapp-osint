"""End-to-end CLI tests: drive the real entry point against a temp database.

These exercise the new presence-aware features through their real interface
(``whatsapp-beacon --analytics``, ``--export-json``, ``--last-seen``) using a
temporary config that points at an isolated data directory.
"""
import json
import sys

import pytest

from src.whatsapp_beacon.database import Database
from src.whatsapp_beacon.main import main


def _seed(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    db = Database(db_path=str(data_dir / 'victims_logs.db'))
    alice = db.get_or_create_user('Alice')
    bob = db.get_or_create_user('Bob')
    session_id = db.insert_session_start(alice, {
        'date': '2026-08-01', 'hour': '10', 'minute': '00', 'second': '00'
    })
    db.update_session_end(session_id, {
        'date': '2026-08-01', 'hour': '10', 'minute': '05', 'second': '00'
    }, '300')
    db.insert_presence(alice, '2026-08-02 09:00:00', 'last_seen', 'last seen yesterday at 22:00', '2026-08-01 22:00:00')
    db.insert_presence(alice, '2026-08-02 09:30:00', 'online', 'online', None)
    db.insert_presence(bob, '2026-08-02 10:00:00', 'last_seen', 'last seen today at 09:45', '2026-08-02 09:45:00')

    config_path = tmp_path / 'config.yaml'
    config_path.write_text(
        'username: ""\nlanguage: "en"\ndata_dir: "%s"\nlog_level: "WARNING"\n' % data_dir,
        encoding='utf-8',
    )
    return config_path


def _run_cli(argv, capsys):
    sys.argv = ['whatsapp-beacon'] + argv
    try:
        main()
    except SystemExit:
        pass  # successful CLI paths call sys.exit(0)
    return capsys.readouterr().out


def test_cli_analytics_includes_presence_trail(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)  # keep main()'s logs/ inside the temp dir
    config_path = _seed(tmp_path)
    html_out = tmp_path / 'reports' / 'analytics.html'

    out = _run_cli(
        ['--config', str(config_path), '--analytics', '--analytics-output', str(html_out)],
        capsys,
    )
    assert 'Analytics dashboard written to' in out
    assert html_out.exists()

    content = html_out.read_text(encoding='utf-8')
    assert 'Presence trail' in content
    assert 'last seen yesterday at 22:00' in content

    json_blob = content.split('const dashboardData = ', 1)[1].split('\n    const state', 1)[0].rstrip(';')
    payload = json.loads(json_blob)
    assert len(payload['presence_trail']) == 3
    alice = next(user for user in payload['users'] if user['user_name'] == 'Alice')
    assert alice['last_seen_label'] == 'Online 2026-08-02 09:30:00'
    assert alice['presence_count'] == 2


def test_cli_export_json(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _seed(tmp_path)
    json_out = tmp_path / 'export.json'

    out = _run_cli(['--config', str(config_path), '--export-json', str(json_out)], capsys)
    assert 'JSON export written to' in out
    payload = json.loads(json_out.read_text(encoding='utf-8'))
    assert len(payload['sessions']) == 1
    assert len(payload['presence']) == 3


def test_cli_last_seen_lists_contacts(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _seed(tmp_path)
    out = _run_cli(['--config', str(config_path), '--last-seen'], capsys)
    assert 'Alice: online (observed 2026-08-02 09:30:00)' in out
    assert 'Bob: last seen today at 09:45 (observed 2026-08-02 10:00:00)' in out


def test_cli_last_seen_filters_by_username(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _seed(tmp_path)
    out = _run_cli(['--config', str(config_path), '-u', 'Bob', '--last-seen'], capsys)
    assert 'Bob:' in out
    assert 'Alice:' not in out


def test_cli_last_seen_empty_database(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / 'empty_data'
    data_dir.mkdir()
    config_path = tmp_path / 'config.yaml'
    config_path.write_text('data_dir: "%s"\nlog_level: "WARNING"\n' % data_dir, encoding='utf-8')

    out = _run_cli(['--config', str(config_path), '--last-seen'], capsys)
    assert 'No presence data recorded yet.' in out
