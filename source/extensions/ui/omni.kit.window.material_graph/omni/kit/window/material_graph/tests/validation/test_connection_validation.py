# pylint: disable=relative-beyond-top-level,no-member
from pxr import Sdf, UsdShade

from ...scripts.models.graph.ports.internal.validation import _collect_cycle_nodes, find_cyclical_prims
from ..base import MaterialGraphTestBase


class TestConnectionValidation(MaterialGraphTestBase):
    """Tests for connection validation helpers."""

    async def test_find_cyclical_prims_detects_cycle(self) -> None:
        """Cycles between shader inputs should be detected."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/MatCycle"))
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/MatCycle/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/MatCycle/ShaderB"))

        a_out = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        a_in = shader_a.CreateInput("in", Sdf.ValueTypeNames.Float)
        b_out = shader_b.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_in = shader_b.CreateInput("in", Sdf.ValueTypeNames.Float)

        b_in.ConnectToSource(a_out)
        a_in.ConnectToSource(b_out)

        cyclical = find_cyclical_prims(material.GetPrim())
        paths = {prim.GetPath() for prim in cyclical}
        self.assertIn(shader_a.GetPrim().GetPath(), paths)
        self.assertIn(shader_b.GetPrim().GetPath(), paths)

    async def test_find_cyclical_prims_no_cycle(self) -> None:
        """Non-cyclical connections should return an empty list."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/MatLinear"))
        shader_a = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/MatLinear/ShaderA"))
        shader_b = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/MatLinear/ShaderB"))

        b_in = shader_b.CreateInput("in", Sdf.ValueTypeNames.Float)
        a_out = shader_a.CreateOutput("out", Sdf.ValueTypeNames.Float)
        b_in.ConnectToSource(a_out)

        self.assertEqual(find_cyclical_prims(material.GetPrim()), [])

    async def test_find_cyclical_prims_invalid_root(self) -> None:
        """Invalid roots should return an empty list."""
        self.assertEqual(find_cyclical_prims(None), [])

    async def test_cycle_collection_excludes_ancestors_and_finds_all_components(self) -> None:
        """Only SCC members are reported, including disjoint cycles and self-loops."""
        ancestor = Sdf.Path("/Ancestor")
        cycle_a = Sdf.Path("/CycleA")
        cycle_b = Sdf.Path("/CycleB")
        cycle_c = Sdf.Path("/CycleC")
        cycle_d = Sdf.Path("/CycleD")
        self_loop = Sdf.Path("/Self")
        edges = {
            ancestor: {cycle_a},
            cycle_a: {cycle_b},
            cycle_b: {cycle_a},
            cycle_c: {cycle_d},
            cycle_d: {cycle_c},
            self_loop: {self_loop},
        }
        nodes = {ancestor, cycle_a, cycle_b, cycle_c, cycle_d, self_loop}

        self.assertEqual(
            _collect_cycle_nodes(edges, nodes),
            {cycle_a, cycle_b, cycle_c, cycle_d, self_loop},
        )
