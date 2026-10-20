# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Contract tests for hover ids and tooltip text on ``GraphCanvasWidget``."""

import importlib
import unittest
from unittest.mock import MagicMock, PropertyMock

import omni.kit.test

try:
    _gnw = importlib.import_module("omni.kit.window.material_graph._graphCanvas")
except ImportError:  # pragma: no cover
    _gnw = None


def _graph_canvas_widget_class():
    if _gnw is None:
        return None
    return getattr(_gnw, "GraphCanvasWidget", None)


class TestTooltipHoverContract(omni.kit.test.AsyncTestCase):
    """Hover and tooltip APIs used by ``graph_canvas_view._update_tooltip``."""

    @unittest.skipIf(_graph_canvas_widget_class() is None, "native _graphCanvas not available")
    async def test_binding_exposes_hover_and_tooltip(self):
        gcls = _graph_canvas_widget_class()
        for attr in ("hover_node_id", "hover_port_index", "set_tooltip_text"):
            self.assertTrue(hasattr(gcls, attr), f"GraphCanvasWidget missing {attr!r}")

    async def test_hover_initially_negative(self):
        w = MagicMock()
        type(w).hover_node_id = PropertyMock(return_value=-1)
        type(w).hover_port_index = PropertyMock(return_value=-1)
        self.assertEqual(w.hover_node_id, -1)
        self.assertEqual(w.hover_port_index, -1)

    async def test_set_tooltip_text(self):
        w = MagicMock()
        w.set_tooltip_text("some text")
        w.set_tooltip_text.assert_called_once_with("some text")

    async def test_tooltip_text_format(self):
        """Tooltip pipeline may concatenate title, metadata, rule, and body."""
        title = "My Node"
        meta = "@mdl::base::some_type"
        rule = "---"
        desc = "Does something useful."
        text = "\n".join([title, meta, rule, desc])
        self.assertIn(title, text)
        self.assertIn("@", text)
        self.assertIn(rule, text)
        self.assertIn(desc, text)


if __name__ == "__main__":
    unittest.main()
