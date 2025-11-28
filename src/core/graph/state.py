from typing import TypedDict, Annotated, List, Optional
from src.core.models import DevelopmentPlan, Step

class AgentState(TypedDict):
    plan: DevelopmentPlan
    current_step_index: int
    current_step: Optional[Step]
    retry_count: int
    project_path: str
    error: Optional[str]
