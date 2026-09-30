"""
mcp_client.py
-------------
MCPClient helper that calls the custom TigerGraph MCP tools directly as Python functions.
"""

from typing import Any, Dict

from mcp_server.custom_tools import (
    close_case,
    detect_pattern,
    find_connected_entities,
    find_similar_cases,
    get_transaction_context,
    record_evidence,
)


class MCPClient:
    """Wrapper around custom TigerGraph MCP tools."""

    def get_transaction_context(self, txn_id: str) -> Dict[str, Any]:
        """Fetch the full graph neighborhood of a transaction."""
        try:
            return get_transaction_context(txn_id)
        except Exception as exc:
            return {"txn_id": txn_id, "error": str(exc)}

    def find_connected_entities(self, customer_id: str) -> Dict[str, Any]:
        """Fetch all reachable entities from a customer."""
        try:
            return find_connected_entities(customer_id)
        except Exception as exc:
            return {"customer_id": customer_id, "error": str(exc)}

    def detect_pattern(self, txn_id: str, pattern_name: str) -> Dict[str, Any]:
        """Assess fraud pattern strength for a transaction."""
        try:
            return detect_pattern(txn_id, pattern_name)
        except Exception as exc:
            return {"pattern": pattern_name, "strength": "none", "error": str(exc)}

    def find_similar_cases(self, entity_id: str, entity_type: str = "customer", k: int = 5) -> Dict[str, Any]:
        """Retrieve similar historical ClosedCases from graph memory."""
        try:
            return find_similar_cases(entity_id, entity_type=entity_type, k=k)
        except Exception as exc:
            return {"entity_id": entity_id, "similar_cases": [], "count": 0, "error": str(exc)}

    def record_evidence(self, case_id: str, claim: str, source: str, ref: str, entity_ids: str) -> Dict[str, Any]:
        """Upsert Evidence vertex and link to InvestigationCase."""
        try:
            return record_evidence(case_id, claim, source, ref, entity_ids)
        except Exception as exc:
            return {"case_id": case_id, "written": False, "error": str(exc)}

    def close_case(self, case_id: str, outcome: str, pattern: str, exposure_usd: float, summary: str) -> Dict[str, Any]:
        """Close InvestigationCase and spawn ResolvedCase."""
        try:
            return close_case(case_id, outcome, pattern, exposure_usd, summary)
        except Exception as exc:
            return {"case_id": case_id, "written": False, "error": str(exc)}
