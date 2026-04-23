from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent import run_agent
from .schemas import AgentRequest, AgentResponse


app = FastAPI(title="AI-First CRM HCP Module API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
