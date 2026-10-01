"""
write_back.py
-------------
Node 9: Writes investigation findings, evidence vertices, and resolved case records back to the graph.
"""

import os
from datetime import datetime
from typing import Any
from dotenv import load_dotenv
from pyTigerGraph import TigerGraphConnection

from agent.mcp_client import MCPClient
from agent.state import AgentState

load_dotenv(r"C:\HHGoa\.env")

_CONN = None


def _get_tg_conn() -> TigerGraphConnection:
    """Get or create singleton TigerGraph connection."""
    global _CONN
    if _CONN is None:
        _CONN = TigerGraphConnection(
            host=os.getenv("TG_HOST", "http://localhost"),
            graphname=os.getenv("TG_GRAPHNAME", "HHGoa"),
            username=os.getenv("TG_USERNAME", "tigergraph"),
            password=os.getenv("TG_PASSWORD", "tigergraph"),
        )
    return _CONN


KNOWN_FRAUD_PATTERNS = {
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
}


def write_back_node(state: AgentState, mcp: MCPClient = None) -> AgentState:
    """Persist case decisions, evidence vertices, and resolved case records back to TigerGraph."""
    case_id = state.get("case_id", "UNKNOWN")
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Derive verdict and status
    llm_findings = state.get("llm_findings") or {}
    hypothesis = str(llm_findings.get("fraud_type_hypothesis", "unknown")).lower()
    confidence = float(llm_findings.get("confidence", 0.0) or 0.0)
    findings_list = llm_findings.get("findings") or []
    sufficiency = state.get("sufficiency", "insufficient")

    if hypothesis in KNOWN_FRAUD_PATTERNS:
        verdict = "fraud"
    elif hypothesis == "none":
        verdict = "legitimate"
    else:
        verdict = "uncertain"

    if sufficiency == "contradictory":
        final_status = "escalated"
    elif verdict == "fraud":
        final_status = "closed_fraud"
    elif verdict == "legitimate":
        final_status = "closed_legitimate"
    else:
        final_status = "open"

    state["final_case_status"] = final_status

    # 2. Extract exposure
    exposure_usd = 0.0
    if "exposure_usd" in state and state["exposure_usd"] is not None:
        try:
            exposure_usd = float(state["exposure_usd"])
        except (ValueError, TypeError):
            pass
    else:
        evidence_pack = state.get("evidence_pack") or {}
        txn_ctx = evidence_pack.get("transaction_context") or {}
        resp_list = txn_ctx.get("response") or []
        txns = []
        if isinstance(resp_list, list) and resp_list:
            txns = resp_list[0].get("txn") or []
        elif "txn" in txn_ctx:
            txns = txn_ctx.get("txn") or []

        if isinstance(txns, list) and txns:
            first_txn = txns[0]
            if isinstance(first_txn, dict):
                amt = first_txn.get("amount")
                if amt is None and "attributes" in first_txn:
                    amt = first_txn.get("attributes", {}).get("amount")
                if amt is not None:
                    try:
                        exposure_usd = float(amt)
                    except (ValueError, TypeError):
                        pass

    # 3. Summary
    summary = ""
    if findings_list:
        summary = " | ".join(str(f) for f in findings_list[:3])
    if not summary:
        summary = f"Investigation for {case_id} concluded with hypothesis: {hypothesis}."

    # 4. Perform TigerGraph writes
    evidence_count = 0
    resolved_written = False
    errors = []

    try:
        conn = _get_tg_conn()

        # a. Upsert InvestigationCase vertex
        inv_case_attrs = {
            "opened_at": now_str,
            "trigger_type": state.get("trigger_type", ""),
            "trigger_text": state.get("trigger_text", ""),
            "status": final_status,
            "verdict": verdict,
            "fraud_probability": confidence,
            "pattern": hypothesis,
            "pattern_description": state.get("pattern_description", ""),
            "exposure_usd": exposure_usd,
            "summary": summary,
            "stop_reason": state.get("stop_reason", "Investigation completed normally"),
            "written_to_graph": True,
        }
        conn.upsertVertex("InvestigationCase", case_id, attributes=inv_case_attrs)

        # b. Link InvestigationCase to flagged Transaction via INVESTIGATES
        flagged_txn = str(state.get("flagged_txn_id", "")).strip()
        if flagged_txn:
            conn.upsertEdge("InvestigationCase", case_id, "INVESTIGATES", "Transaction", flagged_txn)

        # c. Upsert Evidence vertices & link via HAS_EVIDENCE
        for i, claim_text in enumerate(findings_list, 1):
            ev_id = f"{case_id}-E{i}"
            ev_attrs = {
                "claim": str(claim_text),
                "source": "graph",
                "ref": "llm_findings",
                "entity_ids": f"{state.get('customer_id', '')},{state.get('card_id', '')}",
            }
            conn.upsertVertex("Evidence", ev_id, attributes=ev_attrs)
            conn.upsertEdge("InvestigationCase", case_id, "HAS_EVIDENCE", "Evidence", ev_id)
            evidence_count += 1

        # d. If case is closed, create ResolvedCase & link
        if final_status.startswith("closed_"):
            resolved_id = f"R-{case_id}"
            res_attrs = {
                "original_case_id": case_id,
                "closed_at": now_str,
                "outcome": verdict,
                "pattern": hypothesis,
                "exposure_usd": exposure_usd,
                "summary": summary,
                "status": "active_memory",
                "superseded_by": "",
            }
            conn.upsertVertex("ResolvedCase", resolved_id, attributes=res_attrs)
            conn.upsertEdge("InvestigationCase", case_id, "RESOLVED_AS", "ResolvedCase", resolved_id)

            # Optional pattern & entity links
            if hypothesis != "none":
                try:
                    conn.upsertEdge("ResolvedCase", resolved_id, "MATCHED_PATTERN", "DocumentedPattern", hypothesis)
                except Exception as p_err:
                    errors.append(f"MATCHED_PATTERN edge: {p_err}")

            cust_id = str(state.get("customer_id", "")).strip()
            if cust_id:
                try:
                    conn.upsertEdge("ResolvedCase", resolved_id, "INVOLVED_ENTITY_CUSTOMER", "Customer", cust_id)
                except Exception as c_err:
                    errors.append(f"INVOLVED_ENTITY_CUSTOMER edge: {c_err}")

            card_id = str(state.get("card_id", "")).strip()
            if card_id:
                try:
                    conn.upsertEdge("ResolvedCase", resolved_id, "INVOLVED_ENTITY_CARD", "Card", card_id)
                except Exception as k_err:
                    errors.append(f"INVOLVED_ENTITY_CARD edge: {k_err}")

            resolved_written = True

        state["graph_case_id"] = case_id
        state["written_to_graph"] = True

    except Exception as exc:
        errors.append(str(exc))
        state["written_to_graph"] = False

    # Trace log
    err_msg = f" Errors: {', '.join(errors)}" if errors else ""
    trace_msg = f"Wrote InvestigationCase '{case_id}' (status={final_status}, verdict={verdict}). Evidence vertices: {evidence_count}. ResolvedCase written: {resolved_written}.{err_msg}"

    if "trace" not in state or not isinstance(state["trace"], list):
        state["trace"] = []

    state["trace"].append({
        "node": "write_back",
        "timestamp": now_str,
        "details": trace_msg,
    })

    return state

