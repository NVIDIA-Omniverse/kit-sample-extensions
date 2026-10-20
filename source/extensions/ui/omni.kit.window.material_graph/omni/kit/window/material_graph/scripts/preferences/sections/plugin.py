"""Implement material graph extension logic for `preferences/sections/plugin.py`."""

from typing import Any, Dict, List, Optional

from ...plugins.core import PluginManager
from ..plugin.factory import PluginPropertyWidgetFactory

# pylint: disable=no-member


class PluginSettingsSection:
    """Builds the Plugin Settings preferences section."""

    def __init__(self, builder) -> None:
        """Initialize instance state for this material graph component."""

        self._builder = builder
        self._plugin_definitions: Optional[List[Dict[str, Any]]] = None
        self._property_factory = PluginPropertyWidgetFactory(builder)

    def build(self) -> None:
        """Execute build behavior for material graph workflows."""

        with self._builder.add_frame("Plugin Settings"):
            with self._builder.indented_stack():
                with self._builder.add_frame("Plugins"):
                    with self._builder.indented_stack():
                        if self._plugin_definitions is None:
                            self._plugin_definitions = PluginManager.get_plugin_definitions()
                        self._property_factory.build(self._plugin_definitions)

    @property
    def property_factory(self):
        """Execute property factory behavior for material graph workflows."""

        return self._property_factory
