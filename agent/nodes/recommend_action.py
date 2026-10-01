"""
recommend_action.py
--------------------
Node 6: LLM recommends next best actions based on consolidated evidence pack and findings.
"""

import json
from datetime import datetime
from typing import Any

from agent.llm import call_llm_with_retry
from agent.nodes.llm_investigate import _compact_evidence_pack
from agent.state import AgentState

SYSTEM_PROMPT = """You are a fraud investigator deciding on the next best action for a case.

IMPORTANT: You may recommend MULTIPLE actions. If the evidence supports more than one action, list them all in order of priority (most urgent first). Do not limit yourself to a single action. Examples of when to recommend multiple actions:
- If the customer has prior fraud cases AND the current transaction is suspicious: recommend MONITOR_CARD + VERIFY_WITH_CUSTOMER + CREATE_CASE
- If the customer denies the transaction: recommend BLOCK_CARD + CREATE_CASE (and FILE_REPORT if exposure > $1,000 or shared device)
- If a shared device ring is detected: recommend BLOCK_CARD + CREATE_CASE + FILE_REPORT + MONITOR_CONNECTED_CARDS

Review the entire Evidence Pack before deciding. The presence of prior_cases, detected_patterns, or connected_entities should each influence the action set.

You must recommend one or more actions from this fixed vocabulary. Do NOT invent new actions:

ALLOW_TRANSACTION, DECLINE_TRANSACTION, MONITOR_CARD, MONITOR_CONNECTED_CARDS,
WARN_CUSTOMER, VERIFY_WITH_CUSTOMER, STEP_UP_AUTH, BLOCK_CARD, BLOCK_ALL_CARDS,
GENERATE_REPORT, CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST, CLOSE_NO_FRAUD

Approval routes:
- "auto" — the agent may execute directly
- "L1" — team lead approval required
- "L2" — fraud manager approval required

Rules you must follow (from the bank's fraud policy):
- R1: If evidence rests on a single signal and probability < 0.70, use VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any block.
- R2: If customer denies the transaction, recommend BLOCK_CARD and CREATE_CASE. Add FILE_REPORT if exposure > $1,000 or shared device.
- R3: If customer confirms the transaction, recommend CLOSE_NO_FRAUD.
- R4: If no reply within 24 hours, recommend MONITOR_CARD and DECLINE_TRANSACTION for pending authorizations.
- R5: Card testing (3+ small authorizations then larger purchase) → DECLINE_TRANSACTION and STEP_UP_AUTH.
- R6: Shared origin across cards → name it, CREATE_CASE, FILE_REPORT, MONITOR_CONNECTED_CARDS.
- R7: Disputed but legitimate recurring charge → CREATE_CASE, VERIFY_WITH_CUSTOMER, WARN_CUSTOMER. Do not block.
- R8: If verdict is uncertain and exposure > $500, recommend ESCALATE_TO_ANALYST.
- R9: Undocumented pattern → CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST.
- R10: Never BLOCK_ALL_CARDS unless 2+ cards confirmed fraud.

WORKED EXAMPLES:

Example 1 (prior fraud history + weak current signal):
- Case: risk_score 0.61, customer has 4 prior confirmed fraud cases on this card, current transaction is $77 in_person with no device
- Expected actions:
  - MONITOR_CARD (auto) — R6: prior fraud history warrants monitoring
  - VERIFY_WITH_CUSTOMER (auto) — R1: current transaction is a single signal
  - CREATE_CASE (auto) — R6: internal case for ongoing pattern

Example 2 (customer denial):
- Case: customer_report, customer says they did not make the transaction, exposure $500
- Expected actions:
  - BLOCK_CARD (L1) — R2: customer denied
  - CREATE_CASE (auto) — R2: internal case required

Example 3 (shared device ring):
- Case: NewDeviceWithProxy strong, device shared across 5 cards, exposure $2,800
- Expected actions:
  - BLOCK_CARD (L2) — R6: shared ring, exposure > $2,500
  - CREATE_CASE (auto) — R6: internal case
  - FILE_REPORT (L2) — R6: coordinated ring requires SAR
  - MONITOR_CONNECTED_CARDS (auto) — R6: other cards on same device

You must output ONLY valid JSON matching this schema:
{
  "recommended_actions": [
    {
      "action": "ACTION_NAME",
      "route": "auto | L1 | L2",
      "reason": "cite the specific policy rule (R1-R10) and the evidence"
    }
  ],
  "overall_reasoning": "one or two sentences on why these actions follow from the evidence"
}

If the evidence is insufficient to support any action, recommend ESCALATE_TO_ANALYST."""




ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "recommended_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["ALLOW_TRANSACTION", "DECLINE_TRANSACTION", "MONITOR_CARD", "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH", "BLOCK_CARD", "BLOCK_ALL_CARDS", "GENERATE_REPORT", "CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD"]},
                    "route": {"type": "string", "enum": ["auto", "L1", "L2"]},
                    "reason": {"type": "string"}
                },
                "required": ["action", "route", "reason"],
                "additionalProperties": False
            }
        },
        "overall_reasoning": {"type": "string"}
    },
    "required": ["recommended_actions", "overall_reasoning"],
    "additionalProperties": False
}


def recommend_action_node(state: AgentState, llm: Any = None) -> AgentState:
    """Generate recommended policy-compliant actions using Groq LLM."""
    raw_pack = state.get("evidence_pack", {})
    evidence_pack = _compact_evidence_pack(raw_pack)
    llm_findings = state.get("llm_findings", {})
    sufficiency = state.get("sufficiency", "insufficient")

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

SUFFICIENCY STATUS: {sufficiency}

LLM FINDINGS:
{json.dumps(llm_findings, indent=2, default=str)}

EVIDENCE PACK:
{json.dumps(evidence_pack, indent=2, default=str)}
"""

    resp = call_llm_with_retry(SYSTEM_PROMPT, user_prompt, response_schema=ACTION_SCHEMA, max_retries=2)

    if "error" in resp or not isinstance(resp, dict) or "recommended_actions" not in resp:
        rec_actions = [
            {"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": f"LLM unavailable or invalid output: {resp.get('error', 'unknown error')}"}
        ]
    else:
        rec_actions = resp.get("recommended_actions", [])
        if not isinstance(rec_actions, list) or len(rec_actions) == 0:
            rec_actions = [{"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "No actions returned by LLM."}]

    state.setdefault("action_history", []).append(rec_actions)
    state["recommended_actions"] = rec_actions

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["trace"].append({
        "node": "recommend_action",
        "timestamp": now_str,
        "details": f"Generated {len(rec_actions)} recommended action(s) via LLM reasoning.",
    })

    return state
