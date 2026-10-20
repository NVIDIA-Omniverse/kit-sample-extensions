# pylint: disable=relative-beyond-top-level
from pxr import Sdf, UsdShade, Vt

from ...scripts.models.catalog.registries.compound.parsing import _extract_compound_data
from ...scripts.models.catalog.registries.compound.source import CompoundSource
from ..base import MaterialGraphTestBase


class TestCompoundSource(MaterialGraphTestBase):
    """Tests for compound source metadata."""

    async def test_compound_source_fields(self) -> None:
        """CompoundSource should preserve field values."""
        source = CompoundSource(
            source_asset="asset.usda",
            identifier="Prim",
            display_name="Display",
            description="Desc",
            category="Cat",
            icon="icon.png",
            ui_order=1,
            context_visibility=("mdl",),
        )
        self.assertEqual(source.source_asset, "asset.usda")
        self.assertEqual(source.identifier, "Prim")
        self.assertEqual(source.display_name, "Display")
        self.assertEqual(source.description, "Desc")
        self.assertEqual(source.category, "Cat")
        self.assertEqual(source.icon, "icon.png")
        self.assertEqual(source.ui_order, 1)
        self.assertEqual(list(source.context_visibility), ["mdl"])

    async def test_compound_context_visibility_prefers_nested_metadata(self) -> None:
        """Compound parsing should match graph context visibility metadata precedence."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/CompoundGraph"))
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui:contextVisibility", Vt.StringArray(["universal"]))
        prim.SetCustomDataByKey("omni:ui", {"contextVisibility": Vt.StringArray(["mdl"])})

        self.assertEqual(list(_extract_compound_data(prim, "compound.usda").context_visibility), ["mdl"])

    async def test_compound_context_visibility_top_level_fallback(self) -> None:
        """Compound parsing should read top-level context visibility metadata."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/CompoundGraphTopLevel"))
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui:contextVisibility", Vt.StringArray(["universal"]))

        self.assertEqual(list(_extract_compound_data(prim, "compound.usda").context_visibility), ["universal"])

    async def test_compound_context_visibility_nested_only(self) -> None:
        """Compound parsing should read nested context visibility metadata."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/CompoundGraphNested"))
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui", {"contextVisibility": Vt.StringArray(["mdl"])})

        self.assertEqual(list(_extract_compound_data(prim, "compound.usda").context_visibility), ["mdl"])

    async def test_compound_context_visibility_nested_empty(self) -> None:
        """An authored empty nested list should override top-level context visibility metadata."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/CompoundGraphNestedEmpty"))
        prim = nodegraph.GetPrim()
        prim.SetCustomDataByKey("omni:ui:contextVisibility", Vt.StringArray(["universal"]))
        prim.SetCustomDataByKey("omni:ui", {"contextVisibility": Vt.StringArray()})

        self.assertEqual(list(_extract_compound_data(prim, "compound.usda").context_visibility), [])
