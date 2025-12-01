import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from src.services.api_gateway.main import app
from src.core.models import DevelopmentPlan
from src.core.database import get_db

# Override get_db
def override_get_db():
    mock = MagicMock()
    yield mock

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_get_tasks():
    with patch("src.services.api_gateway.main.TaskRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_all_plans.return_value = []

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/tasks")

        assert response.status_code == 200
        assert response.json() == []

@pytest.mark.anyio
async def test_audit_project():
    with patch("src.services.api_gateway.main.TechLeadAgent") as MockAgent, \
         patch("src.services.api_gateway.main.TaskRepository") as MockRepo:

        # Setup TechLeadAgent mock
        mock_agent_instance = MockAgent.return_value
        mock_plan = DevelopmentPlan(original_request="test", steps=[])
        mock_agent_instance.create_development_plan.return_value = mock_plan

        # Setup Repo mock
        mock_repo_instance = MockRepo.return_value
        mock_db_plan = MagicMock()
        mock_db_plan.id = "123"
        mock_db_plan.original_request = "test"
        mock_db_plan.project_path = "./workspace"
        mock_db_plan.created_at = "2023-01-01T00:00:00"
        mock_db_plan.steps = []
        mock_repo_instance.create_plan.return_value = mock_db_plan

        payload = {"description": "test feature", "project_path": "./workspace"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/audit", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "123"
        assert data["original_request"] == "test"

@pytest.mark.anyio
async def test_init_project():
    with patch("src.services.api_gateway.main.StructureBuilderTool") as MockTool, \
         patch("src.services.api_gateway.main.LLMProvider"), \
         patch("src.services.api_gateway.main.FileIOTool"):

        mock_tool_instance = MockTool.return_value
        mock_tool_instance.generate_structure.return_value = {}

        payload = {
            "project_name": "test_proj",
            "description": "desc",
            "stack_preference": "python"
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/init-project", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "success"

@pytest.mark.anyio
async def test_execute_task():
    with patch("src.services.api_gateway.main.TaskRepository") as MockRepo, \
         patch("src.services.api_gateway.main.run_graph_task") as mock_celery:

        mock_repo_instance = MockRepo.return_value
        mock_db_plan = MagicMock()
        mock_db_plan.id = "task-123"
        mock_db_plan.steps = []
        mock_db_plan.original_request = "req"
        mock_db_plan.project_path = "."
        mock_repo_instance.get_plan.return_value = mock_db_plan

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/execute/task-123")

        assert response.status_code == 200
        mock_celery.delay.assert_called_once()
