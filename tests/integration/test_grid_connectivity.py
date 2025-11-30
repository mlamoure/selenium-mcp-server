"""Phase 1: Direct Selenium Grid connectivity tests.

These tests verify that we can connect directly to the Selenium Grid
before involving the MCP server. This isolates Grid connectivity issues.
"""

import pytest
import httpx
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions


class TestGridConnectivity:
    """Tests for direct Selenium Grid access."""

    def test_grid_status_api(self, grid_url):
        """Verify Selenium Grid status API is accessible and ready.

        Empirical data: Grid /status endpoint returns ready: true
        """
        response = httpx.get(f"{grid_url}/status", timeout=10.0)
        assert response.status_code == 200

        status = response.json()
        assert status.get("value", {}).get("ready") is True, \
            f"Grid not ready: {status}"

        # Report empirical data
        print(f"\n[EMPIRICAL] Grid status: {status.get('value', {}).get('message', 'N/A')}")
        print(f"[EMPIRICAL] Grid ready: {status.get('value', {}).get('ready')}")

    def test_grid_accessible_with_browser(self, grid_url):
        """Verify we can create a browser session and navigate.

        Empirical data: example.com title contains "Example Domain"
        """
        options = ChromeOptions()
        # Headed mode for debugging (no headless flag)

        driver = webdriver.Remote(
            command_executor=grid_url,
            options=options
        )

        try:
            driver.get("https://example.com")

            # Gather empirical data
            title = driver.title
            current_url = driver.current_url

            print(f"\n[EMPIRICAL] Page title: {title}")
            print(f"[EMPIRICAL] Current URL: {current_url}")

            # Verify
            assert "Example Domain" in title, f"Unexpected title: {title}"
            assert "example.com" in current_url

        finally:
            driver.quit()

    def test_grid_can_find_elements(self, grid_url):
        """Verify element finding works on the Grid.

        Empirical data: example.com has h1 with text "Example Domain"
        """
        options = ChromeOptions()

        driver = webdriver.Remote(
            command_executor=grid_url,
            options=options
        )

        try:
            driver.get("https://example.com")

            # Find h1 element
            h1 = driver.find_element("css selector", "h1")

            # Gather empirical data
            h1_text = h1.text
            h1_tag = h1.tag_name

            print(f"\n[EMPIRICAL] H1 tag: {h1_tag}")
            print(f"[EMPIRICAL] H1 text: {h1_text}")

            # Verify
            assert h1_text == "Example Domain", f"Unexpected h1 text: {h1_text}"

        finally:
            driver.quit()

    def test_grid_can_execute_javascript(self, grid_url):
        """Verify JavaScript execution works on the Grid.

        Empirical data: document.title returns "Example Domain"
        """
        options = ChromeOptions()

        driver = webdriver.Remote(
            command_executor=grid_url,
            options=options
        )

        try:
            driver.get("https://example.com")

            # Execute script
            result = driver.execute_script("return document.title")

            print(f"\n[EMPIRICAL] JavaScript document.title: {result}")

            assert result == "Example Domain", f"Unexpected result: {result}"

        finally:
            driver.quit()
