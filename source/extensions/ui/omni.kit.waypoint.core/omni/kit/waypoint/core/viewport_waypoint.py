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
import os
from contextlib import nullcontext
from typing import List, Optional, Tuple

import carb
import omni.kit.app
import omni.kit.commands
import omni.kit.prim.icon
import omni.timeline
import omni.usd
from pxr import Sdf, Usd

from .common import WAYPOINT_ICON_URL, WAYPOINT_ROOT_PRIM_PATH
from .pereference import WaypointPereference
from .settings import (
    AbstractWaypointSetting,
    CameraSetting,
    GeneralSetting,
    PrimVisibilitySetting,
    RendererSetting,
    SunstudySetting,
    ThumbnailSetting,
)


# A waypoint instance
class ViewportWaypoint:
    """A class representing a waypoint instance for viewport configurations. This class manages the state and settings associated with a viewport waypoint, including its name, path, icon, and multiple settings such as general, thumbnail, and camera configurations. It offers methods for creating, recalling, renaming, and deleting a waypoint, and provides properties to access related data such as the thumbnail, creation time, and camera prim.

    Args:
        name (str): The name of the waypoint.
        parent_path (str): The parent prim path for the waypoint. Defaults to an empty string, in which case a default root path is used.
        icon_url (str): The URL for the waypoint icon. Uses a default value if not specified.
        icon_click (callable): A callback function invoked when the waypoint icon is clicked.
        sidecar_data (Optional[Usd.EditContext]): An optional edit context that may override the primary edit context.
        edit_context (Usd.EditContext): The active USd edit context for applying changes.
        edit_target_exists (bool): Indicates if an edit target exists, affecting the edit context selection.
        hide_in_stage_window_disabled (bool): Disables the hiding of the waypoint in the stage window if set to True.
        viewport_widget: A widget instance used for viewport related settings such as thumbnail generation.
    """

    def __init__(
        self,
        name,
        parent_path="",
        icon_url: str = WAYPOINT_ICON_URL,
        icon_click: callable = None,
        sidecar_data: Optional[Usd.EditContext] = None,
        edit_context: Usd.EditContext = None,
        edit_target_exists: bool = False,
        hide_in_stage_window_disabled: bool = False,
        viewport_widget=None,
        thumbnail_dir: str = None,
    ):
        self.icon_url = icon_url
        self.icon_click = icon_click
        self._usd_prim = None
        self.__sidecar_data = sidecar_data
        self.__edit_context = edit_context
        self.__edit_target_exists = edit_target_exists
        self.__hide_in_stage_window_disabled = hide_in_stage_window_disabled

        self._general_setting = GeneralSetting(self.edit_context)
        thumbnail_path = os.path.join(thumbnail_dir, f"{name}.jpg") if thumbnail_dir else None
        self._thumbnail_setting = ThumbnailSetting(
            self.edit_context, viewport_widget=viewport_widget, thumbnail_path=thumbnail_path
        )
        self._camera_setting = CameraSetting(self.edit_context, viewport_widget=viewport_widget)
        self._waypoint_settings: List[AbstractWaypointSetting] = [
            self._general_setting,
            self._camera_setting,
            RendererSetting(self.edit_context),
            SunstudySetting(self.edit_context),
            PrimVisibilitySetting(self.edit_context),
            # Thumbnail is the last one to notify creation done after thumbnail generated
            self._thumbnail_setting,
        ]

        self._init(name, parent_path)

    # We call a delete function when removing a waypoint, not destroy.
    # def destroy(self):
    #     for setting in self._waypoint_settings:
    #         setting.destroy()

    def __repr__(self):
        return f'"{self._name}"'

    def __str__(self):
        return f'"{self._name}"'

    @property
    def name(self) -> str:
        """Gets the name of the viewport waypoint.

        Returns:
            str: The current name of the viewport waypoint.
        """
        return self._name

    @name.setter
    def name(self, new_name):
        """Sets the name of the viewport waypoint.

        Args:
            new_name (str): The new name for the waypoint.
        """
        self._name = new_name

    @property
    def path(self) -> str:
        """Gets the complete USD path of the viewport waypoint, concatenating its parent path and name.

        Returns:
            str: The complete USD path of the waypoint.
        """
        return f"{self._parent_path}/{self._name}"

    @property
    def thumbnail(self) -> Optional[str]:
        """Gets the thumbnail path for the viewport waypoint.

        Returns:
            Optional[str]: The thumbnail path if available, otherwise None.
        """
        return self._thumbnail_setting.thumbnail_path

    @property
    def thumbnail_data(self) -> Optional[Tuple[bytes, int, int]]:
        """Gets the thumbnail data for the viewport waypoint.

        Returns:
            Optional[Tuple[bytes, int, int]]: The thumbnail data as a tuple (bytes, width, height) if available, otherwise None.
        """
        return self._thumbnail_setting.thumbnail_data

    @property
    def create_time(self) -> Optional[str]:
        """Gets the creation time for the viewport waypoint.

        Returns:
            Optional[str]: The creation time if available, otherwise None.
        """
        return self._general_setting.data["create_time"]

    @property
    def created_by(self) -> Optional[str]:
        """Gets the creator information for the viewport waypoint.

        Returns:
            Optional[str]: The creator information if available, otherwise None.
        """
        return self._general_setting.data["created_by"]

    @property
    def comment(self) -> str:
        """Gets the comment of the viewport waypoint.

        Returns:
            str: The current comment of the viewport waypoint.
        """
        return self._general_setting.data["comment"]

    @comment.setter
    def comment(self, comment: str):
        """Sets the comment for the viewport waypoint. If the sidecar data is read only, it notifies without updating.

        Args:
            comment (str): The new comment to set.
        """
        # TODO: Need a better way later
        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Set Comment")
            return

        with self.edit_context:
            self._general_setting.set_comment(comment)

    @property
    def frame(self) -> float:
        """Gets the current frame from general setting data.

        Returns:
            float: The current frame number from settings.
        """
        return self._general_setting.data.get("frame", 0.0)

    @frame.setter
    def frame(self, frame: float):
        """Sets the frame time for the viewport waypoint.

        Args:
            frame (float): The new frame time value to set.
        """
        self._general_setting.set_frame(frame)

    @property
    def camera_prim(self) -> Optional[Usd.Prim]:
        """Gets the camera prim from camera setting.

        Returns:
            Optional[Usd.Prim]: The camera prim; may be None if not captured.
        """
        # Camera may not be captured
        return self._camera_setting.camera_prim

    @property
    def is_dirty(self) -> bool:
        """Gets the dirty state indicating if any waypoint setting is modified.

        Returns:
            bool: True if any setting is dirty.
        """
        for setting in self._waypoint_settings:
            if setting.is_dirty():
                return True
        return False

    @property
    def info(self) -> str:
        """Gets concatenated information from each waypoint setting.

        Returns:
            str: Concatenated info messages from settings.
        """
        info = []
        for setting in self._waypoint_settings:
            if setting.info:
                info.extend(setting.info)
        return info

    @property
    def edit_context(self) -> Usd.EditContext:
        """Gets the effective USD edit context with preference given to sidecar overrides.

        Returns:
            Usd.EditContext: The resolved edit context.
        """
        # Resolve any edit context conflict by prioritizing the sidecar
        if self.__sidecar_data and self.__edit_context:
            carb.log_warn(
                "Both SideCarData and WaypointExtension had edit context overrides for ViewportWaypoint. "
                "The returned edit context will be from SideCarData.edit_context."
            )

        # Override the edit context with either WaypointExtension or sidecar edits contexts if necessary
        if self.__sidecar_data:
            return self.__sidecar_data.edit_context
        if self.__edit_target_exists:
            return self.__edit_context

        return Usd.EditContext(omni.usd.get_context().get_stage(), Usd.EditTarget(None))

    @property
    def usd_prim(self) -> Optional[Usd.Prim]:
        """Gets the USD prim from the stage and caches it for future use.

        Returns:
            Optional[Usd.Prim]: The USD prim if available, otherwise None.
        """
        return self._get_usd_prim()

    def recall(
        self,
        without_camera=False,
        enable_settings: Optional[List[str]] = None,
        disable_settings: Optional[List[str]] = None,
    ):
        """Restores the viewport waypoint by processing recall settings and updating each setting.

        Args:
            without_camera (bool): Skip camera update when True.
            enable_settings (Optional[List[str]]): List of settings to enable during recall.
            disable_settings (Optional[List[str]]): List of settings to disable during recall.
        """
        recall_disable_settings = WaypointPereference.get_recall_disable_settings()
        if disable_settings is not None:
            recall_disable_settings.extend(disable_settings)
        if enable_settings is not None:
            for name in enable_settings:
                while name in recall_disable_settings:
                    recall_disable_settings.remove(name)

        usd_prim = self._get_usd_prim()
        if usd_prim:
            if without_camera:
                if self._camera_setting.get_name() not in recall_disable_settings:
                    recall_disable_settings.append(self._camera_setting.get_name())

            for setting in self._waypoint_settings:
                if setting.get_name() not in recall_disable_settings:
                    setting.recall(usd_prim)
        else:
            carb.log_warn("Failed to get prim of current viewport waypoint.")

    def stop_recalling(self):  # pragma: no cover (called by other extensions, but doesn't do anything either)
        """Stops the recalling process for the viewport waypoint. Does nothing by default."""
        pass

    def rename(self, new_name):
        """Renames the waypoint and updates the associated USD prim path and settings.

        Args:
            new_name (str): The new name for the waypoint.

        Returns:
            bool: True if rename is successful, otherwise False.
        """
        if not Sdf.Path.IsValidPathString(new_name):
            return False

        usd_prim = self._get_usd_prim()
        if usd_prim:
            old_path = self.get_usd_prim_path()
            self._name = new_name
            new_path = self.get_usd_prim_path()
            move_dict = {old_path: new_path}
            omni.kit.commands.execute(
                "MovePrimsCommand", paths_to_move=move_dict, on_move_fn=self._on_rename_fn, destructive=False
            )
            for setting in self._waypoint_settings:
                setting.update(omni.usd.get_context().get_stage().GetPrimAtPath(new_path))
            return True

        return False

    async def create_async(self, on_created_fn: callable = None):
        """Asynchronously creates a waypoint by initiating each setting's creation and saving data to the USD prim.

        Args:
            on_created_fn (callable): Function called after the waypoint is created.
        """
        carb.log_info(f"[Waypoint] Creating waypoint async...")
        capture_disable_settings = WaypointPereference.get_capture_disable_settings()

        for setting in self._waypoint_settings:
            setting.create(setting.get_name() not in capture_disable_settings)

        # Save current data (of models) to USD prim
        usd_prim = self._get_usd_prim()
        if usd_prim:
            for setting in self._waypoint_settings:
                if setting.is_valid():
                    await setting.save_async(usd_prim)

        carb.log_info(f"[Waypoint] Waypoint {self.name} created at {self.path}")

    def create(self, on_created_fn: callable = None):
        """Creates a waypoint using the current settings.

        Sets a callback on the thumbnail setting to invoke on_created_fn after successful creation. Iterates through each waypoint setting to perform creation and save the current data to the USD prim if available.

        Args:
            on_created_fn (callable): Callback invoked after waypoint creation.
        """
        carb.log_info(f"[Waypoint] Creating waypoint...")
        capture_disable_settings = WaypointPereference.get_capture_disable_settings()

        def __on_created(result: bool, callback):
            if result:
                callback(self)

        self._thumbnail_setting.on_created_fn = lambda r, c=on_created_fn: __on_created(r, c)

        for setting in self._waypoint_settings:
            setting.create(setting.get_name() not in capture_disable_settings)

        # Save current data (of models) to USD prim
        usd_prim = self._get_usd_prim()
        if usd_prim:
            for setting in self._waypoint_settings:
                if setting.is_valid():
                    setting.save(usd_prim)

        carb.log_info(f"[Waypoint] Waypoint {self.name} created at {self.path}")

    def create_from_prim(self, prim: Usd.Prim) -> bool:
        """Creates a waypoint from the provided USD prim.

        Initializes the waypoint name and parent path from the prim path and loads each setting from the prim data.

        Args:
            prim (Usd.Prim): The USD prim used to initialize the waypoint.

        Returns:
            bool: True if the waypoint was successfully created (has a valid
                name derived from the prim path and settings were loaded),
                otherwise False.
        """
        prim_path = prim.GetPath().pathString
        slash_index = prim_path.rfind("/")
        waypoint_name = prim_path[slash_index + 1 :]
        parent_path = prim_path[:slash_index]

        self._init(waypoint_name, parent_path)

        carb.log_info(f"load {waypoint_name}")
        for setting in self._waypoint_settings:
            setting.load(prim)

        return bool(self._name)

    def delete(self):
        """Deletes the waypoint and its associated data.

        Calls delete on each waypoint setting, removes the prim icon, deletes the USD prim if it exists, and re-initializes the waypoint.
        """
        for setting in self._waypoint_settings:
            setting.delete()

        prim_icons = omni.kit.prim.icon.get_prim_icon_interface()
        prim_icons.remove_prim_icon(self.path)

        if omni.usd.get_context().get_stage().GetPrimAtPath(self.path):
            omni.kit.commands.execute("DeletePrimsCommand", paths=[self.path], destructive=False)

        self._init()

    def get_usd_prim_path(self) -> str:
        """Returns the USD prim path by concatenating the parent path and waypoint name.

        Returns:
            str: The full USD prim path.
        """
        return self._parent_path + "/" + self._name

    def subscribe_changes(self, enable: bool) -> None:
        """Toggles change subscription for all waypoint settings.

        Args:
            enable (bool): Flag to enable or disable subscription to changes.
        """
        for setting in self._waypoint_settings:
            setting.subscribe_changes(enable)

    def _init(self, name="", parent_path=""):
        self._name = name
        if len(parent_path) > 0:
            self._parent_path = parent_path
        else:
            self._parent_path = WAYPOINT_ROOT_PRIM_PATH
        self._thumbnail = None
        self._usd_prim = None

        if not self.__hide_in_stage_window_disabled:
            asyncio.ensure_future(self._hide_waypoint_root_prim())

    def _on_rename_fn(self, old_prim_name: Sdf.Path, new_prim_name: Sdf.Path):
        pass

    def _get_usd_prim(self) -> Usd.Prim:
        if not self._usd_prim:
            prim_path = self.get_usd_prim_path()
            self._usd_prim = omni.usd.get_context().get_stage().GetPrimAtPath(prim_path)
        return self._usd_prim

    async def _hide_waypoint_root_prim(self):
        await omni.kit.app.get_app().next_update_async()
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        root_prim = stage.GetPrimAtPath(WAYPOINT_ROOT_PRIM_PATH)
        if root_prim and not root_prim.GetMetadata("hide_in_stage_window"):
            omni.usd.editor.set_hide_in_stage_window(root_prim, True)
