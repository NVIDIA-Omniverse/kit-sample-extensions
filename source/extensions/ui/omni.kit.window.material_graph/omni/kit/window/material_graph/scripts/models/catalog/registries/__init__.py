"""Catalog registries package for texture and compound discovery.

This package aggregates registry subpackages (texture, compound) that provide
discoverable assets for the catalog. Registries resolve paths from settings
and file system and expose them to the catalog tree model.

Architectural role: Registries are leaf services; they are consumed by the
catalog tree model and drop handlers for populating creatable content.

Typical consumers: CatalogTreeModel, texture/compound catalog population,
CatalogCreationHandler, TextureDropHandler.
"""

from .compound import destroy_compound_registry
from .texture import destroy_texture_registry


def destroy_catalog_registries() -> None:
    """Destroy process-global catalog registries during extension shutdown."""
    try:
        destroy_compound_registry()
    finally:
        destroy_texture_registry()


__all__ = ["destroy_catalog_registries"]
