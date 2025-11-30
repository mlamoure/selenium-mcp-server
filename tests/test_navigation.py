"""Tests for navigation tools."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from selenium_mcp.tools import navigation
from selenium_mcp.config import Settings


# Get the underlying function from the decorated tool
navigate_fn = navigation.navigate.fn


@pytest.fixture
def mock_ctx(mock_webdriver):
    """Create a mock FastMCP Context."""
    ctx = MagicMock()

    # Mock lifespan context with session manager
    app_ctx = MagicMock()
    app_ctx.settings = Settings()
    app_ctx.settings.dom_max_chars = 20000

    # Mock session
    session = MagicMock()
    session.driver = mock_webdriver
    app_ctx.session_manager.get_session.return_value = session

    ctx.request_context.lifespan_context = app_ctx
    ctx.info = AsyncMock()

    return ctx


@pytest.mark.asyncio
async def test_navigate_without_return_dom(mock_ctx, mock_webdriver):
    """Test navigate without return_dom returns standard response."""
    result = await navigate_fn(
        mock_ctx,
        session_id="test-session",
        url="https://example.com",
        return_dom=False,
    )

    assert result["success"] is True
    assert result["session_id"] == "test-session"
    assert "url" in result
    assert "title" in result
    assert "ready_state" in result
    assert "dom" not in result


@pytest.mark.asyncio
async def test_navigate_with_return_dom(mock_ctx, mock_webdriver):
    """Test navigate with return_dom=True includes DOM content."""
    mock_webdriver.page_source = "<html><body><h1>Test Page</h1></body></html>"

    result = await navigate_fn(
        mock_ctx,
        session_id="test-session",
        url="https://example.com",
        return_dom=True,
    )

    assert result["success"] is True
    assert result["session_id"] == "test-session"
    assert "url" in result
    assert "title" in result
    assert "dom" in result
    assert "html" in result["dom"]
    assert "truncated" in result["dom"]
    assert "total_length" in result["dom"]
    assert "<h1>Test Page</h1>" in result["dom"]["html"]


@pytest.mark.asyncio
async def test_navigate_return_dom_strips_scripts(mock_ctx, mock_webdriver):
    """Test that return_dom strips scripts and styles by default."""
    mock_webdriver.page_source = (
        "<html><script>evil();</script><style>.bad{}</style>"
        "<body>Content</body></html>"
    )

    result = await navigate_fn(
        mock_ctx,
        session_id="test-session",
        url="https://example.com",
        return_dom=True,
    )

    assert "dom" in result
    assert "<script>" not in result["dom"]["html"]
    assert "<style>" not in result["dom"]["html"]
    assert "Content" in result["dom"]["html"]


@pytest.mark.asyncio
async def test_navigate_default_return_dom_is_false(mock_ctx, mock_webdriver):
    """Test that return_dom defaults to False."""
    result = await navigate_fn(
        mock_ctx,
        session_id="test-session",
        url="https://example.com",
    )

    assert "dom" not in result
