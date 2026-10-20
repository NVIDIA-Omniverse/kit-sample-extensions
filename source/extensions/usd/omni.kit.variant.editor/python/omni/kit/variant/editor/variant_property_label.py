# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import math
from typing import Dict, Optional

from omni import ui

from . import ui_const as ui_c
from .property_watcher import PropertyWatchButton


def split_selection(text, selection, match_case: bool = False):
    """
    Split given text to substrings to draw selected text. Result starts with unselected text.
    Example: "helloworld" "o" -> ["hell", "o", "w", "o", "rld"]
    Example: "helloworld" "helloworld" -> ["", "helloworld"]
    """
    if not selection:
        return [text, ""]
    else:
        origin_text = text
        if not match_case:
            selection = selection.lower()
            text = text.lower()
        elif text == selection:
            return ["", text]

    selection_len = len(selection)
    result = []
    while True:
        found = text.find(selection)

        result.append(origin_text if found < 0 else origin_text[:found])

        if found < 0:
            break
        else:
            result.append(origin_text[found : found + selection_len])
            text = text[found + selection_len :]
            origin_text = origin_text[found + selection_len :]

    return result


class VariantLabel:
    """
    Represents a label widget could show highlight word.
    Args:
        text (str): String of label.

    Keyword args:
        highlight (Optional[str]): Word to show highlight
        match_case (bool): Show highlight word with case sensitive. Default False.
        width (ui.Length): Widget length. Default ui.Fraction(1)
        height (ui.Length): Widget height. Default 0
        style (Dict): Custom style
    """

    def __init__(
        self,
        text: str,
        highlight: Optional[str] = None,
        match_case: bool = False,
        width: ui.Length = ui.Fraction(1),
        height: ui.Length = ui.Fraction(1),
        style: Dict = None,
        **kwargs,
    ):
        self._container: Optional[ui.HStack] = None
        self._property_watcher = None
        self.__text = text
        self.__highlight = highlight
        self.__match_case = match_case
        self.__width = width
        self.__height = height
        self.__style = ui_c.STYLE_PROPERTY_LABEL
        if style:
            self.__style.update(style)
        self.__label_kwargs = kwargs
        self._build_ui()

    def _build_ui(self):
        if not self._container:
            self._container = ui.HStack(
                width=self.__width,
                height=self.__height,
                style=self.__style,
                **self.__label_kwargs,
            )
        else:
            self._container.clear()

        kwargs = self.__label_kwargs.copy()
        if "alignment" in self.__style:
            alignment = self.__style.get("alignment")
        elif "alignment" in kwargs:
            alignment = kwargs.get("alignment")
        else:
            alignment = ui.Alignment.LEFT_CENTER
        left_aligned = alignment.name.startswith("LEFT")
        if not self.__text == "Checkpoint":
            property_path = kwargs.get("prop_path")

        self._is_variant = kwargs.get("is_variant", False)
        if self._is_variant:
            self.__text = f"VariantSet: {self.__text}"

        self._is_payloads = kwargs.get("is_payloads", False)
        self._is_references = kwargs.get("is_references", False)

        if not self.__highlight:
            with self._container:
                if not left_aligned:
                    ui.Spacer()
                ui.Label(
                    self.__text,
                    width=self.__width,
                    style=self.__style,
                    **kwargs,
                )
                if left_aligned:
                    ui.Spacer()

            with ui.VStack(width=self.__height, height=self.__height, style={"padding": 1}):
                ui.Spacer()
                if not self.__text == "Checkpoint":
                    self._property_watcher = PropertyWatchButton(
                        property_path,
                        width=self.__height,
                        height=self.__height,
                        tooltip_fn=lambda: self._create_tooltip(ui_c.TOOLTIP_BUTTON_OPINION_AUDITOR),
                        is_payloads=self._is_payloads,
                        is_references=self._is_references,
                        is_variant_path=self._is_variant,
                    )
                ui.Spacer()
        else:
            selection_chain = split_selection(self.__text, self.__highlight, match_case=self.__match_case)
            labelnames_chain = [kwargs.pop("name", ""), "highlight"]
            # Extend the label names depending on the size of the selection chain. Example, if it was [a, b]
            # and selection_chain is [z,y,x,w], it will become [a, b, a, b].
            labelnames_chain *= int(math.ceil(len(selection_chain) / len(labelnames_chain)))

            with self._container:
                if not left_aligned:
                    ui.Spacer()
                for current_text, current_name in zip(selection_chain, labelnames_chain):
                    if not current_text:
                        continue

                    # Only override highlight style, so we are otherwise compatible with Label
                    style_type = "VariantLabel" if current_name == "variant" else "Label"
                    style_type = kwargs.pop("style_type_name_override", style_type)

                    ui.Label(
                        current_text,
                        width=0,
                        name=current_name,
                        style_type_name_override=style_type,
                        style=self.__style,
                        **kwargs,
                    )
                if left_aligned:
                    ui.Spacer()
            with ui.VStack(width=self.__height, height=self.__height, style=self.__style):
                ui.Spacer()
                self._property_watcher = PropertyWatchButton(
                    property_path,
                    width=self.__height,
                    height=self.__height,
                    tooltip_fn=lambda: self._create_tooltip(ui_c.TOOLTIP_BUTTON_OPINION_AUDITOR),
                    is_variant_path=self._is_variant,
                )
                ui.Spacer()

    @property
    def widget(self) -> Optional[ui.HStack]:
        return self._container

    @property
    def visible(self) -> None:
        """
        Widget visibility
        """
        return self._container.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._container.visible = value

    @property
    def text(self) -> str:
        return self.__text

    @text.setter
    def text(self, value: str) -> None:
        self.__text = value
        self._build_ui()

    @property
    def highlight(self) -> Optional[str]:
        return self.__highlight

    @highlight.setter
    def highlight(self, value: Optional[str]) -> None:
        self.__highlight = value
        self._build_ui()

    @property
    def text(self) -> str:
        return self.__text

    @text.setter
    def text(self, value: str) -> None:
        self.__text = value

    def __getattr__(self, attr):
        if getattr(self._container, attr):
            return getattr(self._container, attr)
        else:
            return getattr(self, attr)

    # Tooltip helper function
    def _create_tooltip(self, text: str):
        with ui.ZStack(style=ui_c.STYLE_TOOLTIP):
            ui.Rectangle()
            ui.Label(text, style=ui_c.STYLE_TOOLTIP_TEXT)

    def update(self):
        self._property_watcher.update()
