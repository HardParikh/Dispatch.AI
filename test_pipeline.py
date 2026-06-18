"""
Quick end to end test of the Dispatch pipeline without the API or frontend.

Run from the project root:
    python -m test_pipeline

This exercises the extractor, validator, action engine, and store together
through the LangGraph pipeline. Good for confirming everything is wired up
before you start the API.
"""

from graph import process_message


MESSAGES = [
    # Clean load. Should auto confirm and route to dispatch.
    "Need a dry van to grab 42k lbs of canned goods out of Dayton OH Tuesday "
    "morning, deliver to Columbus OH. Ref# B-347363.",

    # Overweight for a reefer (limit 43500). Should flag for review.
    "Reefer load, 45000 lbs of frozen goods, Fresno CA to Phoenix AZ. Pickup 12/15.",

    # Missing equipment and destination. Should flag and draft a clarification.
    "Got 30000 lbs of paper out of Chicago, need it moved next week. Order 99812.",

    # Sparse. Origin only. Should flag and ask for the missing pieces.
    "Can you cover a flatbed out of Houston? Steel coils, about 47000 lbs.",
]


def main():
    for i, msg in enumerate(MESSAGES):
        print("\n" + "=" * 72)
        print(f"MESSAGE {i + 1}: {msg[:64]}...")
        print("=" * 72)
        result = process_message(msg)
        print(f"  Load ID:  {result['load_id']}")
        print(f"  State:    {result['state']}")
        print(f"  Lane:     {result['origin_city']} {result['origin_state']} -> "
              f"{result['dest_city']} {result['dest_state']}")
        print(f"  Weight:   {result['weight_lbs']} lbs   Equipment: {result['equipment']}")
        if result["inferred_fields"]:
            print(f"  Inferred: {result['inferred_fields']}")
        if result["validation_errors"]:
            print(f"  Issues:   {result['validation_errors']}")
        for a in result["actions"]:
            print(f"  Action:   [{a['type']}] {a['summary']}")
            if a["content"]:
                print("    ---")
                for line in a["content"].splitlines():
                    print("    " + line)
                print("    ---")


if __name__ == "__main__":
    main()
