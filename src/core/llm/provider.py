import time
import json
import urllib.request
import urllib.error
from typing import Optional, List, Type, Any, Union
from pydantic import BaseModel
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from src.core.logger import logger
from src.core.config import settings
from src.core.utils.json_parser import extract_json_from_text
from src.core.llm.api_key_manager import key_manager

class LocalOpenAIClient:
    """
    Custom client to interact with OpenAI-compatible APIs (like LM Studio)
    using standard library, avoiding 'openai' package dependency.
    """
    def __init__(self, model_name: str, base_url: str, json_mode: bool = False, temperature: float = 0.5):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        if not self.base_url.endswith("/v1"):
            self.base_url += "/v1"
        self.json_mode = json_mode
        self.temperature = temperature

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
            "temperature": self.temperature,
            "stream": False
        }

        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY or ''}"
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
    def __init__(self, model_name: str, base_url: str = None, provider: str = None, temperature: float = 0.5):
        self.model_name = model_name
        self.temperature = temperature
        self.ollama_base_url = base_url or settings.OLLAMA_BASE_URL

        # Determine provider
        if provider:
            self.provider = provider
        elif base_url:
            # If base_url is explicitly provided, infer local
            self.provider = "local"
        else:
            self.provider = settings.LLM_PROVIDER

        # Normalize provider name
        if self.provider in ["ollama", "local"]:
            self.provider = "local"
            if not self.ollama_base_url:
                 # Should we default? logger warning already in place
                 pass

        # Initialize the default LLM instance (Legacy Mode support)
        # Note: self.llm will hold the initial instance.
        # For Google, this might hold the first key. Rotation happens in get_llm().
        self.llm = self._create_llm_instance(self.model_name, self.temperature, self.ollama_base_url)

    def _create_llm_instance(self, model_name: str, temperature: float, base_url: str, json_mode: bool = False) -> Any:
        """
        Creates an LLM instance.
        Accepts explicit arguments to allow creating temporary instances (e.g. for JSON mode)
        different from the default self.llm.
        """
        if self.provider == "local":
            logger.info(f"Using Local LLM (OpenAI Compatible) with model: {model_name} at {base_url}")
            return LocalOpenAIClient(
                model_name=model_name,
                base_url=base_url,
                json_mode=json_mode,
                temperature=temperature
            )

        elif self.provider == "ollama_native": # Legacy support
             return ChatOllama(
                model=model_name,
                base_url=base_url,
                format="json" if json_mode else None,
                temperature=temperature
            )

        # Google
        logger.info(f"Using Google LLM with model: {model_name}")
        current_key = key_manager.get_next_key()

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=current_key,
            temperature=temperature,
            convert_system_message_to_human=True
        )

    def get_llm(self) -> BaseLanguageModel:
        """
        Returns a fresh LLM instance.
        Crucial for Google provider to ensure API key rotation on every call.
        """
        return self._create_llm_instance(self.model_name, self.temperature, self.ollama_base_url)

    def _apply_delay(self):
        try:
            delay = settings.REQUEST_DELAY_SECONDS
            if delay > 0:
                time.sleep(delay)
        except (ValueError, TypeError):
            pass

    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None
    ) -> Union[str, BaseModel]:
        """
        Generates a response from the LLM.
        - If 'schema' is provided, attempts to generate a structured Pydantic object (Structured Mode).
        - If 'schema' is None, returns a string (Legacy Mode).
        """

        # Get a fresh LLM instance (rotates keys for Google)
        llm = self.get_llm()

        # Prepare messages
        messages = [HumanMessage(content=prompt)]
        if system_message:
            messages.insert(0, SystemMessage(content=system_message))

        try:
            # --- LEGACY MODE (No Schema) ---
            if not schema:
                response = llm.invoke(messages)
                return response.content if hasattr(response, 'content') else str(response)

            # --- STRUCTURED MODE ---

            # PLAN A: Google / Native Structured Output
            if self.provider == "google":
                try:
                    # Google uses the instance with .with_structured_output()
                    structured_llm = llm.with_structured_output(schema)
                    response_obj = structured_llm.invoke(messages)

                    if isinstance(response_obj, schema):
                         return response_obj

                    # If it returned a dict, validate it
                    if isinstance(response_obj, dict):
                        return schema.model_validate(response_obj)

                    if response_obj is None:
                         raise ValueError("Native structured output returned None.")

                except Exception as e:
                    logger.warning(f"Plan A (Native Google) failed: {e}. Falling back to manual.")
                    # Fallback to Plan B logic (Manual JSON injection)

            # PLAN B: Local (or Fallback) - JSON Mode + Schema Injection
            # We create a temporary instance with json_mode=True

            schema_json = schema.model_json_schema()
            json_instructions = f"\n\nRespond strictly with a valid JSON object matching this schema:\n{json.dumps(schema_json, indent=2)}"

            # Inject instructions
            messages_b = list(messages)
            if system_message:
                 messages_b[0] = SystemMessage(content=system_message + json_instructions)
            else:
                 messages_b.insert(0, SystemMessage(content=json_instructions))

            try:
                # Create a specific instance for this call, forcing JSON mode
                llm_json = self._create_llm_instance(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    base_url=self.ollama_base_url,
                    json_mode=True
                )

                response_raw = llm_json.invoke(messages_b)
                response_content = response_raw.content if hasattr(response_raw, 'content') else str(response_raw)

                parsed_json = extract_json_from_text(response_content)
                if not parsed_json:
                    raise ValueError("Could not extract valid JSON from response.")

                return schema.model_validate(parsed_json)

            except Exception as e2:
                 logger.warning(f"Plan B (JSON Mode) failed: {e2}. Falling back to Plan C (Manual Text).")

            # PLAN C: Manual Text Parsing (Last Resort)
            try:
                # Use a text-mode instance (explicitly create one to be safe)
                llm_text = self._create_llm_instance(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    base_url=self.ollama_base_url,
                    json_mode=False
                )

                final_instructions = f"\n\nIMPORTANT: Your response MUST be a valid JSON object that conforms to the provided schema. Do not wrap it in markdown.\nSchema:\n{json.dumps(schema_json, indent=2)}"

                messages_c = list(messages)
                if system_message:
                     messages_c[0] = SystemMessage(content=system_message + final_instructions)
                else:
                     messages_c.insert(0, SystemMessage(content=final_instructions))

                response = llm_text.invoke(messages_c)
                response_content = response.content if hasattr(response, 'content') else str(response)

                parsed_json = extract_json_from_text(response_content)
                if not parsed_json:
                    raise ValueError("Plan C: Could not extract valid JSON from LLM text response.")

                return schema.model_validate(parsed_json)

            except Exception as e3:
                logger.error(f"All attempts to obtain structured response failed: {e3}")
                raise ValueError(f"Failed to generate structured response: {e3}")

        except Exception as e:
            logger.error(f"❌ LLM Error in generate_response: {e}")
            raise
        
        finally:
            self._apply_delay()
