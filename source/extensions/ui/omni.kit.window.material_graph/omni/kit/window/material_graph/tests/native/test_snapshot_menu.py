# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Node context menu registry (no Kit runtime beyond ``carb`` for settings)."""

import uuid

import omni.kit.test

from ...scripts.api.context_menu import (
    NodeMenuItem,
    clear_node_menu_items,
    get_node_menu_items,
    register_node_menu_item,
    unregister_node_menu_item,
)


def _noop_node_cb(node_type: str, prim_path: object) -> None:
    """Valid two-arg node menu stub."""
    del node_type, prim_path


class TestSnapshotMenu(omni.kit.test.AsyncTestCase):
    """Register / query / unregister node menu items on the global registry."""

    async def setUp(self) -> None:
        clear_node_menu_items()

    async def tearDown(self) -> None:
        clear_node_menu_items()

    async def test_register_and_retrieve(self) -> None:
        label = f"mg_test_item_{uuid.uuid4().hex}"
        node_type = "TestNodeTypeMg"
        self.assertTrue(register_node_menu_item(label, _noop_node_cb, node_type))
        items = get_node_menu_items(node_type)
        self.assertTrue(any(i.label == label for i in items))
        self.assertIsInstance(items[0], NodeMenuItem)

    async def test_unregister_removes(self) -> None:
        label = f"mg_test_remove_{uuid.uuid4().hex}"
        node_type = "TestNodeTypeMgRemove"
        self.assertTrue(register_node_menu_item(label, _noop_node_cb, node_type))
        unregister_node_menu_item(label)
        items = get_node_menu_items(node_type)
        self.assertFalse(any(i.label == label for i in items))

    async def test_empty_for_unknown_type(self) -> None:
        self.assertEqual(get_node_menu_items("NonexistentNodeTypeMgXYZ"), [])
