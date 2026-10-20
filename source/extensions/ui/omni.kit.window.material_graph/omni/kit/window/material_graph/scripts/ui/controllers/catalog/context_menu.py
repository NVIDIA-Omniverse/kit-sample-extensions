"""Catalog context-menu controller for import/export and registry management actions."""

import omni.client
import omni.ui
from omni.kit.widget.filebrowser import FileBrowserItem
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.window.popup_dialog import InputDialog

from ....models.catalog.registries.compound import get_compound_registry
from ....models.catalog.registries.texture import get_texture_registry
from ....settings.settings import Settings
from ...interaction.menu_utils import show_menu_at_cursor
from ...sections.catalog.constants import CATALOG_TAB_NODEGRAPHS, CATALOG_TAB_TEXTURES

# pylint: disable=no-member


class CatalogContextMenuController:
    """Controls the catalog context menu entries."""

    def __init__(self, widget: object) -> None:
        """Initialize controller-owned state, callback wiring, and runtime dependencies."""
        self._widget = widget
        self._menu = None
        self._pick_folder_dialog = None
        self._selected_folder = None
        self._active_tab = None

    def show_menu(self, items: object) -> None:
        """Show the catalog context menu."""
        if self._widget and getattr(self._widget, "_catalog_widget", None):
            self._active_tab = self._widget._catalog_widget.get_active_tab()
        if self._active_tab not in (CATALOG_TAB_TEXTURES, CATALOG_TAB_NODEGRAPHS):
            if self._menu:
                self._menu.hide()
            return
        if self._menu:
            self._menu.hide()
        self._menu = omni.ui.Menu("Catalog Context Menu")
        with self._menu:
            if self._active_tab == CATALOG_TAB_TEXTURES:
                omni.ui.MenuItem("New Group", triggered_fn=self.create_group)
            elif self._active_tab == CATALOG_TAB_NODEGRAPHS:
                omni.ui.MenuItem("New Group", triggered_fn=self.create_group)
                omni.ui.MenuItem("Refresh Compounds", triggered_fn=self.refresh_compounds)
                omni.ui.MenuItem("Add Compounds Directory", triggered_fn=self.pick_folder)
                omni.ui.MenuItem("Clear Compounds Directories", triggered_fn=self.clear_compound_dirs)
        show_menu_at_cursor(self._menu)

    def refresh_compounds(self) -> None:
        """Refresh compounds and catalog view."""
        if self._widget and getattr(self._widget, "catalog_model", None):
            self._widget.catalog_model.refresh_compounds()

    def clear_compound_dirs(self) -> None:
        """Clear compound directories and refresh."""
        Settings.clear_compound_paths()
        self.refresh_compounds()

    def create_group(self) -> None:
        """Create a new texture or compound group."""

        def _apply(dialog: InputDialog) -> None:
            """Apply group creation after validating user input."""
            new_name = dialog.get_value()
            if isinstance(new_name, str) and new_name.strip():
                if self._active_tab == CATALOG_TAB_NODEGRAPHS:
                    get_compound_registry().create_group(new_name.strip())
                else:
                    get_texture_registry().create_group(new_name.strip())
            dialog.hide()

        dialog = InputDialog(
            title="New Group",
            width=300,
            message="Group name:",
            ok_handler=_apply,
        )
        dialog.show()

    def pick_folder(self) -> None:
        """Open a folder picker dialog to add compounds."""
        if self._pick_folder_dialog:
            self._pick_folder_dialog.destroy()

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
        """Hide files in the pick folder dialog."""
        return item.is_folder

    def _on_selection_changed(self, items: object) -> None:
        """Track currently selected folder path from picker selection events."""
        if items:
            self._selected_folder = items[0].path

    def _on_apply_folder(self, _filename: str, dir: str) -> None:
        """Handle folder selection in the picker dialog."""
        path = omni.client.combine_urls(dir, self._selected_folder or "")
        if self._pick_folder_dialog:
            self._pick_folder_dialog.hide()
        if not path:
            return
        Settings.add_compound_path(path)
        self.refresh_compounds()

    def destroy(self) -> None:
        """Release menu callbacks and cached menu state owned by this controller."""
        self._menu = None
        if self._pick_folder_dialog:
            self._pick_folder_dialog.destroy()
            self._pick_folder_dialog = None
        self._selected_folder = None
        self._widget = None
