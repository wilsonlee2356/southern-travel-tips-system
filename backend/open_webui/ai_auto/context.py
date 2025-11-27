"""Context models for MCP workflow"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """Represents a single tool call made by the AI"""

    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowState:
    """Tracks the state of the MCP workflow execution"""

    tool_calls: List[ToolCall] = field(default_factory=list)
    saved_flight_count: int = 0
    iteration_count: int = 0
    max_iterations: int = 20
    is_complete: bool = False
    completion_reason: Optional[str] = None
    error: Optional[str] = None
    auto_search_id: Optional[str] = None


@dataclass
class MCPRequest:
    """Request model for MCP workflow"""

    departure: str
    destination: str
    airlines: List[str]
    return_trip_days: Optional[int] = None  # Number of days for return trip
    travel_class: int = 0  # 0=economy, 1=premium_economy, 2=business, 3=first
    direct_flight: bool = False
    model_id: str = ""  # Selected model ID (Gemini, Ollama, or OpenAI)
    user_id: Optional[str] = None


@dataclass
class MCPResponse:
    """Response model for MCP workflow"""

    success: bool
    message: str
    saved_flight_count: int = 0
    tool_calls: List[ToolCall] = field(default_factory=list)
    error: Optional[str] = None
    workflow_state: Optional[WorkflowState] = None

