import logging
from dataclasses import dataclass

import docker
from docker.errors import ContainerError, ImageNotFound, NotFound

from src.core.config.settings import settings


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


class SecureExecutorTool:
    """
    A tool for executing commands in a secure, isolated Docker container.
    """

    def __init__(
        self,
        image_name: str = "python:3.11-slim",
        timeout: int = 60,
        workspace_dir: str = None,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = docker.from_env()
        self.image_name = image_name
        self.timeout = timeout
        self.workspace_dir = workspace_dir or settings.HOST_WORKSPACE_PATH
        self._pull_image_if_not_exists()

    def _pull_image_if_not_exists(self):
        try:
            self.client.images.get(self.image_name)
        except ImageNotFound:
            self.logger.info(f"Pulling Docker image: {self.image_name}")
            self.client.images.pull(self.image_name)

    def execute(self, command: str) -> ExecutionResult:
        """
        Executes a command in a new Docker container.
        """
        self.logger.info(f"Executing command: {command}")
        try:
            container = self.client.containers.run(
                self.image_name,
                command=f"/bin/sh -c '{command}'",
                working_dir=settings.WORKSPACE_PATH,
                volumes={self.workspace_dir: {"bind": settings.WORKSPACE_PATH, "mode": "rw"}},
                detach=True,
                user="root", # Run as root to have permissions to write files
            )
            result = container.wait(timeout=self.timeout)
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
            container.remove()

            return ExecutionResult(
                exit_code=result["StatusCode"], stdout=stdout, stderr=stderr
            )
        except ContainerError as e:
            self.logger.error(f"ContainerError executing command: {e}")
            return ExecutionResult(exit_code=1, stdout="", stderr=str(e))
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            return ExecutionResult(exit_code=1, stdout="", stderr=str(e))

    def write_file(self, file_path: str, content: str):
        """
        Writes content to a file inside the container's workspace.
        This is a convenience method that uses the execute functionality.
        """
        # It's generally safer to handle file writing via the volume mount.
        # This approach is simple but can be slow.
        full_path = f"{self.workspace_dir}/{file_path}"
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    def read_file(self, file_path: str) -> str | None:
        """
        Reads content from a file inside the container's workspace.
        """
        full_path = f"{self.workspace_dir}/{file_path}"
        try:
            with open(full_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"File not found: {full_path}")
            return None
