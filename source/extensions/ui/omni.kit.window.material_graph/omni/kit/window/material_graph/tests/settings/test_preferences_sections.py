# pylint: disable=relative-beyond-top-level
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from omni.kit.window.preferences import SettingType

from ...scripts.preferences.core.constants import ITEM_SPACING, LIST_MAX_ROWS, LIST_MIN_ROWS, LIST_PADDING, ROW_HEIGHT
from ...scripts.preferences.sections.catalog import CatalogSettingsSection
from ...scripts.preferences.sections.export import ExportSettingsSection
from ...scripts.preferences.sections.general import GeneralSettingsSection
from ...scripts.preferences.sections.graph import GraphSettingsSection
from ...scripts.settings.settings import Settings
from ...scripts.settings.utils import COMPOUND_DEFAULT_PATH, DROPPABLE_TEXTURE_FORMATS_DEFAULT
from ..base import MaterialGraphTestBase


class _DummyFrame:
    """Minimal context-manager frame stub with mutable tooltip."""

    def __init__(self) -> None:
        self.tooltip = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyBuilder:
    """Builder stub to capture widget creation."""

    def __init__(self) -> None:
        self.calls = []
        self.frames = []
        self.item_spacing = ITEM_SPACING
        self.row_height = ROW_HEIGHT
        self.list_min_rows = LIST_MIN_ROWS
        self.list_max_rows = LIST_MAX_ROWS
        self.list_padding = LIST_PADDING

    def add_frame(self, name: str):
        self.frames.append(name)
        return _DummyFrame()

    @contextmanager
    def indented_stack(self):
        yield

    def create_setting_widget(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


class TestPreferencesSections(MaterialGraphTestBase):
    """Tests for preferences section builders."""

    async def test_graph_settings_section_builds_widgets(self) -> None:
        """Graph settings section should create expected widgets."""
        builder = _DummyBuilder()
        section = GraphSettingsSection(builder)
        section.build()
        keys = [args[1] for args, _ in builder.calls]
        self.assertEqual(
            keys,
            [
                Settings.CONFINE_NODEGRAPHS,
                Settings.CONFINE_BACKDROPS,
                Settings.BACKDROP_DEFAULT_COLOR,
                Settings.PREVIEW_TEXTURE_INPUT,
                Settings.FORCE_CONNECT,
                Settings.COLOR_NOODLES,
            ],
        )

    async def test_catalog_texture_path_setting_is_built(self) -> None:
        """Catalog settings should expose its standard asset field through the preferences builder."""
        builder = _DummyBuilder()
        section = CatalogSettingsSection(builder)
        dummy_settings = MagicMock()
        dummy_settings.get.side_effect = ["C:/textures", 256]
        with (
            patch("carb.settings.get_settings", return_value=dummy_settings),
            patch.object(section, "_build_icon_size_dropdown"),
            patch.object(section, "_build_compound_paths_frame"),
            patch("omni.ui.VStack", return_value=_DummyFrame()),
        ):
            section.build()

        self.assertEqual(builder.calls[0][0][:3], ("Textures Path", Settings.CATALOG_TEXTURES_PATH, SettingType.ASSET))
        self.assertEqual(builder.calls[1][0][:3], ("Show Catalog", Settings.SHOW_CATALOG, SettingType.BOOL))

    async def test_texture_format_actions_normalize_dedupe_remove_and_refresh(self) -> None:
        """Texture-format add/remove controls should mutate normalized settings and defer list refresh."""
        builder = _DummyBuilder()
        builder.schedule_refresh = MagicMock()
        section = GeneralSettingsSection(builder)
        section._texture_format_model = MagicMock()
        section._texture_format_model.get_value_as_string.return_value = " .PNG "
        with (
            patch.object(Settings, "get_droppable_texture_formats", return_value=["jpg"]),
            patch.object(Settings, "set_droppable_texture_formats") as set_formats,
        ):
            section.add_supported_texture_format()
            set_formats.assert_called_once_with(["jpg", "png"])
        section._texture_format_model.set_value.assert_called_once_with("")
        builder.schedule_refresh.assert_called_once_with(section.refresh_texture_format_list)

        builder.schedule_refresh.reset_mock()
        with (
            patch.object(Settings, "get_droppable_texture_formats", return_value=["jpg", "png"]),
            patch.object(Settings, "set_droppable_texture_formats") as set_formats,
        ):
            section._on_remove_supported_texture_format(".PNG")
            set_formats.assert_called_once_with(["jpg"])
        builder.schedule_refresh.assert_called_once_with(section.refresh_texture_format_list)

    async def test_remove_compound_path_updates_setting_and_defers_refresh(self) -> None:
        """Compound-folder removal should not rebuild OmniUI synchronously from its click callback."""
        builder = _DummyBuilder()
        builder.schedule_refresh = MagicMock()
        section = CatalogSettingsSection(builder)
        with patch.object(Settings, "remove_compound_path") as remove_path:
            section._on_remove_compound_path("C:/compounds")
        remove_path.assert_called_once_with("C:/compounds")
        builder.schedule_refresh.assert_called_once_with(section.refresh_compound_path_list)

    async def test_export_settings_section_sets_default(self) -> None:
        """Export settings section should seed missing defaults."""
        builder = _DummyBuilder()
        section = ExportSettingsSection(builder)
        dummy_settings = MagicMock()
        dummy_settings.get.return_value = None

        with patch("carb.settings.get_settings", return_value=dummy_settings):
            section.build()
        dummy_settings.set_string.assert_called_with(
            Settings.COMPOUND_DEFAULT_EXPORT_PATH,
            COMPOUND_DEFAULT_PATH,
        )
        self.assertTrue(any(args[2] == SettingType.ASSET for args, _ in builder.calls))

    async def test_general_settings_section_seeds_texture_format_defaults(self) -> None:
        """General settings section should initialize supported texture format defaults."""
        builder = _DummyBuilder()
        section = GeneralSettingsSection(builder)
        dummy_settings = MagicMock()
        dummy_settings.get.return_value = None
        with patch("carb.settings.get_settings", return_value=dummy_settings):
            section.build()
        dummy_settings.set.assert_called_with(
            Settings.DROPPABLE_TEXTURE_FORMATS,
            list(DROPPABLE_TEXTURE_FORMATS_DEFAULT),
        )
        self.assertIn("General Settings", builder.frames)
        self.assertIn("Droppable Texture Formats", builder.frames)
