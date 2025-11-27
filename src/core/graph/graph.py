from langgraph.graph import StateGraph

from src.core.agents.state import AgentState
from src.core.graph.nodes import (
    code_execution_node,
    human_in_loop_node,
    planning_node,
    review_node,
    self_healing_node,
)


def create_development_graph():
    """
    Creates the main state graph for the development process.
    """
    graph = StateGraph(AgentState)

    # 1. Define the nodes
    graph.add_node("planner", planning_node)
    graph.add_node("executor", code_execution_node)
    graph.add_node("reviewer", review_node)
    graph.add_node("healer", self_healing_node)
    graph.add_node("human", human_in_loop_node)

    # 2. Define the edges
    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "reviewer")

    # 3. Conditional edges
    graph.add_conditional_edges(
        "reviewer",
        lambda state: "healer" if state["review"] and not state["review"]["approved"] else "__end__",
        {"healer": "healer", "__end__": "__end__"},
    )
    graph.add_conditional_edges(
        "healer",
        lambda state: "executor" if state["review"]["status"] == "FIXED" else "human",
        {"executor": "executor", "human": "human"},
    )
    graph.add_conditional_edges(
        "human",
        lambda state: "planner" if state["human_feedback"] else "__end__",
        {"planner": "planner", "__end__": "__end__"},
    )

    return graph.compile()
