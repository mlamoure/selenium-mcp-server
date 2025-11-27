# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Selenium MCP Server - A FastMCP 2.0 server providing browser automation via Selenium Grid. AI agents call MCP tools instead of writing Selenium scripts directly.

**Tech Stack:**
- Python 3.14
- FastMCP 2.0 (Streamable HTTP transport)
- Selenium RemoteWebDriver → Selenium Grid 4
- Docker containerization

## Build & Run Commands

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate.fish  # or activate for bash

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for development

# Run the server locally (requires Selenium Grid at localhost:4444)
python -m selenium_mcp

# Run with Docker Compose (includes Selenium Grid)
docker-compose up -d

# Run tests
pytest

# Run tests with coverage
pytest --cov=selenium_mcp

# Lint with ruff
ruff check src/
```

## Architecture

```
src/selenium_mcp/
├── server.py          # FastMCP server + lifespan management
├── config.py          # pydantic-settings configuration
├── core/              # Business logic (no MCP deps)
│   ├── session_manager.py  # Session registry + element mapping
│   ├── driver_factory.py   # RemoteWebDriver creation
│   └── exceptions.py       # Domain exceptions
├── tools/             # MCP tool definitions by category
│   ├── __init__.py    # Tool router composition
│   ├── meta.py        # ping, list_sessions
│   ├── session.py     # create_session, close_session
│   ├── navigation.py  # navigate, back, forward, reload
│   ├── observation.py # get_dom, query_elements, screenshot
│   ├── actions.py     # click, type, select, scroll
│   ├── waits.py       # wait_for_selector, wait_for_url
│   └── scripting.py   # execute_script
└── utils/             # Shared utilities
    ├── error_mapper.py    # Selenium → MCP error mapping
    ├── element_resolver.py # element_id resolution
    └── guardrails.py      # Domain validation
```

## Key Patterns

### Tool Router Composition
Tools are organized by category using FastMCP's `import_server()`:
```python
# tools/__init__.py
router = FastMCP("SeleniumTools")
router.import_server(meta_router)
router.import_server(session_router)
# ...
```

### Session + Element Registry
Each session maintains a per-session element ID mapping:
- `query_elements` returns stable element_ids
- `click_element` uses element_id to find the WebElement
- Elements are cleaned up when session closes

### Async with Thread Pool
Selenium's API is synchronous. We use `anyio.to_thread.run_sync()`:
```python
await anyio.to_thread.run_sync(lambda: driver.get(url))
```

### Error Mapping
Selenium exceptions are mapped to MCP error codes with suggestions:
```python
error_code, message = map_selenium_error(exc)
error_response = create_error_response(error_code, message)
```

## Configuration

Environment variables (prefix: `SELENIUM_MCP_`):
- `SELENIUM_GRID_URL` - Selenium Grid URL (default: http://localhost:4444)
- `MAX_CONCURRENT_SESSIONS` - Max simultaneous sessions (default: 10)
- `SESSION_MAX_LIFETIME_SECONDS` - Session timeout (default: 900)
- `ALLOWED_DOMAINS` - Comma-separated allowed domains (empty = all)

## Testing

Tests use mocked WebDriver fixtures:
```bash
pytest tests/                    # All tests
pytest tests/test_session_manager.py  # Specific file
pytest -k "test_create"          # Pattern match
```

## Docker

```bash
# Build image
docker build -t selenium-mcp-server .

# Run with Selenium Grid
docker-compose up -d

# View logs
docker-compose logs -f selenium-mcp

# MCP endpoint: http://localhost:8000/mcp/
# Grid UI: http://localhost:4444
```
