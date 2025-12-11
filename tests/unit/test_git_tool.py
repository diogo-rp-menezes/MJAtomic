import sys
from unittest.mock import MagicMock

# Mock docker module before importing anything that uses it
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

import unittest
from src.tools.git_tool import GitTool

class TestGitTool(unittest.TestCase):
    def setUp(self):
        self.mock_executor = MagicMock()
        self.git_tool = GitTool(self.mock_executor)

    def test_init_repo_success(self):
        # Setup mocks for 4 calls: version, init, config(x2)
        self.mock_executor.run_command.side_effect = [
            {"success": True, "exit_code": 0, "output": "git version 2.30.2"},
            {"success": True, "exit_code": 0, "output": "Initialized empty Git repository"},
            {"success": True, "exit_code": 0, "output": ""}, # user.email
            {"success": True, "exit_code": 0, "output": ""}  # user.name
        ]

        result = self.git_tool.init_repo()

        self.assertIn("Git repository initialized", result)
        self.assertEqual(self.mock_executor.run_command.call_count, 4)

        # Verify commands
        calls = self.mock_executor.run_command.call_args_list
        self.assertEqual(calls[0][0][0], "git --version")
        self.assertEqual(calls[1][0][0], "git init")
        self.assertIn("user.email", calls[2][0][0])
        self.assertIn("user.name", calls[3][0][0])

    def test_init_repo_missing_git(self):
        self.mock_executor.run_command.return_value = {"success": False, "exit_code": 127, "output": "git: command not found"}

        with self.assertRaises(RuntimeError) as cm:
            self.git_tool.init_repo()

        self.assertIn("git version check", str(cm.exception))

    def test_initial_commit_success(self):
        self.mock_executor.run_command.side_effect = [
            {"success": True, "exit_code": 0, "output": ""}, # add
            {"success": True, "exit_code": 0, "output": "[master (root-commit) 123456] Initial commit"} # commit
        ]

        result = self.git_tool.initial_commit()

        self.assertIn("Initial commit created", result)
        self.assertEqual(self.mock_executor.run_command.call_count, 2)

        calls = self.mock_executor.run_command.call_args_list
        self.assertEqual(calls[0][0][0], "git add .")
        self.assertIn("git commit -m", calls[1][0][0])

    def test_initial_commit_failure(self):
        self.mock_executor.run_command.side_effect = [
            {"success": True, "exit_code": 0, "output": ""}, # add
            {"success": False, "exit_code": 1, "output": "nothing to commit"} # commit
        ]

        with self.assertRaises(RuntimeError) as cm:
            self.git_tool.initial_commit()

        self.assertIn("git commit", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
