# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["SnapMarker", "MeasureSceneLabel", "MeasureAxisStackLabel"]

from typing import Callable, List, Optional, Union

from carb.windowing import CursorStandardShape
from omni import ui
from omni.kit.window.cursor import get_main_window_cursor
from omni.ui import scene as sc
from pxr import Gf

from ...common import LABEL_SCALE_MAPPING, MeasureAxis, MeasureMode, SnapMode
from ...interface.style import get_icon_path
from ...manager import ReferenceManager
from ..gesture_manager import PreventOthers
from .viewport_mode_model import GesturePreventionManager

SNAP_SIZE = 32
PADDING = 2


class SnapMarker:
    def __init__(self):
        self.__visible: bool = False
        self.__position: Gf.Vec3d = Gf.Vec3d(0, 0, 0)

        self.__root: sc.Transform = sc.Transform(
            look_at=sc.Transform.LookAt.CAMERA, transform=sc.Matrix44.get_translation_matrix(1, 1, 1)
        )

        self._widget_build_fn()

    @property
    def position(self) -> Gf.Vec3d:
        return self.__position

    @position.setter
    def position(self, position: Optional[Gf.Vec3d]) -> None:
        if not position:
            self.visible = False
            return

        self.__position = position
        self.__root.transform = sc.Matrix44.get_translation_matrix(*position[:3])
        self.visible = True

    @property
    def visible(self) -> bool:
        return self.__visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self.__visible = value
        self.__root.visible = value

    def _widget_build_fn(self) -> None:
        with self.__root:
            with sc.Transform(scale_to=sc.Space.SCREEN):
                self.__icon = sc.Image(
                    get_icon_path("SnapIndicator"),
                    width=SNAP_SIZE,
                    height=SNAP_SIZE,
                    image_width=SNAP_SIZE,
                    image_height=SNAP_SIZE,
                )
            self.__transform_bg = sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(0, 0, 0), scale_to=sc.Space.SCREEN
            )
            with self.__transform_bg:
                self.__label_bg = sc.Rectangle(
                    color=0xFF000000,
                    height=SNAP_SIZE / 2 + 4,
                    width=SNAP_SIZE,
                )
            with sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(SNAP_SIZE / 2, -SNAP_SIZE / 2 - 3, 0),
                scale_to=sc.Space.SCREEN,
            ):
                self.__label = sc.Label("")

        self.visible = False

    def set_snap_marker(self, position: Optional[Gf.Vec3d], snap_type: SnapMode) -> None:
        self.__label.text = snap_type.name
        self.__label_bg.width = 12 * len(self.__label.text) + PADDING
        x_pos = SNAP_SIZE / 2 + self.__label_bg.width / 2 - PADDING
        self.__transform_bg.transform = sc.Matrix44.get_translation_matrix(x_pos, -SNAP_SIZE / 2 - 3, 0)
        self.position = position


# TODO Add gesture to background with callback, otherwise dummy gesture to block others on the screen.
class MeasureSceneLabel:
    def __init__(
        self,
        text: str,
        axis: MeasureAxis,
        tool_mode: MeasureMode,
        position: List[float] = [0, 0, 0],
        clicked_fn: Optional[Callable[[], None]] = None,
        visible: bool = False,
    ):
        self._axis: MeasureAxis = axis
        self._mode: MeasureMode = tool_mode
        self._clicked_fn: Optional[Callable[[], None]] = clicked_fn

        self._root: sc.Transform = sc.Transform(
            look_at=sc.Transform.LookAt.CAMERA, transform=sc.Matrix44.get_translation_matrix(1, 1, 1)
        )

        self._click_gesture = sc.ClickGesture(
            name="click_scene_label", on_ended_fn=self._on_click, manager=GesturePreventionManager()
        )

        self.__draw()
        self.set_position(position)
        self.visible(visible)

    def __draw(self):
        label_color = 0xFF000000
        if self._axis == MeasureAxis.X:
            label_color = 0xFF5555AA
        elif self._axis == MeasureAxis.Y:
            label_color = 0xFF76A371
        elif self._axis == MeasureAxis.Z:
            label_color = 0xFFA07D4F

        text_size = ReferenceManager().ui_display_panel.text_size.value

        with self._root:
            with sc.Transform(scale_to=sc.Space.SCREEN):
                self._label_xform = sc.Transform(transform=sc.Matrix44.get_translation_matrix(-11.25, 0, 0))
                with self._label_xform:
                    self._label = sc.Label(
                        "", size=text_size, color=[0, 0, 0, 1], alignment=ui.Alignment.LEFT_CENTER
                    )  # Aligns right
                self._rectangle = sc.Rectangle(
                    width=135, height=45, color=[1, 1, 1, 1], wireframe=False
                )  # This will have a gesture
                self._icon_xform = sc.Transform(
                    transform=sc.Matrix44.get_translation_matrix(-45, 0, 0)
                )  # Offset the colored box
                with self._icon_xform:
                    self._icon_bg = sc.Rectangle(
                        width=45, height=45, color=label_color, wireframe=False, gesture=self._click_gesture
                    )
                    if self._axis == MeasureAxis.NONE:
                        icon_path = get_icon_path(f"tool_{self._mode.name.lower()}")
                        self._icon = sc.Image(source_url=icon_path, width=45, height=45)
                    else:
                        self._icon = sc.Label(
                            self._axis.name, size=24, color=[1, 1, 1, 1], alignment=ui.Alignment.CENTER
                        )

    @property
    def text(self) -> str:
        return self._label.text

    @text.setter
    def text(self, value: str) -> None:
        self._label.text = value
        self.__update_label_visuals()

    def __update_label_visuals(self):
        # Update label size
        text_size = ReferenceManager().ui_display_panel.text_size
        self._label.size = text_size.value
        size_bias = LABEL_SCALE_MAPPING[text_size]

        # Calculate background width including label size bias
        char_len = len(self._label.text)
        rect_width = int(
            (self._icon_bg.width * 1.5 * size_bias) + (10 * char_len)
        )  # (1.5*icon_width) + 10 units per character
        self._rectangle.width = rect_width

        self._label_xform.transform = sc.Matrix44.get_translation_matrix((rect_width * -0.5) + 22.5, 0, 0)
        self._icon_xform.transform = sc.Matrix44.get_translation_matrix((rect_width * -0.5) - 22.5, 0, 0)

    def visible(self, value: bool) -> None:
        """
        Set widget visibility

        Args:
            value (bool): Visible
        """
        self._label.visible = value
        self._icon_bg.visible = value
        self._icon.visible = value
        self._rectangle.visible = value

    def set_position(self, position: Union[List[float], Gf.Vec3d]) -> None:
        """
        Set widget position

        Args:
            position (List[float], Gf.Vec3d): Position
        """
        self._root.transform = sc.Matrix44.get_translation_matrix(*position)

    def update(self, **kwargs):
        """
        Update properties of the widget

        Kwargs:
            text (str): Widget text
            position (List[float], Gf.Vec3d): Widget position
            visible (bool): Widget visibility
        """
        _text = kwargs.get("text", None)
        _position = kwargs.get("position", None)
        _visible = kwargs.get("visible", None)

        if _text and isinstance(_text, str):
            self.text = _text
        if _position and isinstance(_position, List):
            self.set_position(_position)
        if _visible and isinstance(_visible, bool):
            self.visible(_visible)

    def _on_click(self) -> None:
        if self._clicked_fn:
            self._clicked_fn()


class MeasureAxisStackLabel:
    def __init__(
        self,
        tool_mode: MeasureMode,
        position: List[float] = [0, 0, 0],
        clicked_fn: Optional[Callable[[], None]] = None,
        delete_fn: Optional[Callable] = None,
        delete_gestures=None,
        selected: bool = False,
        visible: bool = False,
    ):
        self._mode: MeasureMode = tool_mode
        self._clicked_fn: Optional[Callable[[], None]] = clicked_fn
        self._delete_fn: Optional[Callable] = delete_fn

        self._selected: bool = selected
        self._hovered: bool = False

        self._root: sc.Transform = sc.Transform(
            look_at=sc.Transform.LookAt.CAMERA, transform=sc.Matrix44.get_translation_matrix(1, 1, 1)
        )

        self._manager = PreventOthers()

        self._click_gesture = sc.ClickGesture(
            name="click_scene_label", on_ended_fn=self._on_click, manager=GesturePreventionManager()
        )

        self._delete_gestures = delete_gestures

        self.__draw()
        self.set_position(position)
        self.visible = visible

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value

    def _on_delete(self):
        if self._delete_fn is not None and self.selected:
            self._delete_fn()

    def _on_hover_start(self, _sender):
        if ReferenceManager().selection_state.enabled:
            return
        self._hovered = True
        get_main_window_cursor().override_cursor_shape(CursorStandardShape.HAND)

    def _on_hover_end(self, _sender):
        self._hovered = False
        get_main_window_cursor().clear_overridden_cursor_shape()

    def __draw_icon(self, axis: MeasureAxis, add_delete: bool = False) -> sc.Transform:
        label_color = 0x00000000
        if axis == MeasureAxis.X:
            label_color = 0xFF5555AA
        elif axis == MeasureAxis.Y:
            label_color = 0xFF76A371
        elif axis == MeasureAxis.Z:
            label_color = 0xFFA07D4F

        xform = sc.Transform(transform=sc.Matrix44.get_translation_matrix(-45, 0, 0))
        with xform:
            icon = sc.Rectangle(width=45, height=45, color=label_color, wireframe=False)

            if add_delete and self._delete_gestures is not None:
                icon.gestures = self._delete_gestures

            if axis == MeasureAxis.NONE:
                icon.gestures = [self._click_gesture]
                icon_path = (
                    get_icon_path("scene_icon_tool_delete")
                    if self.selected
                    else get_icon_path(f"scene_icon_tool_{self._mode.name.lower()}")
                )
                sc.Image(source_url=icon_path, width=45, height=45)
            else:
                sc.Label(axis.name, size=24, color=[1, 1, 1, 1], alignment=ui.Alignment.CENTER)
        return xform

    def __draw(self):
        # Get Local Transform Offset position [Defaults]
        m_pos = sc.Matrix44.get_translation_matrix(0, 67.5, 0)
        x_pos = sc.Matrix44.get_translation_matrix(0, 22.5, 0)
        y_pos = sc.Matrix44.get_translation_matrix(0, -22.5, 0)
        z_pos = sc.Matrix44.get_translation_matrix(0, -67.5, 0)
        lbl_pos = sc.Matrix44.get_translation_matrix(-11.25, 0, 0)

        text_size = ReferenceManager().ui_display_panel.text_size.value

        with self._root:
            with sc.Transform(scale_to=sc.Space.SCREEN):
                # Background
                self._background = sc.Rectangle(width=135, height=180, color=[1, 1, 1, 1], wireframe=False)
                with sc.Transform(transform=m_pos):  # vertical
                    self._m_label_xform = sc.Transform(transform=lbl_pos)  # Label horizontal
                    with self._m_label_xform:
                        self._m_label = sc.Label(
                            "", size=text_size, color=[0, 0, 0, 1], alignment=ui.Alignment.LEFT_CENTER
                        )
                    self._m_icon = self.__draw_icon(MeasureAxis.NONE, add_delete=True)
                with sc.Transform(transform=x_pos):  # vertical
                    self._x_label_xform = sc.Transform(transform=lbl_pos)  # Label horizontal
                    with self._x_label_xform:
                        self._x_label = sc.Label(
                            "", size=text_size, color=[0, 0, 0, 1], alignment=ui.Alignment.LEFT_CENTER
                        )
                    self._x_icon = self.__draw_icon(MeasureAxis.X)
                with sc.Transform(transform=y_pos):  # vertical
                    self._y_label_xform = sc.Transform(transform=lbl_pos)  # Label horizontal
                    with self._y_label_xform:
                        self._y_label = sc.Label(
                            "", size=text_size, color=[0, 0, 0, 1], alignment=ui.Alignment.LEFT_CENTER
                        )
                    self._y_icon = self.__draw_icon(MeasureAxis.Y)
                with sc.Transform(transform=z_pos):  # vertical
                    self._z_label_xform = sc.Transform(transform=lbl_pos)  # Label horizontal
                    with self._z_label_xform:
                        self._z_label = sc.Label(
                            "", size=text_size, color=[0, 0, 0, 1], alignment=ui.Alignment.LEFT_CENTER
                        )
                    self._z_icon = self.__draw_icon(MeasureAxis.Z)

    @property
    def visible(self) -> bool:
        return self._root.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._root.visible = value

    def __update_label_visuals(self):
        m_len = len(self._m_label.text)
        x_len = len(self._x_label.text)
        y_len = len(self._y_label.text)
        z_len = len(self._z_label.text)
        basis_len = max(m_len, x_len, y_len, z_len)

        # Update Label sizes
        text_size = ReferenceManager().ui_display_panel.text_size
        for label in [self._m_label, self._x_label, self._y_label, self._z_label]:
            label.size = text_size.value

        # Calculate background width including label size bias
        size_bias = LABEL_SCALE_MAPPING[text_size]
        bg_width = int((45 * 1.5 * size_bias) + (10 * basis_len))
        self._background.width = bg_width

        label_xform = sc.Matrix44.get_translation_matrix((bg_width * -0.5) + 22.5, 0, 0)
        for xform in [self._m_label_xform, self._x_label_xform, self._y_label_xform, self._z_label_xform]:
            xform.transform = label_xform

        icon_xform = sc.Matrix44.get_translation_matrix((bg_width * -0.5) - 22.5, 0, 0)
        for xform in [self._m_icon, self._x_icon, self._y_icon, self._z_icon]:
            xform.transform = icon_xform

    def set_position(self, position: Union[List[float], Gf.Vec3d]):
        """
        Set position of the widget

        Args:
            position (List[float], Gf.Vec3d): Position
        """
        self._root.transform = sc.Matrix44.get_translation_matrix(*position)

    def update_text(self, **kwargs):
        """
        Updates label text appropriately

        Kwargs:
            main (str): Main measurement label text
            x (str): X axis text
            y (str): Y axis text
            z (str): Z axis text
        """
        _main = kwargs.get("main", None)
        _x = kwargs.get("x", None)
        _y = kwargs.get("y", None)
        _z = kwargs.get("z", None)

        if isinstance(_main, str):
            self._m_label.text = _main
        if isinstance(_x, str):
            self._x_label.text = _x
        if isinstance(_y, str):
            self._y_label.text = _y
        if isinstance(_z, str):
            self._z_label.text = _z

        self.__update_label_visuals()

    def _on_click(self) -> None:
        if self._clicked_fn:
            self._clicked_fn()
