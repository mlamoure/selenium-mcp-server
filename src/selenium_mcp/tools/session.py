"""Browser session lifecycle management tools."""

from typing import Annotated, Optional, Literal
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from ..utils.error_mapper import map_selenium_error, create_error_response

session_router = FastMCP(
    name="SessionTools",
    instructions="Browser session lifecycle management",
)


def get_context(ctx: Context):
    """Helper to retrieve app context from lifespan."""
    return ctx.request_context.lifespan_context


@session_router.tool(
    description="Create a new browser session connected to Selenium Grid",
    tags={"session", "lifecycle"},
)
async def create_session(
    ctx: Context,
    browser: Annotated[
        Literal["chrome", "firefox", "edge"],
        Field(description="Browser type to launch"),
    ] = "chrome",
    headless: Annotated[
        bool,
        Field(description="Run browser in headless mode (no visible window)"),
    ] = True,
    viewport_width: Annotated[
        Optional[int],
        Field(description="Browser viewport width in pixels"),
    ] = None,
    viewport_height: Annotated[
        Optional[int],
        Field(description="Browser viewport height in pixels"),
    ] = None,
    extra_capabilities: Annotated[
        Optional[dict],
        Field(description="Additional browser capabilities for Selenium Grid"),
    ] = None,
) -> dict:
    """
    Create a new browser session connected to Selenium Grid.

    Returns a session_id that must be used in all subsequent tool calls.
    The session will be automatically closed after the configured timeout.

    Args:
        browser: Browser type (chrome, firefox, or edge)
        headless: Whether to run in headless mode
        viewport_width: Optional viewport width
        viewport_height: Optional viewport height
        extra_capabilities: Additional WebDriver capabilities

    Returns:
        Session ID and browser info for use in subsequent calls
    """
    app_ctx = get_context(ctx)

    try:
        session = await app_ctx.session_manager.create_session(
            browser=browser,
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            extra_capabilities=extra_capabilities,
        )

        await ctx.info(f"Created {browser} session: {session.session_id}")

        return {
            "success": True,
            "session_id": session.session_id,
            "browser": session.browser,
            "headless": headless,
            "created_at": session.created_at,
            "capabilities": {
                "browserName": session.capabilities.get("browserName"),
                "browserVersion": session.capabilities.get("browserVersion"),
                "platformName": session.capabilities.get("platformName"),
            },
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@session_router.tool(
    description="Close a browser session and release all resources",
    tags={"session", "lifecycle"},
)
async def close_session(
    ctx: Context,
    session_id: Annotated[
        str,
        Field(description="Session ID to close"),
    ],
) -> dict:
    """
    Close a browser session and release its resources.

    This quits the browser, removes all registered elements,
    and frees the session slot.

    Args:
        session_id: The session ID to close

    Returns:
        Confirmation that the session was closed
    """
    app_ctx = get_context(ctx)

    try:
        closed = await app_ctx.session_manager.close_session(session_id)

        if not closed:
            from ..core.exceptions import SessionNotFoundError
            raise SessionNotFoundError(session_id)

        await ctx.info(f"Closed session: {session_id}")

        return {
            "success": True,
            "closed": True,
            "session_id": session_id,
            "message": "Session closed successfully",
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))
