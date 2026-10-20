# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.

# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import gc
from functools import lru_cache, partial

import omni.ext
import omni.ui as ui
import omni.usd

from .semantics_entry import property_log
from .semantics_widget import SemanticsPropertyWidget

EMPTY_SEMANTICS_LABEL_STYLE = {"font_size": 18}
P0_LABEL_STYLE = {"font_size": 14, "color": 0xFF9A9A9A}
P1_LABEL_STYLE = {"color": 0xFF9A9A9A}


class SemanticsPropertyExtension(omni.ext.IExt):
    def __init__(self):
        self._registered = False
        super().__init__()

    def on_startup(self, ext_id) -> None:
        """Called to load the extension"""
        property_log("info", "Extension startup!")
        manager = omni.kit.app.get_app().get_extension_manager()
        extension_path = manager.get_extension_path(ext_id)

        self._register_widget()

    def on_shutdown(self) -> None:
        """Called when the extesion is unloaded"""
        property_log("info", f"Extension shutdown!")
        gc.collect()

    def _register_widget(self):
        import omni.kit.window.property as p
        from omni.kit.property.usd.usd_property_widget import MultiSchemaPropertiesWidget, SchemaPropertiesWidget
        from omni.kit.window.property.property_scheme_delegate import PropertySchemeDelegate

        w = p.get_window()
        if w:
            w.register_widget("prim", "semantics", SemanticsPropertyWidget(title="Semantics", collapsed=False))
            self._registered = True

    def _unregister_widget(self):
        import omni.kit.window.property as p

        w = p.get_window()
        if w:
            w.unregister_widget("prim", "semantics")
            self._registered = False
