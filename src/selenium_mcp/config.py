"""Configuration settings for Selenium MCP Server."""

import logging
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # API Key Authentication (optional)
    api_key: Optional[str] = None  # Direct API key via env var
    api_key_file: Optional[str] = None  # Path to file containing API key (for Docker secrets)

    # Selenium Grid
    selenium_grid_url: str = "http://localhost:4444"
    default_browser: str = "chrome"

    # Session management
    max_concurrent_sessions: int = 10
    session_max_lifetime_seconds: int = 900  # 15 minutes
    session_max_idle_seconds: int = 300  # 5 minutes
    sweep_interval_seconds: int = 60  # 1 minute

    # Domain guardrails (comma-separated list, empty = allow all)
    allowed_domains: Optional[str] = None

    # Content limits
    dom_max_chars: int = 20000
    visible_text_max_chars: int = 20000

    # Timeouts
    default_wait_timeout_ms: int = 10000
    page_load_timeout_seconds: int = 30
    script_timeout_seconds: int = 30
    implicit_wait_seconds: int = 0

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": "SELENIUM_MCP_"}

    @property
    def allowed_domain_list(self) -> list[str]:
        """Parse comma-separated domains into list."""
        if not self.allowed_domains:
            return []
        return [d.strip().lower() for d in self.allowed_domains.split(",") if d.strip()]

    @property
    def default_wait_timeout_seconds(self) -> float:
        """Convert ms timeout to seconds."""
        return self.default_wait_timeout_ms / 1000.0

    def get_api_key(self) -> str | None:
        """Get API key from file or environment variable.

        Docker secrets are typically mounted at /run/secrets/<secret_name>.
        If api_key_file is set, reads the API key from that file.
        File takes precedence over direct api_key environment variable.

        Returns:
            API key string or None if not configured.
        """
        if self.api_key_file:
            try:
                key = Path(self.api_key_file).read_text().strip()
                if key:
                    logger.info(f"Loaded API key from file: {self.api_key_file}")
                    return key
            except FileNotFoundError:
                logger.warning(f"API key file not found: {self.api_key_file}")
            except PermissionError:
                logger.warning(f"Permission denied reading API key file: {self.api_key_file}")
            except Exception as e:
                logger.warning(f"Error reading API key file: {e}")

        return self.api_key


# Global settings instance
settings = Settings()
