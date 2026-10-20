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
from pxr import Sdf, Usd, UsdGeom

from .. import model


class TestModel(omni.kit.test.AsyncTestCase):

    test_path1 = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Test.usda")

    async def setUp(self):
        """Before running each test"""

        await omni.usd.get_context().new_stage_async()
        usd_context = omni.usd.get_context()
        self.selection = usd_context.get_selection()
        await usd_context.open_stage_async(self.test_path1)

    def recurse_model_items(self, model, item, cnt=0, do_print=False):
        kids = model.get_item_children(item)
        for k in kids:
            if do_print:
                print("\t".join(["" for x in range(cnt)]), "kid", k)
            self.recurse_model_items(model, k, cnt=cnt + 1)
        self.kid_list.extend(kids)

    async def __wait(self, n_frames=3):
        import omni.kit.app

        app = omni.kit.app.get_app()

        for _ in range(n_frames):
            await app.next_update_async()

    async def test_basic_model(self):
        import omni.kit.app
        import omni.kit.commands
        import omni.usd as ou

        stage = ou.get_context().get_stage()
        my_model = model.CollectionModel(stage)

        self.kid_list = []

        # ------------
        # Store the starting model item count
        self.recurse_model_items(my_model, None)  # Required.
        # TODO: fix this test, we build from leaf to root now, so the count is not correct now
        start_len = len(self.kid_list)

        # ------------
        # Capture the prims at the collection path after verifying the path is found in the model
        input_path = Sdf.Path("/CollectionTest.collection:allGeom")
        self.assertTrue(my_model.find(input_path).path == input_path)
        prim_list = stage.GetPropertyAtPath(f"{input_path}:includes").GetTargets()
        self.assertTrue(len(prim_list) == 1)  # Root

        # ------------
        # Reset kid list, Delete a collection entirely
        self.kid_list = []
        omni.kit.commands.execute("DeleteCollection", collection_path=input_path)
        await self.__wait(3)

        self.recurse_model_items(my_model, None)  # Required
        kid_cnt = len(self.kid_list)

        self.assertLess(kid_cnt, start_len)
        self.assertTrue(kid_cnt != 0, "kit cnt is %s" % (kid_cnt))  # Root + children
        self.assertFalse(stage.GetPropertyAtPath(input_path))  # Collection no longer exists

        # ------------
        # Recreate the collection, Rename and check,  Add the prims back, Test Item count
        _, pth = omni.kit.commands.execute("CreateCollection", prim_path="/CollectionTest")
        await self.__wait(3)

        self.recurse_model_items(my_model, None)  # Required
        self.assertIsNotNone(my_model.find(pth))

        # ------------
        # Rename the collection
        _, pth = omni.kit.commands.execute(
            "RenameCollection",
            old_collection_path=pth,
            new_collection_name="allGeom",
        )
        await self.__wait(3)

        self.recurse_model_items(my_model, None)  # Required
        self.assertTrue(my_model.find(pth).path == pth)

        # ------------
        # Add Original Item back to the collection, total children should reflect start count.
        for prim_path in prim_list:
            omni.kit.commands.execute("AddItemToCollection", path_to_add=prim_path, collection_path=pth)
        await self.__wait(13)

        self.kid_list = []
        self.recurse_model_items(my_model, None)
        kid_cnt1 = len(self.kid_list)
        self.assertTrue(stage.GetPropertyAtPath(f"{pth}:includes"))
        self.assertTrue(kid_cnt1 == start_len, "kit cnt1 is %s" % (kid_cnt1))
        # ------------
        # Test to see what happens when we delete a prim with a collection
        # Removes a prim with collections. Check to see if the model has the corrected amount
        self.kid_list = []
        stage.RemovePrim("/CollectionTest/Geom/Shapes")
        await self.__wait(3)

        self.recurse_model_items(my_model, None, do_print=True)
        kid_cnt = len(self.kid_list)
        self.assertTrue(kid_cnt < kid_cnt1, "kid cnt is %s" % (kid_cnt))

    async def test_drag_and_drop(self):
        """
        Simulate the drag and drop of three new prims in the stage to the allGeom collection.
        """
        import omni.usd as ou

        stage = ou.get_context().get_stage()
        my_model = model.CollectionModel(stage)

        # Define specific test prims
        prim_a = stage.DefinePrim("/test1", "Xform")
        prim_b = stage.DefinePrim("/test2", "Xform")

        await self.__wait(3)

        self.kid_list = []
        # ------------
        # Store the starting model item count
        self.recurse_model_items(my_model, None)  # Required.
        start_len = len(self.kid_list)
        kid_cnt = len(self.kid_list)
        self.assertTrue(kid_cnt == start_len, "kid cnt is %s" % (kid_cnt))

        expected_mime_data = "\n".join([prim_a.GetPrimPath().pathString, prim_b.GetPrimPath().pathString])
        target = my_model.find(Sdf.Path("/CollectionTest.collection:allGeom"))
        self.assertTrue(my_model.drop_accepted(target, expected_mime_data))

        my_model.drop(target, expected_mime_data)  # Drop the new data on the target collection.

        await self.__wait(3)

        self.kid_list = []
        self.recurse_model_items(my_model, None)
        kid_cnt = len(self.kid_list)
        self.assertTrue(kid_cnt == start_len + 2, "kid cnt is %s" % (kid_cnt))
        my_model.destroy()
        del my_model
