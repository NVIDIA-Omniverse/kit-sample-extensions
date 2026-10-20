"""Type definitions for the model registry system."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class ModelConfig(BaseModel):
    """Base class for model configurations."""

    name: str
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = None

# https://python.langchain.com/api_reference/nvidia_ai_endpoints/chat_models/langchain_nvidia_ai_endpoints.chat_models.ChatNVIDIA.html
class NVIDIAConfig(ModelConfig):
    """NVIDIA model configuration."""

    api_key: SecretStr | None = None
    model: str
    base_url: str | None = "https://integrate.api.nvidia.com/v1"
    max_tokens: int | None = 1024

# https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
class OpenAIConfig(ModelConfig):
    """OpenAI model configuration."""

    api_key: SecretStr | None = None
    model: str
    base_url: str | None = None


# https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html
class AnthropicConfig(ModelConfig):
    """Anthropic model configuration."""

    api_key: SecretStr | None = None
    model: str

# https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.azure.AzureChatOpenAI.html
class AzureOpenAIConfig(ModelConfig):
    """Azure OpenAI model configuration."""

    api_key: SecretStr | None = None
    azure_deployment: str | None = None
    azure_endpoint: str | None = None
    api_version: str | None = None

class ServiceSetting(BaseModel):
    """Setting of a service type with its models, config, and LangChain class."""

    models: dict[str, Any]
    config_class: type[ModelConfig]
    langchain_class: Callable