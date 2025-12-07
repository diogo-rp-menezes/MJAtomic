import os
import time
import json
import urllib.request
import urllib.error
from typing import Optional, List, Type, Any, Union, Dict
from pydantic import BaseModel
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from src.core.logger import logger
from src.core.config import settings
from src.core.utils.json_parser import extract_json_from_text

class LocalOpenAIClient:
    """
    Custom client to interact with OpenAI-compatible APIs (like LM Studio)
    using standard library, avoiding 'openai' package dependency.
    """
    def __init__(self, model_name: str, base_url: str, json_mode: bool = False):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        if not self.base_url.endswith("/v1"):
            self.base_url += "/v1"
        self.json_mode = json_mode

    def invoke(self, messages: List[BaseMessage]) -> Any:
        url = f"{self.base_url}/chat/completions"

        # Convert LangChain messages to OpenAI format
        formatted_messages = []
        for msg in messages:
            role = "user"
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "user"
            # Add support for AI messages if needed, but for now simplified

            formatted_messages.append({"role": role, "content": str(msg.content)})

        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": 0.5,
            "stream": False
        }

        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer lm-studio" # Dummy key
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req) as response:
                result = json.load(response)
                content = result["choices"][0]["message"]["content"]

                # Return an object compatible with LangChain response (has .content)
                class MockResponse:
                    def __init__(self, content):
                        self.content = content
                return MockResponse(content)

        except urllib.error.URLError as e:
            logger.error(f"Failed to connect to Local OpenAI API at {url}: {e}")
            raise

class LLMProvider:
    def __init__(self, model_name: str, base_url: str = None):
        self.model_name = model_name
        self.ollama_base_url = base_url

        # Determine provider
        if base_url:
            self.provider = "local" # Use custom LocalOpenAIClient
        else:
            self.provider = settings.LLM_PROVIDER

            # If explicit override via env var to use local logic globally
            if self.provider == "ollama" or self.provider == "local":
                 self.ollama_base_url = settings.OLLAMA_BASE_URL
                 if not self.ollama_base_url:
                     logger.warning("OLLAMA_BASE_URL not set for local provider. Defaulting to localhost:11434 is disabled.")
                 self.provider = "local" # Unify under "local"

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

    def _create_llm_instance(self, json_mode: bool = False) -> Any:
        if self.provider == "local":
            logger.info(f"Using Local LLM (OpenAI Compatible) with model: {self.model_name} at {self.ollama_base_url}")
            return LocalOpenAIClient(
                model_name=self.model_name,
                base_url=self.ollama_base_url,
                json_mode=json_mode
            )

        elif self.provider == "ollama_native": # Legacy support if needed
             return ChatOllama(
                model=self.model_name,
                base_url=self.ollama_base_url,
                format="json" if json_mode else None
            )

        logger.info(f"Using Google LLM with model: {self.model_name}")
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

            if json_mode:
                try:
                    # PLANO A: Tenta usar o structured output nativo
                    structured_llm = llm.with_structured_output(schema)
                    response = structured_llm.invoke(messages)

                    if isinstance(response, BaseModel):
                        response_data = response.model_dump_json()
                    else:
                        response_data = json.dumps(response)

                except (AttributeError, NotImplementedError, Exception) as e:
                    # Fallback for providers that don't support with_structured_output (like our LocalOpenAIClient)
                    logger.warning(f"Structured output not supported or failed: {e}. Trying with JSON mode prompt.")

                    try:
                        # PLANO B: Tenta usar o JSON mode da API
                        # Create a JSON-enforcing instance
                        llm_json = self._create_llm_instance(json_mode=True)

                        schema_json = schema.model_json_schema()
                        json_instructions = f"\n\nRespond strictly with a valid JSON object matching this schema:\n{json.dumps(schema_json, indent=2)}"

                        # Clone messages to avoid modifying the original list for fallback
                        messages_b = list(messages)
                        if system_message:
                             messages_b[0] = SystemMessage(content=system_message + json_instructions)
                        else:
                             messages_b.insert(0, SystemMessage(content=json_instructions))

                        response_raw = llm_json.invoke(messages_b)
                        response_content = response_raw.content

                        # Use parser robusto here too, just in case
                        parsed_json = extract_json_from_text(response_content)
                        if not parsed_json:
                             # If parser failed but we didn't crash, we might want to throw to trigger Plan C
                             # but wait, Plan C is for when JSON Mode is NOT supported or fails.
                             # If we are here, it means we got a response but it wasn't valid JSON or parser failed.
                             # Let's assume if it fails here we might as well go to Plan C which is "Manual Parse" with explicit text prompt
                             # Actually Plan C is more about removing "response_format" and just using text.
                             raise ValueError("Invalid JSON from JSON mode")

                        response = schema.model_validate(parsed_json)
                        response_data = response.model_dump_json()

                    except Exception as e2:
                        logger.warning(f"JSON mode not supported or failed: {e2}. Trying with manual parsing.")

                        # --- PLANO C: PARSING MANUAL ---
                        try:
                            # Remove any JSON mode parameter that might cause 400 error
                            llm_text = self._create_llm_instance(json_mode=False)

                            schema_json = schema.model_json_schema()
                            final_instructions = f"\n\nIMPORTANT: Your response MUST be a valid JSON object that conforms to the provided schema, and nothing else. Do not wrap it in markdown.\nSchema:\n{json.dumps(schema_json, indent=2)}"

                            messages_c = list(messages)
                            # Update or insert system message
                            if system_message:
                                 messages_c[0] = SystemMessage(content=system_message + final_instructions)
                            else:
                                 messages_c.insert(0, SystemMessage(content=final_instructions))

                            response = llm_text.invoke(messages_c)

                            # Use robust parser
                            parsed_json = extract_json_from_text(response.content)

                            if not parsed_json:
                                raise ValueError("Could not extract valid JSON from LLM text response.")

                            validated_response = schema.model_validate(parsed_json)
                            response_data = validated_response.model_dump_json()

                        except Exception as e3:
                            logger.error(f"All attempts to obtain structured response failed: {e3}")
                            # Fallback to returning raw parsed json if schema validation failed but we got JSON
                            if 'parsed_json' in locals() and parsed_json:
                                 logger.error("Returning raw JSON that failed schema validation.")
                                 response_data = json.dumps(parsed_json)
                            else:
                                 response_data = "{}" # Ultimate failure

            else:
                # Normal text mode
                response = llm.invoke(messages)
                response_data = response.content

        except Exception as e:
            logger.error(f"❌ LLM Error: {e}")
            response_data = "{}" if json_mode else f"Error: {str(e)}"
        
        finally:
            self._apply_delay()
            return response_data
