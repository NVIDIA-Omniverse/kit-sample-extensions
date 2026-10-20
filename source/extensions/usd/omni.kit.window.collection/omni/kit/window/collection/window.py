# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from typing import List, Tuple

import carb.settings
import omni.stageupdate
import omni.ui as ui
from omni.kit.widget.collection import CollectionWidget
from pxr import Usd, UsdUtils

from .collection_watch import CollectionWatch
from .selection_watch import SelectionWatch


class CollectionWindow:
    """The Collection window"""

    def __init__(self, collection_watch=None):
        window_flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        self._visiblity_changed_listener = None
        self._window = ui.Window(
            "Collection", width=600, height=800, flags=window_flags, dockPreference=ui.DockPreference.RIGHT_TOP
        )
        self._window.set_visibility_changed_fn(self._visibility_changed_fn)

        # Dock it to the same space where Layers is docked, make it the first tab and the active tab.
        self._window.deferred_dock_in("Layers", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        # self._window.dock_order = 0

        # Get list of columns from settings
        self._columns = []
        self._settings = carb.settings.get_settings()
        self._columns_settings_path = "/persistent/exts/omni.kit.window.collection/columns"
        self._collection_watch = collection_watch
        self._window.frame.set_build_fn(self._build)
        self._stage_widget = None
        # The Open/Close Stage logic
        stage_update = omni.stageupdate.get_stage_update_interface()
        self._stage_subscription = stage_update.create_stage_update_node(
            "Collection Window", self._on_attach, self._on_detach
        )
        self._selection = SelectionWatch()

        # Callback when columns are changed or toggled
        # self._columns_changed_sub = self._stage_widget.subscribe_columns_changed(self._columns_changed)

    def _build(self):
        stage = omni.usd.get_context().get_stage()
        self._stage_widget = CollectionWidget(
            stage, collection_watch=self._collection_watch, columns_enabled=self._columns
        )
        # The selection logic
        self._stage_widget.set_selection_watch(self._selection)

    def show(self):
        self._window.visible = True

    def hide(self):
        self._window.visible = False

    def _columns_changed(self, columns: List[Tuple[str, bool]]):
        """
        Called by CollectionWidget when columns are changed or toggled.
        """
        enabled_columns = [c[0] for c in columns if c[1]]
        self._settings.set_string(self._columns_settings_path, "|".join(enabled_columns))

    def _visibility_changed_fn(self, visible):
        if self._visiblity_changed_listener:
            self._visiblity_changed_listener(visible)

        if not visible:
            if self._selection:
                self._selection.destroy()
            self._selection = None
        else:
            self._selection = SelectionWatch()

        if self._selection and self._stage_widget:
            self._stage_widget.set_selection_watch(self._selection)

    def set_visibility_changed_listener(self, listener):
        self._visiblity_changed_listener = listener

    def destroy(self):
        """
        Called by extension before destroying this object. It doesn't happen automatically.
        Without this hot reloading doesn't work.
        """
        self._visiblity_changed_listener = None
        if self._selection:
            self._selection._tree_view = None
            self._selection._events = None
            self._selection._stage_event_sub = None
            self._selection = None
        if self._stage_widget:
            self._stage_widget.destroy()
            self._stage_widget = None
        self._window = None
        self._stage_subscription = None
        self._settings = None
        self._columns_changed_sub = None

    def _on_attach(self, stage_id, meters_per_unit):
        """Called when opening a new stage"""
        # Gett Usd.Stage from ID
        cache = UsdUtils.StageCache.Get()
        stage = cache.Find(Usd.StageCache.Id.FromLongInt(stage_id))
        if not stage:
            return
        if self._stage_widget:
            self._stage_widget.open_stage(stage)

    def _on_detach(self):
        """Called when close the stage"""
        if self._stage_widget:
            self._stage_widget.open_stage(None)
