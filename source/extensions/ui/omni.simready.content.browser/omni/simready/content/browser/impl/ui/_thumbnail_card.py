# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Patches FileBrowserItemCard.draw_badges to render a relevance score in the top-right corner.

The patch is opt-in per item: it only activates when the item has a ``relevance``
attribute (float).  All other items fall back to the original draw_badges behaviour,
so normal file-browser usage is unaffected.
"""

from __future__ import annotations

import omni.ui as ui
from omni.kit.widget.filebrowser import ALERT_ERROR, ALERT_WARNING
from omni.kit.widget.filebrowser.card import FileBrowserItemCard
from omni.kit.widget.filebrowser.style import ICON_PATH
from omni.kit.widget.search_delegate.model import SearchResultsItemFactory
from omni.ui import color as cl

# ---------------------------------------------------------------------------
# Save the original implementations so we can restore them on shutdown.
# ---------------------------------------------------------------------------
_original_draw_badges = FileBrowserItemCard.draw_badges
_original_create_item = SearchResultsItemFactory.create_item


def _patched_draw_badges(self: FileBrowserItemCard) -> None:
    """Draw badges plus an optional relevance score label in the top-right corner."""
    relevance: float | None = getattr(self._item, "relevance", None)

    if relevance is None:
        # No relevance score on this item — preserve existing behaviour.
        _original_draw_badges(self)
        return

    if not self._item:
        return

    # -----------------------------------------------------------------------
    # Collect standard bottom-right icon badges (same logic as the original).
    # -----------------------------------------------------------------------
    badges: list[tuple[str, str]] = []
    if self._get_badges_fn:
        badges = list(self._get_badges_fn(self._item) or [])

    alert = getattr(self._item, "alert", None)
    if alert:
        sev, msg = alert
        theme = getattr(self, "_theme", "NvidiaDark")
        if sev == ALERT_WARNING:
            badges.append((f"{ICON_PATH}/{theme}/warn.svg", msg))
        elif sev == ALERT_ERROR:
            badges.append((f"{ICON_PATH}/{theme}/error.svg", msg))
        else:
            badges.append((f"{ICON_PATH}/{theme}/info.svg", msg))

    badge_size = 14
    margin_w = 6
    margin_h = 8
    shadow_offset = 1

    # -----------------------------------------------------------------------
    # Draw everything into _overlay_frame in a single pass so that both the
    # relevance label (top-right) and the icon badges (bottom-right) live
    # inside one ZStack, which is the single child of the overlay frame.
    # -----------------------------------------------------------------------
    with self._overlay_frame:
        with ui.ZStack():

            # -- relevance label: top-right --------------------------------
            with ui.VStack():
                with ui.HStack(height=20):
                    ui.Spacer()
                    with ui.ZStack(width=30, height=30):
                        ui.Rectangle(
                            style={
                                "background_color": cl(1.0, 1.0, 1.0, 0.9),
                                "border_radius": 3.0,
                            }
                        )
                        if relevance > 0.8:
                            label_color = cl(0.20, 0.85, 0.20, 1.0)
                        elif relevance > 0.4:
                            label_color = cl(1.0, 0.55, 0.0, 1.0)
                        else:
                            label_color = cl(0.85, 0.15, 0.15, 1.0)
                        ui.Label(
                            f"{relevance:.1f}",
                            alignment=ui.Alignment.CENTER,
                            style={
                                "color": label_color,
                                "font_size": 15,
                            },
                        )
                    ui.Spacer(width=4)
                ui.Spacer()

            # -- Icon badges: bottom-right (shadow + image passes) ----------
            if badges:
                # Shadow pass
                with ui.VStack():
                    ui.Spacer()
                    with ui.HStack(height=badge_size, spacing=2):
                        ui.Spacer()
                        for icon, _ in badges:
                            ui.ImageWithProvider(
                                icon,
                                width=badge_size,
                                name="shadow",
                                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                                style_type_name_override="Card.Badge",
                            )
                        ui.Spacer(width=margin_w - shadow_offset)
                    ui.Spacer(height=margin_h - shadow_offset)

                # Image pass
                with ui.VStack():
                    ui.Spacer()
                    with ui.HStack(height=badge_size, spacing=2):
                        ui.Spacer()
                        for icon, tooltip in badges:
                            ui.ImageWithProvider(
                                icon,
                                tooltip=tooltip,
                                width=badge_size,
                                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                                style_type_name_override="Card.Badge",
                            )
                        ui.Spacer(width=margin_w)
                    ui.Spacer(height=margin_h)


@staticmethod
def _patched_create_item(search_item):
    """Forward the ``relevance`` attribute from the source AbstractSearchItem to
    the SearchResultsItem wrapper so that draw_badges can read it later."""
    item = _original_create_item(search_item)
    if item is not None:
        item.relevance = getattr(search_item, "relevance", None)
    return item


# ---------------------------------------------------------------------------
# Public install / uninstall helpers called from BrowserExtensionImpl.
# ---------------------------------------------------------------------------


def install_patch() -> None:
    """Install both patches:
    - SearchResultsItemFactory.create_item: forwards ``relevance`` to the wrapper item
    - FileBrowserItemCard.draw_badges: renders the relevance label in top-right
    """
    SearchResultsItemFactory.create_item = _patched_create_item
    FileBrowserItemCard.draw_badges = _patched_draw_badges


def uninstall_patch() -> None:
    """Restore both original implementations."""
    SearchResultsItemFactory.create_item = _original_create_item
    FileBrowserItemCard.draw_badges = _original_draw_badges
