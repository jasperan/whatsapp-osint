"""Shared pytest fixtures and configuration."""
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_selenium_webdriver():
    """Mock Selenium WebDriver for testing."""
    with patch('selenium.webdriver.Chrome') as mock_driver:
        driver_instance = Mock()
        mock_driver.return_value = driver_instance
        yield driver_instance


@pytest.fixture
def mock_database():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    yield db_path
    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_excel_file(temp_dir):
    """Create a temporary Excel file path for testing."""
    return temp_dir / "test_workbook.xlsx"


@pytest.fixture
def sample_config():
    """Provide sample configuration for testing."""
    return {
        'chrome_driver_path': '/path/to/chromedriver',
        'database_path': 'test_victims_logs.db',
        'excel_file': 'test_history.xlsx',
        'timeout': 30,
    }


@pytest.fixture
def mock_keyboard():
    """Mock keyboard module for testing."""
    with patch('keyboard.is_pressed') as mock_is_pressed:
        mock_is_pressed.return_value = False
        yield mock_is_pressed


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset module imports between tests to ensure isolation."""
    import sys
    modules_to_reset = [
        key for key in sys.modules.keys() 
        if key.startswith('utils') or key == 'whatsappbeacon'
    ]
    for module in modules_to_reset:
        sys.modules.pop(module, None)


@pytest.fixture
def capture_logs():
    """Capture log outputs during tests."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Get root logger
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Cleanup
    logger.removeHandler(handler)


def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )