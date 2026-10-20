# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import omni.ext
import omni.ui as ui
from omni.kit.menu.utils import MenuHelperExtension

from .collection_watch import CollectionWatch
from .window import CollectionWindow


class CollectionWindowExtension(omni.ext.IExt, MenuHelperExtension):
    WINDOW_NAME = "Collection"
    MENU_GROUP = "Window"

    def on_startup(self):
        self._window = None
        # TODO: use show_window_without_destroy will break the old version of the property/widget collection's test
        ui.Workspace.set_show_window_fn(CollectionWindowExtension.WINDOW_NAME, self.show_window)
        self.menu_startup(
            CollectionWindowExtension.WINDOW_NAME,
            CollectionWindowExtension.WINDOW_NAME,
            CollectionWindowExtension.MENU_GROUP,
        )
        self._collection_watch = CollectionWatch()

    def on_shutdown(self):
        ui.Workspace.show_window(CollectionWindowExtension.WINDOW_NAME, False)
        ui.Workspace.set_show_window_fn(CollectionWindowExtension.WINDOW_NAME, None)
        self.menu_shutdown()
        if self._window:
            self._window.destroy()
            self._window = None
        if self._collection_watch:
            self._collection_watch.destroy()
            self._collection_watch = None

    def _visiblity_changed_fn(self, visible):
        self.show_window(visible)
        self.menu_refresh()

    # TODO: this will has better performance than show_window,
    # but can't keep backward compatibility tests of property/widget collection
    def show_window_without_destroy(self, value):
        if value:
            if not self._window:
                self._window = CollectionWindow(self._collection_watch)
                self._window.set_visibility_changed_listener(self._visiblity_changed_fn)
            self._window.show()
        elif self._window:
            self._window.hide()

    def show_window(self, value):
        if value:
            self._window = CollectionWindow(self._collection_watch)
            self._window.set_visibility_changed_listener(self._visiblity_changed_fn)
        elif self._window:
            self._window.destroy()
            self._window = None
