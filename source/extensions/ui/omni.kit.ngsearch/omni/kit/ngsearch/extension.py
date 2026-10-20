# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.ext


class NGSearchExtension(omni.ext.IExt):
    """The NGSearch extension"""

    def on_startup(self, ext_id):
        """Called to load the extension"""
        self._client_instance = None

    @property
    def _client(self):
        """Lazy import of the extension"""
        if self._client_instance is None:
            from .client import NGSearchClient

            self._client_instance = NGSearchClient.get_instance()
        return self._client_instance

    def on_shutdown(self):
        """Called when the extension us unloaded"""
        self._client_instance = None
