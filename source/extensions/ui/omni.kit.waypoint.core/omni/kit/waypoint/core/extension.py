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
import functools
import traceback
from contextlib import nullcontext
from typing import Dict, List, Optional, cast

import carb
import carb.settings
import omni.ext
import omni.kit.app
import omni.kit.prim.icon
import omni.timeline
import omni.ui as ui
import omni.usd
from omni.kit.playlist.core import PlaylistCard
from pxr import Sdf, Tf, Trace, Usd

from .common import (
    CURRENT_TOOL_PATH,
    EXTENSION_NAME,
    SETTINGS_WAYPOINT_ROOT,
    WAYPOINT_ICON_URL,
    WAYPOINT_ROOT_PRIM_PATH,
    create_data_only_prim,
)
from .external import OmniConnectionManager, UsdBakedPreview
from .pereference import WaypointPerefenceWindow
from .playlist_card_waypoint import WaypointCard
from .prompt_ui import Prompt
from .style import ICON_PATH
from .viewport_waypoint import ViewportWaypoint

SETTING_PERSISTENT = "/persistent"
SETTINGS_WAYPOINT_ACTIVE = SETTINGS_WAYPOINT_ROOT + "active_waypoint"
SETTINGS_WAYPOINT_EDITING = SETTINGS_WAYPOINT_ROOT + "editing_waypoint"
SETTINGS_WAYPOINT_SHOW_ICONS = SETTINGS_WAYPOINT_ROOT + "show_icons"

SETTINGS_WAYPOINT_ENABLE_HOTKEYS = SETTINGS_WAYPOINT_ROOT + "enable_hotkeys"
SETTINGS_WAYPOINT_CREATE_HOTKEY = SETTINGS_WAYPOINT_ROOT + "hotkeys/create"
SETTINGS_WAYPOINT_NEXT_HOTKEY = SETTINGS_WAYPOINT_ROOT + "hotkeys/next"
SETTINGS_WAYPOINT_PREVIOUS_HOTKEY = SETTINGS_WAYPOINT_ROOT + "hotkeys/previous"
SETTINGS_WAYPOINT_DELETE_HOTKEY = SETTINGS_WAYPOINT_ROOT + "hotkeys/delete"

WAYPOINT_WINDOW_FOCUS_CONTEXT = "omni.kit.waypoint.core-window-focused"

g_singleton = None


def handle_exception(func):  # pragma: no cover
    """
    Decorator to print exception in async functions
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            carb.log_error(f"Exception when async '{func}'")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

    return wrapper


def get_instance():
    """Return the current instance of the waypoint extension.

    Returns:
        Waypoint: The current instance of the waypoint extension or None if it has not been initialized.
    """
    global g_singleton
    return g_singleton


class WaypointChangeCallbacks:
    """A class for handling waypoint change callbacks.

    This class stores callback functions for waypoint events. It accepts functions to be executed when a waypoint is created, deleted, updated, or when a reset occurs. Users can supply their own functions to customize the behavior on these events.

    Args:
        on_waypoint_created (callable): Function called when a waypoint is created.
        on_waypoint_deleted (callable): Function called when a waypoint is deleted.
        on_waypoint_changed (callable): Function called when a waypoint is modified.
        on_reset (callable): Function called to signal a reset of waypoint state.
    """

    def __dummy(*_):  # pragma: no cover
        pass

    def __init__(
        self,
        on_waypoint_created: callable = __dummy,
        on_waypoint_deleted: callable = __dummy,
        on_waypoint_changed: callable = __dummy,
        on_reset: callable = __dummy,
    ):
        self.on_waypoint_created = on_waypoint_created
        self.on_waypoint_deleted = on_waypoint_deleted
        self.on_waypoint_changed = on_waypoint_changed
        self.on_reset = on_reset


class WaypointExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        self._way_point = Waypoint()
        self._way_point.on_startup(ext_id)

    def on_shutdown(self):
        self._way_point.on_shutdown()


class Waypoint:
    """A class to manage waypoints in the USD stage.

    This class provides APIs for creating, editing, renaming, deleting, and recalling waypoints. It handles the registration of callbacks to notify consumers when a waypoint is created, changed, or deleted. In addition, it manages viewport icons and integrates with user settings to control the visibility and behavior of waypoint indicators.

    Public methods allow you to create new waypoints either synchronously or asynchronously, begin and end editing of existing waypoints, and recall a waypoint to update the viewport state. The class also monitors USD stage events to update or remove waypoints and synchronizes the display of icons based on current settings.

    Overall, this class offers a comprehensive interface to manage the lifecycle and presentation of waypoints within the omni.kit.waypoint.core extension.
    """

    def on_startup(self, ext_id):
        """Initializes the Waypoint and registers the related PlaylistCard. Extracts the extension name from ext_id, sets up sidecar data if available, subscribes to settings and stage events, and initializes hotkeys.

        Args:
            ext_id (str): The current extension id used for initialization.
        """
        PlaylistCard.register(WaypointCard.PLAYLIST_CARD_TYPE_WAYPOINT, WaypointCard)
        sections = ext_id.split("-")
        self._ext_name = sections[0]
        self._edit_target = None
        try:  # pragma: no cover
            from omni.usd_presenter.sidecar import deregister_data, register_data

            self.__sidecar_data = register_data("Waypoints")
        except ImportError:
            self.__sidecar_data = None
        self.__prim_changed_task = None
        self.__dirty_prim_paths = set()
        self._settings = carb.settings.get_settings()
        self._waypoint_icon_visible = self._is_waypoint_icon_visible()
        self._prim_icon = omni.kit.prim.icon.get_prim_icon_interface()

        self._waypoints: Dict[str, ViewportWaypoint] = {}
        self._notifications: List[WaypointChangeCallbacks] = []

        self._current_waypoint: Optional[ViewportWaypoint] = None
        self._editing_waypoint: Optional[ViewportWaypoint] = None

        self._app = omni.kit.app.get_app_interface()
        self._timeline = omni.timeline.get_timeline_interface()
        self._update_sub = None
        self._preference_window: Optional[WaypointPerefenceWindow] = None

        self._usd_context = omni.usd.get_context()
        self._stage = self._usd_context.get_stage()
        self._stage_event_subs = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.kit.waypoint.core.waypoint",
                event_name=self._usd_context.stage_event_name(e),
                on_event=trigger_fn,
            )
            for e, trigger_fn in [
                (omni.usd.StageEventType.OPENED, self._on_stage_opened),
                (omni.usd.StageEventType.CLOSED, self._on_stage_closed),
            ]
        ]
        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:
            self.current_waypoint = None
            self._refresh_waypoints()

        if not self._settings.get_as_bool(SETTINGS_WAYPOINT_SHOW_ICONS):
            self._hide_waypoint_icons()

        if self._stage:
            self.__register_stage_update()
        self._update_setting_sub = omni.kit.app.SettingChangeSubscription(
            SETTINGS_WAYPOINT_SHOW_ICONS, lambda *_: self._on_show_icons_changed()
        )
        self._update_current_tool_sub = omni.kit.app.SettingChangeSubscription(
            CURRENT_TOOL_PATH, lambda *_: self._on_current_tool_changed()
        )
        OmniConnectionManager.get_instance().accept_all_connections = True

        self.__register_display_setting()

        self.__init_hotkeys()
        self._enable_hotkeys_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_WAYPOINT_ENABLE_HOTKEYS,
            self._on_hotkeys_enabled_changed,
        )

        global g_singleton
        g_singleton = self
        WaypointCard.WAYPOINT_EXTENSION_INSTANCE = self

        # Adding viewport_widget in case the applications uses a widget instead of a window viewport
        self._viewport_widget = None
        self._main_window_name = None
        self._hide_in_stage_window_disabled = False

        self._waypoint_thumbnail_directory = None

    def __init_hotkeys(self):
        self._hotkey_reg = None
        self._hotkey_context = None
        self._action_reg = None
        self._actions = {}
        self._hotkeys = {}
        self._register_hotkeys()

    def on_shutdown(self):  # pragma: no cover
        """Handles cleanup on shutdown. Deregisters the PlaylistCard, hotkeys, and stage updates; unsubscribes from settings change events; destroys the preference window; clears notifications; and resets the current and editing waypoints."""
        PlaylistCard.deregister(WaypointCard.PLAYLIST_CARD_TYPE_WAYPOINT)
        self._deregister_all_hotkeys()
        self._action_reg = None
        self._hotkey_reg = None
        self._hotkey_context = None
        global g_singleton
        g_singleton = None
        WaypointCard.WAYPOINT_EXTENSION_INSTANCE = None

        if self._enable_hotkeys_sub is not None:
            self._settings.unsubscribe_to_change_events(self._enable_hotkeys_sub)
            self._enable_hotkeys_sub = None

        try:
            from omni.usd_presenter.sidecar import deregister_data

            deregister_data("Waypoints")
            self.__sidecar_data = None
        except ImportError:
            self.__sidecar_data = None

        self.__deregister_display_setting()

        self._app = None
        self.editing_waypoint = None
        self.current_waypoint = None
        if self._preference_window is not None:
            self._preference_window.destroy()
            self._preference_window = None

        self._notifications.clear()
        self._deregister_check_waypoint_changed()
        self._update_setting_sub = None
        self._update_current_tool_sub = None
        self._stage_event_subs.clear()
        self._stage_event_subs = None
        self.__deregister_stage_update()

        self._hide_waypoint_icons()

    @property
    def viewport_widget(self) -> None:
        """Gets the viewport widget.

        Returns:
            None: The viewport widget is stored internally.
        """
        return self._viewport_widget

    def set_viewport_widget(self, viewport_widget) -> None:
        """Sets the viewport widget.

        Args:
            viewport_widget (object): The widget to be used as the viewport.
        """
        self._viewport_widget = viewport_widget
        # Make sure the waypoints pick up the new viewport
        self._waypoints.clear()
        self._refresh_waypoints()

    @property
    def waypoint_thumbnail_directory(self) -> str:
        return self._waypoint_thumbnail_directory

    @waypoint_thumbnail_directory.setter
    def waypoint_thumbnail_directory(self, directory: str) -> None:
        self._waypoint_thumbnail_directory = directory

    @property
    def main_window_name(self) -> None:
        """Gets the main window name.

        Returns:
            None: The main window name is stored internally.
        """
        return self._main_window_name

    def set_main_window_name(self, main_window_name) -> None:
        """Sets the main window name.

        Args:
            main_window_name (object): The name to be set for the main window.
        """
        self._main_window_name = main_window_name

    @property
    def hide_in_stage_window_disabled(self):
        """Gets the hide_in_stage_window_disabled flag.

        Returns:
            bool: True if saving of the hide in stage window metadata is disabled.
        """
        return self._hide_in_stage_window_disabled

    @hide_in_stage_window_disabled.setter
    def hide_in_stage_window_disabled(self, is_disabled: bool) -> None:
        """Sets the hide_in_stage_window_disabled flag. Controls saving of the hide in stage window metadata.

        Args:
            is_disabled (bool): Flag to disable saving the hide in stage window metadata.
        """
        # Give an option to not save `hide_in_stage_window` metadata for alternate apps
        self._hide_in_stage_window_disabled = is_disabled

    @property
    def current_waypoint(self) -> Optional[ViewportWaypoint]:
        """Gets the current waypoint.

        Returns:
            Optional[ViewportWaypoint]: The currently active waypoint.
        """
        return self._current_waypoint

    @current_waypoint.setter
    def current_waypoint(self, waypoint: Optional[ViewportWaypoint]) -> None:
        """Sets the current waypoint. Updates settings, adjusts subscriptions, and registers or deregisters change checks accordingly.

        Args:
            waypoint (Optional[ViewportWaypoint]): The new current waypoint.
        """
        if self._current_waypoint == waypoint:
            return
        carb.log_info(
            f"Change current waypoint from {self._current_waypoint.name if self._current_waypoint else 'None'} to {waypoint.name if waypoint else 'None'}"
        )
        if self._current_waypoint is not None:
            self._current_waypoint.subscribe_changes(False)

        self._current_waypoint = waypoint
        if self._current_waypoint is None:
            self._settings.set_string(SETTINGS_WAYPOINT_ACTIVE, "")
            self._deregister_check_waypoint_changed()
        else:
            self._settings.set_string(SETTINGS_WAYPOINT_ACTIVE, self._current_waypoint.name)
            self._register_check_waypoint_changed()

    @property
    def editing_waypoint(self) -> Optional[ViewportWaypoint]:
        """Gets the editing_waypoint property. Returns the current viewport waypoint being edited.

        Returns:
            Optional[ViewportWaypoint]: The editing waypoint instance.
        """
        return self._editing_waypoint

    @editing_waypoint.setter
    def editing_waypoint(self, waypoint: Optional[ViewportWaypoint]) -> None:
        """Sets the editing_waypoint property. Updates settings and recalls the provided waypoint if valid, then deregisters waypoint change checking.

        Args:
            waypoint (ViewportWaypoint): Editing waypoint instance to set.
        """
        self._editing_waypoint = waypoint
        if self._editing_waypoint is None:
            self._settings.set(SETTINGS_WAYPOINT_EDITING, "")
        else:
            self._settings.set(SETTINGS_WAYPOINT_EDITING, self._editing_waypoint.name)
            # In edit mode, never check waypoint changes, keep current waypoint
            self.recall_waypoint(waypoint)
            self._deregister_check_waypoint_changed()

    @property
    def edit_target(self) -> Sdf.Layer:
        """Gets the edit_target property. Returns the current Sdf.Layer used as the edit target.

        Returns:
            Sdf.Layer: The current edit target layer.
        """
        return self._edit_target

    @edit_target.setter
    def edit_target(self, layer: Sdf.Layer):
        """Sets the edit_target property after validating its type and local layer stack inclusion.

        Args:
            layer (Sdf.Layer): USD layer that must be part of the local layer stack.
        """
        # The layer must either be None or of type Sdf.layer
        if layer is not None and not isinstance(layer, Sdf.Layer):
            carb.log_error(
                f"Could not set WaypointExtension.edit_target to {layer}. "
                f"The value must be of type Usd.Layer, not {type(layer)}."
            )
            return

        # The layer must be within the local layer stack
        if layer is not None and not self._stage.HasLocalLayer(layer):
            carb.log_error(
                f"Could not set WaypointExtension.edit_target to {layer}. "
                f"The provided layer must be within the local layer stack of {self._stage.GetRootLayer().identifier}"
            )
            return

        self._edit_target = layer

    @property
    def edit_context(self) -> Usd.EditContext:
        """Gets the current edit context for waypoint operations. Considers sidecar data and edit target overrides.

        Returns:
            Usd.EditContext: The effective edit context.
        """
        # Resolve any edit context conflict by prioritizing the sidecar
        if self.__sidecar_data and self._edit_target:
            carb.log_warn(
                "Both SideCarData and WaypointExtension had edit context overrides for WaypointExtension. "
                "The returned edit context will be from SideCarData.edit_context."
            )

        # Override the edit context with either WaypointExtension or sidecar if necessary
        if self.__sidecar_data:
            return self.__sidecar_data.edit_context
        if self._edit_target:
            return Usd.EditContext(omni.usd.get_context().get_stage(), self._edit_target)

        return Usd.EditContext(omni.usd.get_context().get_stage(), Usd.EditTarget(None))

    def register_callback(self, notification: WaypointChangeCallbacks) -> None:
        """Registers a waypoint callback by appending it to the notifications list.

        Args:
            notification (WaypointChangeCallbacks): Callback instance to register.
        """
        self._notifications.append(notification)

    def deregister_callback(self, notification: WaypointChangeCallbacks) -> None:
        """Deregisters a waypoint callback by removing it from the notifications list.

        Args:
            notification (WaypointChangeCallbacks): Callback instance to remove.
        """
        if notification in self._notifications:
            self._notifications.remove(notification)

    def is_waypoint_prim(self, prim_path: str, exact: bool = False) -> bool:
        """Checks if the given prim_path represents a valid waypoint prim. When exact is true, the prim must be an immediate child of the waypoint root.

        Args:
            prim_path (str): USD prim path to check.
            exact (bool): If true, require prim_path to be a direct child.

        Returns:
            bool: True if prim_path corresponds to a waypoint prim, otherwise false.
        """
        if str(prim_path).startswith(WAYPOINT_ROOT_PRIM_PATH + "/"):
            if exact:
                sub_paths = str(prim_path)[len(WAYPOINT_ROOT_PRIM_PATH + "/") :].split("/")
                return len(sub_paths) == 1
            else:
                return True
        else:
            return False

    def create_waypoint(
        self, new_waypoint_path: str = "", icon_url: str = WAYPOINT_ICON_URL, icon_click: callable = None
    ):
        """Creates a new waypoint if no duplicate exists. Determines an available waypoint path and schedules a creation job with a wait prompt.

        Args:
            new_waypoint_path (str): Base path for new waypoint; default is empty.
            icon_url (str): URL for waypoint icon.
            icon_click (callable): Callback invoked on icon click.
        """
        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Create Waypoint")
            return

        # Find an existing waypoint with the same settings, or None
        existing_waypoint = self._find_existing_match()
        if existing_waypoint:
            self._warn_duplicate_waypoint(existing_waypoint.name)
            return

        self._new_waypoint_parent = ""
        self._waypoint_path = omni.usd.get_stage_next_free_path(
            omni.usd.get_context().get_stage(), f"{WAYPOINT_ROOT_PRIM_PATH}/Waypoint_00", False
        )
        self._new_waypoint_name = cast(str, Sdf.Path(self._waypoint_path).name)

        async def __create_waypoint_job():
            with Prompt("Please Wait", "Creating waypoint...", [], [], True):
                for i in range(2):
                    await omni.kit.app.get_app().next_update_async()
                self._create_waypoint(self._new_waypoint_name, icon_url=icon_url, icon_click=icon_click)

        asyncio.ensure_future(__create_waypoint_job())

    async def create_waypoint_async(
        self, new_waypoint_path: str = "", icon_url: str = WAYPOINT_ICON_URL, icon_click: callable = None
    ):
        """Creates a new waypoint asynchronously if no duplicate exists. Determines an available waypoint path and triggers asynchronous creation with a wait prompt.

        Args:
            new_waypoint_path (str): Base path for new waypoint; default is empty.
            icon_url (str): URL for waypoint icon.
            icon_click (callable): Callback invoked on icon click.
        """
        # Find an existing waypoint with the same settings, or None
        existing_waypoint = self._find_existing_match()
        if existing_waypoint:
            self._warn_duplicate_waypoint(existing_waypoint.name)
            return

        with Prompt("Please Wait", f"Creating waypoint...", [], [], True):
            for i in range(2):
                await omni.kit.app.get_app().next_update_async()
            self._new_waypoint_parent = ""
            new_path = new_waypoint_path if new_waypoint_path else f"{WAYPOINT_ROOT_PRIM_PATH}/Waypoint_00"
            self._waypoint_path = omni.usd.get_stage_next_free_path(omni.usd.get_context().get_stage(), new_path, False)
            self._new_waypoint_name = cast(str, Sdf.Path(self._waypoint_path).name)

            self.__deregister_stage_update()
            await self._create_waypoint_async(self._new_waypoint_name, icon_url=icon_url, icon_click=icon_click)
            self.__register_stage_update()

    def begin_edit_waypoint(self, waypoint: ViewportWaypoint) -> bool:
        """Starts editing the given waypoint if allowed by checking sidecar read-only and current editing status.

        Args:
            waypoint (ViewportWaypoint): Waypoint instance to begin editing.

        Returns:
            bool: True if editing starts successfully, False otherwise.
        """
        self._set_current_tool_self()

        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Edit Waypoint")
            return False

        carb.log_info(f"Begin edit waypoint: {waypoint.name}")
        if self._editing_waypoint:
            carb.log_warn(f"[Waypoint] {self._editing_waypoint.name} already in edit!")
            return False

        self.editing_waypoint = waypoint
        return True

    def end_edit_waypoint(self, waypoint: ViewportWaypoint, save: bool, create: bool = False) -> None:
        """Ends editing the provided waypoint. If the waypoint is not the currently editing one, a warning is logged and the operation is aborted. Within an appropriate edit context, if create is True a new waypoint is created; if save is True, changes are saved; else the waypoint is recalled. Resets the editing waypoint and current tool.

        Args:
            waypoint (ViewportWaypoint): Waypoint instance that is being edited.
            save (bool): Flag to save modifications.
            create (bool): Flag to create a new waypoint if needed.
        """
        carb.log_info(f"End edit waypoint: {waypoint.name}")
        if waypoint != self._editing_waypoint:
            carb.log_warn(
                f"Cannot end edit waypoint {waypoint.name} since it is not in edit ({self._editing_waypoint.name if self._editing_waypoint else 'None'})!"
            )
            return

        with self.edit_context if self.edit_target else nullcontext():
            if create:
                self.create_waypoint()
            elif save:
                waypoint.create(lambda w=waypoint: self._on_waypoint_changed(w))
            else:
                self.recall_waypoint(waypoint, force=True)
            if self.current_waypoint is not None:
                self._register_check_waypoint_changed()

            self.editing_waypoint = None
            self._reset_current_tool()

    def delete_waypoint(self, waypoint: Optional[ViewportWaypoint]) -> None:
        """Deletes the specified waypoint if allowed. Removes its icon from the display, removes it from the internal storage, and notifies observers about the deletion.

        Args:
            waypoint (Optional[ViewportWaypoint]): Waypoint instance to delete.
        """
        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Delete Waypoint")
            return

        if waypoint:
            with self.edit_context if self.edit_target else nullcontext():
                if self.current_waypoint == waypoint:
                    self.current_waypoint = None

                self._remove_waypoint_icon_with_path(waypoint.path)
                if waypoint.name in self._waypoints:
                    self._waypoints.pop(waypoint.name)
                waypoint.delete()
                if self.__sidecar_data:  # pragma: no cover
                    self.__sidecar_data.save()
                for n in self._notifications:
                    if n.on_waypoint_deleted is not None:
                        n.on_waypoint_deleted(waypoint)

    def recall_waypoint(
        self,
        waypoint: Optional[ViewportWaypoint],
        without_camera=False,
        enable_settings: Optional[List[str]] = None,
        disable_settings: Optional[List[str]] = None,
        force: bool = False,
        recall_timeline: bool = True,
    ) -> None:
        """Recalls a waypoint by restoring its camera settings and timeline position. If the waypoint is already current and force is not set, the recall is skipped.

        Args:
            waypoint (Optional[ViewportWaypoint]): Waypoint instance to recall.
            without_camera (bool): If True, does not adjust the camera.
            enable_settings (Optional[List[str]]): List of settings to enable during recall.
            disable_settings (Optional[List[str]]): List of settings to disable during recall.
            force (bool): If True, forces the recall even if already current.
            recall_timeline (bool): If True, updates the timeline to the waypoint's frame.
        """
        if not waypoint:
            self.current_waypoint = None
            return

        carb.log_info(f"Recall waypoint {waypoint.name}")
        if self.current_waypoint is not None:
            if waypoint == self.current_waypoint and not force:
                carb.log_info("Skip recall waypoint since it is already current one.")
                return

        waypoint.recall(
            without_camera=without_camera, enable_settings=enable_settings, disable_settings=disable_settings
        )
        if recall_timeline:
            self._timeline.set_current_time(waypoint.frame if waypoint.frame is not None else 0)
        self.current_waypoint = waypoint

    def rename_waypoint(self, waypoint: ViewportWaypoint, new_name: str) -> bool:
        """Renames the specified waypoint if the new name is different, valid as a USD path, and not already used. Updates the waypoint icon and notifies observers on a successful rename.

        Args:
            waypoint (ViewportWaypoint): Waypoint instance to rename.
            new_name (str): The new name proposed for the waypoint.

        Returns:
            bool: True if the renaming is successful, False otherwise.
        """
        if waypoint.name == new_name:
            return True
        if new_name in self._waypoints:
            carb.log_warn(
                f"Can not rename viewport waypoint from '{waypoint.name}'' to '{new_name}', the destination already exists"
            )
            return False

        if not Sdf.Path.IsValidPathString(new_name):
            carb.log_warn(
                f"Can not rename viewport waypoint from '{waypoint.name}'' to '{new_name}' as it's not a valid USD path"
            )
            return False

        with self.edit_context if self.edit_target else nullcontext():
            self._waypoints.pop(waypoint.name)
            old_path = waypoint.path
            if waypoint.rename(new_name):
                self._waypoints[new_name] = waypoint

                # update the prim icon
                self._prim_icon.remove_prim_icon(old_path)
                self._prim_icon.add_prim_icon(waypoint.path, waypoint.icon_url)

                # update the visibility
                self._on_show_icons_changed()
                self._on_waypoint_changed(waypoint)
                return True
            else:
                carb.log_warn(f"Can not rename viewport waypoint from '{waypoint.name}'' to '{new_name}'")
                return False

    def get_waypoints(self) -> List[ViewportWaypoint]:
        """Returns all stored viewport waypoints.

        Returns:
            List[ViewportWaypoint]: List of viewport waypoint instances.
        """
        return self._waypoints.values()

    def get_waypoint(self, name) -> Optional[ViewportWaypoint]:
        """Retrieves a viewport waypoint based on its name.

        Args:
            name (str): Name of the waypoint to look up.

        Returns:
            Optional[ViewportWaypoint]: The waypoint instance if found, otherwise None.
        """
        if name in self._waypoints:
            return self._waypoints[name]

        return None

    def get_waypoint_from_prim_path(self, path: str) -> Optional[ViewportWaypoint]:
        """Retrieves a waypoint using its USD prim path. Extracts the waypoint name from the path and returns the matching waypoint if it exists.

        Args:
            path (str): USD prim path used to determine the waypoint.

        Returns:
            Optional[ViewportWaypoint]: The waypoint instance if found, otherwise None.
        """
        if self.is_waypoint_prim(path):
            sub_path = path[len(WAYPOINT_ROOT_PRIM_PATH + "/") :]
            name = sub_path.split("/")[0]
            return self.get_waypoint(name)
        else:
            return None

    def show_preference(self, x: float, y: float):
        """Displays the preference window at the specified screen coordinates after setting the current tool.

        Args:
            x (float): The x coordinate for the preference window position.
            y (float): The y coordinate for the preference window position.
        """
        self._set_current_tool_self()

        if self._preference_window is None:
            self._preference_window = WaypointPerefenceWindow()

        self._preference_window.show(x, y)

    def can_edit_waypoint(self, waypoint: ViewportWaypoint, show_messages=True) -> bool:
        """Checks whether the given waypoint can be edited. This method always returns True.

        Args:
            waypoint (ViewportWaypoint): Waypoint instance to check for editability.
            show_messages (bool): Flag to display messages if editing is not permitted.

        Returns:
            bool: True indicating the waypoint is editable.
        """
        return True

    def _find_existing_match(self):
        if not self.editing_waypoint and self.current_waypoint:
            return self.current_waypoint
        else:
            for waypoint in self._waypoints.values():
                if not waypoint.is_dirty:
                    return waypoint
            return None

    def _warn_duplicate_waypoint(self, existing_waypoint_name):
        carb.log_warn(f"Waypoint {existing_waypoint_name} already exists with same settings!")
        try:
            import omni.kit.notification_manager as nm

            nm.post_notification(f"Waypoint {existing_waypoint_name} already exists with same settings.")
        except ImportError:  # pragma: no cover
            pass

        return

    def _refresh_waypoints(self):
        self._clear_waypoints()
        self._waypoints.clear()
        current_waypoint_name = self.current_waypoint.name if self.current_waypoint else None

        waypoint_root_path = WAYPOINT_ROOT_PRIM_PATH
        stage = self._usd_context.get_stage()
        if not stage:
            return
        waypoint_root_node = stage.GetPrimAtPath(waypoint_root_path)
        if not waypoint_root_node:
            carb.log_info("No waypoint prim found!")
            self.current_waypoint = None
            return

        for waypoint_prim in waypoint_root_node.GetChildren():
            self.__add_waypoint_from_prim(waypoint_prim)

        if current_waypoint_name:
            if current_waypoint_name not in self._waypoints:
                self.current_waypoint = None

        for n in self._notifications:
            n.on_reset()

    def _clear_waypoints(self):
        self._waypoints.clear()
        self.current_waypoint = None
        self._hide_waypoint_icons()
        # OM-84954
        # Clearing the prim_icon interface is bad news for all other consumers of the extension, as it is a shared model
        # Much better to only remove the icons we directly care about.
        icon_model = self._prim_icon.get_model()
        if icon_model:
            to_remove = {path for path in icon_model.get_prim_paths() if path.startswith(WAYPOINT_ROOT_PRIM_PATH)}
            for path in to_remove:
                self._prim_icon.remove_prim_icon(path)
        for n in self._notifications:
            n.on_reset()

    async def _create_waypoint_async(
        self, waypoint_name: str, icon_url: str = WAYPOINT_ICON_URL, icon_click: callable = None
    ):
        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Create Waypoint (async)")
            return

        with self.edit_context:
            waypoint = ViewportWaypoint(
                waypoint_name,
                self._new_waypoint_parent,
                icon_url=icon_url,
                icon_click=icon_click,
                sidecar_data=self.__sidecar_data,
                edit_context=self.edit_context,
                edit_target_exists=bool(self.edit_target),
                hide_in_stage_window_disabled=self.hide_in_stage_window_disabled,
                viewport_widget=self.viewport_widget,
            )
            waypoint.frame = self._timeline.get_current_time()
            stage = self._usd_context.get_stage()
            stage.DefinePrim(waypoint.path)
            await waypoint.create_async()

        if len(self._new_waypoint_parent) == 0:
            self._waypoints[waypoint_name] = waypoint
            self.current_waypoint = waypoint

        self._on_waypoint_created(waypoint)

    def _create_waypoint(self, waypoint_name: str, icon_url: str = WAYPOINT_ICON_URL, icon_click: callable = None):
        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Create Waypoint")
            return

        with self.edit_context:
            waypoint = ViewportWaypoint(
                waypoint_name,
                self._new_waypoint_parent,
                icon_url=icon_url,
                icon_click=icon_click,
                sidecar_data=self.__sidecar_data,
                edit_context=self.edit_context,
                edit_target_exists=bool(self.edit_target),
                hide_in_stage_window_disabled=self.hide_in_stage_window_disabled,
                viewport_widget=self.viewport_widget,
            )
            waypoint.frame = self._timeline.get_current_time()
            stage = self._usd_context.get_stage()

            root = self._stage.GetPrimAtPath(WAYPOINT_ROOT_PRIM_PATH)
            if not root:
                create_data_only_prim(stage, WAYPOINT_ROOT_PRIM_PATH)

            create_data_only_prim(stage, waypoint.path)
            waypoint.create(self._on_waypoint_created)

        if len(self._new_waypoint_parent) == 0:
            self._waypoints[waypoint_name] = waypoint
            self.current_waypoint = waypoint

    def _on_waypoint_created(self, waypoint: ViewportWaypoint):
        if waypoint:
            if self.__sidecar_data:  # pragma: no cover
                self.__sidecar_data.save()

            # OM-105317 - We want to always add the icon for newly created waypoints, but we might want to hide it.
            self._prim_icon.add_prim_icon(waypoint.path, waypoint.icon_url)
            self._prim_icon.set_icon_click_fn(
                waypoint.path, waypoint.icon_click or self._recall_waypoint_from_prim_path
            )
            if self._waypoint_icon_visible:
                self._show_waypoint_icons()
            else:
                self._hide_waypoint_icons()

            for n in self._notifications:
                n.on_waypoint_created(waypoint)

    def _on_stage_opened(self, _):
        self.current_waypoint = None
        self.editing_waypoint = None
        self._refresh_waypoints()
        self._stage = self._usd_context.get_stage()
        self.__register_stage_update()
        asyncio.ensure_future(self._apply_visibility_delayed())

    def _on_stage_closed(self, _):
        self.__deregister_stage_update()
        self.current_waypoint = None
        self.editing_waypoint = None
        self._clear_waypoints()

    async def _apply_visibility_delayed(self):
        await omni.kit.app.get_app().next_update_async()
        # workaround: simply calling hide didn't work
        visible = self._waypoint_icon_visible
        self._settings.set(SETTINGS_WAYPOINT_SHOW_ICONS, not visible)
        self._settings.set(SETTINGS_WAYPOINT_SHOW_ICONS, visible)

    def _recall_waypoint_from_prim_path(self, prim_path: str):
        waypoint = self.get_waypoint_from_prim_path(prim_path)
        if waypoint:
            self.recall_waypoint(waypoint)

    def _show_waypoint_icons(self):
        waypoint_root_path = WAYPOINT_ROOT_PRIM_PATH
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        waypoint_root_node = stage.GetPrimAtPath(waypoint_root_path)
        if waypoint_root_node:
            for child in waypoint_root_node.GetChildren():
                self._prim_icon.show_prim_icon(child.GetPrimPath().pathString)

    def _hide_waypoint_icons(self):
        waypoint_root_path = WAYPOINT_ROOT_PRIM_PATH
        stage = omni.usd.get_context().get_stage()
        if stage is not None:
            waypoint_root_node = stage.GetPrimAtPath(waypoint_root_path)
            if waypoint_root_node:
                for child in waypoint_root_node.GetChildren():
                    self._prim_icon.hide_prim_icon(child.GetPrimPath().pathString)

    def _remove_waypoint_icon_with_path(self, waypoint_path):
        waypoint_root_path = WAYPOINT_ROOT_PRIM_PATH
        stage = omni.usd.get_context().get_stage()
        waypoint_root_node = stage.GetPrimAtPath(waypoint_root_path)
        if waypoint_root_node:
            for child in waypoint_root_node.GetChildren():
                if waypoint_path == child.GetPrimPath().pathString:
                    self._prim_icon.remove_prim_icon(waypoint_path)
                    break

    def _on_show_icons_changed(self):
        icon_visibiltiy = self._is_waypoint_icon_visible()
        if self._waypoint_icon_visible == icon_visibiltiy:
            return

        self._waypoint_icon_visible = icon_visibiltiy
        if icon_visibiltiy:
            self._show_waypoint_icons()
        else:
            self._hide_waypoint_icons()

    def _on_current_tool_changed(self):
        new_tool = self._settings.get_as_string(CURRENT_TOOL_PATH)
        if new_tool != EXTENSION_NAME:
            # Relinquish any modal operations here
            if self._preference_window:
                self._preference_window.hide()

    def _set_current_tool_self(self):
        current_tool = self._settings.get_as_string(CURRENT_TOOL_PATH)
        if current_tool != EXTENSION_NAME:
            self._settings.set(CURRENT_TOOL_PATH, EXTENSION_NAME)

    def _reset_current_tool(self):
        current_tool = self._settings.get_as_string(CURRENT_TOOL_PATH)
        if current_tool == EXTENSION_NAME:
            self._settings.set(CURRENT_TOOL_PATH, "navigation")

    def _register_check_waypoint_changed(self):
        if self._update_sub is None:
            try:
                from carb.eventdispatcher import get_eventdispatcher
                from omni.kit.app import GLOBAL_EVENT_UPDATE

                self._update_sub = get_eventdispatcher().observe_event(
                    observer_name="omni.kit.waypoint.core:check_waypoint_changed",
                    event_name=GLOBAL_EVENT_UPDATE,
                    on_event=self._check_current_waypoint_changed,
                )
            except ImportError:
                self._update_sub = self._app.get_update_event_stream().create_subscription_to_pop(
                    self._check_current_waypoint_changed, name="waypoint check changes"
                )
        if self.current_waypoint:
            self.current_waypoint.subscribe_changes(True)

    def _deregister_check_waypoint_changed(self):
        self._update_sub = None

    def _check_current_waypoint_changed(self, event):
        # OMPE-63235: Don't check waypoints when stage is closing, to avoid crash with Sdf_PathNode::GetPathToken
        # like crash with uuid 258cef50-2715-410c-8217-d147bea6cab6
        if self._usd_context.get_stage_state() == omni.usd.StageState.CLOSING:
            return
        if self.current_waypoint is not None:
            try:
                if self.current_waypoint.is_dirty:
                    self.current_waypoint = None
            except Exception as e:  # pragma: no cover
                carb.log_warn(f"Failed to check current waypoint because {e}")
                self.current_waypoint = None

    def _is_waypoint_icon_visible(self) -> bool:
        icon_visibiltiy = self._settings.get(SETTING_PERSISTENT + SETTINGS_WAYPOINT_SHOW_ICONS)
        if icon_visibiltiy is None:
            icon_visibiltiy = self._settings.get(SETTINGS_WAYPOINT_SHOW_ICONS)
        return icon_visibiltiy

    def _on_waypoint_changed(self, waypoint):
        if self._waypoint_icon_visible and waypoint:
            # OM-80331: Waypoint icon need to update while waypoint camera may changed
            self._prim_icon.remove_prim_icon(waypoint.path)
            self._prim_icon.add_prim_icon(waypoint.path, waypoint.icon_url)
            self._prim_icon.set_icon_click_fn(
                waypoint.path, waypoint.icon_click or self._recall_waypoint_from_prim_path
            )
        for n in self._notifications:
            if self.__sidecar_data:  # pragma: no cover
                self.__sidecar_data.save()
            if n.on_waypoint_changed is not None:
                n.on_waypoint_changed(waypoint)

    def __register_display_setting(self):  # pragma: no cover
        try:
            from omni.kit.viewport.menubar.core import CategoryStateItem
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            inst = get_display_instance()
            self._waypoint_viewport_item = CategoryStateItem("Waypoint", setting_path=SETTINGS_WAYPOINT_SHOW_ICONS)
            inst.register_custom_category_item("Show By Type", self._waypoint_viewport_item)
        except ImportError:
            self._waypoint_viewport_item = None

    def __deregister_display_setting(self):  # pragma: no cover
        try:
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            inst = get_display_instance()
            if self._waypoint_viewport_item:
                inst.deregister_custom_category_item("Show By Type", self._waypoint_viewport_item)
        except ImportError:  # pragma: no cover
            pass

    def __add_waypoint_from_prim(self, prim: Usd.Prim):
        if not prim:
            return None
        for waypoint in self._waypoints.values():
            if waypoint.path == prim.GetPath().pathString:
                return None
        else:
            with self.edit_context if self.edit_target else nullcontext():
                waypoint = ViewportWaypoint(
                    "",
                    sidecar_data=self.__sidecar_data,
                    edit_context=self.edit_context,
                    edit_target_exists=bool(self.edit_target),
                    hide_in_stage_window_disabled=self.hide_in_stage_window_disabled,
                    viewport_widget=self.viewport_widget,
                )
                if waypoint.create_from_prim(prim):
                    self._waypoints[waypoint.name] = waypoint
                    self._prim_icon.add_prim_icon(waypoint.get_usd_prim_path(), WAYPOINT_ICON_URL)
                    self._prim_icon.set_icon_click_fn(
                        waypoint.get_usd_prim_path(), self._recall_waypoint_from_prim_path
                    )
                    return waypoint
                else:  # pragma: no cover
                    carb.log_warn(f"Failed to create any viewport waypoint from {prim}. Ignoring it.")
                    return None

    def __register_stage_update(self):
        self.__stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, self._stage)

    def __deregister_stage_update(self):
        self.__stage_listener = None

    @Trace.TraceFunction
    def _on_objects_changed(self, notice, stage):
        """Called by Usd.Notice.ObjectsChanged"""
        if not stage or stage != self._stage:
            return

        dirty_prims_paths = []

        for p in notice.GetResyncedPaths():
            if p.IsAbsoluteRootOrPrimPath():
                dirty_prims_paths.append(p)
            # OMFP-2241 - Need to keep the thumbnail in sync regardless of scene size.
            # with OM-84028 we now cache the thumbnail processing so hopefully this is less of a pain point.
            # At least with Markup that appears to be the case.
            # OMFP-2558 - Waypoint sync for participants was broken - reverting MR 968 fixes it but only
            # at the cost of uncovering the sync issue for waypoint edit (i.e. OMFP-2241)
            elif p.pathString.endswith(UsdBakedPreview.ATTR_NAME):
                # OM-80451: for large scene, thumbnail data needs more time to sync in live mode
                # Need to create waypoint while thumbnail data created
                dirty_prims_paths.append(p)

        for p in notice.GetChangedInfoOnlyPaths():
            if p.HasPrefix(WAYPOINT_ROOT_PRIM_PATH):
                dirty_prims_paths.append(p.GetPrimPath())

        if not dirty_prims_paths:
            return

        self.__dirty_prim_paths.update(dirty_prims_paths)

        # Update in the next frame. We need it because we want to accumulate the affected prims
        if self.__prim_changed_task is None or self.__prim_changed_task.done():
            self.__prim_changed_task = asyncio.ensure_future(self.__delayed_prim_changed())

    @handle_exception
    @Trace.TraceFunction
    async def __delayed_prim_changed(self):
        await omni.kit.app.get_app().next_update_async()
        self.update_dirty()
        self.__prim_changed_task = None

    @Trace.TraceFunction
    def update_dirty(self):
        """
        Create/remove dirty items that was collected from TfNotice. Can be
        called any time to pump changes.
        """
        if not self.__dirty_prim_paths:
            return

        dirty_prim_paths = list(self.__dirty_prim_paths)
        self.__dirty_prim_paths = set()

        if not self._stage or self._stage != self._usd_context.get_stage():
            return

        for prim_path in dirty_prim_paths:
            path = prim_path.pathString
            if path.endswith(UsdBakedPreview.ATTR_NAME):
                path = path[: -len(UsdBakedPreview.ATTR_NAME) - 1]
            if path == "/":
                # For fetch, will trigger dirty to "/"
                self._refresh_waypoints()
            elif self.is_waypoint_prim(path, exact=True):
                prim = self._stage.GetPrimAtPath(path)
                if prim and prim.IsValid() and prim.IsActive():
                    waypoint = self.__add_waypoint_from_prim(prim)
                    if waypoint:
                        self._on_waypoint_created(waypoint)
                    else:
                        with self.edit_context if self.edit_target else nullcontext():
                            waypoint = self.__find_waypoint(path)
                            if waypoint and waypoint.create_from_prim(prim):
                                self._on_waypoint_changed(waypoint)
                else:
                    waypoint = self.__find_waypoint(path)
                    if waypoint:
                        self.delete_waypoint(waypoint)
            elif str(path) == WAYPOINT_ROOT_PRIM_PATH:
                # OM-80341: If waypoint root prim removed, need to refresh all waypoints
                prim = self._stage.GetPrimAtPath(path)
                self._refresh_waypoints()
                for n in self._notifications:
                    n.on_reset()

    def __find_waypoint(self, path: str) -> Optional[ViewportWaypoint]:
        for waypoint in self._waypoints.values():
            if waypoint.path == path:
                return waypoint
        return None

    def _register_hotkeys(self):
        enabled = self._settings.get_as_bool(SETTINGS_WAYPOINT_ENABLE_HOTKEYS) or False
        if self._hotkey_reg is None or self._action_reg is None:
            try:
                import omni.kit.actions.core
                import omni.kit.hotkeys.core

                self._hotkey_reg = omni.kit.hotkeys.core.get_hotkey_registry()
                self._action_reg = omni.kit.actions.core.get_action_registry()
                self._hotkey_context = omni.kit.hotkeys.core.get_hotkey_context()
            except ImportError:  # pragma: no cover
                carb.log_warn("Failed to import hotkeys extensions, waypoint hotkeys are disabled.")
                return
        if enabled:
            try:
                from omni.kit.hotkeys.core import HotkeyFilter
            except ImportError:  # pragma: no cover
                carb.log_warn("Failed to import hotkeys extensions, waypoint hotkeys are disabled.")
                return
            key = self._get_hotkey(SETTINGS_WAYPOINT_CREATE_HOTKEY, "ALT + W")
            self._register_hotkey("create", key, _create_waypoint)

            filter = HotkeyFilter(context=WAYPOINT_WINDOW_FOCUS_CONTEXT)
            key = self._get_hotkey(SETTINGS_WAYPOINT_NEXT_HOTKEY, "RIGHT")
            self._register_hotkey("next", key, _next_waypoint, filter=filter)
            key = self._get_hotkey(SETTINGS_WAYPOINT_PREVIOUS_HOTKEY, "LEFT")
            self._register_hotkey("previous", key, _previous_waypoint, filter=filter)

            key = self._get_hotkey(SETTINGS_WAYPOINT_DELETE_HOTKEY, "DEL")
            self._register_hotkey("delete", key, _delete_waypoint, filter=filter)
        else:
            self._deregister_all_hotkeys()

    def _register_hotkey(self, name: str, key: str, callback, filter=None) -> bool:
        enabled = self._settings.get_as_bool(SETTINGS_WAYPOINT_ENABLE_HOTKEYS) or False
        if not enabled or self._hotkey_reg is None or self._action_reg is None:
            return False

        if name in self._actions.keys() and name in self._hotkeys.keys():
            return False

        action_name = self._ext_name + "-" + name
        if name in self._actions.keys():
            action = self._actions[name]
        else:
            display_name = "waypoint::" + name
            action = self._action_reg.register_action(self._ext_name, action_name, callback, display_name)
            self._actions[name] = action
        if name not in self._hotkeys.keys():
            hotkey = self._hotkey_reg.register_hotkey(self._ext_name, key, self._ext_name, action_name, filter=filter)
            self._hotkeys[name] = hotkey

        return True

    def _deregister_all_hotkeys(self):  # pragma: no cover
        if self._action_reg and self._hotkey_reg and self._ext_name is not None:
            self._hotkey_reg.deregister_all_hotkeys_for_extension(self._ext_name)
            self._action_reg.deregister_all_actions_for_extension(self._ext_name)
            self._actions = {}
            self._hotkeys = {}

    def _get_hotkey(self, setting_path: str, default: str) -> str:
        hotkey = self._settings.get_as_string(setting_path)
        if hotkey is None or hotkey == "":
            self._settings.set_string(setting_path, default)
            return default
        return hotkey

    def _on_hotkeys_enabled_changed(self, item, event):
        self._register_hotkeys()


def _next_waypoint():
    try:
        from .widgets.playbar import WAYPOINT_PLAY_NEXT_EVENT
    except ImportError:  # pragma: no cover
        return
    carb.eventdispatcher.get_eventdispatcher().dispatch_event(WAYPOINT_PLAY_NEXT_EVENT, None)


def _previous_waypoint():
    try:
        from .widgets.playbar import WAYPOINT_PLAY_PREVIOUS_EVENT
    except ImportError:  # pragma: no cover
        return
    carb.eventdispatcher.get_eventdispatcher().dispatch_event(WAYPOINT_PLAY_PREVIOUS_EVENT, None)


def _create_waypoint():
    try:
        from .widgets.list_window import WaypointListWindow
    except ImportError:  # pragma: no cover
        return
    waypoints = get_instance()
    if waypoints:
        window = ui.Workspace.get_window("Waypoints")
        if window is None:
            window = WaypointListWindow()
        if not window.visible:
            window.visible = True
        waypoints.create_waypoint()


def _delete_waypoint():
    settings = carb.settings.get_settings()
    current_waypoint = settings.get_as_string(SETTINGS_WAYPOINT_ACTIVE)
    waypoints = get_instance()

    if current_waypoint and current_waypoint != "" and waypoints:

        async def __delete(name: str):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            waypoint = get_instance().get_waypoint(name)
            waypoints.delete_waypoint(waypoint)

        asyncio.ensure_future(__delete(current_waypoint))
