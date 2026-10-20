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
import omni.kit
import omni.ui as ui
from omni.kit.graph.delegate.default.delegate import GraphNodeDelegate
from omni.kit.widget.graph.graph_model import GraphModel
from omni.kit.widget.graph.graph_view import GraphView
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.graph.delegate.default}"))
FILE_PATH = CURRENT_PATH.absolute().resolve().joinpath("omni/kit/graph/delegate/default/tests/example.json")

inputs = [
    "First.color1",
    "First.color1.tex",
    "First.color1.shader",
    "First.color2",
    "Third.size",
    "Fourth.color1",
    "Fourth.color1.tex",
    "Fourth.color1.shader",
]
outputs = ["First.result", "Second.out", "Third.outcome", "Third.outcome.out1", "Third.outcome.out2"]
connections = {"First.color1": ["Second.out"], "First.color2": ["Third.outcome"], "Fourth.color1": ["Third.outcome"]}


class Model(GraphModel):
    def __init__(self):
        super().__init__()

    @property
    def nodes(self, item=None):
        if item:
            return

        return sorted(set([n.split(".")[0] for n in inputs + outputs]))

    @property
    def name(self, item=None):
        return item.split(".")[-1]

    @property
    def ports(self, item=None):
        item_len = len(item.split("."))
        if item_len == 1 or item_len == 2:
            result = [n for n in inputs + outputs if n.startswith(item) and len(n.split(".")) == item_len + 1]
            return result
        return []

    @property
    def expansion_state(self, item=None):
        """the expansion state of a node or a port"""
        item_len = len(item.split("."))
        if item_len == 2:
            return GraphModel.ExpansionState.CLOSED
        return GraphModel.ExpansionState.OPEN

    @property
    def inputs(self, item):
        if item in inputs:
            return connections.get(item, [])
        return None

    @property
    def outputs(self, item):
        if item in outputs:
            return []
        return None


class TestDelegate(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = CURRENT_PATH.absolute().resolve().joinpath("data/tests")

    # After running each test
    async def tearDown(self):
        self._golden_img_dir = None
        await super().tearDown()

    async def test_general(self):
        """Testing general properties of GraphView"""
        window = await self.create_test_window(800, 400)

        delegate = GraphNodeDelegate()
        default_style = delegate.get_style()

        with window.frame:
            model = Model()
            graph_view = GraphView(model=Model(), delegate=delegate, style=default_style, pan_x=600, pan_y=100)

        # Two frames because the first frame is to draw, the second frame is to auto-layout.
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

    async def test_zoom(self):
        """Testing zoom properties of GraphView"""
        window = await self.create_test_window(800, 400)

        delegate = GraphNodeDelegate()
        default_style = delegate.get_style()

        with window.frame:
            # the zoom of 0.5 will be capped by zoom_min of 0.6
            graph_view = GraphView(
                model=Model(), delegate=delegate, style=default_style, pan_x=600, pan_y=100, zoom=0.5, zoom_min=0.6
            )

        # Two frames because the first frame is to draw, the second frame is to auto-layout.
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)
