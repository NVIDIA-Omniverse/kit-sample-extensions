# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import omni.ui as ui

from .browser_delegate import WrappDetailDelegate
from .browser_model import WrappBrowserModel
from .browser_widget import WrappBrowserWidget
from .consistents import WRAPP_EXPLORER_NAME


class WrappBrowserWindow(ui.Window):
    """Main window for the WRAPP browser interface.

    Provides:
    - WRAPP packages browsing interface
    - Property inspection
    - Asset management controls

    Args:
        visible (bool): Whether the window should be visible initially
    """

    def __init__(self, visible=True):
        super().__init__(WRAPP_EXPLORER_NAME, visible=visible)

        self.frame.set_build_fn(self._build_ui)

        self._browser_model = WrappBrowserModel()
        self._delegate = None
        self._widget = None

        # Dock it to the same space where Content is docked.
        self.deferred_dock_in("Content")

    def refresh_asset_folders(self):
        self._browser_model.refresh_asset_folders()

    def destroy(self):
        if self._widget:
            self._widget.destroy()
        if self._delegate:
            self._delegate.destroy()
        super().destroy()

    def _build_ui(self):
        """Build the window's user interface components."""
        self._delegate = WrappDetailDelegate(self._browser_model)

        with self.frame:
            with ui.VStack(spacing=15):
                self._widget = WrappBrowserWidget(
                    self._browser_model,
                    detail_delegate=self._delegate,
                )
