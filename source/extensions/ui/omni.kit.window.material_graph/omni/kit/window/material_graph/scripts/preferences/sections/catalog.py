"""Implement material graph extension logic for `preferences/sections/catalog.py`."""

from typing import Any, Optional

import carb.settings

# pylint: disable=no-member
import omni.ui
from omni.kit.widget.filebrowser import FileBrowserItem
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.window.popup_dialog import MessageDialog
from omni.kit.window.preferences import SettingType

from ...settings.settings import Settings
from ...settings.utils import CATALOG_TEXTURE_ICON_SIZE_DEFAULT, CATALOG_TEXTURES_PATH_DEFAULT, is_existing_path
from ..core.constants import BUTTON_WIDTH
from ..ui.lists import build_path_list


class CatalogSettingsSection:
    """Builds the Catalog Settings preferences section."""

    def __init__(self, builder) -> None:
        """Initialize instance state for this material graph component."""

        self._builder = builder
        self._compound_path_stack: Optional[Any] = None
        self._pick_folder_dialog: Optional[FilePickerDialog] = None
        self._selected_folder: Optional[str] = None

    def build(self) -> None:
        """Execute build behavior for material graph workflows."""

        settings = carb.settings.get_settings()
        value = settings.get(Settings.CATALOG_TEXTURES_PATH)
        if value is None or (isinstance(value, str) and "${" in value):
            settings.set_string(Settings.CATALOG_TEXTURES_PATH, CATALOG_TEXTURES_PATH_DEFAULT)
        icon_size = settings.get(Settings.CATALOG_TEXTURE_ICON_SIZE)
        if icon_size is None:
            settings.set_int(Settings.CATALOG_TEXTURE_ICON_SIZE, CATALOG_TEXTURE_ICON_SIZE_DEFAULT)

        with self._builder.add_frame("Catalog Settings"):
            with self._builder.indented_stack():
                self._builder.create_setting_widget(
                    "Textures Path",
                    Settings.CATALOG_TEXTURES_PATH,
                    SettingType.ASSET,
                    tooltip="Directory used to load and store texture metadata/icons.",
                )
                self._builder.create_setting_widget(
                    "Show Catalog",
                    Settings.SHOW_CATALOG,
                    SettingType.BOOL,
                    tooltip="Show or hide the catalog panel in the graph widget.",
                )
                self._build_icon_size_dropdown()

                with self._builder.add_frame("Compound Folders"):
                    self._compound_path_stack = omni.ui.VStack(height=0)
                    with self._compound_path_stack:
                        self._build_compound_paths_frame()

    def on_compound_paths_changed(self, *_args) -> None:
        """Execute on compound paths changed behavior for material graph workflows."""

        self._builder.schedule_refresh(self.refresh_compound_path_list)

    def refresh_compound_path_list(self) -> None:
        """Execute refresh compound path list behavior for material graph workflows."""

        if not self._compound_path_stack:
            return
        self._compound_path_stack.clear()
        with self._compound_path_stack:
            self._build_compound_paths_frame()

    def _build_compound_paths_frame(self) -> None:
        """Execute build compound paths frame behavior for material graph workflows."""

        with omni.ui.VStack(height=0, spacing=self._builder.item_spacing):
            with omni.ui.HStack(height=self._builder.row_height):
                omni.ui.Button(
                    "Add Folder",
                    clicked_fn=self.pick_compound_path,
                    height=self._builder.row_height,
                    width=BUTTON_WIDTH,
                )

            omni.ui.Spacer(height=self._builder.item_spacing)
            build_path_list(self._builder, Settings.get_compound_paths(), self._on_remove_compound_path)

    def _build_icon_size_dropdown(self) -> None:
        """Execute build icon size dropdown behavior for material graph workflows."""

        sizes = [64, 128, 256, 512, 1024]
        tooltip = "Icon size (pixels) used for catalog texture previews."
        label = "Catalog Texture Icon Size"

        combo_widget = self._builder.create_setting_widget_combo(
            label, Settings.CATALOG_TEXTURE_ICON_SIZE, sizes, setting_is_index=False
        )
        if combo_widget:
            combo_widget.tooltip = tooltip

    def pick_compound_path(self) -> None:
        """Open a folder picker for adding a compound search path."""
        if self._pick_folder_dialog:
            self._pick_folder_dialog.destroy()
        self._selected_folder = None

        self._pick_folder_dialog = FilePickerDialog(
            "Pick Compounds Folder",
            apply_button_label="Use This Folder",
            selection_changed_fn=self._on_selection_changed,
            click_apply_handler=self._on_apply_folder,
            item_filter_options=["All Folders (*)"],
            item_filter_fn=self._on_filter_folder,
        )

    @staticmethod
    def _on_filter_folder(item: FileBrowserItem) -> bool:
        """Hide files in the folder picker."""
        return item.is_folder

    def _on_selection_changed(self, items: object) -> None:
        """Track the selected folder path."""
        self._selected_folder = items[0].path if items else None

    def _on_apply_folder(self, _filename: str, directory: str) -> None:
        """Add the selected folder to compound paths."""
        path = self._selected_folder if self._selected_folder else directory
        if not path:
            self._selected_folder = None
            return
        if not is_existing_path(path):
            MessageDialog(
                title="Invalid Compound Folder", message=f"Folder does not exist:\n{path}", ok_label="OK"
            ).show()
            return
        if self._pick_folder_dialog:
            self._pick_folder_dialog.hide()
        Settings.add_compound_path(path)
        self._selected_folder = None
        self._builder.schedule_refresh(self.refresh_compound_path_list)

    def _on_remove_compound_path(self, path: str) -> None:
        """Execute on remove compound path behavior for material graph workflows."""

        Settings.remove_compound_path(path)
        self._builder.schedule_refresh(self.refresh_compound_path_list)

    def destroy(self) -> None:
        """Destroy any active folder picker dialog."""
        if self._pick_folder_dialog:
            self._pick_folder_dialog.destroy()
            self._pick_folder_dialog = None
        self._selected_folder = None
