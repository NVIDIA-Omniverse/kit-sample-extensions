# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


# Builtin imports
from functools import partial

# Nvidia imports
import omni.kit.test

# Internal imports
from omni.scene.optimizer.ui import edit_paths

# Open Source imports
from pxr import Usd


# Test classes derived from omni.kit.test.AsyncTestCase will be auto-discoverable by omni.kit.test
class Test_Edit_Paths_Panel(omni.kit.test.AsyncTestCase):
    async def test_construction(self):
        """Smoke test the class by constructing it"""
        # Constructing a EditPathsPanel then calling "accept" should return the original list of paths to the accept_fn.

        # Notes:
        #   We pass a partial to assert that the returned list is equal.
        #   We pass an in memory stage to the constructor because we do not have a valid omni.usd context.
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim("/World", "Xform")

        # An empty paths list should return no paths.
        paths = []
        accept_fn = partial(self.assertEqual, paths)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.accept()

        # A valid paths list should return the paths passed in.
        paths = ["/World", "/Test"]
        accept_fn = partial(self.assertEqual, paths)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.accept()

        # Expression strings should be accepted.
        paths = ["/World+"]
        accept_fn = partial(self.assertEqual, paths)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.accept()

        # Adding items to the data model should result in them coming back when accept is called.
        paths = ["/World"]
        expected = ["/World", "/Foo"]
        accept_fn = partial(self.assertEqual, expected)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.add_paths(["/Foo"])
        edit_paths_panel.accept()

        # Adding existing items to the data model should result in the union coming back when accept is called.
        paths = ["/World"]
        expected = ["/World", "/Foo"]
        accept_fn = partial(self.assertEqual, expected)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.add_paths(["/World", "/Foo"])
        edit_paths_panel.accept()

        # Adding empty items should result in no change when accept is called.
        paths = ["/World"]
        expected = ["/World"]
        accept_fn = partial(self.assertEqual, expected)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.add_paths([""])
        edit_paths_panel.accept()

        # Clearing the model should result in no items when accept is called.
        paths = ["/World"]
        expected = []
        accept_fn = partial(self.assertEqual, expected)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel._remove_all_paths_fn(0, 0, 0, 0)
        edit_paths_panel.accept()

        # Removing items that are in the data model should be reflected when accept is called.
        paths = ["/World", "/Foo"]
        expected = ["/World"]
        accept_fn = partial(self.assertEqual, expected)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.remove_paths(["/Foo"])
        edit_paths_panel.accept()

        # Removing all items that are in the data model should result in an empty list when accept is called.
        paths = ["/World", "/Foo"]
        expected = []
        accept_fn = partial(self.assertEqual, expected)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.remove_paths(["/World", "/Foo"])
        edit_paths_panel.accept()

        # Removing items that are not in the data model should result in no items when accept is called.
        paths = ["/World"]
        expected = ["/World"]
        accept_fn = partial(self.assertEqual, expected)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.remove_paths(["/Foo"])
        edit_paths_panel.accept()

    async def test_edit_paths_data_model(self):
        """Test various error conditions do not cause problems"""

        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim("/World", "Xform")

        # An empty paths list should return no paths.
        paths = []
        accept_fn = partial(self.assertEqual, paths)
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)

        # Test removing an invalid "item" does not raise an exception
        edit_paths_panel._data_model.remove_items(["foo"])

        # Test getting children for an invalid item does not raise an exception
        items = edit_paths_panel._data_model.get_item_children("foo")
        self.assertListEqual(items, [])

        # Check removing "None" doesn't raise an exception
        edit_paths_panel._delegate.remove_item(None, None)

    async def test_edit_paths_select_in_stage(self):
        """Test selection"""

        # Need to create a prim
        self.assertTrue(omni.usd.get_context().new_stage())
        stage = omni.usd.get_context().get_stage()
        stage.DefinePrim("/World", "Xform")
        stage.DefinePrim("/World/Mesh", "Mesh")

        # Assert nothing currently selected
        selection = omni.usd.get_context().get_selection()
        selected = selection.get_selected_prim_paths()
        self.assertListEqual(selected, [])

        # Add to path panel
        paths = []
        accept_fn = None
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)

        # Assert nothing changes
        edit_paths_panel.select_paths(0, 0, 0, 0)

        # First assert nothing gets selected, because it is empty
        selected = selection.get_selected_prim_paths()
        self.assertListEqual(selected, [])

        edit_paths_panel.add_paths(["/World/Mesh"])

        # Force selection change by selecting all items
        items = edit_paths_panel._data_model.get_item_children(None)
        edit_paths_panel.selection_changed(items)

        # Select via paths panel
        x = 0
        y = 0
        i = 0
        b = 0
        edit_paths_panel.select_paths(x, y, i, b)

        # Assert path now selected in stage
        selected = selection.get_selected_prim_paths()
        self.assertListEqual(selected, ["/World/Mesh"])

    async def test_edit_paths_add_from_selection(self):
        """Test selection"""

        # Need to create a prim
        self.assertTrue(omni.usd.get_context().new_stage())
        stage = omni.usd.get_context().get_stage()
        stage.DefinePrim("/World", "Xform")
        stage.DefinePrim("/World/Mesh", "Mesh")

        selection = omni.usd.get_context().get_selection()
        selected = selection.get_selected_prim_paths()
        self.assertListEqual(selected, [])

        # Select the path
        selection.set_selected_prim_paths(["/World/Mesh"], True)

        # Create panel
        paths = []
        accept_fn = None
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)

        # Assert panel is empty
        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 0)

        # Add from stage selection
        x = 0
        y = 0
        i = 0
        b = 0
        edit_paths_panel.add_paths_from_selection(x, y, i, b)

        # Assert there is now a path
        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 1)

        # Select the other path
        selection.set_selected_prim_paths(["/World", "/World/Mesh"], True)
        edit_paths_panel.add_paths_from_selection(x, y, i, b)
        edit_paths_panel._selection = ["/World", "/World/Mesh"]
        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 2)

        edit_paths_panel._remove_path_item_fn("/World")
        edit_paths_panel.clear_paths()

        # Assert now empty
        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 0)

    async def test_edit_paths_add_from_selection_empty(self):
        """Test adding empty selection does nothing"""

        # Need to create a prim
        self.assertTrue(omni.usd.get_context().new_stage())
        stage = omni.usd.get_context().get_stage()
        stage.DefinePrim("/World", "Xform")
        stage.DefinePrim("/World/Mesh", "Mesh")

        selection = omni.usd.get_context().get_selection()
        selected = selection.get_selected_prim_paths()
        self.assertListEqual(selected, [])

        paths = []
        accept_fn = None
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)
        edit_paths_panel.add_paths_from_selection(0, 0, 0, 0)

        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 0)

    async def test_edit_paths_reject(self):
        """Test closing/rejecting the panel"""

        # Create panel
        paths = []
        accept_fn = None
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn)
        self.assertTrue(edit_paths_panel.window.visible)

        edit_paths_panel.reject()

        self.assertFalse(edit_paths_panel.window.visible)

    async def test_edit_paths_drop(self):
        """Test the drop filter"""

        # Create panel
        paths = []
        accept_fn = None
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn)

        self.assertTrue(edit_paths_panel.drop_accept("/World"))
        self.assertTrue(edit_paths_panel.drop_accept("/World/Foo"))

        self.assertFalse(edit_paths_panel.drop_accept("123456"))
        self.assertFalse(edit_paths_panel.drop_accept("test string"))

    async def test_edit_paths_add_from_selection_drop(self):
        """Test selection"""

        # Need to create a prim
        self.assertTrue(omni.usd.get_context().new_stage())
        stage = omni.usd.get_context().get_stage()
        stage.DefinePrim("/World", "Xform")
        stage.DefinePrim("/World/Mesh1", "Mesh")
        stage.DefinePrim("/World/Mesh2", "Mesh")
        stage.DefinePrim("/World/Mesh3", "Mesh")
        stage.DefinePrim("/World/Mesh4", "Mesh")

        selection = omni.usd.get_context().get_selection()
        selected = selection.get_selected_prim_paths()
        self.assertListEqual(selected, [])

        # Select the paths
        selection.set_selected_prim_paths(["/World/Mesh1", "/World/Mesh2"], True)

        # Create panel
        paths = []
        accept_fn = None
        edit_paths_panel = edit_paths.EditPathsPanel(paths, accept_fn, stage=stage)

        class Event:
            def __init__(self, mime_data):
                self.mime_data = mime_data

        # Assert panel is empty
        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 0)

        # "drop" one item that is in the selection
        edit_paths_panel.drop(Event("/World/Mesh1"))

        # Assert that BOTH things are selected, as one of them was in the omni
        # selection
        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 2)

        # Now drop one that isn't in the selection
        edit_paths_panel.drop(Event("/World/Mesh3"))

        # Only one more should be selected as it wasn't part of the omni selection
        self.assertEqual(len(edit_paths_panel._data_model.get_item_children(None)), 3)
