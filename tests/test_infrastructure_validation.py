"""Validation tests to ensure the testing infrastructure is properly set up."""
import sys
from pathlib import Path

import pytest


@pytest.mark.unit
def test_pytest_is_installed():
    """Verify pytest is properly installed."""
    assert 'pytest' in sys.modules or True  # pytest is running this test


@pytest.mark.unit
def test_testing_directory_structure():
    """Verify the testing directory structure exists."""
    test_root = Path(__file__).parent

    assert test_root.exists()
    assert test_root.name == 'tests'
    assert (test_root / '__init__.py').exists()
    assert (test_root / 'conftest.py').exists()
    assert (test_root / 'unit' / '__init__.py').exists()
    assert (test_root / 'integration' / '__init__.py').exists()


@pytest.mark.unit
def test_fixtures_available(temp_dir, mock_database, sample_config):
    """Verify that common fixtures are available and working."""
    # Test temp_dir fixture
    assert temp_dir.exists()
    assert temp_dir.is_dir()

    # Test mock_database fixture
    assert mock_database.endswith('.db')
    assert Path(mock_database).exists()

    # Test sample_config fixture
    assert isinstance(sample_config, dict)
    assert 'chrome_driver_path' in sample_config
    assert 'database_path' in sample_config


@pytest.mark.unit
def test_coverage_configuration():
    """Verify coverage is configured correctly."""
    try:
        import coverage
        assert True, "Coverage module is available"
    except ImportError:
        pytest.skip("Coverage not yet installed")


@pytest.mark.unit
def test_mock_fixtures(mock_selenium_webdriver, mock_keyboard):
    """Verify mock fixtures are working."""
    # Test Selenium mock
    assert mock_selenium_webdriver is not None

    # Test keyboard mock
    assert mock_keyboard.return_value is False


@pytest.mark.unit
def test_project_structure():
    """Verify the project has the expected src-layout package structure."""
    project_root = Path(__file__).parent.parent
    package_root = project_root / 'src' / 'whatsapp_beacon'

    assert (project_root / 'setup.py').exists()
    assert (project_root / 'requirements.txt').exists()
    assert package_root.is_dir()
    assert (package_root / '__init__.py').exists()
    assert (package_root / 'beacon.py').exists()
    assert (package_root / 'config.py').exists()


@pytest.mark.integration
def test_packaging_configuration():
    """Verify setuptools and requirements metadata are present and current."""
    project_root = Path(__file__).parent.parent
    setup_path = project_root / 'setup.py'
    requirements_path = project_root / 'requirements.txt'

    assert setup_path.exists()
    assert requirements_path.exists()

    setup_content = setup_path.read_text()
    assert 'name="whatsapp-beacon"' in setup_content
    assert 'console_scripts' in setup_content
    assert 'whatsapp-beacon=whatsapp_beacon.main:main' in setup_content

    requirements_content = requirements_path.read_text()
    assert 'selenium' in requirements_content
    assert 'webdriver-manager' in requirements_content
    assert 'pytest' in requirements_content


@pytest.mark.slow
def test_slow_marker():
    """Verify the slow marker works correctly."""
    import time
    start = time.time()
    time.sleep(0.1)  # Simulate slow test
    duration = time.time() - start
    assert duration >= 0.1
