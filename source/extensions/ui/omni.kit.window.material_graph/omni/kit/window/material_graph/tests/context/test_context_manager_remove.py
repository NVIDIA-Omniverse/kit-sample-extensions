# pylint: disable=relative-beyond-top-level,no-member
from types import SimpleNamespace
from unittest.mock import patch

import omni.kit.undo
from pxr import Sdf

from ...scripts.config.paths import Paths
from .base import ContextManagerTestBase


class TestContextManagerRemove(ContextManagerTestBase):
    """ContextManager.remove_context tears down a plugin context: it removes material outputs for that
    context and drops the context from the registry. We test that outputs are
    removed, that failed cleanup is logged, that the context is
    cleared from the registry, and that removing a missing context returns False."""

    async def setUp(self) -> None:
        """Load the simple scene and seed common prim paths."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._nodegraph_path = Sdf.Path("/World/Looks/material/nodegraph")
        self._backdrop_path = Sdf.Path("/World/Looks/material/backdrop")

    async def test_remove_context_removes_outputs(self) -> None:
        """remove_context removes material outputs for that context."""
        material_prim = self._get_prim_at_path(self._material_path)

        self.assertTrue(self._manager.load(self._material_path))

        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        handle = self._manager.get_context(context_name)
        self.assertIsNotNone(handle.context)
        self.assertIsNotNone(handle.plugin)

        output_names = handle.plugin.get_material_output_names()
        for name in output_names:
            material_prim.CreateAttribute(name, Sdf.ValueTypeNames.Token)

        self.assertTrue(self._manager.remove_context(context_name))
        for name in output_names:
            self.assertFalse(material_prim.HasAttribute(name))

    async def test_remove_context_logs_on_failure(self) -> None:
        """remove_context logs when cleanup fails."""
        self.assertTrue(self._manager.load(self._material_path))
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        handle = self._manager.get_context(context_name)
        self.assertIsNotNone(handle.context)

        material_prim = self._get_prim_at_path(self._material_path)
        output_names = handle.plugin.get_material_output_names()
        for name in output_names:
            material_prim.CreateAttribute(name, Sdf.ValueTypeNames.Token)

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.ContextManager._remove_context_output",
                autospec=True,
                return_value=False,
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            self.assertFalse(self._manager.remove_context(context_name))
            log_warn.assert_called()

    async def test_partial_output_removal_failure_restores_prior_outputs(self) -> None:
        """A later removal failure restores outputs without leaving a ghost redo command."""
        material_prim = self._get_prim_at_path(self._material_path)
        first_name = "outputs:transactionA"
        second_name = "outputs:transactionB"
        material_prim.CreateAttribute(first_name, Sdf.ValueTypeNames.Token)
        material_prim.CreateAttribute(second_name, Sdf.ValueTypeNames.Token)
        self._manager._root_prim = material_prim
        context = SimpleNamespace(plugin=SimpleNamespace(get_material_output_names=lambda: [first_name, second_name]))
        layer = material_prim.GetStage().GetEditTarget().GetLayer()
        before = layer.ExportToString()
        undo_count = len(omni.kit.undo.get_undo_stack())
        call_count = 0

        def _remove_then_fail(attribute) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return bool(attribute.GetPrim().RemoveProperty(attribute.GetName()))
            return False

        with patch.object(self._manager, "_remove_context_output", side_effect=_remove_then_fail):
            success, _ = self._manager._remove_context_outputs(context)

        self.assertFalse(success)
        self.assertTrue(material_prim.HasAttribute(first_name))
        self.assertTrue(material_prim.HasAttribute(second_name))
        self.assertEqual(layer.ExportToString(), before)
        self.assertEqual(len(omni.kit.undo.get_undo_stack()), undo_count)

    async def test_successful_output_removal_is_one_atomic_undo_item(self) -> None:
        """A successful batch round-trips every removed output through one undo item."""
        material_prim = self._get_prim_at_path(self._material_path)
        output_names = ["outputs:transactionA", "outputs:transactionB"]
        for name in output_names:
            material_prim.CreateAttribute(name, Sdf.ValueTypeNames.Token)
        self._manager._root_prim = material_prim
        context = SimpleNamespace(plugin=SimpleNamespace(get_material_output_names=lambda: output_names))

        success, error = self._manager._remove_context_outputs(context)

        self.assertTrue(success, error)
        self.assertTrue(all(not material_prim.HasAttribute(name) for name in output_names))
        omni.kit.undo.undo()
        self.assertTrue(all(material_prim.HasAttribute(name) for name in output_names))
        omni.kit.undo.redo()
        self.assertTrue(all(not material_prim.HasAttribute(name) for name in output_names))

    async def test_remove_context_clears_context(self) -> None:
        """remove_context removes context from registry."""
        self.assertTrue(self._manager.load(self._material_path))
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        handle = self._manager.get_context(context_name)
        self.assertIsNotNone(handle.context)

        self.assertTrue(self._manager.remove_context(context_name))
        self.assertNotIn(context_name, self._manager.get_context_names())

    async def test_remove_missing_context(self) -> None:
        """remove_context returns False for unknown context."""
        self.assertFalse(self._manager.remove_context("missing"))
