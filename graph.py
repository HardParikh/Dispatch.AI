"""
The LangGraph orchestration for Dispatch.

This is where the agent fundamentals you learned in Atlas get applied to a
real domain. The pipeline is a state machine:

    extract -> validate -> act -> persist -> END

Each node does one job and writes to a shared state dict. LangGraph runs them
in order. This is the orchestrator-worker idea from Atlas in its simplest
linear form: a fixed pipeline of specialized steps, each with a clear
contract.

Why a graph instead of just calling the functions in sequence? Three reasons,
all of which matter in production:

1. Observability. Each node is a discrete, named step. When something goes
   wrong you know exactly which stage failed.
2. State management. The shared state flows through cleanly. Adding a step
   later (say, a credit check) means adding a node, not rewriting a function.
3. Extensibility. Today the flow is linear. Tomorrow you can add conditional
   edges (route differently based on load value, customer tier, etc) without
   restructuring everything.

The state is a plain dict. We do not use Pydantic or typed state. LangGraph
works fine with a TypedDict-like plain dict for our purposes.
"""

from langgraph.graph import StateGraph, END

from extractor import extract_load
from validator import validate_load
from actions import decide_and_act
from store import save_load
from models import Load


# ---- Nodes -----------------------------------------------------------------
# Each node takes the state dict and returns a partial update to it.

def extract_node(state):
    """Turn the raw message into a structured Load."""
    load = extract_load(state["message"])
    return {"load": load}


def validate_node(state):
    """Apply deterministic business rules. Sets state to confirmed or needs_review."""
    load = validate_load(state["load"])
    return {"load": load}


def act_node(state):
    """Decide and draft follow up actions based on the validated load."""
    load = decide_and_act(state["load"])
    return {"load": load}


def persist_node(state):
    """Save the finished load to the store (Supabase or in-memory)."""
    load = state["load"]
    save_load(load)
    return {"load": load}


# ---- Graph wiring ----------------------------------------------------------

def build_graph():
    workflow = StateGraph(dict)

    workflow.add_node("extract", extract_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("act", act_node)
    workflow.add_node("persist", persist_node)

    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "validate")
    workflow.add_edge("validate", "act")
    workflow.add_edge("act", "persist")
    workflow.add_edge("persist", END)

    return workflow.compile()


# Build once at import time. Reused across requests.
dispatch_graph = build_graph()


def process_message(message):
    """
    Public entry point. Runs a raw freight message through the full pipeline
    and returns the finished Load as a dict.
    """
    initial_state = {"message": message, "load": None}
    final_state = dispatch_graph.invoke(initial_state)
    load = final_state["load"]
    return load.to_dict()


if __name__ == "__main__":
    # Quick manual test from the project root: python -m graph
    samples = [
        "Need a dry van to grab 42k lbs of canned goods out of Dayton OH "
        "Tuesday morning, deliver to Kansas City. Ref# B-347363.",
        "Can you cover a flatbed out of Houston? Steel coils, about 47000 lbs.",
        "Reefer load. 40k of frozen veggies. Pickup Fresno CA, drop in Phoenix AZ. "
        "Pickup 12/15. Order RF-5521.",
    ]
    for s in samples:
        print("\n" + "=" * 70)
        print("MESSAGE:", s[:60], "...")
        result = process_message(s)
        print("STATE:", result["state"])
        print("LANE:", result["origin_city"], result["origin_state"], "->",
              result["dest_city"], result["dest_state"])
        print("ERRORS:", result["validation_errors"])
        for a in result["actions"]:
            print("ACTION:", a["type"], "-", a["summary"])
            if a["content"]:
                print("  CONTENT:", a["content"][:160], "...")
