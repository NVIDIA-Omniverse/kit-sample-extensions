# pylint: disable=relative-beyond-top-level
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ...scripts.config.paths import Paths
from ...scripts.ui.controllers.catalog import context_menu as context_menu_module
from ...scripts.ui.controllers.catalog.context_menu import CatalogContextMenuController
from ...scripts.ui.sections.catalog.constants import CATALOG_TAB_NODEGRAPHS, CATALOG_TAB_TEXTURES
from ..base import MaterialGraphTestBase


class TestCatalogContextMenuController(MaterialGraphTestBase):
    """Catalog context menu actions."""

    async def test_refresh_compounds_calls_catalog_model(self) -> None:
        """Refresh should call the catalog model's refresh method."""
        widget = MagicMock()
        widget.catalog_model = MagicMock()
        controller = CatalogContextMenuController(widget)

        controller.refresh_compounds()

        widget.catalog_model.refresh_compounds.assert_called_once()

    async def test_clear_compounds_calls_settings_and_refresh(self) -> None:
        """Clear should reset compound paths and refresh the catalog."""
        widget = MagicMock()
        widget.catalog_model = MagicMock()
        controller = CatalogContextMenuController(widget)

        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.catalog.context_menu.Settings.clear_compound_paths",
            autospec=True,
        ) as clear_paths:
            controller.clear_compound_dirs()

        clear_paths.assert_called_once()
        widget.catalog_model.refresh_compounds.assert_called_once()

    async def test_show_menu_tracks_active_tab_and_builds_available_actions(self) -> None:
        """Build only valid actions and replace event-owned menus safely."""

        class _Menu:
            def __init__(self) -> None:
                self.hide = MagicMock()

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

        active_tab = MagicMock(return_value=CATALOG_TAB_TEXTURES)
        widget = SimpleNamespace(_catalog_widget=SimpleNamespace(get_active_tab=active_tab))
        controller = CatalogContextMenuController(widget)
        menus = [_Menu(), _Menu()]
        labels = []

        with (
            patch.object(context_menu_module.omni.ui, "Menu", side_effect=menus) as menu_factory,
            patch.object(
                context_menu_module.omni.ui,
                "MenuItem",
                side_effect=lambda label, **_kwargs: labels.append(label),
            ),
            patch.object(context_menu_module, "show_menu_at_cursor") as show_menu,
        ):
            controller.show_menu([])
            self.assertEqual(labels, ["New Group"])
            show_menu.assert_called_once_with(menus[0])

            labels.clear()
            show_menu.reset_mock()
            active_tab.return_value = CATALOG_TAB_NODEGRAPHS
            controller.show_menu([])

        self.assertEqual(menu_factory.call_count, 2)
        menus[0].hide.assert_called_once_with()
        menus[1].hide.assert_not_called()
        self.assertEqual(
            labels,
            [
                "New Group",
                "Refresh Compounds",
                "Add Compounds Directory",
                "Clear Compounds Directories",
            ],
        )
        show_menu.assert_called_once_with(menus[1])

    async def test_show_menu_ignores_tabs_without_registry_actions(self) -> None:
        """Do not display an empty context menu and hide a stale menu on shader tabs."""

        menu = MagicMock()
        widget = SimpleNamespace(_catalog_widget=SimpleNamespace(get_active_tab=MagicMock(return_value="Shaders")))
        controller = CatalogContextMenuController(widget)
        controller._menu = menu
        with (
            patch.object(context_menu_module.omni.ui, "Menu") as menu_factory,
            patch.object(context_menu_module, "show_menu_at_cursor") as show_menu,
        ):
            controller.show_menu([])
        menu.hide.assert_called_once_with()
        menu_factory.assert_not_called()
        show_menu.assert_not_called()

    async def test_create_group_trims_names_and_routes_to_active_registry(self) -> None:
        """Validate dialog input and create groups in the selected registry only."""

        class _Dialog:
            def __init__(self, *_args, ok_handler, **_kwargs) -> None:
                self.ok_handler = ok_handler
                self.value = ""
                self.show = MagicMock()
                self.hide = MagicMock()

            def get_value(self):
                return self.value

        widget = SimpleNamespace()
        controller = CatalogContextMenuController(widget)
        dialogs = []

        def _make_dialog(*args, **kwargs):
            dialog = _Dialog(*args, **kwargs)
            dialogs.append(dialog)
            return dialog

        compound_registry = MagicMock()
        texture_registry = MagicMock()
        with (
            patch.object(context_menu_module, "InputDialog", side_effect=_make_dialog),
            patch.object(context_menu_module, "get_compound_registry", return_value=compound_registry),
            patch.object(context_menu_module, "get_texture_registry", return_value=texture_registry),
        ):
            controller._active_tab = CATALOG_TAB_NODEGRAPHS
            controller.create_group()
            dialogs[-1].value = "  Compounds  "
            dialogs[-1].ok_handler(dialogs[-1])

            controller._active_tab = CATALOG_TAB_TEXTURES
            controller.create_group()
            dialogs[-1].value = " Textures "
            dialogs[-1].ok_handler(dialogs[-1])

            controller.create_group()
            dialogs[-1].value = "   "
            dialogs[-1].ok_handler(dialogs[-1])

        compound_registry.create_group.assert_called_once_with("Compounds")
        texture_registry.create_group.assert_called_once_with("Textures")
        self.assertEqual([dialog.show.call_count for dialog in dialogs], [1, 1, 1])
        self.assertEqual([dialog.hide.call_count for dialog in dialogs], [1, 1, 1])

    async def test_folder_picker_applies_selection_and_destroy_releases_dialog(self) -> None:
        """Replace stale pickers, accept folders, refresh, and clean up deterministically."""

        class _Picker:
            def __init__(self, *_args, **kwargs) -> None:
                self.callbacks = kwargs
                self.hide = MagicMock()
                self.destroy = MagicMock()

        widget = SimpleNamespace(catalog_model=SimpleNamespace(refresh_compounds=MagicMock()))
        controller = CatalogContextMenuController(widget)
        stale_picker = MagicMock()
        controller._pick_folder_dialog = stale_picker
        pickers = []

        def _make_picker(*args, **kwargs):
            picker = _Picker(*args, **kwargs)
            pickers.append(picker)
            return picker

        with (
            patch.object(context_menu_module, "FilePickerDialog", side_effect=_make_picker),
            patch.object(
                context_menu_module.omni.client, "combine_urls", return_value="omniverse://compounds"
            ) as combine,
            patch.object(context_menu_module.Settings, "add_compound_path") as add_path,
        ):
            controller.pick_folder()
            picker = pickers[0]
            picker.callbacks["selection_changed_fn"]([SimpleNamespace(path="library")])
            self.assertTrue(picker.callbacks["item_filter_fn"](SimpleNamespace(is_folder=True)))
            self.assertFalse(picker.callbacks["item_filter_fn"](SimpleNamespace(is_folder=False)))
            picker.callbacks["click_apply_handler"]("ignored", "omniverse://server")

        stale_picker.destroy.assert_called_once()
        combine.assert_called_once_with("omniverse://server", "library")
        picker.hide.assert_called_once()
        add_path.assert_called_once_with("omniverse://compounds")
        widget.catalog_model.refresh_compounds.assert_called_once()

        controller.destroy()
        picker.destroy.assert_called_once()
        self.assertIsNone(controller._pick_folder_dialog)
        self.assertIsNone(controller._selected_folder)
        self.assertIsNone(controller._widget)
