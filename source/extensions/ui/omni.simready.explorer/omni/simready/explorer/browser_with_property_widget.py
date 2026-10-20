# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
import math
from typing import List, Optional

import carb
import omni.kit.app
import omni.ui as ui
from omni.kit.browser.folder.core import FileDetailItem, TreeFolderBrowserWidget

from .browser_property_view import BrowserPropertyView
from .browser_toolbar import BrowserPropertyToolBar
from .style import UI_STYLES


# Layout are dynmiac changed when window size changed: small to V mode otherwise to H mode
class Layout:
    # V mode, max window width. If window width is bigger, switch to H mode
    V_MAX_WINDOW_WIDTH = 400
    # V mode, min view height, at least show one row
    V_MIN_VIEW_HEIGHT = 156
    # V model, min property view height
    V_MIN_PROPERTY_HEIGHT = 20
    # V mode, default toolkits height
    V_DEFAULT_TOOLKITS_HEIGHT = 280
    # Vmode, search bar width
    V_SEARCH_BAR_WIDTH = ui.Pixel(400)

    # H mode, default toolkits width
    H_DEFAULT_TOOLKITS_WIDTH = 450
    # H mode, min view width, at least show one column
    H_MIN_VIEW_WIDTH = 200
    # H mode, min property view width
    H_MIN_PROPERTY_WIDTH = 75


class BrowserWithPropertyWidget(TreeFolderBrowserWidget):
    """
    The Browser View (V in the MDV achitecture).
    Responsible for creating the frames for Category view, Search bar, Browser area, Property view.
    Takes care of updating the layout when user resizes windows.
    """

    def __init__(self, *args, **kwargs):
        self._frame_width: Optional[float] = None
        self._frame_height: Optional[float] = None

        # Default horizontal layout sice docked bottom along with Content
        self._layout_vertical = False
        self._last_toolkits_width = 0
        self._last_toolkits_height = 0

        super().__init__(*args, **kwargs)

        self._switch_layout(self._layout_vertical)

    def build_widgets(self) -> None:
        """
        Build widgets with property view.
        """
        self._frame = ui.Frame()
        with self._frame:
            with ui.VStack(spacing=4, style=UI_STYLES):
                self._build_search_toolbar()
                self._build_browser_widgets()

        # Need change layout and children size if widget size changed
        self._frame.set_computed_content_size_changed_fn(self._on_size_changed)

    def _build_search_toolbar(self):
        with ui.ZStack(height=0):
            self._build_search_bar()
            self._h_toolbar_container = ui.HStack(height=0)
            with self._h_toolbar_container:
                ui.Spacer()
                self._toolbar = BrowserPropertyToolBar(self._toggle_property_view)

    def _build_browser_widgets(self):
        self._browser_container = ui.Stack(ui.Direction.TOP_TO_BOTTOM, spacing=4)
        with self._browser_container:
            self._browser_view_container = ui.ZStack(height=0)
            with self._browser_view_container:
                self._build_browser_widget()

                # Draggable splitter for H/V layout mode
                self._v_splitter = ui.Placer(offset_y=0, draggable=True, drag_axis=ui.Axis.Y)
                with self._v_splitter:
                    ui.Rectangle(height=4, style_type_name_override="Splitter")

                self._h_splitter = ui.Placer(offset_x=0, draggable=True, drag_axis=ui.Axis.X)
                with self._h_splitter:
                    ui.Rectangle(width=4, style_type_name_override="Splitter")

            # Toolkits
            self._toolkits_container = ui.VStack(spacing=4)
            with self._toolkits_container:
                # Toolbar with property button
                self._v_toolbar_frame = ui.Frame(height=0)
                self._v_toolbar_frame.add_child(self._toolbar.widget)

                # Property View
                self._property_view = BrowserPropertyView()

        self._v_splitter.set_offset_y_changed_fn(self._splitter_offset_y_changed)
        self._h_splitter.set_offset_x_changed_fn(self._splitter_offset_x_changed)
        self._toolbar.btn_property.selected = self._property_view.visible

        self._browser_widget._detail_view.set_selection_changed_fn(self._on_detail_selection_changed)

        # Default show property view
        async def __show_property_view_async():
            await omni.kit.app.get_app().next_update_async()
            self._toggle_property_view()

        asyncio.ensure_future(__show_property_view_async())

    def _splitter_offset_y_changed(self, offset_y: ui.Length) -> None:
        if self._property_view.visible:
            if offset_y.value < Layout.V_MIN_VIEW_HEIGHT:
                self._v_splitter.offset_y = Layout.V_MIN_VIEW_HEIGHT
                return
            available_property_height = (
                self._browser_container.computed_height - offset_y - self._toolbar.computed_height - 12
            )
            if available_property_height < Layout.V_MIN_PROPERTY_HEIGHT:
                self._last_toolkits_height = 0
                self._toggle_property_view()

        if self._property_view.visible:
            self._last_toolkits_height = self._browser_container.computed_height - offset_y

    def _splitter_offset_x_changed(self, offset_x: ui.Length) -> None:
        if self._property_view.visible:
            if offset_x.value < Layout.H_MIN_VIEW_WIDTH:
                self._h_splitter.offset_x = Layout.H_MIN_VIEW_WIDTH
                return
            available_property_width = self._browser_container.computed_width - offset_x - 8
            if available_property_width < Layout.H_MIN_PROPERTY_WIDTH:
                self._toggle_property_view()
                self._last_toolkits_width = 0
        if self._property_view.visible:
            self._last_toolkits_width = self._browser_container.computed_width - offset_x

    def _switch_layout(self, vertical: bool) -> None:
        # toolbar visibility
        self._toolbar.spacer_visible = vertical
        self._toolbar.widget.width = ui.Fraction(1) if vertical else ui.Pixel(0)
        self._v_toolbar_frame.visible = vertical
        self._h_toolbar_container.visible = not vertical

        # searchbar
        self.__update_search_bar_width(vertical)

        # browser view and splitters
        self._browser_container.direction = ui.Direction.TOP_TO_BOTTOM if vertical else ui.Direction.LEFT_TO_RIGHT

        self._v_splitter.visible = vertical
        self._h_splitter.visible = not vertical
        if vertical:
            self._browser_view_container.width = ui.Fraction(1)
            self._toolkits_container.width = ui.Fraction(1)
        else:
            self._browser_view_container.height = ui.Fraction(1)
            self._toolkits_container.height = ui.Fraction(1)
        self._layout_vertical = vertical

        # Hide property if not enough space
        if self._property_view.visible and not self._has_space_for_property():
            self._property_view.visible = False
            self._toolbar.btn_property.selected = False

        # Update widgets position
        asyncio.ensure_future(self._update_layout_async())

    def _on_size_changed(self) -> None:
        # Widget size changed callback
        if self._frame_width is None or self._frame_height is None:
            self._frame_width = self._frame.computed_content_width
            self._frame_height = self._frame.computed_content_height
        else:
            if not math.isclose(self._frame_width, self._frame.computed_content_width):

                async def __delay_update_width():
                    await omni.kit.app.get_app().next_update_async()
                    self._on_width_changed(self._frame.computed_content_width)

                asyncio.ensure_future(__delay_update_width())
                self._frame_width = self._frame.computed_content_width
            if not math.isclose(self._frame_height, self._frame.computed_content_height):

                async def __delay_update_height():
                    await omni.kit.app.get_app().next_update_async()
                    self._on_height_changed(self._frame.computed_content_height)

                asyncio.ensure_future(__delay_update_height())
                self._frame_height = self._frame.computed_content_height

    def _on_width_changed(self, width) -> None:
        # Window width changed, adjust widgets layout
        vertical_layout = width < Layout.V_MAX_WINDOW_WIDTH
        if vertical_layout != self._layout_vertical:
            self._switch_layout(vertical_layout)

        if not self._layout_vertical and self._property_view.visible and self._last_toolkits_width != 0:
            self._h_splitter.offset_x = self._browser_container.computed_width - self._last_toolkits_width

        self.__update_search_bar_width(self._layout_vertical)

    def _on_height_changed(self, height) -> None:
        if self._layout_vertical and self._property_view.visible and self._last_toolkits_height != 0:
            self._v_splitter.offset_y = self._browser_container.computed_height - self._last_toolkits_height

    def _toggle_property_view(self) -> None:
        if not self._property_view.visible and not self._has_space_for_property():
            carb.log_warn("Not enough space to show property!")
            return

        self._property_view.visible = not self._property_view.visible
        self._toolbar.btn_property.selected = self._property_view.visible

        asyncio.ensure_future(self._update_layout_async())

    def __update_search_bar_width(self, vertical: bool):
        # Update width of search bar
        if vertical:
            self._search_bar.width = ui.Fraction(1)
        else:

            def __set_search_bar_width():
                # Adjust search bar width to match the model panel bar
                self._search_bar.width = ui.Pixel(
                    self._toolbar.position_x - self._search_bar._frame.screen_position_x - 10
                )

            if self._toolbar.width > 0:
                __set_search_bar_width()
            else:
                self._search_bar.width = Layout.V_SEARCH_BAR_WIDTH

                async def __delay_update():
                    while self._toolbar.width == 0:
                        await omni.kit.app.get_app().next_update_async()
                    await omni.kit.app.get_app().next_update_async()
                    __set_search_bar_width()

                asyncio.ensure_future(__delay_update())

    def _has_space_for_property(self) -> bool:
        if self._layout_vertical:
            if self._browser_container.computed_height > 0:
                available_property_height = (
                    self._browser_container.computed_height
                    - Layout.V_MIN_VIEW_HEIGHT
                    - self._toolbar.computed_height
                    - 12
                )
                if available_property_height < Layout.V_MIN_PROPERTY_HEIGHT:
                    carb.log_warn("Not enough space to show property!")
                    return False
        else:
            available_property_width = self._browser_container.computed_width - Layout.H_MIN_VIEW_WIDTH - 12
            if available_property_width < Layout.H_MIN_PROPERTY_WIDTH:
                return False

        return True

    async def _update_layout_async(self) -> None:
        if not self._property_view.visible:
            # property hidden
            if self._layout_vertical:
                # toolkits height fix, browser view height max
                await omni.kit.app.get_app().next_update_async()
                self._v_splitter.visible = False
                self._browser_view_container.height = ui.Fraction(1)
                self._toolkits_container.height = ui.Pixel(0)
            else:
                # toolkits width fix, browser view width max
                await omni.kit.app.get_app().next_update_async()
                self._h_splitter.visible = False
                self._browser_view_container.width = ui.Fraction(1)
                self._toolkits_container.width = ui.Pixel(0)
        else:
            # show property view
            if self._layout_vertical:
                # details view height changed by splitter, toolkits max
                self._toolkits_container.height = ui.Fraction(1)
                self._browser_view_container.height = ui.Pixel(0)
                self._v_splitter.visible = True

                await omni.kit.app.get_app().next_update_async()
                if self._last_toolkits_height == 0:
                    offset_y = max(
                        self._browser_container.computed_height - Layout.V_DEFAULT_TOOLKITS_HEIGHT,
                        Layout.V_MIN_VIEW_HEIGHT,
                    )
                    self._last_toolkits_height = self._browser_container.computed_height - offset_y
                    self._v_splitter.offset_y = offset_y
                else:
                    self._v_splitter.offset_y = self._browser_container.computed_height - self._last_toolkits_height
            else:
                # details view height changed by splitter, toolkits max
                self._toolkits_container.width = ui.Fraction(1)
                self._browser_view_container.width = ui.Pixel(0)
                self._h_splitter.visible = True

                await omni.kit.app.get_app().next_update_async()
                if self._last_toolkits_width == 0:
                    offset_x = max(
                        self._browser_container.computed_width - Layout.H_DEFAULT_TOOLKITS_WIDTH,
                        Layout.H_MIN_VIEW_WIDTH,
                    )
                    self._last_toolkits_width = self._browser_container.computed_width - offset_x
                    self._h_splitter.offset_x = offset_x
                else:
                    self._h_splitter.offset_x = self._browser_container.computed_width - self._last_toolkits_width

    def _on_detail_selection_changed(self, selections: List[FileDetailItem]) -> None:
        self.selection = selections
        if len(selections) > 1:
            self._property_view.show_detail_multi_item(selections)
        else:
            self._property_view.show_detail_item(selections[0] if selections else None)
