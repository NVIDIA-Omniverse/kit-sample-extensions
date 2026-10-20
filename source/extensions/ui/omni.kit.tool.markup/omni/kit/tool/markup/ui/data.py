# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import ctypes
import importlib
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, ClassVar, Tuple, TypeVar, cast

from omni import ui
from omni.kit.markup.core import get_instance as get_markup_instance
from pxr import Sdf, Usd

from .events import MarkupEvent

T = TypeVar("T")


class MarkupType(str, Enum):
    SELECT = "Select"
    TEXT = "Label"
    ARROW = "Arrow"
    LINE = "Line"
    CIRCLE = "Circle"
    RECTANGLE = "Rectangle"
    SEGMENT = "LineSegment"


def _get_attribute_from_prim(prim: Usd.Prim, attr: str) -> Usd.Attribute:
    return cast(Usd.Attribute, prim.GetAttribute(attr))


@dataclass
class MarkupElement:

    # Its a bit magic, but lets me not care about the actual element subclasses.
    def __new__(cls, prim, *args, **kwargs):
        for s in cls.__subclasses__():
            prim_type = _get_attribute_from_prim(prim, "type").Get() or ""
            if prim_type in (*s.old_prim_type, s.prim_type):
                return s(prim)
        return super().__new__(cls)

    def __post_init__(self):
        self._style_cache = {}
        if self.style_name not in self.style:
            self.update_style(None)

    prim: Usd.Prim = field(repr=False)
    style_name: str = field(default="Markup.Viewport.Element", init=False)
    style_changed: MarkupEvent = field(default_factory=MarkupEvent, init=False, repr=False)
    color_changed: MarkupEvent = field(default_factory=MarkupEvent, init=False, repr=False)
    element_destroyed: MarkupEvent = field(default_factory=MarkupEvent, init=False, repr=False)
    text_model: ui.SimpleStringModel = field(default_factory=ui.SimpleStringModel, init=False, repr=False)
    old_style_names: ClassVar[Tuple[str, ...]] = ()
    old_prim_type: ClassVar[Tuple[str, ...]] = ()
    color_keys: ClassVar[Tuple[str, ...]] = ()
    prim_type: ClassVar[str]

    @property
    def path(self) -> Sdf.Path:
        return cast(Sdf.Path, self.prim.GetPath())

    @property
    def style(self) -> dict:
        from omni.ui import Alignment  # noqa: F401

        return self._style_cache or eval(_get_attribute_from_prim(self.prim, "style").Get() or "{}")

    @property
    def rect(self) -> "tuple[float, ...]":
        return _get_attribute_from_prim(self.prim, "rect").Get() or ()

    @property
    def type(self) -> str:
        return _get_attribute_from_prim(self.prim, "type").Get() or ""

    @property
    def text(self) -> str:
        return _get_attribute_from_prim(self.prim, "text").Get() or ""

    @property
    def points(self) -> "list[tuple[float, float]]":
        return _get_attribute_from_prim(self.prim, "points").Get() or []

    @property
    def color(self) -> int:  # pragma: no cover
        return self._get_style_value(self.color_keys[0], 0xFFFFFFFF) if self.color_keys else 0xFFFFFFFF

    @property
    def markup_instance(self):
        return get_markup_instance()

    @property
    def shape_type(self) -> str:  # pragma: no cover
        return ""

    @property
    def pixel_size(self) -> "tuple[float, ...]":
        if self.prim.IsValid():
            return _get_attribute_from_prim(self.prim, "pixel_size").Get() or None
        return None

    def _get_style_value(self, style_key: str, default: T) -> T:  # pragma: no cover
        missing = object()
        for name in (self.style_name,) + self.old_style_names:
            value = self.style.get(name, {}).get(style_key, missing)
            if value != missing:
                return cast(T, value)
        return default

    def update_style(self, style: "dict|None", *, update_prim: bool = False) -> None:
        style = style if style is not None else self.style
        if update_prim and self.can_edit() and self.markup_instance:
            self.markup_instance.update_element_attrs(self.path.name, element_style=style)
            self._style_cache.clear()
        self._style_cache.update(style)
        self.style_changed(style)

    def update_type(self):
        if self.can_edit() and self.markup_instance:
            self.markup_instance.update_element_attrs(
                self.path.name,
                ele_type=self.prim_type,
            )

    def destroy(self):
        if self.can_edit() and self.markup_instance:
            self.markup_instance.remove_element(self.path)
        self.element_destroyed(self)

    def update_rect(self, rect: "tuple[float, ...]") -> None:
        if self.can_edit() and self.markup_instance:
            self.markup_instance.update_element_pos(self.path.name, *rect)

    def can_edit(self) -> bool:
        inst = self.markup_instance
        if inst:
            markup = inst.get_markup_from_prim_path(self.path.GetParentPath().pathString)
            if markup:
                return inst.can_edit_markup(markup, show_messages=False)
        else:  # pragma: no cover
            return False


@dataclass
class ShapeElement(MarkupElement):
    style_name: str = field(default="Markup.Viewport.Shape", init=False)
    shape_type_changed: MarkupEvent = field(default_factory=MarkupEvent, init=False, repr=False)
    old_style_names: ClassVar[Tuple[str, ...]] = (
        "Rectangle",
        "Circle",
        "Ellipse",
        "FreeRectangle",
        "FreeCircle",
        "FreeEllipse",
    )
    prim_type: ClassVar[str] = "Shape"
    old_prim_type: ClassVar[Tuple[str, ...]] = ("Rectangle", "Circle")
    color_keys: ClassVar[Tuple[str, ...]] = ("border_color",)

    def __post_init__(self):
        super().__post_init__()
        if self.type in self.old_prim_type:
            self.update_shape_type(self.old_prim_type.index(self.type), update_prim=True)
            self.update_type()

    @property
    def color(self) -> int:
        return self._get_style_value("border_color", 0xFFFFFFFF)

    @color.setter
    def color(self, value: int) -> None:  # pragma: no cover
        self.color_changed(self, value)

    @property
    def stroke(self) -> int:
        return self._get_style_value("border_width", 1)

    @property
    def shape_type(self) -> str:
        return _get_attribute_from_prim(self.prim, "shape_type").Get() or ""

    @property
    def shape(self) -> int:
        return self.old_prim_type.index(self.shape_type)

    def update_style(
        self,
        *_,
        color: "int|None" = None,
        stroke: "int|None" = None,
        shape: "int|None" = None,
        update_prim: bool = False,
    ) -> None:
        if shape is not None:
            self.update_shape_type(shape, update_prim)

        style = {
            self.style_name: {
                **{key: color if color is not None else self.color for key in self.color_keys},
                "border_width": stroke if stroke is not None else self.stroke,
                "background_color": 0x0,
            },
            **{
                old_name: {
                    **{key: color if color is not None else self.color for key in self.color_keys},
                    "border_width": stroke if stroke is not None else self.stroke,
                    "background_color": 0x0,
                }
                for old_name in self.old_prim_type
            },
        }
        super().update_style(style, update_prim=update_prim)

    def update_shape_type(self, shape_type: int, update_prim: bool = False) -> None:
        if update_prim and self.can_edit() and self.markup_instance:
            self.markup_instance.update_element_attrs(self.path.name, shape_type=("Rectangle", "Circle")[shape_type])

        self.shape_type_changed(self)


@dataclass
class LineSegmentMarkup(MarkupElement):
    style_name: str = field(default="Markup.Viewport.LineSegment", init=False)
    old_style_names: ClassVar[Tuple[str, ...]] = ("FreeLine", "Line")
    prim_type: ClassVar[str] = MarkupType.SEGMENT
    old_prim_type: ClassVar[Tuple[str, ...]] = ()
    color_keys: ClassVar[Tuple[str, ...]] = ("color",)

    @property
    def color(self) -> int:
        return self._get_style_value("color", 0xFFFFFFFF)

    @color.setter
    def color(self, value: int) -> None:  # pragma: no cover
        self.color_changed(self, value)

    @property
    def stroke(self) -> int:
        return self._get_style_value("border_width", 1)

    def update_style(self, *_, color: "int|None" = None, stroke: "int|None" = None, update_prim: bool = False) -> None:
        style = {
            self.style_name: {
                **{key: color if color is not None else self.color for key in self.color_keys},
                "border_width": stroke if stroke is not None else self.stroke,
                "background_color": 0x0,
            },
        }
        super().update_style(style, update_prim=update_prim)


@dataclass
class ArrowMarkup(MarkupElement):

    style_name: str = field(default="Markup.Viewport.Arrow", init=False)
    old_style_names: ClassVar[Tuple[str, ...]] = (
        "Line",
        "FreeLine",
    )
    prim_type: ClassVar[str] = MarkupType.ARROW
    color_keys: ClassVar[Tuple[str, ...]] = ("color",)

    @property
    def color(self) -> int:
        return self._get_style_value("color", 0xFFFFFFFF)

    @color.setter
    def color(self, value: int) -> None:  # pragma: no cover
        self.color_changed(self, value)

    @property
    def stroke(self) -> int:
        return self._get_style_value("border_width", 1)

    @property
    def direction(self) -> int:
        return self.style.get("ArrowDirection", 0)

    def update_style(
        self,
        *_,
        color: "int|None" = None,
        stroke: "int|None" = None,
        direction: "int|None" = None,
        update_prim: bool = False,
    ) -> None:
        style = {
            self.style_name: {
                **{key: color if color is not None else self.color for key in self.color_keys},
                "border_width": stroke if stroke is not None else self.stroke,
                "background_color": 0x0,
            },
            "ArrowDirection": direction if direction is not None else self.direction,
        }
        super().update_style(style, update_prim=update_prim)


@dataclass
class DrawMarkup(MarkupElement):

    style_name: str = field(default="Markup.Viewport.Line", init=False)
    old_style_names: ClassVar[Tuple[str, ...]] = ("Line", "FreeLine", "FreeBezierCurve", "Circle")
    prim_type: ClassVar[str] = MarkupType.LINE
    color_keys: ClassVar[Tuple[str, ...]] = ("color", "background_color")

    @property
    def color(self) -> int:
        return self._get_style_value("color", 0xFFFFFFFF)

    @color.setter
    def color(self, value: int) -> None:  # pragma: no cover
        self.color_changed(self, value)

    @property
    def stroke(self) -> int:
        return self._get_style_value("border_width", 1)

    def update_style(self, *_, color: "int|None" = None, stroke: "int|None" = None, update_prim: bool = False) -> None:
        style = {
            self.style_name: {
                **{key: color if color is not None else self.color for key in self.color_keys},
                "border_width": stroke if stroke is not None else self.stroke,
            },
        }
        super().update_style(style, update_prim=update_prim)


@dataclass
class CommentMarkup(MarkupElement):

    style_name: str = field(default="Markup.Viewport.Comment", init=False)
    old_style_names: ClassVar[Tuple[str, ...]] = ("Label", "StringField", "Field", "Circle")
    prim_type: ClassVar[str] = MarkupType.TEXT
    color_keys: ClassVar[Tuple[str, ...]] = ("color", "secondary_color", "border_color")
    text_changed: MarkupEvent = field(default_factory=MarkupEvent, init=False, repr=False)

    def __post_init__(self):
        self.text_model.add_begin_edit_fn(self._on_text_edit_begin)
        self.text_model.add_end_edit_fn(self._on_text_edit_end)
        self.text_model.set_value(self.text)
        return super().__post_init__()

    @property
    def color(self) -> int:
        return self._get_style_value("color", 0xFFFFFFFF)

    @color.setter
    def color(self, value: int) -> None:  # pragma: no cover
        self.color_changed(self, value)

    @property
    def stroke(self) -> int:
        return self._get_style_value("border_width", 1)

    @property
    def font_size(self):
        return self._get_style_value("font_size", 18)

    def update_style(
        self,
        *_,
        color: "int|None" = None,
        stroke: "int|None" = None,
        font_size: "int|None" = None,
        text: "str|None" = None,
        update_prim: bool = False,
    ) -> None:
        # NOTE: OMFP-3180 if style is changed (e.g. font size is edited) after text has been entered
        # but before the text_edit_end function is invoked, we'll have text in the model that we don't
        # want to be lost -- so grab it here:
        text = self.text_model.as_string if text is None else text
        if text:
            self.update_text(text=text, update_prim=update_prim)
        style = {
            self.style_name: {
                **{key: color if color is not None else self.color for key in self.color_keys},
                "border_width": stroke if stroke is not None else self.stroke,
                "background_color": 0x0,
                "font_size": font_size if font_size is not None else self.font_size,
            },
        }
        super().update_style(style, update_prim=update_prim)

    def update_text(self, *_, text: "str|None" = None, update_prim: bool = False):
        text = self.text if text is None else text
        if update_prim and self.can_edit() and self.markup_instance:
            self.markup_instance.update_element_attrs(self.path.name, text=text)
        self.text_changed(self)

    def _on_text_edit_begin(self, model):
        model.as_string = self.text

    def _on_text_edit_end(self, model):
        self.update_text(text=model.as_string, update_prim=True)
