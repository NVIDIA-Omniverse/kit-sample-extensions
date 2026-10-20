# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import omni.ext

from . import BrowserExtensionImpl

WSCACHE_ROOT_URLS_SETTING = "/exts/omni.simready.content.browser/wscache_root_urls"
DEFAULT_WSCACHE_ROOT_URL_INDEX_SETTING = "/exts/omni.simready.content.browser/default_wscache_root_url_index"
# This is not good, this extension should not directly depend on the Isaac settings.
ISAAC_CONTENT_ROOTS_SETTING = "/exts/isaacsim.gui.content_browser/folders"
FILE_INDEX_LOCATIONS_SETTING = "/exts/omni.simready.content.browser/file_index_locations"
USD_SEARCH_ENDPOINT_SETTING = "/exts/omni.simready.content.browser/usd_search_endpoint"
USD_SEARCH_TREE_ROOT_SUBPATH_SETTING = "/exts/omni.simready.content.browser/usd_search_tree_root_subpath"


class Extension(omni.ext.IExt):
    """The Extension class"""

    def on_startup(self, _):
        self._impl = BrowserExtensionImpl()
        self._impl.startup()

    def on_shutdown(self):
        self._impl.shutdown()
        self._impl = None
