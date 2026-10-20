from lc_agent import get_chat_model_registry


class AgentRegistryHelper:
    """Helper Method relate to the agent registry."""

    @staticmethod
    def is_valid_model_name(model_name: str):
        """Check whether the target model name exist within the list."""
        model_registry = get_chat_model_registry()
        # get available model names
        model_names = model_registry.get_registered_names()
        if model_name in model_names:
            return True

        return False