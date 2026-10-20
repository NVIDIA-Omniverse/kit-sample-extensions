# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from collections import namedtuple
from functools import partial
from typing import Callable, List, Optional

import omni.ui as ui


class GraphEditorCoreBreadcrumbs:
    _Item = namedtuple("_Item", "id name")

    def __init__(
        self,
        selected_fn=Callable[["GraphEditorCoreBreadcrumbs._Item"], None],
        navigation: Optional[List[str]] = None,
        **kwargs,
    ):
        self._selected_fn: Callable[["GraphEditorCoreBreadcrumbs._Item"], None] = selected_fn
        self._navigation: List[str] = navigation or []
        with ui.Frame(**kwargs):
            self.on_build()

    def destroy(self):
        self._selected_fn = None

    def on_build(self):
        with ui.HStack(width=0):
            first = True
            for i, name in enumerate(self._navigation):
                if first:
                    first = False
                else:
                    ui.Label(" > ")
                ui.Label(
                    name,
                    name="Navigation",
                    mouse_pressed_fn=lambda x, y, b, m, item=self._Item(i, name): self._selected_fn(item),
                )
