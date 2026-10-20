# pylint: disable=relative-beyond-top-level,no-member,protected-access
from unittest.mock import patch

from pxr import Sdf, UsdShade

from ...scripts.commands.result import CommandResult
from ...scripts.config.paths import Paths
from ...scripts.models.graph.nodes.material import MaterialModel
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestModelValidity(MaterialGraphTestBase):
    async def setUp(self) -> None:
        """Load the simple scene and set up a dummy plugin."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._plugin = DummyPlugin()
        self._validator = MaterialValidator()

    async def test_prim_exists_and_invalidation(self) -> None:
        """Model should invalidate when its prim is removed."""
        material_prim = self._get_prim_at_path(self._material_path)
        model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)

        self.assertTrue(model.prim_exists())
        self.assertTrue(model.valid)

        self._stage.RemovePrim(self._material_path)
        model.sync()
        self.assertFalse(model.valid)
        self.assertIsNone(model.prim)

    async def test_stage_reload_clears_model(self) -> None:
        """Reloading the stage should clear stale prim references."""
        material_prim = self._get_prim_at_path(self._material_path)
        model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)
        self.assertTrue(model.prim_exists())

        await self._usd_context.new_stage_async()
        model.sync()
        self.assertFalse(model.valid)
        self.assertIsNone(model.prim)

    async def test_rename_clears_schema_cache(self) -> None:
        """Renaming a prim should clear schema caches."""
        material_path = Sdf.Path("/World/Looks/RenameTest")
        material_prim = UsdShade.Material.Define(self._stage, material_path)
        model = MaterialModel(material_prim.GetPrim(), "universal", self._usd_context, self._plugin, self._validator)
        model._schema_attributes = {"dummy": "value"}
        model._applied_schemas_cache = ("TestSchema",)

        self.assertTrue(model.set_name("RenameTestNew"))

        self.assertEqual(model._schema_attributes, {})
        self.assertIsNone(model._applied_schemas_cache)

    async def test_failed_rename_preserves_schema_cache(self) -> None:
        """A rejected prim rename must remain visible to the canvas and preserve cached state."""
        material_prim = self._get_prim_at_path(self._material_path)
        model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)
        model._schema_attributes = {"dummy": "value"}
        model._applied_schemas_cache = ("TestSchema",)

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.prim.model.RenamePrim",
            return_value=CommandResult(False, error_code="injected"),
        ):
            self.assertFalse(model.set_name("RejectedRename"))

        self.assertEqual(model._schema_attributes, {"dummy": "value"})
        self.assertEqual(model._applied_schemas_cache, ("TestSchema",))

    async def test_prim_replacement_refreshes_model(self) -> None:
        """Model should rebind when a prim is recreated at the same path."""
        material_prim = self._get_prim_at_path(self._material_path)
        model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)
        self.assertTrue(model.prim_exists())

        self._stage.RemovePrim(self._material_path)
        self.assertFalse(model.prim_exists())

        new_material = UsdShade.Material.Define(self._stage, str(self._material_path))
        model.sync()
        self.assertTrue(model.prim_exists())
        self.assertEqual(model.prim.GetPath(), new_material.GetPrim().GetPath())

    async def test_pause_updates_children_only_after_usd_command_succeeds(self) -> None:
        """A failed pause command must not leave the material model claiming it is paused."""
        material_prim = self._get_prim_at_path(self._material_path)
        model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.material.PauseMaterial",
            return_value=CommandResult(False, error_code="injected"),
        ) as pause_material:
            self.assertFalse(model.set_pause(True))
        self.assertFalse(model.pause)
        pause_material.assert_called_once_with(self._material_path, True, stage=self._stage)

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.material.PauseMaterial",
            return_value=CommandResult(True),
        ):
            self.assertTrue(model.set_pause(True))
        self.assertTrue(model.pause)
