import os
import time
import random
from dotenv import load_dotenv
from typing import Optional, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

load_dotenv()

class LLMProvider:
    def __init__(self, profile: str = "balanced"):
        self.profile = profile
        self.provider = os.getenv("LLM_PROVIDER", "google").lower()
        self.keys = self._load_api_keys()
        self.current_key_index = 0

    def _load_api_keys(self) -> List[str]:
        keys = []
        main_key = os.getenv("GOOGLE_API_KEY")
        if main_key: keys.append(main_key)
        for i in range(1, 11):
            k = os.getenv(f"GOOGLE_API_KEY_{i}")
            if k: keys.append(k)

        if not keys and self.provider == "google":
             # Fallback silencioso para testes sem chave
             return ["mock-key"]
        return keys

    def _get_next_key(self) -> str:
        if not self.keys: return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    def generate_response(self, prompt: str, system_message: Optional[str] = None, json_mode: bool = False) -> str:

        # Configuração específica para JSON Mode dependendo do provedor
        model_kwargs = {}
        if json_mode and self.provider == "openai":
            model_kwargs = {"response_format": {"type": "json_object"}}

        # Google Gemini não tem "json_mode" estrito na API pública via LangChain ainda,
        # mas aceita bem instruções no prompt.
        # Para OpenAI, usamos o parâmetro nativo.

        current_key = self._get_next_key()

        try:
            if self.provider == "openai":
                llm = ChatOpenAI(
                    model="gpt-4-turbo-preview" if self.profile == "smart" else "gpt-3.5-turbo",
                    api_key=os.getenv("OPENAI_API_KEY"),
                    model_kwargs=model_kwargs
                )
            elif self.provider == "anthropic":
                 llm = ChatAnthropic(
                    model="claude-3-opus-20240229" if self.profile == "smart" else "claude-3-haiku-20240307",
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                 )
            else: # Google Default
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=current_key,
                    temperature=0.2,
                    convert_system_message_to_human=True,
                    max_retries=2
                )

            messages = []
            if system_message:
                if json_mode and self.provider == "google":
                     system_message += "\n\nIMPORTANT: Output ONLY valid JSON."
                messages.append(SystemMessage(content=system_message))

            messages.append(HumanMessage(content=prompt))

            # print(f"🤖 LLM Call [{self.profile}] (JSON: {json_mode})")
            response = llm.invoke(messages)
            return response.content

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            # Fallback simples para evitar crash total
            return "{}" if json_mode else f"Error: {str(e)}"
