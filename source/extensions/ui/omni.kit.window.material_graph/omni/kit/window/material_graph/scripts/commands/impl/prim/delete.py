"""Undo-safe deletion for connected Material Graph prims."""

from dataclasses import dataclass
from typing import Optional

import omni.kit.commands
from omni.usd.commands import DeletePrimsCommand
from pxr import Sdf, Usd, UsdShade

from ....config.logging import log_exception, logger
from ..stage_helper import UsdStageHelper

# pylint: disable=no-member


@dataclass
class _AttributeSpecSnapshot:
    """Exact edit-layer state for one connection-bearing attribute."""

    attribute_path: Sdf.Path
    spec_path: Sdf.Path
    target_layer: Sdf.Layer
    snapshot: Sdf.Layer
    authored: bool
    before_prim_paths: frozenset[Sdf.Path]


class MaterialGraph_DeletePrimsCommand(omni.kit.commands.Command, UsdStageHelper):
    """Delete prims while preserving every affected connection for undo.

    Kit's ``DeletePrimsCommand`` cleans connections that target a deleted prim.
    When two connected prims are deleted together, the second prim can be
    snapshotted after the first connection was cleaned, so Kit's undo restores
    the prims without their internal edge.  This command captures only the
    affected attribute specs before delegating deletion and reapplies those
    exact specs after Kit restores the prims.
    """

    def __init__(
        self,
        paths: list[Sdf.Path],
        stage: Optional[Usd.Stage] = None,
        context_name: Optional[str] = None,
    ) -> None:
        UsdStageHelper.__init__(self, stage, context_name)
        self._paths = tuple(Sdf.Path(str(path)) for path in paths if path)
        self._snapshots: list[_AttributeSpecSnapshot] = []
        self._delete_command: Optional[DeletePrimsCommand] = None
        self._captured = False
        self._failed = False

    def _is_affected_path(self, path: Sdf.Path) -> bool:
        """Return whether a prim/property path belongs to a deletion target."""
        prim_path = path.GetPrimPath()
        return any(prim_path == deleted or prim_path.HasPrefix(deleted) for deleted in self._paths)

    @staticmethod
    def _iter_ancestor_paths(path: Sdf.Path):
        """Yield a prim path and its ancestors, nearest first."""
        while path and path != Sdf.Path.absoluteRootPath:
            yield path
            path = path.GetParentPath()

    def _capture_affected_specs(self, stage: Usd.Stage) -> bool:
        """Capture exact layer-stack specs for attributes touching deleted prims."""
        target_paths = ", ".join(str(path) for path in self._paths)
        try:
            edit_target = stage.GetEditTarget()
            edit_layer = edit_target.GetLayer()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "delete edit-target lookup failed",
                prim_path=target_paths,
                action="capture_delete_connections",
                exc=exc,
            )
            return False
        snapshots: list[_AttributeSpecSnapshot] = []
        captured_specs: set[tuple[str, Sdf.Path]] = set()

        def capture_spec(attribute_path: Sdf.Path, target_layer: Sdf.Layer, spec_path: Sdf.Path) -> bool:
            """Capture one unique layer/property pair."""
            key = (target_layer.identifier, spec_path)
            if key in captured_specs:
                return True
            captured_specs.add(key)
            before_prim_paths = frozenset(
                path for path in self._iter_ancestor_paths(spec_path.GetPrimPath()) if target_layer.GetPrimAtPath(path)
            )
            snapshot = Sdf.Layer.CreateAnonymous("material_graph_delete_connection.usda")
            spec = target_layer.GetAttributeAtPath(spec_path)
            authored = bool(spec)
            if authored:
                Sdf.CreatePrimInLayer(snapshot, spec_path.GetPrimPath())
                if not Sdf.CopySpec(target_layer, spec_path, snapshot, spec_path):
                    logger.warning(
                        "delete aborted: failed to snapshot connection attribute='%s' layer='%s'; no prims were deleted",
                        attribute_path,
                        target_layer.identifier,
                    )
                    return False
            snapshots.append(
                _AttributeSpecSnapshot(
                    attribute_path,
                    spec_path,
                    target_layer,
                    snapshot,
                    authored,
                    before_prim_paths,
                )
            )
            return True

        try:
            graph_roots: set[Usd.Prim] = set()
            for path in self._paths:
                prim = stage.GetPrimAtPath(path)
                graph_root = prim
                current = prim
                while current:
                    if current.IsA(UsdShade.Material) or current.IsA(UsdShade.NodeGraph):
                        graph_root = current
                    current = current.GetParent()
                if graph_root:
                    graph_roots.add(graph_root)
            graph_roots = {
                root
                for root in graph_roots
                if not any(root != other and root.GetPath().HasPrefix(other.GetPath()) for other in graph_roots)
            }
            for prim in (item for root in graph_roots for item in Usd.PrimRange(root)):
                for attribute in prim.GetAttributes():
                    connections = attribute.GetConnections()
                    if not connections:
                        continue
                    if not self._is_affected_path(attribute.GetPath()) and not any(
                        self._is_affected_path(source_path) for source_path in connections
                    ):
                        continue
                    spec_path = edit_target.MapToSpecPath(attribute.GetPath())
                    if not spec_path:
                        logger.warning(
                            "delete aborted: edit target could not map connection attribute='%s' for targets=%s; "
                            "no prims were deleted",
                            attribute.GetPath(),
                            target_paths,
                        )
                        return False
                    if not capture_spec(attribute.GetPath(), edit_layer, spec_path):
                        return False
                    for property_spec in attribute.GetPropertyStack():
                        if isinstance(property_spec, Sdf.AttributeSpec) and not capture_spec(
                            attribute.GetPath(), property_spec.layer, property_spec.path
                        ):
                            return False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # USD traversal is the transaction boundary.  A malformed composed
            # property must abort before deletion rather than leave partial state.
            log_exception(
                logger,
                "delete connection snapshot failed",
                prim_path=target_paths,
                action="capture_delete_connections",
                exc=exc,
            )
            return False
        self._snapshots = snapshots
        self._captured = True
        return True

    def _prune_created_ancestors(self, state: _AttributeSpecSnapshot) -> None:
        """Remove inert over specs introduced only by connection cleanup."""
        for path in self._iter_ancestor_paths(state.spec_path.GetPrimPath()):
            if path in state.before_prim_paths:
                break
            spec = state.target_layer.GetPrimAtPath(path)
            if not spec:
                continue
            if spec.properties or spec.nameChildren:
                break
            if any(str(key) != "specifier" for key in spec.ListInfoKeys()):
                break
            parent = spec.nameParent or state.target_layer.pseudoRoot
            try:
                del parent.nameChildren[spec.name]
            except (KeyError, TypeError, AttributeError) as exc:
                logger.warning(
                    "delete undo could not prune temporary inert prim='%s' layer='%s': %s; "
                    "restored graph data is intact but the layer may contain an empty over",
                    path,
                    state.target_layer.identifier,
                    exc,
                )
                break

    def _restore_affected_specs(self) -> bool:
        """Restore every captured connection attribute to its exact prior spec."""
        restored = True
        for state in self._snapshots:
            try:
                current = state.target_layer.GetAttributeAtPath(state.spec_path)
                prim_spec = state.target_layer.GetPrimAtPath(state.spec_path.GetPrimPath())
                if current and prim_spec:
                    prim_spec.RemoveProperty(current)
                if not state.authored:
                    self._prune_created_ancestors(state)
                    continue
                Sdf.CreatePrimInLayer(state.target_layer, state.spec_path.GetPrimPath())
                if not Sdf.CopySpec(state.snapshot, state.spec_path, state.target_layer, state.spec_path):
                    logger.error(
                        "delete undo failed to restore connection attribute='%s' spec='%s' layer='%s'; "
                        "the restored graph may be missing this connection",
                        state.attribute_path,
                        state.spec_path,
                        state.target_layer.identifier,
                    )
                    restored = False
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "delete undo connection restore failed",
                    prim_path=str(state.attribute_path),
                    action="restore_delete_connection",
                    exc=exc,
                )
                restored = False
        return restored

    def do(self) -> bool:
        """Delete every target after capturing affected connection specs."""
        if self._failed or not self._paths:
            self._failed = True
            return False
        stage = self._get_stage()
        if not stage:
            logger.warning(
                "delete prims aborted: no USD stage is open targets=%s; no prims were deleted",
                ", ".join(str(path) for path in self._paths),
            )
            self._failed = True
            return False
        if not self._captured and not self._capture_affected_specs(stage):
            self._failed = True
            return False

        try:
            self._delete_command = DeletePrimsCommand(list(self._paths), stage=stage)
            self._delete_command.do()
            remaining = [path for path in self._paths if stage.GetPrimAtPath(path)]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            target_paths = ", ".join(str(path) for path in self._paths)
            log_exception(logger, "delete prims failed", prim_path=target_paths, action="delete_prims", exc=exc)
            if self._delete_command:
                try:
                    self._delete_command.undo()
                except Exception as rollback_exc:  # pylint: disable=broad-exception-caught
                    log_exception(
                        logger,
                        "delete rollback failed",
                        prim_path=target_paths,
                        action="rollback_delete_prims",
                        exc=rollback_exc,
                    )
            self._restore_affected_specs()
            self._failed = True
            return False
        if remaining:
            logger.warning(
                "delete prims did not remove all targets remaining=%s; the operation will be rolled back",
                ", ".join(str(path) for path in remaining),
            )
            try:
                self._delete_command.undo()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "delete rollback failed",
                    prim_path=", ".join(str(path) for path in self._paths),
                    action="rollback_delete_prims",
                    exc=exc,
                )
            self._restore_affected_specs()
            self._failed = True
            return False
        return True

    def undo(self) -> None:
        """Restore deleted prims, then restore exact pre-delete connections."""
        if self._failed or not self._delete_command:
            return
        stage = self._get_stage()
        if not stage:
            logger.error(
                "delete undo failed for target(s) %s: no USD stage is open; deleted prims remain absent",
                ", ".join(str(path) for path in self._paths),
            )
            self._failed = True
            return
        try:
            self._delete_command.undo()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "delete undo failed",
                prim_path=", ".join(str(path) for path in self._paths),
                action="undo_delete_prims",
                exc=exc,
            )
            self._failed = True
            return
        if not self._restore_affected_specs():
            self._failed = True
