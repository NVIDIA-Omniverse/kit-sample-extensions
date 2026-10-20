## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import json
from pathlib import Path

import carb
import omni.kit
import omni.kit.ui_test as ui_test
import omni.ui as ui
from carb.input import KeyboardEventType, KeyboardInput, MouseEventType
from omni.kit.graph.editor.example.graph_widget import GraphWidget
from omni.kit.ui_test.input import (
    emulate_keyboard,
    emulate_mouse,
    emulate_mouse_drag_and_drop,
    emulate_mouse_slow_move,
    human_delay,
)
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.graph.editor.example}"))
FILE_PATH = CURRENT_PATH.absolute().resolve().joinpath("graphs/example.json")
FILE_PATH2 = CURRENT_PATH.absolute().resolve().joinpath("graphs/example2.json")

json_snippet = """"inputs": ["MyGraph:Math12:out1"]}}, {"output:out1": {"type": "float", "state": "CLOSED"}}, {"output:out2": {"type": "int", "state": "CLOSED"}}]}}, {"Math1234": {"type": "Math", "ui_name": "HD RESOLUTION", "state": "OPEN", "position": "(-66.76306915283203, 770.9641723632812)","""


class TestModel(OmniUiTest):
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
        """test the general widget"""
        await self.create_test_area(width=1950, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=1950, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        graph_widget.open_graph()

        human_delay_speed = 10

        await human_delay(human_delay_speed)
        # Cancel Open dialog
        await ui_test.emulate_keyboard_press(KeyboardInput.ESCAPE)
        await human_delay(human_delay_speed)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        graph_widget.save_graph()
        await human_delay(human_delay_speed)
        self.assertIsNotNone(graph_widget._GraphWidget__save_file_dialog)
        # Cancel Save dialog
        await ui_test.emulate_keyboard_press(KeyboardInput.ESCAPE)

        await human_delay(30)

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_neo_delegate(self):
        """test changing to the neo delegate"""
        window_width = 1950
        await self.create_test_area(width=window_width, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=window_width, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        human_delay_speed = 10
        # Click on Delegate dropdown
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(window_width - 100, 90), human_delay_speed=2)
        await human_delay(human_delay_speed)
        # Click on Neo Delegate
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(window_width - 80, 120), human_delay_speed=2)

        await human_delay(10)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, threshold=0.03)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_default_delegate(self):
        """test changing to the default delegate"""
        window_width = 1950
        await self.create_test_area(width=window_width, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=window_width, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        human_delay_speed = 10
        # Click on Delegate dropdown
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(window_width - 100, 90), human_delay_speed=2)
        await human_delay(human_delay_speed)
        # Click on Default delegate
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(window_width - 80, 140), human_delay_speed=2)

        await human_delay(10)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, threshold=0.03)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_deletion(self):
        """test the compound deletion"""
        await self.create_test_area(width=1950, height=1050)
        graph_window = ui.Window("DeletionTest", width=1950, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        root_item = graph_widget._graph_root
        nodes = root_item.children()
        compound_nodes = [n for n in nodes if n.type == "Compound"]

        compound_node_names = [n.name for n in compound_nodes]

        self.assertEqual(set(compound_node_names), {"One Compound", "Other Compound"})

        # goes into the Compound node
        graph_widget.set_current_compound(compound_nodes[0])
        self.assertEqual(graph_widget._graph_model.current_graph, compound_nodes[0])

        # goes back to the graph root again
        graph_widget.set_current_compound(root_item)
        self.assertEqual(graph_widget._graph_model.current_graph, root_item)

        graph_widget._graph_model.selection = compound_nodes
        graph_widget._graph_model.delete_selection()

        # check the children again and verify the compound nodes have been removed
        nodes = root_item.children()
        compound_nodes = [n for n in nodes if n.type == "Compound"]
        self.assertEqual(len(compound_nodes), 0)

        await human_delay(30)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, threshold=100)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_focus_hotkey(self):
        """test the focus 'f' hotkey with nodes selected"""
        window_width = 1950
        await self.create_test_area(width=window_width, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=window_width, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        human_delay_speed = 10
        # Move mouse to a node to select it
        await ui_test.emulate_mouse_move(ui_test.Vec2(900, 390), human_delay_speed=2)
        await human_delay(human_delay_speed)
        await ui_test.emulate_mouse_click()
        await human_delay(human_delay_speed)
        # Press "F" to focus node
        await ui_test.emulate_keyboard_press(KeyboardInput.F)

        await human_delay(20)

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_focus_context_menu(self):
        """test the focus menu item with nodes selected"""
        window_width = 1950
        await self.create_test_area(width=window_width, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=window_width, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        human_delay_speed = 5
        # Move mouse to a node to select it
        await ui_test.emulate_mouse_move(ui_test.Vec2(900, 390), human_delay_speed=2)
        await human_delay(human_delay_speed)
        await ui_test.emulate_mouse_click()
        await human_delay(human_delay_speed)
        # Rt-click to bring up context menu
        await ui_test.emulate_mouse_click(right_click=True)
        await human_delay(human_delay_speed)
        # Click on "Focus on Selection"
        await ui_test.select_context_menu("Focus on Selection")

        await human_delay(20)

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_descendant_getter(self):
        """test dragging descendants together"""
        window_width = 1950
        await self.create_test_area(width=window_width, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=window_width, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        human_delay_speed = 20  # Needs to be long or Mouse Down acts like a double-click in some cases
        # Move mouse to a node to select it
        await ui_test.emulate_mouse_move(ui_test.Vec2(1260, 200), human_delay_speed=10)
        await human_delay(human_delay_speed)
        await ui_test.emulate_mouse_click()
        await human_delay(human_delay_speed)

        await emulate_keyboard(KeyboardEventType.KEY_PRESS, KeyboardInput.D)
        await human_delay(human_delay_speed)
        start_pos = ui_test.Vec2(1260, 200)
        end_pos = ui_test.Vec2(1310, 220)
        # breaking down emulate_mouse_drag_and_drop call
        await emulate_mouse(MouseEventType.MOVE, start_pos)
        await human_delay(human_delay_speed)
        await emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await human_delay(human_delay_speed)
        await emulate_mouse_slow_move(start_pos, end_pos, human_delay_speed=human_delay_speed)
        await human_delay(human_delay_speed)
        await emulate_mouse(MouseEventType.LEFT_BUTTON_UP)

        await human_delay(human_delay_speed)
        await emulate_keyboard(KeyboardEventType.KEY_RELEASE, KeyboardInput.D)

        await human_delay(20)

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_write_graph(self):
        """test dragging descendants together"""
        window_width = 1950
        await self.create_test_area(width=window_width, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=window_width, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH2)

        await human_delay(30)

        # Mimic the write_graph method, without actually writing out to disk
        simple_model = graph_widget._graph_model
        data = {}
        graph_data = {}
        data[simple_model._graph_root.name] = graph_data
        graph_data["type"] = "Graph"
        graph_data["nodes"] = []

        for child in simple_model._graph_root._children:
            graph_data["nodes"].append(simple_model.write_node(child))

        data_str = json.dumps(data)
        self.assertTrue(json_snippet in data_str)

        await self.finalize_test_no_image()

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_create_nodes(self):
        """test creating lots of different types of nodes"""
        window_width = 1950
        await self.create_test_area(width=window_width, height=1050, block_devices=False)
        graph_window = ui.Window("DelegateTest", width=window_width, height=1050)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphWidget()
        # wait a few frames for the GraphView to initialize the model
        await human_delay(5)

        # Then just read the graph in
        graph_widget.read_graph(FILE_PATH)

        await human_delay(30)

        human_delay_speed = 5
        # Open up left node catalogs
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 160), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a Note node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 220), ui_test.Vec2(1460, 340), human_delay_speed=5)
        await human_delay(human_delay_speed)

        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get an Animation Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 140), ui_test.Vec2(1250, 630), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a Debug Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 180), ui_test.Vec2(1475, 630), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get an Event Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 240), ui_test.Vec2(1720, 630), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a Geometry Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 330), ui_test.Vec2(1220, 800), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a IO Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 380), ui_test.Vec2(1475, 800), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a Math Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 480), ui_test.Vec2(1720, 800), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a Rendering Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 530), ui_test.Vec2(1250, 950), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a Time Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 660), ui_test.Vec2(1475, 950), human_delay_speed=5)
        await human_delay(human_delay_speed)
        # Get a Ui Node
        await emulate_mouse_drag_and_drop(ui_test.Vec2(100, 720), ui_test.Vec2(1720, 950), human_delay_speed=5)

        await human_delay(20)

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        if graph_widget:
            graph_widget.destroy()
        graph_widget = None
        graph_window = None
