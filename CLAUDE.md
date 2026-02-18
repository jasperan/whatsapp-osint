# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**WhatsApp Beacon** is a Selenium-based OSINT tool that monitors WhatsApp Web to track when specific contacts go online/offline. It logs session data to SQLite and can export to Excel.

## Commands

### Install
```bash
pip install -r requirements.txt
# Or install as a package:
pip install -e .
```

### Run
```bash
# Module invocation (recommended during development)
python3 -m src.whatsapp_beacon.main -u "Contact Name"

# With options
python3 -m src.whatsapp_beacon.main -u "Contact Name" -l es --headless

# After pip install:
whatsapp-beacon -u "Contact Name"
```

### Tests
```bash
# All tests
pytest

# Single test file
pytest tests/unit/test_beacon.py

# Single test
pytest tests/unit/test_beacon.py::TestClassName::test_method_name

# With coverage
coverage run -m pytest && coverage report
```

## Architecture

The package lives in `src/whatsapp_beacon/` and follows a clean separation:

- **`config.py` (`Config`)**: Loads settings in priority order: defaults → `config.yaml` → CLI args. Properties expose each setting. No env var support yet (stub exists).
- **`beacon.py` (`WhatsAppBeacon`)**: Core class. Manages Selenium Chrome driver, WhatsApp Web login, contact search, and the polling loop. Supports multi-language online status detection via the `ONLINE_STATUS` dict (en/de/pt/es/fr/it/cat/tr).
- **`database.py` (`Database`)**: SQLite wrapper. Two tables: `Users` (user_name) and `Sessions` (start/end timestamps, duration). Uses separate columns for date/hour/minute/second rather than a single timestamp column.
- **`db_to_excel.py` (`Converter`)**: Reads Sessions+Users via JOIN and writes to `History_wp.xlsx` using openpyxl.
- **`logger.py`**: Sets up colorlog console handler + plain file handler writing to `logs/whatsapp_beacon.log`.
- **`main.py`**: Entry point — parses args, builds `Config`, calls `WhatsAppBeacon.run()`.

### Runtime-generated directories
- `data/` — SQLite DB (`victims_logs.db`) and Chrome profile (`chrome_profile/`)
- `logs/` — `whatsapp_beacon.log`

### Authentication / First Run
Chrome session is persisted in `data/chrome_profile`. First run must be non-headless to scan the WhatsApp QR code. Subsequent runs (including headless) reuse the saved session.

### Adding a New Language
Add an entry to the `ONLINE_STATUS` dict in `beacon.py` with the ISO language code and the localized "online" status string as it appears in WhatsApp Web.

### Fixing Broken XPaths (WhatsApp DOM Changes)
WhatsApp Web updates its DOM structure periodically. When selectors break, update the three candidate lists near the top of `beacon.py`:
- `_LOGIN_READY_XPATHS` — used to detect a successful login
- `_SEARCH_BOX_XPATHS` — the search input element
- `_SEARCH_RESULT_XPATHS` — the first chat result row

Prefer `data-testid` and `aria-label` attributes over positional XPaths; they survive layout changes better.

## Key Dependencies
- `selenium` + `webdriver-manager` — browser automation (ChromeDriver auto-managed)
- `pyyaml` — config file parsing
- `openpyxl` — Excel export
- `colorlog` — colored console logging
- `pytest` + `pytest-mock` + `coverage` — testing
