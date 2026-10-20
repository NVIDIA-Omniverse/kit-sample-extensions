# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module defines classes for managing and playing camera playlists with both timer-based and animation-based transitions and camera controls in Omni UI."""

from typing import Callable, List, Optional, Tuple

import carb
import omni.kit.commands
import omni.kit.notification_manager
import omni.timeline
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.widgets.custom import Timer
from pxr import Usd

from .constant import PlayMode
from .playlist import PlaylistModel
from .playlist_card import PlaylistCard

SMOOTH_WITH_TIME_SAMPLING = "/exts/omni.kit.playlist.core/smooth_with_time_sampling"


class PlaylistPlayer:
    """PlaylistPlayer is a class that provides basic functionality for controlling playback of a camera playlist. It manages the sequence of items in the playlist, handling the start and stop of playback, as well as updating the current playing index through a user-defined callback function. This class is designed to work with a playlist model and supports extending behavior through subclassing for different playback modes, such as timer-based or animation-based playback.

    Args:
        playlist (PlaylistModel): The model representing the playlist to be played.
        start_position (int): The index in the playlist from which the playback begins.
        on_started_fn (callable): A callback function invoked when the playback starts.
        on_stopped_fn (callable): A callback function invoked when the playback stops.
        on_playing_fn (callable, optional): A callback function called to notify which item is currently playing by providing its index.
    """

    @staticmethod
    def create(
        playlist: PlaylistModel,
        start: int = 0,
        on_started_fn: Callable = None,
        on_stopped_fn: Callable = None,
        on_playing_fn: Callable = None,
        on_transition_fn: Callable[[bool], None] = None,
    ) -> "PlaylistPlayer":
        """Create a camera player.

        Args:
            playlist (PlaylistModel): Model of playlist to play.
            start (int): Index of the first item to play.
            on_started_fn (Callable): Function called when play starts.
            on_stopped_fn (Callable): Function called when play stops.
            on_playing_fn (Callable): Function called to notify current playing item.
            on_transition_fn (Callable[[bool], None]): Function called to notify transition state.

        Returns:
            PlaylistPlayer: A new PlaylistPlayer instance.
        """
        if playlist.transition_type == PlayMode.TRANSITION_CUT:
            return TimerPlayer(playlist, start, on_started_fn, on_stopped_fn, on_playing_fn=on_playing_fn)
        elif playlist.transition_type == PlayMode.TRANSITION_SMOOTH:
            return AnimationPlayer(
                playlist,
                start,
                on_started_fn,
                on_stopped_fn,
                on_playing_fn=on_playing_fn,
                on_transition_fn=on_transition_fn,
            )
        else:
            return None

    def __init__(
        self,
        playlist: PlaylistModel,
        start_position: int,
        on_started_fn: callable,
        on_stopped_fn: callable,
        on_playing_fn: callable = None,
    ):
        """Initialize the PlaylistPlayer instance with provided settings."""
        self._playlist = playlist
        self._interval = playlist.item_time
        self._transition_time = playlist.transition_time

        self._start_position = start_position
        self._on_started_fn = on_started_fn
        self._on_stopped_fn = on_stopped_fn
        self._on_playing_fn = on_playing_fn

        self._playing = False
        self._playlist.playing_model.set_value(False)

    def destroy(self):
        """Destroy the player if currently playing."""
        if self._playing:
            self.stop()

    def play(self, navigation_mode: bool = False):
        """Start playing playlist.

        Args:
            navigation_mode (bool): Flag to specify navigation mode.

        Returns:
            bool: True if playing started successfully, False otherwise.
        """
        items = self._playlist.get_item_children(None)
        if len(items) == 0:
            carb.log_error("[Playlist] No cameras defined in playlist, cannot play!")
            return False

        self._navigation_mode = navigation_mode
        if self._on_start(self._start_position):
            if self._on_started_fn is not None:
                self._on_started_fn()
            self._playlist.playing_model.set_value(True)
            self._playing = True
            return True
        else:
            return False

    def stop(self):
        """Stop playing the playlist. Set playing state to false and trigger the on_stopped callback if provided."""
        self._playlist.playing_model.set_value(False)
        self._playing = False
        if self._on_stopped_fn is not None:
            self._on_stopped_fn()

    def set_time_per_item(self, time_per_item):
        """Set the time per item for playback.

        Args:
            time_per_item (int or float): Duration to display each item.
        """
        self._interval = time_per_item

    def set_transition_time(self, transition_time):
        """Set the transition time between items.

        Args:
            transition_time (int or float): Duration for transition between items.
        """
        self._transition_time = transition_time

    def set_playing_index(self, index: int) -> None:
        """Set the current playing index in the playlist.

        Args:
            index (int): Index to set as playing.
        """
        self._playlist.index_model.set_value(index)
        if self._on_playing_fn is not None:
            self._on_playing_fn(index)


class TimerPlayer(PlaylistPlayer):
    def __init__(
        self,
        playlist: PlaylistModel,
        start_position: int,
        on_started_fn: callable,
        on_stopped_fn: callable,
        on_playing_fn: callable = None,
    ):
        super().__init__(playlist, start_position, on_started_fn, on_stopped_fn, on_playing_fn=on_playing_fn)

        self._timer = Timer(self._interval, self._play_next)

    def set_time_per_item(self, time_per_item):
        self._timer.interval = time_per_item
        super().set_time_per_item(time_per_item)

    def _on_start(self, start_position):
        self._start_position = start_position
        self._last_position = start_position
        self._timer.start()

        return True

    def stop(self):
        self._timer.stop()
        super().stop()

    def _play_next(self):
        index = self._last_position + 1
        items = self._playlist.get_item_children(None)
        if index >= len(items):
            if len(items) == 0:
                index = -1
            else:
                # Loop to first
                index = 0

        if index == self._start_position:
            carb.log_info("[Playlist] Play to end. Stop!")
            self.stop()
            return False
        else:
            self.set_playing_index(index)
            camera = items[index].data
            carb.log_info(f"[Playlist] Switch camera to: {camera.path}")
            camera.active()
            self._last_position = index
            return True


class AnimationPlayer(PlaylistPlayer):
    def __init__(
        self,
        playlist: PlaylistModel,
        start_position: int,
        on_started_fn: callable,
        on_stopped_fn: callable,
        on_playing_fn=None,
        on_transition_fn: Callable[[bool], None] = None,
    ):
        super().__init__(playlist, start_position, on_started_fn, on_stopped_fn, on_playing_fn=on_playing_fn)

        self._usd_context = omni.usd.get_context()
        self._timeline = omni.timeline.get_timeline_interface()
        self._frames_per_second = self._timeline.get_time_codes_per_seconds()
        self._timer = Timer(self._interval, self._resume_play)
        self._on_transition_fn = on_transition_fn

        self._frame = 0
        self._saved_active_camera = None

        self._animation_list: List[Tuple(int, PlaylistCard, int)] = []
        self._current_playlist_card = None
        self._timeline_sub = None

    def destroy(self):
        self._timeline_sub = None
        super().destroy()

    def set_time_per_item(self, time_per_item):
        self._timer.interval = time_per_item
        super().set_time_per_item(time_per_item)

    def _on_start(self, start_position):
        settings = carb.settings.get_settings()
        self.__use_time_sampling = settings.get(SMOOTH_WITH_TIME_SAMPLING)
        carb.log_info(f"[playlist] Use {'TimeSampling' if self.__use_time_sampling else 'Animation'} for smooth play")

        if not self._create_animation(self._playlist, start_position, self._transition_time):
            return False

        # Change active camera
        viewport_api = get_active_viewport()
        self._saved_active_camera = viewport_api.camera_path
        viewport_api.camera_path = self._camera_prim.GetPath()

        self._animation_list.append((self._frame, None, -1))
        self._current_playlist_card = None
        self._timeline.set_looping(False)

        stream = self._timeline.get_timeline_event_stream()
        self._timeline_sub = stream.create_subscription_to_pop(self._on_timeline_event)

        self._timeline.play()

        return True

    def stop(self, stop_timeline=True):
        self._timeline_sub = None
        if stop_timeline and not self._timeline.is_stopped():
            carb.log_info("[Playlist] stopped")
            # It is strange that stop timeline here will reset camera to start position in navigation mode
            self._timeline.stop()

        if self._current_playlist_card is not None:
            self._current_playlist_card.clean(without_camera=True)
        self._current_playlist_card = None

        # Restore active camera
        if not self._navigation_mode and self._saved_active_camera:
            viewport_api = get_active_viewport()
            viewport_api.camera_path = self._saved_active_camera
            self._saved_active_camera = None

        super().stop()

    def _create_animation(self, playlist: PlaylistModel, start_position, transition_time):
        cards = playlist.items
        if self._navigation_mode:
            self._timeline.set_end_time((len(cards) - 1) * transition_time)
        else:
            self._timeline.set_end_time(len(cards) * transition_time)
        self._frame = 0
        self._animation_list = []

        start_card = cards[start_position]
        if not self._create_animation_list(playlist, start_card.data):
            return False

        for next in range(len(cards)):
            index = start_position + next
            if index >= len(cards):
                index -= len(cards)

            self.add_playlist_card(cards[index].data, index)

        return True

    def add_playlist_card(self, playlist_card: PlaylistCard, index):
        camera_prim = playlist_card.camera_prim

        animate_attrbute_names = [attr.GetName() for attr in self._camera_prim.GetAttributes()]
        valid = False
        ignore = False
        for attr in camera_prim.GetAttributes():
            # Available anim data types are:
            # [Gf.Vec2d, Gf.Vec3d, Gf.Vec4d, Gf.Vec2f, Gf.Vec3f, Gf.Vec4f, Gf.Vec2h, Gf.Vec3h, Gf.Vec4h, Gf.Vec2i, Gf.Vec3i, Gf.Vec4i]
            # [int, float, bool]
            name = attr.GetName()
            if name == "xformOp:translate":
                if self.__use_time_sampling:
                    self._camera_prim.GetAttribute("xformOp:translate").Set(attr.Get(), Usd.TimeCode(self._frame))
                else:
                    paths = [f"{self._camera_prim.GetPath().pathString}.{name}|{axis}" for axis in ["x", "y", "z"]]
                    values = list(attr.Get())
                    for i in range(3):
                        omni.kit.commands.execute(
                            "SetAnimCurveKeys",
                            paths=[paths[i]],
                            value=values[i],
                            time=Usd.TimeCode(self._frame),
                        )
                valid = True
            elif name.startswith("xformOp:rotate"):
                if name in animate_attrbute_names:
                    if self.__use_time_sampling:
                        self._camera_prim.GetAttribute(name).Set(attr.Get(), Usd.TimeCode(self._frame))
                    else:
                        paths = [f"{self._camera_prim.GetPath().pathString}.{name}|{axis}" for axis in ["x", "y", "z"]]
                        values = list(attr.Get())
                        for i in range(3):
                            omni.kit.commands.execute(
                                "SetAnimCurveKeys",
                                paths=[paths[i]],
                                value=values[i],
                                time=Usd.TimeCode(self._frame),
                            )
                else:
                    omni.kit.notification_manager.post_notification(
                        f"Ignore {playlist_card.name} because it uses '{name}' different from the first camera!",
                        status=omni.kit.notification_manager.NotificationStatus.WARNING,
                    )
                    ignore = True

                    carb.log_warn(
                        f"[Playlist] Ignore {playlist_card.name} because it uses '{name}' different from the first camera!"
                    )

                valid = True
        if valid:
            if not ignore:
                carb.log_info(f"[Playlist] Add camera ({playlist_card.path}) to animation at frame: {self._frame}")
                self._animation_list.append((self._frame, playlist_card, index))
                self._frame += self._transition_time * self._frames_per_second + self._interval
        else:
            omni.kit.notification_manager.post_notification(
                f"{playlist_card.name} not supported in Smooth mode due to unsupported camera!",
                status=omni.kit.notification_manager.NotificationStatus.WARNING,
            )

            carb.log_warn(
                f"[Playlist] {playlist_card.name} not supported in Smooth mode! because no 'xformOp:translate' or 'xformOp:rotate' defined in camera!"
            )

    def _create_playlist_camera(self, playlist: PlaylistModel, source_camera_path):
        # Here must define prim for playlist
        # Otherwise it will be "over" for system playlist which makes camera display incorrect
        prim = self._get_prim(playlist.path)
        if not prim:
            stage = omni.usd.get_context().get_stage()
            if stage:
                stage.DefinePrim(playlist.path)
                prim = self._get_prim(playlist.path)

        playlist_camera_path = playlist.path + "/camera_animation"

        prim = self._get_prim(playlist_camera_path)
        if prim:
            # Clear old animation data
            stage = omni.usd.get_context().get_stage()
            # TODO: Always crash, bug reported, now have to delete prim and create again
            # AnimationSchemaTools.DeleteAnimation(stage, playlist_camera_path)
            stage.RemovePrim(playlist_camera_path + "/animationData")

            if self.__use_time_sampling:
                for attr in prim.GetAttributes():
                    name = attr.GetName()
                    if name == "xformOp:translate" or name.startswith("xformOp:rotate"):
                        attr.Clear()

            if self._navigation_mode:
                # Navigation model, alwasy new camera for animation
                stage.RemovePrim(playlist_camera_path)
                # Create new playlist camera
                omni.kit.commands.execute(
                    "CopyPrimCommand",
                    path_from=source_camera_path,
                    path_to=playlist_camera_path,
                    duplicate_layers=False,
                    combine_layers=True,  # Kit 111: built-in cameras compose from several layers
                    exclusive_select=True,
                )
                prim = self._get_prim(playlist_camera_path)
        else:
            # Create new playlist camera
            omni.kit.commands.execute(
                "CopyPrimCommand",
                path_from=source_camera_path,
                path_to=playlist_camera_path,
                duplicate_layers=False,
                combine_layers=True,  # Kit 111: built-in cameras compose from several layers
                exclusive_select=True,
            )
            prim = self._get_prim(playlist_camera_path)

        if prim.GetTypeName() == "":
            prim.SetTypeName("Camera")
        return prim

    def _create_animation_list(self, playlist: PlaylistModel, start_card: PlaylistCard):
        # Create playlist camera prim
        camera_prim = self._create_playlist_camera(playlist, start_card.camera_prim.GetPath().pathString)
        if camera_prim is None:
            return False
        self._camera_prim = camera_prim

        return True

    def _get_prim(self, path):
        stage = self._usd_context.get_stage()
        if stage is None:
            return None

        if not path:
            return None
        prim = stage.GetPrimAtPath(path)
        if not prim:
            return None

        return prim

    def _on_timeline_event(self, e):
        if e.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED) or e.type == int(
            omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED
        ):
            # current_frame = self._frame_range.update_current_frame_from_timeline()
            current_frame = self._timeline.get_current_time() * self._frames_per_second
            # Check current playlist card
            self._check_playing_playlist_card(current_frame)
            end_frame = self._frames_per_second * self._timeline.get_end_time()
            if current_frame >= end_frame:
                self.stop(stop_timeline=False)
        if e.type == int(omni.timeline.TimelineEventType.STOP) and self._timeline_sub:
            self.stop(stop_timeline=False)

    def _check_playing_playlist_card(self, current_frame):
        for l_index in range(len(self._animation_list) - 1):
            frame, card, index = self._animation_list[l_index]
            next_frame, next_card, next_index = self._animation_list[l_index + 1]

            if frame <= current_frame and next_frame > current_frame:
                if self._current_playlist_card != card:
                    carb.log_info(f"[Playlist] Start playing {card.name} at frame {current_frame}")
                    if self._current_playlist_card is not None:
                        self._current_playlist_card.clean(without_camera=True)
                    card.active(without_camera=True)
                    self._current_playlist_card = card
                    self.set_playing_index(index)

                    # Pause for transition time
                    if self._navigation_mode:
                        # Change camera to animation
                        viewport_api = get_active_viewport()
                        viewport_api.camera_path = self._camera_prim.GetPath()
                    else:
                        self._timeline.pause()
                        self._timer.start()
                    if self._on_transition_fn:
                        self._on_transition_fn(True)
                break

    def _resume_play(self):
        # carb.log_info("[Playlist] continue")
        # Change camera to animation
        viewport_api = get_active_viewport()
        viewport_api.camera_path = self._camera_prim.GetPath()

        self._timeline.play()
        self._timer.stop()
        if self._on_transition_fn:
            self._on_transition_fn(False)
