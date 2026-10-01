"""
graph.py
--------
LangGraph StateMachine definition for the HHGoa Fraud Investigation Agent.
"""

from typing import Any, Dict, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes.assess_sufficiency import assess_sufficiency_node
from agent.nodes.collect_evidence import collect_evidence_node
from agent.nodes.enforce_policy import enforce_policy_node
from agent.nodes.execute_or_approve import execute_or_approve_node
from agent.nodes.llm_investigate import llm_investigate_node
from agent.nodes.recommend_action import recommend_action_node
from agent.nodes.request_evidence import request_evidence_node
from agent.nodes.trigger import trigger_node
from agent.nodes.write_back import write_back_node
from agent.state import AgentState, new_state


def _sufficiency_router(state: AgentState) -> Literal["request_evidence", "recommend_action"]:
    """Conditional routing based on evidence sufficiency and evidence round circuit breaker."""
    sufficiency = state.get("sufficiency", "insufficient")
    rounds = state.get("evidence_rounds", 0)

    if sufficiency == "insufficient" and rounds < 3:
        return "request_evidence"
    return "recommend_action"


def build_investigation_graph(checkpointer: Any = None):
    """Build and compile the 9-node fraud investigation StateGraph."""
    workflow = StateGraph(AgentState)

    # 1. Add all 9 nodes
    workflow.add_node("trigger", trigger_node)
    workflow.add_node("collect_evidence", collect_evidence_node)
    workflow.add_node("llm_investigate", llm_investigate_node)
    workflow.add_node("assess_sufficiency", assess_sufficiency_node)
    workflow.add_node("request_evidence", request_evidence_node)
    workflow.add_node("recommend_action", recommend_action_node)
    workflow.add_node("enforce_policy", enforce_policy_node)
    workflow.add_node("execute_or_approve", execute_or_approve_node)
    workflow.add_node("write_back", write_back_node)

    # 2. Add fixed edges
    workflow.add_edge(START, "trigger")
    workflow.add_edge("trigger", "collect_evidence")
    workflow.add_edge("collect_evidence", "llm_investigate")
    workflow.add_edge("llm_investigate", "assess_sufficiency")

    # 3. Conditional edge from assess_sufficiency
    workflow.add_conditional_edges(
        "assess_sufficiency",
        _sufficiency_router,
        {
            "request_evidence": "request_evidence",
            "recommend_action": "recommend_action",
        },
    )

    # 4. Loop back from request_evidence to collect_evidence
    workflow.add_edge("request_evidence", "collect_evidence")

    # 5. Downstream action & resolution pipeline
    workflow.add_edge("recommend_action", "enforce_policy")
    workflow.add_edge("enforce_policy", "execute_or_approve")
    workflow.add_edge("execute_or_approve", "write_back")
    workflow.add_edge("write_back", END)

    # 6. Checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


# Compiled default graph instance
investigation_graph = build_investigation_graph()


def run_case(case_row: Dict[str, Any]) -> AgentState:
    """Run a fraud investigation case from row dict through the compiled LangGraph pipeline."""
    initial_state = new_state(case_row)
    thread_id = initial_state["case_id"] or "default-case"
    config = {"configurable": {"thread_id": thread_id}}

    final_state = investigation_graph.invoke(initial_state, config=config)
    return final_state
