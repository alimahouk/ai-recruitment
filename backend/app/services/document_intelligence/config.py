from dataclasses import dataclass

from backend.app.config import Configuration


@dataclass
class AzureConfig:
    """Azure configuration settings."""

    endpoint: str
    key: str

    @classmethod
    def from_env(cls) -> "AzureConfig":
        """Create configuration from environment variables."""
        endpoint = Configuration.AZURE_AI_SERVICES_EASTUS_ENDPOINT
        key = Configuration.AZURE_AI_SERVICES_EASTUS_API_KEY

        if not endpoint or not key:
            raise ValueError(
                "Azure credentials not found in environment variables"
            )

        return cls(endpoint=endpoint, key=key)


@dataclass
class ProcessingConfig:
    """Document processing configuration."""

    min_confidence: float = 0.8
    include_tables: bool = True
    include_figures: bool = True
    clean_text: bool = True
    debug_output: bool = False

    def __post_init__(self):
        if not 0 <= self.min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
