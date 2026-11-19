# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import inspect
import math
from typing import Dict, List, Optional

import carb
import omni.kit.app
import omni.ui as ui
import omni.usd
from omni.kit.browser.core import BrowserWidget, CollectionItem, DetailItem, OptionsMenu
from omni.kit.browser.folder.core import TreeFolderBrowserWidget
from omni.kit.browser.material import MaterialBrowserModel, MaterialDetailDelegate, MaterialOptionsMenu
from pxr import Usd

from ..models import MaterialPrimDetailItem, StageMaterialModel
from .delegate import MaterialPrimDelegate
from .empty_notification import EmptyNotification
from .material_preview_widget import MaterialPreviewWidget
from .material_property_widget import MaterialPropertyWidget
from .new_material_menu import NewMaterialMenu
from .options_menu import MaterialStageOptionsMenu
from .panel_mode import PanelModeBar, PanelModes
from .style import ICON_PATH, UI_STYLES
from .toolbar import MaterialToolBar

SETTING_ROOT = "/exts/omni.kit.window.material/"
SETTING_MIN_THUMBNAIL_SIZE = SETTING_ROOT + "min_thumbnail_size"
SETTING_MAX_THUMBNAIL_SIZE = SETTING_ROOT + "max_thumbnail_size"
SETTING_DATA_TIMEOUT = SETTING_ROOT + "data/timeout"
SETTING_CUSTOM_FOLDER_ROOT = SETTING_ROOT + "custom_folders"
SETTING_PANEL_MODE = SETTING_ROOT + "panel_mode"

# Here are two kinds of layout:

# Vertical (V): Widgets from top to bottom
# - SearchBar
# - Model Panel
# - View
# - Toolbar
# - Property

# Horizontal (H): tools at top, view at left and property at right
# - SearchBar -- Mode Panel -- Toolbar
# - View ----------------------\Property


# Layouts are dynamically changed when window size changes: small to V mode otherwise to H mode
class Layout:
    # V mode, max window width. If window width is bigger, switch to H mode
    V_MAX_WINDOW_WIDTH = 560
    # V mode, min view height, at least show one row
    V_MIN_VIEW_HEIGHT = 156
    # V model, min property height
    V_MIN_PROPERTY_HEIGHT = 20
    # V mode, default toolkits height
    V_DEFAULT_TOOLKITS_HEIGHT = 280
    # Vmode, search bar width
    V_SEARCH_BAR_WIDTH = ui.Pixel(300)

    # H mode, default toolkits width
    H_DEFAULT_TOOLKITS_WIDTH = 450
    # H mode, min view width, at least show one column
    H_MIN_VIEW_WIDTH = 200
    # H mode, min property width
    H_MIN_PROPERTY_WIDTH = 20


def _scan_progress_kwarg() -> dict:
    """``{"show_scan_progress": True}`` where the browser widget knows the argument, else empty."""
    try:
        for base in TreeFolderBrowserWidget.__mro__:
            if "show_scan_progress" in inspect.signature(base.__init__).parameters:
                return {"show_scan_progress": True}
    except (TypeError, ValueError):  # a signature that cannot be read is one that cannot take it
        pass
    return {}


class MaterialBrowserWidget(TreeFolderBrowserWidget):
    """
    Represent material browser widget with kinds of view mode supoort.
    """

    def _refresh_scan_progress_if_present(self) -> None:
        """
        Tell the scan spinner the panel mode changed, if there is a spinner to tell.

        It belongs to omni.kit.browser.folder.core, which grew it in 2.1.0. Asking rather than
        assuming lets this window run against an older one: no spinner, and nothing to refresh.
        """
        refresh = getattr(self, "_refresh_scan_progress_visibility", None)
        if refresh is not None:
            refresh()

    def __init__(self, **kwargs):
        settings = carb.settings.get_settings()
        self._frame_width: Optional[float] = None
        self._frame_height: Optional[float] = None
        browser_model = kwargs.pop(
            "model",
            MaterialBrowserModel(
                timeout=settings.get(SETTING_DATA_TIMEOUT), custom_folders_setting=SETTING_CUSTOM_FOLDER_ROOT
            ),
        )
        self._stage_material_model = kwargs.pop("stage_model", StageMaterialModel())
        self._stage_material_model.add_item_changed_fn(self._on_material_model_changed)
        self._stage_delegate = kwargs.pop(
            "stage_delegate",
            MaterialPrimDelegate(self._stage_material_model, lambda item: self.preview_material(item, True)),
        )
        self._stage_options_menu: Optional[OptionsMenu] = kwargs.pop(
            "stage_options_menu", MaterialStageOptionsMenu(self._stage_delegate)
        )
        self._delegate = kwargs.pop("stage_delegate", MaterialDetailDelegate(browser_model))
        self._options_menu = kwargs.pop("options_menu", MaterialOptionsMenu(self._delegate))

        min_thumbnail_size = settings.get(SETTING_MIN_THUMBNAIL_SIZE)
        max_thumbnail_size = settings.get(SETTING_MAX_THUMBNAIL_SIZE)

        kwargs["extra_filter_fn"] = self._filter_item
        self._panel_mode = PanelModes.LIBRARY
        settings.set(SETTING_PANEL_MODE, self._panel_mode)

        super().__init__(
            browser_model,
            detail_delegate=self._delegate,
            options_menu=self._options_menu,
            min_thumbnail_size=min_thumbnail_size,
            max_thumbnail_size=max_thumbnail_size,
            # The only opt-in anywhere. omni.kit.browser.material's own window shares this model
            # but builds the plain TreeFolderBrowserWidget, so it stays unchanged.
            #
            # Offered only if the base takes it: omni.kit.browser.folder.core grew the argument in
            # 2.1.0, and passing it to an older one is a TypeError raised before this widget exists
            # - which would take the window with it, and before the two shims below could run.
            **_scan_progress_kwarg(),
            **kwargs,
        )
        self._library_model = self._browser_model

        # Default vertical layout since docked right along with Stage
        self._layout_vertical = False
        self._last_toolkits_width = 0
        self._last_toolkits_height = 0

        self._stage_widget: Optional[BrowserWidget] = None

        self._switch_layout(self._layout_vertical)

        self._new_material_url = None

    def destroy(self) -> None:
        """Destroys all widget components and releases resources.

        Releases callbacks registered with the search bar and stage material model, removes widget listeners, and calls destroy on the toolbar, preview widget, stage options menu, browser model, and delegate. Finally, calls the parent destroy method to complete cleanup.
        """
        self._search_bar.remove_on_search_fn(self._on_search_in_stage)
        self._search_bar.set_navigation_clicked_fn(None)
        self._stage_material_model.remove_on_selection_changed_fn(self._on_material_selection_changed)
        if self._stage_widget:
            self._stage_widget.remove_thumbnail_size_changed_fn(self._sub_thumbnail_size_changed)
            self._stage_widget.remove_filter_changed_fn(self._sub_filter_changed)
        self._panel_mode_bar = None
        self._toolbar.destroy()
        self._preview_widget.destroy()

        self._stage_material_model.destroy()
        self._stage_delegate.destroy()
        self._stage_options_menu.destroy()
        self._browser_model.destroy()
        if self._delegate:
            self._delegate.destroy()

        super().destroy()

    @property
    def library_options_menu(self) -> Optional[OptionsMenu]:
        """Gets the library options menu for the widget.

        Returns:
            Optional[OptionsMenu]: The options menu used for library mode in the MaterialBrowserWidget.
        """
        return self._options_menu

    @property
    def stage_options_menu(self) -> Optional[OptionsMenu]:
        """Gets the stage options menu for the widget.

        Returns:
            Optional[OptionsMenu]: The options menu used for stage mode in the MaterialBrowserWidget.
        """
        return self._stage_options_menu

    def build_widgets(self) -> None:
        """
        Build widgets for mateiral browser.
        """

        self._frame = ui.Frame()
        with self._frame:
            with ui.VStack(spacing=4, style=UI_STYLES):
                # Main toolbar, including search bar, mode options(visible when H layout)
                self._build_search_toolbar()

                # Mode options (visible when V layout)
                self._v_mode_container = ui.HStack(height=0)
                with self._v_mode_container:
                    ui.Spacer()
                    self._mode_frame = ui.Frame()
                    self._mode_frame.add_child(self._panel_mode_bar.widget)
                    ui.Spacer()

                self._browser_container = ui.ZStack()
                with self._browser_container:
                    # Material browser widget for LIBRARY mode
                    self._build_browser_widget()

                    # Stage browser widget for CURRENT_SCENE and SELECTED mode
                    self._build_stage_view()

        # By default, LIBRARY mode, only show library browser widget
        self._search_bar.navigation_button.text = "Tree"
        self._search_bar.add_on_search_fn(self._on_search_in_stage)
        self._stage_container.visible = False
        NewMaterialMenu.set_on_material_created_fn(self._on_material_created)

        # Need change layout and children size if widget size changed
        self._frame.set_computed_content_size_changed_fn(self._on_size_changed)

    def _build_search_toolbar(self):
        with ui.ZStack(height=0):
            self._build_search_bar()
            self._h_mode_container = ui.HStack(height=0)
            with self._h_mode_container:
                ui.Spacer()
                self._panel_mode_bar = PanelModeBar(
                    self._stage_material_model, on_mode_changed_fn=self._on_panel_mode_changed
                )
                ui.Spacer()
            self._h_toolbar_container = ui.HStack(height=0)
            with self._h_toolbar_container:
                ui.Spacer()
                self._toolbar = MaterialToolBar(
                    self._stage_material_model, self._om_materials_picked, self._trigger_property_widget
                )
            # Scan progress needs its own right-aligned layer: _h_toolbar_container is hidden in
            # Library mode, which is the only mode that scans, and the search bar is width-clamped
            # short of the mode bar, which would put it mid-window.
            #
            # Asked for rather than assumed. The spinner is omni.kit.browser.folder.core's, which
            # grew it in 2.1.0; against an older one this window still builds, without a spinner,
            # which is how it looked before.
            build_spinner = getattr(self, "_build_scan_spinner", None)
            if build_spinner is not None:
                self._h_spinner_container = ui.HStack(height=0)
                with self._h_spinner_container:
                    ui.Spacer()
                    build_spinner()

        # Default, in vertical layout, do not show mode bar and toolbar bar in search toolbar
        self._h_mode_container.visible = True
        self._h_toolbar_container.visible = True

    def _build_stage_view(self):
        self._stage_container = ui.Stack(ui.Direction.TOP_TO_BOTTOM, spacing=4)
        with self._stage_container:
            self._stage_view_container = ui.ZStack(height=0)
            with self._stage_view_container:
                with ui.ZStack():
                    with ui.VStack():
                        # OM-83662: Only create widget when visible
                        ui.Frame(build_fn=self._build_stage_widget)

                    # The material preview widget
                    self._preview_widget = MaterialPreviewWidget(self._stage_delegate, self.preview_material)

                    # The empty notification
                    self._empty_notification = EmptyNotification()

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
                # Material toolbar
                self._v_toolbar_frame = ui.Frame(height=0)
                self._v_toolbar_frame.add_child(self._toolbar.widget)

                # Material property
                self._property_widget = MaterialPropertyWidget()

        self._v_splitter.set_offset_y_changed_fn(self._splitter_offset_y_changed)
        self._h_splitter.set_offset_x_changed_fn(self._splitter_offset_x_changed)
        self._preview_widget.show(None)
        self._toolbar.btnProperty.selected = self._property_widget.visible
        self._empty_notification.visible = False

    def _build_stage_widget(self):
        # Material browser widget for CURRENT_SCENE and SELECTED mode
        self._stage_widget = BrowserWidget(
            self._stage_material_model,
            detail_delegate=self._stage_delegate,
            min_thumbnail_size=self._min_thumbnail_size,
            max_thumbnail_size=self._max_thumbnail_size,
            detail_thumbnail_size=self._detail_thumbnail_size,
            thumbnail_aspect=self._thumbnail_aspect,
            style=self._extra_ui_style,
            extra_filter_fn=self._extra_filter_fn,
        )
        self._stage_widget.show_widgets(collection=False, category=False)
        self._stage_widget._detail_view.set_selection_changed_fn(self._on_stage_material_selection_changed)
        self._sub_thumbnail_size_changed = self._stage_widget.add_thumbnail_size_changed_fn(
            self._on_stage_thumbnail_size_changed
        )
        self._sub_filter_changed = self._stage_widget.add_filter_changed_fn(self._on_filter_changed)
        self._stage_widget.collection_index = 0

        self._stage_options_menu.bind_browser_widget(self._stage_widget)

    def preview_material(self, item: MaterialPrimDetailItem, on: bool) -> None:
        """
        Material preview on/off.
        Args:
            item (Optional[MaterialPrimDetailItem]): Detail item to preview the material.
            on (bool): True means preview is on, False means preview off
        """
        if self._stage_widget:
            self._stage_widget.show_widgets(detail=not on)
        self._preview_widget.show(item if on else None)
        if item is not None and not on:
            # Capture Thumbnail
            async def __capture_thumbnail(material_item):
                raw_data = await self._preview_widget.capture_thumbnail_async()
                if raw_data:
                    self._stage_delegate.thumbnail_captured(material_item, raw_data)

            if item.prim.IsInstanceProxy():
                # TODO: Failed to create attribute for such prim with error "authoring to an instance proxy is not allowed"
                carb.log_error(f"{item.url}: capture thumbnail on an instance proxy is not allowed")
                return
            else:
                asyncio.ensure_future(__capture_thumbnail(item))

    def _on_panel_mode_changed(self, mode: str) -> None:
        if self._panel_mode == mode:
            return

        old_panel_mode = self._panel_mode
        if self._panel_mode == PanelModes.SELECTED:
            self._stage_material_model.remove_on_selection_changed_fn(self._on_material_selection_changed)

        self._panel_mode = mode
        carb.settings.get_settings().set(SETTING_PANEL_MODE, self._panel_mode)
        if self._panel_mode == PanelModes.LIBRARY:
            self._search_bar._options_menu = self._options_menu
        else:
            self._search_bar._options_menu = self._stage_options_menu

        if mode == PanelModes.CURRENT_SCENE or mode == PanelModes.SELECTED:

            async def __delay_switch_stage():
                self._browser_widget.visible = False
                # A mode switch emits no progress event, so the spinner has to be told: left to a
                # progress-driven refresh it would keep turning over the stage view whenever a
                # scan happened to be stalled.
                self._refresh_scan_progress_if_present()
                self._stage_container.visible = True
                self._stage_material_model.actived = True
                self._search_bar.navigation_button.text = "Graph"
                self._search_bar.navigation_button.selected = False
                self._search_bar.navigation_button.image_url = f"{ICON_PATH}/graph_Tree_dark.svg"
                self._search_bar.set_navigation_clicked_fn(self._show_material_editor)
                await omni.kit.app.get_app().next_update_async()
                self.preview_material(None, False)
                self._empty_notification.visible = False
                self._switch_layout(self._layout_vertical)
                if self._stage_widget.detail_selection:
                    self._on_stage_material_selection_changed(self._stage_widget.detail_selection)
                if mode == PanelModes.SELECTED:
                    # only show selected
                    self._stage_material_model.add_on_selection_changed_fn(self._on_material_selection_changed)
                elif old_panel_mode == PanelModes.SELECTED:
                    # Refresh to show all items
                    self._stage_widget.refresh_details()
                if not self._layout_vertical:
                    self._h_toolbar_container.visible = True

                self._select_stage_material()

            asyncio.ensure_future(__delay_switch_stage())

        elif mode == PanelModes.LIBRARY:
            self._browser_widget.visible = True
            self._refresh_scan_progress_if_present()
            self._stage_container.visible = False
            self._stage_material_model.actived = False
            self._preview_widget.show(False)
            self._search_bar.navigation_button.text = "Tree"
            self._search_bar.navigation_button.selected = self._search_bar._navigation_visible
            self._search_bar.navigation_button.image_url = f"{ICON_PATH}/navtree.svg"
            self._search_bar.set_navigation_clicked_fn(None)
            if not self._layout_vertical:
                self._h_toolbar_container.visible = False

    def _on_material_selection_changed(self, materials: Dict[Usd.Prim, any]) -> None:
        # Material selection changed, update detail view in PanelModes.SELECTED
        detail_items = self._stage_widget._detail_view.model.get_item_children()
        for item in detail_items:
            if item.prim in materials:
                item.selected = True
            else:
                item.selected = False

        self._stage_widget.refresh_details()
        self._select_stage_material()
        self._show_empty_notification_if_necessary()

        if self._panel_mode == PanelModes.SELECTED:
            if self._preview_widget.visible:
                if len(self._stage_widget.detail_selection) == 0:
                    # Hide preview image since nothing selected
                    self._preview_widget.show(None)
                else:
                    self._preview_widget.show(self._stage_widget.detail_selection[0])

    def _show_empty_notification_if_necessary(self):
        if self._panel_mode == PanelModes.SELECTED:
            if len(self._stage_widget.detail_selection) == 0:
                # Show empty notification, hide stage view and property
                self._stage_widget.show_widgets(detail=False)

                selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
                if selected_paths:
                    self._empty_notification.set_message(
                        "Asset selected but no material assigned.\nAssign material to the asset to see its materials here."
                    )
                else:
                    self._empty_notification.set_message()
                self._empty_notification.visible = True

                if self._property_widget.visible:
                    self._trigger_property_widget()
            elif self._empty_notification.visible:
                # Hide empty notification, show stage view
                self._stage_widget.show_widgets(detail=True)
                self._empty_notification.visible = False

    def _om_materials_picked(self, picked_material_prims: Dict[Usd.Prim, any]):
        if picked_material_prims:
            if self._panel_mode == PanelModes.SELECTED:
                # in selected mode, add selected one to view
                self._on_material_selection_changed(picked_material_prims)
            # Select related items in detail view
            detail_items = self._stage_widget._detail_view.model.get_item_children()
            selected_detail_items = []
            for item in detail_items:
                if item.prim in picked_material_prims:
                    selected_detail_items.append(item)
            self._stage_widget.detail_selection = selected_detail_items

    def _filter_item(self, item: DetailItem) -> bool:
        # If PanelModes.SELECTED, only show selected detail items
        if (
            isinstance(item, MaterialPrimDetailItem)
            and self._panel_mode == PanelModes.SELECTED
            and item.prim is not None
        ):
            return item.selected
        else:
            return True

    def _on_search_in_stage(self, filter_words: Optional[List[str]]) -> None:
        if self._stage_widget:
            self._stage_widget.filter_details(filter_words)

    def _on_stage_thumbnail_size_changed(self, thumbnail_size: int) -> None:
        # Hide detail label if thumbnail size is smaller than 128
        self._stage_delegate.hide_label = thumbnail_size < 128
        self._stage_delegate.item_changed(None, None)

    def _show_material_editor(self):
        try:
            import omni.kit.window.material_graph

            prim_list = []
            for item in self._stage_widget.detail_selection:
                if item.prim is not None:
                    prim_list.append(item.prim)

            window = ui.Workspace.get_window("Material Graph")
            popup = True
            if window and window.visible and window.docked:
                popup = False

            omni.kit.window.material_graph.GraphExtension.show_materials(prim_list)

            async def __focus_material_graph():
                # Wait for window visible and docked
                for _ in range(3):
                    await omni.kit.app.get_app().next_update_async()
                window = ui.Workspace.get_window("Material Graph")
                window.focus()
                # OM-35294: undock material graph if it is not opened
                if popup:
                    window.undock()
                    # Move to center of main window
                    width = ui.Workspace.get_main_window_width()
                    height = ui.Workspace.get_main_window_height()
                    if window.width < width:
                        window.position_x = (width - window.width) / 2
                    if window.height < height:
                        window.position_y = (height - window.height) / 2

            asyncio.ensure_future(__focus_material_graph())

        except ImportError:
            carb.log_warn(
                "Failed to import material graph editor module (omni.kit.window.material_graph). Please enable it first."
            )

    def _on_stage_material_selection_changed(self, selections: List[DetailItem]) -> None:
        material_prims = [item.prim for item in selections if item and item.prim]

        async def __change_property_materials(materials):
            # OM-36123: Need to wait for widgets with popup window (for example color picker)
            # end edit before showing new materials, otherwise it will crash
            for _ in range(2):
                await omni.kit.app.get_app().next_update_async()

            self._property_widget.set_materials(materials)

        asyncio.ensure_future(__change_property_materials(material_prims))

    def _splitter_offset_y_changed(self, offset_y: ui.Length) -> None:
        if self._property_widget.visible:
            if offset_y.value < Layout.V_MIN_VIEW_HEIGHT:
                self._v_splitter.offset_y = Layout.V_MIN_VIEW_HEIGHT
                return
            available_property_height = (
                self._browser_container.computed_height - offset_y - self._toolbar.computed_height - 12
            )
            if available_property_height < Layout.V_MIN_PROPERTY_HEIGHT:
                self._last_toolkits_height = 0
                self._trigger_property_widget()

        if self._property_widget.visible:
            self._last_toolkits_height = self._browser_container.computed_height - offset_y

    def _splitter_offset_x_changed(self, offset_x: ui.Length) -> None:
        if self._property_widget.visible:
            if offset_x.value < Layout.H_MIN_VIEW_WIDTH:
                self._h_splitter.offset_x = Layout.H_MIN_VIEW_WIDTH
                return
            available_property_width = self._browser_container.computed_width - offset_x - 8
            if available_property_width < Layout.H_MIN_PROPERTY_WIDTH:
                self._trigger_property_widget()
                self._last_toolkits_width = 0
        if self._property_widget.visible:
            self._last_toolkits_width = self._browser_container.computed_width - offset_x

    def _select_stage_material(self) -> None:
        # Make sure at least one stage material selected in the detail view
        if len(self._stage_widget.detail_selection) == 0:
            detail_items = self._stage_widget._detail_view.model.get_item_children()
            if len(detail_items) > 1:
                # Find first visible item
                for index in range(1, len(detail_items)):
                    item = detail_items[index]
                    if (
                        item in self._stage_widget._detail_view._delegates
                        and self._stage_widget._detail_view._delegates[item].visible
                    ):
                        if self._new_material_url is not None:
                            if item.url == self._new_material_url:
                                self._stage_widget.detail_selection = [item]
                                self._new_material_url = None
                                break
                        else:
                            self._stage_widget.detail_selection = [item]
                            break

    def _on_material_model_changed(self, model: ui.AbstractItemModel, item: DetailItem) -> None:
        if isinstance(item, CollectionItem):

            async def __update_material_selection():
                await omni.kit.app.get_app().next_update_async()
                self._select_stage_material()
                self._show_empty_notification_if_necessary()

            asyncio.ensure_future(__update_material_selection())
        elif isinstance(item, MaterialPrimDetailItem):
            self._stage_delegate.item_changed(model, item)

    def _on_filter_changed(self, filter_words: Optional[List[str]]) -> None:
        self._select_stage_material()

    def _switch_layout(self, vertical: bool) -> None:
        # mode panel visibility
        self._h_mode_container.visible = not vertical
        self._v_mode_container.visible = vertical

        # toolbar visibility
        self._toolbar.spacer_visible = vertical
        self._toolbar.widget.width = ui.Fraction(1) if vertical else ui.Pixel(0)
        self._v_toolbar_frame.visible = vertical
        self._h_toolbar_container.visible = False if vertical else (self._panel_mode != PanelModes.LIBRARY)

        # searchbar
        self.__update_search_bar_width(vertical)

        # stage view and splitters
        self._stage_container.direction = ui.Direction.TOP_TO_BOTTOM if vertical else ui.Direction.LEFT_TO_RIGHT

        self._v_splitter.visible = vertical
        self._h_splitter.visible = not vertical
        if vertical:
            self._stage_view_container.width = ui.Fraction(1)
            self._toolkits_container.width = ui.Fraction(1)
        else:
            self._stage_view_container.height = ui.Fraction(1)
            self._toolkits_container.height = ui.Fraction(1)
        self._layout_vertical = vertical

        # Hide property if not enough space
        if self._property_widget.visible:
            if not self._has_space_for_property():
                self._property_widget.visible = False
                self._toolbar.btnProperty.selected = False

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

        if not self._layout_vertical:
            if self._property_widget.visible:
                if self._last_toolkits_width != 0:
                    self._h_splitter.offset_x = self._browser_container.computed_width - self._last_toolkits_width

            self.__update_search_bar_width(self._layout_vertical)

    def _on_height_changed(self, height) -> None:
        if self._layout_vertical:
            if self._property_widget.visible:
                if self._last_toolkits_height != 0:
                    self._v_splitter.offset_y = self._browser_container.computed_height - self._last_toolkits_height

    def _trigger_property_widget(self) -> None:
        if not self._property_widget.visible:
            if not self._has_space_for_property():
                carb.log_warn("Not enough space to show material property!")
                return

        self._property_widget.visible = not self._property_widget.visible
        self._toolbar.btnProperty.selected = self._property_widget.visible

        asyncio.ensure_future(self._update_layout_async())

    async def _update_layout_async(self) -> None:
        if not self._property_widget.visible:
            # property hidden
            if self._layout_vertical:
                # toolkits height fix, stage view height max
                await omni.kit.app.get_app().next_update_async()
                self._v_splitter.visible = False
                self._stage_view_container.height = ui.Fraction(1)
                self._toolkits_container.height = ui.Pixel(0)
            else:
                # toolkits width fix, stage view width max
                await omni.kit.app.get_app().next_update_async()
                self._h_splitter.visible = False
                self._stage_view_container.width = ui.Fraction(1)
                self._toolkits_container.width = ui.Pixel(0)
        else:
            # show property widget
            if self._layout_vertical:
                # stage view height changed by splitter, toolkits max
                self._toolkits_container.height = ui.Fraction(1)
                self._stage_view_container.height = ui.Pixel(0)
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
                # stage view height changed by splitter, toolkits max
                self._toolkits_container.width = ui.Fraction(1)
                self._stage_view_container.width = ui.Pixel(0)
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

    def _has_space_for_property(self) -> bool:
        if self._layout_vertical:
            available_property_height = (
                self._browser_container.computed_height - Layout.V_MIN_VIEW_HEIGHT - self._toolbar.computed_height - 12
            )
            if available_property_height < Layout.V_MIN_PROPERTY_HEIGHT:
                carb.log_warn("Not enough space to show material property!")
                return False
        elif self._browser_container.computed_width > 0:
            available_property_width = self._browser_container.computed_width - Layout.H_MIN_VIEW_WIDTH - 12
            if available_property_width < Layout.H_MIN_PROPERTY_WIDTH:
                return False

        return True

    def _on_material_created(self, url):
        self._new_material_url = url

    def __update_search_bar_width(self, vertical: bool):
        # Update width of search bar
        if vertical:
            self._search_bar.width = ui.Fraction(1)
        else:

            def __set_search_bar_width():
                # Adjust search bar width to match the model panel bar
                self._search_bar.width = ui.Pixel(
                    self._panel_mode_bar.position_x - self._search_bar._frame.screen_position_x - 10
                )

            if self._panel_mode_bar.width > 0:
                __set_search_bar_width()
            else:
                self._search_bar.width = Layout.V_SEARCH_BAR_WIDTH

                async def __delay_update():
                    while self._panel_mode_bar.width == 0:
                        await omni.kit.app.get_app().next_update_async()
                    await omni.kit.app.get_app().next_update_async()
                    __set_search_bar_width()

                asyncio.ensure_future(__delay_update())
