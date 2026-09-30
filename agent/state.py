"""
state.py
--------
Defines the TypedDict state shape and constructor for the HHGoa Fraud Investigation Agent.
"""

from typing import Any, Dict, List, TypedDict


class AgentState(TypedDict):
    case_id: str                          # "HHG-001"
    trigger_type: str                     # "risk_score" | "customer_report" | "analyst_request"
    trigger_text: str
    flagged_txn_id: str
    card_id: str
    customer_id: str
    risk_score: float

    evidence_pack: Dict[str, Any]         # from collect_evidence
    llm_findings: Dict[str, Any]          # from llm_investigate
    sufficiency: str                      # "sufficient" | "insufficient" | "contradictory"
    evidence_requests: List[Dict[str, Any]]  # list of requests made

    recommended_actions: List[Dict[str, Any]]  # list of {action, route, reason}
    action_history: List[List[Dict[str, Any]]]  # one entry per recommend_action call
    approval_route: str                   # "auto" | "L1" | "L2"
    executed_actions: List[Dict[str, Any]]
    final_case_status: str                # "open" | "closed_fraud" | "closed_legitimate" | "escalated"

    evidence_rounds: int                  # counter for circuit breaker
    contradiction_cycles: int             # counter
    trace: List[Dict[str, Any]]           # list of {node, timestamp, details}

    graph_case_id: str                    # ID of InvestigationCase written to TigerGraph
    written_to_graph: bool                # whether write back completed successfully


def new_state(case_row: Dict[str, Any]) -> AgentState:
    """Build the initial AgentState from a case_pack.csv row dict."""
    risk_raw = case_row.get("risk_score", 0.0)
    try:
        risk_val = float(risk_raw) if str(risk_raw).strip() else 0.0
    except (ValueError, TypeError):
        risk_val = 0.0

    return {
        "case_id": str(case_row.get("case_id", "")).strip(),
        "trigger_type": str(case_row.get("trigger_type", "")).strip(),
        "trigger_text": str(case_row.get("trigger_text", "")).strip(),
        "flagged_txn_id": str(case_row.get("flagged_txn_id", "")).strip(),
        "card_id": str(case_row.get("card_id", "")).strip(),
        "customer_id": str(case_row.get("customer_id", "")).strip(),
        "risk_score": risk_val,

        "evidence_pack": {},
        "llm_findings": {},
        "sufficiency": "insufficient",
        "evidence_requests": [],

        "recommended_actions": [],
        "action_history": [],
        "approval_route": "auto",
        "executed_actions": [],
        "final_case_status": "open",

        "evidence_rounds": 0,
        "contradiction_cycles": 0,
        "trace": [],

        "graph_case_id": "",
        "written_to_graph": False,
    }
