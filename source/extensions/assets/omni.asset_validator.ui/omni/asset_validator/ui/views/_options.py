# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

import webbrowser
from collections.abc import Callable
from functools import partial

from omni.ui import (
    Alignment,
    Button,
    CheckBox,
    CollapsableFrame,
    Frame,
    HStack,
    Label,
    Spacer,
    Triangle,
    VStack,
    ZStack,
)

from ..models._options import OptionGroup, OptionItem, OptionMode, OptionModeModel, OptionsItemModel
from ._icons import Icons

__all__ = ["OptionModeViewsWidget", "OptionsWidget"]


class OptionModeViewsWidget:

    def __init__(self, model: OptionModeModel, build_fn: Callable[[OptionMode], None]):
        self._model = model
        self._build_fn = build_fn
        self._frames: dict[OptionMode, Frame] = {}
        self._subscription = None
        self._build_widget()

    def _build_widget(self):
        with ZStack():
            for mode in OptionMode:
                frame = Frame(build_fn=partial(self._build_fn, mode), visible=False)
                self._frames[mode] = frame
        self._subscription = self._model.subscribe_value_changed_fn(self._on_value_changed)
        self._on_value_changed(self._model)

    def _on_value_changed(self, value_model) -> None:
        for mode, frame in self._frames.items():
            frame.visible = mode == value_model.mode


class OptionsWidget:
    def __init__(self, model: OptionsItemModel):
        self._model = model
        with VStack(height=0):
            with HStack(height=30):
                self._create_toggle_button(enable=True)
                self._create_toggle_button(enable=False)

            Spacer(width=0, height=10)
            for item in model.get_item_children(None):
                with CollapsableFrame(item.model.name, build_header_fn=partial(self._build_header_fn, item.model)):
                    with VStack():
                        with HStack(height=30):
                            self._create_toggle_button(enable=True, item=item)
                            self._create_toggle_button(enable=False, item=item)
                        Spacer(height=10)
                        for child_item in model.get_item_children(item):
                            with HStack(height=18):
                                CheckBox(
                                    child_item.model,
                                    width=20,
                                    tooltip=child_item.model.description,
                                    enabled=child_item.model.enabled,
                                )
                                Label(
                                    child_item.model.name,
                                    tooltip=child_item.model.description,
                                    word_wrap=True,
                                )
                                if child_item.model.url:
                                    Button(
                                        width=20,
                                        height=20,
                                        image_url=Icons.HYPERLINK,
                                        clicked_fn=partial(self._open_url, url=child_item.model.url),
                                    )
                            Spacer(height=10)

    def _create_toggle_button(self, enable: bool, item: OptionItem | None = None) -> None:
        action = "Enable" if enable else "Disable"
        Button(
            f"{action} All",
            clicked_fn=partial(self._toggle_option, enable=enable, item=item),
        )

    def _toggle_option(self, enable: bool = True, item: OptionItem | None = None) -> None:
        if item is None:
            for option_item in self._model.get_item_children(None):
                for child in self._model.get_item_children(option_item):
                    child.model.selected = enable
        else:
            for child in self._model.get_item_children(item):
                child.model.selected = enable

    def _open_url(self, url: str) -> None:
        webbrowser.open(url)

    def _build_header_fn(self, model: OptionGroup, collapsed: bool, title: str) -> None:
        alignment = Alignment.CENTER_BOTTOM if not collapsed else Alignment.RIGHT_CENTER
        with HStack():
            with VStack(width=10):
                Spacer()
                with HStack():
                    Spacer(width=3)
                    Triangle(alignment=alignment, width=8, height=8, style={"background_color": 0xFFFFFFFF})
                    Spacer(width=7)
                Spacer()
            Label(model.name)
            Spacer()
            if model.url:
                with HStack(content_clipping=True, width=16):
                    Button(
                        width=16,
                        height=16,
                        image_url=Icons.HYPERLINK,
                        clicked_fn=partial(self._open_url, url=model.url),
                    )
