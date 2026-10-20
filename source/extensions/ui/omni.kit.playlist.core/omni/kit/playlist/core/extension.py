# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module implements a playlist core extension that initializes, manages, and cleans up a PlayManager instance using an omni.ext.IExt extension."""

import omni.ext

from .play_manager import PlayManager

_g_instance = None


def get_play_manager() -> PlayManager:
    """Return the PlayManager instance if available, else return None.

    Returns:

        PlayManager: The instance of PlayManager if available, else None.
    """
    if _g_instance:
        return _g_instance._play_manager
    else:
        return None


class PlaylistCoreExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._play_manager = PlayManager()

        global _g_instance
        _g_instance = self

    def on_shutdown(self):
        global _g_instance
        _g_instance = None

        self._play_manager.destroy()
        self._play_manager = None
