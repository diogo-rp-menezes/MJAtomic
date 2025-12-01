import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.database import Base
from src.core.repositories import TaskRepository
from src.core.models import DevelopmentPlan, DevelopmentStep, TaskStatus, AgentRole
from src.core.orm_models import DBDevelopmentPlan, DBStep

# Setup in-memory SQLite for unit tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_create_plan(db_session):
    repo = TaskRepository(db_session)
    plan = DevelopmentPlan(
        original_request="Test Request",
        project_path="/tmp/test",
        steps=[
            DevelopmentStep(
                id="step-1",
                description="Step 1",
                role=AgentRole.TECH_LEAD,
                status=TaskStatus.PENDING
            )
        ]
    )

    db_plan = repo.create_plan(plan)

    assert db_plan.id is not None
    assert db_plan.original_request == "Test Request"
    assert len(db_plan.steps) == 1
    assert db_plan.steps[0].description == "Step 1"

def test_get_plan(db_session):
    repo = TaskRepository(db_session)
    # Create manually to test get
    db_plan = DBDevelopmentPlan(original_request="Get Test", project_path="/tmp")
    db_session.add(db_plan)
    db_session.commit()

    fetched_plan = repo.get_plan(str(db_plan.id))
    assert fetched_plan is not None
    assert fetched_plan.original_request == "Get Test"

def test_get_all_plans(db_session):
    repo = TaskRepository(db_session)
    for i in range(3):
        db_session.add(DBDevelopmentPlan(original_request=f"Plan {i}"))
    db_session.commit()

    plans = repo.get_all_plans()
    assert len(plans) == 3

def test_update_step(db_session):
    repo = TaskRepository(db_session)

    # Create plan with step
    db_plan = DBDevelopmentPlan(original_request="Update Test")
    db_step = DBStep(
        plan=db_plan,
        description="Step to update",
        role=AgentRole.FULLSTACK,
        status=TaskStatus.PENDING
    )
    db_session.add(db_plan) # cascades to step
    db_session.commit()

    step_id = str(db_step.id)

    updated_step = repo.update_step(step_id, status=TaskStatus.COMPLETED, result="Done", logs="Log output")

    assert updated_step.status == TaskStatus.COMPLETED
    assert updated_step.result == "Done"
    assert updated_step.logs == "Log output"

    # Verify in DB
    refreshed_step = repo.get_step(step_id)
    assert refreshed_step.status == TaskStatus.COMPLETED

def test_update_non_existent_step(db_session):
    repo = TaskRepository(db_session)
    result = repo.update_step("non-existent-id", status=TaskStatus.COMPLETED)
    assert result is None
