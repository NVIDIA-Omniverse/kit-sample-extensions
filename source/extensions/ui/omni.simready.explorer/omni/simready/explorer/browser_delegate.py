# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Optional

import omni.ui as ui
from omni.kit.browser.folder.core import FolderDetailDelegate

from .browser_model import AssetDetailItem, SimReadyBrowserModel
from .context_menu import ContextMenu
from .style import ICON_PATH
from .viewport_drop_delegate import SimReadyDragDropObject


class SimReadyDetailDelegate(FolderDetailDelegate):
    """
    Delegate to show SimReady asset item in detail view
    (where the list of thumbnails is shown)
    Args:
        model (SimReadyBrowserModel): Asset browser model
    """

    def __init__(self, model: SimReadyBrowserModel):
        super().__init__(model=model)

        # Context menu for detail item
        self._context_menu: Optional[ContextMenu] = None

        # Drop helper to handle dropping in viewport (only works for VP2)
        self._drop_helper = SimReadyDragDropObject()

    def destroy(self):
        self._drop_helper = None
        if self._context_menu:
            self._context_menu.destroy()
            self._context_menu = None
        super().destroy()

    def get_thumbnail(self, item: AssetDetailItem) -> str:
        """Set default thumbnail if thumbnail is None"""
        return item.thumbnail or f"{ICON_PATH}/usd_stage_256.png"

    def get_tooltip(self, item: AssetDetailItem) -> Optional[str]:
        """No tooltip for detail item as it interferes with the right-click menu"""
        return None

    def on_drag(self, item: AssetDetailItem) -> str:
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

    def on_multiple_drag(self, item: AssetDetailItem) -> str:
        """Could be dragged to viewport window"""
        thumbnail = self.get_thumbnail(item)
        icon_size = 32
        with ui.HStack(height=icon_size):
            if thumbnail:
                ui.ImageWithProvider(thumbnail, width=icon_size, height=icon_size)
                ui.Spacer(width=8)
            ui.Label(item.name, style_type_name_override="GridView.Item")

        return self._model.get_drag_mime_data(item)

    def on_right_click(self, item: AssetDetailItem) -> None:
        """Show context menu"""
        if self._context_menu is None:
            self._context_menu = ContextMenu()

        self._context_menu.show_item(item)

    def build_widget(
        self, model: ui.AbstractItemModel, item: AssetDetailItem, index: int = 0, level: int = 0, expand: bool = False
    ):
        super().build_widget(model, item, index=index, level=level, expand=expand)
        tooltip = self.get_tooltip(item)
        if tooltip is not None:
            self._cached_thumbnail_widgets[item].set_tooltip(tooltip)

    def build_thumbnail(self, item: AssetDetailItem) -> Optional[ui.Image]:
        """
        Display thumbnail per detail item
        Args:
            item (DetailItem): detail item to display
        """
        with ui.ZStack():
            thumbnail_image = ui.Image(
                self.get_thumbnail(item), fill_policy=ui.FillPolicy.STRETCH, style_type_name_override="GridView.Image"
            )
            # Badge to indicate item physics ON, need to change visibility if physics status changed
            badge_container = ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM, visible=item.physics != "None")
            with badge_container:
                ui.Spacer(width=ui.Percent(80))
                with ui.VStack():
                    ui.Spacer(height=2)
                    ui.ImageWithProvider(
                        fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                        alignment=ui.Alignment.LEFT,
                        style_type_name_override="GridView.Item.Badge.Image",
                    )

            badge_container.visible = item.physics != "None"
            if item.physics_model:
                item.physics_model.current_index.add_value_changed_fn(
                    lambda m, w=badge_container: self.__on_item_physics_changed(m, w)
                )

        return thumbnail_image  # noqa: R504

    def __on_item_physics_changed(self, model: ui.SimpleIntModel, badge_widget: ui.Widget) -> None:
        badge_widget.visible = model.as_int != 0
