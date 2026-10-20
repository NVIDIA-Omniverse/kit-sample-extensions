"""Catalog-related controllers for visibility and context menus.

This package provides controllers that manage catalog tree visibility
(CatalogController) and context-menu presentation for catalog items
(CatalogContextMenuController). These controllers bind catalog model
state to UI behavior.

Architectural role: Catalog controllers sit between the catalog widget
and the catalog tree model. They handle settings-driven visibility
and selection-driven context menus.

Typical consumers: GraphWidget composition, catalog section setup, and
tests that verify catalog visibility and menu behavior.
"""

from .context_menu import CatalogContextMenuController
from .visibility import CatalogController

__all__ = [
    "CatalogContextMenuController",
    "CatalogController",
]
