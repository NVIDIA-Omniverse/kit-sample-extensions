# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import tempfile
from pathlib import Path

from omni.kit import ui_test

from ..file_picker import FileBrowserMode, FilePicker
from ..filebrowser import FileBrowserSelectionType
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestFilePicker(TestWidgetsCustomBase):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR
        self._hide_main_menu_bar()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    def _on_file_selected(self, path: str):
        self._file = path

    def _on_canceled(self):
        self._file = "Cancel"

    async def test_filepicker(self):
        self._window = await self.create_test_window(width=1024, height=624, block_devices=False)
        self._file = None

        filepicker = FilePicker(
            "Test to pick a file",
            FileBrowserMode.SAVE,
            FileBrowserSelectionType.FILE_ONLY,
            [(r".*\.txt]", "Txt Files (*.txt)")],
        )

        filepicker.set_file_selected_fn(self._on_file_selected)
        filepicker.set_cancel_fn(self._on_canceled)

        # Check the file picker window
        filepicker.show(None, None, True)
        await wait_frames(3)
        await self.capture_and_compare(100, self._golden_img_dir, golden_img_name="file_picker-1.png")
        await wait_frames(3)

        path = str(Path(tempfile.gettempdir()).joinpath("12345678.test").absolute())
        path.replace("/", "\\")
        file = open(path, "w")
        file.close()

        # Check the prompt (overwrite) dialog
        filepicker._on_file_open(path)
        await wait_frames(3)
        await self.capture_and_compare(100, self._golden_img_dir, golden_img_name="file_picker-2.png")

        # Confirm overwrite
        await ui_test.emulate_mouse_move(ui_test.Vec2(480, 335))
        await wait_frames(3)
        await ui_test.emulate_mouse_click()

        await wait_frames(3)
        await self.capture_and_compare(100, self._golden_img_dir, golden_img_name="file_picker-1.png")

        await wait_frames(3)
        self.assertEqual(self._file, path)

        await ui_test.emulate_mouse_move(ui_test.Vec2(950, 600))
        await wait_frames(3)
        await ui_test.emulate_mouse_click()

        filepicker.set_current_directory("c:/")
        filepicker.set_current_filename("123.txt")
        filepicker.destroy()

        await wait_frames(3)
        await self.finalize_test_no_image()
