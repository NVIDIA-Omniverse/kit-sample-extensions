from typing import Collection, Optional

from omni.kit.browser.core import OptionMenuDescription, OptionsMenu
from omni.kit.browser.folder.core import FolderOptionsMenu

from .browser_folder import AssetFolder


class SimReadyFolderOptionsMenu(OptionsMenu):
    """
    Represent options menu used in SimReady browser.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Do not use default menu items
        self._menu_descs = []
        self.append_menu_item(
            OptionMenuDescription(
                "Refresh Assets",
                clicked_fn=self._on_refresh_asset_folder,
                visible_fn=self._is_refresh_asset_folder_visible,
                get_text_fn=self._get_menu_item_text,
            )
        )

    def destroy(self) -> None:
        super().destroy()

    def _on_refresh_asset_folder(self):
        self._browser_widget.model.refresh_current_asset_folder()

    def _is_refresh_asset_folder_visible(self) -> bool:
        return self._browser_widget.model.current_asset_folder is not None

    def _get_menu_item_text(self) -> str:
        folder: AssetFolder = self._browser_widget.model.current_asset_folder
        return (f"Refresh {folder.name}" if folder else "No Asset Folder") + "..."

    def set_add_collection_fn(self, on_add_collection_fn: callable) -> None:
        """Do not override "Refresh Assets" since "Add Collection" is removed"""
        pass
