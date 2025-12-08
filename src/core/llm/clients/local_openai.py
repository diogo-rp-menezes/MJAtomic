import json
import urllib.request
import urllib.error
from typing import List, Any
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from src.core.logger import logger
from src.core.config import settings

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

    def invoke(self, messages: List[BaseMessage], **kwargs) -> Any:
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

        # Check for response_format in kwargs (native structured output)
        if 'response_format' in kwargs:
             payload['response_format'] = kwargs['response_format']
        # Legacy JSON mode
        elif self.json_mode:
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
