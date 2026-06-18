"""
Core data structures for Dispatch.

A Load is the central object. It moves through a lifecycle of states.
Kept as plain Python so the structure is obvious and the validation logic
in validator.py can operate on it directly with no framework in the way.
"""

from datetime import datetime


# Load lifecycle states
STATE_DRAFT = "draft"
STATE_NEEDS_REVIEW = "needs_review"
STATE_CONFIRMED = "confirmed"
STATE_IN_TRANSIT = "in_transit"
STATE_DELIVERED = "delivered"
STATE_BILLED = "billed"

LOAD_STATES = [
    STATE_DRAFT,
    STATE_NEEDS_REVIEW,
    STATE_CONFIRMED,
    STATE_IN_TRANSIT,
    STATE_DELIVERED,
    STATE_BILLED,
]

# Which state transitions are allowed. The state machine enforces this.
ALLOWED_TRANSITIONS = {
    STATE_DRAFT: [STATE_NEEDS_REVIEW, STATE_CONFIRMED],
    STATE_NEEDS_REVIEW: [STATE_CONFIRMED, STATE_DRAFT],
    STATE_CONFIRMED: [STATE_IN_TRANSIT],
    STATE_IN_TRANSIT: [STATE_DELIVERED],
    STATE_DELIVERED: [STATE_BILLED],
    STATE_BILLED: [],
}


# Equipment types
EQUIP_DRY_VAN = "dry_van"
EQUIP_REEFER = "reefer"
EQUIP_FLATBED = "flatbed"
EQUIP_UNKNOWN = "unknown"

EQUIPMENT_TYPES = [EQUIP_DRY_VAN, EQUIP_REEFER, EQUIP_FLATBED, EQUIP_UNKNOWN]


# Maximum payload weight in pounds per equipment type.
# Real freight has more nuance, but this captures the validation pattern.
EQUIPMENT_WEIGHT_LIMITS = {
    EQUIP_DRY_VAN: 45000,
    EQUIP_REEFER: 43500,
    EQUIP_FLATBED: 48000,
    EQUIP_UNKNOWN: 0,
}


class Load:
    """A freight load. Plain class, explicit fields, no framework."""

    def __init__(
        self,
        load_id,
        origin_city="",
        origin_state="",
        dest_city="",
        dest_state="",
        weight_lbs=0,
        equipment=EQUIP_UNKNOWN,
        commodity="",
        pickup_date="",
        reference_number="",
        state=STATE_DRAFT,
        validation_errors=None,
        inferred_fields=None,
        actions=None,
        created_at=None,
        source_message="",
    ):
        # Identity
        self.load_id = load_id

        # Core shipment details (extracted from the message)
        self.origin_city = origin_city
        self.origin_state = origin_state
        self.dest_city = dest_city
        self.dest_state = dest_state
        self.weight_lbs = weight_lbs
        self.equipment = equipment
        self.commodity = commodity
        self.pickup_date = pickup_date
        self.reference_number = reference_number

        # System fields
        self.state = state
        self.validation_errors = validation_errors if validation_errors is not None else []
        self.inferred_fields = inferred_fields if inferred_fields is not None else []
        self.actions = actions if actions is not None else []
        self.created_at = created_at if created_at is not None else datetime.utcnow().isoformat()
        self.source_message = source_message

    def to_dict(self):
        return {
            "load_id": self.load_id,
            "origin_city": self.origin_city,
            "origin_state": self.origin_state,
            "dest_city": self.dest_city,
            "dest_state": self.dest_state,
            "weight_lbs": self.weight_lbs,
            "equipment": self.equipment,
            "commodity": self.commodity,
            "pickup_date": self.pickup_date,
            "reference_number": self.reference_number,
            "state": self.state,
            "validation_errors": self.validation_errors,
            "inferred_fields": self.inferred_fields,
            "actions": self.actions,
            "created_at": self.created_at,
            "source_message": self.source_message,
        }

    @staticmethod
    def from_dict(d):
        """Rebuild a Load from a stored dict (e.g. a Supabase row)."""
        return Load(
            load_id=d.get("load_id"),
            origin_city=d.get("origin_city", ""),
            origin_state=d.get("origin_state", ""),
            dest_city=d.get("dest_city", ""),
            dest_state=d.get("dest_state", ""),
            weight_lbs=d.get("weight_lbs", 0) or 0,
            equipment=d.get("equipment", EQUIP_UNKNOWN),
            commodity=d.get("commodity", ""),
            pickup_date=d.get("pickup_date", ""),
            reference_number=d.get("reference_number", ""),
            state=d.get("state", STATE_DRAFT),
            validation_errors=d.get("validation_errors") or [],
            inferred_fields=d.get("inferred_fields") or [],
            actions=d.get("actions") or [],
            created_at=d.get("created_at"),
            source_message=d.get("source_message", ""),
        )
