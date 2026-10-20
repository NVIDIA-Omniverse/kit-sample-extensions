"""Command for importing external USD nodegraphs into the active material graph."""

from pathlib import Path
from typing import Dict, Optional, Sequence

import omni.kit.commands
import omni.usd
from omni.usd.commands import DeletePrimsCommand
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdUI

from ....config.logging import logger
from ..nodegraph_api import get_nodegraph_node_api
from ..stage_helper import UsdStageHelper

# pylint: disable=no-member


class MaterialGraph_ImportNodeGraphCommand(omni.kit.commands.Command, UsdStageHelper):
    """
    Import compound shader from external USD file.
    """

    def __init__(
        self,
        parent_path: Sdf.Path,
        source_asset: str,
        identifier: str,
        position: Optional[Sequence[float]] = None,
        stage: Optional[Usd.Stage] = None,
        select_new_prim: bool = True,
        attributes_to_set: Optional[Dict[str, object]] = None,
        prim_name: Optional[str] = None,
        context_name: Optional[str] = None,
    ) -> None:
        """Capture import source, destination, and optional post-import authoring inputs."""
        UsdStageHelper.__init__(self, stage)
        self._parent_path = parent_path
        self._source_asset = source_asset
        self._identifier = identifier
        self._position = position
        self._select_new_prim = select_new_prim
        self._attributes_to_set = attributes_to_set
        self._prim_name = prim_name
        self._context_name = context_name
        self._created_path: Optional[str] = None
        self._selected_prim_paths: list[str] = []
        self._failed = False

    def _resolve_source_layer(self) -> Optional[Sdf.Layer]:
        """Resolve and validate the source layer path before import."""
        if not isinstance(self._source_asset, str) or not self._source_asset:
            logger.warning(
                "nodegraph import rejected invalid source asset: value=%r actual_type=%s target_parent=%s",
                self._source_asset,
                type(self._source_asset).__name__,
                self._parent_path,
            )
            return None
        path = Path(self._source_asset)
        if path.suffix and path.is_absolute() and not path.exists():
            logger.warning(
                "nodegraph import source asset does not exist: asset='%s' identifier='%s' target_parent='%s'",
                self._source_asset,
                self._identifier,
                self._parent_path,
            )
            return None
        source_layer = Sdf.Layer.FindOrOpen(self._source_asset)
        if not source_layer:
            logger.warning(
                "nodegraph import could not open source asset='%s' identifier='%s' target_parent='%s'",
                self._source_asset,
                self._identifier,
                self._parent_path,
            )
            return None
        return source_layer

    def _resolve_source_path(self) -> Optional[Sdf.Path]:
        """Resolve the source prim path to an absolute Sdf.Path."""
        if not self._identifier:
            logger.warning(
                "nodegraph import rejected empty source identifier: asset=%s target_parent=%s",
                self._source_asset,
                self._parent_path,
            )
            return None
        source_path = self._identifier
        if not source_path.startswith("/"):
            source_path = Sdf.Path.absoluteRootPath.AppendChild(self._identifier)
        else:
            source_path = Sdf.Path(source_path)
        if not source_path.IsAbsolutePath():
            logger.warning(
                "nodegraph import rejected non-absolute source identifier='%s' asset='%s' target_parent='%s'",
                self._identifier,
                self._source_asset,
                self._parent_path,
            )
            return None
        return source_path

    def _resolve_target_path(self, stage: Usd.Stage, source_path: Sdf.Path) -> Sdf.Path:
        """Compute a unique target path under parent_path and cache it for undo."""
        target_name = self._prim_name
        if isinstance(target_name, str) and target_name.strip():
            target_name = _make_valid_identifier(target_name.strip())
        else:
            target_name = source_path.name
        target_path = omni.usd.get_stage_next_free_path(
            stage,
            self._parent_path.AppendChild(target_name).pathString,
            False,
        )
        self._created_path = target_path
        return Sdf.Path(target_path)

    def _apply_position(self, prim: Usd.Prim) -> bool:
        """Author node position metadata/customData on the imported prim when provided."""
        if not self._position:
            return True
        if not self._clear_position_custom_data(prim):
            return False
        node_graph_node = get_nodegraph_node_api(prim)
        if not node_graph_node:
            return False
        pos_attr = node_graph_node.CreatePosAttr()
        if not pos_attr or pos_attr.Set(self._position) is False:
            return False
        if self._context_name:
            key = f"omni:{UsdUI.Tokens.uiNodegraphNodePos}:{self._context_name}"
            if prim.SetCustomDataByKey(key, Gf.Vec2f(self._position)) is False:
                return False
        return True

    @staticmethod
    def _clear_position_custom_data(prim: Usd.Prim) -> bool:
        """Remove context-specific position customData keys before applying new values."""
        if not prim:
            return False
        prefixes = {
            f"omni:{UsdUI.Tokens.uiNodegraphNodePos}",
            # Legacy builds authored the token's Python property spelling
            # instead of its schema value.
            "omni:uiNodegraphNodePos",
        }
        data = dict(prim.GetCustomData() or {})
        changed = False

        # Remove malformed literal top-level spellings authored by older
        # whole-dictionary code.
        for key in list(data):
            if isinstance(key, str) and any(key == prefix or key.startswith(f"{prefix}:") for prefix in prefixes):
                data.pop(key)
                changed = True

        # USD namespace-path APIs represent the same keys as nested mappings
        # in GetCustomData(). Remove the complete position subtree while
        # preserving unrelated values under ``omni`` and elsewhere.
        for prefix in prefixes:
            segments = prefix.split(":")
            container = data
            for segment in segments[:-1]:
                child = container.get(segment)
                if not isinstance(child, dict):
                    container = None
                    break
                container = child
            if container is not None and segments[-1] in container:
                container.pop(segments[-1])
                changed = True

        if changed and prim.SetCustomData(data) is False:
            return False
        return True

    def _apply_attributes(self, stage: Usd.Stage, target_path: Sdf.Path) -> bool:
        """Apply optional attribute overrides onto the imported target prim."""
        if not self._attributes_to_set:
            return True
        resolved = []
        for attribute_path, value in self._attributes_to_set.items():
            property_name = str(attribute_path).lstrip(".")
            if not property_name or not Sdf.Path.IsValidNamespacedIdentifier(property_name):
                logger.warning(
                    "nodegraph import rejected invalid attribute name='%s' source='%s%s' target='%s'",
                    attribute_path,
                    self._source_asset,
                    self._identifier,
                    target_path,
                )
                return False
            attr_path = target_path.AppendProperty(property_name)
            attribute = stage.GetObjectAtPath(attr_path)
            if not isinstance(attribute, Usd.Attribute):
                logger.warning(
                    "nodegraph import could not initialize missing target attribute='%s' source='%s%s'",
                    attr_path,
                    self._source_asset,
                    self._identifier,
                )
                return False
            if attribute.GetTypeName() == Sdf.ValueTypeNames.Asset:
                value = Sdf.AssetPath(value)
            resolved.append((attribute, value))
        for attribute, value in resolved:
            if attribute.Set(value) is False:
                logger.warning(
                    "nodegraph import failed to set target attribute='%s' value=%r; imported prim will be rolled back",
                    attribute.GetPath(),
                    value,
                )
                return False
        return True

    def _rollback_target(self, target_layer: Sdf.Layer, snapshot: Sdf.Layer) -> None:
        """Restore the exact edit-layer state from before a failed import."""
        target_layer.TransferContent(snapshot)
        self._created_path = None
        self._failed = True

    def _run_import_transaction(
        self,
        stage: Usd.Stage,
        source_layer: Sdf.Layer,
        source_path: Sdf.Path,
        target_layer: Sdf.Layer,
        target_path: Sdf.Path,
        snapshot: Sdf.Layer,
    ) -> Optional[Usd.Prim]:
        """Copy and initialize the target after capturing the edit-layer snapshot."""
        copied = Sdf.CopySpec(source_layer, source_path, target_layer, target_path)
        if copied is False:
            logger.error(
                "import compound failed: CopySpec returned false source=%s target=%s", source_path, target_path
            )
            self._rollback_target(target_layer, snapshot)
            return None
        target_prim = stage.GetPrimAtPath(target_path)
        if not target_prim:
            logger.error("import compound failed: target prim missing at %s", target_path)
            self._rollback_target(target_layer, snapshot)
            return None

        if target_prim.HasProperty(UsdGeom.Tokens.xformOpOrder):
            if not target_prim.RemoveProperty(UsdGeom.Tokens.xformOpOrder):
                self._rollback_target(target_layer, snapshot)
                return None

        if not self._apply_position(target_prim) or not self._apply_attributes(stage, target_path):
            self._rollback_target(target_layer, snapshot)
            return None
        if self._select_new_prim and self._created_path:
            selection = self._get_context().get_selection()
            self._selected_prim_paths = selection.get_selected_prim_paths()
            selection.set_selected_prim_paths([self._created_path], True)
        return target_prim

    def do(self) -> Optional[Usd.Prim]:
        """Import source spec, post-process target prim, and optionally select it."""
        if self._failed:
            return None
        stage = self._get_stage()
        if not stage:
            logger.error(
                "nodegraph import failed: no USD stage is open source_asset='%s' identifier='%s' target_parent='%s'; "
                "no prim was created",
                self._source_asset,
                self._identifier,
                self._parent_path,
            )
            self._failed = True
            return None
        source_layer = self._resolve_source_layer()
        if not source_layer:
            self._failed = True
            return None
        source_path = self._resolve_source_path()
        if not source_path:
            self._failed = True
            return None
        target_layer = stage.GetEditTarget().GetLayer()
        target_path = self._resolve_target_path(stage, source_path)
        snapshot = Sdf.Layer.CreateAnonymous("material_graph_import_transaction.usda")
        snapshot.TransferContent(target_layer)

        try:
            return self._run_import_transaction(
                stage,
                source_layer,
                source_path,
                target_layer,
                target_path,
                snapshot,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # This is the transaction boundary: resolver and USD exceptions
            # must not leave a copied or partially initialized target spec.
            logger.warning(
                "nodegraph import transaction failed source='%s%s' target='%s': %s; partial target will be rolled back",
                self._source_asset,
                self._identifier,
                target_path,
                exc,
            )
            self._rollback_target(target_layer, snapshot)
            return None

    def undo(self) -> None:
        """Delete the imported prim when a created path exists and still resolves."""
        if not self._created_path:
            return
        stage = self._get_stage()
        if not stage or not stage.GetPrimAtPath(self._created_path):
            return
        delete_cmd = DeletePrimsCommand([self._created_path], stage=stage)
        delete_cmd.do()
        if self._select_new_prim:
            self._get_context().get_selection().set_selected_prim_paths(self._selected_prim_paths, True)


def _make_valid_identifier(name: str) -> str:
    """Return USD-safe identifier with fallback sanitizer."""
    try:
        return Tf.MakeValidIdentifier(name)
    except (TypeError, ValueError) as exc:
        logger.debug("Tf.MakeValidIdentifier failed name=%s: %s", name, exc)
        cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)
        return cleaned or "Nodegraph"
