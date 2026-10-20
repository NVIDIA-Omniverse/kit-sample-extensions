# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.commands
import omni.usd

from .actions import _set_lighting_mode


class SetLightingMenuModeCommand(omni.kit.commands.Command):
    """
    Set the current lighting rig

    Args:
        lighting_mode: (str) The lgihting mode to set to
        usd_context_name: (str) The UsdContext to target
    """

    def __init__(self, lighting_mode: str, usd_context_name: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__usd_context_name = usd_context_name
        self.__lighting_mode = lighting_mode

    def do(self):
        usd_context = omni.usd.get_context(self.__usd_context_name)
        succeeded, lighting_mode, prev_mode = _set_lighting_mode(self.__lighting_mode, usd_context=usd_context)
        if succeeded:
            self.__lighting_mode = prev_mode
        return lighting_mode, prev_mode

    def undo(self):
        if self.__lighting_mode:
            usd_context = omni.usd.get_context(self.__usd_context_name)
            succeeded, lighting_mode, prev_mode = _set_lighting_mode(self.__lighting_mode, usd_context=usd_context)
            self.__lighting_mode = prev_mode


def register_commands():
    return omni.kit.commands.register_all_commands_in_module(__name__)


def unregister_commands(cmds):
    omni.kit.commands.unregister_module_commands(cmds)
