import omni.kit.commands
from pxr import Sdf, UsdShade, UsdUI

from .base import CommandsTestBase


class TestMaterialCommand(CommandsTestBase):
    """MaterialGraph_NewUsdShadeMaterialCommand creates a Material prim under Looks with NodeGraphNodeAPI.
    We test create/undo/redo and that undo does not clobber user selection when they changed it."""

    async def setUp(self) -> None:
        """Load the simple scene for material command tests."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._looks_path = Sdf.Path("/World/Looks")
        self._material_path = Sdf.Path("/World/Looks/Material")

    async def test_create_material_undo_redo(self) -> None:
        """Create material; undo/redo round-trips."""
        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([Sdf.Path("/World/Looks/material").pathString], True)

        omni.kit.commands.execute(
            "MaterialGraph_NewUsdShadeMaterialCommand",
            parent_path=self._looks_path,
            identifier="Material",
            position=(10, 20),
            select_new_prim=True,
        )

        def _after() -> None:
            """Validate material creation after redo."""
            prim = self._get_prim_at_path(self._material_path)
            self.assertTrue(prim.IsA(UsdShade.Material))
            self.assertTrue(prim.HasAPI(UsdUI.NodeGraphNodeAPI))

        def _before() -> None:
            """Validate material removal and selection after undo."""
            self.assertFalse(self._stage.GetPrimAtPath(self._material_path))
            selected = self._usd_context.get_selection().get_selected_prim_paths()
            self.assertIn("/World/Looks/material", selected)

        await self._assert_undo_redo(_before, _after)

    async def test_create_material_undo_respects_user_selection(self) -> None:
        """Undo does not clobber user selection."""
        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([Sdf.Path("/World/Looks/material").pathString], True)

        omni.kit.commands.execute(
            "MaterialGraph_NewUsdShadeMaterialCommand",
            parent_path=self._looks_path,
            identifier="Material",
            position=(10, 20),
            select_new_prim=True,
        )
        selection.set_selected_prim_paths([Sdf.Path("/World/Looks/material").pathString], True)
        self.assertTrue(omni.kit.undo.undo())
        selected = selection.get_selected_prim_paths()
        self.assertEqual(selected, ["/World/Looks/material"])
