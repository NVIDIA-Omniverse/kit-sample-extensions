"""Model Factory for creating and managing LangChain model instances."""

import logging
from typing import Any

from .models import ANTHROPIC_MODELS, AZURE_MODELS, LLAMA_MODELS, NEMOTRON_MODELS, OPENAI_MODELS, SUPPORTED_SERVICES
from .types import AnthropicConfig, AzureOpenAIConfig, ModelConfig, NVIDIAConfig, OpenAIConfig, ServiceSetting

logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory for creating and managing LangChain model instances."""

    def __init__(self):
        self._langchain_classes = {}  # Lazy-loaded cache: service -> langchain class
        self._service_settings = self._initialize_service_settings() # Service -> {models, model_config, langchain_class}

    def _initialize_service_settings(self) -> dict[str, ServiceSetting]:
        """Initialize service settings."""
        settings = {}

        # NVIDIA
        settings["nvidia"] = ServiceSetting(
            models={**LLAMA_MODELS, **NEMOTRON_MODELS},
            config_class=NVIDIAConfig,
            langchain_class=lambda: __import__('langchain_nvidia_ai_endpoints').ChatNVIDIA
        )

        # OpenAI
        settings["openai"] = ServiceSetting(
            models=OPENAI_MODELS,
            config_class=OpenAIConfig,
            langchain_class=lambda: __import__('langchain_openai').ChatOpenAI
        )

        # Anthropic
        settings["anthropic"] = ServiceSetting(
            models=ANTHROPIC_MODELS,
            config_class=AnthropicConfig,
            langchain_class=lambda: __import__('langchain_anthropic').ChatAnthropic
        )

        # Azure OpenAI
        settings["azure_openai"] = ServiceSetting(
            models=AZURE_MODELS,
            config_class=AzureOpenAIConfig,
            langchain_class=lambda: __import__('langchain_openai').AzureChatOpenAI
        )

        return settings

    def _load_langchain_class(self, service: str) -> type:
        """Load LangChain class for a specific service."""
        if service in self._langchain_classes:
            return self._langchain_classes[service]

        service_setting = self._service_settings.get(service)
        if not service_setting:
            raise ValueError(f"Unsupported service: {service}")

        try:
            langchain_class = service_setting.langchain_class()
            self._langchain_classes[service] = langchain_class
            return langchain_class
        except ImportError as e:
            raise ImportError(f"LangChain class not available for {service}: {e}")


    def _create_model_instance(self, model_config: ModelConfig, service: str) -> Any:
        """Create the actual LangChain model instance."""
        # Load the appropriate LangChain class
        langchain_class = self._load_langchain_class(service)

        # Convert config to LangChain format
        config_dict = model_config.model_dump()

        # Create the model instance
        return langchain_class(**config_dict)

    def create_model(self, service: str, name: str, **config_values) -> Any:
        """Create a model instance for both supported and unsupported services."""
        if service in SUPPORTED_SERVICES:
            service_setting = self._service_settings.get(service)
            # Get defaults and create service config
            defaults = self.get_field_defaults(service, name)
            config_dict = {**defaults, **config_values}
            config_dict['name'] = name  # Set application name

            # Create service-specific config with Pydantic validation
            model_config = service_setting.config_class(**config_dict)

            # Create the model instance
            return self._create_model_instance(model_config, service)
        else:
            # Use init_chat_model for custom services
            return self._create_custom_model_instance(service, **config_values)

    def _create_custom_model_instance(self, service: str, **config_values) -> Any:
        """Create model instance for custom service using init_chat_model."""
        try:
            from langchain.chat_models import init_chat_model

            if 'model' not in config_values:
                raise ValueError("'model' field is required. ")

            # Use init_chat_model for custom services
            return init_chat_model(
                model_provider=service,
                **config_values
            )
        except ImportError:
            raise ImportError("langchain package is required for custom services")

    def get_all_services(self) -> list[str]:
        """Get all available known service types as strings."""
        return list(self._service_settings.keys())

    def get_available_models(self, service: str) -> list[str]:
        """Get available models for a specific service type (only works for known services)."""
        if service not in SUPPORTED_SERVICES:
            raise ValueError(f"Cannot list models for custom service '{service}'. Use config file registration.")

        service_setting = self._service_settings.get(service)
        if not service_setting:
            raise ValueError(f"Unknown service: {service}")

        return list(service_setting.models.keys())

    def get_field_defaults(self, service: str, name: str) -> dict[str, Any]:
        """Get default configuration: model defaults first, then service defaults."""
        service_setting = self._service_settings.get(service)
        if not service_setting:
            return {}

        defaults = {}

        # Get model-specific defaults first
        if name in service_setting.models:
            model_config = service_setting.models[name]
            # Handle both tuple and dict structures
            if isinstance(model_config, tuple):
                config, _max_tokens, _hidden = model_config
                defaults.update(config)
            else:
                # Handle dict structure
                defaults.update(model_config)

        # Add service defaults from Pydantic config class
        from pydantic_core import PydanticUndefined
        for field_name, field_info in service_setting.config_class.model_fields.items():
            if field_name not in defaults and hasattr(field_info, 'default'):
                if field_info.default is not PydanticUndefined and field_info.default is not None:
                    defaults[field_name] = field_info.default

        return defaults

    def get_config_fields(self, service: str) -> dict[str, Any]:
        """Get configuration fields for a service (only works for known services)."""
        if service not in SUPPORTED_SERVICES:
            raise ValueError(f"Cannot get config fields for custom service '{service}'. Use config file registration.")

        service_setting = self._service_settings.get(service)
        if not service_setting:
            raise ValueError(f"Unknown service: {service}")

        return service_setting.config_class.model_fields
