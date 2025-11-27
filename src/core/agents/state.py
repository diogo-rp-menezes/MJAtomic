from typing import Dict, Any
from pydantic import BaseModel, Field

# Represents the overall state of the development process
class AgentState(BaseModel):
    project_name: str = Field(..., description="The name of the project.")
    plan: Dict[str, Any] = Field(..., description="The development plan.")
    current_step_index: int = Field(0, description="The index of the current step in the plan.")
    code: str = Field(None, description="The code generated in the current step.")
    test_results: Dict[str, Any] = Field(None, description="The results of the tests run.")
    review: Dict[str, Any] = Field(None, description="The code review feedback.")
    is_human_in_loop: bool = Field(False, description="Flag to indicate if human intervention is needed.")
    human_feedback: str = Field(None, description="Feedback provided by the human.")
