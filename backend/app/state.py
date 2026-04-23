from __future__ import annotations

from typing import Any, TypedDict
from langchain_core.messages import AnyMessage

from .schemas import InteractionFormState, ToolEvent


class AgentState(TypedDict, total=False):
    messages: list[AnyMessage]
    ui_state: InteractionFormState
    tool_events: list[ToolEvent]
    last_user_message: str
    pending_tool_calls: list[dict[str, Any]]
    assistant_message: str
