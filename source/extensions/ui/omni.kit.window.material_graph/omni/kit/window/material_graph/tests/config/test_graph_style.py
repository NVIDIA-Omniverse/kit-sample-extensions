# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Unit tests for ``GraphStyle`` → ``StyleConfig`` dict mapping (no Kit runtime)."""

from unittest.mock import patch

import omni.kit.test

from ...scripts.config.graph_style import GraphStyle


def _expected_style_dict_keys() -> set[str]:
    """Keys derived from ``GraphStyle`` UPPER_SNAKE constants (must match ``to_dict``)."""
    keys: set[str] = set()
    for name in dir(GraphStyle):
        if not name.isupper():
            continue
        keys.add("_".join(part.lower() for part in name.split("_")))
    return keys


class TestGraphStyle(omni.kit.test.AsyncTestCase):
    """``GraphStyle`` supplies defaults and a flat dict for the native canvas."""

    async def test_defaults_are_set(self) -> None:
        """Key style defaults match the native renderer contract."""
        self.assertEqual(GraphStyle.HEADER_HEIGHT, 24.0)
        self.assertEqual(GraphStyle.LOD_THRESHOLD_3, 0.18)
        self.assertEqual(GraphStyle.BASE_FONT_SIZE, 14.0)

    async def test_to_dict_returns_all_keys(self) -> None:
        """``to_dict`` exposes every style constant under stable snake_case keys."""
        style = GraphStyle.to_dict()
        self.assertIsInstance(style, dict)
        self.assertEqual(set(style.keys()), _expected_style_dict_keys())

    async def test_to_dict_values_match_attributes(self) -> None:
        """Each dict entry matches the corresponding class constant."""
        for key, value in GraphStyle.to_dict().items():
            const = "_".join(part.upper() for part in key.split("_"))
            self.assertEqual(value, getattr(GraphStyle, const))

    async def test_custom_override(self) -> None:
        """Patched constants flow through ``to_dict``."""
        with patch.object(GraphStyle, "HEADER_HEIGHT", 42.0):
            style = GraphStyle.to_dict()
        self.assertEqual(style["header_height"], 42.0)
