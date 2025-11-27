"""Pytest fixtures for testing Selenium MCP Server."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from selenium_mcp.core.session_manager import SessionManager, BrowserSession
from selenium_mcp.core.driver_factory import DriverFactory


@pytest.fixture
def mock_webelement():
    """Create a mock WebElement."""
    element = MagicMock()
    element.tag_name = "button"
    element.text = "Click Me"
    element.is_displayed.return_value = True
    element.is_enabled.return_value = True
    element.is_selected.return_value = False
    element.get_attribute.return_value = None
    element.location = {"x": 100, "y": 200}
    element.size = {"width": 80, "height": 30}
    element.value_of_css_property.return_value = "pointer"
    return element


@pytest.fixture
def mock_webdriver(mock_webelement):
    """Create a mock WebDriver with common methods."""
    driver = MagicMock()

    # Navigation
    driver.get = MagicMock()
    driver.refresh = MagicMock()
    driver.back = MagicMock()
    driver.forward = MagicMock()
    driver.current_url = "https://example.com"
    driver.title = "Example Page"
    driver.page_source = "<html><body><h1>Hello</h1></body></html>"

    # Execute script
    driver.execute_script = MagicMock(return_value="complete")
    driver.execute_async_script = MagicMock(return_value="async_result")

    # Find elements
    driver.find_element = MagicMock(return_value=mock_webelement)
    driver.find_elements = MagicMock(return_value=[mock_webelement])

    # Screenshot
    driver.get_screenshot_as_png = MagicMock(return_value=b"PNG_DATA")
    driver.get_screenshot_as_base64 = MagicMock(return_value="BASE64_DATA")

    # Window management
    driver.get_window_size = MagicMock(return_value={"width": 1920, "height": 1080})
    driver.set_window_size = MagicMock()
    driver.window_handles = ["window1"]
    driver.current_window_handle = "window1"

    # Timeouts
    driver.set_page_load_timeout = MagicMock()
    driver.set_script_timeout = MagicMock()
    driver.implicitly_wait = MagicMock()

    # Session
    driver.session_id = "mock-session-id"
    driver.capabilities = {
        "browserName": "chrome",
        "browserVersion": "120.0",
        "platformName": "linux",
    }

    # Cleanup
    driver.quit = MagicMock()

    # Logs
    driver.get_log = MagicMock(return_value=[])

    return driver


@pytest.fixture
def mock_driver_factory(mock_webdriver):
    """Create mock DriverFactory that returns mock WebDriver."""
    factory = MagicMock(spec=DriverFactory)
    factory.create = AsyncMock(return_value=mock_webdriver)
    factory.grid_url = "http://mock-grid:4444"
    return factory


@pytest.fixture
def session_manager(mock_driver_factory):
    """Create SessionManager with mocked driver factory."""
    return SessionManager(
        driver_factory=mock_driver_factory,
        max_sessions=5,
        max_lifetime_seconds=900,
        max_idle_seconds=300,
    )


@pytest.fixture
def mock_session(mock_webdriver):
    """Create a mock BrowserSession."""
    import time

    session = BrowserSession(
        session_id="test-session-123",
        driver=mock_webdriver,
        browser="chrome",
        created_at=time.time(),
        last_activity=time.time(),
        capabilities=mock_webdriver.capabilities,
    )
    return session
