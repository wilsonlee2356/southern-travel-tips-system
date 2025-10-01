"""
Middleware to handle adapter model interception for OpenWebUI.
This allows the frontend to specify which adapter should be used when calling qwen2.5:14b.
"""

import logging
import json
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger(__name__)

class AdapterInterceptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts requests and extracts adapter selection information.
    When a user selects an adapter in the frontend, this middleware captures that information
    and makes it available for model interception in the Ollama router.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Initialize adapter info in request state
        if not hasattr(request.state, 'selected_adapter'):
            request.state.selected_adapter = None
        
        # Check if this is a chat completion request with adapter information
        if request.url.path == "/api/v1/chat/completions":
            try:
                # Read the request body to check for adapter information
                body = await request.body()
                if body:
                    try:
                        payload = json.loads(body.decode('utf-8'))
                        
                        # Check for adapter information in the payload
                        if 'metadata' in payload and payload['metadata']:
                            metadata = payload['metadata']
                            
                            # Look for adapter selection in metadata
                            if 'adapter_info' in metadata:
                                adapter_info = metadata['adapter_info']
                                request.state.selected_adapter = adapter_info
                                log.info(f"🔧 ADAPTER MIDDLEWARE: Adapter info captured!")
                                log.info(f"   📋 Adapter details: {adapter_info}")
                                log.info(f"   🎯 Will intercept qwen2.5:14b calls")
                            
                            # Also check for model-specific adapter info
                            elif 'selected_adapter' in metadata:
                                adapter_info = metadata['selected_adapter']
                                request.state.selected_adapter = adapter_info
                                log.info(f"🔧 ADAPTER MIDDLEWARE: Adapter info captured from metadata!")
                                log.info(f"   📋 Adapter details: {adapter_info}")
                                log.info(f"   🎯 Will intercept qwen2.5:14b calls")
                    
                    except json.JSONDecodeError:
                        # If JSON parsing fails, continue without adapter info
                        pass
                    except Exception as e:
                        log.warning(f"⚠️ Adapter middleware error: {e}")
                        pass
                
                # Reconstruct the request with the body for further processing
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive
                
            except Exception as e:
                log.warning(f"⚠️ Adapter middleware body reading error: {e}")
        
        # Continue with the request
        response = await call_next(request)
        return response
