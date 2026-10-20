# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import omni.ui as ui

from .browser_delegate import SimReadyDetailDelegate
from .browser_model import SimReadyBrowserModel
from .browser_widget import SimReadyBrowserWidget

SETTING_COLLECTION_ROOTS = "/exts/omni.simready.explorer/folders"
SIMREADY_EXPLORER_NAME = "SimReady Explorer"


class SimReadyBrowserWindow(ui.Window):
    """
    Represent a window to show SimReady Assets
    """

    def __init__(self, visible=True):
        super().__init__(SIMREADY_EXPLORER_NAME, visible=visible)

        self.frame.set_build_fn(self._build_ui)

        self._browser_model = SimReadyBrowserModel(setting_folders=SETTING_COLLECTION_ROOTS)
        self._delegate = None
        self._widget = None

        # Dock it to the same space where Content is docked.
        self.deferred_dock_in("Content")

    def destroy(self):
        if self._widget:
            self._widget.destroy()
        if self._delegate:
            self._delegate.destroy()
        super().destroy()

    def _build_ui(self):
        self._delegate = SimReadyDetailDelegate(self._browser_model)

        with self.frame:
            with ui.VStack(spacing=15):
                self._widget = SimReadyBrowserWidget(
                    self._browser_model,
                    detail_delegate=self._delegate,
                )
