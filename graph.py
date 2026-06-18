"""
The Dispatch v2 orchestration.

v1 was a fixed pipeline: extract, validate, act. v2 adds a conditional branch.
After validation, the graph decides:

    - Clean load (confirmed): go straight to act, then persist. No agent needed.
    - Load that needs judgment (needs_review): route through the AGENT, which
      enriches it with knowledge and a recommendation, then act, then persist.

This is the workflow-plus-agent pattern from the concept doc. The deterministic
spine (extract, validate) always runs. The agent handles only the open ended
part, and only when needed. Most loads never touch the agent, which keeps cost
down. That is the discipline: use the agent only where runtime judgment helps.

The conditional edge is the new concept here versus v1's linear graph.
"""

from langgraph.graph import StateGraph, END

from extractor import extract_load
from validator import validate_load
from actions import decide_and_act
from store import save_load
from agent import run_agent
from models import STATE_CONFIRMED, STATE_NEEDS_REVIEW


def extract_node(state):
    load = extract_load(state["message"])
    return {"load": load}


def validate_node(state):
    load = validate_load(state["load"])
    return {"load": load}


def agent_node(state):
    """
    Run the agent on a load that needs judgment. The agent enriches the load
    with an assessment and a recommended action, and produces a trace. We
    attach the agent's output to the load as an action so it shows in the UI.
    """
    load = state["load"]
    result = run_agent(load)

    load.actions.append({
        "type": "agent_assessment",
        "summary": f"Agent recommendation: {result['recommended_action']}",
        "content": result["assessment"],
    })

    # Stash the trace id on the load so the frontend can fetch the full trace.
    load.agent_trace_id = result["trace"]["trace_id"]

    return {"load": load}


def act_node(state):
    load = decide_and_act(state["load"])
    return {"load": load}


def persist_node(state):
    load = state["load"]
    save_load(load)
    return {"load": load}


def route_after_validation(state):
    """
    The conditional edge. This is the new v2 concept. After validation, decide
    whether the load needs the agent. Clean loads skip it; loads needing review
    go through it. The function returns the name of the next node.
    """
    load = state["load"]
    if load.state == STATE_NEEDS_REVIEW:
        return "agent"
    return "act"


def build_graph():
    workflow = StateGraph(dict)

    workflow.add_node("extract", extract_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("act", act_node)
    workflow.add_node("persist", persist_node)

    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "validate")

    # The conditional branch. After validate, route to either agent or act.
    workflow.add_conditional_edges("validate", route_after_validation, {
        "agent": "agent",
        "act": "act",
    })

    # The agent feeds into act, same as the clean path.
    workflow.add_edge("agent", "act")
    workflow.add_edge("act", "persist")
    workflow.add_edge("persist", END)

    return workflow.compile()


dispatch_graph = build_graph()


def process_message(message):
    initial_state = {"message": message, "load": None}
    final_state = dispatch_graph.invoke(initial_state)
    load = final_state["load"]
    return load.to_dict()


if __name__ == "__main__":
    samples = [
        # Clean, skips the agent.
        "Dry van, 42000 lbs canned goods, Dayton OH to Columbus OH. Ref B-347363.",
        # Needs review, goes through the agent: overweight reefer.
        "Reefer, 45000 lbs frozen goods, Fresno CA to Phoenix AZ from Armstrong Transport.",
        # Needs review, missing destination, agent enriches.
        "Flatbed out of Houston, steel coils about 47000 lbs.",
    ]
    for s in samples:
        print("\n" + "=" * 70)
        print("MESSAGE:", s[:60])
        result = process_message(s)
        print("STATE:", result["state"])
        for a in result["actions"]:
            print("ACTION:", a["type"], "-", a["summary"])
