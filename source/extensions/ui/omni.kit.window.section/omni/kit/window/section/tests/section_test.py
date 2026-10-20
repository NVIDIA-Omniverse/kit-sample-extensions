from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.commands as cmd
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd as ou
from omni.kit.ui_test.vec2 import Vec2
from omni.kit.window.section import get_instance as get_section_instance
from omni.kit.window.section.common import CURRENT_TOOL_PATH, SETTING_SECTION_ALWAYS_DISPLAY, WINDOW_NAME
from omni.ui.tests.compare_utils import CompareMetric
from omni.ui.tests.test_base import OmniUiTest


class TestSection(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._section = get_section_instance()

        ext_root_folder = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._golden_img_dir = ext_root_folder.joinpath("data/golden_img")
        self._test_files = ext_root_folder.joinpath("data/usd")

        # Create temp stage
        self._ctx = ou.get_context()
        await self._ctx.new_stage_async()
        await ui_test.wait_n_updates(3)

        self._selection = self._ctx.get_selection()
        self._selection.clear_selected_prim_paths()

        # Show section window and dock
        ui.Workspace.show_window(WINDOW_NAME, True)
        await ui_test.human_delay(2)
        section_window = ui.Workspace.get_window(WINDOW_NAME)

        active_view = ui.Workspace.get_window("Viewport")
        dock_space = ui.Workspace.get_window("DockSpace")
        active_view.dock_in(dock_space, ui.DockPosition.LEFT, 0.7)
        section_window.dock_in(dock_space, ui.DockPosition.RIGHT, 0.3)
        await ui_test.human_delay(2)

    # After running each test
    async def tearDown(self):
        # Close section window
        ui.Workspace.show_window(WINDOW_NAME, False)
        await ui_test.human_delay(2)

        await self._ctx.close_stage_async()
        await super().tearDown()

    def ndc_to_mouse_coord(self, ndc_coord) -> Vec2:
        from omni.kit.viewport.utility import get_active_viewport_window

        window = get_active_viewport_window()

        screen_x = (ndc_coord[0] + 1) * 0.5
        screen_y = 1 - ((ndc_coord[1] + 1) * 0.5)

        # Apply Window Size
        mouse_x = screen_x * window.width
        mouse_y = screen_y * window.height
        return Vec2(mouse_x, mouse_y)

    def create_test_object(self, prim_path, prim_type="Cube", position=(0, 0, 0)):
        kwargs = {"prim_type": prim_type, "prim_path": prim_path, "attributes": {"size": 100.0}}

        cmd.execute("CreatePrimWithDefaultXform", **kwargs)

        prim = self._ctx.get_stage().GetPrimAtPath(prim_path)
        prim.GetAttribute("xformOp:translate").Set(position)

    async def test_general(self):
        from omni.kit.window.section.common import SectionManager

        """Testing general look of section"""
        # Default with section enabled
        await ui_test.human_delay(2)
        await self.finalize_test("section_1.png")

        # Moving mouse over Section
        await ui_test.emulate_mouse_move(self.ndc_to_mouse_coord([0, 0]))
        await ui_test.human_delay(2)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay(2)

        # Changing Alignment of the Section
        self._section._window._quickmove_panel._align_z()
        await ui_test.human_delay(2)
        await self.finalize_test("section_align_z.png")
        self._section._window._quickmove_panel._align_y()
        await ui_test.human_delay(2)
        await self.finalize_test("section_align_y.png")
        self._section._window._quickmove_panel._align_x()
        await ui_test.human_delay(2)
        await self.finalize_test("section_align_x.png")

        # Rotating Clockwise and CounterClockwise
        self._section._window._quickmove_panel._on_rotate_clockwise()
        await ui_test.human_delay(2)
        self._section._window._quickmove_panel._on_rotate_counter_clockwise()
        await ui_test.human_delay(2)
        await self.finalize_test("section_2.png")

        # Rotating Widget
        SectionManager().rotate_widget("x", 90)
        await ui_test.human_delay(2)
        await self.finalize_test("section_3.png")
        SectionManager().rotate_widget("y", 90)
        await ui_test.human_delay(2)
        await self.finalize_test("section_3b.png")
        SectionManager().rotate_widget("z", 90)
        await ui_test.human_delay(2)
        await self.finalize_test("section_3c.png")

        # Moving the section to a new position
        SectionManager().set_widget_position([0, 100, 0])

        # Checking math on computing center of prim bounds
        self.create_test_object("/cube_a", position=(100, 0, 0))
        await ui_test.human_delay(2)
        self.create_test_object("/cube_b", position=(-100, 0, 0))
        await ui_test.human_delay(2)
        prim_midpoint = SectionManager().get_center_of_prims(["/cube_a", "/cube_b"])
        self.assertTrue(prim_midpoint == [0, 0, 0])

    async def test_hide_when_window_close(self):
        await ui_test.human_delay(2)
        await self.finalize_test("section_1.png")

        settings = carb.settings.get_settings()
        always_display = settings.get(SETTING_SECTION_ALWAYS_DISPLAY)
        self.assertFalse(always_display)

        switch = self._section._window._always_display_switch
        self.assertFalse(switch.model.as_bool)
        self.assertFalse(switch.checked)

        try:
            # Close section window with always display OFF
            ui.Workspace.show_window(WINDOW_NAME, False)
            await ui_test.human_delay(2)
            await self.finalize_test("section_all_hide.png")

            ui.Workspace.show_window(WINDOW_NAME, True)
            await ui_test.human_delay(2)
            await self.finalize_test("section_1.png")

            settings.set(SETTING_SECTION_ALWAYS_DISPLAY, True)
            self.assertTrue(switch.model.as_bool)
            self.assertTrue(switch.checked)

            # Close section window again with always display ON
            ui.Workspace.show_window(WINDOW_NAME, False)
            await ui_test.human_delay(2)
            await self.finalize_test("section_still_enable.png")
        finally:
            settings.set(SETTING_SECTION_ALWAYS_DISPLAY, False)

    async def test_tool_change(self):
        settings = carb.settings.get_settings()

        window = ui.Workspace.get_window(WINDOW_NAME)
        self.assertTrue(window is not None and window.visible)

        await ui_test.human_delay(10)

        settings.set(CURRENT_TOOL_PATH, "None")

        await ui_test.human_delay(10)

        self.assertFalse(window.visible)

        await self.finalize_test("section_tool_change.png")

    async def test_quick_move_panel(self):
        x_button = ui_test.find(f"{WINDOW_NAME}//Frame/**/Button[*].text=='X'")
        await x_button.click()

        await ui_test.human_delay(2)

        y_button = ui_test.find(f"{WINDOW_NAME}//Frame/**/Button[*].text=='Y'")
        await y_button.click()

        await ui_test.human_delay(2)

        z_button = ui_test.find(f"{WINDOW_NAME}//Frame/**/Button[*].text=='Z'")
        await z_button.click()

        await ui_test.human_delay(2)

        ccw_button = ui_test.find(f"{WINDOW_NAME}//Frame/**/Button[*].name=='counter_clockwise'")
        await ccw_button.click()

        await ui_test.human_delay(2)

        cw_button = ui_test.find(f"{WINDOW_NAME}//Frame/**/Button[*].name=='clockwise'")
        await cw_button.click()

        await ui_test.human_delay(2)

        inverse_button = ui_test.find(f"{WINDOW_NAME}//Frame/**/Button[*].text=='Inverse Cut Direction'")
        await inverse_button.click()

        await ui_test.human_delay(2)

        await self.finalize_test("section_quick_move_panel.png")

    async def test_always_display_switch(self):
        switch = ui_test.find(f"{WINDOW_NAME}//Frame/**/ImageWithProvider[*].identifier=='switch'")
        await ui_test.human_delay(2)

        await switch.click()
        await ui_test.human_delay(2)

        await switch.click()
        await ui_test.human_delay(2)

        await self.finalize_test("section_always_display_switch.png")

    async def test_dock(self):
        window = ui.Workspace.get_window(WINDOW_NAME)

        self.assertTrue(window.is_visible())
        self.assertTrue(window.get_active())

        docked = window.dock("DockSpace")
        self.assertTrue(docked)

    async def test_section_manager(self):
        from omni.kit.window.section.common import SectionManager

        manager = SectionManager()

        self.assertTrue(len(manager.section_names) == 1)

    async def test_current_tool(self):
        """OMFP-3552: Opening Section tool disables navigation tools"""
        settings = carb.settings.get_settings()
        NAVIGATION_TOOL = "navigation"
        SECTION_TOOL = WINDOW_NAME
        settings.set_string(CURRENT_TOOL_PATH, NAVIGATION_TOOL)

        # Start with a hidden window
        ui.Workspace.show_window(WINDOW_NAME, False)
        await ui_test.human_delay(2)

        # Showing the window changes current tool
        ui.Workspace.show_window(WINDOW_NAME, True)
        await ui_test.human_delay(2)
        self.assertEqual(settings.get_as_string(CURRENT_TOOL_PATH), SECTION_TOOL)

        # Close window => set to navigation
        ui.Workspace.show_window(WINDOW_NAME, False)
        await ui_test.human_delay(2)
        self.assertEqual(settings.get_as_string(CURRENT_TOOL_PATH), NAVIGATION_TOOL)

        # Don't interfere with other tools - these interactions must be defined by the app
        other_tool_name = "some_other_tool"
        settings.set_string(CURRENT_TOOL_PATH, other_tool_name)
        ui.Workspace.show_window(WINDOW_NAME, True)
        await ui_test.human_delay(2)
        self.assertEqual(settings.get_as_string(CURRENT_TOOL_PATH), other_tool_name)

    async def finalize_test(self, golden_img_name):
        return await super().finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)


class TestSectionExtension(OmniUiTest):
    async def setUp(self):
        await super().setUp()

        # Create temp stage
        self._ctx = ou.get_context()
        await self._ctx.new_stage_async()
        await ui_test.wait_n_updates(3)

    async def tearDown(self):
        await super().tearDown()

        await self._ctx.close_stage_async()
        await super().tearDown()

    async def test_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.window.section"
        self.assertTrue(manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay(5)
        self.assertFalse(manager.is_extension_enabled(ext_id))

        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay(5)
        self.assertTrue(manager.is_extension_enabled(ext_id))
