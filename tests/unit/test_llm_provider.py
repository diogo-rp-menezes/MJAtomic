import unittest
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
            provider = LLMProvider()

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

if __name__ == '__main__':
    unittest.main()
