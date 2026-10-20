"""Catalog item exports for shader, compound, texture, and group entries.

This package provides the concrete catalog item types (ShaderItem, CompoundItem,
TextureItem, GroupItem, etc.) and base types (BaseItem, CatalogItemData,
DroppableItem) used by the catalog tree model. Items represent creatable
assets that can be dragged onto the graph.

Architectural role: Catalog items are leaf model types; they implement
the item interface expected by the catalog tree and delegate. They depend
on plugin/shader/compound registries for data.

Typical consumers: CatalogTreeModel, MaterialGraphCatalogDelegate,
node-creation flows, and drop handlers.
"""

from ..core import BaseItem, CatalogItemData
from .compound import CompoundItem
from .droppable import DroppableItem
from .group import GroupItem
from .misc import MiscellaneousItem
from .shader import ShaderItem
from .texture import TextureItem

__all__ = [
    "BaseItem",
    "CatalogItemData",
    "CompoundItem",
    "DroppableItem",
    "GroupItem",
    "MiscellaneousItem",
    "ShaderItem",
    "TextureItem",
]
