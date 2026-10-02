"""
test_skeleton.py
----------------
Runs the first 3 cases from case_pack.csv through the LangGraph StateMachine skeleton.
"""

import csv
import json
import os
import sys

# Ensure C:\HHGoa is in Python path
sys.path.insert(0, r"C:\HHGoa")

from agent.graph import run_case

CASE_PACK_PATH = r"C:\HHGoa\data\case_pack.csv"


def main():
    print("=" * 70)
    print("HHGOA FRAUD INVESTIGATION AGENT — SKELETON TEST RUN")
    print("=" * 70)

    if not os.path.exists(CASE_PACK_PATH):
        print(f"[ERROR] case_pack.csv not found at {CASE_PACK_PATH}")
        sys.exit(1)

    cases = []
    with open(CASE_PACK_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            cases.append(row)

    print(f"Loaded {len(cases)} test cases from case_pack.csv.\n")

    for idx, case_row in enumerate(cases, start=1):
        case_id = case_row.get("case_id", f"Case-{idx}")
        print(f"\n>>> Running Case {idx}/3: {case_id} (Trigger: {case_row.get('trigger_type')}) ...")

        final_state = run_case(case_row)

        print("-" * 50)
        print(f"Case ID              : {final_state.get('case_id')}")
        print(f"Final Case Status    : {final_state.get('final_case_status')}")
        print(f"Sufficiency          : {final_state.get('sufficiency')}")
        print(f"Evidence Rounds      : {final_state.get('evidence_rounds')}")
        print(f"Recommended Actions  : {json.dumps(final_state.get('recommended_actions'), indent=2)}")
        print(f"Executed Actions     : {json.dumps(final_state.get('executed_actions'), indent=2)}")
        print(f"Evidence Requests    : {json.dumps(final_state.get('evidence_requests'), indent=2)}")
        print("\nLast 5 Trace Entries :")
        trace = final_state.get("trace", [])
        for entry in trace[-5:]:
            print(f"  [{entry.get('timestamp')}] {entry.get('node'):<20} -> {entry.get('details')}")
        print("-" * 50)

    print("\n" + "=" * 70)
    print("ALL 3 SKELETON RUNS COMPLETED SUCCESSFULLY.")
    print("=" * 70)


if __name__ == "__main__":
    main()
