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
from typing import Dict, List, Optional

import carb
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.ui as ui
import omni.usd
from carb.input import KeyboardInput as Keyboard
from omni.kit.playlist.core import PlaylistCard, PlaylistModel, SystemPlaylistModel, enum_playlist_cards
from omni.kit.widgets.custom import DashRectangle, DefaultWidgetStyle, Hotkey, InfoPanel, MouseKey, get_ui_style
from pxr import Usd, UsdGeom

from .constant import OPTIONS_PADDING_X
from .playlist_manager import PlaylistManager
from .playlist_usd import PlaylistUsd
from .style import WINDOW_STYLE
from .ui import ListBar, PlayControls, PlaylistView
from .utils import get_icon_path

LIST_PADDING_X = 30


class PlaylistWindow(ui.Window):
    def __init__(self, visible=False):
        super().__init__("Playlist", width=600, height=650, visible=visible)
        self._hotkey_up: Hotkey = None
        self._hotkey_down: Hotkey = None
        self._hotkey_left: Hotkey = None
        self._hotkey_right: Hotkey = None
        self._playlist_view: PlaylistView = PlaylistView()
        self._list_bar: Optional[ListBar] = None
        self._play_controls: Optional[PlayControls] = None

        self.frame.set_build_fn(self._build_ui)

        ui_style = get_ui_style()
        def_style = DefaultWidgetStyle.get_style(ui_style)
        style = def_style.copy()
        style.update(WINDOW_STYLE[ui_style])
        self.frame.set_style(style)

        # Dock it to the same space where Property is docked, make it active.
        self.deferred_dock_in("Property", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

    def destroy(self):  # pragma: no cover
        super().destroy()
        self.visible = False
        if self._list_bar:
            self._list_bar.destroy()
            self._list_bar = None
        if self._playlist_view is not None:
            self._playlist_view.destroy()
        if self._play_controls is not None:
            self._play_controls.destroy()
        if self._hotkey_up is not None:
            self._hotkey_up.clean()
        if self._hotkey_down is not None:
            self._hotkey_down.clean()
        if self._hotkey_left is not None:
            self._hotkey_left.clean()
        if self._hotkey_right is not None:
            self._hotkey_right.clean()

    @property
    def currect_playlist_name(self) -> PlaylistModel:
        return self._list_bar._get_current_playlist_name() if self._list_bar else None

    def add_camera_to_playlist(self, camera_prim: Optional[Usd.Prim], playlist_name):

        async def __add_playlist():
            while self._list_bar is None:
                self.visible = True
                await omni.kit.app.get_app().next_update_async()

            card = PlaylistCard.create(camera_prim=camera_prim)
            if playlist_name is None:

                def on_playlist_created(index):
                    playlist = self._playlist_manager.get_playlist(index)
                    if playlist is not None:
                        playlist.insert_item(card)

                self._list_bar.new_playlist(on_playlist_created_fn=on_playlist_created)
            else:
                playlist = self._playlist_manager.get_playlist(None, name=playlist_name)
                if playlist is not None:
                    index = playlist.insert_item(card)
                    if self._playlist_view.model == playlist:
                        self._playlist_view.update_data(playlist)
                        self._playlist_view.selection = [index]

        asyncio.ensure_future(__add_playlist())

    def _build_ui(self):
        self._playlist_manager = PlaylistManager.get_instance()
        self._playlist_usd = PlaylistUsd.get_instance()
        self._cameras_menu = None
        self._view_menu = omni.ui.Menu(
            "Camera Playlist view menu", name="this", menu_compatibility=False, tearable=False
        )

        self._build_content()

        # Register callback for stage opened
        self._usd_context = omni.usd.get_context()
        self._stage_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="omni.kit.tool.camera_playlist.window",
            event_name=self._usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=lambda _: self._on_stage_opened(),
        )
        self._on_stage_opened()

        # Register callback for camera created/removed
        self._stage_subscription = omni.stageupdate.get_stage_update_interface().create_stage_update_node(
            "CameraPlaylist", None, None, None, self._on_prim_created, None, self._on_prim_removed
        )

        # Register hotkey to change cameras
        self._hotkey_down = Hotkey(Keyboard.DOWN, self._next_camera, hotkey_enabled_fn=self._hotkey_enabled)
        self._hotkey_up = Hotkey(Keyboard.UP, self._previous_camera, hotkey_enabled_fn=self._hotkey_enabled)
        self._hotkey_right = Hotkey(Keyboard.RIGHT, self._next_camera, hotkey_enabled_fn=self._hotkey_enabled)
        self._hotkey_left = Hotkey(Keyboard.LEFT, self._previous_camera, hotkey_enabled_fn=self._hotkey_enabled)

    def _build_content(self):
        with ui.VStack(spacing=5):
            ui.Spacer(height=3)
            self._list_bar = ListBar(self._update_data)

            with ui.HStack(height=250):
                ui.Spacer(width=LIST_PADDING_X)
                with ui.VStack(height=40):
                    with ui.ZStack(accept_drop_fn=self.__accept_drop, drop_fn=self.__drop):
                        ui.Rectangle()
                        DashRectangle(500, 40)
                        with ui.VStack():
                            ui.Spacer()
                            with ui.HStack(height=26):
                                ui.Spacer(width=20)
                                self._add_button = ui.Button(
                                    "Add",
                                    width=120,
                                    height=26,
                                    clicked_fn=self._add_camera,
                                    style_type_name_override="TreeView.Button",
                                )
                                ui.Label("Or", alignment=ui.Alignment.CENTER, style={"background_color": 0xFF00FF00})
                                ui.Image(get_icon_path("dropHere_dark.svg"), width=26, height=26)
                                ui.Label("Drag and Drop", width=100)
                                ui.Spacer(width=20)
                            ui.Spacer()

                    self._playlist_view.build_ui()
                ui.Spacer(width=LIST_PADDING_X)

            self._play_controls = PlayControls(self._playlist_view.model)

            self._build_info()

    def _get_content_style(self, ui_style):
        # overided base.
        style = WINDOW_STYLE[ui_style]
        return style

    def _build_info(self):
        with ui.HStack():
            ui.Spacer(width=OPTIONS_PADDING_X)
            self._info_panel = InfoPanel()
            ui.Spacer(width=OPTIONS_PADDING_X)

    def _add_camera(self):
        if self._cameras_menu is None:
            self._cameras_menu = omni.ui.Menu("Camera list menu", name="this", menu_compatibility=False)
        else:
            self._cameras_menu.clear()

        cards: Dict[str, List[PlaylistCard]] = {}
        for card in enum_playlist_cards():
            if card.menu_text:
                if card.menu_text not in cards:
                    cards[card.menu_text] = []
                cards[card.menu_text].append(card)

        with self._cameras_menu:
            for menu_text in sorted(list(cards.keys())):
                with ui.Menu(menu_text, menu_compatibility=False):
                    for card in cards[menu_text]:
                        ui.MenuItem(card.name, triggered_fn=lambda c=card: self._on_add_playlist_card(c))

        self._cameras_menu.show()

    def _on_stage_opened(self):
        self._stage = self._usd_context.get_stage()
        if self._stage:
            self._playlist_manager.load_from_usd(self._stage)
            if self._list_bar:
                self._list_bar.reset()

    # Callback when a new USD prim created
    def _on_prim_created(self, path):
        if not path:
            return
        prim = self._stage.GetPrimAtPath(path)
        if prim.IsA(UsdGeom.Camera):
            card = PlaylistCard.create(path=path)
            if card:
                current_playlist = self._playlist_view.model
                if isinstance(current_playlist, SystemPlaylistModel):
                    if current_playlist.camera_type == card.type:
                        self._playlist_view.update_data(current_playlist)

    # Callback when a USD prim removed
    def _on_prim_removed(self, path):
        # TODO: how to verify this is a camera prim?
        pass

    def _update_data(self, playlist: Optional[PlaylistModel]):
        self._playlist_view.update_data(playlist)
        self._play_controls.bind_playlist(playlist)

        if playlist is None:
            self._add_button.enabled = False
            self._info_panel.show(False)
        else:
            playlist.set_dropped_fn(self._on_camera_dropped)
            self._info_panel.show(True)
            self._add_button.enabled = playlist.can_change
            self._info_panel.update_data(playlist.attributes)

    def _on_add_playlist_card(self, card: PlaylistCard):
        selection = self._playlist_view.selection
        if len(selection) > 0:
            # Insert after selection
            self._playlist_view.insert(card, index=selection[0] + 1)
            self._playlist_view.selection = [selection[0] + 1]
        else:
            # Append
            self._playlist_view.insert(card)
            items = self._playlist_view.items
            self._playlist_view.selection = [len(items) - 1]

        # Always re-create camera menu
        self._cameras_men = None

    def _on_camera_dropped(self, index: int):
        async def __auto_select_async():
            await omni.kit.app.get_app().next_update_async()
            if index < 0:
                items = self._playlist_view.items
                self._playlist_view.selection = [len(items) - 1]
            else:
                self._playlist_view.selection = [index]

        asyncio.ensure_future(__auto_select_async())

    def _on_remove_camera(self):
        self._playlist_view.remove_selected()

    def _on_mouse_pressed_view(self, x, y, button, modifier_flags):
        if button != MouseKey.RIGHT:
            return

        self._view_menu.clear()
        with self._view_menu:
            ui.MenuItem("Remove Camera", triggered_fn=self._on_remove_camera, enabled=self._playlist_view.can_change)

        self._view_menu.show()

    def _next_camera(self):
        self._playlist_view.next()

    def _previous_camera(self):
        self._playlist_view.previous()

    def _hotkey_enabled(self):
        return self.visible

    def __accept_drop(self, url: str) -> bool:
        accepted = self._playlist_view.model.drop_accepted(None, url)
        return accepted

    def __drop(self, url: str) -> None:
        try:
            drop_url = str(url)
        except Exception as e:
            carb.log_warn(f"Cannot convert {url} to string.")
            return
        self._playlist_view.model.drop(None, drop_url)
