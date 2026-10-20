# pylint: disable=relative-beyond-top-level,no-member
from pxr import Sdf, UsdShade

from ...scripts.models.graph.nodes.prim.schema import SchemaAttributeCollector
from ...scripts.models.graph.ports.proxy import ProxyAttribute
from ..base import MaterialGraphTestBase


class TestSchemaAttributes(MaterialGraphTestBase):
    """Tests for schema attribute helpers."""

    async def test_insert_schema_attributes_merges(self) -> None:
        """Schema attributes should be inserted after their anchor."""
        collector = SchemaAttributeCollector(None)
        anchor = ProxyAttribute("inputs:foo", False)
        anchor.display_name = "Foo"
        anchor.display_group = "Inputs:Group"

        schema_attr = ProxyAttribute("inputs:foo:bar", False)
        schema_attr.display_group = "Inputs:Extra"

        schema = {UsdShade.Tokens.inputs: {"inputs:foo": [schema_attr]}}
        merged = collector.insert_schema_attributes(False, [anchor], schema)

        self.assertEqual(len(merged), 2)
        self.assertIs(merged[0], anchor)
        self.assertIs(merged[1], schema_attr)
        self.assertIn("Foo", schema_attr.display_name)
        self.assertIn("Group", schema_attr.display_group)

    async def test_insert_schema_attributes_is_idempotent(self) -> None:
        """Repeated schema insertion should not duplicate anchor prefixes."""
        collector = SchemaAttributeCollector(None)
        anchor = ProxyAttribute("inputs:tex", False)
        anchor.display_name = "tex"
        anchor.display_group = "Inputs"

        schema_attr = ProxyAttribute("inputs:omni:playback:inputs:tex:playbackStart", False)
        schema_attr.display_name = "Playback Start"
        schema_attr.display_group = "Inputs:Playback"
        schema = {UsdShade.Tokens.inputs: {"inputs:tex": [schema_attr]}}

        first = collector.insert_schema_attributes(False, [anchor], schema)
        second = collector.insert_schema_attributes(False, first, schema)

        self.assertEqual(second[1].display_name, "tex Playback Start")
        self.assertEqual(second[1].display_group, "Inputs:tex Playback")

    async def test_add_or_update_proxy_attribute(self) -> None:
        """USD attributes should be added to proxy lists."""
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/Shader"))
        usd_attr = shader.CreateInput("input", Sdf.ValueTypeNames.Float).GetAttr()

        proxy_attributes = []
        SchemaAttributeCollector.add_or_update_proxy_attribute(False, usd_attr, proxy_attributes)

        self.assertEqual(len(proxy_attributes), 1)
        self.assertEqual(proxy_attributes[0].name, usd_attr.GetName())
