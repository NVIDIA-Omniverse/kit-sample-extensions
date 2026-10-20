# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import carb.input
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.ui_test.vec2 import Vec2

from ..extension import WindowExtension, get_ext_instance, has_extension
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestExtension(TestWidgetsCustomBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR
        self._visible = False

        self._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_functions(self):
        result = has_extension("omni.kit.widgets.custom")
        self.assertTrue(result)
        inst = get_ext_instance("omni.kit.widgets.custom")
        self.assertNotEqual(inst, None)

    def _on_visibility_changed(self, visible):
        self._visible = visible

    async def test_window_extension(self):
        class SampleWindow(ui.Window):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._active = True

            def destroy(self):
                pass

            def is_visible(self):
                return self.visible

            def show(self, visible):
                self.visible = visible

            def get_active(self):
                return self._active

            def set_active(self, value):
                self._active = value

            def dock(self, target, ratio, pos):
                pass

        class SampleWindowExtension(WindowExtension):
            def _create_window(self):
                window_flags = ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_NO_RESIZE
                window = SampleWindow(
                    "Test Window Extension",
                    dockPreference=ui.DockPreference.RIGHT,
                    flags=window_flags,
                    width=400,
                    height=200,
                    position_x=0,
                    position_y=0,
                )
                return window

        self._window = await self.create_test_window(width=480, height=320, block_devices=False)
        ext_window = SampleWindowExtension()
        ext_window.on_startup(
            menu_path="Window/TestExtension",
            hotkey=(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL, carb.input.KeyboardInput.T),
            appear_after="",
            use_editor_menu=False,
            on_visibility_changed_fn=self._on_visibility_changed,
        )

        await wait_frames(3)
        self.assertTrue(ext_window.is_visible())

        ext_window.hide()
        await wait_frames(3)
        self.assertFalse(ext_window.is_visible())

        ext_window.show()
        await wait_frames(3)
        self.assertTrue(ext_window.is_visible())

        ext_window.active = False
        await wait_frames(3)
        self.assertFalse(ext_window.active)

        ext_window.active = True
        await wait_frames(3)
        self.assertTrue(ext_window.active)

        ext_window.dock("aaa")

        ext_window.on_shutdown()
        ext_window = None
        await self.finalize_test_no_image()
