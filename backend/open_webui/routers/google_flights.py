import logging
import os
from urllib.parse import urlencode
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from starlette.requests import Request

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()

SEARCH_API_ENDPOINT = "https://www.searchapi.io/api/v1/search"


@router.get("/api/google-flights")
async def proxy_google_flights(
    request: Request,
    user=Depends(get_verified_user),
):
    """
    Proxy Google Flights API requests to SearchAPI.io
    This endpoint forwards all query parameters to SearchAPI.io and adds the API key
    """
    # Get API key from environment variables
    api_key = (
        os.environ.get("GOOGLE_FLIGHTS_API_KEY")
        or os.environ.get("SEARCHAPI_KEY")
        or os.environ.get("SERPAPI_API_KEY")
    )

    if not api_key:
        log.error("GOOGLE_FLIGHTS_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is not configured. Please set GOOGLE_FLIGHTS_API_KEY or SEARCHAPI_KEY in your environment.",
        )

    # Build query parameters
    query_params = {}
    
    # Add engine parameter (required by SearchAPI)
    query_params["engine"] = "google_flights"
    
    # Add API key
    query_params["api_key"] = api_key
    
    # Forward all client parameters (except api_key to prevent override)
    for key, value in request.query_params.items():
        if key != "api_key":  # Don't allow client to override server's API key
            query_params[key] = value

    # Build the SearchAPI URL
    search_api_url = f"{SEARCH_API_ENDPOINT}?{urlencode(query_params)}"
    log.info(f"Calling SearchAPI.io: {search_api_url.replace(api_key, '***')}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                search_api_url,
                headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if not response.ok:
                    error_text = await response.text()
                    try:
                        error_json = await response.json()
                        error_detail = error_json.get("error") or error_json.get("message") or error_text
                    except:
                        error_detail = error_text
                    
                    log.error(f"SearchAPI error: {error_detail}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=error_detail,
                    )

                data = await response.json()
                return data

    except aiohttp.ClientError as e:
        log.error(f"SearchAPI request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to SearchAPI: {str(e)}",
        )
    except Exception as e:
        log.error(f"Unexpected error in Google Flights proxy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )

