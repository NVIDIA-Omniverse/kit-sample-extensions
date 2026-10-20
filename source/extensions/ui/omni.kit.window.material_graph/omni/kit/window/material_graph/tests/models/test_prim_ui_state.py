# pylint: disable=relative-beyond-top-level,no-member,protected-access
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from omni.kit.widget.graph import GraphModel
from pxr import Gf, Sdf, UsdShade, UsdUI

from ...scripts.commands.result import CommandResult
from ...scripts.config.paths import Paths
from ...scripts.models.graph.nodes.backdrop import BackdropModel
from ...scripts.models.graph.nodes.nodegraph import NodeGraphModel
from ...scripts.models.graph.nodes.prim.model import PrimModel
from ...scripts.models.graph.nodes.prim.ui_state import PrimUiState
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestPrimUiState(MaterialGraphTestBase):
    """Tests for prim UI state helpers."""

    async def test_sync_position_and_ui(self) -> None:
        """Position and UI attributes should sync from USD."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/Looks/Nodegraph"))
        prim = nodegraph.GetPrim()
        api = UsdUI.NodeGraphNodeAPI.Apply(prim)

        api.GetPosAttr().Set((1.0, 2.0))
        api.GetDisplayColorAttr().Set((0.1, 0.2, 0.3))
        api.GetStackingOrderAttr().Set(5)
        api.GetIconAttr().Set(Sdf.AssetPath("Preview.png", "C:/Temp/Preview.png"))

        ui_state = PrimUiState(prim, (10.0, 20.0))
        ui_state.sync_position()
        ui_state.sync_ui()

        self.assertEqual(ui_state.position, (1.0, 2.0))
        self.assertEqual(ui_state.display_color, (0.1, 0.2, 0.3))
        self.assertEqual(ui_state.stacking_order, 5)
        self.assertTrue(ui_state.preview.endswith("preview.png"))

    async def test_sync_size_defaults(self) -> None:
        """Size should default when not authored."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/Looks/NodegraphSize"))
        prim = nodegraph.GetPrim()
        UsdUI.NodeGraphNodeAPI.Apply(prim)

        ui_state = PrimUiState(prim, (10.0, 20.0))
        ui_state.sync_size()
        self.assertEqual(ui_state.size, (10.0, 20.0))

        api = UsdUI.NodeGraphNodeAPI(prim)
        api.GetSizeAttr().Set((3.0, 4.0))
        ui_state.sync_size()
        self.assertEqual(ui_state.size, (3.0, 4.0))

    async def test_prim_model_position_size_color_and_tooltip_state(self) -> None:
        """Prim UI mutations should delegate, deduplicate, author commands, and notify without rendering."""
        model = PrimModel.__new__(PrimModel)
        model._parent = None
        model._prim_path = Sdf.Path("/World/Node")
        model._path = model._prim_path
        model._type = UsdShade.Shader
        model._description = "Description"
        model._expansion_state = GraphModel.ExpansionState.OPEN
        model._sizes_on_begin_end = {}
        model._ui_state = SimpleNamespace(position=(1.0, 2.0), size=(100.0, 80.0), display_color=(0.1, 0.2, 0.3))
        model._outputs = SimpleNamespace(ports=["out"], connected_ports=["connected-out"])
        model._inputs = SimpleNamespace(ports=["in"], connected_ports=["connected-in"])
        model._item_changed = MagicMock()
        model.remove_position_cmd = MagicMock(return_value=CommandResult(True))
        model.set_position_cmd = MagicMock(return_value=CommandResult(True))

        self.assertTrue(model._positions_close((1.0, 2.0), (1.0001, 2.0001)))
        self.assertTrue(model._positions_close(Gf.Vec2d(1.0, 2.0), Gf.Vec2f(1.0001, 2.0001)))
        self.assertTrue(model._positions_close(Gf.Vec2f(1.0, 2.0), Gf.Vec2d(1.0001, 2.0001)))
        self.assertFalse(model._positions_close(Gf.Vec2d(1.0, 2.0), Gf.Vec2f(2.0, 3.0)))
        model.set_position((1.0, 2.0))
        model.set_position(None)
        model.remove_position_cmd.assert_called_once_with()
        model._item_changed.assert_called_with(model)
        model.set_position((5.0, 6.0), notify=False)
        model.set_position_cmd.assert_called_once_with((5.0, 6.0), prev=None)

        delegated = SimpleNamespace(set_position=MagicMock(), position=None)
        model.set_position((7.0, 8.0), delegated)
        delegated.set_position.assert_called_once_with((7.0, 8.0), notify=True)

        size_item = SimpleNamespace(prim_path=Sdf.Path("/World/Node"), size=(100.0, 80.0), set_size_cmd=MagicMock())
        model.size_begin_edit(size_item)
        PrimModel.size.fset(model, (120.0, 90.0), size_item)
        model.size_end_edit(size_item)
        size_item.set_size_cmd.assert_called_once_with([(100.0, 80.0), (120.0, 90.0)])

        with patch(f"{PrimModel.__module__}.SetDisplayColor", return_value=CommandResult(True)) as set_color:
            PrimModel.display_color.fset(model, None)
            PrimModel.display_color.fset(model, (0.1, 0.2))
            PrimModel.display_color.fset(model, (0.1, 0.2, 0.3))
            PrimModel.display_color.fset(model, (0.4, 0.5, 0.6, 1.0))
        set_color.assert_called_once_with(model.prim_path, (0.4, 0.5, 0.6), (0.1, 0.2, 0.3))
        self.assertEqual(model.display_color, (0.4, 0.5, 0.6))

        color_item = SimpleNamespace(display_color=None)
        PrimModel.display_color.fset(model, (1.0, 0.0, 0.0), color_item)
        self.assertEqual(color_item.display_color, (1.0, 0.0, 0.0))
        self.assertEqual(model.ports, ["out", "in"])
        self.assertEqual(model.connected_ports, ["connected-out", "connected-in"])
        self.assertIn("/World/Node", model.tooltip_text)
        self.assertIn("Description", model.tooltip_text)

    async def test_nodegraph_move_accepts_double_precision_cached_position(self) -> None:
        """A freshly authored Vec2d position must accept a Vec2f drag commit."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/Looks/MovableNodeGraph"))
        prim = nodegraph.GetPrim()
        key = f"omni:{UsdUI.Tokens.uiNodegraphNodePos}:mdl"
        prim.SetCustomDataByKey(key, Gf.Vec2d(10.0, 20.0))
        self.assertTrue(prim.HasAuthoredCustomDataKey(key))
        self.assertIsInstance(prim.GetCustomDataByKey(key), Gf.Vec2d)
        model = NodeGraphModel(prim, "mdl", self._usd_context, DummyPlugin(), None, sync=False)

        try:
            self.assertEqual(model._get_context_position_key(), key)
            model.sync_position()
            self.assertIsInstance(model._ui_state.position, Gf.Vec2d)

            self.assertTrue(model.set_position(Gf.Vec2f(30.0, 40.0), notify=False))

            authored = prim.GetCustomDataByKey(key)
            self.assertEqual(tuple(authored), (30.0, 40.0))
            self.assertEqual(tuple(model._ui_state.position), (30.0, 40.0))
        finally:
            model.destroy()

    async def test_failed_ui_commands_preserve_cached_position_and_color(self) -> None:
        """Failure injection must not make cached UI metadata diverge from USD."""
        model = PrimModel.__new__(PrimModel)
        model._parent = None
        model._prim = None
        model._prim_path = Sdf.Path("/World/Node")
        model._path = model._prim_path
        model._type = UsdShade.Shader
        model._ui_state = SimpleNamespace(position=(1.0, 2.0), display_color=(0.1, 0.2, 0.3))
        model._item_changed = MagicMock()
        model.set_position_cmd = MagicMock(return_value=CommandResult(False, error_code="injected"))

        self.assertFalse(model.set_position((5.0, 6.0)))
        self.assertEqual(model._ui_state.position, (1.0, 2.0))
        model._item_changed.assert_not_called()

        with patch(f"{PrimModel.__module__}.SetDisplayColor", return_value=CommandResult(False, error_code="injected")):
            PrimModel.display_color.fset(model, (0.4, 0.5, 0.6))
        self.assertEqual(model._ui_state.display_color, (0.1, 0.2, 0.3))
        model._item_changed.assert_not_called()

    async def test_backdrop_edits_commit_cache_only_after_commands_succeed(self) -> None:
        """Backdrop size and description edits must remain undoable and failure-safe."""
        prim = UsdUI.Backdrop.Define(self._stage, "/World/BackdropEdit").GetPrim()
        model = BackdropModel(prim, "mdl", self._usd_context, DummyPlugin(), None, sync=False)
        model._ui_state.size = (100.0, 80.0)
        model._description = "old"

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.backdrop.SetContextPosition",
            return_value=CommandResult(False, error_code="injected"),
        ):
            self.assertFalse(model.set_size_cmd([(100.0, 80.0), (200.0, 160.0)]))
        self.assertEqual(model._ui_state.size, (100.0, 80.0))

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.backdrop.SetContextPosition",
            return_value=CommandResult(True),
        ):
            self.assertTrue(model.set_size_cmd([(100.0, 80.0), (200.0, 160.0)]))
        self.assertEqual(model._ui_state.size, (200.0, 160.0))

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.backdrop.SetDescription",
            return_value=CommandResult(False, error_code="injected"),
        ):
            BackdropModel.description.fset(model, "new")
        self.assertEqual(model._description, "old")

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.backdrop.SetDescription",
            return_value=CommandResult(True),
        ):
            BackdropModel.description.fset(model, "new")
        self.assertEqual(model._description, "new")

        model._description = "new"
        self.assertTrue(model.set_description("authored on owning stage"))
        self.assertEqual(UsdUI.Backdrop(prim).GetDescriptionAttr().Get(), "authored on owning stage")

    async def test_expansion_state_routes_prim_proxy_and_self_notifications(self) -> None:
        """Expansion changes should notify the correct graph root for every supported item shape."""
        model = PrimModel.__new__(PrimModel)
        model._parent = None
        model._expansion_state = GraphModel.ExpansionState.OPEN
        model._item_changed = MagicMock()
        model.get_item_model = MagicMock(return_value=None)

        child = PrimModel.__new__(PrimModel)
        child._parent = None
        child._expansion_state = GraphModel.ExpansionState.OPEN
        child._item_changed = MagicMock()
        PrimModel.expansion_state.fset(model, GraphModel.ExpansionState.CLOSED, child)
        self.assertEqual(child._expansion_state, GraphModel.ExpansionState.CLOSED)
        child._item_changed.assert_called_once_with(None)

        proxy_root = SimpleNamespace(_item_changed=MagicMock())
        proxy = SimpleNamespace(expansion_state=GraphModel.ExpansionState.OPEN, model_root=proxy_root)
        PrimModel.expansion_state.fset(model, GraphModel.ExpansionState.MINIMIZED, proxy)
        self.assertEqual(proxy.expansion_state, GraphModel.ExpansionState.MINIMIZED)
        proxy_root._item_changed.assert_called_once_with(None)

        PrimModel.expansion_state.fset(model, GraphModel.ExpansionState.CLOSED)
        self.assertEqual(model._expansion_state, GraphModel.ExpansionState.CLOSED)
        model._item_changed.assert_called_once_with(None)
