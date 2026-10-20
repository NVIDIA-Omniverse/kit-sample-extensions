# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import tempfile
import unittest.mock as mock

import omni.kit.test
from omni.asset_validator.core import Issue, IssueSeverity
from omni.asset_validator.ui import ApplicationModel, AssetResultsModel, IssueModel, SaveCSVAction
from pxr import Usd


class SaveCSVActionTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.model = ApplicationModel.create()
        test_asset = Usd.Stage.CreateInMemory()
        asset_results = AssetResultsModel(test_asset)
        issue = Issue(message="Test", severity=IssueSeverity.FAILURE)
        issue_model = IssueModel(issue)
        issue_model.selected = True
        asset_results.issues = [issue_model]
        self.model.results.add_asset(asset_results)

    async def test_save_csv_action_shows_dialog(self):
        with mock.patch("omni.asset_validator.ui.commands._save_csv.get_file_exporter") as mock_exporter_fn:
            mock_exporter = mock.MagicMock()
            mock_exporter_fn.return_value = mock_exporter

            action = SaveCSVAction(model=self.model)
            await action.apply_async()

            mock_exporter.show_window.assert_called_once()
            call_kwargs = mock_exporter.show_window.call_args[1]
            self.assertEqual(call_kwargs["title"], "Save as CSV")
            self.assertEqual(call_kwargs["export_handler"], action.export_csv)

    async def test_save_csv_action_no_exporter(self):
        with mock.patch("omni.asset_validator.ui.commands._save_csv.get_file_exporter", return_value=None):
            action = SaveCSVAction(model=self.model)
            await action.apply_async()  # Should not raise

    async def test_export_csv_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            combined_path = os.path.join(tmp_dir, "test.csv")
            with mock.patch("omni.client.combine_urls", return_value=combined_path) as mock_combine:
                with mock.patch.object(
                    __import__("omni.asset_validator.core", fromlist=["IssueCSVData"]).IssueCSVData,
                    "export_csv",
                ) as mock_export:
                    action = SaveCSVAction(model=self.model)
                    action.export_csv("test", tmp_dir, ".csv", [])

                    mock_combine.assert_called_once_with(tmp_dir, "test.csv")
                    mock_export.assert_called_once_with(combined_path)
