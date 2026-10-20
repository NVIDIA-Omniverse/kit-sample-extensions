# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, Optional

import omni.kit.app
from omni import ui
from omni.kit.async_engine import run_coroutine

from ..extension import MarkupCore, get_instance
from ..model import MarkupItem


def on_edit(item: MarkupItem, markup_instance: MarkupCore, on_edit_begin_fn: Optional[Callable]) -> None:
    markup = markup_instance.get_markup(item.name)
    if (
        markup
        and markup_instance.can_edit_markup(markup)
        and markup_instance.begin_edit_markup(markup)
        and on_edit_begin_fn
    ):
        on_edit_begin_fn(item)


class MarkupItemHoverWidget:
    def __init__(self, item: MarkupItem, on_edit_begin_fn: Optional[Callable] = None):
        self._on_edit_begin_fn = on_edit_begin_fn
        self._markup_instance = get_instance()
        self._build_ui(item)
        self._button_hovered = False

    def destroy(self):
        self._markup_instance = None

    @property
    def visible(self) -> bool:  # pragma: no cover
        return self._container.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._container.visible = value

    def _build_ui(self, item: MarkupItem) -> None:
        self._container = ui.HStack()
        with self._container:
            with ui.HStack():
                ui.Spacer()
                with ui.ZStack(width=24):
                    ui.Rectangle(style_type_name_override="GridView.Hover.Frame")
                    with ui.HStack(width=24):
                        ui.Spacer()
                        with ui.VStack(width=18):
                            ui.Spacer()
                            self._edit_button = ui.Button(
                                "",
                                width=18,
                                name="edit",
                                mouse_pressed_fn=lambda x, y, btn, a, item=item: self._on_edit(btn, item),
                                style_type_name_override="GridView.Hover.Button",
                                tooltip="Edit Markup",
                                mouse_hovered_fn=self._on_button_hovered,
                                identifier="HoverEditButton",
                            )
                            ui.Spacer()
                            self._delete_button = ui.Button(
                                "",
                                width=18,
                                name="delete",
                                mouse_pressed_fn=lambda x, y, btn, a, item=item: self._on_remove(btn, item),
                                style_type_name_override="GridView.Hover.Button",
                                tooltip="Delete Markup",
                                mouse_hovered_fn=self._on_button_hovered,
                                identifier="HoverDeleteButton",
                            )
                            ui.Spacer()
                        ui.Spacer()

    def _on_edit(self, btn: int, item: MarkupItem) -> None:
        if btn == 0 and isinstance(self._markup_instance, MarkupCore):
            self._container.visible = False
            self._button_hovered = False
            on_edit(item, self._markup_instance, self._on_edit_begin_fn)

    def _on_remove(self, btn: int, item: MarkupItem) -> None:
        if btn == 0:

            async def __delete(item: MarkupItem):
                await omni.kit.app.get_app().next_update_async()  # type: ignore
                markup = get_instance().get_markup(item.name)
                self._markup_instance.delete_markup(markup)

            run_coroutine(__delete(item))

    def _on_button_hovered(self, hovered: bool):
        self._button_hovered = hovered

    @property
    def button_hovered(self) -> bool:
        return self._button_hovered
