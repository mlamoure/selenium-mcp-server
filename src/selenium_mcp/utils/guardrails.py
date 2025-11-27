"""Domain validation and other guardrails for safe browsing."""

from urllib.parse import urlparse
from typing import Optional


def validate_domain(url: str, allowed_domains: list[str]) -> bool:
    """
    Check if a URL's domain is in the allowed list.

    Args:
        url: URL to validate
        allowed_domains: List of allowed domain patterns

    Returns:
        True if domain is allowed, False otherwise

    Notes:
        - If allowed_domains is empty, all domains are allowed
        - Supports exact match and subdomain matching
        - Domain matching is case-insensitive
    """
    if not allowed_domains:
        return True

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port number if present
        if ":" in domain:
            domain = domain.split(":")[0]

        for allowed in allowed_domains:
            allowed = allowed.lower().strip()
            if not allowed:
                continue

            # Exact match
            if domain == allowed:
                return True

            # Subdomain match (e.g., "example.com" allows "sub.example.com")
            if domain.endswith(f".{allowed}"):
                return True

        return False

    except Exception:
        return False


def extract_domain(url: str) -> Optional[str]:
    """
    Extract the domain from a URL.

    Args:
        url: URL to parse

    Returns:
        Domain string or None if invalid
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain if domain else None
    except Exception:
        return None


def is_safe_url(url: str) -> bool:
    """
    Check if a URL uses a safe protocol.

    Args:
        url: URL to check

    Returns:
        True if http or https, False otherwise
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme.lower() in ("http", "https")
    except Exception:
        return False
