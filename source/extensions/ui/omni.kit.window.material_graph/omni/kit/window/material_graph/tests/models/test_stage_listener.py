from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pxr import Sdf, Usd, UsdShade, UsdUI

from ...scripts.models.graph.nodes.material import MaterialModel
from ...scripts.models.graph.nodes.nodegraph.stage_listener.listener import StageListener
from ...scripts.models.graph.nodes.nodegraph.stage_listener.manager import StageListenerManager
from ...scripts.utils.lifecycle_registry import LifecycleRegistry
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


def _consume_task(coro: Any, **_kwargs: Any) -> MagicMock:
    """Consume and return a completed task mock."""
    coro.close()
    task = MagicMock()
    task.done.return_value = True
    return task


class TestStageListener(MaterialGraphTestBase):
    """StageListener dirty-path handling coverage."""

    async def setUp(self) -> None:
        """Load the scene and wire a StageListener to a model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._plugin = DummyPlugin()
        self._validator = MaterialValidator()
        material_prim = self._get_prim_at_path(self._material_path)
        self._model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)
        self._listener = StageListener(self._model, self._stage)
        self._listener._revoke_listener()

    async def test_info_property_triggers_refresh(self) -> None:
        """Info properties should invalidate the model."""
        self._model._item_changed = MagicMock()
        info_prop = self._material_path.AppendProperty("info:test")
        self._listener._update_dirty({self._material_path}, {info_prop})
        self._model._item_changed.assert_called_with(None)

    async def test_on_objects_changed_accumulates_dirty_paths(self) -> None:
        """Changed info paths should populate dirty path sets."""
        info_prop = self._material_path.AppendProperty("info:test")
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = []
        notice.GetChangedInfoOnlyPaths.return_value = [info_prop]

        self._listener._lifecycle.add_task = MagicMock(side_effect=_consume_task)

        self._listener._on_objects_changed(notice, self._stage)
        self.assertIn(self._material_path, self._listener._dirty_prim_paths)
        self.assertIn(info_prop, self._listener._dirty_prop_paths)

    async def test_collect_changed_paths_merges_resync_and_info_sets(self) -> None:
        """Mixed notices must not drop info-only paths when resync has prims and properties."""
        resync_prop = self._shader_path.AppendProperty("inputs:diffuseColor")
        info_prop = self._material_path.AppendProperty("info:test")
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = [self._shader_path, resync_prop]
        notice.GetChangedInfoOnlyPaths.return_value = [info_prop]

        prims, props = self._listener._collect_changed_paths(notice)

        self.assertIn(self._shader_path, prims)
        self.assertIn(resync_prop, props)
        self.assertIn(info_prop, props)

    async def test_customdata_info_change_triggers_dirty_prop_marker(self) -> None:
        """customData metadata changes should mark customData property refresh."""
        # Undo/redo for metadata-backed node positions depends on this marker;
        # without it, metadata changes can miss immediate graph refresh.
        notice = MagicMock()
        notice.GetResyncedPaths.return_value = []
        notice.GetChangedInfoOnlyPaths.return_value = [self._material_path]
        notice.GetChangedFields.return_value = ["customData"]

        self._listener._lifecycle.add_task = MagicMock(side_effect=_consume_task)
        self._listener._on_objects_changed(notice, self._stage)

        self.assertIn(self._material_path, self._listener._dirty_prim_paths)
        self.assertIn(self._material_path.AppendProperty("customData"), self._listener._dirty_prop_paths)

    async def test_dirty_paths_overflow_forces_full_refresh(self) -> None:
        """Dirty-path overflow should coalesce to a full refresh instead of dropping queued paths."""
        notice = MagicMock()
        prims_changed = [Sdf.Path(f"/World/prim_{idx}") for idx in range(self._listener.MAX_DIRTY_PATHS + 1)]
        notice.GetResyncedPaths.return_value = prims_changed
        notice.GetChangedInfoOnlyPaths.return_value = []

        self._listener._lifecycle.add_task = MagicMock(side_effect=_consume_task)
        self._listener._on_objects_changed(notice, self._stage)

        self.assertEqual(self._listener._dirty_prim_paths, {self._material_path})
        self.assertTrue(self._listener._force_full_refresh)

        self._model._item_changed = MagicMock()
        self._listener._update_dirty({self._material_path}, set(), force_full_refresh=True)
        self._model._item_changed.assert_called_once_with(None)

    async def test_deleted_child_removes_model(self) -> None:
        """Removed prims should remove cached models."""
        child_path = self._shader_path
        self.assertIsNotNone(self._model.get_item_model(child_path))
        self._stage.RemovePrim(child_path)

        self._model._item_changed = MagicMock()
        self._listener._update_dirty({child_path}, set())
        self.assertIsNone(self._model.get_item_model(child_path))
        self._model._item_changed.assert_called_with(None)

    async def test_ui_position_property_updates_position_without_rebuild(self) -> None:
        """UI position changes should avoid full node rebuilds."""
        self._model._item_changed = MagicMock()
        self._model._rebuild_node = MagicMock()
        prop_path = self._shader_path.AppendProperty(UsdUI.Tokens.uiNodegraphNodePos)
        item = self._model.get_item_model(self._shader_path)
        self._listener._update_dirty(set(), {prop_path})

        self._model._item_changed.assert_called_once_with(item)
        self._model._rebuild_node.assert_not_called()
        self.assertTrue(self._model.consume_position_only_changed(item))

    async def test_ui_non_position_property_rebuilds_node(self) -> None:
        """Non-position UI nodegraph properties still rebuild node UI."""
        self._model._item_changed = MagicMock()
        self._model._rebuild_node = MagicMock()
        prop_path = self._shader_path.AppendProperty(UsdUI.Tokens.uiNodegraphNodeSize)
        self._listener._update_dirty(set(), {prop_path})

        self.assertTrue(self._model._item_changed.called)
        self.assertTrue(self._model._rebuild_node.called)

    async def test_connection_property_updates_port_without_full_refresh(self) -> None:
        """Connection changes should refresh the affected port instead of full-syncing the graph."""
        prop_path = self._shader_path.AppendProperty("inputs:diffuseColor")
        item = MagicMock()
        self._model.get_item_model = MagicMock(return_value=item)
        self._model._item_changed = MagicMock()
        self._model._rebuild_node = MagicMock()

        self._listener._update_dirty(set(), {prop_path})

        item.sync.assert_called_once_with()
        self._model._item_changed.assert_called_once_with(item)
        self._model._rebuild_node.assert_not_called()

    async def test_disconnected_port_notice_never_authors_stage_data(self) -> None:
        """A read-only stage observer must not write empty connections into another layer."""
        shader = UsdShade.Shader(self._stage.GetPrimAtPath(self._shader_path))
        port = shader.CreateInput("listenerReadOnly", Sdf.ValueTypeNames.Float)
        prop_path = port.GetAttr().GetPath()
        root_layer = self._stage.GetRootLayer()
        session_layer = self._stage.GetSessionLayer()

        root_before = root_layer.ExportToString()
        session_before = session_layer.ExportToString()
        with Usd.EditContext(self._stage, session_layer):
            self._listener._update_dirty(set(), {prop_path})

        self.assertEqual(root_layer.ExportToString(), root_before)
        self.assertEqual(session_layer.ExportToString(), session_before)

    async def test_connection_property_missing_item_uses_connection_notifier(self) -> None:
        """Unresolved connection notices should keep sync-before-rebuild ordering."""
        prop_path = self._shader_path.AppendProperty("inputs:diffuseColor")
        self._model.get_item_model = MagicMock(return_value=None)
        self._model.notify_connection_changed = MagicMock()
        self._listener._notify_changed = MagicMock()

        self._listener._update_connection_only(prop_path)

        self._model.notify_connection_changed.assert_called_once_with(None)
        self._listener._notify_changed.assert_not_called()

    async def test_connection_property_does_not_skip_other_rebuild_props(self) -> None:
        """Connection-only changes should not abort remaining dirty-property processing."""
        connection_path = self._shader_path.AppendProperty("inputs:diffuseColor")
        size_path = self._shader_path.AppendProperty(UsdUI.Tokens.uiNodegraphNodeSize)
        connection_item = MagicMock()
        rebuild_item = MagicMock()

        def _get_item_model(path):
            if path == connection_path:
                return connection_item
            if path == self._shader_path:
                return rebuild_item
            return None

        self._model.get_item_model = MagicMock(side_effect=_get_item_model)
        self._model._item_changed = MagicMock()
        self._model._rebuild_node = MagicMock()

        self._listener._update_dirty(set(), {connection_path, size_path})

        connection_item.sync.assert_called_once_with()
        self._model._rebuild_node.assert_called_once_with(rebuild_item)

    async def test_stage_listener_manager_uses_model_context_and_replaces_listeners(self) -> None:
        """Non-default contexts and repeated save events must not leak stage listeners."""
        context = MagicMock()
        context.stage_event_name.side_effect = lambda event_type: f"ctx-{event_type.name}"
        model = SimpleNamespace(
            _is_context_root=True,
            _usd_context=context,
            _stage=self._stage,
            _selection_changed=MagicMock(),
        )
        lifecycle = LifecycleRegistry()
        manager = StageListenerManager(model, lifecycle)
        subscriptions = [MagicMock(), MagicMock(), MagicMock()]
        dispatcher = MagicMock()
        dispatcher.observe_event.side_effect = subscriptions
        listener_a = MagicMock()
        listener_b = MagicMock()
        listener_c = MagicMock()

        with (
            patch(
                "omni.kit.window.material_graph.scripts.models.graph.nodes.nodegraph.stage_listener.manager."
                "carb.eventdispatcher.get_eventdispatcher",
                return_value=dispatcher,
            ),
            patch(
                "omni.kit.window.material_graph.scripts.models.graph.nodes.nodegraph.stage_listener.manager."
                "StageListener",
                side_effect=[listener_a, listener_b, listener_c],
            ),
        ):
            manager.activate()
            manager._on_stage_saved_event(None)
            manager._on_stage_saved_event(None)

        self.assertEqual(context.stage_event_name.call_count, 3)
        listener_a.destroy.assert_called_once_with()
        listener_b.destroy.assert_called_once_with()
        self.assertIs(manager._stage_listener, listener_c)
        manager.clear()
        listener_c.destroy.assert_called_once_with()

    async def test_delayed_processing_keeps_one_owner_and_reschedules_new_dirties(self) -> None:
        """Deferred processing should retain task ownership and schedule dirties arriving mid-update."""
        info_path = self._material_path.AppendProperty("info:test")
        queued_path = self._shader_path.AppendProperty("inputs:queued")
        self._listener._dirty_prim_paths = {self._shader_path}
        self._listener._dirty_prop_paths = {info_path}
        self._listener._force_full_refresh = True
        self._listener._task = MagicMock()

        def _queue_during_update(*_args, **_kwargs):
            self._listener._dirty_prop_paths.add(queued_path)

        self._listener._update_dirty = MagicMock(side_effect=_queue_during_update)
        self._listener._ensure_delayed_task = MagicMock()
        app = SimpleNamespace(next_update_async=AsyncMock())
        with patch(
            "omni.kit.window.material_graph.scripts.models.graph.nodes.nodegraph.stage_listener.listener."
            "omni.kit.app.get_app",
            return_value=app,
        ):
            await self._listener._delayed_prim_changed()

        self._listener._update_dirty.assert_called_once_with({self._shader_path}, {info_path}, force_full_refresh=True)
        self.assertEqual(app.next_update_async.await_count, 1 + self._listener._info_sync_updates)
        self.assertIsNone(self._listener._task)
        self.assertEqual(self._listener._dirty_prop_paths, {queued_path})
        self._listener._ensure_delayed_task.assert_called_once_with()

    async def test_prim_creation_and_property_fallback_branches_are_contained(self) -> None:
        """Missing parents, created children, and unsupported property changes should remain deterministic."""
        child_path = self._material_path.AppendChild("NewChild")
        child_prim = self._stage.DefinePrim(child_path)
        parent = SimpleNamespace(create_child=MagicMock(return_value=True))
        self._model.get_item_model = MagicMock(side_effect=lambda path: parent if path == self._material_path else None)
        self._listener._notify_changed = MagicMock()

        self.assertTrue(self._listener._ensure_child_model_for_prim(child_path, child_prim))
        parent.create_child.assert_called_once_with(child_prim)
        self._listener._notify_changed.assert_called_once_with(None, reason="child_created")

        self._model.get_item_model = MagicMock(return_value=None)
        self._listener._notify_changed.reset_mock()
        self.assertFalse(self._listener._ensure_child_model_for_prim(child_path, child_prim))
        self._listener._notify_changed.assert_not_called()

        rebuild = set()
        stacking = self._shader_path.AppendProperty(UsdUI.Tokens.uiNodegraphNodeStackingOrder)
        self.assertTrue(self._listener._collect_rebuild_paths({stacking}, rebuild))
        self._listener._notify_changed.assert_called_once_with(None, reason="ui_stack_or_info")

        self._listener._notify_changed.reset_mock()
        custom_data = self._material_path.AppendProperty("customData")
        paused = self._shader_path.AppendProperty("paused")
        self.assertFalse(self._listener._collect_rebuild_paths({custom_data, paused}, set()))
        self._listener._notify_changed.assert_not_called()

        missing = self._shader_path.AppendProperty("inputs:missing")
        original_stage = self._listener._stage
        self._listener._stage = SimpleNamespace(GetAttributeAtPath=MagicMock(return_value=None))
        try:
            self.assertTrue(self._listener._collect_rebuild_paths({missing}, set()))
        finally:
            self._listener._stage = original_stage
        self._listener._notify_changed.assert_called_once_with(None, reason="missing_attribute")

    async def test_connection_signature_and_notification_fallbacks_are_safe(self) -> None:
        """Broken attributes and lightweight models should fall back without raising or duplicate churn."""
        self.assertIsNone(StageListener._connection_signature(object()))
        broken = SimpleNamespace(GetConnections=MagicMock(side_effect=RuntimeError("broken")))
        self.assertIsNone(StageListener._connection_signature(broken))

        prop_path = self._shader_path.AppendProperty("inputs:diffuseColor")
        attribute = self._stage.GetAttributeAtPath(prop_path)
        self._listener._recent_connection_only_props.clear()
        self._listener._recent_connection_signatures.clear()
        self.assertFalse(self._listener._is_duplicate_connection_only_prop(prop_path, attribute))
        self.assertTrue(self._listener._is_duplicate_connection_only_prop(prop_path, attribute))

        item = SimpleNamespace(sync_position=MagicMock(), sync=MagicMock())
        self._model.get_item_model = MagicMock(return_value=item)
        self._model.notify_position_changed = None
        self._model.notify_connection_changed = None
        self._listener._notify_changed = MagicMock()
        self._listener._update_position_only(self._shader_path)
        self._listener._update_connection_only(prop_path)
        item.sync_position.assert_called_once_with()
        item.sync.assert_called_once_with()
        self._listener._notify_changed.assert_any_call(item, reason="position_only_fallback")
        self._listener._notify_changed.assert_any_call(item, reason="connection_only_fallback")
