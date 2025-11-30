"""Tests for action tools."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from selenium_mcp.tools import actions
from selenium_mcp.config import Settings


# Get the underlying function from the decorated tool
click_element_fn = actions.click_element.fn


@pytest.fixture
def mock_ctx(mock_webdriver, mock_webelement):
    """Create a mock FastMCP Context."""
    ctx = MagicMock()

    # Mock lifespan context with session manager
    app_ctx = MagicMock()
    app_ctx.settings = Settings()
    app_ctx.settings.dom_max_chars = 20000

    # Mock session
    session = MagicMock()
    session.driver = mock_webdriver
    session.get_element.return_value = mock_webelement
    app_ctx.session_manager.get_session.return_value = session

    ctx.request_context.lifespan_context = app_ctx
    ctx.info = AsyncMock()

    return ctx


@pytest.mark.asyncio
async def test_click_element_without_return_dom(mock_ctx, mock_webdriver, mock_webelement):
    """Test click_element without return_dom returns standard response."""
    result = await click_element_fn(
        mock_ctx,
        session_id="test-session",
        element_id="elem_1",
        return_dom=False,
    )

    assert result["success"] is True
    assert result["session_id"] == "test-session"
    assert result["element_id"] == "elem_1"
    assert result["action"] == "clicked"
    assert "dom" not in result
    mock_webelement.click.assert_called_once()


@pytest.mark.asyncio
async def test_click_element_with_return_dom(mock_ctx, mock_webdriver, mock_webelement):
    """Test click_element with return_dom=True includes DOM content."""
    mock_webdriver.page_source = "<html><body><h1>After Click</h1></body></html>"

    result = await click_element_fn(
        mock_ctx,
        session_id="test-session",
        element_id="elem_1",
        return_dom=True,
    )

    assert result["success"] is True
    assert result["session_id"] == "test-session"
    assert result["element_id"] == "elem_1"
    assert result["action"] == "clicked"
    assert "dom" in result
    assert "html" in result["dom"]
    assert "truncated" in result["dom"]
    assert "total_length" in result["dom"]
    assert "<h1>After Click</h1>" in result["dom"]["html"]


@pytest.mark.asyncio
async def test_click_element_return_dom_strips_scripts(mock_ctx, mock_webdriver, mock_webelement):
    """Test that return_dom strips scripts and styles by default."""
    mock_webdriver.page_source = (
        "<html><script>evil();</script><style>.bad{}</style>"
        "<body>Content</body></html>"
    )

    result = await click_element_fn(
        mock_ctx,
        session_id="test-session",
        element_id="elem_1",
        return_dom=True,
    )

    assert "dom" in result
    assert "<script>" not in result["dom"]["html"]
    assert "<style>" not in result["dom"]["html"]
    assert "Content" in result["dom"]["html"]


@pytest.mark.asyncio
async def test_click_element_default_return_dom_is_false(mock_ctx, mock_webdriver, mock_webelement):
    """Test that return_dom defaults to False."""
    result = await click_element_fn(
        mock_ctx,
        session_id="test-session",
        element_id="elem_1",
    )

    assert "dom" not in result


@pytest.mark.asyncio
async def test_click_element_scrolls_into_view(mock_ctx, mock_webdriver, mock_webelement):
    """Test that click_element scrolls element into view before clicking."""
    await click_element_fn(
        mock_ctx,
        session_id="test-session",
        element_id="elem_1",
    )

    # Verify execute_script was called for scrolling
    mock_webdriver.execute_script.assert_called()
    call_args = mock_webdriver.execute_script.call_args_list[0]
    assert "scrollIntoView" in call_args[0][0]
