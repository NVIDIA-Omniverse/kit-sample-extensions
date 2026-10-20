# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module defines a system for managing playlist cards with base and camera-specific implementations, including functionality for registration, creation, and enumeration of playlist cards based on USD stage primitives."""

from typing import Any, Callable, Dict, List, Optional

import carb
import carb.tokens
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from pxr import Usd, UsdGeom

from .constant import PLAYLISTS_ROOT

DEFAULT_VIEWS = {
    "OmniverseKit_Persp": "Perspective",
    # "OmniverseKit_Top": "Top",
    # "OmniverseKit_Front": "Front",
    # "OmniverseKit_Right": "Right",
}


class PlaylistCard:
    """A class representing a playlist card used to organize and display different types of content within a playlist interface. This class provides the minimal set of attributes required to reference content items, such as camera views, and is designed to be extended by subclasses that implement additional functionality and custom presentation details.

    Args:

        type (str): The identifier for the type of the playlist card. It specifies the category or role of the card within the playlist.
        path (str): The path string that uniquely identifies the element represented by the card within the scene or data structure.
        name (str): A human-readable name for the playlist card. If not provided, it defaults to 'Unknown' to indicate an unspecified name.

    This class focuses solely on initializing and storing these attributes without enforcing any specific behavior. Specialized subclasses or dynamically registered types can extend its functionality to provide additional features such as custom icons, menu text, or interaction behaviors.
    """

    CAMERA = "camera"
    """str: Constant representing camera type in playlist card."""
    PLAYLIST = "playlist"
    """str: Constant representing playlist type in playlist card."""
    WAYPOINT = "waypoint"
    """str: Constant representing waypoint type in playlist card."""

    # Registered card
    __g_registered: Dict[str, Any] = {}

    @staticmethod
    def register(type: str, cls) -> bool:
        """Registers a new type of playlist card.

        Args:
            type (str): Type name.
            cls (Any): Class for the new playlist card type.

        Returns:
            bool: True if registration is successful, False otherwise.
        """
        if type in PlaylistCard.__g_registered:
            return False

        PlaylistCard.__g_registered[type] = cls
        carb.log_info(f"[Playlist] registered playlist card: {type} {cls}")
        return True

    @staticmethod
    def deregister(type: str):
        """Deregisters a type of playlist card.

        Args:
            type (str): Type name.
        """
        PlaylistCard.__g_registered.pop(type, None)
        carb.log_info(f"[Playlist] deregistered playlist card: {type}")

    @classmethod
    def accept(camera_path: str) -> bool:
        """Checks if the camera path belongs to the playlist card.

        Returns:
            bool: True if the camera path belongs to the playlist card, False otherwise.
        """
        return False  # pragma: no cover

    @staticmethod
    def create(
        type: Optional[str] = None,
        camera_prim: Optional[Usd.Prim] = None,
        name: Optional[str] = None,
        path: Optional[str] = None,
    ):
        """Creates a new playlist card instance based on input parameters.

        Args:
            type (str): Playlist card type.
            camera_prim (Usd.Prim): Camera prim object.
            name (str): Name of the playlist card.
            path (str): A path string for camera or playlist.

        Returns:
            Any: An instance of the playlist card or None if creation fails.
        """
        if camera_prim:
            path = camera_prim.GetPath().pathString
            if name is None:
                name = camera_prim.GetName()

        if path is None:
            carb.log_error(f"[playlist] No camera path defined!")
            return None

        if type is None:
            for t, cls in PlaylistCard.__g_registered.items():
                if cls.accept(path):
                    type = t
                    break
            else:
                if camera_prim:
                    if camera_prim.IsA(UsdGeom.Camera):
                        type = PlaylistCard.CAMERA
                elif path:
                    type = PlaylistCard.CAMERA

        if type in PlaylistCard.__g_registered:
            return PlaylistCard.__g_registered[type](type, name=name, path=path)
        elif type == PlaylistCard.CAMERA:
            return CameraCard(type, name=name, path=path)
        else:
            carb.log_info(f"[playlist] Unknown playlist card type: {type} from {path}")
            return None

    def __init__(self, type: str, path: str, name: Optional[str] = None):
        """Initializes the PlaylistCard with type, path, and an optional name."""
        self.type = type
        self.path = path
        self.name = name if name else "Unknown"

    @property
    def camera_prim(self) -> Optional[Usd.Prim]:
        """Gets the camera prim property of the playlist card.

        Returns:
            Optional[Usd.Prim]: The Usd prim at the card path or None if stage is not available.
        """
        stage = omni.usd.get_context().get_stage()
        if stage:
            return stage.GetPrimAtPath(self.path)
        else:
            return None

    @property
    def menu_text(self) -> str:
        """Gets the menu text property of the playlist card.

        Returns:
            str: The menu text.
        """
        return ""  # pragma: no cover

    @property
    def icon(self) -> str:
        """Gets the icon property of the playlist card.

        Returns:
            str: The icon representation string.
        """
        return ""  # pragma: no cover

    # In animation mode, active card without active camera
    def active(self, without_camera=False):
        """Activates the playlist card.

        Args:
            without_camera (bool): Activate without camera if True.
        """
        pass  # pragma: no cover

    def clean(self, without_camera=False):
        """Cleans the playlist card.

        Args:
            without_camera (bool): Clean without camera resources if True.
        """
        pass  # pragma: no cover


class CameraCard(PlaylistCard):
    def __init__(self, type: str, path: str, name=None):
        super().__init__(type, path, name=name)

        if self.name in DEFAULT_VIEWS:
            self.name = DEFAULT_VIEWS[self.name]

    @property
    def icon(self) -> str:
        return carb.tokens.get_tokens_interface().resolve("${omni.kit.playlist.core}/icons/Camera.png")

    @property
    def menu_text(self) -> str:
        return "Cameras"

    def active(self, without_camera=False):
        if not without_camera:
            viewport_api = get_active_viewport()
            viewport_api.camera_path = self.path


# Kit 111: omni.runtime.core's private viewport camera, hidden from the UI like Kit's own camera menu does.
_RUNTIME_VIEWPORT_CAMERA = "/OVRuntimeViewportCamera"


def _is_hidden_camera(prim: Usd.Prim) -> bool:
    """Cameras the app hides from the UI (e.g. the Kit 111 runtime's private viewport camera) are not playlist items."""
    if omni.usd.editor.is_hide_in_ui(prim):
        return True
    return prim.GetPath().pathString == _RUNTIME_VIEWPORT_CAMERA and omni.usd.editor.is_hide_in_stage_window(prim)


def enum_playlist_cards() -> List[PlaylistCard]:
    """Enumerate playlist cards from the active USD stage. If no stage is available, return an empty list. Iterate over the stage's camera prims and create a playlist card for valid prims, excluding hidden cameras.

    Returns:

        List[PlaylistCard]: List of discovered playlist cards.
    """
    HIDDEN_CAMERAS = ["OmniverseKit_Top", "OmniverseKit_Front", "OmniverseKit_Right"]
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return []

    cards = []
    for prim in Usd.PrimRange(stage.GetPseudoRoot()):
        if prim.IsA(UsdGeom.Camera):
            path = prim.GetPath().pathString
            if path.startswith(PLAYLISTS_ROOT) or _is_hidden_camera(prim):
                continue
            else:
                card = PlaylistCard.create(camera_prim=prim)
                if card and card.name not in HIDDEN_CAMERAS:
                    cards.append(card)

    return cards
