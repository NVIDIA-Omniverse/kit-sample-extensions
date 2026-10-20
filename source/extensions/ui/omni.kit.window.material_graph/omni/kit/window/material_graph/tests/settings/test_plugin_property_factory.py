# pylint: disable=relative-beyond-top-level,protected-access
from unittest.mock import MagicMock, patch

from ...scripts.config.paths import Paths
from ...scripts.preferences.plugin.factory import PluginPropertyWidgetFactory
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class TestPluginPropertyFactory(MaterialGraphTestBase):
    """Direct tests for plugin property widget factory."""

    async def test_generic_list_refresh_preserves_expanded_subpage(self) -> None:
        """Refreshing rows must not recreate or collapse their parent frame."""
        builder = MagicMock(indent=0, item_spacing=4, row_height=24)
        frame = MagicMock(collapsed=True)
        frame.__enter__.return_value = frame
        builder.add_frame.return_value = frame
        stack = MagicMock()
        stack.__enter__.return_value = stack
        factory = PluginPropertyWidgetFactory(builder)

        Settings.set_plugin_property("test_plugin", "items", ["first"])
        with patch(f"{Paths.MODULE_ID}.scripts.preferences.plugin.factory.omni.ui") as ui_mock:
            ui_mock.VStack.return_value = stack
            factory._build_string_list(
                "test_plugin",
                {"key": "items", "label": "Items", "description": "Paths", "default": []},
            )
            frame.collapsed = False

            Settings.set_plugin_property("test_plugin", "items", ["second"])
            factory._refresh_list_property("test_plugin:items")

        builder.add_frame.assert_called_once_with("Items")
        self.assertFalse(frame.collapsed)
        self.assertEqual(stack.clear.call_count, 2)

    async def test_mdl_list_refresh_preserves_expanded_subpage(self) -> None:
        """MDL row refreshes must retain the existing Modules frame."""
        builder = MagicMock(
            item_spacing=4,
            row_height=24,
            list_min_rows=1,
            list_max_rows=6,
            list_padding=6,
        )
        frame = MagicMock(collapsed=True)
        frame.__enter__.return_value = frame
        builder.add_frame.return_value = frame
        stack = MagicMock()
        stack.__enter__.return_value = stack
        factory = PluginPropertyWidgetFactory(builder)

        with (
            patch(f"{Paths.MODULE_ID}.scripts.preferences.plugin.factory.omni.ui") as ui_mock,
            patch.object(Settings, "get_mdl_catalog_modules", side_effect=[["first"], ["second"]]),
        ):
            ui_mock.VStack.return_value = stack
            factory._build_mdl_modules("mdl", {"key": "modules", "description": "Modules"})
            frame.collapsed = False

            factory._refresh_mdl_modules("mdl:modules")

        builder.add_frame.assert_called_once_with("Modules")
        self.assertFalse(frame.collapsed)
        self.assertEqual(stack.clear.call_count, 2)

    async def test_list_add_remove_dedupe_refresh(self) -> None:
        """List handling should dedupe, update settings, and defer UI rebuilds."""
        builder = MagicMock()
        builder.schedule_refresh = MagicMock()
        factory = PluginPropertyWidgetFactory(builder)
        factory._list_stacks["test:items"] = {
            "stack": MagicMock(),
            "plugin": "test_plugin",
            "prop": {"key": "items", "default": []},
        }
        model = MagicMock()
        model.get_value_as_string.return_value = " Value "

        with patch.object(factory, "_refresh_list_property", autospec=True) as refresh:
            Settings.set_plugin_property("test_plugin", "items", [])
            factory._on_add_list_item("test:items", model)
            self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), ["Value"])
            model.set_value.assert_called_with("")
            refresh.assert_not_called()
            builder.schedule_refresh.assert_called_once()

            builder.schedule_refresh.call_args.args[0]()
            refresh.assert_called_once_with("test:items")

            model.get_value_as_string.return_value = "value"
            factory._on_add_list_item("test:items", model)
            self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), ["Value"])

            factory._on_remove_list_item("test:items", "Value")
            self.assertEqual(Settings.get_plugin_property("test_plugin", "items", []), [])
            self.assertEqual(builder.schedule_refresh.call_count, 3)

    async def test_mdl_module_add_schedules_refresh(self) -> None:
        """MDL module adds should schedule a refresh and clear the model."""
        builder = MagicMock()
        builder.schedule_refresh = MagicMock()
        factory = PluginPropertyWidgetFactory(builder)
        factory._list_stacks["mdl:modules"] = {
            "stack": MagicMock(),
            "plugin": "mdl",
            "prop": {"key": "modules", "default": []},
            "kind": "mdl_modules",
        }
        model = MagicMock()
        model.get_value_as_string.return_value = "test.mdl"

        with (
            patch.object(Settings, "get_mdl_catalog_modules", autospec=True, return_value=[]),
            patch.object(Settings, "add_mdl_catalog_module", autospec=True),
            patch.object(factory, "_refresh_mdl_modules", autospec=True) as refresh,
        ):
            factory._on_add_list_item("mdl:modules", model)
            model.set_value.assert_called_with("")
            builder.schedule_refresh.assert_called()
            refresh.assert_not_called()

    async def test_unknown_property_type_logs_warning(self) -> None:
        """Unknown property types should warn."""
        builder = MagicMock()
        factory = PluginPropertyWidgetFactory(builder)
        with patch(
            f"{Paths.MODULE_ID}.scripts.preferences.plugin.factory.logger.warning",
            autospec=True,
        ) as log_warn:
            factory._build_property("test", {"key": "x", "type": "bogus"})
            log_warn.assert_called()

    async def test_missing_setting_key_logs_warning(self) -> None:
        """Missing setting keys should warn and skip widget creation."""
        builder = MagicMock()
        factory = PluginPropertyWidgetFactory(builder)
        with (
            patch.object(Settings, "get_plugin_property_key", autospec=True, return_value=None),
            patch(
                f"{Paths.MODULE_ID}.scripts.preferences.plugin.factory.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            factory._build_bool("test", {"key": "missing"})
            log_warn.assert_called()
