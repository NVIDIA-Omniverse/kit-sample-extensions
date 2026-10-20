# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import copy
import glob
import os
import shutil
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.test
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.kit.markup.core import FORMAT_EXTS, SETTING_MARKUP_EXPORT_LOCAL_FOLDER, MarkupExport, MarkupExportObject
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf

from .. import extension
from ..playlist_card_markup import MarkupCard
from ._viewport_frames import wait_for_viewport_frames

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"


class TestMarkupExport(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._setting = carb.settings.get_settings()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        self._export_folder = self._setting.get(SETTING_MARKUP_EXPORT_LOCAL_FOLDER)
        self._setting.set(SETTING_MARKUP_EXPORT_LOCAL_FOLDER, omni.kit.test.get_test_output_path())
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        await wait_for_viewport_frames()

        # create a test markup
        extension.get_instance().create_markup()
        await omni.kit.app.get_app().next_update_async()
        self._markup = list(extension.get_instance().get_markups())[0]
        extension.get_instance().end_edit_markup(self._markup, save=True)
        extension.get_instance().add_element(10, 10, 20, 20, "Label", None, text="hello")
        attr_author = self._markup.usd_prim.GetAttribute("created_by")
        attr_author.Set("Markup Tester")

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        self._setting.set(SETTING_MARKUP_EXPORT_LOCAL_FOLDER, self._export_folder)
        await super().tearDown()

    async def test_export_all_formats(self):
        export_formats = {ext: True for ext in FORMAT_EXTS}
        export_formats["HTML"] = False
        markup_export = MarkupExport(
            get_markup_instance(), export_formats, pdf_page_size_idx=0, pdf_page_landscape=False
        )
        export_file_basename = str(markup_export.export_filepath)

        for f in glob.glob(export_file_basename + ".*"):
            os.remove(f)

        finishedCalled = []

        def finished_callback(finishedCalled):
            finishedCalled.append(True)

        await markup_export.export(lambda: finished_callback(finishedCalled))

        for ext in [".csv", ".pdf", ".xlsx"]:
            self.assertTrue(os.path.exists(export_file_basename + ext))
        self.assertEqual(finishedCalled, [True])

    async def test_export_pdf_landscape(self):
        # export in landscape mode to make sure that doesn't error:
        export_formats = {"PDF": True}
        markup_export = MockMarkupExport(
            get_markup_instance(), export_formats, pdf_page_size_idx=0, pdf_page_landscape=True
        )
        markup_export._filename = "pdf"
        markup_export._title = "Makrup PDF Landscape"
        export_file_basename = str(markup_export.export_filepath)

        finishedCalled = []

        def finished_callback(finishedCalled):
            finishedCalled.append(True)

        for f in glob.glob(export_file_basename + ".*"):
            os.remove(f)

        await markup_export.export(lambda: finished_callback(finishedCalled))

        path_output = export_file_basename + ".pdf"
        self.assertTrue(os.path.exists(path_output))
        self.assertEqual(finishedCalled, [True])

    async def test_export_csv(self):
        """export a csv file and verify the contents"""
        import csv

        export_formats = {"CSV": True}
        markup_export = MockMarkupExport(get_markup_instance(), export_formats)
        markup_export._filename = "csv"
        markup_export._title = "Makrup CSV"
        export_file_basename = str(markup_export.export_filepath)

        finishedCalled = []

        def finished_callback(finishedCalled):
            finishedCalled.append(True)

        for f in glob.glob(export_file_basename + ".*"):
            os.remove(f)

        await markup_export.export(lambda: finished_callback(finishedCalled))

        path_output = export_file_basename + ".csv"
        self.assertTrue(os.path.exists(path_output))
        self.assertEqual(finishedCalled, [True])

        # compare csv files
        path_ref = TEST_DATA_PATH.joinpath(markup_export.export_filepath.name + ".csv")
        with open(path_output, "r", encoding="ascii") as out:
            with open(path_ref, "r", encoding="ascii") as ref:
                out_rows = list(csv.reader(out, delimiter=","))
                ref_rows = list(csv.reader(ref, delimiter=","))

        self.assertEqual(len(out_rows), len(ref_rows))
        for out_row, ref_row in zip(out_rows, ref_rows):
            self.assertListEqual(out_row, ref_row)


class MockMarkupExport(MarkupExport):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._export_dir = Path(omni.kit.test.get_test_output_path())
        self._filename = "export_test"
        self._title = "Test Markup Export"

    @property
    def export_dir(self):
        return self._export_dir

    @property
    def filename(self):
        return self._filename

    @property
    def title(self):
        return self._title

    @property
    def timestamp(self):
        return "no-timestamp"

    def _get_markup_objects(self, markup_instance):
        objects = [MockMarkupExportObject(name, markup_instance) for name in markup_instance.get_all_markup_names()]
        return objects


class MockMarkupExportObject(MarkupExportObject):

    @property
    def url(self):
        return "test-no-url.usd"

    @property
    def creation_date(self):
        return "2023-10-25 20:44:51"
