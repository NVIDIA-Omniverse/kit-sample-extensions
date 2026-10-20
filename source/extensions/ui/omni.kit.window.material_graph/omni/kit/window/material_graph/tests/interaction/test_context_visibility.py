from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import omni.kit.undo
from pxr import UsdShade, UsdUI, Vt

from ...scripts.config.paths import Paths
from ...scripts.ui.controllers.core.context_visibility import ContextVisibilityController
from ..base import MaterialGraphTestBase

MODULE_ID = Paths.MODULE_ID


class _DummyPlugin:
    """Plugin stub for context visibility tests."""

    def __init__(self, name: str, display_name: str) -> None:
        """Initialize with name and display label."""
        self.name = name
        self.display_name = display_name


class _DummyContextManager:
    """Context manager stub returning plugin list."""

    def __init__(self, plugins: list[_DummyPlugin]) -> None:
        """Initialize with plugins."""
        self._plugins = plugins

    def get_plugins(self) -> list[_DummyPlugin]:
        """Return configured plugins."""
        return list(self._plugins)


class TestContextVisibilityController(MaterialGraphTestBase):
    """Context visibility controller behavior."""

    async def setUp(self) -> None:
        """Initialize controller with a dummy widget and manager."""
        await super().setUp()
        self._widget = SimpleNamespace(
            current_context="universal",
            _context_manager=_DummyContextManager([_DummyPlugin("universal", "Universal")]),
            request_model_refresh=MagicMock(),
            show_error=MagicMock(),
        )
        self._controller = ContextVisibilityController(self._widget)

    async def test_apply_to_prim_sets_custom_data(self) -> None:
        """Applying visibility should set custom data on nodegraphs."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/Graph")
        prim = nodegraph.GetPrim()

        with patch(
            f"{MODULE_ID}.scripts.ui.controllers.core.context_visibility.Settings.confine_nodegraphs", return_value=True
        ):
            self._controller.apply_to_prim(prim)

        data = prim.GetCustomDataByKey("omni:ui")
        self.assertIn("contextVisibility", data)
        self.assertIn("universal", data["contextVisibility"])
        self._widget.request_model_refresh.assert_called_once()

        self.assertTrue(omni.kit.undo.undo())
        self.assertFalse(prim.HasAuthoredCustomDataKey("omni:ui"))
        self.assertTrue(omni.kit.undo.redo())
        self.assertIn("universal", prim.GetCustomDataByKey("omni:ui")["contextVisibility"])

    async def test_apply_to_backdrop_sets_custom_data(self) -> None:
        """Applying visibility should set custom data on backdrops."""
        backdrop = UsdUI.Backdrop.Define(self._stage, "/World/BackdropApply")
        prim = backdrop.GetPrim()

        with patch(
            f"{MODULE_ID}.scripts.ui.controllers.core.context_visibility.Settings.confine_backdrops", return_value=True
        ):
            self._controller.apply_to_prim(prim)

        data = prim.GetCustomDataByKey("omni:ui")
        self.assertIn("contextVisibility", data)
        self.assertIn("universal", data["contextVisibility"])

    async def test_show_in_all_contexts_clears_metadata(self) -> None:
        """Clearing visibility should remove contextVisibility metadata."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/GraphClear")
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui", {"contextVisibility": ["universal"]})

        self._controller._set_context_visibility(prim, None)
        data = prim.GetCustomDataByKey("omni:ui")
        self.assertTrue(not data or "contextVisibility" not in data)

    async def test_get_context_visibility_reads_nested_metadata(self) -> None:
        """Context visibility reads should match the nested metadata written by creation helpers."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/GraphNested")
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui", {"contextVisibility": ["mdl"]})

        self.assertEqual(list(self._controller._get_context_visibility(prim)), ["mdl"])

    async def test_nested_context_visibility_overrides_stale_flat_metadata(self) -> None:
        """Nested context visibility is authoritative when old flat metadata also exists."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/GraphNestedPreferred")
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui:contextVisibility", Vt.StringArray(["universal"]))
        prim.SetCustomDataByKey("omni:ui", {"contextVisibility": Vt.StringArray(["mdl"])})

        self.assertEqual(list(self._controller._get_context_visibility(prim)), ["mdl"])

    async def test_toggle_on_empty_authored_list_does_not_imply_all_contexts(self) -> None:
        """Toggling an authored empty visibility list should not imply all contexts."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/GraphEmptyVisibility")
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui", {"contextVisibility": Vt.StringArray()})

        self._controller._toggle_context_visibility(prim, "universal", ["universal", "mdl"])

        self.assertEqual(list(self._controller._get_context_visibility(prim)), ["mdl"])

    async def test_toggle_visibility_updates_metadata(self) -> None:
        """Toggling visibility should add/remove context metadata."""
        backdrop = UsdUI.Backdrop.Define(self._stage, "/World/Backdrop")
        prim = backdrop.GetPrim()
        all_contexts = ["universal", "rtx"]

        self._controller._toggle_context_visibility(prim, "universal", all_contexts)
        data = prim.GetCustomDataByKey("omni:ui")
        self.assertIn("contextVisibility", data)

        self._controller._toggle_context_visibility(prim, "rtx", all_contexts)
        data = prim.GetCustomDataByKey("omni:ui")
        self.assertEqual(data["contextVisibility"], ["rtx"])

    async def test_apply_normalization_and_context_fallback_boundaries(self) -> None:
        """Invalid prim inputs are ignored and the active context is always represented."""
        self.assertIsNone(self._controller._normalize_prim(None))
        self.assertIsNone(self._controller._normalize_prim(True))
        self.assertIsNone(self._controller._normalize_prim(object()))
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/NormalizeGraph").GetPrim()
        self.assertIs(self._controller._normalize_prim([False, nodegraph]), nodegraph)

        self._widget.current_context = "mdl"
        self.assertEqual(
            self._controller._get_contexts(),
            [("universal", "Universal"), ("mdl", "mdl")],
        )
        self.assertIsNone(self._controller._normalize_visibility(None))
        self.assertEqual(self._controller._normalize_visibility("mdl"), ["mdl"])
        self.assertIsNone(self._controller._normalize_visibility(["", None]))
        self.assertEqual(self._controller._visibility_set(None, ["mdl", "universal"]), {"mdl", "universal"})

        self._controller.apply_to_prim(object())
        self._widget.current_context = ""
        self._controller.apply_to_prim(nodegraph)
        self._widget.request_model_refresh.assert_not_called()

    async def test_context_visibility_command_failure_is_reported(self) -> None:
        """Failed metadata commands surface through the widget error framework."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, "/World/FailedVisibility").GetPrim()
        result = SimpleNamespace(success=False, message="injected failure")
        with patch(
            f"{MODULE_ID}.scripts.ui.controllers.core.context_visibility.SetPrimCustomData",
            return_value=result,
        ):
            self.assertFalse(self._controller._set_context_visibility(nodegraph, ["universal"]))
        self._widget.show_error.assert_called_once_with("injected failure", log_message=False)
        self._widget.request_model_refresh.assert_not_called()

    async def test_context_visibility_menu_registration_lifecycle(self) -> None:
        """NodeGraph and Backdrop registrations are exactly paired at teardown."""
        with (
            patch(f"{MODULE_ID}.scripts.ui.controllers.core.context_visibility.add_node_menu_item") as add_item,
            patch(f"{MODULE_ID}.scripts.ui.controllers.core.context_visibility.remove_node_menu_item") as remove_item,
        ):
            self._controller.setup_menu_items()
            self.assertEqual(add_item.call_count, 2)
            callbacks = list(self._controller._menu_callbacks)
            self._controller.unregister_menu_items()
        self.assertEqual(remove_item.call_count, 2)
        self.assertEqual(self._controller._menu_callbacks, [])
        self.assertEqual([entry[0] for entry in callbacks], ["NodeGraph", "Backdrop"])
