from typing import Any

from pxr import Sdf, UsdShade

from ...scripts.models.graph.nodes.material import MaterialModel
from ...scripts.models.graph.nodes.nodegraph.selection_helper import PrimSelectionHelper
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestSelectionHelper(MaterialGraphTestBase):
    """Prim selection helper behavior."""

    async def setUp(self) -> None:
        """Load the scene and initialize a material model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._plugin = DummyPlugin()
        self._validator = MaterialValidator()

        material_prim = self._get_prim_at_path(self._material_path)
        self._model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)

    async def test_get_selected_nodes_filters_and_caches(self) -> None:
        """Selected node lookups should filter invalid prims."""
        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([self._shader_path.pathString, "/World/Looks/material/does_not_exist"], True)

        helper = PrimSelectionHelper()
        first = helper.get_selected_nodes(
            self._usd_context, self._stage, self._material_path, self._model.get_item_model
        )
        self.assertTrue(first)
        self.assertFalse(any(item is None for item in first))
        self.assertEqual({item.prim_path for item in first}, {self._shader_path})

        second = helper.get_selected_nodes(
            self._usd_context, self._stage, self._material_path, self._model.get_item_model
        )
        self.assertIs(first, second)

    async def test_sync_selection_runs_callbacks(self) -> None:
        """Selection sync should invoke callbacks."""
        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([self._shader_path.pathString], True)

        helper = PrimSelectionHelper()
        calls = []

        def _on_changed(kit_selection: Any, selection_value: Any, run_select: Any) -> None:
            """Record callback invocations."""
            calls.append((kit_selection, selection_value, run_select))

        shader_model = self._model.get_item_model(self._shader_path)
        helper.sync_selection(self._usd_context, [shader_model], _on_changed)
        self.assertTrue(calls)

        selection.set_selected_prim_paths([self._material_path.pathString], True)
        helper.sync_selection(self._usd_context, [self._model], _on_changed)
        self.assertTrue(len(calls) >= 2)

    async def test_selection_cache_refresh_on_rename(self) -> None:
        """Renaming prims should invalidate selection cache."""
        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([self._shader_path.pathString], True)

        helper = PrimSelectionHelper()
        first = helper.get_selected_nodes(
            self._usd_context, self._stage, self._material_path, self._model.get_item_model
        )
        self.assertTrue(first)

        new_path = self._shader_path.GetParentPath().AppendChild("shader_renamed")
        self._stage.RemovePrim(self._shader_path)
        UsdShade.Shader.Define(self._stage, new_path)
        self._model.sync()
        selection.set_selected_prim_paths([new_path.pathString], True)

        second = helper.get_selected_nodes(
            self._usd_context, self._stage, self._material_path, self._model.get_item_model
        )
        self.assertTrue(second)
        self.assertNotEqual(first, second)
