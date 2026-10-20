# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import omni.ext
from omni.kit.search_core import SearchEngineRegistry

from .search_file_model import SearchFileModel


class SearchFilesExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._subscription = SearchEngineRegistry().register_search_model("File Search", SearchFileModel)

    def on_shutdown(self):
        self._subscription = None
