import pytest
from unittest.mock import patch, mock_open, MagicMock
import os
from src.tools.core_tools import (
    write_file, read_file, list_files, execute_command,
    search_codebase, update_codebase_memory, _resolve_path
)

@pytest.fixture
def mock_workspace(tmp_path):
    # We patch WORKSPACE_PATH where it is defined
    with patch("src.tools.core_tools.WORKSPACE_PATH", str(tmp_path)):
        yield tmp_path

def test_resolve_path_valid(mock_workspace):
    path = _resolve_path("test.txt")
    assert path == os.path.join(mock_workspace, "test.txt")

def test_resolve_path_traversal(mock_workspace):
    with pytest.raises(ValueError, match="fora do workspace"):
        _resolve_path("../../etc/passwd")

def test_write_file_success(mock_workspace):
    # invoke with string input (filename, content are args) but tool invoke takes dict or str
    # For multi-arg tools, invoke takes dict
    result = write_file.invoke({"filename": "test.txt", "content": "hello"})
    assert "escrito com sucesso" in result
    assert (mock_workspace / "test.txt").read_text(encoding="utf-8") == "hello"

def test_read_file_success(mock_workspace):
    (mock_workspace / "test.txt").write_text("hello", encoding="utf-8")
    content = read_file.invoke("test.txt")
    assert content == "hello"

def test_read_file_not_found(mock_workspace):
    result = read_file.invoke("missing.txt")
    assert "não encontrado" in result

def test_list_files_success(mock_workspace):
    (mock_workspace / "a.txt").touch()
    (mock_workspace / "b.txt").touch()
    result = list_files.invoke(".")
    assert "a.txt" in result
    assert "b.txt" in result

@patch("src.tools.core_tools.SecureExecutorTool")
def test_execute_command_success(MockExecutor, mock_workspace):
    mock_instance = MockExecutor.return_value
    mock_instance.run_command.return_value = {"exit_code": 0, "output": "Done"}

    result = execute_command.invoke("echo hi")
    assert "Código de Saída: 0" in result
    assert "Done" in result

@patch("src.tools.core_tools.VectorMemory")
def test_search_codebase_success(MockMemory):
    mock_instance = MockMemory.return_value
    mock_instance.search.return_value = [("def foo(): pass", {"source": "foo.py"})]

    result = search_codebase.invoke("foo")
    assert "foo.py" in result
    assert "def foo(): pass" in result

@patch("src.tools.core_tools.CodeIndexer")
def test_update_codebase_memory_success(MockIndexer):
    mock_instance = MockIndexer.return_value

    # invoke() calls the function.
    result = update_codebase_memory.invoke({})
    assert "sucesso" in result

    # Check call count
    assert mock_instance.index_workspace.call_count >= 1
