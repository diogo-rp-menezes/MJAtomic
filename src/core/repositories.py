from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from src.core.orm_models import DBDevelopmentPlan, DBStep
from src.core.models import DevelopmentPlan, DevelopmentStep, TaskStatus
import uuid

class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_plan(self, plan_model: DevelopmentPlan) -> DBDevelopmentPlan:
        db_plan = DBDevelopmentPlan(
            original_request=plan_model.original_request,
            project_path=plan_model.project_path,
            created_at=plan_model.created_at
        )
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)

        for step in plan_model.steps:
            step_id = step.id if step.id else str(uuid.uuid4())
            db_step = DBStep(
                id=step_id,
                plan_id=db_plan.id,
                description=step.description,
                role=step.role,
                status=step.status,
                result=step.result or "", # Garante string
                logs=step.logs or ""      # Garante string
            )
            self.db.add(db_step)

        self.db.commit()
        self.db.refresh(db_plan)
        return db_plan

    def get_plan(self, plan_id: str) -> DBDevelopmentPlan:
        return self.db.query(DBDevelopmentPlan).filter(DBDevelopmentPlan.id == plan_id).first()

    def get_all_plans(self, limit: int = 50) -> List[DBDevelopmentPlan]:
        return self.db.query(DBDevelopmentPlan).order_by(desc(DBDevelopmentPlan.created_at)).limit(limit).all()

    def get_step(self, step_id: str) -> DBStep:
        return self.db.query(DBStep).filter(DBStep.id == step_id).first()

    def update_step(self, step_id: str, status: TaskStatus, result: str = None, logs: str = None):
        step = self.get_step(step_id)
        if step:
            step.status = status
            if result is not None: step.result = result
            if logs is not None: step.logs = logs
            self.db.commit()
            self.db.refresh(step)
        return step
