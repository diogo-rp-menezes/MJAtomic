from pydantic import BaseModel, Field

# Represents a single step in the development plan
class DevelopmentStep(BaseModel):
    step: str = Field(..., description="Description of the development step.")
    task: str = Field(..., description="The high-level task this step belongs to.")
    language: str = Field(..., description="The programming language for this step.")
    test_command: str = Field(..., description="The command to run tests for this step.")

# Represents the entire development plan
class DevelopmentPlan(BaseModel):
    project_name: str
    tasks: list[str]
    steps: list[DevelopmentStep]

# Represents the result of a code review
class CodeReview(BaseModel):
    approved: bool
    comments: str

# Represents a piece of code to be executed or written to a file
class CodeExecution(BaseModel):
    file_path: str
    code: str

# Represents the result of running a test command
class TestExecutionResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str

# Represents the final result of a code execution cycle, including tests
class CodeExecutionResult(BaseModel):
    code_execution: CodeExecution
    test_result: TestExecutionResult
    status: str  # e.g., "PASSED", "FAILED", "FIXED", "FAILED_TO_FIX"
