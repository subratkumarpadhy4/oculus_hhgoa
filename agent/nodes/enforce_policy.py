"""
enforce_policy.py
-----------------
Node 7: Deterministic policy enforcement to validate action authority and route (auto/L1/L2).
"""

from datetime import datetime
from agent.state import AgentState

AUTO_ACTIONS = {
    "ALLOW_TRANSACTION",
    "MONITOR_CARD",
    "MONITOR_CONNECTED_CARDS",
    "WARN_CUSTOMER",
    "VERIFY_WITH_CUSTOMER",
    "STEP_UP_AUTH",
    "GENERATE_REPORT",
    "CREATE_CASE",
    "ESCALATE_TO_ANALYST",
    "CLOSE_NO_FRAUD",
}

L1_ACTIONS = {
    "DECLINE_TRANSACTION",
}

L2_ACTIONS = {
    "BLOCK_ALL_CARDS",
    "FILE_REPORT",
}


def _extract_exposure(state: AgentState) -> float:
    """Extract exposure amount in USD from state or evidence pack."""
    if "exposure_usd" in state and state["exposure_usd"] is not None:
        try:
            return float(state["exposure_usd"])
        except (ValueError, TypeError):
            pass

    evidence_pack = state.get("evidence_pack") or {}
    txn_ctx = evidence_pack.get("transaction_context") or {}
    txns = txn_ctx.get("txn") or []
    if isinstance(txns, list) and txns:
        first_txn = txns[0]
        if isinstance(first_txn, dict):
            amt = first_txn.get("amount")
            if amt is None and "attributes" in first_txn:
                amt = first_txn.get("attributes", {}).get("amount")
            if amt is not None:
                try:
                    return float(amt)
                except (ValueError, TypeError):
                    pass
    return 0.0


def determine_authoritative_route(action_name: str, exposure_usd: float) -> str:
    """Determine the authoritative approval tier for a given action and exposure."""
    action = str(action_name).strip()
    if action == "BLOCK_CARD":
        return "L2" if exposure_usd > 2500.0 else "L1"
    elif action in AUTO_ACTIONS:
        return "auto"
    elif action in L1_ACTIONS:
        return "L1"
    elif action in L2_ACTIONS:
        return "L2"
    else:
        # Default to highest security tier for unrecognized actions
        return "L2"


def enforce_policy_node(state: AgentState) -> AgentState:
    """Enforce financial crime policy rules to assign approval route."""
    raw_actions = state.get("recommended_actions")
    if not raw_actions or not isinstance(raw_actions, list) or len(raw_actions) == 0:
        raw_actions = [{"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "No actions"}]

    exposure_usd = _extract_exposure(state)

    updated_actions = []
    tier_counts = {"auto": 0, "L1": 0, "L2": 0}

    for item in raw_actions:
        if not isinstance(item, dict):
            continue
        act_name = item.get("action", "ESCALATE_TO_ANALYST")
        authoritative_route = determine_authoritative_route(act_name, exposure_usd)
        
        # Override route with authoritative determination
        updated_item = dict(item)
        updated_item["route"] = authoritative_route
        updated_actions.append(updated_item)

        tier_counts[authoritative_route] = tier_counts.get(authoritative_route, 0) + 1

    # Overall route: highest tier required
    if tier_counts.get("L2", 0) > 0:
        overall_route = "L2"
    elif tier_counts.get("L1", 0) > 0:
        overall_route = "L1"
    else:
        overall_route = "auto"

    state["recommended_actions"] = updated_actions
    state["approval_route"] = overall_route

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "trace" not in state or not isinstance(state["trace"], list):
        state["trace"] = []

    state["trace"].append({
        "node": "enforce_policy",
        "timestamp": now_str,
        "details": f"Policy evaluated ({tier_counts['auto']} auto, {tier_counts['L1']} L1, {tier_counts['L2']} L2). Assigned overall route: '{overall_route}'. Exposure: ${exposure_usd:.2f}.",
    })

    return state

