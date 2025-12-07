import unittest
from unittest.mock import patch, MagicMock
import os
import json
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

# Importa a classe a ser testada
from src.core.llm.provider import LLMProvider, LocalOpenAIClient

# Mock de uma classe de schema para testes
class MockSchema(BaseModel):
    name: str
    age: int

class TestLLMProvider(unittest.TestCase):

    @patch('src.core.llm.provider.ChatGoogleGenerativeAI')
    @patch('src.core.llm.provider.key_manager')
    def test_key_rotation_integration(self, mock_key_manager, mock_chat_google):
        """
        Verifies that LLMProvider uses the key manager to obtain keys.
        """
        # Configure mock manager to return specific keys
        mock_key_manager.get_next_key.side_effect = ['key_A', 'key_B', 'key_A']

        # Configure env to use google
        with patch.dict(os.environ, {'LLM_PROVIDER': 'google'}, clear=True):
            # We also need to patch settings because LLMProvider reads settings.LLM_PROVIDER
            # but we can assume default or mocked settings if we patch 'src.core.config.settings'
            # OR just rely on the env var being read by settings IF settings were reloaded,
            # but settings is instantiated at import time.
            # So we should patch settings in the provider module.

             with patch('src.core.llm.provider.settings') as mock_settings:
                mock_settings.LLM_PROVIDER = "google"
                mock_settings.OLLAMA_BASE_URL = None

                provider = LLMProvider(model_name="test_model")
                provider.get_llm()
                provider.get_llm()
                provider.get_llm()

                self.assertEqual(mock_chat_google.call_count, 3)
                calls = mock_chat_google.call_args_list

                # Verify keys passed to ChatGoogleGenerativeAI match what key_manager returned
                self.assertEqual(calls[0].kwargs.get('google_api_key'), 'key_A')
                self.assertEqual(calls[1].kwargs.get('google_api_key'), 'key_B')
                self.assertEqual(calls[2].kwargs.get('google_api_key'), 'key_A')

    @patch('src.core.llm.provider.urllib.request.urlopen')
    def test_local_openai_client(self, mock_urlopen):
        """
        Tests the LocalOpenAIClient invoke method.
        """
        # Mock HTTP response context manager
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Hello Local"}}]
        }).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        mock_urlopen.return_value = mock_response

        client = LocalOpenAIClient(model_name="test-local", base_url="http://localhost:1234")
        resp = client.invoke([HumanMessage(content="Hi")])

        self.assertEqual(resp.content, "Hello Local")

        # Verify URL
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertEqual(req.full_url, "http://localhost:1234/v1/chat/completions")

    @patch('src.core.llm.provider.urllib.request.urlopen')
    def test_generate_response_local_fallback(self, mock_urlopen):
        """
        Tests that generate_response falls back to manual JSON prompting when
        LocalOpenAIClient (which lacks with_structured_output) is used.
        """
        # Mock response for the 'invoke' call.
        # Expecting a JSON string as content because we force JSON mode in fallback.
        expected_json = '{"name": "Alice", "age": 30}'

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": expected_json}}]
        }).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        # Setup provider as 'local'
        provider = LLMProvider(model_name="test-local", base_url="http://localhost:1234")

        # It should trigger the fallback logic because LocalOpenAIClient has no with_structured_output
        result_json = provider.generate_response("User prompt", schema=MockSchema)

        # Verify the result is parsed correctly
        result_dict = json.loads(result_json)
        self.assertEqual(result_dict["name"], "Alice")
        self.assertEqual(result_dict["age"], 30)
