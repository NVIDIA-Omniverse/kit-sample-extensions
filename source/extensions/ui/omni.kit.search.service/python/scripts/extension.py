# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import omni.client
import omni.ext
from omni.kit.search_core import SearchEngineRegistry

from .searchservice_model import NGSearchServiceModel


class OmniSearch(omni.ext.IExt):
    def on_startup(self):
        self._ng_subscription = SearchEngineRegistry().register_search_model("Search Service", NGSearchServiceModel)

    def on_shutdown(self):
        self._ng_subscription = None
