import pytest
from unittest.mock import patch, MagicMock
import os
from src.core.llm.provider import LLMProvider
from langchain_google_genai import ChatGoogleGenerativeAI

class TestLLMProviderConfig:
    @patch.dict(os.environ, {"LLM_PROVIDER": "google", "GOOGLE_API_KEY": "fake_key"})
    def test_google_defaults(self):
        # Default profile (should be smart/balanced -> gemini-2.5-pro)
        provider = LLMProvider()
        llm = provider._create_llm_instance()
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.model == "models/gemini-2.5-pro"

    @patch.dict(os.environ, {"LLM_PROVIDER": "google", "GOOGLE_API_KEY": "fake_key"})
    def test_google_fast_profile(self):
        provider = LLMProvider(profile="fast")
        llm = provider._create_llm_instance()
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.model == "models/gemini-2.5-flash"

    @patch.dict(os.environ, {"LLM_PROVIDER": "google", "GOOGLE_API_KEY": "fake_key"})
    def test_google_smart_profile(self):
        provider = LLMProvider(profile="smart")
        llm = provider._create_llm_instance()
        assert isinstance(llm, ChatGoogleGenerativeAI)
        # Assuming smart falls back to the default else branch which is gemini-2.5-pro
        assert llm.model == "models/gemini-2.5-pro"
