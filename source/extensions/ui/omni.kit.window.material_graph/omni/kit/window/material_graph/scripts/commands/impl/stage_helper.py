"""Reliable explicit-stage lookup for Material Graph commands."""

from typing import Optional

from omni.usd.commands import UsdStageHelper as KitUsdStageHelper
from pxr import Usd


class UsdStageHelper(KitUsdStageHelper):
    """Prefer the exact stage supplied by the caller.

    Kit's helper stores only a ``UsdUtils.StageCache`` ID. In-memory stages
    and some non-default contexts are not guaranteed to be in that cache, so
    an explicitly supplied valid stage can otherwise resolve to ``None`` when
    the command executes. Keeping the direct reference also ensures undo and
    redo continue to target the command's owning stage.
    """

    def __init__(self, stage: Optional[Usd.Stage] = None, context_name: Optional[str] = None) -> None:
        self._material_graph_stage = stage
        super().__init__(stage, context_name)

    def _get_stage(self) -> Optional[Usd.Stage]:
        """Return the explicit stage, falling back to Kit context lookup."""
        if self._material_graph_stage is not None:
            return self._material_graph_stage
        return super()._get_stage()
