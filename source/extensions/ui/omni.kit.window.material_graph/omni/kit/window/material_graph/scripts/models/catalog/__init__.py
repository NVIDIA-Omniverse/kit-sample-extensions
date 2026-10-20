"""Catalog-model package for discoverable node/content sources.

Catalog models represent creatable assets that are not the current stage graph
state itself: shader definitions from plugins, user texture entries, and stored
compound nodegraphs, grouped and filtered for UI browsing.

This separation from stage-backed graph models is intentional: catalog entries
describe "what can be created", while graph models describe "what already exists
on the USD stage".

Typical consumers: catalog tree/widget/delegate code and node-creation flows that
instantiate stage content from discoverable catalog entries.
"""

from .items import CompoundItem, GroupItem, ShaderItem, TextureItem
from .quicksearch.model import MaterialGraphQuickSearchModel
from .tree import CatalogTreeModel

__all__ = [
    "CatalogTreeModel",
    "CompoundItem",
    "GroupItem",
    "MaterialGraphQuickSearchModel",
    "ShaderItem",
    "TextureItem",
]
