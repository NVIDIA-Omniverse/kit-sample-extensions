"""Core catalog model types and base item definitions.

This package provides the base item class (BaseItem) and catalog item data
container (CatalogItemData) used by all concrete catalog item types. These
types define the common interface for catalog tree items.

Architectural role: Core catalog types are foundational; all catalog items
inherit from BaseItem and use CatalogItemData for shared attributes.

Typical consumers: Catalog item subclasses (ShaderItem, CompoundItem, etc.)
and the catalog tree model.
"""

from .base import BaseItem
from .data import CatalogItemData

__all__ = ["BaseItem", "CatalogItemData"]
