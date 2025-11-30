#!/bin/bash
# Start the Selenium MCP server locally for testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export SELENIUM_MCP_SELENIUM_GRID_URL="${SELENIUM_MCP_SELENIUM_GRID_URL:-https://selenium-api.common-services.home.mikelamoureux.net}"
export SELENIUM_MCP_HOST="${SELENIUM_MCP_HOST:-0.0.0.0}"
export SELENIUM_MCP_PORT="${SELENIUM_MCP_PORT:-8000}"

echo "Starting Selenium MCP Server..."
echo "  Grid URL: $SELENIUM_MCP_SELENIUM_GRID_URL"
echo "  Server:   http://$SELENIUM_MCP_HOST:$SELENIUM_MCP_PORT"
echo ""

# Run the server
python -m selenium_mcp
