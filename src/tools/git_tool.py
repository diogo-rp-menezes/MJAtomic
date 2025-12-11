import logging
from typing import Dict, Any, Optional
from src.tools.secure_executor import SecureExecutorTool

logger = logging.getLogger(__name__)

class GitTool:
    def __init__(self, executor: SecureExecutorTool):
        self.executor = executor

    def _check_result(self, result: Dict[str, Any], context: str):
        if not result.get("success", False):
            # Check exit code directly if success flag is ambiguous, but SecureExecutor sets success based on exit_code==0
            error_msg = result.get("error") or result.get("output") or "Unknown error"
            raise RuntimeError(f"Git execution failed during '{context}': {error_msg}")

    def init_repo(self) -> str:
        """
        Initializes the git repository in the sandbox.
        Sets up default identity.
        """
        work_dir = "/app"

        # 1. Check Git Version (Fail fast if missing)
        res = self.executor.run_command("git --version", work_dir=work_dir)
        self._check_result(res, "git version check")

        # 2. Init
        res = self.executor.run_command("git init", work_dir=work_dir)
        self._check_result(res, "git init")

        # 3. Configure Identity (Crucial for commit)
        commands = [
            'git config user.email "bot@devagent.ai"',
            'git config user.name "DevAgent Bot"'
        ]

        for cmd in commands:
            res = self.executor.run_command(cmd, work_dir=work_dir)
            self._check_result(res, f"git config ({cmd})")

        return "Git repository initialized and identity configured."

    def initial_commit(self, message: str = "Initial commit by Architect Agent") -> str:
        """
        Adds all files and makes the initial commit.
        """
        work_dir = "/app"

        # 1. Add .
        res = self.executor.run_command("git add .", work_dir=work_dir)
        self._check_result(res, "git add")

        # 2. Commit
        # Escape quotes in message to prevent shell injection/breaking
        safe_message = message.replace('"', '\\"')
        res = self.executor.run_command(f'git commit -m "{safe_message}"', work_dir=work_dir)
        self._check_result(res, "git commit")

        return "Initial commit created successfully."
