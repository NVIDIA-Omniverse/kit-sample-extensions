"""Plugin framework and built-in plugin implementations.

This package provides the plugin base classes (Plugin, PluginPropertiesBase,
PluginProperty, PluginManager) and built-in implementations for USD,
MDL, and MaterialX. Plugins supply shader catalogs, connection rules,
and prim support to the material graph.

Architectural role: Plugins are the extension point for shader/connection
semantics. The catalog and graph models depend on plugins for node
definitions and creation logic.

Typical consumers: CatalogTreeModel, node-creation flows, connection
validation, and plugin configuration.
"""

from .core import Plugin, PluginManager, PluginPropertiesBase, PluginProperty
from .impl.materialx.plugin import MaterialXPlugin
from .impl.materialx.properties import MaterialXProperties
from .impl.mdl.plugin import MdlPlugin
from .impl.mdl.properties import MdlProperties
from .impl.usd.plugin import UsdPlugin
from .impl.usd.properties import UsdProperties

__all__ = [
    "MaterialXPlugin",
    "MaterialXProperties",
    "MdlPlugin",
    "MdlProperties",
    "Plugin",
    "PluginManager",
    "PluginPropertiesBase",
    "PluginProperty",
    "UsdPlugin",
    "UsdProperties",
]
