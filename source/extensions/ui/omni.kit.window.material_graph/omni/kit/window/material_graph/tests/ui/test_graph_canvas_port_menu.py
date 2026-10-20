# pylint: disable=protected-access
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.ui.graph_canvas_view import GraphCanvasView
from ..base import MaterialGraphTestBase


class _OwnerInputNode:
    """Minimal InputNode owner used by GraphCanvasView port helpers."""

    source = object()

    @staticmethod
    def get_type_name() -> str:
        """Return the isolation-node type name."""
        return "InputNode"


class _OwnerShaderNode:
    """Minimal non-interface node owner."""

    @staticmethod
    def get_type_name() -> str:
        """Return a regular compute-node type name."""
        return "Shader"


class _OwnerOutputNode:
    """Minimal OutputNode owner used by hit-testing helpers."""

    source = object()

    @staticmethod
    def get_type_name() -> str:
        """Return the isolation-node type name."""
        return "OutputNode"


class _PortStub:
    """Hashable port stub with the fields GraphCanvasView uses."""

    def __init__(self, path: Sdf.Path, proxy_attribute: object) -> None:
        self.path = path
        self.proxy_attribute = proxy_attribute
        self.update_proxy_attribute = MagicMock()


class _MaterialOutputPortStub(_PortStub):
    """Material output-shaped port stub for sink-side interaction tests."""

    def __init__(self, path: Sdf.Path, proxy_attribute: object) -> None:
        super().__init__(path, proxy_attribute)
        self.prim = MagicMock()
        self.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        self.usdshade_port = MagicMock()


class _FakeModel:
    """Mapping-backed graph model stub."""

    def __init__(self, values: dict) -> None:
        self._values = values
        self._item_changed = MagicMock()

    def __getitem__(self, item):
        return self._values[item]


class _FakeMenu:
    """Small context-manager stand-in for omni.ui.Menu."""

    def __init__(self, *_args, **_kwargs) -> None:
        self.visible = False
        self.shown = False
        self.hidden = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def hide(self) -> None:
        """Record replacement of a previously shown menu."""
        self.hidden = True

    def show(self) -> None:
        """Record that the menu was shown."""
        self.shown = True


class TestGraphCanvasPortMenu(MaterialGraphTestBase):
    """Canvas port menu helpers for NodeGraph interface ports."""

    def _create_view_and_port(self, owner=None):
        if owner is None:
            owner = _OwnerInputNode()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:abs_out")
        port = _PortStub(Sdf.Path("/World/Looks/Mat.outputs:abs_out"), proxy_attribute)
        model = _FakeModel(
            {
                owner: SimpleNamespace(ports=[port]),
                port: SimpleNamespace(name="abs_out", ports=None, inputs=[]),
            }
        )
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [owner]
        view._port_context_menu = None
        view._io_node_context_menu = None
        view._port_rename_dialog = None
        return view, port, model, proxy_attribute

    def _create_shader_pin_test_view(self):
        owner = _OwnerShaderNode()
        proxy_attribute = SimpleNamespace(display_name="", name="inputs:tex")
        port = _PortStub(Sdf.Path("/World/Looks/Mat/lookup.inputs:tex"), proxy_attribute)
        model = _FakeModel(
            {owner: SimpleNamespace(ports=[port]), port: SimpleNamespace(name="tex", ports=None, inputs=[])}
        )
        model.selection = []
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [owner]
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [200.0]
        view._scene_heights = [100.0]
        view._scene_is_backdrop = [False]
        view._scene_has_menu = [False]
        view._scene_port_start_y = [32.0]
        view._input_node_vm = None
        view._color_picker_widget = None
        view._selection = []
        view._screen_to_canvas = lambda x, y: (x, y)
        view._update_scene_selection = MagicMock()
        return view, owner

    def _create_shader_output_pin_test_view(self):
        owner = _OwnerShaderNode()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:out")
        port = _PortStub(Sdf.Path("/World/Looks/Mat/lookup.outputs:out"), proxy_attribute)
        model = _FakeModel(
            {owner: SimpleNamespace(ports=[port]), port: SimpleNamespace(name="out", ports=None, outputs=[])}
        )
        model.selection = []
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [owner]
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [200.0]
        view._scene_heights = [100.0]
        view._scene_is_backdrop = [False]
        view._scene_has_menu = [False]
        view._scene_port_start_y = [32.0]
        view._input_node_vm = None
        view._color_picker_widget = None
        view._selection = []
        view._screen_to_canvas = lambda x, y: (x, y)
        view._update_scene_selection = MagicMock()
        return view, owner

    async def test_output_node_label_area_resolves_to_port_hit(self) -> None:
        """OutputNode label/body clicks should resolve as graph-sink input hits."""
        view, _port, _model, _proxy_attribute = self._create_view_and_port(_OwnerOutputNode())
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [200.0]
        view._scene_heights = [80.0]
        view._scene_is_backdrop = [False]
        view._scene_port_start_y = [32.0]

        self.assertEqual(view._find_port_hit_at_canvas(100.0, 43.0), (0, 0, True))

    async def test_output_node_gap_below_header_not_port_hit(self) -> None:
        """Clicks between the header and port rows should not map to port zero."""
        view, _port, _model, _proxy_attribute = self._create_view_and_port(_OwnerOutputNode())
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [200.0]
        view._scene_heights = [80.0]
        view._scene_is_backdrop = [False]
        view._scene_port_start_y = [32.0]

        self.assertIsNone(view._find_port_hit_at_canvas(100.0, 30.0))

    async def test_normal_node_body_left_strip_does_not_start_noodle(self) -> None:
        """Dragging a normal node body near its left side should drag the node, not start a noodle."""
        view, owner = self._create_shader_pin_test_view()

        self.assertEqual(view._find_port_at(20.0, 43.0), (0, 0, True))
        self.assertIsNone(view._find_port_pin_at_canvas(20.0, 43.0))

        view._on_mouse_pressed(20.0, 43.0, 0, 0)

        self.assertIsNone(view._pending_port_hit)
        self.assertIs(view._drag_node, owner)

    async def test_normal_node_input_pin_still_starts_noodle(self) -> None:
        """Clicking the actual normal-node pin should still prepare a noodle drag."""
        view, owner = self._create_shader_pin_test_view()

        view._on_mouse_pressed(1.0, 43.0, 0, 0)

        self.assertEqual(view._pending_port_hit, (0, 0, True))
        self.assertIs(view._drag_node, owner)

    async def test_normal_node_output_left_edge_does_not_start_noodle(self) -> None:
        """Output-only rows should not create opposite-side noodles from the left edge."""
        view, owner = self._create_shader_output_pin_test_view()

        self.assertIsNone(view._find_port_at(1.0, 43.0))
        self.assertIsNone(view._find_port_pin_at_canvas(1.0, 43.0))

        view._on_mouse_pressed(1.0, 43.0, 0, 0)

        self.assertIsNone(view._pending_port_hit)
        self.assertIs(view._drag_node, owner)

    async def test_normal_node_output_right_pin_still_starts_noodle(self) -> None:
        """Output-only rows should start noodles only from the visible right pin."""
        view, owner = self._create_shader_output_pin_test_view()

        self.assertEqual(view._find_port_at(199.0, 43.0), (0, 0, False))

        view._on_mouse_pressed(199.0, 43.0, 0, 0)

        self.assertEqual(view._pending_port_hit, (0, 0, False))
        self.assertIs(view._drag_node, owner)

    async def test_initial_frame_retries_when_focus_not_ready(self) -> None:
        """Initial framing should retry instead of being consumed by an unready viewport."""
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._needs_initial_frame = True
        view._initial_frame_retry_count = 0
        view._scene_model_nodes = [object()]
        view.focus_on_nodes = MagicMock(return_value=False)
        view._schedule_rebuild_work = MagicMock()

        self.assertFalse(view._focus_initial_frame_if_ready())

        self.assertTrue(view._needs_initial_frame)
        view._schedule_rebuild_work.assert_called_once_with()

    async def test_initial_frame_retry_is_capped(self) -> None:
        """Persistent focus failures should not schedule rebuilds forever."""
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._needs_initial_frame = True
        view._initial_frame_retry_count = view._INITIAL_FRAME_MAX_RETRIES - 1
        view._scene_model_nodes = [object()]
        view.focus_on_nodes = MagicMock(return_value=False)
        view._schedule_rebuild_work = MagicMock()

        self.assertFalse(view._focus_initial_frame_if_ready())

        self.assertFalse(view._needs_initial_frame)
        view._schedule_rebuild_work.assert_not_called()

    async def test_initial_frame_empty_graph_does_not_retry_forever(self) -> None:
        """Empty graphs have nothing to frame and should not schedule endless retries."""
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._needs_initial_frame = True
        view._initial_frame_retry_count = 2
        view._scene_model_nodes = []
        view.focus_on_nodes = MagicMock(return_value=False)
        view._schedule_rebuild_work = MagicMock()

        self.assertTrue(view._focus_initial_frame_if_ready())

        self.assertFalse(view._needs_initial_frame)
        self.assertEqual(view._initial_frame_retry_count, 0)
        view.focus_on_nodes.assert_not_called()
        view._schedule_rebuild_work.assert_not_called()

    async def test_initial_frame_clears_after_successful_focus(self) -> None:
        """Initial framing should be marked complete only after focus succeeds."""
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._needs_initial_frame = True
        view._initial_frame_retry_count = 2
        view._scene_model_nodes = [object()]
        view.focus_on_nodes = MagicMock(return_value=True)
        view._schedule_rebuild_work = MagicMock()

        self.assertTrue(view._focus_initial_frame_if_ready())

        self.assertFalse(view._needs_initial_frame)
        self.assertEqual(view._initial_frame_retry_count, 0)
        view._schedule_rebuild_work.assert_not_called()

    async def test_clear_scene_state_removes_stale_nodes_for_model_switch(self) -> None:
        """Model switches should not inherit stale scene nodes that suppress initial framing."""
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._scene_model_nodes = [object()]
        view._scene_stable_ids = [7]
        view._scene_pos_x = [1.0]
        view._scene_pos_y = [2.0]
        view._scene_widths = [3.0]
        view._scene_heights = [4.0]
        view._scene_port_start_y = [5.0]
        view._node_to_stable = {1: 7}
        view._scene_is_backdrop = [False]
        view._scene_has_menu = [True]
        view._fallback_port_map = {(0, 0): object()}
        view._last_scene = object()

        view._clear_scene_state()

        self.assertEqual(view._scene_model_nodes, [])
        self.assertEqual(view._scene_pos_x, [])
        self.assertEqual(view._fallback_port_map, {})
        self.assertIsNone(view._last_scene)

    async def test_pending_noodle_uses_canvas_space_drag_threshold(self) -> None:
        """Noodle arming should use the same canvas-space threshold as node dragging."""
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._resize_node_index = None
        view._pending_port_hit = (0, 0, True)
        view._pending_port_canvas = (0.0, 0.0)
        view._noodle_source = None
        view._noodle_rewire = False
        view._noodle_rewire_old_source = None
        view._drag_node = None
        view._drag_start_canvas = None
        view._marquee_start = None
        view._drag_threshold = 3.0
        view._screen_to_canvas = lambda x, y: (x * 0.5, y * 0.5)

        view._on_mouse_moved(4.0, 0.0, 0, True)

        self.assertIsNone(view._noodle_source)
        self.assertEqual(view._pending_port_hit, (0, 0, True))

    async def test_io_body_hit_does_not_click_through_overlapping_node(self) -> None:
        """A top node's non-port area should block lower IO port body hits."""
        lower_owner = _OwnerOutputNode()
        upper_owner = _OwnerShaderNode()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:out")
        lower_port = _PortStub(Sdf.Path("/World/Looks/Mat.outputs:out"), proxy_attribute)
        model = _FakeModel(
            {
                lower_owner: SimpleNamespace(ports=[lower_port]),
                upper_owner: SimpleNamespace(ports=[]),
                lower_port: SimpleNamespace(name="out", ports=None, inputs=[]),
            }
        )
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [lower_owner, upper_owner]
        view._scene_pos_x = [0.0, 0.0]
        view._scene_pos_y = [0.0, 0.0]
        view._scene_widths = [200.0, 200.0]
        view._scene_heights = [80.0, 80.0]
        view._scene_is_backdrop = [False, False]
        view._scene_port_start_y = [32.0, 32.0]

        self.assertIsNone(view._find_port_hit_at_canvas(100.0, 43.0))

    async def test_io_body_hit_skips_overlapping_backdrop(self) -> None:
        """Backdrops should not block IO body hits behind them."""
        lower_owner = _OwnerOutputNode()
        backdrop = object()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:out")
        lower_port = _PortStub(Sdf.Path("/World/Looks/Mat.outputs:out"), proxy_attribute)
        model = _FakeModel(
            {
                lower_owner: SimpleNamespace(ports=[lower_port]),
                lower_port: SimpleNamespace(name="out", ports=None, inputs=[]),
            }
        )
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [lower_owner, backdrop]
        view._scene_pos_x = [0.0, 0.0]
        view._scene_pos_y = [0.0, 0.0]
        view._scene_widths = [200.0, 200.0]
        view._scene_heights = [80.0, 80.0]
        view._scene_is_backdrop = [False, True]
        view._scene_port_start_y = [32.0, 32.0]

        self.assertEqual(view._find_port_hit_at_canvas(100.0, 43.0), (0, 0, True))

    async def test_material_output_left_edge_resolves_as_input_hit(self) -> None:
        """Material outputs render as sink ports and should hit-test on the left edge."""
        owner = _OwnerShaderNode()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:surface")
        port = _MaterialOutputPortStub(Sdf.Path("/World/Looks/Mat.outputs:surface"), proxy_attribute)
        model = _FakeModel({owner: SimpleNamespace(ports=[port]), port: SimpleNamespace(name="surface", ports=None)})
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [owner]
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [200.0]
        view._scene_heights = [80.0]
        view._scene_is_backdrop = [False]
        view._scene_port_start_y = [32.0]

        self.assertEqual(view._find_port_at(1.0, 43.0), (0, 0, True))
        self.assertIsNone(view._find_port_at(199.0, 43.0))

    async def test_output_node_right_edge_is_not_output_hit(self) -> None:
        """OutputNode ports are graph sinks, so their right edge should not start output-side drags."""
        view, _port, _model, _proxy_attribute = self._create_view_and_port(_OwnerOutputNode())
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [200.0]
        view._scene_heights = [80.0]
        view._scene_is_backdrop = [False]
        view._scene_port_start_y = [32.0]

        self.assertEqual(view._find_port_at(1.0, 43.0), (0, 0, True))
        self.assertIsNone(view._find_port_at(199.0, 43.0))

    async def test_output_node_empty_port_is_sink_hit(self) -> None:
        """OutputNode Add Port rows should accept incoming connections from the left only."""
        owner = _OwnerOutputNode()
        empty_port = object()
        model = _FakeModel(
            {
                owner: SimpleNamespace(ports=[empty_port]),
                empty_port: SimpleNamespace(name="EmptyPort", ports=None, inputs=[]),
            }
        )
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [owner]
        view._scene_pos_x = [0.0]
        view._scene_pos_y = [0.0]
        view._scene_widths = [200.0]
        view._scene_heights = [80.0]
        view._scene_is_backdrop = [False]
        view._scene_port_start_y = [32.0]

        self.assertEqual(view._find_port_at(1.0, 43.0), (0, 0, True))
        self.assertIsNone(view._find_port_at(199.0, 43.0))

    async def test_commit_io_node_position_uses_isolation_proxy(self) -> None:
        """Input/output wrapper drags should persist through the isolation proxy path."""
        node = _OwnerInputNode()
        node.source = SimpleNamespace(set_position=MagicMock())
        proxy = SimpleNamespace(position=None)
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = _FakeModel({node: proxy})

        view._commit_node_position(node, (10.0, 20.0))

        self.assertEqual(proxy.position, (10.0, 20.0))
        node.source.set_position.assert_not_called()

    async def test_commit_prim_node_position_suppresses_notify(self) -> None:
        """Prim-backed drags should persist without full position notifications."""
        node = SimpleNamespace(set_position=MagicMock())
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = _FakeModel({})

        view._commit_node_position(node, (10.0, 20.0))

        node.set_position.assert_called_once_with((10.0, 20.0), notify=False)

    async def test_disconnected_regular_port_context_menu_is_hidden(self) -> None:
        """Disconnected non-interface ports should not get a context menu."""
        view, port, _model, _proxy_attribute = self._create_view_and_port(_OwnerShaderNode())
        labels = []
        fake_menu = _FakeMenu()

        with (
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Menu", return_value=fake_menu),
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.MenuItem",
                side_effect=lambda label, **_kwargs: labels.append(label),
            ),
        ):
            view._show_port_context_menu(port)

        self.assertEqual(labels, [])
        self.assertFalse(fake_menu.shown)

    async def test_disconnected_nodegraph_port_context_menu_has_rename_and_remove(self) -> None:
        """Disconnected NodeGraph interface ports should still show edit actions."""
        view, port, _model, _proxy_attribute = self._create_view_and_port()
        labels = []

        with (
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Menu", return_value=_FakeMenu()),
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.MenuItem",
                side_effect=lambda label, **_kwargs: labels.append(label),
            ),
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Separator"),
        ):
            view._show_port_context_menu(port)

        self.assertEqual(labels, ["Rename", "Remove"])

    async def test_repeated_port_and_io_menus_replace_live_containers(self) -> None:
        """Canvas menus opened from pointer events must never clear in-place."""
        view, port, _model, _proxy_attribute = self._create_view_and_port()
        port_menus = [_FakeMenu(), _FakeMenu()]
        io_menus = [_FakeMenu(), _FakeMenu()]

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Menu",
                side_effect=port_menus,
            ),
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.MenuItem"),
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Separator"),
        ):
            view._show_port_context_menu(port)
            view._show_port_context_menu(port)

        self.assertTrue(port_menus[0].hidden)
        self.assertFalse(port_menus[1].hidden)
        self.assertIs(view._port_context_menu, port_menus[1])

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Menu",
                side_effect=io_menus,
            ),
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.MenuItem"),
        ):
            view._show_io_node_context_menu(0)
            view._show_io_node_context_menu(0)

        self.assertTrue(io_menus[0].hidden)
        self.assertFalse(io_menus[1].hidden)
        self.assertIs(view._io_node_context_menu, io_menus[1])

    async def test_nodegraph_port_rename_sets_display_name_metadata(self) -> None:
        """Rename action should set displayName metadata, not the property token."""
        view, port, model, proxy_attribute = self._create_view_and_port()

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.attributes.SetDisplayName",
            return_value=SimpleNamespace(success=True, message=""),
        ) as set_display_name:
            view._set_nodegraph_port_display_name(port, "Result")

        set_display_name.assert_called_once_with(port.path, "Result")
        self.assertEqual(proxy_attribute.display_name, "Result")
        port.update_proxy_attribute.assert_called_once_with(proxy_attribute)
        model._item_changed.assert_called_once_with(None)

    async def test_nodegraph_port_remove_removes_property(self) -> None:
        """Remove action should remove the backing interface property."""
        view, port, model, _proxy_attribute = self._create_view_and_port()

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.attributes.RemoveProperty",
            return_value=SimpleNamespace(success=True, message=""),
        ) as remove_property:
            view._remove_nodegraph_port(port)

        remove_property.assert_called_once_with(port.path)
        model._item_changed.assert_called_once_with(None)

    async def test_io_node_context_menu_has_remove(self) -> None:
        """InputNode/OutputNode wrappers should expose a Remove action."""
        view, _port, _model, _proxy_attribute = self._create_view_and_port()
        labels = []

        with (
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Menu", return_value=_FakeMenu()),
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.MenuItem",
                side_effect=lambda label, **_kwargs: labels.append(label),
            ),
        ):
            view._show_io_node_context_menu(0)

        self.assertEqual(labels, ["Remove"])

    async def test_remove_io_node_uses_isolation_wrapper(self) -> None:
        """Remove action should call the undoable isolation deletion wrapper."""
        view, _port, model, _proxy_attribute = self._create_view_and_port()
        model._model = object()
        node = view._scene_model_nodes[0]

        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.wrappers.isolation.DeleteInputOutputNodes",
            return_value=SimpleNamespace(success=True, message=""),
        ) as delete_nodes:
            view._remove_io_node(node)

        delete_nodes.assert_called_once_with(model, [node], model._model)

    async def test_right_click_io_node_body_shows_remove_menu(self) -> None:
        """Right-clicking an IO node body should open the IO-node context menu."""
        view, _port, _model, _proxy_attribute = self._create_view_and_port()
        view._color_picker_widget = None
        view._event_consumed = False
        view._screen_to_canvas = lambda x, y: (x, y)
        view._find_port_hit_at_canvas = MagicMock(return_value=None)
        view._find_node_at = MagicMock(return_value=view._scene_model_nodes[0])
        view._show_io_node_context_menu = MagicMock()

        view._on_mouse_pressed(10.0, 10.0, 1, 0)

        view._show_io_node_context_menu.assert_called_once_with(0)
        self.assertTrue(view._event_consumed)

    async def test_rewire_drop_clears_native_drag_before_disconnect_notify(self) -> None:
        """Dropped rewires should clear native drag state before model notifications rebuild."""

        class PortValue:
            """Records whether drag state was cleared before disconnect mutation."""

            def __init__(self, canvas) -> None:
                self.canvas = canvas
                self.events = []

            @property
            def inputs(self):
                return []

            @inputs.setter
            def inputs(self, value):
                self.events.append(("set_inputs", self.canvas.clear_drag_noodle.called, value))

        port = object()
        canvas = MagicMock()
        canvas.clear_drag_noodle.side_effect = lambda: port_value.events.append(("clear_drag", True, None))
        port_value = PortValue(canvas)

        view = GraphCanvasView.__new__(GraphCanvasView)
        view._resize_node_index = None
        view._pending_port_hit = None
        view._pending_port_canvas = None
        view._noodle_source = (0, 0, False)
        view._noodle_rewire = True
        view._noodle_rewire_port = port
        view._noodle_rewire_old_source = object()
        view._model = _FakeModel({port: port_value})
        view._canvas_widget = canvas
        view._deferred_disconnect_task = None
        view._deferred_disconnect_ports = []
        view._screen_to_canvas = lambda _x, _y: (0.0, 0.0)
        view._find_port_hit_at_canvas = MagicMock(return_value=None)
        view._is_material_output_sink_port = MagicMock(return_value=False)
        view._notify_connection_changed = MagicMock()

        view._on_mouse_released(0.0, 0.0, 0, 0)

        self.assertEqual(port_value.events[0][0], "clear_drag")
        self.assertEqual(len(port_value.events), 1)
        await view._deferred_disconnect_task
        self.assertEqual(port_value.events[1], ("set_inputs", True, []))
        view._notify_connection_changed.assert_called_once_with(
            port, reason="deferred_rewire_drop_disconnect", sync_item=True
        )

    async def test_deferred_rewire_drop_does_not_apply_after_model_swap(self) -> None:
        """Deferred disconnects should not mutate a replacement model."""

        class PortValue:
            def __init__(self) -> None:
                self.inputs_set = False

            @property
            def inputs(self):
                return []

            @inputs.setter
            def inputs(self, _value):
                self.inputs_set = True

        port = object()
        port_value = PortValue()
        old_model = _FakeModel({port: port_value})
        new_model = _FakeModel({})
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = old_model
        view._deferred_disconnect_task = None
        view._deferred_disconnect_ports = []

        view._defer_rewire_drop_disconnect(port)
        view._model = new_model
        await view._deferred_disconnect_task

        self.assertFalse(port_value.inputs_set)
        self.assertEqual(view._deferred_disconnect_ports, [])

    async def test_deferred_material_output_rewire_drop_requests_full_connection_refresh(self) -> None:
        """Material output dropped rewires need root refresh after USD disconnect."""

        proxy_attribute = SimpleNamespace(display_name="", name="outputs:surface")
        port = _MaterialOutputPortStub(Sdf.Path("/World/Looks/Mat.outputs:surface"), proxy_attribute)
        port_value = SimpleNamespace(inputs=[object()])
        model = _FakeModel({port: port_value})
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._deferred_disconnect_task = None
        view._deferred_disconnect_ports = []
        view._notify_connection_changed = MagicMock()

        view._defer_rewire_drop_disconnect(port)
        await view._deferred_disconnect_task

        self.assertEqual(port_value.inputs, [])
        view._notify_connection_changed.assert_called_once_with(
            None, reason="deferred_rewire_drop_disconnect", sync_item=True
        )

    async def test_deferred_rewire_rejection_does_not_emit_success_refresh(self) -> None:
        """A rejected deferred disconnect must not publish a connection-changed success signal."""
        port = object()
        port_value = SimpleNamespace(inputs=[object()], set_inputs=MagicMock(return_value=False))
        model = _FakeModel({port: port_value})
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._deferred_disconnect_task = None
        view._deferred_disconnect_ports = []
        view._notify_connection_changed = MagicMock()

        view._defer_rewire_drop_disconnect(port)
        await view._deferred_disconnect_task

        port_value.set_inputs.assert_called_once_with([])
        view._notify_connection_changed.assert_not_called()

    async def test_deferred_rewire_drop_rebuilds_if_notify_and_item_changed_fail(self) -> None:
        """A successful deferred disconnect should still force some visual refresh."""

        class PortValue:
            @property
            def inputs(self):
                return []

            @inputs.setter
            def inputs(self, _value):
                return

        port = object()
        model = _FakeModel({port: PortValue()})
        model._item_changed.side_effect = RuntimeError("refresh failed")
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._deferred_disconnect_task = None
        view._deferred_disconnect_ports = []
        view._is_material_output_sink_port = MagicMock(return_value=False)
        view._notify_connection_changed = MagicMock(side_effect=RuntimeError("notify failed"))
        view._rebuild_core = MagicMock()

        view._defer_rewire_drop_disconnect(port)
        await view._deferred_disconnect_task

        view._rebuild_core.assert_called_once_with()

    async def test_connect_to_material_output_requests_full_connection_refresh(self) -> None:
        """Material output connections can change root-visible graph contents."""
        output_port = object()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:surface")
        material_port = _MaterialOutputPortStub(Sdf.Path("/World/Looks/Mat.outputs:surface"), proxy_attribute)
        material_port_value = SimpleNamespace(inputs=[])
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = _FakeModel({material_port: material_port_value})
        view._canvas_widget = MagicMock()
        view._resize_node_index = None
        view._pending_port_hit = None
        view._pending_port_canvas = None
        view._noodle_source = (0, 0, False)
        view._noodle_rewire = False
        view._noodle_rewire_port = None
        view._noodle_rewire_old_source = None
        view._screen_to_canvas = lambda _x, _y: (0.0, 0.0)
        view._find_port_hit_at_canvas = MagicMock(return_value=(1, 0, True))
        view._resolve_port = MagicMock(side_effect=lambda ni, _pi: output_port if ni == 0 else material_port)
        view._notify_connection_changed = MagicMock()

        view._on_mouse_released(0.0, 0.0, 0, 0)

        self.assertEqual(material_port_value.inputs, [output_port])
        view._notify_connection_changed.assert_called_once_with(None, reason="connect")

    async def test_failed_rewire_keeps_old_source_and_does_not_notify_success(self) -> None:
        """Canvas rewires must verify the edit before clearing or reporting success."""

        class RefusingPortValue:
            def __init__(self, old_source) -> None:
                self._inputs = [old_source]
                self.assignments = []

            @property
            def inputs(self):
                return self._inputs

            @inputs.setter
            def inputs(self, value):
                self.assignments.append(value)

        old_output = object()
        new_output = object()
        input_port = object()
        port_value = RefusingPortValue(old_output)
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = _FakeModel({input_port: port_value})
        view._canvas_widget = MagicMock()
        view._resize_node_index = None
        view._pending_port_hit = None
        view._pending_port_canvas = None
        view._noodle_source = (0, 0, False)
        view._noodle_rewire = True
        view._noodle_rewire_port = input_port
        view._noodle_rewire_old_source = old_output
        view._screen_to_canvas = lambda _x, _y: (0.0, 0.0)
        view._find_port_hit_at_canvas = MagicMock(return_value=(1, 0, True))
        view._resolve_port = MagicMock(side_effect=lambda ni, _pi: new_output if ni == 0 else input_port)
        view._is_material_output_sink_port = MagicMock(return_value=False)
        view._defer_rewire_drop_disconnect = MagicMock()
        view._notify_connection_changed = MagicMock()

        view._on_mouse_released(0.0, 0.0, 0, 0)

        self.assertEqual(port_value.inputs, [old_output])
        self.assertEqual(port_value.assignments, [[new_output]])
        view._defer_rewire_drop_disconnect.assert_not_called()
        view._notify_connection_changed.assert_not_called()

    async def test_failed_two_port_rewire_restores_the_new_sink(self) -> None:
        """A failed old-sink disconnect must compensate the newly connected sink."""

        class PortValue:
            def __init__(self, inputs, refuse_clear: bool = False) -> None:
                self._inputs = list(inputs)
                self.refuse_clear = refuse_clear

            @property
            def inputs(self):
                return self._inputs

            @inputs.setter
            def inputs(self, value):
                if not (self.refuse_clear and not value):
                    self._inputs = list(value)

        old_output = object()
        new_output = object()
        target_old_output = object()
        old_input = object()
        target_input = object()
        old_value = PortValue([old_output], refuse_clear=True)
        target_value = PortValue([target_old_output])
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = _FakeModel({old_input: old_value, target_input: target_value})
        view._canvas_widget = MagicMock()
        view._resize_node_index = None
        view._pending_port_hit = None
        view._pending_port_canvas = None
        view._noodle_source = (0, 0, False)
        view._noodle_rewire = True
        view._noodle_rewire_port = old_input
        view._noodle_rewire_old_source = old_output
        view._screen_to_canvas = lambda _x, _y: (0.0, 0.0)
        view._find_port_hit_at_canvas = MagicMock(return_value=(1, 0, True))
        view._resolve_port = MagicMock(side_effect=lambda ni, _pi: new_output if ni == 0 else target_input)
        view._is_material_output_sink_port = MagicMock(return_value=False)
        view._defer_rewire_drop_disconnect = MagicMock()
        view._notify_connection_changed = MagicMock()

        view._on_mouse_released(0.0, 0.0, 0, 0)

        self.assertEqual(old_value.inputs, [old_output])
        self.assertEqual(target_value.inputs, [target_old_output])
        view._notify_connection_changed.assert_not_called()

    async def test_disconnect_material_output_port_uses_model_inputs_path(self) -> None:
        """Disconnecting a material output sink should route through model inputs."""
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:surface")
        port = _MaterialOutputPortStub(Sdf.Path("/World/Looks/Mat.outputs:surface"), proxy_attribute)
        port_value = SimpleNamespace(inputs=[object()])
        model = _FakeModel({port: port_value})
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._notify_connection_changed = MagicMock()

        self.assertTrue(view._disconnect_port(port))

        self.assertEqual(port_value.inputs, [])
        view._notify_connection_changed.assert_called_once_with(None, reason="disconnect_input_port", sync_item=True)

    async def test_disconnect_rejection_does_not_emit_success_notification(self) -> None:
        """A model-level disconnect failure must leave the source and notification state unchanged."""
        source = object()
        port = object()
        port_value = SimpleNamespace(inputs=[source], set_inputs=MagicMock(return_value=False))
        model = _FakeModel({port: port_value})
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._notify_connection_changed = MagicMock()

        self.assertFalse(view._disconnect_port(port))
        self.assertEqual(port_value.inputs, [source])
        view._notify_connection_changed.assert_not_called()

    async def test_disconnect_material_output_consumer_branch_requests_full_refresh(self) -> None:
        """Consumer-removal fallback still needs root refresh for material outputs."""
        owner = _OwnerShaderNode()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:surface")
        material_port = _MaterialOutputPortStub(Sdf.Path("/World/Looks/Mat.outputs:surface"), proxy_attribute)
        consumer_port = _PortStub(
            Sdf.Path("/World/Looks/Shader.inputs:surface"), SimpleNamespace(name="inputs:surface")
        )
        consumer_value = SimpleNamespace(inputs=[material_port])
        model = _FakeModel(
            {
                owner: SimpleNamespace(ports=[consumer_port]),
                material_port: SimpleNamespace(inputs=[]),
                consumer_port: consumer_value,
            }
        )
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [owner]
        view._notify_connection_changed = MagicMock()

        self.assertTrue(view._disconnect_port(material_port))

        self.assertEqual(consumer_value.inputs, [])
        view._notify_connection_changed.assert_called_once_with(
            None, reason="disconnect_output_consumer", sync_item=True
        )

    async def test_material_output_context_menu_detects_usd_output_connection(self) -> None:
        """Material output sinks should offer Disconnect from their UsdShade output."""
        owner = _OwnerShaderNode()
        proxy_attribute = SimpleNamespace(display_name="", name="outputs:surface")
        port = _MaterialOutputPortStub(Sdf.Path("/World/Looks/Mat.outputs:surface"), proxy_attribute)
        owner.prim = MagicMock()
        attr = MagicMock()
        owner.prim.GetAttribute.return_value = attr
        model = _FakeModel({owner: SimpleNamespace(ports=[port]), port: SimpleNamespace(inputs=[])})
        view = GraphCanvasView.__new__(GraphCanvasView)
        view._model = model
        view._scene_model_nodes = [owner]
        view._port_context_menu = None
        labels = []

        with (
            patch(f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.Menu", return_value=_FakeMenu()),
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.graph_canvas_view.ui.MenuItem",
                side_effect=lambda label, **_kwargs: labels.append(label),
            ),
            patch.object(UsdShade, "Output") as output_cls,
        ):
            output_cls.return_value.HasConnectedSource.return_value = True
            view._show_port_context_menu(port)

        self.assertIn("Disconnect", labels)
