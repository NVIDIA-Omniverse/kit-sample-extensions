# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

import carb
import omni.usd
from omni.kit.playlist.core import PLAYLISTS_ROOT, PlaylistCard, PlaylistModel
from pxr import Sdf, Usd

PLAYLIST_CAMERA_PREFIX = "camera:"
PLAYLIST_ATTRIBUTE_PREFIX = "general:"
PLAYLIST_CAMERA_NAME = "names"
PLAYLIST_CAMERA_PATH = "paths"
PLAYLIST_CAMERA_TYPE = "types"
PLAYLIST_PLAY_PREFIX = "play:"
PLAYLIST_TRANSITION_TYPE = "transition_type"
PLAYLIST_TRANSITION_TIME = "transition_time"
PLAYLIST_ITEM_TIME = "item_time"
PLAYLIST_NAME = "name"


class PlaylistUsd:
    __instance__ = None

    def __init__(self):
        try:
            from omni.usd_presenter.sidecar import deregister_data, register_data

            self.__sidecar_data = register_data("Playlist")
            carb.log_info(f"[Playlist] Use sidecar")
        except ImportError:
            self.__sidecar_data = None
        PlaylistUsd.__instance__ = self

    @staticmethod
    def get_instance():
        if PlaylistUsd.__instance__ is None:
            PlaylistUsd.__instance__ = PlaylistUsd()
        return PlaylistUsd.__instance__

    @property
    def edit_context(self) -> Usd.EditContext:
        return (
            self.__sidecar_data.edit_context
            if self.__sidecar_data
            else Usd.EditContext(omni.usd.get_context().get_stage(), Usd.EditTarget(None))
        )

    def _get_root_prim(self, create: bool = False) -> Usd.Prim:
        prim = self.get_prim(PLAYLISTS_ROOT, create=create)
        return prim

    def get_playlist_paths(self):
        playlist_paths = []

        root_prim = self._get_root_prim()
        if not root_prim:
            return playlist_paths
        else:
            for child in root_prim.GetChildren():
                playlist_paths.append(child.GetPath().pathString)
            return playlist_paths

    def add_playlist(self, playlist: PlaylistModel, save=True):
        """Add playlist name"""
        prim = self._get_playlist_prim(playlist)
        if save and prim:
            self.save_playlist(playlist)

        if prim and self.__sidecar_data:
            self.__sidecar_data.save()

    def remove_playlist(self, playlist: PlaylistModel):
        if self._get_root_prim():
            self.remove_prim(playlist.path)

        if self.__sidecar_data:
            self.__sidecar_data.save()

    def save_playlist(self, playlist: PlaylistModel):
        if self.__sidecar_data and self.__sidecar_data.read_only:
            self.__sidecar_data.notify_read_only("Save Playlist")
            return

        prim = self._get_playlist_prim(playlist)
        if not prim:
            return

        with self.edit_context:
            # Attributes
            for attribute in playlist.attributes:
                self.set_prim_attribute(prim, PLAYLIST_ATTRIBUTE_PREFIX + attribute[0], attribute[1])

            # Play options
            self.set_prim_attribute(prim, PLAYLIST_PLAY_PREFIX + PLAYLIST_NAME, playlist.name)
            self.set_prim_attribute(prim, PLAYLIST_PLAY_PREFIX + PLAYLIST_TRANSITION_TYPE, playlist.transition_type)
            self.set_prim_attribute(
                prim,
                PLAYLIST_PLAY_PREFIX + PLAYLIST_TRANSITION_TIME,
                playlist.transition_time,
                type_name=Sdf.ValueTypeNames.Float,
            )
            self.set_prim_attribute(
                prim, PLAYLIST_PLAY_PREFIX + PLAYLIST_ITEM_TIME, playlist.item_time, type_name=Sdf.ValueTypeNames.Float
            )

            # Cameras
            camera_names = []
            camera_paths = []
            camera_types = []
            for item in playlist.get_item_children(None):
                camera_names.append(item.data.name)
                camera_paths.append(str(item.data.path))
                camera_types.append(str(item.data.type))
            self.set_prim_attribute(
                prim, PLAYLIST_CAMERA_PREFIX + PLAYLIST_CAMERA_NAME, camera_names, Sdf.ValueTypeNames.StringArray
            )
            self.set_prim_attribute(
                prim, PLAYLIST_CAMERA_PREFIX + PLAYLIST_CAMERA_PATH, camera_paths, Sdf.ValueTypeNames.StringArray
            )
            self.set_prim_attribute(
                prim, PLAYLIST_CAMERA_PREFIX + PLAYLIST_CAMERA_TYPE, camera_types, Sdf.ValueTypeNames.StringArray
            )

        if self.__sidecar_data:
            self.__sidecar_data.save()

    def load_playlist(self, playlist: PlaylistModel):
        attributes = []
        prim = self._get_playlist_prim(playlist)
        if not prim:
            return

        camera_names = []
        camera_paths = []
        camera_types = []
        for attribute in prim.GetAttributes():
            name = attribute.GetName()
            if name.startswith(PLAYLIST_ATTRIBUTE_PREFIX):
                # Attributes
                attributes.append([name[len(PLAYLIST_ATTRIBUTE_PREFIX) :], attribute.Get()])
            elif name.startswith(PLAYLIST_CAMERA_PREFIX):
                # Cameras
                name = name[len(PLAYLIST_CAMERA_PREFIX) :]
                if name == PLAYLIST_CAMERA_NAME:
                    camera_names = attribute.Get()
                elif name == PLAYLIST_CAMERA_PATH:
                    camera_paths = attribute.Get()
                elif name == PLAYLIST_CAMERA_TYPE:
                    camera_types = attribute.Get()
            elif name.startswith(PLAYLIST_PLAY_PREFIX):
                # Play options
                name = name[len(PLAYLIST_PLAY_PREFIX) :]
                if name == PLAYLIST_TRANSITION_TYPE:
                    playlist._transition_type = attribute.Get()
                elif name == PLAYLIST_TRANSITION_TIME:
                    playlist.transition_time_model.set_value(attribute.Get())
                elif name == PLAYLIST_ITEM_TIME:
                    playlist.item_time_model.set_value(attribute.Get())
                elif name == PLAYLIST_NAME:
                    playlist.name = attribute.Get()

        playlist.attributes = attributes
        for index in range(len(camera_names)):
            card = PlaylistCard.create(type=camera_types[index], name=camera_names[index], path=camera_paths[index])
            if card is not None:
                playlist.insert_item(card, notify=False)

    def _get_playlist_prim(self, playlist: PlaylistModel, create=True):
        if self._get_root_prim(create=create):
            return self.get_prim(playlist.path, create=create)
        else:
            return None

    def _save_camera(self, prim: Usd.Prim, camera):
        if self.__sidecar_data and self.__sidecar_data.read_only:
            self.__sidecar_data.notify_read_only("Save Camera")
            return

        if not prim:
            return
        camera_prim_path = prim.GetPath().pathString + "/" + camera.name
        camera_prim = self.get_prim(camera_prim_path)
        if not camera_prim:
            return

        with self.edit_context:
            self.set_prim_attribute(camera_prim, "path", str(camera.path))

    def get_prim(self, path, create=True, type_name=None) -> Optional[Usd.Prim]:
        stage: Usd.Stage = omni.usd.get_context().get_stage()
        if not stage:
            return None
        if path:
            prim = stage.GetPrimAtPath(path)
        else:
            prim = None
        if not prim and create:
            if self.__sidecar_data and self.__sidecar_data.read_only:
                self.__sidecar_data.notify_read_only("Get Prim")
                return None

            with self.edit_context:
                if type_name:
                    prim = stage.DefinePrim(path, type_name)
                else:
                    prim = stage.DefinePrim(path)
            if not prim:
                carb.log_error("Faile to create prim at '{path}'!")
                return None
        return prim

    def remove_prim(self, path):
        if self.__sidecar_data and self.__sidecar_data.read_only:
            self.__sidecar_data.notify_read_only("Remove Prim")
            return

        stage: Usd.Stage = omni.usd.get_context().get_stage()
        if not stage:
            return
        with self.edit_context:
            stage.RemovePrim(path)

    def set_prim_attribute(self, prim, name, value, type_name=Sdf.ValueTypeNames.String, create=True):
        if prim.HasAttribute(name):
            attribute = prim.GetAttribute(name)
        elif create:
            attribute = prim.CreateAttribute(name, type_name)
        else:
            return
        attribute.Set(value)

    def get_prim_attribute(self, prim, name, default):
        if prim.HasAttribute(name):
            attribute = prim.GetAttribute(name)
            value = attribute.Get()
            if value is None:
                return default
            else:
                return value
        else:
            return default
