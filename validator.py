"""
The validator applies deterministic business rules to an extracted Load.

This is the half of the system that must be correct every time. The extractor
is probabilistic (an LLM), so we never let it be the source of truth for
business logic. The model proposes structured data; this code disposes by
checking it against rules we can unit test.

Every function here is pure and testable. No LLM calls, no network, no
randomness. Given the same Load, you always get the same validation result.
That determinism is the whole point.
"""

from models import (
    EQUIPMENT_WEIGHT_LIMITS,
    EQUIP_UNKNOWN,
    STATE_CONFIRMED,
    STATE_NEEDS_REVIEW,
)


# US state codes, used to sanity check extracted states.
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}


def validate_load(load):
    """
    Run all business rules against a load. Mutates the load in place:
    appends any problems to load.validation_errors and sets load.state to
    either confirmed (clean) or needs_review (has problems).

    Returns the same load for convenience.
    """
    errors = []

    errors.extend(_check_required_fields(load))
    errors.extend(_check_weight(load))
    errors.extend(_check_states(load))
    errors.extend(_check_equipment(load))
    errors.extend(_flag_inferred_critical_fields(load))

    # Preserve any errors already present (e.g. extraction_failed) and add new ones.
    for e in errors:
        if e not in load.validation_errors:
            load.validation_errors.append(e)

    # Decide the resulting state. Clean loads are auto confirmed.
    # Anything with a problem needs a human to look at it.
    if load.validation_errors:
        load.state = STATE_NEEDS_REVIEW
    else:
        load.state = STATE_CONFIRMED

    return load


def _check_required_fields(load):
    """A load needs at minimum an origin, a destination, and a weight."""
    errors = []
    if not load.origin_city:
        errors.append("missing: origin_city")
    if not load.dest_city:
        errors.append("missing: dest_city")
    if not load.weight_lbs or load.weight_lbs <= 0:
        errors.append("missing: weight_lbs")
    return errors


def _check_weight(load):
    """Weight must not exceed the limit for the equipment type."""
    errors = []
    if load.weight_lbs and load.weight_lbs > 0:
        limit = EQUIPMENT_WEIGHT_LIMITS.get(load.equipment, 0)
        if limit and load.weight_lbs > limit:
            errors.append(
                f"weight_exceeds_limit: {load.weight_lbs} lbs over {limit} lbs max for {load.equipment}"
            )
    return errors


def _check_states(load):
    """Any state code present must be a real US state."""
    errors = []
    if load.origin_state and load.origin_state.upper() not in US_STATES:
        errors.append(f"invalid_state: origin_state '{load.origin_state}'")
    if load.dest_state and load.dest_state.upper() not in US_STATES:
        errors.append(f"invalid_state: dest_state '{load.dest_state}'")
    return errors


def _check_equipment(load):
    """Equipment must be known for a load to be auto confirmed."""
    errors = []
    if load.equipment == EQUIP_UNKNOWN:
        errors.append("missing: equipment (not stated in message)")
    return errors


def _flag_inferred_critical_fields(load):
    """
    If the model inferred a critical routing field (a destination or origin
    state), flag it. Inferred values could be wrong, and a wrong state routes
    a truck to the wrong place. We would rather a human confirm.
    """
    errors = []
    critical = {"origin_state", "dest_state"}
    for f in load.inferred_fields:
        if f in critical:
            errors.append(f"inferred_critical_field: {f} was inferred, confirm before dispatch")
    return errors
