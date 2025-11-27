from sqlalchemy import (create_engine, Column, Integer, String, Text,
                        ForeignKey, Enum, LargeBinary)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from src.core.config.settings import settings
from src.models.enums import AgentRole, StepStatus

Base = declarative_base()

class DevelopmentPlan(Base):
    __tablename__ = "development_plans"
    id = Column(Integer, primary_key=True)
    project_name = Column(String(255), nullable=False)
    steps = relationship("Step", back_populates="plan")

class Step(Base):
    __tablename__ = "steps"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("development_plans.id"))
    description = Column(Text, nullable=False)
    status = Column(Enum(StepStatus), default=StepStatus.PENDING)
    agent_role = Column(Enum(AgentRole), nullable=False)
    plan = relationship("DevelopmentPlan", back_populates="steps")

class DBCheckpoint(Base):
    __tablename__ = "graph_checkpoints"
    thread_id = Column(String, primary_key=True)
    version = Column(Integer, primary_key=True)
    checkpoint = Column(LargeBinary)


def get_engine():
    return create_engine(settings.DATABASE_URL)

def create_tables():
    engine = get_engine()
    Base.metadata.create_all(engine)

# To initialize the database
if __name__ == "__main__":
    create_tables()
