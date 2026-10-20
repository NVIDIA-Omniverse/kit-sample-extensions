"""Catalog section components for the shader/compound browser.

This package provides the catalog tree widget (MaterialGraphCatalog) and
its delegate (MaterialGraphCatalogDelegate) used to browse and filter
shaders, compounds, and textures. The catalog section is composed into
the main graph window layout.

Architectural role: Catalog section components sit between the catalog
tree model and the graph widget. The delegate customizes item rendering
and drag behavior for material-graph-specific catalog entries.

Typical consumers: GraphWindow layout, catalog controller setup, and
tests that verify catalog browsing and drag behavior.
"""

from .delegate import MaterialGraphCatalogDelegate
from .quicksearch_delegate import MaterialGraphQuickSearchDelegate
from .widget import MaterialGraphCatalog

__all__ = [
    "MaterialGraphCatalog",
    "MaterialGraphCatalogDelegate",
    "MaterialGraphQuickSearchDelegate",
]
