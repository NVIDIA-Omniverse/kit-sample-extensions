# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from functools import lru_cache
from typing import Any, DefaultDict, Dict, List, Sequence, Set, Tuple

import carb
import omni.ui as ui
import omni.usd
import Semantics
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.property.usd import ADDITIONAL_CHANGED_PATH_GLOBAL_EVENT
from omni.kit.property.usd.usd_property_widget import UsdPropertiesWidget
from omni.kit.widget.settings import get_style
from omni.kit.window.property.templates import HORIZONTAL_SPACING, LABEL_HEIGHT, LABEL_WIDTH, LABEL_WIDTH_LIGHT
from pxr import Sdf, Tf, Trace, Usd, UsdGeom, UsdSemantics

from .semantics_entry import PrimSemantics

EMPTY_SEMANTICS_LABEL_STYLE = {"font_size": 18}
P0_LABEL_STYLE = {"font_size": 14, "color": 0xFF9A9A9A}


def property_log(level, message):
    if level == "info":
        carb.log_info(f"[semantics.schema.property] {message}")
    if level == "warn":
        carb.log_warn(f"[semantics.schema.property] {message}")
    if level == "error":
        carb.log_error(f"[semantics.schema.property] {message}")


class SemanticsPropertyWidget(UsdPropertiesWidget):
    def __init__(self, title: str, collapsed: bool):
        super().__init__(title="Semantics", collapsed=False)
        self._listener = None
        self._semantic_items = []
        self._semantics_present = 0

    def on_new_payload(self, payload):
        if not super().on_new_payload(payload):
            return False

        stage = self._payload.get_stage()
        if not stage or not len(self._payload):
            return False

        self._semantic_items = []
        for path in self._payload:
            prim = stage.GetPrimAtPath(path)
            if prim.IsValid():
                self._semantic_items.append(PrimSemantics(prim))

        check = [item.has_semantics for item in self._semantic_items]
        self._semantics_present = sum(check)

        return True

    def clean(self):
        """
        See PropertyWidget.clean
        """
        self._current_items = []
        super().clean()

    def build_items(self):
        self.reset()

        if len(self._payload) == 0:
            return

        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, stage)
        self._bus_sub = get_eventdispatcher().observe_event(
            event_name=ADDITIONAL_CHANGED_PATH_GLOBAL_EVENT, on_event=self._on_bus_event
        )

        # for prim_path in self._payload:
        if self._payload is not None:
            if self._semantics_present > 0:
                with ui.HStack(spacing=HORIZONTAL_SPACING, width=ui.Percent(100)):
                    ui.Label("Semantic Name", width=LABEL_WIDTH)
                    ui.Spacer(width=HORIZONTAL_SPACING)
                    ui.Label("Semantic Labels")
                for item in self._semantic_items:
                    if len(self._payload) > 1:
                        with ui.HStack():
                            ui.Label(item.prim_path, identifier="lbl_semantic_prim_path", style=P0_LABEL_STYLE, width=0)
                            ui.Spacer(width=HORIZONTAL_SPACING)
                            ui.Line(style={"color": 0x338A8777}, width=ui.Fraction(1))
                    if item.has_semantics:
                        item.draw_ui()
                    else:
                        ui.Label(
                            "This prim has no semantics",
                            style=EMPTY_SEMANTICS_LABEL_STYLE,
                            alignment=ui.Alignment.CENTER,
                        )
            else:
                with ui.VStack(spacing=8):
                    if len(self._payload) == 1:
                        ui.Label(
                            "This prim has no semantics",
                            style=EMPTY_SEMANTICS_LABEL_STYLE,
                            alignment=ui.Alignment.CENTER,
                        )
                    else:
                        ui.Label(
                            "None of the selected prims have semantics",
                            style=EMPTY_SEMANTICS_LABEL_STYLE,
                            alignment=ui.Alignment.CENTER,
                        )

    @Trace.TraceFunction
    def _on_usd_changed(self, notice, stage):
        if stage != self._payload.get_stage():
            return

        for path in notice.GetChangedInfoOnlyPaths():
            # if anyone changes the xformOpOrder of the current prim rebuild the collapsable frame
            if str(path).split(".")[-1] == "xformOpOrder" and path.GetPrimPath() in self._payload:
                super().request_rebuild()
                return

        super()._on_usd_changed(notice, stage)

    def _build_frame_header(self, collapsed, text: str, id: str = None):
        """Custom header for CollapsableFrame"""
        if id is None:
            id = text

        if collapsed:
            alignment = ui.Alignment.RIGHT_CENTER
            width = 5
            height = 7
        else:
            alignment = ui.Alignment.CENTER_BOTTOM
            width = 7
            height = 5

        header_stack = ui.HStack(spacing=8)
        with header_stack:
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Triangle(
                    style_type_name_override="CollapsableFrame.Header", width=width, height=height, alignment=alignment
                )
                ui.Spacer()
            ui.Label(text, style_type_name_override="CollapsableFrame.Header", width=ui.Fraction(1))

            button_style = {
                "Button.Image": {
                    "color": 0xFFFFFFFF,
                    "alignment": ui.Alignment.CENTER,
                },
            }

            defaultStyle = get_style()
            label_style = defaultStyle.get("CollapsableFrame.Header", {})
            label_style.update({"color": 0xFFFFC734})

        def show_attribute_context_menu(b):
            if b != 1:
                return

            event = GroupHeaderContextMenuEvent(group_id=id, payload=[])
            GroupHeaderContextMenu.on_mouse_event(event)

        header_stack.set_mouse_pressed_fn(lambda x, y, b, _: show_attribute_context_menu(b))
