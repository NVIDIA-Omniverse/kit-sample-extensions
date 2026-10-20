# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import Optional

from omni import ui
from omni.kit.browser.core import DetailItem, create_drop_helper
from omni.kit.browser.folder.core import BrowserFile, FolderDetailDelegate

from ..models import EnvBrowserModel, EnvDetailItem, EnvType

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")
ENV_DRAG_PAYLOAD_PREFIX = "env::"


class EnvDetailDelegate(FolderDetailDelegate):
    """
    Delegate to show env item in detail view
    Args:
        model (EnvBrowserModel): Sky browser model
    """

    def __init__(self, model: EnvBrowserModel):
        super().__init__(model)
        self._action_item: EnvDetailItem = None
        self._context_menu: ui.Menu = None

        self._drop_helper = create_drop_helper(
            pickable=False,
            add_outline=False,
            on_drop_accepted_fn=self._on_drop_accepted,
            on_drop_fn=self._on_drop,
            protocal=ENV_DRAG_PAYLOAD_PREFIX,
        )

    def destroy(self) -> None:
        self._drop_helper = None
        self._context_menu = None
        super().destroy()

    def build_thumbnail(self, item: DetailItem) -> Optional[ui.Image]:
        """
        Display thumbnail per detail item
        Args:
            item (DetailItem): detail item to display
        """
        thumbnail = self.get_thumbnail(item)
        with ui.ZStack():
            thumbnail_image = ui.Image(
                thumbnail, fill_policy=ui.FillPolicy.STRETCH, style_type_name_override="GridView.Image"
            )
            if item.type == EnvType.USD:
                with ui.VStack(alignment=ui.Alignment.LEFT_BOTTOM):
                    ui.Spacer(height=ui.Percent(60))
                    ui.Triangle(
                        width=ui.Percent(40),
                        height=ui.Percent(40),
                        alignment=ui.Alignment.LEFT_TOP,
                        style={"background_color": 0xFFC2C2C2},
                    )
                with ui.VStack():
                    ui.Spacer(height=ui.Percent(83))
                    with ui.HStack():
                        ui.Spacer(width=ui.Percent(8))
                        ui.Triangle(
                            width=ui.Percent(8),
                            height=ui.Percent(50),
                            alignment=ui.Alignment.RIGHT_CENTER,
                            style={"background_color": 0xFF858585},
                        )

        return thumbnail_image

    def get_thumbnail(self, item: EnvDetailItem) -> str:
        """Set default sky thumbnail if thumbnail is None"""
        if item.thumbnail is None:
            return f"{ICON_PATH}/usd_stage_256.png"
        else:
            return item.thumbnail

    def on_right_click(self, item: EnvDetailItem) -> None:
        """Show sky context menu"""
        self._action_item = item
        # Show context menu to apply sky
        if self._context_menu is None:
            self._context_menu = ui.Menu("Sky context menu", name="this")
            with self._context_menu:
                ui.MenuItem("Set to Stage", triggered_fn=self._apply_sky)
                # TODO: temp disabled since thumbnail generation does not work now.
                # ui.MenuItem("Generate thumbnail", triggered_fn=self._on_generate_thumbnail)
        self._context_menu.show()

    def on_drag(self, item: EnvDetailItem) -> str:
        if self._drop_helper is None:
            return ""

        """Could be dragged to viewport window"""
        thumbnail = self.get_thumbnail(item)
        with ui.VStack(width=96):
            if thumbnail:
                ui.Spacer(height=2)
                with ui.HStack():
                    ui.Spacer()
                    # TODO: If using ui.ImageWithProvider here and dragging, crash happens when app shutdown.
                    # Now using ui.Image instead.
                    ui.Image(thumbnail, width=96, height=96)
                    ui.Spacer()
            ui.Label(
                item.name,
                word_wrap=False,
                elided_text=True,
                skip_draw_when_clipped=True,
                alignment=ui.Alignment.TOP,
                style_type_name_override="GridView.Item",
            )

        return ENV_DRAG_PAYLOAD_PREFIX + item.type + "::" + item.url

    def _apply_sky(self) -> None:
        self._model.execute(self._action_item)

    def _on_generate_thumbnail(self) -> None:
        # TODO: generate thumbnail for self._action_item
        # If done, call self._model.folder_changed(self._action_item.file) to update UI
        pass

    def _on_drop_accepted(self, url: str):
        return url.startswith(ENV_DRAG_PAYLOAD_PREFIX)

    def _on_drop(self, url: str, target, viewport_name, context_name):
        env_type, env_url = url[len(ENV_DRAG_PAYLOAD_PREFIX) :].split("::")
        item = EnvDetailItem(BrowserFile(env_url))
        return self._model.execute(item)
