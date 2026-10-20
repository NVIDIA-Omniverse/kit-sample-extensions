# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Optional

import omni.ui as ui
from omni.kit.browser.folder.core import FolderDetailDelegate

from .browser_model import WrappAssetDetailItem, WrappBrowserModel
from .context_menu import ContextMenu
from .style import ICON_PATH
from .viewport_drop_delegate import WrappDragDropObject


class WrappDetailDelegate(FolderDetailDelegate):
    """Delegate for displaying WRAPP asset details in the browser view.
    (where the list of thumbnails is shown)

    Handles the presentation of asset information and interaction with the viewport.
    Manages thumbnail display, property editing, and drag-drop operations.

    Args:
        model (WrappBrowserModel): The browser model managing the assets

    Attributes:
        _drop_helper (WrappDragDropObject): Helper for handling viewport drag-drop
        _context_menu (ContextMenu): Menu shown on right-click
    """

    def __init__(self, model: WrappBrowserModel):
        super().__init__(model=model)
        # Context menu for detail item
        self._context_menu: Optional[ContextMenu] = None
        # Drop helper to handle dropping in viewport (only works for VP2)
        self._drop_helper = WrappDragDropObject()

    def get_thumbnail(self, item: WrappAssetDetailItem) -> str:
        """Set default thumbnail if thumbnail is None"""
        return item.thumbnail or f"{ICON_PATH}/usd_stage_256.png"

    def get_tooltip(self, item: WrappAssetDetailItem) -> Optional[str]:
        """No tooltip for detail item as it interferes with the right-click menu"""
        return None

    def destroy(self):
        self._drop_helper = None
        if self._context_menu:
            self._context_menu.destroy()
            self._context_menu = None
        super().destroy()

    def on_right_click(self, item: WrappAssetDetailItem) -> None:
        """Show context menu"""
        if self._context_menu is None:
            self._context_menu = ContextMenu()

        self._context_menu.show_item(item)

    def on_drag(self, item: WrappAssetDetailItem) -> str:
        """Could be dragged to viewport window"""
        thumbnail = self.get_thumbnail(item)
        icon_size = 128
        with ui.VStack(width=icon_size):
            if thumbnail:
                ui.Spacer(height=2)
                with ui.HStack():
                    ui.Spacer()
                    ui.ImageWithProvider(thumbnail, width=icon_size, height=icon_size)
                    ui.Spacer()
            ui.Label(
                item.name,
                word_wrap=False,
                elided_text=True,
                skip_draw_when_clipped=True,
                alignment=ui.Alignment.TOP,
                style_type_name_override="GridView.Item",
            )

        return self._model.get_drag_mime_data(item)

    def on_multiple_drag(self, item: WrappAssetDetailItem) -> str:
        """Could be dragged to viewport window"""
        thumbnail = self.get_thumbnail(item)
        icon_size = 32
        with ui.HStack(height=icon_size):
            if thumbnail:
                ui.ImageWithProvider(thumbnail, width=icon_size, height=icon_size)
                ui.Spacer(width=8)
            ui.Label(item.name, style_type_name_override="GridView.Item")

        return self._model.get_drag_mime_data(item)

    def build_widget(
        self,
        model: ui.AbstractItemModel,
        item: WrappAssetDetailItem,
        index: int = 0,
        level: int = 0,
        expand: bool = False,
    ):
        super().build_widget(model, item, index=index, level=level, expand=expand)
        tooltip = self.get_tooltip(item)
        if tooltip is not None:
            self._cached_thumbnail_widgets[item].set_tooltip(tooltip)

    def build_thumbnail(self, item: WrappAssetDetailItem) -> Optional[ui.Image]:
        """
        Display thumbnail per detail item
        Args:
            item (DetailItem): detail item to display
        """
        with ui.ZStack():
            thumbnail_image = ui.Image(
                self.get_thumbnail(item), fill_policy=ui.FillPolicy.STRETCH, style_type_name_override="GridView.Image"
            )
            # Badge is not used in WRAPP asset currently
            badge_container = ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM, visible=False)
            with badge_container:
                ui.Spacer(width=ui.Percent(80))
                with ui.VStack():
                    ui.Spacer(height=2)
                    ui.ImageWithProvider(
                        fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                        alignment=ui.Alignment.LEFT,
                        style_type_name_override="GridView.Item.Badge.Image",
                    )

        return thumbnail_image  # noqa: R504


class DetailListViewDelegate(ui.AbstractItemDelegate):
    """
    Delegate for displaying detail items in a list view (table format).
    Shows item name with an icon in a compact row format.
    Supports drag-and-drop at the widget level with custom selection handling.
    """

    def __init__(self, detail_delegate, browser_model=None, tree_view=None):
        super().__init__()
        self._detail_delegate = detail_delegate
        self._browser_model = browser_model
        self._tree_view = tree_view
        self._mouse_pressed_item = None  # Track which item was pressed for mouse release

    def destroy(self):
        self._detail_delegate = None
        self._browser_model = None
        self._tree_view = None
        self._mouse_pressed_item = None

    def build_header(self, column_id: int):
        """Build header for the list view columns."""
        if column_id == 0:
            with ui.HStack():
                ui.Spacer(width=4)
                ui.Label("Name", style_type_name_override="TreeView.Header")

    def build_branch(
        self,
        model: ui.AbstractItemModel,
        item,
        column_id: int,
        level: int,
        expanded: bool,
    ):
        """No branches for flat list view."""
        pass

    def build_widget(
        self,
        model: ui.AbstractItemModel,
        item,
        column_id: int,
        level: int,
        expanded: bool,
    ):
        """Build a row widget for each detail item."""
        if item is None:
            return

        if column_id == 0:
            with ui.HStack(height=24):
                ui.Spacer(width=4)
                # Show thumbnail as small icon
                thumbnail = None
                if self._detail_delegate:
                    try:
                        thumbnail = self._detail_delegate.get_thumbnail(item)
                    except Exception:
                        thumbnail = None
                if thumbnail:
                    image_widget = ui.ImageWithProvider(
                        thumbnail,
                        width=20,
                        height=20,
                        style_type_name_override="TreeView.Icon",
                    )
                    # Set drag, mouse press, and mouse release handlers
                    image_widget.set_drag_fn(lambda item=item: self._on_drag(item))
                    image_widget.set_mouse_pressed_fn(
                        lambda x, y, btn, mod, item=item: self._on_mouse_pressed(btn, mod, item)
                    )
                    image_widget.set_mouse_released_fn(
                        lambda x, y, btn, mod, item=item: self._on_mouse_released(btn, mod, item)
                    )
                    ui.Spacer(width=6)
                # Item name
                item_name = getattr(item, "name", str(item))
                name_widget = ui.Label(
                    item_name,
                    alignment=ui.Alignment.LEFT_CENTER,
                    style_type_name_override="TreeView.Item.Name",
                )
                # Set drag, mouse press, and mouse release handlers
                name_widget.set_drag_fn(lambda item=item: self._on_drag(item))
                name_widget.set_mouse_pressed_fn(
                    lambda x, y, btn, mod, item=item: self._on_mouse_pressed(btn, mod, item)
                )
                name_widget.set_mouse_released_fn(
                    lambda x, y, btn, mod, item=item: self._on_mouse_released(btn, mod, item)
                )

    def _on_mouse_pressed(self, button: int, modifier: int, item) -> None:
        """Handle mouse press on list view item for manual selection.

        Args:
            button: Mouse button (0=left, 1=right, 2=middle)
            modifier: Keyboard modifier flags (1=Shift, 2=Ctrl/Cmd)
            item: The item that was clicked
        """
        if not self._tree_view:
            return

        # Get current selection
        current_selection = list(self._tree_view.selection) if self._tree_view.selection else []

        # Right mouse button - ensure clicked item is selected for context menu
        if button == 1:
            # If right-clicking on an unselected item, select only that item
            if item not in current_selection:
                self._tree_view.selection = [item]
            return

        # Left mouse button
        elif button == 0:
            # Track which item was pressed (for mouse release handling)
            self._mouse_pressed_item = item

            # Check modifier keys for multi-selection
            shift_pressed = (modifier & 1) != 0
            ctrl_pressed = (modifier & 2) != 0

            if shift_pressed and current_selection:
                # Shift+Click: Range selection from last selected item to clicked item
                model = self._tree_view.model
                if model:
                    all_items = model.get_item_children(None) or []

                    # Find indices of the last selected item and clicked item
                    last_selected = current_selection[-1] if current_selection else None
                    try:
                        last_idx = all_items.index(last_selected) if last_selected else -1
                        clicked_idx = all_items.index(item)

                        # Determine range (handle both forward and backward selection)
                        start_idx = min(last_idx, clicked_idx)
                        end_idx = max(last_idx, clicked_idx)

                        # Add all items in range to selection
                        for i in range(start_idx, end_idx + 1):
                            if all_items[i] not in current_selection:
                                current_selection.append(all_items[i])
                    except (ValueError, IndexError):
                        # If item not found, just add it
                        if item not in current_selection:
                            current_selection.append(item)
                # For shift-click, update selection immediately
                self._tree_view.selection = current_selection
            elif ctrl_pressed:
                # Ctrl+Click: Toggle item in selection
                if item in current_selection:
                    current_selection.remove(item)
                else:
                    current_selection.append(item)
                # For ctrl-click, update selection immediately
                self._tree_view.selection = current_selection
            else:
                # Regular click (no modifiers):
                if item not in current_selection:
                    # Clicking on unselected item - select it immediately
                    self._tree_view.selection = [item]
                # else: clicking on already-selected item
                # Keep current selection for now (for potential drag-and-drop)
                # Will update on mouse release if user didn't drag

    def _on_mouse_released(self, button: int, modifier: int, item) -> None:
        """Handle mouse release on list view item.

        If releasing on the same item that was pressed (without modifiers),
        select only that item. This allows click-and-release to select a single item
        from a multi-selection, while click-and-drag keeps the multi-selection.

        Args:
            button: Mouse button (0=left, 1=right, 2=middle)
            modifier: Keyboard modifier flags (1=Shift, 2=Ctrl/Cmd)
            item: The item that was released on
        """
        if self._tree_view is None:
            return

        # Only handle left mouse button releases
        if button == 0:
            # Check if we released on the same item we pressed (no modifiers)
            shift_pressed = (modifier & 1) != 0
            ctrl_pressed = (modifier & 2) != 0

            # If no modifiers and releasing on the same item that was pressed
            if not shift_pressed and not ctrl_pressed and item == self._mouse_pressed_item:
                self._tree_view.selection = [item]

        # Clear pressed item tracker
        self._mouse_pressed_item = None

    def _on_drag(self, item) -> str:
        """Handle drag from list view item - returns mime data for drag-and-drop.

        Supports both single and multiple item drag-and-drop.
        Combines multiple items' mime data with newlines (same as grid view).
        """
        if not self._browser_model:
            return ""

        # Check if dragging multiple items
        current_selection = list(self._tree_view.selection) if self._tree_view and self._tree_view.selection else []
        is_multiple = len(current_selection) > 1 and item in current_selection

        # Build drag preview UI
        thumbnail = None
        if self._detail_delegate:
            try:
                thumbnail = self._detail_delegate.get_thumbnail(item)
            except Exception:
                thumbnail = None

        if is_multiple:
            # Multiple items: compact preview (small icon + name + count)
            icon_size = 32
            with ui.HStack(height=icon_size):
                if thumbnail:
                    ui.ImageWithProvider(thumbnail, width=icon_size, height=icon_size)
                    ui.Spacer(width=8)
                ui.Label(
                    f"{getattr(item, 'name', str(item))} (+{len(current_selection)-1} more)",
                    style_type_name_override="GridView.Item",
                )

            # Combine mime data from all selected items (same format as grid view)
            drag_mime_datas = []
            for selected_item in current_selection:
                mime_data = self._browser_model.get_drag_mime_data(selected_item)
                if mime_data:
                    drag_mime_datas.append(mime_data)
            return "\n".join(drag_mime_datas)
        else:
            # Single item: larger preview
            icon_size = 128
            with ui.VStack(width=icon_size):
                if thumbnail:
                    ui.Spacer(height=2)
                    with ui.HStack():
                        ui.Spacer()
                        ui.ImageWithProvider(thumbnail, width=icon_size, height=icon_size)
                        ui.Spacer()
                ui.Label(
                    getattr(item, "name", str(item)),
                    word_wrap=False,
                    elided_text=True,
                    skip_draw_when_clipped=True,
                    alignment=ui.Alignment.TOP,
                    style_type_name_override="GridView.Item",
                )

            # Return single item mime data
            return self._browser_model.get_drag_mime_data(item)
