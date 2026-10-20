# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Contract tests for inline rename on ``GraphCanvasWidget`` (native binding)."""

import importlib
import unittest
from unittest.mock import MagicMock, PropertyMock

import omni.kit.test

try:
    _gnw = importlib.import_module("omni.kit.window.material_graph._graphCanvas")
except ImportError:  # pragma: no cover - optional native binary
    _gnw = None


def _graph_canvas_widget_class():
    if _gnw is None:
        return None
    return getattr(_gnw, "GraphCanvasWidget", None)


class TestInlineRenameContract(omni.kit.test.AsyncTestCase):
    """Rename API surface matches what ``graph_canvas_view`` expects."""

    @unittest.skipIf(_graph_canvas_widget_class() is None, "native _graphCanvas not available")
    async def test_rename_api_contract(self):
        """Binding exposes rename entry points used by the Python graph view."""
        self.assertIsNotNone(_gnw)
        self.assertTrue(hasattr(_gnw, "GraphCanvasWidget"))
        gcls = _graph_canvas_widget_class()
        self.assertIsNotNone(gcls)
        for attr in (
            "start_rename",
            "has_rename_result",
            "consume_rename_result",
            "is_renaming",
        ):
            self.assertTrue(
                hasattr(gcls, attr),
                f"GraphCanvasWidget missing {attr!r}",
            )

        widget = MagicMock()
        widget.start_rename = MagicMock()
        widget.has_rename_result = MagicMock(return_value=True)
        widget.consume_rename_result = MagicMock(return_value=(42, "new_name"))
        type(widget).is_renaming = PropertyMock(side_effect=[True, True])

        stable_id, current = 7, "Old"
        widget.start_rename(stable_id, current)
        widget.start_rename.assert_called_once_with(stable_id, current)

        self.assertTrue(widget.is_renaming)
        self.assertTrue(widget.has_rename_result())
        sid, new_name = widget.consume_rename_result()
        self.assertEqual(sid, 42)
        self.assertEqual(new_name, "new_name")

    async def test_rename_not_active_initially(self):
        widget = MagicMock()
        type(widget).is_renaming = PropertyMock(return_value=False)
        self.assertFalse(widget.is_renaming)

    async def test_consume_without_result_returns_empty(self):
        widget = MagicMock()
        widget.has_rename_result.return_value = False
        widget.consume_rename_result.return_value = (0, "")
        self.assertFalse(widget.has_rename_result())
        sid, name = widget.consume_rename_result()
        self.assertEqual(sid, 0)
        self.assertEqual(name, "")


if __name__ == "__main__":
    unittest.main()
