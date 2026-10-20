# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ext
from omni.kit.markup.core import MarkupCard
from omni.kit.markup.core.playlist_card_markup import MarkupCard
from omni.kit.playlist.core import PlaylistCard

from .play_control import PlayControl
from .playlist_model import AllMarkupPlaylistModel


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class PlaylistMarkupExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.

    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls, *args, **kwargs)
        return cls.instance

    def on_startup(self, ext_id):
        PlaylistCard.register(MarkupCard.PLAYLIST_CARD_TYPE_MARKUP, MarkupCard)
        self.__markup_playlist_model = AllMarkupPlaylistModel()
        self.__play_control = PlayControl(self.__markup_playlist_model)

        try:
            from omni.kit.tool.camera_playlist import PlaylistManager

            PlaylistManager.get_instance().register(self.__markup_playlist_model)
        except ImportError:  # pragma: no cover
            pass

    def on_shutdown(self):
        PlaylistCard.deregister(MarkupCard.PLAYLIST_CARD_TYPE_MARKUP)
        try:
            from omni.kit.tool.camera_playlist import PlaylistManager

            PlaylistManager.get_instance().deregister(self.__markup_playlist_model)
        except ImportError:  # pragma: no cover
            pass

        self.__play_control.destroy()
        self.__markup_playlist_model.destroy()


def get_instance():
    return PlaylistMarkupExtension.instance
