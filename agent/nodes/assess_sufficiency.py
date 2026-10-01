"""
assess_sufficiency.py
---------------------
Node 4: Deterministic evaluation of whether collected evidence is sufficient to make a decision.
"""

from datetime import datetime
from agent.state import AgentState

# Dimension encodings
DIM_ENCODING = {
    "none": 0,
    "weak": 1,
    "moderate": 2,
    "strong": 3,
}

CONTRADICTORY_ENCODING = {
    "none": 0,
    "minor": 1,
    "major": 3,
}

# Frozen weights & threshold
W_GRAPH = 0.35
W_BEHAVIORAL = 0.25
W_PRIOR = 0.25
W_CONTRADICTORY = 0.50
SUFFICIENT_THRESHOLD = 1.5


def assess_sufficiency_node(state: AgentState) -> AgentState:
    """Assess whether current evidence is sufficient for action recommendation."""
    # 1. Increment round counter
    current_round = state.get("evidence_rounds", 0) + 1
    state["evidence_rounds"] = current_round

    # Extract dimensions gracefully
    llm_findings = state.get("llm_findings") or {}
    if not isinstance(llm_findings, dict):
        llm_findings = {}
    unc_dims = llm_findings.get("uncertainty_dimensions") or {}
    if not isinstance(unc_dims, dict):
        unc_dims = {}

    graph_ev = str(unc_dims.get("graph_evidence", "none")).lower()
    behavioral_ev = str(unc_dims.get("behavioral_evidence", "none")).lower()
    prior_ev = str(unc_dims.get("prior_case_match", "none")).lower()
    contradictory_ev = str(unc_dims.get("contradictory_evidence", "none")).lower()

    # Ordinal encodings
    graph_enc = DIM_ENCODING.get(graph_ev, 0)
    behavioral_enc = DIM_ENCODING.get(behavioral_ev, 0)
    prior_enc = DIM_ENCODING.get(prior_ev, 0)
    contradictory_enc = CONTRADICTORY_ENCODING.get(contradictory_ev, 0)

    # Calculate weighted score
    score = (
        W_GRAPH * graph_enc
        + W_BEHAVIORAL * behavioral_enc
        + W_PRIOR * prior_enc
        - W_CONTRADICTORY * contradictory_enc
    )

    reason = ""
    # Circuit breaker: hard cap of 3 rounds
    if current_round >= 3:
        sufficiency = "sufficient"
        reason = f"Circuit breaker reached max rounds ({current_round}); forced sufficient."
    # Step 1: Hard overrides
    elif contradictory_ev == "major":
        sufficiency = "contradictory"
        reason = "Hard override: major contradictory evidence."
    elif (
        graph_ev == "strong"
        and behavioral_ev == "strong"
        and prior_ev in {"moderate", "strong"}
        and contradictory_ev in {"none", "minor"}
    ):
        sufficiency = "sufficient"
        reason = "Hard override: strong multi-dimensional evidence."
    # Step 2: Weighted score
    elif score >= SUFFICIENT_THRESHOLD:
        sufficiency = "sufficient"
        reason = f"Score {score:.2f} >= threshold {SUFFICIENT_THRESHOLD}."
    else:
        sufficiency = "insufficient"
        reason = f"Score {score:.2f} < threshold {SUFFICIENT_THRESHOLD}."

    state["sufficiency"] = sufficiency

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "trace" not in state or not isinstance(state["trace"], list):
        state["trace"] = []

    state["trace"].append({
        "node": "assess_sufficiency",
        "timestamp": now_str,
        "details": f"Sufficiency evaluated as '{sufficiency}' (round {current_round}). {reason} [score={score:.2f}]",
    })

    # On the first round only: if evidence is insufficient (graph will loop back for more
    # evidence), snapshot the current recommendation NOW as action_history[0].
    # This becomes "initial" — what the agent recommended before any extra evidence was gathered.
    # The final recommend_action node at the end of the graph will add action_history[1] = "final".
    if current_round == 1 and sufficiency == "insufficient":
        from agent.nodes.recommend_action import recommend_action_node
        state = recommend_action_node(state)

    return state
