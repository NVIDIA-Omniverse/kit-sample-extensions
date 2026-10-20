# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["AssetDetailDelegate"]

import asyncio
from pathlib import Path
from typing import Optional

import carb
import omni.kit.app
import omni.ui as ui
from omni.kit.browser.core import DetailItem, create_drop_helper
from omni.kit.browser.folder.core import FolderDetailDelegate

from .context_menu import ContextMenu
from .model import AssetBrowserModel

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")


class AssetDetailDelegate(FolderDetailDelegate):
    """
    Delegate to show asset item in detail view
    Args:
        model (AssetBrowserModel): Asset browser model
    """

    def __init__(self, model: AssetBrowserModel):
        super().__init__(model=model)

        self._dragging_url = None
        self._settings = carb.settings.get_settings()
        self._context_menu: Optional[ContextMenu] = None
        self._action_item: Optional[DetailItem] = None

        self._instanceable_categories = self._settings.get("/exts/omni.kit.browser.asset/instanceable")
        if self._instanceable_categories:
            self._drop_helper = create_drop_helper(
                pickable=True,
                add_outline=True,
                on_drop_accepted_fn=self._on_drop_accepted,
                on_drop_fn=self._on_drop,
            )

    def destroy(self):
        self._drop_helper = None
        super().destroy()

    def get_thumbnail(self, item) -> str:
        """Set default sky thumbnail if thumbnail is None"""
        if item.thumbnail is None:
            return f"{ICON_PATH}/usd_stage_256.png"
        return item.thumbnail

    def on_drag(self, item: DetailItem) -> str:
        """Could be dragged to viewport window"""
        thumbnail = self.get_thumbnail(item)
        icon_size = 128
        with ui.VStack(width=icon_size):
            if thumbnail:
                ui.Spacer(height=2)
                with ui.HStack():
                    ui.Spacer()
                    ui.ImageWithProvider(thumbnail, width=icon_size, height=icon_size)
                    ui.Spacer()
            ui.Label(
                item.name,
                word_wrap=False,
                elided_text=True,
                skip_draw_when_clipped=True,
                alignment=ui.Alignment.TOP,
                style_type_name_override="GridView.Item",
            )

        self._dragging_url = None
        if self._instanceable_categories:
            # For required categories, need to set instanceable after dropped
            url = item.url
            pos = url.rfind("/")
            if pos > 0:
                url = url[:pos]
            for category in self._instanceable_categories:
                if category in url:
                    self._dragging_url = item.url
                    break
        return item.url

    def _on_drop_accepted(self, url):
        # Only handle dragging from asset browser
        return url == self._dragging_url

    def _on_drop(self, url, target, viewport_name, context_name):  # pylint: disable=useless-return
        saved_instanceable = self._settings.get("/persistent/app/stage/instanceableOnCreatingReference")
        if not saved_instanceable and url == self._dragging_url:
            # Enable instanceable for viewport asset drop handler
            self._settings.set_bool("/persistent/app/stage/instanceableOnCreatingReference", True)

            async def __restore_instanceable_flag():
                # Waiting for viewport asset dropper handler completed
                await omni.kit.app.get_app().next_update_async()
                self._settings.set("/persistent/app/stage/instanceableOnCreatingReference", saved_instanceable)

            asyncio.ensure_future(__restore_instanceable_flag())

        self._dragging_url = None
        # Let viewport do asset dropping
        return None  # noqa: R501

    def on_right_click(self, item: DetailItem) -> None:
        """Show context menu"""
        self._action_item = item
        if self._context_menu is None:
            self._context_menu = ContextMenu()

        if self._context_menu:
            self._context_menu.url = self._action_item.url
            self._context_menu.show()
