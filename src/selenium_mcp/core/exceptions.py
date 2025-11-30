"""Domain-specific exceptions for the Selenium MCP server."""


class SeleniumMCPError(Exception):
    """Base exception for all Selenium MCP errors."""

    pass


class SessionNotFoundError(SeleniumMCPError):
    """Raised when referencing a non-existent or expired session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class SessionLimitError(SeleniumMCPError):
    """Raised when max session limit is reached."""

    def __init__(self, max_sessions: int):
        self.max_sessions = max_sessions
        super().__init__(f"Maximum sessions ({max_sessions}) reached")


class ElementNotFoundError(SeleniumMCPError):
    """Raised when element ID is not in the session's element registry."""

    def __init__(self, element_id: str):
        self.element_id = element_id
        super().__init__(f"Element not found in registry: {element_id}")


class ElementStaleError(SeleniumMCPError):
    """Raised when a registered element is no longer valid in the DOM."""

    def __init__(self, element_id: str):
        self.element_id = element_id
        super().__init__(f"Element is stale (no longer in DOM): {element_id}")


class DomainNotAllowedError(SeleniumMCPError):
    """Raised when attempting to navigate to a domain not in the allowed list."""

    def __init__(self, domain: str, allowed_domains: list[str]):
        self.domain = domain
        self.allowed_domains = allowed_domains
        super().__init__(f"Domain '{domain}' is not in allowed list: {allowed_domains}")


class WaitTimeoutError(SeleniumMCPError):
    """Raised when a wait condition times out."""

    def __init__(self, condition: str, timeout_seconds: float):
        self.condition = condition
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Timeout ({timeout_seconds}s) waiting for: {condition}")


class ScriptExecutionError(SeleniumMCPError):
    """Raised when JavaScript execution fails."""

    def __init__(self, message: str):
        super().__init__(f"Script execution failed: {message}")


class GridConnectionError(SeleniumMCPError):
    """Raised when unable to connect to Selenium Grid."""

    def __init__(self, grid_url: str, message: str):
        self.grid_url = grid_url
        super().__init__(f"Failed to connect to Selenium Grid at {grid_url}: {message}")
