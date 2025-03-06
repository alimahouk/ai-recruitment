from dataclasses import dataclass

from backend.app.config import AzureOpenAIDeployment, Configuration


@dataclass
class VisionConfig:
    """Azure Vision API configuration."""

    endpoint: str
    key: str

    @classmethod
    def from_env(cls) -> "VisionConfig":
        """Create configuration from environment variables."""
        endpoint = Configuration.AZURE_AI_SERVICES_EASTUS_ENDPOINT
        key = Configuration.AZURE_AI_SERVICES_EASTUS_API_KEY

        if not endpoint or not key:
            raise ValueError(
                "Azure Vision credentials not found in environment variables"
            )

        return cls(endpoint=endpoint, key=key)


@dataclass
class OpenAI4oConfig:
    """Azure OpenAI GPT-4o configuration."""

    api_key: str
    api_version: str
    endpoint: str
    model: str = AzureOpenAIDeployment.GPT_4O

    @classmethod
    def from_env(cls) -> "OpenAI4oConfig":
        """Create a GPT-4o configuration from environment variables."""
        api_key = Configuration.AZURE_AI_SERVICES_EASTUS_API_KEY
        api_version = Configuration.AZURE_OPENAI_GPT_4O_API_VERSION
        endpoint = Configuration.AZURE_AI_SERVICES_EASTUS_ENDPOINT

        if not all([api_key, api_version, endpoint]):
            raise ValueError(
                "Azure OpenAI credentials not found in environment variables"
            )

        return cls(api_key=api_key, api_version=api_version, endpoint=endpoint)


@dataclass
class OpenAIEmbeddingsConfig:
    """Azure OpenAI embeddings configuration."""

    api_key: str
    api_version: str
    endpoint: str
    model: str = AzureOpenAIDeployment.TEXT_EMBEDDINGS_3_LARGE

    @classmethod
    def from_env(cls) -> "OpenAIEmbeddingsConfig":
        """Create an embeddings configuration from environment variables."""
        api_key = Configuration.AZURE_AI_SERVICES_EASTUS_API_KEY
        api_version = (
            Configuration.AZURE_OPENAI_TEXT_EMBEDDINGS_3_LARGE_API_VERSION
        )
        endpoint = Configuration.AZURE_AI_SERVICES_EASTUS_ENDPOINT

        if not all([api_key, api_version, endpoint]):
            raise ValueError(
                "Azure OpenAI credentials not found in environment variables"
            )

        return cls(api_key=api_key, api_version=api_version, endpoint=endpoint)
