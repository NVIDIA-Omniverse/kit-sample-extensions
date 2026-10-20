"""Create-prim command used by material graph node/material authoring flows."""

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import omni.kit.commands
import omni.kit.undo
import omni.usd
from pxr import Sdf, Usd, UsdShade, UsdUI

from ....config.logging import get_logger
from ..stage_helper import UsdStageHelper

# pylint: disable=no-member

_PathLike = Union[Sdf.Path, str]
logger = get_logger()


class MaterialGraph_CreatePrimCommand(omni.kit.commands.Command, UsdStageHelper):
    """Create a USD prim with optional selection."""

    def __init__(
        self,
        parent_path: _PathLike,
        prim_type: str,
        prim_name: str,
        select_new_prim: bool = True,
        stage: Optional[Usd.Stage] = None,
        shader_identifier: Optional[str] = None,
        source_asset_path: Optional[str] = None,
        source_asset_context: Optional[str] = None,
        source_asset_subidentifier: Optional[str] = None,
        output_types: Optional[Dict[str, Sdf.ValueTypeName]] = None,
        position: Optional[Sequence[float]] = None,
        position_key: Optional[str] = None,
        context_visibility: Optional[Union[str, Iterable[str]]] = None,
        display_color: Optional[Sequence[float]] = None,
        size: Optional[Sequence[float]] = None,
        custom_data: Optional[Dict[str, object]] = None,
        input_values: Optional[Dict[str, Tuple[Sdf.ValueTypeName, object]]] = None,
    ) -> None:
        """Capture creation inputs and selection state required for undo restoration."""
        UsdStageHelper.__init__(self, stage)
        self._parent_path = parent_path
        self._prim_type = prim_type
        self._prim_name = prim_name
        self._select_new_prim = select_new_prim
        self._prim_path: Optional[Sdf.Path] = None
        self._selected_prim_paths: List[str] = []
        self._shader_identifier = shader_identifier
        self._source_asset_path = source_asset_path
        self._source_asset_context = source_asset_context
        self._source_asset_subidentifier = source_asset_subidentifier
        self._output_types = dict(output_types or {})
        self._position = tuple(position) if position is not None else None
        self._position_key = position_key
        self._context_visibility = context_visibility
        self._display_color = tuple(display_color) if display_color is not None else None
        self._size = tuple(size) if size is not None else None
        self._custom_data = dict(custom_data or {})
        self._input_values = dict(input_values or {})
        self._failed = False

    @staticmethod
    def _operation_succeeded(result: object) -> bool:
        """Treat only an explicit False from USD setters as failure."""
        return result is not False

    def _initialize_shader(self, prim: Usd.Prim) -> bool:
        """Author the complete shader definition and declared outputs."""
        if self._prim_type != UsdShade.Tokens.Shader:
            return True
        node_def = UsdShade.NodeDefAPI(prim)
        if not node_def:
            return False
        if self._source_asset_path:
            if not self._source_asset_context or not self._source_asset_subidentifier:
                return False
            if not self._operation_succeeded(
                node_def.SetSourceAsset(Sdf.AssetPath(self._source_asset_path), self._source_asset_context)
            ):
                return False
            if not self._operation_succeeded(
                node_def.SetSourceAssetSubIdentifier(
                    self._source_asset_subidentifier,
                    self._source_asset_context,
                )
            ):
                return False
        elif self._shader_identifier and not self._operation_succeeded(node_def.SetShaderId(self._shader_identifier)):
            return False

        shader = UsdShade.Shader(prim)
        if not shader:
            return False
        for name, value_type in self._output_types.items():
            if not shader.CreateOutput(name, value_type):
                return False
        for name, (value_type, value) in self._input_values.items():
            shader_input = shader.CreateInput(name, value_type)
            if not shader_input or shader_input.Set(value) is False:
                return False
        return True

    def _initialize_ui_state(self, prim: Usd.Prim) -> bool:
        """Author position, backdrop styling, and context visibility."""
        api = UsdUI.NodeGraphNodeAPI(prim)
        if self._display_color is not None and not self._operation_succeeded(
            api.CreateDisplayColorAttr().Set(self._display_color)
        ):
            return False
        if self._size is not None and not self._operation_succeeded(api.CreateSizeAttr().Set(self._size)):
            return False
        if self._position is not None:
            if self._position_key:
                if not self._operation_succeeded(prim.SetCustomDataByKey(self._position_key, self._position)):
                    return False
            elif not self._operation_succeeded(api.CreatePosAttr().Set(self._position)):
                return False
        if self._custom_data:
            updated_custom_data = dict(prim.GetCustomData() or {})
            updated_custom_data.update(self._custom_data)
            if not self._operation_succeeded(prim.SetCustomData(updated_custom_data)):
                return False
        if self._context_visibility:
            visibility = (
                [self._context_visibility]
                if isinstance(self._context_visibility, str)
                else list(self._context_visibility)
            )
            ui_data = prim.GetCustomDataByKey("omni:ui") if prim.HasAuthoredCustomDataKey("omni:ui") else {}
            ui_data = dict(ui_data) if isinstance(ui_data, dict) else {}
            ui_data["contextVisibility"] = visibility
            if not self._operation_succeeded(prim.SetCustomDataByKey("omni:ui", ui_data)):
                return False
        return True

    def _initialize_prim(self, prim: Usd.Prim) -> bool:
        """Apply all state owned by this creation command."""
        if not prim.ApplyAPI(UsdUI.NodeGraphNodeAPI):
            return False
        return self._initialize_shader(prim) and self._initialize_ui_state(prim)

    def _rollback_failed_create(self, edit_layer: Sdf.Layer, snapshot: Sdf.Layer) -> None:
        """Restore the exact edit-layer state from before a failed creation."""
        edit_layer.TransferContent(snapshot)
        self._prim_path = None
        self._failed = True

    def _build_prim_path(self) -> Sdf.Path:
        """Build a unique child path under parent_path using USD next-free-path rules."""
        if isinstance(self._parent_path, Sdf.Path):
            parent_path = self._parent_path
        else:
            parent_path = Sdf.Path(str(self._parent_path))
        path = parent_path.AppendChild(self._prim_name)
        return omni.usd.get_stage_next_free_path(self._get_stage(), path, True)

    def _ensure_material_parent_scope(self, stage) -> bool:
        """Ensure a material parent scope exists before creating material prims."""
        if self._prim_type != UsdShade.Tokens.Material:
            return True
        parent_path = (
            self._parent_path.pathString if isinstance(self._parent_path, Sdf.Path) else str(self._parent_path)
        )
        if stage.GetPrimAtPath(parent_path):
            return True
        return bool(stage.DefinePrim(parent_path, "Scope"))

    def _run_create_transaction(
        self,
        stage: Usd.Stage,
        edit_layer: Sdf.Layer,
        snapshot: Sdf.Layer,
    ) -> Optional[Usd.Prim]:
        """Perform creation after the edit-layer snapshot has been captured."""
        if not self._ensure_material_parent_scope(stage):
            self._rollback_failed_create(edit_layer, snapshot)
            return None

        self._prim_path = self._build_prim_path()
        # This command owns the complete create/initialize/undo transaction.
        # Author directly so a failed outer command cannot leave nested Kit
        # commands on the undo stack that later recreate a rolled-back prim.
        prim = stage.DefinePrim(self._prim_path, self._prim_type)
        if not prim:
            logger.warning(
                "create prim failed path='%s' type='%s': USD DefinePrim returned invalid; no prim was created",
                self._prim_path,
                self._prim_type,
            )
            self._rollback_failed_create(edit_layer, snapshot)
            return None

        if not self._initialize_prim(prim):
            logger.warning(
                "create prim initialization failed path='%s' type='%s' shader_identifier='%s' "
                "source_asset='%s' subidentifier='%s'; the partial prim will be rolled back",
                self._prim_path,
                self._prim_type,
                self._shader_identifier,
                self._source_asset_path,
                self._source_asset_subidentifier,
            )
            self._rollback_failed_create(edit_layer, snapshot)
            return None

        if self._select_new_prim:
            selection = self._get_context().get_selection()
            self._selected_prim_paths = selection.get_selected_prim_paths()
            # Replace the current selection with the newly created prim.
            selection.set_selected_prim_paths([str(self._prim_path)], True)

        return prim

    def do(self):
        """Create the prim, apply nodegraph API, and optionally select the new prim."""
        if self._failed:
            return None
        stage = self._get_stage()
        if not stage:
            logger.warning(
                "create prim failed parent='%s' name='%s' type='%s': no USD stage is open; no prim was created",
                self._parent_path,
                self._prim_name,
                self._prim_type,
            )
            self._failed = True
            return None

        edit_layer = stage.GetEditTarget().GetLayer()
        snapshot = Sdf.Layer.CreateAnonymous("material_graph_create_prim_transaction.usda")
        snapshot.TransferContent(edit_layer)
        try:
            return self._run_create_transaction(stage, edit_layer, snapshot)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # This is the transaction boundary: no command exception may leave
            # a partially created scope, prim, shader definition, or UI state.
            logger.warning(
                "create prim transaction failed parent='%s' name='%s' type='%s': %s; "
                "the partial edit-layer changes will be rolled back",
                self._parent_path,
                self._prim_name,
                self._prim_type,
                exc,
            )
            self._rollback_failed_create(edit_layer, snapshot)
            return None

    def undo(self) -> None:
        """Delete the created prim and restore previous selection when possible."""
        if self._prim_path:
            with omni.kit.undo.disabled():
                stage = self._get_stage()
                if stage and stage.GetPrimAtPath(self._prim_path):
                    if stage.RemovePrim(self._prim_path) is False or stage.GetPrimAtPath(self._prim_path):
                        logger.warning(
                            "create-prim undo failed to remove '%s'; the created prim remains in the stage",
                            self._prim_path,
                        )
            if self._select_new_prim and self._selected_prim_paths is not None:
                selection = self._get_context().get_selection()
                current = selection.get_selected_prim_paths()
                if (not current) or str(self._prim_path) in current:
                    selection.set_selected_prim_paths(self._selected_prim_paths, True)
