"""Shared utilities for Selenium MCP Server."""

from .error_mapper import map_selenium_error, ErrorCode
from .guardrails import validate_domain
from .element_resolver import resolve_element

__all__ = [
    "map_selenium_error",
    "ErrorCode",
    "validate_domain",
    "resolve_element",
]
