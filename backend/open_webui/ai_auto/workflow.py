"""MCP Workflow Orchestrator"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import Request

from open_webui.ai_auto.context import MCPRequest, MCPResponse, ToolCall, WorkflowState
from open_webui.ai_auto.prompting import build_system_prompt, build_user_prompt
from open_webui.ai_auto.storage import FlightStorage
from open_webui.ai_auto.tools.google_ai_mode import GoogleAiModeTool
from open_webui.ai_auto.tools.google_flight_calendar import GoogleFlightCalendarTool
from open_webui.ai_auto.tools.google_flight_search import GoogleFlightSearchTool
from open_webui.models.flight_pricing import (
    AutoSearchTable,
    FlightRoutesTable,
)
from open_webui.utils.chat import generate_chat_completion

log = logging.getLogger(__name__)

# Travel class mapping
TRAVEL_CLASS_MAP = {
    0: "economy",
    1: "premium_economy",
    2: "business",
    3: "first",
}


async def run_mcp_workflow(
    request: Request,
    mcp_request: MCPRequest,
    user: Any,
) -> MCPResponse:
    """
    Run the MCP workflow to search for flights using AI.

    Args:
        request: FastAPI request object
        mcp_request: MCP request parameters
        user: User object

    Returns:
        MCPResponse with workflow results
    """
    log.info(
        "Starting MCP workflow for user %s: %s -> %s, airlines=%s, model=%s, return_days=%s",
        user.id if user else "unknown",
        mcp_request.departure,
        mcp_request.destination,
        mcp_request.airlines,
        mcp_request.model_id,
        mcp_request.return_trip_days,
    )
    
    workflow_state = WorkflowState()
    tools = {
        "google_ai_mode": GoogleAiModeTool(),
        "google_flight_calendar": GoogleFlightCalendarTool(),
        "google_flight_search": GoogleFlightSearchTool(),
    }
    
    log.debug("Initialized MCP tools: %s", list(tools.keys()))

    # Create auto_search in database first
    auto_search_id = None
    try:
        routes_table = FlightRoutesTable()
        auto_search_table = AutoSearchTable()

        departure_route = routes_table.get_or_create(mcp_request.departure, mcp_request.destination)
        return_route = routes_table.get_or_create(mcp_request.destination, mcp_request.departure)

        auto_search = auto_search_table.create(
            departure_route_id=departure_route.route_id,
            return_route_id=return_route.route_id,
            travel_class=mcp_request.travel_class,
            direct_flight=mcp_request.direct_flight,
        )
        auto_search_id = auto_search.auto_search_id
        log.info(
            "Created auto_search %s for MCP workflow: route=%s->%s, class=%s, direct=%s",
            auto_search_id,
            mcp_request.departure,
            mcp_request.destination,
            mcp_request.travel_class,
            mcp_request.direct_flight,
        )

    except Exception as e:
        log.exception("Failed to create auto_search: %s", e)
        return MCPResponse(
            success=False,
            message="Failed to initialize search",
            error=str(e),
            workflow_state=workflow_state,
        )

    # Update flight search tool with auto_search_id
    tools["google_flight_search"].storage = FlightStorage()
    
    # Store auto_search_id in workflow state for return
    workflow_state.auto_search_id = auto_search_id

    travel_class_label = TRAVEL_CLASS_MAP.get(mcp_request.travel_class, "economy")
    log.debug("Using travel class: %s (mapped from %d)", travel_class_label, mcp_request.travel_class)

    # Build prompts
    system_prompt = build_system_prompt(
        departure=mcp_request.departure,
        destination=mcp_request.destination,
        airlines=mcp_request.airlines,
        return_trip_days=mcp_request.return_trip_days,
        travel_class=travel_class_label,
    )
    log.debug("Built system prompt (length: %d chars)", len(system_prompt))

    user_prompt = build_user_prompt(
        departure=mcp_request.departure,
        destination=mcp_request.destination,
        airlines=mcp_request.airlines,
        return_trip_days=mcp_request.return_trip_days,
    )
    log.debug("Built user prompt: %s", user_prompt)

    # Prepare messages for chat completion
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Define tool schemas for function calling
    tools_schema = [
        {
            "type": "function",
            "function": {
                "name": "google_ai_mode",
                "description": "Get initial insights about cheap flight periods using Google AI Mode. Use simple sentences in the query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Simple sentence query, e.g., 'Give me the cheapest 8 days return flights of CX from HKG to NGO in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time'",
                        },
                        "location": {"type": "string", "description": "Optional location string"},
                        "hl": {"type": "string", "description": "Interface language", "default": "en"},
                        "gl": {"type": "string", "description": "Geolocation country code", "default": "HK"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "google_flight_calendar",
                "description": "Get price overview for a date range using Google Flight Calendar API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "departure_id": {"type": "string", "description": "Departure airport code"},
                        "arrival_id": {"type": "string", "description": "Arrival airport code"},
                        "outbound_date": {"type": "string", "description": "Anchor date for outbound (YYYY-MM-DD)"},
                        "outbound_date_start": {"type": "string", "description": "Start of outbound date range (YYYY-MM-DD)"},
                        "outbound_date_end": {"type": "string", "description": "End of outbound date range (YYYY-MM-DD)"},
                        "flight_type": {"type": "string", "enum": ["one_way", "round_trip"], "default": "round_trip"},
                        "travel_class": {"type": "string", "enum": ["economy", "premium_economy", "business", "first"]},
                        "non_stop": {"type": "boolean", "description": "Direct flights only"},
                        "included_airlines": {"type": "string", "description": "Comma-separated airline codes"},
                        "return_date": {"type": "string", "description": "Anchor date for return (YYYY-MM-DD)"},
                        "return_date_start": {"type": "string", "description": "Start of return date range (YYYY-MM-DD)"},
                        "return_date_end": {"type": "string", "description": "End of return date range (YYYY-MM-DD)"},
                    },
                    "required": ["departure_id", "arrival_id", "outbound_date", "outbound_date_start", "outbound_date_end"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "google_flight_search",
                "description": "Get detailed flight data using Google Flight Search API and store results in database. This is the only tool that stores data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "departure_id": {"type": "string", "description": "Departure airport code"},
                        "arrival_id": {"type": "string", "description": "Arrival airport code"},
                        "outbound_date": {"type": "string", "description": "Outbound date (YYYY-MM-DD)"},
                        "return_date": {"type": "string", "description": "Return date (YYYY-MM-DD)"},
                        "travel_class": {"type": "string", "enum": ["economy", "premium_economy", "business", "first"], "default": "economy"},
                        "included_airlines": {"type": "string", "description": "Comma-separated airline codes"},
                        "excluded_airlines": {"type": "string", "description": "Comma-separated airline codes to exclude"},
                        "non_stop": {"type": "boolean", "description": "Direct flights only"},
                        "adults": {"type": "integer", "default": 1},
                        "children": {"type": "integer", "default": 0},
                    },
                    "required": ["departure_id", "arrival_id", "outbound_date"],
                },
            },
        },
    ]

    # Main workflow loop
    try:
        while workflow_state.iteration_count < workflow_state.max_iterations and not workflow_state.is_complete:
            workflow_state.iteration_count += 1
            log.info("MCP workflow iteration %d/%d", workflow_state.iteration_count, workflow_state.max_iterations)

            # Prepare form_data for chat completion
            form_data = {
                "model": mcp_request.model_id,
                "messages": messages,
                "tools": tools_schema,
                "tool_choice": "auto",
                "stream": False,
                "temperature": 0.7,
            }

            # Call model
            try:
                log.info(
                    "Calling model %s (iteration %d, message count: %d, tools: %d)",
                    mcp_request.model_id,
                    workflow_state.iteration_count,
                    len(messages),
                    len(tools_schema),
                )
                log.debug("Form data keys: %s", list(form_data.keys()))
                log.debug("Tools schema: %s", [t.get("function", {}).get("name") for t in tools_schema])
                
                response = await generate_chat_completion(request, form_data, user, bypass_filter=True)
                
                log.debug("Response type: %s, class: %s", type(response).__name__, type(response))
                
                # Handle different response types
                if isinstance(response, dict):
                    response_data = response
                    log.debug("Response is dict, keys: %s", list(response_data.keys()))
                else:
                    # Try to extract JSON from various response types
                    try:
                        # Check if it's a JSONResponse (FastAPI/Starlette)
                        if hasattr(response, "body") and hasattr(response, "media_type"):
                            # JSONResponse - extract body
                            body_bytes = response.body
                            if isinstance(body_bytes, bytes):
                                response_data = json.loads(body_bytes.decode('utf-8'))
                            elif isinstance(body_bytes, str):
                                response_data = json.loads(body_bytes)
                            else:
                                response_data = body_bytes
                            log.debug("Extracted from JSONResponse body, keys: %s", list(response_data.keys()) if isinstance(response_data, dict) else "not a dict")
                        # Check if it has a json() method (aiohttp Response, etc.)
                        elif hasattr(response, "json") and callable(getattr(response, "json")):
                            response_data = await response.json()
                            log.debug("Extracted from response.json(), keys: %s", list(response_data.keys()) if isinstance(response_data, dict) else "not a dict")
                        # Check if it's already the content (some wrappers)
                        elif hasattr(response, "__dict__"):
                            # Try to get content attribute
                            if hasattr(response, "content"):
                                content = response.content
                                if isinstance(content, dict):
                                    response_data = content
                                elif isinstance(content, (str, bytes)):
                                    response_data = json.loads(content if isinstance(content, str) else content.decode('utf-8'))
                                else:
                                    response_data = {}
                            else:
                                # Try to access as dict-like
                                try:
                                    response_data = dict(response)
                                except:
                                    response_data = {}
                            log.debug("Extracted from response object, keys: %s", list(response_data.keys()) if isinstance(response_data, dict) else "not a dict")
                        elif hasattr(response, "body_iterator"):
                            log.warning("Response appears to be streaming, cannot extract JSON directly")
                            response_data = {}
                        else:
                            log.warning("Unknown response type %s, cannot extract data. Response: %s", type(response).__name__, str(response)[:200])
                            response_data = {}
                    except Exception as e:
                        log.exception("Error extracting response data: %s", e)
                        response_data = {}
                
                log.info(
                    "Model response received: type=%s, has_choices=%s, choices_count=%d",
                    type(response_data).__name__,
                    "choices" in response_data,
                    len(response_data.get("choices", [])),
                )
                
                if "choices" in response_data and response_data["choices"]:
                    first_choice = response_data["choices"][0]
                    log.debug("First choice keys: %s", list(first_choice.keys()) if isinstance(first_choice, dict) else "not a dict")
                    if isinstance(first_choice, dict) and "message" in first_choice:
                        message = first_choice["message"]
                        log.debug("Message keys: %s", list(message.keys()))
                        tool_calls_in_message = message.get("tool_calls")
                        log.info(
                            "Message analysis: has_content=%s, content_length=%d, has_tool_calls=%s, tool_calls_count=%d",
                            bool(message.get("content")),
                            len(message.get("content", "")),
                            bool(tool_calls_in_message),
                            len(tool_calls_in_message) if tool_calls_in_message else 0,
                        )
                else:
                    log.warning("Response has no 'choices' field or choices is empty. Response structure: %s", list(response_data.keys())[:10])

            except Exception as e:
                error_msg = str(e)
                # Check if it's an HTTPException (from FastAPI/HTTP errors)
                if hasattr(e, "status_code"):
                    status_code = e.status_code
                    detail = getattr(e, "detail", error_msg)
                    if status_code == 504:
                        error_msg = f"Ollama server timeout (504): The server at the configured Ollama endpoint is not responding. Please check your Ollama server connection."
                    elif status_code == 503:
                        error_msg = f"Ollama server unavailable (503): The server is temporarily unavailable."
                    elif status_code == 500:
                        error_msg = f"Ollama server error (500): {detail}"
                    else:
                        error_msg = f"HTTP {status_code}: {detail}"
                elif "504" in error_msg or "Gateway Timeout" in error_msg or "timeout" in error_msg.lower():
                    error_msg = f"Ollama server timeout: The server is not responding. Please check your Ollama server connection and try again."
                elif "Connection" in error_msg or "connection" in error_msg.lower():
                    error_msg = f"Connection error: Unable to connect to Ollama server. Please verify the server is running and accessible."
                
                log.exception("Error calling model %s (iteration %d): %s", mcp_request.model_id, workflow_state.iteration_count, e)
                workflow_state.error = f"Model call failed: {error_msg}"
                break

            # Extract assistant message and tool calls
            if not response_data.get("choices"):
                log.error("No choices in response_data. Full response: %s", str(response_data)[:500])
                workflow_state.error = "Model returned no choices in response"
                break
                
            assistant_message = response_data.get("choices", [{}])[0].get("message", {})
            if not assistant_message:
                log.error("No message in first choice. Choice structure: %s", str(response_data.get("choices", [{}])[0])[:500])
                workflow_state.error = "Model returned no message in response"
                break
                
            assistant_content = assistant_message.get("content", "")
            tool_calls = assistant_message.get("tool_calls", [])
            
            log.info(
                "Extracted assistant message: content_length=%d, tool_calls=%d, message_keys=%s",
                len(assistant_content) if assistant_content else 0,
                len(tool_calls) if tool_calls else 0,
                list(assistant_message.keys()),
            )
            if assistant_content:
                log.debug("Assistant content preview: %s", assistant_content[:200])
            if not tool_calls:
                log.warning("No tool calls in response. Model may not be recognizing tools or may need different prompting.")
                if assistant_content:
                    log.info("Model response content: %s", assistant_content[:500])

            # Add assistant message to conversation
            messages.append({"role": "assistant", "content": assistant_content, "tool_calls": tool_calls})

            # Execute tool calls
            if tool_calls:
                for tool_call_data in tool_calls:
                    tool_call_id = tool_call_data.get("id", "")
                    function_name = tool_call_data.get("function", {}).get("name", "")
                    function_args_str = tool_call_data.get("function", {}).get("arguments", "{}")

                    try:
                        function_args = json.loads(function_args_str) if isinstance(function_args_str, str) else function_args_str
                    except json.JSONDecodeError:
                        log.warning("Failed to parse tool call arguments: %s", function_args_str)
                        function_args = {}

                    tool_call = ToolCall(tool_name=function_name, arguments=function_args)
                    
                    log.info(
                        "Executing tool: %s (iteration %d, tool_call_id: %s)",
                        function_name,
                        workflow_state.iteration_count,
                        tool_call_id[:20] if tool_call_id else "none",
                    )
                    log.debug("Tool %s arguments: %s", function_name, json.dumps(function_args, default=str)[:500])

                    # Execute tool
                    try:
                        if function_name == "google_ai_mode":
                            log.debug("Calling Google AI Mode tool")
                            result = tools["google_ai_mode"].call(**function_args)
                            log.info("Google AI Mode tool completed: has_text_blocks=%s", bool(result.get("text_blocks")))
                        elif function_name == "google_flight_calendar":
                            log.debug(
                                "Calling Google Flight Calendar: %s -> %s, dates=%s to %s",
                                function_args.get("departure_id"),
                                function_args.get("arrival_id"),
                                function_args.get("outbound_date_start"),
                                function_args.get("outbound_date_end"),
                            )
                            result = tools["google_flight_calendar"].call(**function_args)
                            calendar_entries = result.get("calendar", [])
                            log.info(
                                "Google Flight Calendar tool completed: %d calendar entries",
                                len(calendar_entries) if isinstance(calendar_entries, list) else 0,
                            )
                        elif function_name == "google_flight_search":
                            # Add auto_search_id and store_results flag
                            function_args["auto_search_id"] = auto_search_id
                            function_args["store_results"] = True
                            log.debug(
                                "Calling Google Flight Search: %s -> %s, outbound=%s, return=%s, airlines=%s",
                                function_args.get("departure_id"),
                                function_args.get("arrival_id"),
                                function_args.get("outbound_date"),
                                function_args.get("return_date"),
                                function_args.get("included_airlines"),
                            )
                            result = tools["google_flight_search"].call(**function_args)
                            stored_count = result.get("stored_count", 0)
                            total_flights = result.get("total_count", 0)
                            workflow_state.saved_flight_count += stored_count
                            log.info(
                                "Google Flight Search tool completed: total_flights=%d, stored=%d, cumulative_stored=%d",
                                total_flights,
                                stored_count,
                                workflow_state.saved_flight_count,
                            )
                        else:
                            log.warning("Unknown tool requested: %s", function_name)
                            result = {"error": f"Unknown tool: {function_name}"}

                        tool_call.result = result
                        workflow_state.tool_calls.append(tool_call)

                        # Add tool result to messages
                        # Include function_name for Google AI compatibility
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "function_name": function_name,  # Store for Google AI conversion
                                "content": json.dumps(result, default=str),
                            }
                        )

                        log.info("Tool call %s completed successfully", function_name)

                    except Exception as e:
                        log.exception("Error executing tool %s: %s", function_name, e)
                        tool_call.error = str(e)
                        workflow_state.tool_calls.append(tool_call)

                        # Add error to messages
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "function_name": function_name,  # Store for Google AI conversion
                                "content": json.dumps({"error": str(e)}, default=str),
                            }
                        )

            # Check completion criteria
            if workflow_state.saved_flight_count >= 3:  # Found at least 3 flights
                workflow_state.is_complete = True
                workflow_state.completion_reason = f"Found {workflow_state.saved_flight_count} flights"
                log.info(
                    "Workflow completion criteria met: saved_flight_count=%d >= 3",
                    workflow_state.saved_flight_count,
                )
            elif not tool_calls and assistant_content:
                # Model finished without tool calls
                workflow_state.is_complete = True
                workflow_state.completion_reason = "Model completed workflow"
                log.info("Model completed workflow without tool calls (iteration %d)", workflow_state.iteration_count)
            elif workflow_state.iteration_count >= workflow_state.max_iterations:
                log.warning(
                    "Workflow reached max iterations (%d) without completion. Saved flights: %d",
                    workflow_state.max_iterations,
                    workflow_state.saved_flight_count,
                )

    except Exception as e:
        log.exception("Error in MCP workflow (iteration %d): %s", workflow_state.iteration_count, e)
        workflow_state.error = str(e)

    # Build response
    success = workflow_state.error is None and workflow_state.is_complete
    message = (
        f"Workflow completed. Found {workflow_state.saved_flight_count} flights."
        if success
        else f"Workflow failed: {workflow_state.error or 'Unknown error'}"
    )
    
    log.info(
        "MCP workflow finished: success=%s, flights_saved=%d, tool_calls=%d, iterations=%d, reason=%s",
        success,
        workflow_state.saved_flight_count,
        len(workflow_state.tool_calls),
        workflow_state.iteration_count,
        workflow_state.completion_reason or workflow_state.error or "unknown",
    )

    return MCPResponse(
        success=success,
        message=message,
        saved_flight_count=workflow_state.saved_flight_count,
        tool_calls=workflow_state.tool_calls,
        error=workflow_state.error,
        workflow_state=workflow_state,
    )

