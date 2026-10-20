## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from pathlib import Path

import carb
import omni.ui as ui
from omni.kit import ui_test
from omni.kit.graph.editor.example.graph_widget import GraphWidget
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.graph.delegate.modern}"))
FILE_PATH = CURRENT_PATH.absolute().resolve().joinpath("omni/kit/graph/delegate/modern/tests/example.json")
PAUSE = 5


class TestBackdropDelegate(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = CURRENT_PATH.absolute().resolve().joinpath("data/tests")

        # OMPE-57951: Need to hide main menu bar so golden images will not include it
        try:
            from omni.kit.mainwindow import get_main_window

            main_window = get_main_window()
            menu_bar = main_window.get_main_menu_bar()
            menu_bar.visible = False
        except:
            pass

    # After running each test
    async def tearDown(self):
        self._golden_img_dir = None
        await super().tearDown()

    async def test_backdrop_description(self):
        """test the update the backdrop description"""
        await self.create_test_area(width=1950, height=1050, block_devices=False)
        graph_window = ui.Window("BackdropTest", width=1950, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await ui_test.wait_n_updates(PAUSE)

        graph_widget.read_graph(FILE_PATH)

        # wait a few frames for the window to be fully loaded
        await ui_test.wait_n_updates(PAUSE)

        # focus on the backdrop description and start editing
        await ui_test.emulate_mouse_move(ui_test.Vec2(600, 170))
        await ui_test.emulate_mouse_click(double=True)
        await ui_test.wait_n_updates(PAUSE)

        # editing the backdrop description
        await ui_test.emulate_char_press("hello I am a backdrop")
        await ui_test.wait_n_updates(PAUSE)

        # move out from the field to end the editing
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(800, 600))
        await ui_test.wait_n_updates(PAUSE)

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None
