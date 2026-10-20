"""Types and data containers for context menu integration."""

import weakref
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Set, Tuple, Union

from pxr import Sdf


class NodeMenuCallback(Protocol):
    """Node menu callback contract: callback(node_type, prim_path)."""

    def __call__(self, node_type: str, prim_path: Sdf.Path) -> object:
        """Handle a node-context menu action for a specific node type/path."""
        ...


class BackgroundMenuCallback(Protocol):
    """Background menu callback contract: callback(items, mouse_position)."""

    def __call__(self, items: List[Any], mouse_position: Tuple[float, float]) -> object:
        """Handle a background-context action for selected items and cursor position."""
        ...


Callback = Union[NodeMenuCallback, BackgroundMenuCallback, Callable[..., object]]
WeakCallbackRef = weakref.ReferenceType[Callback]
WeakOwnerRef = weakref.ReferenceType[object]
PartialCallbackMeta = Tuple[WeakCallbackRef, Tuple[object, ...], Dict[str, object]]
PartialBoundCallbackMeta = Tuple[WeakOwnerRef, Callback, Tuple[object, ...], Dict[str, object]]
OriginalCallback = Union[Callback, WeakCallbackRef, PartialCallbackMeta, PartialBoundCallbackMeta]


@dataclass(frozen=True)
class ContextMenuItem:
    """Represents a single context menu entry and its callback metadata."""

    label: str
    callback: Callback
    node_types: Optional[Set[str]] = None
    original_callback: Optional[OriginalCallback] = None


def normalize_node_types(node_types: Optional[Union[str, Iterable[str]]]) -> Optional[Set[str]]:
    """Normalize node type input into a stable set of strings."""
    if node_types is None:
        return None
    if isinstance(node_types, str):
        return {node_types} if node_types else None
    try:
        normalized = {str(n) for n in node_types if n}
        return normalized or None
    except TypeError:
        return None
