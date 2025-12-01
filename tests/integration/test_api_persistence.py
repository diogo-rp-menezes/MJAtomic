from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from unittest.mock import patch, MagicMock
import os
import shutil
from httpx import AsyncClient, ASGITransport

from src.services.api_gateway.main import app
from src.core.database import Base, get_db
from src.core.models import TaskRequest, ProjectInitRequest

# Setup in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
async def client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.anyio
@patch("src.services.api_gateway.main.run_graph_task.delay")
async def test_create_and_list_tasks(mock_delay, client):
    # Mock celery task result
    mock_task = MagicMock()
    mock_task.id = "mock-task-id"
    mock_delay.return_value = mock_task

    # Test Create
    payload = {"description": "Test Task Persistence", "project_path": "./test_workspace"}
    response = await client.post("/tasks/create", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] is not None
    # assert data["task_id"] == "mock-task-id"

    # Test List
    response = await client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0
    # Find the task we just created
    found = False
    for task in tasks:
        if task["original_request"] == "Test Task Persistence":
            found = True
            assert task["id"] is not None
            assert task["created_at"] is not None
            pass
    assert found

@pytest.mark.anyio
async def test_init_project(client):
    test_path = "./test_workspace_init"
    if not os.path.exists(test_path):
        os.makedirs(test_path)
    with open(f"{test_path}/dummy", "w") as f: f.write("test")

    payload = {"project_name": "Test", "description": "Test", "root_path": test_path}
    response = await client.post("/init-project", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify dummy file is gone (folder recreated)
    assert not os.path.exists(f"{test_path}/dummy")
    assert os.path.exists(test_path)

    # Clean up
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
