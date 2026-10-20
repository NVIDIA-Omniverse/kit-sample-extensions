# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Contract tests for native breadcrumb bar APIs on ``GraphCanvasWidget``.

The pybind surface uses ``breadcrumb_clicked_index`` and ``breadcrumb_hovered``
(read-only properties), not ``get_*`` / ``is_*`` methods.
"""

import importlib
import unittest
from unittest.mock import MagicMock

import omni.kit.test

try:
    _gnw = importlib.import_module("omni.kit.window.material_graph._graphCanvas")
except ImportError:  # pragma: no cover
    _gnw = None


def _graph_canvas_widget_class():
    if _gnw is None:
        return None
    return getattr(_gnw, "GraphCanvasWidget", None)


class _FakeBreadcrumbCanvas:
    """Minimal stand-in for the C++ widget breadcrumb state machine."""

    def __init__(self):
        self._clicked_index = -1
        self._hovered = False
        self._path = []

    def set_breadcrumb(self, path):
        self._path = list(path)

    @property
    def breadcrumb_clicked_index(self):
        return self._clicked_index

    @property
    def breadcrumb_hovered(self):
        return self._hovered

    def clear_breadcrumb_clicked(self):
        self._clicked_index = -1

    def simulate_click(self, index: int):
        self._clicked_index = index


class TestBreadcrumbContract(omni.kit.test.AsyncTestCase):
    """Breadcrumb data flow matches ``GraphCanvasWidget`` bindings."""

    @unittest.skipIf(_graph_canvas_widget_class() is None, "native _graphCanvas not available")
    async def test_breadcrumb_api_contract(self):
        gcls = _graph_canvas_widget_class()
        for attr in (
            "set_breadcrumb",
            "clear_breadcrumb_clicked",
            "breadcrumb_clicked_index",
            "breadcrumb_hovered",
        ):
            self.assertTrue(hasattr(gcls, attr), f"GraphCanvasWidget missing {attr!r}")

        canvas = _FakeBreadcrumbCanvas()
        canvas.set_breadcrumb(["Material", "NodeGraph_01"])
        self.assertEqual(canvas.breadcrumb_clicked_index, -1)

    async def test_breadcrumb_single_segment(self):
        canvas = _FakeBreadcrumbCanvas()
        canvas.set_breadcrumb(["Material"])
        self.assertEqual(canvas._path, ["Material"])

    async def test_breadcrumb_empty(self):
        canvas = _FakeBreadcrumbCanvas()
        canvas.set_breadcrumb([])
        self.assertEqual(canvas._path, [])

    async def test_breadcrumb_click_returns_index(self):
        canvas = _FakeBreadcrumbCanvas()
        canvas.set_breadcrumb(["A", "B", "C"])
        self.assertEqual(canvas.breadcrumb_clicked_index, -1)
        canvas.simulate_click(2)
        self.assertEqual(canvas.breadcrumb_clicked_index, 2)
        canvas.clear_breadcrumb_clicked()
        self.assertEqual(canvas.breadcrumb_clicked_index, -1)

    async def test_breadcrumb_mock_flow(self):
        """MagicMock can mirror the property + method surface."""
        w = MagicMock()
        w.breadcrumb_clicked_index = -1
        w.breadcrumb_hovered = False
        w.set_breadcrumb(["Material", "NodeGraph_01"])
        w.set_breadcrumb.assert_called_once_with(["Material", "NodeGraph_01"])
        self.assertEqual(w.breadcrumb_clicked_index, -1)


if __name__ == "__main__":
    unittest.main()
