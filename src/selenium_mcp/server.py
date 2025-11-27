"""Main FastMCP server with lifespan management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import settings
from .core.driver_factory import DriverFactory
from .core.session_manager import SessionManager, SessionSweeper
from .tools import create_tool_router, import_all_tools

# Try to import auth provider (requires fastmcp >= 2.13.1)
try:
    from fastmcp.server.auth.providers.debug import DebugTokenVerifier

    HAS_AUTH_SUPPORT = True
except ImportError:
    HAS_AUTH_SUPPORT = False
    DebugTokenVerifier = None

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_auth_verifier():
    """Create auth verifier if API key is configured.

    Returns:
        DebugTokenVerifier instance if API key is configured and auth is supported,
        None otherwise.
    """
    api_key = settings.get_api_key()

    if not api_key:
        logger.info("No API key configured - authentication disabled")
        return None

    if not HAS_AUTH_SUPPORT:
        logger.warning(
            "API key configured but fastmcp auth support not available. "
            "Upgrade to fastmcp >= 2.13.1 for authentication support. "
            "Continuing without authentication."
        )
        return None

    def validate_token(token: str) -> bool:
        """Validate bearer token against configured API key."""
        return token == api_key

    logger.info("API key authentication enabled")
    return DebugTokenVerifier(
        validate=validate_token,
        client_id="selenium-mcp-client",
        scopes=["*"],
    )


@dataclass
class AppContext:
    """Lifespan context holding all services shared across tools."""

    session_manager: SessionManager
    settings: type  # Settings class


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Initialize services on startup, cleanup on shutdown.

    This lifespan function:
    1. Creates the DriverFactory and SessionManager
    2. Starts the background session sweeper
    3. Yields the context for tools to access
    4. On shutdown, stops sweeper and closes all sessions
    """
    logger.info(
        f"Starting Selenium MCP Server (grid: {settings.selenium_grid_url})"
    )

    # Initialize core components
    driver_factory = DriverFactory(
        grid_url=settings.selenium_grid_url,
        page_load_timeout=settings.page_load_timeout_seconds,
        script_timeout=settings.script_timeout_seconds,
        implicit_wait=settings.implicit_wait_seconds,
    )

    session_manager = SessionManager(
        driver_factory=driver_factory,
        max_sessions=settings.max_concurrent_sessions,
        max_lifetime_seconds=settings.session_max_lifetime_seconds,
        max_idle_seconds=settings.session_max_idle_seconds,
    )

    # Start background session sweeper
    sweeper = SessionSweeper(
        session_manager=session_manager,
        interval_seconds=settings.sweep_interval_seconds,
    )
    await sweeper.start()

    try:
        yield AppContext(
            session_manager=session_manager,
            settings=settings,
        )
    finally:
        # Shutdown: stop sweeper and close all sessions
        logger.info("Shutting down Selenium MCP Server...")
        await sweeper.stop()
        closed = await session_manager.close_all()
        logger.info(f"Shutdown complete ({closed} sessions closed)")


def create_server() -> FastMCP:
    """Create and configure the main MCP server (without tools - they're added async)."""
    # Create auth verifier if API key is configured
    auth = create_auth_verifier()

    mcp = FastMCP(
        name="selenium-mcp",
        instructions=(
            "Browser automation server using Selenium WebDriver. "
            "Use create_session to start a browser, then interact with pages "
            "using navigation, observation, and action tools. "
            "Always close sessions when done with close_session."
        ),
        lifespan=app_lifespan,
        auth=auth,
    )
    return mcp


async def setup_server(mcp: FastMCP) -> None:
    """Import all tool routers into the server (async)."""
    tool_router = create_tool_router()
    await import_all_tools(tool_router)
    await mcp.import_server(tool_router)


# Create the global server instance
mcp = create_server()


# Health check endpoint for Docker/Kubernetes health probes
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Health check endpoint for container orchestration."""
    return JSONResponse({"status": "ok"})


def run_server() -> None:
    """Run the MCP server with HTTP transport."""
    # Setup tools before running
    asyncio.run(setup_server(mcp))

    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
    )
