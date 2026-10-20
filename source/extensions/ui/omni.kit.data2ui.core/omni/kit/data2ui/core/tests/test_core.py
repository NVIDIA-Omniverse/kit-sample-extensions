# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.test

from ..delegate import Delegate
from ..model import (
    Button,
    Circle,
    Container,
    Frame,
    HStack,
    Image,
    Label,
    Line,
    Model,
    Placer,
    Rectangle,
    Triangle,
    ViewportButton,
    ViewportCircle,
    VStack,
    Widget,
    ZStack,
)
from ..omniuidelegate import OmniUiDelegate
from ..view import DDView

CURRENT_PATH = Path(__file__).parent.joinpath("data").absolute().resolve()


class TestData2UICore(omni.kit.test.AsyncTestCase):
    async def test_delegate(self):

        # Simply by importing the module, we've covered 50% since it is a base class and the syntax is simple.
        delegate = Delegate()

        # We start with the already defined widget types
        self.assertGreater(len(delegate.widget_types_by_item_type), 0)

        import omni.ui as ui

        TestUIWidget = ui.Widget

        # We invent a new widget and ensure it gets to the mapping
        class TestWidget(Widget):
            some_property = True

        delegate.TestWidget = delegate.register_type(ui.Widget, TestWidget)

        # We make sure we can get it out
        self.assertEqual(TestUIWidget, delegate.widget_types_by_item_type.get(TestWidget))

    async def test_omniuidelegate(self):

        delegate = OmniUiDelegate()

        # We start with the already defined widget types
        self.assertGreater(len(delegate.widget_types_by_item_type), 0)

        import omni.ui as ui

        TestUIWidget = ui.Widget

        # We invent a new widget and ensure it gets to the mapping
        class TestWidget(Widget):
            some_property = True

        delegate.TestWidget = delegate.register_type(ui.Widget, TestWidget)

        # We make sure we can get it out
        self.assertEqual(TestUIWidget, delegate.widget_types_by_item_type.get(TestWidget))

    async def test_model(self):

        model = Model()

        # We invent a new widget to register it with the model.
        class TestWidget(Widget):
            some_property = True

        item_data = {"widget_data": "some item data"}

        TestWidget.__type_subscription = model.register_type(TestWidget, item_data)

        # Ensure bidirectional lookups
        self.assertEqual(model.get_item_data(TestWidget), item_data)
        self.assertEqual(model.get_type_from_data(item_data), TestWidget)

    async def test_view(self):
        class MockFrame(Frame):
            def __init__(self):
                super().__init__()
                self._children = []

            @property
            def children(self):
                return self._children

        delegate = OmniUiDelegate()
        model = Model()
        frame = MockFrame()
        for widget_type in [
            VStack,
            HStack,
            ZStack,
            Placer,
            Label,
            Button,
            Image,
            Rectangle,
            Circle,
            Triangle,
            Line,
            ViewportButton,
            ViewportCircle,
        ]:

            if issubclass(widget_type, Container):

                class ConcreteContainer(widget_type):
                    def __init__(self):
                        return super().__init__()

                    @property
                    def children(self):
                        return []

                item = ConcreteContainer()
            else:
                item = widget_type()

            item.style = {"color": "#123456"}
            frame._children.append(item)

        model.root = frame
        view = DDView(delegate=delegate, model=model)
        view.rebuild_all()
