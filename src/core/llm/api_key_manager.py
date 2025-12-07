import threading
import time
from typing import List, Optional
from src.core.config import settings
from src.core.logger import logger

class ApiKeyManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ApiKeyManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            # Get list directly from settings (already parsed by Pydantic)
            self.keys: List[str] = settings.GOOGLE_API_KEYS

            if not self.keys:
                logger.warning("No Google API keys found in settings (GOOGLE_API_KEYS).")

            # Rate Limiter Logic
            self.rpm = settings.GOOGLE_RPM
            self.delay_between_requests = 60.0 / self.rpm if self.rpm > 0 else 0
            self.last_request_time = 0

            self.current_index = 0
            self._initialized = True

    def get_next_key(self) -> Optional[str]:
        """
        Obtains the next key and ensures rate limiting.
        """
        if not self.keys:
            return None

        with self._lock:
            # --- Rate Limiter Logic ---
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay_between_requests:
                sleep_time = self.delay_between_requests - elapsed
                logger.debug(f"Rate limit: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)

            self.last_request_time = time.time()
            # -----------------------------

            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)

            return key

key_manager = ApiKeyManager()
