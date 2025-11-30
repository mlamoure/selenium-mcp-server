"""Tests for DOM helper utilities."""

import pytest
from unittest.mock import MagicMock

from selenium_mcp.utils.dom_helpers import get_dom_content


@pytest.fixture
def mock_driver_with_html():
    """Create a mock WebDriver with customizable page_source."""
    driver = MagicMock()
    driver.page_source = "<html><body><h1>Test</h1></body></html>"
    return driver


@pytest.mark.asyncio
async def test_get_dom_content_basic(mock_driver_with_html):
    """Test basic DOM content retrieval."""
    result = await get_dom_content(
        mock_driver_with_html,
        max_chars=10000,
    )

    assert "html" in result
    assert result["truncated"] is False
    assert result["html"] == "<html><body><h1>Test</h1></body></html>"


@pytest.mark.asyncio
async def test_get_dom_content_strips_scripts():
    """Test that scripts are stripped by default."""
    driver = MagicMock()
    driver.page_source = "<html><script>alert('evil');</script><body>Content</body></html>"

    result = await get_dom_content(driver, max_chars=10000)

    assert "<script>" not in result["html"]
    assert "alert" not in result["html"]
    assert "Content" in result["html"]


@pytest.mark.asyncio
async def test_get_dom_content_strips_styles():
    """Test that styles are stripped by default."""
    driver = MagicMock()
    driver.page_source = "<html><style>.foo { color: red; }</style><body>Content</body></html>"

    result = await get_dom_content(driver, max_chars=10000)

    assert "<style>" not in result["html"]
    assert "color: red" not in result["html"]
    assert "Content" in result["html"]


@pytest.mark.asyncio
async def test_get_dom_content_preserves_scripts_when_disabled():
    """Test that scripts are preserved when stripping is disabled."""
    driver = MagicMock()
    driver.page_source = "<html><script>alert('hi');</script><body>Content</body></html>"

    result = await get_dom_content(
        driver,
        max_chars=10000,
        strip_scripts_and_styles=False,
    )

    assert "<script>" in result["html"]
    assert "alert" in result["html"]


@pytest.mark.asyncio
async def test_get_dom_content_truncates():
    """Test that long content is truncated."""
    driver = MagicMock()
    driver.page_source = "A" * 1000

    result = await get_dom_content(driver, max_chars=100)

    assert result["truncated"] is True
    assert len(result["html"]) == 100
    assert result["total_length"] == ">100"


@pytest.mark.asyncio
async def test_get_dom_content_no_truncation_when_under_limit():
    """Test that content under limit is not truncated."""
    driver = MagicMock()
    driver.page_source = "A" * 50

    result = await get_dom_content(driver, max_chars=100)

    assert result["truncated"] is False
    assert len(result["html"]) == 50
    assert result["total_length"] == 50
