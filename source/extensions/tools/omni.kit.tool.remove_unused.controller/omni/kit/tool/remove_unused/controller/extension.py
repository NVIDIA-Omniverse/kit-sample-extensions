# * Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
# *
# * NVIDIA CORPORATION and its licensors retain all intellectual property
# * and proprietary rights in and to this software, related documentation
# * and any modifications thereto.  Any use, reproduction, disclosure or
# * distribution of this software and related documentation without an express
# * license agreement from NVIDIA CORPORATION is strictly prohibited.

import carb
import omni.ext

from .controller import RemoveUnusedController

_INSTANCE = None


def get_instance():
    """Expose the created instance of the tool"""
    return _INSTANCE


class RemoveUnusedExtension(omni.ext.IExt):
    """Standard extension support class, necessary for extension management"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_startup(self, ext_id):
        global _INSTANCE
        carb.log_info("[omni.kit.tools.remove_unused] startup")
        _INSTANCE = RemoveUnusedController()

    def on_shutdown(self):
        global _INSTANCE
        carb.log_info("[omni.kit.tools.remove_unused] shutdown")
        _INSTANCE.destroy()
        _INSTANCE = None
