from typing import TypedDict, Annotated, List, Optional
from src.core.models import DevelopmentPlan, Step, CodeReviewVerdict

class AgentState(TypedDict):
    plan: DevelopmentPlan
    current_step_index: int
    current_step: Optional[Step]
    retry_count: int
    project_path: str
    error: Optional[str]
    review_verdict: Optional[CodeReviewVerdict]
    modified_files: Optional[List[str]]
