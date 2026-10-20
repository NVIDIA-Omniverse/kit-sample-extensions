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
from omni.kit.window.preferences import register_page, unregister_page

from .preference_page import ThumbnailPage


class ThunbnailGenerationExtension(omni.ext.IExt):
    """A class for integrating thumbnail generation preferences into the user interface.

    This extension provides a dedicated preference page that allows users to configure settings related to thumbnail generation. The preference page enables easy access to controls for adjusting thumbnail parameters, ensuring that the configuration of thumbnail generation is both straightforward and flexible.
    """

    def __init__(self):
        self._preference_page = None
        super().__init__()

    def on_startup(self, ext_id):
        """Initializes the thumbnail generation extension by registering thumbnail generation preferences.

        Args:
            ext_id (str): Extension identifier passed during startup.
        """
        self._preference_page = ThumbnailPage()
        register_page(self._preference_page)

    def on_shutdown(self):
        """Unregisters the registered thumbnail generation preferences."""
        unregister_page(self._preference_page)
