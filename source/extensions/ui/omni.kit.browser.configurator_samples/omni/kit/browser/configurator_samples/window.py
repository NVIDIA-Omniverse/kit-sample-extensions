# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ui as ui

from .browser_widget import ConfiguratorSamplesTreeFolderBrowserWidget
from .model import ConfiguratorSamplesBrowserModel


class ConfiguratorSamplesBrowserWindow(ui.Window):  # pylint: disable=too-few-public-methods
    """Window that shows all different types of Configurator Samples."""

    WINDOW_TITLE = "Configurator Samples"

    def __init__(self, model: ConfiguratorSamplesBrowserModel):
        """Browser Window takes a ConfiguratorSamplesBrowserModel and displays a FolderBrowserWidget.

        Args:
            model: ConfiguratorSamplesBrowserModel that contains data for the folder hierarchy.
        """
        super().__init__(self.WINDOW_TITLE)

        self._widget = None
        self._browser_model = model

        self.frame.set_build_fn(self._build_ui)

        # Dock it to the same space where Stage is docked.
        self.deferred_dock_in("Content")

    def _build_ui(self):
        with self.frame:
            with ui.VStack(spacing=15):
                self._widget = ConfiguratorSamplesTreeFolderBrowserWidget(
                    self._browser_model,
                )
