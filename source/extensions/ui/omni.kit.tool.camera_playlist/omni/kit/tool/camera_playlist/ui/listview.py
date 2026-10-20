# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Dict, Optional

import carb
from omni import ui
from omni.kit.playlist.core import CardItem, Column, PlaylistModel, get_play_manager
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.widgets.custom import DarkColors, SimpleListView

from ..utils import get_icon_path

LIST_STYLE = {"TreeView.HoveredIcon": {"background_color": 0xFFFF0000}}


class PlaylistDelegate(ui.AbstractItemDelegate):
    """
    Delegate is the representation layer. TreeView calls the methods
    of the delegate to create custom widgets for each item.
    """

    def __init__(self, on_item_clicked: callable):
        super().__init__()
        self._on_item_clicked = on_item_clicked
        self.subscription = None
        self._widgets: Dict[CardItem, ui.Widget] = {}
        self._remove_widgets: Dict[CardItem, ui.ImageWithProvider] = {}

    def destroy(self):  # pragma: no cover
        self._remove_widgets.clear()
        self._widgets.clear()

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""
        pass

    def build_widget(self, model: PlaylistModel, item: CardItem, column_id, level, expanded):
        """Create a widget per column per item"""

        if column_id == 0:
            self._widgets[item] = ui.HStack(
                mouse_pressed_fn=lambda x, y, btn, flag, model=model, item=item: self._on_clicked(btn, model, item),
                mouse_hovered_fn=lambda hovered, item=item: self._on_hover(item, hovered),
                style=LIST_STYLE,
            )
            with self._widgets[item]:
                # ID + NAME
                name_model = model.get_item_value_model(item, Column.NAME)
                index_model = model.get_item_value_model(item, Column.ID)
                label_id = ui.Label(
                    index_model.as_string,
                    alignment=ui.Alignment.CENTER,
                    width=32,
                    style_type_name_override="TreeView.Item",
                )
                ui.Label(name_model.as_string, style_type_name_override="TreeView.Item")

                def change_id(model):
                    label_id.text = model.as_string

                item.subscribe_index_changed_fn(change_id)

                # Type icon
                ui.Spacer()
                with ui.VStack(width=0):
                    ui.Spacer()
                    ui.ImageWithProvider(item.data.icon, width=18, height=18, style_type_name_override="TreeView.Icon")
                    ui.Spacer()
                ui.Spacer(width=4)

                # Remove icon, visible when hovered
                self._remove_widgets[item] = ui.ZStack(
                    width=0,
                    mouse_pressed_fn=lambda x, y, btn, flag, model=model, item=item: self._on_delete(btn, model, item),
                )
                with self._remove_widgets[item]:
                    ui.Rectangle(style={"background_color": DarkColors.WindowBackground})
                    with ui.HStack(width=24):
                        ui.Spacer()
                        with ui.VStack(width=18):
                            ui.Spacer()
                            ui.ImageWithProvider(
                                get_icon_path("remove_dark.svg"),
                                width=18,
                                height=18,
                                style_type_name_override="TreeView.Icon",
                            )
                            ui.Spacer()
                        ui.Spacer()
                self._remove_widgets[item].visible = False

    def _on_clicked(self, btn: int, model: PlaylistModel, item: CardItem) -> None:
        return self._on_item_clicked(btn, model, item)

    def _on_hover(self, item: CardItem, hovered: bool) -> None:
        if hovered:
            self._remove_widgets[item].visible = True
        else:
            self._remove_widgets[item].visible = False

    def _on_delete(self, btn: int, model: PlaylistModel, item: CardItem) -> None:
        if btn == 0:
            model.remove_item(item)


class PlaylistView(SimpleListView):
    def __init__(self):
        self._empty_model = PlaylistModel("", path="")
        self._playlist_delegate = PlaylistDelegate(self._on_item_clicked)
        self._context_menu = ui.Menu("Camera Playlist context menu", menu_compatibility=False, tearable=False)
        self.__sub_index = None

        self.__play_manager = get_play_manager()
        self.__item_clicked = False

    def build_ui(self):
        super().__init__(
            height=250,
            model=self._empty_model,
            column_widths=[ui.Fraction(1)],
            # on_item_selected_fn=self._on_item_selected,
            delegate=self._playlist_delegate,
            drop_between_items=True,
        )
        self._tree_view.set_selection_changed_fn(self._on_item_selected)

    def destroy(self):  # pragma: no cover
        self._playlist_delegate.destroy()
        self._context_menu = None
        self.__sub_index = None

    @property
    def can_change(self):
        return self.model.can_change

    def update_data(self, playlist_model: Optional[PlaylistModel]):
        if playlist_model is None:
            self._tree_view.model = self._empty_model
        else:
            playlist_model.check_update()
            super().update_data(playlist_model)
            viewport_api = get_active_viewport()
            active_camera_path = viewport_api.camera_path

            for item in self.items:
                if str(item.data.path) == str(active_camera_path):
                    self.selection = [self.items.index(item)]
            else:
                self.selection = []

            def __on_playing_item_changed(model: ui.SimpleIntModel):
                if model.as_int >= 0:
                    selection = [model.as_int]
                else:
                    selection = []
                if selection != self.selection:
                    self.selection = selection

            if self.__sub_index:
                self.__sub_index = None
            self.__sub_index = self._tree_view.model.index_model.subscribe_value_changed_fn(__on_playing_item_changed)

    def _on_item_selected(self, selections):
        if len(selections) == 0:
            self.model.index_model.set_value(-1)

        if not self._multi_selection:
            # Disable multi selection
            if selections and len(selections) > 1:
                selections = selections[-1:]
                self._tree_view.selection = selections

        for item in selections:
            if self.__item_clicked:
                # If selection comes from item click, navigate
                self.__play_manager.navigate(item=item)
                self.__item_clicked = False
            else:
                self.model.selection = item

    def _on_item_clicked(self, btn: int, model: PlaylistModel, item: CardItem):
        if btn == 0:
            self.__item_clicked = True
        if btn != 1:
            return True
        index = self.items.index(item)
        self.selection = [index]

        self._context_menu.clear()
        with self._context_menu:
            ui.MenuItem("Send to Start", triggered_fn=self._send_to_start, enabled=self.can_change)
            ui.MenuItem("Send to End", triggered_fn=self._send_to_end, enabled=self.can_change)
            ui.MenuItem("Remove Item", triggered_fn=self._on_remove_camera, enabled=self.can_change)

        self._context_menu.show()

        return True

    def _send_to_start(self):
        selected_item = self.treeview.selection[0]
        self.model.drop(None, selected_item, 0)

    def _send_to_end(self):
        selected_item = self.treeview.selection[0]
        self.model.drop(None, selected_item, len(self.items))

    def _on_remove_camera(self):
        self.remove_selected()
