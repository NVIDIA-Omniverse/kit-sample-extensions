# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import omni.kit.test

from ..models import folder_browser_data
from ..models.folder_browser_data import FileSystemFolder, TraverseResult


class TestConnectionManager(omni.kit.test.AsyncTestCase):
    async def _check_connection_result(self, success, error=None):
        folder = FileSystemFolder("server", "omniverse://unreachable_server_probe/assets")
        callback = Mock()
        connection = AsyncMock(return_value=success, side_effect=error)
        with patch.object(folder, "_traverse_async", AsyncMock(return_value=TraverseResult.URL_UNREACHABLE)), patch.object(
            folder_browser_data, "ensure_connection", connection
        ):
            self.assertFalse(await folder.start_traverse(on_connected_fn=callback))
            callback.assert_not_called()
            await asyncio.sleep(0)
            connection.assert_awaited_once_with("omniverse://unreachable_server_probe", show_connecting_dialog=True)
            callback.assert_called_once_with(folder, success)
        folder.destroy()

    async def test_connection_success_notifies_traversal(self):
        await self._check_connection_result(True)

    async def test_connection_failure_notifies_traversal(self):
        await self._check_connection_result(False)

    async def test_connection_exception_settles_traversal(self):
        await self._check_connection_result(False, RuntimeError("connection probe failed"))

    async def test_cancelled_connection_does_not_report_success_or_failure(self):
        folder = FileSystemFolder("server", "omniverse://unreachable_server_probe/assets")
        callback = Mock()
        with patch.object(folder, "_traverse_async", AsyncMock(return_value=TraverseResult.URL_UNREACHABLE)), patch.object(
            folder_browser_data, "ensure_connection", AsyncMock(side_effect=asyncio.CancelledError)
        ):
            self.assertFalse(await folder.start_traverse(on_connected_fn=callback))
            await asyncio.sleep(0)
            callback.assert_not_called()
        folder.destroy()
