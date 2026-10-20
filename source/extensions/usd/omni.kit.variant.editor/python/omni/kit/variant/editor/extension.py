# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import weakref
from pathlib import Path

import carb
import omni.ext

from .commands import *
from .hotkeys import HotkeyBuilder
from .variant_property_widget_builder import UsdVariantPropertiesWidgetBuilder
from .window import VariantEditorWindow

# Variant Editor Extension
_variant_editor_window_weakref = None


def get_window():
    return _variant_editor_window_weakref if not _variant_editor_window_weakref else _variant_editor_window_weakref()


TEST_DATA_PATH = ""
_extension_instance = None


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        global _variant_editor_window_weakref
        carb.log_verbose("Variant Editor Startup")
        self._window = VariantEditorWindow()
        UsdVariantPropertiesWidgetBuilder.startup()
        _variant_editor_window_weakref = weakref.ref(self._window)
        global TEST_DATA_PATH
        manager = omni.kit.app.get_app().get_extension_manager()
        extension_path = manager.get_extension_path(ext_id)
        TEST_DATA_PATH = Path(extension_path).joinpath("data").joinpath("tests")

        global _extension_instance
        _extension_instance = self

        self._hotkey = HotkeyBuilder(ext_id, self._window)

    def on_shutdown(self):
        carb.log_verbose("Variant Editor Shutdown")
        if self._hotkey:
            self._hotkey.on_shutdown()
            self._hotkey = None

        if self._window:
            self._window.destroy()
            self._window = None
        UsdVariantPropertiesWidgetBuilder.shutdown()

        global _extension_instance
        _extension_instance = None


def get_instance():
    global _extension_instance
    return _extension_instance
