"""
test_policy.py
--------------
Unit tests for the deterministic policy authorization engine.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/HHGoa")))

from agent.nodes.enforce_policy import enforce_policy_node


def run_scenario(name: str, actions: list, exposure: float, expected_routes: list, expected_overall: str):
    state = {
        "recommended_actions": actions,
        "exposure_usd": exposure,
        "trace": []
    }
    result = enforce_policy_node(state)
    actual_routes = [a.get("route") for a in result.get("recommended_actions", [])]
    actual_overall = result.get("approval_route")

    routes_ok = actual_routes == expected_routes
    overall_ok = actual_overall == expected_overall
    passed = routes_ok and overall_ok

    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {name}")
    print(f"  Exposure:        ${exposure:.2f}")
    print(f"  Expected Routes: {expected_routes} | Expected Overall: {expected_overall}")
    print(f"  Got Routes:      {actual_routes} | Got Overall:      {actual_overall}")
    print(f"  Trace:           {result['trace'][-1]['details']}")
    print("-" * 60)
    return passed


def main():
    print("=== RUNNING POLICY ENGINE TESTS ===\n")
    all_passed = True

    # Scenario A — Everything auto
    scen_a = run_scenario(
        "Scenario A — Everything auto",
        [{"action": "VERIFY_WITH_CUSTOMER"}, {"action": "MONITOR_CARD"}],
        77.07,
        ["auto", "auto"],
        "auto"
    )
    all_passed = all_passed and scen_a

    # Scenario B — One L1
    scen_b = run_scenario(
        "Scenario B — One L1",
        [{"action": "BLOCK_CARD"}, {"action": "CREATE_CASE"}],
        500.00,
        ["L1", "auto"],
        "L1"
    )
    all_passed = all_passed and scen_b

    # Scenario C — One L2
    scen_c = run_scenario(
        "Scenario C — One L2",
        [{"action": "BLOCK_CARD"}, {"action": "FILE_REPORT"}],
        3500.00,
        ["L2", "L2"],
        "L2"
    )
    all_passed = all_passed and scen_c

    # Scenario D — Mixed
    scen_d = run_scenario(
        "Scenario D — Mixed",
        [{"action": "VERIFY_WITH_CUSTOMER"}, {"action": "BLOCK_CARD"}, {"action": "MONITOR_CONNECTED_CARDS"}],
        1800.00,
        ["auto", "L1", "auto"],
        "L1"
    )
    all_passed = all_passed and scen_d

    if all_passed:
        print("\nALL SCENARIOS PASSED SUCCESSFULLY!")
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
