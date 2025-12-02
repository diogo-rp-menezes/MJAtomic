import os
import time
from typing import Optional, List, Type, Any, Union
from pydantic import BaseModel
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

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
             return ["mock-key"]
        return keys

    def _get_next_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    def _create_llm_instance(self) -> BaseLanguageModel:
        current_key = self._get_next_key()
        return ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL_FAST", "gemini-2.5-flash") if self.profile == "fast" else os.getenv("LLM_MODEL_SMART", "gemini-2.5-pro"),
            google_api_key=current_key,
            temperature=0.2 if self.profile == "fast" else 0.5,
            convert_system_message_to_human=True,
            max_retries=2
        )

    def get_llm(self) -> BaseLanguageModel:
        return self._create_llm_instance()

    def _apply_delay(self):
        try:
            delay = float(os.getenv("REQUEST_DELAY_SECONDS", "1"))
            if delay > 0:
                time.sleep(delay)
        except (ValueError, TypeError):
            time.sleep(1)

    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None
    ) -> Union[str, BaseModel]:
        llm = self.get_llm()
        json_mode = schema is not None
        response_data = ""

        try:
            if json_mode:
                structured_llm = llm.with_structured_output(schema)
                messages = [HumanMessage(content=prompt)]
                if system_message:
                    messages.insert(0, SystemMessage(content=system_message))
                
                response = structured_llm.invoke(messages)

                if isinstance(response, BaseModel):
                    response_data = response.model_dump_json()
                elif isinstance(response, dict):
                    import json
                    response_data = json.dumps(response)
                else:
                    response_data = str(response)
            else:
                messages = [HumanMessage(content=prompt)]
                if system_message:
                    messages.insert(0, SystemMessage(content=system_message))
                
                response = llm.invoke(messages)
                response_data = response.content

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            response_data = "{}" if json_mode else f"Error: {str(e)}"
        
        finally:
            self._apply_delay()
            return response_data
