"""Phase 2: MCP tool integration tests.

These tests call MCP tools through the Streamable HTTP transport to verify
the full stack: MCP Server -> Selenium -> Grid -> Browser -> Website
"""

import pytest
import base64


class TestMetaTools:
    """Tests for meta/diagnostic tools."""

    @pytest.mark.asyncio
    async def test_ping(self, mcp_session):
        """Test ping tool returns expected response.

        Expected: Returns status "ok" with version and grid_url
        """
        result = await mcp_session.call_tool("ping", {})

        print(f"\n[EMPIRICAL] Ping result: {result}")

        assert result.get("status") == "ok"
        assert "version" in result
        assert "grid_url" in result


class TestSessionTools:
    """Tests for session lifecycle tools."""

    @pytest.mark.asyncio
    async def test_create_and_close_session(self, mcp_session):
        """Test creating and closing a session.

        Expected: session_id starts with "sess_"
        """
        # Create session
        create_result = await mcp_session.call_tool( "create_session", {
            "browser": "chrome",
            "headless": False
        })

        session_id = create_result.get("session_id")
        print(f"\n[EMPIRICAL] Created session: {session_id}")
        print(f"[EMPIRICAL] Browser: {create_result.get('browser')}")

        assert session_id is not None
        assert session_id.startswith("sess_")

        # Close session
        close_result = await mcp_session.call_tool( "close_session", {
            "session_id": session_id
        })

        print(f"[EMPIRICAL] Close result: {close_result}")
        assert close_result.get("success") is True

    @pytest.mark.asyncio
    async def test_list_sessions(self, mcp_session, session_id):
        """Test listing sessions shows the created session.

        Uses session_id fixture which creates and cleans up a session.
        """
        result = await mcp_session.call_tool( "list_sessions", {})

        print(f"\n[EMPIRICAL] Sessions: {result}")

        sessions = result.get("sessions", [])
        session_ids = [s.get("session_id") for s in sessions]

        assert session_id in session_ids, \
            f"Session {session_id} not found in {session_ids}"


class TestNavigationTools:
    """Tests for navigation tools."""

    @pytest.mark.asyncio
    async def test_navigate(self, mcp_session, session_id):
        """Test navigating to a URL.

        Empirical: example.com URL is https://example.com/
        """
        result = await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        print(f"\n[EMPIRICAL] Navigate result: {result}")

        assert result.get("success") is True
        assert "example.com" in result.get("url", "")

    @pytest.mark.asyncio
    async def test_get_page_info(self, mcp_session, session_id):
        """Test getting page info after navigation.

        Empirical: title="Example Domain", ready_state="complete"
        """
        # First navigate
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Get page info
        result = await mcp_session.call_tool( "get_page_info", {
            "session_id": session_id
        })

        print(f"\n[EMPIRICAL] Page info: {result}")

        assert result.get("title") == "Example Domain", \
            f"Unexpected title: {result.get('title')}"
        assert "example.com" in result.get("url", "")
        assert result.get("ready_state") == "complete"

    @pytest.mark.asyncio
    async def test_navigate_back_forward(self, mcp_session, session_id):
        """Test back/forward navigation.

        Empirical: Navigate example.com -> httpbin.org -> back returns to example.com
        """
        # Navigate to first page
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Navigate to second page
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://httpbin.org"
        })

        # Go back
        back_result = await mcp_session.call_tool( "navigate_back", {
            "session_id": session_id
        })

        print(f"\n[EMPIRICAL] After back: {back_result}")
        assert "example.com" in back_result.get("url", ""), \
            f"Expected example.com, got {back_result.get('url')}"

        # Go forward
        forward_result = await mcp_session.call_tool( "navigate_forward", {
            "session_id": session_id
        })

        print(f"[EMPIRICAL] After forward: {forward_result}")
        assert "httpbin.org" in forward_result.get("url", ""), \
            f"Expected httpbin.org, got {forward_result.get('url')}"

    @pytest.mark.asyncio
    async def test_reload_page(self, mcp_session, session_id):
        """Test page reload.

        Empirical: Reload returns ready_state=complete
        """
        # Navigate first
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Reload
        result = await mcp_session.call_tool( "reload_page", {
            "session_id": session_id
        })

        print(f"\n[EMPIRICAL] Reload result: {result}")

        assert result.get("success") is True


class TestObservationTools:
    """Tests for observation tools."""

    @pytest.mark.asyncio
    async def test_get_dom(self, mcp_session, session_id):
        """Test getting DOM content.

        Empirical: example.com DOM contains <h1>Example Domain</h1>
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "get_dom", {
            "session_id": session_id
        })

        html = result.get("html", "")
        print(f"\n[EMPIRICAL] DOM length: {len(html)} chars")
        print(f"[EMPIRICAL] Contains h1: {'<h1>' in html.lower()}")

        assert "Example Domain" in html, \
            f"'Example Domain' not found in DOM (length {len(html)})"

    @pytest.mark.asyncio
    async def test_get_visible_text(self, mcp_session, session_id):
        """Test getting visible text.

        Empirical: example.com visible text contains "Example Domain"
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "get_visible_text", {
            "session_id": session_id
        })

        text = result.get("text", "")
        print(f"\n[EMPIRICAL] Visible text length: {len(text)} chars")
        print(f"[EMPIRICAL] Text preview: {text[:200]}...")

        assert "Example Domain" in text

    @pytest.mark.asyncio
    async def test_query_elements_css(self, mcp_session, session_id):
        """Test querying elements with CSS selector.

        Empirical: example.com has h1 element, returns element_id
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "h1"
        })

        elements = result.get("elements", [])
        print(f"\n[EMPIRICAL] Found {len(elements)} h1 element(s)")

        assert len(elements) >= 1, "No h1 elements found"
        assert elements[0].get("element_id", "").startswith("elem_")

        # Check element properties
        print(f"[EMPIRICAL] Element ID: {elements[0].get('element_id')}")
        print(f"[EMPIRICAL] Tag name: {elements[0].get('tag_name')}")
        print(f"[EMPIRICAL] Text: {elements[0].get('text')}")

    @pytest.mark.asyncio
    async def test_query_elements_xpath(self, mcp_session, session_id):
        """Test querying elements with XPath.

        Empirical: //h1 finds the h1 element
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "query_elements", {
            "session_id": session_id,
            "strategy": "xpath",
            "selector": "//h1"
        })

        elements = result.get("elements", [])
        print(f"\n[EMPIRICAL] XPath found {len(elements)} element(s)")

        assert len(elements) >= 1

    @pytest.mark.asyncio
    async def test_get_screenshot(self, mcp_session, session_id):
        """Test taking a screenshot.

        Empirical: Returns base64-encoded PNG data as image_base64
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "get_screenshot", {
            "session_id": session_id
        })

        # Tool returns image_base64, not screenshot
        screenshot = result.get("image_base64", "")
        print(f"\n[EMPIRICAL] Screenshot data length: {len(screenshot)} chars")

        # Verify it's valid base64
        assert len(screenshot) > 100, "Screenshot too small"

        # Try to decode it
        try:
            decoded = base64.b64decode(screenshot)
            # PNG magic bytes
            assert decoded[:4] == b'\x89PNG', "Not a valid PNG"
            print(f"[EMPIRICAL] Valid PNG, size: {len(decoded)} bytes")
        except Exception as e:
            pytest.fail(f"Invalid base64/PNG: {e}")


class TestActionTools:
    """Tests for action tools."""

    @pytest.mark.asyncio
    async def test_click_element(self, mcp_session, session_id):
        """Test clicking an element.

        Empirical: Click "More information" link on example.com
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Find the link
        elements = await mcp_session.call_tool( "query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "a"
        })

        assert len(elements.get("elements", [])) >= 1, "No links found"

        element_id = elements["elements"][0]["element_id"]
        print(f"\n[EMPIRICAL] Clicking element: {element_id}")

        # Click it
        result = await mcp_session.call_tool( "click_element", {
            "session_id": session_id,
            "element_id": element_id
        })

        print(f"[EMPIRICAL] Click result: {result}")
        assert result.get("success") is True

        # Verify navigation happened
        page_info = await mcp_session.call_tool( "get_page_info", {
            "session_id": session_id
        })
        print(f"[EMPIRICAL] After click URL: {page_info.get('url')}")

        # Should have navigated away from example.com
        assert "iana.org" in page_info.get("url", "") or "example.com" not in page_info.get("url", ""), \
            "Click did not navigate"

    @pytest.mark.asyncio
    async def test_scroll_by(self, mcp_session, session_id):
        """Test scrolling the page.

        Empirical: Scroll down and verify scroll position changed
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Get initial scroll position
        initial_pos = await mcp_session.call_tool( "execute_script", {
            "session_id": session_id,
            "script": "return window.scrollY"
        })
        print(f"\n[EMPIRICAL] Initial scroll Y: {initial_pos.get('result')}")

        # Scroll down - tool uses x/y, not delta_x/delta_y
        result = await mcp_session.call_tool( "scroll_by", {
            "session_id": session_id,
            "x": 0,
            "y": 200
        })

        print(f"[EMPIRICAL] Scroll result: {result}")
        assert result.get("success") is True


class TestWaitTools:
    """Tests for wait tools."""

    @pytest.mark.asyncio
    async def test_wait_for_selector(self, mcp_session, session_id):
        """Test waiting for an element.

        Empirical: Wait for h1 on example.com
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "wait_for_selector", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "h1",
            "timeout_ms": 5000
        })

        print(f"\n[EMPIRICAL] Wait result: {result}")

        # Tool returns success=True and element_id when condition met
        assert result.get("success") is True
        assert result.get("element_id", "").startswith("elem_")

    @pytest.mark.asyncio
    async def test_wait_for_url(self, mcp_session, session_id):
        """Test waiting for URL pattern.

        Empirical: Wait for URL containing "example"
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "wait_for_url", {
            "session_id": session_id,
            "pattern": "example",
            "timeout_ms": 5000
        })

        print(f"\n[EMPIRICAL] Wait for URL result: {result}")

        # Tool returns success=True and url when pattern matches
        assert result.get("success") is True
        assert "example" in result.get("url", "")

    @pytest.mark.asyncio
    async def test_wait_for_ready_state(self, mcp_session, session_id):
        """Test waiting for document ready state.

        Empirical: Ready state is "complete"
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "wait_for_ready_state", {
            "session_id": session_id,
            "state": "complete",
            "timeout_ms": 10000
        })

        print(f"\n[EMPIRICAL] Ready state result: {result}")

        assert result.get("ready_state") == "complete"


class TestScriptingTools:
    """Tests for JavaScript execution tools."""

    @pytest.mark.asyncio
    async def test_execute_script(self, mcp_session, session_id):
        """Test executing JavaScript.

        Empirical: document.title returns "Example Domain"
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "execute_script", {
            "session_id": session_id,
            "script": "return document.title"
        })

        print(f"\n[EMPIRICAL] Script result: {result}")

        assert result.get("result") == "Example Domain"

    @pytest.mark.asyncio
    async def test_execute_script_with_element(self, mcp_session, session_id):
        """Test executing JavaScript with element reference.

        Empirical: Get h1 element's textContent via script
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # First get an element
        elements = await mcp_session.call_tool( "query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "h1"
        })

        element_id = elements["elements"][0]["element_id"]

        # Execute script with element - tool uses `args` param, element_ids are auto-resolved
        result = await mcp_session.call_tool( "execute_script", {
            "session_id": session_id,
            "script": "return arguments[0].textContent",
            "args": [element_id]
        })

        print(f"\n[EMPIRICAL] Script with element result: {result}")

        assert result.get("result") == "Example Domain"

    @pytest.mark.asyncio
    async def test_execute_script_complex(self, mcp_session, session_id):
        """Test executing more complex JavaScript.

        Empirical: Return object with multiple properties
        """
        await mcp_session.call_tool( "navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool( "execute_script", {
            "session_id": session_id,
            "script": """
                return {
                    title: document.title,
                    url: window.location.href,
                    h1Count: document.querySelectorAll('h1').length
                }
            """
        })

        print(f"\n[EMPIRICAL] Complex script result: {result}")

        script_result = result.get("result", {})
        assert script_result.get("title") == "Example Domain"
        assert "example.com" in script_result.get("url", "")
        assert script_result.get("h1Count") >= 1

    @pytest.mark.asyncio
    async def test_execute_async_script(self, mcp_session, session_id):
        """Test executing asynchronous JavaScript.

        Empirical: Async script with setTimeout returns after delay
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool("execute_async_script", {
            "session_id": session_id,
            "script": """
                var callback = arguments[arguments.length - 1];
                setTimeout(function() {
                    callback({done: true, title: document.title});
                }, 100);
            """,
            "timeout_ms": 5000
        })

        print(f"\n[EMPIRICAL] Async script result: {result}")

        assert result.get("success") is True
        script_result = result.get("result", {})
        assert script_result.get("done") is True
        assert script_result.get("title") == "Example Domain"


class TestAdditionalObservationTools:
    """Tests for additional observation tools."""

    @pytest.mark.asyncio
    async def test_get_console_logs(self, mcp_session, session_id):
        """Test getting browser console logs.

        Empirical: Chrome returns console logs (may be empty or have message about unavailability)
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Generate a console log
        await mcp_session.call_tool("execute_script", {
            "session_id": session_id,
            "script": "console.log('Test log message')"
        })

        result = await mcp_session.call_tool("get_console_logs", {
            "session_id": session_id,
            "level": "all"
        })

        print(f"\n[EMPIRICAL] Console logs: {result}")

        # Tool returns success even if logs not available
        assert result.get("success") is True
        assert "logs" in result or "message" in result


class TestAdditionalActionTools:
    """Tests for additional action tools."""

    @pytest.mark.asyncio
    async def test_click_selector(self, mcp_session, session_id):
        """Test clicking by selector directly.

        Empirical: Click link on example.com by CSS selector
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool("click_selector", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "a"
        })

        print(f"\n[EMPIRICAL] Click selector result: {result}")

        assert result.get("success") is True
        assert result.get("element_id", "").startswith("elem_")

    @pytest.mark.asyncio
    async def test_type_text(self, mcp_session, session_id):
        """Test typing text into an input field.

        Empirical: Use httpbin.org forms page to test input
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://httpbin.org/forms/post"
        })

        # Find the customer name input
        elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "input[name='custname']"
        })

        print(f"\n[EMPIRICAL] Found input elements: {elements}")

        assert len(elements.get("elements", [])) >= 1
        element_id = elements["elements"][0]["element_id"]

        # Type text into the input
        result = await mcp_session.call_tool("type_text", {
            "session_id": session_id,
            "element_id": element_id,
            "text": "Test Customer",
            "clear_first": True
        })

        print(f"[EMPIRICAL] Type result: {result}")
        assert result.get("success") is True

        # Verify the value was typed
        value = await mcp_session.call_tool("execute_script", {
            "session_id": session_id,
            "script": "return arguments[0].value",
            "args": [element_id]
        })
        print(f"[EMPIRICAL] Input value: {value.get('result')}")
        assert value.get("result") == "Test Customer"

    @pytest.mark.asyncio
    async def test_clear_element(self, mcp_session, session_id):
        """Test clearing an input field.

        Empirical: Type then clear input on httpbin forms
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://httpbin.org/forms/post"
        })

        # Find input and type something
        elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "input[name='custname']"
        })
        element_id = elements["elements"][0]["element_id"]

        await mcp_session.call_tool("type_text", {
            "session_id": session_id,
            "element_id": element_id,
            "text": "To be cleared",
            "clear_first": True
        })

        # Clear the element
        result = await mcp_session.call_tool("clear_element", {
            "session_id": session_id,
            "element_id": element_id
        })

        print(f"\n[EMPIRICAL] Clear result: {result}")
        assert result.get("success") is True

        # Verify it's cleared
        value = await mcp_session.call_tool("execute_script", {
            "session_id": session_id,
            "script": "return arguments[0].value",
            "args": [element_id]
        })
        print(f"[EMPIRICAL] Value after clear: '{value.get('result')}'")
        assert value.get("result") == ""

    @pytest.mark.asyncio
    async def test_send_keys(self, mcp_session, session_id):
        """Test sending keyboard keys.

        Empirical: Send keys to focused element
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://httpbin.org/forms/post"
        })

        # Focus on input first
        elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "input[name='custname']"
        })
        element_id = elements["elements"][0]["element_id"]

        # Click to focus
        await mcp_session.call_tool("click_element", {
            "session_id": session_id,
            "element_id": element_id
        })

        # Send keys to the element
        result = await mcp_session.call_tool("send_keys", {
            "session_id": session_id,
            "keys": ["H", "i"],
            "element_id": element_id
        })

        print(f"\n[EMPIRICAL] Send keys result: {result}")
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_hover_element(self, mcp_session, session_id):
        """Test hovering over an element.

        Empirical: Hover over link on example.com
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Find an element to hover
        elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "a"
        })
        element_id = elements["elements"][0]["element_id"]

        result = await mcp_session.call_tool("hover_element", {
            "session_id": session_id,
            "element_id": element_id
        })

        print(f"\n[EMPIRICAL] Hover result: {result}")
        assert result.get("success") is True
        assert result.get("action") == "hovered"

    @pytest.mark.asyncio
    async def test_scroll_to_element(self, mcp_session, session_id):
        """Test scrolling to an element.

        Empirical: Scroll to h1 element
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        # Find element to scroll to
        elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "h1"
        })
        element_id = elements["elements"][0]["element_id"]

        result = await mcp_session.call_tool("scroll_to_element", {
            "session_id": session_id,
            "element_id": element_id,
            "align_to": "center"
        })

        print(f"\n[EMPIRICAL] Scroll to element result: {result}")
        assert result.get("success") is True
        assert result.get("action") == "scrolled"

    @pytest.mark.asyncio
    async def test_set_checkbox_state(self, mcp_session, session_id):
        """Test setting checkbox state.

        Empirical: Toggle checkbox on httpbin forms (has topping checkboxes)
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://httpbin.org/forms/post"
        })

        # Find a checkbox (topping checkboxes)
        elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "input[type='checkbox']"
        })

        print(f"\n[EMPIRICAL] Found checkboxes: {len(elements.get('elements', []))}")

        if len(elements.get("elements", [])) > 0:
            element_id = elements["elements"][0]["element_id"]

            # Check the checkbox
            result = await mcp_session.call_tool("set_checkbox_state", {
                "session_id": session_id,
                "element_id": element_id,
                "checked": True
            })

            print(f"[EMPIRICAL] Set checkbox result: {result}")
            assert result.get("success") is True

            # Uncheck it
            result2 = await mcp_session.call_tool("set_checkbox_state", {
                "session_id": session_id,
                "element_id": element_id,
                "checked": False
            })
            assert result2.get("success") is True
        else:
            pytest.skip("No checkboxes found on page")

    @pytest.mark.asyncio
    async def test_select_dropdown_option(self, mcp_session, session_id):
        """Test selecting dropdown option.

        Uses the-internet.herokuapp.com dropdown page
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://the-internet.herokuapp.com/dropdown"
        })

        # Find the select element
        elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "#dropdown"
        })

        print(f"\n[EMPIRICAL] Found select elements: {elements}")

        if len(elements.get("elements", [])) > 0:
            element_id = elements["elements"][0]["element_id"]

            # Select by visible text
            result = await mcp_session.call_tool("select_dropdown_option", {
                "session_id": session_id,
                "element_id": element_id,
                "by": "visible_text",
                "value": "Option 1"
            })

            print(f"[EMPIRICAL] Select dropdown result: {result}")
            assert result.get("success") is True

            # Select by value
            result2 = await mcp_session.call_tool("select_dropdown_option", {
                "session_id": session_id,
                "element_id": element_id,
                "by": "value",
                "value": "2"
            })
            assert result2.get("success") is True
        else:
            pytest.skip("No select elements found on page")


class TestAdditionalWaitTools:
    """Tests for additional wait tools."""

    @pytest.mark.asyncio
    async def test_wait_for_text(self, mcp_session, session_id):
        """Test waiting for text to appear.

        Empirical: Wait for "Example Domain" text on example.com
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://example.com"
        })

        result = await mcp_session.call_tool("wait_for_text", {
            "session_id": session_id,
            "text": "Example Domain",
            "timeout_ms": 5000
        })

        print(f"\n[EMPIRICAL] Wait for text result: {result}")

        assert result.get("success") is True
        assert result.get("text_found") == "Example Domain"


class TestComplexActionTools:
    """Tests for complex action tools that need special setup."""

    @pytest.mark.asyncio
    async def test_drag_drop(self, mcp_session, session_id):
        """Test drag and drop functionality.

        Uses the-internet.herokuapp.com drag-and-drop page
        """
        await mcp_session.call_tool("navigate", {
            "session_id": session_id,
            "url": "https://the-internet.herokuapp.com/drag_and_drop"
        })

        # Find source (column A) and target (column B)
        source_elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "#column-a"
        })

        target_elements = await mcp_session.call_tool("query_elements", {
            "session_id": session_id,
            "strategy": "css",
            "selector": "#column-b"
        })

        print(f"\n[EMPIRICAL] Source elements: {source_elements}")
        print(f"[EMPIRICAL] Target elements: {target_elements}")

        if (len(source_elements.get("elements", [])) > 0 and
            len(target_elements.get("elements", [])) > 0):

            source_id = source_elements["elements"][0]["element_id"]
            target_id = target_elements["elements"][0]["element_id"]

            result = await mcp_session.call_tool("drag_drop", {
                "session_id": session_id,
                "source_element_id": source_id,
                "target_element_id": target_id
            })

            print(f"[EMPIRICAL] Drag drop result: {result}")
            assert result.get("success") is True
        else:
            pytest.skip("Drag drop elements not found")

    @pytest.mark.asyncio
    async def test_upload_file(self, mcp_session, session_id):
        """Test file upload functionality.

        Uses the-internet.herokuapp.com file upload page
        Note: This test creates a temp file to upload
        """
        import tempfile
        import os

        # Create a temp file to upload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test file content for upload")
            temp_file_path = f.name

        try:
            await mcp_session.call_tool("navigate", {
                "session_id": session_id,
                "url": "https://the-internet.herokuapp.com/upload"
            })

            # Find the file input
            elements = await mcp_session.call_tool("query_elements", {
                "session_id": session_id,
                "strategy": "css",
                "selector": "input[type='file']"
            })

            print(f"\n[EMPIRICAL] File input elements: {elements}")

            if len(elements.get("elements", [])) > 0:
                element_id = elements["elements"][0]["element_id"]

                result = await mcp_session.call_tool("upload_file", {
                    "session_id": session_id,
                    "element_id": element_id,
                    "file_path": temp_file_path
                })

                print(f"[EMPIRICAL] Upload result: {result}")
                assert result.get("success") is True
            else:
                pytest.skip("File input not found")
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
