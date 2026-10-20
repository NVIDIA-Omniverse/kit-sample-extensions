import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.kit.undo
import omni.usd
from omni.kit import ui_test
from omni.ui.tests.test_base import OmniUiTest

from ..extension import _extension_instance
from ..prims.prim_style_properties import prims_add_style_property


class TestExtension(OmniUiTest):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore

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
            ("Image", "/World/UI/Frame/VStack/Image"),
            ("StyleContainer", "/World/Styles/StyleContainer"),
            ("Style", "/World/Styles/StyleContainer/Style"),
        ]
        for prim_type, prim_path in prims:
            omni.kit.commands.execute("CreateUIPrimCommand", prim_type=prim_type, prim_path=prim_path)
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        success, _ = omni.kit.commands.execute("ParentToViewportCommand", prim_path="/World/UI/Frame")
        await omni.kit.app.get_app().next_update_async()  # type: ignore

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
            elif prim_type == "Image":
                prim.GetAttribute("omni:ui:Image:source_url").Set("")

            else:
                binding = prim.GetRelationship("omni:ui:Style:binding")
                binding.SetTargets([style_container_prim.GetPath()])
        prims_add_style_property(stage, ["/World/UI/Frame"], "debug_color")

        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()  # type: ignore

    async def test_move_ui_prims(self):
        move_dict = {"/World/UI/Frame/VStack/HStack_01": "/World/UI/Frame/VStack/HStack/HStack_01"}
        omni.kit.commands.execute("MovePrims", paths_to_move=move_dict, destructive=False)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def test_delete_ui_prims(self):
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        omni.kit.commands.execute("DeletePrims", paths=["/World/UI/Frame/VStack"])
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def test_delete_ui_property(self):
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success, _ = omni.kit.commands.execute(
            "RemovePropertyCommand", prop_path="/World/UI/Frame/VStack/Button_01.omni:ui:Button:clicked_fn"
        )
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def test_delete_ui_style_property(self):
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success, _ = omni.kit.commands.execute(
            "RemovePropertyCommand", prop_path="/World/Styles/StyleContainer/Style.omni:ui:Style:color"
        )
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        success, _ = omni.kit.commands.execute(
            "RemovePropertyCommand", prop_path="/World/UI/Frame.omni:ui:Style:debug_color"
        )
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
        await omni.kit.app.get_app().next_update_async()  # type: ignore

    async def test_change_ui_style_property(self):
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        success, _ = omni.kit.commands.execute(
            "ChangePropertyCommand",
            prop_path="/World/UI/Frame.omni:ui:Style:debug_color",
            value=(1.0, 0.0, 1.0, 1.0),
            prev=(1.0, 1.0, 1.0, 1.0),
        )
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
        await omni.kit.app.get_app().next_update_async()  # type: ignore

        success, _ = omni.kit.commands.execute(
            "ChangePropertyCommand",
            prop_path="/World/Styles/StyleContainer/Style.omni:ui:Style:color",
            value=(1.0, 0.0, 1.0, 1.0),
            prev=(1.0, 1.0, 1.0, 1.0),
        )
        self.assertTrue(success)
        await omni.kit.app.get_app().next_update_async()  # type: ignore
        self.assertTrue(omni.kit.undo.undo())
        await omni.kit.app.get_app().next_update_async()  # type: ignore
