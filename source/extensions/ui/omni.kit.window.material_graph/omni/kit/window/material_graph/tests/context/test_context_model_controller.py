# pylint: disable=relative-beyond-top-level,protected-access,no-member,attribute-defined-outside-init,unnecessary-lambda
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf

from ...scripts.context_manager.context_handle import ContextHandle
from ...scripts.ui.controllers.core.context_model import ContextModelController
from ...scripts.validation.result import ValidationResult
from ..base import MaterialGraphTestBase


class _FakeModel:
    """Minimal graph model used by controller tests."""

    def __init__(self, prim_path: Sdf.Path) -> None:
        """Initialize with a prim path."""
        self.prim_path = prim_path
        self.isolation_model = None
        self.active = False
        self._item_changed = None
        self._has_validation_errors = False
        self._has_validation_warnings = False

    def subscribe_item_changed(self, callback):
        """Register an item-changed callback and return a subscription shim."""
        self._item_changed = callback

        class _Subscription:
            def unsubscribe(self_inner):
                self._item_changed = None

        return _Subscription()

    def set_validation_state(self, has_errors: bool, has_warnings: bool) -> None:
        """Store context validation state from the widget."""
        self._has_validation_errors = has_errors
        self._has_validation_warnings = has_warnings


class _FakeWidget:
    """Minimal widget surface for context controller tests."""

    def __init__(self) -> None:
        """Initialize widget state."""
        self.model = None
        self.current_context = None
        self._toolbar_items = []
        self._errors = []
        self._compound_set = None
        self._refresh_calls = 0
        self._validation_result = None

    def set_current_compound(self, model: _FakeModel, _name: str) -> None:
        """Record the active compound model."""
        self._compound_set = model

    def set_toolbar_items(self, items: list[str]) -> None:
        """Record toolbar items set by the controller."""
        self._toolbar_items = items

    def get_toolbar_items(self, _context: str) -> list[str]:
        """Return a placeholder toolbar list."""
        return ["toolbar"]

    def update_style(self) -> None:
        """Record that a style update was requested."""
        self._style_updated = True

    def clear_error(self) -> None:
        """Clear tracked error messages."""
        self._errors.clear()

    def show_error(self, message: str, *, log_message: bool = True) -> None:
        """Record an error message."""
        self._errors.append(message)

    def request_model_refresh(self) -> None:
        """Record a model refresh request."""
        self._refresh_calls += 1

    def apply_validation_result(self, result: ValidationResult) -> None:
        """Record validation state updates."""
        self._validation_result = result


class _FailWidget(_FakeWidget):
    """Widget that raises on compound assignment."""

    def set_current_compound(self, model: _FakeModel, _name: str) -> None:
        """Raise to simulate widget failures."""
        raise RuntimeError("boom")


class _FakeCatalogModel:
    """Catalog model stub for controller tests."""

    def __init__(self) -> None:
        """Initialize with no plugin."""
        self.plugin = None

    def set_discovery_plugin(self, plugin: object) -> None:
        """Record the active discovery plugin."""
        self.plugin = plugin


class _FakeContextSwitcher:
    """Context switcher stub for controller tests."""

    def __init__(self) -> None:
        """Initialize refresh tracking."""
        self.refreshed = False

    def refresh_tabs(self) -> None:
        """Record a refresh request."""
        self.refreshed = True


class _FakeContext:
    """Context wrapper used by the fake manager."""

    def __init__(self, model: _FakeModel, plugin: object) -> None:
        """Initialize with a model and plugin."""
        self.model = model
        self.plugin = plugin


class TestContextModelController(MaterialGraphTestBase):
    """ContextModelController syncs widget, catalog, and context switcher when set_context or edit_graph
    is called. We test set_context updates widget and catalog, same-name refresh, missing context
    error, edit_graph load failure, and rollback on widget failure."""

    async def setUp(self) -> None:
        """Set a default material path used by tests."""
        await super().setUp()
        self._material_path = Sdf.Path("/Looks/material")

    async def tearDown(self) -> None:
        """Invoke base teardown."""
        await super().tearDown()

    async def test_set_context_updates_widget(self) -> None:
        """set_context updates model, catalog, toolbar."""
        widget = _FakeWidget()
        catalog = _FakeCatalogModel()
        switcher = _FakeContextSwitcher()

        plugin = SimpleNamespace(name="mdl")
        context = _FakeContext(_FakeModel(self._material_path), plugin)

        class FakeManager:
            """Context manager stub returning a fixed handle."""

            def get_context(self, _name: str) -> ContextHandle:
                """Return the fixed context handle."""
                return ContextHandle(context, plugin, "mdl")

            def validate_context(self, context_name: str) -> ValidationResult:
                return ValidationResult.ok(context_name)

        controller = ContextModelController(widget, switcher, FakeManager(), None, catalog)
        controller.set_context("mdl")

        self.assertIs(widget.model, context.model)
        self.assertTrue(widget.model.active)
        self.assertEqual(widget.current_context, "mdl")
        self.assertIs(catalog.plugin, plugin)
        self.assertEqual(widget._toolbar_items, ["toolbar"])
        self.assertTrue(switcher.refreshed)
        self.assertEqual(widget._refresh_calls, 0)

    async def test_set_context_same_name_updates_model(self) -> None:
        """set_context refreshes when name unchanged but model differs."""
        widget = _FakeWidget()
        catalog = _FakeCatalogModel()
        switcher = _FakeContextSwitcher()

        old_model = _FakeModel(self._material_path)
        old_model.active = True
        widget.model = old_model
        widget.current_context = "mdl"

        plugin = SimpleNamespace(name="mdl")
        new_model = _FakeModel(self._material_path.AppendChild("new"))
        context = _FakeContext(new_model, plugin)

        class FakeManager:
            """Context manager stub returning a fixed handle."""

            def get_context(self, _name: str) -> ContextHandle:
                """Return the fixed context handle."""
                return ContextHandle(context, plugin, "mdl")

            def validate_context(self, context_name: str) -> ValidationResult:
                return ValidationResult.ok(context_name)

        controller = ContextModelController(widget, switcher, FakeManager(), None, catalog)
        controller.set_context("mdl")

        self.assertIs(widget.model, new_model)
        self.assertTrue(widget.model.active)
        self.assertEqual(widget._refresh_calls, 0)

    async def test_set_context_missing_shows_error(self) -> None:
        """Missing context shows error and does not change model."""
        widget = _FakeWidget()
        widget.model = _FakeModel(self._material_path)
        widget.current_context = "mdl"

        class FakeManager:
            """Context manager stub returning an empty handle."""

            def get_context(self, _name: str) -> ContextHandle:
                """Return a missing context handle."""
                return ContextHandle(None, None, "missing")

            def validate_context(self, context_name: str) -> ValidationResult:
                return ValidationResult.ok(context_name)

        controller = ContextModelController(widget, _FakeContextSwitcher(), FakeManager(), None, _FakeCatalogModel())
        controller.set_context("missing")
        self.assertEqual(widget.current_context, "mdl")
        self.assertTrue(widget._errors)

    async def test_edit_graph_load_failure_shows_error(self) -> None:
        """edit_graph surfaces load error."""
        widget = _FakeWidget()
        catalog = _FakeCatalogModel()
        switcher = _FakeContextSwitcher()

        class FakeManager:
            """Context manager stub that fails loads."""

            def load(self, _path: str) -> bool:
                """Return False to simulate load failure."""
                return False

            def clear(self) -> None:
                """Record that clear was called."""
                self.cleared = True

            def validate_context(self, context_name: str) -> ValidationResult:
                return ValidationResult.ok(context_name)

        class FakeSelection:
            """Selection stub returning invalid prim paths."""

            def get_selected_prim_paths(self) -> list[str]:
                """Return a placeholder invalid selection."""
                return ["/Invalid"]

        usd_context = SimpleNamespace(get_selection=lambda: FakeSelection())
        controller = ContextModelController(widget, switcher, FakeManager(), usd_context, catalog)
        controller.edit_graph()
        self.assertTrue(widget._errors)

    async def test_edit_graph_non_material_selection_silently_ignored(self) -> None:
        """Non-material stage selection should not surface context-load errors."""
        widget = _FakeWidget()
        catalog = _FakeCatalogModel()
        switcher = _FakeContextSwitcher()

        class FakeManager:
            """Context manager stub recording clear calls."""

            def __init__(self) -> None:
                self.cleared = False

            def load(self, _path: str) -> bool:
                return False

            def clear(self) -> None:
                self.cleared = True

            def validate_context(self, context_name: str) -> ValidationResult:
                return ValidationResult.ok(context_name)

        class FakeSelection:
            """Selection stub returning /World."""

            def get_selected_prim_paths(self) -> list[str]:
                return ["/World"]

        class FakePrim:
            """Non-material prim with no bound material."""

            @staticmethod
            def IsValid() -> bool:
                return True

            @staticmethod
            def IsA(_type) -> bool:
                return False

            @staticmethod
            def GetPath() -> Sdf.Path:
                return Sdf.Path("/World")

        class FakeStage:
            """Stage stub returning the fake world prim."""

            @staticmethod
            def GetPrimAtPath(_path: str) -> FakePrim:
                return FakePrim()

        manager = FakeManager()
        usd_context = SimpleNamespace(get_selection=lambda: FakeSelection(), get_stage=lambda: FakeStage())
        controller = ContextModelController(widget, switcher, manager, usd_context, catalog)
        controller.edit_graph()

        self.assertFalse(widget._errors)
        self.assertTrue(manager.cleared)

    async def test_edit_graph_same_material_is_noop(self) -> None:
        """Editing the already-open material should not reload or clear contexts."""
        widget = _FakeWidget()
        catalog = _FakeCatalogModel()
        switcher = _FakeContextSwitcher()
        widget.model = _FakeModel(self._material_path)
        material_path = self._material_path

        class FakeManager:
            """Context manager stub tracking load/clear calls."""

            def __init__(self) -> None:
                self.load_calls = 0
                self.clear_calls = 0

            def load(self, _path: str) -> bool:
                self.load_calls += 1
                return True

            def clear(self) -> None:
                self.clear_calls += 1

            def validate_context(self, context_name: str) -> ValidationResult:
                return ValidationResult.ok(context_name)

        class FakeSelection:
            """Selection stub returning currently loaded material path."""

            def get_selected_prim_paths(self) -> list[str]:
                return [str(material_path)]

        manager = FakeManager()
        usd_context = SimpleNamespace(get_selection=lambda: FakeSelection())
        controller = ContextModelController(widget, switcher, manager, usd_context, catalog)
        controller.edit_graph()

        self.assertEqual(manager.load_calls, 0)
        self.assertEqual(manager.clear_calls, 0)
        self.assertFalse(widget._errors)

    async def test_set_context_rolls_back_on_failure(self) -> None:
        """set_context restores previous model on widget failure."""
        widget = _FailWidget()
        catalog = _FakeCatalogModel()
        switcher = _FakeContextSwitcher()

        old_model = _FakeModel(self._material_path)
        old_model.active = True
        widget.model = old_model
        widget.current_context = "mdl"

        plugin = SimpleNamespace(name="mdl2")
        context = _FakeContext(_FakeModel(self._material_path), plugin)

        class FakeManager:
            """Context manager stub returning a fixed handle."""

            def get_context(self, _name: str) -> ContextHandle:
                """Return the fixed context handle."""
                return ContextHandle(context, plugin, "mdl2")

            def validate_context(self, context_name: str) -> ValidationResult:
                return ValidationResult.ok(context_name)

        controller = ContextModelController(widget, switcher, FakeManager(), None, catalog)
        result = controller.set_context("mdl2", log_errors=False)

        self.assertFalse(result)
        self.assertIs(widget.model, old_model)
        self.assertEqual(widget.current_context, "mdl")
        self.assertTrue(widget.model.active)
        self.assertGreaterEqual(widget._refresh_calls, 1)

        with patch(f"{ContextModelController.__module__}.log_exception") as log_failure:
            result = controller.set_context("mdl2", log_errors=True)
        self.assertFalse(result)
        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], RuntimeError)

    async def test_open_and_new_graph_route_created_and_fallback_targets(self) -> None:
        """Open/new graph should clear solo state, route command payloads, and focus the result."""
        widget = _FakeWidget()
        widget._solo_controller = SimpleNamespace(clear=MagicMock())
        widget.focus_all_nodes = MagicMock()
        manager = SimpleNamespace(clear=MagicMock())
        controller = ContextModelController(widget, _FakeContextSwitcher(), manager, None, _FakeCatalogModel())
        controller.edit_graph = MagicMock()

        with patch(
            f"{ContextModelController.__module__}.CreateMaterial",
            return_value=SimpleNamespace(success=True, payload=Sdf.Path("/Looks/NewMaterial")),
        ):
            controller.open_graph(None)
        controller.edit_graph.assert_called_once_with(Sdf.Path("/Looks/NewMaterial"))
        widget.focus_all_nodes.assert_called_once_with()
        widget._solo_controller.clear.assert_called_once_with()

        controller.edit_graph.reset_mock()
        with patch(
            f"{ContextModelController.__module__}.CreateMaterial",
            return_value=SimpleNamespace(success=False, payload=None),
        ):
            controller.new_graph()
        controller.edit_graph.assert_called_once_with()

        prim = object()
        controller.edit_graph.reset_mock()
        controller.open_graph(prim)
        controller.edit_graph.assert_called_once_with(prim)
        controller.destroy()

    async def test_resolve_edit_target_handles_selection_material_binding_and_failures(self) -> None:
        """Edit-target resolution should support selections and bindings without surfacing invalid prims."""
        widget = _FakeWidget()
        selection = SimpleNamespace(get_selected_prim_paths=lambda: [])
        usd_context = SimpleNamespace(get_selection=lambda: selection, get_stage=lambda: None)
        controller = ContextModelController(
            widget, _FakeContextSwitcher(), SimpleNamespace(), usd_context, _FakeCatalogModel()
        )
        self.assertIsNone(controller._resolve_edit_target_path())

        selection.get_selected_prim_paths = lambda: ["/Looks/Selected"]
        self.assertEqual(controller._resolve_edit_target_path(), Sdf.Path("/Looks/Selected"))
        invalid = SimpleNamespace(IsValid=lambda: False)
        self.assertIsNone(controller._resolve_edit_target_path(invalid))

        material = SimpleNamespace(
            IsValid=lambda: True,
            IsA=lambda schema: True,
            GetPath=lambda: Sdf.Path("/Looks/Material"),
        )
        self.assertEqual(controller._resolve_edit_target_path(material), Sdf.Path("/Looks/Material"))

        mesh = SimpleNamespace(
            IsValid=lambda: True,
            IsA=lambda schema: False,
            GetPath=lambda: Sdf.Path("/World/Mesh"),
        )
        bound_prim = SimpleNamespace(IsValid=lambda: True, GetPath=lambda: Sdf.Path("/Looks/Bound"))
        bound_material = SimpleNamespace(GetPrim=lambda: bound_prim)
        with patch(f"{ContextModelController.__module__}.UsdShade.MaterialBindingAPI") as binding_api:
            binding_api.return_value.ComputeBoundMaterial.return_value = (bound_material, None)
            self.assertEqual(controller._resolve_edit_target_path(mesh), Sdf.Path("/Looks/Bound"))
            binding_api.return_value.ComputeBoundMaterial.side_effect = RuntimeError("binding failure")
            self.assertIsNone(controller._resolve_edit_target_path(mesh))
        controller.destroy()

    async def test_same_context_validation_and_compound_signature_paths(self) -> None:
        """Same-context refresh and both compound setter signatures should remain supported."""
        widget = _FakeWidget()
        model = _FakeModel(self._material_path)
        widget.model = model
        widget.current_context = "mdl"
        handle = ContextHandle(_FakeContext(model, object()), object(), "mdl")
        manager = SimpleNamespace(
            get_context=lambda _name: handle,
            validate_context=lambda name: ValidationResult.ok(name),
        )
        controller = ContextModelController(widget, _FakeContextSwitcher(), manager, None, _FakeCatalogModel())
        controller._schedule_validation = MagicMock()

        self.assertTrue(controller.set_context("mdl"))
        self.assertEqual(widget._refresh_calls, 1)
        controller._schedule_validation.assert_called_once_with("mdl")

        calls = []
        widget.set_current_compound = lambda selected, name, refresh=True: calls.append((selected, name, refresh))
        controller._set_current_compound_supports_refresh = None
        controller._set_current_compound_without_refresh(model)
        self.assertEqual(calls, [(model, True, False)])
        controller.destroy()

    async def test_listener_validation_and_destroy_failure_paths(self) -> None:
        """Listener fallbacks and validation tasks should be contained and released on teardown."""
        widget = _FakeWidget()
        widget.current_context = "mdl"
        manager = SimpleNamespace(validate_context=lambda name: ValidationResult.ok(name))
        controller = ContextModelController(widget, _FakeContextSwitcher(), manager, None, _FakeCatalogModel())

        release = MagicMock()
        controller._model_changed_subscription = SimpleNamespace(
            unsubscribe=MagicMock(side_effect=AttributeError("legacy")),
            release=release,
        )
        controller._unsubscribe_model_listener()
        release.assert_called_once_with()

        failing_model = SimpleNamespace(subscribe_item_changed=MagicMock(side_effect=RuntimeError("subscribe")))
        controller._bind_model_listener(failing_model)
        self.assertIsNone(controller._model_changed_subscription)
        controller._bind_model_listener(None)

        controller._on_model_item_changed()
        await self._app.next_update_async()
        await self._app.next_update_async()
        self.assertIsNotNone(widget._validation_result)

        controller.destroy()
        self.assertIsNone(controller._widget)
        self.assertIsNone(controller._lifecycle)

    async def test_position_only_model_changes_do_not_schedule_semantic_validation(self) -> None:
        """Dragging a node must not rerun semantic validation or repeat unchanged diagnostics."""
        widget = _FakeWidget()
        widget.current_context = "mtlx"
        widget.model = _FakeModel(self._material_path)
        position_item = object()
        widget.model.consume_position_only_validation_changed = MagicMock(
            side_effect=lambda item: item is position_item
        )
        controller = ContextModelController(
            widget,
            _FakeContextSwitcher(),
            SimpleNamespace(),
            None,
            _FakeCatalogModel(),
        )
        controller._schedule_validation = MagicMock()

        controller._on_model_item_changed(position_item)
        controller._on_model_item_changed(object())
        widget.current_context = None
        controller._on_model_item_changed(position_item)

        self.assertEqual(widget.model.consume_position_only_validation_changed.call_count, 3)
        controller._schedule_validation.assert_called_once_with("mtlx")
        controller.destroy()
