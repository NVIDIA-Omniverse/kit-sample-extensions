"""Public integration API for material-graph context menus."""

from .context_menu import (
    add_background_menu_item,
    add_node_menu_item,
    remove_background_menu_item,
    remove_node_menu_item,
)

__all__ = [
    "add_background_menu_item",
    "add_node_menu_item",
    "remove_background_menu_item",
    "remove_node_menu_item",
]
