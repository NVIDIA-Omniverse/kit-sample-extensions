"""Undoable, explicit-stage metadata commands used by Material Graph UI controllers."""

from typing import Dict, Optional, Union

import omni.kit.commands
from pxr import Sdf, Usd

from ...config.logging import logger
from .stage_helper import UsdStageHelper


class MaterialGraph_SetPrimCustomDataCommand(omni.kit.commands.Command, UsdStageHelper):
    """Replace a prim's customData exactly while preserving undo/redo state."""

    def __init__(
        self,
        prim_path: Union[Sdf.Path, str],
        custom_data: Dict[str, object],
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        UsdStageHelper.__init__(self, stage)
        self._prim_path = Sdf.Path(str(prim_path))
        self._custom_data = dict(custom_data or {})
        self._previous_custom_data: Dict[str, object] = {}
        self._captured_previous = False
        self._failed = False

    def do(self):
        """Author the complete customData dictionary on the requested stage."""
        if self._failed:
            return None
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path) if stage else None
        if not prim or not prim.IsValid():
            self._failed = True
            return None
        if not self._captured_previous:
            self._previous_custom_data = dict(prim.GetCustomData() or {})
            self._captured_previous = True
        if prim.SetCustomData(self._custom_data) is False:
            if prim.SetCustomData(self._previous_custom_data) is False:
                logger.error("customData rollback failed for %s", self._prim_path)
            self._failed = True
            return None
        return prim

    def undo(self) -> None:
        """Restore the exact customData dictionary captured before the first execution."""
        if self._failed:
            return
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path) if stage else None
        if prim and prim.IsValid():
            if prim.SetCustomData(self._previous_custom_data) is False:
                logger.warning("customData undo failed for %s", self._prim_path)


class MaterialGraph_SetPrimCustomDataKeyCommand(omni.kit.commands.Command, UsdStageHelper):
    """Set or clear one namespaced customData key with exact undo state."""

    def __init__(
        self,
        prim_path: Union[Sdf.Path, str],
        key: str,
        value: object = None,
        clear: bool = False,
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        UsdStageHelper.__init__(self, stage)
        self._prim_path = Sdf.Path(str(prim_path))
        self._key = key
        self._value = value
        self._clear = clear
        self._previous_custom_data: Dict[str, object] = {}
        self._captured_previous = False
        self._failed = False

    def do(self):
        """Author the key using USD namespace-path semantics."""
        if self._failed:
            return None
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path) if stage else None
        if not prim or not prim.IsValid() or not self._key:
            self._failed = True
            return None
        if not self._captured_previous:
            self._previous_custom_data = dict(prim.GetCustomData() or {})
            self._captured_previous = True

        # Older whole-dictionary authoring could create a top-level literal
        # ``position:context`` entry that USD key-path access cannot read.
        # Remove that malformed spelling before setting/clearing the real key.
        cleaned = dict(prim.GetCustomData() or {})
        if self._key in cleaned:
            cleaned.pop(self._key)
            if prim.SetCustomData(cleaned) is False:
                if prim.SetCustomData(self._previous_custom_data) is False:
                    logger.error("customData-key rollback failed for %s", self._prim_path)
                self._failed = True
                return None

        if self._clear:
            result = prim.ClearCustomDataByKey(self._key)
        else:
            result = prim.SetCustomDataByKey(self._key, self._value)
        if result is False:
            if prim.SetCustomData(self._previous_custom_data) is False:
                logger.error("customData-key rollback failed for %s", self._prim_path)
            self._failed = True
            return None
        return prim

    def undo(self) -> None:
        """Restore the complete customData dictionary captured initially."""
        if self._failed:
            return
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(self._prim_path) if stage else None
        if prim and prim.IsValid():
            if prim.SetCustomData(self._previous_custom_data) is False:
                logger.warning("customData-key undo failed for %s", self._prim_path)
