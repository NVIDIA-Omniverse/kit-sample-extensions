# pylint: disable=relative-beyond-top-level
import carb.settings

from ...scripts.settings.catalog import Catalog
from ...scripts.settings.utils import CATALOG_TEXTURE_ICON_SIZE
from ..base import MaterialGraphTestBase


class TestConfigCatalog(MaterialGraphTestBase):
    """Catalog config (e.g. texture icon size) is read from carb.settings; invalid or missing values
    must fall back to defaults so the UI never gets bad numbers. We test defaults for invalid/zero
    negative/non-numeric and that float is coerced to int."""

    async def test_texture_icon_size_defaults_on_invalid(self) -> None:
        """Invalid values fall back to default size."""
        settings = carb.settings.get_settings()
        key = CATALOG_TEXTURE_ICON_SIZE
        original = settings.get(key)
        try:
            settings.set(key, 0)
            self.assertEqual(Catalog.get_texture_icon_size(), Catalog.TEXTURE_ICON_SIZE_DEFAULT)
            settings.set(key, -5)
            self.assertEqual(Catalog.get_texture_icon_size(), Catalog.TEXTURE_ICON_SIZE_DEFAULT)
            settings.set(key, "bad")
            self.assertEqual(Catalog.get_texture_icon_size(), Catalog.TEXTURE_ICON_SIZE_DEFAULT)
        finally:
            settings.set(key, original)

    async def test_texture_icon_size_accepts_float(self) -> None:
        """Float coerced to int."""
        settings = carb.settings.get_settings()
        key = CATALOG_TEXTURE_ICON_SIZE
        original = settings.get(key)
        try:
            settings.set(key, 128.7)
            self.assertEqual(Catalog.get_texture_icon_size(), 128)
        finally:
            settings.set(key, original)
