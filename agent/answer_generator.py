"""
answer_generator.py
--------------------
Generates structured HHGOA submission format JSON files from agent investigation state.
"""

from datetime import datetime
from typing import Any, Dict, List

from agent.sar_generator import generate_sar_narrative
from agent.state import AgentState

KNOWN_FRAUD_PATTERNS = {
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
}


def generate_answer_file(state: AgentState) -> Dict[str, Any]:
    """Transform AgentState into the full HHGOA JSON answer format."""
    case_id = state.get("case_id", "UNKNOWN")
    flagged_txn = str(state.get("flagged_txn_id", "")).strip()
    customer_id = str(state.get("customer_id", "")).strip()
    card_id = str(state.get("card_id", "")).strip()

    evidence_pack = state.get("evidence_pack") or {}
    llm_findings = state.get("llm_findings") or {}
    findings_list = llm_findings.get("findings") or []
    hypothesis = str(llm_findings.get("fraud_type_hypothesis", "unknown")).lower()
    confidence = float(llm_findings.get("confidence", 0.0) or 0.0)

    # 1. Verdict & Status
    if hypothesis in KNOWN_FRAUD_PATTERNS:
        verdict = "fraud"
    elif hypothesis == "none":
        verdict = "legitimate"
    else:
        verdict = "uncertain"

    status = state.get("final_case_status", "open")

    # 2. Extract transaction metadata & exposure
    txn_ctx = evidence_pack.get("transaction_context") or {}
    resp_list = txn_ctx.get("response") or []
    txns = []
    if isinstance(resp_list, list) and resp_list:
        txns = resp_list[0].get("txn") or []
    elif "txn" in txn_ctx:
        txns = txn_ctx.get("txn") or []

    exposure_usd = 0.0
    activity_dates = []
    if txns and isinstance(txns, list):
        first_txn = txns[0]
        if isinstance(first_txn, dict):
            attrs = first_txn.get("attributes", {})
            amt = attrs.get("amount", first_txn.get("amount", 0.0))
            ts = attrs.get("ts", first_txn.get("ts", ""))
            try:
                exposure_usd = float(amt)
            except (ValueError, TypeError):
                pass
            if ts:
                activity_dates = [str(ts), str(ts)]

    if not exposure_usd and "exposure_usd" in state and state["exposure_usd"] is not None:
        try:
            exposure_usd = float(state["exposure_usd"])
        except (ValueError, TypeError):
            pass

    if not activity_dates:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        activity_dates = [now_iso, now_iso]

    # 3. Connected Entities (Cards & Devices)
    connected_cards = [card_id] if card_id else []
    connected_devices = []

    # Check transaction_context devices
    if isinstance(resp_list, list) and resp_list:
        ctx_devs = resp_list[0].get("devices") or []
        for d in ctx_devs:
            v_id = d.get("v_id") if isinstance(d, dict) else str(d)
            if v_id and v_id not in connected_devices:
                connected_devices.append(v_id)

    # Check connected_entities block
    conn_block = evidence_pack.get("connected_entities") or {}
    if isinstance(conn_block, dict):
        for c in conn_block.get("cards", []):
            if c and c not in connected_cards:
                connected_cards.append(c)
        for d in conn_block.get("sample_devices", conn_block.get("devices", [])):
            if d and d not in connected_devices:
                connected_devices.append(d)

    # 4. Evidence list
    evidence_items: List[Dict[str, Any]] = []
    for claim in findings_list:
        evidence_items.append({
            "claim": str(claim),
            "source": "graph",
            "ref": "llm_findings",
            "entity_ids": [customer_id, card_id] if customer_id else [card_id]
        })

    # 5. Similar prior cases
    prior_cases_info = evidence_pack.get("prior_cases") or {}
    similar_cases_list = prior_cases_info.get("similar_cases") or []
    similar_prior_cases = []
    for sc in similar_cases_list:
        if isinstance(sc, dict):
            c_id = sc.get("case_id") or sc.get("v_id")
            if c_id:
                similar_prior_cases.append(c_id)

    # 6. Summary & Pattern Description
    if findings_list:
        summary = " ".join(str(f) for f in findings_list[:4])
    else:
        summary = f"Investigation for case {case_id} concluded with hypothesis: {hypothesis}."

    pattern_desc = state.get("pattern_description", "")
    if not pattern_desc and hypothesis == "undocumented":
        pattern_desc = f"Undocumented anomaly pattern observed for customer {customer_id} on card {card_id}."

    # 7. Next Best Actions — initial (before evidence rounds) vs final (after)
    rec_actions = state.get("recommended_actions") or []
    if not rec_actions:
        rec_actions = [{"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "No actions returned."}]

    action_history = state.get("action_history") or []
    initial_actions = action_history[0] if action_history else rec_actions
    final_actions = rec_actions

    # Compute what_changed
    initial_action_names = {a.get("action") for a in initial_actions}
    final_action_names   = {a.get("action") for a in final_actions}
    added   = final_action_names - initial_action_names
    removed = initial_action_names - final_action_names
    if not added and not removed:
        what_changed = "No change — initial and final recommendations are identical."
    else:
        parts = []
        if added:
            parts.append(f"Added: {', '.join(sorted(added))}")
        if removed:
            parts.append(f"Removed: {', '.join(sorted(removed))}")
        what_changed = "; ".join(parts) + " after additional evidence was gathered."


    # 8. SAR Assessment & Narrative Generation
    file_sar = any(a.get("action") == "FILE_REPORT" for a in rec_actions)
    sar_reason = ""
    for a in rec_actions:
        if a.get("action") == "FILE_REPORT":
            sar_reason = a.get("reason", "")
            break
    if not sar_reason and file_sar:
        sar_reason = "FILE_REPORT recommended per financial crime policy."

    sar_narrative = generate_sar_narrative(state) if file_sar else ""

    subjects = []
    if customer_id:
        subjects.append(customer_id)
    if card_id:
        subjects.append(card_id)

    # 9. Latency and Tool calls from trace
    trace = state.get("trace") or []
    tool_calls = 0
    start_ts = None
    end_ts = None
    for t in trace:
        node_name = t.get("node", "")
        if node_name == "collect_evidence":
            tool_calls += 6  # standard 6 MCP tool queries
        elif node_name == "request_evidence":
            tool_calls += 1
        ts_str = t.get("timestamp")
        if ts_str:
            try:
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                if start_ts is None or dt < start_ts:
                    start_ts = dt
                if end_ts is None or dt > end_ts:
                    end_ts = dt
            except Exception:
                pass

    latency_s = round((end_ts - start_ts).total_seconds(), 2) if (start_ts and end_ts) else 0.0

    return {
        "case_id": case_id,
        "case": {
            "status": status,
            "verdict": verdict,
            "fraud_probability": confidence,
            "pattern": hypothesis,
            "pattern_description": pattern_desc,
            "affected_txn_ids": [flagged_txn] if flagged_txn else [],
            "first_suspicious_txn_id": flagged_txn,
            "connected_card_ids": connected_cards,
            "connected_device_profiles": connected_devices,
            "exposure_usd": exposure_usd,
            "evidence": evidence_items,
            "similar_prior_cases": similar_prior_cases,
            "summary": summary,
            "written_to_graph": state.get("written_to_graph", True),
            "graph_case_id": state.get("graph_case_id", case_id),
        },
        "evidence_requests": state.get("evidence_requests", []),
        "next_best_actions": {
            "initial": initial_actions,
            "final": final_actions,
            "what_changed": what_changed,
        },
        "sar": {
            "file": file_sar,
            "reason": sar_reason,
            "narrative": sar_narrative,
            "subjects": subjects,
            "total_amount_usd": exposure_usd,
            "activity_dates": activity_dates,
        },
        "stop_reason": state.get("stop_reason", "Investigation completed normally"),
        "tool_calls": tool_calls,
        "tokens": 0,
        "latency_s": latency_s,
    }
