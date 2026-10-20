# Copyright (c) 2022-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import numpy as np
import omni.graph.core as og
import omni.ui as ui
from omni.graph.visualization.nodes import ViewportManager

from ..OgnDrawScreenSpaceTextDatabase import OgnDrawScreenSpaceTextDatabase


class OgnDrawScreenSpaceTextInternalState:
    def __init__(self):
        self.prev_text = None
        self.prev_text_color = None
        self.prev_background_color = None
        self.prev_size = None
        self.prev_box_width = None
        self.prev_position = None

        self.rectangle_style = {}
        self.label_style = {}
        self.placer = None  # ui.Placer()
        self.stack = None  # ui.ZStack()
        self.rectangle = None  # ui.Rectangle()
        self.label = None  # ui.Label("")


def to_color(input_color):
    """Handle nparray and list conversion to ui.color"""
    if hasattr(input_color, "tolist"):
        return ui.color(*input_color.tolist())
    return ui.color(*input_color)


class OgnDrawScreenSpaceText:
    @staticmethod
    def internal_state():
        return OgnDrawScreenSpaceTextInternalState()

    @staticmethod
    def update(db):
        try:
            inputs = db.inputs
            state = db.per_instance_state

            ViewportManager.add_layout_builder(str(db.node.get_prim_path()), OgnDrawScreenSpaceText.build_layout)

            # Early out if our registered layout builder has not yet run.
            if state.placer is None:
                return

            inputs_changed = (
                inputs.text != state.prev_text
                or not np.array_equal(inputs.textColor, state.prev_text_color)
                or not np.array_equal(inputs.backgroundColor, state.prev_background_color)
                or inputs.size != state.prev_size
                or inputs.boxWidth != state.prev_box_width
                or not np.array_equal(inputs.position, state.prev_position)
                or state.needs_update
            )

            if inputs_changed:
                state.placer.offset_x = ui.Percent(inputs.position[0])
                state.placer.offset_y = ui.Percent(inputs.position[1])

                state.stack.width = ui.Length(inputs.boxWidth)

                state.rectangle_style["background_color"] = to_color(inputs.backgroundColor)
                state.rectangle.visible = len(inputs.text) > 0
                state.rectangle.set_style(state.rectangle_style)

                state.label_style["color"] = to_color(inputs.textColor)
                state.label_style["font_size"] = inputs.size
                state.label.text = inputs.text
                state.label.set_style(state.label_style)

                state.prev_text = inputs.text
                state.prev_text_color = np.copy(inputs.textColor)
                state.prev_background_color = np.copy(inputs.backgroundColor)
                state.prev_size = inputs.size
                state.prev_box_width = inputs.boxWidth
                state.prev_position = np.copy(inputs.position)
                state.needs_update = False

        except Exception:
            import traceback

            raise RuntimeError(traceback.format_exc())

    @staticmethod
    def build_layout(node):
        db = OgnDrawScreenSpaceTextDatabase(node)
        state = db.per_instance_state

        if state.placer is None:
            state.placer = ui.Placer()
            with state.placer:
                state.stack = ui.ZStack(width=0, height=0)

                with state.stack:
                    state.rectangle_style = {"border_radius": 5, "margin_width": -10}
                    state.label_style = {"alignment": ui.Alignment.LEFT, "color": ui.color("545454FF")}
                    state.rectangle = ui.Rectangle(style=state.rectangle_style)
                    state.label = ui.Label("", style=state.label_style, word_wrap=True)

            state.needs_update = True

        OgnDrawScreenSpaceText.update(db)

    @staticmethod
    def initialize(_, node):
        ViewportManager.add_layout_builder(str(node.get_prim_path()), OgnDrawScreenSpaceText.build_layout)

    @staticmethod
    def release(node):
        ViewportManager.remove_layout_builder(str(node.get_prim_path()))

    @staticmethod
    def compute(db) -> bool:
        OgnDrawScreenSpaceText.update(db)
        db.outputs.execOut = og.ExecutionAttributeState.ENABLED
        return True
