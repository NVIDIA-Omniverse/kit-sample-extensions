from pathlib import Path
from unittest.mock import Mock, patch

import carb
import omni.kit.app
import omni.kit.clipboard
import omni.kit.commands
import omni.kit.menu.utils
import omni.kit.viewport.utility
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.kit.menu.utils import MenuLayout
from omni.ui.tests.test_base import OmniUiTest
from pxr import UsdGeom

from ..extension import FileMenu
from ..ui.file_share_window import FileShareWindow

TEST_MENUBAR_FRAME = "MenubarFrame Test"
CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.usd_explorer.main.menubar}/data/tests"))
SETTINGS_APPLICATION_MODE_PATH = "/app/application_mode"
APPLICATION_MODES_PATH = "/exts/omni.kit.usd_explorer.main.menubar/include_application_modes"
FILE_MENU_PATH = "/exts/omni.kit.usd_explorer.main.menubar/include_file_menu"
RENDER_MODES_PATH = "/exts/omni.kit.usd_explorer.main.menubar/include_render_modes"


class MockLayerInterface:

    @staticmethod
    def get_live_syncing():
        return MockLiveSync()


class MockLiveSession:

    logged_user_name = "live_user"
    shared_link = "omniverse://dummy.usd?live_session_name=Default"


class MockLiveSync:

    @staticmethod
    def is_in_live_session():
        return True

    @staticmethod
    def get_current_live_session():
        return MockLiveSession()


class TestMenuBarExtension(OmniUiTest):
    async def test_01_file_share_window(self):
        try:
            self._show_viewport_window(visible=False)
            window = FileShareWindow(modal=True)
            await ui_test.human_delay()

            # initial state
            self.assertFalse(window.visible)
            self.assertTrue(window.flags | ui.WINDOW_FLAGS_MODAL)
            self.assertEqual(window.url, "")

            # show, set url
            window.visible = True
            await ui_test.human_delay(10)

            url = "omniverse://dummy.usd"
            window.url = url
            self.assertEqual(window.url, url)
            await ui_test.human_delay()
            await self.capture_and_compare(
                threshold=100, golden_img_dir=self._golden_img_dir, golden_img_name="fileshare.png"
            )

            # click on share
            share_button = ui_test.find(("Share Omniverse USD Path//Frame/**/Button[*].name=='share_button'"))
            self.assertIsNotNone(share_button)
            await share_button.click()
            await ui_test.human_delay()
            self.assertFalse(window.visible)
            self.assertEqual(omni.kit.clipboard.paste(), url)
        finally:
            window.destroy()

    async def test_01_file_share_window_live(self):
        self._show_viewport_window(visible=False)
        await self._enable_extension()
        try:
            buttons = FileMenu()._buttons[:]
            self.assertTrue(buttons)
            share = next((btn for btn in buttons if type(btn).__name__ == "ShareButton"), None)
            self.assertIsNotNone(share)
            with patch.object(share, "_layers_interface", MockLayerInterface):
                self.assertTrue(hasattr(share, "_on_click"))
                share._on_click()
                await ui_test.human_delay()
                await self.capture_and_compare(
                    threshold=100, golden_img_dir=self._golden_img_dir, golden_img_name="fileshare_live.png"
                )

                # click on share
                share_button = ui_test.find(("Share Omniverse USD Path//Frame/**/Button[*].name=='share_button'"))

                self.assertIsNotNone(share_button)
                await share_button.click()
                await ui_test.human_delay()
        finally:
            await self._disable_extension()

    async def test_02_application_modes(self):
        self._show_viewport_window(visible=False)
        self._setting.set_bool(APPLICATION_MODES_PATH, True)
        self._setting.set_bool(FILE_MENU_PATH, False)
        self._setting.set_bool(RENDER_MODES_PATH, False)

        self._setting.set_string(SETTINGS_APPLICATION_MODE_PATH, "review")

        await self._enable_extension()

        modes = ["review", "present", "layout", "approve"]

        for mode in modes:
            self._setting.set_string(SETTINGS_APPLICATION_MODE_PATH, mode)
            await ui_test.human_delay(10)
            await self.capture_and_compare(
                threshold=self._DIFF_THRESHOLD,
                golden_img_dir=self._golden_img_dir,
                golden_img_name=f"app_modes_{mode}.png",
                hide_menu_bar=False,
            )

        import omni.appwindow

        app_window = omni.appwindow.get_default_app_window()
        old_width, old_height = app_window.get_width(), app_window.get_height()
        app_window.resize(old_width - 100, old_height - 100)
        await ui_test.human_delay(50)
        app_window.resize(old_width, old_height)
        await ui_test.human_delay(50)

        await self._disable_extension()

    async def test_03_file_menu(self):
        self._show_viewport_window(visible=False)
        self._setting.set_bool(APPLICATION_MODES_PATH, False)
        self._setting.set_bool(FILE_MENU_PATH, True)
        self._setting.set_bool(RENDER_MODES_PATH, False)

        self._setting.set_string(SETTINGS_APPLICATION_MODE_PATH, "review")

        await self._enable_extension()

        modes = ["review", "present", "layout", "approve"]

        for mode in modes:
            self._setting.set_string(SETTINGS_APPLICATION_MODE_PATH, mode)
            await ui_test.human_delay(10)
            await self.capture_and_compare(
                threshold=self._DIFF_THRESHOLD,
                golden_img_dir=self._golden_img_dir,
                golden_img_name=f"file_menu_{mode}.png",
                hide_menu_bar=False,
            )

        await self._disable_extension()

    async def test_04_default_menu_hover(self):
        """Test hover state of default menu in menubar"""
        self._show_viewport_window(visible=False)
        # Only make Edit visible
        omni.kit.menu.utils.remove_layout(self._clean_layout)
        self._clean_layout = [
            MenuLayout.Menu("File", remove=True),
            MenuLayout.Menu("Edit", remove=False),
            MenuLayout.Menu("Create", remove=True),
            MenuLayout.Menu("Rendering", remove=True),
            MenuLayout.Menu("Window", remove=True),
            MenuLayout.Menu("Tools", remove=True),
            MenuLayout.Menu("Help", remove=True),
        ]
        omni.kit.menu.utils.add_layout(self._clean_layout)

        await self._enable_extension()

        menubar_ref = ui_test.get_menubar()
        edit_ref = menubar_ref.find_menu("Edit")
        await ui_test.emulate_mouse_move(edit_ref.center)
        await self.capture_and_compare(
            threshold=self._DIFF_THRESHOLD,
            golden_img_dir=self._golden_img_dir,
            golden_img_name="default_menu_hover.png",
            hide_menu_bar=False,
        )

        await self._disable_extension()

    async def test_05_selection(self):
        self._show_viewport_window()
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        stage = usd_context.get_stage()
        self.assertIsNotNone(stage)

        await ui_test.human_delay()
        await self._enable_extension()
        await ui_test.human_delay()

        with omni.kit.undo.disabled():
            size = 0.5 / UsdGeom.GetStageMetersPerUnit(stage)
            omni.kit.commands.execute(
                "CreatePrimWithDefaultXform",
                prim_type="Sphere",
                select_new_prim=False,
                attributes={
                    UsdGeom.Tokens.radius: size,
                    UsdGeom.Tokens.extent: [(-size, -size, -size), (size, size, size)],
                },
            )

        app_window = omni.appwindow.get_default_app_window()
        app_width, app_height = app_window.get_width(), app_window.get_height()
        drag_offset = 100
        drag_end = ui_test.Vec2(app_width - drag_offset, app_height - drag_offset)
        drag_start = ui_test.Vec2(drag_offset, drag_offset)

        async def do_test(expected_result: True):
            await ui_test.human_delay()
            await ui_test.emulate_mouse_move(drag_start)
            await ui_test.human_delay()
            await ui_test.emulate_mouse_drag_and_drop(drag_start, drag_end)
            await ui_test.human_delay()
            selection = usd_context.get_selection().get_selected_prim_paths()
            result = True if len(selection) > 0 else False
            self.assertEqual(result, expected_result)

        tests = [
            ("layout", ui_test.Vec2(675.0, 10.0), True),
            ("review", ui_test.Vec2(600.0, 10.0), False),
            ("present", ui_test.Vec2(525.0, 10.0), False),
        ]

        for mode, mode_menu_item_pos, expected_result in tests:
            await ui_test.emulate_mouse_move(mode_menu_item_pos)
            await ui_test.human_delay()
            await ui_test.emulate_mouse_click()
            await do_test(expected_result)

        for mode, mode_menu_item_pos, expected_result in tests:
            self._setting.set_string(SETTINGS_APPLICATION_MODE_PATH, mode)
            await do_test(expected_result)

        await self._disable_extension()

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._setting = carb.settings.get_settings()
        self._save_settings()
        self._setting.set(FILE_MENU_PATH, True)
        await self._disable_extension()
        self._DIFF_THRESHOLD = 0.5

        # Clean main menu bar
        self._menu_layout = omni.kit.menu.utils.get_menu_layout()
        self._clean_layout = [
            MenuLayout.Menu("File", remove=True),
            MenuLayout.Menu("Edit", remove=True),
            MenuLayout.Menu("Create", remove=True),
            MenuLayout.Menu("Rendering", remove=True),
            MenuLayout.Menu("Window", remove=True),
            MenuLayout.Menu("Tools", remove=True),
            MenuLayout.Menu("Help", remove=True),
        ]
        omni.kit.menu.utils.add_layout(self._clean_layout)

    # After running each test
    async def tearDown(self):
        self._restore_settings()
        omni.kit.menu.utils.remove_layout(self._clean_layout)
        await super().tearDown()

    def _save_settings(self):
        settings_path_list = [
            APPLICATION_MODES_PATH,
            FILE_MENU_PATH,
            RENDER_MODES_PATH,
        ]
        self._stored_settings = {}
        for path in settings_path_list:
            self._stored_settings[path] = self._setting.get(path)

    def _restore_settings(self):
        for path, value in self._stored_settings.items():
            self._setting.set(path, value)

    async def _enable_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.usd_explorer.main.menubar"
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay(100)
        self.assertTrue(manager.is_extension_enabled(ext_id))

    async def _disable_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.usd_explorer.main.menubar"
        self.assertTrue(ext_id)
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertFalse(manager.is_extension_enabled(ext_id))

    def _show_viewport_window(self, visible=True):
        _, window = omni.kit.viewport.utility.get_active_viewport_and_window()
        if window:
            window.visible = visible
