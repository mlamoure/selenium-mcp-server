# Selenium MCP Server

A Model Context Protocol (MCP) server that provides browser automation capabilities via Selenium Grid. AI agents can drive web browsers step-by-step using MCP tools instead of writing Selenium scripts directly.

## Architecture

Built with [FastMCP 2.0](https://github.com/jlowin/fastmcp) using **Streamable HTTP transport** for self-hosted deployment. Deploy once on your infrastructure and connect from any MCP client remotely.

- **Streamable HTTP** - Native HTTP transport with streaming support
- **Selenium Grid Backend** - Separates browser instances from the MCP server for independent scaling
- **Centralized Endpoint** - Single server serves multiple AI agents/clients

## Features

- **35+ MCP Tools** for complete browser automation
- **Session Management** with automatic timeout and cleanup
- **Element Registry** for stable element references across tool calls
- **Domain Guardrails** to restrict navigation to allowed domains
- **Structured Errors** with helpful suggestions for AI recovery
- **Docker Support** with Selenium Grid included

## Quick Start

### Deploy from Container Registry (Recommended)

Deploy directly without cloning the repository. Create a `docker-compose.yml`:

```yaml
services:
  selenium-mcp:
    image: ghcr.io/mlamoure/selenium-mcp-server:latest
    ports:
      - "8000:8000"
    environment:
      - SELENIUM_MCP_SELENIUM_GRID_URL=http://selenium-hub:4444
    depends_on:
      selenium-hub:
        condition: service_healthy
    restart: unless-stopped

  selenium-hub:
    image: selenium/hub:4.25
    ports:
      - "4444:4444"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4444/status"]
      interval: 10s
      timeout: 5s
      retries: 5

  chrome-node:
    image: selenium/node-chrome:4.25
    shm_size: 2g
    environment:
      - SE_EVENT_BUS_HOST=selenium-hub
      - SE_EVENT_BUS_PUBLISH_PORT=4442
      - SE_EVENT_BUS_SUBSCRIBE_PORT=4443
      - SE_NODE_MAX_SESSIONS=4
    depends_on:
      selenium-hub:
        condition: service_healthy
```

```bash
docker-compose up -d

# MCP server: http://localhost:8000/mcp/
# Selenium Grid UI: http://localhost:4444
```

### Using Docker Compose (From Source)

```bash
git clone https://github.com/mlamoure/selenium-mcp-server.git
cd selenium-mcp-server
docker-compose up -d

# MCP server: http://localhost:8000/mcp/
# Selenium Grid UI: http://localhost:4444
```

### Manual Installation

```bash
# Requires Python 3.12+ and a running Selenium Grid
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set Grid URL and run
export SELENIUM_MCP_SELENIUM_GRID_URL=http://localhost:4444
python -m selenium_mcp
```

## Tool Categories

### Session Management
- `create_session` - Create a new browser session
- `close_session` - Close a browser session
- `list_sessions` - List all active sessions
- `ping` - Health check

### Navigation
- `navigate` - Go to a URL
- `reload_page` - Refresh the current page
- `navigate_back` / `navigate_forward` - Browser history
- `get_page_info` - Get current URL, title, and ready state

### Observation
- `get_dom` - Get page HTML (with optional script/style stripping)
- `get_visible_text` - Get all visible text content
- `query_elements` - Find elements and get stable IDs
- `get_screenshot` - Capture page screenshot
- `get_console_logs` - Get browser console logs

### Actions
- `click_element` / `click_selector` - Click elements
- `type_text` - Type into input fields
- `clear_element` - Clear input content
- `set_checkbox_state` - Check/uncheck checkboxes
- `select_dropdown_option` - Select from dropdowns
- `scroll_to_element` / `scroll_by` - Scroll the page
- `hover_element` - Mouse hover
- `drag_drop` - Drag and drop
- `send_keys` - Send keyboard keys
- `upload_file` - Upload files

### Waits
- `wait_for_selector` - Wait for element (exists/visible/clickable/hidden)
- `wait_for_url` - Wait for URL to match pattern
- `wait_for_ready_state` - Wait for document ready state
- `wait_for_text` - Wait for text to appear

### JavaScript
- `execute_script` - Run synchronous JavaScript
- `execute_async_script` - Run asynchronous JavaScript

## Configuration

Configure via environment variables (prefix: `SELENIUM_MCP_`):

| Variable | Description | Default |
|----------|-------------|---------|
| `SELENIUM_GRID_URL` | Selenium Grid endpoint | `http://localhost:4444` |
| `DEFAULT_BROWSER` | Default browser type | `chrome` |
| `MAX_CONCURRENT_SESSIONS` | Maximum simultaneous sessions | `10` |
| `SESSION_MAX_LIFETIME_SECONDS` | Session auto-close timeout | `900` |
| `SESSION_MAX_IDLE_SECONDS` | Idle session timeout | `300` |
| `ALLOWED_DOMAINS` | Comma-separated allowed domains | (all allowed) |
| `DOM_MAX_CHARS` | Max chars for get_dom | `20000` |
| `DEFAULT_WAIT_TIMEOUT_MS` | Default wait timeout | `10000` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |

## Example Usage

```python
# Typical AI agent workflow:

# 1. Create a session
result = await client.call_tool("create_session", {"browser": "chrome"})
session_id = result["session_id"]

# 2. Navigate to a page
await client.call_tool("navigate", {
    "session_id": session_id,
    "url": "https://example.com"
})

# 3. Find elements
elements = await client.call_tool("query_elements", {
    "session_id": session_id,
    "strategy": "css",
    "selector": "button.submit"
})

# 4. Click an element
await client.call_tool("click_element", {
    "session_id": session_id,
    "element_id": elements["elements"][0]["element_id"]
})

# 5. Wait for navigation
await client.call_tool("wait_for_url", {
    "session_id": session_id,
    "pattern": "success"
})

# 6. Close session when done
await client.call_tool("close_session", {"session_id": session_id})
```

## Error Handling

All tools return structured errors with:
- `error_code` - Machine-readable code (e.g., `ELEMENT_NOT_FOUND`)
- `message` - Human-readable description
- `suggestion` - Recovery hint for the AI

Example error:
```json
{
  "success": false,
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "Element not found: css=#missing",
    "suggestion": "Verify the selector is correct. Use wait_for_selector before querying if the element loads dynamically."
  }
}
```

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Lint
ruff check src/
```

## License

MIT
