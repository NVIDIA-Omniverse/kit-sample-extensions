# pylint: disable=relative-beyond-top-level
from ...scripts.plugins.impl.materialx.properties import MaterialXProperties
from ...scripts.plugins.impl.usd.properties import UsdProperties
from ..base import MaterialGraphTestBase


class TestPluginProperties(MaterialGraphTestBase):
    """Tests for plugin properties metadata."""

    async def test_materialx_properties_keys(self) -> None:
        """MaterialX properties should include expected keys."""
        keys = [prop.key for prop in MaterialXProperties().list()]
        self.assertIn("outputPorts", keys)
        self.assertIn("ignoreContexts", keys)
        self.assertIn("ignoreFamilies", keys)
        self.assertIn("ignoreNameRegexes", keys)

    async def test_usd_properties_keys(self) -> None:
        """USD properties should include outputPorts."""
        keys = [prop.key for prop in UsdProperties().list()]
        self.assertEqual(keys, ["outputPorts"])
