# Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["TestSliderManipulator"]

from pathlib import Path

import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.usd
from omni.sample.ui_scene.slider_manipulator.slider_manipulator import SliderManipulator
from omni.ui import scene as sc
from omni.ui.tests.test_base import OmniUiTest

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")


class SliderTestModelItem(sc.AbstractManipulatorItem):
    class PositionItem(sc.AbstractManipulatorItem):
        def __init__(self):
            super().__init__()
            self.value = [0, 0, 0]

    class ValueItem(sc.AbstractManipulatorItem):
        def __init__(self, value=0):
            super().__init__()
            self.value = [value]


class SliderTestModel(sc.AbstractManipulatorModel):
    def __init__(self):
        super().__init__()

        self.scale = SliderTestModelItem.ValueItem()
        self.min = SliderTestModelItem.ValueItem()
        self.max = SliderTestModelItem.ValueItem(1)
        self.position = SliderTestModelItem.PositionItem()

    def get_item(self, identifier):
        if identifier == "value":
            return self.scale
        if identifier == "position":
            return self.position
        if identifier == "min":
            return self.min
        if identifier == "max":
            return self.max

    def get_as_floats(self, item):
        if item == self.position:
            # Requesting position
            return [0, 0, 0]
        if item:
            # Get the value directly from the item
            return item.value
        return []


class TestSliderManipulator(OmniUiTest):
    async def test_general(self):
        """Testing general look of the item"""
        window = await self.create_test_window(width=400, height=400)

        with window.frame:
            # Camera matrices
            projection = [1e-2, 0, 0, 0]
            projection += [0, 1e-2, 0, 0]
            projection += [0, 0, -2e-7, 0]
            projection += [0, 0, 1, 1]
            view = sc.Matrix44.get_translation_matrix(0, 0, 0)

            scene_view = sc.SceneView(sc.CameraModel(projection, view))
            with scene_view.scene:
                # The manipulator
                model = SliderTestModel()
                SliderManipulator(model=model)

        await omni.kit.app.get_app().next_update_async()
        model._item_changed(None)

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(threshold=10, golden_img_dir=TEST_DATA_PATH, golden_img_name="general.png")

    async def test_selection(self):
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        test_file_path = TEST_DATA_PATH.joinpath("selection_test.usd")
        await usd_context.open_stage_async(str(test_file_path))
        stage = usd_context.get_stage()
        self.assertIsNotNone(stage)

        await ui_test.human_delay(5)
        usd_context.get_selection().set_selected_prim_paths(["/World/Cube"])
        await ui_test.human_delay(5)
        usd_context.get_selection().set_selected_prim_paths(["/World/Cone"])
        await ui_test.human_delay(5)
        usd_context.get_selection().clear_selected_prim_paths()
        await ui_test.human_delay(5)
        await usd_context.close_stage_async()
