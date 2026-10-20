# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import omni.ext
import omni.kit.ui

from .icons import CollectionIcons


class CollectionWidgetExtension(omni.ext.IExt):
    def on_startup(self):
        # TODO we should merge the code with change changes to omni.kit.widget.stage_icons
        # from omni.kit.widget.stage_icons import stage_icons_extension
        # stage_icons_extension.StageIconsExtension.register_icons_externally(StageIcons())

        # For now to get it working, lets' hardcode...
        from omni.kit.widget.stage.stage_icons import StageIcons  # it's a singleton

        CollectionIcons()._icons.update(StageIcons()._icons)

    def on_shutdown(self):
        CollectionIcons()._icons = {}
