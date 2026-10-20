# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["GraphEditorCoreWidget"]

import asyncio
import traceback
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import carb
import omni.kit.app
import omni.ui as ui
from omni.kit.graph.delegate.default.delegate import GraphNodeDelegate
from omni.kit.widget.graph import GraphView, IsolationGraphModel
from omni.ui import color as cl

from .graph_editor_core_breadcrumbs import GraphEditorCoreBreadcrumbs
from .graph_editor_core_catalog import GraphEditorCoreCatalog
from .graph_editor_core_splitter import GraphEditorCoreSplitter

CURRENT_PATH = Path(__file__).parent
EXT_PATH = CURRENT_PATH.parent.parent.parent.parent.parent
ICON_PATH = EXT_PATH.joinpath("icons")

BACKGROUND = cl("#1F2123")
BORDER_MISCELLANEOUS = cl("#207C98")
BORDER_SELECTED = cl("#FFFFFF")
ICON_BACKGROUND = cl("#2A3034")
NODE_BACKGROUND = cl("#3C404B")
NODE_BACKGROUND_SELECTED = cl("#666C7F")


def is_func_empty(func: Callable) -> bool:
    """Return True if the given function has only pass"""
    # Source: https://stackoverflow.com/questions/13620542

    def empty_func():
        pass

    def empty_func_with_doc():
        """Empty function with docstring."""
        pass

    return (
        func.__code__.co_code == empty_func.__code__.co_code
        or func.__code__.co_code == empty_func_with_doc.__code__.co_code
    )


class GraphEditorCoreWidget:
    """The common widget for Graph extensions"""

    def __init__(
        self,
        model=None,
        delegate=None,
        view_type=GraphView,
        style=None,
        catalog_model: Optional[ui.AbstractItemModel] = None,
        catalog_delegate: Optional[ui.AbstractItemDelegate] = None,
        has_catalog: bool = True,
        toolbar_items=[],
        **kwargs,
    ):
        self.__graph_model = model
        self._isolation_model = None
        self._isolation_changed_subscription = None

        # Make sure we always have the delegate because GraphView needs it
        if delegate is None:
            self.__graph_delegate = GraphNodeDelegate()
            self.__graph_delegate_created = True
        else:
            self.__graph_delegate = delegate
            self.__graph_delegate_created = False

        self.__view_type = view_type
        self.__catalog_model = catalog_model
        self.__catalog_delegate = catalog_delegate
        self.__clear_graph_task: asyncio.Task = None
        self.__has_catalog = has_catalog
        self.__main_frame = None
        self.__breadcrumbs_frame = None
        self.__breadcrumbs = None
        self.__startup_frame = None
        self.__toolbar_items = toolbar_items
        self.__toolbar_frame = None

        self._navigation = []

        self._splitter_left: Optional[GraphEditorCoreSplitter] = None
        # Not private to let derived classes operate with it
        self._graph_view: Optional[GraphView] = None
        self._catalog_widget = None

        self.__frame = ui.Frame(build_fn=self.__on_build)

        # Save the style, we need to match the behaviour of Widget.style.
        # GraphEditorCoreWidget.style should return exactly the style that was
        # given with the user.
        self.style = style

    @property
    def style(self):
        return self.__style

    @style.setter
    def style(self, style):
        """Apply the style and mix it with the default one"""

        # Keep it on the case the user wants to get it back
        self.__style = style

        # Get the default style from the delegate
        default_style = self.__graph_delegate.get_style(
            border=BORDER_MISCELLANEOUS,
            background=BACKGROUND,
            node_background=NODE_BACKGROUND,
            icon_background=ICON_BACKGROUND,
            border_selected=BORDER_SELECTED,
            node_background_selected=NODE_BACKGROUND_SELECTED,
        )
        # Other omni.ui elements
        default_style.update(
            {
                # Label
                "Label::Navigation": {"color": 0x66FFFFFF},
                "Label::Navigation:hovered": {"color": 0xFFFFFFFF},
                # Splitter
                "Rectangle::Splitter": {"background_color": 0x0, "margin": 3, "border_radius": 2},
                "Rectangle::Splitter:hovered": {"background_color": 0xFFB0703B},
                "Rectangle::Splitter:pressed": {"background_color": 0xFFB0703B},
                # TreeView
                "TreeView": {"background_color": BACKGROUND, "background_selected_color": 0x77E3B334},
                "TreeView:selected": {"background_color": 0x77E3B334},
                "TreeView.Item": {"margin": 0},
                "TreeView.Item.Icon": {"margin": 4, "border_radius": 2},
                "TreeView.Item.Icon::Collapse": {"color": 0xFFCCCCCC},
                "TreeView.Item.Description": {"color": 0xFF707071, "font_size": 14},
                "TreeView.Item.Title": {"color": 0xFFB4B4B4, "font_size": 14},
                "TreeView.Item::Type": {"color": 0xFF8A8777, "font_size": 14},
                "TreeView.Item:selected": {"color": 0xFFEEEEEE},
                "Rectangle::section_background": {"background_color": 0xFF343434},
                # ToolBar
                "ToolBar": {"margin_height": 9},
                "ToolBar.Separator": {"background_color": 0xFF707070},
                "ToolBar.Button": {"padding": 4, "background_color": 0x0},
                "ToolBar.Button.Label": {"color": 0xFFAAAAAA, "alignment": ui.Alignment.CENTER, "font_size": 14},
                "ToolBar.Button.Image": {"color": 0xFFFFFFFF, "alignment": ui.Alignment.CENTER},
                "ToolBar.Button:hovered": {"background_color": 0xFF373737},
            }
        )
        # The style from arguments overrides the default one
        if style:
            default_style.update(style)

        self.__frame.style = default_style

    def destroy(self):
        self.__frame = None

        if self._catalog_widget:
            self._catalog_widget.destroy()
        self._catalog_widget = None

        self.__toolbar_frame = None
        self.__toolbar_items = []

        if self.__clear_graph_task:
            self.__clear_graph_task.cancel()
            self.__clear_graph_task = None

        if self._graph_view:
            self._graph_view.destroy()
        self._graph_view = None

        if self._splitter_left:
            self._splitter_left.destroy()
        self._splitter_left = None

        self._navigation = None

        if self.__breadcrumbs:
            self.__breadcrumbs.destroy()
        self.__breadcrumbs = None
        self.__startup_frame = None
        self.__breadcrumbs_frame = None
        self.__main_frame = None
        self.__catalog_delegate = None
        self.__catalog_model = None
        self.__view_type = None
        if self.__graph_delegate_created and self.__graph_delegate:
            self.__graph_delegate.destroy()
        self.__graph_delegate = None

        self._isolation_changed_subscription = None
        if self._isolation_model:
            self._isolation_model.destroy()
        self._isolation_model = None
        self.__graph_model = None

    def get_current_graph_item(self):
        # The last item in the Navigation
        return self._navigation[-1] if self._navigation else None

    def on_accept_drop(self, drop_data: str):
        """Called to check if the widget can accept the drop"""
        return False

    def on_drop(self, event: ui.WidgetMouseDropEvent):
        """Called when the user dropped something to the window"""
        pass

    def on_build_catalog(self):
        """Create a pannel used to create new nodes"""
        self._catalog_widget = GraphEditorCoreCatalog(
            model=self.__catalog_model,
            delegate=self.__catalog_delegate,
            on_context_menu_fn=self.on_catalog_context_menu,
            search_field_style=self.style,
        )

    def on_build_breadcrumbs(self):
        if self.__breadcrumbs:
            self.__breadcrumbs.destroy()
        self.__breadcrumbs = GraphEditorCoreBreadcrumbs(
            selected_fn=lambda i: self.set_current_compound(self._navigation[i.id]),
            navigation=[self.__graph_model[i].name for i in self._navigation],
        )

    def on_build_graph(self):
        if self.__clear_graph_task:
            self.__clear_graph_task.cancel()
            self.__clear_graph_task = None

        self._graph_view = self.__view_type(
            model=self.__graph_model,
            delegate=self.__graph_delegate,
            accept_drop_fn=self.on_accept_drop,
            drop_fn=self.on_drop,
            virtual_ports=False,
            port_grouping=True,
            smooth_zoom=True,
            rectangle_selection=True,
        )
        self._graph_view.set_mouse_pressed_fn(lambda x, y, b, m: self.__on_mouse_pressed(b))
        self._graph_view.set_mouse_double_clicked_fn(lambda x, y, b, m: self.__on_mouse_mouse_double_clicked(b))
        self._graph_view.set_key_pressed_fn(lambda k, m, p: self.on_key_pressed(k, m, p))

    def on_build_startup(self):
        # Usually we need buttons or menu here
        pass

    def on_left_mouse_button_pressed(self, items):
        pass

    def on_right_mouse_button_pressed(self, items):
        pass

    def on_left_mouse_button_double_clicked(self, items):
        pass

    def on_key_pressed(self, key, mod, pressed):
        pass

    def on_catalog_context_menu(self, items: List[ui.AbstractItem]):
        pass

    def focus_on_nodes(self):
        """Zoom and pan to fit all the nodes"""

        async def focus_on_nodes_async():
            for _ in range(2):
                await omni.kit.app.get_app().next_update_async()
            self._graph_view.focus_on_nodes()

        asyncio.ensure_future(focus_on_nodes_async())

    def set_current_compound(self, item, focus=True):
        """Changes the current view to show the subgraph of the compound"""
        if self.__graph_model[item].nodes is None:
            # This item can't have children
            return

        if self._isolation_model and self._isolation_model._root == item:
            # It happens when double click by input or output node. The model
            # already has this item as a root.
            return

        if item in self._navigation:
            self._navigation = self._navigation[: self._navigation.index(item) + 1]
        elif item is not None:
            self._navigation.append(item)

        self.__build_navigation()

        # Set the new root
        if self._isolation_model:
            self._isolation_model.destroy()
        self._isolation_model = IsolationGraphModel(self.__graph_model, item)
        self._isolation_changed_subscription = self._isolation_model.subscribe_item_changed(self.__on_item_changed)

        # Better handling of error messages. The error message from Kit is
        # totaly uninformative
        try:
            self._graph_view.model = self._isolation_model
        except Exception as e:
            carb.log_error("Exception when changing compound")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

        if focus:
            self.focus_on_nodes()

    @property
    def model(self):
        return self.__graph_model

    @model.setter
    def model(self, model):
        self._navigation = []

        self.__graph_model = model

        if self._isolation_model:
            self._isolation_model.destroy()
        self._isolation_model = None

        if self._graph_view:

            async def _clear_graph_view():
                self._graph_view.clear()

            if not self.__clear_graph_task or self.__clear_graph_task.done():
                self.__clear_graph_task = asyncio.ensure_future(_clear_graph_view())

            if self.__graph_model is None:
                self._graph_view.model = None
            else:
                self.set_current_compound(None, True)

        is_startup_screen = self.__graph_model is None
        if self.__main_frame:
            self.__main_frame.visible = not is_startup_screen
        if self.__startup_frame:
            self.__startup_frame.visible = is_startup_screen

    def __on_build(self):
        with ui.VStack():
            # build customized toolbar
            if self.__toolbar_items:
                self.__toolbar_frame = ui.Frame(build_fn=self.__on_build_toolbar)
            if not self.__has_catalog or not self.__catalog_model or is_func_empty(self.on_build_catalog):
                self.__on_build_middle()
            else:
                self._splitter_left = GraphEditorCoreSplitter(
                    build_left_fn=self.on_build_catalog, build_right_fn=self.__on_build_middle
                )

    def __on_build_middle(self):
        is_startup_screen = self.__graph_model is None

        with ui.ZStack():
            self.__main_frame = ui.Frame(visible=not is_startup_screen)
            with self.__main_frame:
                with ui.ZStack():
                    self.on_build_graph()
                    self.__breadcrumbs_frame = ui.Frame(height=0)

            self.__startup_frame = ui.Frame(visible=is_startup_screen)
            with self.__startup_frame:
                self.on_build_startup()

    def __on_build_toolbar(self):
        """
        example of self.__toolbar_items
        self.__toolbar_items = [
        { "name": "open", "icon": path, "on_clicked": fn},
        { "name": "save", "icon": path, "on_clicked": fn},
        { "name": "-"},
        { "name": "reset", "icon": path, "on_clicked": fn}
        { "name": "load", "label": "Load"}
        { "name": "unavailable", "icon": path, "enabled": False, "tooltip": "A tooltip"}
        ]
        """
        if not self.__toolbar_items or not isinstance(self.__toolbar_items, List):
            return

        with ui.HStack(height=30, style_type_name_override="ToolBar"):
            for item in self.__toolbar_items:
                name = item.get("name", None)
                if name == "-":
                    style_type_name_override = item.get("style_type_name_override", "ToolBar.Separator")

                    # spliter
                    ui.Spacer(width=2)
                    ui.Rectangle(
                        width=2,
                        height=26,
                        style_type_name_override=style_type_name_override,
                    )
                    ui.Spacer(width=2)
                elif name == " ":
                    # spacer
                    width = item.get("width", None)
                    if width:
                        ui.Spacer(width=width)
                    else:
                        ui.Spacer()
                else:
                    # button
                    label = item.get("label", "")
                    enabled = item.get("enabled", True)
                    tooltip = item.get("tooltip", "")
                    style_type_name_override = item.get("style_type_name_override", "ToolBar.Button")
                    button_item = ui.Button(
                        text=label,
                        enabled=enabled,
                        tooltip=tooltip,
                        image_width=18,
                        image_height=18,
                        width=0,
                        style_type_name_override=style_type_name_override,
                    )

                    icon = item.get("icon", None)
                    if icon:
                        button_item.image_url = icon
                    on_click_fn = item.get("on_clicked", None)
                    if on_click_fn:
                        button_item.set_clicked_fn(on_click_fn)

    def set_toolbar_items(self, items):
        self.__toolbar_items = items
        if self.__toolbar_frame:
            self.__toolbar_frame.rebuild()
        else:
            self.__frame.rebuild()

    def __build_navigation(self):
        """Create the top panel with the navigation"""
        if self.__breadcrumbs_frame:
            with self.__breadcrumbs_frame:
                self.on_build_breadcrumbs()

    def clear_all(self):
        self.model = None

    def _get_graph_view_hovered_position(self) -> Optional[Tuple[float]]:
        """Return the position of mouse if self._graph_view is hovered"""
        # TODO: Check if the window is visible
        if not self._graph_view or not self._graph_view.visible:
            return

        zoom = self._graph_view.zoom

        app_window = omni.appwindow.get_default_app_window()
        input = carb.input.acquire_input_interface()
        dpi_scale = ui.Workspace.get_dpi_scale()
        pos_x, pos_y = input.get_mouse_coords_pixel(app_window.get_mouse())
        pos_x = pos_x / dpi_scale / zoom
        pos_y = pos_y / dpi_scale / zoom

        screen_x = self._graph_view.screen_position_x
        screen_y = self._graph_view.screen_position_y
        screen_w = self._graph_view.computed_width
        screen_h = self._graph_view.computed_height

        if pos_x > screen_x and pos_y > screen_y and pos_x < screen_x + screen_w and pos_y < screen_y + screen_h:
            return pos_x, pos_y

    def __on_item_changed(self, item):
        if self._isolation_model and self._isolation_model.nodes is None:
            # It happens when prim is deleted and the modes doesn't have any
            # node. We need to go to the startup screen.
            self.clear_all()

    def __on_mouse_pressed(self, button):
        if self._graph_view:
            selection = self._graph_view.selection
        else:
            selection = []

        if button == 0:
            self.on_left_mouse_button_pressed(selection)
        elif button == 1:
            self.on_right_mouse_button_pressed(selection)

    def __on_mouse_mouse_double_clicked(self, button):
        if self._graph_view:
            selection = self._graph_view.selection
        else:
            selection = []

        if button == 0:
            self.on_left_mouse_button_double_clicked(selection)
