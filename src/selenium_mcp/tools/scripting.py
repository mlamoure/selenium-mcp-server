"""JavaScript execution tools."""

from typing import Annotated, Optional
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import anyio

from ..utils.error_mapper import map_selenium_error, create_error_response

scripting_router = FastMCP(
    name="ScriptingTools",
    instructions="Execute JavaScript in the browser context",
)


def get_context(ctx: Context):
    """Helper to retrieve app context from lifespan."""
    return ctx.request_context.lifespan_context


def get_session(ctx: Context, session_id: str):
    """Get session from manager."""
    app_ctx = get_context(ctx)
    return app_ctx.session_manager.get_session(session_id)


# Maximum script length for safety
MAX_SCRIPT_LENGTH = 10000


@scripting_router.tool(
    description="Execute JavaScript code in the browser",
    tags={"script", "javascript"},
)
async def execute_script(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    script: Annotated[
        str,
        Field(description="JavaScript code to execute"),
    ],
    args: Annotated[
        Optional[list],
        Field(description="Arguments to pass to the script (accessible as arguments[0], etc.)"),
    ] = None,
) -> dict:
    """
    Execute JavaScript code synchronously in the browser.

    The script runs in the page context and can access the DOM.
    Arguments are passed via the JavaScript `arguments` array.

    Example scripts:
    - "return document.title"
    - "return arguments[0].textContent" (with element as arg)
    - "window.scrollTo(0, document.body.scrollHeight)"

    Args:
        session_id: Active session ID
        script: JavaScript code to execute
        args: Optional list of arguments (can include element_ids)

    Returns:
        Script execution result (JSON-serializable values)
    """
    try:
        session = get_session(ctx, session_id)

        # Safety check on script length
        if len(script) > MAX_SCRIPT_LENGTH:
            raise ValueError(
                f"Script too long ({len(script)} chars). "
                f"Maximum allowed: {MAX_SCRIPT_LENGTH}"
            )

        # Resolve any element_id arguments to actual elements
        resolved_args = []
        if args:
            for arg in args:
                if isinstance(arg, str) and arg.startswith("elem_"):
                    # Attempt to resolve as element ID
                    try:
                        element = session.get_element(arg)
                        resolved_args.append(element)
                    except Exception:
                        resolved_args.append(arg)  # Use as string if not found
                else:
                    resolved_args.append(arg)

        # Execute the script
        result = await anyio.to_thread.run_sync(
            lambda: session.driver.execute_script(script, *resolved_args)
        )

        # Try to make result JSON-serializable
        try:
            import json
            json.dumps(result)
        except (TypeError, ValueError):
            result = str(result)

        return {
            "success": True,
            "session_id": session_id,
            "result": result,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))


@scripting_router.tool(
    description="Execute asynchronous JavaScript code",
    tags={"script", "javascript"},
)
async def execute_async_script(
    ctx: Context,
    session_id: Annotated[str, Field(description="Active session ID")],
    script: Annotated[
        str,
        Field(description="Async JavaScript code (must call callback as last argument)"),
    ],
    args: Annotated[
        Optional[list],
        Field(description="Arguments to pass to the script"),
    ] = None,
    timeout_ms: Annotated[
        Optional[int],
        Field(description="Script timeout in milliseconds"),
    ] = None,
) -> dict:
    """
    Execute asynchronous JavaScript code in the browser.

    The script must call a callback function (provided as the last argument)
    when it completes. The callback's argument becomes the result.

    Example:
    ```
    var callback = arguments[arguments.length - 1];
    setTimeout(function() {
        callback("done after delay");
    }, 1000);
    ```

    Args:
        session_id: Active session ID
        script: Async JavaScript code (must call callback)
        args: Optional list of arguments
        timeout_ms: Script timeout

    Returns:
        Value passed to the callback
    """
    try:
        app_ctx = get_context(ctx)
        session = get_session(ctx, session_id)

        # Safety check on script length
        if len(script) > MAX_SCRIPT_LENGTH:
            raise ValueError(
                f"Script too long ({len(script)} chars). "
                f"Maximum allowed: {MAX_SCRIPT_LENGTH}"
            )

        # Set script timeout if specified
        if timeout_ms:
            await anyio.to_thread.run_sync(
                lambda: session.driver.set_script_timeout(timeout_ms / 1000.0)
            )
        else:
            await anyio.to_thread.run_sync(
                lambda: session.driver.set_script_timeout(
                    app_ctx.settings.script_timeout_seconds
                )
            )

        # Resolve element arguments
        resolved_args = []
        if args:
            for arg in args:
                if isinstance(arg, str) and arg.startswith("elem_"):
                    try:
                        element = session.get_element(arg)
                        resolved_args.append(element)
                    except Exception:
                        resolved_args.append(arg)
                else:
                    resolved_args.append(arg)

        # Execute the async script
        result = await anyio.to_thread.run_sync(
            lambda: session.driver.execute_async_script(script, *resolved_args)
        )

        # Try to make result JSON-serializable
        try:
            import json
            json.dumps(result)
        except (TypeError, ValueError):
            result = str(result)

        return {
            "success": True,
            "session_id": session_id,
            "result": result,
        }

    except Exception as e:
        error_code, message = map_selenium_error(e)
        error_response = create_error_response(error_code, message)
        raise ToolError(str(error_response.to_dict()))
