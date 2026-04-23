from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from .config import get_settings
from .schemas import AgentResponse, ChatMessage, InteractionFormState
from .state import AgentState
from .tools import fallback_process, get_tool_registry, to_json


SYSTEM_PROMPT = """
You are an AI-first CRM copilot for life sciences field representatives.

Your job:
- Control the interaction form only through tool calls.
- Decide which tool to use based on the user's natural language request.
- Prefer tool usage whenever the user provides interaction details, corrections, materials, samples, or asks for next steps.
- After tools run, summarize what changed in a concise, professional assistant response.

Available tools:
1. log_interaction: extract and populate a new interaction from free text.
2. edit_interaction: correct previously captured fields without overwriting unrelated data.
3. add_materials: append materials shared or content assets discussed.
4. add_sample: record product samples distributed.
5. suggest_follow_ups: create suggested next actions for the rep.
"""


def _build_llm() -> ChatGroq | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
    )


def _build_tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "log_interaction",
                "description": "Log a new HCP interaction from a user's natural language summary.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": "The rep's interaction note."}
                    },
                    "required": ["instruction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_interaction",
                "description": "Edit specific fields already present in the form using the rep's correction.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": "The correction to apply."}
                    },
                    "required": ["instruction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_materials",
                "description": "Capture materials shared such as brochures, PDFs, leave-behinds, or links.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": "Details about materials shared."}
                    },
                    "required": ["instruction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_sample",
                "description": "Capture sample distribution details like product name and quantity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": "Details about distributed samples."}
                    },
                    "required": ["instruction"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "suggest_follow_ups",
                "description": "Generate recommended next steps for the field rep after the interaction.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": "Context for follow-up suggestions."}
                    },
                    "required": ["instruction"],
                },
            },
        },
    ]


def _assistant_router(state: AgentState) -> AgentState:
    llm = _build_llm()
    if llm is None:
        ui_state, events, assistant = fallback_process(state["ui_state"], state["last_user_message"])
        return {
            "ui_state": ui_state,
            "tool_events": events,
            "assistant_message": assistant,
            "pending_tool_calls": [],
        }

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT
            + "\nCurrent form state:\n"
            + state["ui_state"].model_dump_json(indent=2)
        )
    ]
    messages.extend(state.get("messages", []))
    bound_llm = llm.bind(tools=_build_tool_specs(), tool_choice="auto")
    reply = bound_llm.invoke(messages)
    pending = []
    raw_calls = reply.tool_calls or reply.additional_kwargs.get("tool_calls", [])
    for call in raw_calls:
        args = call.get("args")
        if args is None:
            args = json.loads(call["function"]["arguments"])
        pending.append(
            {
                "id": call["id"],
                "name": call.get("name") or call["function"]["name"],
                "args": args,
            }
        )
    return {
        "messages": state.get("messages", []) + [reply],
        "pending_tool_calls": pending,
    }


def _has_tool_calls(state: AgentState) -> str:
    return "tools" if state.get("pending_tool_calls") else "respond"


def _tool_executor(state: AgentState) -> AgentState:
    llm = _build_llm()
    registry = get_tool_registry(llm)
    ui_state = state["ui_state"]
    tool_events = list(state.get("tool_events", []))
    new_messages = list(state.get("messages", []))

    for call in state.get("pending_tool_calls", []):
        handler = registry.get(call["name"])
        if not handler:
            continue
        ui_state, event = handler(ui_state, call["args"]["instruction"])
        tool_events.append(event)
        new_messages.append(
            ToolMessage(
                tool_call_id=call["id"],
                content=to_json(
                    {
                        "summary": event.summary,
                        "payload": event.payload,
                        "ui_state": ui_state.model_dump(),
                    }
                ),
            )
        )

    return {
        "ui_state": ui_state,
        "tool_events": tool_events,
        "messages": new_messages,
        "pending_tool_calls": [],
    }


def _response_node(state: AgentState) -> AgentState:
    if state.get("assistant_message"):
        return state

    llm = _build_llm()
    if llm is None:
        return {
            "assistant_message": "The form has been updated in demo mode.",
        }

    prompt_messages = [
        SystemMessage(
            content=(
                "You are a helpful CRM copilot. Summarize the tool actions in 2-4 sentences,"
                " confirm what was updated in the form, and suggest one useful next step."
            )
        ),
        HumanMessage(
            content=(
                "Updated form state:\n"
                + state["ui_state"].model_dump_json(indent=2)
                + "\n\nTool events:\n"
                + json.dumps([event.model_dump() for event in state.get("tool_events", [])], indent=2)
            )
        ),
    ]
    reply = llm.invoke(prompt_messages)
    return {
        "assistant_message": reply.content,
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("route_tools", _assistant_router)
    graph.add_node("run_tools", _tool_executor)
    graph.add_node("respond", _response_node)
    graph.set_entry_point("route_tools")
    graph.add_conditional_edges("route_tools", _has_tool_calls, {"tools": "run_tools", "respond": "respond"})
    graph.add_edge("run_tools", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def run_agent(
    message: str,
    form_state: InteractionFormState,
    history: list[ChatMessage],
) -> AgentResponse:
    compiled = build_graph()
    langchain_history = []
    for item in history:
        if item.role == "user":
            langchain_history.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            langchain_history.append(AIMessage(content=item.content))

    initial_state: AgentState = {
        "messages": langchain_history + [HumanMessage(content=message)],
        "ui_state": form_state,
        "tool_events": [],
        "last_user_message": message,
    }
    result = compiled.invoke(initial_state)
    return AgentResponse(
        assistant_message=result.get("assistant_message", "The interaction has been updated."),
        form_state=result.get("ui_state", form_state),
        tool_events=result.get("tool_events", []),
    )
