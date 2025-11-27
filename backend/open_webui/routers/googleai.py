import asyncio
import hashlib
import json
import logging
import time
from typing import Optional

import aiohttp
from aiocache import cached
import requests
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
    JSONResponse,
    PlainTextResponse,
)
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
)
from open_webui.env import (
    MODELS_CACHE_TTL,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
)
from open_webui.utils.models import get_all_models

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_GOOGLEAI_API": getattr(request.app.state.config, 'ENABLE_GOOGLEAI_API', False),
        "GOOGLEAI_API_KEYS": getattr(request.app.state.config, 'GOOGLEAI_API_KEYS', ['']),
        "GOOGLEAI_API_CONFIGS": getattr(request.app.state.config, 'GOOGLEAI_API_CONFIGS', {}),
    }


class GoogleAIConfigForm(BaseModel):
    ENABLE_GOOGLEAI_API: Optional[bool] = None
    GOOGLEAI_API_KEYS: list[str]
    GOOGLEAI_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: GoogleAIConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_GOOGLEAI_API = form_data.ENABLE_GOOGLEAI_API
    request.app.state.config.GOOGLEAI_API_KEYS = form_data.GOOGLEAI_API_KEYS
    request.app.state.config.GOOGLEAI_API_CONFIGS = form_data.GOOGLEAI_API_CONFIGS

    # Remove the API configs that are not in the API KEYS
    keys = list(map(str, range(len(request.app.state.config.GOOGLEAI_API_KEYS))))
    request.app.state.config.GOOGLEAI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.GOOGLEAI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_GOOGLEAI_API": request.app.state.config.ENABLE_GOOGLEAI_API,
        "GOOGLEAI_API_KEYS": request.app.state.config.GOOGLEAI_API_KEYS,
        "GOOGLEAI_API_CONFIGS": request.app.state.config.GOOGLEAI_API_CONFIGS,
    }


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str


@router.post("/verify")
async def verify_connection(
    form_data: ConnectionVerificationForm, user=Depends(get_admin_user)
):
    url = form_data.url
    key = form_data.key

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
    ) as session:
        try:
            # Test connection to Google AI Studio API
            # Google AI Studio API uses API key as query parameter, not Bearer token
            request_url = f"{url}/models?key={key}"
            async with session.get(
                request_url,
                headers={
                    "Content-Type": "application/json",
                    **(
                        {
                            "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS and user
                        else {}
                    ),
                },
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                if r.status != 200:
                    detail = f"HTTP Error: {r.status}"
                    try:
                        res = await r.json()
                        if "error" in res:
                            detail = f"External Error: {res['error']}"
                        log.error(f"Google AI API error {r.status}: {res}")
                    except:
                        try:
                            error_text = await r.text()
                            detail = f"External Error: {error_text}"
                            log.error(f"Google AI API error {r.status}: {error_text}")
                        except:
                            pass
                    raise Exception(detail)

                data = await r.json()
                return data
        except aiohttp.ClientError as e:
            log.exception(f"Client error: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Open WebUI: {str(e)}"
            )


@router.get("/urls")
async def get_urls(user=Depends(get_admin_user)):
    return {"urls": ["https://generativelanguage.googleapis.com/v1beta"]}


@router.post("/models")
async def get_models(
    request: Request, idx: int = 0, user=Depends(get_admin_user)
):
    try:
        # Get the API key and config for the specified index
        api_keys = getattr(request.app.state.config, 'GOOGLEAI_API_KEYS', [''])
        api_configs = getattr(request.app.state.config, 'GOOGLEAI_API_CONFIGS', {})
        
        if idx >= len(api_keys) or not api_keys[idx]:
            return {"models": [], "pipelines": False}

        api_key = api_keys[idx]
        config = api_configs.get(str(idx), {})
        
        # Check if this connection is enabled
        if not config.get('enable', True):
            return {"models": [], "pipelines": False}

        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as session:
            try:
                # Google AI Studio API uses API key as query parameter, not Bearer token
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                async with session.get(
                    url,
                    headers={
                        "Content-Type": "application/json",
                    },
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status != 200:
                        try:
                            error_data = await r.json()
                            log.error(f"Google AI API error {r.status}: {error_data}")
                        except:
                            try:
                                error_text = await r.text()
                                log.error(f"Google AI API error {r.status}: {error_text}")
                            except:
                                log.error(f"Google AI API error: {r.status}")
                        return {"models": [], "pipelines": False}

                    data = await r.json()
                    
                    # Transform Google AI models to OpenAI format
                    models = []
                    if 'models' in data:
                        for model in data['models']:
                            model_name = model.get('name', '')
                            # Filter out embedding models and other non-chat models
                            if 'generateContent' in model.get('supportedGenerationMethods', []):
                                models.append({
                                    "id": model_name,
                                    "name": model_name,
                                    "owned_by": "google",
                                    "googleai": {"id": model_name},
                                    "urlIdx": idx
                                })
                    
                    return {"models": models, "pipelines": False}
                    
            except aiohttp.ClientError as e:
                log.exception(f"Client error: {str(e)}")
                return {"models": [], "pipelines": False}
            except Exception as e:
                log.exception(f"Error: {str(e)}")
                return {"models": [], "pipelines": False}
                
    except Exception as e:
        log.exception(f"Error getting Google AI models: {str(e)}")
        return {"models": [], "pipelines": False}


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        params = model_info.params.model_dump()

        if params:
            system = params.pop("system", None)
            payload = apply_model_params_to_body_openai(params, payload)
            payload = apply_model_system_prompt_to_body(system, payload, metadata, user)

        # Check if user has access to the model
        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Model not found",
            )

    await get_all_models(request, user=user)
    
    model = request.app.state.GOOGLEAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        log.error(f"Google AI model not found: {model_id}")
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Get the API config for the model
    api_config = request.app.state.config.GOOGLEAI_API_CONFIGS.get(str(idx), {})

    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # Convert OpenAI format to Google AI format
    googleai_payload = convert_openai_to_googleai_payload(payload)
    

    api_key = request.app.state.config.GOOGLEAI_API_KEYS[idx]
    
    # Google AI Studio API uses API key as query parameter
    # Remove "models/" prefix if it exists since we're already including it in the URL
    model_name = payload['model']
    if model_name.startswith('models/'):
        model_name = model_name[7:]  # Remove "models/" prefix
    
    
    # Try the requested model first, but have fallbacks for common issues
    model_variations = [model_name]
    
    # Add fallback variations for common model naming issues
    if model_name == "gemini-2.5-flash":
        model_variations.extend(["gemini-2.0-flash", "gemini-1.5-flash"])
    elif model_name == "gemini-2.5-pro":
        model_variations.extend(["gemini-2.0-pro", "gemini-1.5-pro"])
    
    headers = {
        "Content-Type": "application/json",
        **(
            {
                "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                "X-OpenWebUI-User-Id": user.id,
                "X-OpenWebUI-User-Email": user.email,
                "X-OpenWebUI-User-Role": user.role,
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS and user
            else {}
        ),
    }

    payload_json = json.dumps(googleai_payload)

    r = None
    session = None
    streaming = False
    response = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        # Try each model variation until one works
        for i, test_model in enumerate(model_variations):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{test_model}:generateContent?key={api_key}"
                
                # Make the request
                r = await session.post(
                    url,
                    data=payload_json,
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                )
                
                if r.status == 200:
                    break
                elif i < len(model_variations) - 1:
                    continue
                else:
                    # This is the last variation, handle the error
                    if r.status != 200:
                        error_detail = f"Google AI API error: {r.status}"
                        try:
                            error_data = await r.json()
                            log.error(f"Google AI API error {r.status}: {error_data}")
                            if "error" in error_data:
                                error_detail = f"Google AI Error: {error_data['error'].get('message', 'Unknown error')}"
                            else:
                                error_detail = f"Google AI API Error: {error_data}"
                        except Exception as e:
                            try:
                                error_text = await r.text()
                                error_detail = f"Google AI Error: {error_text}"
                                log.error(f"Google AI API error {r.status}: {error_text}")
                            except Exception as e2:
                                error_detail = f"Google AI API Error: {r.status} - Failed to read response: {e2}"
                                log.error(f"Google AI API error {r.status}: Failed to read response - {e2}")
                        
                        log.error(f"Full request details - URL: {url}, Headers: {headers}, Payload: {payload_json}")
                        raise HTTPException(status_code=r.status, detail=error_detail)
            except Exception as e:
                if i < len(model_variations) - 1:
                    continue
                else:
                    raise e

        # For now, force non-streaming as Google AI streaming format might be different
        # TODO: Implement proper Google AI streaming support
        if False:  # payload.get("stream", False):
            streaming = True
            response = StreamingResponse(
                convert_googleai_stream_to_openai(r, payload['model']),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            # Non-streaming response
            response_data = await r.json()
            openai_response = convert_googleai_response_to_openai(response_data, form_data["model"])
            response = JSONResponse(content=openai_response)

    except aiohttp.ClientError as e:
        log.exception(f"Client error: {str(e)}")
        raise HTTPException(
            status_code=500, detail={"error": {"message": "Server Connection Error", "type": "connection_error"}}
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        log.exception(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": {"message": str(e), "type": "server_error"}})
    finally:
        if r:
            r.close()
        if session:
            await session.close()

    return response


def convert_openai_to_googleai_payload(payload):
    """Convert OpenAI chat completion payload to Google AI format"""
    messages = payload.get("messages", [])
    tools = payload.get("tools", [])
    
    # Convert messages to Google AI format
    googleai_messages = []
    for message in messages:
        if message["role"] == "system":
            # Google AI doesn't have system messages, convert to user message
            googleai_messages.append({
                "role": "user",
                "parts": [{"text": f"System: {message['content']}"}]
            })
        elif message["role"] == "user":
            googleai_messages.append({
                "role": "user", 
                "parts": [{"text": message["content"]}]
            })
        elif message["role"] == "assistant":
            parts = []
            # Add text content if present
            if message.get("content"):
                parts.append({"text": message["content"]})
            # Add function calls if present
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    function_call = tool_call.get("function", {})
                    parts.append({
                        "functionCall": {
                            "name": function_call.get("name", ""),
                            "args": json.loads(function_call.get("arguments", "{}")) if isinstance(function_call.get("arguments"), str) else function_call.get("arguments", {})
                        }
                    })
            if parts:
                googleai_messages.append({
                    "role": "model",
                    "parts": parts
                })
        elif message["role"] == "tool":
            # Google AI uses "functionResponse" for tool responses
            tool_call_id = message.get("tool_call_id", "")
            content = message.get("content", "")
            # Get function name from message metadata (added by workflow)
            function_name = message.get("function_name")
            
            # If not in metadata, try to find from previous messages
            if not function_name:
                for prev_msg in reversed(googleai_messages):
                    if prev_msg.get("role") == "model" and "parts" in prev_msg:
                        for part in prev_msg["parts"]:
                            if "functionCall" in part:
                                function_name = part["functionCall"].get("name")
                                if function_name:
                                    break
                        if function_name:
                            break
            
            if not function_name:
                log.warning("Could not find function name for tool response (tool_call_id=%s), using default", tool_call_id)
                function_name = "unknown_function"
            
            try:
                # Try to parse content as JSON
                function_response = json.loads(content) if isinstance(content, str) else content
            except:
                function_response = {"result": content}
            
            googleai_messages.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": function_name,
                        "response": function_response
                    }
                }]
            })
    
    # Build Google AI payload
    googleai_payload = {
        "contents": googleai_messages
    }
    
    # Convert tools to Google AI function declarations
    if tools:
        function_declarations = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                # Convert OpenAI function schema to Google AI format
                parameters = func.get("parameters", {})
                googleai_params = {
                    "type": parameters.get("type", "object"),
                    "properties": parameters.get("properties", {}),
                    "required": parameters.get("required", [])
                }
                
                function_declarations.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "parameters": googleai_params
                })
        
        if function_declarations:
            googleai_payload["tools"] = [{
                "functionDeclarations": function_declarations
            }]
            log.debug("Converted %d tools to Google AI function declarations", len(function_declarations))
    
    # Add generation config only if parameters are provided
    generation_config = {}
    if "temperature" in payload:
        generation_config["temperature"] = payload["temperature"]
    if "max_tokens" in payload:
        generation_config["maxOutputTokens"] = payload["max_tokens"]
    if "top_p" in payload:
        generation_config["topP"] = payload["top_p"]
    if "top_k" in payload:
        generation_config["topK"] = payload["top_k"]
    
    if generation_config:
        googleai_payload["generationConfig"] = generation_config
    
    return googleai_payload


def convert_googleai_response_to_openai(googleai_response, model_name):
    """Convert Google AI response to OpenAI format"""
    try:
        if "candidates" in googleai_response and len(googleai_response["candidates"]) > 0:
            candidate = googleai_response["candidates"][0]
            
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                
                # Extract text content and function calls
                content_parts = []
                tool_calls = []
                
                for part in parts:
                    if "text" in part:
                        content_parts.append(part["text"])
                    elif "functionCall" in part:
                        func_call = part["functionCall"]
                        tool_calls.append({
                            "id": f"call_{int(time.time() * 1000)}_{len(tool_calls)}",
                            "type": "function",
                            "function": {
                                "name": func_call.get("name", ""),
                                "arguments": json.dumps(func_call.get("args", {}))
                            }
                        })
                
                content = "".join(content_parts) if content_parts else None
                
                message = {
                    "role": "assistant"
                }
                if content:
                    message["content"] = content
                if tool_calls:
                    message["tool_calls"] = tool_calls
                
                finish_reason = candidate.get("finishReason", "stop").lower()
                # Google AI uses "FUNCTION_CALL" for function calling
                if finish_reason == "function_call":
                    finish_reason = "tool_calls"
                
                openai_response = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "message": message,
                            "finish_reason": finish_reason
                        }
                    ],
                    "usage": {
                        "prompt_tokens": googleai_response.get("usageMetadata", {}).get("promptTokenCount", 0),
                        "completion_tokens": googleai_response.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                        "total_tokens": googleai_response.get("usageMetadata", {}).get("totalTokenCount", 0)
                    }
                }
                
                if tool_calls:
                    log.debug("Converted Google AI response with %d function calls", len(tool_calls))
                
                return openai_response
            
    except Exception as e:
        log.exception(f"Error converting Google AI response: {e}")
    
    # Fallback response
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion", 
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Sorry, I encountered an error processing your request."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }


async def convert_googleai_stream_to_openai(response, model_name):
    """Convert Google AI streaming response to OpenAI format"""
    try:
        async for line in response.content:
            if line:
                line_text = line.decode('utf-8').strip()
                if line_text.startswith('data: '):
                    try:
                        data = json.loads(line_text[6:])
                        if "candidates" in data and len(data["candidates"]) > 0:
                            candidate = data["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                content = candidate["content"]["parts"][0]["text"]
                                
                                openai_chunk = {
                                    "id": f"chatcmpl-{int(time.time())}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": model_name,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"content": content},
                                            "finish_reason": None
                                        }
                                    ]
                                }
                                
                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                    except json.JSONDecodeError:
                        continue
                        
        # Send final chunk
        final_chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk", 
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        log.error(f"Error in streaming conversion: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
