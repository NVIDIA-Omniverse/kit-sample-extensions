from unittest.mock import patch

import omni.kit.commands
from pxr import Gf, Sdf, UsdShade, UsdUI

from ...scripts.commands.impl.nodegraph.import_ import MaterialGraph_ImportNodeGraphCommand
from .base import CommandsTestBase


class TestCompoundCommands(CommandsTestBase):
    """ImportNodeGraphCommand copies a compound/nodegraph from a source asset into the material and
    must create the prim, set position/attributes, and support undo. We test invalid source (no prim
    created), select_new_prim=False (selection unchanged), and full import with undo/redo."""

    async def setUp(self) -> None:
        """Load the simple scene for compound import tests."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._compound_source = self._get_scene_path("compound.usda")

    async def test_import_compound_invalid_source(self) -> None:
        """Invalid source does not create prim."""
        _success, created = omni.kit.commands.execute(
            "MaterialGraph_ImportNodeGraphCommand",
            parent_path=self._material_path,
            source_asset="",
            identifier="/CompoundShader",
        )
        self.assertIsNone(created)
        self.assertFalse(self._stage.GetPrimAtPath("/World/Looks/CompoundShader"))

    async def test_import_compound_no_selection(self) -> None:
        """select_new_prim=False leaves selection unchanged."""
        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([self._material_path.pathString], True)

        color_value = Gf.Vec3f(0.25, 0.5, 0.75)
        success, created = omni.kit.commands.execute(
            "MaterialGraph_ImportNodeGraphCommand",
            parent_path=self._material_path,
            source_asset=self._compound_source,
            identifier="/Root/NodeGraph",
            position=(7, 9),
            attributes_to_set={f"{UsdShade.Tokens.inputs}color_const_c": color_value},
            select_new_prim=False,
        )

        self.assertTrue(success)
        self.assertTrue(created)
        selected = selection.get_selected_prim_paths()
        self.assertIn(self._material_path.pathString, selected)

    async def test_import_compound(self) -> None:
        """Import copies spec, sets attrs, and undoes."""
        color_value = Gf.Vec3f(0.25, 0.5, 0.75)
        success, created = omni.kit.commands.execute(
            "MaterialGraph_ImportNodeGraphCommand",
            parent_path=self._material_path,
            source_asset=self._compound_source,
            identifier="/Root/NodeGraph",
            position=(7, 9),
            attributes_to_set={f"{UsdShade.Tokens.inputs}color_const_c": color_value},
        )

        self.assertTrue(success)
        self.assertTrue(created)

        created_path = self._material_path.AppendChild("NodeGraph")

        def _after() -> None:
            """Validate compound import after redo."""
            prim = self._get_prim_at_path(created_path)
            self.assertTrue(prim.HasAPI(UsdUI.NodeGraphNodeAPI))
            attr = self._get_attribute_at_path(created_path.AppendProperty(f"{UsdShade.Tokens.inputs}color_const_c"))
            self.assertEqual(attr.Get(), color_value)

        def _before() -> None:
            """Validate compound removal after undo."""
            self.assertFalse(self._stage.GetPrimAtPath(created_path))

        await self._assert_undo_redo(_before, _after)

    async def test_failed_import_rollback_restores_the_exact_edit_layer(self) -> None:
        """Failed import rollback must remove copied specs even when no prim composes."""
        edit_layer = self._stage.GetEditTarget().GetLayer()
        snapshot = Sdf.Layer.CreateAnonymous("import_before.usda")
        snapshot.TransferContent(edit_layer)
        before = snapshot.ExportToString()
        Sdf.CreatePrimInLayer(edit_layer, "/Uncomposed/Partial")
        command = MaterialGraph_ImportNodeGraphCommand(
            parent_path=self._material_path,
            source_asset=self._compound_source,
            identifier="/Root/NodeGraph",
            stage=self._stage,
        )
        command._created_path = "/Uncomposed/Partial"

        command._rollback_target(edit_layer, snapshot)

        self.assertEqual(edit_layer.ExportToString(), before)
        self.assertIsNone(command._created_path)

    async def test_import_exception_restores_the_exact_edit_layer(self) -> None:
        """Unexpected USD copy exceptions must not escape the import transaction."""
        edit_layer = self._stage.GetEditTarget().GetLayer()
        before = edit_layer.ExportToString()
        command = MaterialGraph_ImportNodeGraphCommand(
            parent_path=self._material_path,
            source_asset=self._compound_source,
            identifier="/Root/NodeGraph",
            stage=self._stage,
        )

        with patch("pxr.Sdf.CopySpec", side_effect=RuntimeError("injected")):
            created = command.do()

        self.assertIsNone(created)
        self.assertEqual(edit_layer.ExportToString(), before)
        self.assertIsNone(command._created_path)
