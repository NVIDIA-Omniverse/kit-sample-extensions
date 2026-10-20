"""Compound registry for discoverable compound/nodegraph assets.

This package provides the CompoundRegistry, CompoundSource, and
get_compound_registry accessor used to enumerate stored compound
nodegraphs for the catalog. The registry resolves compound paths
from settings and file system.

Architectural role: Compound registry is a leaf service; it is consumed
by the catalog tree model and compound drop handlers.

Typical consumers: CatalogTreeModel, CatalogCreationHandler, compound
catalog population.
"""

from .registry import CompoundRegistry, destroy_compound_registry, get_compound_registry
from .source import CompoundSource

__all__ = [
    "CompoundRegistry",
    "CompoundSource",
    "get_compound_registry",
    "destroy_compound_registry",
]
