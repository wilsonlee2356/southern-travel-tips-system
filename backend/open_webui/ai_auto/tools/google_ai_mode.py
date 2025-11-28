"""Google AI Mode Tool for MCP"""

import json
import logging
import os
from typing import Any, Dict, Optional

import requests

from open_webui.utils.json_extractor import extract_json

log = logging.getLogger(__name__)

GOOGLE_AI_MODE_ENDPOINT = "https://www.searchapi.io/api/v1/search"
DEFAULT_ENGINE = "google_ai_mode"


class GoogleAiModeTool:
    """Tool for querying Google AI Mode to get insights about cheap flight periods"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_FLIGHTS_API_KEY") or os.environ.get("SEARCHAPI_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing SearchAPI key. Set GOOGLE_FLIGHTS_API_KEY or SEARCHAPI_KEY environment variable."
            )

    def call(
        self,
        query: str,
        location: Optional[str] = None,
        hl: str = "en",
        gl: str = "HK",
    ) -> Dict[str, Any]:
        """
        Call Google AI Mode API with a simple sentence query.

        Args:
            query: Simple sentence query (e.g., "Give me the cheapest 8 days return flights of CX from HKG to NGO in the next 6 months")
            location: Optional location string
            hl: Interface language
            gl: Geolocation country code

        Returns:
            Dict containing the AI Mode response with extracted JSON if available
        """
        params: Dict[str, Any] = {
            "engine": DEFAULT_ENGINE,
            "api_key": self.api_key,
            "q": query,
            "hl": hl,
            "gl": gl,
        }

        if location:
            params["location"] = location

        log.info("Calling Google AI Mode API with query (length: %d)", len(query))
        log.debug("Google AI Mode query: %s", query[:200] if len(query) > 200 else query)
        log.debug("Google AI Mode params: %s", {k: v for k, v in params.items() if k != "api_key"})

        try:
            response = requests.get(GOOGLE_AI_MODE_ENDPOINT, params=params, timeout=60)
            log.debug("Google AI Mode response status: %d", response.status_code)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
            log.debug("Google AI Mode response keys: %s", list(data.keys()))

            # Try to extract JSON from text_blocks if present
            if "text_blocks" in data:
                text_content = self._extract_text_from_blocks(data["text_blocks"])
                if text_content:
                    json_str = extract_json(text_content)
                    if json_str:
                        try:
                            parsed_json = json.loads(json_str)
                            data["extracted_json"] = parsed_json
                            log.info("Extracted JSON from Google AI Mode response")
                        except json.JSONDecodeError:
                            log.warning("Failed to parse extracted JSON from Google AI Mode")

            log.info("Google AI Mode response received (text_blocks: %d)", len(data.get("text_blocks", [])))
            
            # Log full response (truncated if too long)
            response_str = json.dumps(data, default=str, indent=2)
            if len(response_str) > 2000:
                log.info("Google AI Mode Response (truncated): %s...", response_str[:2000])
                log.debug("Google AI Mode Response (full): %s", response_str)
            else:
                log.info("Google AI Mode Response: %s", response_str)
            
            return data

        except requests.RequestException as e:
            log.error("Google AI Mode request failed: %s", e)
            raise RuntimeError(f"Google AI Mode request failed: {str(e)}") from e

    def _extract_text_from_blocks(self, text_blocks: list) -> str:
        """Extract plain text from Google AI Mode text_blocks structure"""
        if not isinstance(text_blocks, list):
            return ""

        segments = []
        for block in text_blocks:
            if isinstance(block, dict):
                if "answer" in block and isinstance(block["answer"], str):
                    segments.append(block["answer"])
                if "items" in block and isinstance(block["items"], list):
                    for item in block["items"]:
                        if isinstance(item, dict) and "answer" in item:
                            segments.append(item["answer"])

        return "\n".join(segments)

