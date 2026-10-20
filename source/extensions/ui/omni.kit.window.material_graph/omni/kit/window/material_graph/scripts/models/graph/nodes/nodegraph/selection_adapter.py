"""Selection synchronization adapter between graph model items and USD stage selection."""

from typing import Any, List, Optional

from pxr import Usd

from .....commands.wrappers.selection import SelectPrims
from .....config.logging import logger
from .selection_helper import PrimSelectionHelper


class SelectionAdapter:
    """Adapter that bridges graph-model selection with stage prim-selection APIs."""

    def __init__(self, usd_context: Any) -> None:
        """Initialize instance state for this material graph component."""

        self._usd_context = usd_context
        self._helper = PrimSelectionHelper()

    def clear(self) -> None:
        """Reset cached selection helper state before context/model transitions."""
        self._helper.clear()

    def get_selected_nodes(
        self,
        stage: Optional[Usd.Stage],
        prim_path: Any,
        get_item_model: Any,
    ) -> List[Any]:
        """Return selected node items from the USD context."""
        return self._helper.get_selected_nodes(self._usd_context, stage, prim_path, get_item_model)

    def sync_selection(self, value: List[Any], on_changed: Any) -> None:
        """Synchronize selection with the USD context."""
        self._helper.sync_selection(self._usd_context, value, on_changed)

    @staticmethod
    def apply_selection(kit_selection: Any, selection: List[Any], run_select: bool) -> bool:
        """Apply selection to Kit, optionally running the select command."""
        if not run_select:
            return True
        result = SelectPrims(kit_selection, selection)
        if not result.success:
            logger.warning(
                "USD selection update failed requested=%s: %s; the previous selection was preserved",
                [str(item) for item in selection],
                result.error_code or result.message or "command returned no reason",
            )
        return result.success
