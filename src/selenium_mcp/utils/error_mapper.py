"""Map Selenium exceptions to structured MCP-friendly errors."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    ElementNotVisibleException,
    ElementNotSelectableException,
    InvalidSelectorException,
    TimeoutException,
    NoSuchWindowException,
    NoSuchFrameException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    JavascriptException,
    WebDriverException,
    InvalidArgumentException,
    SessionNotCreatedException,
    InsecureCertificateException,
    InvalidCookieDomainException,
    MoveTargetOutOfBoundsException,
    InvalidElementStateException,
    NoSuchCookieException,
)

from ..core.exceptions import (
    SeleniumMCPError,
    SessionNotFoundError,
    SessionLimitError,
    ElementNotFoundError,
    ElementStaleError,
    DomainNotAllowedError,
    WaitTimeoutError,
    ScriptExecutionError,
    GridConnectionError,
)


class ErrorCode(str, Enum):
    """MCP-compatible error codes for Selenium operations."""

    # Session errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_LIMIT_REACHED = "SESSION_LIMIT_REACHED"
    SESSION_CREATION_FAILED = "SESSION_CREATION_FAILED"
    SESSION_TERMINATED = "SESSION_TERMINATED"

    # Element errors
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_STALE = "ELEMENT_STALE"
    ELEMENT_NOT_INTERACTABLE = "ELEMENT_NOT_INTERACTABLE"
    ELEMENT_NOT_VISIBLE = "ELEMENT_NOT_VISIBLE"
    ELEMENT_NOT_SELECTABLE = "ELEMENT_NOT_SELECTABLE"

    # Selector errors
    INVALID_SELECTOR = "INVALID_SELECTOR"

    # Navigation errors
    NAVIGATION_FAILED = "NAVIGATION_FAILED"
    DOMAIN_NOT_ALLOWED = "DOMAIN_NOT_ALLOWED"
    INSECURE_CERTIFICATE = "INSECURE_CERTIFICATE"

    # Timeout errors
    TIMEOUT = "TIMEOUT"
    SCRIPT_TIMEOUT = "SCRIPT_TIMEOUT"
    PAGE_LOAD_TIMEOUT = "PAGE_LOAD_TIMEOUT"

    # Window/Frame errors
    WINDOW_NOT_FOUND = "WINDOW_NOT_FOUND"
    FRAME_NOT_FOUND = "FRAME_NOT_FOUND"

    # Alert errors
    ALERT_NOT_PRESENT = "ALERT_NOT_PRESENT"
    UNEXPECTED_ALERT = "UNEXPECTED_ALERT"

    # Cookie errors
    COOKIE_NOT_FOUND = "COOKIE_NOT_FOUND"
    INVALID_COOKIE_DOMAIN = "INVALID_COOKIE_DOMAIN"

    # JavaScript errors
    JAVASCRIPT_ERROR = "JAVASCRIPT_ERROR"

    # Grid/Connection errors
    GRID_UNAVAILABLE = "GRID_UNAVAILABLE"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"

    # Generic errors
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Map Selenium exceptions to MCP error codes
EXCEPTION_MAP: dict[type[Exception], ErrorCode] = {
    # Selenium exceptions
    NoSuchElementException: ErrorCode.ELEMENT_NOT_FOUND,
    StaleElementReferenceException: ErrorCode.ELEMENT_STALE,
    ElementNotInteractableException: ErrorCode.ELEMENT_NOT_INTERACTABLE,
    ElementNotVisibleException: ErrorCode.ELEMENT_NOT_VISIBLE,
    ElementNotSelectableException: ErrorCode.ELEMENT_NOT_SELECTABLE,
    InvalidSelectorException: ErrorCode.INVALID_SELECTOR,
    TimeoutException: ErrorCode.TIMEOUT,
    NoSuchWindowException: ErrorCode.WINDOW_NOT_FOUND,
    NoSuchFrameException: ErrorCode.FRAME_NOT_FOUND,
    NoAlertPresentException: ErrorCode.ALERT_NOT_PRESENT,
    UnexpectedAlertPresentException: ErrorCode.UNEXPECTED_ALERT,
    JavascriptException: ErrorCode.JAVASCRIPT_ERROR,
    InvalidArgumentException: ErrorCode.INVALID_ARGUMENT,
    SessionNotCreatedException: ErrorCode.SESSION_CREATION_FAILED,
    InsecureCertificateException: ErrorCode.INSECURE_CERTIFICATE,
    InvalidCookieDomainException: ErrorCode.INVALID_COOKIE_DOMAIN,
    MoveTargetOutOfBoundsException: ErrorCode.INVALID_ARGUMENT,
    InvalidElementStateException: ErrorCode.ELEMENT_NOT_INTERACTABLE,
    NoSuchCookieException: ErrorCode.COOKIE_NOT_FOUND,
    # Domain exceptions
    SessionNotFoundError: ErrorCode.SESSION_NOT_FOUND,
    SessionLimitError: ErrorCode.SESSION_LIMIT_REACHED,
    ElementNotFoundError: ErrorCode.ELEMENT_NOT_FOUND,
    ElementStaleError: ErrorCode.ELEMENT_STALE,
    DomainNotAllowedError: ErrorCode.DOMAIN_NOT_ALLOWED,
    WaitTimeoutError: ErrorCode.TIMEOUT,
    ScriptExecutionError: ErrorCode.JAVASCRIPT_ERROR,
    GridConnectionError: ErrorCode.GRID_UNAVAILABLE,
}

# Suggestions for each error code to help the AI recover
SUGGESTIONS: dict[ErrorCode, str] = {
    ErrorCode.SESSION_NOT_FOUND: (
        "The session ID is invalid or has expired. "
        "Create a new session with create_session."
    ),
    ErrorCode.SESSION_LIMIT_REACHED: (
        "Maximum number of concurrent sessions reached. "
        "Close unused sessions with close_session before creating new ones."
    ),
    ErrorCode.SESSION_CREATION_FAILED: (
        "Failed to create browser session. "
        "Check that Selenium Grid is running and the browser is available."
    ),
    ErrorCode.ELEMENT_NOT_FOUND: (
        "Element not found. Verify the selector is correct and the element exists in the DOM. "
        "Use wait_for_selector before querying if the element loads dynamically."
    ),
    ErrorCode.ELEMENT_STALE: (
        "Element reference is outdated (page may have changed). "
        "Re-query the element with query_elements before interacting with it."
    ),
    ErrorCode.ELEMENT_NOT_INTERACTABLE: (
        "Element exists but cannot be interacted with. "
        "It may be hidden, disabled, or covered by another element. "
        "Try scroll_to_element first, or wait for it to become clickable."
    ),
    ErrorCode.ELEMENT_NOT_VISIBLE: (
        "Element is not visible on the page. "
        "Try scrolling to the element or waiting for it to become visible."
    ),
    ErrorCode.ELEMENT_NOT_SELECTABLE: (
        "Element cannot be selected. Ensure it is a <select> element "
        "or an input type that supports selection."
    ),
    ErrorCode.INVALID_SELECTOR: (
        "The selector syntax is invalid. "
        "Check for typos in CSS selectors or XPath expressions."
    ),
    ErrorCode.DOMAIN_NOT_ALLOWED: (
        "Navigation to this domain is not permitted by the server configuration. "
        "Only allowed domains can be accessed."
    ),
    ErrorCode.TIMEOUT: (
        "Operation timed out. Increase the timeout value or check if the condition "
        "can ever be met."
    ),
    ErrorCode.WINDOW_NOT_FOUND: (
        "The specified window or tab does not exist. "
        "Use get_window_handles to list available windows."
    ),
    ErrorCode.FRAME_NOT_FOUND: (
        "The specified frame or iframe does not exist. "
        "Verify the frame name/ID or use query_elements to find frame elements."
    ),
    ErrorCode.ALERT_NOT_PRESENT: (
        "No alert, confirm, or prompt dialog is currently open. "
        "Wait for the alert to appear before trying to interact with it."
    ),
    ErrorCode.JAVASCRIPT_ERROR: (
        "JavaScript execution failed. Check the script syntax and ensure all "
        "referenced objects exist in the page context."
    ),
    ErrorCode.GRID_UNAVAILABLE: (
        "Cannot connect to Selenium Grid. "
        "Verify the Grid URL is correct and the Grid service is running."
    ),
    ErrorCode.INVALID_ARGUMENT: (
        "Invalid argument provided. Check parameter types and values."
    ),
}


@dataclass
class ToolErrorResponse:
    """Structured error response for MCP tools."""

    error_code: str
    message: str
    suggestion: Optional[str] = None
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for tool response."""
        result = {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
            },
        }
        if self.suggestion:
            result["error"]["suggestion"] = self.suggestion
        if self.details:
            result["error"]["details"] = self.details
        return result


def map_selenium_error(exc: Exception) -> tuple[ErrorCode, str]:
    """
    Map an exception to an MCP error code and message.

    Args:
        exc: The exception to map

    Returns:
        Tuple of (ErrorCode, error message)
    """
    exc_type = type(exc)

    # Check exact type first
    if exc_type in EXCEPTION_MAP:
        return EXCEPTION_MAP[exc_type], str(exc)

    # Check parent types
    for exc_class, code in EXCEPTION_MAP.items():
        if isinstance(exc, exc_class):
            return code, str(exc)

    # Check for connection errors in WebDriverException
    if isinstance(exc, WebDriverException):
        msg_lower = str(exc).lower()
        if "connection refused" in msg_lower:
            return ErrorCode.CONNECTION_REFUSED, str(exc)
        if "session" in msg_lower and ("not found" in msg_lower or "deleted" in msg_lower):
            return ErrorCode.SESSION_TERMINATED, str(exc)

    # Fallback
    return ErrorCode.UNKNOWN_ERROR, str(exc)


def create_error_response(
    code: ErrorCode,
    message: str,
    details: Optional[dict] = None,
) -> ToolErrorResponse:
    """
    Create a structured error response with suggestion.

    Args:
        code: Error code
        message: Error message
        details: Optional additional details

    Returns:
        ToolErrorResponse with suggestion from SUGGESTIONS
    """
    return ToolErrorResponse(
        error_code=code.value,
        message=message,
        suggestion=SUGGESTIONS.get(code),
        details=details,
    )
