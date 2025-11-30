"""DOM content retrieval helpers."""

import re
import anyio


async def get_dom_content(
    driver,
    max_chars: int,
    strip_scripts_and_styles: bool = True,
) -> dict:
    """
    Get DOM content with standard processing.

    Retrieves page source and applies optional transformations
    (script/style stripping, truncation).

    Args:
        driver: Selenium WebDriver instance
        max_chars: Maximum characters to return
        strip_scripts_and_styles: Whether to remove script/style tags

    Returns:
        Dict with:
        - html: Processed HTML content
        - truncated: Whether content was truncated
        - total_length: Original length or ">limit" if truncated
    """
    # Get page source
    html = await anyio.to_thread.run_sync(lambda: driver.page_source)

    # Optionally strip scripts and styles
    if strip_scripts_and_styles:
        html = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
        )

    # Truncate if needed
    truncated = len(html) > max_chars
    original_length = len(html)
    if truncated:
        html = html[:max_chars]

    return {
        "html": html,
        "truncated": truncated,
        "total_length": original_length if not truncated else f">{max_chars}",
    }
