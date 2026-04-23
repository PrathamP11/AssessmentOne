from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .agent import run_agent
from .database import get_db, init_db
from .repository import list_interactions, record_to_form_state, save_interaction
from .schemas import (
    AgentRequest,
    AgentResponse,
    InteractionListItem,
    SaveInteractionRequest,
    SavedInteractionResponse,
)


app = FastAPI(title="AI-First CRM HCP Module API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.post("/api/agent/message", response_model=AgentResponse)
def agent_message(payload: AgentRequest):
    return run_agent(
        message=payload.message,
        form_state=payload.form_state,
        history=payload.history,
    )


@app.post("/api/interactions", response_model=SavedInteractionResponse)
def create_interaction(payload: SaveInteractionRequest, db: Session = Depends(get_db)):
    record = save_interaction(db, payload.form_state)
    return SavedInteractionResponse(
        id=record.id,
        message="Interaction saved successfully.",
        form_state=record_to_form_state(record),
    )


@app.get("/api/interactions", response_model=list[InteractionListItem])
def get_interactions(db: Session = Depends(get_db)):
    return [
        InteractionListItem(
            id=record.id,
            hcp_name=record.hcp_name,
            interaction_type=record.interaction_type,
            date=record.interaction_date,
            time=record.interaction_time,
            sentiment=record.sentiment,
        )
        for record in list_interactions(db)
    ]
