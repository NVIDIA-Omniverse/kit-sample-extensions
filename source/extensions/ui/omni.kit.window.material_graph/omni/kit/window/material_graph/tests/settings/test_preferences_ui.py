# pylint: disable=relative-beyond-top-level,protected-access
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import carb.settings
import omni.kit.ui_test as ui_test

from ...scripts.config.paths import Paths
from ...scripts.extension import GraphExtension
from ...scripts.plugins.impl.mdl import settings as mdl_settings
from ...scripts.preferences.core.constants import (
    INDENT,
    ITEM_SPACING,
    LIST_MAX_ROWS,
    LIST_MIN_ROWS,
    LIST_PADDING,
    ROW_HEIGHT,
)
from ...scripts.preferences.page import MaterialGraphPreferences
from ...scripts.preferences.ui.lists import get_list_height
from ...scripts.settings.settings import Settings
from ...scripts.settings.utils import (
    CATALOG_TEXTURES_PATH_DEFAULT,
    COMPOUND_DEFAULT_PATH,
)
from ..ui_base import MaterialGraphUiTestBase


class TestPreferencesUi(MaterialGraphUiTestBase):
    """Preference UI interactions for settings."""

    async def test_real_list_widget_repeated_add_remove_is_deferred_and_stays_expanded(self) -> None:
        """Exercise real OmniUI callbacks without coordinate-based mouse automation."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        factory = prefs.get_plugin_property_factory()
        window = await self.create_test_window(width=480, height=360, block_devices=False)
        Settings.set_plugin_property("test_plugin", "items", ["Remove Me"])

        try:
            with window.frame:
                factory._build_string_list(
                    "test_plugin",
                    {"key": "items", "label": "Lifecycle Items", "default": []},
                )
            entry = factory._list_stacks["test_plugin:items"]
            frame = entry["frame"]
            frame.collapsed = False
            await self.wait_n_updates(3)

            window_ref = ui_test.WindowRef(window, "")
            remove = window_ref.find("**/Button[*].text=='Remove'")
            self.assertIsNotNone(remove)
            await remove.click()
            await self.wait_n_updates(3)
            self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), [])

            for index in range(3):
                self.assertIs(factory._list_stacks["test_plugin:items"]["frame"], frame)
                self.assertFalse(frame.collapsed)

                field = window_ref.find("**/StringField[*]")
                add = window_ref.find("**/Button[*].text=='Add'")
                self.assertIsNotNone(field)
                self.assertIsNotNone(add)
                value = f"Cycle {index}"
                field.widget.model.set_value(value)
                await add.click()
                await self.wait_n_updates(3)
                self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), [value])

                remove = window_ref.find("**/Button[*].text=='Remove'")
                self.assertIsNotNone(remove)
                await remove.click()
                await self.wait_n_updates(3)
                self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), [])

            self.assertIs(factory._list_stacks["test_plugin:items"]["frame"], frame)
            self.assertFalse(frame.collapsed)
        finally:
            Settings.set_plugin_property("test_plugin", "items", [])
            prefs.destroy()
            window.visible = False
            await self.wait_n_updates(2)

    async def test_real_mdl_module_buttons_mutate_settings_semantically(self) -> None:
        """Click the MDL Add/Remove controls while keeping resolution at the external boundary."""

        original = Settings.get_mdl_catalog_modules()
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        factory = prefs.get_plugin_property_factory()
        window = await self.create_test_window(width=520, height=300, block_devices=False)
        try:
            with patch.object(mdl_settings, "_can_resolve_mdl_path", return_value=True):
                Settings.set_mdl_catalog_modules(["existing.mdl"])
                with window.frame:
                    factory._build_mdl_modules(
                        "mdl",
                        {"key": "modules", "label": "Modules", "default": []},
                    )
                entry = factory._list_stacks["mdl:modules"]
                entry["frame"].collapsed = False
                await self.wait_n_updates(3)
                window_ref = ui_test.WindowRef(window, "")

                remove = window_ref.find("**/Button[*].text=='Remove'")
                self.assertIsNotNone(remove.widget)
                await remove.click()
                await self.wait_n_updates(3)
                self.assertNotIn("existing.mdl", Settings.get_mdl_catalog_modules())

                field = window_ref.find("**/StringField[*]")
                add = window_ref.find("**/Button[*].text=='Add'")
                field.widget.model.set_value("semantic.mdl")
                await add.click()
                await self.wait_n_updates(3)
                self.assertIn("semantic.mdl", Settings.get_mdl_catalog_modules())
        finally:
            with patch.object(mdl_settings, "_can_resolve_mdl_path", return_value=True):
                Settings.set_mdl_catalog_modules(original)
            prefs.destroy()
            window.visible = False
            await self.wait_n_updates(2)

    async def test_real_texture_format_buttons_mutate_settings_semantically(self) -> None:
        """Click custom texture-format controls and verify their extension-owned normalization."""

        original = Settings.get_droppable_texture_formats()
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        window = await self.create_test_window(width=520, height=240, block_devices=False)
        Settings.set_droppable_texture_formats(["png"])

        try:
            with window.frame:
                prefs._general_section._build_texture_formats_frame()
            await self.wait_n_updates(3)
            window_ref = ui_test.WindowRef(window, "")
            field = window_ref.find("**/StringField[*]")
            field.widget.model.set_value(" .TGA ")
            await window_ref.find("**/Button[*].text=='Add'").click()
            await self.wait_n_updates(2)
            self.assertEqual(Settings.get_droppable_texture_formats(), ["png", "tga"])

            await window_ref.find("**/Button[*].text=='Remove'").click()
            await self.wait_n_updates(2)
            self.assertEqual(Settings.get_droppable_texture_formats(), ["tga"])
        finally:
            Settings.set_droppable_texture_formats(original)
            prefs.destroy()
            window.visible = False
            await self.wait_n_updates(2)

    async def test_real_compound_folder_buttons_route_semantically(self) -> None:
        """Click Add Folder and Remove while dialog rendering remains Kit's responsibility."""

        original = Settings.get_compound_paths()
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        window = await self.create_test_window(width=560, height=240, block_devices=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            Settings.set_compound_paths([temp_dir])
            try:
                with window.frame:
                    prefs._catalog_section._build_compound_paths_frame()
                await self.wait_n_updates(3)
                window_ref = ui_test.WindowRef(window, "")
                with patch(f"{Paths.MODULE_ID}.scripts.preferences.sections.catalog.FilePickerDialog") as picker:
                    await window_ref.find("**/Button[*].text=='Add Folder'").click()
                picker.assert_called_once()

                await window_ref.find("**/Button[*].text=='Remove'").click()
                await self.wait_n_updates(2)
                self.assertNotIn(temp_dir, Settings.get_compound_paths())
            finally:
                Settings.set_compound_paths(original)
                prefs.destroy()
                window.visible = False
                await self.wait_n_updates(2)

    async def test_add_remove_mdl_module(self) -> None:
        """MDL module list should update via plugin settings UI."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        prefs.build()
        factory = prefs.get_plugin_property_factory()
        stack_key = "mdl:modules"
        entry = factory._list_stacks.get(stack_key)
        self.assertIsNotNone(entry)
        model = MagicMock()
        model.get_value_as_string.return_value = "test.mdl"
        with patch.object(mdl_settings, "_can_resolve_mdl_path", autospec=True, return_value=True):
            factory._on_add_list_item(stack_key, model)
            self.assertIn("test.mdl", Settings.get_mdl_catalog_modules())

            factory._on_remove_list_item(stack_key, "test.mdl")
            self.assertNotIn("test.mdl", Settings.get_mdl_catalog_modules())
        prefs.destroy()

    async def test_toggle_show_catalog_setting(self) -> None:
        """Preferences build should initialize expected UI models."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        prefs.build()
        settings = carb.settings.get_settings()
        self.assertEqual(
            settings.get(Settings.CATALOG_TEXTURES_PATH),
            CATALOG_TEXTURES_PATH_DEFAULT,
        )
        self.assertEqual(
            settings.get(Settings.COMPOUND_DEFAULT_EXPORT_PATH),
            COMPOUND_DEFAULT_PATH,
        )
        prefs.destroy()

    async def test_preferences_layout_constants(self) -> None:
        """Preference builder should use shared layout constants."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        self.assertEqual(prefs.indent, INDENT)
        self.assertEqual(prefs.item_spacing, ITEM_SPACING)
        self.assertEqual(prefs.row_height, ROW_HEIGHT)
        self.assertEqual(prefs.list_min_rows, LIST_MIN_ROWS)
        self.assertEqual(prefs.list_max_rows, LIST_MAX_ROWS)
        self.assertEqual(prefs.list_padding, LIST_PADDING)
        prefs.destroy()

    async def test_icon_size_dropdown_values(self) -> None:
        """Icon size dropdown should use the expected values."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        with (
            patch.object(
                MaterialGraphPreferences,
                "create_setting_widget_combo",
                autospec=True,
                return_value=None,
            ) as combo,
            patch.object(
                MaterialGraphPreferences,
                "create_setting_widget",
                autospec=True,
                return_value=None,
            ),
        ):
            prefs.build()
        sizes = None
        for call in combo.call_args_list:
            if call.args and call.args[1] == "Catalog Texture Icon Size":
                sizes = call.args[3]
                break
        self.assertEqual(sizes, [64, 128, 256, 512, 1024])
        prefs.destroy()

    async def test_plugin_property_list_trims_and_dedupes(self) -> None:
        """List property inputs should trim and avoid case-insensitive duplicates."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        factory = prefs.get_plugin_property_factory()
        factory._list_stacks["test:items"] = {
            "stack": MagicMock(),
            "plugin": "test_plugin",
            "prop": {"key": "items", "default": []},
        }
        model = MagicMock()
        model.get_value_as_string.return_value = " Value "

        with patch.object(factory, "_refresh_list_property", autospec=True):
            Settings.set_plugin_property("test_plugin", "items", [])
            factory._on_add_list_item("test:items", model)
            self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), ["Value"])
            model.get_value_as_string.return_value = "value"
            factory._on_add_list_item("test:items", model)
            self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), ["Value"])
        prefs.destroy()

    async def test_plugin_property_list_remove(self) -> None:
        """Removing list items should update the stored setting."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        factory = prefs.get_plugin_property_factory()
        factory._list_stacks["test:items"] = {
            "stack": MagicMock(),
            "plugin": "test_plugin",
            "prop": {"key": "items", "default": []},
        }
        with patch.object(factory, "_refresh_list_property", autospec=True):
            Settings.set_plugin_property("test_plugin", "items", ["Keep", "Remove"])
            factory._on_remove_list_item("test:items", "Remove")
            self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), ["Keep"])
        prefs.destroy()

    async def test_compound_path_add_opens_folder_picker(self) -> None:
        """Compound folder Add should launch a folder picker."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        with patch(f"{Paths.MODULE_ID}.scripts.preferences.sections.catalog.FilePickerDialog") as picker:
            prefs._catalog_section.pick_compound_path()
            picker.assert_called_once()
        prefs.destroy()

    async def test_compound_folder_picker_apply_adds_path(self) -> None:
        """Applying a selected compound folder should store the path."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        with tempfile.TemporaryDirectory() as temp_dir:
            dialog = MagicMock()
            prefs._catalog_section._pick_folder_dialog = dialog
            prefs._catalog_section._on_selection_changed([SimpleNamespace(path=temp_dir)])
            prefs._catalog_section._on_apply_folder("", "")

            self.assertIn(temp_dir, Settings.get_compound_paths())
            dialog.hide.assert_called_once()
        prefs.destroy()

    async def test_path_list_height_bounds(self) -> None:
        """Path list helper should honor min/max row bounds."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        self.assertEqual(get_list_height(prefs, 0), ROW_HEIGHT + LIST_PADDING)
        self.assertEqual(get_list_height(prefs, LIST_MAX_ROWS + 2), (LIST_MAX_ROWS * ROW_HEIGHT) + LIST_PADDING)
        prefs.destroy()

    async def test_preferences_subscribe_once(self) -> None:
        """Preferences should not re-subscribe on repeated build calls."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        dummy_settings = MagicMock()
        dummy_settings.subscribe_to_tree_change_events.return_value = MagicMock()
        with (
            patch("carb.settings.get_settings", autospec=True, return_value=dummy_settings),
            patch.object(MaterialGraphPreferences, "create_setting_widget", autospec=True, return_value=None),
        ):
            prefs.build()
            prefs.build()
        self.assertEqual(dummy_settings.subscribe_to_tree_change_events.call_count, 1)
        prefs.destroy()

    async def test_preferences_frames_default_expand_one_level(self) -> None:
        """Top-level settings frames should default open; nested frames closed."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        calls = []
        dummy_settings = MagicMock()
        dummy_settings.get.side_effect = lambda key: "" if key == "/placeholder" else None
        dummy_settings.subscribe_to_tree_change_events.return_value = MagicMock()

        class _DummyFrame:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _fake_collapsable_frame(**kwargs):
            calls.append(kwargs)
            return _DummyFrame()

        with (
            patch("carb.settings.get_settings", return_value=dummy_settings),
            patch(
                f"{Paths.MODULE_ID}.scripts.preferences.page.omni.ui.CollapsableFrame",
                side_effect=_fake_collapsable_frame,
            ),
        ):
            prefs.build()

        by_title = {call["title"]: call["collapsed"] for call in calls if "title" in call and "collapsed" in call}
        self.assertFalse(by_title["General Settings"])
        self.assertFalse(by_title["Graph Settings"])
        self.assertFalse(by_title["Catalog Settings"])
        self.assertFalse(by_title["Plugin Settings"])
        self.assertFalse(by_title["Export Settings"])
        self.assertTrue(by_title["Droppable Texture Formats"])
        self.assertTrue(by_title["Plugins"])
        self.assertTrue(by_title["Compound Folders"])
        prefs.destroy()
