import unittest
from unittest.mock import patch, MagicMock

from src.services.celery_worker.tasks import run_agent_graph


class TestWorkerGraphIntegration(unittest.TestCase):
    """
    Integration tests for the Celery worker and the LangGraph execution.
    """

    @patch("src.services.celery_worker.tasks.create_dev_graph_with_checkpoint")
    @patch("src.services.celery_worker.tasks.sync_state_to_db")
    def test_run_agent_graph_task(self, mock_sync_db, mock_create_graph):
        # Mock the graph and its stream method
        mock_graph = MagicMock()
        mock_graph.stream.return_value = [{"project_name": "Test Project", "current_step_index": 0}]
        mock_create_graph.return_value = mock_graph

        # Run the Celery task synchronously for testing
        result = run_agent_graph.s(plan_id=1, project_name="Test Project").apply()

        # Assertions
        self.assertTrue(result.successful())
        mock_create_graph.assert_called_once()
        mock_graph.stream.assert_called_once()
        mock_sync_db.assert_called() # Check that we tried to sync the state
        self.assertEqual(result.result, {"plan_id": 1, "status": "completed"})

if __name__ == "__main__":
    unittest.main()
