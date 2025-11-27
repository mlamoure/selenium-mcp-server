"""Entry point for running the Selenium MCP Server."""

import sys


def main() -> int:
    """Main entry point."""
    from .server import run_server

    try:
        run_server()
        return 0
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
