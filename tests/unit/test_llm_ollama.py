import os
import pytest
import json
from unittest.mock import patch, MagicMock
from src.core.llm.provider import LLMProvider
from pydantic import BaseModel

class MockSchema(BaseModel):
    reasoning: str
    answer: str

@pytest.fixture
def ollama_env():
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "ollama",
        "OLLAMA_LLM_MODEL": "llama3.2",
        "OLLAMA_BASE_URL": "http://ollama:11434"
    }):
        yield

def test_ollama_initialization(ollama_env):
    with patch("src.core.llm.provider.ChatOllama") as MockChatOllama:
        provider = LLMProvider()
        llm = provider.get_llm()

        MockChatOllama.assert_called()
        # The last call should be the one creating the instance
        call_kwargs = MockChatOllama.call_args.kwargs
        assert call_kwargs["model"] == "llama3.2"
        assert call_kwargs["base_url"] == "http://ollama:11434"

def test_ollama_generate_response_simple(ollama_env):
    with patch("src.core.llm.provider.ChatOllama") as MockChatOllama:
        mock_instance = MockChatOllama.return_value
        mock_instance.invoke.return_value.content = "Ollama response"

        provider = LLMProvider()
        response = provider.generate_response("Test prompt")

        assert response == "Ollama response"
        mock_instance.invoke.assert_called_once()

def test_ollama_structured_output_success(ollama_env):
    with patch("src.core.llm.provider.ChatOllama") as MockChatOllama:
        mock_instance = MockChatOllama.return_value

        # Mock successful structured output
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = MockSchema(reasoning="Because", answer="42")
        mock_instance.with_structured_output.return_value = mock_structured

        provider = LLMProvider()
        response = provider.generate_response("Test prompt", schema=MockSchema)

        # Parse JSON response to verify
        data = json.loads(response)
        assert data["reasoning"] == "Because"
        assert data["answer"] == "42"

        mock_instance.with_structured_output.assert_called_once_with(MockSchema)

def test_ollama_structured_output_fallback(ollama_env):
    with patch("src.core.llm.provider.ChatOllama") as MockChatOllama:
        # First instance (created in __init__ or get_llm)
        mock_instance_1 = MagicMock()
        mock_instance_1.with_structured_output.side_effect = Exception("Not supported")

        # Second instance (fallback created in exception block)
        mock_instance_2 = MagicMock()
        mock_instance_2.invoke.return_value.content = '{"reasoning": "Fallback", "answer": "OK"}'

        # We need to manage the side_effect of the class constructor
        # 1. get_llm calls ChatOllama() -> returns mock_instance_1
        # 2. generate_response calls ChatOllama(..., format="json") -> returns mock_instance_2
        MockChatOllama.side_effect = [mock_instance_1, mock_instance_2]

        provider = LLMProvider()
        response = provider.generate_response("Test prompt", schema=MockSchema)

        # Verify fallback logic
        data = json.loads(response)
        assert data["reasoning"] == "Fallback"
        assert MockChatOllama.call_count == 2

        # Check that second call had format="json"
        assert MockChatOllama.call_args_list[1].kwargs.get("format") == "json"

def test_ollama_structured_output_fallback_with_markdown(ollama_env):
    with patch("src.core.llm.provider.ChatOllama") as MockChatOllama:
        mock_instance_1 = MagicMock()
        mock_instance_1.with_structured_output.side_effect = Exception("Not supported")

        mock_instance_2 = MagicMock()
        # Simulate markdown wrapped JSON
        mock_instance_2.invoke.return_value.content = 'Here is the json:\n```json\n{"reasoning": "Markdown", "answer": "Yes"}\n```'

        MockChatOllama.side_effect = [mock_instance_1, mock_instance_2]

        provider = LLMProvider()
        response = provider.generate_response("Test prompt", schema=MockSchema)

        data = json.loads(response)
        assert data["reasoning"] == "Markdown"
