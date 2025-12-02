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


def _calculate_effective_recording(
    record_video: Optional[bool],
    recording_default: bool,
    recording_force: bool,
) -> bool:
    """
    Calculate effective recording state based on request and server config.

    Logic:
    - If recording_force is True, always use recording_default (ignore client request)
    - Else if client specified record_video, use that value
    - Else use recording_default

    Args:
        record_video: Client-specified recording preference (None if not specified)
        recording_default: Server default recording state
        recording_force: Whether to ignore client preferences

    Returns:
        Effective recording state to use
    """
    if recording_force:
        return recording_default
    elif record_video is not None:
        return record_video
    else:
        return recording_default


def _merge_recording_capability(
    extra_capabilities: Optional[dict],
    record_video: bool,
) -> dict:
    """
    Merge se:recordVideo into extra_capabilities.

    Args:
        extra_capabilities: Original capabilities dict (may be None)
        record_video: Whether to enable video recording

    Returns:
        New dict with se:recordVideo added
    """
    merged = dict(extra_capabilities) if extra_capabilities else {}
    merged["se:recordVideo"] = record_video
    return merged


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
    record_video: Annotated[
        Optional[bool],
        Field(description="Enable video recording for this session. Uses server default if not specified."),
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
        record_video: Enable video recording (uses server default if not specified)

    Returns:
        Session ID, browser info, and recording status for use in subsequent calls
    """
    app_ctx = get_context(ctx)
    settings = app_ctx.settings

    # Calculate effective recording state
    effective_record_video = _calculate_effective_recording(
        record_video=record_video,
        recording_default=settings.recording_default,
        recording_force=settings.recording_force,
    )

    # Merge se:recordVideo into extra_capabilities
    merged_capabilities = _merge_recording_capability(
        extra_capabilities=extra_capabilities,
        record_video=effective_record_video,
    )

    try:
        session = await app_ctx.session_manager.create_session(
            browser=browser,
            headless=headless,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            extra_capabilities=merged_capabilities,
            record_video=effective_record_video,
        )

        await ctx.info(f"Created {browser} session: {session.session_id} (recording={effective_record_video})")

        return {
            "success": True,
            "session_id": session.session_id,
            "browser": session.browser,
            "headless": headless,
            "created_at": session.created_at,
            "record_video": session.record_video,
            "selenium_session_id": session.selenium_session_id,
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


@session_router.tool(
    description="Get information about the current page",
    tags={"session", "info"},
)
async def get_session_info(
    ctx: Context,
    session_id: Annotated[
        str,
        Field(description="Session ID to get info for"),
    ],
    include_grid_capabilities: Annotated[
        bool,
        Field(description="Include Selenium Grid specific capabilities (CDP, VNC URLs)"),
    ] = False,
    include_full_capabilities: Annotated[
        bool,
        Field(description="Include all browser capabilities (can be verbose)"),
    ] = False,
) -> dict:
    """
    Get detailed information about a browser session.

    Returns session metadata including recording status, Selenium session ID,
    and optionally Grid-specific capabilities for debugging.

    Args:
        session_id: The session ID to query
        include_grid_capabilities: Include se:cdp, se:vnc URLs
        include_full_capabilities: Include complete capabilities dict

    Returns:
        Session information including recording state and node details
    """
    app_ctx = get_context(ctx)

    try:
        session = app_ctx.session_manager.get_session(session_id)

        response = {
            "success": True,
            "session_id": session.session_id,
            "browser": session.browser,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "element_count": session.element_count,
            "current_url": session.driver.current_url if session.driver else None,
            "current_title": session.driver.title if session.driver else None,
            "record_video": session.record_video,
            "selenium_session_id": session.selenium_session_id,
            "capabilities": {
                "browserName": session.capabilities.get("browserName"),
                "browserVersion": session.capabilities.get("browserVersion"),
                "platformName": session.capabilities.get("platformName"),
            },
        }

        if include_grid_capabilities:
            response["grid_capabilities"] = session.get_grid_capabilities()

        if include_full_capabilities:
            response["full_capabilities"] = session.capabilities

        return response

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))