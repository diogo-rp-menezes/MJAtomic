import pytest
from unittest.mock import MagicMock, patch
from src.tools.architect.document_generator import DocumentGeneratorTool
from src.tools.architect.project_builder import StructureBuilderTool

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.fixture
def mock_file_io():
    return MagicMock()

def test_document_generator(mock_llm):
    tool = DocumentGeneratorTool(mock_llm)
    mock_llm.generate_response.return_value = "Markdown content"

    guideline = tool.generate_guideline("Proj", "Desc", "Stack")
    assert guideline == "Markdown content"

    mock_llm.generate_response.return_value = "`gitignore\nnode_modules\n`"
    gitignore = tool.generate_gitignore("Node")
    assert gitignore == "node_modules"

def test_structure_builder_generate(mock_llm, mock_file_io):
    tool = StructureBuilderTool(mock_llm, mock_file_io)
    mock_llm.generate_response.return_value = '{"directories": ["src"], "files": ["main.py"]}'

    struct = tool.generate_structure("Context")
    assert struct["directories"] == ["src"]

def test_structure_builder_build(mock_llm, mock_file_io):
    tool = StructureBuilderTool(mock_llm, mock_file_io)
    mock_llm.generate_response.return_value = "print('code')"

    struct = {"directories": ["src"], "files": ["src/main.py"]}
    tool.build_project(struct, "ctx", "name")

    mock_file_io.write_file.assert_called()
