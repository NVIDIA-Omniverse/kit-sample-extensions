# SPDX-FileCopyrightText: Copyright (c) 2021-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import omni.ext

from .core import SceneOptimizerUI

_extension_instance = None


class _PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        """ """
        # Construct the manager class that handles the menu item and panel.
        self.ui = SceneOptimizerUI()
        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):  # pragma: no cover
        """ """
        # Shutdown and release the manager class.
        self.ui.shutdown()
        self.ui = None
        global _extension_instance
        _extension_instance = None


def get_instance():  # pragma: no cover
    """Used externally for testing by QA"""
    return _extension_instance
