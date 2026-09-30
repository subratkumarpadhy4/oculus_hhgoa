"""
custom_tools.py
---------------
Extends the official tigergraph-mcp server with fraud-investigation-specific
tools for the HHGoa graph.

Three tools are defined and registered:

  1. get_transaction_context  - full neighbourhood of a single transaction
  2. find_connected_entities  - all entities reachable from a customer
  3. detect_pattern           - pattern-strength assessment for a transaction

Registration mechanism
----------------------
The tigergraph_mcp package exposes its tool list as
``tigergraph_mcp.tools.tool_registry._ALL_TOOLS``, a plain ``List[Tool]``.
Appending ``mcp_types.Tool`` objects to that list before the MCP server is
started is the supported extension point.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any, Dict, List

import pyTigerGraph as tg

import tigergraph_mcp.tools.tool_registry as _registry
from mcp_types import Tool


# -- .env loader --------------------------------------------------------------
def _load_env(env_path: str = r"C:\HHGoa\.env") -> Dict[str, str]:
    env: Dict[str, str] = {}
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    return env


# -- Shared connection (Cached Singleton) -------------------------------------
_CONN: tg.TigerGraphConnection | None = None


def _get_sync_conn() -> tg.TigerGraphConnection:
    global _CONN
    if _CONN is not None:
        return _CONN
    env = _load_env()
    conn = tg.TigerGraphConnection(
        host=env.get("TG_HOST", "http://localhost"),
        graphname=env.get("TG_GRAPHNAME", "HHGoa"),
        username=env.get("TG_USERNAME", "tigergraph"),
        password=env.get("TG_PASSWORD", "tigergraph"),
    )
    try:
        conn.getToken(conn.createSecret())
    except Exception:
        pass
    _CONN = conn
    return _CONN


# =============================================================================
# Tool 1 - get_transaction_context
# =============================================================================
def get_transaction_context(txn_id: str) -> Dict[str, Any]:
    """Return the full neighbourhood of a single Transaction vertex."""
    conn = _get_sync_conn()

    gsql = f"""
INTERPRET QUERY () FOR GRAPH HHGoa {{
  seed = {{Transaction.*}};
  txn  = SELECT t FROM seed:t WHERE t.txn_id == "{txn_id}" LIMIT 1;

  cards     = SELECT c  FROM txn:t  -(MADE_REVERSE)-  Card:c;
  customers = SELECT cu FROM cards:c -(OWNS_REVERSE)- Customer:cu;
  devices   = SELECT d  FROM txn:t  -(FROM_DEVICE)-   DeviceProfile:d;
  emails    = SELECT em FROM txn:t  -(PURCHASER_EMAIL)- EmailDomain:em;
  regions   = SELECT r  FROM txn:t  -(BILLED_IN)-     BillingRegion:r;

  PRINT txn, cards, customers, devices, emails, regions;
}}
"""
    try:
        resp = conn.runInterpretedQuery(gsql)
        return {
            "txn_id":   txn_id,
            "response": resp,
        }
    except Exception as exc:
        return {"txn_id": txn_id, "error": str(exc)}


# =============================================================================
# Tool 2 - find_connected_entities
# =============================================================================
def find_connected_entities(customer_id: str) -> Dict[str, Any]:
    """Return all entities reachable from a Customer vertex."""
    conn = _get_sync_conn()

    gsql = f"""
INTERPRET QUERY () FOR GRAPH HHGoa {{
  seed = {{Customer.*}};
  cust = SELECT c FROM seed:c WHERE c.customer_id == "{customer_id}" LIMIT 1;

  cards   = SELECT c FROM cust:cu  -(OWNS)-   Card:c;
  txns    = SELECT t FROM cards:c  -(MADE)-   Transaction:t;
  devices = SELECT d FROM txns:t   -(FROM_DEVICE)- DeviceProfile:d;
  emails  = SELECT em FROM txns:t  -(PURCHASER_EMAIL)- EmailDomain:em;
  regions = SELECT r FROM txns:t   -(BILLED_IN)- BillingRegion:r;

  PRINT cust, cards, txns, devices, emails, regions;
}}
"""
    try:
        resp = conn.runInterpretedQuery(gsql)
        return {
            "customer_id": customer_id,
            "response":    resp,
        }
    except Exception as exc:
        return {"customer_id": customer_id, "error": str(exc)}


# =============================================================================
# Tool 3 - detect_pattern  (real implementations)
# =============================================================================

def _detect_shared_device_ring(conn, seed_txn_id: str) -> Dict[str, Any]:
    """Detect when a device is shared across multiple distinct customer accounts.

    Uses GSQL to:
    1. Find the DeviceProfile of the seed transaction (FROM_DEVICE edge).
       If none exists (in-person), returns strength "none".
    2. Walk FROM_DEVICE_REVERSE to all transactions on that device.
    3. Walk MADE_REVERSE -> Card -> OWNS_REVERSE -> Customer to collect
       distinct customer IDs and card IDs via SetAccum.
    4. Applies strength thresholds and returns observations.
    """
    gsql = f"""INTERPRET QUERY () FOR GRAPH HHGoa {{
  SetAccum<STRING> @@customer_ids;
  SetAccum<STRING> @@card_ids;
  SumAccum<INT>    @@total_txns;
  SumAccum<INT>    @@has_device;

  seed     = {{Transaction.*}};
  txn      = SELECT t FROM seed:t WHERE t.txn_id == "{seed_txn_id}";
  devices  = SELECT d FROM txn:t -(FROM_DEVICE:e)- DeviceProfile:d
             ACCUM @@has_device += 1;

  dev_txns = SELECT t2 FROM devices:d -(FROM_DEVICE_REVERSE:e)- Transaction:t2
             ACCUM @@total_txns += 1;

  dev_cards = SELECT c FROM dev_txns:t2 -(MADE_REVERSE:e)- Card:c
              ACCUM @@card_ids += c.card_id;

  dev_custs = SELECT cu FROM dev_cards:c -(OWNS_REVERSE:e)- Customer:cu
              ACCUM @@customer_ids += cu.customer_id;

  PRINT @@has_device, @@total_txns, @@customer_ids, @@card_ids;
  PRINT devices[devices.device_id];
}}"""
    try:
        resp = conn.runInterpretedQuery(gsql)
    except Exception as exc:
        return {"pattern": "SharedDeviceRing", "strength": "weak",
                "observations": [], "error": str(exc)}

    # Parse response
    has_device = 0
    total_txns = 0
    customer_ids: List[str] = []
    card_ids: List[str] = []
    device_id = ""
    for block in resp:
        if "@@has_device"    in block: has_device   = block["@@has_device"]
        if "@@total_txns"    in block: total_txns   = block["@@total_txns"]
        if "@@customer_ids"  in block: customer_ids = block["@@customer_ids"]
        if "@@card_ids"      in block: card_ids      = block["@@card_ids"]
        if "devices"         in block and block["devices"]:
            device_id = block["devices"][0].get("v_id", "")

    if has_device == 0:
        return {
            "pattern":      "SharedDeviceRing",
            "strength":     "none",
            "observations": ["No device — in-person transaction (no FROM_DEVICE edge)."],
        }

    n_customers = len(customer_ids)
    n_cards     = len(card_ids)

    if   n_customers >= 5 and total_txns >= 10: strength = "strong"
    elif n_customers >= 3 and total_txns >= 5:  strength = "moderate"
    elif n_customers >= 2:                      strength = "weak"
    else:                                       strength = "none"

    return {
        "pattern":  "SharedDeviceRing",
        "strength": strength,
        "observations": [
            f"Device {device_id} shared across {n_customers} distinct customer(s)",
            f"{total_txns} transaction(s) on this device",
            f"{n_cards} distinct card(s) on this device",
        ],
    }


def _detect_velocity_burst(conn, seed_txn_id: str) -> Dict[str, Any]:
    """Detect an abnormal burst of transactions on the same card within a short window.

    Uses GSQL to:
    1. Get the card of the seed transaction (MADE_REVERSE edge).
    2. Capture the seed transaction's epoch timestamp via datetime_to_epoch().
    3. Walk MADE to all card transactions, accumulating counts for those
       within +/-1 hour and +/-24 hours of the seed's timestamp using IF-in-ACCUM.
    4. Applies velocity thresholds and returns observations.
    """
    gsql = f"""INTERPRET QUERY () FOR GRAPH HHGoa {{
  SumAccum<INT> @@seed_epoch;
  SumAccum<INT> @@txns_in_1h;
  SumAccum<INT> @@txns_in_24h;
  SumAccum<INT> @@total_on_card;

  seed       = {{Transaction.*}};
  txn        = SELECT t FROM seed:t WHERE t.txn_id == "{seed_txn_id}";
  epoch_step = SELECT t FROM txn:t ACCUM @@seed_epoch += datetime_to_epoch(t.ts);
  cards      = SELECT c FROM txn:t -(MADE_REVERSE:e)- Card:c;

  all_txns   = SELECT t2 FROM cards:c -(MADE:e)- Transaction:t2
               ACCUM
                 @@total_on_card += 1,
                 IF abs(datetime_to_epoch(t2.ts) - @@seed_epoch) <= 3600
                   THEN @@txns_in_1h += 1 END,
                 IF abs(datetime_to_epoch(t2.ts) - @@seed_epoch) <= 86400
                   THEN @@txns_in_24h += 1 END;

  PRINT cards[cards.card_id];
  PRINT @@total_on_card, @@txns_in_1h, @@txns_in_24h;
}}"""
    try:
        resp = conn.runInterpretedQuery(gsql)
    except Exception as exc:
        return {"pattern": "VelocityBurst", "strength": "weak",
                "observations": [], "error": str(exc)}

    # Parse response
    txns_1h   = 0
    txns_24h  = 0
    total     = 0
    card_id   = ""
    for block in resp:
        if "@@txns_in_1h"    in block: txns_1h  = block["@@txns_in_1h"]
        if "@@txns_in_24h"   in block: txns_24h = block["@@txns_in_24h"]
        if "@@total_on_card" in block: total    = block["@@total_on_card"]
        if "cards" in block and block["cards"]:
            card_id = block["cards"][0].get("v_id", "")

    if   txns_1h >= 5: strength = "strong"
    elif txns_1h >= 3: strength = "moderate"
    elif txns_1h >= 2: strength = "weak"
    else:              strength = "none"

    return {
        "pattern":  "VelocityBurst",
        "strength": strength,
        "observations": [
            f"{txns_1h} transaction(s) on card {card_id} within 1 hour of seed",
            f"{txns_24h} transaction(s) within 24 hours of seed",
            f"{total} total transaction(s) on this card in the graph",
        ],
    }


def _detect_amount_anomaly(conn, seed_txn_id: str) -> Dict[str, Any]:
    """Detect when a transaction amount is a statistical outlier for its card.

    Uses GSQL to:
    1. Capture the seed transaction's amount via SumAccum.
    2. Get the card (MADE_REVERSE edge).
    3. Walk MADE to all card transactions and compute the average amount
       using AvgAccum and count using SumAccum<INT>.
    4. Computes ratio = seed_amount / avg_amount and applies thresholds.
    """
    gsql = f"""INTERPRET QUERY () FOR GRAPH HHGoa {{
  SumAccum<DOUBLE> @@seed_amount;
  AvgAccum         @@avg_amount;
  SumAccum<INT>    @@txn_count;

  seed      = {{Transaction.*}};
  txn       = SELECT t FROM seed:t WHERE t.txn_id == "{seed_txn_id}";
  amt_step  = SELECT t FROM txn:t ACCUM @@seed_amount += t.amount;
  cards     = SELECT c FROM txn:t -(MADE_REVERSE:e)- Card:c;
  all_txns  = SELECT t2 FROM cards:c -(MADE:e)- Transaction:t2
              ACCUM @@avg_amount += t2.amount, @@txn_count += 1;

  PRINT cards[cards.card_id];
  PRINT @@seed_amount, @@avg_amount, @@txn_count;
}}"""
    try:
        resp = conn.runInterpretedQuery(gsql)
    except Exception as exc:
        return {"pattern": "AmountAnomaly", "strength": "weak",
                "observations": [], "error": str(exc)}

    # Parse response
    seed_amount = 0.0
    avg_amount  = 0.0
    txn_count   = 0
    card_id     = ""
    for block in resp:
        if "@@seed_amount" in block: seed_amount = float(block["@@seed_amount"])
        if "@@avg_amount"  in block: avg_amount  = float(block["@@avg_amount"])
        if "@@txn_count"   in block: txn_count   = int(block["@@txn_count"])
        if "cards" in block and block["cards"]:
            card_id = block["cards"][0].get("v_id", "")

    if avg_amount == 0.0:
        return {
            "pattern":      "AmountAnomaly",
            "strength":     "none",
            "observations": ["Card has no transaction history to compare against."],
        }

    ratio = seed_amount / avg_amount

    if   ratio >= 10 and txn_count >= 5: strength = "strong"
    elif ratio >= 5  and txn_count >= 5: strength = "moderate"
    elif ratio >= 3  and txn_count >= 3: strength = "weak"
    else:                                strength = "none"

    return {
        "pattern":  "AmountAnomaly",
        "strength": strength,
        "observations": [
            f"Seed amount: ${seed_amount:.2f}",
            f"Card average: ${avg_amount:.2f} across {txn_count} transaction(s) on card {card_id}",
            f"Ratio: {ratio:.1f}x",
        ],
    }


def _detect_new_device_with_proxy(conn, seed_txn_id: str) -> Dict[str, Any]:
    """Detect card-not-present fraud from a new device (and optional proxy).

    Uses GSQL to:
    1. Fetch the transaction and its device (via FROM_DEVICE edge).
       If no device, return strength "none".
    2. Check device.is_new_for_account (BOOL) and device.proxy_type (STRING).
    3. Count how many distinct customers use this device_id
       (via FROM_DEVICE_REVERSE -> MADE_REVERSE -> OWNS_REVERSE).
    4. Evaluates strength:
       - is_new == True AND proxy contains "PROXY" -> "strong"
       - is_new == True AND proxy is empty -> "moderate"
       - is_new == False AND proxy contains "PROXY" -> "moderate"
       - Else -> "none"
    """
    gsql = f"""INTERPRET QUERY () FOR GRAPH HHGoa {{
  SetAccum<STRING> @@customer_ids;
  SumAccum<INT> @@has_device;

  seed     = {{Transaction.*}};
  txn      = SELECT t FROM seed:t WHERE t.txn_id == "{seed_txn_id}";
  devices  = SELECT d FROM txn:t -(FROM_DEVICE:e)- DeviceProfile:d
             ACCUM @@has_device += 1;

  dev_txns = SELECT t2 FROM devices:d -(FROM_DEVICE_REVERSE:e)- Transaction:t2;
  dev_cards = SELECT c FROM dev_txns:t2 -(MADE_REVERSE:e)- Card:c;
  dev_custs = SELECT cu FROM dev_cards:c -(OWNS_REVERSE:e)- Customer:cu
              ACCUM @@customer_ids += cu.customer_id;

  PRINT @@has_device, @@customer_ids;
  PRINT devices[devices.device_id, devices.device_info, devices.is_new_for_account, devices.proxy_type];
}}"""
    try:
        resp = conn.runInterpretedQuery(gsql)
    except Exception as exc:
        return {"pattern": "NewDeviceWithProxy", "strength": "weak",
                "observations": [], "error": str(exc)}

    has_device = 0
    customer_ids: List[str] = []
    device_id = ""
    device_info = ""
    is_new = False
    proxy_type = ""

    for block in resp:
        if "@@has_device" in block:
            has_device = block["@@has_device"]
        if "@@customer_ids" in block:
            customer_ids = block["@@customer_ids"]
        if "devices" in block and block["devices"]:
            dev_block = block["devices"][0]
            device_id = dev_block.get("v_id", "")
            attrs = dev_block.get("attributes", {})
            device_info = attrs.get("devices.device_info", attrs.get("device_info", ""))
            is_new = attrs.get("devices.is_new_for_account", attrs.get("is_new_for_account", False))
            proxy_type = attrs.get("devices.proxy_type", attrs.get("proxy_type", ""))

    if has_device == 0:
        return {
            "pattern":      "NewDeviceWithProxy",
            "strength":     "none",
            "observations": ["No device — in-person transaction (no FROM_DEVICE edge)."],
        }

    has_proxy = "proxy" in str(proxy_type).lower()
    proxy_str = str(proxy_type) if proxy_type else "none"

    if is_new and has_proxy:
        strength = "strong"
    elif is_new and not has_proxy:
        strength = "moderate"
    elif not is_new and has_proxy:
        strength = "moderate"
    else:
        strength = "none"

    n_customers = len(customer_ids)

    return {
        "pattern":  "NewDeviceWithProxy",
        "strength": strength,
        "observations": [
            f"Device {device_id} — model {device_info}",
            f"New for account: {is_new}",
            f"Proxy: {proxy_str}",
            f"Device shared across {n_customers} distinct customers",
        ],
    }


_PATTERN_DISPATCH = {
    "SharedDeviceRing":   _detect_shared_device_ring,
    "VelocityBurst":      _detect_velocity_burst,
    "AmountAnomaly":      _detect_amount_anomaly,
    "NewDeviceWithProxy": _detect_new_device_with_proxy,
}

VALID_PATTERNS = list(_PATTERN_DISPATCH.keys())


def detect_pattern(seed_txn_id: str, pattern_name: str) -> Dict[str, Any]:
    """Assess the strength of a named fraud pattern anchored at a transaction."""
    if pattern_name not in _PATTERN_DISPATCH:
        return {
            "pattern":      pattern_name,
            "strength":     "weak",
            "observations": [],
            "error":        f"Unknown pattern '{pattern_name}'.",
        }
    try:
        conn = _get_sync_conn()
        return _PATTERN_DISPATCH[pattern_name](conn, seed_txn_id)
    except Exception as exc:
        return {
            "pattern":      pattern_name,
            "strength":     "weak",
            "observations": [],
            "error":        str(exc),
        }


# =============================================================================
# Tool 5 - find_similar_cases
# =============================================================================
def find_similar_cases(entity_id: str, entity_type: str = "customer", k: int = 5) -> Dict[str, Any]:
    """Given a customer_id, device_id, or card_id, find ClosedCases from graph memory."""
    conn = _get_sync_conn()
    e_type = entity_type.lower().strip()
    k_val = int(k)

    if e_type == "customer":
        gsql = f"""INTERPRET QUERY () FOR GRAPH HHGoa {{
  seed = {{Customer.*}};
  cust = SELECT c FROM seed:c WHERE c.customer_id == "{entity_id}";
  cases1 = SELECT cc FROM cust:c -(INVOLVES_CUSTOMER_REVERSE:e)- ClosedCase:cc;
  cards = SELECT cr FROM cust:c -(OWNS:e)- Card:cr;
  cases2 = SELECT cc FROM cards:cr -(ON_CARD_REVERSE:e)- ClosedCase:cc;
  all_cases = cases1 UNION cases2;
  top_cases = SELECT cc FROM all_cases:cc LIMIT {k_val};
  PRINT top_cases[top_cases.case_id, top_cases.customer_id, top_cases.card_id, top_cases.outcome, top_cases.pattern, top_cases.exposure_usd, top_cases.opened_at, top_cases.analyst_notes];
}}"""
        relevance_str = "same customer"
    elif e_type == "device":
        gsql = f"""INTERPRET QUERY () FOR GRAPH HHGoa {{
  seed = {{DeviceProfile.*}};
  dev = SELECT d FROM seed:d WHERE d.device_id == "{entity_id}";
  txns = SELECT t FROM dev:d -(FROM_DEVICE_REVERSE:e)- Transaction:t;
  all_cases = SELECT cc FROM txns:t -(INVOLVES_TXN_REVERSE:e)- ClosedCase:cc;
  top_cases = SELECT cc FROM all_cases:cc LIMIT {k_val};
  PRINT top_cases[top_cases.case_id, top_cases.customer_id, top_cases.card_id, top_cases.outcome, top_cases.pattern, top_cases.exposure_usd, top_cases.opened_at, top_cases.analyst_notes];
}}"""
        relevance_str = "same device"
    elif e_type == "card":
        gsql = f"""INTERPRET QUERY () FOR GRAPH HHGoa {{
  seed = {{Card.*}};
  cr = SELECT c FROM seed:c WHERE c.card_id == "{entity_id}";
  all_cases = SELECT cc FROM cr:c -(ON_CARD_REVERSE:e)- ClosedCase:cc;
  top_cases = SELECT cc FROM all_cases:cc LIMIT {k_val};
  PRINT top_cases[top_cases.case_id, top_cases.customer_id, top_cases.card_id, top_cases.outcome, top_cases.pattern, top_cases.exposure_usd, top_cases.opened_at, top_cases.analyst_notes];
}}"""
        relevance_str = "same card"
    else:
        return {
            "query": {"entity_id": entity_id, "entity_type": entity_type, "k": k_val},
            "similar_cases": [],
            "count": 0,
            "error": f"Unsupported entity_type '{entity_type}'. Must be 'customer', 'device', or 'card'.",
        }

    try:
        resp = conn.runInterpretedQuery(gsql)
    except Exception as exc:
        return {
            "query": {"entity_id": entity_id, "entity_type": entity_type, "k": k_val},
            "similar_cases": [],
            "count": 0,
            "error": str(exc),
        }

    similar_cases = []
    for block in resp:
        if "top_cases" in block:
            for item in block["top_cases"]:
                attrs = item.get("attributes", {})
                notes = attrs.get("top_cases.analyst_notes", attrs.get("analyst_notes", ""))
                similar_cases.append({
                    "case_id": attrs.get("top_cases.case_id", attrs.get("case_id", item.get("v_id", ""))),
                    "customer_id": attrs.get("top_cases.customer_id", attrs.get("customer_id", "")),
                    "card_id": attrs.get("top_cases.card_id", attrs.get("card_id", "")),
                    "outcome": attrs.get("top_cases.outcome", attrs.get("outcome", "")),
                    "pattern": attrs.get("top_cases.pattern", attrs.get("pattern", "")),
                    "exposure_usd": float(attrs.get("top_cases.exposure_usd", attrs.get("exposure_usd", 0.0))),
                    "opened_at": str(attrs.get("top_cases.opened_at", attrs.get("opened_at", ""))),
                    "analyst_notes_short": notes[:200],
                    "relevance": relevance_str,
                })

    return {
        "query": {"entity_id": entity_id, "entity_type": entity_type, "k": k_val},
        "similar_cases": similar_cases,
        "count": len(similar_cases),
    }


# =============================================================================
# Tool 6 - record_evidence
# =============================================================================
def record_evidence(case_id: str, claim: str, source: str, ref: str, entity_ids: str) -> Dict[str, Any]:
    """Write an Evidence vertex and link it to an InvestigationCase."""
    try:
        conn = _get_sync_conn()
        h = hashlib.md5(f"{claim}:{ref}".encode("utf-8")).hexdigest()[:6].upper()
        evidence_id = f"{case_id}-E{h}"

        conn.upsertVertex("InvestigationCase", case_id, {"status": "under_investigation"})
        conn.upsertVertex("Evidence", evidence_id, {
            "claim": claim,
            "source": source,
            "ref": ref,
            "entity_ids": entity_ids,
        })
        conn.upsertEdge("InvestigationCase", case_id, "HAS_EVIDENCE", "Evidence", evidence_id)
        return {"evidence_id": evidence_id, "written": True}
    except Exception as exc:
        return {"case_id": case_id, "written": False, "error": str(exc)}


# =============================================================================
# Tool 7 - close_case
# =============================================================================
def close_case(case_id: str, outcome: str, pattern: str, exposure_usd: float, summary: str) -> Dict[str, Any]:
    """Close an InvestigationCase and spawn a ResolvedCase linked to entities."""
    try:
        conn = _get_sync_conn()
        resolved_id = f"R-{case_id}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.upsertVertex("ResolvedCase", resolved_id, {
            "original_case_id": case_id,
            "closed_at": now_str,
            "outcome": outcome,
            "pattern": pattern,
            "exposure_usd": float(exposure_usd),
            "summary": summary,
            "status": "active_memory",
            "superseded_by": "",
        })

        status = "closed_fraud" if outcome == "fraud" else ("closed_legitimate" if outcome == "legitimate" else "closed_uncertain")
        conn.upsertVertex("InvestigationCase", case_id, {
            "status": status,
            "verdict": outcome,
            "pattern": pattern,
            "exposure_usd": float(exposure_usd),
            "summary": summary,
            "written_to_graph": True,
        })

        conn.upsertEdge("InvestigationCase", case_id, "RESOLVED_AS", "ResolvedCase", resolved_id)

        if pattern != "none":
            conn.upsertVertex("DocumentedPattern", pattern, {"description": f"Documented pattern: {pattern}", "policy_rule": ""})
            conn.upsertEdge("ResolvedCase", resolved_id, "MATCHED_PATTERN", "DocumentedPattern", pattern)

        return {"resolved_id": resolved_id, "written": True}
    except Exception as exc:
        return {"case_id": case_id, "written": False, "error": str(exc)}


# =============================================================================
# Tool registration
# =============================================================================
def _build_tool(name: str, description: str, properties: Dict, required: List[str]) -> Tool:
    return Tool(
        name=name,
        description=description,
        input_schema={
            "type":       "object",
            "properties": properties,
            "required":   required,
        },
    )


_get_transaction_context_tool = _build_tool(
    name="hhgoa__get_transaction_context",
    description=(
        "Return the full neighbourhood of a single Transaction vertex in the "
        "HHGoa fraud-investigation graph: card, customer, device (online only), "
        "email domain, billing region."
    ),
    properties={
        "txn_id": {"type": "string", "description": "The TransactionID (e.g. '3000001')."}
    },
    required=["txn_id"],
)

_find_connected_entities_tool = _build_tool(
    name="hhgoa__find_connected_entities",
    description=(
        "Return all graph entities reachable from a Customer vertex: cards, "
        "transactions, devices, email domains, billing regions."
    ),
    properties={
        "customer_id": {"type": "string", "description": "The Customer ID (e.g. 'C12382')."}
    },
    required=["customer_id"],
)

_detect_pattern_tool = _build_tool(
    name="hhgoa__detect_pattern",
    description=(
        "Assess the strength of a named fraud pattern anchored at a transaction. "
        "Supported: SharedDeviceRing, VelocityBurst, AmountAnomaly, NewDeviceWithProxy."
    ),
    properties={
        "seed_txn_id":  {"type": "string", "description": "TransactionID to anchor on."},
        "pattern_name": {"type": "string", "enum": VALID_PATTERNS},
    },
    required=["seed_txn_id", "pattern_name"],
)

_find_similar_cases_tool = _build_tool(
    name="hhgoa__find_similar_cases",
    description=(
        "Given a customer_id, device_id, or card_id, find ClosedCases from the "
        "closed_cases_history that share entities with the current investigation."
    ),
    properties={
        "entity_id":   {"type": "string", "description": "The entity identifier (e.g. customer_id, device_id, card_id)."},
        "entity_type": {"type": "string", "enum": ["customer", "device", "card"], "description": "Type of entity (customer, device, card). Defaults to customer."},
        "k":           {"type": "integer", "description": "Maximum number of similar cases to return. Defaults to 5."},
    },
    required=["entity_id"],
)

_record_evidence_tool = _build_tool(
    name="hhgoa__record_evidence",
    description=(
        "Write an Evidence vertex and link it to an InvestigationCase via HAS_EVIDENCE."
    ),
    properties={
        "case_id":    {"type": "string", "description": "The InvestigationCase ID (e.g. 'HHG-001')."},
        "claim":      {"type": "string", "description": "The factual statement or finding."},
        "source":     {"type": "string", "enum": ["graph", "document", "customer", "external"], "description": "Source of evidence."},
        "ref":        {"type": "string", "description": "Query name, document section, or request ID."},
        "entity_ids": {"type": "string", "description": "Comma-separated list of entity IDs the claim rests on."},
    },
    required=["case_id", "claim", "source", "ref", "entity_ids"],
)

_close_case_tool = _build_tool(
    name="hhgoa__close_case",
    description=(
        "Close an InvestigationCase and spawn a ResolvedCase linked to entities and documented patterns."
    ),
    properties={
        "case_id":      {"type": "string", "description": "The InvestigationCase ID (e.g. 'HHG-001')."},
        "outcome":      {"type": "string", "enum": ["fraud", "legitimate", "uncertain"], "description": "Investigation outcome verdict."},
        "pattern":      {"type": "string", "enum": ["card_testing", "card_not_present_fraud", "card_not_present_new_device", "out_of_region_use", "account_takeover", "undocumented", "none"], "description": "Detected fraud pattern."},
        "exposure_usd": {"type": "number", "description": "Total USD amount at risk."},
        "summary":      {"type": "string", "description": "2-6 sentence summary of investigation findings and rationale."},
    },
    required=["case_id", "outcome", "pattern", "exposure_usd", "summary"],
)

_CUSTOM_TOOLS: List[Tool] = [
    _get_transaction_context_tool,
    _find_connected_entities_tool,
    _detect_pattern_tool,
    _find_similar_cases_tool,
    _record_evidence_tool,
    _close_case_tool,
]

_registry._ALL_TOOLS.extend(_CUSTOM_TOOLS)

_default_count = len(_registry._ALL_TOOLS) - len(_CUSTOM_TOOLS)
_total_count   = len(_registry._ALL_TOOLS)

print(
    f"[custom_tools] Registered {len(_CUSTOM_TOOLS)} custom tools. "
    f"Total: {_default_count} built-in + {len(_CUSTOM_TOOLS)} custom = {_total_count}."
)