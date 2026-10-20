"""Texture registry for discoverable texture assets.

This package provides the TextureRegistry and get_texture_registry accessor
used to enumerate and resolve texture files for the catalog. The registry
integrates with the file system and optional texture-info plugins.

Architectural role: Texture registry is a leaf service; it is consumed by
the catalog tree model and texture drop handlers.

Typical consumers: CatalogTreeModel, TextureDropHandler, texture catalog
population.
"""

from .registry import TextureRegistry, destroy_texture_registry, get_texture_registry

__all__ = [
    "TextureRegistry",
    "get_texture_registry",
    "destroy_texture_registry",
]
