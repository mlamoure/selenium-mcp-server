"""Fixtures for integration tests against real Selenium Grid."""

import json
import pytest
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Configuration
GRID_URL = "https://selenium-api.common-services.home.mikelamoureux.net"
MCP_SERVER_URL = "http://localhost:8000/mcp"


@pytest.fixture
def grid_url():
    """Return the Selenium Grid URL."""
    return GRID_URL


@pytest.fixture
def mcp_server_url():
    """Return the MCP server URL."""
    return MCP_SERVER_URL


class MCPTestClient:
    """Wrapper for MCP client that handles async context properly."""

    def __init__(self, url: str):
        self.url = url
        self._session = None
        self._read_stream = None
        self._write_stream = None
        self._ctx = None

    async def connect(self):
        """Connect to MCP server."""
        self._ctx = streamablehttp_client(self.url)
        self._read_stream, self._write_stream, _ = await self._ctx.__aenter__()
        self._session = ClientSession(self._read_stream, self._write_stream)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool."""
        result = await self._session.call_tool(tool_name, arguments)

        # Extract text content and parse as JSON
        if result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"raw_text": content.text}
        return {}

    async def close(self):
        """Close the connection."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
        if self._ctx:
            try:
                await self._ctx.__aexit__(None, None, None)
            except Exception:
                pass


@pytest.fixture
def mcp_client_factory():
    """Factory for creating MCP test clients."""
    clients = []

    def _create():
        client = MCPTestClient(MCP_SERVER_URL)
        clients.append(client)
        return client

    yield _create

    # Cleanup all clients
    async def cleanup():
        for client in clients:
            await client.close()

    try:
        asyncio.get_event_loop().run_until_complete(cleanup())
    except RuntimeError:
        asyncio.run(cleanup())


async def call_tool(client: MCPTestClient, tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool via the test client.

    Args:
        client: MCP test client instance
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments as a dictionary

    Returns:
        The tool result (parsed from content)
    """
    return await client.call_tool(tool_name, arguments)


@pytest.fixture
async def mcp_session(mcp_client_factory):
    """Create an MCP client session.

    Yields a connected MCPTestClient for calling tools.
    """
    client = mcp_client_factory()
    await client.connect()
    return client


@pytest.fixture
async def session_id(mcp_session):
    """Create a browser session and clean it up after the test.

    Yields the session_id for use in tests.
    """
    # Create session (headed mode for debugging)
    result = await mcp_session.call_tool("create_session", {
        "browser": "chrome",
        "headless": False
    })

    sid = result.get("session_id")
    assert sid is not None, f"Failed to create session: {result}"

    yield sid

    # Cleanup: close the session
    try:
        await mcp_session.call_tool("close_session", {"session_id": sid})
    except Exception:
        pass  # Ignore cleanup errors
