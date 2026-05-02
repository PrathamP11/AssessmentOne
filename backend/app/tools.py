from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .schemas import InteractionFormState, SampleItem, ToolEvent


class InteractionExtraction(BaseModel):
    hcp_name: str = ""
    interaction_type: str = "Meeting"
    date: str = ""
    time: str = ""
    attendees: list[str] = Field(default_factory=list)
    topics_discussed: str = ""
    materials_shared: list[str] = Field(default_factory=list)
    samples_distributed: list[SampleItem] = Field(default_factory=list)
    sentiment: str = "neutral"
    outcomes: str = ""
    follow_up_actions: str = ""
    compliance_notes: list[str] = Field(default_factory=list)


class PartialInteractionUpdate(BaseModel):
    hcp_name: str = ""
    interaction_type: str = ""
    date: str = ""
    time: str = ""
    attendees: list[str] = Field(default_factory=list)
    topics_discussed: str = ""
    materials_shared: list[str] = Field(default_factory=list)
    samples_distributed: list[SampleItem] = Field(default_factory=list)
    sentiment: str = ""
    outcomes: str = ""
    follow_up_actions: str = ""
    compliance_notes: list[str] = Field(default_factory=list)


class FollowUpSuggestions(BaseModel):
    suggestions: list[str] = Field(default_factory=list)


def _clean_date(value: str) -> str:
    if not value:
        return datetime.now().strftime("%d-%m-%Y")
    return value


def _clean_time(value: str) -> str:
    if not value:
        return datetime.now().strftime("%H:%M")
    return value


def _normalize_sentiment(value: str) -> str:
    value = (value or "neutral").strip().lower()
    if value not in {"positive", "neutral", "negative"}:
        return "neutral"
    return value


def _merge_interaction(
    current_state: InteractionFormState,
    extracted: InteractionExtraction,
    overwrite_existing: bool,
) -> InteractionFormState:
    state = current_state.model_copy(deep=True)
    incoming = extracted.model_dump()

    for key, value in incoming.items():
        if key == "sentiment":
            value = _normalize_sentiment(value)
        if key == "date":
            value = _clean_date(value)
        if key == "time":
            value = _clean_time(value)

        current_value = getattr(state, key)
        if isinstance(value, list):
            if overwrite_existing and value:
                setattr(state, key, value)
            elif not overwrite_existing and value:
                if key == "samples_distributed":
                    merged = current_value + value
                else:
                    merged = list(dict.fromkeys(current_value + value))
                setattr(state, key, merged)
        elif isinstance(value, str):
            if value.strip():
                # Sentiment starts with a default value in the UI, so allow the
                # extracted value to replace that placeholder during first-time logging.
                if key == "sentiment" and value in {"positive", "neutral", "negative"}:
                    if overwrite_existing or current_value in {"", "neutral"}:
                        setattr(state, key, value)
                    continue
                if overwrite_existing or not str(current_value).strip():
                    setattr(state, key, value.strip())
        else:
            if value:
                setattr(state, key, value)

    if not state.date:
        state.date = _clean_date("")
    if not state.time:
        state.time = _clean_time("")
    return state


def _run_structured_llm(
    llm: Any,
    schema: type[BaseModel],
    system_text: str,
    human_text: str,
) -> BaseModel:
    parser = PydanticOutputParser(pydantic_object=schema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_text}\nReturn only valid JSON.\n{format_instructions}"),
            ("human", "{human_text}"),
        ]
    )
    chain = prompt | llm | parser
    return chain.invoke(
        {
            "system_text": system_text,
            "human_text": human_text,
            "format_instructions": parser.get_format_instructions(),
        }
    )


def log_interaction_tool(
    llm: Any,
    current_state: InteractionFormState,
    user_text: str,
) -> tuple[InteractionFormState, ToolEvent]:
    extracted = _run_structured_llm(
        llm=llm,
        schema=InteractionExtraction,
        system_text=(
            "You are a life sciences CRM assistant. Extract structured HCP interaction"
            " details from the rep's natural language note. Use dd-mm-yyyy for date when"
            " explicit, HH:MM 24-hour time when explicit, and only include facts present"
            " or strongly implied."
        ),
        human_text=f"Current form state:\n{current_state.model_dump_json(indent=2)}\n\nUser note:\n{user_text}",
    )
    updated = _merge_interaction(current_state, extracted, overwrite_existing=False)
    event = ToolEvent(
        name="log_interaction",
        summary="Captured interaction details from the conversation and filled the form.",
        payload=extracted.model_dump(),
    )
    return updated, event


def edit_interaction_tool(
    llm: Any,
    current_state: InteractionFormState,
    instruction: str,
) -> tuple[InteractionFormState, ToolEvent]:
    extracted = _run_structured_llm(
        llm=llm,
        schema=PartialInteractionUpdate,
        system_text=(
            "You update only the fields explicitly corrected by the sales rep. Leave fields"
            " blank when the instruction does not mention them. Return only the corrected"
            " values that should overwrite the existing form."
        ),
        human_text=f"Existing form:\n{current_state.model_dump_json(indent=2)}\n\nCorrection:\n{instruction}",
    )
    updated = _merge_interaction(current_state, extracted, overwrite_existing=True)
    event = ToolEvent(
        name="edit_interaction",
        summary="Updated the previously logged interaction using the correction provided.",
        payload=extracted.model_dump(),
    )
    return updated, event


def add_materials_tool(
    llm: Any,
    current_state: InteractionFormState,
    instruction: str,
) -> tuple[InteractionFormState, ToolEvent]:
    extracted = _run_structured_llm(
        llm=llm,
        schema=InteractionExtraction,
        system_text=(
            "Extract only materials shared and optionally topics/outcomes if the user"
            " mentions them. Use materials_shared as a list of concise items."
        ),
        human_text=f"Form state:\n{current_state.model_dump_json(indent=2)}\n\nInstruction:\n{instruction}",
    )
    updated = _merge_interaction(current_state, extracted, overwrite_existing=False)
    event = ToolEvent(
        name="add_materials",
        summary="Added materials shared details for the HCP visit.",
        payload={"materials_shared": extracted.materials_shared},
    )
    return updated, event


def add_sample_tool(
    llm: Any,
    current_state: InteractionFormState,
    instruction: str,
) -> tuple[InteractionFormState, ToolEvent]:
    extracted = _run_structured_llm(
        llm=llm,
        schema=InteractionExtraction,
        system_text=(
            "Extract only samples distributed from the note. Each sample should include"
            " a product name and quantity string."
        ),
        human_text=f"Form state:\n{current_state.model_dump_json(indent=2)}\n\nInstruction:\n{instruction}",
    )
    updated = _merge_interaction(current_state, extracted, overwrite_existing=False)
    event = ToolEvent(
        name="add_sample",
        summary="Recorded the sample distribution discussed in chat.",
        payload={"samples_distributed": [item.model_dump() for item in extracted.samples_distributed]},
    )
    return updated, event


def suggest_follow_ups_tool(
    llm: Any,
    current_state: InteractionFormState,
    instruction: str,
) -> tuple[InteractionFormState, ToolEvent]:
    suggestions = _run_structured_llm(
        llm=llm,
        schema=FollowUpSuggestions,
        system_text=(
            "You are a CRM copilot for pharma field reps. Suggest 3 short, useful,"
            " compliant next-step follow-ups based on the latest HCP interaction and"
            " the user's request."
        ),
        human_text=(
            f"Interaction state:\n{current_state.model_dump_json(indent=2)}\n\n"
            f"Rep request:\n{instruction}"
        ),
    )
    updated = current_state.model_copy(deep=True)
    updated.ai_suggested_follow_ups = suggestions.suggestions
    event = ToolEvent(
        name="suggest_follow_ups",
        summary="Generated AI follow-up suggestions for the sales rep.",
        payload={"ai_suggested_follow_ups": suggestions.suggestions},
    )
    return updated, event


def fallback_process(
    current_state: InteractionFormState,
    user_text: str,
) -> tuple[InteractionFormState, list[ToolEvent], str]:
    state = current_state.model_copy(deep=True)
    normalized = user_text.lower()
    events: list[ToolEvent] = []

    if "dr." in user_text.lower() and not state.hcp_name:
        start = normalized.index("dr.")
        state.hcp_name = user_text[start:].split(" and ")[0].split(",")[0].strip().rstrip(".")

    if "positive" in normalized:
        state.sentiment = "positive"
    elif "negative" in normalized:
        state.sentiment = "negative"
    elif "neutral" in normalized:
        state.sentiment = "neutral"

    if "today" in normalized or not state.date:
        state.date = datetime.now().strftime("%d-%m-%Y")
    if not state.time:
        state.time = datetime.now().strftime("%H:%M")

    if "discussed" in normalized:
        state.topics_discussed = user_text
    if "brochure" in normalized:
        state.materials_shared = list(dict.fromkeys(state.materials_shared + ["Brochure"]))
    if "sample" in normalized:
        state.samples_distributed.append(SampleItem(name="Product sample", quantity="1 unit"))

    state.ai_suggested_follow_ups = [
        "Schedule a follow-up meeting in 2 weeks",
        "Share the relevant product PDF",
        "Prepare a response to the HCP's open questions",
    ]
    events.append(
        ToolEvent(
            name="fallback_demo_mode",
            summary="Applied a lightweight demo-mode extraction because no Groq API key was configured.",
            payload={"message": user_text},
        )
    )
    assistant_message = (
        "Demo mode is active because `GROQ_API_KEY` is not configured. I still populated the form"
        " with a lightweight parser so you can continue building and recording the UI."
    )
    return state, events, assistant_message


def get_tool_registry(llm: Any) -> dict[str, Callable[[InteractionFormState, str], tuple[InteractionFormState, ToolEvent]]]:
    return {
        "log_interaction": lambda state, text: log_interaction_tool(llm, state, text),
        "edit_interaction": lambda state, text: edit_interaction_tool(llm, state, text),
        "add_materials": lambda state, text: add_materials_tool(llm, state, text),
        "add_sample": lambda state, text: add_sample_tool(llm, state, text),
        "suggest_follow_ups": lambda state, text: suggest_follow_ups_tool(llm, state, text),
    }


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)
