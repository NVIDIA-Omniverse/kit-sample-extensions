# pylint: disable=relative-beyond-top-level,protected-access
from typing import Optional
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.ui.controllers.core.stage_lifecycle import StageLifecycleController
from ..base import MaterialGraphTestBase


class _DummyModel:
    """Model stub for stage lifecycle controller tests."""

    def __init__(
        self,
        parent: Optional["_DummyModel"] = None,
        exists: bool = False,
        prim_path: Optional[str] = None,
    ) -> None:
        """Initialize with an optional parent and prim existence."""
        self.parent = parent
        self._exists = exists
        self.prim_path = prim_path

    def prim_exists(self) -> bool:
        """Return whether the prim exists."""
        return self._exists


class _DummyWidget:
    """Widget stub for stage lifecycle controller tests."""

    def __init__(self, current_model: Optional[_DummyModel] = None, model: Optional[_DummyModel] = None) -> None:
        """Initialize with current and root models."""
        self.current_model = current_model
        self.model = model
        self.reset = MagicMock()
        self.set_current_compound = MagicMock()
        self.edit_graph = MagicMock()


class TestStageLifecycleController(MaterialGraphTestBase):
    """Stage lifecycle controller behavior."""

    def _assert_objects_changed_resets(self, widget: _DummyWidget) -> None:
        """Assert object-change handling resets a provided widget stub."""
        controller = StageLifecycleController(widget, usd_context=MagicMock())
        controller._handle_objects_changed()
        widget.reset.assert_called_once()

    async def test_selection_parent_cycle_resets(self) -> None:
        """Parent cycles should reset selection state."""
        node_a = _DummyModel()
        node_b = _DummyModel(parent=node_a)
        node_a.parent = node_b
        widget = _DummyWidget(current_model=node_a)

        self._assert_objects_changed_resets(widget)

    async def test_deleted_model_resets_widget(self) -> None:
        """Missing root prim should reset the widget."""
        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False))

        self._assert_objects_changed_resets(widget)

    async def test_valid_model_without_current_model_does_not_reset(self) -> None:
        """A valid root model without a compound selection should remain open."""
        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=True))

        controller = StageLifecycleController(widget, usd_context=MagicMock())
        controller._handle_objects_changed()

        widget.reset.assert_not_called()

    async def test_model_prim_exists_error_resets_widget(self) -> None:
        """Prim existence failures should fail closed to the startup state."""
        model = MagicMock()
        model.prim_exists.side_effect = RuntimeError("stage unavailable")
        model.prim_path = None
        widget = _DummyWidget(current_model=None, model=model)

        self._assert_objects_changed_resets(widget)

    async def test_current_model_prim_exists_error_resets_widget(self) -> None:
        """Selection existence failures should fail closed to the startup state."""
        current_model = MagicMock()
        current_model.prim_exists.side_effect = RuntimeError("selection unavailable")
        current_model.parent = None
        widget = _DummyWidget(current_model=current_model, model=None)

        self._assert_objects_changed_resets(widget)

    async def test_parent_prim_exists_error_resets_widget(self) -> None:
        """Parent existence failures should fail closed to the startup state."""
        parent = MagicMock()
        parent.prim_exists.side_effect = RuntimeError("parent unavailable")
        parent.parent = None
        current_model = _DummyModel(parent=parent, exists=False)
        widget = _DummyWidget(current_model=current_model, model=None)

        self._assert_objects_changed_resets(widget)

    async def test_deleted_material_does_not_reopen_selected_sibling(self) -> None:
        """Deleting the open material should not jump to an unrelated selected material."""
        old_path = Sdf.Path("/World/Looks/material")
        sibling_path = Sdf.Path("/World/Looks/sibling")
        UsdShade.Material.Define(self._stage, sibling_path)
        self._usd_context.get_selection().set_selected_prim_paths([sibling_path.pathString], True)

        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False, prim_path=old_path.pathString))
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [old_path]

        controller = StageLifecycleController(widget, usd_context=self._usd_context)
        controller._handle_objects_changed(notice)

        widget.edit_graph.assert_not_called()
        widget.reset.assert_called_once()

    async def test_renamed_material_reopens_selected_material(self) -> None:
        """Missing root prim should reopen a selected material sibling from the same resync."""
        old_path = Sdf.Path("/World/Looks/material")
        new_path = Sdf.Path("/World/Looks/material_renamed")
        UsdShade.Material.Define(self._stage, new_path)
        self._usd_context.get_selection().set_selected_prim_paths([new_path.pathString], True)

        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False, prim_path=old_path.pathString))
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [old_path, new_path]

        controller = StageLifecycleController(widget, usd_context=self._usd_context)
        controller._handle_objects_changed(notice)
        # The rename reopen is deliberately deferred out of the USD notice callback.
        await self._app.next_update_async()
        await self._app.next_update_async()

        widget.reset.assert_not_called()
        widget.edit_graph.assert_called_once_with(self._stage.GetPrimAtPath(new_path))

    async def test_renamed_material_reopens_when_selection_still_old_path(self) -> None:
        """Stage rename notices may arrive before selection advances to the new material path."""
        old_path = Sdf.Path("/World/Looks/material")
        new_path = Sdf.Path("/World/Looks/material_renamed")
        UsdShade.Material.Define(self._stage, new_path)
        self._usd_context.get_selection().set_selected_prim_paths([old_path.pathString], True)

        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False, prim_path=old_path.pathString))
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [old_path, new_path]

        controller = StageLifecycleController(widget, usd_context=self._usd_context)
        controller._handle_objects_changed(notice)
        await self._app.next_update_async()
        await self._app.next_update_async()

        widget.reset.assert_not_called()
        widget.edit_graph.assert_called_once_with(self._stage.GetPrimAtPath(new_path))

    async def test_stage_opening_cancels_deferred_rename_reopen(self) -> None:
        """Stage resets should cancel pending deferred rename recovery work."""
        old_path = Sdf.Path("/World/Looks/material")
        new_path = Sdf.Path("/World/Looks/material_renamed")
        UsdShade.Material.Define(self._stage, new_path)
        self._usd_context.get_selection().set_selected_prim_paths([new_path.pathString], True)

        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False, prim_path=old_path.pathString))
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [old_path, new_path]

        controller = StageLifecycleController(widget, usd_context=self._usd_context)
        controller._handle_objects_changed(notice)
        controller._on_stage_opening(MagicMock())
        await self._app.next_update_async()
        await self._app.next_update_async()

        widget.edit_graph.assert_not_called()
        widget.reset.assert_called_once()

    async def test_invalid_deferred_rename_candidate_resets_widget(self) -> None:
        """Deferred rename recovery should reset if the candidate disappears before reopen."""
        old_path = Sdf.Path("/World/Looks/material")
        new_path = Sdf.Path("/World/Looks/material_renamed")
        UsdShade.Material.Define(self._stage, new_path)
        self._usd_context.get_selection().set_selected_prim_paths([new_path.pathString], True)

        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False, prim_path=old_path.pathString))
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [old_path, new_path]

        controller = StageLifecycleController(widget, usd_context=self._usd_context)
        controller._handle_objects_changed(notice)
        self._stage.RemovePrim(new_path)
        await self._app.next_update_async()
        await self._app.next_update_async()

        widget.edit_graph.assert_not_called()
        widget.reset.assert_called_once()

    async def test_deferred_rename_reopen_coalesces_repeated_notices(self) -> None:
        """Repeated rename notices should keep only the latest deferred reopen."""
        old_path = Sdf.Path("/World/Looks/material")
        new_path = Sdf.Path("/World/Looks/material_renamed")
        UsdShade.Material.Define(self._stage, new_path)
        self._usd_context.get_selection().set_selected_prim_paths([new_path.pathString], True)

        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False, prim_path=old_path.pathString))
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [old_path, new_path]

        controller = StageLifecycleController(widget, usd_context=self._usd_context)
        controller._handle_objects_changed(notice)
        controller._handle_objects_changed(notice)
        await self._app.next_update_async()
        await self._app.next_update_async()

        widget.reset.assert_not_called()
        widget.edit_graph.assert_called_once_with(self._stage.GetPrimAtPath(new_path))

    async def test_set_visible_cancels_deferred_rename_reopen(self) -> None:
        """Rebinding visibility should not allow a stale deferred rename reopen to run."""
        old_path = Sdf.Path("/World/Looks/material")
        new_path = Sdf.Path("/World/Looks/material_renamed")
        UsdShade.Material.Define(self._stage, new_path)
        self._usd_context.get_selection().set_selected_prim_paths([new_path.pathString], True)

        widget = _DummyWidget(current_model=None, model=_DummyModel(exists=False, prim_path=old_path.pathString))
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [old_path, new_path]

        controller = StageLifecycleController(widget, usd_context=self._usd_context)
        controller._handle_objects_changed(notice)
        with (
            patch(f"{Paths.MODULE_ID}.scripts.ui.controllers.core.stage_lifecycle.Tf.Notice.Register"),
            patch(
                f"{Paths.MODULE_ID}.scripts.ui.controllers.core.stage_lifecycle.carb.eventdispatcher.get_eventdispatcher"
            ) as dispatcher_mock,
        ):
            dispatcher_mock.return_value.observe_event.return_value = MagicMock()
            controller.set_visible(True)
        await self._app.next_update_async()
        await self._app.next_update_async()

        widget.edit_graph.assert_not_called()
        widget.reset.assert_called_once()

    async def test_stage_opened_resets_widget(self) -> None:
        """Stage opened events should reset and rebind listeners."""
        widget = _DummyWidget()
        usd_context = MagicMock()
        usd_context.get_stage.return_value = MagicMock()

        controller = StageLifecycleController(widget, usd_context=usd_context)
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.core.stage_lifecycle.Tf.Notice.Register"
        ) as register_mock:
            controller._on_stage_opened(MagicMock())

        widget.reset.assert_called_once()
        register_mock.assert_called_once()
