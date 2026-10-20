"""Standalone graph canvas view that renders the entire material graph
using a single native C++ GraphCanvasWidget.

This class replaces omni.kit.widget.graph.GraphView entirely — it does NOT
inherit from it.  It owns its own ui.CanvasFrame, model subscription,
index/layout pipeline, and scene push.  No per-node widgets are created.

Plug in via the ``view_type`` parameter of ``GraphEditorCoreWidget``.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import carb
import carb.input
import omni.kit.app
import omni.ui as ui

from ..config.logging import get_logger, log_exception
from ..utils.async_utils import ensure_future_logged
from ..utils.modifiers import clear_active_modifier_flags, set_active_modifier_flags

logger = get_logger()

FLOATING_DELTA = 0.00001


class GraphCanvasView:
    """Drop-in replacement for the per-node-widget GraphView.

    Provides the interface that ``GraphEditorCoreWidget`` expects
    (model, selection, focus_on_nodes, zoom/pan, mouse callbacks, destroy)
    while rendering everything through a single native canvas widget.
    """

    def __init__(self, **kwargs: Any) -> None:
        self._model = None
        kwargs.pop("delegate", None)
        self._port_grouping = kwargs.pop("port_grouping", False)

        kwargs.pop("virtual_ports", None)
        kwargs.pop("draw_curve_top_layer", None)
        kwargs.pop("rectangle_selection", None)
        kwargs.pop("always_force_regenerate", None)
        kwargs.pop("enable_snapping_for_connection", None)

        zoom_min = kwargs.pop("zoom_min", 0.01)
        zoom_max = kwargs.pop("zoom_max", 3.0)
        kwargs.pop("smooth_zoom", None)

        model = kwargs.pop("model", None)

        if "style_type_name_override" not in kwargs:
            kwargs["style_type_name_override"] = "Graph"

        self.__root_frame = ui.CanvasFrame(**kwargs)
        self.__root_frame.zoom_min = zoom_min
        self.__root_frame.zoom_max = zoom_max
        self.__root_stack = None
        self.__root_frame.set_zoom_key_shortcut(1, carb.input.KEYBOARD_MODIFIER_FLAG_ALT)

        self._layout = None
        self._canvas_widget = None
        self._rebuild_kit_sub = None
        self._connection_visual_cb_target = None
        self._skip_deferred_rebuild_once = False
        self._rebuilding = False
        self._selection: List[Any] = []
        self._breadcrumb_path: List[str] = []

        self._model_subscription = None
        self._selection_subscription = None
        self._node_subscription = None

        self._needs_initial_frame = True
        self._initial_frame_retry_count = 0
        self._suppress_focus = False

        # Hit-testing / selection data (populated by _rebuild)
        self._scene_model_nodes: List = []
        self._scene_stable_ids: List[int] = []
        self._scene_pos_x: List[float] = []
        self._scene_pos_y: List[float] = []
        self._scene_widths: List[float] = []
        self._scene_heights: List[float] = []
        self._scene_port_start_y: List[float] = []
        self._scene_port_sides: List[List[Tuple[bool, bool]]] = []
        self._node_to_stable: Dict[Any, int] = {}

        # Marquee state
        self._marquee_start = None
        self._marquee_active = False

        # Node drag state
        self._drag_node = None
        self._drag_start_canvas = None
        self._drag_active = False
        self._drag_threshold = 3.0

        # Connection noodle drag state
        self._noodle_source = None
        self._pending_port_hit = None
        self._pending_port_canvas = None

        # Backdrop tracking + per-node menu flag
        self._scene_is_backdrop: List[bool] = []
        self._scene_has_menu: List[bool] = []
        self._resize_node_index: Optional[int] = None
        self._resize_start_canvas: Optional[Tuple[float, float]] = None
        self._resize_start_size: Optional[Tuple[float, float]] = None
        self._rename_opened_frame = 0
        self._rename_poll_task = None
        self._desc_edit_poll_task = None
        self._port_rename_dialog = None
        self._last_tooltip_node = -1
        self._last_tooltip_port = -1
        self._color_picker_widget = None

        self._event_consumed = False

        self._validation_errors_by_path: dict = {}
        self._fallback_port_map: dict = {}
        self._last_scene = None
        self._position_change_consumer = None

        # InputNode Phase 1 view model
        self._input_node_vm = None
        self._input_node_context_manager = None
        self._input_node_current_context = ""

        # Chained mouse callbacks: we register on the CanvasFrame and chain
        # with any callback the parent (GraphEditorCoreWidget) sets later via
        # set_mouse_pressed_fn etc.
        self._parent_mouse_pressed_fn = None
        self._parent_mouse_released_fn = None
        self._parent_mouse_moved_fn = None
        self._parent_mouse_double_clicked_fn = None

        # Register our combined handler on the CanvasFrame
        self.__root_frame.set_mouse_pressed_fn(self._combined_mouse_pressed)
        self.__root_frame.set_mouse_released_fn(self._combined_mouse_released)
        self.__root_frame.set_mouse_moved_fn(self._combined_mouse_moved)
        self.__root_frame.set_mouse_double_clicked_fn(self._combined_mouse_double_clicked)

        self._edit_poll_task = None
        self._tooltip_task = ensure_future_logged(self._tooltip_loop(), "graph tooltip polling")
        self._deferred_disconnect_task = None
        self._deferred_disconnect_ports = []

        self.set_model(model)

    # ------------------------------------------------------------------
    # Attribute delegation — intercept mouse callback setters so the
    # parent's callbacks chain with ours rather than replacing them.
    # ------------------------------------------------------------------

    def __getattr__(self, attr: str):
        return getattr(self.__root_frame, attr)

    def set_mouse_pressed_fn(self, fn):
        self._parent_mouse_pressed_fn = fn

    def set_mouse_released_fn(self, fn):
        self._parent_mouse_released_fn = fn

    def set_mouse_moved_fn(self, fn):
        self._parent_mouse_moved_fn = fn

    def set_mouse_double_clicked_fn(self, fn):
        self._parent_mouse_double_clicked_fn = fn

    # ------------------------------------------------------------------
    # Combined mouse handlers (our logic + parent chain)
    # ------------------------------------------------------------------

    def _combined_mouse_pressed(self, x, y, button, modifier):
        self._event_consumed = False
        self._on_mouse_pressed(x, y, button, modifier)
        if self._parent_mouse_pressed_fn and not self._event_consumed:
            self._parent_mouse_pressed_fn(x, y, button, modifier)

    def _combined_mouse_released(self, x, y, button, modifier):
        self._on_mouse_released(x, y, button, modifier)
        if self._parent_mouse_released_fn:
            self._parent_mouse_released_fn(x, y, button, modifier)

    def _combined_mouse_moved(self, x, y, modifier, pressed):
        self._on_mouse_moved(x, y, modifier, pressed)
        if self._parent_mouse_moved_fn:
            self._parent_mouse_moved_fn(x, y, modifier, pressed)

    def _combined_mouse_double_clicked(self, x, y, button, modifier):
        self._on_mouse_double_clicked(x, y, button, modifier)
        if self._parent_mouse_double_clicked_fn:
            self._parent_mouse_double_clicked_fn(x, y, button, modifier)

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self.set_model(value)

    def set_model(self, model) -> None:
        old_model = self._model
        self._cancel_deferred_disconnects()
        if old_model:
            self._release_connection_visual_callback()
            self._model_subscription = None
            self._selection_subscription = None
            self._node_subscription = None

        model_changed = old_model is not model
        if model_changed:
            self._clear_scene_state()

        self._model = model
        self._position_change_consumer = self._resolve_position_change_consumer()
        had_nodes = bool(self._scene_model_nodes)
        self._needs_initial_frame = bool(model) and (model_changed or not had_nodes)
        self._initial_frame_retry_count = 0
        self._suppress_focus = bool(model) and not self._needs_initial_frame and had_nodes

        if not model:
            self._on_item_changed(None)
            return

        self._model_subscription = self._model.subscribe_item_changed(self._on_item_changed)
        self._selection_subscription = self._model.subscribe_selection_changed(self._on_selection_changed)
        self._node_subscription = self._model.subscribe_node_changed(
            lambda item=None, **_kw: self._on_item_changed(item)
        )
        self._install_connection_visual_callback()

        self._on_item_changed(None)

    def _clear_scene_state(self) -> None:
        """Clear scene caches so new models cannot inherit stale framing state."""
        self._scene_model_nodes = []
        self._scene_stable_ids = []
        self._scene_pos_x = []
        self._scene_pos_y = []
        self._scene_widths = []
        self._scene_heights = []
        self._scene_port_start_y = []
        self._scene_port_sides = []
        self._node_to_stable = {}
        self._scene_is_backdrop = []
        self._scene_has_menu = []
        self._fallback_port_map = {}
        self._last_scene = None

    def _resolve_nodegraph_for_connection_visual_cb(self):
        """Return the ``NodeGraphModel`` (or compatible) that owns ``notify_connection_changed``.

        ``GraphCanvasView.model`` is often an ``IsolationGraphModel``; the concrete
        ``NodeGraphModel`` lives on ``_model`` / ``_root`` before the isolation shell.
        """
        im = self._model
        if im is None:
            return None
        for model in (
            getattr(im, "_model", None),
            getattr(im, "_root", None),
            im,
        ):
            if model is not None and callable(getattr(model, "set_connection_visual_sync_callback", None)):
                return model
        return None

    def _release_connection_visual_callback(self) -> None:
        target = getattr(self, "_connection_visual_cb_target", None)
        self._connection_visual_cb_target = None
        if target is None:
            return
        setter = getattr(target, "set_connection_visual_sync_callback", None)
        if callable(setter):
            try:
                setter(None)
            except (RuntimeError, ValueError, TypeError, AttributeError):
                pass

    def _install_connection_visual_callback(self) -> None:
        self._release_connection_visual_callback()
        target = self._resolve_nodegraph_for_connection_visual_cb()
        if target is None:
            return
        self._connection_visual_cb_target = target
        target.set_connection_visual_sync_callback(self._sync_rebuild_for_connection_notify)

    def _sync_rebuild_for_connection_notify(self, item: Any) -> None:
        """Native rebuild during ``notify_connection_changed`` (before deferred tick scheduling)."""
        if not self._model:
            return
        if self._rebuilding:
            self._skip_deferred_rebuild_once = False
            if self._rebuild_kit_sub is None:
                self._schedule_rebuild_work()
            return
        self._skip_deferred_rebuild_once = True
        self._rebuild_core()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        if self._model:
            self._model.selection = value

    def _on_selection_changed(self) -> None:
        self._selection = list(self._model.selection or []) if self._model else []
        self._update_scene_selection()

    def _update_scene_selection(self) -> None:
        if not self._canvas_widget or not self._scene_model_nodes:
            return
        for i, model_node in enumerate(self._scene_model_nodes):
            if i < len(self._scene_stable_ids):
                is_sel = model_node in self._selection
                self._canvas_widget.set_node_selected(self._scene_stable_ids[i], is_sel)

    # ------------------------------------------------------------------
    # Breadcrumb proxy (survives canvas widget recreation)
    # ------------------------------------------------------------------

    def set_breadcrumb(self, path: list) -> None:
        self._breadcrumb_path = list(path)
        if self._canvas_widget:
            try:
                self._canvas_widget.set_breadcrumb(self._breadcrumb_path)
            except Exception:
                pass

    @property
    def breadcrumb_clicked_index(self) -> int:
        if self._canvas_widget:
            try:
                return self._canvas_widget.breadcrumb_clicked_index
            except Exception:
                pass
        return -1

    def clear_breadcrumb_clicked(self) -> None:
        if self._canvas_widget:
            try:
                self._canvas_widget.clear_breadcrumb_clicked()
            except Exception:
                pass

    @property
    def breadcrumb_hovered(self) -> bool:
        if self._canvas_widget:
            try:
                return self._canvas_widget.breadcrumb_hovered
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------
    # Persistent edit result polling (rename + description)
    # ------------------------------------------------------------------

    def _start_edit_poll(self) -> None:
        """Start polling for edit results only if C++ has an active edit."""
        if self._edit_poll_task and not self._edit_poll_task.done():
            return
        if not self._canvas_widget:
            return
        try:
            if not (self._canvas_widget.is_renaming or self._canvas_widget.is_desc_editing):
                return
        except Exception:
            return
        self._edit_poll_task = ensure_future_logged(self._poll_edit_results(), "graph edit polling")

    async def _poll_edit_results(self) -> None:
        """Poll C++ for rename/description edit results until no edit is active."""
        app = omni.kit.app.get_app()
        while self._canvas_widget and self._model:
            await app.next_update_async()
            if not self._canvas_widget or not self._model:
                break
            has_any = False
            try:
                if self._canvas_widget.has_rename_result():
                    stable_id, new_name = self._canvas_widget.consume_rename_result()
                    if new_name:
                        for i, mn in enumerate(self._scene_model_nodes):
                            if i < len(self._scene_stable_ids) and self._scene_stable_ids[i] == stable_id:
                                if self._commit_node_name(mn, new_name):
                                    self._model._item_changed(None)
                                break
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "graph-canvas rename result processing failed: %s; the pending rename was not applied",
                    exc,
                )
            try:
                if self._canvas_widget.has_desc_edit_result():
                    stable_id, new_desc = self._canvas_widget.consume_desc_edit_result()
                    for i, mn in enumerate(self._scene_model_nodes):
                        if i < len(self._scene_stable_ids) and self._scene_stable_ids[i] == stable_id:
                            if self._commit_node_description(mn, new_desc):
                                self._model._item_changed(None)
                            break
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "graph-canvas description result processing failed: %s; the pending description was not applied",
                    exc,
                )
            try:
                has_any = self._canvas_widget.is_renaming or self._canvas_widget.is_desc_editing
            except Exception:
                pass
            if not has_any:
                break

    def _commit_node_name(self, model_node: object, value: str) -> bool:
        """Commit a node rename and preserve a model-provided failure result."""
        item = self._model[model_node]
        setter = getattr(item, "set_name", None)
        if callable(setter):
            success = setter(value) is not False
        else:
            item.name = value
            success = True
        if not success:
            logger.warning("node rename was rejected for %s", getattr(item, "path", model_node))
        return success

    def _commit_node_description(self, model_node: object, value: str) -> bool:
        """Commit a node description and preserve a model-provided failure result."""
        item = self._model[model_node]
        setter = getattr(item, "set_description", None)
        if callable(setter):
            success = setter(value) is not False
        else:
            item.description = value
            success = True
        if not success:
            logger.warning("node description edit was rejected for %s", getattr(item, "path", model_node))
        return success

    def _set_port_inputs(self, model_port: object, value: list) -> bool:
        """Set port inputs while preserving an explicit connection result when available."""
        item = self._model[model_port]
        setter = getattr(item, "set_inputs", None)
        if callable(setter):
            return setter(value) is not False
        item.inputs = value
        return True

    # ------------------------------------------------------------------
    # Screen-to-canvas coordinate conversion
    # ------------------------------------------------------------------

    def _screen_to_canvas(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        return (
            self.__root_frame.screen_to_canvas_x(screen_x),
            self.__root_frame.screen_to_canvas_y(screen_y),
        )

    # ------------------------------------------------------------------
    # Hit testing in canvas coordinates
    # ------------------------------------------------------------------

    _HEADER_ACTUAL = 24.0
    _BODY_INSET = 8.0
    _BODY_INSET_NO_OUT = 16.0
    _HEADER_H = _HEADER_ACTUAL + _BODY_INSET  # default for nodes with outputs
    _PORT_H = 22.0
    _PORT_MARGIN = 8.0
    _PORT_HIT_W = 30.0
    _PORT_PIN_HIT_RADIUS = 7.0
    _INITIAL_FRAME_MAX_RETRIES = 5

    _RESIZE_HANDLE_SZ = 16.0

    def _port_start_y_for(self, node_index: int) -> float:
        if node_index < len(self._scene_port_start_y):
            return self._scene_port_start_y[node_index]
        return self._HEADER_H

    def _find_node_at(self, canvas_x: float, canvas_y: float, return_index: bool = False) -> Optional[Any]:
        # Regular nodes first (they are on top of backdrops)
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i < len(self._scene_is_backdrop) and self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]
            if px <= canvas_x <= px + pw and py <= canvas_y <= py + ph:
                return (self._scene_model_nodes[i], i) if return_index else self._scene_model_nodes[i]
        # Then backdrops (behind regular nodes)
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i >= len(self._scene_is_backdrop) or not self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]
            if px <= canvas_x <= px + pw and py <= canvas_y <= py + ph:
                return (self._scene_model_nodes[i], i) if return_index else self._scene_model_nodes[i]
        return None

    def _find_node_index_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return scene node index for a canvas point, or None."""
        result = self._find_node_at(canvas_x, canvas_y, return_index=True)
        if result is None:
            return None
        if not isinstance(result, tuple):
            for index, scene_node in enumerate(self._scene_model_nodes):
                if scene_node is result:
                    return index
            return None
        _node, index = result
        return index

    def _find_backdrop_resize_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return node index if click is on a backdrop resize handle, or None."""
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i >= len(self._scene_is_backdrop) or not self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]
            handle_x = px + pw - self._RESIZE_HANDLE_SZ
            handle_y = py + ph - self._RESIZE_HANDLE_SZ
            if canvas_x >= handle_x and canvas_y >= handle_y and canvas_x <= px + pw and canvas_y <= py + ph:
                return i
        return None

    def _find_backdrop_color_swatch_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return node index if click is on a backdrop color swatch, or None."""
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i >= len(self._scene_is_backdrop) or not self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            swatch_sz = 14.0
            swatch_x = px + (self._HEADER_H - swatch_sz) * 0.5 + 2.0
            swatch_y = py + (self._HEADER_H - swatch_sz) * 0.5
            if swatch_x <= canvas_x <= swatch_x + swatch_sz and swatch_y <= canvas_y <= swatch_y + swatch_sz:
                return i
        return None

    def _find_backdrop_body_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return node index if click is on a backdrop body (below header), or None."""
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i >= len(self._scene_is_backdrop) or not self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]
            if px <= canvas_x <= px + pw and py + self._HEADER_ACTUAL <= canvas_y <= py + ph:
                return i
        return None

    def _find_port_at(self, canvas_x: float, canvas_y: float):
        """Return (node_index, port_index, is_input) or None."""
        _R = 5.0
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i < len(self._scene_is_backdrop) and self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]
            if not (px - _R <= canvas_x <= px + pw + _R and py <= canvas_y <= py + ph):
                continue
            psy = self._port_start_y_for(i)
            rel_y = canvas_y - py - psy
            if rel_y < 0:
                return None

            if self._is_input_node(i):
                port_idx = self._input_node_port_idx_at(i, canvas_y)
            else:
                port_idx = int(rel_y / self._PORT_H)
                n_ports = int((ph - psy - 4.0) / self._PORT_H)
                if port_idx < 0 or port_idx >= n_ports:
                    return None

            if port_idx < 0:
                return None
            rel_x = canvas_x - px
            model_port = self._get_model_port(i, port_idx)
            has_left_input, has_right_output = self._port_hit_sides_at(i, port_idx, model_port)
            if has_left_input and rel_x < self._PORT_HIT_W:
                return (i, port_idx, True)
            if has_right_output and rel_x > pw - self._PORT_HIT_W:
                return (i, port_idx, False)
            return None
        return None

    def _find_group_icon_at(self, canvas_x: float, canvas_y: float) -> Optional[Tuple[int, int]]:
        """Return (node_index, port_index) if click is on a group +/- icon, else None."""
        _ICON_HIT = 6.0
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i < len(self._scene_is_backdrop) and self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]

            is_in = self._is_input_node(i)

            # For InputNode, accept clicks anywhere in the left half of the
            # node body (the +/- icon is rendered inside at x+6).
            # For normal nodes, check only near the left edge.
            if is_in:
                if not (px - 4.0 <= canvas_x <= px + pw * 0.5):
                    continue
            else:
                if abs(canvas_x - px) > _ICON_HIT:
                    continue

            psy = self._port_start_y_for(i)
            if not (py + psy - 2.0 <= canvas_y <= py + ph + 2.0):
                continue

            # Compute port index
            if is_in:
                port_idx = self._input_node_port_idx_at(i, canvas_y)
            else:
                rel_y = canvas_y - py - psy
                port_idx = int(rel_y / self._PORT_H)
                n_ports = int((ph - psy - 4.0) / self._PORT_H)
                if port_idx < 0 or port_idx >= n_ports:
                    continue

            if port_idx < 0:
                continue
            if not self._is_group_port(i, port_idx):
                continue
            return (i, port_idx)
        return None

    def _resolve_port(self, node_index: int, port_index: int):
        """Resolve a port object from node/port indices.

        For InputNode, uses the scene-index-to-port map (Phase 4) which
        correctly handles filtered/reordered port lists.  For normal
        nodes, falls back to the model-tree walk via _get_model_port.
        For invalid nodes with fallback ports, uses _fallback_port_map.
        """
        if self._is_input_node(node_index) and self._input_node_vm is not None:
            port_map = getattr(self._input_node_vm, "_scene_idx_to_port", {})
            port = port_map.get(port_index)
            if port is not None:
                return port
        result = self._get_model_port(node_index, port_index)
        if result is not None:
            return result
        return self._fallback_port_map.get((node_index, port_index))

    def _is_input_node(self, node_index: int) -> bool:
        """Return True if the node at the given index is an InputNode."""
        if node_index >= len(self._scene_model_nodes):
            return False
        mn = self._scene_model_nodes[node_index]
        try:
            return type(mn).get_type_name() == "InputNode"
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return False

    def _is_output_node(self, node_index: int) -> bool:
        """Return True if the node at the given index is an OutputNode."""
        if node_index >= len(self._scene_model_nodes):
            return False
        mn = self._scene_model_nodes[node_index]
        try:
            return type(mn).get_type_name() == "OutputNode"
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return False

    def _port_hit_sides_at(self, node_index: int, port_index: int, model_port) -> Tuple[bool, bool]:
        """Return ``(has_left_input, has_right_output)`` for a visible port row."""
        # IO wrapper nodes use inverted connection semantics in the isolation
        # model snapshot.  Determine their sides from node type directly so the
        # ``_scene_port_sides`` cache (which reflects the inverted data) cannot
        # override them.
        if self._is_input_node(node_index):
            return True, True
        if self._is_output_node(node_index) or self._is_material_output_sink_port(model_port):
            return True, False

        scene_port_sides = self.__dict__.get("_scene_port_sides", [])
        if node_index < len(scene_port_sides):
            node_sides = scene_port_sides[node_index]
            if port_index < len(node_sides):
                has_left_input, has_right_output = node_sides[port_index]
                if has_left_input or has_right_output:
                    return has_left_input, has_right_output

        has_left_input = False
        has_right_output = False
        if model_port is not None and self._model is not None:
            try:
                proxy = self._model[model_port]
                has_left_input = getattr(proxy, "inputs", None) is not None
                has_right_output = getattr(proxy, "outputs", None) is not None
            except (RuntimeError, ValueError, TypeError, AttributeError, KeyError):
                pass

        if has_left_input or has_right_output:
            return has_left_input, has_right_output

        proxy_attr = getattr(model_port, "proxy_attribute", None)
        port_name = str(getattr(proxy_attr, "name", ""))
        if port_name.startswith("inputs:"):
            return True, False
        if port_name.startswith("outputs:"):
            return False, True

        return False, False

    def _input_node_port_idx_at(self, node_index: int, canvas_y: float) -> int:
        """Map a canvas Y coordinate to a port index using InputNode variable heights."""
        py = self._scene_pos_y[node_index]
        psy = self._port_start_y_for(node_index)
        rel_y = canvas_y - py - psy
        if rel_y < 0:
            return -1
        vm = self._input_node_vm
        if vm is None:
            return int(rel_y / 16.0)
        group_set = getattr(vm, "_scene_group_indices", set())
        synth_set = set(getattr(vm, "_synthetic_row_indices", {}).values())
        tall_rows = group_set | synth_set
        accum = 0.0
        ph = self._scene_heights[node_index]
        max_ports = int((ph - psy) / 14.0) + 2
        for pi in range(max_ports):
            h = 18.0 if pi in tall_rows else 16.0
            if accum + h > rel_y:
                return pi
            accum += h
        return -1

    def _find_port_hit_at_canvas(self, canvas_x: float, canvas_y: float):
        """Return a port hit, including InputNode/OutputNode label/body rows."""
        port_hit = self._find_port_at(canvas_x, canvas_y)
        if port_hit is not None:
            return port_hit

        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i < len(self._scene_is_backdrop) and self._scene_is_backdrop[i]:
                continue
            try:
                node_type = type(self._scene_model_nodes[i]).get_type_name()
            except Exception:
                node_type = ""
            npx = self._scene_pos_x[i]
            npy = self._scene_pos_y[i]
            npw = self._scene_widths[i]
            nph = self._scene_heights[i]
            if not (npx <= canvas_x <= npx + npw and npy <= canvas_y <= npy + nph):
                continue
            if node_type not in {"InputNode", "OutputNode"}:
                return None
            if canvas_y < npy + self._HEADER_ACTUAL:
                return None
            if node_type == "InputNode":
                pidx = self._input_node_port_idx_at(i, canvas_y)
            else:
                rel_y = canvas_y - npy - self._port_start_y_for(i)
                if rel_y < 0:
                    pidx = -1
                else:
                    pidx = int(rel_y / self._PORT_H)
                    max_ports = int((nph - self._port_start_y_for(i) - 4.0) / self._PORT_H)
                    if pidx < 0 or pidx >= max_ports:
                        pidx = -1
            if pidx >= 0:
                model_port = self._get_model_port(i, pidx)
                has_left_input, has_right_output = self._port_hit_sides_at(i, pidx, model_port)
                if node_type == "OutputNode" and has_left_input:
                    return (i, pidx, True)
                if node_type == "InputNode" and has_right_output:
                    return (i, pidx, False)
                if has_left_input:
                    return (i, pidx, True)
                if has_right_output:
                    return (i, pidx, False)
            return None
        return None

    def _find_port_pin_at_canvas(self, canvas_x: float, canvas_y: float):
        """Return a port hit only when the pointer is close to the visible pin."""
        port_hit = self._find_port_at(canvas_x, canvas_y)
        if port_hit is None:
            return None
        ni, pi, is_input = port_hit
        port_x, port_y = self._port_canvas_pos(ni, pi, is_input)
        dx = canvas_x - port_x
        dy = canvas_y - port_y
        hit_radius = self._PORT_PIN_HIT_RADIUS
        if dx * dx + dy * dy <= hit_radius * hit_radius:
            return port_hit
        return None

    _ICON_SZ = 38.0

    def _find_header_name_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return node index if click is on the header name text area."""
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i < len(self._scene_is_backdrop) and self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            name_x0 = px + self._ICON_SZ + 4.0
            name_x1 = px + pw - 20.0
            name_y0 = py
            name_y1 = py + self._HEADER_H
            if name_x0 <= canvas_x <= name_x1 and name_y0 <= canvas_y <= name_y1:
                return i
        return None

    def is_point_over_header(self, item: Any) -> bool:
        """Return True if the current mouse position is over the header of the given node."""
        current_frame = omni.kit.app.get_app().get_update_number()
        if current_frame - self._rename_opened_frame <= 1:
            return True

        try:
            import carb.input

            input_iface = carb.input.acquire_input_interface()
            mouse = input_iface.get_mouse()
            mouse_pos = input_iface.get_mouse_coords_pixel(mouse)
            sx, sy = float(mouse_pos[0]), float(mouse_pos[1])
        except Exception:
            return False

        cx, cy = self._screen_to_canvas(sx, sy)
        for i, mn in enumerate(self._scene_model_nodes):
            if mn is not item:
                continue
            if i < len(self._scene_is_backdrop) and self._scene_is_backdrop[i]:
                return False
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            if px <= cx <= px + pw and py <= cy <= py + self._HEADER_ACTUAL:
                return True
            return False
        return False

    def _find_expansion_icon_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return node index if click is on the expansion chevron."""
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i < len(self._scene_is_backdrop) and self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            has_menu = i < len(self._scene_has_menu) and self._scene_has_menu[i]
            if has_menu:
                chev_x0 = px + pw - 40.0
                chev_x1 = px + pw - 20.0
            else:
                chev_x0 = px + pw - 24.0
                chev_x1 = px + pw
            chev_y0 = py
            chev_y1 = py + self._HEADER_H
            if chev_x0 <= canvas_x <= chev_x1 and chev_y0 <= canvas_y <= chev_y1:
                return i
        return None

    def _find_node_menu_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return node index if click is on the '...' menu area (far right of header)."""
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i >= len(self._scene_has_menu) or not self._scene_has_menu[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]
            menu_x0 = px + pw - 20.0
            menu_y0 = py
            menu_y1 = py + min(self._HEADER_ACTUAL, ph)
            if menu_x0 <= canvas_x <= px + pw and menu_y0 <= canvas_y <= menu_y1:
                return i
        return None

    def _show_node_context_menu(self, node_index: int) -> None:
        """Show the registered context menu for a node."""
        if not self._model or node_index >= len(self._scene_model_nodes):
            return
        mn = self._scene_model_nodes[node_index]
        try:
            from pxr import Sdf, UsdShade, UsdUI

            from ..api.context_menu import get_node_menu_items
            from .interaction.menu_utils import show_menu_at_cursor

            inner = self._model[mn]
            node_type = str(inner.type or "")
            prim = getattr(mn, "prim", None)
            prim_path = prim.GetPath() if prim else Sdf.Path()

            items = get_node_menu_items(node_type)
            resolved_type = node_type
            if not items and prim:
                if prim.IsA(UsdShade.NodeGraph) or prim.IsA(UsdShade.Material):
                    resolved_type = "NodeGraph"
                    items = get_node_menu_items("NodeGraph")
                elif prim.IsA(UsdUI.Backdrop):
                    resolved_type = "Backdrop"
                    items = get_node_menu_items("Backdrop")

            if not items:
                return

            from functools import partial

            self._node_context_menu = ui.Menu("Node Context Menu")
            with self._node_context_menu:
                for item in items:
                    ui.MenuItem(
                        item.label,
                        triggered_fn=partial(
                            self._safe_node_menu_callback,
                            item.callback,
                            resolved_type,
                            prim_path,
                        ),
                    )
            show_menu_at_cursor(self._node_context_menu)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(logger, "node context menu build failed", action="node_context_menu", exc=exc)

    @staticmethod
    def _safe_node_menu_callback(callback, node_type, prim_path) -> None:
        try:
            callback(node_type, prim_path)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "node context menu callback failed",
                prim_path=str(prim_path),
                action=str(node_type),
                exc=exc,
            )

    def _show_io_node_context_menu(self, node_index: int) -> None:
        """Show actions for InputNode/OutputNode wrappers."""
        if not self._model or node_index >= len(self._scene_model_nodes):
            return
        if getattr(self, "_io_node_context_menu", None) is not None:
            self._io_node_context_menu.hide()
        self._io_node_context_menu = ui.Menu("IO Node Context Menu")
        node = self._scene_model_nodes[node_index]
        with self._io_node_context_menu:
            ui.MenuItem("Remove", triggered_fn=lambda n=node: self._remove_io_node(n))
        from .interaction.menu_utils import show_menu_at_cursor

        show_menu_at_cursor(self._io_node_context_menu)

    def _remove_io_node(self, node: object) -> None:
        """Remove an InputNode/OutputNode wrapper through the undoable isolation command."""
        if not self._model:
            return
        from ..commands.wrappers.isolation import DeleteInputOutputNodes

        graph_model = getattr(self._model, "_model", None)
        result = DeleteInputOutputNodes(self._model, [node], graph_model)
        if not result.success:
            logger.warning(
                "failed to remove graph IO node '%s': %s; the node was not removed",
                getattr(node, "path", getattr(node, "name", "<unknown>")),
                result.error_code or result.message or "command returned no reason",
            )

    def _toggle_expansion_state(self, node_index: int) -> None:
        """Cycle the node's expansion state: OPEN -> MINIMIZED -> CLOSED -> OPEN."""
        if not self._model or node_index >= len(self._scene_model_nodes):
            return
        mn = self._scene_model_nodes[node_index]
        try:
            from omni.kit.widget.graph.graph_model import GraphModel

            current = self._model[mn].expansion_state
            if not isinstance(current, int):
                current = current.value
            next_val = (current + 1) % 3
            self._model[mn].expansion_state = GraphModel.ExpansionState(next_val)
            self._model._item_changed(None)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "node expansion update failed",
                prim_path=str(getattr(mn, "path", "")),
                action="toggle_expansion",
                exc=exc,
            )

    def _get_model_port(self, node_index: int, port_index: int):
        """Return the model port object at the given VISIBLE (flattened) index.

        The scene port list is flattened: top-level ports + expanded group
        children interleaved.  This must match NativeBuildScene's traversal.
        """
        if node_index < 0 or node_index >= len(self._scene_model_nodes):
            return None
        try:
            from omni.kit.widget.graph.graph_model import GraphModel

            model_node = self._scene_model_nodes[node_index]
            root_ports = self._model[model_node].ports
            if not root_ports:
                return None

            flat_idx = [0]

            def _find(port_list):
                for port in port_list:
                    if flat_idx[0] == port_index:
                        return port
                    flat_idx[0] += 1
                    pp = self._model[port]
                    sub = pp.ports
                    if sub is not None and len(sub) > 0:
                        exp = pp.expansion_state
                        if exp == GraphModel.ExpansionState.OPEN:
                            result = _find(sub)
                            if result is not None:
                                return result
                return None

            return _find(root_ports)
        except Exception:
            pass
        return None

    def _is_group_port(self, node_index: int, port_index: int) -> bool:
        """Check if the port at the given index is a group port."""
        model_port = self._get_model_port(node_index, port_index)
        if model_port is None:
            # Synthetic group header (port=None) on an InputNode is always a group
            if self._is_input_node(node_index):
                return True
            return False
        if model_port and self._model:
            try:
                sub = self._model[model_port].ports
                return sub is not None and len(sub) > 0
            except Exception:
                pass
        return False

    def _toggle_group_expansion(self, node_index: int, port_index: int) -> None:
        """Toggle a group port between OPEN and CLOSED."""
        model_port = self._get_model_port(node_index, port_index)
        if not model_port or not self._model:
            return
        try:
            from omni.kit.widget.graph.graph_model import GraphModel

            proxy = self._model[model_port]
            current = proxy.expansion_state
            if current == GraphModel.ExpansionState.OPEN:
                next_state = GraphModel.ExpansionState.CLOSED
            else:
                next_state = GraphModel.ExpansionState.OPEN
            # Try multiple approaches to set expansion state
            try:
                proxy.expansion_state = next_state
            except (AttributeError, TypeError):
                try:
                    # Direct attribute on the port object
                    model_port.expansion_state = next_state
                except (AttributeError, TypeError):
                    try:
                        # Through the model's set method
                        self._model.set_expansion_state(model_port, next_state)
                    except (AttributeError, TypeError):
                        return

            self._model._item_changed(None)
        except Exception:
            pass

    def _port_canvas_pos(self, node_index: int, port_index: int, is_input: bool) -> Tuple[float, float]:
        """Return the canvas-space center of a port circle (at node edge)."""
        px = self._scene_pos_x[node_index]
        py = self._scene_pos_y[node_index]
        pw = self._scene_widths[node_index]
        psy = self._port_start_y_for(node_index)

        if self._is_input_node(node_index) and self._input_node_vm is not None:
            group_set = getattr(self._input_node_vm, "_scene_group_indices", set())
            synth_set = set(getattr(self._input_node_vm, "_synthetic_row_indices", {}).values())
            tall_rows = group_set | synth_set
            accum = 0.0
            for pi in range(port_index):
                accum += 18.0 if pi in tall_rows else 16.0
            cur_h = 18.0 if port_index in tall_rows else 16.0
            cy = py + psy + accum + cur_h * 0.5
        else:
            cy = py + psy + port_index * self._PORT_H + self._PORT_H * 0.5

        if is_input:
            return (px, cy)
        return (px + pw, cy)

    def _find_nodes_in_rect(self, x0: float, y0: float, x1: float, y1: float) -> List[Any]:
        rx_min, rx_max = min(x0, x1), max(x0, x1)
        ry_min, ry_max = min(y0, y1), max(y0, y1)
        result = []
        for i, model_node in enumerate(self._scene_model_nodes):
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            ph = self._scene_heights[i]
            if not (px + pw < rx_min or px > rx_max or py + ph < ry_min or py > ry_max):
                result.append(model_node)
        return result

    # ------------------------------------------------------------------
    # Mouse event handlers (selection + marquee + node drag + noodle)
    # ------------------------------------------------------------------

    def _on_mouse_pressed(self, x: float, y: float, button: int, modifier: int) -> None:
        if self._color_picker_widget:
            self._commit_color_picker()
            return

        # ---- Right-click: port context menu ----
        if button == 1:
            cx, cy = self._screen_to_canvas(x, y)
            port_hit = self._find_port_hit_at_canvas(cx, cy)
            if port_hit is not None:
                ni, pi, is_input = port_hit
                model_port = self._resolve_port(ni, pi)
                if model_port:
                    self._show_port_context_menu(model_port)
                    self._event_consumed = True
            else:
                node_idx = self._find_node_index_at(cx, cy)
                if node_idx is not None and self._is_io_node(node_idx):
                    self._show_io_node_context_menu(node_idx)
                    self._event_consumed = True
            return

        if button != 0:
            return

        cx, cy = self._screen_to_canvas(x, y)

        self._drag_node = None
        self._drag_active = False
        self._drag_start_canvas = None
        self._noodle_source = None
        self._pending_port_hit = None
        self._pending_port_canvas = None
        self._noodle_rewire = False
        self._noodle_rewire_port = None
        self._noodle_rewire_old_source = None
        self._resize_node_index = None
        self._resize_start_canvas = None
        self._resize_start_size = None

        # ---- Check backdrop resize handle ----
        resize_idx = self._find_backdrop_resize_at(cx, cy)
        if resize_idx is not None:
            self._resize_node_index = resize_idx
            self._resize_start_canvas = (cx, cy)
            w = self._scene_widths[resize_idx]
            h = self._scene_heights[resize_idx]
            self._resize_start_size = (w, h)
            if self._model:
                try:
                    self._model.size_begin_edit(self._scene_model_nodes[resize_idx])
                except Exception:
                    pass
            return

        # ---- Check node menu dots click (far right of header) ----
        menu_idx = self._find_node_menu_at(cx, cy)
        if menu_idx is not None:
            self._show_node_context_menu(menu_idx)
            return

        # ---- Check expansion chevron click (top-right of header) ----
        exp_idx = self._find_expansion_icon_at(cx, cy)
        if exp_idx is not None:
            self._toggle_expansion_state(exp_idx)
            return

        # ---- InputNode summary-row toggles (Other / Unused / semantic groups) ----
        if self._input_node_vm is not None:
            for i in range(len(self._scene_model_nodes) - 1, -1, -1):
                if not self._is_input_node(i):
                    continue
                npx = self._scene_pos_x[i]
                npy = self._scene_pos_y[i]
                npw = self._scene_widths[i]
                nph = self._scene_heights[i]
                if not (npx <= cx <= npx + npw and npy <= cy <= npy + nph):
                    continue
                if cy < npy + 24.0:
                    break
                # Walk the compact port rows to find which row was clicked.
                # Row heights vary: groups/headers=18px, ports=16px, empty=22px.
                # Use the scene-index-to-port map to identify group rows.
                psy = self._port_start_y_for(i)
                rel_y = cy - npy - psy
                if rel_y < 0:
                    break
                vm = self._input_node_vm
                synth_indices = getattr(vm, "_synthetic_row_indices", {})
                group_set = getattr(vm, "_scene_group_indices", set())
                synth_set = set(synth_indices.values())
                tall_rows = group_set | synth_set
                accum = 0.0
                port_idx = -1
                max_ports = int((nph - psy) / 14.0) + 2
                for pi in range(max_ports):
                    h = 18.0 if pi in tall_rows else 16.0
                    if accum + h > rel_y:
                        port_idx = pi
                        break
                    accum += h
                if port_idx < 0:
                    break
                other_idx = synth_indices.get("other", -1)
                unused_idx = synth_indices.get("unused", -1)

                if port_idx == other_idx:
                    vm._other_group_expanded = not vm._other_group_expanded
                    self._rebuild_core()
                    return
                if port_idx == unused_idx:
                    vm._unused_group_expanded = not vm._unused_group_expanded
                    self._rebuild_core()
                    return
                scene_port_map = getattr(vm, "_scene_idx_to_port", {})
                group_port = scene_port_map.get(port_idx) if port_idx in group_set else None
                if group_port is not None:
                    # Use the view model's group collapse state dict
                    # (model expansion_state doesn't persist through rebuild)
                    gname = str(getattr(group_port, "name", "") or "")
                    if not gname:
                        try:
                            gname = str(self._model[group_port].name or "")
                        except Exception:
                            gname = f"group_{port_idx}"
                    cs = vm._group_collapse_state
                    cs[gname] = not cs.get(gname, False)
                    self._rebuild_core()
                    return
                break

        # ---- Check group expand/collapse icon click ----
        group_hit = self._find_group_icon_at(cx, cy)
        if group_hit is not None:
            ni, pi = group_hit
            self._toggle_group_expansion(ni, pi)
            return

        # ---- Check port hit (noodle drag deferred until mouse move) ----
        port_hit = self._find_port_pin_at_canvas(cx, cy)
        if port_hit is not None:
            ni, pi, is_input = port_hit

            # Record port hit but don't start noodle yet — wait for mouse move.
            # This lets click-without-drag fall through to node selection.
            self._pending_port_hit = port_hit
            self._pending_port_canvas = (cx, cy)

            # Rewire: if clicking a connected input port, prepare rewire info.
            if is_input and self._model:
                model_port = self._resolve_port(ni, pi)
                if model_port:
                    existing = self._model[model_port].inputs or []
                    if not existing and self._is_material_output_sink_port(model_port):
                        existing = self._material_output_sources(model_port)
                    if existing:
                        self._noodle_rewire = True
                        self._noodle_rewire_port = model_port
                        self._noodle_rewire_old_source = existing[0]

        # ---- Check node hit (selection + drag) ----
        hit_node = self._find_node_at(cx, cy)

        if hit_node is not None:
            shift = bool(modifier & carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
            ctrl = bool(modifier & carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL)
            current = list(self._model.selection or []) if self._model else []

            if shift:
                if hit_node not in current:
                    current.append(hit_node)
                new_sel = current
            elif ctrl:
                if hit_node in current:
                    current.remove(hit_node)
                else:
                    current.append(hit_node)
                new_sel = current
            else:
                if hit_node in current:
                    new_sel = current
                else:
                    new_sel = [hit_node]

            if new_sel is not None and self._model:
                self._model.selection = new_sel
                self._selection = list(new_sel)
                self._update_scene_selection()

            self._drag_node = hit_node
            self._drag_start_canvas = (cx, cy)
            self._marquee_start = None
        else:
            self._marquee_start = (x, y)
            self._marquee_active = False
            shift = bool(modifier & carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
            ctrl = bool(modifier & carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL)
            if not shift and not ctrl and self._model:
                self._model.selection = []
                self._selection = []
                self._update_scene_selection()

    async def _tooltip_loop(self) -> None:
        """Per-frame loop: read C++ hover state, resolve tooltip_text, push to C++."""
        app = omni.kit.app.get_app()
        while True:
            await app.next_update_async()
            self._update_hover_tooltip()

    def _update_hover_tooltip(self) -> None:
        if not self._canvas_widget or not self._model or not self._scene_model_nodes:
            return
        try:
            node_id = self._canvas_widget.hover_node_id
            port_idx = self._canvas_widget.hover_port_index
        except Exception:
            return

        if node_id == self._last_tooltip_node and port_idx == self._last_tooltip_port:
            return
        self._last_tooltip_node = node_id
        self._last_tooltip_port = port_idx

        if node_id < 0:
            try:
                self._canvas_widget.set_tooltip_text("")
            except Exception:
                pass
            return

        text = ""
        for i, mn in enumerate(self._scene_model_nodes):
            if i >= len(self._scene_stable_ids) or self._scene_stable_ids[i] != node_id:
                continue
            try:
                if port_idx >= 0:
                    model_port = self._resolve_port(i, port_idx)
                    if model_port:
                        pp = self._model[model_port]
                        custom = str(getattr(pp, "tooltip_text", "") or "")
                        if custom:
                            text = custom
                        else:
                            name = str(getattr(pp, "name", "") or "")
                            typ = str(getattr(pp, "type", "") or "")
                            variability = str(getattr(pp, "variability", "") or "")
                            lines = [name]
                            if typ:
                                lines.append(f"@Type: {typ}")
                            if variability:
                                lines.append(f"@Variability: {variability}")
                            text = "\n".join(lines)
                        try:
                            from pxr import UsdShade as _UsdShade

                            _pa = getattr(model_port, "proxy_attribute", None)
                            if _pa is None:
                                _pa = getattr(pp, "_proxy_attribute", None)
                            if (
                                _pa is not None
                                and getattr(_pa, "connectability", None) == _UsdShade.Tokens.interfaceOnly
                            ):
                                text += "\n@Connectability: Interface Only"
                        except Exception:
                            pass
                        # InputNode context provenance (Phase 2) -- only for InputNode ports
                        if self._input_node_vm is not None and self._is_input_node(i):
                            ctxs = self._input_node_vm.get_port_contexts(model_port)
                            io = self._input_node_vm.get_io_state(model_port)
                            cur = self._input_node_current_context or ""
                            if ctxs:
                                ordered = sorted(ctxs, key=lambda c: (0 if c == cur else 1, c))
                                text += f"\n@Used by: {', '.join(ordered)}"
                            elif io == 2:
                                text += "\n@Used by: none"
                        if self._validation_errors_by_path:
                            try:
                                _port_pa = getattr(model_port, "proxy_attribute", None)
                                if _port_pa is None:
                                    _port_pa = getattr(pp, "_proxy_attribute", None)
                                if _port_pa is not None:
                                    pa_path = ""
                                    node_prim = getattr(mn, "prim", None)
                                    if node_prim:
                                        pa_path = str(node_prim.GetPath()) + "." + str(_port_pa.name)
                                    err_msg = self._validation_errors_by_path.get(pa_path, "")
                                    if err_msg:
                                        text += f"\n\n[Error] {err_msg}"
                            except Exception:
                                pass
                else:
                    np = self._model[mn]
                    custom = str(getattr(np, "tooltip_text", "") or "")
                    if custom:
                        text = custom
                    else:
                        name = str(getattr(np, "name", "") or "")
                        typ = str(getattr(np, "type", "") or getattr(np, "type_name", "") or "")
                        lines = [name]
                        if typ:
                            lines.append(f"@{typ}")
                        text = "\n".join(lines)
                    if self._validation_errors_by_path and getattr(np, "valid", True) is not True:
                        try:
                            prim = getattr(mn, "prim", None)
                            if prim:
                                pp_str = str(prim.GetPath())
                                err_msg = self._validation_errors_by_path.get(pp_str, "")
                                if err_msg:
                                    text += f"\n\n[Error] {err_msg}"
                        except Exception:
                            pass
            except Exception:
                pass
            break

        try:
            self._canvas_widget.set_tooltip_text(text)
        except Exception:
            pass

    def _on_mouse_moved(self, x: float, y: float, modifier: int, pressed: bool) -> None:
        if not pressed:
            return

        # ---- Backdrop resize drag ----
        if self._resize_node_index is not None:
            cx, cy = self._screen_to_canvas(x, y)
            idx = self._resize_node_index
            sx, sy = self._resize_start_canvas
            ow, oh = self._resize_start_size
            new_w = max(100.0, ow + (cx - sx))
            new_h = max(50.0, oh + (cy - sy))
            self._scene_widths[idx] = new_w
            self._scene_heights[idx] = new_h
            if self._canvas_widget and idx < len(self._scene_stable_ids):
                self._canvas_widget.set_node_size(self._scene_stable_ids[idx], new_w, new_h)
            return

        # ---- Promote pending port hit to noodle drag on movement ----
        if self._pending_port_hit is not None and self._noodle_source is None:
            sx, sy = self._pending_port_canvas
            cx, cy = self._screen_to_canvas(x, y)
            if abs(cx - sx) > self._drag_threshold or abs(cy - sy) > self._drag_threshold:
                ni, pi, is_input = self._pending_port_hit
                if self._noodle_rewire and self._noodle_rewire_old_source:
                    src_ni, src_pi = self._find_scene_port(self._noodle_rewire_old_source)
                    if src_ni is not None:
                        self._noodle_source = (src_ni, src_pi, False)
                    else:
                        self._noodle_source = (ni, pi, is_input)
                else:
                    self._noodle_source = (ni, pi, is_input)
                self._pending_port_hit = None
                self._drag_node = None

        # ---- Noodle drag ----
        if self._noodle_source is not None:
            ni, pi, is_input = self._noodle_source
            src_cx, src_cy = self._port_canvas_pos(ni, pi, is_input)
            dst_cx, dst_cy = self._screen_to_canvas(x, y)

            # Noodle always goes output→input visually
            if is_input:
                out_x, out_y, in_x, in_y = dst_cx, dst_cy, src_cx, src_cy
            else:
                out_x, out_y, in_x, in_y = src_cx, src_cy, dst_cx, dst_cy

            # Color feedback: check target compatibility
            color = 0xFFAAAAAA
            target = self._find_port_hit_at_canvas(dst_cx, dst_cy)
            if target is not None and self._model:
                tgt_ni, tgt_pi, tgt_is_input = target
                if tgt_ni != ni and tgt_is_input != is_input:
                    src_port = self._resolve_port(ni, pi)
                    tgt_port = self._resolve_port(tgt_ni, tgt_pi)
                    if src_port and tgt_port:
                        out_p = tgt_port if is_input else src_port
                        in_p = src_port if is_input else tgt_port
                        can = True
                        set_active_modifier_flags(modifier)
                        try:
                            if hasattr(self._model, "can_connect"):
                                can = self._model.can_connect(out_p, in_p)
                            if not can:
                                color = 0xFF3838A0  # incompatible
                            else:
                                color = 0xFF48A050  # compatible
                        finally:
                            clear_active_modifier_flags()
                else:
                    color = 0xFF3838A0  # muted red-blue — same side or same node

            if self._canvas_widget:
                self._canvas_widget.set_drag_noodle(out_x, out_y, in_x, in_y, color)
            return

        # ---- Marquee drag ----
        if self._marquee_start:
            self._marquee_active = True
            if self._canvas_widget:
                sx, sy = self._marquee_start
                cx0, cy0 = self._screen_to_canvas(sx, sy)
                cx1, cy1 = self._screen_to_canvas(x, y)
                self._canvas_widget.set_marquee_rect(cx0, cy0, cx1, cy1)
            return

        # ---- Node drag ----
        if self._drag_node and self._drag_start_canvas:
            cx, cy = self._screen_to_canvas(x, y)
            dx = cx - self._drag_start_canvas[0]
            dy = cy - self._drag_start_canvas[1]

            if not self._drag_active:
                if abs(dx) > self._drag_threshold or abs(dy) > self._drag_threshold:
                    self._drag_active = True
                else:
                    return

            self._drag_start_canvas = (cx, cy)

            selected = self._selection or []
            for node in selected:
                idx = None
                for j, mn in enumerate(self._scene_model_nodes):
                    if mn is node:
                        idx = j
                        break
                if idx is None:
                    continue

                new_x = self._scene_pos_x[idx] + dx
                new_y = self._scene_pos_y[idx] + dy
                self._scene_pos_x[idx] = new_x
                self._scene_pos_y[idx] = new_y

                if self._canvas_widget and idx < len(self._scene_stable_ids):
                    sid = self._scene_stable_ids[idx]
                    self._canvas_widget.set_node_position(sid, new_x, new_y)

    def _on_mouse_released(self, x: float, y: float, button: int, modifier: int) -> None:
        if button != 0:
            return

        # ---- End backdrop resize ----
        if self._resize_node_index is not None:
            idx = self._resize_node_index
            resize_succeeded = False
            if self._model and idx < len(self._scene_model_nodes):
                mn = self._scene_model_nodes[idx]
                new_w = self._scene_widths[idx]
                new_h = self._scene_heights[idx]
                import omni.kit.undo

                resize_succeeded = True
                with omni.kit.undo.group():
                    try:
                        self._model[mn].size = (new_w, new_h)
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logger.warning(
                            "backdrop resize staging failed for %s to size=(%s, %s): %s",
                            getattr(mn, "prim_path", getattr(mn, "path", "<unknown>")),
                            new_w,
                            new_h,
                            exc,
                        )
                        resize_succeeded = False
                try:
                    resize_succeeded = self._model.size_end_edit(mn) is not False and resize_succeeded
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "backdrop resize commit failed for %s to size=(%s, %s): %s",
                        getattr(mn, "prim_path", getattr(mn, "path", "<unknown>")),
                        new_w,
                        new_h,
                        exc,
                    )
                    resize_succeeded = False
            self._resize_node_index = None
            self._resize_start_canvas = None
            self._resize_start_size = None
            if resize_succeeded and self._model:
                self._model._item_changed(None)
            elif self._model:
                self._rebuild_core()
            return

        # Clear pending port hit (click-without-drag = node selection, already handled)
        self._pending_port_hit = None
        self._pending_port_canvas = None
        if self._noodle_source is None:
            self._noodle_rewire = False
            self._noodle_rewire_port = None
            self._noodle_rewire_old_source = None

        # ---- End noodle drag: create/rewire connection ----
        if self._noodle_source is not None:
            set_active_modifier_flags(modifier)
            try:
                src_ni, src_pi, src_is_input = self._noodle_source
                cx, cy = self._screen_to_canvas(x, y)
                target = self._find_port_hit_at_canvas(cx, cy)
                connected = False
                targeted_port = target is not None
                connection_notify_item = None
                if self._canvas_widget:
                    self._canvas_widget.clear_drag_noodle()

                if target is not None and self._model:
                    tgt_ni, tgt_pi, tgt_is_input = target
                    if tgt_ni != src_ni and tgt_is_input != src_is_input:
                        if src_is_input:
                            input_port = self._resolve_port(src_ni, src_pi)
                            output_port = self._resolve_port(tgt_ni, tgt_pi)
                        else:
                            output_port = self._resolve_port(src_ni, src_pi)
                            input_port = self._resolve_port(tgt_ni, tgt_pi)

                        if input_port is not None and output_port is not None:
                            can = True
                            if hasattr(self._model, "can_connect"):
                                can = self._model.can_connect(output_port, input_port)
                            if can:
                                try:
                                    import omni.kit.undo

                                    with omni.kit.undo.group():
                                        previous_target_inputs = list(self._model[input_port].inputs or [])
                                        connected = self._set_port_inputs(input_port, [output_port])
                                        connected = connected and self._port_has_input(input_port, output_port)
                                        if (
                                            connected
                                            and self._noodle_rewire
                                            and self._noodle_rewire_port
                                            and self._noodle_rewire_port != input_port
                                        ):
                                            # Moving the output end of a noodle
                                            # edits two input ports. Treat the
                                            # pair as one logical operation:
                                            # only report success after the old
                                            # sink actually disconnected, and
                                            # compensate the new sink if it did
                                            # not.
                                            connected = False
                                            disconnected = self._set_port_inputs(self._noodle_rewire_port, [])
                                            if disconnected and not self._port_has_any_input(self._noodle_rewire_port):
                                                connected = True
                                            else:
                                                self._set_port_inputs(input_port, previous_target_inputs)
                                                logger.warning(
                                                    "rewire rollback failed: original target %s remained connected "
                                                    "after source %s was assigned to target %s",
                                                    getattr(self._noodle_rewire_port, "path", "<unknown>"),
                                                    getattr(output_port, "path", "<unknown>"),
                                                    getattr(input_port, "path", "<unknown>"),
                                                )
                                    if self._is_material_output_sink_port(
                                        input_port
                                    ) or self._is_material_output_sink_port(self._noodle_rewire_port):
                                        connection_notify_item = None
                                    else:
                                        connection_notify_item = input_port
                                except Exception as exc:  # pylint: disable=broad-exception-caught
                                    logger.warning(
                                        "connection edit failed: source=%s target=%s reason=%s",
                                        getattr(output_port, "path", "<unknown>"),
                                        getattr(input_port, "path", "<unknown>"),
                                        exc,
                                    )
                        else:
                            pass
                    else:
                        pass

                # Rewire dropped on empty: disconnect the original
                if (
                    not connected
                    and not targeted_port
                    and self._noodle_rewire
                    and self._noodle_rewire_port
                    and self._model
                ):
                    self._defer_rewire_drop_disconnect(self._noodle_rewire_port)
            finally:
                clear_active_modifier_flags()

            self._noodle_source = None
            self._noodle_rewire = False
            self._noodle_rewire_port = None
            self._noodle_rewire_old_source = None
            if connected:
                from omni.kit.widget.graph import IsolationGraphModel as _IsoModel

                if isinstance(input_port, _IsoModel.EmptyPort) or isinstance(output_port, _IsoModel.EmptyPort):
                    self._model._item_changed(None)
                else:
                    self._notify_connection_changed(connection_notify_item, reason="connect")
            return

        # ---- End node drag: commit positions to model ----
        if self._drag_active and self._model:
            import omni.kit.undo

            selected = self._selection or []
            scene_index_by_id = {id(model_node): index for index, model_node in enumerate(self._scene_model_nodes)}
            with omni.kit.undo.group():
                for node in selected:
                    idx = scene_index_by_id.get(id(node))
                    if idx is None:
                        try:
                            drag_name = str(self._model[node].name)
                            for j, mn in enumerate(self._scene_model_nodes):
                                try:
                                    if str(self._model[mn].name) == drag_name:
                                        idx = j
                                        break
                                except Exception:
                                    pass
                        except Exception:
                            drag_name = "?"
                    if idx is not None and idx < len(self._scene_pos_x):
                        new_pos = (self._scene_pos_x[idx], self._scene_pos_y[idx])
                        try:
                            if not self._commit_node_position(node, new_pos):
                                logger.warning("node position edit was rejected for %s", getattr(node, "path", node))
                        except Exception as exc:  # pylint: disable=broad-exception-caught
                            logger.warning(
                                "node position commit failed for node='%s' requested_position=%s: %s; "
                                "the previous authored position was preserved",
                                getattr(node, "path", node),
                                new_pos,
                                exc,
                            )

        self._drag_node = None
        self._drag_active = False
        self._drag_start_canvas = None

        # ---- End marquee ----
        if self._marquee_start and self._marquee_active:
            sx, sy = self._marquee_start
            start_cx, start_cy = self._screen_to_canvas(sx, sy)
            end_cx, end_cy = self._screen_to_canvas(x, y)
            nodes_in_rect = self._find_nodes_in_rect(start_cx, start_cy, end_cx, end_cy)

            shift = bool(modifier & carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
            ctrl = bool(modifier & carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL)

            if shift and self._model:
                current = list(self._model.selection or [])
                for n in nodes_in_rect:
                    if n not in current:
                        current.append(n)
                self._model.selection = current
            elif ctrl and self._model:
                current = list(self._model.selection or [])
                rect_ids = set(id(n) for n in nodes_in_rect)
                self._model.selection = [n for n in current if id(n) not in rect_ids]
            elif self._model:
                self._model.selection = nodes_in_rect

        self._marquee_start = None
        self._marquee_active = False
        if self._canvas_widget:
            self._canvas_widget.clear_marquee()

    def _defer_rewire_drop_disconnect(self, port: object) -> None:
        """Run dropped-rewire USD disconnect after one rendered update."""
        ports = self._deferred_disconnect_ports
        if port not in ports:
            ports.append(port)
        if self._deferred_disconnect_task and not self._deferred_disconnect_task.done():
            return

        async def _disconnect_after_frame() -> None:
            expected_model = self._model
            await omni.kit.app.get_app().next_update_async()
            if not self._model or self._model is not expected_model:
                self._deferred_disconnect_ports = []
                return
            ports = list(self._deferred_disconnect_ports)
            self._deferred_disconnect_ports = []
            for pending_port in ports:
                try:
                    disconnected = self._set_port_inputs(pending_port, [])
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "deferred rewire disconnect failed for target %s: %s",
                        getattr(pending_port, "path", "<unknown>"),
                        exc,
                    )
                    continue
                if not disconnected or self._port_has_any_input(pending_port):
                    logger.warning(
                        "deferred rewire disconnect was rejected for target %s; the existing source is unchanged",
                        getattr(pending_port, "path", "<unknown>"),
                    )
                    continue
                try:
                    notify_item = self._connection_notify_item_for_port(pending_port)
                    self._notify_connection_changed(
                        notify_item, reason="deferred_rewire_drop_disconnect", sync_item=True
                    )
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    log_exception(
                        logger,
                        "deferred connection notification failed",
                        level=logging.WARNING,
                        action="deferred_disconnect",
                        exc=exc,
                    )
                    try:
                        self._model._item_changed(None)
                    except Exception as refresh_exc:  # pylint: disable=broad-exception-caught
                        log_exception(
                            logger,
                            "deferred connection refresh failed",
                            level=logging.WARNING,
                            action="deferred_disconnect",
                            exc=refresh_exc,
                        )
                        self._rebuild_core()

        self._deferred_disconnect_task = ensure_future_logged(
            _disconnect_after_frame(), "deferred connection disconnect"
        )

    def _cancel_deferred_disconnects(self) -> None:
        """Cancel pending deferred USD disconnects."""
        task = getattr(self, "_deferred_disconnect_task", None)
        if task and not task.done():
            task.cancel()
        self._deferred_disconnect_task = None
        self._deferred_disconnect_ports = []

    def _commit_node_position(self, node, position) -> bool:
        """Persist a dragged node position while avoiding full sync for prim-backed nodes."""
        if self._is_isolation_io_node(node):
            self._model[node].position = position
            return True
        set_position = getattr(node, "set_position", None)
        if callable(set_position):
            return set_position(position, notify=False) is not False
        # IO wrapper nodes rely on the isolation proxy to persist context positions.
        self._model[node].position = position
        return True

    @staticmethod
    def _is_isolation_io_node(node) -> bool:
        """Return True for input/output wrapper nodes shown by the isolation model."""
        try:
            type_name = type(node).get_type_name()
        except (RuntimeError, ValueError, TypeError, AttributeError):
            type_name = None
        return type_name in ("InputNode", "OutputNode") or hasattr(node, "source")

    # ------------------------------------------------------------------
    # Double-click: backdrop description edit + color swatch
    # ------------------------------------------------------------------

    def _is_io_node(self, node_index: int) -> bool:
        """Return True if the node at this index is an Input/Output isolation node."""
        if node_index >= len(self._scene_model_nodes):
            return False
        mn = self._scene_model_nodes[node_index]
        return self._is_isolation_io_node(mn)

    def _find_backdrop_header_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        """Return node index if click is on a backdrop header, or None."""
        for i in range(len(self._scene_model_nodes) - 1, -1, -1):
            if i >= len(self._scene_is_backdrop) or not self._scene_is_backdrop[i]:
                continue
            px = self._scene_pos_x[i]
            py = self._scene_pos_y[i]
            pw = self._scene_widths[i]
            if px <= canvas_x <= px + pw and py <= canvas_y <= py + self._HEADER_ACTUAL:
                return i
        return None

    def _on_mouse_double_clicked(self, x: float, y: float, button: int, modifier: int) -> None:
        if button != 0:
            return
        cx, cy = self._screen_to_canvas(x, y)

        port_hit = self._find_port_hit_at_canvas(cx, cy)
        if port_hit is not None:
            ni, pi, _is_input = port_hit
            model_port = self._resolve_port(ni, pi)
            if model_port and self._is_nodegraph_interface_port(model_port):
                self._show_nodegraph_port_rename_dialog(model_port)
                return

        # Color swatch check first (it's inside the header)
        swatch_idx = self._find_backdrop_color_swatch_at(cx, cy)
        if swatch_idx is not None:
            self._open_color_picker(swatch_idx, x, y)
            return

        # Backdrop header rename
        bd_hdr_idx = self._find_backdrop_header_at(cx, cy)
        if bd_hdr_idx is not None:
            self._open_rename_editor(bd_hdr_idx)
            return

        # Node name rename (header text area, skip IO nodes)
        name_idx = self._find_header_name_at(cx, cy)
        if name_idx is not None:
            if not self._is_io_node(name_idx):
                self._open_rename_editor(name_idx)
            return

        # Description body edit (backdrop)
        body_idx = self._find_backdrop_body_at(cx, cy)
        if body_idx is not None:
            self._open_description_editor(body_idx, x, y)
            self._start_edit_poll()
            return

        # C++ may have self-triggered a backdrop edit — start polling
        self._start_edit_poll()

    def _open_description_editor(self, node_index: int, screen_x: float, screen_y: float) -> None:
        """Trigger C++ inline description edit via ImGui InputTextMultiline."""
        if not self._model or node_index >= len(self._scene_model_nodes):
            return
        if not self._canvas_widget:
            return
        mn = self._scene_model_nodes[node_index]

        try:
            current_desc = str(self._model[mn].description or "")
        except Exception:
            current_desc = ""

        stable_id = self._scene_stable_ids[node_index] if node_index < len(self._scene_stable_ids) else 0
        try:
            self._canvas_widget.start_desc_edit(stable_id, current_desc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "description editor failed to start",
                level=logging.WARNING,
                action="description_edit",
                exc=exc,
            )
            return

        if self._desc_edit_poll_task:
            self._desc_edit_poll_task.cancel()
        self._desc_edit_poll_task = ensure_future_logged(self._poll_desc_edit_result(), "description edit polling")

    async def _poll_desc_edit_result(self) -> None:
        """Poll the C++ widget for description edit commit each frame."""
        app = omni.kit.app.get_app()
        while self._canvas_widget:
            await app.next_update_async()
            if not self._canvas_widget:
                break
            try:
                if not self._canvas_widget.has_desc_edit_result():
                    continue
                stable_id, new_desc = self._canvas_widget.consume_desc_edit_result()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "description edit polling failed",
                    level=logging.WARNING,
                    action="description_edit",
                    exc=exc,
                )
                break
            if not self._model:
                break
            for i, mn in enumerate(self._scene_model_nodes):
                if i < len(self._scene_stable_ids) and self._scene_stable_ids[i] == stable_id:
                    if self._commit_node_description(mn, new_desc):
                        self._model._item_changed(None)
                    break
            break

    def _close_description_editor(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Node rename (double-click header name)
    # ------------------------------------------------------------------

    def _open_rename_editor(self, node_index: int) -> None:
        """Trigger C++ inline rename via ImGui InputText."""
        if not self._model or node_index >= len(self._scene_model_nodes):
            return
        if not self._canvas_widget:
            return
        mn = self._scene_model_nodes[node_index]
        try:
            current_name = str(self._model[mn].name or "")
        except Exception:
            current_name = ""

        self._rename_opened_frame = omni.kit.app.get_app().get_update_number()

        stable_id = self._scene_stable_ids[node_index] if node_index < len(self._scene_stable_ids) else 0
        try:
            self._canvas_widget.start_rename(stable_id, current_name)
        except Exception:
            return

        self._start_edit_poll()

    def _close_rename_editor(self) -> None:
        pass

    def _open_color_picker(self, node_index: int, screen_x: float, screen_y: float) -> None:
        """Overlay a tiny ColorWidget on the swatch so the picker opens on click."""
        if not self._model or node_index >= len(self._scene_model_nodes):
            return
        mn = self._scene_model_nodes[node_index]

        try:
            current_color = self._model[mn].display_color
        except Exception:
            current_color = None

        self._close_color_picker()

        px = self._scene_pos_x[node_index]
        py = self._scene_pos_y[node_index]
        swatch_sz = 14.0
        swatch_x = px + (self._HEADER_H - swatch_sz) * 0.5 + 2.0
        swatch_y = py + (self._HEADER_H - swatch_sz) * 0.5

        if self.__root_stack:
            with self.__root_stack:
                placer = ui.Placer(offset_x=swatch_x, offset_y=swatch_y)
                with placer:
                    color_widget = ui.ColorWidget(width=swatch_sz, height=swatch_sz)
                    if current_color:
                        sub_models = color_widget.model.get_item_children()
                        try:
                            color_widget.model.get_item_value_model(sub_models[0]).as_float = float(current_color[0])
                            color_widget.model.get_item_value_model(sub_models[1]).as_float = float(current_color[1])
                            color_widget.model.get_item_value_model(sub_models[2]).as_float = float(current_color[2])
                        except Exception:
                            pass

                    def _on_color_end(m, _mn=mn, _placer=placer, _cw=color_widget):
                        if self._color_picker_widget is None:
                            return
                        sub = m.get_item_children()
                        r = m.get_item_value_model(sub[0]).as_float
                        g = m.get_item_value_model(sub[1]).as_float
                        b = m.get_item_value_model(sub[2]).as_float
                        _placer.visible = False
                        _cw.visible = False
                        self._color_picker_widget = None
                        if self._model and self._commit_node_color(_mn, (r, g, b)):
                            self._model._item_changed(None)

                    color_widget.model.add_end_edit_fn(_on_color_end)
                    self._color_picker_widget = (placer, color_widget, mn)

    def _commit_color_picker(self) -> None:
        """Read the current color values from the widget and apply them."""
        if not self._color_picker_widget:
            return
        placer, cw, mn = self._color_picker_widget
        r = g = b = 0.0
        read_succeeded = True
        try:
            sub = cw.model.get_item_children()
            r = cw.model.get_item_value_model(sub[0]).as_float
            g = cw.model.get_item_value_model(sub[1]).as_float
            b = cw.model.get_item_value_model(sub[2]).as_float
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "color picker value read failed for node %s: %s",
                getattr(mn, "prim_path", getattr(mn, "path", "<unknown>")),
                exc,
            )
            read_succeeded = False
        try:
            placer.visible = False
            cw.visible = False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "color picker cleanup failed",
                level=logging.WARNING,
                action="color_picker",
                exc=exc,
            )
        self._color_picker_widget = None
        if read_succeeded and self._model and self._commit_node_color(mn, (r, g, b)):
            self._model._item_changed(None)

    def _commit_node_color(self, model_node: object, value: tuple[float, float, float]) -> bool:
        """Commit a node display color and preserve a model-provided failure result."""
        item = self._model[model_node]
        setter = getattr(item, "set_display_color", None)
        if callable(setter):
            success = setter(value) is not False
        else:
            item.display_color = value
            success = True
        if not success:
            logger.warning("node color edit was rejected for %s", getattr(item, "path", model_node))
        return success

    def _close_color_picker(self) -> None:
        if self._color_picker_widget:
            self._commit_color_picker()

    # ------------------------------------------------------------------
    # Port context menu (right-click disconnect)
    # ------------------------------------------------------------------

    def _show_port_context_menu(self, model_port) -> None:
        if not self._model:
            return

        is_fallback = hasattr(model_port, "_fallback_usd_attr")
        owner_node = None if is_fallback else self._find_port_owner_node(model_port)
        can_edit_interface_port = (not is_fallback) and self._is_nodegraph_interface_owner(owner_node)
        has_input_conn = False
        has_output_conn = False

        if is_fallback:
            fb_attr = model_port._fallback_usd_attr
            if fb_attr:
                from pxr import UsdShade as _US

                if model_port._is_output:
                    shade_out = _US.Output(fb_attr)
                    has_input_conn = bool(shade_out and shade_out.HasConnectedSource())
                    has_output_conn = self._fallback_output_has_consumers(model_port)
                else:
                    shade_inp = _US.Input(fb_attr)
                    has_input_conn = bool(shade_inp and shade_inp.HasConnectedSource())
        else:
            try:
                inputs = self._model[model_port].inputs or []
                has_input_conn = bool(inputs)
            except Exception:
                pass
            if not has_input_conn:
                try:
                    from pxr import UsdShade as _US

                    pa = getattr(model_port, "proxy_attribute", None)
                    if pa:
                        if owner_node:
                            prim = getattr(owner_node, "prim", None)
                            if prim:
                                usd_attr = prim.GetAttribute(pa.name)
                                if usd_attr:
                                    if self._is_material_output_sink_port(model_port):
                                        shade_output = _US.Output(usd_attr)
                                        has_input_conn = bool(shade_output and shade_output.HasConnectedSource())
                                    else:
                                        shade_inp = _US.Input(usd_attr)
                                        has_input_conn = bool(shade_inp and shade_inp.HasConnectedSource())
                except Exception:
                    pass
            has_output_conn = self._port_has_output_connections(model_port)

        if not has_input_conn and not has_output_conn and not can_edit_interface_port:
            return

        if getattr(self, "_port_context_menu", None) is not None:
            self._port_context_menu.hide()
        self._port_context_menu = ui.Menu("Port Context Menu")
        with self._port_context_menu:
            if can_edit_interface_port:
                ui.MenuItem("Rename", triggered_fn=lambda p=model_port: self._show_nodegraph_port_rename_dialog(p))
                ui.MenuItem("Remove", triggered_fn=lambda p=model_port: self._remove_nodegraph_port(p))
                if has_input_conn or has_output_conn:
                    ui.Separator()
            if is_fallback and (has_input_conn or has_output_conn):
                ui.MenuItem("Disconnect", triggered_fn=lambda p=model_port: self._disconnect_fallback_port(p))
            elif has_input_conn or has_output_conn:
                ui.MenuItem("Disconnect", triggered_fn=lambda p=model_port: self._disconnect_port(p))
        from .interaction.menu_utils import show_menu_at_cursor

        show_menu_at_cursor(self._port_context_menu)

    def _find_port_owner_node(self, model_port) -> Optional[Any]:
        """Return the scene node that owns a port, including grouped sub-ports."""
        if not self._model:
            return None
        for mn in self._scene_model_nodes:
            try:
                node_ports = self._model[mn].ports or []
            except Exception:
                continue
            if model_port in self._iter_port_tree(node_ports):
                return mn
        return None

    def _iter_port_tree(self, ports):
        """Yield ports recursively through expanded group children."""
        for port in ports or []:
            yield port
            try:
                sub_ports = self._model[port].ports
            except Exception:
                sub_ports = None
            if sub_ports:
                yield from self._iter_port_tree(sub_ports)

    def _is_nodegraph_interface_port(self, model_port) -> bool:
        """Return True for ports shown on NodeGraph InputNode/OutputNode wrappers."""
        if not getattr(model_port, "path", None):
            return False
        return self._is_nodegraph_interface_owner(self._find_port_owner_node(model_port))

    @staticmethod
    def _is_nodegraph_interface_owner(owner) -> bool:
        """Return True for InputNode/OutputNode scene nodes."""
        if owner is None:
            return False
        try:
            type_name = type(owner).get_type_name()
        except Exception:
            type_name = ""
        return type_name in {"InputNode", "OutputNode"}

    def _nodegraph_port_label(self, model_port) -> str:
        """Return the current visible label for a NodeGraph interface port."""
        try:
            return str(self._model[model_port].name or "")
        except Exception:
            proxy_attribute = getattr(model_port, "proxy_attribute", None)
            if proxy_attribute:
                try:
                    display_name = proxy_attribute.display_name
                    if display_name:
                        return str(display_name)
                except Exception:
                    pass
                return str(getattr(proxy_attribute, "name", "")).split(":")[-1]
        return ""

    def _show_nodegraph_port_rename_dialog(self, model_port) -> None:
        """Show a dialog that edits displayName metadata for a NodeGraph interface port."""
        if not self._is_nodegraph_interface_port(model_port):
            return
        from omni.kit.window.popup_dialog import InputDialog

        def _apply(dialog: InputDialog) -> None:
            new_label = dialog.get_value()
            if isinstance(new_label, str) and new_label.strip():
                self._set_nodegraph_port_display_name(model_port, new_label.strip())
            dialog.hide()

        self._port_rename_dialog = InputDialog(
            title="Rename Port",
            width=300,
            message="Display name:",
            default_value=self._nodegraph_port_label(model_port),
            ok_handler=_apply,
        )
        self._port_rename_dialog.show()

    def _set_nodegraph_port_display_name(self, model_port, display_name: str) -> None:
        """Set displayName metadata for a NodeGraph interface port and refresh the graph."""
        if not self._is_nodegraph_interface_port(model_port):
            return
        from ..commands.wrappers.attributes import SetDisplayName

        result = SetDisplayName(model_port.path, display_name)
        if not result.success:
            logger.warning("failed to rename NodeGraph port %s: %s", model_port.path, result.message)
            return
        proxy_attribute = getattr(model_port, "proxy_attribute", None)
        if proxy_attribute is not None:
            try:
                proxy_attribute.display_name = display_name
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "port display name cache update failed",
                    level=logging.WARNING,
                    prim_path=str(model_port.path),
                    action="set_display_name",
                    exc=exc,
                )
            updated_proxy = False
            update_proxy = getattr(model_port, "update_proxy_attribute", None)
            if callable(update_proxy):
                try:
                    update_proxy(proxy_attribute)
                    updated_proxy = True
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    log_exception(
                        logger,
                        "port proxy synchronization failed",
                        level=logging.WARNING,
                        prim_path=str(model_port.path),
                        action="set_display_name",
                        exc=exc,
                    )
            if not updated_proxy and self._model:
                try:
                    inner_model = self._model[model_port]
                    update_proxy = getattr(inner_model, "update_proxy_attribute", None)
                    if callable(update_proxy):
                        update_proxy(proxy_attribute)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    log_exception(
                        logger,
                        "port model synchronization failed",
                        level=logging.WARNING,
                        prim_path=str(model_port.path),
                        action="set_display_name",
                        exc=exc,
                    )
        if self._model:
            self._model._item_changed(None)

    def _remove_nodegraph_port(self, model_port) -> None:
        """Remove a NodeGraph interface port from its backing prim."""
        if not self._is_nodegraph_interface_port(model_port):
            return
        from ..commands.wrappers.attributes import RemoveProperty

        result = RemoveProperty(model_port.path)
        if not result.success:
            logger.warning("failed to remove NodeGraph port %s: %s", model_port.path, result.message)
            return
        if self._model:
            self._model._item_changed(None)

    def _port_has_output_connections(self, port) -> bool:
        """Check if this port is a source in any connection."""
        if not self._model:
            return False
        for mn in self._scene_model_nodes:
            try:
                ports = self._model[mn].ports or []
                for p in self._iter_port_tree(ports):
                    inp = self._model[p].inputs or []
                    if port in inp:
                        return True
            except Exception:
                pass
        return False

    def _disconnect_port(self, port) -> bool:
        if not self._model:
            return False
        import omni.kit.undo

        inputs = self._model[port].inputs or []
        if inputs:
            with omni.kit.undo.group():
                disconnected = self._set_port_inputs(port, [])
            if not disconnected or self._port_has_any_input(port):
                logger.warning(
                    "disconnect input port was rejected for target %s; the existing source is unchanged",
                    getattr(port, "path", "<unknown>"),
                )
                return False
            notify_item = self._connection_notify_item_for_port(port)
            self._notify_connection_changed(notify_item, reason="disconnect_input_port", sync_item=True)
            return True

        try:
            from pxr import UsdShade as _US

            from ..commands.wrappers.ports import DisconnectSourcePort

            pa = getattr(port, "proxy_attribute", None)
            if pa:
                node_ref = self._find_port_owner_node(port)
                if node_ref:
                    prim = getattr(node_ref, "prim", None)
                    if prim:
                        usd_attr = prim.GetAttribute(pa.name)
                        if usd_attr:
                            shade_port = (
                                _US.Output(usd_attr)
                                if self._is_material_output_sink_port(port)
                                else _US.Input(usd_attr)
                            )
                            if shade_port and shade_port.HasConnectedSource():
                                with omni.kit.undo.group():
                                    result = DisconnectSourcePort(shade_port)
                                if result.success:
                                    notify_item = self._connection_notify_item_for_port(port)
                                    self._notify_connection_changed(
                                        notify_item, reason="disconnect_usd_source_scan", sync_item=True
                                    )
                                    return True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "USD source disconnect scan failed for port='%s': %s; falling back to model consumer scan",
                getattr(port, "path", "<unknown>"),
                exc,
            )

        removed_consumer_count = 0
        with omni.kit.undo.group():
            for mn in self._scene_model_nodes:
                try:
                    ports = self._model[mn].ports or []
                    for p in self._iter_port_tree(ports):
                        inp = self._model[p].inputs or []
                        new_inp = [s for s in inp if s != port]
                        if len(new_inp) != len(inp):
                            removed = self._set_port_inputs(p, new_inp)
                            if removed and not self._port_has_input(p, port):
                                removed_consumer_count += 1
                            else:
                                logger.warning(
                                    "disconnect output consumer was rejected: source=%s target=%s",
                                    getattr(port, "path", "<unknown>"),
                                    getattr(p, "path", "<unknown>"),
                                )
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "disconnect output consumer failed for source %s while scanning node %s: %s",
                        getattr(port, "path", "<unknown>"),
                        getattr(mn, "prim_path", getattr(mn, "path", "<unknown>")),
                        exc,
                    )
        if removed_consumer_count:
            notify_item = self._connection_notify_item_for_port(port)
            self._notify_connection_changed(notify_item, reason="disconnect_output_consumer", sync_item=True)
            return True
        return False

    def _port_has_input(self, input_port: object, output_port: object) -> bool:
        """Return whether the graph model reflects the requested authored source."""
        try:
            inputs = self._model[input_port].inputs or []
            output_path = getattr(output_port, "path", None)
            for source in inputs:
                if source is output_port or source == output_port:
                    return True
                if output_path is not None and getattr(source, "path", None) == output_path:
                    return True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "connection verification failed: source=%s target=%s reason=%s",
                getattr(output_port, "path", "<unknown>"),
                getattr(input_port, "path", "<unknown>"),
                exc,
            )
        return False

    def _port_has_any_input(self, input_port: object) -> bool:
        """Return whether the graph model still reports any source for a port."""
        try:
            return bool(self._model[input_port].inputs or [])
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "connection disconnect verification failed for target %s: %s",
                getattr(input_port, "path", "<unknown>"),
                exc,
            )
            return True

    def _disconnect_fallback_port(self, port) -> None:
        """Disconnect a fallback ProxyAttribute port via USD directly."""
        fb_attr = getattr(port, "_fallback_usd_attr", None)
        fb_prim = getattr(port, "_fallback_prim", None)
        if not fb_attr or not fb_prim:
            return
        import omni.kit.undo
        from pxr import UsdShade as _US

        from ..commands.wrappers.ports import DisconnectSourcePort

        if not port._is_output:
            shade_inp = _US.Input(fb_attr)
            if shade_inp and shade_inp.HasConnectedSource():
                with omni.kit.undo.group():
                    result = DisconnectSourcePort(shade_inp)
                if result.success and self._model:
                    notify_item = self._connection_notify_item_for_port(port)
                    self._notify_connection_changed(notify_item, reason="disconnect_fallback_input", sync_item=True)
                return
        else:
            shade_out = _US.Output(fb_attr)
            if shade_out and shade_out.HasConnectedSource():
                with omni.kit.undo.group():
                    result = DisconnectSourcePort(shade_out)
                if result.success and self._model:
                    notify_item = self._connection_notify_item_for_port(port)
                    self._notify_connection_changed(
                        notify_item, reason="disconnect_fallback_output_source", sync_item=True
                    )
                return

        fb_path = fb_prim.GetPath()
        out_name = port.name.replace("outputs:", "") if port.name.startswith("outputs:") else port.name
        disconnected = False
        scan_error = None
        with omni.kit.undo.group():
            for mn in self._scene_model_nodes:
                try:
                    node_ports = self._model[mn].ports or []
                    for p in self._iter_port_tree(node_ports):
                        try:
                            pp = self._model[p]
                            inp = pp.inputs or []
                            if not inp:
                                continue
                            pa = getattr(p, "proxy_attribute", None)
                            if not pa:
                                continue
                            usd_attr = getattr(pa, "attribute", None)
                            if not usd_attr:
                                node_prim = getattr(mn, "prim", None)
                                if node_prim:
                                    usd_attr = node_prim.GetAttribute(pa.name)
                            if not usd_attr:
                                continue
                            shade_inp = _US.Input(usd_attr)
                            if not shade_inp or not shade_inp.HasConnectedSource():
                                continue
                            sources = shade_inp.GetConnectedSources()
                            if isinstance(sources, tuple):
                                sources = sources[0]
                            for src in sources or []:
                                src_api = src.source if hasattr(src, "source") else src
                                if not src_api:
                                    continue
                                if src_api.GetPrim().GetPath() == fb_path:
                                    src_name = src.sourceName if hasattr(src, "sourceName") else ""
                                    if src_name == out_name:
                                        result = DisconnectSourcePort(shade_inp)
                                        if result.success:
                                            disconnected = True
                                        break
                        except Exception as exc:  # pylint: disable=broad-exception-caught
                            if scan_error is None:
                                scan_error = exc
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    if scan_error is None:
                        scan_error = exc
        if scan_error is not None:
            log_exception(
                logger,
                "fallback connection scan failed",
                level=logging.WARNING,
                prim_path=str(fb_path),
                action="disconnect_fallback",
                exc=scan_error,
            )
        if disconnected and self._model:
            self._notify_connection_changed(None, reason="disconnect_fallback_scan")

    def _fallback_output_has_consumers(self, port) -> bool:
        """Return whether a fallback output is consumed by any visible port."""
        if not self._model:
            return False
        fb_prim = getattr(port, "_fallback_prim", None)
        fb_path = fb_prim.GetPath() if fb_prim else None
        out_name = (
            port.name.replace("outputs:", "")
            if str(getattr(port, "name", "")).startswith("outputs:")
            else getattr(port, "name", "")
        )
        if not fb_path or not out_name:
            return False
        for mn in self._scene_model_nodes:
            try:
                for p in self._iter_port_tree(self._model[mn].ports or []):
                    for source in self._model[p].inputs or []:
                        if source is port:
                            return True
            except Exception:
                continue
        return False

    @staticmethod
    def _is_material_output_sink_port(port) -> bool:
        """Return True for material outputs rendered as input-side graph sinks."""
        from pxr import UsdShade

        try:
            prim = getattr(port, "prim", None)
            proxy = getattr(port, "proxy_attribute", None)
            return bool(
                prim
                and prim.IsA(UsdShade.Material)
                and proxy is not None
                and str(getattr(proxy, "name", "")).startswith(UsdShade.Tokens.outputs)
            )
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return False

    def _connection_notify_item_for_port(self, port):
        """Return notification item, requesting root refresh for material output sinks."""
        return None if self._is_material_output_sink_port(port) else port

    def _material_output_sources(self, port) -> list:
        """Return connected source models for a material output sink."""
        if not self._is_material_output_sink_port(port):
            return []
        try:
            usd_port = getattr(port, "usdshade_port", None)
            sources = usd_port.GetConnectedSources() if usd_port and usd_port.HasConnectedSource() else []
            if isinstance(sources, tuple):
                sources = sources[0]
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return []
        from pxr import UsdShade

        resolved = []
        for source in sources or []:
            try:
                src_api = source.source if hasattr(source, "source") else source
                src_name = source.sourceName if hasattr(source, "sourceName") else ""
                src_type = source.sourceType if hasattr(source, "sourceType") else UsdShade.AttributeType.Output
                prefix = UsdShade.Tokens.inputs if src_type == UsdShade.AttributeType.Input else UsdShade.Tokens.outputs
                source_path = src_api.GetPrim().GetPath().AppendProperty(f"{prefix}{src_name}")
                resolved_port = self._model.get_item_model(source_path) if self._model else None
                if resolved_port:
                    resolved.append(resolved_port)
            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue
        return resolved

    @property
    def hovered_connection_index(self) -> int:
        """Return the scene connection index the mouse is hovering over, or -1."""
        if self._canvas_widget:
            return self._canvas_widget.hover_connection_index
        return -1

    def disconnect_hovered_connection(self) -> bool:
        """If a connection is hovered, disconnect it and return True."""
        ci = self.hovered_connection_index
        if ci < 0 or not self._canvas_widget or not self._model:
            return False
        scene = self._last_scene
        if scene is None:
            return False
        conns = scene.connections
        if ci >= len(conns):
            return False
        conn = conns[ci]
        tgt_port = self._resolve_port_by_stable_id(conn.target_node_id, conn.target_port_index, is_input=True)
        if tgt_port is None:
            return False
        return self._disconnect_port(tgt_port)

    def _notify_connection_changed(self, item, reason: str, sync_item: bool = False) -> None:
        """Emit connection-only notification and avoid full model refresh when possible."""
        if not self._model:
            return
        if sync_item:
            item_sync = getattr(item, "sync", None)
            if callable(item_sync):
                try:
                    item_sync()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    log_exception(
                        logger,
                        "connection model synchronization failed",
                        level=logging.WARNING,
                        action=reason,
                        exc=exc,
                    )
        root = self._resolve_nodegraph_for_connection_visual_cb()
        notifier = getattr(root, "notify_connection_changed", None) if root is not None else None
        if not callable(notifier):
            notifier = getattr(self._model, "notify_connection_changed", None)
        if callable(notifier):
            notifier(item)
            return
        self._model._item_changed(None)

    def _resolve_port_by_stable_id(self, stable_id: int, port_index: int, is_input: bool):
        """Map a (stableId, visiblePortIndex) pair back to a model port object."""
        if not self._model:
            return None
        node_idx = None
        for i, sid in enumerate(self._scene_stable_ids):
            if sid == stable_id:
                node_idx = i
                break
        if node_idx is None:
            return None
        return self._resolve_port(node_idx, port_index)

    def _find_scene_port(self, model_port) -> Tuple[Optional[int], Optional[int]]:
        """Find (node_index, port_index) for a model port object."""
        if not self._model:
            return None, None
        for i, mn in enumerate(self._scene_model_nodes):
            try:
                ports = self._model[mn].ports or []
                for pi, p in enumerate(ports):
                    if p == model_port:
                        return i, pi
            except Exception:
                pass
        return None, None

    def hide_port_context_menu(self) -> None:
        menu = getattr(self, "_port_context_menu", None)
        if not menu:
            return
        try:
            menu.hide()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "port context menu hide failed",
                level=logging.WARNING,
                action="hide_port_context_menu",
                exc=exc,
            )
        try:
            menu.visible = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Rebuild trigger
    # ------------------------------------------------------------------

    def _detach_rebuild_kit_subscription(self) -> None:
        """Drop the pending deferred-rebuild Events 2.0 observer handle."""
        sub = self._rebuild_kit_sub
        self._rebuild_kit_sub = None
        if sub is None:
            return
        for name in ("unsubscribe", "release", "destroy"):
            fn = getattr(sub, name, None)
            if callable(fn):
                try:
                    fn()
                except (RuntimeError, ValueError, TypeError, AttributeError):
                    pass
                break

    def _on_rebuild_deferred(self, _event: Any = None) -> None:
        """Run the native rebuild on the next Kit tick via Events 2.0 ``GLOBAL_EVENT_UPDATE``."""
        self._detach_rebuild_kit_subscription()
        if not self._model:
            return
        self._rebuild_core()

    def _schedule_rebuild_work(self) -> None:
        """Defer rebuild to the next Kit tick using Events 2.0 ``GLOBAL_EVENT_UPDATE``."""
        try:
            from carb.eventdispatcher import get_eventdispatcher

            self._rebuild_kit_sub = get_eventdispatcher().observe_event(
                observer_name="omni.kit.window.material_graph.canvas_rebuild",
                event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                on_event=self._on_rebuild_deferred,
            )
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning(
                "graph canvas deferred rebuild: observe_event(GLOBAL_EVENT_UPDATE) failed (%s); rebuilding now",
                exc,
            )
            self._rebuild_core()

    def _on_item_changed(self, item) -> None:
        if self._rebuilding:
            return
        if getattr(self, "_skip_deferred_rebuild_once", False):
            self._skip_deferred_rebuild_once = False
            return
        if item is not None and self._consume_position_only_changed(item) and self._update_scene_node_geometry(item):
            return
        if self._rebuild_kit_sub is not None and item is not None:
            return
        if self._rebuild_kit_sub is not None:
            self._detach_rebuild_kit_subscription()
        self._schedule_rebuild_work()

    def _consume_position_only_changed(self, item) -> bool:
        """Return True when the root model marked this item as position-only."""
        consumer = getattr(self, "_position_change_consumer", None)
        return bool(callable(consumer) and consumer(item))

    def _resolve_position_change_consumer(self):
        """Return the model hook that consumes position-only change markers."""
        for model in (self._model, getattr(self._model, "_root", None), getattr(self._model, "_model", None)):
            consumer = getattr(model, "consume_position_only_changed", None)
            if callable(consumer):
                return consumer
        return None

    def _update_scene_node_geometry(self, item) -> bool:
        """Apply position-only item changes without rebuilding the native scene."""
        if not self._model or not self._canvas_widget:
            return False
        idx = self._find_scene_node_index(item)
        if idx is None:
            return False
        try:
            model_proxy = self._model[item]
            pos = model_proxy.position
        except Exception:
            return False
        if pos is None:
            return False
        try:
            new_x = float(pos[0])
            new_y = float(pos[1])
        except (RuntimeError, ValueError, TypeError, AttributeError, IndexError):
            return False
        if idx < len(self._scene_pos_x):
            self._scene_pos_x[idx] = new_x
        if idx < len(self._scene_pos_y):
            self._scene_pos_y[idx] = new_y
        if idx < len(self._scene_stable_ids):
            self._canvas_widget.set_node_position(self._scene_stable_ids[idx], new_x, new_y)
        return True

    def _find_scene_node_index(self, item) -> Optional[int]:
        """Return the scene index for a model item by identity or prim path."""
        for index, model_node in enumerate(self._scene_model_nodes):
            if model_node is item:
                return index
        item_path = getattr(item, "prim_path", None)
        if item_path is None:
            return None
        for index, model_node in enumerate(self._scene_model_nodes):
            if getattr(model_node, "prim_path", None) == item_path:
                return index
        return None

    # ------------------------------------------------------------------
    # Snapshot: pre-extract model data in Python for fast C++ dict reads
    # ------------------------------------------------------------------

    def _snapshot_for_build(self) -> list:
        vm = self._ensure_input_node_vm()
        snapshot = self._model.export_snapshot(self._port_grouping, input_node_view_model=vm)
        return snapshot

    def _ensure_input_node_vm(self):
        """Return the InputNode view model (lazy — rebuild happens inside export_snapshot)."""
        ctx_mgr = self._input_node_context_manager
        ctx_name = self._input_node_current_context
        if ctx_mgr is None or not ctx_name or not self._model:
            return None
        from ..models.graph.input_node_view import InputNodeViewModel

        if self._input_node_vm is None:
            self._input_node_vm = InputNodeViewModel()
        self._input_node_vm._context_manager_ref = ctx_mgr
        self._input_node_vm._current_context = ctx_name
        return self._input_node_vm

    def set_input_node_context(self, context_manager, current_context_name: str):
        """Called by the widget when the context changes."""
        self._input_node_context_manager = context_manager
        self._input_node_current_context = current_context_name
        if self._input_node_vm is not None:
            self._input_node_vm._built = False

    def set_validation_errors(self, errors_by_path: dict) -> None:
        """Store prim_path -> error message mapping for tooltip enrichment."""
        self._validation_errors_by_path = errors_by_path or {}

    # ------------------------------------------------------------------
    # Core rebuild — native C++ build, layout, positions, push
    # ------------------------------------------------------------------

    def _rebuild_core(self) -> None:
        if not self._model:
            return

        self._rebuilding = True

        try:
            from omni.kit.window.material_graph._graphCanvas import (
                native_build_from_snapshot,
                set_color_noodles,
            )

            from ..settings.settings import Settings

            set_color_noodles(Settings.color_noodles())
            snapshot = self._snapshot_for_build()
            self._upload_node_icons(snapshot)
            result = native_build_from_snapshot(snapshot)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(logger, "graph canvas rebuild failed", action="rebuild", exc=exc)
            self._rebuilding = False
            return

        scene = result.scene
        edges = result.edges
        port_counts = result.visible_port_counts
        model_nodes = result.model_nodes

        self._scene_model_nodes = list(model_nodes)
        self._scene_stable_ids = list(result.stable_ids)
        self._scene_pos_x = list(result.node_pos_x)
        self._scene_pos_y = list(result.node_pos_y)
        self._scene_widths = list(result.node_widths)
        self._scene_heights = list(result.node_heights)
        self._scene_port_start_y = list(result.node_port_start_y)
        scene_is_backdrop = []
        scene_has_menu = []
        scene_port_sides = []
        fb_map = {}
        for ni, ns in enumerate(snapshot):
            scene_is_backdrop.append(bool(ns.get("is_backdrop")))
            scene_has_menu.append(bool(ns.get("has_menu")))
            scene_port_sides.append(
                [(ps.get("inputs") is not None, ps.get("outputs") is not None) for ps in ns.get("ports", [])]
            )
            if ns.get("valid", True):
                continue
            for pi, ps in enumerate(ns.get("ports", [])):
                port_obj = ps.get("port")
                if port_obj is not None:
                    fb_map[(ni, pi)] = port_obj
        self._scene_is_backdrop = scene_is_backdrop
        self._scene_has_menu = scene_has_menu
        self._scene_port_sides = scene_port_sides
        self._node_to_stable = {}
        for i, mn in enumerate(self._scene_model_nodes):
            if i < len(self._scene_stable_ids):
                self._node_to_stable[id(mn)] = self._scene_stable_ids[i]

        self._fallback_port_map = fb_map

        self._layout = self._build_layout(edges, 20.0, 200.0)

        unpositioned = set()
        for i, ns in enumerate(snapshot):
            pc = port_counts[i] if i < len(port_counts) else 0
            nh = result.node_heights[i] if i < len(result.node_heights) else (36.0 + pc * 22.0 + 4.0)
            self._layout.set_size(i, 200.0, nh)
            if ns.get("pos") is None:
                unpositioned.add(i)

        layout_patches: List[Tuple[int, float, float]] = []
        if unpositioned:
            input_ids = []
            output_ids = []
            for i in unpositioned:
                mn = model_nodes[i] if i < len(model_nodes) else None
                if mn is not None and hasattr(mn, "source"):
                    try:
                        tn = type(mn).get_type_name()
                    except Exception:
                        tn = ""
                    if tn == "InputNode":
                        input_ids.append(i)
                    elif tn == "OutputNode":
                        output_ids.append(i)

            if input_ids or output_ids:
                self._layout.pin_io_layers(input_ids, output_ids)

            self._layout.update_positions()
            for i in unpositioned:
                new_pos = self._layout.get_position(i)
                if new_pos:
                    try:
                        positioned = self._commit_node_position(model_nodes[i], new_pos)
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logger.warning(
                            "automatic node positioning failed for node='%s' requested_position=%s: %s; "
                            "the node remains unpositioned",
                            getattr(model_nodes[i], "path", model_nodes[i]),
                            new_pos,
                            exc,
                        )
                        positioned = False
                    if positioned:
                        self._scene_pos_x[i] = new_pos[0]
                        self._scene_pos_y[i] = new_pos[1]
                    if positioned and i < len(self._scene_stable_ids):
                        layout_patches.append((self._scene_stable_ids[i], new_pos[0], new_pos[1]))

        self._ensure_canvas_widget()

        needs_frame = self._needs_initial_frame

        if scene and self._canvas_widget:
            if needs_frame:
                self._focus_initial_frame_if_ready()

            self._register_icon_textures()
            self._canvas_widget.set_scene(scene)
            self._last_scene = scene

            for sid, px, py in layout_patches:
                self._canvas_widget.set_node_position(sid, px, py)

            self._selection = list(self._model.selection or []) if self._model else []
            self._update_scene_selection()

            if self._breadcrumb_path:
                try:
                    self._canvas_widget.set_breadcrumb(self._breadcrumb_path)
                except Exception:
                    pass
        else:
            pass
        self._rebuilding = False

    def _focus_initial_frame_if_ready(self) -> bool:
        """Focus the initial graph once the canvas has usable geometry."""
        if not self._needs_initial_frame:
            return True
        if not self._scene_model_nodes:
            self._needs_initial_frame = False
            self._initial_frame_retry_count = 0
            return True
        focused = self.focus_on_nodes()
        self._needs_initial_frame = not focused
        if self._needs_initial_frame:
            self._initial_frame_retry_count += 1
            if self._initial_frame_retry_count < self._INITIAL_FRAME_MAX_RETRIES:
                self._schedule_rebuild_work()
            else:
                self._needs_initial_frame = False
        else:
            self._initial_frame_retry_count = 0
        return focused

    # ------------------------------------------------------------------
    # Layout builder (native C++ Sugiyama)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_layout(edges, vdist, hdist):
        try:
            from omni.kit.window.material_graph._graphCanvas import SugiyamaLayoutNative

            layout = SugiyamaLayoutNative(edges, vdist, hdist)
            return layout
        except ImportError:
            from omni.kit.widget.graph.graph_layout import SugiyamaLayout

            return SugiyamaLayout(edges=edges, vertical_distance=vdist, horizontal_distance=hdist)

    # ------------------------------------------------------------------
    # Canvas widget lifecycle
    # ------------------------------------------------------------------

    def _ensure_canvas_widget(self) -> None:
        try:
            from omni.kit.window.material_graph._graphCanvas import GraphCanvasWidget
        except ImportError:
            return

        with self.__root_frame:
            self.__root_stack = ui.ZStack()
            with self.__root_stack:
                placer = ui.Placer(offset_x=0, offset_y=0)
                with placer:
                    self._canvas_widget = GraphCanvasWidget.create()
                    try:
                        from ..config.graph_style import GraphStyle

                        self._canvas_widget.set_style_config(GraphStyle.to_dict())
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Node icons (ImGui textures via ByteImageProvider)
    # ------------------------------------------------------------------

    def _resolve_node_icon(self, model_node) -> Tuple[Optional[str], int]:
        """Return (icon_path, icon_color) for a node, or (None, 0)."""
        import os

        def _normalize(p):
            if not p:
                return p
            return os.path.abspath(str(p))

        try:
            from ..models.catalog.registries.icon_registry import get_icon as get_catalog_icon
            from ..models.graph.nodes.shader import ShaderModel

            np = self._model[model_node]

            item = np
            prim_model = getattr(np, "prim_model", None)
            if prim_model is not None and not isinstance(item, ShaderModel):
                item = prim_model

            if isinstance(item, ShaderModel):
                context_name = getattr(item, "context_name", None)
                sdr_node = getattr(item, "_sdr_node", None)
                if sdr_node and context_name:
                    icon, icon_color = get_catalog_icon(context_name, sdr_node.GetIdentifier())
                    if icon:
                        return (_normalize(icon), icon_color or 0xFFFFFFFF)
        except Exception:
            pass

        # Check the current context plugin's get_style() for a default icon
        try:
            ctx_mgr = self._input_node_context_manager
            ctx_name = self._input_node_current_context
            if ctx_mgr and ctx_name:
                handle = ctx_mgr.get_context(ctx_name)
                if handle.is_valid and handle.plugin:
                    style = handle.plugin.get_style()
                    icon_entry = style.get("Graph.Node.Icon", {})
                    url = icon_entry.get("image_url", "")
                    if url:
                        return (_normalize(url), 0xFFFFFFFF)
        except Exception:
            pass

        try:
            from ..config.paths import Paths

            fallback = str(Paths.ICON_PATH / "type_function_noBorder_dark.svg")
            return (_normalize(fallback), 0xFFFFFFFF)
        except Exception:
            return (None, 0)

    def _resolve_node_preview(self, model_node) -> Optional[str]:
        """Return a texture preview path for a node, or None."""
        import os

        try:
            np = self._model[model_node]
            preview = getattr(np, "preview", None)
            if preview:
                return os.path.abspath(str(preview))
        except Exception:
            pass
        return None

    def _upload_node_icons(self, snapshot: list) -> None:
        """Resolve icon paths and inject into snapshot dicts."""
        if not self._model:
            return

        icon_paths: set = set()
        count = 0

        for ns in snapshot:
            mn = ns.get("node")
            if mn is None:
                continue

            icon_path, _ = self._resolve_node_icon(mn)
            if icon_path:
                ns["icon_url"] = icon_path
                icon_paths.add(icon_path)
                count += 1

            preview_path = self._resolve_node_preview(mn)
            if preview_path:
                ns["preview_url"] = preview_path
                icon_paths.add(preview_path)

        self._pending_icon_paths = icon_paths

    def _register_icon_textures(self) -> None:
        """Register pending icon paths with the C++ widget for texture loading."""
        if not self._canvas_widget:
            return

        self._register_expansion_icons()

        paths = getattr(self, "_pending_icon_paths", None)
        if not paths:
            return
        for p in paths:
            self._canvas_widget.set_icon_path(p, p)
        self._pending_icon_paths = None

    def _register_expansion_icons(self) -> None:
        """Register the 3 expansion-state SVG icons with well-known keys."""
        try:
            from ..config.paths import Paths

            base = Paths.ICON_PATH / "node"
            mapping = {
                "__expand_open": str(base / "expand_open.svg"),
                "__expand_minimized": str(base / "expand_minimized.svg"),
                "__expand_closed": str(base / "expand_closed.svg"),
            }
            for key, path in mapping.items():
                self._canvas_widget.set_icon_path(key, path)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API expected by GraphEditorCoreWidget / GraphWidget
    # ------------------------------------------------------------------

    def focus_on_nodes(self, nodes=None) -> bool:
        if self._suppress_focus:
            self._suppress_focus = False
            return False
        if not self._model:
            return False

        min_x = min_y = max_x = max_y = None

        if nodes:
            node_set = set(id(n) for n in nodes)
            for i, mn in enumerate(self._scene_model_nodes):
                if id(mn) not in node_set:
                    continue
                if i >= len(self._scene_pos_x):
                    continue
                x, y = self._scene_pos_x[i], self._scene_pos_y[i]
                w = self._scene_widths[i] if i < len(self._scene_widths) else 200.0
                h = self._scene_heights[i] if i < len(self._scene_heights) else 200.0
                if min_x is None:
                    min_x, min_y = x, y
                    max_x, max_y = x + w, y + h
                else:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x + w)
                    max_y = max(max_y, y + h)
        else:
            for i in range(len(self._scene_pos_x)):
                x, y = self._scene_pos_x[i], self._scene_pos_y[i]
                w = self._scene_widths[i] if i < len(self._scene_widths) else 200.0
                h = self._scene_heights[i] if i < len(self._scene_heights) else 200.0
                if min_x is None:
                    min_x, min_y = x, y
                    max_x, max_y = x + w, y + h
                else:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x + w)
                    max_y = max(max_y, y + h)

        if min_x is None:
            return False

        content_w = max_x - min_x
        content_h = max_y - min_y
        if content_w <= 0 or content_h <= 0:
            return False

        pad_x = content_w * 0.1
        pad_y = content_h * 0.1
        min_x -= pad_x
        min_y -= pad_y
        content_w += 2 * pad_x
        content_h += 2 * pad_y

        cur_zoom = self.__root_frame.zoom
        raw_w = self.__root_frame.computed_width
        raw_h = self.__root_frame.computed_height
        vw = raw_w * cur_zoom
        vh = raw_h * cur_zoom
        if vw <= 0 or vh <= 0:
            return False

        z = min(vw / content_w, vh / content_h)
        z = max(min(z, self.__root_frame.zoom_max - FLOATING_DELTA), self.__root_frame.zoom_min + FLOATING_DELTA)

        px = -min_x * z + vw / 2 - content_w * z / 2
        py = -min_y * z + vh / 2 - content_h * z / 2

        self.__root_frame.zoom = z
        self.__root_frame.pan_x = px
        self.__root_frame.pan_y = py
        return True

    def layout_all(self) -> None:
        if not self._model:
            return
        for node in self._model.nodes or []:
            try:
                if not self._commit_node_position(node, None):
                    logger.warning("clear node position was rejected for %s", getattr(node, "path", node))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "automatic-layout reset failed to clear position for node='%s': %s; "
                    "its existing position was preserved",
                    getattr(node, "path", node),
                    exc,
                )
        self._on_item_changed(None)

    @property
    def raster_nodes(self):
        return False

    def set_expansion(self, state) -> None:
        if not self._model:
            return
        for node in self._model.nodes or []:
            self._model[node].expansion_state = state

    def destroy(self) -> None:
        self._release_connection_visual_callback()
        self._close_description_editor()
        self._close_rename_editor()
        self._close_color_picker()
        if self._port_rename_dialog:
            try:
                self._port_rename_dialog.hide()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            self._port_rename_dialog = None
        if self._rename_poll_task:
            self._rename_poll_task.cancel()
            self._rename_poll_task = None
        if self._desc_edit_poll_task:
            self._desc_edit_poll_task.cancel()
            self._desc_edit_poll_task = None
        if hasattr(self, "_edit_poll_task") and self._edit_poll_task:
            self._edit_poll_task.cancel()
            self._edit_poll_task = None
        if hasattr(self, "_tooltip_task") and self._tooltip_task:
            self._tooltip_task.cancel()
            self._tooltip_task = None
        self._cancel_deferred_disconnects()
        self._detach_rebuild_kit_subscription()
        self._model_subscription = None
        self._selection_subscription = None
        self._node_subscription = None
        self._model = None
        self._canvas_widget = None
        self._layout = None
        self._scene_model_nodes = []
        self._scene_stable_ids = []
        self._scene_pos_x = []
        self._scene_pos_y = []
        self._scene_widths = []
        self._scene_heights = []
        self._scene_port_start_y = []
        self._scene_is_backdrop = []
        self._scene_has_menu = []
        self._node_to_stable = {}
        self._last_scene = None
        self._parent_mouse_pressed_fn = None
        self._parent_mouse_released_fn = None
        self._parent_mouse_moved_fn = None
        self._parent_mouse_double_clicked_fn = None
        if self.__root_frame:
            self.__root_frame = None
        self.__root_stack = None
