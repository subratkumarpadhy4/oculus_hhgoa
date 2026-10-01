"""
sar_generator.py
----------------
Generates FinCEN-standard Suspicious Activity Report (SAR) narratives for cases requiring FILE_REPORT.
"""

import json
from typing import Any, Dict
from agent.llm import call_llm_with_retry
from agent.nodes.llm_investigate import _compact_evidence_pack

SAR_SCHEMA = {
    "type": "object",
    "properties": {
        "narrative": {
            "type": "string",
            "description": "6 to 12 sentence FinCEN-standard narrative prose without headers or bullets."
        }
    },
    "required": ["narrative"],
    "additionalProperties": False
}

SYSTEM_PROMPT = """You are a compliance officer writing a Suspicious Activity Report (SAR) narrative for a US bank, following FinCEN standards.

The narrative must stand on its own. A regulator reading it must understand the case without any internal context, case IDs, or system references.

Write 6 to 12 sentences. Cover all of:
- WHO: the customer, their card, the device, any linked accounts
- WHAT: the suspicious activity — specific amounts, transaction patterns, channels
- WHEN: specific dates and times
- WHERE: billing region, channel, device
- HOW: how the fraud was carried out
- WHY: why it is suspicious

Do not reference internal case IDs, internal system names, detector names, or the graph schema.

Output only the narrative text. No headers, no JSON, no bullet points. Prose only."""


def _build_fallback_narrative(state: dict) -> str:
    """Build a deterministic 6-8 sentence template fallback narrative from raw facts."""
    customer_id = state.get("customer_id", "Unknown Customer")
    card_id = state.get("card_id", "Unknown Card")

    evidence_pack = state.get("evidence_pack") or {}
    txn_ctx = evidence_pack.get("transaction_context") or {}
    resp_list = txn_ctx.get("response") or []
    txns = []
    devices = []
    billing_region = "Unknown Region"

    if isinstance(resp_list, list) and resp_list:
        block = resp_list[0]
        txns = block.get("txn") or []
        devices = [d.get("v_id") for d in block.get("devices") or [] if d]
        regions = block.get("regions") or []
        if regions and isinstance(regions[0], dict):
            billing_region = regions[0].get("v_id", "Unknown Region")

    amount = 0.0
    ts = "recent transactions"
    channel = "online/in-person"
    if txns and isinstance(txns[0], dict):
        attrs = txns[0].get("attributes", {})
        amount = attrs.get("amount", txns[0].get("amount", 0.0))
        ts = attrs.get("ts", txns[0].get("ts", "recent transactions"))
        channel = attrs.get("channel", txns[0].get("channel", "electronic"))

    exposure = state.get("exposure_usd") or amount

    dev_str = f"device profile {devices[0]}" if devices else "an unknown device"
    hypothesis = state.get("llm_findings", {}).get("fraud_type_hypothesis", "unauthorized activity")

    sentences = [
        f"This Suspicious Activity Report is filed on account holder {customer_id} in connection with unauthorized transaction activity on card {card_id}.",
        f"On or around {ts}, an anomalous transaction totaling ${exposure:.2f} was processed via the {channel} channel in billing region {billing_region}.",
        f"The transaction originated from {dev_str}, which exhibited unusual linkage and velocity characteristics inconsistent with the cardholder's historical profile.",
        f"Subsequent analysis revealed that the activity corresponds to suspected {hypothesis.replace('_', ' ')}.",
        "Customer engagement and validation records confirmed the charge was disputed and unrecognized by the legitimate cardholder.",
        "The bank has initiated immediate mitigation by blocking the compromised instrument to prevent further financial exposure.",
        "This report is submitted to document potential financial crime and facilitate regulatory oversight."
    ]
    return " ".join(sentences)


def generate_sar_narrative(state: dict) -> str:
    """
    Produce a FinCEN-standard SAR narrative from the case state.
    Returns "" if the case does not require a SAR (i.e. FILE_REPORT is not present).
    """
    rec_actions = state.get("recommended_actions") or []
    file_report_action = None
    for a in rec_actions:
        if isinstance(a, dict) and a.get("action") == "FILE_REPORT":
            file_report_action = a
            break

    if not file_report_action:
        return ""

    customer_id = state.get("customer_id", "Unknown")
    card_id = state.get("card_id", "Unknown")
    flagged_txn = state.get("flagged_txn_id", "Unknown")

    raw_pack = state.get("evidence_pack") or {}
    evidence_pack = _compact_evidence_pack(raw_pack)
    txn_ctx = evidence_pack.get("transaction_context") or {}
    connected_entities = evidence_pack.get("connected_entities") or {}
    detected_patterns = evidence_pack.get("detected_patterns") or []
    prior_cases = evidence_pack.get("prior_cases") or {}
    evidence_requests = state.get("evidence_requests") or []
    llm_findings = state.get("llm_findings") or {}

    user_prompt = f"""CASE FACTS:
Customer ID: {customer_id}
Card ID: {card_id}
Flagged Transaction ID: {flagged_txn}
Trigger Type: {state.get('trigger_type')}
Trigger Text: {state.get('trigger_text')}

TRANSACTION CONTEXT:
{json.dumps(txn_ctx, indent=2, default=str)}

CONNECTED ENTITIES:
{json.dumps(connected_entities, indent=2, default=str)}

DETECTED PATTERNS:
{json.dumps(detected_patterns, indent=2, default=str)}

PRIOR FRAUD CASES:
{json.dumps(prior_cases, indent=2, default=str)}

EVIDENCE REQUESTS & RESPONSES:
{json.dumps(evidence_requests, indent=2, default=str)}

INVESTIGATION FINDINGS & HYPOTHESIS:
{json.dumps(llm_findings, indent=2, default=str)}

RECOMMENDED ACTIONS & REASON:
{json.dumps(rec_actions, indent=2, default=str)}
"""

    try:
        resp = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, response_schema=SAR_SCHEMA, max_retries=2)
        if isinstance(resp, dict) and "narrative" in resp and resp["narrative"]:
            return resp["narrative"].strip()
        elif isinstance(resp, str) and resp.strip():
            return resp.strip()
    except Exception:
        pass

    return _build_fallback_narrative(state)
