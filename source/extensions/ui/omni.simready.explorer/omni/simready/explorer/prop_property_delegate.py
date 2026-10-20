# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
from typing import List, Optional

import omni.kit.app
import omni.ui as ui
from omni.kit.browser.core import TreeBrowserWidget

from .asset import AssetType
from .browser_model import AssetDetailItem
from .browser_property_delegate import BrowserPropertyDelegate
from .property_widgets import *


class PropAssetPropertyDelegate(BrowserPropertyDelegate):
    """
    A delegate to show properties of assets of type Prop.
    """

    def accepted(self, item: Optional[AssetDetailItem]) -> bool:
        """BrowserPropertyDelegate method override"""
        return item and item.asset.asset_type == AssetType.PROP

    def show(self, item: Optional[AssetDetailItem], frame: ui.Frame) -> None:
        """BrowserPropertyDelegate method override"""
        if item is None:
            return
        asset = item.asset
        self._item = item
        if hasattr(self, "_container"):
            self._container.visible = True
            self._name_label.text = asset.name
            self._qcode_value.text = asset.qcode
            self._dimensions_value.text = asset.extent_as_str
            if hasattr(self, "h_buttons"):
                self._h_hstack.clear()

            with self._h_hstack:
                self._build_hierarchy_links()
            self._thumbnail_img.source_url = asset.thumbnail
            self._physx_combobox.model = item.physics_model
            self._tags_field.tags = asset.tags

            async def __delay_show_physics():
                # Delay to show badge to make display correct
                if item.physics_model:
                    await omni.kit.app.get_app().next_update_async()
                    self._badge_container.visible = item.physics_model.current_index.as_int != 0
                    self._sub_physics = None
                    self._sub_physics = item.physics_model.current_index.subscribe_value_changed_fn(
                        self.__on_item_physics_changed
                    )

            asyncio.ensure_future(__delay_show_physics())
        else:
            with frame:
                self._container = ui.VStack(height=0, spacing=5)
                with self._container:
                    self._build_thumbnail(item)
                    with ui.HStack():
                        ui.Spacer()
                        self._name_label = ui.Label(asset.name, height=0, style_type_name_override="Asset.Title")
                        ui.Spacer()

                    with ui.CollapsableFrame("Behaviors"):
                        self._physx_combobox = self._build_combobox("PhysicsVariant", item.physics_model)

                    with ui.CollapsableFrame("Asset info"):
                        self.collapse_info = self._build_info_widget()

                    with ui.CollapsableFrame("Tags", height=ui.Percent(100)):
                        self._tags_field = self._build_tags()

                    ui.Spacer()

    def accepted_multiple(self, detail_items: List[AssetDetailItem]) -> bool:
        """BrowserPropertyDelegate method override"""
        return False

    def show_multiple(self, detail_items: List[AssetDetailItem], frame: ui.Frame) -> None:
        """BrowserPropertyDelegate method override"""
        pass

    def _build_info_widget(self):
        """Build the Asset information section"""
        with ui.VStack(spacing=10):
            with ui.HStack():
                self._qcode_label = ui.Label("QCode:", style_type_name_override="Asset.Label", width=100)
                self._qcode_value = ui.Label(
                    self._item.asset.qcode, alignment=ui.Alignment.LEFT_BOTTOM, style_type_name_override="Asset.Value"
                )

            with ui.HStack():
                self._dimensions_label = ui.Label("Dimensions:(m)", style_type_name_override="Asset.Label", width=100)
                self._dimensions_value = ui.Label(
                    self._item.asset.extent_as_str,
                    alignment=ui.Alignment.LEFT_BOTTOM,
                    style_type_name_override="Asset.Value",
                )
            self._h_hstack = ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM)
            with self._h_hstack:
                self._hierachy_label = ui.Label("Hierarchy:", style_type_name_override="Asset.Label", width=100)
                self._build_hierarchy_links()
            ui.Spacer()

    def _build_tags(self):
        """Add the tag link section. must pass explorer instance"""
        from .extension import get_instance

        browser_widget: Optional[TreeBrowserWidget] = get_instance().browser_widget
        tag_widget = PropAssetTagsWidget(self._item.asset.tags, browser_widget)
        return tag_widget

    def _build_thumbnail(self, item: AssetDetailItem):
        """Builds thumbnail frame and resizes"""
        self._thumbnail_frame = ui.Frame(height=0)
        self._thumbnail_frame.set_computed_content_size_changed_fn(self._on_thumbnail_frame_size_changed)

        with self._thumbnail_frame:
            with ui.HStack():
                ui.Spacer(width=ui.Percent(25))

                self._thumbnail_container = ui.ZStack(height=ui.Fraction(1))
                with self._thumbnail_container:
                    self._thumbnail_img = ui.Image(
                        item.asset.thumbnail,
                        fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT,
                        alignment=ui.Alignment.CENTER_TOP,
                    )
                    # Badge to indicate item physics ON, need to change visibility if physics status changed
                    self._badge_container = ui.HStack(
                        alignment=ui.Alignment.LEFT_BOTTOM, visible=item.physics != "None"
                    )
                    with self._badge_container:
                        ui.Spacer(width=ui.Percent(80))
                        with ui.VStack():
                            ui.Spacer(height=2)
                            ui.ImageWithProvider(
                                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                                alignment=ui.Alignment.LEFT,
                                style_type_name_override="GridView.Item.Badge.Image",
                            )
                    if item.physics_model:
                        self._sub_physics = item.physics_model.current_index.subscribe_value_changed_fn(
                            self.__on_item_physics_changed
                        )
                ui.Spacer(width=ui.Percent(25))

    def __on_item_physics_changed(self, model: ui.SimpleIntModel) -> None:
        self._badge_container.visible = model.as_int != 0

    def _build_hierarchy_links(self):
        """build h links"""
        from .extension import get_instance

        browser_widget = get_instance().browser_widget

        def on_click(value):
            """set the browse search field with this tag

            Args:
                value (List): tag search value
            """
            search_field = browser_widget.search_field
            search_field.search_words = value

        self.h_buttons = []

        for i, h in enumerate(self._item.asset.hierarchy):
            text_v = "{}".format(h)

            new_button = ui.Button(
                text_v,
                alignment=ui.Alignment.LEFT_BOTTOM,
                click_fn=on_click,
                spacing=0,
                width=0,
                style_type_name_override="Asset.ButtonLinks",
            )
            h_list = self._item.asset.hierarchy[0 : (i + 1)]
            new_button.set_clicked_fn(lambda value=h_list: on_click(value))

            if i < (len(self._item.asset.hierarchy) - 1):
                new_label = ui.Label(" > ", width=0)

    def clear_buttons(self, buttons):
        for b in buttons:
            b.visible = False
        self.h_buttons = []

    def _on_thumbnail_frame_size_changed(self):
        # Dynamic change thumbnail size to be half of frame width
        async def __change_thumbnail_size_async():
            await omni.kit.app.get_app().next_update_async()
            image_size = self._thumbnail_frame.computed_width / 2
            self._thumbnail_img.height = ui.Pixel(image_size)

        asyncio.ensure_future(__change_thumbnail_size_async())
