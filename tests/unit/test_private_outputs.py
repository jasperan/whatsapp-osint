"""Every persisted copy of the presence history stays owner-only, like the database itself."""
import logging
import os
import stat
import sys

import pytest

from src.whatsapp_beacon.analytics import AnalyticsDashboard
from src.whatsapp_beacon.database import Database
from src.whatsapp_beacon.db_to_excel import Converter, export_json
from src.whatsapp_beacon.logger import setup_logging

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='POSIX file modes')


def _mode(path):
    return stat.S_IMODE(path.stat().st_mode)


@pytest.fixture
def seeded_db(tmp_path):
    old_umask = os.umask(0o022)  # the common default that exposed the copies
    try:
        db_path = tmp_path / 'data' / 'victims_logs.db'
        db = Database(db_path=str(db_path))
        user = db.get_or_create_user('Alice')
        db.insert_session_start(user, {'date': '2026-08-01', 'hour': '10', 'minute': '00', 'second': '00'})
        db.insert_presence(user, '2026-08-02 09:00:00', 'last_seen', 'last seen yesterday at 22:00',
                           '2026-08-01 22:00:00')
        yield db_path
    finally:
        os.umask(old_umask)


def test_json_export_and_directory_are_owner_only(seeded_db, tmp_path):
    out = export_json(db_path=str(seeded_db), output_path=str(tmp_path / 'analytics' / 'sessions.json'))
    assert _mode(out) == 0o600
    assert _mode(out.parent) == 0o700


def test_dashboard_html_and_directory_are_owner_only(seeded_db, tmp_path):
    out = AnalyticsDashboard(db_path=str(seeded_db), output_file=str(tmp_path / 'analytics' / 'index.html')).export()
    assert _mode(out) == 0o600
    assert _mode(out.parent) == 0o700


def test_excel_export_and_directory_are_owner_only(seeded_db, tmp_path):
    xlsx = tmp_path / 'out' / 'History_wp.xlsx'
    Converter(db_path=str(seeded_db), excel_file=str(xlsx)).db_to_excel()
    assert xlsx.exists()
    assert _mode(xlsx) == 0o600
    assert _mode(xlsx.parent) == 0o700


def test_database_directory_is_owner_only(seeded_db):
    assert _mode(seeded_db) == 0o600
    assert _mode(seeded_db.parent) == 0o700


def test_log_file_and_directory_are_owner_only(tmp_path):
    old_umask = os.umask(0o022)
    root_handlers = logging.getLogger().handlers[:]
    try:
        setup_logging(log_dir=str(tmp_path / 'logs'))
        logging.getLogger('WhatsAppBeacon').info('[ONLINE] Alice')
        log_file = tmp_path / 'logs' / 'whatsapp_beacon.log'
        assert 'Alice' in log_file.read_text()
        assert _mode(log_file) == 0o600
        assert _mode(log_file.parent) == 0o700
    finally:
        os.umask(old_umask)
        for handler in logging.getLogger().handlers[:]:
            if handler not in root_handlers:
                handler.close()
        logging.getLogger().handlers = root_handlers


def test_existing_wide_output_is_tightened_and_existing_directory_left_alone(seeded_db, tmp_path):
    shared = tmp_path / 'shared'
    shared.mkdir(mode=0o755)
    os.chmod(shared, 0o755)
    old = shared / 'sessions.json'
    old.write_text('{}')
    os.chmod(old, 0o644)

    export_json(db_path=str(seeded_db), output_path=str(old))

    assert _mode(old) == 0o600
    assert _mode(shared) == 0o755  # an operator-chosen existing directory is not modified
