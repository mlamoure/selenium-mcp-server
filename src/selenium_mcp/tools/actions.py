"""Element interaction and action tools."""

from typing import Annotated, Optional, Literal
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import anyio
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select

from ..utils.error_mapper import map_selenium_error, create_error_response
from ..utils.element_resolver import get_by_strategy, resolve_element

actions_router = FastMCP(
    name="ActionTools",
    instructions="Element interaction tools: click, type, select, scroll",
)


def get_context(ctx: Context):
    """Helper to retrieve app context from lifespan."""
    return ctx.request_context.lifespan_context


def get_session(ctx: Context, session_id: str):
    """Get session from manager."""
    app_ctx = get_context(ctx)
    return app_ctx.session_manager.get_session(session_id)


# Key name mapping
KEY_MAP = {
    "ENTER": Keys.ENTER,
    "RETURN": Keys.RETURN,
    "TAB": Keys.TAB,
    "ESCAPE": Keys.ESCAPE,
    "ESC": Keys.ESCAPE,
    "BACKSPACE": Keys.BACKSPACE,
    "DELETE": Keys.DELETE,
    "SPACE": Keys.SPACE,
    "UP": Keys.UP,
    "DOWN": Keys.DOWN,
    "LEFT": Keys.LEFT,
    "RIGHT": Keys.RIGHT,
    "HOME": Keys.HOME,
    "END": Keys.END,
    "PAGE_UP": Keys.PAGE_UP,
    "PAGE_DOWN": Keys.PAGE_DOWN,
    "CONTROL": Keys.CONTROL,
    "CTRL": Keys.CONTROL,
    "ALT": Keys.ALT,
    "SHIFT": Keys.SHIFT,
    "META": Keys.META,
    "COMMAND": Keys.COMMAND,
    "F1": Keys.F1,
    "F2": Keys.F2,
    "F3": Keys.F3,
    "F4": Keys.F4,
    "F5": Keys.F5,
    "F6": Keys.F6,
    "F7": Keys.F7,
    "F8": Keys.F8,
    "F9": Keys.F9,
    "F10": Keys.F10,
    "F11": Keys.F11,
    "F12": Keys.F12,
}


@actions_router.tool(
    description="Click on an element by its ID",
    tags={"action", "click"},
)
async def click_element(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    element_id: Annotated[str, Field(description="Element ID from query_elements")],
) -> dict:
    """
    Click on a previously queried element.

    The element must have been returned by query_elements.
    Automatically scrolls the element into view before clicking.

    Args:
        session_id: Active session ID
        element_id: Element ID from a previous query_elements call

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        element = session.get_element(element_id)

        # Scroll into view and click
        await anyio.to_thread.run_sync(
            lambda: session.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
        )
        await anyio.to_thread.run_sync(lambda: element.click())

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "action": "clicked",
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Click on an element by selector (finds and clicks in one step)",
    tags={"action", "click"},
)
async def click_selector(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    strategy: Annotated[
        Literal["css", "xpath", "id", "name", "class", "tag", "link_text"],
        Field(description="Locator strategy"),
    ],
    selector: Annotated[str, Field(description="Selector value")],
) -> dict:
    """
    Find an element by selector and click it in one step.

    Useful when you don't need to reuse the element reference.

    Args:
        session_id: Active session ID
        strategy: Locator strategy (css, xpath, id, etc.)
        selector: Selector string

    Returns:
        Success status and the element ID for future reference
    """
    try:
        session = get_session(ctx, session_id)

        by = get_by_strategy(strategy)
        elements = await anyio.to_thread.run_sync(
            lambda: session.driver.find_elements(by, selector)
        )

        if not elements:
            from ..core.exceptions import ElementNotFoundError
            raise ElementNotFoundError(f"{strategy}={selector}")

        element = elements[0]
        element_id = session.register_element(element)

        # Scroll into view and click
        await anyio.to_thread.run_sync(
            lambda: session.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
        )
        await anyio.to_thread.run_sync(lambda: element.click())

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "action": "clicked",
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Type text into an input element",
    tags={"action", "input"},
)
async def type_text(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    text: Annotated[str, Field(description="Text to type")],
    element_id: Annotated[
        Optional[str],
        Field(description="Element ID (if not provided, uses strategy/selector)"),
    ] = None,
    strategy: Annotated[
        Optional[Literal["css", "xpath", "id", "name", "class"]],
        Field(description="Locator strategy (if element_id not provided)"),
    ] = None,
    selector: Annotated[
        Optional[str],
        Field(description="Selector value (if element_id not provided)"),
    ] = None,
    clear_first: Annotated[
        bool,
        Field(description="Clear existing content before typing"),
    ] = True,
) -> dict:
    """
    Type text into an input element.

    Can target by element_id or by strategy+selector.

    Args:
        session_id: Active session ID
        text: Text to type into the element
        element_id: Optional element ID from query_elements
        strategy: Optional locator strategy if not using element_id
        selector: Optional selector if not using element_id
        clear_first: Whether to clear existing content first

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        element = resolve_element(session, element_id, strategy, selector)

        if clear_first:
            await anyio.to_thread.run_sync(lambda: element.clear())

        await anyio.to_thread.run_sync(lambda: element.send_keys(text))

        return {
            "success": True,
            "session_id": session_id,
            "action": "typed",
            "text_length": len(text),
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Clear the content of an input element",
    tags={"action", "input"},
)
async def clear_element(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    element_id: Annotated[str, Field(description="Element ID to clear")],
) -> dict:
    """
    Clear the content of an input element.

    Args:
        session_id: Active session ID
        element_id: Element ID from query_elements

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        element = session.get_element(element_id)

        await anyio.to_thread.run_sync(lambda: element.clear())

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "action": "cleared",
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Set checkbox or radio button state",
    tags={"action", "input"},
)
async def set_checkbox_state(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    element_id: Annotated[str, Field(description="Checkbox/radio element ID")],
    checked: Annotated[bool, Field(description="Desired checked state")],
) -> dict:
    """
    Set the checked state of a checkbox or radio button.

    Only clicks if the current state differs from desired.

    Args:
        session_id: Active session ID
        element_id: Checkbox or radio button element ID
        checked: Whether it should be checked (True) or unchecked (False)

    Returns:
        Success status and whether a click was needed
    """
    try:
        session = get_session(ctx, session_id)
        element = session.get_element(element_id)

        is_selected = await anyio.to_thread.run_sync(lambda: element.is_selected())

        clicked = False
        if is_selected != checked:
            await anyio.to_thread.run_sync(lambda: element.click())
            clicked = True

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "checked": checked,
            "clicked": clicked,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Select an option from a dropdown/select element",
    tags={"action", "select"},
)
async def select_dropdown_option(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    element_id: Annotated[str, Field(description="Select element ID")],
    by: Annotated[
        Literal["visible_text", "value", "index"],
        Field(description="How to identify the option"),
    ],
    value: Annotated[str, Field(description="Option value, text, or index")],
) -> dict:
    """
    Select an option from a dropdown/select element.

    Args:
        session_id: Active session ID
        element_id: Select element ID
        by: Selection method (visible_text, value, or index)
        value: The value, text, or index of the option to select

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        element = session.get_element(element_id)

        select = Select(element)

        if by == "visible_text":
            await anyio.to_thread.run_sync(
                lambda: select.select_by_visible_text(value)
            )
        elif by == "value":
            await anyio.to_thread.run_sync(lambda: select.select_by_value(value))
        elif by == "index":
            await anyio.to_thread.run_sync(
                lambda: select.select_by_index(int(value))
            )

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "action": "selected",
            "by": by,
            "value": value,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Scroll an element into view",
    tags={"action", "scroll"},
)
async def scroll_to_element(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    element_id: Annotated[str, Field(description="Element ID to scroll to")],
    align_to: Annotated[
        Literal["top", "center", "bottom"],
        Field(description="Where to align the element in viewport"),
    ] = "center",
) -> dict:
    """
    Scroll an element into the visible viewport.

    Args:
        session_id: Active session ID
        element_id: Element ID to scroll into view
        align_to: Alignment (top, center, or bottom of viewport)

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        element = session.get_element(element_id)

        block = {"top": "start", "center": "center", "bottom": "end"}[align_to]

        await anyio.to_thread.run_sync(
            lambda: session.driver.execute_script(
                f"arguments[0].scrollIntoView({{block: '{block}', behavior: 'smooth'}});",
                element,
            )
        )

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "action": "scrolled",
            "align_to": align_to,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Scroll the page by a pixel offset",
    tags={"action", "scroll"},
)
async def scroll_by(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    x: Annotated[int, Field(description="Horizontal scroll pixels")] = 0,
    y: Annotated[int, Field(description="Vertical scroll pixels")] = 0,
) -> dict:
    """
    Scroll the page by a specified pixel offset.

    Positive y scrolls down, negative y scrolls up.

    Args:
        session_id: Active session ID
        x: Horizontal pixels to scroll (positive = right)
        y: Vertical pixels to scroll (positive = down)

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)

        await anyio.to_thread.run_sync(
            lambda: session.driver.execute_script(f"window.scrollBy({x}, {y});")
        )

        return {
            "success": True,
            "session_id": session_id,
            "action": "scrolled",
            "x": x,
            "y": y,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Hover over an element",
    tags={"action", "mouse"},
)
async def hover_element(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    element_id: Annotated[str, Field(description="Element ID to hover over")],
) -> dict:
    """
    Move the mouse to hover over an element.

    Useful for triggering hover states or dropdown menus.

    Args:
        session_id: Active session ID
        element_id: Element ID to hover over

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        element = session.get_element(element_id)

        actions = ActionChains(session.driver)
        await anyio.to_thread.run_sync(
            lambda: actions.move_to_element(element).perform()
        )

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "action": "hovered",
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Send keyboard keys (Enter, Tab, Escape, etc.)",
    tags={"action", "keyboard"},
)
async def send_keys(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    keys: Annotated[
        list[str],
        Field(description="List of key names (e.g., ['CONTROL', 'A'] for Ctrl+A)"),
    ],
    element_id: Annotated[
        Optional[str],
        Field(description="Optional element ID (otherwise sends to active element)"),
    ] = None,
) -> dict:
    """
    Send keyboard keys to an element or the active element.

    Supports special keys: ENTER, TAB, ESCAPE, BACKSPACE, DELETE, SPACE,
    UP, DOWN, LEFT, RIGHT, CONTROL, ALT, SHIFT, META, F1-F12.

    For key combinations, pass multiple keys (e.g., ["CONTROL", "A"]).

    Args:
        session_id: Active session ID
        keys: List of key names to send
        element_id: Optional element to send keys to

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)

        # Build key sequence
        key_sequence = []
        for key in keys:
            key_upper = key.upper()
            if key_upper in KEY_MAP:
                key_sequence.append(KEY_MAP[key_upper])
            else:
                key_sequence.append(key)  # Literal character

        if element_id:
            element = session.get_element(element_id)
            await anyio.to_thread.run_sync(lambda: element.send_keys(*key_sequence))
        else:
            # Send to active element
            actions = ActionChains(session.driver)
            await anyio.to_thread.run_sync(
                lambda: actions.send_keys(*key_sequence).perform()
            )

        return {
            "success": True,
            "session_id": session_id,
            "action": "sent_keys",
            "keys": keys,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Drag an element and drop it on another element",
    tags={"action", "mouse"},
)
async def drag_drop(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    source_element_id: Annotated[str, Field(description="Element to drag")],
    target_element_id: Annotated[str, Field(description="Element to drop onto")],
) -> dict:
    """
    Drag one element and drop it onto another.

    Args:
        session_id: Active session ID
        source_element_id: Element ID to drag
        target_element_id: Element ID to drop onto

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        source = session.get_element(source_element_id)
        target = session.get_element(target_element_id)

        actions = ActionChains(session.driver)
        await anyio.to_thread.run_sync(
            lambda: actions.drag_and_drop(source, target).perform()
        )

        return {
            "success": True,
            "session_id": session_id,
            "action": "drag_and_drop",
            "source_element_id": source_element_id,
            "target_element_id": target_element_id,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@actions_router.tool(
    description="Upload a file to a file input element",
    tags={"action", "file"},
)
async def upload_file(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    element_id: Annotated[str, Field(description="File input element ID")],
    file_path: Annotated[str, Field(description="Path to the file to upload")],
) -> dict:
    """
    Upload a file to a file input element.

    The element must be an <input type="file">.

    Args:
        session_id: Active session ID
        element_id: File input element ID
        file_path: Absolute path to the file to upload

    Returns:
        Success status
    """
    try:
        session = get_session(ctx, session_id)
        element = session.get_element(element_id)

        await anyio.to_thread.run_sync(lambda: element.send_keys(file_path))

        return {
            "success": True,
            "session_id": session_id,
            "element_id": element_id,
            "action": "uploaded",
            "file_path": file_path,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))
