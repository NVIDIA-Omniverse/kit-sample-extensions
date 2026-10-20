"""Implement material graph extension logic for `settings/catalog.py`."""

from . import utils
from .settings import Settings


class Catalog:
    """Typed facade for catalog-related settings keys and persistence helpers."""

    TEXTURE_ICON_SIZE_DEFAULT = utils.CATALOG_TEXTURE_ICON_SIZE_DEFAULT
    SUPPORTED_TEXTURE_FORMATS_DEFAULT = list(utils.DROPPABLE_TEXTURE_FORMATS_DEFAULT)

    @staticmethod
    def get_texture_icon_size() -> int:
        """Return the configured texture icon size."""
        return Settings.get_catalog_texture_icon_size()

    @staticmethod
    def get_supported_texture_formats() -> list[str]:
        """Return configured supported texture file extensions."""
        return Settings.get_droppable_texture_formats()
