"""
mock_apis.py
------------
Simulated deterministic mock evidence APIs for fraud investigation agent.
Uses seeded hashing (case_id + request_type) to ensure determinism.
"""

import hashlib
from typing import Any, Dict, List


def _get_seed_int(case_id: str, request_type: str) -> int:
    """Generate a deterministic integer from case_id and request_type using MD5."""
    key = f"{case_id}:{request_type}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest, 16)


def request_step_up_auth(case_id: str) -> Dict[str, Any]:
    """Simulate step-up authentication check (pass / fail / timeout)."""
    options = ["pass", "fail", "timeout"]
    idx = _get_seed_int(case_id, "request_step_up_auth") % len(options)
    return {
        "response": options[idx],
        "type": "request_step_up_auth"
    }


def request_customer_validation(case_id: str) -> Dict[str, Any]:
    """Simulate customer confirmation response (confirmed / denied / no_response)."""
    options = ["confirmed", "denied", "no_response"]
    idx = _get_seed_int(case_id, "request_customer_validation") % len(options)
    return {
        "response": options[idx],
        "type": "request_customer_validation"
    }


def request_device_fingerprint(case_id: str, device_id: str = None) -> Dict[str, Any]:
    """Simulate device fingerprint lookup (new_device_signal / known_device / inconclusive)."""
    options = ["new_device_signal", "known_device", "inconclusive"]
    idx = _get_seed_int(case_id, "request_device_fingerprint") % len(options)
    return {
        "response": options[idx],
        "type": "request_device_fingerprint"
    }


def request_kyc_reverification(case_id: str) -> Dict[str, Any]:
    """Simulate KYC reverification (verified / mismatch / pending)."""
    options = ["verified", "mismatch", "pending"]
    idx = _get_seed_int(case_id, "request_kyc_reverification") % len(options)
    return {
        "response": options[idx],
        "type": "request_kyc_reverification"
    }


def request_transaction_history_extension(case_id: str) -> Dict[str, Any]:
    """Simulate retrieving extended transaction history outside current graph window."""
    seed = _get_seed_int(case_id, "request_transaction_history_extension")
    num_txns = (seed % 3) + 1
    extra_txns = []
    for i in range(num_txns):
        amt = round(15.0 + ((seed + i * 37) % 25000) / 100.0, 2)
        extra_txns.append({
            "txn_id": f"EXT_{seed % 100000}_{i+1}",
            "amount": amt,
            "channel": "in-person" if (seed + i) % 2 == 0 else "online",
            "risk_score": round(((seed + i * 19) % 100) / 100.0, 2)
        })
    return {
        "response": "extended_history_available",
        "type": "request_transaction_history_extension",
        "extra_transactions": extra_txns
    }


def request_analyst_review(case_id: str) -> Dict[str, Any]:
    """Simulate human analyst review note."""
    notes = [
        "Analyst note: Customer confirmed recent travel to billing region.",
        "Analyst note: Shared device ring confirmed active across 3 associated cards.",
        "Analyst note: Velocity burst consistent with card testing behavior.",
        "Analyst note: Account KYC verified with matching phone and email records."
    ]
    idx = _get_seed_int(case_id, "request_analyst_review") % len(notes)
    return {
        "response": notes[idx],
        "type": "request_analyst_review"
    }
