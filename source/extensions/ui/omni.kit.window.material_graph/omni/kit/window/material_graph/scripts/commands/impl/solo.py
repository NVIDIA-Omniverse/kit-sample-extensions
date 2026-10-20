"""Command for soloing/unsoloing a render context via session layer disconnections."""

from typing import Dict, List, Optional

import omni.kit.commands
from pxr import Sdf, Tf, Usd, UsdShade

from ...config.logging import logger
from .stage_helper import UsdStageHelper

__all__ = ["MaterialGraph_SoloContextCommand"]


class MaterialGraph_SoloContextCommand(omni.kit.commands.Command, UsdStageHelper):
    """Disconnect or restore Material outputs on the session layer for context soloing.

    When *solo* is True, all outputs in *output_names* are disconnected on the
    session layer.  When False, session layer overrides for those outputs are
    removed, restoring the root layer connections.
    """

    def __init__(
        self,
        prim_path: Sdf.Path,
        output_names: List[str],
        solo: bool = True,
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        UsdStageHelper.__init__(self, stage)
        self._prim_path = prim_path
        self._output_names = list(output_names)
        self._solo = solo
        self._affected: List[str] = []
        self._session_snapshot: Sdf.Layer | None = None
        self._snapshot_properties: Dict[str, bool] = {}
        self._failed = False

    def _capture_session_properties(self, session_layer: Sdf.Layer) -> bool:
        """Snapshot exact pre-command property specs for lossless undo."""
        self._session_snapshot = Sdf.Layer.CreateAnonymous("material_graph_solo_undo.usda")
        self._snapshot_properties = {}
        for output_name in self._output_names:
            attr_path = self._prim_path.AppendProperty(f"{UsdShade.Tokens.outputs}{output_name}")
            exists = bool(session_layer.GetAttributeAtPath(attr_path))
            self._snapshot_properties[output_name] = exists
            if not exists:
                continue
            Sdf.CreatePrimInLayer(self._session_snapshot, self._prim_path)
            try:
                copied = Sdf.CopySpec(session_layer, attr_path, self._session_snapshot, attr_path)
            except (RuntimeError, ValueError, TypeError, Tf.ErrorException) as exc:
                logger.warning("Solo context: failed to snapshot %s: %s", attr_path, exc)
                self._session_snapshot = None
                self._snapshot_properties = {}
                return False
            if not copied:
                logger.warning("Solo context: failed to snapshot %s", attr_path)
                self._session_snapshot = None
                self._snapshot_properties = {}
                return False
        return True

    def _restore_session_properties(self, session_layer: Sdf.Layer) -> None:
        """Restore the exact property specs that existed before do()."""
        if not self._session_snapshot:
            return
        prim_spec = session_layer.GetPrimAtPath(self._prim_path)
        with Sdf.ChangeBlock():
            for output_name in self._output_names:
                full_name = f"{UsdShade.Tokens.outputs}{output_name}"
                attr_path = self._prim_path.AppendProperty(full_name)
                if prim_spec:
                    current = prim_spec.properties.get(full_name)
                    if current:
                        prim_spec.RemoveProperty(current)
                if self._snapshot_properties.get(output_name):
                    Sdf.CreatePrimInLayer(session_layer, self._prim_path)
                    if not Sdf.CopySpec(self._session_snapshot, attr_path, session_layer, attr_path):
                        logger.warning("Solo context: failed to restore %s", attr_path)

    def do(self) -> bool:
        if self._failed:
            return False
        stage = self._get_stage()
        if not stage:
            self._failed = True
            return False
        session_layer = stage.GetSessionLayer()
        if not session_layer:
            logger.warning(
                "solo context failed for material '%s' outputs=%s: the USD stage has no session layer; "
                "connections were not changed",
                self._prim_path,
                self._output_names,
            )
            self._failed = True
            return False
        prim = stage.GetPrimAtPath(self._prim_path)
        if not prim or not prim.IsValid():
            logger.warning(
                "solo context failed: material prim not found at '%s'; connections were not changed",
                self._prim_path,
            )
            self._failed = True
            return False

        if not self._capture_session_properties(session_layer):
            self._failed = True
            return False
        if self._solo:
            result = self._do_solo(stage, session_layer, prim)
        else:
            result = self._do_unsolo(session_layer)
        self._failed = not result
        return result

    def _do_solo(self, stage: Usd.Stage, session_layer: Sdf.Layer, prim: Usd.Prim) -> bool:
        material = UsdShade.Material(prim)
        self._affected = []
        with Sdf.ChangeBlock():
            for output_name in self._output_names:
                output = material.GetOutput(output_name)
                if not output or not output.HasConnectedSource():
                    continue
                attr_path = output.GetAttr().GetPath()

                session_spec = session_layer.GetAttributeAtPath(attr_path)
                if not session_spec:
                    Sdf.JustCreatePrimAttributeInLayer(
                        session_layer,
                        attr_path,
                        Sdf.ValueTypeNames.Token,
                        Sdf.VariabilityVarying,
                        False,
                    )
                    session_spec = session_layer.GetAttributeAtPath(attr_path)

                if session_spec:
                    session_spec.connectionPathList.ClearEditsAndMakeExplicit()
                    session_spec.connectionPathList.explicitItems = []
                    self._affected.append(output_name)
                    logger.debug("Solo context: disconnected %s on session layer", output_name)
        return True

    def _do_unsolo(self, session_layer: Sdf.Layer) -> bool:
        prim_spec = session_layer.GetPrimAtPath(self._prim_path)
        if not prim_spec:
            return True
        with Sdf.ChangeBlock():
            for output_name in self._output_names:
                full_name = f"{UsdShade.Tokens.outputs}{output_name}"
                prop = prim_spec.properties.get(full_name)
                if prop:
                    prim_spec.RemoveProperty(prop)
                    logger.debug("Solo context: removed session override for %s", full_name)
        return True

    def undo(self) -> None:
        if self._failed:
            return
        stage = self._get_stage()
        if not stage:
            return
        session_layer = stage.GetSessionLayer()
        if not session_layer:
            return
        self._restore_session_properties(session_layer)
