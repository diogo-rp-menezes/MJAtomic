import time
import json
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
from src.core.llm.clients.local_openai import LocalOpenAIClient

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

        # Prepare messages
        messages = [HumanMessage(content=prompt)]
        if system_message:
            messages.insert(0, SystemMessage(content=system_message))

        try:
            # --- LEGACY MODE (No Schema) ---
            if not schema:
                # Get a fresh LLM instance
                llm = self.get_llm()
                response = llm.invoke(messages)
                return response.content if hasattr(response, 'content') else str(response)

            # --- STRUCTURED MODE ---
            return self._generate_structured_response(messages, schema)

        except Exception as e:
            logger.error(f"❌ LLM Error in generate_response: {e}")
            raise

        finally:
            self._apply_delay()

    def _generate_structured_response(
        self,
        messages: List[BaseMessage],
        pydantic_schema: Type[BaseModel]
    ) -> BaseModel:
        """
        Implements fallback logic to obtain a structured JSON output.
        """
        llm = self.get_llm()

        # --- PLAN A: Native Structured Output (Gemini) ---
        if self.provider == "google":
            try:
                logger.info("Tentando com Saída Estruturada Nativa do Gemini...")
                structured_llm = llm.with_structured_output(pydantic_schema)
                response_obj = structured_llm.invoke(messages)

                if isinstance(response_obj, pydantic_schema):
                    return response_obj

                if isinstance(response_obj, dict):
                    return pydantic_schema.model_validate(response_obj)

                if response_obj is None:
                     raise ValueError("Native structured output returned None.")

            except Exception as e:
                logger.warning(f"Saída Estruturada Nativa do Gemini falhou: {e}. Usando fallback.")
                # Fallback to Plan C

        # --- PLAN B: Native Structured Output (LM Studio) ---
        elif self.provider == "local":
            try:
                logger.info("Tentando com Structured Output nativo do LM Studio...")

                # 1. Build payload for response_format
                schema_payload = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": pydantic_schema.__name__,
                        "strict": True,
                        "schema": pydantic_schema.model_json_schema()
                    }
                }

                # 2. Call invoke with response_format
                response_raw = llm.invoke(messages, response_format=schema_payload)
                response_str = response_raw.content if hasattr(response_raw, 'content') else str(response_raw)

                # 3. Validate returned JSON
                return pydantic_schema.model_validate_json(response_str)
            except Exception as e:
                logger.warning(f"Structured Output do LM Studio falhou: {e}. Usando fallback.")
                # Fallback to Plan C

        # --- PLAN C: Final Fallback (Manual Text Parsing) ---
        try:
            logger.info("Usando fallback final: parsing manual de texto...")

            schema_json = pydantic_schema.model_json_schema()
            final_instructions = f"\n\nIMPORTANT: Your response MUST be a valid JSON object that conforms to the provided schema. Do not wrap it in markdown.\nSchema:\n{json.dumps(schema_json, indent=2)}"

            messages_c = list(messages)

            if isinstance(messages_c[0], SystemMessage):
                 messages_c[0] = SystemMessage(content=str(messages_c[0].content) + final_instructions)
            else:
                 messages_c.insert(0, SystemMessage(content=final_instructions))

            # Use a text-mode instance (explicitly create one to be safe)
            llm_text = self._create_llm_instance(
                model_name=self.model_name,
                temperature=self.temperature,
                base_url=self.ollama_base_url,
                json_mode=False
            )

            response = llm_text.invoke(messages_c)
            content = response.content if hasattr(response, 'content') else str(response)

            parsed_json = extract_json_from_text(content)
            if not parsed_json:
                raise ValueError(f"Não foi possível extrair um JSON válido da resposta. Resposta: {content}")

            return pydantic_schema.model_validate(parsed_json)
        
        except Exception as e3:
            logger.error(f"Todas as tentativas de obter uma resposta estruturada falharam: {e3}")
            raise
