"""Implement material graph extension logic for `context_manager/context_plugin_access.py`."""

from typing import List, Optional

from ..plugins.core import Plugin as PluginBase
from ..plugins.core import PluginManager


class ContextPluginAccess:
    """Isolate plugin lookup behavior for contexts."""

    def __init__(self, plugin_manager: PluginManager) -> None:
        """Initialize instance state for this material graph component."""

        self._plugin_manager = plugin_manager

    def get_plugins(self) -> List[PluginBase]:
        """Return all registered plugins."""
        return list(self._plugin_manager.get_all_plugins())

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Return a plugin by name when available."""
        return self._plugin_manager.get_plugin(name)
