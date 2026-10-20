# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import carb.tokens
import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.kit.undo
import omni.ui
import omni.usd
from omni.ui.tests.test_base import OmniUiTest

from ..extension import _extension_instance
from ..prims.prim_style_properties import prims_add_style_property

CURRENT_PATH = Path(__file__).parent.joinpath("data").absolute().resolve()


async def _wait_for_viewport_frames():
    """Waits until the viewport has rendered real frames. On Kit 111 the viewport can present a transitional
    (light grey) frame after a new stage, and a fixed number of app updates sometimes captured it."""
    from omni.kit.viewport.utility import get_active_viewport

    viewport = get_active_viewport()
    if viewport:
        await viewport.wait_for_rendered_frames(10)


class TestData2UIUsdViews(OmniUiTest):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore
        self.__golden_image_dir = Path(
            carb.tokens.get_tokens_interface().resolve("${omni.kit.data2ui.usd}/data/tests/images")
        )
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore
        prims = [
            ("Frame", "/World/UI/Frame"),
            ("VStack", "/World/UI/Frame/VStack"),
            ("Label", "/World/UI/Frame/VStack/Label"),
            ("HStack", "/World/UI/Frame/VStack/HStack"),
            ("Button", "/World/UI/Frame/VStack/Button"),
            ("Button", "/World/UI/Frame/VStack/Button_01"),
            ("Button", "/World/UI/Frame/VStack/Button_02"),
            ("Spacer", "/World/UI/Frame/VStack/Spacer"),
            ("HStack", "/World/UI/Frame/VStack/HStack_01"),
            ("Rectangle", "/World/UI/Frame/VStack/HStack_01/Rectangle"),
            ("Spacer", "/World/UI/Frame/VStack/HStack_01/Spacer"),
            ("Rectangle", "/World/UI/Frame/VStack/HStack_01/Rectangle_01"),
            ("Spacer", "/World/UI/Frame/VStack/HStack_01/Spacer_01"),
            ("Rectangle", "/World/UI/Frame/VStack/HStack_01/Rectangle_02"),
            ("Spacer", "/World/UI/Frame/VStack/Spacer"),
            ("HStack", "/World/UI/Frame/VStack/HStack_02"),
            ("Circle", "/World/UI/Frame/VStack/HStack_02/Circle"),
            ("Line", "/World/UI/Frame/VStack/Line"),
            ("StyleContainer", "/World/Styles/StyleContainer"),
            ("Style", "/World/Styles/StyleContainer/Style"),
        ]
        for prim_type, prim_path in prims:
            omni.kit.commands.execute("CreateUIPrimCommand", prim_type=prim_type, prim_path=prim_path)
        style_container_prim = stage.GetPrimAtPath("/World/Styles/StyleContainer")
        style_prim = stage.GetPrimAtPath("/World/Styles/StyleContainer/Style")
        style_prim.GetAttribute("omni:ui:StyleSelector:type_name").Set("Circle")
        style_prim.GetAttribute("omni:ui:StyleSelector:name").Set("Circle")
        style_prim.GetAttribute("omni:ui:StyleSelector:state").Set("hovered")
        prims_add_style_property(stage, [style_prim], "color")

        for prim_type, prim_path in prims:
            prim = stage.GetPrimAtPath(prim_path)
            if prim_type in ["StyleContainer", "Style", "Frame"]:
                continue
            elif prim_type == "Button":
                fn = prim.GetAttribute("omni:ui:Button:clicked_fn")
                if prim_path.endswith("Button"):
                    fn.Set("Action('omni.kit.data2ui.usd', 'create_ui_prim_button')")
                elif prim_path.endswith("Button_01"):
                    fn.Set("Command('CreateUIPrimCommand', prim_type='Frame')")
                else:
                    fn.Set('Event("omni.graph.action.silly_event")')

                prims_add_style_property(stage, [prim_path], "custom")
                prims_add_style_property(stage, [prim_path], "color")
                prims_add_style_property(stage, [prim_path], "border_radius")
                prims_add_style_property(stage, [prim_path], "image_url")
                custom = prim.GetAttribute("omni:ui:Style:custom")
                custom.Set('{"background_color": "#123456"}')
                color = prim.GetAttribute("omni:ui:Style:color")
                color.Set((0.5, 0.5, 0.5, 1.0))
                radius = prim.GetAttribute("omni:ui:Style:border_radius")
                radius.Set(4.5)
                url = prim.GetAttribute("omni:ui:Style:image_url")

            else:
                binding = prim.GetRelationship("omni:ui:Style:binding")
                binding.SetTargets([style_container_prim.GetPath()])

        omni.ui.Workspace.show_window("Property", False)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()  # type: ignore
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def test_window(self):
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore
        frame_prim = stage.GetPrimAtPath("/World/UI/Frame")

        _extension_instance._execute_view(frame_prim, "window")  # type: ignore
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()  # type: ignore

        await _wait_for_viewport_frames()
        await self.finalize_test(golden_img_dir=self.__golden_image_dir, golden_img_name="test_window.png")
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        if getattr(_extension_instance, "_window", None):
            _extension_instance._window.destroy()

    async def test_viewport(self):
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore
        frame_prim = stage.GetPrimAtPath("/World/UI/Frame")

        # Not sure why this isn't set yet, but the test environment gets weird at times.
        _extension_instance._viewport_view = None
        _extension_instance._execute_view(frame_prim, "viewport")  # type: ignore
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
        await _wait_for_viewport_frames()
        await self.finalize_test(golden_img_dir=self.__golden_image_dir, golden_img_name="test_viewport.png")
        _extension_instance._execute_view(frame_prim, "remove viewport")  # type: ignore
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
        await _wait_for_viewport_frames()
        await self.finalize_test(golden_img_dir=self.__golden_image_dir, golden_img_name="test_remove_viewport.png")

    async def test_frame(self):
        context = omni.usd.get_context()
        stage = context.get_stage()  # type: ignore
        frame_prim = stage.GetPrimAtPath("/World/UI/Frame")

        _extension_instance._execute_view(frame_prim, "frame")  # type: ignore
        for i in range(10):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
