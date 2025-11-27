"""Meta and health check tools."""

from typing import Optional, Annotated
from pydantic import Field
from fastmcp import FastMCP, Context

from .. import __version__

meta_router = FastMCP(
    name="MetaTools",
    instructions="Health check and server information tools",
)


def get_context(ctx: Context):
    """Helper to retrieve app context from lifespan."""
    return ctx.request_context.lifespan_context


@meta_router.tool(
    description="Health check - verify server is running and get server info",
    tags={"meta", "health"},
)
async def ping() -> dict:
    """
    Simple health check returning server status.

    Returns:
        Server status, version, and configuration info
    """
    from ..config import settings

    return {
        "status": "ok",
        "version": __version__,
        "grid_url": settings.selenium_grid_url,
    }


@meta_router.tool(
    description="List all active browser sessions",
    tags={"meta", "sessions"},
)
async def list_sessions(
    ctx: Context,
    browser: Annotated[
        Optional[str],
        Field(description="Optional filter by browser type (chrome, firefox, edge)"),
    ] = None,
) -> dict:
    """
    List all active browser sessions with their metadata.

    Args:
        browser: Optional filter by browser type

    Returns:
        List of active sessions with IDs, browser types, and timestamps
    """
    app_ctx = get_context(ctx)
    sessions = app_ctx.session_manager.list_sessions(browser=browser)

    return {
        "sessions": sessions,
        "count": len(sessions),
    }
