# pylint: disable=no-member
"""Implement material graph extension logic for `models/graph/nodes/nodegraph/selection_helper.py`."""

from typing import Any, Callable, List, Optional, Sequence

from pxr import Sdf

from .....config.logging import logger


class PrimSelectionHelper:
    """Caches selection state for graph models."""

    def __init__(self) -> None:
        """Initialize cached snapshot used to avoid redundant selection churn."""
        self._cache = []

    def clear(self) -> None:
        """Clear cached selection snapshot so next read fully resynchronizes."""
        self._cache.clear()

    def get_selected_nodes(
        self, usd_context: Any, stage: Any, root_path: Any, get_item_model: Callable[[Any], Any]
    ) -> List[Any]:
        """Return selected node models for the current selection."""
        context_selection = usd_context.get_selection() if usd_context else None
        if not context_selection:
            logger.debug("selection sync skipped: missing USD selection")
            return []

        kit_selection = sorted(set(context_selection.get_selected_prim_paths() or []))
        cache = sorted(
            set([model.prim_path.pathString for model in self._cache if model and getattr(model, "prim_path", None)])
        )
        if kit_selection == cache:
            return self._cache

        selected = []
        path_string = root_path.pathString
        for prim_path in kit_selection:
            if prim_path.startswith(path_string):
                prim = stage.GetPrimAtPath(Sdf.Path(prim_path)) if stage else None
                if prim:
                    model = get_item_model(Sdf.Path(prim_path))
                    if model:
                        selected.append(model)

        self._cache = selected
        return selected

    def sync_selection(self, usd_context: Any, value: Optional[Sequence[Any]], on_changed: Callable) -> None:
        """Sync selection to USD and emit change callbacks."""
        context_selection = usd_context.get_selection() if usd_context else None
        if not context_selection:
            return

        kit_selection = sorted(set(context_selection.get_selected_prim_paths() or []))
        selection = sorted(set([model.prim_path.pathString for model in (value or []) if model]))

        if kit_selection != selection:
            self._cache = value
            on_changed(kit_selection, selection, True)
            return

        if self._cache != value:
            self._cache = value
            on_changed(kit_selection, selection, False)
