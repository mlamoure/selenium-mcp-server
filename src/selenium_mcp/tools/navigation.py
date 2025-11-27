"""Page navigation tools."""

from typing import Annotated
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import anyio

from ..core.exceptions import DomainNotAllowedError
from ..utils.error_mapper import map_selenium_error, create_error_response
from ..utils.guardrails import validate_domain, extract_domain

navigation_router = FastMCP(
    name="NavigationTools",
    instructions="Browser navigation and page context tools",
)


def get_context(ctx: Context):
    """Helper to retrieve app context from lifespan."""
    return ctx.request_context.lifespan_context


def get_session(ctx: Context, session_id: str):
    """Get session from manager, raising appropriate error if not found."""
    app_ctx = get_context(ctx)
    return app_ctx.session_manager.get_session(session_id)


async def get_page_state(driver) -> dict:
    """Get current page state from driver."""
    url = await anyio.to_thread.run_sync(lambda: driver.current_url)
    title = await anyio.to_thread.run_sync(lambda: driver.title)
    ready_state = await anyio.to_thread.run_sync(
        lambda: driver.execute_script("return document.readyState")
    )
    return {"url": url, "title": title, "ready_state": ready_state}


@navigation_router.tool(
    description="Navigate to a URL",
    tags={"navigation"},
)
async def navigate(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    url: Annotated[str, Field(description="URL to navigate to")],
) -> dict:
    """
    Navigate browser to the specified URL.

    Subject to domain guardrails if ALLOWED_DOMAINS is configured.

    Args:
        session_id: Active session ID from create_session
        url: Full URL to navigate to (e.g., "https://example.com")

    Returns:
        Final URL (after redirects), page title, and ready state
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        # Domain guardrail check
        allowed_domains = app_ctx.settings.allowed_domain_list
        if allowed_domains and not validate_domain(url, allowed_domains):
            domain = extract_domain(url)
            raise DomainNotAllowedError(domain or url, allowed_domains)

        # Navigate
        await anyio.to_thread.run_sync(lambda: session.driver.get(url))

        # Get resulting page state
        state = await get_page_state(session.driver)

        await ctx.info(f"Navigated to {state['url']}")

        return {
            "success": True,
            "session_id": session_id,
            **state,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@navigation_router.tool(
    description="Reload the current page",
    tags={"navigation"},
)
async def reload_page(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
) -> dict:
    """
    Reload/refresh the current page.

    Args:
        session_id: Active session ID

    Returns:
        Current URL, title, and ready state after reload
    """
    try:
        session = get_session(ctx, session_id)
        await anyio.to_thread.run_sync(lambda: session.driver.refresh())
        state = await get_page_state(session.driver)

        return {
            "success": True,
            "session_id": session_id,
            **state,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@navigation_router.tool(
    description="Navigate back in browser history",
    tags={"navigation"},
)
async def navigate_back(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
) -> dict:
    """
    Navigate back to the previous page in browser history.

    Args:
        session_id: Active session ID

    Returns:
        Current URL, title, and ready state after navigation
    """
    try:
        session = get_session(ctx, session_id)
        await anyio.to_thread.run_sync(lambda: session.driver.back())
        state = await get_page_state(session.driver)

        return {
            "success": True,
            "session_id": session_id,
            **state,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@navigation_router.tool(
    description="Navigate forward in browser history",
    tags={"navigation"},
)
async def navigate_forward(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
) -> dict:
    """
    Navigate forward to the next page in browser history.

    Args:
        session_id: Active session ID

    Returns:
        Current URL, title, and ready state after navigation
    """
    try:
        session = get_session(ctx, session_id)
        await anyio.to_thread.run_sync(lambda: session.driver.forward())
        state = await get_page_state(session.driver)

        return {
            "success": True,
            "session_id": session_id,
            **state,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@navigation_router.tool(
    description="Get information about the current page",
    tags={"navigation", "observation"},
)
async def get_page_info(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
) -> dict:
    """
    Get current page metadata: URL, title, and document ready state.

    Args:
        session_id: Active session ID

    Returns:
        Current URL, page title, and document.readyState
    """
    try:
        session = get_session(ctx, session_id)
        state = await get_page_state(session.driver)

        return {
            "success": True,
            "session_id": session_id,
            **state,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))
