import unittest
import os
from unittest.mock import patch, MagicMock
from pydantic import BaseModel, Field

# Importe as classes necessárias do seu projeto
from src.core.llm.provider import LLMProvider
from langchain_google_genai import ChatGoogleGenerativeAI

# Defina um schema Pydantic simples para o teste
class TestSchema(BaseModel):
    name: str = Field(description="The name of the item")
    value: int = Field(description="A numerical value")

class TestLLMProvider(unittest.TestCase):

    @patch('src.core.llm.provider.ChatGoogleGenerativeAI')
    def test_generate_response_google_structured_output(self, mock_chat_google):
        """
        Verifica se o LLMProvider chama .with_structured_output() para o Google
        quando um schema é fornecido.
        """
        # --- Configuração ---
        # Mock para a instância do LLM e o método with_structured_output
        mock_structured_llm = MagicMock()
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_chat_google.return_value = mock_llm_instance

        # Força o provedor a ser 'google' no ambiente de teste
        with patch('src.core.llm.provider.os.getenv', side_effect=lambda k, v='google': {'LLM_PROVIDER': 'google'}.get(k, v)):
            provider = LLMProvider(model_name="gemini-test")

        # --- Ação ---
        provider.generate_response(
            prompt="Test prompt",
            schema=TestSchema
        )

        # --- Verificação ---
        # 1. Verifica se `with_structured_output` foi chamado com o schema correto
        mock_llm_instance.with_structured_output.assert_called_once_with(TestSchema)

        # 2. Verifica se o método `invoke` foi chamado no objeto retornado por `with_structured_output`
        mock_structured_llm.invoke.assert_called_once()

    @patch('src.core.llm.provider.ChatGoogleGenerativeAI')
    def test_key_rotation(self, mock_chat_google):
        """
        Verifies that LLMProvider rotates through API keys on subsequent calls.
        """
        # Mock API keys in environment
        mock_env = {
            'LLM_PROVIDER': 'google',
            'GOOGLE_API_KEY': 'key_0',
            'GOOGLE_API_KEY_1': 'key_1',
            'GOOGLE_API_KEY_2': 'key_2'
        }

        with patch.dict(os.environ, mock_env):
            # Create provider - should load keys [key_0, key_1, key_2]
            provider = LLMProvider(model_name="gemini-test")

            # Call get_llm multiple times
            provider.get_llm() # Should use key_0
            provider.get_llm() # Should use key_1
            provider.get_llm() # Should use key_2
            provider.get_llm() # Should cycle back to key_0

        # Verify calls
        self.assertEqual(mock_chat_google.call_count, 4)

        calls = mock_chat_google.call_args_list

        # Check first call
        self.assertEqual(calls[0].kwargs.get('google_api_key'), 'key_0')
        # Check second call
        self.assertEqual(calls[1].kwargs.get('google_api_key'), 'key_1')
        # Check third call
        self.assertEqual(calls[2].kwargs.get('google_api_key'), 'key_2')
        # Check fourth call (wrapped around)
        self.assertEqual(calls[3].kwargs.get('google_api_key'), 'key_0')

if __name__ == '__main__':
    unittest.main()
