from unittest.mock import patch

import omni.kit.commands
import omni.kit.undo
from pxr import Sdf, UsdShade, UsdUI

from ...scripts.commands.impl.backdrop import MaterialGraph_CreateUsdUIBackdropCommand
from ...scripts.commands.impl.prim.create import MaterialGraph_CreatePrimCommand
from .base import CommandsTestBase


class TestNodeGraphCommand(CommandsTestBase):
    """MaterialGraph_NewUsdShadeNodeGraphCommand creates a NodeGraph prim under a material with
    position (NodeGraphNodeAPI or custom_data). We test create/undo/redo and custom position_key."""

    async def setUp(self) -> None:
        """Load the simple scene for nodegraph command tests."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._nodegraph_path = Sdf.Path("/World/Looks/material/NodeGraph")

    async def test_create_nodegraph_with_pos_attr(self) -> None:
        """Create nodegraph with position; undo/redo round-trips."""
        material_prim = self._get_prim_at_path(self._material_path)
        before_children = {child.GetName() for child in material_prim.GetChildren()}
        omni.kit.commands.execute(
            "MaterialGraph_NewUsdShadeNodeGraphCommand",
            parent_path=self._material_path,
            identifier="NodeGraph",
            position=(10, 20),
        )
        after_children = {child.GetName() for child in material_prim.GetChildren()}
        created_name = next(iter(after_children - before_children), None)
        self.assertIsNotNone(created_name)
        created_path = self._material_path.AppendChild(created_name)

        def _after() -> None:
            """Validate the created nodegraph after redo."""
            prim = self._get_prim_at_path(created_path)
            self.assertTrue(prim.IsA(UsdShade.NodeGraph))
            self.assertTrue(prim.HasAPI(UsdUI.NodeGraphNodeAPI))

        def _before() -> None:
            """Validate nodegraph removal after undo."""
            self.assertFalse(self._stage.GetPrimAtPath(created_path))

        await self._assert_undo_redo(_before, _after)

    async def test_create_nodegraph_with_custom_position_key(self) -> None:
        """Custom position_key sets custom_data."""
        material_prim = self._get_prim_at_path(self._material_path)
        before_children = {child.GetName() for child in material_prim.GetChildren()}
        omni.kit.commands.execute(
            "MaterialGraph_NewUsdShadeNodeGraphCommand",
            parent_path=self._material_path,
            identifier="NodeGraph",
            position=(1, 2),
            position_key="position:mdl",
        )
        after_children = {child.GetName() for child in material_prim.GetChildren()}
        created_name = next(iter(after_children - before_children), None)
        self.assertIsNotNone(created_name)
        created_path = self._material_path.AppendChild(created_name)

        def _after() -> None:
            """Validate custom position data after redo."""
            prim = self._get_prim_at_path(created_path)
            value = prim.GetCustomDataByKey("position:mdl")
            self.assertEqual(tuple(value), (1, 2))

        def _before() -> None:
            """Validate nodegraph removal after undo."""
            self.assertFalse(self._stage.GetPrimAtPath(created_path))

        await self._assert_undo_redo(_before, _after)

    async def test_create_backdrop_command_authors_optional_state_and_undoes(self) -> None:
        """The direct backdrop command should choose a unique path and author every optional field."""
        UsdUI.Backdrop.Define(self._stage, self._material_path.AppendChild("Backdrop"))
        command = MaterialGraph_CreateUsdUIBackdropCommand(
            parent_path=self._material_path,
            identifier="Backdrop",
            position=(10.0, 20.0),
            size=(300.0, 200.0),
            display_color=(0.1, 0.2, 0.3),
            stacking_order=7,
            stage=self._stage,
        )

        prim = command.do()

        self.assertEqual(prim.GetPath(), self._material_path.AppendChild("Backdrop01"))
        api = UsdUI.NodeGraphNodeAPI(prim)
        self.assertEqual(tuple(api.GetPosAttr().Get()), (10.0, 20.0))
        self.assertEqual(tuple(api.GetSizeAttr().Get()), (300.0, 200.0))
        for actual, expected in zip(api.GetDisplayColorAttr().Get(), (0.1, 0.2, 0.3)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(api.GetStackingOrderAttr().Get(), 7)

        created_path = prim.GetPath()
        command.undo()
        self.assertFalse(self._stage.GetPrimAtPath(created_path))

    async def test_create_backdrop_command_supports_context_position_metadata(self) -> None:
        """Context-specific backdrop positions should be stored under the caller-provided key."""
        command = MaterialGraph_CreateUsdUIBackdropCommand(
            parent_path=self._material_path,
            identifier="Backdrop",
            position=(1.0, 2.0),
            position_key="omni:uiNodegraphNodePos:mdl",
            stage=self._stage,
        )

        prim = command.do()

        self.assertEqual(tuple(prim.GetCustomDataByKey("omni:uiNodegraphNodePos:mdl")), (1.0, 2.0))

    async def test_failed_create_rollback_restores_the_exact_edit_layer(self) -> None:
        """Failed creation rollback must remove specs that do not compose to a valid prim."""
        edit_layer = self._stage.GetEditTarget().GetLayer()
        snapshot = Sdf.Layer.CreateAnonymous("create_before.usda")
        snapshot.TransferContent(edit_layer)
        before = snapshot.ExportToString()
        Sdf.CreatePrimInLayer(edit_layer, "/Uncomposed/Partial")
        command = MaterialGraph_CreatePrimCommand(
            parent_path=Sdf.Path("/Uncomposed"),
            prim_type=UsdShade.Tokens.Shader,
            prim_name="Partial",
            stage=self._stage,
        )
        command._prim_path = Sdf.Path("/Uncomposed/Partial")

        command._rollback_failed_create(edit_layer, snapshot)

        self.assertEqual(edit_layer.ExportToString(), before)
        self.assertIsNone(command._prim_path)

    async def test_create_exception_restores_the_exact_edit_layer(self) -> None:
        """Unexpected initialization exceptions must not escape the create transaction."""
        edit_layer = self._stage.GetEditTarget().GetLayer()
        before = edit_layer.ExportToString()
        command = MaterialGraph_CreatePrimCommand(
            parent_path=self._material_path,
            prim_type=UsdShade.Tokens.Shader,
            prim_name="FailingShader",
            stage=self._stage,
        )

        with patch.object(command, "_initialize_prim", side_effect=RuntimeError("injected")):
            created = command.do()

        self.assertIsNone(created)
        self.assertEqual(edit_layer.ExportToString(), before)
        self.assertFalse(self._stage.GetPrimAtPath(self._material_path.AppendChild("FailingShader")))

    async def test_failed_registered_create_leaves_no_ghost_undo_or_redo(self) -> None:
        """A rolled-back create must not survive as a nested undo-stack command."""
        edit_layer = self._stage.GetEditTarget().GetLayer()
        before = edit_layer.ExportToString()
        parent_path = Sdf.Path("/AdversarialCreateScope")

        with patch.object(MaterialGraph_CreatePrimCommand, "_initialize_prim", return_value=False):
            success, created = omni.kit.commands.execute(
                "MaterialGraph_CreatePrimCommand",
                parent_path=parent_path,
                prim_type=UsdShade.Tokens.Material,
                prim_name="FailedMaterial",
                stage=self._stage,
            )

        self.assertTrue(success)
        self.assertIsNone(created)
        self.assertEqual(edit_layer.ExportToString(), before)
        omni.kit.undo.undo()
        omni.kit.undo.redo()
        self.assertEqual(edit_layer.ExportToString(), before)
        self.assertFalse(self._stage.GetPrimAtPath(parent_path))
