"""AI Auto Flight Search MCP Integration

This module provides MCP (Model Context Protocol) integration for automated
flight search using AI agents. The AI can use three tools:
1. Google AI Mode - for getting initial insights about cheap periods
2. Google Flight Calendar - for getting price overviews
3. Google Flight Search - for getting detailed flight data and storing in DB
"""

from open_webui.ai_auto.workflow import run_mcp_workflow
from open_webui.ai_auto.context import (
    MCPRequest,
    MCPResponse,
    ToolCall,
    WorkflowState,
)

__all__ = [
    "run_mcp_workflow",
    "MCPRequest",
    "MCPResponse",
    "ToolCall",
    "WorkflowState",
]

