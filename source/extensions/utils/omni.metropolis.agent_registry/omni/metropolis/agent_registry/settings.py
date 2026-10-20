
from omni.metropolis.utils.carb_util import CarbSettingMeta, CarbSettingProperty, get_value_by_key

EXTENSION_NAME = "omni.metropolis.agent_registry"


class ModelRegistrySetting(metaclass=CarbSettingMeta):
    """setting values related to model registry."""

    # API Keys for different services
    NVIDIA_API_KEY = CarbSettingProperty(default_value="", is_persistent=True)
    OPENAI_API_KEY = CarbSettingProperty(default_value="", is_persistent=True)
    ANTHROPIC_API_KEY = CarbSettingProperty(default_value="", is_persistent=True)
    AZURE_OPENAI_API_KEY = CarbSettingProperty(default_value="", is_persistent=True)

    SERVICE_API_KEY_MAPPING = {
        "nvidia": "NVIDIA_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "azure_openai": "AZURE_OPENAI_API_KEY",
    }

    @staticmethod
    def get_extension_name() -> str:
        """Get the agent driven sdg config generation extension name."""
        return EXTENSION_NAME

    @staticmethod
    def get_setting_path(setting_name: str) -> str:
        """Get the setting path for a given setting name."""
        return f"{EXTENSION_NAME}/{setting_name}"

    @staticmethod
    def get_supported_services() -> list[str]:
        """Get list of all services that have API key support and require API keys."""
        return list(ModelRegistrySetting.SERVICE_API_KEY_MAPPING.keys())

    @staticmethod
    def is_service_supported(service: str) -> bool:
        """Check if a service requires and has API key support."""
        return service in ModelRegistrySetting.SERVICE_API_KEY_MAPPING

    @staticmethod
    def get_api_key_for_service(service: str) -> str:
        """Get the API key for a specific service from carb settings."""
        result = ""
        if service in ModelRegistrySetting.SERVICE_API_KEY_MAPPING:
            setting_name = ModelRegistrySetting.SERVICE_API_KEY_MAPPING[service]
            setting_path = ModelRegistrySetting.get_setting_path(setting_name)
            return get_value_by_key(setting_path, "")
        return result

    @staticmethod
    def get_api_key_setting_name_for_service(service: str) -> str:
        """Get the carb setting name for a specific service's API key."""
        return ModelRegistrySetting.SERVICE_API_KEY_MAPPING.get(service, "")

    @staticmethod
    def get_all_api_key_settings() -> dict[str, str]:
        """Get all service -> setting_name mappings for UI building."""
        return ModelRegistrySetting.SERVICE_API_KEY_MAPPING.copy()
