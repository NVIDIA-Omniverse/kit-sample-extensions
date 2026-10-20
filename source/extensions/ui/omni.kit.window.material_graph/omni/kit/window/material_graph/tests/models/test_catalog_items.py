import json

from ...scripts.models.catalog.items import CompoundItem, MiscellaneousItem, ShaderItem
from ..base import MaterialGraphTestBase

# pylint: disable=relative-beyond-top-level


class TestCatalogItems(MaterialGraphTestBase):
    """Catalog item serialization helpers."""

    async def test_drag_payload_serialization(self) -> None:
        """ShaderItem drag payload should serialize expected keys."""
        item = ShaderItem(
            name="TestShader",
            context="mdl",
            identifier="test_identifier",
            info="info",
        )
        payload = json.loads(item.get_drag_mime_data())
        self.assertEqual(payload["type"], "Shader")
        self.assertEqual(payload["identifier"], "test_identifier")
        self.assertEqual(payload["context"], "mdl")

    async def test_missing_icon_fallback(self) -> None:
        """Miscellaneous items should tolerate missing icon files."""
        item = MiscellaneousItem("MissingIcon", "info")
        payload = json.loads(item.get_drag_mime_data())
        self.assertEqual(payload["type"], "MissingIcon")

    async def test_compound_payload_serialization(self) -> None:
        """CompoundItem drag payload should serialize expected keys."""
        item = CompoundItem(
            name="TestCompound",
            info="info",
            icon="",
            tooltip="tooltip",
            source_asset="compound.usda",
            identifier="/CompoundGraph",
            context_visibility=["mdl"],
        )
        payload = json.loads(item.get_drag_mime_data())
        self.assertEqual(payload["type"], "ImportNodeGraph")
        self.assertEqual(payload["source_asset"], "compound.usda")
        self.assertEqual(payload["identifier"], "/CompoundGraph")
        self.assertEqual(payload["name"], "TestCompound")
