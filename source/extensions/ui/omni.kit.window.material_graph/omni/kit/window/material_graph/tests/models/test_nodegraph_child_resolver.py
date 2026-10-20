# pylint: disable=relative-beyond-top-level,no-member,protected-access
from pxr import Sdf, UsdShade, UsdUI

from ...scripts.models.graph.nodes.nodegraph.child_resolver import NodeGraphChildResolver
from ..base import MaterialGraphTestBase


class _DummyPlugin:
    """Plugin stub for child resolver tests."""

    def is_supported_prim(self, prim) -> bool:
        return prim.IsA(UsdShade.Shader)


class _DummyModel:
    """Minimal model stub for resolver tests."""

    def __init__(self, prim, context_name: str) -> None:
        self.prim = prim
        self._prim = prim
        self._plugin = _DummyPlugin()
        self.context_name = context_name


class TestNodeGraphChildResolver(MaterialGraphTestBase):
    """Tests for nodegraph child resolution."""

    async def test_context_visibility_filtering(self) -> None:
        """Context visibility should filter contextual prims."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/Nodegraph"))
        prim = nodegraph.GetPrim()

        child_shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Nodegraph/Shader")).GetPrim()
        child_backdrop = UsdUI.Backdrop.Define(self._stage, Sdf.Path("/World/Nodegraph/Backdrop")).GetPrim()
        child_nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/Nodegraph/Child")).GetPrim()

        child_backdrop.SetCustomDataByKey("omni:ui", {"contextVisibility": ["mdl"]})
        child_nodegraph.SetCustomDataByKey("omni:ui", {"contextVisibility": ["mtlx"]})

        model = _DummyModel(prim, "mdl")
        resolver = NodeGraphChildResolver(model)
        children = resolver.get_child_prims()

        self.assertIn(child_shader, children)
        self.assertIn(child_backdrop, children)
        self.assertNotIn(child_nodegraph, children)
