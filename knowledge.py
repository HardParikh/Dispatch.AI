"""
The knowledge base for Dispatch's RAG layer.

This holds freight business knowledge the agent can retrieve: carrier
reliability profiles, lane pricing benchmarks, customer SOPs, and freight
policy. In a real system this would be hundreds of documents in a vector
database. Here we seed a representative set so you can see RAG work end to end.

Each entry is a plain dict with an id, a category, and the text. The text is
what gets embedded and retrieved. We keep each entry to roughly one coherent
idea, which is good chunking: big enough to stand alone, small enough to be
about one thing.
"""

# The seed knowledge. In production this comes from real company documents,
# chunked and embedded. Here it is hand written to be representative.
KNOWLEDGE = [
    {
        "id": "carrier_armstrong",
        "category": "carrier_profile",
        "text": (
            "Armstrong Transport Group is a reliable dry van and reefer carrier. "
            "Reliability score 92 out of 100. Typical dry van loads run 40000 to "
            "44000 lbs. They prefer lanes in the Midwest and Southeast. On time "
            "delivery rate is 96 percent. They require a 24 hour notice for "
            "pickup scheduling and do not handle hazmat."
        ),
    },
    {
        "id": "carrier_ewing",
        "category": "carrier_profile",
        "text": (
            "Ewing Outdoor Supply runs primarily flatbed equipment for building "
            "materials and landscaping supply. Reliability score 85 out of 100. "
            "Typical flatbed loads run 45000 to 48000 lbs. They specialize in "
            "Southeast regional lanes. Note that Ewing requires tarping on all "
            "exposed loads and charges a tarp fee."
        ),
    },
    {
        "id": "lane_dayton_columbus",
        "category": "lane_pricing",
        "text": (
            "The Dayton OH to Columbus OH lane is a short haul of about 75 miles. "
            "Standard dry van rate is 250 to 320 dollars all in. Reefer adds "
            "roughly 80 dollars. This lane has high carrier availability so rates "
            "are competitive. Transit time is same day."
        ),
    },
    {
        "id": "lane_fresno_phoenix",
        "category": "lane_pricing",
        "text": (
            "The Fresno CA to Phoenix AZ lane is a medium haul of about 600 miles. "
            "Standard reefer rate is 1400 to 1800 dollars all in, driven by produce "
            "season demand. Dry van runs 900 to 1200 dollars. Transit time is one "
            "day. Rates spike sharply during summer produce season."
        ),
    },
    {
        "id": "sop_armstrong",
        "category": "customer_sop",
        "text": (
            "Standard operating procedure for Armstrong Transport loads. Always "
            "confirm the reference number before dispatch. Armstrong requires a "
            "rate confirmation document on every load. For any load over 44000 lbs, "
            "escalate to a human because it exceeds Armstrong's typical dry van "
            "capacity and may need special equipment."
        ),
    },
    {
        "id": "policy_weight_limits",
        "category": "freight_policy",
        "text": (
            "Federal weight limits. The maximum gross vehicle weight is 80000 lbs "
            "including the tractor and trailer. Usable payload for a standard dry "
            "van is about 45000 lbs, for a reefer about 43500 lbs because the "
            "refrigeration unit adds weight, and for a flatbed about 48000 lbs. "
            "Loads exceeding these payloads require special permits and routing."
        ),
    },
    {
        "id": "policy_reefer",
        "category": "freight_policy",
        "text": (
            "Reefer freight policy. Refrigerated loads must specify a temperature "
            "setpoint. Frozen goods run at zero degrees Fahrenheit or below, fresh "
            "produce runs between 33 and 40 degrees. Reefer payload capacity is "
            "lower than dry van because the refrigeration unit and fuel add weight. "
            "Always confirm the setpoint with the shipper before dispatch."
        ),
    },
    {
        "id": "policy_detention",
        "category": "freight_policy",
        "text": (
            "Detention policy. Detention is charged when a carrier waits beyond the "
            "free time at pickup or delivery, typically two hours. Standard "
            "detention rate is 50 to 75 dollars per hour after free time. Detention "
            "must be documented with arrival and departure times to be billable."
        ),
    },
]


def all_knowledge():
    """Return all knowledge entries."""
    return KNOWLEDGE


def get_by_category(category):
    """Return all entries in a category."""
    return [k for k in KNOWLEDGE if k["category"] == category]
