from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph

from src.core.agents.state import AgentState
from src.core.graph.checkpoint import get_checkpoint_saver
from src.core.graph.graph import create_development_graph


def create_dev_graph_with_checkpoint(
    checkpoint_saver: BaseCheckpointSaver = None,
) -> StateGraph:
    """
    Factory function to create the development graph with an optional checkpoint saver.
    """
    checkpoint = checkpoint_saver or get_checkpoint_saver()
    app = create_development_graph()
    return app.with_checkpoints(checkpoint)
