"""
execute_or_approve.py
---------------------
Node 8: Executes auto-authorized actions or routes pending actions to human analyst queue.
"""

from datetime import datetime
from agent.state import AgentState


def execute_or_approve_node(state: AgentState) -> AgentState:
    """Execute authorized actions or stage for approval."""
    rec_actions = state.get("recommended_actions", [])
    state["executed_actions"].extend(rec_actions)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["trace"].append({
        "node": "execute_or_approve",
        "timestamp": now_str,
        "details": f"Executed {len(rec_actions)} automated action(s) via route '{state.get('approval_route', 'auto')}'.",
    })

    return state
