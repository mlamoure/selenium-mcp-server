"""Element ID resolution utilities."""

from typing import Optional
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

from ..core.session_manager import BrowserSession
from ..core.exceptions import ElementNotFoundError


# Map strategy names to Selenium By constants
STRATEGY_MAP = {
    "css": By.CSS_SELECTOR,
    "xpath": By.XPATH,
    "id": By.ID,
    "name": By.NAME,
    "class": By.CLASS_NAME,
    "tag": By.TAG_NAME,
    "link_text": By.LINK_TEXT,
    "partial_link_text": By.PARTIAL_LINK_TEXT,
}


def get_by_strategy(strategy: str) -> By:
    """
    Convert strategy string to Selenium By constant.

    Args:
        strategy: Locator strategy name (css, xpath, id, name, class, tag, link_text)

    Returns:
        Selenium By constant

    Raises:
        ValueError: If strategy is not supported
    """
    strategy = strategy.lower()
    if strategy not in STRATEGY_MAP:
        raise ValueError(
            f"Unsupported locator strategy: {strategy}. "
            f"Supported: {list(STRATEGY_MAP.keys())}"
        )
    return STRATEGY_MAP[strategy]


def resolve_element(
    session: BrowserSession,
    element_id: Optional[str] = None,
    strategy: Optional[str] = None,
    selector: Optional[str] = None,
) -> WebElement:
    """
    Resolve an element from either element_id or strategy/selector.

    This allows tools to accept either:
    - element_id: Reference to a previously queried element
    - strategy + selector: Find element on-the-fly

    Args:
        session: Browser session
        element_id: Optional element ID from previous query
        strategy: Optional locator strategy (css, xpath, etc.)
        selector: Optional selector string

    Returns:
        Resolved WebElement

    Raises:
        ElementNotFoundError: If element cannot be found
        ValueError: If neither element_id nor strategy+selector provided
    """
    if element_id:
        return session.get_element(element_id)

    if strategy and selector:
        by = get_by_strategy(strategy)
        elements = session.driver.find_elements(by, selector)
        if not elements:
            raise ElementNotFoundError(f"{strategy}={selector}")
        return elements[0]

    raise ValueError("Must provide either element_id or (strategy + selector)")


def serialize_element(element: WebElement, include_text: bool = True) -> dict:
    """
    Serialize a WebElement to a dictionary for API responses.

    Args:
        element: WebElement to serialize
        include_text: Whether to include text content

    Returns:
        Dictionary with element properties
    """
    result = {
        "tag_name": element.tag_name,
        "is_displayed": element.is_displayed(),
        "is_enabled": element.is_enabled(),
        "is_selected": element.is_selected(),
        "location": element.location,
        "size": element.size,
        "attributes": {
            "id": element.get_attribute("id"),
            "class": element.get_attribute("class"),
            "name": element.get_attribute("name"),
            "type": element.get_attribute("type"),
            "value": element.get_attribute("value"),
            "href": element.get_attribute("href"),
            "src": element.get_attribute("src"),
            "placeholder": element.get_attribute("placeholder"),
            "aria-label": element.get_attribute("aria-label"),
            "role": element.get_attribute("role"),
        },
    }

    if include_text:
        text = element.text
        result["text"] = text[:500] if text else ""

    # Clean up None values in attributes
    result["attributes"] = {k: v for k, v in result["attributes"].items() if v}

    return result


def is_clickable(element: WebElement) -> bool:
    """
    Heuristic to determine if an element appears clickable.

    Args:
        element: WebElement to check

    Returns:
        True if element appears clickable
    """
    if not element.is_displayed() or not element.is_enabled():
        return False

    tag = element.tag_name.lower()

    # Clickable by nature
    if tag in ("a", "button", "input", "select", "textarea", "label"):
        return True

    # Check for click-related attributes
    onclick = element.get_attribute("onclick")
    role = element.get_attribute("role")
    tabindex = element.get_attribute("tabindex")
    cursor = element.value_of_css_property("cursor")

    if onclick:
        return True
    if role in ("button", "link", "menuitem", "tab", "checkbox", "radio"):
        return True
    if tabindex and tabindex != "-1":
        return True
    if cursor == "pointer":
        return True

    return False
