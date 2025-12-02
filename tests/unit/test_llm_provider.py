import unittest
from unittest.mock import patch, MagicMock
import os
from pydantic import BaseModel

# Importa a classe a ser testada
from src.core.llm.provider import LLMProvider

# Mock de uma classe de schema para testes
class MockSchema(BaseModel):
    name: str
    age: int

class TestLLMProvider(unittest.TestCase):

    @patch('src.core.llm.provider.ChatGoogleGenerativeAI')
    def test_key_rotation(self, mock_chat_google):
        """
        Verifica que o LLMProvider rotaciona as chaves de API em chamadas subsequentes.
        """
        # Define um ambiente mockado e limpo
        mock_env = {
            'LLM_PROVIDER': 'google',
            'GOOGLE_API_KEY': 'key_0',
            'GOOGLE_API_KEY_1': 'key_1',
            'GOOGLE_API_KEY_2': 'key_2'
        }

        # Garante que nenhuma outra chave GOOGLE_API_KEY_* exista no ambiente do teste
        # O `clear=True` no patch.dict garante que o ambiente seja limpo antes de aplicar o mock.
        with patch.dict(os.environ, mock_env, clear=True):
            provider = LLMProvider(model_name="test_model")

            # Chama get_llm várias vezes
            provider.get_llm()  # Deve usar key_0
            provider.get_llm()  # Deve usar key_1
            provider.get_llm()  # Deve usar key_2
            provider.get_llm()  # Deve voltar para key_0

            # Verifica as chamadas
            self.assertEqual(mock_chat_google.call_count, 4)
            calls = mock_chat_google.call_args_list

            # Verifica se a chave correta foi usada em cada chamada
            self.assertEqual(calls[0].kwargs.get('google_api_key'), 'key_0')
            self.assertEqual(calls[1].kwargs.get('google_api_key'), 'key_1')
            self.assertEqual(calls[2].kwargs.get('google_api_key'), 'key_2')
            self.assertEqual(calls[3].kwargs.get('google_api_key'), 'key_0')

    # ... (outros testes podem ser adicionados aqui) ...
