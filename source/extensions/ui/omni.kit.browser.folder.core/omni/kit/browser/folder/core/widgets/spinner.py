# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["RotatingSpinner"]

import asyncio
from typing import Callable, Optional

import omni.kit.app
import omni.ui as ui
from omni.ui import scene as sc

# Slot size, matching every other icon slot in these toolbars (search bar and material toolbar
# both use a 26px slot around a 20px image), so the spinner lines up with its neighbours.
SPINNER_SIZE = 26
# Rendered size of the glyph itself. Kept to the same 20px as the neighbouring icons: a glyph
# filling the whole 26px slot reads as noticeably bigger than the buttons either side of it.
GLYPH_SIZE = 20
# sc.SceneView spans -1..1, so the full view is 2.0 scene units wide.
GLYPH_SCENE_SIZE = 2.0 * GLYPH_SIZE / SPINNER_SIZE
SPINNER_IMAGE = "${omni.kit.browser.core}/icons/omni_logo_24.png"
ROTATE_SPEED = 1.5

# Chrome matching the toolbar's other buttons, so the slot reads as pressable rather than as a
# status icon that happens to be clickable. SearchBar.Button's colours, restated because that style
# lives in another extension and a Rectangle does not take a Button's state styling. Keyed on the
# name rather than :hovered, because the hover is driven by hand - see RotatingSpinner.__on_hover.
SPINNER_STYLE = {
    "Rectangle::scan_progress": {"background_color": 0x00000000, "border_radius": 2},
    "Rectangle::scan_progress_hovered": {"background_color": 0xFF3A3A3A, "border_radius": 2},
}


class RotatingSpinner:
    """
    A small always-present slot that shows a rotating glyph while work is in progress.

    The slot keeps a constant width whether or not the glyph is drawn, so neighbouring toolbar
    widgets never shift when a scan starts or ends.

    Args:
        clicked_fn: Called when the spinner is clicked. Optional.
        tooltip_fn: Returns the tooltip text; called each time the tooltip is built, so it can
            report live progress. Optional.
    """

    def __init__(self, clicked_fn: Optional[Callable[[], None]] = None, tooltip_fn: Optional[Callable[[], str]] = None):
        self._clicked_fn = clicked_fn
        self._tooltip_fn = tooltip_fn
        self._active = False
        self._rotate_future: Optional[asyncio.Future] = None
        self._transform: Optional[sc.Transform] = None

        # A fixed-size stack: the glyph is shown or hidden inside it, the slot itself never moves.
        self._container = ui.ZStack(width=SPINNER_SIZE, height=SPINNER_SIZE, content_clipping=1, style=SPINNER_STYLE)
        with self._container:
            # Button chrome, underneath everything. Hidden with the glyph: an empty slot must not
            # highlight on hover, or the toolbar grows a button that does nothing.
            self._chrome = ui.Rectangle(name="scan_progress", visible=False)
            self._glyph = ui.VStack(visible=False)
            with self._glyph:
                ui.Spacer()
                with ui.HStack(height=SPINNER_SIZE):
                    ui.Spacer()
                    # The view stays slot-sized while the glyph is smaller, which also gives the
                    # rotation room: a glyph spanning the full view would clip its own corners as
                    # it turns through 45 degrees.
                    with sc.SceneView(width=SPINNER_SIZE, height=SPINNER_SIZE).scene:
                        self._transform = sc.Transform()
                        with self._transform:
                            sc.Image(SPINNER_IMAGE, width=GLYPH_SCENE_SIZE, height=GLYPH_SCENE_SIZE)
                    ui.Spacer()
                ui.Spacer()
            # Transparent hit area so the whole slot is clickable, not just the glyph pixels. It
            # sits on top, so it - not the chrome beneath - is what receives the hover; the two are
            # kept in step by __on_hover.
            self._button = ui.InvisibleButton(clicked_fn=self.__on_clicked)
            self._button.set_mouse_hovered_fn(self.__on_hover)

    def __on_hover(self, hovered: bool) -> None:
        """Paint the chrome as the button beside it would. omni.ui cannot do this for a Rectangle
        under an InvisibleButton, because the button takes the mouse."""
        if self._chrome is None:
            return
        self._chrome.name = "scan_progress_hovered" if hovered else "scan_progress"

    def destroy(self) -> None:
        self.__stop_rotation()
        self._clicked_fn = None
        self._tooltip_fn = None
        self._transform = None
        self._container = None
        self._glyph = None
        self._chrome = None
        self._button = None

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        if value == self._active:
            return
        self._active = value
        if self._glyph is not None:
            self._glyph.visible = value
        if self._chrome is not None:
            self._chrome.visible = value
        if self._button is not None:
            self._button.enabled = value
        if value:
            self.__start_rotation()
        else:
            self.__stop_rotation()

    def refresh_tooltip(self) -> None:
        """Rebuild the tooltip from ``tooltip_fn``. Cheap; call it on progress updates."""
        if self._button is None or self._tooltip_fn is None:
            return
        self._button.tooltip = self._tooltip_fn()

    def __on_clicked(self) -> None:
        if self._active and self._clicked_fn is not None:
            self._clicked_fn()

    def __start_rotation(self) -> None:
        if self._rotate_future is not None and not self._rotate_future.done():
            return

        async def _rotate():
            angle = 0.0
            while True:
                delta = await omni.kit.app.get_app().next_update_async()
                if self._transform is None:
                    return
                angle -= delta * ROTATE_SPEED
                self._transform.transform = sc.Matrix44.get_rotation_matrix(0, 0, angle)

        self._rotate_future = asyncio.ensure_future(_rotate())

    def __stop_rotation(self) -> None:
        if self._rotate_future is not None:
            if not self._rotate_future.done():
                self._rotate_future.cancel()
            self._rotate_future = None
