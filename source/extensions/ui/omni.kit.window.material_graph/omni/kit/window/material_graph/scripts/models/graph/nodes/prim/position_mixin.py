"""Context-aware position metadata helpers shared by prim/nodegraph model classes."""

# pylint: disable=no-member
from typing import Any, Optional

from pxr import Gf, UsdUI

from .....commands.result import CommandResult
from .....commands.wrappers.ui_nodes import RemoveContextPosition, SetContextPosition


class PositionMixin:
    """Mixin that reads/writes per-context node position metadata through customData."""

    def _get_context_position_key(self, suffix: Optional[str] = None) -> str:
        """Return the custom data key for a position."""
        return self._get_context_custom_data_key(UsdUI.Tokens.uiNodegraphNodePos, suffix)

    def _get_context_custom_data_key(self, token: str, suffix: Optional[str] = None) -> str:
        """Return a per-context custom data key for a token."""
        key = f"omni:{token}"

        if suffix:
            key = f"{key}:{suffix}"

        return f"{key}:{self.context_name}"

    def sync_position(self) -> None:
        """Sync position from per-context custom data."""
        key = self._get_context_position_key()

        if self.prim.HasAuthoredCustomDataKey(key):
            self._ui_state.position = self.prim.GetCustomDataByKey(key)
        else:
            super().sync_position()

    def remove_position_cmd(self, suffix: Optional[str] = None) -> CommandResult:
        """Remove per-context position custom data via an undoable command."""
        key = self._get_context_position_key(suffix)

        if self.prim.HasAuthoredCustomDataKey(key):
            previous = self.prim.GetCustomDataByKey(key)
            return RemoveContextPosition(self.prim.GetPath(), key, previous, stage=self.prim.GetStage())
        return CommandResult(True, None, validation={"unchanged": True})

    def set_position_cmd(self, value: Any, suffix: Optional[str] = None, prev: Any = None) -> CommandResult:
        """Set per-context position custom data via an undoable command."""
        key = self._get_context_position_key(suffix)
        previous = (
            prev
            if prev is not None
            else (self.prim.GetCustomDataByKey(key) if self.prim.HasAuthoredCustomDataKey(key) else None)
        )
        return SetContextPosition(self.prim.GetPath(), key, Gf.Vec2f(value), previous, stage=self.prim.GetStage())
