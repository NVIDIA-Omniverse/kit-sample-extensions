# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.ext

from ..bindings._omni_curve_creator import *


class PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        # self._interface = acquire_interface()
        ...

    def on_shutdown(self):
        # release_interface(self._interface)
        ...
