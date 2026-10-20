"""Fast controller coverage for render-context solo behavior."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import omni.kit.test
from pxr import Usd, UsdShade

from ...scripts.ui.controllers.core import context_solo as context_solo_module
from ...scripts.ui.controllers.core.context_solo import ContextSoloController, is_solo_supported


class _Plugin:
    def __init__(self, name, output_names=None, error=None) -> None:
        self.name = name
        self._output_names = output_names or []
        self._error = error

    def get_material_output_names(self):
        if self._error:
            raise self._error
        return self._output_names


class TestContextSoloController(omni.kit.test.AsyncTestCase):
    """Exercise solo state and command routing without opening the graph UI."""

    @staticmethod
    def _material_fixture():
        stage = Usd.Stage.CreateInMemory()
        material = UsdShade.Material.Define(stage, "/Material")
        mtlx_output = material.CreateSurfaceOutput("mtlx")
        mdl_output = material.CreateSurfaceOutput("mdl")
        widget = SimpleNamespace(
            _stage=stage,
            model=SimpleNamespace(prim=material.GetPrim()),
            rebuild_graph_toolbar=MagicMock(),
            ignore_stage_listener_paths=MagicMock(),
            unignore_stage_listener_paths=MagicMock(),
        )
        plugins = [
            _Plugin("mtlx", ["outputs:mtlx:surface"]),
            _Plugin("mdl", ["outputs:mdl:surface"]),
        ]
        manager = SimpleNamespace(get_plugins=MagicMock(return_value=plugins))
        return material, mtlx_output, mdl_output, widget, manager

    async def test_solo_support_gate_handles_fabric_and_versions(self) -> None:
        settings = SimpleNamespace(get_as_bool=MagicMock(return_value=False))
        with patch.object(context_solo_module.carb.settings, "get_settings", return_value=settings):
            self.assertEqual(is_solo_supported(), (True, ""))

        settings.get_as_bool.return_value = True
        with (
            patch.object(context_solo_module.carb.settings, "get_settings", return_value=settings),
            patch.object(
                context_solo_module.omni.kit.app,
                "get_app",
                return_value=SimpleNamespace(get_kit_version_short=lambda: "110.4.0"),
            ),
        ):
            supported, reason = is_solo_supported()
            self.assertFalse(supported)
            self.assertIn("110.4.0", reason)

        with (
            patch.object(context_solo_module.carb.settings, "get_settings", return_value=settings),
            patch.object(
                context_solo_module.omni.kit.app,
                "get_app",
                return_value=SimpleNamespace(get_kit_version_short=lambda: "111.0.0"),
            ),
        ):
            self.assertEqual(is_solo_supported(), (True, ""))

    async def test_solo_support_gate_contains_missing_or_malformed_version(self) -> None:
        settings = SimpleNamespace(get_as_bool=MagicMock(return_value=True))
        with (
            patch.object(context_solo_module.carb.settings, "get_settings", return_value=settings),
            patch.object(context_solo_module.omni.kit.app, "get_app", return_value=None),
        ):
            supported, reason = is_solo_supported()
            self.assertFalse(supported)
            self.assertIn("unknown", reason)

        with (
            patch.object(context_solo_module.carb.settings, "get_settings", return_value=settings),
            patch.object(
                context_solo_module.omni.kit.app,
                "get_app",
                return_value=SimpleNamespace(get_kit_version_short=lambda: "not-a-version"),
            ),
        ):
            supported, reason = is_solo_supported()
            self.assertFalse(supported)
            self.assertIn("not-a-version", reason)

    async def test_toggle_routes_solo_unsolo_and_rebuild(self) -> None:
        widget = SimpleNamespace(rebuild_graph_toolbar=MagicMock())
        controller = ContextSoloController(widget, object())
        controller._solo = MagicMock()
        controller._unsolo = MagicMock()
        with patch.object(context_solo_module, "is_solo_supported", return_value=(True, "")):
            controller.toggle_solo("mtlx")
            controller._solo.assert_called_once_with("mtlx")
            controller._soloed_context = "mtlx"
            controller.toggle_solo("mtlx")
            controller._unsolo.assert_called_once_with()
        self.assertEqual(widget.rebuild_graph_toolbar.call_count, 2)

    async def test_toggle_unsupported_is_a_noop(self) -> None:
        widget = SimpleNamespace(rebuild_graph_toolbar=MagicMock())
        controller = ContextSoloController(widget, object())
        controller._solo = MagicMock()
        with (
            patch.object(context_solo_module, "is_solo_supported", return_value=(False, "blocked")),
            patch.object(context_solo_module.logger, "warning") as warning,
        ):
            controller.toggle_solo("mtlx")
        controller._solo.assert_not_called()
        widget.rebuild_graph_toolbar.assert_not_called()
        warning.assert_called_once_with("context solo unavailable: %s", "blocked")

    async def test_clear_only_unsolos_active_context(self) -> None:
        widget = SimpleNamespace(rebuild_graph_toolbar=MagicMock())
        controller = ContextSoloController(widget, object())
        controller._unsolo = MagicMock()
        controller.clear()
        controller._unsolo.assert_not_called()
        controller._soloed_context = "mtlx"
        controller.clear()
        controller._unsolo.assert_called_once_with()
        widget.rebuild_graph_toolbar.assert_called_once_with()

    async def test_solo_authors_state_and_ignores_all_output_paths(self) -> None:
        material, mtlx_output, mdl_output, widget, manager = self._material_fixture()
        controller = ContextSoloController(widget, manager)
        result = SimpleNamespace(success=True, message="")
        with patch.object(context_solo_module, "SoloContext", return_value=result) as solo_command:
            controller._solo("mtlx")

        solo_command.assert_called_once_with(material.GetPath(), ["mdl:surface"], stage=material.GetPrim().GetStage())
        ignored = widget.ignore_stage_listener_paths.call_args.args[0]
        self.assertEqual(set(ignored), {mtlx_output.GetAttr().GetPath(), mdl_output.GetAttr().GetPath()})
        self.assertEqual(controller.soloed_context, "mtlx")
        self.assertEqual(controller._disconnected_outputs, ["mdl:surface"])
        self.assertEqual(controller._ignored_attr_paths, ignored)

    async def test_solo_failure_releases_listener_paths_and_keeps_state_clear(self) -> None:
        _material, _mtlx_output, _mdl_output, widget, manager = self._material_fixture()
        controller = ContextSoloController(widget, manager)
        result = SimpleNamespace(success=False, message="injected")
        with patch.object(context_solo_module, "SoloContext", return_value=result):
            controller._solo("mtlx")
        widget.ignore_stage_listener_paths.assert_called_once()
        widget.unignore_stage_listener_paths.assert_called_once_with(
            widget.ignore_stage_listener_paths.call_args.args[0]
        )
        self.assertIsNone(controller.soloed_context)
        self.assertEqual(controller._disconnected_outputs, [])

    async def test_solo_without_material_is_safe(self) -> None:
        controller = ContextSoloController(None, SimpleNamespace(get_plugins=lambda: []))
        with (
            patch.object(context_solo_module, "SoloContext") as solo_command,
            patch.object(context_solo_module.logger, "warning") as warning,
        ):
            controller._solo("mtlx")
        solo_command.assert_not_called()
        warning.assert_called_once_with(
            "context solo '%s' was not applied: no valid material prim is loaded (model_path=%s)",
            "mtlx",
            "<none>",
        )

    async def test_solo_replaces_an_existing_solo_first(self) -> None:
        _material, _mtlx_output, _mdl_output, widget, manager = self._material_fixture()
        controller = ContextSoloController(widget, manager)
        controller._soloed_context = "mdl"
        controller._unsolo = MagicMock()
        with patch.object(
            context_solo_module,
            "SoloContext",
            return_value=SimpleNamespace(success=True, message=""),
        ):
            controller._solo("mtlx")
        controller._unsolo.assert_called_once_with()
        self.assertEqual(controller.soloed_context, "mtlx")

    async def test_unsolo_restores_command_and_clears_state(self) -> None:
        material, _mtlx_output, mdl_output, widget, manager = self._material_fixture()
        controller = ContextSoloController(widget, manager)
        controller._soloed_context = "mtlx"
        controller._disconnected_outputs = ["mdl:surface"]
        controller._ignored_attr_paths = [mdl_output.GetAttr().GetPath()]
        with patch.object(
            context_solo_module, "UnsoloContext", return_value=SimpleNamespace(success=True, message="")
        ) as unsolo_command:
            self.assertTrue(controller._unsolo())
        widget.unignore_stage_listener_paths.assert_called_once_with([mdl_output.GetAttr().GetPath()])
        unsolo_command.assert_called_once_with(
            material.GetPath(),
            ["mdl:surface"],
            stage=material.GetPrim().GetStage(),
        )
        self.assertIsNone(controller.soloed_context)
        self.assertEqual(controller._disconnected_outputs, [])
        self.assertEqual(controller._ignored_attr_paths, [])

    async def test_unsolo_failure_preserves_recovery_state(self) -> None:
        """A failed reconnect must retain the solo snapshot so the operation can be retried."""
        _material, _mtlx_output, mdl_output, widget, manager = self._material_fixture()
        controller = ContextSoloController(widget, manager)
        controller._soloed_context = "mtlx"
        controller._disconnected_outputs = ["mdl:surface"]
        controller._ignored_attr_paths = [mdl_output.GetAttr().GetPath()]
        with patch.object(
            context_solo_module, "UnsoloContext", return_value=SimpleNamespace(success=False, message="injected")
        ):
            self.assertFalse(controller._unsolo())
        self.assertEqual(controller.soloed_context, "mtlx")
        self.assertEqual(controller._disconnected_outputs, ["mdl:surface"])
        self.assertEqual(controller._ignored_attr_paths, [mdl_output.GetAttr().GetPath()])

    async def test_unsolo_without_material_or_outputs_clears_state(self) -> None:
        controller = ContextSoloController(None, object())
        controller._soloed_context = "mtlx"
        controller._disconnected_outputs = ["mdl:surface"]
        controller._ignored_attr_paths = ["path"]
        with patch.object(context_solo_module, "UnsoloContext") as unsolo_command:
            controller._unsolo()
        unsolo_command.assert_not_called()
        self.assertIsNone(controller.soloed_context)
        self.assertEqual(controller._disconnected_outputs, [])
        self.assertEqual(controller._ignored_attr_paths, [])

    async def test_material_lookup_covers_widget_model_and_prim_states(self) -> None:
        controller = ContextSoloController(None, object())
        self.assertIsNone(controller._get_material_prim())
        controller._widget = SimpleNamespace(model=None)
        self.assertIsNone(controller._get_material_prim())
        invalid = SimpleNamespace(IsValid=lambda: False)
        controller._widget = SimpleNamespace(model=SimpleNamespace(prim=invalid))
        self.assertIsNone(controller._get_material_prim())
        valid = SimpleNamespace(IsValid=lambda: True)
        controller._widget = SimpleNamespace(model=SimpleNamespace(prim=valid))
        self.assertIs(controller._get_material_prim(), valid)

    async def test_output_name_collection_contains_plugin_failures(self) -> None:
        plugins = [
            _Plugin("mtlx", ["outputs:mtlx:surface", "custom"]),
            _Plugin("mdl", ["outputs:mdl:surface"]),
            _Plugin("broken", error=RuntimeError("injected")),
        ]
        controller = ContextSoloController(None, SimpleNamespace(get_plugins=lambda: plugins))
        self.assertEqual(controller._get_soloed_output_names("mtlx"), ["mtlx:surface", "custom"])
        with patch.object(context_solo_module.logger, "warning") as warning:
            self.assertEqual(controller._get_non_soloed_output_names("mtlx"), ["mdl:surface"])
        warning.assert_called_once()

    async def test_destroy_clears_solo_and_references(self) -> None:
        widget = SimpleNamespace(rebuild_graph_toolbar=MagicMock())
        controller = ContextSoloController(widget, object())
        controller.clear = MagicMock()
        controller.destroy()
        controller.clear.assert_called_once_with()
        self.assertIsNone(controller._widget)
        self.assertIsNone(controller._context_manager)
