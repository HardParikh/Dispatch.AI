"""
The extractor turns an unstructured freight message into a structured Load.

Design: we use Claude's tool use mechanism for structured output. We define
a tool whose input schema matches the fields we want, and the model returns
its extraction as a tool call conforming to that schema. We never execute
the tool. We read the structured input the model produced.

This gives us guaranteed structure with no JSON parsing fragility. This is
the single most important pattern in this project: when you need structured
data from an LLM, use tool use even if you never run a tool. The schema is
both the output contract and the extraction instructions.
"""

import os
import uuid
import warnings

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

from models import Load, EQUIP_UNKNOWN

warnings.filterwarnings("ignore")
load_dotenv()

# Corporate cert bypass. On a normal machine verify=False is unnecessary but
# harmless. On the corporate laptop it is required.
client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    http_client=httpx.Client(verify=False),
)


# The extraction tool schema. This defines the exact shape we want back.
# The model will "call" this tool with the values it extracts.
EXTRACTION_TOOL = {
    "name": "record_load",
    "description": (
        "Record the structured details of a freight load extracted from a "
        "message. Call this once with all the fields you can identify. For "
        "fields you cannot find in the message, leave them empty or use the "
        "appropriate empty value. Do NOT guess values that are not supported "
        "by the message, except for inferring a US state from a well known "
        "city when the state is unambiguous."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "origin_city": {
                "type": "string",
                "description": "Pickup city. Empty string if not found.",
            },
            "origin_state": {
                "type": "string",
                "description": "Pickup state as two letter code (e.g. OH). Empty if not found or ambiguous.",
            },
            "dest_city": {
                "type": "string",
                "description": "Delivery city. Empty string if not found.",
            },
            "dest_state": {
                "type": "string",
                "description": "Delivery state as two letter code. Empty if not found or ambiguous.",
            },
            "weight_lbs": {
                "type": "integer",
                "description": "Weight in pounds as an integer. Convert '42k lbs' to 42000 and 'twenty two thousand pounds' to 22000. Use 0 if not found.",
            },
            "equipment": {
                "type": "string",
                "enum": ["dry_van", "reefer", "flatbed", "unknown"],
                "description": "Equipment type, normalized. 'dry van' -> dry_van, 'reefer'/'refrigerated'/'frozen' -> reefer, 'flatbed' -> flatbed. Use 'unknown' if not stated.",
            },
            "commodity": {
                "type": "string",
                "description": "What is being shipped. Empty string if not found.",
            },
            "pickup_date": {
                "type": "string",
                "description": "Pickup date. If a specific calendar date is determinable, use YYYY-MM-DD. Otherwise keep the raw phrase like 'Tuesday morning'. Empty if not found.",
            },
            "reference_number": {
                "type": "string",
                "description": "Any reference, load, or order number. Empty string if not found.",
            },
            "inferred_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of field names whose values you inferred rather than read directly from the message. For example, if you inferred dest_state from a city name, include 'dest_state'.",
            },
        },
        "required": ["origin_city", "dest_city", "weight_lbs", "equipment", "inferred_fields"],
    },
}


EXTRACTION_SYSTEM_PROMPT = """You are a freight load extraction system.

You read messages from brokers, shippers, and carriers and extract the
structured details of the load being discussed.

Rules:
- Extract only what is supported by the message.
- Normalize values to the canonical forms described in the tool schema.
- For weight, always convert to an integer number of pounds.
- For equipment, map to the normalized enum values.
- You MAY infer a US state from a well known, unambiguous city (Dayton OH,
  not Kansas City which is ambiguous between MO and KS). When you infer,
  add the field name to inferred_fields.
- If a city is genuinely ambiguous for its state, leave the state empty and
  do NOT guess.
- Do not invent reference numbers, dates, or weights that are not present.

Call the record_load tool exactly once with your extraction.
"""


def new_load_id():
    """Generate a short load ID."""
    return "L-" + uuid.uuid4().hex[:8].upper()


def extract_load(message):
    """
    Extract a structured Load from an unstructured freight message.

    Uses Claude's tool use mechanism for guaranteed structured output.
    """
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=EXTRACTION_SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_load"},
        messages=[{"role": "user", "content": message}],
    )

    # Find the tool use block in the response.
    tool_input = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_load":
            tool_input = block.input
            break

    if tool_input is None:
        # The model failed to call the tool. Return an empty load flagged for review.
        load = Load(load_id=new_load_id(), source_message=message)
        load.validation_errors.append("extraction_failed: model did not return structured output")
        return load

    load = Load(
        load_id=new_load_id(),
        origin_city=tool_input.get("origin_city", ""),
        origin_state=tool_input.get("origin_state", ""),
        dest_city=tool_input.get("dest_city", ""),
        dest_state=tool_input.get("dest_state", ""),
        weight_lbs=tool_input.get("weight_lbs", 0),
        equipment=tool_input.get("equipment", EQUIP_UNKNOWN),
        commodity=tool_input.get("commodity", ""),
        pickup_date=tool_input.get("pickup_date", ""),
        reference_number=tool_input.get("reference_number", ""),
        inferred_fields=tool_input.get("inferred_fields", []),
        source_message=message,
    )

    return load
