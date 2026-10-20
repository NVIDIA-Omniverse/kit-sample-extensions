"""Command that groups selected nodes into a generated USD nodegraph container."""

from typing import List, Optional, Sequence

import omni.kit.commands
import omni.kit.undo
from pxr import Sdf, Usd, UsdShade

from ....config.logging import logger
from ...execution import execute_command
from ...wrappers import CreateNodeGraph
from ..stage_helper import UsdStageHelper
from .helpers import _group_nodes_into_nodegraph, _ungroup_nodegraph

# pylint: disable=no-member


class MaterialGraph_GroupNodeGraphCommand(omni.kit.commands.Command, UsdStageHelper):
    """Group selected nodes into a NodeGraph."""

    def __init__(
        self,
        parent_path: Sdf.Path,
        selected_paths: Sequence[Sdf.Path],
        position: Optional[Sequence[float]] = None,
        position_key: Optional[str] = None,
        context_visibility: Optional[object] = None,
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        """Store selection and placement inputs required for group/ungroup lifecycle."""
        UsdStageHelper.__init__(self, stage)
        self._parent_path = Sdf.Path(str(parent_path)) if parent_path else None
        self._selected_paths = [Sdf.Path(str(path)) for path in (selected_paths or [])]
        self._position = position
        self._position_key = position_key
        self._context_visibility = context_visibility
        self._nodegraph_path: Optional[Sdf.Path] = None
        self._moved_paths: List[Sdf.Path] = []
        self._failed = False

    def _validate_moved_prims(self, stage: Usd.Stage, moved_paths: List[Sdf.Path]) -> bool:
        """Return True when every expected moved path resolves to an authored prim."""
        for path in moved_paths:
            if not stage.GetPrimAtPath(path):
                logger.warning("grouping failed: missing moved prim %s", path)
                return False
        return True

    def _reset_failed_group(self, layer: Sdf.Layer, snapshot: Sdf.Layer) -> None:
        """Restore the exact pre-command edit layer and clear transient command state."""
        layer.TransferContent(snapshot)
        self._nodegraph_path = None
        self._moved_paths = []
        # Kit records a command whose ``do`` returned no payload.  Make any
        # later redo a permanent no-op so a transient failure cannot turn into
        # a delayed successful grouping after the original caller saw failure.
        self._failed = True

    def do(self) -> Optional[Usd.Prim]:
        """Create nodegraph, move selected nodes into it, and rewire edge connections."""
        if self._failed:
            return None
        stage = self._get_stage()
        if not stage or not self._parent_path or not self._selected_paths:
            self._failed = True
            return None

        edit_layer = stage.GetEditTarget().GetLayer()
        snapshot = Sdf.Layer.CreateAnonymous("material_graph_group_transaction.usda")
        snapshot.TransferContent(edit_layer)

        with omni.kit.undo.disabled():
            nodegraph_result = CreateNodeGraph(
                self._parent_path,
                self._position,
                self._position_key,
                self._context_visibility,
                stage=stage,
            )
        if not nodegraph_result.success or not nodegraph_result.payload:
            self._reset_failed_group(edit_layer, snapshot)
            return None
        nodegraph_prim = nodegraph_result.payload

        self._nodegraph_path = nodegraph_prim.GetPath()
        paths_to_move = {
            path.pathString: self._nodegraph_path.AppendChild(path.name).pathString for path in self._selected_paths
        }
        with omni.kit.undo.disabled():
            result = execute_command(
                "MovePrims",
                paths_to_move=paths_to_move,
                destructive=False,
                stage_or_context=stage,
            )
        if not result.success:
            self._reset_failed_group(edit_layer, snapshot)
            return None

        self._moved_paths = [Sdf.Path(path) for path in paths_to_move.values()]
        if not self._validate_moved_prims(stage, self._moved_paths):
            self._reset_failed_group(edit_layer, snapshot)
            return None
        with omni.kit.undo.disabled():
            grouped = _group_nodes_into_nodegraph(stage, self._parent_path, nodegraph_prim, set(self._moved_paths))
        if not grouped:
            self._reset_failed_group(edit_layer, snapshot)
            return None
        return nodegraph_prim

    def undo(self) -> None:
        """Undo grouping by ungrouping the created nodegraph prim when it still exists."""
        if not self._nodegraph_path:
            return
        stage = self._get_stage()
        if not stage:
            return
        prim = stage.GetPrimAtPath(self._nodegraph_path)
        if prim:
            _ungroup_nodegraph(stage, prim)
