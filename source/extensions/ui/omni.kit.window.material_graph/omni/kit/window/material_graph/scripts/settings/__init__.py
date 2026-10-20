"""Runtime settings APIs for material graph.

This package provides Settings (carb.settings-backed helpers) and Catalog
(catalog-specific settings) used to read and write persistent configuration.
Settings are used for graph options, export paths, and plugin configuration.

Architectural role: Settings is a leaf dependency; it wraps carb.settings
and is consumed by controllers, preferences, and command layers.

Typical consumers: GraphSettingsController, preferences sections, export
resolution, plugin property access.
"""

from .catalog import Catalog
from .settings import Settings

__all__ = ["Catalog", "Settings"]
