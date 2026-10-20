# pylint: disable=relative-beyond-top-level,no-member
import unittest

from pxr import Sdf, UsdShade

from ...scripts.context_manager.context_manager import ContextManager
from .base import ContextManagerTestBase


class TestContextManagerLoad(ContextManagerTestBase):
    """ContextManager resolves a material prim from a path (material, nodegraph, shader, or backdrop)
    and builds per-plugin contexts for the graph. Load must succeed for valid material paths, resolve
    child paths to the parent material, and fail cleanly for invalid or missing stage. Validation runs
    after load per context, so cyclical graphs still load and are reported by validate_context."""

    async def setUp(self) -> None:
        """Load the simple scene and seed common prim paths."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._nodegraph_path = Sdf.Path("/World/Looks/material/nodegraph")
        self._backdrop_path = Sdf.Path("/World/Looks/material/backdrop")

    async def test_load_material_path(self) -> None:
        """Material path loads successfully."""
        self.assertTrue(self._manager.load(self._material_path))

        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        handle = self._manager.get_context(context_name)
        self.assertIsNotNone(handle.context)
        self.assertIsNotNone(handle.plugin)

    async def test_load_nodegraph_path(self) -> None:
        """NodeGraph path resolves to parent material."""
        self.assertTrue(self._manager.load(self._nodegraph_path))
        self.assertTrue(self._manager.load(self._material_path))

    async def test_load_shader_path(self) -> None:
        """Shader path resolves to parent material."""
        self.assertTrue(self._manager.load(self._shader_path))
        self.assertTrue(self._manager.load(self._material_path))

    async def test_load_backdrop_path(self) -> None:
        """Backdrop path resolves to parent material."""
        self.assertTrue(self._manager.load(self._backdrop_path))
        self.assertTrue(self._manager.load(self._material_path))

    async def test_load_invalid_path_retains_context(self) -> None:
        """Invalid path does not clear existing contexts."""
        self.assertTrue(self._manager.load(self._material_path))
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        handle_before = self._manager.get_context(context_name)
        self.assertIsNotNone(handle_before.context)

        self.assertFalse(self._manager.load(Sdf.Path("/InvalidPath")))
        handle_after = self._manager.get_context(context_name)
        self.assertIs(handle_before.context, handle_after.context)

    async def test_load_missing_stage(self) -> None:
        """Load fails when USD stage is missing."""

        class DummyContext:
            """Context returning no stage."""

            def get_stage(self) -> None:
                """Return no stage."""
                return None

        manager = ContextManager(DummyContext())
        self.assertFalse(manager.load(Sdf.Path("/Looks/material")))
        self.assertEqual(manager.get_last_error(), "No USD stage")
        manager.destroy()
