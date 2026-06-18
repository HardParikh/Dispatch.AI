"""
Dispatch API.

Endpoints:
    POST /ingest          take a raw message, run the pipeline, return the load
    GET  /loads           list all loads
    GET  /loads/{id}      get one load
    POST /loads/{id}/state  manually advance a load's state (the human in the loop)
    GET  /                 health check

The frontend calls these. CORS is wide open for local development; tighten
allow_origins to your deployed frontend URL in production.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph import process_message
from store import list_loads, get_load, update_load_state
from models import ALLOWED_TRANSITIONS

app = FastAPI(title="Dispatch")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dispatch-ai.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "Dispatch", "status": "running"}


@app.post("/ingest")
def ingest(request: dict):
    """Take a raw freight message and run it through the full pipeline."""
    message = request.get("message", "")
    if not message.strip():
        return {"error": "empty message"}
    result = process_message(message)
    return result


@app.get("/loads")
def loads():
    """List all loads, newest first."""
    return {"loads": list_loads()}


@app.get("/loads/{load_id}")
def load_detail(load_id: str):
    """Get one load by id."""
    load = get_load(load_id)
    if load is None:
        return {"error": "not found"}
    return load.to_dict()


@app.post("/loads/{load_id}/state")
def change_state(load_id: str, request: dict):
    """
    Manually move a load to a new state. This is the human in the loop:
    an operator reviewing a flagged load can confirm it, or advance a
    confirmed load through its lifecycle. We enforce the allowed transitions
    so the state machine can never enter an invalid state.
    """
    new_state = request.get("state", "")
    load = get_load(load_id)
    if load is None:
        return {"error": "not found"}

    allowed = ALLOWED_TRANSITIONS.get(load.state, [])
    if new_state not in allowed:
        return {
            "error": f"invalid transition from {load.state} to {new_state}",
            "allowed": allowed,
        }

    updated = update_load_state(load_id, new_state)
    return updated.to_dict()
