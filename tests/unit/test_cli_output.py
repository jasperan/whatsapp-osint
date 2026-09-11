"""Terminal-output guards for the CLI.

Contact names and status text are written by other people on WhatsApp, so they can contain
ANSI escape sequences. Generation 1 of the audit hardened the dashboard (HTML), the Excel
export and the embedded-JSON paths; the ``--last-seen`` listing prints the same data to the
operator's terminal and was not covered (.audit/SECURITY.md, generation 2).

These tests drive the real CLI entry point against a database seeded with hostile text, so
they fail if the sanitising is removed or bypassed by a new print site.
"""
import sys
from pathlib import Path

import pytest

from src.whatsapp_beacon.database import Database
from src.whatsapp_beacon.main import main

# C0 ESC with a colour sequence, a bell, and an OSC 52 clipboard write.
HOSTILE_STATUS = 'online\x1b[31mPWNED\x1b[0m\x07\x1b]52;c;aGFjaw==\x07'
HOSTILE_NAME = 'Evil\x1b[2JContact'


def _seed(data_dir: Path) -> None:
    db = Database(db_path=str(data_dir / 'victims_logs.db'))
    user_id = db.get_or_create_user(HOSTILE_NAME)
    db.insert_presence(user_id, '2026-09-11 08:00:00', 'online', HOSTILE_STATUS)


def _config(data_dir: Path) -> Path:
    config = data_dir / 'config.yaml'
    config.write_text(
        f"data_dir: {data_dir}\nlog_level: INFO\nusername: ''\n", encoding='utf-8'
    )
    return config


def test_last_seen_output_contains_no_control_characters(tmp_path, capsys, monkeypatch):
    _seed(tmp_path)

    # main() reads sys.argv itself, so drive it the way the shell would.
    monkeypatch.setattr(sys, 'argv', ['whatsapp-beacon', '--last-seen', '--config', str(_config(tmp_path))])
    with pytest.raises(SystemExit):
        main()

    out = capsys.readouterr().out
    assert '\x1b' not in out, f"escape sequence reached the terminal: {out!r}"
    assert '\x07' not in out, f"bell/OSC terminator reached the terminal: {out!r}"
    # The visible text must survive: sanitising must not be "drop the whole line".
    assert 'PWNED' in out
    assert 'Evil' in out and 'Contact' in out
