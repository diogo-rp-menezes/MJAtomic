import os
from dotenv import load_dotenv
from typing import Optional, List, Type
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

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
        if main_key:
            keys.append(main_key)
        for i in range(1, 11):
            k = os.getenv(f"GOOGLE_API_KEY_{i}")
            if k:
                keys.append(k)

        if not keys and self.provider == "google":
             # Fallback silencioso para testes sem chave
             return ["mock-key"]
        return keys

    def _get_next_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None
    ) -> str:
        json_mode = schema is not None
        model_kwargs = {}

        if json_mode and self.provider == "openai":
            model_kwargs = {"response_format": {"type": "json_object"}}

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
            else:  # Google Default
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=current_key,
                    temperature=0.2,
                    convert_system_message_to_human=True,
                    max_retries=2
                )

            if json_mode:
                if self.provider == "google":
                    llm = llm.with_structured_output(schema)
                # A lógica do OpenAI já está coberta por model_kwargs

            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))

            messages.append(HumanMessage(content=prompt))

            response = llm.invoke(messages)

            if isinstance(response, BaseModel):
                return response.model_dump_json()

            # Para OpenAI e outros que retornam uma BaseMessage
            if hasattr(response, 'content'):
                return response.content

            # Fallback para outros tipos de resposta
            return str(response)

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return "{}" if json_mode else f"Error: {str(e)}"
