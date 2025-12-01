import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from src.core.database import Base
from src.core.models import AgentRole, TaskStatus

class DBDevelopmentPlan(Base):
    __tablename__ = "development_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_request = Column(Text, nullable=False)
    project_path = Column(String, nullable=True, default="./workspace")
    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship("DBStep", back_populates="plan", cascade="all, delete-orphan")

class DBStep(Base):
    __tablename__ = "steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String, ForeignKey("development_plans.id"), nullable=False)
    description = Column(Text, nullable=False)
    role = Column(SQLEnum(AgentRole), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    result = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)

    plan = relationship("DBDevelopmentPlan", back_populates="steps")

class DBCheckpoint(Base):
    __tablename__ = "checkpoints"

    thread_id = Column(String, primary_key=True)
    checkpoint_id = Column(String, primary_key=True)
    parent_checkpoint_id = Column(String, nullable=True)
    type = Column(String) # json, msgpack, etc
    checkpoint = Column(LargeBinary) # Serialized state
    metadata_ = Column(LargeBinary) # Serialized metadata (using metadata_ to avoid SQL reserved word conflict)
    created_at = Column(DateTime, default=datetime.utcnow)
