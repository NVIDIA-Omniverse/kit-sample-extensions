from pathlib import Path
from unittest.mock import patch

import carb.settings
import carb.tokens
import omni.client
import omni.kit.actions.core
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.ui.tests.test_base import OmniUiTest

from ..scripts import window as _window
from ..scripts.extension import WindowWelcomeExtension, get_instance
from ..scripts.widgets.action_button_container import SETTINGS_APPLICATION_MODE_PATH

TEST_DATA_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.usd_explorer.window.welcome}/data/tests"))


class TestWelcomeWindow(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.joinpath("golden_img").absolute()
        self._usd_dir = TEST_DATA_PATH.joinpath("usd").absolute()
        settings = carb.settings.get_settings()
        settings.set_bool("/app/window/showStartup", True)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    # @skip
    async def test_welcome_window(self):
        def dummy_stat(_):
            return omni.client.Result.OK, None

        # patch omni client stat calls
        with patch("omni.client.stat", side_effect=dummy_stat):
            ui.Workspace.show_window(WindowWelcomeExtension.WINDOW_NAME)
            window = ui.Workspace.get_window(WindowWelcomeExtension.WINDOW_NAME)
            await omni.kit.app.get_app().next_update_async()
            await self.docked_test_window(window=window, width=1400, height=640, block_devices=False)
            await omni.kit.app.get_app().next_update_async()

            # test file actions
            # mock action execution
            with patch.object(omni.kit.actions.core, "execute_action") as mock_action:
                await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(430, 130))
                mock_action.assert_called_with("omni.kit.window.file", "open")
                # OMFP-2112 -- we don't want to close this window until a file is actually opened,
                # in case the user cancels out of the file dialog.
                self.assertTrue(window.visible)

            # # test UI
            # get_instance().show_window(True)
            # await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(500, 500), right_click=True)
            # await ui_test.human_delay(20)
            # await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="welcome_window.png")
            await self.finalize_test_no_image()

    async def test_welcome_window_open_file(self):
        def dummy_stat(_):
            return omni.client.Result.OK, None

        # patch omni client stat calls
        with patch("omni.client.stat", side_effect=dummy_stat):
            ui.Workspace.show_window(WindowWelcomeExtension.WINDOW_NAME)
            window = ui.Workspace.get_window(WindowWelcomeExtension.WINDOW_NAME)
            await omni.kit.app.get_app().next_update_async()
            await self.docked_test_window(window=window, width=1400, height=640, block_devices=False)
            await omni.kit.app.get_app().next_update_async()

            open_button = ui_test.find("Welcome//Frame/**/Rectangle[*].name=='Open'")
            self.assertIsNotNone(open_button)
            await open_button.click()
            await omni.kit.app.get_app().next_update_async()

            new_session_link_field = ui_test.find("Welcome//Frame/**/StringField[*].name=='new_session_link_field'")
            self.assertIsNotNone(new_session_link_field)
            source_file = str(self._usd_dir.joinpath("cubeYellow.usda"))
            new_session_link_field.model.set_value(source_file)
            await omni.kit.app.get_app().next_update_async()

            open_link_button = ui_test.find("Welcome//Frame/**/Button[*].name=='open_link_button'")
            self.assertIsNotNone(open_link_button)
            await open_link_button.click()
            await ui_test.wait_n_updates(10)
            stage = omni.usd.get_context().get_stage()
            self.assertIsNotNone(stage)
            if stage is not None:
                root_layer = stage.GetRootLayer()
                self.assertIsNotNone(root_layer)
                if root_layer is not None:
                    self.assertTrue(str(root_layer.resolvedPath).endswith("cubeYellow.usda"))

            await self.finalize_test_no_image()

    async def test_welcome_window_modify(self):
        settings = carb.settings.get_settings()

        ui.Workspace.show_window(WindowWelcomeExtension.WINDOW_NAME)
        window = ui.Workspace.get_window(WindowWelcomeExtension.WINDOW_NAME)
        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(window=window, width=1400, height=640, block_devices=False)
        await omni.kit.app.get_app().next_update_async()

        modify_button = ui_test.find("Welcome//Frame/**/Rectangle[*].name=='New'")
        self.assertIsNotNone(modify_button)
        await modify_button.click()
        await omni.kit.app.get_app().next_update_async()
        application_mode = settings.get_as_string(SETTINGS_APPLICATION_MODE_PATH).lower()
        self.assertTrue(application_mode == "layout")
        window.show()
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test_no_image()

    async def test_welcome_window_learn(self):
        ui.Workspace.show_window(WindowWelcomeExtension.WINDOW_NAME)
        window = ui.Workspace.get_window(WindowWelcomeExtension.WINDOW_NAME)
        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(window=window, width=1400, height=640, block_devices=False)
        await omni.kit.app.get_app().next_update_async()

        learn_button = ui_test.find("Welcome//Frame/**/Rectangle[*].name=='Learn'")
        self.assertIsNotNone(learn_button)
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test_no_image()

    async def test_welcome_window_toggle(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.usd_explorer.window.welcome"
        self.assertTrue(ext_id)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, False)
        await ui_test.wait_n_updates(30)
        self.assertTrue(not manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.wait_n_updates(30)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        await self.finalize_test_no_image()

    async def test_welcome_window_remains_visible_after_canceling_open(self):
        def dummy_stat(_):
            return omni.client.Result.OK, None

        # patch omni client stat calls
        with patch("omni.client.stat", side_effect=dummy_stat):
            ui.Workspace.show_window(WindowWelcomeExtension.WINDOW_NAME)
            window = ui.Workspace.get_window(WindowWelcomeExtension.WINDOW_NAME)
            await omni.kit.app.get_app().next_update_async()
            await self.docked_test_window(window=window, width=1400, height=640, block_devices=False)
            await omni.kit.app.get_app().next_update_async()
            self.assertTrue(window.visible, "welcome window is not visible before opening file dialog.")

            open_button = ui_test.find("Welcome//Frame/**/Rectangle[*].name=='Open'")
            self.assertIsNotNone(open_button)
            await open_button.click()
            await omni.kit.app.get_app().next_update_async()

            open_file_window = ui.Workspace.get_window("Open File")
            self.assertTrue(open_file_window is not None and open_file_window.visible)

            await ui_test.emulate_keyboard_press(carb.input.KeyboardInput.ESCAPE)
            await omni.kit.app.get_app().next_update_async()

            self.assertTrue(window.visible, "welcome window is not visible after exiting file dialog.")

            await self.finalize_test_no_image()
