import docker
import os
from typing import Dict, Any
from src.core.logger import logger

class SecureExecutorTool:
    def __init__(self, workspace_path: str):
        self.client = docker.from_env()
        self.image = "devagent-sandbox"
        self.workspace_path = os.path.abspath(workspace_path)

    def run_command(self, command: str, work_dir: str = "/app") -> Dict[str, Any]:
        try:
            # Garante que o diretório local existe
            os.makedirs(self.workspace_path, exist_ok=True)

            # FIX CRÍTICO PARA DOCKER-IN-DOCKER (DinD):
            # Se o DevAgent estiver rodando dentro de um container, 'self.workspace_path' é um caminho interno.
            # O daemon do Docker (no host) precisa saber o caminho REAL no host para montar o volume corretamente.
            # Usamos a variável de ambiente HOST_WORKSPACE_PATH para isso.
            host_path = os.getenv("HOST_WORKSPACE_PATH", self.workspace_path)

            container = self.client.containers.run(
                self.image,
                command=f"sh -c '{command}'",
                detach=True,
                working_dir=work_dir,
                # Monta o caminho do host (se definido) ou o caminho local
                volumes={host_path: {'bind': '/app', 'mode': 'rw'}},
                user=0,
                mem_limit="1024m",
                network_disabled=False
            )

            result = container.wait()
            logs = container.logs().decode('utf-8')
            container.remove()

            return {
                "exit_code": result['StatusCode'],
                "output": logs,
                "success": result['StatusCode'] == 0
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
