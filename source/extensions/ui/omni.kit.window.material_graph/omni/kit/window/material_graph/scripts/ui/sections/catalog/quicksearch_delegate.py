"""QuickSearch delegate bridge for material graph catalog items."""

from typing import Any

import omni.ui as ui

from .delegate import MaterialGraphCatalogDelegate


class MaterialGraphQuickSearchDelegate(MaterialGraphCatalogDelegate):
    """Adapter delegate that matches quicksearch's `delegate_type(flat=...)` contract."""

    def __init__(self, flat: bool = False) -> None:
        super().__init__()
        self._flat = bool(flat)

    def build_widget(self, model: ui.AbstractItemModel, item: Any, column_id: int, level: int, expanded: bool) -> None:
        """Build grouped rows for tree mode and regular rows for flat mode."""
        if self._flat and item is None:
            return
        super().build_widget(model, item, column_id, level, expanded)
