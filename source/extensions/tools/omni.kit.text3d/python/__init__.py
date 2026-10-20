# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["create_text_prim"]
from omni.kit.commands import register_all_commands_in_module

from ._impl import commands
from ._impl.extension import TextGeneratorExtension, create_text_prim

cmds = register_all_commands_in_module(commands)
