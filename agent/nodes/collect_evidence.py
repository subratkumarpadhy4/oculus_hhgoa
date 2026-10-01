"""
collect_evidence.py
-------------------
Node 2: Collects multi-hop graph neighborhood, pattern signals, and prior case memory via MCP tools.
"""

from datetime import datetime
from agent.mcp_client import MCPClient
from agent.state import AgentState


def collect_evidence_node(state: AgentState, mcp: MCPClient = None) -> AgentState:
    """Query graph neighborhood, pattern detectors, and case memory to build Evidence Pack."""
    if mcp is None:
        mcp = MCPClient()

    txn_id = state["flagged_txn_id"]
    customer_id = state["customer_id"]

    # 1. Transaction neighborhood
    txn_context = mcp.get_transaction_context(txn_id)

    # 2. Connected entities for customer
    connected_entities = mcp.find_connected_entities(customer_id)

    # 3. Prior similar cases from closed case memory
    prior_cases = mcp.find_similar_cases(customer_id, entity_type="customer", k=5)

    # 4. Pattern detectors
    patterns = ["SharedDeviceRing", "VelocityBurst", "AmountAnomaly", "NewDeviceWithProxy"]
    detected_patterns = []
    for pat in patterns:
        res = mcp.detect_pattern(txn_id, pat)
        detected_patterns.append(res)

    evidence_pack = {
        "trigger": {
            "case_id": state["case_id"],
            "trigger_type": state["trigger_type"],
            "trigger_text": state["trigger_text"],
            "flagged_txn_id": txn_id,
            "card_id": state["card_id"],
            "customer_id": customer_id,
            "risk_score": state["risk_score"],
        },
        "transaction_context": txn_context,
        "connected_entities": connected_entities,
        "detected_patterns": detected_patterns,
        "prior_cases": prior_cases,
        "missing_evidence": [],
        "contradictions": [],
    }

    state["evidence_pack"] = evidence_pack

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["trace"].append({
        "node": "collect_evidence",
        "timestamp": now_str,
        "details": (
            f"Evidence Pack assembled for txn {txn_id}. "
            f"Evaluated {len(detected_patterns)} patterns, retrieved {prior_cases.get('count', 0)} prior cases."
        ),
    })

    return state
