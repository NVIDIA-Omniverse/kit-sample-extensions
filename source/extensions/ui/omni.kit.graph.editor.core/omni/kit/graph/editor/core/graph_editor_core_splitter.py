# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from functools import partial
from typing import Callable

import omni.ui as ui


class GraphEditorCoreSplitter:
    def __init__(self, build_left_fn: Callable[[], None], build_right_fn: Callable[[], None]):
        self._frame = ui.Frame()
        self._frame.set_build_fn(self.on_build)
        self.__build_left_fn = build_left_fn
        self.__build_right_fn = build_right_fn
        self._button = None

    def destroy(self):
        self.__build_right_fn = None
        self.__build_left_fn = None
        self._frame = None
        self._button = None

    def on_build(self):
        def toggle_panel(panel: ui.Container, placer: ui.Placer, button: ui.Button, highlight: ui.Rectangle):
            if panel.visible:
                panel.visible = False
                highlight.visible = False
                placer.offset_x = 0.0
                placer.draggable = False
                button.text = ">"
            else:
                panel.visible = True
                highlight.visible = True
                placer.offset_x = 250.0
                placer.draggable = True
                button.text = "<"

        with ui.HStack():
            with ui.ZStack(width=0):
                # Draggable splitter
                placer = ui.Placer(drag_axis=ui.Axis.X)
                with placer:
                    with ui.ZStack(width=10):
                        splitter_highlight = ui.Rectangle(name="Splitter")
                        with ui.VStack():
                            ui.Spacer()
                            self._button = ui.Button(
                                ">", height=50, style={"Button": {"margin": 0}, "Button.Label": {"font_size": 10}}
                            )
                            ui.Spacer()

                # Left pannel
                panel = ui.Frame(visible=False)
                with panel:
                    self.__build_left_fn()

            # Right pannel
            with ui.Frame():
                self.__build_right_fn()

        self._button.set_clicked_fn(partial(toggle_panel, panel, placer, self._button, splitter_highlight))
        # Turn it on
        toggle_panel(panel, placer, self._button, splitter_highlight)
