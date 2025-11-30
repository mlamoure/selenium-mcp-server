"""DOM observation and element query tools."""

import base64
from typing import Annotated, Optional, Literal
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import anyio

from ..utils.error_mapper import map_selenium_error, create_error_response
from ..utils.element_resolver import (
    get_by_strategy,
    serialize_element,
    is_clickable,
)
from ..utils.dom_helpers import get_dom_content

observation_router = FastMCP(
    name="ObservationTools",
    instructions="DOM observation, element querying, and screenshot tools",
)


def get_context(ctx: Context):
    """Helper to retrieve app context from lifespan."""
    return ctx.request_context.lifespan_context


def get_session(ctx: Context, session_id: str):
    """Get session from manager."""
    app_ctx = get_context(ctx)
    return app_ctx.session_manager.get_session(session_id)


@observation_router.tool(
    description="Get the DOM HTML structure of the current page",
    tags={"observation", "dom"},
)
async def get_dom(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    max_chars: Annotated[
        Optional[int],
        Field(description="Maximum characters to return (default: from config)"),
    ] = None,
    strip_scripts_and_styles: Annotated[
        bool,
        Field(description="Remove <script> and <style> tags from output"),
    ] = True,
) -> dict:
    """
    Get the DOM HTML structure of the current page.

    Useful for understanding page structure and finding elements.
    Large pages will be truncated to max_chars.

    Args:
        session_id: Active session ID
        max_chars: Maximum characters to return
        strip_scripts_and_styles: Whether to remove script/style tags

    Returns:
        HTML content (possibly truncated) and metadata
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        limit = max_chars or app_ctx.settings.dom_max_chars

        dom_content = await get_dom_content(
            session.driver,
            max_chars=limit,
            strip_scripts_and_styles=strip_scripts_and_styles,
        )

        return {
            "success": True,
            "session_id": session_id,
            **dom_content,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@observation_router.tool(
    description="Get all visible text content from the page",
    tags={"observation", "text"},
)
async def get_visible_text(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    max_chars: Annotated[
        Optional[int],
        Field(description="Maximum characters to return (default: from config)"),
    ] = None,
) -> dict:
    """
    Extract all visible text content from the current page.

    This returns the text that a user would see, excluding hidden elements.

    Args:
        session_id: Active session ID
        max_chars: Maximum characters to return

    Returns:
        Visible text content (possibly truncated)
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        limit = max_chars or app_ctx.settings.visible_text_max_chars

        # Get visible text via JavaScript
        text = await anyio.to_thread.run_sync(
            lambda: session.driver.execute_script("return document.body.innerText")
        )

        text = text or ""
        truncated = len(text) > limit
        if truncated:
            text = text[:limit]

        return {
            "success": True,
            "session_id": session_id,
            "text": text,
            "truncated": truncated,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@observation_router.tool(
    description="Find elements matching a selector and return their IDs for later use",
    tags={"observation", "elements"},
)
async def query_elements(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    strategy: Annotated[
        Literal["css", "xpath", "id", "name", "class", "tag", "link_text"],
        Field(description="Locator strategy to use"),
    ],
    selector: Annotated[str, Field(description="Selector value for the chosen strategy")],
    max_results: Annotated[
        int,
        Field(description="Maximum number of elements to return"),
    ] = 20,
) -> dict:
    """
    Find elements matching a selector and return element IDs.

    The returned element_ids can be used with action tools like click_element.
    Elements are registered in the session for later reference.

    Args:
        session_id: Active session ID
        strategy: Locator strategy (css, xpath, id, name, class, tag, link_text)
        selector: Selector string for the chosen strategy
        max_results: Maximum elements to return

    Returns:
        List of elements with their IDs, properties, and attributes
    """
    try:
        session = get_session(ctx, session_id)

        by = get_by_strategy(strategy)

        # Find elements
        elements = await anyio.to_thread.run_sync(
            lambda: session.driver.find_elements(by, selector)
        )

        total_found = len(elements)
        elements = elements[:max_results]

        # Register and serialize elements
        results = []
        for el in elements:
            element_id = session.register_element(el)
            serialized = await anyio.to_thread.run_sync(
                lambda e=el: serialize_element(e)
            )
            clickable = await anyio.to_thread.run_sync(lambda e=el: is_clickable(e))

            results.append({
                "element_id": element_id,
                "is_clickable": clickable,
                **serialized,
            })

        return {
            "success": True,
            "session_id": session_id,
            "elements": results,
            "count": len(results),
            "total_found": total_found,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@observation_router.tool(
    description="Take a screenshot of the current page",
    tags={"observation", "screenshot"},
)
async def get_screenshot(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    full_page: Annotated[
        bool,
        Field(description="Capture full page (Chrome only, may not work in all cases)"),
    ] = False,
) -> dict:
    """
    Take a screenshot of the current page.

    Returns base64-encoded PNG image data.

    Args:
        session_id: Active session ID
        full_page: Attempt full page capture (browser support varies)

    Returns:
        Base64-encoded screenshot image and dimensions
    """
    try:
        session = get_session(ctx, session_id)

        if full_page:
            # Try full page screenshot (Chrome-specific)
            try:
                # Get page dimensions
                dimensions = await anyio.to_thread.run_sync(
                    lambda: session.driver.execute_script(
                        "return {width: document.body.scrollWidth, height: document.body.scrollHeight}"
                    )
                )
                # Resize window to full page
                await anyio.to_thread.run_sync(
                    lambda: session.driver.set_window_size(
                        dimensions["width"], dimensions["height"]
                    )
                )
            except Exception:
                pass  # Fall back to viewport screenshot

        # Take screenshot
        screenshot_bytes = await anyio.to_thread.run_sync(
            lambda: session.driver.get_screenshot_as_png()
        )
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        # Get dimensions
        size = await anyio.to_thread.run_sync(
            lambda: session.driver.get_window_size()
        )

        return {
            "success": True,
            "session_id": session_id,
            "image_base64": screenshot_b64,
            "format": "png",
            "width": size.get("width"),
            "height": size.get("height"),
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@observation_router.tool(
    description="Get browser console logs",
    tags={"observation", "logs"},
)
async def get_console_logs(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    level: Annotated[
        Literal["all", "error", "warning", "info"],
        Field(description="Filter logs by level"),
    ] = "all",
) -> dict:
    """
    Get browser console logs (Chrome/Chromium only).

    Note: This feature may not be available in all browsers.

    Args:
        session_id: Active session ID
        level: Filter by log level (all, error, warning, info)

    Returns:
        List of console log entries
    """
    try:
        session = get_session(ctx, session_id)

        # Get logs (Chrome-specific)
        try:
            logs = await anyio.to_thread.run_sync(
                lambda: session.driver.get_log("browser")
            )
        except Exception:
            return {
                "success": True,
                "session_id": session_id,
                "logs": [],
                "message": "Console logs not available for this browser",
            }

        # Filter by level
        if level != "all":
            level_map = {
                "error": ["SEVERE"],
                "warning": ["WARNING"],
                "info": ["INFO"],
            }
            allowed = level_map.get(level, [])
            logs = [log for log in logs if log.get("level") in allowed]

        return {
            "success": True,
            "session_id": session_id,
            "logs": logs,
            "count": len(logs),
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))
