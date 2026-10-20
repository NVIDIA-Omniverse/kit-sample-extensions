"""Drag-and-drop payload parsing and node creation helpers for graph/catalog targets."""

import json
from typing import Callable, Dict, Optional, Tuple

import omni.ui
from omni.kit.widget.graph import IsolationGraphModel
from pxr import Gf, UsdShade, UsdUI

from ....commands.wrappers.nodes import CreateNode, CreateShader
from ....commands.wrappers.ui_nodes import CreateBackdrop, CreateNodeGraph
from ....config.logging import logger
from ....models.catalog.registries.texture.info import get_texture_info
from ...interaction.menu_utils import show_menu_at_cursor

# pylint: disable=no-member,unnecessary-lambda


class PayloadDropHandler:
    """Handle drops that are JSON payloads."""

    def __init__(
        self,
        widget: object,
        context_manager: object,
        graph_settings_controller: object,
        context_visibility_controller: object,
        create_shader: Optional[Callable[..., object]] = None,
        create_backdrop: Optional[Callable[..., object]] = None,
        create_nodegraph: Optional[Callable[..., object]] = None,
        create_node: Optional[Callable[..., object]] = None,
        texture_drop_fn: Optional[Callable[..., object]] = None,
    ) -> None:
        """Initialize payload drop handling."""
        self._widget = widget
        self._context_manager = context_manager
        self._graph_settings_controller = graph_settings_controller
        self._context_visibility_controller = context_visibility_controller
        self._create_shader = create_shader or (lambda *args, **kwargs: CreateShader(*args, **kwargs))
        self._create_backdrop = create_backdrop or (lambda *args, **kwargs: CreateBackdrop(*args, **kwargs))
        self._create_nodegraph = create_nodegraph or (lambda *args, **kwargs: CreateNodeGraph(*args, **kwargs))
        self._create_node = create_node or (lambda *args, **kwargs: CreateNode(*args, **kwargs))
        self._texture_drop_fn = texture_drop_fn
        self._shader_variant_menu: Optional[omni.ui.Menu] = None

    @staticmethod
    def _unpack_drop_settings(settings: object) -> Tuple[Optional[object], Optional[object]]:
        """Return (position_key, visibility) from a settings response."""
        if isinstance(settings, tuple) and len(settings) == 2:
            return settings
        if isinstance(settings, list) and len(settings) == 2:
            return settings[0], settings[1]
        return None, None

    @staticmethod
    def _get_model_stage(model: object) -> Optional[object]:
        """Return the graph root's owning stage when the model exposes one."""
        prim = getattr(model, "prim", None)
        get_stage = getattr(prim, "GetStage", None)
        return get_stage() if callable(get_stage) else None

    def can_accept(self, drop_data: str) -> bool:
        """Return True if the JSON payload is supported."""
        if not self._widget or not self._widget.graph_view or not self._widget.graph_view.model:
            return False

        json_data = self._parse_payload(drop_data)
        if not json_data:
            logger.warning(
                "drop rejected: invalid JSON payload context=%s",
                self._widget.current_context,
            )
            return False

        item_type = json_data.get("type", None)
        if not item_type:
            logger.warning(
                "drop rejected: missing type context=%s",
                self._widget.current_context,
            )
            return False

        if item_type in [
            UsdUI.Tokens.Backdrop,
            UsdShade.Tokens.NodeGraph,
            IsolationGraphModel.InputNode.get_type_name(),
            IsolationGraphModel.OutputNode.get_type_name(),
            "ImportNodeGraph",
        ]:
            return True

        if item_type == "Texture":
            source = json_data.get("source")
            info = get_texture_info(source) if source else None
            return bool(info and info[0] and self._texture_drop_fn)

        if item_type == UsdShade.Tokens.Shader and json_data.get("context", None) != self._widget.current_context:
            return False

        return item_type in [UsdShade.Tokens.Shader]

    def _show_payload_error(self, message: str) -> bool:
        """Log and show payload processing errors on the widget."""
        logger.warning("%s context=%s", message, self._widget.current_context)
        self._widget.show_error(message, log_message=False)
        return True

    def _finish_creation(self, model: object, result: object, operation: str) -> bool:
        """Finalize a drop only when its command produced a valid created prim."""
        if not result or not getattr(result, "success", False) or not getattr(result, "payload", None):
            detail = getattr(result, "message", None) if result else None
            message = f"{operation} failed"
            if detail:
                message = f"{message}: {detail}"
            return self._show_payload_error(message)
        self._sync_graph_selection_to_created_prim(model, result)
        self._widget.clear_error()
        return True

    def _resolve_drop_position(self, event: omni.ui.WidgetMouseDropEvent) -> Gf.Vec2f:
        """Resolve drop position in canvas coordinates."""
        graph_view = self._widget.graph_view
        if event.x is None and event.y is None:
            event.x = graph_view.screen_position_x + graph_view.computed_width / 2
            event.y = graph_view.screen_position_y + graph_view.computed_height / 2
        return Gf.Vec2f(graph_view.screen_to_canvas(event.x, event.y))

    @staticmethod
    def _sync_graph_selection_to_created_prim(model: object, command_result: object) -> None:
        """Best-effort graph selection sync to the newly created prim."""
        if not command_result or not command_result.success:
            return
        created_prim = command_result.payload
        if not created_prim:
            return

        item_model = model.get_item_model(created_prim.GetPath())
        if item_model:
            model.selection = [item_model]

    def _create_shader_from_payload(self, json_data: Dict[str, object], model: object, position: Gf.Vec2f) -> bool:
        """Create shader node for a resolved shader payload."""
        identifier = json_data.get("identifier")
        if not identifier:
            return self._show_payload_error("drop ignored: missing identifier")
        if json_data.get("context", None) != self._widget.current_context:
            payload_context = json_data.get("context", None)
            logger.warning(
                "drop ignored: context mismatch context=%s payload_context=%s identifier=%s",
                self._widget.current_context,
                payload_context,
                identifier,
            )
            self._widget.show_error(
                f"shader '{identifier}' belongs to context '{payload_context}', but the active context is "
                f"'{self._widget.current_context}'; switch contexts or choose a compatible shader",
                log_message=False,
            )
            return True
        sdr_node = self._context_manager.get_node(self._widget.current_context, identifier)
        if not sdr_node:
            return self._show_payload_error(f"drop failed: shader definition not found ({identifier})")
        creation_data = dict(json_data)
        creation_data["stage"] = self._get_model_stage(model)
        result = self._create_shader(model.prim_path, sdr_node, position, **creation_data)
        return self._finish_creation(model, result, "shader creation")

    def _show_shader_variant_menu(
        self,
        json_data: Dict[str, object],
        model: object,
        position: Gf.Vec2f,
        event: omni.ui.WidgetMouseDropEvent,
    ) -> bool:
        """Show variant chooser menu and create shader from selected variant."""
        variants = json_data.get("variant_subidentifiers", None)
        if not isinstance(variants, list) or len(variants) <= 1:
            return self._create_shader_from_payload(json_data, model, position)

        variant_identifiers = json_data.get("variant_identifiers", {})
        variant_output_types = json_data.get("variant_output_types", {})
        if self._shader_variant_menu:
            self._shader_variant_menu.hide()
        menu = omni.ui.Menu("Node variant")
        self._shader_variant_menu = menu

        with menu:
            for variant in variants:
                subidentifier = str(variant)
                output_suffix = (
                    variant_output_types.get(subidentifier, "") if isinstance(variant_output_types, dict) else ""
                )
                label = f"{subidentifier} {output_suffix}".strip() if output_suffix else subidentifier

                def _select(selected_variant: str = subidentifier) -> None:
                    selected_payload = dict(json_data)
                    selected_payload["subidentifier"] = selected_variant
                    if isinstance(variant_identifiers, dict):
                        selected_identifier = variant_identifiers.get(selected_variant)
                        if selected_identifier:
                            selected_payload["identifier"] = selected_identifier
                    selected_payload["requires_variant_selection"] = False
                    self._create_shader_from_payload(selected_payload, model, position)

                omni.ui.MenuItem(label, triggered_fn=_select)

        show_menu_at_cursor(menu, (event.x or 0, event.y or 0))
        return True

    def _handle_shader_drop(
        self, json_data: Dict[str, object], model: object, position: Gf.Vec2f, event: omni.ui.WidgetMouseDropEvent
    ) -> bool:
        """Handle shader payload drops."""
        requires_variant_selection = bool(json_data.get("requires_variant_selection", False))
        variants = json_data.get("variant_subidentifiers", None)
        if requires_variant_selection and isinstance(variants, list) and len(variants) > 1:
            return self._show_shader_variant_menu(json_data, model, position, event)
        return self._create_shader_from_payload(json_data, model, position)

    def _handle_texture_drop(self, json_data: Dict[str, object], event: omni.ui.WidgetMouseDropEvent) -> bool:
        """Handle texture payload drops."""
        source = json_data.get("source")
        if not source:
            return self._show_payload_error("drop ignored: missing texture source")
        if self._texture_drop_fn:
            self._texture_drop_fn(source, event)
        return True

    def _handle_backdrop_drop(self, model: object, position: Gf.Vec2f) -> bool:
        """Handle backdrop payload drops."""
        settings = (
            self._graph_settings_controller.get_backdrop_drop_settings() if self._graph_settings_controller else None
        )
        position_key, visibility = self._unpack_drop_settings(settings)
        result = self._create_backdrop(
            model.prim_path,
            position,
            position_key,
            visibility,
            stage=self._get_model_stage(model),
        )
        return self._finish_creation(model, result, "backdrop creation")

    def _handle_import_nodegraph_drop(self, json_data: Dict[str, object], model: object, position: Gf.Vec2f) -> bool:
        """Handle import-nodegraph payload drops."""
        source_asset = json_data.get("source_asset")
        identifier = json_data.get("identifier")
        prim_name = json_data.get("name")
        if not source_asset or not identifier:
            logger.warning(
                "drop ignored: missing compound source context=%s identifier=%s",
                self._widget.current_context,
                identifier,
            )
            self._widget.show_error(
                f"compound drop is missing {'source asset' if not source_asset else 'identifier'}; "
                "refresh the catalog entry and try again",
                log_message=False,
            )
            return True
        result = self._create_node(
            model.prim_path,
            "ImportNodeGraph",
            identifier,
            source_asset,
            position=position,
            prim_name=prim_name,
            context_name=self._widget.current_context if self._widget else None,
            stage=self._get_model_stage(model),
        )
        return self._finish_creation(model, result, "compound import")

    def _handle_nodegraph_drop(self, model: object, position: Gf.Vec2f) -> bool:
        """Handle nodegraph payload drops."""
        settings = (
            self._graph_settings_controller.get_nodegraph_drop_settings() if self._graph_settings_controller else None
        )
        position_key, visibility = self._unpack_drop_settings(settings)
        result = self._create_nodegraph(
            model.prim_path,
            position,
            position_key,
            visibility,
            stage=self._get_model_stage(model),
        )
        return self._finish_creation(model, result, "nodegraph creation")

    def _handle_isolation_node_drop(self, item_type: str, position: Gf.Vec2f) -> bool:
        """Handle input/output isolation node payload drops."""
        isolation_model = self._widget.isolation_model
        if item_type == IsolationGraphModel.InputNode.get_type_name():
            isolation_model.add_input_or_output(position, True)
            return True
        if item_type == IsolationGraphModel.OutputNode.get_type_name():
            isolation_model.add_input_or_output(position, False)
            return True
        return False

    def handle_drop(self, drop_data: str, event: omni.ui.WidgetMouseDropEvent) -> bool:
        """Handle a JSON payload drop and return True if consumed."""
        if not self._widget or not self._widget.graph_view:
            return False

        position = self._resolve_drop_position(event)
        json_data = self._parse_payload(drop_data)
        if not json_data:
            return self._show_payload_error("drop ignored: invalid JSON payload")

        item_type = json_data.get("type", None)
        if not item_type:
            return self._show_payload_error("drop ignored: missing type")

        isolation_model = self._widget.isolation_model
        model = isolation_model.root if isolation_model else None
        if not model:
            self._widget.show_error(
                "drop ignored: no material graph is loaded; open or create a material and try again"
            )
            return True

        if item_type == UsdShade.Tokens.Shader:
            return self._handle_shader_drop(json_data, model, position, event)

        if item_type == "Texture":
            return self._handle_texture_drop(json_data, event)

        if item_type == UsdUI.Tokens.Backdrop:
            return self._handle_backdrop_drop(model, position)

        if item_type == "ImportNodeGraph":
            return self._handle_import_nodegraph_drop(json_data, model, position)

        if item_type == UsdShade.Tokens.NodeGraph:
            return self._handle_nodegraph_drop(model, position)

        if self._handle_isolation_node_drop(item_type, position):
            return True

        return False

    def _parse_payload(self, payload: str) -> Optional[Dict[str, object]]:
        """Parse a JSON payload into a dict."""
        try:
            json_data = json.loads(payload)
        except (TypeError, ValueError):
            # Non-JSON payloads are not handled by this handler.
            return None
        if isinstance(json_data, dict):
            return json_data
        return None

    def destroy(self) -> None:
        """Release drop-handler references and callbacks to avoid retaining stale UI state."""
        if self._shader_variant_menu:
            self._shader_variant_menu.hide()
        self._widget = None
        self._context_manager = None
        self._graph_settings_controller = None
        self._context_visibility_controller = None
        self._texture_drop_fn = None
        self._create_shader = None
        self._create_backdrop = None
        self._create_nodegraph = None
        self._create_node = None
        self._shader_variant_menu = None
