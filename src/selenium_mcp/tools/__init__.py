"""MCP tool definitions organized by category."""

from fastmcp import FastMCP

from .meta import meta_router
from .session import session_router
from .navigation import navigation_router
from .observation import observation_router
from .actions import actions_router
from .waits import waits_router
from .scripting import scripting_router


def create_tool_router() -> FastMCP:
    """Create empty router - tools will be imported async in setup."""
    return FastMCP("SeleniumTools")


async def import_all_tools(router: FastMCP) -> None:
    """Import all tool sub-routers into the main router (async)."""
    await router.import_server(meta_router)
    await router.import_server(session_router)
    await router.import_server(navigation_router)
    await router.import_server(observation_router)
    await router.import_server(actions_router)
    await router.import_server(waits_router)
    await router.import_server(scripting_router)


__all__ = ["create_tool_router", "import_all_tools"]
