"""Core plugin framework APIs."""

from .base import Plugin
from .manager import PluginManager
from .polymorphic_state import PolymorphicState
from .properties_base import PluginPropertiesBase
from .property import PluginProperty

__all__ = ["Plugin", "PluginProperty", "PluginPropertiesBase", "PluginManager", "PolymorphicState"]
