"""
The action engine decides what to do with a load after validation, and
drafts the actual action content.

In a real Augie-style system, these actions would send real emails, write to
a real TMS, and post to real Slack channels. Here, each action produces a
structured record describing what the agent decided to do and the content it
generated. The frontend displays these so you can see the agent's decisions.

This mirrors the production pattern: the agent does not silently take actions.
Every action is a recorded, inspectable artifact. That auditability is what
makes an agent trustworthy in a business workflow.
"""

import os
import warnings

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

from models import STATE_CONFIRMED, STATE_NEEDS_REVIEW

warnings.filterwarnings("ignore")
load_dotenv()

client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    http_client=httpx.Client(verify=False),
)


def decide_and_act(load):
    """
    Look at the validated load and decide what action to take. Append the
    action record to load.actions. Returns the load.

    Two paths:
    - Clean load (confirmed): route to dispatch.
    - Problem load (needs_review): draft a clarification email for the broker
      describing exactly what is missing or wrong, and flag for human review.
    """
    if load.state == STATE_CONFIRMED:
        action = _route_to_dispatch(load)
        load.actions.append(action)
    elif load.state == STATE_NEEDS_REVIEW:
        clarification = _draft_clarification(load)
        load.actions.append(clarification)
        load.actions.append(_flag_for_review(load))

    return load


def _route_to_dispatch(load):
    """A clean load is routed to the dispatch queue."""
    lane = f"{load.origin_city}, {load.origin_state} to {load.dest_city}, {load.dest_state}"
    return {
        "type": "route_to_dispatch",
        "summary": f"Load {load.load_id} routed to dispatch. Lane: {lane}. {load.weight_lbs} lbs, {load.equipment}.",
        "content": "",
    }


def _flag_for_review(load):
    """A problem load is flagged for a human operator."""
    problems = ", ".join(load.validation_errors) if load.validation_errors else "unspecified"
    return {
        "type": "flag_for_review",
        "summary": f"Load {load.load_id} flagged for human review. Issues: {problems}.",
        "content": "",
    }


CLARIFICATION_SYSTEM_PROMPT = """You are a freight operations assistant writing
a short, professional reply to a broker to resolve missing or unclear details
about a load.

You are given the issues with the load. Write a brief, friendly email that
asks only for the specific missing or unclear information. Do not invent
details. Do not be verbose. Keep it to a few sentences. Reference the load
details you do have so the broker knows which load you mean.

Output only the email body. No subject line, no preamble.
"""


def _draft_clarification(load):
    """
    Use the LLM to draft a clarification email to the broker. This is a good
    use of an LLM: generating natural language from structured facts. The
    facts (what is wrong) come from the deterministic validator, so the email
    is grounded in real issues, not hallucinated ones.
    """
    known = []
    if load.origin_city:
        known.append(f"origin {load.origin_city} {load.origin_state}".strip())
    if load.dest_city:
        known.append(f"destination {load.dest_city} {load.dest_state}".strip())
    if load.weight_lbs:
        known.append(f"weight {load.weight_lbs} lbs")
    if load.equipment and load.equipment != "unknown":
        known.append(f"equipment {load.equipment}")
    if load.reference_number:
        known.append(f"ref {load.reference_number}")

    known_str = "; ".join(known) if known else "no details confirmed yet"
    issues_str = "; ".join(load.validation_errors) if load.validation_errors else "none"

    user_content = (
        f"Load details we have: {known_str}.\n"
        f"Issues to resolve: {issues_str}.\n"
        f"Original message from broker: {load.source_message}\n\n"
        f"Write the clarification email."
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            system=CLARIFICATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        body = response.content[0].text
    except Exception as e:
        body = f"(failed to draft clarification: {e})"

    return {
        "type": "draft_clarification",
        "summary": f"Drafted clarification email for load {load.load_id}.",
        "content": body,
    }
