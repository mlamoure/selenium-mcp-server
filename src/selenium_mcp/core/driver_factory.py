"""Factory for creating RemoteWebDriver instances connected to Selenium Grid."""

from typing import Optional
import anyio
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

from .exceptions import GridConnectionError


class DriverFactory:
    """
    Creates RemoteWebDriver instances connected to Selenium Grid.

    All WebDriver creation is run in a thread pool to avoid blocking
    the async event loop, since Selenium's API is synchronous.
    """

    def __init__(
        self,
        grid_url: str,
        page_load_timeout: int = 30,
        script_timeout: int = 30,
        implicit_wait: int = 0,
    ):
        self.grid_url = grid_url
        self.page_load_timeout = page_load_timeout
        self.script_timeout = script_timeout
        self.implicit_wait = implicit_wait

    async def create(
        self,
        browser: str = "chrome",
        headless: bool = True,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None,
        extra_capabilities: Optional[dict] = None,
    ) -> WebDriver:
        """
        Create a new RemoteWebDriver connected to the Grid.

        Args:
            browser: Browser type (chrome, firefox, edge)
            headless: Run browser in headless mode
            viewport_width: Optional viewport width
            viewport_height: Optional viewport height
            extra_capabilities: Additional capabilities to pass to the browser

        Returns:
            Configured WebDriver instance

        Raises:
            GridConnectionError: If unable to connect to Selenium Grid
            ValueError: If browser type is not supported
        """
        options = self._build_options(
            browser=browser,
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            extra_capabilities=extra_capabilities,
        )

        try:
            # Run blocking WebDriver creation in thread pool
            driver = await anyio.to_thread.run_sync(
                lambda: webdriver.Remote(command_executor=self.grid_url, options=options)
            )

            # Configure timeouts
            await anyio.to_thread.run_sync(
                lambda: driver.set_page_load_timeout(self.page_load_timeout)
            )
            await anyio.to_thread.run_sync(
                lambda: driver.set_script_timeout(self.script_timeout)
            )
            await anyio.to_thread.run_sync(
                lambda: driver.implicitly_wait(self.implicit_wait)
            )

            # Set viewport if specified
            if viewport_width and viewport_height:
                await anyio.to_thread.run_sync(
                    lambda: driver.set_window_size(viewport_width, viewport_height)
                )

            return driver

        except WebDriverException as e:
            raise GridConnectionError(self.grid_url, str(e)) from e

    def _build_options(
        self,
        browser: str,
        headless: bool,
        viewport_width: Optional[int],
        viewport_height: Optional[int],
        extra_capabilities: Optional[dict],
    ):
        """Build browser-specific options object."""
        options_map = {
            "chrome": webdriver.ChromeOptions,
            "firefox": webdriver.FirefoxOptions,
            "edge": webdriver.EdgeOptions,
        }

        if browser.lower() not in options_map:
            raise ValueError(
                f"Unsupported browser: {browser}. "
                f"Supported browsers: {list(options_map.keys())}"
            )

        options = options_map[browser.lower()]()

        # Common arguments for stability
        if browser.lower() == "chrome":
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            if headless:
                options.add_argument("--headless=new")
            if viewport_width and viewport_height:
                options.add_argument(f"--window-size={viewport_width},{viewport_height}")

        elif browser.lower() == "firefox":
            if headless:
                options.add_argument("-headless")

        elif browser.lower() == "edge":
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            if headless:
                options.add_argument("--headless=new")

        # Apply extra capabilities
        if extra_capabilities:
            for key, value in extra_capabilities.items():
                options.set_capability(key, value)

        return options
