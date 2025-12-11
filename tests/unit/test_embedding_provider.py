import pytest
from unittest.mock import patch
from src.core.llm.embedding_provider import EmbeddingProvider
from src.core.config import settings

def test_embedding_provider_uses_specific_url():
    """Test that EmbeddingProvider prioritizes OLLAMA_EMBEDDING_URL when set."""
    with patch.object(settings, 'EMBEDDING_PROVIDER', 'ollama'), \
         patch.object(settings, 'OLLAMA_EMBEDDING_URL', 'http://specific-url:11434'), \
         patch.object(settings, 'OLLAMA_BASE_URL', 'http://general-url:1234'), \
         patch.object(settings, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text'):

        provider = EmbeddingProvider()

        # Verify that it picked the specific URL, not the general one
        assert provider.ollama_base_url == 'http://specific-url:11434'
        assert provider.ollama_model_name == 'nomic-embed-text'

def test_embedding_provider_fallback_to_base_url():
    """Test that EmbeddingProvider falls back to OLLAMA_BASE_URL when OLLAMA_EMBEDDING_URL is missing."""
    with patch.object(settings, 'EMBEDDING_PROVIDER', 'ollama'), \
         patch.object(settings, 'OLLAMA_EMBEDDING_URL', None), \
         patch.object(settings, 'OLLAMA_BASE_URL', 'http://general-url:1234'):

        provider = EmbeddingProvider()

        # Verify that it falls back to base URL
        assert provider.ollama_base_url == 'http://general-url:1234'
