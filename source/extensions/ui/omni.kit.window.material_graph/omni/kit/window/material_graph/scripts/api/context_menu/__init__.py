"""Context menu registration API for the material graph."""

from typing import Iterable, List, Optional, Union

from .registry import ContextMenuRegistry
from .types import Callback, ContextMenuItem

_REGISTRY = ContextMenuRegistry()


def add_node_menu_item(
    label: str,
    callback: Callback,
    node_types: Optional[Union[str, Iterable[str]]] = None,
) -> bool:
    """Register a node-context menu callback in the global registry."""
    return _REGISTRY.add_node_menu_item(label, callback, node_types)


def remove_node_menu_item(
    label: str,
    callback: Optional[Callback] = None,
) -> None:
    """Remove node-context menu callbacks by label and optional callback."""
    _REGISTRY.remove_node_menu_item(label, callback)


register_node_menu_item = add_node_menu_item
unregister_node_menu_item = remove_node_menu_item
NodeMenuItem = ContextMenuItem


def add_background_menu_item(
    label: str,
    callback: Callback,
) -> bool:
    """Register a background-context menu callback in the global registry."""
    return _REGISTRY.add_background_menu_item(label, callback)


def remove_background_menu_item(
    label: str,
    callback: Optional[Callback] = None,
) -> None:
    """Remove background menu callbacks by label and optional callback."""
    _REGISTRY.remove_background_menu_item(label, callback)


def _get_node_menu_items(node_type: Optional[str]) -> List[ContextMenuItem]:
    """Internal: return node menu entries applicable to the provided node type."""
    return _REGISTRY.get_node_menu_items(node_type)


def get_node_menu_items(node_type: Optional[str]) -> List[ContextMenuItem]:
    """Internal compatibility alias for node menu queries."""
    return _get_node_menu_items(node_type)


def get_background_menu_items() -> List[ContextMenuItem]:
    """Internal: return currently registered background menu entries."""
    return _REGISTRY.get_background_menu_items()


def clear_node_menu_items() -> None:
    """Internal: remove all node menu registrations from the global registry."""
    _REGISTRY.clear_node_menu_items()


def clear_background_menu_items() -> None:
    """Internal: remove all background menu registrations from the global registry."""
    _REGISTRY.clear_background_menu_items()


__all__ = [
    "NodeMenuItem",
    "add_background_menu_item",
    "add_node_menu_item",
    "get_node_menu_items",
    "register_node_menu_item",
    "remove_background_menu_item",
    "remove_node_menu_item",
    "unregister_node_menu_item",
]
