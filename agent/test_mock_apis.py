"""
test_mock_apis.py
-----------------
Tests for the 6 deterministic mock evidence APIs.
Validates repeatable deterministic output for HHG-001 and differentiation for HHG-002.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/HHGoa")))

from agent.mock_apis import (
    request_step_up_auth,
    request_customer_validation,
    request_device_fingerprint,
    request_kyc_reverification,
    request_transaction_history_extension,
    request_analyst_review,
)


def run_all_apis(case_id: str) -> dict:
    return {
        "request_step_up_auth": request_step_up_auth(case_id),
        "request_customer_validation": request_customer_validation(case_id),
        "request_device_fingerprint": request_device_fingerprint(case_id),
        "request_kyc_reverification": request_kyc_reverification(case_id),
        "request_transaction_history_extension": request_transaction_history_extension(case_id),
        "request_analyst_review": request_analyst_review(case_id),
    }


def main():
    print("=== TESTING MOCK EVIDENCE APIS DETERMINISM ===\n")

    # 1. Call for HHG-001 (Run 1)
    print("--- 1. Calling for HHG-001 (Run 1) ---")
    run1 = run_all_apis("HHG-001")
    for k, v in run1.items():
        print(f"  {k}: {v['response']}")

    # 2. Call for HHG-001 (Run 2)
    print("\n--- 2. Calling for HHG-001 (Run 2) ---")
    run2 = run_all_apis("HHG-001")
    for k, v in run2.items():
        print(f"  {k}: {v['response']}")

    # Check determinism for HHG-001
    deterministic = run1 == run2
    print(f"\n>> HHG-001 Determinism check (Run 1 == Run 2): {'PASS' if deterministic else 'FAIL'}")

    # 3. Call for HHG-002
    print("\n--- 3. Calling for HHG-002 ---")
    run_hhg2 = run_all_apis("HHG-002")
    for k, v in run_hhg2.items():
        print(f"  {k}: {v['response']}")

    # Check differentiation between HHG-001 and HHG-002
    different = run1 != run_hhg2
    print(f"\n>> Differentiation check (HHG-001 != HHG-002): {'PASS' if different else 'FAIL'}")

    all_ok = deterministic and different
    if all_ok:
        print("\nALL MOCK API TESTS PASSED SUCCESSFULLY!")
    else:
        print("\nMOCK API TESTS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
