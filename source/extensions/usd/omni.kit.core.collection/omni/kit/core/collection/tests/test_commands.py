## Copyright (c) 2018-2019, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from unittest.case import skip

import omni.kit.test
import omni.kit.usd.layers
import omni.usd
from pxr import Sdf, UsdGeom

from .. import CollectionHelper


class TestCommands(omni.kit.test.AsyncTestCase):
    async def setUp(self):

        await omni.usd.get_context().new_stage_async()
        usd_context = omni.usd.get_context()
        self.selection = usd_context.get_selection()
        self.stage = usd_context.get_stage()

        root_ref_cube = UsdGeom.Sphere.Define(self.stage, "/Sphere")
        root_ref_cube = UsdGeom.Cube.Define(self.stage, "/Cube")
        UsdGeom.Cube.Define(self.stage, "/Cube/Cube2")
        UsdGeom.Cube.Define(self.stage, "/Sphere/Sphere2")
        UsdGeom.Cube.Define(self.stage, "/Sphere/Sphere2/Sphere3")
        prim = self.stage.GetPrimAtPath("/Sphere/Sphere2/Sphere3")
        prim.CreateAttribute("foo", Sdf.ValueTypeNames.Float)

    async def test_create_collection_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        self.assertTrue(CollectionHelper(collection_path).is_valid())

        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere")
        collection_path = "/Sphere.collection:collection"
        self.assertTrue(CollectionHelper(collection_path).is_valid())

        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere")
        collection_path = "/Sphere.collection:collection_01"
        self.assertTrue(CollectionHelper(collection_path).is_valid())

    async def test_undo_create_collection_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        self.assertTrue(CollectionHelper(collection_path).is_valid())
        omni.kit.undo.undo()
        self.assertFalse(CollectionHelper(collection_path).is_valid())
        prim = self.stage.GetPrimAtPath("/Sphere")
        props = prim.GetAuthoredPropertiesInNamespace(CollectionHelper.prop_prefix + "giorgio")
        self.assertTrue(len(props) == 0)

    async def test_undo_create_collection_command_wuth_changed_edit_target(self):
        root_layer = self.stage.GetRootLayer()
        omni.kit.commands.execute(
            "CreateSublayer",
            layer_identifier=root_layer.identifier,
            sublayer_position=0,
            new_layer_path="",
            transfer_root_content=False,
            create_or_insert=True,
        )
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        self.assertTrue(CollectionHelper(collection_path).is_valid())

        sublayer_paths = root_layer.subLayerPaths
        self.assertTrue(len(sublayer_paths) == 1)
        sublayer1 = Sdf.Layer.FindOrOpen(sublayer_paths[0])
        self.stage.SetEditTarget(sublayer1)
        omni.kit.undo.undo()
        self.assertFalse(CollectionHelper(collection_path).is_valid())
        prim = self.stage.GetPrimAtPath("/Sphere")
        props = prim.GetAuthoredPropertiesInNamespace(CollectionHelper.prop_prefix + "giorgio")
        self.assertTrue(len(props) == 0)

    async def test_add_to_collection_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 1)
        res = omni.kit.undo.undo()
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 0)

    async def test_undo_add_to_collection_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        res = omni.kit.undo.undo()
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 0)

    async def test_remove_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        omni.kit.commands.execute(
            "RemoveItemFromCollection", prim_or_prop_path="/Cube/Cube2", collection_path=collection_path
        )
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 0)

    async def test_undo_remove_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        omni.kit.commands.execute(
            "RemoveItemFromCollection", prim_or_prop_path="/Cube/Cube2", collection_path=collection_path
        )
        res = omni.kit.undo.undo()
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 1)

    async def test_duplicate_command(self):
        # TODO test attributes get copied also
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("DuplicateCollection", collection_path=collection_path, new_collection_name="sergio")
        new_collection_path = "/Sphere.collection:sergio"
        self.assertTrue(CollectionHelper(new_collection_path).is_valid())

    async def test_undo_duplicate_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("DuplicateCollection", collection_path=collection_path, new_collection_name="sergio")
        new_collection_path = "/Sphere.collection:sergio"
        res = omni.kit.undo.undo()
        self.assertFalse(CollectionHelper(new_collection_path).is_valid())

    async def test_duplicate_command_generated_name(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("DuplicateCollection", collection_path=collection_path)
        new_collection_path = "/Sphere.collection:giorgio_01"
        self.assertTrue(CollectionHelper(new_collection_path).is_valid())

        # Make sure next path is created properly.
        omni.kit.commands.execute("DuplicateCollection", collection_path=new_collection_path)
        new_collection_path = "/Sphere.collection:giorgio_02"
        self.assertTrue(CollectionHelper(new_collection_path).is_valid())

        # Now dupe the original
        omni.kit.commands.execute("DuplicateCollection", collection_path=collection_path)
        new_collection_path = "/Sphere.collection:giorgio_03"
        self.assertTrue(CollectionHelper(new_collection_path).is_valid())

    async def test_delete_command(self):
        # TODO test attributes get deleted also
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("DeleteCollection", collection_path=collection_path)
        self.assertFalse(CollectionHelper(collection_path).is_valid())

    async def test_undo_delete_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("DeleteCollection", collection_path=collection_path)
        self.assertFalse(CollectionHelper(collection_path).is_valid())
        res = omni.kit.undo.undo()
        self.assertTrue(CollectionHelper(collection_path).is_valid())

    async def test_rename_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute(
            "RenameCollection", old_collection_path=collection_path, new_collection_name="giovanni"
        )
        new_new_collection_path = "/Sphere.collection:giovanni"
        self.assertTrue(CollectionHelper(new_new_collection_path).is_valid())

    async def test_undo_rename_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute(
            "RenameCollection", old_collection_path=collection_path, new_collection_name="giovanni"
        )
        res = omni.kit.undo.undo()
        self.assertTrue(CollectionHelper("/Sphere.collection:giorgio").is_valid())
        self.assertFalse(CollectionHelper("/Sphere.collection:giovanni").is_valid())

    async def test_clear_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        omni.kit.commands.execute("ClearCollection", collection_path=collection_path)
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 0)

    async def test_undo_clear_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        omni.kit.commands.execute("ClearCollection", collection_path=collection_path)
        res = omni.kit.undo.undo()
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 1)

    async def test_block_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        # print (self.stage.ExportToString())
        omni.kit.commands.execute("BlockCollection", collection_path=collection_path)
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 0)

    async def test_undo_block_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Cube/Cube2", collection_path=collection_path)
        omni.kit.commands.execute("BlockCollection", collection_path=collection_path)
        res = omni.kit.undo.undo()
        kids = CollectionHelper(collection_path).get_members()
        self.assertTrue(len(kids) == 1)

    async def test_set_expansion_rule_command(self):
        # TODO Looks like we can't create a collection at the root...oh oh
        # omni.kit.commands.execute("CreateCollection", prim_path="/", collection_name="giorgio")

        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Sphere/Sphere2", collection_path=collection_path)
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=collection_path, expansion_rule="explicitOnly"
        )
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 1)
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=collection_path, expansion_rule="expandPrims"
        )
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 2, "actually is %s" % (len(kids)))
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=collection_path, expansion_rule="expandPrimsAndProperties"
        )
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 23, "actually is %s" % (len(kids)))

    async def test_undo_set_expansion_rule_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"

        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Sphere/Sphere2", collection_path=collection_path)
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=collection_path, expansion_rule="explicitOnly"
        )
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=collection_path, expansion_rule="expandPrims"
        )
        res = omni.kit.undo.undo()
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 1, "actually is %s" % (len(kids)))

    async def test_exclude_item_from_collection_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Sphere", collection_path=collection_path)
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=collection_path, expansion_rule="expandPrims"
        )
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 3, "actually is %s" % (len(kids)))
        omni.kit.commands.execute(
            "ExcludeItemFromCollection", prim_or_prop_path="/Sphere/Sphere2/Sphere3", collection_path=collection_path
        )
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 2, "actually is %s" % (len(kids)))
        omni.kit.commands.execute(
            "ExcludeItemFromCollection", prim_or_prop_path="/Sphere/Sphere2", collection_path=collection_path
        )
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 1, "actually is %s" % (len(kids)))

    async def test_undo_exclude_item_from_collection_command(self):
        omni.kit.commands.execute("CreateCollection", prim_path="/Sphere", collection_name="giorgio")
        collection_path = "/Sphere.collection:giorgio"
        omni.kit.commands.execute("AddItemToCollection", path_to_add="/Sphere", collection_path=collection_path)
        omni.kit.commands.execute(
            "SetCollectionExpansionRule", collection_path=collection_path, expansion_rule="expandPrims"
        )
        omni.kit.commands.execute(
            "ExcludeItemFromCollection", prim_or_prop_path="/Sphere/Sphere2/Sphere3", collection_path=collection_path
        )
        res = omni.kit.undo.undo()
        kids = CollectionHelper(collection_path).get_all_members()
        self.assertTrue(len(kids) == 3, "actually is %s" % (len(kids)))
