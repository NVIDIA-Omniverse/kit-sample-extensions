# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import omni.ui as ui
from omni.kit.browser.folder.core import FolderCategoryDelegate

from .style import CONTEXT_MENU_STYLE


class ContextMenu(ui.Menu):  # pragma: no cover - never called
    """
    Context menu for Wrapp Package category item right click.
    """

    def __init__(self):
        super().__init__("Wrapp Package category menu", style=CONTEXT_MENU_STYLE)
        self.item = None
        with self:
            ui.MenuItem(f"{ui.get_custom_glyph_code('${glyphs}/sync.svg')}  Reload", triggered_fn=self._reload)

    def _reload(self):
        if hasattr(self.item, "folder"):
            self.item.folder.reload()

    def show_menu(self):
        # TODO: Need to handle all sub folders
        if hasattr(self.item, "folder") and self.item.folder.name == "Installed":
            self.show()


class WrappPackageCategoryDelegate(FolderCategoryDelegate):
    def build_widget(
        self, model: ui.AbstractItemModel, item: "CategoryItem", index: int = 0, level: int = 0, expanded: bool = False
    ):
        """Create a widget per category item

        Args:
            model (ui.AbstractItemModel): Category data model.
            item (CategoryItem): Category item.
            index (int): ignore.
            level (int): ignore.
            expanded (bool): ignore.
        """
        tooltip = ""
        try:
            if hasattr(item, "source_folders"):
                tooltip = "\n".join([folder.url for folder in item.source_folders])
            else:
                tooltip = item.folder.url
        except Exception:
            pass

        # We just wrapp the category label with a HStack to get the tooltip
        with ui.HStack(tooltip=tooltip):
            super().build_widget(model, item, index, level, expanded)

    def _on_item_right_click(self, item):  # pragma: no cover - never called
        """Show category item's menu"""
        if self._context_menu is None:
            self._context_menu = ContextMenu()
        if self._context_menu:
            self._context_menu.item = item
            self._context_menu.show_menu()
