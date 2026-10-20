# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import glob
import os
import sys
import unittest
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.usd
from carb.input import KeyboardInput, MouseEventType
from omni import ui
from omni.kit import ui_test
from omni.kit.markup.core import SETTING_MARKUP_EXPORT_LOCAL_FOLDER
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.markup.core.widgets.list_window import MarkupListWindow
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window, next_viewport_frame_async
from omni.ui.tests.test_base import OmniUiTest
from omni.ui_query.query import OmniUIQuery

from ..ui.constant import TOOL_NAME
from ..ui.markup_scene import MARKUP_TOOL_CURRENT, SETTINGS_MARKUP_ACTIVE, SETTINGS_MARKUP_EDITING

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"
CLOUD_DEPLOYMENT_SETTINGS_PATH = "/app/ovc_deployment"


def _skip_etm():
    if (
        carb.settings.get_settings().get_as_bool(CLOUD_DEPLOYMENT_SETTINGS_PATH)
        or os.getenv("ETM_DGXC_ACTIVE")
        or os.getenv("ETM_ACTIVE")
    ):
        return True
    return False


class TestMarkupExportUI(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        get_markup_instance().end_edit_markup(list(get_markup_instance().get_markups())[0], save=True)
        await ui_test.human_delay()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "select")
        self._setting.set_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER, omni.kit.test.get_test_output_path())

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    # Disabling on DGX where the file paths are behaving oddly, causing the test to fail.
    # Will re-enable once we can investigate the issue.
    @unittest.skipIf(_skip_etm(), "Test skipped in OVC deployment, ETM DGX, or ETM active")
    async def test_export_panel(self):

        window = MarkupListWindow()
        window.visible = True

        window.selected_index = 1

        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(window=window, width=1280, height=720, block_devices=False)

        await ui_test.human_delay(20)

        export_button = [
            w
            for w in ui_test.find_all(f"{window.title}//Frame/**")
            if w.widget.style_type_name_override == "Export.Button"
        ][0]
        await export_button.click()

        await ui_test.human_delay(2)

        browse_button = ui_test.find("Markup Export//Frame/**/BrowseButton")
        await browse_button.click()

        await ui_test.human_delay(2)

        # we set this this in the setting so check it went through:
        export_field = ui_test.find("Markup Export//Frame/**/ExportDirField")
        self.assertEqual(export_field.widget.model.as_string, omni.kit.test.get_test_output_path())

        select_button = [
            w
            for w in ui_test.find_all("Select Markup Export Directory//Frame/**")
            if isinstance(w.widget, ui.Button) and w.widget.text == "Select"
        ][0]
        await select_button.click()

        # check all the export format buttons:
        csv_button = ui_test.find("Markup Export//Frame/**/FormatCheckCSV")
        xlsx_button = ui_test.find("Markup Export//Frame/**/FormatCheckXLSX")
        pdf_button = ui_test.find("Markup Export//Frame/**/FormatCheckPDF")

        await csv_button.click()
        await xlsx_button.click()
        await pdf_button.click()

        to_delete = (
            glob.glob(os.path.join(omni.kit.test.get_test_output_path(), "*.csv"))
            + glob.glob(os.path.join(omni.kit.test.get_test_output_path(), "*.xlsx"))
            + glob.glob(os.path.join(omni.kit.test.get_test_output_path(), "*.pdf"))
        )
        for f in to_delete:
            os.remove(f)

        files_before = glob.glob(os.path.join(omni.kit.test.get_test_output_path(), "*"))
        export_button = ui_test.find("Markup Export//Frame/**/ExportButton")
        await export_button.click()
        await ui_test.human_delay(200)

        files_after = glob.glob(os.path.join(omni.kit.test.get_test_output_path(), "*"))

        # make sure we've exported a csv, pdf and xlsx:
        new_files = [x.split(".")[-1] for x in set(files_after) - set(files_before)]
        self.assertEqual(len(new_files), 3)

        self.assertTrue("csv" in new_files)
        self.assertTrue("pdf" in new_files)
        self.assertTrue("xlsx" in new_files)
