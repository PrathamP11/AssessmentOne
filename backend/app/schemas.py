from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


Sentiment = Literal["", "positive", "neutral", "negative"]


class SampleItem(BaseModel):
    name: str
    quantity: str = "1 unit"


class InteractionFormState(BaseModel):
    hcp_name: str = ""
    interaction_type: str = "Meeting"
    date: str = ""
    time: str = ""
    attendees: list[str] = Field(default_factory=list)
    topics_discussed: str = ""
    materials_shared: list[str] = Field(default_factory=list)
    samples_distributed: list[SampleItem] = Field(default_factory=list)
    sentiment: Sentiment = "neutral"
    outcomes: str = ""
    follow_up_actions: str = ""
    ai_suggested_follow_ups: list[str] = Field(default_factory=list)
    compliance_notes: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class AgentRequest(BaseModel):
    message: str
    form_state: InteractionFormState
    history: list[ChatMessage] = Field(default_factory=list)


class ToolEvent(BaseModel):
    name: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    assistant_message: str
    form_state: InteractionFormState
    tool_events: list[ToolEvent] = Field(default_factory=list)


class SaveInteractionRequest(BaseModel):
    form_state: InteractionFormState


class SavedInteractionResponse(BaseModel):
    id: int
    message: str
    form_state: InteractionFormState


class InteractionListItem(BaseModel):
    id: int
    hcp_name: str
    interaction_type: str
    date: str
    time: str
    sentiment: Sentiment
