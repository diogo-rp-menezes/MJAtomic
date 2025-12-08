import unittest
from unittest.mock import patch, MagicMock
import os
import json
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

# Importa a classe a ser testada
from src.core.llm.provider import LLMProvider
# LocalOpenAIClient is now in its own module
from src.core.llm.clients.local_openai import LocalOpenAIClient

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
        # We need enough keys for:
        # 1. __init__ call
        # 2. get_llm() call 1
        # 3. get_llm() call 2
        # 4. get_llm() call 3
        mock_key_manager.get_next_key.side_effect = ['key_A', 'key_B', 'key_C', 'key_D']

        # Configure env to use google
        with patch.dict(os.environ, {'LLM_PROVIDER': 'google'}, clear=True):
             with patch('src.core.llm.provider.settings') as mock_settings:
                mock_settings.LLM_PROVIDER = "google"
                mock_settings.OLLAMA_BASE_URL = None

                provider = LLMProvider(model_name="test_model")

                # Check initial instance
                self.assertIsNotNone(provider.llm)

                # Call get_llm() multiple times
                llm1 = provider.get_llm()
                llm2 = provider.get_llm()
                llm3 = provider.get_llm()

                # Expect 4 calls total: 1 from __init__, 3 from get_llm()
                self.assertEqual(mock_chat_google.call_count, 4)
                calls = mock_chat_google.call_args_list

                # Verify keys passed to ChatGoogleGenerativeAI match what key_manager returned
                self.assertEqual(calls[0].kwargs.get('google_api_key'), 'key_A') # __init__
                self.assertEqual(calls[1].kwargs.get('google_api_key'), 'key_B') # get_llm 1
                self.assertEqual(calls[2].kwargs.get('google_api_key'), 'key_C') # get_llm 2
                self.assertEqual(calls[3].kwargs.get('google_api_key'), 'key_D') # get_llm 3

    @patch('src.core.llm.clients.local_openai.urllib.request.urlopen')
    @patch('src.core.llm.clients.local_openai.json.load')
    def test_local_openai_client(self, mock_json_load, mock_urlopen):
        """
        Tests the LocalOpenAIClient invoke method.
        """
        # Mock HTTP response context manager
        mock_response = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        mock_json_load.return_value = {
            "choices": [{"message": {"content": "Hello Local"}}]
        }

        client = LocalOpenAIClient(model_name="test-local", base_url="http://localhost:1234")
        resp = client.invoke([HumanMessage(content="Hi")])

        self.assertEqual(resp.content, "Hello Local")

        # Verify URL
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertEqual(req.full_url, "http://localhost:1234/v1/chat/completions")

    @patch('src.core.llm.clients.local_openai.urllib.request.urlopen')
    @patch('src.core.llm.clients.local_openai.json.load')
    def test_generate_response_local_fallback(self, mock_json_load, mock_urlopen):
        """
        Tests that generate_response works with Local provider (Plan B).
        """
        expected_json = '{"name": "Alice", "age": 30}'

        # Mock successful response
        mock_response = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # We need to handle possible multiple calls if it falls back, but let's assume Plan B works
        mock_json_load.return_value = {
            "choices": [{"message": {"content": expected_json}}]
        }

        # Setup provider as 'local' explicitly to avoid Google auth error
        provider = LLMProvider(model_name="test-local", base_url="http://localhost:1234", provider="local")

        # It should use Plan B (native structured output for local)
        result_obj = provider.generate_response("User prompt", schema=MockSchema)

        # Verify the result is parsed correctly and is an instance of MockSchema
        self.assertIsInstance(result_obj, MockSchema)
        self.assertEqual(result_obj.name, "Alice")
        self.assertEqual(result_obj.age, 30)

    @patch('src.core.llm.provider.ChatGoogleGenerativeAI')
    @patch('src.core.llm.provider.key_manager')
    def test_generate_response_google_structured_output(self, mock_key_manager, mock_chat_google):
        """
        Tests that generate_response uses with_structured_output when using Google provider.
        """
        # Mock structured LLM
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = MockSchema(name="Bob", age=40)

        # Mock base LLM
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm

        mock_chat_google.return_value = mock_llm_instance

        with patch('src.core.llm.provider.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "google"

            # Explicitly set provider="google" to ensure isolation
            provider = LLMProvider(model_name="test-google", provider="google")

            # Reset mock to clear __init__ call
            mock_llm_instance.reset_mock()

            result_obj = provider.generate_response("User prompt", schema=MockSchema)

            self.assertIsInstance(result_obj, MockSchema)
            self.assertEqual(result_obj.name, "Bob")
            self.assertEqual(result_obj.age, 40)

            # Verify with_structured_output was called
            mock_llm_instance.with_structured_output.assert_called_with(MockSchema)
