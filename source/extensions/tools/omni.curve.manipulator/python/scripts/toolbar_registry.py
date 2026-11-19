# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from omni.kit.manipulator.transform.toolbar_registry import ToolbarRegistry

_toolbar_registry = ToolbarRegistry()


def get_toolbar_registry() -> ToolbarRegistry:
    return _toolbar_registry
