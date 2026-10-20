# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
"""This module defines a MovieCaptureExtension that integrates a movie capture window into Omni UI and menu systems, handling its creation, visibility toggling, and live session restrictions."""

from functools import partial

import omni.ext
import omni.ui as ui
from omni.kit.menu.utils import MenuHelperExtension, MenuItemDescription
from omni.kit.widget.prompt import Prompt

from .output_settings_widget import LIVE_SESSION_RESTRICTION_WARNING, is_in_live_session
from .window import MovieCaptureWindow


class MovieCaptureExtension(omni.ext.IExt, MenuHelperExtension):
    """The entry point for MovieCaptureExtension"""

    MENU_PATH = "Window/Rendering/Movie Capture"
    MENU_NAME = "Rendering/Movie Capture"
    MENU_GROUP = "Window"
    _instance = None

    @staticmethod
    def get_instance():
        return MovieCaptureExtension._instance

    def on_startup(self):
        self._window = None
        MovieCaptureExtension._instance = self
        ui.Workspace.set_show_window_fn(MovieCaptureWindow.WINDOW_NAME, partial(self.show_window, None))
        self.menu_startup(
            MovieCaptureWindow.WINDOW_NAME, MovieCaptureExtension.MENU_NAME, MovieCaptureExtension.MENU_GROUP
        )

        # MenuHelperExtension does not support menu path with sub-menus
        # so remove the menu item and setup our own with correct menu path, along with existing tick_fn and onclick_action
        omni.kit.menu.utils.remove_menu_items(self._menu_entry, name=self._menu_group)
        self._menu_entry = [
            omni.kit.menu.utils.MenuItemDescription(
                name="Rendering",
                sub_menu=[
                    MenuItemDescription(
                        name="Movie Capture",
                        ticked=True,  # menu item is ticked
                        ticked_fn=lambda v=False, w=MovieCaptureWindow.WINDOW_NAME: MenuHelperExtension._is_visible(
                            v, w
                        ),  # gets called when the menu needs to get the state of the ticked menu
                        onclick_action=(
                            self.__class__.__module__,
                            f"menu_toggle_window_helper_rendering_movie_capture",
                        ),
                    )
                ],
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_entry, name=MovieCaptureExtension.MENU_GROUP)

    def on_shutdown(self):
        self._clean_up_window()
        self.menu_shutdown()
        MovieCaptureExtension._instance = None
        ui.Workspace.set_show_window_fn(MovieCaptureWindow.WINDOW_NAME, None)

    def _visiblity_changed_fn(self, visible):
        self.menu_refresh()

    def _clean_up_window(self):
        if self._window is not None:
            self._window.destroy()
            self._window = None

    def show_window(self, menu, value):
        if value:
            if is_in_live_session():
                Prompt(title="Movie Capture unavailable", text=LIVE_SESSION_RESTRICTION_WARNING, modal=True).show()
                if self._window:
                    self._window.hide()

            else:
                if self._window is None:
                    self._window = MovieCaptureWindow()
                    self._window.set_visibility_changed_listener(self._visiblity_changed_fn)
                else:
                    self._window.show()
        elif self._window:
            self._window.hide()
