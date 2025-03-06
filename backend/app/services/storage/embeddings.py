import time
from threading import Lock
from typing import Optional

from openai import AzureOpenAI

from backend.app.services.vision.config import OpenAIEmbeddingsConfig


class EmbeddingsClient:
    """Handles embedding generation"""

    def __init__(
        self,
        openai_config: Optional[OpenAIEmbeddingsConfig] = None,
    ):
        self.openai_client = None
        self.openai_config = openai_config
        if openai_config:
            self.openai_client = AzureOpenAI(
                api_key=openai_config.api_key,
                api_version=openai_config.api_version,
                azure_endpoint=openai_config.endpoint,
            )

        # Add rate limiting
        self._api_rate_limit = 0.5  # seconds between calls
        self._last_api_call = 0
        self._lock = Lock()

    @classmethod
    def from_env(cls) -> "EmbeddingsClient":
        """Create a client using environment variables."""
        try:
            openai_config = OpenAIEmbeddingsConfig.from_env()
        except ValueError:
            openai_config = None
        return cls(openai_config)

    def generate_embeddings(self, text: str) -> list[float]:
        """
        Generate embeddings from string of text.
        This will be used to vectorise data and user input for interactions with Cosmos DB.
        """

        if not text:
            raise ValueError("No text provided to generate embeddings!")

        try:
            self._wait_for_rate_limit()  # Add rate limiting

            response = self.openai_client.embeddings.create(
                input=text, model=self.openai_config.model
            )
            return response.data[0].embedding
        except Exception as e:
            raise ValueError(f"Failed to generate embeddings: {str(e)}")

    def _wait_for_rate_limit(self):
        """Enforce rate limiting for API calls"""
        with self._lock:
            now = time.time()
            if now - self._last_api_call < self._api_rate_limit:
                time.sleep(self._api_rate_limit - (now - self._last_api_call))
            self._last_api_call = time.time()
