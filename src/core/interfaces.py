from typing import Protocol, Dict, Any, Optional, Type, Union, List
from pydantic import BaseModel

class ILLMProvider(Protocol):
    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None
    ) -> Union[str, BaseModel]:
        ...

class IFileSystem(Protocol):
    def read_file(self, filepath: str) -> str:
        ...

    def write_file(self, filepath: str, content: str) -> str:
        ...

    def get_project_structure(self) -> str:
        ...

class IExecutor(Protocol):
    def run_command(self, command: str, work_dir: str = "/app") -> Dict[str, Any]:
        ...

    def start_background_process(self, command: str, work_dir: str = "/app") -> Dict[str, Any]:
        ...

    def read_background_logs(self, pid: str, lines: int = 50, work_dir: str = "/app") -> Dict[str, Any]:
        ...

    def stop_background_process(self, pid: str) -> Dict[str, Any]:
        ...

    def send_background_input(self, pid: str, text: str) -> Dict[str, Any]:
        ...

    def create_directory(self, path: str) -> Dict[str, Any]:
        ...
