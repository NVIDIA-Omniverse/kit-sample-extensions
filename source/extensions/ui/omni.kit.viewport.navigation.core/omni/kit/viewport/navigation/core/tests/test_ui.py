import asyncio
from pathlib import Path
from re import I

import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.ui_test import Vec2
from omni.kit.viewport.menubar.core import get_instance as get_menubar_instance
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

from ..constant import (
    NAVIGATION_HOTKEYS_ENABLED,
    NAVIGATION_IS_LARGE,
    NAVIGATION_IS_VISIBLE,
    NAVIGATION_TOOL_BOTTOM_OFFSET,
    NAVIGATION_TOOL_BOTTOM_SPACING,
    NAVIGATION_TOOL_OPERATION_ACTIVE,
    SETTINGS_PATH_MODAL_TOOL_ACTIVE,
    SETTINGS_ROOT,
    VIEWPORT_TOOLS_BOTTOM_OFFSET_PATH,
)
from ..delegate import ToolBarIconMenuDelegate
from ..extension import get_navigation_bar_name
from ..navigation_tooltip import ViewportNavigationTooltip
from ..widget import ViewportNavigationButton, ViewportNavigationOptionMenuButton, ViewportNavigationSeparator

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300

SETTING_COMPARE_COLDEN = "/app.navigation.test/golden_compare"


class TestNavigationBar(OmniUiTest):
    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()
        self._golden_compare = self._settings.get(SETTING_COMPARE_COLDEN)

        self._settings.set_bool(NAVIGATION_IS_VISIBLE, True)

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        navigation_bar_name = get_navigation_bar_name()
        self._navigaiton_bar = get_menubar_instance().get_menubar(navigation_bar_name)
        tokens = carb.tokens.get_tokens_interface()
        icon_path = tokens.resolve("${omni.kit.viewport.navigation.core}/icons/")
        true_image = icon_path + "navTips_active_dark.svg"
        print(true_image)
        false_image = icon_path + "navTips_dark.svg"
        order_setting = SETTINGS_ROOT + "tips_order"
        visible_setting = SETTINGS_ROOT + "tips_visible"
        name = "tips1"
        name2 = "tips2"
        name3 = "tips3"
        style = {
            "Navigation.Button.Image::" + f"{name}": {"image_url": f"{false_image}"},
            "Navigation.Button.Image::" + f"{name}:checked": {"image_url": f"{true_image}"},
            "Navigation.Button.Image::" + f"{name2}": {"image_url": f"{false_image}"},
            "Navigation.Button.Image::" + f"{name2}:checked": {"image_url": f"{true_image}"},
            "Navigation.Button.Image::" + f"{name3}": {"image_url": f"{false_image}"},
            "Navigation.Button.Image::" + f"{name3}:checked": {"image_url": f"{true_image}"},
        }

        with self._navigaiton_bar:
            self._navigation_button = ViewportNavigationButton(
                name,
                43,
                visible_setting_path=visible_setting,
                order_setting_path=order_setting,
                has_triangle=True,
                build_menu_fn=self._build_menu_items,
                build_tooltip_fn=self._build_tooltip,
                style=style,
            )
            self._navigation_button.set_state(False)

            self._window_button = ViewportNavigationButton(
                name2,
                43,
                has_triangle=True,
                build_window_fn=self._build_window,
                style=style,
            )
            self._window_button.set_state(False)

            self._option_button = ViewportNavigationOptionMenuButton(
                name3,
                false_image,
                43,
                size_change_fn=self.on_size_change,
                direction_change_fn=self.on_direction_change,
                direction=self._navigaiton_bar._direction,
            )
            self._option_button.state = False
            # https://docs.google.com/presentation/d/1gbWFNoNsKq9slCRaBicaF9QAbhLiY8ZM_4l-DkFSRq0/edit#slide=id.g15bcfa696e3_0_54
            # Add separator for review tools
            self._separator = ViewportNavigationSeparator()

        ViewportNavigationTooltip.set_visible(True)
        for i in range(14):
            await omni.kit.app.get_app().next_update_async()
        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='tips1'")
        self._button2 = ui_test.find("Viewport//Frame/**/Button[*].name=='tips2'")
        self._button3 = ui_test.find("Viewport//Frame/**/Menu[*].name=='tips3'")

    def on_direction_change(self, direction):
        pass

    def on_size_change(self, is_big: bool):
        pass

    def _build_window(self):
        self._test_window = ui.Window("test")
        self._test_window.visible = True
        with self._test_window.frame:
            self._build_tooltip()
        return self._test_window

    def _build_menu_items(self) -> list:
        return [
            ui.MenuItem(
                "test menu1",
            ),
            ui.MenuItem(
                "test menu2",
            ),
        ]

    def _build_tooltip(self):
        ViewportNavigationTooltip.build_space(self)
        ViewportNavigationTooltip.build_shortcut("F", 18)
        ViewportNavigationTooltip.build_label("test")
        return 50, 50

    async def tearDown(self):
        self._navigation_button.destroy()
        self._navigation_button = None
        self._window_button.destroy()
        self._window_button = None
        self._option_button.destroy()
        self._option_button = None
        self._separator.destroy()
        self._separator = None

    async def finalize_test(self, golden_img_name: str):
        if self._golden_compare:
            await omni.kit.app.get_app().next_update_async()
            await super().finalize_test(
                threshold=500, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name
            )
            await omni.kit.app.get_app().next_update_async()
        else:
            self.assertTrue(self._button)

    async def test_button(self):
        self.assertEqual(self._navigation_button.name, "tips1")
        self.assertEqual(self._navigation_button.label, "tips1")
        self._navigation_button.label = "test_label"
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self._navigation_button.label, "test_label")

        test_button = ViewportNavigationButton(
            "test",
            43,
            has_triangle=True,
            build_menu_fn=self._build_menu_items,
            build_window_fn=self._build_window,
            alignment=ui.Alignment.RIGHT_BOTTOM,
        )
        test_button.build_fn({})
        test_button.name = "test"
        test_button.style = {}
        test_button.checked = True
        self.assertTrue(test_button.checked)
        test_button._show_menu()
        self.assertTrue(test_button._menu.visible)
        test_button._show_window()
        self.assertTrue(test_button._window.visible)

    async def test_general(self):
        self._settings.set(NAVIGATION_IS_LARGE, True)
        self._settings.set(NAVIGATION_IS_LARGE, False)
        self._settings.set(NAVIGATION_IS_VISIBLE, True)
        self._settings.set(NAVIGATION_IS_VISIBLE, False)
        self._settings.set(SETTINGS_PATH_MODAL_TOOL_ACTIVE, True)
        self._settings.set(SETTINGS_PATH_MODAL_TOOL_ACTIVE, False)
        await self.finalize_test(golden_img_name="navigation_core.png")

    async def test_icon_menu_delegate(self):
        menu_delegate = ToolBarIconMenuDelegate("test_menu")
        menu_delegate.build_item(ui.MenuItem("test_menu_item"))
        menu_delegate.has_title = True
        self.assertTrue(menu_delegate.has_title)
        menu_delegate.text_visible = True
        self.assertTrue(menu_delegate.text_visible)
        menu_delegate.checked = True
        self.assertTrue(menu_delegate.checked)
        menu_delegate.enabled = True
        self.assertTrue(menu_delegate.enabled)
        menu_delegate = None

    async def test_tooltip(self):
        ViewportNavigationTooltip.set_visible(True)
        ViewportNavigationTooltip.show(self._navigation_button, self._navigation_button.name, self._build_tooltip)
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        ViewportNavigationTooltip.hide(self._navigation_button.name)
        self.assertTrue(ViewportNavigationTooltip.show_tooltip())

    async def test_waypoint_active(self):
        # Create a new stage to show camera parameters
        await omni.usd.get_context().new_stage_async()
        await self._button.click()
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                break
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_name="navigation_core_active.png")

        await self._button.right_click()
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                break
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_name="navigation_core_window.png")

        await self._button2.right_click()
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                break
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_name="navigation_core_menu.png")

        await self._button3.right_click()
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                break
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_name="navigation_core_option.png")

        self._navigaiton_bar.destroy()
        self._navigaiton_bar = None

    async def test_hotkeys(self):
        next_op_key = "SPACE"
        self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, "none")
        self.assertEqual(self._settings.get(NAVIGATION_HOTKEYS_ENABLED) or False, False)

        await ui_test.emulate_key_combo(next_op_key)
        self.assertEqual(self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE), "none")

        # enable hotkeys, reload extension
        self._settings.set(NAVIGATION_HOTKEYS_ENABLED, True)
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.viewport.navigation.core"
        self.assertTrue(ext_id)
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertFalse(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))

        await ui_test.emulate_key_combo(next_op_key)
        self.assertEqual(self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE), "orbit")

        await ui_test.emulate_key_combo(next_op_key)
        self.assertEqual(self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE), "teleport")

        await ui_test.emulate_key_combo(next_op_key)
        self.assertEqual(self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE), "orbit")

        # hotkeys are deregistered after extension unload
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertFalse(manager.is_extension_enabled(ext_id))

        await ui_test.emulate_key_combo(next_op_key)
        self.assertEqual(self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE), "orbit")

        # re-enable for other tests
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))
