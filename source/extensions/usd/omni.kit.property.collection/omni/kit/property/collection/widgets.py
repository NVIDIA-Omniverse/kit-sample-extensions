# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import List

import omni.ext
import omni.kit.app
import omni.usd

from .collection_props_widget import CollectionPropertiesWidget


class UsdCollectionPropertyWidgets(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        self._registered = False

    def on_startup(self, ext_id):
        self._register_widget()

    def on_shutdown(self):
        if self._registered:
            self._unregister_widget()

    def _register_widget(self):
        import omni.kit.window.property as p

        w = p.get_window()
        if w:
            w.register_widget(
                "collection",
                "collection",
                CollectionPropertiesWidget(title="Collection Properties", collapsed=False),
                False,
            )

            self._registered = True

    def _unregister_widget(self):
        import omni.kit.window.property as p

        w = p.get_window()
        if w:
            w.unregister_widget("collection", "collection")
            self._registered = False
