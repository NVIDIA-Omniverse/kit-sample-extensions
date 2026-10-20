from pxr import Sdf, UsdShade

from ...scripts.models.graph.nodes.prim.model import PrimModel
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestConnectionTraversal(MaterialGraphTestBase):
    async def setUp(self) -> None:
        """Load the simple scene and initialize a shader prim model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._plugin = DummyPlugin()

        self._shader_prim = self._get_prim_at_path(self._shader_path)
        self._prim_model = PrimModel(
            self._shader_prim,
            "universal",
            self._usd_context,
            self._plugin,
            None,
            UsdShade.Shader,
        )

    async def test_traversal_skips_materials(self) -> None:
        input_model = self._prim_model._inputs.get_child_by_path(
            self._shader_path.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor")
        )
        input_model.sync()
        connected = input_model.get_connected_prims(recurse_nodegraphs=True)
        self.assertFalse(any(prim.IsA(UsdShade.Material) for prim in connected))

    async def test_traversal_avoids_cycles(self) -> None:
        """Traversal should not loop forever when cycles exist."""
        # Build two shaders that reference each other and ensure traversal
        # does not expand indefinitely.
        shader_a = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        shader_b_path = self._shader_path.GetParentPath().AppendChild("shader_b")
        shader_b = UsdShade.Shader.Define(self._stage, shader_b_path)
        out_a = shader_a.CreateOutput("outA", Sdf.ValueTypeNames.Float)
        in_a = shader_a.CreateInput("inA", Sdf.ValueTypeNames.Float)
        out_b = shader_b.CreateOutput("outB", Sdf.ValueTypeNames.Float)
        in_b = shader_b.CreateInput("inB", Sdf.ValueTypeNames.Float)

        in_b.ConnectToSource(out_a)
        in_a.ConnectToSource(out_b)

        self._prim_model.sync()
        input_model = self._prim_model._inputs.get_child_by_path(
            self._shader_path.AppendProperty(f"{UsdShade.Tokens.inputs}inA")
        )
        input_model.sync()
        connected = input_model.get_connected_prims(recurse_nodegraphs=True)
        self.assertLessEqual(len(connected), 2)

    async def test_traversal_handles_invalid_prims(self) -> None:
        """Traversal should ignore sources that no longer exist."""
        shader = UsdShade.Shader(self._get_prim_at_path(self._shader_path))
        temp_path = self._shader_path.GetParentPath().AppendChild("temp_shader")
        temp_shader = UsdShade.Shader.Define(self._stage, temp_path)
        out_temp = temp_shader.CreateOutput("outTemp", Sdf.ValueTypeNames.Float)
        in_main = shader.CreateInput("inTemp", Sdf.ValueTypeNames.Float)
        in_main.ConnectToSource(out_temp)

        self._stage.RemovePrim(temp_path)
        self._prim_model.sync()
        input_model = self._prim_model._inputs.get_child_by_path(
            self._shader_path.AppendProperty(f"{UsdShade.Tokens.inputs}inTemp")
        )
        input_model.sync()
        connected = input_model.get_connected_prims(recurse_nodegraphs=True)
        self.assertTrue(all(prim.IsValid() for prim in connected))

    async def test_traversal_handles_ports_without_getattr(self) -> None:
        """Traversal should handle ports that only implement GetPath()."""
        # Dummy port objects are used by some tests; ensure they are tracked.
        input_model = self._prim_model._inputs.get_child_by_path(
            self._shader_path.AppendProperty(f"{UsdShade.Tokens.inputs}diffuseColor")
        )
        input_model.sync()

        class DummyPort:
            """Port stub lacking getattr access."""

            def GetPath(self) -> Sdf.Path:
                """Return the dummy port path."""
                return Sdf.Path("/Dummy/Port")

            def GetConnectedSources(self) -> list:
                """Return an empty list of connected sources."""
                return []

        visited_ports = set()
        input_model._connections._walk_connected_port(
            DummyPort(),
            True,
            [],
            set(),
            visited_ports,
            set(),
        )
        self.assertIn(Sdf.Path("/Dummy/Port"), visited_ports)
