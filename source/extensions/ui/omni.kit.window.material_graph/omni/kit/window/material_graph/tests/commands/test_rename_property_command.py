import omni.kit.commands
from pxr import Sdf, Usd, UsdShade

from .base import CommandsTestBase


class TestRenamePropertyCommand(CommandsTestBase):
    """MaterialGraph_RenamePropertyCommand renames material/shader inputs and preserves connections.
    We test that renaming preserves connections and undo/redo, and that rename no-ops on collision."""

    async def setUp(self) -> None:
        """Load the simple test scene for property rename coverage."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")

    async def test_rename_preserves_connections(self) -> None:
        """Rename preserves connections and undo/redo."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        input_port = shader.GetInput("diffuseColor")
        self.assertTrue(input_port)
        self.assertTrue(input_port.HasConnectedSource())

        omni.kit.commands.execute(
            "MaterialGraph_RenamePropertyCommand",
            prim_path=self._material_path,
            property_name=f"{UsdShade.Tokens.inputs}diffuseColor",
            new_name=f"{UsdShade.Tokens.inputs}diffuseColorRenamed",
        )

        def _after() -> None:
            """Validate renamed property after redo."""
            prim = self._get_prim_at_path(self._material_path)
            self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}diffuseColor"))
            self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}diffuseColorRenamed"))
            self.assertTrue(input_port.HasConnectedSource())
            source, source_name, source_type = input_port.GetConnectedSource()
            if source_type == UsdShade.AttributeType.Output:
                attr = source.GetOutput(source_name)
            else:
                attr = source.GetInput(source_name)
            self.assertEqual(attr.GetPrim().GetPath(), self._material_path)
            self.assertEqual(attr.GetAttr().GetName(), f"{UsdShade.Tokens.inputs}diffuseColorRenamed")

        def _before() -> None:
            """Validate original property after undo."""
            prim = self._get_prim_at_path(self._material_path)
            self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}diffuseColor"))
            self.assertFalse(prim.HasAttribute(f"{UsdShade.Tokens.inputs}diffuseColorRenamed"))
            self.assertTrue(input_port.HasConnectedSource())

        await self._assert_undo_redo(_before, _after)

    async def test_rename_skips_on_collision(self) -> None:
        """Rename no-ops when target name exists."""
        prim = self._get_prim_at_path(self._material_path)
        prim.CreateAttribute(f"{UsdShade.Tokens.inputs}temp", Sdf.ValueTypeNames.Float)
        prim.CreateAttribute(f"{UsdShade.Tokens.inputs}collision", Sdf.ValueTypeNames.Float)

        omni.kit.commands.execute(
            "MaterialGraph_RenamePropertyCommand",
            prim_path=self._material_path,
            property_name=f"{UsdShade.Tokens.inputs}temp",
            new_name=f"{UsdShade.Tokens.inputs}collision",
        )

        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}temp"))
        self.assertTrue(prim.HasAttribute(f"{UsdShade.Tokens.inputs}collision"))

    async def test_rename_preserves_complete_attribute_spec(self) -> None:
        """Rename and undo preserve custom state, metadata, defaults, and time samples."""
        prim = self._get_prim_at_path(self._material_path)
        old_name = f"{UsdShade.Tokens.inputs}animatedCustom"
        new_name = f"{UsdShade.Tokens.inputs}animatedCustomRenamed"
        attr = prim.CreateAttribute(old_name, Sdf.ValueTypeNames.Float, custom=True, variability=Sdf.VariabilityVarying)
        attr.Set(1.25)
        attr.Set(2.5, Usd.TimeCode(1.0))
        attr.Set(3.5, Usd.TimeCode(2.0))
        attr.SetMetadata("displayGroup", "Audit")
        attr.SetCustomDataByKey("audit:marker", "preserve")
        before = self._stage.GetRootLayer().ExportToString()

        omni.kit.commands.execute(
            "MaterialGraph_RenamePropertyCommand",
            prim_path=self._material_path,
            property_name=old_name,
            new_name=new_name,
        )

        def _after() -> None:
            renamed = prim.GetAttribute(new_name)
            self.assertTrue(renamed)
            self.assertTrue(renamed.IsCustom())
            self.assertEqual(renamed.Get(), 1.25)
            self.assertEqual(renamed.GetTimeSamples(), [1.0, 2.0])
            self.assertEqual(renamed.Get(Usd.TimeCode(1.0)), 2.5)
            self.assertEqual(renamed.Get(Usd.TimeCode(2.0)), 3.5)
            self.assertEqual(renamed.GetMetadata("displayGroup"), "Audit")
            self.assertEqual(renamed.GetCustomDataByKey("audit:marker"), "preserve")

        def _before() -> None:
            self.assertEqual(self._stage.GetRootLayer().ExportToString(), before)

        await self._assert_undo_redo(_before, _after)
