"""Backdrop node model handling per-context size, description, and stacking behavior."""

from typing import Any, Optional

from pxr import Usd, UsdUI

from ....commands.wrappers.attributes import SetDescription
from ....commands.wrappers.ui_nodes import SetContextPosition
from ....config.logging import logger
from ....config.nodes import Nodes
from ....settings.settings import Settings
from .prim.model import PrimModel
from .prim.position_mixin import PositionMixin


class BackdropModel(PositionMixin, PrimModel):
    """Prim model specialization for UsdUI.Backdrop nodes in the graph."""

    def __init__(
        self, prim: Usd.Prim, context_name: str, usd_context: Any, plugin: Any, parent: Any, sync: bool = True
    ) -> None:
        """Initialize backdrop model bound to UsdUI.Backdrop schema with parent context."""
        super().__init__(prim, context_name, usd_context, plugin, parent, UsdUI.Backdrop, sync)

    def sync_size(self) -> None:
        """Sync backdrop size, preferring per-context custom data."""
        key = self._get_context_custom_data_key(UsdUI.Tokens.uiNodegraphNodeSize)

        if self.prim.HasAuthoredCustomDataKey(key):
            size = self.prim.GetCustomDataByKey(key)
            self._ui_state.size = size
        else:
            super().sync_size()

    def set_size_cmd(self, value: Any) -> bool:
        """Set backdrop size in per-context custom data."""
        key = self._get_context_custom_data_key(UsdUI.Tokens.uiNodegraphNodeSize)
        previous = value[0] if value is not None else self._ui_state.size
        new_size = value[1] if value is not None else None
        result = SetContextPosition(self.prim_path, key, new_size, previous, stage=self._stage)
        if not result.success:
            logger.warning(
                "set backdrop size failed for prim '%s' requested_size=%r: %s; size was not changed",
                self.prim_path,
                new_size,
                result.error_code or result.message or "command returned no reason",
            )
            return False
        if new_size is None:
            self.sync_size()
        else:
            self._ui_state.size = new_size
        return True

    def sync_description(self) -> None:
        """Sync description from the USD backdrop API."""
        api = UsdUI.Backdrop(self._prim)
        self._description = api.GetDescriptionAttr().Get()

    @property
    def description(self, item: Optional[Any] = None) -> Optional[str]:
        """Return backdrop description text authored for this node or delegated item."""
        return item.description if item else self._description

    @description.setter
    def description(self, value: str, item: Optional[Any] = None) -> None:
        """Update backdrop description cache and persist it on UsdUI.Backdrop attribute."""

        self.set_description(value, item)

    def set_description(self, value: str, item: Optional[Any] = None) -> bool:
        """Update the backdrop description and report whether authoring succeeded."""
        if item and item != self:
            setter = getattr(item, "set_description", None)
            if callable(setter):
                return setter(value) is not False
            item.description = value
            return True
        if self._description != value:
            result = SetDescription(self.prim_path, value, self._description, stage=self._stage)
            if not result.success:
                logger.warning(
                    "set backdrop description failed for prim '%s': %s; description was not changed",
                    self.prim_path,
                    result.error_code or result.message or "command returned no reason",
                )
                return False
            self._description = value
        return True

    @property
    def display_color(self, item: Optional[Any] = None) -> Any:
        """Return backdrop display color, defaulting when no authored UI color exists."""
        if item:
            return item.display_color

        if self._ui_state.display_color is not None:
            return self._ui_state.display_color

        return Settings.get_backdrop_default_color()

    @display_color.setter
    def display_color(self, value: Any, item: Optional[Any] = None) -> None:
        """Set display color via base prim-model implementation."""
        PrimModel.display_color.fset(self, value, item)

    @property
    def stacking_order(self, item: Optional[Any] = None) -> int:
        """Return effective stacking order, using parent overlap calculator when available."""
        if item:
            return item.stacking_order

        if self._parent and hasattr(self._parent, "get_backdrop_stacking_order"):
            return self._parent.get_backdrop_stacking_order(self)

        return self._ui_state.stacking_order or 0

    def get_stacking_inputs(self) -> tuple[Any, Any, int]:
        """Return position, size, and raw stacking order for calculations."""
        return (
            self._ui_state.position,
            self._ui_state.size,
            self._ui_state.stacking_order or 0,
        )

    def set_stacking_inputs(
        self,
        *,
        position: Optional[Any] = None,
        size: Optional[Any] = None,
        stacking_order: Optional[int] = None,
    ) -> None:
        """Set UI state for stacking calculations without authoring USD."""
        if position is not None:
            self._ui_state.position = position
        if size is not None:
            self._ui_state.size = size
        if stacking_order is not None:
            self._ui_state.stacking_order = stacking_order
