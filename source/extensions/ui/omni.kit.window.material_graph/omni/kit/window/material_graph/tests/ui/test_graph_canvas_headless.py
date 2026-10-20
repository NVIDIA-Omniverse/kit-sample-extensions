"""Fast non-rendering coverage for GraphCanvasView controller seams."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import carb.input
import omni.kit.test
from omni.kit.widget.graph.graph_model import GraphModel
from pxr import Sdf, Usd, UsdShade

from ...scripts.commands.result import CommandResult
from ...scripts.ui import graph_canvas_view as canvas_module
from ...scripts.ui.graph_canvas_view import GraphCanvasView


class _Model:
    def __init__(self, mapping=None) -> None:
        self.mapping = mapping or {}
        self.selection = []
        self.nodes = []
        self._item_changed = MagicMock()
        self.subscribe_item_changed = MagicMock(return_value="item-sub")
        self.subscribe_selection_changed = MagicMock(return_value="selection-sub")
        self.subscribe_node_changed = MagicMock(return_value="node-sub")

    def __getitem__(self, item):
        return self.mapping[item]


class TestGraphCanvasHeadless(omni.kit.test.AsyncTestCase):
    """Exercise canvas state transitions without constructing its native widget."""

    @staticmethod
    def _view() -> GraphCanvasView:
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = None
        view._canvas_widget = None
        view._model_subscription = None
        view._selection_subscription = None
        view._node_subscription = None
        view._connection_visual_cb_target = None
        view._position_change_consumer = None
        view._selection = []
        view._scene_model_nodes = []
        view._scene_stable_ids = []
        view._scene_pos_x = []
        view._scene_pos_y = []
        view._scene_widths = []
        view._scene_heights = []
        view._scene_port_start_y = []
        view._scene_port_sides = []
        view._scene_is_backdrop = []
        view._scene_has_menu = []
        view._node_to_stable = {}
        view._fallback_port_map = {}
        view._last_scene = None
        view._needs_initial_frame = False
        view._initial_frame_retry_count = 0
        view._suppress_focus = False
        view._rebuilding = False
        view._skip_deferred_rebuild_once = False
        view._rebuild_kit_sub = None
        view._breadcrumb_path = []
        view._edit_poll_task = None
        view._rename_poll_task = None
        view._desc_edit_poll_task = None
        view._tooltip_task = None
        view._color_picker_widget = None
        view._port_rename_dialog = None
        view._port_context_menu = None
        view._input_node_context_manager = None
        view._input_node_current_context = None
        view._input_node_vm = None
        view._pending_icon_paths = None
        view._layout = None
        view._parent_mouse_pressed_fn = None
        view._parent_mouse_released_fn = None
        view._parent_mouse_moved_fn = None
        view._parent_mouse_double_clicked_fn = None
        view._event_consumed = False
        view._marquee_start = None
        view._marquee_active = False
        view._drag_node = None
        view._drag_start_canvas = None
        view._drag_active = False
        view._drag_threshold = 3.0
        view._noodle_source = None
        view._pending_port_hit = None
        view._pending_port_canvas = None
        view._noodle_rewire = False
        view._noodle_rewire_port = None
        view._noodle_rewire_old_source = None
        view._resize_node_index = None
        view._resize_start_canvas = None
        view._resize_start_size = None
        view._deferred_disconnect_task = None
        view._deferred_disconnect_ports = []
        view._rename_opened_frame = 0
        view._last_tooltip_node = -1
        view._last_tooltip_port = -1
        view._validation_errors_by_path = {}
        view._GraphCanvasView__root_frame = None
        view._GraphCanvasView__root_stack = None
        return view

    async def test_constructor_callback_chaining_and_attribute_delegation(self) -> None:
        """The public canvas adapter should initialize and chain callbacks without a rendered window."""
        frame = MagicMock()
        frame.zoom_min = None
        frame.zoom_max = None
        frame.delegated_value = "delegated"
        scheduled = []

        def capture(coro, _label):
            coro.close()
            task = MagicMock()
            scheduled.append(task)
            return task

        with (
            patch.object(canvas_module.ui, "CanvasFrame", return_value=frame) as canvas_frame,
            patch.object(canvas_module, "ensure_future_logged", side_effect=capture),
        ):
            view = GraphCanvasView(
                model=None,
                delegate=object(),
                port_grouping=True,
                virtual_ports=True,
                smooth_zoom=True,
                zoom_min=0.2,
                zoom_max=2.0,
            )

        canvas_frame.assert_called_once_with(style_type_name_override="Graph")
        self.assertEqual((frame.zoom_min, frame.zoom_max), (0.2, 2.0))
        self.assertEqual(view.delegated_value, "delegated")
        self.assertTrue(view._port_grouping)
        self.assertEqual(len(scheduled), 1)
        frame.set_zoom_key_shortcut.assert_called_once()

        view._on_mouse_pressed = MagicMock()
        view._on_mouse_released = MagicMock()
        view._on_mouse_moved = MagicMock()
        view._on_mouse_double_clicked = MagicMock()
        pressed = MagicMock()
        released = MagicMock()
        moved = MagicMock()
        doubled = MagicMock()
        view.set_mouse_pressed_fn(pressed)
        view.set_mouse_released_fn(released)
        view.set_mouse_moved_fn(moved)
        view.set_mouse_double_clicked_fn(doubled)
        view._combined_mouse_pressed(1, 2, 0, 3)
        view._combined_mouse_released(1, 2, 0, 3)
        view._combined_mouse_moved(1, 2, 3, True)
        view._combined_mouse_double_clicked(1, 2, 0, 3)
        pressed.assert_called_once_with(1, 2, 0, 3)
        released.assert_called_once_with(1, 2, 0, 3)
        moved.assert_called_once_with(1, 2, 3, True)
        doubled.assert_called_once_with(1, 2, 0, 3)

        view._on_mouse_pressed.side_effect = lambda *_args: setattr(view, "_event_consumed", True)
        view._combined_mouse_pressed(4, 5, 0, 6)
        pressed.assert_called_once()
        view.destroy()

    async def test_headless_geometry_hit_testing_covers_node_port_and_backdrop_regions(self) -> None:
        """Canvas-space hit testing should respect z-order, port sides, and backdrop controls."""

        class Regular:
            @classmethod
            def get_type_name(cls):
                return "Shader"

        class Input:
            @classmethod
            def get_type_name(cls):
                return "InputNode"

        class Output:
            @classmethod
            def get_type_name(cls):
                return "OutputNode"

        view = self._view()
        backdrop, regular, input_node, output_node = object(), Regular(), Input(), Output()
        view._scene_model_nodes = [backdrop, regular, input_node, output_node]
        view._scene_pos_x = [0.0, 20.0, 300.0, 500.0]
        view._scene_pos_y = [0.0, 20.0, 0.0, 0.0]
        view._scene_widths = [260.0, 120.0, 120.0, 120.0]
        view._scene_heights = [180.0, 100.0, 100.0, 100.0]
        view._scene_port_start_y = [32.0, 32.0, 24.0, 32.0]
        view._scene_is_backdrop = [True, False, False, False]
        view._scene_has_menu = [False, True, False, False]
        view._scene_port_sides = [[], [(True, True)], [(True, True)], [(True, False)]]
        ports = [object(), object(), object()]
        view._get_model_port = MagicMock(side_effect=lambda ni, _pi: ports[ni - 1] if ni else None)
        view._is_material_output_sink_port = MagicMock(return_value=False)
        view._model = _Model({port: SimpleNamespace(inputs=[], outputs=[]) for port in ports})

        root = SimpleNamespace(screen_to_canvas_x=lambda x: x + 1, screen_to_canvas_y=lambda y: y + 2)
        view._GraphCanvasView__root_frame = root
        self.assertEqual(view._screen_to_canvas(3, 4), (4, 6))
        self.assertIs(view._find_node_at(30, 30), regular)
        self.assertEqual(view._find_node_at(30, 30, return_index=True), (regular, 1))
        self.assertIs(view._find_node_at(10, 100), backdrop)
        self.assertEqual(view._find_node_index_at(30, 30), 1)
        self.assertIsNone(view._find_node_index_at(900, 900))
        self.assertEqual(view._find_backdrop_resize_at(255, 175), 0)
        self.assertEqual(view._find_backdrop_color_swatch_at(13, 9), 0)
        self.assertEqual(view._find_backdrop_header_at(50, 10), 0)
        self.assertEqual(view._find_backdrop_body_at(50, 80), 0)
        self.assertEqual(view._find_header_name_at(75, 25), 1)
        self.assertEqual(view._find_expansion_icon_at(105, 25), 1)
        self.assertEqual(view._find_node_menu_at(125, 25), 1)
        self.assertEqual(view._find_nodes_in_rect(10, 10, 160, 130), [backdrop, regular])

        self.assertEqual(view._find_port_at(20, 63), (1, 0, True))
        self.assertEqual(view._find_port_at(140, 63), (1, 0, False))
        self.assertEqual(view._find_port_at(300, 32), (2, 0, True))
        self.assertIsNone(view._find_port_at(620, 43))
        self.assertIsNone(view._find_port_at(80, 10))
        self.assertEqual(view._port_canvas_pos(1, 0, True), (20.0, 63.0))
        self.assertEqual(view._port_canvas_pos(1, 0, False), (140.0, 63.0))
        self.assertEqual(view._find_port_pin_at_canvas(20, 63), (1, 0, True))
        self.assertIsNone(view._find_port_pin_at_canvas(35, 63))

        view._input_node_vm = SimpleNamespace(
            _scene_group_indices={0},
            _synthetic_row_indices={"other": 1},
            _scene_idx_to_port={0: ports[1]},
        )
        self.assertEqual(view._input_node_port_idx_at(2, 25), 0)
        self.assertIs(view._resolve_port(2, 0), ports[1])
        self.assertEqual(view._port_canvas_pos(2, 1, False), (420.0, 51.0))
        view._is_group_port = MagicMock(return_value=True)
        self.assertEqual(view._find_group_icon_at(320, 27), (2, 0))
        self.assertEqual(view._find_port_hit_at_canvas(350, 32), (2, 0, False))
        self.assertEqual(view._find_port_hit_at_canvas(550, 43), (3, 0, True))

    async def test_hover_tooltips_include_port_metadata_context_and_validation(self) -> None:
        """Native hover state should resolve rich node and port diagnostics from model data."""

        class Input:
            @classmethod
            def get_type_name(cls):
                return "InputNode"

        class Port:
            pass

        view = self._view()
        node = Input()
        port = Port()
        port.proxy_attribute = SimpleNamespace(name="inputs:value", connectability=UsdShade.Tokens.interfaceOnly)
        node.prim = SimpleNamespace(GetPath=lambda: Sdf.Path("/Node"))
        port_proxy = SimpleNamespace(
            tooltip_text="",
            name="Value",
            type="float",
            variability="uniform",
        )
        node_proxy = SimpleNamespace(tooltip_text="", name="Broken", type="Shader", valid=False)
        view._model = _Model({node: node_proxy, port: port_proxy})
        view._scene_model_nodes = [node]
        view._scene_stable_ids = [17]
        view._resolve_port = MagicMock(return_value=port)
        view._input_node_vm = SimpleNamespace(
            get_port_contexts=lambda _port: {"mdl", "mtlx"},
            get_io_state=lambda _port: 1,
        )
        view._input_node_current_context = "mtlx"
        view._validation_errors_by_path = {
            "/Node.inputs:value": "Invalid input",
            "/Node": "Invalid shader",
        }
        canvas = MagicMock()
        canvas.hover_node_id = 17
        canvas.hover_port_index = 0
        view._canvas_widget = canvas
        view._update_hover_tooltip()
        port_text = canvas.set_tooltip_text.call_args.args[0]
        self.assertIn("@Type: float", port_text)
        self.assertIn("@Connectability: Interface Only", port_text)
        self.assertIn("@Used by: mtlx, mdl", port_text)
        self.assertIn("[Error] Invalid input", port_text)

        canvas.set_tooltip_text.reset_mock()
        canvas.hover_port_index = -1
        view._update_hover_tooltip()
        node_text = canvas.set_tooltip_text.call_args.args[0]
        self.assertIn("@Shader", node_text)
        self.assertIn("[Error] Invalid shader", node_text)
        canvas.hover_node_id = -1
        view._update_hover_tooltip()
        canvas.set_tooltip_text.assert_called_with("")

    async def test_mouse_resize_drag_marquee_and_noodle_paths_are_model_driven(self) -> None:
        """Press/move/release behavior should mutate model state without pointer automation."""
        view = self._view()
        first, second = object(), object()
        first_proxy = SimpleNamespace(size=None, position=None, name="First")
        second_proxy = SimpleNamespace(size=None, position=None, name="Second")
        model = _Model({first: first_proxy, second: second_proxy})
        model.size_begin_edit = MagicMock()
        model.size_end_edit = MagicMock()
        view._model = model
        view._scene_model_nodes = [first, second]
        view._scene_stable_ids = [1, 2]
        view._scene_pos_x = [0.0, 200.0]
        view._scene_pos_y = [0.0, 0.0]
        view._scene_widths = [100.0, 100.0]
        view._scene_heights = [80.0, 80.0]
        view._scene_is_backdrop = [True, False]
        view._scene_has_menu = [False, False]
        view._GraphCanvasView__root_frame = SimpleNamespace(
            screen_to_canvas_x=lambda x: x,
            screen_to_canvas_y=lambda y: y,
        )
        canvas = MagicMock()
        view._canvas_widget = canvas

        view._on_mouse_pressed(95, 75, 0, 0)
        self.assertEqual(view._resize_node_index, 0)
        view._on_mouse_moved(125, 105, 0, True)
        self.assertEqual((view._scene_widths[0], view._scene_heights[0]), (130.0, 110.0))
        view._on_mouse_released(125, 105, 0, 0)
        self.assertEqual(first_proxy.size, (130.0, 110.0))
        model.size_end_edit.assert_called_once_with(first)

        view._scene_is_backdrop = [False, False]
        view._find_backdrop_resize_at = MagicMock(return_value=None)
        view._find_node_menu_at = MagicMock(return_value=None)
        view._find_expansion_icon_at = MagicMock(return_value=None)
        view._find_group_icon_at = MagicMock(return_value=None)
        view._find_port_pin_at_canvas = MagicMock(return_value=None)
        view._find_node_at = MagicMock(return_value=second)
        view._on_mouse_pressed(210, 10, 0, 0)
        self.assertEqual(model.selection, [second])
        view._on_mouse_moved(225, 30, 0, True)
        self.assertTrue(view._drag_active)
        view._commit_node_position = MagicMock()
        view._on_mouse_released(225, 30, 0, 0)
        view._commit_node_position.assert_called_once_with(second, (215.0, 20.0))

        view._find_node_at.return_value = None
        view._on_mouse_pressed(0, 0, 0, 0)
        view._on_mouse_moved(350, 100, 0, True)
        view._on_mouse_released(350, 100, 0, 0)
        self.assertEqual(model.selection, [first, second])
        canvas.clear_marquee.assert_called()

        output_port, input_port = object(), object()
        model.mapping.update(
            {
                output_port: SimpleNamespace(inputs=[], outputs=[]),
                input_port: SimpleNamespace(inputs=[], outputs=[]),
            }
        )
        model.can_connect = MagicMock(return_value=True)
        view._noodle_source = (0, 0, False)
        view._resolve_port = MagicMock(side_effect=[output_port, input_port])
        view._find_port_hit_at_canvas = MagicMock(return_value=(1, 0, True))
        view._port_has_input = MagicMock(return_value=True)
        view._is_material_output_sink_port = MagicMock(return_value=False)
        view._notify_connection_changed = MagicMock()
        view._on_mouse_released(200, 20, 0, 0)
        self.assertEqual(model[input_port].inputs, [output_port])
        view._notify_connection_changed.assert_called_once()

    async def test_selection_modifiers_cover_click_and_marquee_semantics(self) -> None:
        """Shift/Ctrl selection semantics should be testable without moving a system pointer."""
        view = self._view()
        first, second = object(), object()
        model = _Model({first: SimpleNamespace(), second: SimpleNamespace()})
        model.selection = [first]
        view._model = model
        view._selection = [first]
        view._scene_model_nodes = [first, second]
        view._scene_stable_ids = [1, 2]
        view._scene_pos_x = [0.0, 200.0]
        view._scene_pos_y = [0.0, 0.0]
        view._scene_widths = [100.0, 100.0]
        view._scene_heights = [80.0, 80.0]
        view._scene_is_backdrop = [False, False]
        view._scene_has_menu = [False, False]
        view._GraphCanvasView__root_frame = SimpleNamespace(
            screen_to_canvas_x=lambda x: x,
            screen_to_canvas_y=lambda y: y,
        )
        view._find_backdrop_resize_at = MagicMock(return_value=None)
        view._find_node_menu_at = MagicMock(return_value=None)
        view._find_expansion_icon_at = MagicMock(return_value=None)
        view._find_group_icon_at = MagicMock(return_value=None)
        view._find_port_pin_at_canvas = MagicMock(return_value=None)
        view._find_node_at = MagicMock(return_value=second)
        view._update_scene_selection = MagicMock()
        view._canvas_widget = MagicMock()

        shift = int(carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT)
        control = int(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL)
        view._on_mouse_pressed(210, 10, 0, shift)
        self.assertEqual(model.selection, [first, second])

        view._find_node_at.return_value = first
        view._on_mouse_pressed(10, 10, 0, control)
        self.assertEqual(model.selection, [second])
        view._on_mouse_pressed(10, 10, 0, control)
        self.assertEqual(model.selection, [second, first])

        # Shift-marquee adds hits to the existing selection.
        model.selection = [first]
        view._selection = [first]
        view._drag_node = None
        view._drag_active = False
        view._marquee_start = (150, -10)
        view._marquee_active = True
        view._on_mouse_released(350, 100, 0, shift)
        self.assertEqual(model.selection, [first, second])

        # Ctrl-marquee subtracts hits from the existing selection.
        view._marquee_start = (150, -10)
        view._marquee_active = True
        view._on_mouse_released(350, 100, 0, control)
        self.assertEqual(model.selection, [first])

    async def test_rebuild_core_projects_native_snapshot_into_canvas_state(self) -> None:
        """A native snapshot result should populate caches, layout, fallback ports, and scene selection."""

        class Input:
            source = object()

            @classmethod
            def get_type_name(cls):
                return "InputNode"

        view = self._view()
        positioned, unpositioned = object(), Input()
        model = _Model(
            {
                positioned: SimpleNamespace(position=(10.0, 20.0)),
                unpositioned: SimpleNamespace(position=None),
            }
        )
        model.selection = [positioned]
        view._model = model
        fallback_port = object()
        snapshot = [
            {"node": positioned, "pos": (10.0, 20.0), "ports": [], "valid": True},
            {
                "node": unpositioned,
                "pos": None,
                "ports": [{"port": fallback_port, "inputs": [], "outputs": None}],
                "valid": False,
                "is_backdrop": False,
                "has_menu": True,
            },
        ]
        scene = object()
        result = SimpleNamespace(
            scene=scene,
            edges=[(0, 1)],
            visible_port_counts=[0, 1],
            model_nodes=[positioned, unpositioned],
            stable_ids=[10, 20],
            node_pos_x=[10.0, 0.0],
            node_pos_y=[20.0, 0.0],
            node_widths=[200.0, 200.0],
            node_heights=[80.0, 100.0],
            node_port_start_y=[32.0, 24.0],
        )
        layout = MagicMock()
        layout.get_position.return_value = (300.0, 40.0)
        canvas = MagicMock()
        view._canvas_widget = canvas
        view._snapshot_for_build = MagicMock(return_value=snapshot)
        view._upload_node_icons = MagicMock()
        view._build_layout = MagicMock(return_value=layout)
        view._ensure_canvas_widget = MagicMock()
        view._focus_initial_frame_if_ready = MagicMock(return_value=True)
        view._needs_initial_frame = True

        with (
            patch(
                "omni.kit.window.material_graph._graphCanvas.native_build_from_snapshot",
                return_value=result,
            ),
            patch("omni.kit.window.material_graph._graphCanvas.set_color_noodles"),
        ):
            view._rebuild_core()

        self.assertFalse(view._rebuilding)
        self.assertEqual(view._scene_stable_ids, [10, 20])
        self.assertEqual(view._fallback_port_map, {(1, 0): fallback_port})
        self.assertEqual(view._node_to_stable[id(unpositioned)], 20)
        self.assertEqual(model[unpositioned].position, (300.0, 40.0))
        layout.pin_io_layers.assert_called_once_with([1], [])
        canvas.set_scene.assert_called_once_with(scene)
        canvas.set_node_position.assert_called_with(20, 300.0, 40.0)
        self.assertIs(view._last_scene, scene)

    async def test_rebuild_failure_is_logged_and_contained(self) -> None:
        """Native snapshot failures should leave the canvas reusable and preserve the traceback."""
        view = self._view()
        view._model = _Model()
        view._snapshot_for_build = MagicMock(side_effect=OSError("snapshot failed"))

        with (
            patch("omni.kit.window.material_graph._graphCanvas.set_color_noodles"),
            patch.object(canvas_module, "log_exception") as log_failure,
        ):
            view._rebuild_core()

        self.assertFalse(view._rebuilding)
        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], OSError)

    async def test_context_menus_expansion_and_nested_port_resolution_are_headless(self) -> None:
        """Node actions and expansion state should route through registries and model proxies."""
        view = self._view()
        node, root_port, child_port = object(), object(), object()
        node_proxy = SimpleNamespace(
            type="Shader",
            expansion_state=GraphModel.ExpansionState.OPEN,
            ports=[root_port],
        )
        root_proxy = SimpleNamespace(
            ports=[child_port],
            expansion_state=GraphModel.ExpansionState.OPEN,
        )
        child_proxy = SimpleNamespace(ports=None)
        model = _Model({node: node_proxy, root_port: root_proxy, child_port: child_proxy})
        view._model = model
        view._scene_model_nodes = [node]
        view._scene_stable_ids = [5]
        callback = MagicMock()
        menu = MagicMock()

        with (
            patch.object(canvas_module.ui, "Menu", return_value=menu),
            patch.object(canvas_module.ui, "MenuItem") as menu_item,
            patch(
                "omni.kit.window.material_graph.scripts.api.context_menu.get_node_menu_items",
                return_value=[SimpleNamespace(label="Inspect", callback=callback)],
            ),
            patch("omni.kit.window.material_graph.scripts.ui.interaction.menu_utils.show_menu_at_cursor") as show_menu,
        ):
            view._show_node_context_menu(0)
        menu_item.assert_called_once()
        show_menu.assert_called_once_with(menu)
        GraphCanvasView._safe_node_menu_callback(callback, "Shader", Sdf.Path("/Node"))
        callback.assert_called_once_with("Shader", Sdf.Path("/Node"))

        failing_callback = MagicMock(side_effect=KeyError("callback failed"))
        with patch.object(canvas_module, "log_exception") as log_failure:
            GraphCanvasView._safe_node_menu_callback(failing_callback, "Shader", Sdf.Path("/Node"))
        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], KeyError)

        view._toggle_expansion_state(0)
        self.assertEqual(node_proxy.expansion_state, GraphModel.ExpansionState.MINIMIZED)
        self.assertIs(view._get_model_port(0, 0), root_port)
        self.assertIs(view._get_model_port(0, 1), child_port)
        self.assertTrue(view._is_group_port(0, 0))
        view._toggle_group_expansion(0, 0)
        self.assertEqual(root_proxy.expansion_state, GraphModel.ExpansionState.CLOSED)
        self.assertIsNone(view._get_model_port(0, 1))

        io_menu = MagicMock()
        with (
            patch.object(canvas_module.ui, "Menu", return_value=io_menu),
            patch.object(canvas_module.ui, "MenuItem") as io_menu_item,
            patch(
                "omni.kit.window.material_graph.scripts.ui.interaction.menu_utils.show_menu_at_cursor"
            ) as show_io_menu,
        ):
            view._show_io_node_context_menu(0)
        io_menu_item.assert_called_once()
        show_io_menu.assert_called_once_with(io_menu)

    async def test_input_summary_clicks_and_noodle_feedback_use_view_model_state(self) -> None:
        """InputNode summaries and connection previews should update without native pointer events."""

        class Input:
            @classmethod
            def get_type_name(cls):
                return "InputNode"

        class Port:
            pass

        view = self._view()
        node = Input()
        port = Port()
        port.name = "Surface"
        model = _Model({port: SimpleNamespace(name="Surface")})
        view._model = model
        view._scene_model_nodes = [node]
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [160.0]
        view._scene_heights = [120.0]
        view._scene_port_start_y = [24.0]
        view._scene_is_backdrop = [False]
        view._scene_has_menu = [False]
        view._GraphCanvasView__root_frame = SimpleNamespace(
            screen_to_canvas_x=lambda x: x,
            screen_to_canvas_y=lambda y: y,
        )
        view._find_backdrop_resize_at = MagicMock(return_value=None)
        view._find_node_menu_at = MagicMock(return_value=None)
        view._find_expansion_icon_at = MagicMock(return_value=None)
        view._rebuild_core = MagicMock()
        vm = SimpleNamespace(
            _synthetic_row_indices={"other": 0, "unused": 1},
            _scene_group_indices={2},
            _scene_idx_to_port={2: port},
            _other_group_expanded=False,
            _unused_group_expanded=False,
            _group_collapse_state={},
        )
        view._input_node_vm = vm

        view._on_mouse_pressed(20, 25, 0, 0)
        self.assertTrue(vm._other_group_expanded)
        view._on_mouse_pressed(20, 43, 0, 0)
        self.assertTrue(vm._unused_group_expanded)
        view._on_mouse_pressed(20, 61, 0, 0)
        self.assertTrue(vm._group_collapse_state["Surface"])
        self.assertEqual(view._rebuild_core.call_count, 3)

        output_port, input_port = object(), object()
        view._pending_port_hit = (0, 0, False)
        view._pending_port_canvas = (0.0, 0.0)
        view._drag_node = node
        view._input_node_vm = None
        view._port_canvas_pos = MagicMock(return_value=(0.0, 0.0))
        view._find_port_hit_at_canvas = MagicMock(return_value=(1, 0, True))
        view._resolve_port = MagicMock(side_effect=[output_port, input_port])
        model.can_connect = MagicMock(return_value=False)
        canvas = MagicMock()
        view._canvas_widget = canvas
        view._on_mouse_moved(20, 20, 0, True)
        self.assertEqual(view._noodle_source, (0, 0, False))
        self.assertEqual(canvas.set_drag_noodle.call_args.args[-1], 0xFF3838A0)

    async def test_double_click_routes_inline_editors_and_color_picker_commit(self) -> None:
        """Double-click routing and backdrop color edits should remain model-driven."""
        view = self._view()
        node, port = object(), object()
        node_proxy = SimpleNamespace(display_color=(0.1, 0.2, 0.3))
        model = _Model({node: node_proxy})
        model._model = {node: node_proxy}
        view._model = model
        view._scene_model_nodes = [node]
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_stable_ids = [1]
        view._GraphCanvasView__root_frame = SimpleNamespace(
            screen_to_canvas_x=lambda x: x,
            screen_to_canvas_y=lambda y: y,
        )
        view._find_port_hit_at_canvas = MagicMock(return_value=(0, 0, True))
        view._resolve_port = MagicMock(return_value=port)
        view._is_nodegraph_interface_port = MagicMock(return_value=True)
        view._show_nodegraph_port_rename_dialog = MagicMock()
        view._on_mouse_double_clicked(1, 1, 0, 0)
        view._show_nodegraph_port_rename_dialog.assert_called_once_with(port)

        view._find_port_hit_at_canvas.return_value = None
        view._find_backdrop_color_swatch_at = MagicMock(return_value=0)
        view._open_color_picker = MagicMock()
        view._on_mouse_double_clicked(1, 1, 0, 0)
        view._open_color_picker.assert_called_once_with(0, 1, 1)

        values = [SimpleNamespace(as_float=0.0), SimpleNamespace(as_float=0.0), SimpleNamespace(as_float=0.0)]
        color_model = SimpleNamespace(
            get_item_children=lambda: [0, 1, 2],
            get_item_value_model=lambda index: values[index],
            add_end_edit_fn=MagicMock(),
        )
        color_widget = SimpleNamespace(model=color_model, visible=True)
        placer = MagicMock()
        root_stack = MagicMock()
        view._GraphCanvasView__root_stack = root_stack
        view._close_color_picker = MagicMock()
        with (
            patch.object(canvas_module.ui, "Placer", return_value=placer),
            patch.object(canvas_module.ui, "ColorWidget", return_value=color_widget),
        ):
            GraphCanvasView._open_color_picker(view, 0, 10, 10)
        self.assertEqual([value.as_float for value in values], [0.1, 0.2, 0.3])
        end_edit = color_model.add_end_edit_fn.call_args.args[0]
        values[0].as_float, values[1].as_float, values[2].as_float = 0.4, 0.5, 0.6
        end_edit(color_model)
        self.assertEqual(node_proxy.display_color, (0.4, 0.5, 0.6))
        model._item_changed.assert_called_once_with(None)

    async def test_deferred_disconnect_cancellation_and_model_change_are_safe(self) -> None:
        """Dropped rewires should disconnect once, notify, and cancel cleanly during model replacement."""
        view = self._view()
        port = object()
        proxy = SimpleNamespace(inputs=[object()])
        model = _Model({port: proxy})
        view._model = model
        view._connection_notify_item_for_port = MagicMock(return_value=port)
        view._notify_connection_changed = MagicMock()
        pending = []

        def capture(coro, _label):
            task = MagicMock()
            task.done.return_value = False
            pending.append((coro, task))
            return task

        with patch.object(canvas_module, "ensure_future_logged", side_effect=capture):
            view._defer_rewire_drop_disconnect(port)
            view._defer_rewire_drop_disconnect(port)
        self.assertEqual(len(pending), 1)
        with patch.object(
            canvas_module.omni.kit.app,
            "get_app",
            return_value=SimpleNamespace(next_update_async=AsyncMock()),
        ):
            await pending[0][0]
        self.assertEqual(proxy.inputs, [])
        view._notify_connection_changed.assert_called_once_with(
            port, reason="deferred_rewire_drop_disconnect", sync_item=True
        )

        view._deferred_disconnect_task = pending[0][1]
        view._deferred_disconnect_ports = [port]
        view._cancel_deferred_disconnects()
        pending[0][1].cancel.assert_called_once_with()
        self.assertEqual(view._deferred_disconnect_ports, [])

    async def test_initial_frame_icon_fallback_and_native_widget_setup(self) -> None:
        """Initial focus retries, context icons, and native widget creation should degrade safely."""
        view = self._view()
        view._model = _Model()
        view._needs_initial_frame = True
        view._scene_model_nodes = []
        self.assertTrue(view._focus_initial_frame_if_ready())
        self.assertFalse(view._needs_initial_frame)

        view._needs_initial_frame = True
        view._scene_model_nodes = [object()]
        view.focus_on_nodes = MagicMock(return_value=False)
        view._schedule_rebuild_work = MagicMock()
        self.assertFalse(view._focus_initial_frame_if_ready())
        view._schedule_rebuild_work.assert_called_once_with()

        plugin = SimpleNamespace(get_style=lambda: {"Graph.Node.Icon": {"image_url": "context.svg"}})
        view._input_node_context_manager = SimpleNamespace(
            get_context=lambda _name: SimpleNamespace(is_valid=True, plugin=plugin)
        )
        view._input_node_current_context = "mdl"
        icon, color = view._resolve_node_icon(object())
        self.assertTrue(icon.endswith("context.svg"))
        self.assertEqual(color, 0xFFFFFFFF)

        frame = MagicMock()
        view._GraphCanvasView__root_frame = frame
        stack = MagicMock()
        placer = MagicMock()
        canvas = MagicMock()
        with (
            patch.object(canvas_module.ui, "ZStack", return_value=stack),
            patch.object(canvas_module.ui, "Placer", return_value=placer),
            patch(
                "omni.kit.window.material_graph._graphCanvas.GraphCanvasWidget.create",
                return_value=canvas,
            ),
        ):
            view._ensure_canvas_widget()
        self.assertIs(view._canvas_widget, canvas)
        canvas.set_style_config.assert_called_once()

    async def test_model_switch_subscribes_and_clears_scene_state(self) -> None:
        view = self._view()
        old = _Model()
        view._model = old
        view._scene_model_nodes = [object()]
        view._cancel_deferred_disconnects = MagicMock()
        view._release_connection_visual_callback = MagicMock()
        view._install_connection_visual_callback = MagicMock()
        view._resolve_position_change_consumer = MagicMock(return_value="consumer")
        view._on_item_changed = MagicMock()
        new = _Model()

        view.set_model(new)
        view._cancel_deferred_disconnects.assert_called_once_with()
        view._release_connection_visual_callback.assert_called_once_with()
        self.assertEqual(view._scene_model_nodes, [])
        self.assertIs(view.model, new)
        self.assertEqual(view._position_change_consumer, "consumer")
        self.assertTrue(view._needs_initial_frame)
        self.assertEqual(view._model_subscription, "item-sub")
        self.assertEqual(view._selection_subscription, "selection-sub")
        self.assertEqual(view._node_subscription, "node-sub")
        view._install_connection_visual_callback.assert_called_once_with()
        view._on_item_changed.assert_called_once_with(None)

        view._on_item_changed.reset_mock()
        view.set_model(None)
        view._on_item_changed.assert_called_once_with(None)
        self.assertIsNone(view.model)

    async def test_connection_visual_callback_resolution_release_and_sync(self) -> None:
        view = self._view()
        inner = SimpleNamespace(set_connection_visual_sync_callback=MagicMock())
        shell = SimpleNamespace(_model=inner, _root=None)
        view._model = shell
        self.assertIs(view._resolve_nodegraph_for_connection_visual_cb(), inner)
        view._install_connection_visual_callback()
        inner.set_connection_visual_sync_callback.assert_called_with(view._sync_rebuild_for_connection_notify)
        view._release_connection_visual_callback()
        inner.set_connection_visual_sync_callback.assert_called_with(None)

        broken = SimpleNamespace(set_connection_visual_sync_callback=MagicMock(side_effect=RuntimeError("injected")))
        view._connection_visual_cb_target = broken
        view._release_connection_visual_callback()
        self.assertIsNone(view._connection_visual_cb_target)

        view._model = object()
        view._rebuild_core = MagicMock()
        view._schedule_rebuild_work = MagicMock()
        view._sync_rebuild_for_connection_notify(None)
        view._rebuild_core.assert_called_once_with()
        self.assertTrue(view._skip_deferred_rebuild_once)
        view._rebuilding = True
        view._rebuild_kit_sub = None
        view._sync_rebuild_for_connection_notify(None)
        view._schedule_rebuild_work.assert_called_once_with()

    async def test_selection_and_breadcrumb_proxy_contain_native_failures(self) -> None:
        view = self._view()
        first, second = object(), object()
        view._model = SimpleNamespace(selection=[second])
        canvas = MagicMock()
        view._canvas_widget = canvas
        view._scene_model_nodes = [first, second]
        view._scene_stable_ids = [11, 22]
        view._on_selection_changed()
        self.assertEqual(view.selection, [second])
        self.assertEqual(canvas.set_node_selected.call_args_list[0].args, (11, False))
        self.assertEqual(canvas.set_node_selected.call_args_list[1].args, (22, True))

        target_model = SimpleNamespace(selection=None)
        view._model = target_model
        view.selection = [first]
        self.assertEqual(target_model.selection, [first])
        view.set_breadcrumb(["Root", "Child"])
        canvas.set_breadcrumb.assert_called_once_with(["Root", "Child"])
        canvas.breadcrumb_clicked_index = 2
        canvas.breadcrumb_hovered = True
        self.assertEqual(view.breadcrumb_clicked_index, 2)
        self.assertTrue(view.breadcrumb_hovered)
        view.clear_breadcrumb_clicked()
        canvas.clear_breadcrumb_clicked.assert_called_once_with()

        class BrokenCanvas:
            @staticmethod
            def set_breadcrumb(_path):
                raise RuntimeError("injected")

            @property
            def breadcrumb_clicked_index(self):
                raise RuntimeError("injected")

            @property
            def breadcrumb_hovered(self):
                raise RuntimeError("injected")

        view._canvas_widget = BrokenCanvas()
        view.set_breadcrumb(["Safe"])
        self.assertEqual(view.breadcrumb_clicked_index, -1)
        self.assertFalse(view.breadcrumb_hovered)

    async def test_edit_poll_consumes_rename_and_description_results(self) -> None:
        view = self._view()
        node = object()
        proxy = SimpleNamespace(name="Old", description="Old description")
        model = _Model({node: proxy})
        view._model = model
        view._scene_model_nodes = [node]
        view._scene_stable_ids = [7]
        canvas = SimpleNamespace(
            has_rename_result=lambda: True,
            consume_rename_result=lambda: (7, "New"),
            has_desc_edit_result=lambda: True,
            consume_desc_edit_result=lambda: (7, "New description"),
            is_renaming=False,
            is_desc_editing=False,
        )
        view._canvas_widget = canvas
        with patch.object(
            canvas_module.omni.kit.app,
            "get_app",
            return_value=SimpleNamespace(next_update_async=AsyncMock()),
        ):
            await view._poll_edit_results()
        self.assertEqual(proxy.name, "New")
        self.assertEqual(proxy.description, "New description")
        self.assertEqual(model._item_changed.call_count, 2)

    async def test_edit_start_open_and_description_poll_are_headless(self) -> None:
        view = self._view()
        node = object()
        proxy = SimpleNamespace(name="Node", description="Description")
        model = _Model({node: proxy})
        view._model = model
        view._scene_model_nodes = [node]
        view._scene_stable_ids = [9]
        canvas = MagicMock()
        canvas.is_renaming = True
        canvas.is_desc_editing = False
        view._canvas_widget = canvas

        scheduled = []

        def capture(coro, _label):
            scheduled.append(coro)
            return MagicMock()

        with patch.object(canvas_module, "ensure_future_logged", side_effect=capture):
            view._start_edit_poll()
            view._open_description_editor(0, 0, 0)
            view._open_rename_editor(0)
        canvas.start_desc_edit.assert_called_once_with(9, "Description")
        canvas.start_rename.assert_called_once_with(9, "Node")
        for coro in scheduled:
            coro.close()

        view._canvas_widget = SimpleNamespace(
            has_desc_edit_result=lambda: True,
            consume_desc_edit_result=lambda: (9, "Committed"),
        )
        with patch.object(
            canvas_module.omni.kit.app,
            "get_app",
            return_value=SimpleNamespace(next_update_async=AsyncMock()),
        ):
            await view._poll_desc_edit_result()
        self.assertEqual(proxy.description, "Committed")
        model._item_changed.assert_called_with(None)

    async def test_color_picker_commit_updates_model_and_hides_controls(self) -> None:
        view = self._view()
        node = object()
        target = SimpleNamespace(display_color=None)
        model = _Model({node: target})
        view._model = model
        values = [SimpleNamespace(as_float=0.1), SimpleNamespace(as_float=0.2), SimpleNamespace(as_float=0.3)]
        color_model = SimpleNamespace(
            get_item_children=lambda: [0, 1, 2],
            get_item_value_model=lambda item: values[item],
        )
        placer = SimpleNamespace(visible=True)
        color_widget = SimpleNamespace(model=color_model, visible=True)
        view._color_picker_widget = (placer, color_widget, node)
        view._commit_color_picker()
        self.assertEqual(target.display_color, (0.1, 0.2, 0.3))
        self.assertFalse(placer.visible)
        self.assertFalse(color_widget.visible)
        self.assertIsNone(view._color_picker_widget)
        model._item_changed.assert_called_once_with(None)

        model._item_changed.reset_mock()
        target.display_color = (0.7, 0.8, 0.9)
        failing_widget = SimpleNamespace(
            model=SimpleNamespace(get_item_children=MagicMock(side_effect=RuntimeError("injected"))),
            visible=True,
        )
        view._color_picker_widget = (placer, failing_widget, node)
        view._commit_color_picker()
        self.assertEqual(target.display_color, (0.7, 0.8, 0.9))
        self.assertIsNone(view._color_picker_widget)
        model._item_changed.assert_not_called()

    async def test_mutation_helpers_do_not_notify_after_model_rejection(self) -> None:
        """Native edit results must preserve failures from rename, description, color, and position models."""
        view = self._view()
        node = object()
        target = SimpleNamespace(
            path=Sdf.Path("/World/Rejected"),
            set_name=MagicMock(return_value=False),
            set_description=MagicMock(return_value=False),
            set_display_color=MagicMock(return_value=False),
        )
        model = _Model({node: target})
        view._model = model

        self.assertFalse(view._commit_node_name(node, "new"))
        self.assertFalse(view._commit_node_description(node, "new description"))
        self.assertFalse(view._commit_node_color(node, (0.1, 0.2, 0.3)))

        prim_node = SimpleNamespace(path=Sdf.Path("/World/Prim"), set_position=MagicMock(return_value=False))
        self.assertFalse(view._commit_node_position(prim_node, (10.0, 20.0)))
        model._item_changed.assert_not_called()

    async def test_material_output_resolution_and_connection_notification(self) -> None:
        view = self._view()
        prim = MagicMock()
        prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        source_prim = SimpleNamespace(GetPath=lambda: Sdf.Path("/Source"))
        source_api = SimpleNamespace(GetPrim=lambda: source_prim)
        source = SimpleNamespace(
            source=source_api,
            sourceName="out",
            sourceType=UsdShade.AttributeType.Output,
        )
        usd_port = SimpleNamespace(HasConnectedSource=lambda: True, GetConnectedSources=lambda: ([source], []))
        port = SimpleNamespace(
            prim=prim,
            proxy_attribute=SimpleNamespace(name="outputs:mtlx:surface"),
            usdshade_port=usd_port,
        )
        resolved = object()
        model = SimpleNamespace(
            get_item_model=MagicMock(return_value=resolved),
            _item_changed=MagicMock(),
            notify_connection_changed=MagicMock(),
        )
        view._model = model
        self.assertTrue(view._is_material_output_sink_port(port))
        self.assertIsNone(view._connection_notify_item_for_port(port))
        self.assertEqual(view._material_output_sources(port), [resolved])
        model.get_item_model.assert_called_once_with(Sdf.Path("/Source.outputs:out"))

        sync_item = SimpleNamespace(sync=MagicMock())
        view._resolve_nodegraph_for_connection_visual_cb = MagicMock(return_value=None)
        view._notify_connection_changed(sync_item, "test", sync_item=True)
        sync_item.sync.assert_called_once_with()
        model.notify_connection_changed.assert_called_once_with(sync_item)

        model.notify_connection_changed = None
        view._notify_connection_changed(sync_item, "fallback")
        model._item_changed.assert_called_once_with(None)

    async def test_port_scene_lookup_menu_and_disconnect_hovered(self) -> None:
        view = self._view()
        node = object()
        port = object()
        view._model = _Model({node: SimpleNamespace(ports=[port])})
        view._scene_model_nodes = [node]
        view._scene_stable_ids = [42]
        self.assertEqual(view._find_scene_port(port), (0, 0))
        self.assertIs(view._resolve_port_by_stable_id(42, 0, True), port)
        self.assertIsNone(view._resolve_port_by_stable_id(99, 0, True))

        menu = SimpleNamespace(hide=MagicMock(), visible=True)
        view._port_context_menu = menu
        view.hide_port_context_menu()
        menu.hide.assert_called_once_with()
        self.assertFalse(menu.visible)

        connection = SimpleNamespace(target_node_id=42, target_port_index=0)
        view._last_scene = SimpleNamespace(connections=[connection])
        view._canvas_widget = SimpleNamespace(hover_connection_index=0)
        view._disconnect_port = MagicMock(return_value=True)
        self.assertTrue(view.disconnect_hovered_connection())
        view._disconnect_port.assert_called_once_with(port)
        view._disconnect_port.return_value = False
        self.assertFalse(view.disconnect_hovered_connection())
        view._canvas_widget.hover_connection_index = -1
        self.assertFalse(view.disconnect_hovered_connection())

    async def test_rebuild_scheduling_and_position_only_geometry(self) -> None:
        view = self._view()

        class Item:
            prim_path = "/Node"

        item = Item()
        scene_item = Item()
        proxy = SimpleNamespace(position=(12, 34))
        view._model = _Model({item: proxy})
        view._canvas_widget = SimpleNamespace(set_node_position=MagicMock())
        view._scene_model_nodes = [scene_item]
        view._scene_stable_ids = [8]
        view._scene_pos_x = [0]
        view._scene_pos_y = [0]
        self.assertEqual(view._find_scene_node_index(item), 0)
        self.assertTrue(view._update_scene_node_geometry(item))
        self.assertEqual((view._scene_pos_x[0], view._scene_pos_y[0]), (12.0, 34.0))
        view._canvas_widget.set_node_position.assert_called_once_with(8, 12.0, 34.0)

        view._position_change_consumer = MagicMock(return_value=True)
        view._schedule_rebuild_work = MagicMock()
        view._on_item_changed(item)
        view._schedule_rebuild_work.assert_not_called()
        proxy.position = None
        view._on_item_changed(item)
        view._schedule_rebuild_work.assert_called_once_with()

        subscription = SimpleNamespace(unsubscribe=MagicMock())
        view._rebuild_kit_sub = subscription
        view._detach_rebuild_kit_subscription()
        subscription.unsubscribe.assert_called_once_with()
        self.assertIsNone(view._rebuild_kit_sub)

    async def test_snapshot_input_context_icon_preview_and_registration(self) -> None:
        view = self._view()
        model = SimpleNamespace(export_snapshot=MagicMock(return_value=[{"node": "node"}]))
        view._model = model
        view._port_grouping = "grouping"
        view._ensure_input_node_vm = MagicMock(return_value="input-vm")
        self.assertEqual(view._snapshot_for_build(), [{"node": "node"}])
        model.export_snapshot.assert_called_once_with("grouping", input_node_view_model="input-vm")

        view._input_node_vm = SimpleNamespace(_built=True)
        manager = object()
        view.set_input_node_context(manager, "mtlx")
        self.assertFalse(view._input_node_vm._built)
        self.assertEqual(view._input_node_current_context, "mtlx")
        view.set_validation_errors({"/Node": "broken"})
        self.assertEqual(view._validation_errors_by_path, {"/Node": "broken"})

        preview_node = object()
        view._model = _Model({preview_node: SimpleNamespace(preview="relative.png")})
        self.assertTrue(view._resolve_node_preview(preview_node).endswith("relative.png"))
        view._resolve_node_icon = MagicMock(return_value=("icon.svg", 0xFFFFFFFF))
        view._resolve_node_preview = MagicMock(return_value="preview.png")
        snapshot = [{"node": preview_node}, {"node": None}]
        view._upload_node_icons(snapshot)
        self.assertEqual(snapshot[0]["icon_url"], "icon.svg")
        self.assertEqual(snapshot[0]["preview_url"], "preview.png")
        self.assertEqual(view._pending_icon_paths, {"icon.svg", "preview.png"})

        canvas = SimpleNamespace(set_icon_path=MagicMock())
        view._canvas_widget = canvas
        view._register_expansion_icons = MagicMock()
        view._register_icon_textures()
        view._register_expansion_icons.assert_called_once_with()
        self.assertIn((("icon.svg", "icon.svg")), [call.args for call in canvas.set_icon_path.call_args_list])
        self.assertIsNone(view._pending_icon_paths)

    async def test_focus_layout_expansion_and_destroy(self) -> None:
        view = self._view()
        first, second = object(), object()
        model = _Model(
            {
                first: SimpleNamespace(position=(1, 2), expansion_state=None),
                second: SimpleNamespace(position=(3, 4), expansion_state=None),
            }
        )
        model.nodes = [first, second]
        view._model = model
        view._scene_model_nodes = [first, second]
        view._scene_pos_x = [0.0, 300.0]
        view._scene_pos_y = [0.0, 100.0]
        view._scene_widths = [100.0, 100.0]
        view._scene_heights = [50.0, 50.0]
        root = SimpleNamespace(
            zoom=1.0,
            zoom_min=0.1,
            zoom_max=4.0,
            computed_width=800.0,
            computed_height=600.0,
            pan_x=0.0,
            pan_y=0.0,
        )
        view._GraphCanvasView__root_frame = root
        self.assertTrue(view.focus_on_nodes())
        self.assertGreater(root.zoom, 0)
        self.assertTrue(view.focus_on_nodes([first]))
        view._suppress_focus = True
        self.assertFalse(view.focus_on_nodes())

        view._on_item_changed = MagicMock()
        view.layout_all()
        self.assertIsNone(model[first].position)
        self.assertIsNone(model[second].position)
        view.set_expansion("closed")
        self.assertEqual(model[first].expansion_state, "closed")
        self.assertFalse(view.raster_nodes)

        view._release_connection_visual_callback = MagicMock()
        view._close_description_editor = MagicMock()
        view._close_rename_editor = MagicMock()
        view._close_color_picker = MagicMock()
        view._cancel_deferred_disconnects = MagicMock()
        view._detach_rebuild_kit_subscription = MagicMock()
        view._rename_poll_task = SimpleNamespace(cancel=MagicMock())
        view._desc_edit_poll_task = SimpleNamespace(cancel=MagicMock())
        view._edit_poll_task = SimpleNamespace(cancel=MagicMock())
        view._tooltip_task = SimpleNamespace(cancel=MagicMock())
        view._port_rename_dialog = SimpleNamespace(hide=MagicMock())
        view.destroy()
        self.assertIsNone(view._model)
        self.assertIsNone(view._canvas_widget)
        self.assertEqual(view._scene_model_nodes, [])
        self.assertIsNone(view._GraphCanvasView__root_frame)

    async def test_header_detection_uses_current_pointer_coordinates_without_ui_events(self) -> None:
        """Header hit testing should use the input snapshot and honor rename/backdrop guards."""
        view = self._view()
        node = object()
        view._scene_model_nodes = [node]
        view._scene_pos_x = [10.0]
        view._scene_pos_y = [20.0]
        view._scene_widths = [100.0]
        view._scene_is_backdrop = [False]
        view._screen_to_canvas = MagicMock(side_effect=lambda x, y: (x, y))

        app = SimpleNamespace(get_update_number=lambda: 100)
        view._rename_opened_frame = 99
        with patch.object(canvas_module.omni.kit.app, "get_app", return_value=app):
            self.assertTrue(view.is_point_over_header(node))

        view._rename_opened_frame = 0
        input_iface = SimpleNamespace(
            get_mouse=lambda: "mouse",
            get_mouse_coords_pixel=lambda mouse: (50.0, 30.0),
        )
        with (
            patch.object(canvas_module.omni.kit.app, "get_app", return_value=app),
            patch.object(carb.input, "acquire_input_interface", return_value=input_iface),
        ):
            self.assertTrue(view.is_point_over_header(node))
            input_iface.get_mouse_coords_pixel = lambda mouse: (500.0, 300.0)
            self.assertFalse(view.is_point_over_header(node))
            self.assertFalse(view.is_point_over_header(object()))
            view._scene_is_backdrop = [True]
            self.assertFalse(view.is_point_over_header(node))

        with (
            patch.object(canvas_module.omni.kit.app, "get_app", return_value=app),
            patch.object(carb.input, "acquire_input_interface", side_effect=RuntimeError("input")),
        ):
            self.assertFalse(view.is_point_over_header(node))

    async def test_fallback_input_output_and_consumer_scan_disconnect_paths(self) -> None:
        """Fallback ports should disconnect direct USD sources and scanned consumers with notifications."""
        stage = Usd.Stage.CreateInMemory()
        source = UsdShade.Shader.Define(stage, Sdf.Path("/Source"))
        source_output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target = UsdShade.Shader.Define(stage, Sdf.Path("/Target"))
        target_input = target.CreateInput("in", Sdf.ValueTypeNames.Float)
        target_input.ConnectToSource(source_output)
        target_output = target.CreateOutput("forward", Sdf.ValueTypeNames.Float)
        target_output.ConnectToSource(source_output)

        view = self._view()
        view._model = _Model()
        view._notify_connection_changed = MagicMock()
        view._connection_notify_item_for_port = MagicMock(side_effect=lambda port: port)
        success = CommandResult(True, None)
        module = "omni.kit.window.material_graph.scripts.commands.wrappers.ports.DisconnectSourcePort"

        input_port = SimpleNamespace(
            _fallback_usd_attr=target_input.GetAttr(),
            _fallback_prim=target.GetPrim(),
            _is_output=False,
            name="inputs:in",
        )
        output_port = SimpleNamespace(
            _fallback_usd_attr=target_output.GetAttr(),
            _fallback_prim=target.GetPrim(),
            _is_output=True,
            name="outputs:forward",
        )
        with patch(module, return_value=success) as disconnect:
            view._disconnect_fallback_port(input_port)
            view._disconnect_fallback_port(output_port)
        self.assertEqual(disconnect.call_count, 2)
        self.assertEqual(view._notify_connection_changed.call_count, 2)

        fallback = UsdShade.Shader.Define(stage, Sdf.Path("/Fallback"))
        fallback_output = fallback.CreateOutput("out", Sdf.ValueTypeNames.Float)
        consumer = UsdShade.Shader.Define(stage, Sdf.Path("/Consumer"))
        consumer_input = consumer.CreateInput("in", Sdf.ValueTypeNames.Float)
        consumer_input.ConnectToSource(fallback_output)
        consumer_port = MagicMock()
        consumer_port.proxy_attribute = SimpleNamespace(name="inputs:in", attribute=consumer_input.GetAttr())
        consumer_node = MagicMock()
        consumer_node.prim = consumer.GetPrim()
        scan_port = SimpleNamespace(
            _fallback_usd_attr=fallback_output.GetAttr(),
            _fallback_prim=fallback.GetPrim(),
            _is_output=True,
            name="outputs:out",
        )
        view._scene_model_nodes = [consumer_node]
        view._model = _Model(
            {
                consumer_node: SimpleNamespace(ports=[consumer_port]),
                consumer_port: SimpleNamespace(inputs=[scan_port]),
            }
        )
        view._notify_connection_changed.reset_mock()
        with patch(module, return_value=success) as disconnect:
            view._disconnect_fallback_port(scan_port)
        disconnect.assert_called_once()
        view._notify_connection_changed.assert_called_once_with(None, reason="disconnect_fallback_scan")
        self.assertTrue(view._fallback_output_has_consumers(scan_port))
        view._model = None
        self.assertFalse(view._fallback_output_has_consumers(scan_port))

    async def test_nodegraph_port_display_name_and_remove_commands_are_headless(self) -> None:
        """NodeGraph interface edits should update proxies and surface command failures without dialogs."""
        view = self._view()
        port = MagicMock()
        port.path = Sdf.Path("/Graph.inputs:value")
        port.proxy_attribute = SimpleNamespace(display_name="Value", name="inputs:value")
        port.update_proxy_attribute = MagicMock()
        view._model = _Model({port: SimpleNamespace(update_proxy_attribute=MagicMock())})
        view._is_nodegraph_interface_port = MagicMock(return_value=True)
        result = CommandResult(True, None)
        with (
            patch(
                "omni.kit.window.material_graph.scripts.commands.wrappers.attributes.SetDisplayName",
                return_value=result,
            ) as set_name,
            patch(
                "omni.kit.window.material_graph.scripts.commands.wrappers.attributes.RemoveProperty",
                return_value=result,
            ) as remove,
        ):
            view._set_nodegraph_port_display_name(port, "Renamed")
            view._remove_nodegraph_port(port)
        set_name.assert_called_once_with(port.path, "Renamed")
        self.assertEqual(port.proxy_attribute.display_name, "Renamed")
        port.update_proxy_attribute.assert_called_once_with(port.proxy_attribute)
        remove.assert_called_once_with(port.path)
        self.assertEqual(view._model._item_changed.call_count, 2)

        failure = CommandResult(False, None, message="failed")
        view._model._item_changed.reset_mock()
        with (
            patch(
                "omni.kit.window.material_graph.scripts.commands.wrappers.attributes.SetDisplayName",
                return_value=failure,
            ),
            patch(
                "omni.kit.window.material_graph.scripts.commands.wrappers.attributes.RemoveProperty",
                return_value=failure,
            ),
        ):
            view._set_nodegraph_port_display_name(port, "Ignored")
            view._remove_nodegraph_port(port)
        view._model._item_changed.assert_not_called()
