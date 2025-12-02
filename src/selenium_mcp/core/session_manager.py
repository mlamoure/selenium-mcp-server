"""Session management with element registry for browser sessions."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

import anyio
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from .exceptions import (
    SessionNotFoundError,
    SessionLimitError,
    ElementNotFoundError,
    ElementStaleError,
)
from .driver_factory import DriverFactory

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """
    Represents an active browser session with its element registry.

    Each session maintains its own element_id -> WebElement mapping,
    allowing tools to reference elements by stable IDs across calls.
    """

    session_id: str
    driver: WebDriver
    browser: str
    created_at: float
    last_activity: float
    capabilities: dict = field(default_factory=dict)
    record_video: bool = False  # Whether video recording is enabled
    selenium_session_id: Optional[str] = None  # Grid's internal session ID for video retrieval
    _element_map: Dict[str, WebElement] = field(default_factory=dict)
    _element_counter: int = field(default=0)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def register_element(self, element: WebElement) -> str:
        """
        Register a WebElement and return a stable element ID.

        Args:
            element: WebElement to register

        Returns:
            Stable element ID for future reference
        """
        self._element_counter += 1
        element_id = f"elem_{self._element_counter}"
        self._element_map[element_id] = element
        self.touch()
        return element_id

    def register_elements(self, elements: list[WebElement]) -> list[str]:
        """Register multiple elements and return their IDs."""
        return [self.register_element(el) for el in elements]

    def get_element(self, element_id: str) -> WebElement:
        """
        Get a WebElement by its ID.

        Args:
            element_id: Previously returned element ID

        Returns:
            The WebElement

        Raises:
            ElementNotFoundError: If element ID not in registry
            ElementStaleError: If element is no longer attached to DOM
        """
        element = self._element_map.get(element_id)
        if element is None:
            raise ElementNotFoundError(element_id)

        # Check for staleness
        try:
            _ = element.is_enabled()  # Triggers staleness check
        except StaleElementReferenceException:
            del self._element_map[element_id]
            raise ElementStaleError(element_id)

        self.touch()
        return element

    def remove_element(self, element_id: str) -> bool:
        """Remove an element from the registry."""
        if element_id in self._element_map:
            del self._element_map[element_id]
            return True
        return False

    def clear_elements(self) -> int:
        """Clear all registered elements. Returns count of cleared elements."""
        count = len(self._element_map)
        self._element_map.clear()
        self._element_counter = 0
        return count

    @property
    def element_count(self) -> int:
        """Number of registered elements."""
        return len(self._element_map)

    def to_dict(self) -> dict:
        """Convert session info to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "browser": self.browser,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "element_count": self.element_count,
            "current_url": self.driver.current_url if self.driver else None,
            "record_video": self.record_video,
            "selenium_session_id": self.selenium_session_id,
        }

    def get_grid_capabilities(self) -> dict:
        """Extract Selenium Grid specific capabilities (se: prefixed)."""
        return {
            "se:cdp": self.capabilities.get("se:cdp"),
            "se:vnc": self.capabilities.get("se:vnc"),
            "se:vncEnabled": self.capabilities.get("se:vncEnabled"),
            "se:vncLocalAddress": self.capabilities.get("se:vncLocalAddress"),
            "se:recordVideo": self.capabilities.get("se:recordVideo"),
        }


class SessionManager:
    """
    Thread-safe manager for browser sessions.

    Uses asyncio.Lock for coroutine-safe access to the session registry.
    Each session has its own lock for per-session operations.
    """

    def __init__(
        self,
        driver_factory: DriverFactory,
        max_sessions: int = 10,
        max_lifetime_seconds: int = 900,
        max_idle_seconds: int = 300,
    ):
        self._driver_factory = driver_factory
        self._max_sessions = max_sessions
        self._max_lifetime_seconds = max_lifetime_seconds
        self._max_idle_seconds = max_idle_seconds
        self._sessions: Dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        browser: str = "chrome",
        headless: bool = True,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None,
        extra_capabilities: Optional[dict] = None,
        record_video: bool = False,
    ) -> BrowserSession:
        """
        Create a new browser session.

        Args:
            browser: Browser type (chrome, firefox, edge)
            headless: Run in headless mode
            viewport_width: Optional viewport width
            viewport_height: Optional viewport height
            extra_capabilities: Additional browser capabilities
            record_video: Whether video recording is enabled for this session

        Returns:
            New BrowserSession

        Raises:
            SessionLimitError: If max sessions reached
            GridConnectionError: If unable to connect to Grid
        """
        async with self._lock:
            if len(self._sessions) >= self._max_sessions:
                raise SessionLimitError(self._max_sessions)

            driver = await self._driver_factory.create(
                browser=browser,
                headless=headless,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                extra_capabilities=extra_capabilities,
            )

            session_id = f"sess_{uuid.uuid4().hex[:16]}"
            now = time.time()

            session = BrowserSession(
                session_id=session_id,
                driver=driver,
                browser=browser,
                created_at=now,
                last_activity=now,
                capabilities=driver.capabilities or {},
                record_video=record_video,
                selenium_session_id=driver.session_id,
            )

            self._sessions[session_id] = session
            logger.info(f"Created session {session_id} with {browser} (recording={record_video})")

            return session

    def get_session(self, session_id: str) -> BrowserSession:
        """
        Get a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            BrowserSession

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        session.touch()
        return session

    async def close_session(self, session_id: str) -> bool:
        """
        Close a session and release its resources.

        Args:
            session_id: Session ID to close

        Returns:
            True if session was closed, False if not found
        """
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                return False

            async with session._lock:
                try:
                    await anyio.to_thread.run_sync(session.driver.quit)
                except Exception as e:
                    logger.warning(f"Error closing driver for {session_id}: {e}")

            logger.info(f"Closed session {session_id}")
            return True

    def list_sessions(self, browser: Optional[str] = None) -> list[dict]:
        """
        List all active sessions.

        Args:
            browser: Optional filter by browser type

        Returns:
            List of session info dictionaries
        """
        sessions = list(self._sessions.values())
        if browser:
            sessions = [s for s in sessions if s.browser.lower() == browser.lower()]
        return [s.to_dict() for s in sessions]

    async def get_expired_sessions(self) -> list[str]:
        """
        Find sessions that have exceeded lifetime or idle limits.

        Returns:
            List of expired session IDs
        """
        now = time.time()
        expired = []

        for session_id, session in self._sessions.items():
            age = now - session.created_at
            idle = now - session.last_activity

            if age > self._max_lifetime_seconds:
                logger.info(f"Session {session_id} exceeded max lifetime ({age:.0f}s)")
                expired.append(session_id)
            elif idle > self._max_idle_seconds:
                logger.info(f"Session {session_id} exceeded max idle time ({idle:.0f}s)")
                expired.append(session_id)

        return expired

    async def sweep_expired(self) -> int:
        """
        Close all expired sessions.

        Returns:
            Number of sessions closed
        """
        expired = await self.get_expired_sessions()
        count = 0
        for session_id in expired:
            if await self.close_session(session_id):
                count += 1
        return count

    async def close_all(self) -> int:
        """
        Close all sessions (for shutdown).

        Returns:
            Number of sessions closed
        """
        session_ids = list(self._sessions.keys())
        count = 0
        for session_id in session_ids:
            if await self.close_session(session_id):
                count += 1
        logger.info(f"Closed all {count} sessions")
        return count

    @property
    def session_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)


class SessionSweeper:
    """
    Background task that periodically cleans up expired sessions.

    Started during server lifespan and cancelled on shutdown.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        interval_seconds: int = 60,
    ):
        self._session_manager = session_manager
        self._interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the sweeper background task."""
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._sweep_loop())
        logger.info(f"Session sweeper started (interval: {self._interval}s)")

    async def stop(self) -> None:
        """Stop the sweeper gracefully."""
        if self._task:
            self._shutdown_event.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Session sweeper stopped")

    async def _sweep_loop(self) -> None:
        """Main sweep loop - runs until shutdown."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for interval or shutdown signal
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=self._interval
                )
            except asyncio.TimeoutError:
                # Timeout means interval elapsed - time to sweep
                try:
                    swept = await self._session_manager.sweep_expired()
                    if swept > 0:
                        logger.info(f"Swept {swept} expired session(s)")
                except Exception as e:
                    logger.error(f"Error during session sweep: {e}")
