# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Headless behavior tests for catalog drag/drop feedback."""

from unittest.mock import MagicMock, call

import omni.ui

from ...scripts.config.nodes import Nodes
from ...scripts.ui.controllers.overlay.catalog_drop_overlay import CatalogDropOverlayController
from ..base import MaterialGraphTestBase


class TestCatalogDropOverlayController(MaterialGraphTestBase):
    """Keep catalog drop feedback state and visuals synchronized."""

    async def test_background_callback_receives_accept_reject_and_clear_states(self) -> None:
        """Drive host-panel background feedback without constructing overlay widgets."""

        controller = CatalogDropOverlayController()
        callback = MagicMock()
        controller.set_background_fn(callback)

        controller.show(True)
        self.assertEqual(controller.current_color, Nodes.DROP_OVERLAY_ACCEPT_ABGR)
        controller.show(False)
        self.assertEqual(controller.current_color, Nodes.DROP_OVERLAY_REJECT_ABGR)
        controller.hide()
        self.assertEqual(controller.current_color, controller.TRANSPARENT)
        self.assertEqual(
            callback.call_args_list,
            [
                call(Nodes.DROP_OVERLAY_ACCEPT_ABGR),
                call(Nodes.DROP_OVERLAY_REJECT_ABGR),
                call(None),
            ],
        )

        controller.destroy()
        self.assertIsNone(controller.frame)
        self.assertEqual(controller.current_color, controller.TRANSPARENT)

    async def test_widget_fallback_build_show_hide_and_destroy(self) -> None:
        """Exercise the real OmniUI overlay when no host background callback is available."""

        controller = CatalogDropOverlayController()
        with omni.ui.Frame():
            controller.build()

        self.assertIsNotNone(controller.frame)
        self.assertFalse(controller.frame.visible)
        controller.show(True)
        self.assertTrue(controller.frame.visible)
        self.assertEqual(controller.current_color, Nodes.DROP_OVERLAY_ACCEPT_ABGR)
        controller.hide()
        self.assertFalse(controller.frame.visible)
        self.assertEqual(controller.current_color, controller.TRANSPARENT)

        controller.destroy()
        self.assertIsNone(controller.frame)
        self.assertEqual(controller.current_color, controller.TRANSPARENT)
