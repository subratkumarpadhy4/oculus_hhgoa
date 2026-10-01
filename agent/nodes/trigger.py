"""
trigger.py
----------
Node 1: Receives case trigger and initializes investigation trace.
"""

from datetime import datetime
from agent.state import AgentState


def trigger_node(state: AgentState) -> AgentState:
    """Initialize case and record trigger trace."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["trace"].append({
        "node": "trigger",
        "timestamp": now_str,
        "details": f"Case {state['case_id']} opened. Trigger: {state['trigger_type']} — {state['trigger_text']}",
    })
    return state
