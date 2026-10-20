"""Top-level settings facade for the material graph extension."""

# pylint: disable=protected-access,no-member

from typing import Iterable, List, Optional, TypeVar, Union

import carb.settings

from . import compounds, plugins, ui, utils

T = TypeVar("T")

__all__ = ["Settings"]


class Settings:
    """Material graph settings helpers backed by carb.settings."""

    SETTINGS_PREFIX = utils.SETTINGS_PREFIX
    FORCE_CONNECT = utils.FORCE_CONNECT
    COLOR_NOODLES = utils.COLOR_NOODLES
    MDL_CATALOG_MODULES = utils.MDL_CATALOG_MODULES
    SHOW_CATALOG = utils.SHOW_CATALOG
    CONFINE_NODEGRAPHS = utils.CONFINE_NODEGRAPHS
    BACKDROP_DEFAULT_COLOR = utils.BACKDROP_DEFAULT_COLOR
    CONFINE_BACKDROPS = utils.CONFINE_BACKDROPS
    PREVIEW_TEXTURE_INPUT = utils.PREVIEW_TEXTURE_INPUT
    PLUGIN_PROPERTIES_PREFIX = utils.PLUGIN_PROPERTIES_PREFIX
    COMPOUND_PATHS = utils.COMPOUND_PATHS
    COMPOUND_DEFAULT_EXPORT_PATH = utils.COMPOUND_DEFAULT_EXPORT_PATH
    CATALOG_TEXTURES_PATH = utils.CATALOG_TEXTURES_PATH
    CATALOG_TEXTURE_ICON_SIZE = utils.CATALOG_TEXTURE_ICON_SIZE
    DROPPABLE_TEXTURE_FORMATS = utils.DROPPABLE_TEXTURE_FORMATS
    RENDER_CONTEXTS = utils.RENDER_CONTEXTS

    @staticmethod
    def get_setting_keys() -> List[str]:
        """Execute get setting keys behavior for material graph workflows."""

        return utils.get_setting_keys()

    @staticmethod
    def get_render_contexts() -> List[str]:
        """Execute get render contexts behavior for material graph workflows."""

        return ui.get_render_contexts()

    @staticmethod
    def get_render_context() -> str:
        """Execute get render context behavior for material graph workflows."""

        return ui.get_render_context()

    @staticmethod
    def get_mdl_catalog_modules() -> List[str]:
        """Execute get mdl catalog modules behavior for material graph workflows."""
        # Lazy import avoids settings<->plugins initialization cycle.
        from ..plugins.impl.mdl.settings import get_mdl_catalog_modules

        return get_mdl_catalog_modules()

    @staticmethod
    def set_mdl_catalog_modules(paths: Optional[Union[str, Iterable[str]]]) -> None:
        """Execute set mdl catalog modules behavior for material graph workflows."""
        # Lazy import avoids settings<->plugins initialization cycle.
        from ..plugins.impl.mdl.settings import set_mdl_catalog_modules

        set_mdl_catalog_modules(paths)

    @staticmethod
    def add_mdl_catalog_module(path: str) -> None:
        """Execute add mdl catalog module behavior for material graph workflows."""
        # Lazy import avoids settings<->plugins initialization cycle.
        from ..plugins.impl.mdl.settings import add_mdl_catalog_module

        add_mdl_catalog_module(path)

    @staticmethod
    def remove_mdl_catalog_module(path: str) -> None:
        """Execute remove mdl catalog module behavior for material graph workflows."""
        # Lazy import avoids settings<->plugins initialization cycle.
        from ..plugins.impl.mdl.settings import remove_mdl_catalog_module

        remove_mdl_catalog_module(path)

    @staticmethod
    def get_force_connect() -> bool:
        """Execute get force connect behavior for material graph workflows."""

        return ui.get_force_connect()

    @staticmethod
    def color_noodles() -> bool:
        """Return whether connection noodles should use port type colors."""
        return ui.color_noodles()

    @staticmethod
    def show_catalog() -> bool:
        """Execute show catalog behavior for material graph workflows."""

        return ui.show_catalog()

    @staticmethod
    def confine_nodegraphs() -> bool:
        """Execute confine nodegraphs behavior for material graph workflows."""

        return ui.confine_nodegraphs()

    @staticmethod
    def confine_backdrops() -> bool:
        """Execute confine backdrops behavior for material graph workflows."""

        return ui.confine_backdrops()

    @staticmethod
    def get_backdrop_default_color() -> tuple:
        """Return the default backdrop display color from settings."""
        settings = carb.settings.get_settings()
        val = settings.get(Settings.BACKDROP_DEFAULT_COLOR)
        if val and len(val) >= 3:
            return (float(val[0]), float(val[1]), float(val[2]))
        return utils.BACKDROP_DEFAULT_COLOR_DEFAULT

    @staticmethod
    def preview_texture_input() -> bool:
        """Execute preview texture input behavior for material graph workflows."""

        return ui.preview_texture_input()

    @staticmethod
    def get_compound_paths() -> List[str]:
        """Execute get compound paths behavior for material graph workflows."""

        return compounds.get_compound_paths()

    @staticmethod
    def set_compound_paths(paths: Optional[Union[str, Iterable[str]]]) -> None:
        """Execute set compound paths behavior for material graph workflows."""

        compounds.set_compound_paths(paths)

    @staticmethod
    def add_compound_path(path: str) -> None:
        """Execute add compound path behavior for material graph workflows."""

        compounds.add_compound_path(path)

    @staticmethod
    def remove_compound_path(path: str) -> None:
        """Execute remove compound path behavior for material graph workflows."""

        compounds.remove_compound_path(path)

    @staticmethod
    def clear_compound_paths() -> None:
        """Execute clear compound paths behavior for material graph workflows."""

        compounds.clear_compound_paths()

    @staticmethod
    def ensure_compound_paths_initialized() -> None:
        """Execute ensure compound paths initialized behavior for material graph workflows."""

        compounds.ensure_compound_paths_initialized()

    @staticmethod
    def get_plugin_property_key(plugin_name: str, key: str) -> Optional[str]:
        """Execute get plugin property key behavior for material graph workflows."""

        return plugins.get_plugin_property_key(plugin_name, key)

    @staticmethod
    def get_plugin_property(plugin_name: str, key: str, default: Optional[T] = None) -> Optional[T]:
        """Execute get plugin property behavior for material graph workflows."""

        return plugins.get_plugin_property(plugin_name, key, default)

    @staticmethod
    def set_plugin_property(plugin_name: str, key: str, value: T) -> None:
        """Execute set plugin property behavior for material graph workflows."""

        plugins.set_plugin_property(plugin_name, key, value)

    @staticmethod
    def set_plugin_property_schema(plugin_name: str, properties: Iterable[object]) -> None:
        """Execute set plugin property schema behavior for material graph workflows."""

        plugins.set_plugin_property_schema(plugin_name, properties)

    @staticmethod
    def clear_plugin_property_schema(plugin_name: str) -> None:
        """Execute clear plugin property schema behavior for material graph workflows."""

        plugins.clear_plugin_property_schema(plugin_name)

    @staticmethod
    def get_catalog_texture_icon_size() -> int:
        """Execute get catalog texture icon size behavior for material graph workflows."""

        settings = carb.settings.get_settings()
        value = settings.get(utils.CATALOG_TEXTURE_ICON_SIZE) if settings else None
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
        return utils.CATALOG_TEXTURE_ICON_SIZE_DEFAULT

    @staticmethod
    def get_droppable_texture_formats() -> List[str]:
        """Execute get droppable texture formats behavior for material graph workflows."""

        settings = carb.settings.get_settings()
        raw = settings.get(utils.DROPPABLE_TEXTURE_FORMATS) if settings else None
        sanitized = utils.sanitize_texture_formats(raw)
        if sanitized:
            return sanitized
        return list(utils.DROPPABLE_TEXTURE_FORMATS_DEFAULT)

    @staticmethod
    def set_droppable_texture_formats(formats: Optional[Union[str, Iterable[object]]]) -> None:
        """Execute set droppable texture formats behavior for material graph workflows."""

        settings = carb.settings.get_settings()
        if not settings:
            return
        sanitized = utils.sanitize_texture_formats(formats)
        settings.set(utils.DROPPABLE_TEXTURE_FORMATS, sanitized)

    @staticmethod
    def _get_bool(key: str, default: bool) -> bool:
        """Execute get bool behavior for material graph workflows."""

        return utils._get_bool(key, default)

    @staticmethod
    def _get_list(key: str) -> List[object]:
        """Execute get list behavior for material graph workflows."""

        return utils._get_list(key)

    @classmethod
    def _sync_from_utils(cls) -> None:
        """Execute sync from utils behavior for material graph workflows."""

        cls.SETTINGS_PREFIX = utils.SETTINGS_PREFIX
        cls.FORCE_CONNECT = utils.FORCE_CONNECT
        cls.COLOR_NOODLES = utils.COLOR_NOODLES
        cls.MDL_CATALOG_MODULES = utils.MDL_CATALOG_MODULES
        cls.SHOW_CATALOG = utils.SHOW_CATALOG
        cls.CONFINE_NODEGRAPHS = utils.CONFINE_NODEGRAPHS
        cls.BACKDROP_DEFAULT_COLOR = utils.BACKDROP_DEFAULT_COLOR
        cls.CONFINE_BACKDROPS = utils.CONFINE_BACKDROPS
        cls.PREVIEW_TEXTURE_INPUT = utils.PREVIEW_TEXTURE_INPUT
        cls.PLUGIN_PROPERTIES_PREFIX = utils.PLUGIN_PROPERTIES_PREFIX
        cls.COMPOUND_PATHS = utils.COMPOUND_PATHS
        cls.COMPOUND_DEFAULT_EXPORT_PATH = utils.COMPOUND_DEFAULT_EXPORT_PATH
        cls.CATALOG_TEXTURES_PATH = utils.CATALOG_TEXTURES_PATH
        cls.CATALOG_TEXTURE_ICON_SIZE = utils.CATALOG_TEXTURE_ICON_SIZE
        cls.DROPPABLE_TEXTURE_FORMATS = utils.DROPPABLE_TEXTURE_FORMATS
        cls.RENDER_CONTEXTS = utils.RENDER_CONTEXTS


utils.set_settings_sync_hook(Settings._sync_from_utils)
