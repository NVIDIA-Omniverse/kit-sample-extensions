"""Undoable command for removing selected source connections from a destination."""

from typing import Iterable, List, Optional

import omni.kit.commands
from pxr import Sdf, Tf, Usd

from ....config.logging import logger
from ..stage_helper import UsdStageHelper

# pylint: disable=no-member


class MaterialGraph_RemoveConnectionsCommand(omni.kit.commands.Command, UsdStageHelper):
    """Disconnects a list of sources from a destination attribute."""

    def __init__(
        self, dest_attr_path: Sdf.Path, disconnected_values: Iterable[Sdf.Path], stage: Optional[Usd.Stage] = None
    ) -> None:
        """Store destination/source paths and initialize previous-source undo cache."""
        UsdStageHelper.__init__(self, stage)
        self._dest_attr_path = dest_attr_path
        self._disconnected_values: List[Sdf.Path] = list(disconnected_values or [])
        self._spec_path: Optional[Sdf.Path] = None
        self._before_spec: Optional[Sdf.Layer] = None
        self._after_spec: Optional[Sdf.Layer] = None
        self._before_authored = False
        self._after_authored = False
        self._before_prim_paths: set[Sdf.Path] = set()
        self._failed = False

    def _iter_spec_prim_paths(self):
        """Yield the destination prim path and its ancestors, nearest first."""
        path = self._spec_path.GetPrimPath() if self._spec_path else Sdf.Path.emptyPath
        while path and path != Sdf.Path.absoluteRootPath:
            yield path
            path = path.GetParentPath()

    def _prune_created_ancestors(self, edit_layer: Sdf.Layer) -> None:
        """Remove empty over specs created solely to hold the connection edit."""
        for path in self._iter_spec_prim_paths():
            if path in self._before_prim_paths:
                break
            spec = edit_layer.GetPrimAtPath(path)
            if not spec:
                continue
            if spec.properties or spec.nameChildren:
                break
            if any(str(key) != "specifier" for key in spec.ListInfoKeys()):
                break
            parent = spec.nameParent or edit_layer.pseudoRoot
            try:
                del parent.nameChildren[spec.name]
            except (KeyError, TypeError, AttributeError) as exc:
                logger.warning("remove-connections could not prune inert prim %s: %s", path, exc)
                break

    def _capture_spec(self, edit_layer: Sdf.Layer, label: str) -> tuple[Optional[Sdf.Layer], bool]:
        """Copy the destination property spec without snapshotting unrelated layer state."""
        snapshot = Sdf.Layer.CreateAnonymous(label)
        spec = edit_layer.GetAttributeAtPath(self._spec_path) if self._spec_path else None
        if not spec:
            return snapshot, False
        Sdf.CreatePrimInLayer(snapshot, self._spec_path.GetPrimPath())
        if not Sdf.CopySpec(edit_layer, self._spec_path, snapshot, self._spec_path):
            logger.warning("remove-connections snapshot failed for %s", self._dest_attr_path)
            return None, False
        return snapshot, True

    def _restore_spec(self, edit_layer: Sdf.Layer, snapshot: Sdf.Layer, authored: bool) -> bool:
        """Replace only the destination property spec with a captured version."""
        if not self._spec_path:
            return False
        current = edit_layer.GetAttributeAtPath(self._spec_path)
        prim_spec = edit_layer.GetPrimAtPath(self._spec_path.GetPrimPath())
        if current and prim_spec:
            prim_spec.RemoveProperty(current)
        if not authored:
            self._prune_created_ancestors(edit_layer)
            return True
        Sdf.CreatePrimInLayer(edit_layer, self._spec_path.GetPrimPath())
        return bool(Sdf.CopySpec(snapshot, self._spec_path, edit_layer, self._spec_path))

    def _rollback(self, edit_layer: Sdf.Layer) -> bool:
        """Restore the pre-command property spec and latch command failure."""
        if self._before_spec and not self._restore_spec(edit_layer, self._before_spec, self._before_authored):
            logger.error("remove-connections rollback failed for %s", self._dest_attr_path)
        self._failed = True
        return False

    def do(self) -> bool:
        """Disconnect selected sources from destination and cache them for undo."""
        if self._failed:
            return False
        stage = self._get_stage()
        if not stage:
            self._failed = True
            return False
        dest_attr = stage.GetAttributeAtPath(self._dest_attr_path)
        if not dest_attr:
            self._failed = True
            return False

        edit_layer = stage.GetEditTarget().GetLayer()
        if not edit_layer:
            self._failed = True
            return False
        self._spec_path = stage.GetEditTarget().MapToSpecPath(self._dest_attr_path)
        if not self._spec_path:
            self._failed = True
            return False
        if self._after_spec:
            if self._restore_spec(edit_layer, self._after_spec, self._after_authored):
                return True
            self._failed = True
            return False

        self._before_spec, self._before_authored = self._capture_spec(
            edit_layer, "material_graph_remove_connections_before.usda"
        )
        if not self._before_spec:
            self._failed = True
            return False
        self._before_prim_paths = {path for path in self._iter_spec_prim_paths() if edit_layer.GetPrimAtPath(path)}
        connected = set(dest_attr.GetConnections())
        try:
            for path in self._disconnected_values:
                if path in connected and dest_attr.RemoveConnection(path) is False:
                    return self._rollback(edit_layer)
        except (RuntimeError, ValueError, TypeError, AttributeError, Tf.ErrorException) as exc:
            logger.warning("remove-connections write failed for %s: %s", self._dest_attr_path, exc)
            return self._rollback(edit_layer)

        self._after_spec, self._after_authored = self._capture_spec(
            edit_layer, "material_graph_remove_connections_after.usda"
        )
        if not self._after_spec:
            return self._rollback(edit_layer)
        return True

    def undo(self) -> None:
        """Restore previously disconnected sources back onto destination port."""
        if self._failed:
            return
        stage = self._get_stage()
        # Do not recreate a destination that was removed after this command.
        if not stage or not stage.GetAttributeAtPath(self._dest_attr_path):
            return
        edit_layer = stage.GetEditTarget().GetLayer()
        if not edit_layer or not self._before_spec:
            return
        if not self._restore_spec(edit_layer, self._before_spec, self._before_authored):
            logger.warning("remove-connections undo failed for %s", self._dest_attr_path)
