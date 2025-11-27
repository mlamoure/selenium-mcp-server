"""Wait and synchronization tools."""

import re
from typing import Annotated, Optional, Literal
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import anyio
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ..utils.error_mapper import map_selenium_error, create_error_response, ErrorCode
from ..utils.element_resolver import get_by_strategy, serialize_element

waits_router = FastMCP(
    name="WaitTools",
    instructions="Wait for conditions before proceeding",
)


def get_context(ctx: Context):
    """Helper to retrieve app context from lifespan."""
    return ctx.request_context.lifespan_context


def get_session(ctx: Context, session_id: str):
    """Get session from manager."""
    app_ctx = get_context(ctx)
    return app_ctx.session_manager.get_session(session_id)


@waits_router.tool(
    description="Wait for an element to meet a condition",
    tags={"wait", "element"},
)
async def wait_for_selector(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    strategy: Annotated[
        Literal["css", "xpath", "id", "name", "class", "tag", "link_text"],
        Field(description="Locator strategy"),
    ],
    selector: Annotated[str, Field(description="Selector value")],
    condition: Annotated[
        Literal["exists", "visible", "clickable", "hidden"],
        Field(description="Condition to wait for"),
    ] = "visible",
    timeout_ms: Annotated[
        Optional[int],
        Field(description="Timeout in milliseconds"),
    ] = None,
) -> dict:
    """
    Wait for an element to meet a specified condition.

    Conditions:
    - exists: Element is present in DOM (may not be visible)
    - visible: Element is present and visible
    - clickable: Element is visible and can be clicked
    - hidden: Element is not visible or not in DOM

    Args:
        session_id: Active session ID
        strategy: Locator strategy (css, xpath, id, etc.)
        selector: Selector string
        condition: What to wait for
        timeout_ms: Timeout in milliseconds (default from config)

    Returns:
        Success status and element ID (if exists/visible/clickable)
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        timeout_seconds = (
            timeout_ms / 1000.0
            if timeout_ms
            else app_ctx.settings.default_wait_timeout_seconds
        )

        by = get_by_strategy(strategy)
        locator = (by, selector)

        # Map conditions to expected conditions
        condition_map = {
            "exists": EC.presence_of_element_located,
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable,
            "hidden": EC.invisibility_of_element_located,
        }

        ec = condition_map[condition](locator)
        wait = WebDriverWait(session.driver, timeout_seconds)

        try:
            result = await anyio.to_thread.run_sync(lambda: wait.until(ec))

            # For non-hidden conditions, register the element
            if condition != "hidden" and result:
                element_id = session.register_element(result)
                element_info = await anyio.to_thread.run_sync(
                    lambda: serialize_element(result)
                )

                return {
                    "success": True,
                    "session_id": session_id,
                    "condition": condition,
                    "element_id": element_id,
                    "element": element_info,
                }
            else:
                return {
                    "success": True,
                    "session_id": session_id,
                    "condition": condition,
                    "message": f"Element is now {condition}",
                }

        except TimeoutException:
            error_response = create_error_response(
                ErrorCode.TIMEOUT,
                f"Timeout waiting for element to be {condition}: {strategy}={selector}",
            )
            raise ToolError(str(error_response.to_dict()))

    except ToolError:
        raise
    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@waits_router.tool(
    description="Wait for the URL to match a pattern",
    tags={"wait", "navigation"},
)
async def wait_for_url(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    pattern: Annotated[
        str,
        Field(description="URL pattern (substring or regex)"),
    ],
    is_regex: Annotated[
        bool,
        Field(description="Whether pattern is a regex"),
    ] = False,
    timeout_ms: Annotated[
        Optional[int],
        Field(description="Timeout in milliseconds"),
    ] = None,
) -> dict:
    """
    Wait for the URL to match a pattern.

    Args:
        session_id: Active session ID
        pattern: URL substring or regex pattern to match
        is_regex: Whether to treat pattern as regex (default: substring match)
        timeout_ms: Timeout in milliseconds

    Returns:
        Success status and final URL
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        timeout_seconds = (
            timeout_ms / 1000.0
            if timeout_ms
            else app_ctx.settings.default_wait_timeout_seconds
        )

        if is_regex:
            compiled = re.compile(pattern)
            ec = EC.url_matches(compiled)
        else:
            ec = EC.url_contains(pattern)

        wait = WebDriverWait(session.driver, timeout_seconds)

        try:
            await anyio.to_thread.run_sync(lambda: wait.until(ec))
            url = await anyio.to_thread.run_sync(lambda: session.driver.current_url)

            return {
                "success": True,
                "session_id": session_id,
                "url": url,
                "pattern": pattern,
            }

        except TimeoutException:
            current_url = await anyio.to_thread.run_sync(
                lambda: session.driver.current_url
            )
            error_response = create_error_response(
                ErrorCode.TIMEOUT,
                f"Timeout waiting for URL to match '{pattern}'. Current: {current_url}",
            )
            raise ToolError(str(error_response.to_dict()))

    except ToolError:
        raise
    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@waits_router.tool(
    description="Wait for the page to reach a ready state",
    tags={"wait", "page"},
)
async def wait_for_ready_state(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    state: Annotated[
        Literal["complete", "interactive"],
        Field(description="Ready state to wait for"),
    ] = "complete",
    timeout_ms: Annotated[
        Optional[int],
        Field(description="Timeout in milliseconds"),
    ] = None,
) -> dict:
    """
    Wait for the document to reach a ready state.

    States:
    - interactive: DOM is ready, resources may still be loading
    - complete: Page is fully loaded including resources

    Args:
        session_id: Active session ID
        state: Ready state to wait for
        timeout_ms: Timeout in milliseconds

    Returns:
        Success status and actual ready state
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        timeout_seconds = (
            timeout_ms / 1000.0
            if timeout_ms
            else app_ctx.settings.default_wait_timeout_seconds
        )

        valid_states = ["interactive", "complete"] if state == "interactive" else ["complete"]

        def check_ready_state(driver):
            current = driver.execute_script("return document.readyState")
            return current if current in valid_states else False

        wait = WebDriverWait(session.driver, timeout_seconds)

        try:
            ready_state = await anyio.to_thread.run_sync(
                lambda: wait.until(check_ready_state)
            )

            return {
                "success": True,
                "session_id": session_id,
                "ready_state": ready_state,
            }

        except TimeoutException:
            current = await anyio.to_thread.run_sync(
                lambda: session.driver.execute_script("return document.readyState")
            )
            error_response = create_error_response(
                ErrorCode.TIMEOUT,
                f"Timeout waiting for ready state '{state}'. Current: {current}",
            )
            raise ToolError(str(error_response.to_dict()))

    except ToolError:
        raise
    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@waits_router.tool(
    description="Wait for text to appear on the page",
    tags={"wait", "text"},
)
async def wait_for_text(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    text: Annotated[str, Field(description="Text to wait for")],
    element_id: Annotated[
        Optional[str],
        Field(description="Optional element to search within"),
    ] = None,
    timeout_ms: Annotated[
        Optional[int],
        Field(description="Timeout in milliseconds"),
    ] = None,
) -> dict:
    """
    Wait for specific text to appear on the page or within an element.

    Args:
        session_id: Active session ID
        text: Text content to wait for
        element_id: Optional element to search within (otherwise searches body)
        timeout_ms: Timeout in milliseconds

    Returns:
        Success status
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        timeout_seconds = (
            timeout_ms / 1000.0
            if timeout_ms
            else app_ctx.settings.default_wait_timeout_seconds
        )

        if element_id:
            element = session.get_element(element_id)

            def check_text(driver):
                return text in element.text

        else:

            def check_text(driver):
                body_text = driver.execute_script("return document.body.innerText")
                return text in body_text

        wait = WebDriverWait(session.driver, timeout_seconds)

        try:
            await anyio.to_thread.run_sync(lambda: wait.until(check_text))

            return {
                "success": True,
                "session_id": session_id,
                "text_found": text,
            }

        except TimeoutException:
            error_response = create_error_response(
                ErrorCode.TIMEOUT,
                f"Timeout waiting for text: '{text}'",
            )
            raise ToolError(str(error_response.to_dict()))

    except ToolError:
        raise
    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))
