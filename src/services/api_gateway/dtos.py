from pydantic import BaseModel, Field
from typing import Optional

class AuditRequest(BaseModel):
    description: str = Field(..., description="Description of the task or feature to audit/plan")
    project_path: str = Field(default="./workspace", description="Relative path to the project root")
    code_language: str = Field(default="Python", description="Programming language for the project")

class ResumeRequest(BaseModel):
    user_input: str = Field(..., description="Feedback or approval from the user")
