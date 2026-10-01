"""
request_evidence.py
-------------------
Node 5: Requests additional evidence or customer confirmation when evidence is insufficient.
Uses deterministic mock APIs to simulate responses based on LLM missing evidence analysis.
"""

from datetime import datetime
from agent.mock_apis import (
    request_analyst_review,
    request_customer_validation,
    request_device_fingerprint,
    request_kyc_reverification,
    request_step_up_auth,
    request_transaction_history_extension,
)
from agent.state import AgentState


def _map_missing_to_request(item_text: str, case_id: str) -> dict:
    """Map a missing evidence description to one of six mock API calls."""
    text_lower = item_text.lower()
    if "kyc" in text_lower:
        res = request_kyc_reverification(case_id)
    elif "device" in text_lower:
        res = request_device_fingerprint(case_id)
    elif "history" in text_lower or "additional_transactions" in text_lower or "past transactions" in text_lower:
        res = request_transaction_history_extension(case_id)
    elif "auth" in text_lower or "step_up" in text_lower or "mfa" in text_lower:
        res = request_step_up_auth(case_id)
    elif "analyst" in text_lower or "human" in text_lower:
        res = request_analyst_review(case_id)
    else:
        # Defaults to customer confirmation / validation
        res = request_customer_validation(case_id)

    return res


def request_evidence_node(state: AgentState) -> AgentState:
    """Simulate requesting additional evidence from customer or analyst based on missing evidence."""
    if "evidence_requests" not in state or not isinstance(state["evidence_requests"], list):
        state["evidence_requests"] = []

    case_id = state.get("case_id", "UNKNOWN")
    current_round = state.get("evidence_rounds", 1)

    llm_findings = state.get("llm_findings") or {}
    missing_evidence = llm_findings.get("missing_evidence") or []

    # If missing_evidence is empty, create a general customer validation request
    if not missing_evidence:
        missing_evidence = ["customer_confirmation"]

    new_requests_count = 0
    for item in missing_evidence:
        # Cap total requests at 3 per case
        if len(state["evidence_requests"]) >= 3:
            break

        api_res = _map_missing_to_request(str(item), case_id)
        req_entry = {
            "type": api_res.get("type"),
            "asked_after_step": current_round,
            "assumed_response": api_res.get("response"),
            "requested_from_missing": str(item),
        }
        if "extra_transactions" in api_res:
            req_entry["extra_transactions"] = api_res["extra_transactions"]

        state["evidence_requests"].append(req_entry)
        new_requests_count += 1

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "trace" not in state or not isinstance(state["trace"], list):
        state["trace"] = []

    state["trace"].append({
        "node": "request_evidence",
        "timestamp": now_str,
        "details": f"Generated {new_requests_count} evidence request(s) at round {current_round} (total requests: {len(state['evidence_requests'])}).",
    })

    return state

