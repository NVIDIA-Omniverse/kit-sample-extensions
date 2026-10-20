# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest.mock as mock

import omni.kit.test
from omni.asset_validator.core import Issue, IssueSeverity
from omni.asset_validator.ui import ApplicationModel, AssetResultsModel, CopyAction, IssueModel
from pxr import Usd


class CopyActionTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.model = ApplicationModel.create()
        test_asset = Usd.Stage.CreateInMemory()
        asset_results = AssetResultsModel(test_asset)
        issue = Issue(message="Test", severity=IssueSeverity.FAILURE)
        issue_model = IssueModel(issue)
        issue_model.selected = True
        asset_results.issues = [issue_model]
        self.model.results.add_asset(asset_results)

    async def test_copy_action_copies_to_clipboard(self):
        with mock.patch("omni.asset_validator.ui.commands._copy.pyperclip.copy") as mock_copy:
            action = CopyAction(model=self.model)
            await action.apply_async()

            self.assertTrue(mock_copy.called)
            copied_text = mock_copy.call_args[0][0]
            self.assertIn("Test", copied_text)

    async def test_copy_action_adds_task(self):
        with mock.patch("omni.asset_validator.ui.commands._copy.pyperclip.copy"):
            action = CopyAction(model=self.model)
            action.apply()

            self.assertTrue(self.model.has_tasks())
            await self.model.wait_tasks()
