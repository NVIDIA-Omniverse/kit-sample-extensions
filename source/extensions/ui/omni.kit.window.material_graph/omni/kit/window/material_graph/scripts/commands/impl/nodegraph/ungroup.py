"""Command that ungroups a nodegraph by moving children back to its parent scope."""

from typing import List, Optional, Sequence

import omni.kit.commands
from pxr import Sdf, Usd, UsdShade, UsdUI

from ....config.logging import logger
from ...execution import execute_command
from ..nodegraph_api import get_nodegraph_node_api
from ..stage_helper import UsdStageHelper
from .helpers import _group_nodes_into_nodegraph, _ungroup_nodegraph

# pylint: disable=no-member


class MaterialGraph_UngroupNodeGraphCommand(omni.kit.commands.Command, UsdStageHelper):
    """Ungroup a NodeGraph and move its contents out."""

    def __init__(self, nodegraph_path: Sdf.Path, stage: Optional[Usd.Stage] = None) -> None:
        """Store nodegraph identity and caches needed to rebuild grouping on undo."""
        UsdStageHelper.__init__(self, stage)
        self._nodegraph_path = Sdf.Path(str(nodegraph_path)) if nodegraph_path else None
        self._parent_path: Optional[Sdf.Path] = None
        self._child_names: List[str] = []
        self._position: Optional[Sequence[float]] = None
        self._nodegraph_snapshot: Optional[Sdf.Layer] = None
        self._nodegraph_spec_path: Optional[Sdf.Path] = None
        self._failed = False

    def _capture_nodegraph_spec(self, stage: Usd.Stage, prim: Usd.Prim) -> None:
        """Capture the complete edit-target NodeGraph spec for lossless undo."""
        edit_target = stage.GetEditTarget()
        spec_path = edit_target.MapToSpecPath(prim.GetPath())
        layer = edit_target.GetLayer()
        if not layer.GetPrimAtPath(spec_path):
            self._nodegraph_snapshot = None
            self._nodegraph_spec_path = None
            return
        snapshot = Sdf.Layer.CreateAnonymous("material_graph_ungroup_undo.usda")
        Sdf.CreatePrimInLayer(snapshot, spec_path.GetParentPath())
        if not Sdf.CopySpec(layer, spec_path, snapshot, spec_path):
            logger.warning("ungroup could not snapshot nodegraph spec %s", spec_path)
            return
        self._nodegraph_snapshot = snapshot
        self._nodegraph_spec_path = spec_path

    def _restore_nodegraph_spec(self, stage: Usd.Stage) -> None:
        """Overlay the exact pre-ungroup NodeGraph spec after structural undo."""
        if not self._nodegraph_snapshot or not self._nodegraph_spec_path:
            return
        layer = stage.GetEditTarget().GetLayer()
        if not Sdf.CopySpec(
            self._nodegraph_snapshot,
            self._nodegraph_spec_path,
            layer,
            self._nodegraph_spec_path,
        ):
            logger.warning("ungroup could not restore nodegraph spec %s", self._nodegraph_spec_path)

    def do(self) -> bool:
        """Ungroup target nodegraph while caching child names and position for undo."""
        if self._failed:
            return False
        stage = self._get_stage()
        if not stage or not self._nodegraph_path:
            self._failed = True
            return False
        prim = stage.GetPrimAtPath(self._nodegraph_path)
        if not prim:
            self._failed = True
            return False
        self._parent_path = prim.GetPath().GetParentPath()
        self._child_names = [child.GetName() for child in prim.GetChildren()]
        self._capture_nodegraph_spec(stage, prim)
        api = UsdUI.NodeGraphNodeAPI(prim)
        self._position = api.GetPosAttr().Get() if api else None
        result = _ungroup_nodegraph(stage, prim)
        self._failed = not result
        return result

    def undo(self) -> None:
        """Recreate nodegraph, move cached children back in, and restore connections."""
        if self._failed:
            return
        stage = self._get_stage()
        if not stage or not self._nodegraph_path or not self._parent_path:
            return

        if not stage.GetPrimAtPath(self._nodegraph_path):
            result = execute_command(
                "CreatePrimCommand",
                prim_type=UsdShade.Tokens.NodeGraph,
                prim_path=self._nodegraph_path.pathString,
                select_new_prim=False,
                create_default_xform=False,
                stage=stage,
            )
            if not result.success:
                return
        nodegraph_prim = stage.GetPrimAtPath(self._nodegraph_path)
        get_nodegraph_node_api(nodegraph_prim)
        if self._position is not None:
            api = UsdUI.NodeGraphNodeAPI(nodegraph_prim)
            api.CreatePosAttr(self._position)

        paths_to_move = {}
        for name in self._child_names:
            old_path = self._parent_path.AppendChild(name).pathString
            new_path = self._nodegraph_path.AppendChild(name).pathString
            if stage.GetPrimAtPath(old_path):
                paths_to_move[old_path] = new_path
        if paths_to_move:
            result = execute_command(
                "MovePrims",
                paths_to_move=paths_to_move,
                destructive=False,
                stage_or_context=stage,
            )
            if not result.success:
                return
        if self._nodegraph_snapshot and self._nodegraph_spec_path:
            self._restore_nodegraph_spec(stage)
            return
        selected_paths = {Sdf.Path(path) for path in paths_to_move.values()}
        if not _group_nodes_into_nodegraph(stage, self._parent_path, nodegraph_prim, selected_paths):
            logger.warning("ungroup undo could not reconstruct nodegraph connections %s", self._nodegraph_path)
