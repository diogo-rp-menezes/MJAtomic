import docker
import os
import time
from typing import Dict, Any, Optional
from src.core.logger import logger

class SecureExecutorTool:
    def __init__(self, workspace_path: str):
        self.client = docker.from_env()
        self.image = "devagent-sandbox"
        self.workspace_path = os.path.abspath(workspace_path)
        self.container_name = "devagent-sandbox-persistent"
        self.container = None

    def _ensure_sandbox(self):
        """Ensures the persistent sandbox container is running."""
        try:
            # Check if container exists
            try:
                self.container = self.client.containers.get(self.container_name)
                if self.container.status != "running":
                    logger.info(f"Starting existing sandbox: {self.container_name}")
                    self.container.start()
            except docker.errors.NotFound:
                # Create new container
                logger.info(f"Creating new persistent sandbox: {self.container_name}")

                # Check for image, pull/build if needed (simplified for now assuming existence or pull)
                try:
                    self.client.images.get(self.image)
                except docker.errors.ImageNotFound:
                    logger.warning(f"Image {self.image} not found. Using python:3.11-slim as fallback for testing.")
                    self.image = "python:3.11-slim"

                host_path = os.getenv("HOST_WORKSPACE_PATH", self.workspace_path)

                self.container = self.client.containers.run(
                    self.image,
                    command="sleep infinity", # Keep alive
                    detach=True,
                    name=self.container_name,
                    working_dir="/app",
                    volumes={host_path: {'bind': '/app', 'mode': 'rw'}},
                    user=0, # Root to install things if needed
                    mem_limit="1024m",
                    network_disabled=False,
                    # Auto restart if it crashes
                    restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}
                )

        except Exception as e:
            logger.error(f"Failed to ensure sandbox: {e}")
            raise

    def run_command(self, command: str, work_dir: str = "/app") -> Dict[str, Any]:
        """Runs a synchronous command in the persistent sandbox."""
        try:
            self._ensure_sandbox()

            # Using list format to avoid shell quoting issues
            result = self.container.exec_run(
                ["sh", "-c", command],
                workdir=work_dir,
                demux=False # Combine stdout/stderr
            )

            output = result.output.decode('utf-8', errors='replace')
            exit_code = result.exit_code

            return {
                "exit_code": exit_code,
                "output": output,
                "success": exit_code == 0
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"success": False, "error": str(e)}

    def start_background_process(self, command: str, work_dir: str = "/app") -> Dict[str, Any]:
        """
        Starts a process in the background using nohup.
        Returns the PID.
        """
        try:
            self._ensure_sandbox()

            import uuid
            proc_id = str(uuid.uuid4())[:8]
            log_file = f"bg_{proc_id}.log"

            # Use 'exec' inside sh to ensure the PID we get is the shell or the process?
            # echo $! gives the PID of the last background job.
            wrapped_cmd = f"nohup {command} > {log_file} 2>&1 & echo $!"

            result = self.container.exec_run(
                ["sh", "-c", wrapped_cmd],
                workdir=work_dir
            )

            pid = result.output.decode().strip()

            if result.exit_code != 0:
                return {"success": False, "error": f"Failed to start: {result.output.decode()}"}

            # Try to rename log file to use PID for consistency, if PID is valid
            try:
                if pid.isdigit():
                    self.container.exec_run(f"mv {log_file} bg_{pid}.log", workdir=work_dir)
                else:
                    # If we got garbage, stick to proc_id log, but we can't tell user PID easily.
                    # Fallback to proc_id if PID extraction failed (unlikely with echo $!)
                    pass
            except:
                pass

            return {
                "success": True,
                "pid": pid,
                "message": f"Process started with PID {pid}. Logs at bg_{pid}.log"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_background_logs(self, pid: str, lines: int = 50, work_dir: str = "/app") -> Dict[str, Any]:
        """Reads the logs of a background process."""
        try:
            self._ensure_sandbox()
            log_file = f"bg_{pid}.log"

            cmd = f"tail -n {lines} {log_file}"
            result = self.container.exec_run(["sh", "-c", cmd], workdir=work_dir)

            if result.exit_code != 0:
                 return {"success": False, "error": f"Log file not found or empty for PID {pid}"}

            return {
                "success": True,
                "logs": result.output.decode('utf-8', errors='replace')
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_background_process(self, pid: str) -> Dict[str, Any]:
        """Stops a background process."""
        try:
            self._ensure_sandbox()
            cmd = f"kill {pid}"
            result = self.container.exec_run(["sh", "-c", cmd])

            if result.exit_code != 0:
                # Try force kill
                cmd = f"kill -9 {pid}"
                result = self.container.exec_run(["sh", "-c", cmd])

            return {
                "success": result.exit_code == 0,
                "output": result.output.decode()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_background_input(self, pid: str, text: str) -> Dict[str, Any]:
        """
        Sends input to stdin of a background process.
        Current implementation limitation: Requires process to be reading from a pipe.
        For now, this is a placeholder or requires advanced setup.
        """
        return {"success": False, "error": "Interactive input to background processes not yet supported in Docker mode."}
