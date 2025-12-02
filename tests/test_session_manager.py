"""Unit tests for SessionManager."""

import pytest
import time
from selenium_mcp.core.session_manager import SessionManager, BrowserSession
from selenium_mcp.core.exceptions import (
    SessionNotFoundError,
    SessionLimitError,
    ElementNotFoundError,
    ElementStaleError,
)


class TestBrowserSession:
    """Tests for BrowserSession element registry."""

    def test_register_element(self, mock_session, mock_webelement):
        """Should register element and return stable ID."""
        element_id = mock_session.register_element(mock_webelement)

        assert element_id.startswith("elem_")
        assert mock_session.element_count == 1

    def test_register_multiple_elements(self, mock_session, mock_webelement):
        """Should assign unique IDs to each element."""
        id1 = mock_session.register_element(mock_webelement)
        id2 = mock_session.register_element(mock_webelement)

        assert id1 != id2
        assert mock_session.element_count == 2

    def test_get_element_success(self, mock_session, mock_webelement):
        """Should retrieve registered element by ID."""
        element_id = mock_session.register_element(mock_webelement)
        retrieved = mock_session.get_element(element_id)

        assert retrieved is mock_webelement

    def test_get_element_not_found(self, mock_session):
        """Should raise ElementNotFoundError for unknown ID."""
        with pytest.raises(ElementNotFoundError) as exc:
            mock_session.get_element("unknown_id")

        assert "unknown_id" in str(exc.value)

    def test_remove_element(self, mock_session, mock_webelement):
        """Should remove element from registry."""
        element_id = mock_session.register_element(mock_webelement)
        assert mock_session.element_count == 1

        removed = mock_session.remove_element(element_id)

        assert removed is True
        assert mock_session.element_count == 0

    def test_clear_elements(self, mock_session, mock_webelement):
        """Should clear all registered elements."""
        mock_session.register_element(mock_webelement)
        mock_session.register_element(mock_webelement)
        assert mock_session.element_count == 2

        cleared = mock_session.clear_elements()

        assert cleared == 2
        assert mock_session.element_count == 0

    def test_touch_updates_last_activity(self, mock_session):
        """Should update last_activity timestamp on touch."""
        original = mock_session.last_activity
        time.sleep(0.01)

        mock_session.touch()

        assert mock_session.last_activity > original

    def test_to_dict(self, mock_session, mock_webelement):
        """Should convert session to dictionary."""
        mock_session.register_element(mock_webelement)
        result = mock_session.to_dict()

        assert result["session_id"] == "test-session-123"
        assert result["browser"] == "chrome"
        assert result["element_count"] == 1
        assert "created_at" in result
        assert "last_activity" in result
        assert "record_video" in result
        assert "selenium_session_id" in result

    def test_record_video_default_false(self, mock_webdriver):
        """Should default record_video to False."""
        session = BrowserSession(
            session_id="test-id",
            driver=mock_webdriver,
            browser="chrome",
            created_at=time.time(),
            last_activity=time.time(),
        )
        assert session.record_video is False

    def test_record_video_stored(self, mock_webdriver):
        """Should store record_video value."""
        session = BrowserSession(
            session_id="test-id",
            driver=mock_webdriver,
            browser="chrome",
            created_at=time.time(),
            last_activity=time.time(),
            record_video=True,
        )
        assert session.record_video is True

    def test_selenium_session_id_stored(self, mock_webdriver):
        """Should store selenium_session_id."""
        session = BrowserSession(
            session_id="test-id",
            driver=mock_webdriver,
            browser="chrome",
            created_at=time.time(),
            last_activity=time.time(),
            selenium_session_id="selenium-abc-123",
        )
        assert session.selenium_session_id == "selenium-abc-123"

    def test_to_dict_includes_recording_fields(self, mock_webdriver):
        """Should include recording fields in to_dict()."""
        session = BrowserSession(
            session_id="test-id",
            driver=mock_webdriver,
            browser="chrome",
            created_at=time.time(),
            last_activity=time.time(),
            record_video=True,
            selenium_session_id="selenium-abc-123",
        )
        result = session.to_dict()
        assert result["record_video"] is True
        assert result["selenium_session_id"] == "selenium-abc-123"

    def test_get_grid_capabilities(self, mock_webdriver):
        """Should extract se: prefixed capabilities."""
        mock_webdriver.capabilities = {
            "browserName": "chrome",
            "se:cdp": "ws://node:4444/session/abc/cdp",
            "se:vnc": "ws://node:4444/session/abc/vnc",
            "se:vncEnabled": True,
            "se:recordVideo": True,
        }
        session = BrowserSession(
            session_id="test-id",
            driver=mock_webdriver,
            browser="chrome",
            created_at=time.time(),
            last_activity=time.time(),
            capabilities=mock_webdriver.capabilities,
        )
        grid_caps = session.get_grid_capabilities()
        assert grid_caps["se:cdp"] == "ws://node:4444/session/abc/cdp"
        assert grid_caps["se:vnc"] == "ws://node:4444/session/abc/vnc"
        assert grid_caps["se:vncEnabled"] is True
        assert grid_caps["se:recordVideo"] is True


class TestSessionManager:
    """Tests for SessionManager."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_manager, mock_driver_factory):
        """Should create session and return BrowserSession."""
        session = await session_manager.create_session(browser="chrome")

        assert session.session_id.startswith("sess_")
        assert session.browser == "chrome"
        assert session_manager.session_count == 1
        mock_driver_factory.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_limit_reached(self, mock_driver_factory):
        """Should raise SessionLimitError when max reached."""
        manager = SessionManager(mock_driver_factory, max_sessions=1)

        await manager.create_session()

        with pytest.raises(SessionLimitError) as exc:
            await manager.create_session()

        assert "1" in str(exc.value)

    def test_get_session_success(self, session_manager):
        """Should retrieve existing session."""
        # Manually add a session for testing
        from selenium_mcp.core.session_manager import BrowserSession
        from unittest.mock import MagicMock

        session = BrowserSession(
            session_id="test-id",
            driver=MagicMock(),
            browser="chrome",
            created_at=time.time(),
            last_activity=time.time(),
        )
        session_manager._sessions["test-id"] = session

        retrieved = session_manager.get_session("test-id")

        assert retrieved is session

    def test_get_session_not_found(self, session_manager):
        """Should raise SessionNotFoundError for unknown ID."""
        with pytest.raises(SessionNotFoundError) as exc:
            session_manager.get_session("unknown-id")

        assert "unknown-id" in str(exc.value)

    @pytest.mark.asyncio
    async def test_close_session_success(self, session_manager, mock_driver_factory):
        """Should close session and remove from registry."""
        session = await session_manager.create_session()
        session_id = session.session_id

        closed = await session_manager.close_session(session_id)

        assert closed is True
        assert session_manager.session_count == 0

    @pytest.mark.asyncio
    async def test_close_session_not_found(self, session_manager):
        """Should return False for unknown session."""
        closed = await session_manager.close_session("unknown-id")

        assert closed is False

    def test_list_sessions_empty(self, session_manager):
        """Should return empty list when no sessions."""
        sessions = session_manager.list_sessions()

        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions_with_filter(self, session_manager, mock_driver_factory):
        """Should filter sessions by browser type."""
        await session_manager.create_session(browser="chrome")

        chrome_sessions = session_manager.list_sessions(browser="chrome")
        firefox_sessions = session_manager.list_sessions(browser="firefox")

        assert len(chrome_sessions) == 1
        assert len(firefox_sessions) == 0

    @pytest.mark.asyncio
    async def test_close_all_sessions(self, session_manager, mock_driver_factory):
        """Should close all sessions."""
        await session_manager.create_session()
        await session_manager.create_session()
        assert session_manager.session_count == 2

        closed = await session_manager.close_all()

        assert closed == 2
        assert session_manager.session_count == 0


class TestElementStaleHandling:
    """Tests for stale element handling."""

    def test_stale_element_raises_error(self, mock_session):
        """Should raise ElementStaleError when element is stale."""
        from selenium.common.exceptions import StaleElementReferenceException
        from unittest.mock import MagicMock

        stale_element = MagicMock()
        stale_element.is_enabled.side_effect = StaleElementReferenceException("Element is stale")

        element_id = mock_session.register_element(stale_element)

        with pytest.raises(ElementStaleError):
            mock_session.get_element(element_id)

        # Element should be removed from registry
        assert mock_session.element_count == 0
