# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import weakref

import carb.settings
import omni.ext
import omni.ui as ui
from omni.kit.menu.utils import MenuHelperExtension

from .window import VariantPresenterWindow

SETTING_SHOW_STARTUP = "/exts/omni.kit.variant.presenter/showStartup"
_variant_presenter_model = None
_variant_presenter_window = None


def get_model():
    return _variant_presenter_model if not _variant_presenter_model else _variant_presenter_model()


def get_window():
    return _variant_presenter_window if not _variant_presenter_window else _variant_presenter_window()


class VariantPresenterExtension(omni.ext.IExt, MenuHelperExtension):
    """The entry point for the extension"""

    WINDOW_NAME = "Variant Presenter"
    MENU_GROUP = "Tools/Variants"

    def on_startup(self):
        self._presenter_window = None
        ui.Workspace.set_show_window_fn(self.WINDOW_NAME, self.show_window)
        show_startup = carb.settings.get_settings().get(SETTING_SHOW_STARTUP)
        # Register menu item via menu utils
        self.menu_startup(self.WINDOW_NAME, self.WINDOW_NAME, self.MENU_GROUP)
        if show_startup:
            ui.Workspace.show_window(self.WINDOW_NAME)

    def on_shutdown(self):
        ui.Workspace.set_show_window_fn(self.WINDOW_NAME, None)
        self.menu_shutdown()
        if self._presenter_window:
            self._presenter_window.set_visibility_changed_listener(None)
            self._presenter_window.destroy()
        self._presenter_window = None

    def show_window(self, value):
        global _variant_presenter_model
        global _variant_presenter_window
        if value:
            self._presenter_window = VariantPresenterWindow()
            self._presenter_window.set_visibility_changed_listener(self._visibility_changed_fn)
            self._presenter_window._load_model()
            _variant_presenter_model = weakref.ref(self._presenter_window._model)
            _variant_presenter_window = weakref.ref(self._presenter_window)
        else:
            if self._presenter_window:
                self._presenter_window.destroy()
            self._presenter_window = None

    def _visibility_changed_fn(self, visible):
        # Refresh menu tick state via menu utils helper
        self.menu_refresh()
