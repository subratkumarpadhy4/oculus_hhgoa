"""
test_sufficiency.py
-------------------
Unit tests for the deterministic sufficiency assessment engine.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/HHGoa")))

from agent.nodes.assess_sufficiency import assess_sufficiency_node


def run_test(scenario_name: str, dimensions: dict, expected: str, initial_round: int = 0):
    state = {
        "evidence_rounds": initial_round,
        "llm_findings": {
            "uncertainty_dimensions": dimensions
        },
        "trace": []
    }
    result_state = assess_sufficiency_node(state)
    verdict = result_state.get("sufficiency")
    passed = verdict == expected
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {scenario_name}")
    print(f"  Inputs:   {dimensions}")
    print(f"  Expected: {expected}")
    print(f"  Got:      {verdict}")
    print(f"  Trace:    {result_state['trace'][-1]['details']}")
    print("-" * 60)
    return passed


def main():
    print("=== RUNNING SUFFICIENCY ENGINE TESTS ===\n")
    all_passed = True

    # Scenario A — Strong evidence
    scen_a = run_test(
        "Scenario A — Strong evidence",
        {
            "graph_evidence": "strong",
            "behavioral_evidence": "strong",
            "prior_case_match": "strong",
            "contradictory_evidence": "none",
        },
        "sufficient"
    )
    all_passed = all_passed and scen_a

    # Scenario B — Weak evidence
    scen_b = run_test(
        "Scenario B — Weak evidence",
        {
            "graph_evidence": "weak",
            "behavioral_evidence": "weak",
            "prior_case_match": "none",
            "contradictory_evidence": "none",
        },
        "insufficient"
    )
    all_passed = all_passed and scen_b

    # Scenario C — Contradictory
    scen_c = run_test(
        "Scenario C — Contradictory",
        {
            "graph_evidence": "moderate",
            "behavioral_evidence": "moderate",
            "prior_case_match": "strong",
            "contradictory_evidence": "major",
        },
        "contradictory"
    )
    all_passed = all_passed and scen_c

    # Scenario D — Borderline
    scen_d = run_test(
        "Scenario D — Borderline",
        {
            "graph_evidence": "moderate",
            "behavioral_evidence": "moderate",
            "prior_case_match": "moderate",
            "contradictory_evidence": "minor",
        },
        "insufficient"
    )
    all_passed = all_passed and scen_d

    # Circuit breaker test (round >= 3)
    cb_test = run_test(
        "Circuit Breaker (round cap >= 3)",
        {
            "graph_evidence": "weak",
            "behavioral_evidence": "weak",
            "prior_case_match": "none",
            "contradictory_evidence": "none",
        },
        "sufficient",
        initial_round=2  # will increment to 3
    )
    all_passed = all_passed and cb_test

    if all_passed:
        print("\nALL SCENARIOS PASSED SUCCESSFULLY!")
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
