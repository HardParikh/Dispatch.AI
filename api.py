"""
Dispatch v2 API.

Everything from v1 plus:
    GET /traces/{load_id}   the full agent trace for a load
    GET /knowledge          browse the knowledge base
    GET /stats              aggregate observability stats across all loads

The trace and stats endpoints are what make the agent observable from the
frontend. The knowledge endpoint powers the knowledge browser.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph import process_message
from store import list_loads, get_load, update_load_state
from models import ALLOWED_TRANSITIONS
from observability import get_trace, list_traces
from knowledge import all_knowledge

app = FastAPI(title="Dispatch v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "Dispatch", "version": 2, "status": "running"}


@app.post("/ingest")
def ingest(request: dict):
    message = request.get("message", "")
    if not message.strip():
        return {"error": "empty message"}
    return process_message(message)


@app.get("/loads")
def loads():
    return {"loads": list_loads()}


@app.get("/loads/{load_id}")
def load_detail(load_id: str):
    load = get_load(load_id)
    if load is None:
        return {"error": "not found"}
    return load.to_dict()


@app.post("/loads/{load_id}/state")
def change_state(load_id: str, request: dict):
    new_state = request.get("state", "")
    load = get_load(load_id)
    if load is None:
        return {"error": "not found"}

    allowed = ALLOWED_TRANSITIONS.get(load.state, [])
    if new_state not in allowed:
        return {"error": f"invalid transition from {load.state} to {new_state}", "allowed": allowed}

    updated = update_load_state(load_id, new_state)
    return updated.to_dict()


@app.get("/traces/{load_id}")
def trace_for_load(load_id: str):
    """The full agent trace for a load, if it went through the agent."""
    trace = get_trace(load_id)
    if trace is None:
        return {"error": "no trace for this load"}
    return trace


@app.get("/knowledge")
def knowledge():
    """Browse the knowledge base that powers RAG."""
    return {"knowledge": all_knowledge()}


@app.get("/stats")
def stats():
    """
    Aggregate observability across all agent runs. This is the production
    operability view from the concept doc: totals and averages across runs,
    not just one run.
    """
    traces = list_traces()
    if not traces:
        return {
            "agent_runs": 0,
            "total_tokens": 0,
            "avg_steps": 0,
            "avg_duration_ms": 0,
        }

    total_runs = len(traces)
    total_tokens = sum(t["total_input_tokens"] + t["total_output_tokens"] for t in traces)
    avg_steps = round(sum(t["step_count"] for t in traces) / total_runs, 1)
    avg_duration = round(sum(t["total_duration_ms"] for t in traces) / total_runs)

    return {
        "agent_runs": total_runs,
        "total_tokens": total_tokens,
        "avg_steps": avg_steps,
        "avg_duration_ms": avg_duration,
    }
