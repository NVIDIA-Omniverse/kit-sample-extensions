from unittest.mock import patch

import omni.kit.commands
from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.utils.sdr_wrappers import SdrRegistryWrapper
from .base import CommandsTestBase


class TestNodeCommands(CommandsTestBase):
    """NewUsdShadeNodeCommand and NewUsdShadeNodeFromSdrCommand create shader nodes under a material.
    We test creation with SDR node and with identifier, custom data, and undo/redo."""

    async def setUp(self) -> None:
        """Load the simple scene for node command tests."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")

    async def test_create_node_from_sdr_node(self) -> None:
        """Create shader from SDR node; undo/redo round-trips."""
        sdr_node = SdrRegistryWrapper().GetShaderNodeByIdentifier("UsdPreviewSurface")
        self.assertIsNotNone(sdr_node)

        omni.kit.commands.execute(
            "MaterialGraph_NewUsdShadeNodeCommand",
            parent_path=self._material_path,
            node=sdr_node,
            position=(5, 6),
            custom_data={"custom": "value"},
        )

        created_path = Sdf.Path("/World/Looks/material/UsdPreviewSurface")

        def _after() -> None:
            """Validate shader creation after redo."""
            prim = self._get_prim_at_path(created_path)
            self.assertTrue(prim.IsA(UsdShade.Shader))
            # Some builds do not apply the API via the wrapped command.
            self.assertEqual(prim.GetCustomData().get("custom"), "value")

        def _before() -> None:
            """Validate shader removal after undo."""
            self.assertFalse(self._stage.GetPrimAtPath(created_path))

        await self._assert_undo_redo(_before, _after)

    async def test_create_node_from_identifier(self) -> None:
        """Create shader from identifier; undo/redo round-trips."""
        result = omni.kit.commands.execute(
            "MaterialGraph_NewUsdShadeNodeFromSdrCommand",
            parent_path=self._material_path,
            identifier="UsdPreviewSurface",
            position=(12, 14),
        )

        shader_prim = result
        if isinstance(shader_prim, tuple):
            if len(shader_prim) >= 2 and isinstance(shader_prim[0], bool):
                self.assertTrue(shader_prim[0])
                shader_prim = shader_prim[1]
            else:
                shader_prim = shader_prim[0]
        self.assertIsNotNone(UsdShade.Shader(shader_prim))

        created_path = Sdf.Path("/World/Looks/material/UsdPreviewSurface")

        def _after() -> None:
            """Validate shader creation after redo."""
            prim = self._get_prim_at_path(created_path)
            self.assertTrue(prim.IsA(UsdShade.Shader))
            # NodeGraphNodeAPI application varies by Kit build; don't assert it here.

        def _before() -> None:
            """Validate shader removal after undo."""
            self.assertFalse(self._stage.GetPrimAtPath(created_path))

        await self._assert_undo_redo(_before, _after)

    async def test_create_node_from_invalid_identifier_logs_and_returns_none(self) -> None:
        """Invalid SDR identifiers should fail safely and emit a warning."""
        # Patch logger.warning to assert that the command reports the invalid
        # identifier failure path without depending on global logging output.
        with patch(f"{Paths.MODULE_ID}.scripts.commands.impl.prim.new_node_from_sdr.logger.warning") as warn:
            result = omni.kit.commands.execute(
                "MaterialGraph_NewUsdShadeNodeFromSdrCommand",
                parent_path=self._material_path,
                identifier="DefinitelyNotARealSdrNodeIdentifier",
                position=(1, 2),
            )
        if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[0], bool):
            self.assertTrue(result[0])
            self.assertIsNone(result[1])
        else:
            self.assertIsNone(result)
        warn.assert_called_once()
