import unittest
from unittest.mock import patch

from src.core.graph.graph import create_development_graph


class TestGraphStructure(unittest.TestCase):
    """
    Unit tests to ensure the graph is structured correctly.
    """

    def test_graph_creation_and_nodes(self):
        # Create the graph
        graph = create_development_graph()

        # Check that all expected nodes are present
        expected_nodes = ["planner", "executor", "reviewer", "healer", "human"]
        self.assertCountEqual(graph.nodes.keys(), expected_nodes)

    def test_graph_entry_point(self):
        graph = create_development_graph()
        self.assertEqual(graph.entry_point, "planner")

    @patch("src.core.graph.nodes.planning_node")
    @patch("src.core.graph.nodes.code_execution_node")
    def test_simple_graph_flow(self, mock_executor, mock_planner):
        # This is more of a conceptual test of flow logic.
        # A full test would require running the graph, which is more of an integration test.
        
        # Mock node outputs
        mock_planner.return_value = {"plan": {"steps": [{}]}, "current_step_index": 0}
        mock_executor.return_value = {"code": "print('ok')", "test_results": {"exit_code": 0}}

        # In a real scenario, you'd compile and run the graph.
        # For a unit test, we can just assert the structure implies a certain flow.
        graph = create_development_graph()
        
        # Check edges from planner
        self.assertIn("executor", graph.edges["planner"].downstream)

        # Check edges from executor
        self.assertIn("reviewer", graph.edges["executor"].downstream)

if __name__ == "__main__":
    unittest.main()
