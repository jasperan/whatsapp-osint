import pytest
from unittest.mock import MagicMock, patch
from src.whatsapp_beacon.beacon import WhatsAppBeacon
from src.whatsapp_beacon.config import Config

@pytest.fixture
def mock_driver():
    with patch('src.whatsapp_beacon.beacon.webdriver.Chrome') as mock:
        yield mock

@pytest.fixture
def mock_webdriver_manager():
    with patch('src.whatsapp_beacon.beacon.ChromeDriverManager') as mock:
        mock.return_value.install.return_value = "/path/to/driver"
        yield mock

@pytest.fixture
def config():
    c = Config("nonexistent.yaml")
    c.config['username'] = "Test User"
    c.config['headless'] = True
    c.config['data_dir'] = "/tmp/data" # Should be mocked usually
    return c

def test_beacon_init(config):
    beacon = WhatsAppBeacon(config)
    assert beacon.driver is None
    assert beacon.config.username == "Test User"

def test_setup_driver(config, mock_driver, mock_webdriver_manager):
    beacon = WhatsAppBeacon(config)
    beacon.setup_driver()

    mock_driver.assert_called_once()
    # Check if headless options were added
    args, kwargs = mock_driver.call_args
    options = kwargs['options']
    # We can't easily inspect C++ objects (ChromeOptions) deeply in mocks easily without more work,
    # but we verify the call happened.

def test_whatsapp_login_headless(config, mock_driver, mock_webdriver_manager):
    beacon = WhatsAppBeacon(config)
    beacon.setup_driver()

    # Mock driver instance
    driver_instance = mock_driver.return_value
    beacon.driver = driver_instance

    # Simulate Login Success
    # We need to mock WebDriverWait to return True immediately
    with patch('src.whatsapp_beacon.beacon.WebDriverWait') as mock_wait:
         # Mocking the presence_of_element_located check
         mock_wait.return_value.until.return_value = True

         beacon.whatsapp_login()

         driver_instance.get.assert_called_with('https://web.whatsapp.com')

def test_check_online_status_true(config, mock_driver):
    beacon = WhatsAppBeacon(config)
    beacon.driver = MagicMock()

    # If find_element succeeds, it returns true
    beacon.driver.find_element.return_value = "Element"

    assert beacon.check_online_status("//xpath") is True

def test_check_online_status_false(config, mock_driver):
    from selenium.common.exceptions import NoSuchElementException
    beacon = WhatsAppBeacon(config)
    beacon.driver = MagicMock()

    beacon.driver.find_element.side_effect = NoSuchElementException("msg")

    assert beacon.check_online_status("//xpath") is False
