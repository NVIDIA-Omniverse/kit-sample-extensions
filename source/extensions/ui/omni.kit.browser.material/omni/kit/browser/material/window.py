# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb.settings
from omni import ui
from omni.kit.browser.folder.core import TreeFolderBrowserWidget

from .delegate import MaterialDetailDelegate
from .model import MaterialBrowserModel
from .options_menu import MaterialOptionsMenu

SETTING_ROOT = "/exts/omni.kit.browser.material/"
SETTING_MIN_THUMBNAIL_SIZE = SETTING_ROOT + "min_thumbnail_size"
SETTING_MAX_THUMBNAIL_SIZE = SETTING_ROOT + "max_thumbnail_size"
SETTING_LOAD_AFTER_STARTUP = SETTING_ROOT + "load_after_startup"


class MaterialBrowserWindow(ui.Window):
    """
    Represent a window to show materials.
    """

    WINDOW_TITLE = "Material Browser"

    def __init__(self):
        super().__init__(self.WINDOW_TITLE, width=500, height=600)
        self._widget = None

        settings = carb.settings.get_settings()
        load_after_startup = settings.get(SETTING_LOAD_AFTER_STARTUP)
        if load_after_startup:
            self._build_ui()
        else:
            self.frame.set_build_fn(self._build_ui)

        # Dock it to the same space where Stage is docked, make it active.
        self.deferred_dock_in("Content", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

    def destroy(self):
        if self._widget:
            self._delegate.destroy()
            self._widget.destroy()

        super().destroy()

    def _build_ui(self):
        self._browser_model = MaterialBrowserModel()
        self._delegate = MaterialDetailDelegate(self._browser_model)
        self._options_menu = MaterialOptionsMenu(self._delegate)

        settings = carb.settings.get_settings()
        min_thumbnail_size = settings.get(SETTING_MIN_THUMBNAIL_SIZE)
        max_thumbnail_size = settings.get(SETTING_MAX_THUMBNAIL_SIZE)
        with self.frame:
            self._widget = TreeFolderBrowserWidget(
                self._browser_model,
                detail_delegate=self._delegate,
                options_menu=self._options_menu,
                min_thumbnail_size=min_thumbnail_size,
                max_thumbnail_size=max_thumbnail_size,
            )
