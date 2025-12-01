import os
from dotenv import load_dotenv
from typing import Optional, List, Type, Any, Union
from pydantic import BaseModel
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

class LLMProvider:
    def __init__(self, profile: str = "balanced"):
        self.profile = profile
        self.provider = "google"
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
             return ["mock-key"]
        return keys

    def _get_next_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    def _create_llm_instance(self) -> BaseLanguageModel:
        """Cria e retorna uma instância do modelo LLM configurado."""
        current_key = self._get_next_key()

        model_name = os.getenv("LLM_MODEL_FAST", "gemini-2.5-flash") if self.profile == "fast" else os.getenv("LLM_MODEL_SMART", "gemini-2.5-pro")

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=current_key,
            temperature=0.2 if self.profile == "fast" else 0.5,
            convert_system_message_to_human=True,
            max_retries=2
        )

    def get_llm(self) -> BaseLanguageModel:
        """
        Retorna uma instância configurada do modelo LLM do LangChain.
        Ideal para uso com agentes LangChain.
        """
        return self._create_llm_instance()

    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None
    ) -> Union[str, BaseModel]:
        """Gera uma resposta direta do LLM, com suporte opcional a schema JSON."""
        llm = self.get_llm()
        json_mode = schema is not None

        try:
            # If schema is provided, we use the model's structured output capability if available.
            # with_structured_output typically returns a Pydantic object directly.
            if json_mode:
                structured_llm = llm.with_structured_output(schema)

                messages = []
                if system_message:
                    messages.append(SystemMessage(content=system_message))
                messages.append(HumanMessage(content=prompt))

                response = structured_llm.invoke(messages)

                # with_structured_output returns the parsed object (or dict), so we return its json representation
                # to keep the interface consistent (returning str), or we adjust caller to handle object.
                # The prompt plan says "generate_response returns json string", so we dump it.
                if isinstance(response, BaseModel):
                    return response.model_dump_json()
                elif isinstance(response, dict):
                    import json
                    return json.dumps(response)
                else:
                    # Fallback if it returned something else, although unlikely with structured_output
                    return str(response)

            else:
                messages = []
                if system_message:
                    messages.append(SystemMessage(content=system_message))
                messages.append(HumanMessage(content=prompt))

                response = llm.invoke(messages)
                return response.content

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return "{}" if json_mode else f"Error: {str(e)}"
