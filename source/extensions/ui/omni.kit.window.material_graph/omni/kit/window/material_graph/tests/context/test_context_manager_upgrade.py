"""Failure and rollback coverage for ContextManager's MaterialX identifier application."""

from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.context_manager import ContextManager
from ...scripts.plugins.impl.materialx.plugin import MaterialXPlugin
from ..base import MaterialGraphTestBase


class TestContextManagerUpgrade(MaterialGraphTestBase):
    """MaterialX identifier batches must not leave partially-upgraded USD state."""

    async def test_batch_identifier_failure_rolls_back_and_preserves_cache(self) -> None:
        """A later SetShaderId failure restores every earlier identifier and retains the cache."""
        manager = object.__new__(ContextManager)
        stage = MagicMock()
        prim_a = MagicMock()
        prim_b = MagicMock()
        prim_a.IsValid.return_value = True
        prim_b.IsValid.return_value = True
        stage.GetPrimAtPath.side_effect = [prim_a, prim_b]
        api_a = MagicMock()
        api_b = MagicMock()
        api_a.GetShaderId.return_value = "old_a"
        api_b.GetShaderId.return_value = "old_b"
        api_a.SetShaderId.return_value = True
        api_b.SetShaderId.return_value = False
        changes = [
            SimpleNamespace(prim_path="/A", old_identifier="old_a", new_identifier="new_a"),
            SimpleNamespace(prim_path="/B", old_identifier="old_b", new_identifier="new_b"),
        ]
        plugin = SimpleNamespace(_shader_node_cache=MagicMock())

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.UsdShade.NodeDefAPI",
                side_effect=[api_a, api_b],
            ),
            patch(f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.logger.error"),
        ):
            self.assertFalse(manager._apply_upgrade_changes(changes, stage, plugin))

        self.assertEqual(api_a.SetShaderId.call_args_list, [call("new_a"), call("old_a")])
        api_b.SetShaderId.assert_called_once_with("new_b")
        plugin._shader_node_cache.clear.assert_not_called()

    async def test_identifier_rollback_diagnostic_cannot_mask_the_original_failure(self) -> None:
        """A broken NodeDefAPI during rollback must still return a clean failure with the known prim path."""
        manager = object.__new__(ContextManager)
        stage = MagicMock()
        prim_a = MagicMock()
        prim_b = MagicMock()
        prim_a.IsValid.return_value = True
        prim_b.IsValid.return_value = True
        stage.GetPrimAtPath.side_effect = [prim_a, prim_b]
        api_a = MagicMock()
        api_b = MagicMock()
        api_a.GetShaderId.return_value = "old_a"
        api_b.GetShaderId.return_value = "old_b"
        api_a.SetShaderId.side_effect = [True, RuntimeError("rollback rejected")]
        api_a.GetPrim.side_effect = RuntimeError("diagnostic lookup rejected")
        api_b.SetShaderId.return_value = False
        changes = [
            SimpleNamespace(prim_path="/A", old_identifier="old_a", new_identifier="new_a"),
            SimpleNamespace(prim_path="/B", old_identifier="old_b", new_identifier="new_b"),
        ]
        plugin = SimpleNamespace(_shader_node_cache=MagicMock())

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.UsdShade.NodeDefAPI",
                side_effect=[api_a, api_b],
            ),
            patch(f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.logger.error") as error,
        ):
            self.assertFalse(manager._apply_upgrade_changes(changes, stage, plugin))

        api_a.GetPrim.assert_not_called()
        self.assertIn("/A", str(error.call_args_list[0]))
        self.assertIn("/B", str(error.call_args_list[1]))
        plugin._shader_node_cache.clear.assert_not_called()

    async def test_upgrade_discovery_stores_manual_changes_and_clears_stale_results(self) -> None:
        """Manual mode should retain current changes and clear stale results when none remain."""
        manager = object.__new__(ContextManager)
        plugin = MaterialXPlugin(load_catalog=False)
        plugin._pending_upgrade_changes = [object()]
        manager._plugin_access = SimpleNamespace(get_plugins=lambda: [plugin])
        change = SimpleNamespace(prim_path="/World/Shader", old_identifier="old", new_identifier="new")
        result = SimpleNamespace(diagnostics=["upgrade available"], any_changes=True, changes=[change])
        root = UsdShade.Material.Define(self._stage, "/World/Material").GetPrim()
        try:
            with patch(
                f"{Paths.MODULE_ID}.scripts.materialx_upgrade.upgrade_materialx_identifiers",
                return_value=result,
            ):
                manager._run_materialx_upgrade_if_needed(root, apply_changes=False)
            self.assertEqual(plugin._pending_upgrade_changes, [change])
            self.assertFalse(manager._last_upgrade_had_changes)

            result.any_changes = False
            with patch(
                f"{Paths.MODULE_ID}.scripts.materialx_upgrade.upgrade_materialx_identifiers",
                return_value=result,
            ):
                manager._run_materialx_upgrade_if_needed(root, apply_changes=False)
            self.assertEqual(plugin._pending_upgrade_changes, [])
        finally:
            plugin.destroy()

    async def test_auto_upgrade_records_success_and_retains_failed_changes(self) -> None:
        """Automatic upgrade should clear successful work but preserve retryable failures."""
        manager = object.__new__(ContextManager)
        plugin = MaterialXPlugin(load_catalog=False)
        plugin._pending_upgrade_changes = []
        manager._plugin_access = SimpleNamespace(get_plugins=lambda: [plugin])
        change = SimpleNamespace(prim_path="/World/Shader", old_identifier="old", new_identifier="new")
        result = SimpleNamespace(diagnostics=[], any_changes=True, changes=[change])
        root = UsdShade.Material.Define(self._stage, "/World/Material").GetPrim()
        try:
            with (
                patch(
                    f"{Paths.MODULE_ID}.scripts.materialx_upgrade.upgrade_materialx_identifiers",
                    return_value=result,
                ),
                patch.object(manager, "_apply_upgrade_changes", return_value=True),
            ):
                manager._run_materialx_upgrade_if_needed(root, apply_changes=True)
            self.assertEqual(plugin._pending_upgrade_changes, [])
            self.assertTrue(manager._last_upgrade_had_changes)

            with (
                patch(
                    f"{Paths.MODULE_ID}.scripts.materialx_upgrade.upgrade_materialx_identifiers",
                    return_value=result,
                ),
                patch.object(manager, "_apply_upgrade_changes", return_value=False),
            ):
                manager._run_materialx_upgrade_if_needed(root, apply_changes=True)
            self.assertEqual(plugin._pending_upgrade_changes, [change])
            self.assertFalse(manager._last_upgrade_had_changes)
        finally:
            plugin.destroy()

    async def test_check_materialx_upgrade_rebuilds_only_after_applied_changes(self) -> None:
        """Context rebuilding should occur only after a successful automatic rewrite."""
        manager = object.__new__(ContextManager)
        plugin = MaterialXPlugin(load_catalog=False)
        plugin._pending_upgrade_changes = []
        manager._root_prim = UsdShade.Material.Define(self._stage, "/World/Material").GetPrim()
        manager._plugin_access = SimpleNamespace(get_plugin=lambda _name: plugin)
        manager._last_upgrade_had_changes = True
        try:
            with (
                patch.object(plugin, "get_plugin_property", return_value=True),
                patch.object(manager, "_run_materialx_upgrade_if_needed"),
                patch.object(manager, "destroy_context", return_value=True) as destroy_context,
            ):
                manager.check_materialx_upgrade(plugin.name)
            destroy_context.assert_called_once_with(plugin.name)

            plugin._pending_upgrade_changes = [object()]
            with (
                patch.object(plugin, "get_plugin_property", return_value=True),
                patch.object(manager, "_run_materialx_upgrade_if_needed"),
                patch.object(manager, "destroy_context", return_value=True) as destroy_context,
            ):
                manager.check_materialx_upgrade(plugin.name)
            destroy_context.assert_not_called()
        finally:
            plugin.destroy()

    async def test_apply_single_upgrade_updates_stage_cache_and_context(self) -> None:
        """Manual upgrade should update one prim and invalidate all dependent caches."""
        manager = object.__new__(ContextManager)
        material = UsdShade.Material.Define(self._stage, "/World/Material")
        shader = UsdShade.Shader.Define(self._stage, "/World/Material/Shader")
        shader.SetShaderId("old_identifier")
        plugin = MaterialXPlugin(load_catalog=False)
        change = SimpleNamespace(
            prim_path=str(shader.GetPath()),
            old_identifier="old_identifier",
            new_identifier="new_identifier",
        )
        plugin._pending_upgrade_changes = [change, SimpleNamespace(prim_path="/Other")]
        context = SimpleNamespace(destroy=MagicMock())
        manager._root_prim = material.GetPrim()
        manager._usd_context = SimpleNamespace(get_stage=lambda: self._stage)
        manager._plugin_access = SimpleNamespace(get_plugins=lambda: [plugin])
        manager._contexts = {plugin.name: context}
        manager._validation_results = {plugin.name: object()}
        try:
            self.assertTrue(manager.apply_single_upgrade(change))
            self.assertEqual(UsdShade.NodeDefAPI(shader.GetPrim()).GetShaderId(), "new_identifier")
            self.assertEqual([item.prim_path for item in plugin._pending_upgrade_changes], ["/Other"])
            self.assertNotIn(plugin.name, manager._contexts)
            self.assertNotIn(plugin.name, manager._validation_results)
            context.destroy.assert_called_once_with()

            manager._root_prim = None
            self.assertFalse(manager.apply_single_upgrade(change))
        finally:
            plugin.destroy()

    async def test_apply_upgrade_changes_rejects_missing_prims_without_mutation(self) -> None:
        """Batch upgrades should validate every target before changing any identifier."""
        manager = object.__new__(ContextManager)
        plugin = SimpleNamespace(_shader_node_cache=MagicMock())
        missing = SimpleNamespace(
            prim_path="/Missing",
            old_identifier="old",
            new_identifier="new",
        )
        self.assertFalse(manager._apply_upgrade_changes([missing], self._stage, plugin))
        plugin._shader_node_cache.clear.assert_not_called()

        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Shader"))
        valid = SimpleNamespace(
            prim_path=str(shader.GetPath()),
            old_identifier="old",
            new_identifier="new",
        )
        self.assertTrue(manager._apply_upgrade_changes([valid], self._stage, plugin))
        self.assertEqual(UsdShade.NodeDefAPI(shader.GetPrim()).GetShaderId(), "new")
        plugin._shader_node_cache.clear.assert_called_once_with()
