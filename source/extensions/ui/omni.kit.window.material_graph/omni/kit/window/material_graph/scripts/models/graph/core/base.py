"""Implement material graph extension logic for `models/graph/core/base.py`."""

from typing import Any, Optional

from omni.kit.widget.graph import GraphModel
from pxr import Sdf, Usd

from ....config.logging import logger
from .proxy_item_mixin import ProxyItemMixin
from .state import ModelState

# pylint: disable=no-member


class GraphModelBase(ProxyItemMixin, GraphModel):
    """Base graph model for Kit graph widgets."""

    def __init__(
        self,
        name: str,
        type_name: str,
        path: Sdf.Path,
        parent: Optional[Any],
        prim: Usd.Prim,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool = False,
    ) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__()

        self._name = name
        self._type = type_name
        self._path = path
        self._parent = parent
        self._prim = prim
        self._context_name = context_name
        self._usd_context = usd_context
        self._plugin = plugin
        self._pause = pause
        self._valid = True
        self._has_validation_errors = False
        self._has_validation_warnings = False
        self._state = ModelState.ACTIVE
        self._validator = None

        self._stage = prim.GetStage()
        self._prim_path = prim.GetPath()

    def clear(self) -> None:
        """Execute clear behavior for material graph workflows."""

        self._prim = None
        self._prim_path = None
        self._valid = False
        self._state = ModelState.CLEARED
        self._notify_invalidated()

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        self.clear()
        self._stage = None
        self._parent = None
        self._usd_context = None
        self._plugin = None
        self._state = ModelState.DESTROYED
        self._notify_invalidated()

    def _notify_invalidated(self) -> None:
        """Execute notify invalidated behavior for material graph workflows."""

        try:
            self._item_changed(None)
        except AttributeError as exc:
            logger.debug("item_changed callback unavailable during notify: %s", exc)

    def notify_changed(self) -> None:
        """Execute notify changed behavior for material graph workflows."""

        self._notify_invalidated()

    def set_validation_state(self, has_errors: bool, has_warnings: bool) -> None:
        """Persist context-level validation state used by UI rendering."""
        self._has_validation_errors = bool(has_errors)
        self._has_validation_warnings = bool(has_warnings)

    def get_valid(self, item: Optional[Any] = None) -> bool:
        """Execute get valid behavior for material graph workflows."""

        return self._proxy_value(item, "valid", self._valid)

    @property
    def valid(self, item: Optional[Any] = None) -> bool:
        """Execute valid behavior for material graph workflows."""

        return self.get_valid(item)

    @property
    def has_validation_errors(self, item: Optional[Any] = None) -> bool:
        """Return whether context-level validation has active errors."""
        return self._proxy_value(item, "has_validation_errors", self._has_validation_errors)

    @property
    def has_validation_warnings(self, item: Optional[Any] = None) -> bool:
        """Return whether context-level validation has active warnings."""
        return self._proxy_value(item, "has_validation_warnings", self._has_validation_warnings)

    def get_path(self, item: Optional[Any] = None) -> Sdf.Path:
        """Execute get path behavior for material graph workflows."""

        return self._proxy_value(item, "path", self._path)

    @property
    def path(self, item: Optional[Any] = None) -> Sdf.Path:
        """Execute path behavior for material graph workflows."""

        return self.get_path(item)

    def get_parent(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute get parent behavior for material graph workflows."""

        return self._proxy_value(item, "parent", self._parent)

    @property
    def parent(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute parent behavior for material graph workflows."""

        return self.get_parent(item)

    def set_name(self, value: str) -> None:
        """Execute set name behavior for material graph workflows."""

        pass

    @classmethod
    def get_type_name(cls) -> str:
        """Execute get type name behavior for material graph workflows."""

        return cls.__name__

    def get_name(self, item: Optional[Any] = None) -> str:
        """Execute get name behavior for material graph workflows."""

        return self._proxy_value(item, "name", self._name)

    @property
    def name(self, item: Optional[Any] = None) -> str:
        """Execute name behavior for material graph workflows."""

        return self.get_name(item)

    def set_name_for_item(self, value: str, item: Optional[Any] = None) -> None:
        """Execute set name for item behavior for material graph workflows."""

        if self._proxy_set(item, "name", value):
            return
        if value != self._name:
            self.set_name(value)

    @name.setter
    def name(self, value: str, item: Optional[Any] = None) -> None:
        """Execute name behavior for material graph workflows."""

        self.set_name_for_item(value, item)

    def get_type(self, item: Optional[Any] = None) -> str:
        """Execute get type behavior for material graph workflows."""

        return self._proxy_value(item, "type", self._type)

    @property
    def type(self, item: Optional[Any] = None) -> str:
        """Execute type behavior for material graph workflows."""

        return self.get_type(item)

    def get_stage(self, item: Optional[Any] = None) -> Any:
        """Execute get stage behavior for material graph workflows."""

        return self._proxy_value(item, "stage", self._get_stage())

    @property
    def stage(self, item: Optional[Any] = None) -> Any:
        """Execute stage behavior for material graph workflows."""

        return self.get_stage(item)

    def get_model_root(self, item: Optional[Any] = None) -> "GraphModelBase":
        """Execute get model root behavior for material graph workflows."""

        if item:
            return item.model_root
        return self._parent.model_root if self._parent else self

    @property
    def model_root(self, item: Optional[Any] = None) -> "GraphModelBase":
        """Execute model root behavior for material graph workflows."""

        return self.get_model_root(item)

    def get_pause(self, item: Optional[Any] = None) -> bool:
        """Execute get pause behavior for material graph workflows."""

        return self._proxy_value(item, "pause", self._pause)

    @property
    def pause(self, item: Optional[Any] = None) -> bool:
        """Execute pause behavior for material graph workflows."""

        return self.get_pause(item)

    @pause.setter
    def pause(self, enabled: bool) -> None:
        """Execute pause behavior for material graph workflows."""

        self.set_pause(enabled)

    def set_pause(self, enabled: bool) -> None:
        """Execute set pause behavior for material graph workflows."""

        self._pause = enabled

    def get_prim(self, item: Optional[Any] = None) -> Any:
        """Execute get prim behavior for material graph workflows."""

        return self._proxy_value(item, "prim", self._prim)

    @property
    def prim(self, item: Optional[Any] = None) -> Any:
        """Execute prim behavior for material graph workflows."""

        return self.get_prim(item)

    def get_usd_context(self, item: Optional[Any] = None) -> Any:
        """Execute get usd context behavior for material graph workflows."""

        return self._proxy_value(item, "usd_context", self._usd_context)

    @property
    def usd_context(self, item: Optional[Any] = None) -> Any:
        """Execute usd context behavior for material graph workflows."""

        return self.get_usd_context(item)

    def get_plugin(self, item: Optional[Any] = None) -> Any:
        """Execute get plugin behavior for material graph workflows."""

        return self._proxy_value(item, "plugin", self._plugin)

    @property
    def plugin(self, item: Optional[Any] = None) -> Any:
        """Execute plugin behavior for material graph workflows."""

        return self.get_plugin(item)

    def get_item_model(self, item: Any) -> Optional[Any]:
        """Execute get item model behavior for material graph workflows."""

        if item is None:
            return None

        if isinstance(item, Sdf.Path):
            if item.IsPrimPath() and item == self._prim_path:
                return self
            if item.IsPrimPropertyPath():
                getter = getattr(self, "get_property_model", None)
                if callable(getter):
                    return getter(item)
                logger.debug("property model lookup failed for %s", item)
            return None

        get_path = getattr(item, "GetPath", None)
        if callable(get_path):
            return self.get_item_model(get_path())

        if hasattr(item, "prim_model"):
            return item.prim_model

        return None

    def get_context_name(self, item: Optional[Any] = None) -> str:
        """Execute get context name behavior for material graph workflows."""

        return self._proxy_value(item, "context_name", self._context_name)

    @property
    def context_name(self, item: Optional[Any] = None) -> str:
        """Execute context name behavior for material graph workflows."""

        return self.get_context_name(item)

    @property
    def validator(self) -> Optional[Any]:
        """Return the validator associated with this graph model tree."""
        if self._parent:
            return self.model_root.validator
        return self._validator

    @validator.setter
    def validator(self, value: Optional[Any]) -> None:
        """Set the validator on the root model."""
        if self._parent:
            self.model_root.validator = value
            return
        self._validator = value

    def get_prim_model(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute get prim model behavior for material graph workflows."""

        return self._proxy_value(item, "prim_model", None)

    @property
    def prim_model(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute prim model behavior for material graph workflows."""

        return self.get_prim_model(item)

    def get_prim_path(self, item: Optional[Any] = None) -> Sdf.Path:
        """Execute get prim path behavior for material graph workflows."""

        return self._proxy_value(item, "prim_path", self._prim_path)

    @property
    def prim_path(self, item: Optional[Any] = None) -> Sdf.Path:
        """Execute prim path behavior for material graph workflows."""

        return self.get_prim_path(item)

    def prim_exists(self, prim_path: Optional[Sdf.Path] = None) -> bool:
        """Execute prim exists behavior for material graph workflows."""

        stage = self._get_stage()
        if not stage:
            return False

        path = prim_path
        if not path:
            path = self._prim_path
        if not path:
            return False

        return bool(stage.GetPrimAtPath(path))

    def can_connect(self, source: Any, target: Any) -> bool:
        """Execute can connect behavior for material graph workflows."""

        from ..ports import AttributeModel

        if isinstance(source, AttributeModel) and isinstance(target, AttributeModel):
            return source.can_connect(target)
        return False

    def _get_stage(self) -> Optional[Usd.Stage]:
        """Execute get stage behavior for material graph workflows."""

        if self._usd_context:
            stage = self._usd_context.get_stage()
            if not stage:
                self._stage = None
            else:
                self._stage = stage
        return self._stage


__all__ = ["GraphModelBase"]
