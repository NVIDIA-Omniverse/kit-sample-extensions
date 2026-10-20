## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import asyncio
from pathlib import Path

import carb
import omni.kit
import omni.ui as ui
from omni.kit import ui_test
from omni.kit.graph.editor.example.graph_widget import GraphWidget
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.graph.delegate.modern}"))
FILE_PATH = CURRENT_PATH.absolute().resolve().joinpath("omni/kit/graph/delegate/modern/tests/example.json")


class TestModernDelegate(OmniUiTest):
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

    async def test_general(self):
        """test the general core widget"""
        await self.create_test_area(width=1950, height=1050)
        graph_window = ui.Window("DelegateTest", width=1950, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        graph_widget.read_graph(FILE_PATH)

        # wait a few frames for the window to be fully loaded
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_compound(self):
        """test the general core widget"""
        await self.create_test_area(width=1950, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=1950, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget(delegate_type=2)

        # wait a few frames for the GraphView to initialize the model
        await ui_test.human_delay(10)

        graph_widget.read_graph(FILE_PATH)

        human_delay = 20  # Longer wait time helps with flakiness
        # wait a few frames for the graph to be fully loaded
        await ui_test.human_delay(human_delay)

        # Move to a compound node
        await ui_test.emulate_mouse_move(ui_test.Vec2(600, 820), human_delay_speed=3)
        await ui_test.human_delay(human_delay)
        # dive into the compound node
        await ui_test.emulate_mouse_click(double=True)

        # wait a few frames for the sun gragh to be fully loaded
        await ui_test.human_delay(human_delay)

        # enable context menu for the compound port
        await ui_test.emulate_mouse_move(ui_test.Vec2(440, 520), human_delay_speed=3)
        await ui_test.human_delay(human_delay)
        await ui_test.emulate_mouse_click(right_click=True)

        await ui_test.human_delay(human_delay)

        # choose remove port
        await ui_test.emulate_mouse_move(ui_test.Vec2(475, 530), human_delay_speed=3)
        await ui_test.human_delay(human_delay)
        await ui_test.emulate_mouse_click()

        await ui_test.human_delay(human_delay)

        # check connection tooltip
        await ui_test.emulate_mouse_move(ui_test.Vec2(920, 590), human_delay_speed=3)
        # wait for tooltip to be shown
        await asyncio.sleep(3)

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None
