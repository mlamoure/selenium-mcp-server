"""Unit tests for error mapper."""

import pytest
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    InvalidSelectorException,
    WebDriverException,
)

from selenium_mcp.utils.error_mapper import (
    ErrorCode,
    map_selenium_error,
    create_error_response,
    SUGGESTIONS,
)
from selenium_mcp.core.exceptions import (
    SessionNotFoundError,
    ElementNotFoundError,
    DomainNotAllowedError,
)


class TestErrorCodeMapping:
    """Tests for exception to error code mapping."""

    def test_map_no_such_element(self):
        """Should map NoSuchElementException to ELEMENT_NOT_FOUND."""
        exc = NoSuchElementException("Element not found")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.ELEMENT_NOT_FOUND
        assert "Element not found" in message

    def test_map_stale_element(self):
        """Should map StaleElementReferenceException to ELEMENT_STALE."""
        exc = StaleElementReferenceException("Element is stale")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.ELEMENT_STALE

    def test_map_timeout(self):
        """Should map TimeoutException to TIMEOUT."""
        exc = TimeoutException("Timed out")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.TIMEOUT

    def test_map_invalid_selector(self):
        """Should map InvalidSelectorException to INVALID_SELECTOR."""
        exc = InvalidSelectorException("Invalid CSS")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.INVALID_SELECTOR

    def test_map_session_not_found(self):
        """Should map SessionNotFoundError to SESSION_NOT_FOUND."""
        exc = SessionNotFoundError("test-session")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.SESSION_NOT_FOUND
        assert "test-session" in message

    def test_map_element_not_found(self):
        """Should map ElementNotFoundError to ELEMENT_NOT_FOUND."""
        exc = ElementNotFoundError("elem_123")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.ELEMENT_NOT_FOUND

    def test_map_domain_not_allowed(self):
        """Should map DomainNotAllowedError to DOMAIN_NOT_ALLOWED."""
        exc = DomainNotAllowedError("evil.com", ["good.com"])
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.DOMAIN_NOT_ALLOWED

    def test_map_connection_refused(self):
        """Should detect connection refused in WebDriverException."""
        exc = WebDriverException("Connection refused to localhost:4444")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.CONNECTION_REFUSED

    def test_map_unknown_error(self):
        """Should return UNKNOWN_ERROR for unmapped exceptions."""
        exc = RuntimeError("Something unexpected")
        code, message = map_selenium_error(exc)

        assert code == ErrorCode.UNKNOWN_ERROR


class TestErrorResponse:
    """Tests for error response creation."""

    def test_create_error_response(self):
        """Should create response with suggestion."""
        response = create_error_response(
            ErrorCode.ELEMENT_NOT_FOUND,
            "Element not found: #missing",
        )

        assert response.error_code == "ELEMENT_NOT_FOUND"
        assert "Element not found" in response.message
        assert response.suggestion is not None

    def test_error_response_to_dict(self):
        """Should convert to proper dictionary format."""
        response = create_error_response(
            ErrorCode.TIMEOUT,
            "Timed out after 10s",
        )

        result = response.to_dict()

        assert result["success"] is False
        assert result["error"]["code"] == "TIMEOUT"
        assert result["error"]["message"] == "Timed out after 10s"
        assert "suggestion" in result["error"]

    def test_error_response_with_details(self):
        """Should include details when provided."""
        response = create_error_response(
            ErrorCode.DOMAIN_NOT_ALLOWED,
            "Domain blocked",
            details={"domain": "evil.com", "allowed": ["good.com"]},
        )

        result = response.to_dict()

        assert result["error"]["details"]["domain"] == "evil.com"


class TestSuggestions:
    """Tests for error suggestions."""

    def test_all_common_errors_have_suggestions(self):
        """Common error codes should have suggestions."""
        common_codes = [
            ErrorCode.SESSION_NOT_FOUND,
            ErrorCode.ELEMENT_NOT_FOUND,
            ErrorCode.ELEMENT_STALE,
            ErrorCode.TIMEOUT,
            ErrorCode.INVALID_SELECTOR,
            ErrorCode.DOMAIN_NOT_ALLOWED,
        ]

        for code in common_codes:
            assert code in SUGGESTIONS, f"Missing suggestion for {code}"
            assert len(SUGGESTIONS[code]) > 10, f"Suggestion too short for {code}"
