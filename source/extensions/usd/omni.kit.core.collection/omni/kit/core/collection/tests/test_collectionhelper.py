## Copyright (c) 2018-2019, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import os

import omni.kit.test
from pxr import Sdf, Usd

from .. import CollectionHelper


class TestCollectionHelper(omni.kit.test.AsyncTestCase):

    # These 2 scenes are the same, I just can't work out how to clear the stage after opening it once.
    test_path1 = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Test.usda")
    test_path2 = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Test2.usda")

    async def test_multi_level_prim_expansion(self):
        stage1 = Usd.Stage.Open(self.test_path1)
        helper = CollectionHelper("/CollectionTest.collection:allGeom", stage1)
        kids = helper.get_members()
        self.assertTrue(len(kids) == 1)
        self.assertTrue(kids[0] == Sdf.Path("/CollectionTest/Geom"))

        kids = helper.get_members(filter="/CollectionTest/Geom")
        self.assertTrue(len(kids) == 2)
        # We probably can't rely on this ordering...
        self.assertTrue(Sdf.Path("/CollectionTest/Geom/Box") in kids)
        self.assertTrue(Sdf.Path("/CollectionTest/Geom/Shapes") in kids)

        kids = helper.get_members(filter="/CollectionTest/Geom/Shapes")

    async def test_explicit_properties(self):
        stage1 = Usd.Stage.Open(self.test_path1)
        helper = CollectionHelper("/CollectionTest.collection:hasRelationships", stage1)
        kids = helper.get_members()
        self.assertTrue(len(kids) == 2)
        # We probably can't rely on this ordering...
        self.assertTrue(Sdf.Path("/CollectionTest/Geom/Shapes/Cube.sphere") in kids)
        self.assertTrue(Sdf.Path("/CollectionTest/Geom/Shapes/Sphere.cube") in kids)

        kids = helper.get_members(filter="/CollectionTest/Geom/Shapes/Sphere.cube")
        # Props should have no children
        self.assertTrue(len(kids) == 0)

    async def test_properties_from_expandprops(self):
        stage1 = Usd.Stage.Open(self.test_path1)
        helper = CollectionHelper("/CollectionTest.collection:allGeomProperties", stage1)
        collection_api = helper.get_collection_api()

        # just one immediate prim child
        kids = helper.get_members()
        self.assertTrue(len(kids) == 1)
        self.assertTrue(kids[0] == Sdf.Path("/CollectionTest/Geom"))

        kids = helper.get_members(filter="/CollectionTest/Geom")
        # under /Geom we should have some props and 2 prims
        # Props should have no children

        self.assertTrue(Sdf.Path("/CollectionTest/Geom/Box") in kids)
        self.assertTrue(Sdf.Path("/CollectionTest/Geom/Shapes") in kids)
        self.assertTrue(Sdf.Path("/CollectionTest/Geom/Shapes") in kids)

        self.assertTrue(len(kids) == 2, f"actually {len(kids)} kids {kids}")

        kid_list = [Sdf.Path("/CollectionTest/Geom/Box"), Sdf.Path("/CollectionTest/Geom/Shapes")]
        for kid in kid_list:
            self.assertTrue(kid in kids)

        kids = helper.get_members(filter="/CollectionTest/Geom/Box")
        self.assertTrue(len(kids) == 4, "actually %s" % (len(kids)))
        kid_list = [
            Sdf.Path("/CollectionTest/Geom/Box.proxyPrim"),
            Sdf.Path("/CollectionTest/Geom/Box.purpose"),
            Sdf.Path("/CollectionTest/Geom/Box.visibility"),
            Sdf.Path("/CollectionTest/Geom/Box.xformOpOrder"),
        ]
        for kid in kid_list:
            self.assertTrue(kid in kids)

    async def test_syntax_validation(self):
        valid = CollectionHelper.is_valid_collection_path(Sdf.Path("/CollectionTest/Geom.collection:blah"))
        self.assertTrue(valid)
        valid = CollectionHelper.is_valid_collection_path(Sdf.Path("/CollectionTest/Geom.collection"))
        self.assertFalse(valid)
        # valid = CollectionHelper.is_valid_collection_path(Sdf.Path("/CollectionTest/Geom.collection:blah:expansionState"))
        # self.assertFalse(valid)

        valid = CollectionHelper.is_collection_property_path(
            Sdf.Path("/CollectionTest/Geom.collection:blah:expansionState")
        )
        self.assertFalse(valid)
        valid = CollectionHelper.is_collection_property_path(
            Sdf.Path("/CollectionTest/Geom.collection:blah:expansionRule")
        )
        self.assertTrue(valid)

    async def test_validation(self):
        stage1 = Usd.Stage.CreateInMemory()
        test_prim = stage1.DefinePrim("/Test")

        # USD >=21.02 uses Apply, earlier uses ApplyCollection
        if hasattr(Usd.CollectionAPI, "Apply"):
            Usd.CollectionAPI.Apply(test_prim, "test_collection")
        else:
            Usd.CollectionAPI.ApplyCollection(test_prim, "test_collection")

        path = test_prim.GetPath().pathString + CollectionHelper.prop_dotted_prefix + "test_collection"
        coll_helper = CollectionHelper(path, stage1)
        self.assertTrue(coll_helper.is_valid())

        path = "/Blah" + CollectionHelper.prop_dotted_prefix + "test_collection"
        coll_helper = CollectionHelper(path, stage1)
        self.assertFalse(coll_helper.is_valid())

        path = test_prim.GetPath().pathString + CollectionHelper.prop_dotted_prefix + "test_collectionX"
        coll_helper = CollectionHelper(path, stage1)
        self.assertFalse(coll_helper.is_valid())

    async def test_get_collection_api(self):
        stage1 = Usd.Stage.CreateInMemory()
        test_prim = stage1.DefinePrim("/Test")

        # USD >=21.02 uses Apply, earlier uses ApplyCollection
        if hasattr(Usd.CollectionAPI, "Apply"):
            Usd.CollectionAPI.Apply(test_prim, "test_collection")
        else:
            Usd.CollectionAPI.ApplyCollection(test_prim, "test_collection")

        path = test_prim.GetPath().pathString + CollectionHelper.prop_dotted_prefix + "test_collection"
        coll_helper = CollectionHelper(path, stage1)
        api = coll_helper.get_collection_api()
        self.assertTrue(api.Validate())

    async def test_duplicate(self):
        stage1 = Usd.Stage.Open(self.test_path2)
        helper = CollectionHelper("/CollectionTest/Geom.collection:allGeom", stage1)
        status = helper.duplicate_with_name("jim_morrison")
        self.assertTrue(status)

        # We should detect a duplicate name and exit early
        status = helper.duplicate_with_name("jim_morrison")
        self.assertTrue(status == "")

        status = helper.duplicate_with_name("jim_morrison", generate_valid_name=True)
        self.assertTrue(status == "/CollectionTest/Geom.collection:jim_morrison_01")

        status = helper.duplicate_with_name("jim_morrison", generate_valid_name=True)
        self.assertTrue(status == "/CollectionTest/Geom.collection:jim_morrison_02")
