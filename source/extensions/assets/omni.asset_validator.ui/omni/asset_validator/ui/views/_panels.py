# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

__all__ = ["PanelWidget"]

from collections.abc import Callable
from typing import Any

import omni.ui

from ._style import PANEL_STYLE


class PanelWidget:
    def __init__(
        self,
        *,
        menu_build_fn: Callable[[], None],
        view_build_fn: Callable[[], Any],
    ) -> None:
        with omni.ui.HStack(style=PANEL_STYLE):
            with omni.ui.ZStack(width=0):
                with omni.ui.Placer(
                    offset_x=300,
                    draggable=True,
                    drag_axis=omni.ui.Axis.X,
                ):
                    omni.ui.Rectangle(width=4, name="splitter")

                with omni.ui.HStack():
                    self._frame = omni.ui.ScrollingFrame(build_fn=menu_build_fn)
                    omni.ui.Spacer(width=4)

            with omni.ui.VStack():
                with omni.ui.VStack():
                    view_build_fn()

    def rebuild(self) -> None:
        self._frame.rebuild()
        self._frame.scroll_y = 0
