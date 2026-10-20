"""Position transaction staging for atomic multi-item graph drag operations."""

from typing import Any, Dict, List, Optional

from ....ports import InputAttributeModel, OutputAttributeModel
from ...prim.model import PrimModel


class PositionMoveTransaction:
    """Stage transient node positions across a drag transaction."""

    def __init__(self) -> None:
        """Initialize instance state for this material graph component."""

        self._cache: Dict[str, Dict[str, Any]] = {}
        self._staging = False
        self._committing = False

    @property
    def is_staging(self) -> bool:
        """Return True when staged-position reads/writes are active."""
        return self._staging

    @property
    def is_committing(self) -> bool:
        """Return True while staged values are being committed."""
        return self._committing

    def _get_item_path(self, item: Any) -> str:
        """Build a stable cache key for prim and IO attribute items."""
        if item is None:
            return "__none__"
        if not hasattr(item, "prim_path"):
            return f"__item__:{type(item).__name__}"
        path = str(item.prim_path)

        if not isinstance(item, PrimModel):
            if isinstance(item, InputAttributeModel):
                path = f"{path}:InputNode"
            elif isinstance(item, OutputAttributeModel):
                path = f"{path}:OutputNode"
            elif hasattr(item, "get_type_name"):
                type_name = item.get_type_name()
                path = f"{path}:{type_name}"

        return path

    @staticmethod
    def _io_key(path: str, is_output: bool) -> str:
        """Build the staged key for an IO wrapper bound to a prim path."""
        return f"{path}:{'OutputNode' if is_output else 'InputNode'}"

    def _get_io_entry_key_for_prim_path(self, prim_path: str) -> Optional[str]:
        """Return unique IO key for a prim path, if exactly one exists."""
        keys = [k for k in (self._io_key(prim_path, False), self._io_key(prim_path, True)) if k in self._cache]
        return keys[0] if len(keys) == 1 else None

    def has_any_io_entries(self) -> bool:
        """Return True when current transaction contains IO wrapper keys."""
        return any(path.endswith(("InputNode", "OutputNode")) for path in self._cache)

    def begin(self, items: List[Any]) -> None:
        """Start a move transaction and snapshot initial item positions."""
        self._staging = False
        self._cache.clear()
        self._committing = False

        for item in items:
            self._insert(item)

        self._staging = True

    def _insert(self, item: Any, default_position: Any = None) -> None:
        """Insert a staged entry for an item, using fallback position if needed."""
        if item is None:
            return
        path = self._get_item_path(item)
        position = item.position
        if position is None:
            position = default_position
        self._cache[path] = {"item": item, "start": position, "end": position}

    def get_position(self, item: Any) -> Any:
        """Return staged end position when available, else live item position."""
        if item is None:
            return None
        path = self._get_item_path(item)
        entry = self._cache.get(path)
        if entry is None and isinstance(item, PrimModel):
            io_key = self._get_io_entry_key_for_prim_path(path)
            if io_key is not None:
                entry = self._cache.get(io_key)
        if not entry:
            return item.position
        if entry["end"] is None:
            return item.position
        return entry["end"]

    def set_position(self, item: Any, value: Any) -> None:
        """Update staged end position for an item during drag."""
        if item is None:
            return
        path = self._get_item_path(item)
        remapped_from_prim = False
        if path not in self._cache and isinstance(item, PrimModel):
            io_key = self._get_io_entry_key_for_prim_path(path)
            if io_key is not None:
                path = io_key
                remapped_from_prim = True
        entry = self._cache.get(path)
        if not entry:
            self._insert(item, default_position=value)
            entry = self._cache.get(path)

        # Keep IO wrapper owner bound to the IO key even when updates come in
        # through the owning PrimModel during drag.
        if not (remapped_from_prim and path.endswith(("InputNode", "OutputNode"))):
            entry["item"] = item
        if entry["start"] is None:
            current = item.position
            entry["start"] = current if current is not None else value
            if entry["end"] is None:
                entry["end"] = entry["start"]
        entry["end"] = value

    def apply(self, apply_position_fn: Any = None) -> None:
        """Commit changed staged entries and clear the transaction cache."""
        self._staging = False

        for _path, entry in self._cache.items():
            if entry["start"] != entry["end"]:
                if callable(apply_position_fn):
                    apply_position_fn(entry["item"], entry["end"])
                else:
                    entry["item"].position = entry["end"]

        self._cache.clear()

    def commit(self, apply_position_fn: Any = None) -> None:
        """Commit the current transaction and clear staging/commit flags."""
        if not self._staging:
            return

        self._committing = True
        try:
            self.apply(apply_position_fn)
        finally:
            self._committing = False

    def force_commit(self, apply_position_fn: Any = None) -> bool:
        """Commit if staged writes are pending and return whether commit ran."""
        if not self._staging:
            return False
        self.commit(apply_position_fn)
        return True
