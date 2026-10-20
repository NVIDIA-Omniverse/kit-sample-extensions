"""Implement material graph extension logic for `plugins/core/manager.py`."""

import logging
from typing import Any, Dict, Iterable, List, Optional, Type

from ...config.logging import log_exception, logger
from ..impl.materialx.plugin import MaterialXPlugin
from ..impl.mdl.plugin import MdlPlugin
from ..impl.usd.plugin import UsdPlugin
from .base import Plugin

# pylint: disable=protected-access

_BUILTIN_PLUGIN_CLASSES: tuple[Type[Plugin], ...] = (MdlPlugin, MaterialXPlugin, UsdPlugin)


class PluginManager:
    """Load and manage built-in material graph plugins."""

    def __init__(self, auto_discover: bool = True) -> None:
        """Initialize instance state for this material graph component."""

        self._plugins: Dict[str, Plugin] = {}
        self._destroyed = False
        if auto_discover:
            self.discover_plugins()

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        if self._destroyed:
            return
        self._destroyed = True
        for name in list(self._plugins.keys()):
            self.remove_plugin(name)
        self._plugins.clear()
        logger.info("plugin manager destroyed")

    def remove_plugin(self, name: str) -> None:
        """Destroy and remove a plugin registration by name."""
        plugin = self._plugins.get(name)
        if not plugin:
            return
        try:
            plugin.destroy()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("failed to destroy plugin '%s': %s", plugin.name, exc)
        self._plugins.pop(name, None)

    def add_plugin(self, plugin_class: Type[Plugin]) -> None:
        """Execute add plugin behavior for material graph workflows."""

        if self._destroyed:
            return
        try:
            plugin = plugin_class(load_catalog=True)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            plugin_name = getattr(plugin_class, "__name__", None) or str(plugin_class)
            log_exception(
                logger,
                "failed to initialize plugin",
                level=logging.WARNING,
                plugin_name=plugin_name,
                exc=exc,
            )
            return
        if not plugin.name:
            logger.warning("skipping plugin with empty name: %s", plugin_class)
            plugin.destroy()
            return
        if not plugin.display_name:
            logger.warning("skipping plugin with empty display name: %s", plugin_class)
            plugin.destroy()
            return
        existing = self._plugins.get(plugin.name)
        if existing:
            try:
                existing.destroy()
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.warning("failed to destroy plugin '%s': %s", plugin.name, exc)
        self._plugins[plugin.name] = plugin
        logger.info("plugin registered: %s", plugin.name)

    @classmethod
    def get_plugin_definitions(cls) -> List[Dict[str, Any]]:
        """Execute get plugin definitions behavior for material graph workflows."""

        definitions = []
        for plugin_class in _BUILTIN_PLUGIN_CLASSES:
            try:
                plugin = plugin_class(load_catalog=False)
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.warning("failed to inspect plugin %s: %s", plugin_class, exc)
                continue
            plugin_name = plugin.name
            display_name = plugin.display_name
            properties = [
                {
                    "key": prop.key,
                    "label": prop.label,
                    "type": prop.type,
                    "default": prop.default,
                    "description": prop.description,
                    "allowed_values": prop.allowed_values,
                }
                for prop in plugin.properties
            ]
            plugin.destroy()
            definitions.append(
                {
                    "name": plugin_name,
                    "display_name": display_name,
                    "properties": properties,
                }
            )
        return definitions

    def discover_plugins(self) -> None:
        """Execute discover plugins behavior for material graph workflows."""

        if self._destroyed:
            return
        for plugin_class in _BUILTIN_PLUGIN_CLASSES:
            self.add_plugin(plugin_class)
        logger.info(
            "plugin discovery complete: built_in=%s",
            len(_BUILTIN_PLUGIN_CLASSES),
        )

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Execute get plugin behavior for material graph workflows."""

        if self._destroyed:
            return None
        return self._plugins.get(name)

    def get_all_plugins(self) -> Iterable[Plugin]:
        """Execute get all plugins behavior for material graph workflows."""

        if self._destroyed:
            return []
        return self._plugins.values()
