import pytest
import os
from src.tools.file_io import FileIOTool

@pytest.fixture
def file_io(tmp_path):
    return FileIOTool(root_path=str(tmp_path))

def test_write_read_file(file_io):
    file_io.write_file("test.txt", "hello")
    content = file_io.read_file("test.txt")
    assert content == "hello"

def test_sanitize_content(file_io):
    raw = "```python\nprint('hi')\n```"
    sanitized = file_io._sanitize_content(raw)
    assert sanitized == "print('hi')"

def test_read_file_sanitization(file_io):
    # If file on disk has markdown
    path = os.path.join(file_io.root_path, "md.txt")
    with open(path, "w") as f:
        f.write("```python\ncode\n```")

    content = file_io.read_file("md.txt")
    assert content == "code"

def test_get_project_structure(file_io):
    file_io.write_file("src/main.py", "print('main')")
    structure = file_io.get_project_structure()
    assert "src/" in structure
    assert "main.py" in structure
    assert "CONTENT (main.py)" in structure

def test_security_traversal(file_io):
    with pytest.raises(ValueError):
        file_io.write_file("../out.txt", "bad")
