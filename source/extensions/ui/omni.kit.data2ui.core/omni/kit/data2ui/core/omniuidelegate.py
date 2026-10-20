# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from collections import ChainMap
from dataclasses import dataclass
from math import pi
from typing import Callable, TypedDict

import carb.settings
import omni.usd
from omni import ui
from omni.ui import scene as sc
from pxr import Sdf, Tf, Usd

from .delegate import Delegate
from .event import WeakEvent
from .model import (
    Button,
    Circle,
    CollapsableFrame,
    Container,
    Frame,
    HStack,
    Image,
    Label,
    Line,
    Placer,
    Rectangle,
    ScrollingFrame,
    Spacer,
    Stack,
    Triangle,
    ViewportButton,
    ViewportCircle,
    VStack,
    ZStack,
)


class OmniUiDelegate(Delegate):
    pass


# Because we had previously been exposing `ui.Image` as our image widget, I need to create a compatibility hack
# This should allow for existing stages alerady using the old Image primitive to smoothly transition to the
# provider backed widget instead.
class ImageWithProviderProxy(ui.ImageWithProvider):
    def __init__(self, *args, **kwargs):
        kwargs["style_type_name_override"] = "Image"
        super().__init__(*args, **kwargs)

    @property
    def image_url(self) -> str:
        return self.style.get("image_url", "") if isinstance(self.style, dict) else ""

    @image_url.setter
    def image_url(self, value):
        style = self.style if isinstance(self.style, dict) else {}
        self.style = {**style, "image_url": value}

    @property
    def fill_policy(self) -> ui.FillPolicy:
        return ui.FillPolicy(int(super().fill_policy))

    @fill_policy.setter
    def fill_policy(self, value) -> None:
        if isinstance(value, ui.FillPolicy):
            ui.ImageWithProvider.fill_policy.fset(self, ui.IwpFillPolicy(int(value)))
        elif isinstance(value, int):
            ui.ImageWithProvider.fill_policy.fset(self, ui.IwpFillPolicy(value))


class ButtonProxy(ui.Button):
    @property
    def clicked_fn(self):
        # Returning `None` here for a few reasons.
        # 1) Because ui.Button lacks a `get_clicked_fn` method
        # 2) Because syncing with the view checks to see if the previous value is `None` or not, and this ensures the
        #    the callable is properly updated
        return

    @clicked_fn.setter
    def clicked_fn(self, callable):
        self.set_clicked_fn(callable)


class DistanceManager(sc.GestureManager):
    def should_prevent(self, gesture: sc.AbstractGesture, preventer: sc.AbstractGesture) -> bool:
        if type(gesture) == type(preventer):
            if preventer.state in (sc.GestureState.BEGAN, sc.GestureState.CHANGED):
                return gesture.gesture_payload.ray_distance > preventer.gesture_payload.ray_distance
        return False


class ViewportButtonItem(sc.AbstractManipulatorItem):
    def __init__(self):
        super().__init__()
        self.style_changed_event = WeakEvent()
        self.prim_path = None
        self.target_path = Sdf.Path()
        self.hovered = False
        self.pressed = False
        self.visible = True
        self.selected = False
        self.checked = False
        self.enabled = True
        self.height = 20
        self.width = 20
        self.radius = 20
        self.image_url = ""
        self.style = {}
        self.__manager = DistanceManager()
        self.click_gesture = sc.ClickGesture(manager=self.__manager)
        self.hover_gesture = sc.HoverGesture(
            manager=self.__manager,
            on_began_fn=lambda *x, **kw: setattr(self, "hovered", True),
            on_ended_fn=lambda *x, **kw: setattr(self, "hovered", False),
        )
        self.drag_gesture = sc.DragGesture(
            manager=self.__manager,
            on_began_fn=lambda *x, **kw: setattr(self, "pressed", True),
            on_ended_fn=lambda *x, **kw: setattr(self, "pressed", False),
        )

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self.style_changed_event()

    @property
    def pressed(self):
        return self._pressed

    @pressed.setter
    def pressed(self, value):
        self._pressed = value
        self.style_changed_event()

    @property
    def hovered(self):
        return self._hovered

    @hovered.setter
    def hovered(self, value):
        self._hovered = value
        self.style_changed_event()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        self.style_changed_event()

    @property
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, value):
        self._checked = value
        self.style_changed_event()

    @property
    def target_path(self):
        return self._target_path

    @target_path.setter
    def target_path(self, value):
        self._target_path = value
        self.style_changed_event()

    @property
    def image_url(self) -> str:
        return self._image_url

    @image_url.setter
    def image_url(self, image_url: str):
        self._image_url = image_url
        self.style_changed_event()

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, radius: float):
        self._radius = radius
        self.style_changed_event()

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, height: float):
        self._height = height
        self.style_changed_event()

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, width: float):
        self._width = width
        self.style_changed_event()

    def destroy(self):
        # Needed to keep interface consistent, should be used for cleaning up any resources that aren't tracked by GC.
        return

    @property
    def clicked_fn(self):
        # Return None so that the callable is always properly updated during sync.
        return

    @clicked_fn.setter
    def clicked_fn(self, callable: Callable[..., None]):
        # Gestures get passed specific arguments, but our callables and events don't.
        # This is holding a hard reference to the callable though, which might be undesirable.
        self.click_gesture.set_on_ended_fn(lambda *x, **kw: callable() if self.enabled else None)

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
        self._style = value

    @property
    def active_style(self) -> ChainMap:
        # Checks in order that matches the C++ code found in omni.ui
        if not self.enabled:
            return ChainMap(
                self._style.get("ViewportButton:disabled", {}),
                self._style.get(":disabled", {}),
                self._style.get("ViewportButton", {}),
                self._style,
            )
        if self.checked:
            return ChainMap(
                self._style.get("ViewportButton:checked", {}),
                self._style.get(":checked", {}),
                self._style.get("ViewportButton", {}),
                self._style,
            )
        if self.selected:
            return ChainMap(
                self._style.get("ViewportButton:selected", {}),
                self._style.get(":selected", {}),
                self._style.get("ViewportButton", {}),
                self._style,
            )
        if self.pressed:
            return ChainMap(
                self._style.get("ViewportButton:pressed", {}),
                self._style.get(":pressed", {}),
                self._style.get("ViewportButton", {}),
                self._style,
            )
        if self.hovered:
            return ChainMap(
                self._style.get("ViewportButton:hovered", {}),
                self._style.get(":hovered", {}),
                self._style.get("ViewportButton", {}),
                self._style,
            )
        return ChainMap(
            self._style.get("ViewportButton", {}),
            self._style,
        )


class ViewportCircleItem(sc.AbstractManipulatorItem):
    def __init__(self):
        super().__init__()
        self.style_changed_event = WeakEvent()
        self.prim_path = None
        self.target_path = Sdf.Path()
        self.hovered = False
        self.pressed = False
        self.visible = True
        self.selected = False
        self.checked = False
        self.enabled = True
        self.height = 20
        self.width = 20
        self.radius = 20
        self.image_url = ""
        self.style = {}
        self.__manager = DistanceManager()
        self.click_gesture = sc.ClickGesture(manager=self.__manager)
        self.hover_gesture = sc.HoverGesture(
            manager=self.__manager,
            on_began_fn=lambda *x, **kw: setattr(self, "hovered", True),
            on_ended_fn=lambda *x, **kw: setattr(self, "hovered", False),
        )
        self.drag_gesture = sc.DragGesture(
            manager=self.__manager,
            on_began_fn=lambda *x, **kw: setattr(self, "pressed", True),
            on_ended_fn=lambda *x, **kw: setattr(self, "pressed", False),
        )

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self.style_changed_event()

    @property
    def pressed(self):
        return self._pressed

    @pressed.setter
    def pressed(self, value):
        self._pressed = value
        self.style_changed_event()

    @property
    def hovered(self):
        return self._hovered

    @hovered.setter
    def hovered(self, value):
        self._hovered = value
        self.style_changed_event()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        self.style_changed_event()

    @property
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, value):
        self._checked = value
        self.style_changed_event()

    @property
    def target_path(self):
        return self._target_path

    @target_path.setter
    def target_path(self, value):
        self._target_path = value
        self.style_changed_event()

    @property
    def image_url(self) -> str:
        return self._image_url

    @image_url.setter
    def image_url(self, image_url: str):
        self._image_url = image_url
        self.style_changed_event()

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, radius: float):
        self._radius = radius
        self.style_changed_event()

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, height: float):
        self._height = height
        self.style_changed_event()

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, width: float):
        self._width = width
        self.style_changed_event()

    def destroy(self):
        # Needed to keep interface consistent, should be used for cleaning up any resources that aren't tracked by GC.
        return

    @property
    def clicked_fn(self):
        # Return None so that the callable is always properly updated during sync.
        return

    @clicked_fn.setter
    def clicked_fn(self, callable: Callable[..., None]):
        # Gestures get passed specific arguments, but our callables and events don't.
        # This is holding a hard reference to the callable though, which might be undesirable.
        self.click_gesture.set_on_ended_fn(lambda *x, **kw: callable() if self.enabled else None)

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
        self._style = value

    @property
    def active_style(self) -> ChainMap:
        # Checks in order that matches the C++ code found in omni.ui
        if not self.enabled:
            return ChainMap(
                self._style.get("ViewportCircle:disabled", {}),
                self._style.get(":disabled", {}),
                self._style.get("ViewportCircle", {}),
                self._style,
            )
        if self.checked:
            return ChainMap(
                self._style.get("ViewportCircle:checked", {}),
                self._style.get(":checked", {}),
                self._style.get("ViewportCircle", {}),
                self._style,
            )
        if self.selected:
            return ChainMap(
                self._style.get("ViewportCircle:selected", {}),
                self._style.get(":selected", {}),
                self._style.get("ViewportCircle", {}),
                self._style,
            )
        if self.pressed:
            return ChainMap(
                self._style.get("ViewportCircle:pressed", {}),
                self._style.get(":pressed", {}),
                self._style.get("ViewportCircle", {}),
                self._style,
            )
        if self.hovered:
            return ChainMap(
                self._style.get("ViewportCircle:hovered", {}),
                self._style.get(":hovered", {}),
                self._style.get("ViewportCircle", {}),
                self._style,
            )
        return ChainMap(
            self._style.get("ViewportCircle", {}),
            self._style,
        )


@dataclass(unsafe_hash=True)
class ViewportCircleBundle:
    item: ViewportCircleItem
    context_name: str

    def __post_init__(self):
        world = omni.usd.get_context(self.context_name).compute_path_world_transform(str(self.item.target_path))[12:15]
        transform = sc.Matrix44.get_translation_matrix(*world)
        self.__transform = sc.Transform(transform=transform)
        with self.__transform:
            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                with sc.Transform(scale_to=sc.Space.SCREEN):
                    self.__base = sc.Arc(
                        radius=self.item.active_style.get("radius", 20.0),
                        begin=0,
                        end=pi * 2,
                        wireframe=False,
                        color=self.item.active_style.get("background_color", 0xFFFFFFFF),
                        visible=self.item.visible,
                        thickness=self.item.active_style.get("border_width", 0.0),
                        gestures=[
                            self.item.click_gesture,
                            self.item.hover_gesture,
                            self.item.drag_gesture,
                        ],
                    )
                    self.__outline = sc.Arc(
                        radius=self.item.active_style.get("radius", 20.0)
                        + self.item.active_style.get("border_width", 0.0) / 2,
                        begin=0,
                        end=pi * 2,
                        wireframe=True,
                        color=self.item.active_style.get("border_color", 0xFFFFFFFF),
                        visible=self.item.visible,
                        thickness=self.item.active_style.get("border_width", 0.0),
                    )
        self.item.style_changed_event += self.__on_style_changed

    def __on_style_changed(self):
        self.__base.radius = self.item.active_style.get("radius", 20.0)
        self.__base.color = self.item.active_style.get("background_color", 0xFFFFFFFF)
        self.__base.visible = self.item.visible
        self.__base.thickness = self.item.active_style.get("border_width", 0.0)

        self.__outline.radius = self.item.active_style.get("radius", 20.0)
        self.__outline.color = self.item.active_style.get("border_color", 0xFFFFFFFF)
        self.__outline.visible = self.item.visible
        self.__outline.thickness = self.item.active_style.get("border_width", 0.0)
        world = omni.usd.get_context(self.context_name).compute_path_world_transform(str(self.item.target_path))[12:15]
        self.__transform.transform = sc.Matrix44.get_translation_matrix(*world)

    def destroy(self):
        self.__transform.clear()


@dataclass(unsafe_hash=True)
class ViewportButtonBundle:
    item: ViewportButtonItem
    context_name: str

    def __post_init__(self):
        world = omni.usd.get_context(self.context_name).compute_path_world_transform(str(self.item.target_path))[12:15]
        transform = sc.Matrix44.get_translation_matrix(*world)
        self.__transform = sc.Transform(transform=transform)
        with self.__transform:
            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                with sc.Transform(scale_to=sc.Space.SCREEN):
                    if image_url := self.item.active_style.get("image_url", ""):
                        self.__base = sc.Image(
                            source_url=image_url,
                            fill_policy=sc.Image.FillPolicy.PRESERVE_ASPECT_CROP,
                            height=self.item.active_style.get("height", 20.0),
                            width=self.item.active_style.get("width", 20.0),
                            wireframe=False,
                            color=self.item.active_style.get("background_color", 0xFFFFFFFF),
                            visible=self.item.visible,
                            thickness=self.item.active_style.get("border_width", 0.0),
                            gestures=[
                                self.item.click_gesture,
                                self.item.hover_gesture,
                                self.item.drag_gesture,
                            ],
                        )
                    else:
                        self.__base = sc.Rectangle(
                            height=self.item.active_style.get("height", 20.0),
                            width=self.item.active_style.get("width", 20.0),
                            begin=0,
                            end=pi * 2,
                            wireframe=False,
                            color=self.item.active_style.get("background_color", 0xFFFFFFFF),
                            visible=self.item.visible,
                            thickness=self.item.active_style.get("border_width", 0.0),
                            gestures=[
                                self.item.click_gesture,
                                self.item.hover_gesture,
                                self.item.drag_gesture,
                            ],
                        )
                    self.__outline = sc.Rectangle(
                        height=self.item.active_style.get("height", 20.0)
                        + self.item.active_style.get("border_width", 0.0) / 2,
                        width=self.item.active_style.get("width", 20.0)
                        + self.item.active_style.get("border_width", 0.0) / 2,
                        begin=0,
                        end=pi * 2,
                        wireframe=True,
                        color=self.item.active_style.get("border_color", 0xFFFFFFFF),
                        visible=self.item.visible,
                        thickness=self.item.active_style.get("border_width", 0.0),
                    )
        self.item.style_changed_event += self.__on_style_changed

    def __on_style_changed(self):
        self.__base.height = self.item.active_style.get("height", 20.0)
        self.__base.width = self.item.active_style.get("width", 20.0)
        self.__base.color = self.item.active_style.get("background_color", 0xFFFFFFFF)
        self.__base.visible = self.item.visible
        self.__base.thickness = self.item.active_style.get("border_width", 0.0)

        self.__outline.height = self.item.active_style.get("height", 20.0)
        self.__outline.width = self.item.active_style.get("width", 20.0)
        self.__outline.color = self.item.active_style.get("border_color", 0xFFFFFFFF)
        self.__outline.visible = self.item.visible
        self.__outline.thickness = self.item.active_style.get("border_width", 0.0)
        world = omni.usd.get_context(self.context_name).compute_path_world_transform(str(self.item.target_path))[12:15]
        self.__transform.transform = sc.Matrix44.get_translation_matrix(*world)

    def destroy(self):
        self.__transform.clear()


class ButtonManipulator(sc.Manipulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__context_name = kwargs.pop("context_name", "")
        self._context = omni.usd.get_context(self.__context_name)
        self._stage: Usd.Stage = self._context.get_stage()
        self._items: set[ViewportButtonItem | ViewportCircleItem] = set()
        self.__items: dict[ViewportButtonItem | ViewportCircleItem, ViewportButtonBundle | ViewportCircleBundle] = {}
        self.root = sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 0, 0))

    def on_model_updated(self, item: ViewportButtonItem | ViewportCircleItem):
        if not self._stage:
            return
        # An item without a prim path has no USD object. Kit 111's USD bindings (25.11) reject None for the SdfPath
        # argument with an ArgumentError instead of treating it as an empty path, so test it explicitly.
        prim_path = item.prim_path
        if prim_path is not None and self._stage.GetObjectAtPath(prim_path):
            if item not in self.__items:
                with self.root:
                    if isinstance(item, ViewportButtonItem):
                        self.__items[item] = ViewportButtonBundle(item=item, context_name=self.__context_name)
                    elif isinstance(item, ViewportCircleItem):
                        self.__items[item] = ViewportCircleBundle(item=item, context_name=self.__context_name)

            item.style_changed_event()
        else:
            if bundle := self.__items.pop(item, None):
                bundle.destroy()


OmniUiDelegate.Frame = OmniUiDelegate.register_type(ui.Frame, Frame)  # type: ignore
OmniUiDelegate.ScrollingFrame = OmniUiDelegate.register_type(ui.ScrollingFrame, ScrollingFrame)  # type: ignore
OmniUiDelegate.CollapsableFrame = OmniUiDelegate.register_type(ui.CollapsableFrame, CollapsableFrame)  # type: ignore
OmniUiDelegate.Stack = OmniUiDelegate.register_type(ui.Stack, Stack)  # type: ignore
OmniUiDelegate.HStack = OmniUiDelegate.register_type(ui.HStack, HStack)  # type: ignore
OmniUiDelegate.VStack = OmniUiDelegate.register_type(ui.VStack, VStack)  # type: ignore
OmniUiDelegate.ZStack = OmniUiDelegate.register_type(ui.ZStack, ZStack)  # type: ignore
OmniUiDelegate.Placer = OmniUiDelegate.register_type(ui.Placer, Placer)  # type: ignore
OmniUiDelegate.Label = OmniUiDelegate.register_type(ui.Label, Label)  # type: ignore
OmniUiDelegate.Button = OmniUiDelegate.register_type(ButtonProxy, Button)  # type: ignore
OmniUiDelegate.Image = OmniUiDelegate.register_type(ImageWithProviderProxy, Image)  # type: ignore
OmniUiDelegate.Spacer = OmniUiDelegate.register_type(ui.Spacer, Spacer)  # type: ignore
OmniUiDelegate.Rectangle = OmniUiDelegate.register_type(ui.Rectangle, Rectangle)  # type: ignore
OmniUiDelegate.Line = OmniUiDelegate.register_type(ui.Line, Line)  # type: ignore
OmniUiDelegate.Circle = OmniUiDelegate.register_type(ui.Circle, Circle)  # type: ignore
OmniUiDelegate.Triangle = OmniUiDelegate.register_type(ui.Triangle, Triangle)  # type: ignore
OmniUiDelegate.ViewportButton = OmniUiDelegate.register_type(ViewportButtonItem, ViewportButton)  # type: ignore
OmniUiDelegate.ViewportCircle = OmniUiDelegate.register_type(ViewportCircleItem, ViewportCircle)  # type: ignore
