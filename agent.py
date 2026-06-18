"""
The Dispatch agent.

This is the leap from workflow to agent. After a load is extracted and
validated, if it needs enrichment or judgment, it goes to this agent. The
agent runs a ReAct loop: it reasons, calls a tool, observes the result, and
repeats until it has enough to produce an enriched assessment, or it hits the
iteration cap.

The agent has four tools:
    retrieve_knowledge  RAG over freight business knowledge
    lookup_carrier      a carrier's reliability and typical loads
    check_lane          lane pricing benchmark
    finalize            produce the final assessment and stop

Every safeguard from concept-agents.md is here:
    - an iteration cap so it cannot loop forever
    - graceful tool failure so a miss does not crash it
    - the deterministic validator still owns business rules; the agent enriches
      and advises but never overrides validation
    - full tracing of every step

The agent reasons and advises. It does not get to be the source of truth for
business decisions. That stays in deterministic code.
"""

import json
import os
import time
import warnings

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

from rag import retrieve, format_context
from knowledge import get_by_category
from observability import Trace

warnings.filterwarnings("ignore")
load_dotenv()

client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    http_client=httpx.Client(verify=False),
)

MAX_ITERATIONS = 5


# ---- Tools the agent can call ----------------------------------------------
# Each tool is a Python function plus a schema entry. The schema descriptions
# are written carefully because the model selects tools by reading them. This
# is prompt engineering for tool selection.

AGENT_TOOLS = [
    {
        "name": "retrieve_knowledge",
        "description": (
            "Search the freight knowledge base for relevant business knowledge: "
            "freight policy, reefer rules, weight limits, detention policy. Use "
            "this when you need general freight domain knowledge to assess a load. "
            "Provide a natural language query describing what you need to know."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What you want to know, in natural language.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "lookup_carrier",
        "description": (
            "Look up a specific carrier's reliability score, typical load weights, "
            "equipment types, and special requirements by carrier name. Use this "
            "when a carrier is named and you want their profile. If the carrier is "
            "not known, this returns a not-found result."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "carrier_name": {
                    "type": "string",
                    "description": "The carrier or company name to look up.",
                },
            },
            "required": ["carrier_name"],
        },
    },
    {
        "name": "check_lane",
        "description": (
            "Check the typical pricing and transit time for a freight lane by "
            "origin and destination city. Use this to assess whether a load's "
            "details are reasonable for its lane. If the lane is not known, this "
            "returns a not-found result."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Origin city."},
                "destination": {"type": "string", "description": "Destination city."},
            },
            "required": ["origin", "destination"],
        },
    },
    {
        "name": "finalize",
        "description": (
            "Produce your final assessment of the load and stop. Call this when "
            "you have gathered enough information. Provide a concise assessment "
            "and a recommended next action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assessment": {
                    "type": "string",
                    "description": "Your concise assessment of the load.",
                },
                "recommended_action": {
                    "type": "string",
                    "description": "The single recommended next action.",
                },
            },
            "required": ["assessment", "recommended_action"],
        },
    },
]


# ---- Tool implementations --------------------------------------------------
# Each returns a string the agent reads. Note the graceful not-found handling:
# tools never throw, they return a clear message the agent can reason about.

def tool_retrieve_knowledge(args, trace):
    query = args.get("query", "")
    t0 = time.time()
    chunks = retrieve(query, top_k=3)
    dur = round((time.time() - t0) * 1000)
    trace.add_retrieval(query, chunks, duration_ms=dur)
    return format_context(chunks)


def tool_lookup_carrier(args, trace):
    name = args.get("carrier_name", "").lower()
    profiles = get_by_category("carrier_profile")
    for p in profiles:
        if name and name.split()[0] in p["text"].lower():
            return p["text"]
    return f"No carrier profile found for '{args.get('carrier_name', '')}'."


def tool_check_lane(args, trace):
    origin = args.get("origin", "").lower()
    dest = args.get("destination", "").lower()
    lanes = get_by_category("lane_pricing")
    for lane in lanes:
        text = lane["text"].lower()
        if origin and dest and origin.split()[0] in text and dest.split()[0] in text:
            return lane["text"]
    return f"No lane pricing found for {args.get('origin', '')} to {args.get('destination', '')}."


TOOL_IMPLS = {
    "retrieve_knowledge": tool_retrieve_knowledge,
    "lookup_carrier": tool_lookup_carrier,
    "check_lane": tool_check_lane,
}


AGENT_SYSTEM_PROMPT = """You are a freight operations agent assessing a load
that needs enrichment or judgment before dispatch.

You have tools to look up carrier profiles, check lane pricing, and retrieve
freight knowledge. Use them to gather the information you need, then call
finalize with your assessment and a recommended action.

Rules:
- Use the tools for facts. Do not rely on your own assumptions about carriers,
  lanes, or policy. If a tool returns not-found, reason about what that means
  rather than inventing the answer.
- Ground your assessment in what the tools returned. When you reference a fact,
  it should come from a tool result.
- Be efficient. Gather what you need, then finalize. Do not call tools you do
  not need.
- You are advising, not deciding. The deterministic validator owns whether the
  load is valid. Your job is to enrich and recommend, not to override rules.

When you have enough, call finalize."""


def run_agent(load):
    """
    Run the agent loop over a load. Returns a dict with the agent's assessment,
    recommended action, and the trace. Also returns the trace object for the
    caller to access the full record.
    """
    trace = Trace(load.load_id)

    # Build the initial context describing the load and why it needs the agent.
    load_summary = (
        f"Load {load.load_id}. "
        f"Origin: {load.origin_city} {load.origin_state}. "
        f"Destination: {load.dest_city} {load.dest_state}. "
        f"Weight: {load.weight_lbs} lbs. Equipment: {load.equipment}. "
        f"Commodity: {load.commodity}. Reference: {load.reference_number}. "
        f"Validation issues: {', '.join(load.validation_errors) if load.validation_errors else 'none'}. "
        f"Original message: {load.source_message}"
    )

    messages = [{
        "role": "user",
        "content": f"Assess this load and recommend a next action.\n\n{load_summary}",
    }]

    assessment = ""
    recommended_action = ""

    for iteration in range(MAX_ITERATIONS):
        t0 = time.time()
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=AGENT_SYSTEM_PROMPT,
            tools=AGENT_TOOLS,
            messages=messages,
        )
        dur = round((time.time() - t0) * 1000)

        in_tok = response.usage.input_tokens
        out_tok = response.usage.output_tokens

        # Find any tool calls in the response.
        tool_calls = [b for b in response.content if b.type == "tool_use"]

        # Record the model's reasoning text if any.
        text_blocks = [b.text for b in response.content if b.type == "text"]
        reasoning = " ".join(text_blocks).strip()
        if reasoning:
            trace.add_step("reason", {"text": reasoning}, duration_ms=dur,
                           input_tokens=in_tok, output_tokens=out_tok)

        if not tool_calls:
            # No tool call and no finalize. Treat the text as the assessment.
            assessment = reasoning or "No assessment produced."
            recommended_action = "review"
            break

        # Append the assistant turn so the conversation stays coherent.
        messages.append({"role": "assistant", "content": response.content})

        # Handle each tool call. We must produce a tool_result for EVERY
        # tool_use block in the assistant turn, or the next API call errors.
        # So we build a result for every call, including finalize, and only
        # stop the loop after all results are recorded.
        tool_results = []
        finalized = False
        for call in tool_calls:
            if call.name == "finalize":
                assessment = call.input.get("assessment", "")
                recommended_action = call.input.get("recommended_action", "")
                trace.add_step("finalize", {
                    "assessment": assessment,
                    "recommended_action": recommended_action,
                })
                finalized = True
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": "Assessment recorded.",
                })
                continue

            impl = TOOL_IMPLS.get(call.name)
            t0 = time.time()
            if impl is None:
                result = f"Unknown tool: {call.name}"
            else:
                result = impl(call.input, trace)
            tdur = round((time.time() - t0) * 1000)

            trace.add_step("tool_call", {
                "tool": call.name,
                "args": call.input,
                "result": result,
            }, duration_ms=tdur)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result,
            })

        # If the agent finalized, we stop here. We do not need to send the
        # tool_results back because we are done.
        if finalized:
            break

        # Feed the tool results back for the next iteration.
        messages.append({"role": "user", "content": tool_results})
    else:
        # The loop ran out of iterations without finalizing. The iteration cap
        # safeguard from the concept doc. Return the best we have.
        if not assessment:
            assessment = "Agent reached maximum iterations without a final assessment."
            recommended_action = "review"

    trace.finish(f"{recommended_action}: {assessment}")

    return {
        "assessment": assessment,
        "recommended_action": recommended_action,
        "trace": trace.to_dict(),
    }
