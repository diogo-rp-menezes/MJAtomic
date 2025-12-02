import os
import time
import json
from typing import Optional, List, Type, Any, Union
from pydantic import BaseModel
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.logger import logger

class LLMProvider:
    def __init__(self, model_name: str, base_url: str = None):
        self.model_name = model_name

        if base_url:
            self.provider = "ollama"
            self.ollama_base_url = base_url
        else:
            self.provider = os.getenv("LLM_PROVIDER", "google").lower()
            self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        if self.provider == "google":
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
        if not keys:
             return ["mock-key"]
        return keys

    def _get_next_key(self) -> str:
        if not hasattr(self, 'keys') or not self.keys:
            return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    def _create_llm_instance(self) -> BaseLanguageModel:
        if self.provider == "ollama":
            logger.info(f"Usando Ollama LLM com o modelo: {self.model_name} em {self.ollama_base_url}")
            return ChatOllama(
                model=self.model_name,
                base_url=self.ollama_base_url,
                format="json"
            )

        logger.info(f"Usando Google LLM com o modelo: {self.model_name}")
        current_key = self._get_next_key()
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=current_key,
            temperature=0.5,
            convert_system_message_to_human=True
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
    ) -> str:
        llm = self.get_llm()
        json_mode = schema is not None
        response_data = ""

        try:
            messages = [HumanMessage(content=prompt)]
            if system_message:
                messages.insert(0, SystemMessage(content=system_message))

                    response = structured_llm.invoke(messages)
                except Exception as e:
                    if self.provider == "ollama":
                        print(f"⚠️ Structured output failed for Ollama, retrying with JSON mode. Error: {e}")
                        llm_json = ChatOllama(
                            model=self.model_name,
                            base_url=self.ollama_base_url,
                            temperature=0.5,
                            format="json"
                        )

                        schema_json = schema.model_json_schema()
                        json_instructions = f"\n\nRespond strictly with a valid JSON object matching this schema:\n{schema_json}"

                        messages = [HumanMessage(content=prompt)]
                        if system_message:
                            messages.insert(0, SystemMessage(content=system_message + json_instructions))
                        else:
                            messages.insert(0, SystemMessage(content=json_instructions))

                        response_raw = llm_json.invoke(messages)
                        response_content = response_raw.content
                        if "```json" in response_content:
                            response_content = response_content.split("```json")[1].split("```")[0].strip()
                        elif "```" in response_content:
                            response_content = response_content.split("```")[1].split("```")[0].strip()

                        import json
                        parsed_json = json.loads(response_content)
                        try:
                            response = schema.model_validate(parsed_json)
                        except Exception as val_e:
                            print(f"⚠️ Schema validation failed: {val_e}. Returning raw JSON.")
                            response = parsed_json
                    elif self.provider == 'google' and json_mode:
                        structured_llm = llm.with_structured_output(schema)
                        response = structured_llm.invoke(messages)
                    else:
                        raise e
                if isinstance(response, BaseModel):
                    response_data = response.model_dump_json()
                else:
                    response_data = json.dumps(response)

            # Se não for modo JSON, para qualquer provedor.
            else:
                response = llm.invoke(messages)
                response_data = response.content

        except Exception as e:
            logger.error(f"❌ LLM Error: {e}")
            response_data = "{}" if json_mode else f"Error: {str(e)}"
        
        finally:
            self._apply_delay()
            return response_data
