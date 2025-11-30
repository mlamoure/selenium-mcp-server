"""Core business logic for Selenium MCP Server."""

from .exceptions import (
    SeleniumMCPError,
    SessionNotFoundError,
    SessionLimitError,
    ElementNotFoundError,
    ElementStaleError,
    DomainNotAllowedError,
)
from .session_manager import SessionManager, BrowserSession

__all__ = [
    "SeleniumMCPError",
    "SessionNotFoundError",
    "SessionLimitError",
    "ElementNotFoundError",
    "ElementStaleError",
    "DomainNotAllowedError",
    "SessionManager",
    "BrowserSession",
]
