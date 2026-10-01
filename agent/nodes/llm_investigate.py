"""
llm_investigate.py
------------------
Node 3: LLM reasoning over Evidence Pack to assess fraud hypothesis and uncertainty dimensions.
"""

import json
from datetime import datetime
from typing import Any

from agent.llm import call_llm_with_retry
from agent.state import AgentState

SYSTEM_PROMPT = """You are a fraud investigation analyst for a bank. You will be given a structured Evidence Pack
containing factual observations extracted from a graph database. Your job is to reason over the
evidence and produce a structured finding.

CRITICAL CONSTRAINTS:
- Do NOT invent facts. Every finding must trace to a specific field in the Evidence Pack.
- Do NOT claim confidence levels that the evidence does not support.
- Do NOT try to write GSQL or query the graph. All data you need is in the Evidence Pack.
- If a claim cannot be supported by the Evidence Pack, do not include it.

You must output ONLY valid JSON matching this schema:
{
  "findings": ["array of factual statements, each traceable to Evidence Pack"],
  "fraud_type_hypothesis": "card_testing | card_not_present_fraud | card_not_present_new_device | out_of_region_use | account_takeover | undocumented | none | unknown",
  "uncertainty_dimensions": {
    "graph_evidence": "none | weak | moderate | strong",
    "prior_case_match": "none | weak | moderate | strong",
    "behavioral_evidence": "none | weak | moderate | strong",
    "contradictory_evidence": "none | minor | major"
  },
  "missing_evidence": ["what would help resolve remaining uncertainty"],
  "contradictions": ["specific contradictions observed in the evidence"],
  "confidence": 0.0
}"""


def _compact_evidence_pack(pack: dict, max_chars: int = 40000) -> dict:
    compact = {}
    for k, v in pack.items():
        if k == "connected_entities" and isinstance(v, dict):
            resp_list = v.get("response", [])
            if resp_list and isinstance(resp_list, list) and isinstance(resp_list[0], dict):
                block = resp_list[0]
                txns = block.get("txns", [])
                devs = [d.get("v_id") for d in block.get("devices", [])]
                emails = [e.get("v_id") for e in block.get("emails", [])]
                regions = [r.get("v_id") for r in block.get("regions", [])]
                cards = [c.get("v_id") for c in block.get("cards", [])]
                compact["connected_entities"] = {
                    "cards": cards[:5],
                    "total_cards_count": len(cards),
                    "total_transactions_count": len(txns),
                    "sample_recent_transactions": [
                        {
                            "txn_id": t.get("v_id"),
                            "amount": t.get("attributes", {}).get("amount"),
                            "ts": t.get("attributes", {}).get("ts"),
                            "channel": t.get("attributes", {}).get("channel"),
                            "risk_score": t.get("attributes", {}).get("risk_score"),
                        }
                        for t in txns[:3]
                    ],
                    "total_devices_count": len(devs),
                    "sample_devices": devs[:3],
                    "total_emails_count": len(emails),
                    "sample_email_domains": emails[:5],
                    "total_regions_count": len(regions),
                    "sample_billing_regions": regions[:5],
                }
            else:
                compact["connected_entities"] = {"note": "no entities"}
        elif k == "prior_cases" and isinstance(v, dict):
            similar = v.get("similar", [])
            compact["prior_cases"] = {
                "count": len(similar),
                "similar": [
                    {
                        "case_id": c.get("case_id"),
                        "outcome": c.get("outcome"),
                        "pattern": c.get("pattern"),
                        "exposure_usd": c.get("exposure_usd"),
                        "analyst_notes_short": (c.get("analyst_notes_short") or "")[:150],
                    }
                    for c in similar[:3]
                ]
            }
        elif k == "detected_patterns" and isinstance(v, list):
            compact["detected_patterns"] = [
                {
                    "pattern": p.get("pattern"),
                    "strength": p.get("strength"),
                    "observations": (p.get("observations") or [])[:3],
                }
                for p in v
            ]
        else:
            compact[k] = v

    # HARD CAP
    serialized = json.dumps(compact, default=str)
    if len(serialized) > max_chars:
        print(f"[compaction] First pass: {len(serialized)} chars — dropping samples")
        if "connected_entities" in compact:
            ce = compact["connected_entities"]
            ce.pop("sample_recent_transactions", None)
            ce.pop("sample_devices", None)
            ce.pop("sample_email_domains", None)
            ce.pop("sample_billing_regions", None)
            ce.pop("cards", None)
        serialized = json.dumps(compact, default=str)
    
    if len(serialized) > max_chars:
        print(f"[compaction] Second pass: {len(serialized)} chars — minimal mode")
        compact = {
            "trigger": pack.get("trigger", {}),
            "transaction_context": compact.get("transaction_context", {}),
            "detected_patterns": [
                {"pattern": p.get("pattern"), "strength": p.get("strength")}
                for p in compact.get("detected_patterns", [])
            ],
            "prior_cases": {"count": compact.get("prior_cases", {}).get("count", 0)},
            "truncated": True,
        }
        serialized = json.dumps(compact, default=str)
    
    print(f"[compaction] Final size: {len(serialized)} chars (~{len(serialized)//4} tokens)")
    return compact


INVESTIGATION_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "items": {"type": "string"}},
        "fraud_type_hypothesis": {"type": "string", "enum": ["card_testing", "card_not_present_fraud", "card_not_present_new_device", "out_of_region_use", "account_takeover", "undocumented", "none", "unknown"]},
        "uncertainty_dimensions": {
            "type": "object",
            "properties": {
                "graph_evidence": {"type": "string", "enum": ["none", "weak", "moderate", "strong"]},
                "prior_case_match": {"type": "string", "enum": ["none", "weak", "moderate", "strong"]},
                "behavioral_evidence": {"type": "string", "enum": ["none", "weak", "moderate", "strong"]},
                "contradictory_evidence": {"type": "string", "enum": ["none", "minor", "major"]}
            },
            "required": ["graph_evidence", "prior_case_match", "behavioral_evidence", "contradictory_evidence"],
            "additionalProperties": False
        },
        "missing_evidence": {"type": "array", "items": {"type": "string"}},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"}
    },
    "required": ["findings", "fraud_type_hypothesis", "uncertainty_dimensions", "missing_evidence", "contradictions", "confidence"],
    "additionalProperties": False
}


def llm_investigate_node(state: AgentState, llm: Any = None) -> AgentState:
    """Evaluate Evidence Pack with LLM to formulate hypothesis and uncertainty assessment."""
    raw_pack = state.get("evidence_pack", {})
    evidence_pack = _compact_evidence_pack(raw_pack)

    if state.get('trigger_type') == 'customer_report':
        trigger_note = "IMPORTANT: The trigger is a CUSTOMER REPORT. The customer has already stated they did not make this transaction. Per policy R2, this is a denial. Recommend BLOCK_CARD and CREATE_CASE. Add FILE_REPORT if exposure > $1,000 or a shared device is detected."
    else:
        trigger_note = ""

    user_prompt = f"""CASE METADATA:
- Case ID: {state.get('case_id')}
- Trigger Type: {state.get('trigger_type')}
- Trigger Text: {state.get('trigger_text')}
- Flagged Txn ID: {state.get('flagged_txn_id')}
- Customer ID: {state.get('customer_id')}
- Card ID: {state.get('card_id')}
- Risk Score: {state.get('risk_score')}

{trigger_note}

EVIDENCE PACK:
{json.dumps(evidence_pack, indent=2, default=str)}
"""

    resp = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, response_schema=INVESTIGATION_SCHEMA, max_retries=2)

    if "error" in resp or not isinstance(resp, dict):
        findings = {
            "findings": ["LLM unavailable — fallback used"],
            "fraud_type_hypothesis": "unknown",
            "uncertainty_dimensions": {
                "graph_evidence": "none",
                "prior_case_match": "none",
                "behavioral_evidence": "none",
                "contradictory_evidence": "none",
            },
            "missing_evidence": ["LLM unavailable"],
            "contradictions": [],
            "confidence": 0.0,
        }
    else:
        findings = resp

    state["llm_findings"] = findings

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["trace"].append({
        "node": "llm_investigate",
        "timestamp": now_str,
        "details": f"LLM investigation complete. Hypothesis: {findings.get('fraud_type_hypothesis')}",
    })

    return state
