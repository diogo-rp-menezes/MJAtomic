from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.core.config.settings import settings


class LLM:
    """
    Factory class for creating language model instances.
    """

    def __init__(self, model_name: str = "default"):
        self.provider = settings.LLM_PROVIDER.lower()
        self.model_name = self._get_model_name(model_name)

    def _get_model_name(self, model_type: str) -> str:
        """
        Returns the appropriate model name based on the provider and model type.
        """
        models = {
            "openai": {"default": "gpt-4-turbo", "smart": "gpt-4-turbo", "fast": "gpt-3.5-turbo"},
            "anthropic": {
                "default": "claude-3-opus-20240229",
                "smart": "claude-3-opus-20240229",
                "fast": "claude-3-sonnet-20240229",
            },
            "google": {
                "default": "gemini-pro",
                "smart": "gemini-1.5-pro-latest",
                "fast": "gemini-pro",
            },
        }
        return models.get(self.provider, {}).get(model_type, "default-model")

    def get_llm(self) -> BaseLanguageModel:
        """
        Returns an instance of the language model based on the configured provider.
        """
        if self.provider == "openai":
            return ChatOpenAI(model=self.model_name, api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            return ChatAnthropic(model=self.model_name, api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "google":
            return ChatGoogleGenerativeAI(
                model=self.model_name, google_api_key=settings.GOOGLE_API_KEY
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
