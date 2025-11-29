from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class AgentRole(str, Enum):
    TECH_LEAD = "TECH_LEAD"
    FULLSTACK = "FULLSTACK"
    DEVOPS = "DEVOPS"
    REVIEWER = "REVIEWER"
    ARCHITECT = "ARCHITECT"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Verdict(str, Enum):
    """Enumeração estrita para os possíveis vereditos da revisão de código."""
    PASS = "PASS"
    FAIL = "FAIL"

class CodeReviewVerdict(BaseModel):
    """Modelo de dados para a saída estruturada do CodeReviewAgent."""
    verdict: Verdict = Field(description="O veredito final da revisão. Deve ser estritamente 'PASS' ou 'FAIL'.")
    justification: str = Field(description="Uma justificativa clara e concisa para o veredito, explicando o porquê da aprovação ou falha.")

class DevelopmentStep(BaseModel):
    id: str
    description: str
    role: AgentRole
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""  # Default vazio em vez de None
    logs: str = ""    # Default vazio em vez de None

# Alias for backward compatibility if any module imports Step
Step = DevelopmentStep

class DevelopmentPlan(BaseModel):
    id: Optional[str] = None
    original_request: str
    project_path: str = "./workspace" # Default seguro
    steps: List[DevelopmentStep] = []
    created_at: datetime = Field(default_factory=datetime.now)

class TaskRequest(BaseModel):
    description: str
    project_path: Optional[str] = None
    project_context: Optional[Dict[str, Any]] = None

class ProjectInitRequest(BaseModel):
    project_name: str
    description: str
    stack_preference: Optional[str] = "Recomendada pelo Arquiteto"
    root_path: Optional[str] = None
