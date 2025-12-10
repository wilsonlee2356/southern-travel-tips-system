"""MCP Workflow Orchestrator"""

import json
import logging
import re
import time
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
                "description": "Get initial insights about cheap flight periods using Google AI Mode. You MUST use this EXACT query format: 'Give me the cheapest {day_number} days return flights of {airline} from {departure_airport} to {arrival_airport} in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time'. Only change day_number, airline, departure_airport, and arrival_airport. Do NOT modify any other words or structure.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "MUST use this EXACT format (only change variables): 'Give me the cheapest {day_number} days return flights of {airline} from {departure_airport} to {arrival_airport} in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time'. Example: 'Give me the cheapest 8 days return flights of CX from HKG to NGO in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time'",
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
                "description": "MANDATORY: Get real flight data using Google Flight Search API and AUTOMATICALLY save results to database. This is the ONLY tool that saves data. When you call this tool, it AUTOMATICALLY saves all cheap flights it finds - you do NOT need to ask the user for permission. You MUST call this with specific dates (YYYY-MM-DD format) extracted from google_ai_mode results. Call it for ALL promising dates to save as many cheap flights as possible. Simply summarizing google_ai_mode results is NOT enough - you must call this tool to actually save flights.",
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
        {
            "type": "function",
            "function": {
                "name": "finish_workflow",
                "description": "Call this tool when you have completed the flight search workflow. Use this when you have found enough flights, exhausted reasonable search options, or determined that no more searches are needed. This will end the workflow.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Brief reason for finishing the workflow (e.g., 'Found sufficient cheap flights', 'Exhausted search options', 'No flights found matching criteria')",
                        },
                        "summary": {
                            "type": "string",
                            "description": "Optional summary of what was accomplished (e.g., 'Found 5 cheap flights for CX from HKG to NGO')",
                        },
                    },
                    "required": ["reason"],
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
            # Use "required" tool_choice on first iteration to force the model to use tools
            # After that, use "auto" to let the model decide
            tool_choice = "required" if workflow_state.iteration_count == 1 else "auto"
            
            form_data = {
                "model": mcp_request.model_id,
                "messages": messages,
                "tools": tools_schema,
                "tool_choice": tool_choice,  # Force tool use on first iteration
                "stream": False,
                "temperature": 0.7,
            }
            
            log.debug("Tool choice for iteration %d: %s", workflow_state.iteration_count, tool_choice)

            # Call model
            call_start_time = None
            try:
                call_start_time = time.time()
                
                # Calculate total message size for logging
                total_message_size = sum(len(json.dumps(m, default=str)) for m in messages)
                log.info(
                    "Calling model %s (iteration %d, message count: %d, total message size: %d bytes, tools: %d)",
                    mcp_request.model_id,
                    workflow_state.iteration_count,
                    len(messages),
                    total_message_size,
                    len(tools_schema),
                )
                if total_message_size > 100000:  # > 100KB
                    log.warning(
                        "Large message context detected (%d bytes). This may cause slow responses with reasoning models. Consider using a faster model or reducing context size.",
                        total_message_size,
                    )
                log.debug("Form data keys: %s", list(form_data.keys()))
                log.debug("Tools schema: %s", [t.get("function", {}).get("name") for t in tools_schema])
                
                response = await generate_chat_completion(request, form_data, user, bypass_filter=True)
                
                call_duration = time.time() - call_start_time
                log.info(
                    "Model call completed in %.2f seconds (iteration %d)",
                    call_duration,
                    workflow_state.iteration_count,
                )
                
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
                
                # Log full AI response (truncated if too long)
                response_str = json.dumps(response_data, default=str, indent=2)
                if len(response_str) > 2000:
                    log.info("AI Model Response (truncated): %s...", response_str[:2000])
                    log.debug("AI Model Response (full): %s", response_str)
                else:
                    log.info("AI Model Response: %s", response_str)
                
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
                        # Log tool calls details if present
                        if tool_calls_in_message:
                            for idx, tc in enumerate(tool_calls_in_message):
                                log.info(
                                    "Tool call %d: id=%s, function=%s, arguments=%s",
                                    idx,
                                    tc.get("id", "unknown"),
                                    tc.get("function", {}).get("name", "unknown"),
                                    tc.get("function", {}).get("arguments", "{}")[:500],
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
                        call_duration = time.time() - call_start_time if call_start_time else 0
                        error_msg = f"Ollama server timeout (504): The model took {call_duration:.1f}s to respond, but the server/gateway timed out. DeepSeek R1 models with reasoning can take 5-10+ minutes, especially with complex tool calls. If using a reverse proxy (nginx, etc.), increase timeout settings significantly: proxy_read_timeout 600s; proxy_connect_timeout 600s; proxy_send_timeout 600s; (or even 900s for very long reasoning). Also check Ollama server timeout settings."
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
                            # Validate and enforce the exact query template format
                            query = function_args.get("query", "")
                            log.debug("Google AI Mode query received: %s", query[:200] if len(query) > 200 else query)
                            
                            # Check if query matches the required template pattern
                            # Template: "Give me the cheapest {day_number} days return flights of {airline} from {departure_airport} to {arrival_airport} in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time"
                            required_parts = [
                                "Give me the cheapest",
                                "days return flights of",
                                "from",
                                "to",
                                "in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time"
                            ]
                            
                            query_lower = query.lower()
                            matches_template = all(part.lower() in query_lower for part in required_parts)
                            
                            if not matches_template:
                                log.warning(
                                    "Google AI Mode query does not match required template. Received: %s. Reformatting to match template.",
                                    query[:200],
                                )
                                # Extract variables from query if possible, otherwise use defaults
                                day_match = re.search(r'(\d+)\s*days?', query, re.IGNORECASE)
                                airline_match = re.search(r'flights?\s+of\s+([A-Z]{2,3})', query, re.IGNORECASE)
                                dep_match = re.search(r'from\s+([A-Z]{3})', query, re.IGNORECASE)
                                arr_match = re.search(r'to\s+([A-Z]{3})', query, re.IGNORECASE)
                                
                                day_number = day_match.group(1) if day_match else (str(mcp_request.return_trip_days) if mcp_request.return_trip_days else "8")
                                airline = airline_match.group(1) if airline_match else (mcp_request.airlines[0] if mcp_request.airlines else "CX")
                                departure_airport = dep_match.group(1) if dep_match else mcp_request.departure
                                arrival_airport = arr_match.group(1) if arr_match else mcp_request.destination
                                
                                # Reformat to exact template
                                query = f"Give me the cheapest {day_number} days return flights of {airline} from {departure_airport} to {arrival_airport} in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time"
                                function_args["query"] = query
                                log.info("Reformatted Google AI Mode query to match template: %s", query)
                            
                            log.debug("Calling Google AI Mode tool with validated query")
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
                            # Clean up empty parameters that might cause API errors
                            # Remove excluded_airlines if it's empty or None
                            if not function_args.get("excluded_airlines") or not str(function_args.get("excluded_airlines", "")).strip():
                                function_args.pop("excluded_airlines", None)
                            
                            # Add auto_search_id and store_results flag
                            function_args["auto_search_id"] = auto_search_id
                            function_args["store_results"] = True
                            log.debug(
                                "Calling Google Flight Search: %s -> %s, outbound=%s, return=%s, airlines=%s, non_stop=%s",
                                function_args.get("departure_id"),
                                function_args.get("arrival_id"),
                                function_args.get("outbound_date"),
                                function_args.get("return_date"),
                                function_args.get("included_airlines"),
                                function_args.get("non_stop"),
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
                        elif function_name == "finish_workflow":
                            # Handle workflow completion tool
                            reason = function_args.get("reason", "Workflow completed by AI")
                            summary = function_args.get("summary", "")
                            log.info(
                                "AI requested workflow completion: reason=%s, summary=%s",
                                reason,
                                summary,
                            )
                            workflow_state.is_complete = True
                            workflow_state.completion_reason = f"AI completed workflow: {reason}"
                            if summary:
                                workflow_state.completion_reason += f" ({summary})"
                            result = {
                                "status": "success",
                                "message": "Workflow completed successfully",
                                "reason": reason,
                                "summary": summary,
                                "saved_flight_count": workflow_state.saved_flight_count,
                            }
                            log.info(
                                "Workflow marked as complete by AI. Saved flights: %d",
                                workflow_state.saved_flight_count,
                            )
                        else:
                            log.warning("Unknown tool requested: %s", function_name)
                            result = {"error": f"Unknown tool: {function_name}"}

                        # Log full tool response (truncated if too long)
                        result_str = json.dumps(result, default=str, indent=2)
                        if len(result_str) > 3000:
                            log.info("Tool '%s' Response (truncated): %s...", function_name, result_str[:3000])
                            log.debug("Tool '%s' Response (full): %s", function_name, result_str)
                        else:
                            log.info("Tool '%s' Response: %s", function_name, result_str)

                        tool_call.result = result
                        workflow_state.tool_calls.append(tool_call)

                        # Prepare tool result for messages - truncate very large responses to reduce context size
                        # This helps with reasoning models that take too long with large contexts
                        result_for_message = result
                        result_json_str = json.dumps(result, default=str)
                        
                        # If result is very large (>50KB), create a summary instead
                        MAX_TOOL_RESULT_SIZE = 50000  # 50KB limit
                        if len(result_json_str) > MAX_TOOL_RESULT_SIZE:
                            log.warning(
                                "Tool '%s' response is very large (%d bytes), creating summary for message context",
                                function_name,
                                len(result_json_str),
                            )
                            # Create a summary with key information
                            if function_name == "google_ai_mode":
                                summary = {
                                    "status": "success",
                                    "text_blocks_count": len(result.get("text_blocks", [])),
                                    "has_extracted_json": "extracted_json" in result,
                                    "summary": "Large response received. Use google_flight_calendar and google_flight_search for real data.",
                                }
                            elif function_name == "google_flight_calendar":
                                calendar_entries = result.get("calendar", [])
                                summary = {
                                    "status": "success",
                                    "calendar_entries_count": len(calendar_entries) if isinstance(calendar_entries, list) else 0,
                                    "summary": f"Received {len(calendar_entries) if isinstance(calendar_entries, list) else 0} calendar entries with price data.",
                                }
                            elif function_name == "google_flight_search":
                                summary = {
                                    "status": "success",
                                    "total_count": result.get("total_count", 0),
                                    "stored_count": result.get("stored_count", 0),
                                    "summary": f"Found {result.get('total_count', 0)} flights, stored {result.get('stored_count', 0)} in database.",
                                }
                            else:
                                summary = {
                                    "status": "success",
                                    "summary": "Large response received. Check logs for full details.",
                                }
                            result_for_message = summary
                            log.info("Created summary for tool '%s' response: %s", function_name, json.dumps(summary, default=str))

                        # Add tool result to messages
                        # Include function_name for Google AI compatibility
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "function_name": function_name,  # Store for Google AI conversion
                                "content": json.dumps(result_for_message, default=str),
                            }
                        )
                        
                        # Log message size
                        message_content_size = len(json.dumps(result_for_message, default=str))
                        log.debug(
                            "Added tool result to messages: function=%s, content_size=%d bytes",
                            function_name,
                            message_content_size,
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

            # Check completion criteria (after tool execution)
            # Note: finish_workflow tool sets is_complete = True during execution
            
            # Check if google_flight_search has been called at least once
            has_called_flight_search = any(
                tc.tool_name == "google_flight_search" for tc in workflow_state.tool_calls
            )
            
            if workflow_state.is_complete:
                # Already completed (either by finish_workflow tool or automatic threshold)
                if not has_called_flight_search and workflow_state.saved_flight_count == 0:
                    log.warning(
                        "Workflow completed but google_flight_search was never called. No flights were saved. Completion reason: %s",
                        workflow_state.completion_reason,
                    )
                else:
                    log.info(
                        "Workflow completed: reason=%s, saved_flights=%d, flight_search_called=%s",
                        workflow_state.completion_reason,
                        workflow_state.saved_flight_count,
                        has_called_flight_search,
                    )
            elif workflow_state.saved_flight_count >= 3:  # Found at least 3 flights
                workflow_state.is_complete = True
                workflow_state.completion_reason = f"Found {workflow_state.saved_flight_count} flights (automatic threshold)"
                log.info(
                    "Workflow completion criteria met: saved_flight_count=%d >= 3",
                    workflow_state.saved_flight_count,
                )
            elif not tool_calls and assistant_content:
                # Model finished without tool calls
                if not has_called_flight_search:
                    log.warning(
                        "Model completed workflow without calling google_flight_search (iteration %d). No flights were saved. The AI should call google_flight_search with dates from google_ai_mode results.",
                        workflow_state.iteration_count,
                    )
                    # Don't complete - force the AI to call google_flight_search
                    # Add a message to remind the AI
                    messages.append({
                        "role": "user",
                        "content": "You have not called google_flight_search yet. You MUST call google_flight_search with specific dates from the google_ai_mode results to save flights. The goal is to SAVE flights, not just report on them. Please extract dates from the google_ai_mode results (e.g., 'Feb 3, 2026' → '2026-02-03') and call google_flight_search with those dates.",
                    })
                    log.info("Added reminder message to force AI to call google_flight_search")
                    # Continue the loop instead of completing
                    continue
                else:
                    # Model finished without tool calls but has called google_flight_search before
                    workflow_state.is_complete = True
                    workflow_state.completion_reason = "Model completed workflow without tool calls (legacy - should use finish_workflow tool)"
                    log.warning(
                        "Model completed workflow without tool calls (iteration %d). Consider using finish_workflow tool for explicit completion.",
                        workflow_state.iteration_count,
                    )
            elif workflow_state.iteration_count >= workflow_state.max_iterations:
                workflow_state.is_complete = True
                workflow_state.completion_reason = f"Reached max iterations ({workflow_state.max_iterations})"
                if not has_called_flight_search:
                    log.error(
                        "Workflow reached max iterations (%d) without calling google_flight_search. No flights were saved.",
                        workflow_state.max_iterations,
                    )
                else:
                    log.warning(
                        "Workflow reached max iterations (%d) without explicit completion. Saved flights: %d",
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

