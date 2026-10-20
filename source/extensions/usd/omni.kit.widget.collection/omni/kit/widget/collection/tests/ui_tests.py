import unittest

import omni.kit.commands
import omni.kit.test
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.kit.core.collection.usd import CollectionHelper
from omni.kit.test_suite.helpers import arrange_windows
from omni.kit.widget.collection import context_menu
from omni.kit.window.collection.window import CollectionWindow


async def select_prims(paths, usd_context=omni.usd.get_context()):
    usd_context.get_selection().set_selected_prim_paths(paths, True)
    await ui_test.human_delay()


class TestCollectionWidget(omni.kit.test.AsyncTestCase):
    async def setUp(self) -> None:
        # create new stage
        self.window = CollectionWindow()
        usd_context = omni.usd.get_context()
        usd_context.new_stage()
        # show window
        await ui_test.human_delay(10)
        # make sure windows don't overlap
        await arrange_windows()
        self.window.position_x = 0
        self.window.position_y = 0

    async def tearDown(self):
        self.window.destroy()
        self.window = None
        await ui_test.human_delay(10)

    async def get_stage_tree(self):
        stage_window = ui_test.find("Stage")
        await stage_window.focus()
        await ui_test.human_delay(10)

        ret = omni.kit.commands.execute("CreatePrim", prim_type="Cone", attributes={})
        ret = omni.kit.commands.execute("CreatePrim", prim_type="Sphere", attributes={})

        await select_prims(["/World/Cube", "/World/Sphere"])
        stage_tree = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")

        stage_tree.widget.set_expanded(None, True, True)
        return stage_tree

    async def test_stage_collection_create(self):
        """
        Create a collection with right click context menu on the stage widget
        """
        stage_tree = await self.get_stage_tree()
        src_item = stage_tree.find("**/StringField[*].model._prim_path=='/Cone'")

        # This should create 2 collections under the 2 prims
        await ui_test.emulate_mouse_move_and_click(src_item.center, right_click=True)
        await ui_test.human_delay(20)
        await ui_test.select_context_menu("Create/Collection")

        # Check that the 2 collections were created..
        self.assertTrue(CollectionHelper.is_valid_collection_path("/Cone.collection:collection"))
        self.assertTrue(CollectionHelper.is_valid_collection_path("/Sphere.collection:collection"))

    async def test_drag_additional_items_to_collection(self):
        """
        drag a prim into a collection (default collection under a light) from stage widget
        to
        """

        stage_tree = await self.get_stage_tree()

        ret = omni.kit.commands.execute("CreatePrim", prim_type="DistantLight", attributes={})

        await select_prims(["/World/Cube", "/World/Sphere"])
        self.assertTrue(isinstance(stage_tree.widget, omni.ui.TreeView))
        stage_tree.widget.set_expanded(None, True, True)

        await ui_test.human_delay()
        # Get the cone
        src_item = stage_tree.find("**/StringField[*].model._prim_path=='/Cone'")
        self.assertTrue(src_item)

        src_item_center = src_item.center

        await ui_test.human_delay()

        coll_window = ui_test.find("Collection")
        self.assertTrue(coll_window)
        collection_tree = coll_window.find("Frame/Frame[0]/*/*/*/TreeView[0]")
        self.assertTrue(collection_tree)
        collection_tree.widget.set_expanded(None, True, True)
        await coll_window.focus()
        await ui_test.human_delay(100)

        default_light_light_link = collection_tree.find("**/Label[*].text=='collection:lightLink'")
        self.assertTrue(default_light_light_link)

        await ui_test.human_delay()
        light_link_center = default_light_light_link.center

        default_light_coll = CollectionHelper("/DistantLight.collection:lightLink")
        self.assertTrue(default_light_coll.is_valid())
        include_root_attr = default_light_coll.get_collection_api().GetIncludeRootAttr()
        include_root_attr.Set(False)

        await ui_test.emulate_mouse_drag_and_drop(src_item_center, light_link_center)

        collection_elements = default_light_coll.get_members()
        self.assertGreater(len(collection_elements), 0)

    async def test_duplicate(self):
        """
        Duplicate a collection via context menu
        """

        ret = omni.kit.commands.execute("CreatePrim", prim_type="DistantLight", attributes={})
        await ui_test.human_delay(10)  # This is 100% necessary
        coll_window = ui_test.find("Collection")
        self.assertTrue(coll_window)
        collection_tree = coll_window.find("Frame/Frame[0]/*/*/*/TreeView[0]")
        self.assertTrue(collection_tree)
        collection_tree.widget.set_expanded(None, True, True)
        await coll_window.focus()
        await ui_test.human_delay(100)

        default_light_light_link = collection_tree.find("**/Label[*].text=='collection:lightLink'")
        self.assertTrue(default_light_light_link)

        await ui_test.emulate_mouse_move_and_click(default_light_light_link.center, right_click=True)
        await ui_test.human_delay(20)
        await ui_test.select_context_menu("Duplicate")
        await ui_test.human_delay(20)

        self.assertTrue(CollectionHelper.is_valid_collection_path("/DistantLight.collection:lightLink_01"))

    async def test_rename(self):
        """
        Rename a collection via context menu
        """

        ret = omni.kit.commands.execute("CreatePrim", prim_type="DistantLight", attributes={})
        await ui_test.human_delay(20)

        coll_window = ui_test.find("Collection")
        self.assertTrue(coll_window)
        collection_tree = coll_window.find("Frame/Frame[0]/*/*/*/TreeView[0]")
        self.assertTrue(collection_tree)
        collection_tree.widget.set_expanded(None, True, True)
        await coll_window.focus()
        await ui_test.human_delay(100)

        default_light_light_link = collection_tree.find("**/Label[*].text=='collection:lightLink'")
        self.assertTrue(default_light_light_link)

        await ui_test.human_delay(20)

        helper = CollectionHelper("/DistantLight.collection:lightLink")
        self.assertTrue(helper.is_valid())

        window_name = "Rename " + helper.get_collection_name() + "###context_menu_rename"

        await ui_test.emulate_mouse_move_and_click(default_light_light_link.center, right_click=True)
        await ui_test.human_delay(20)
        await ui_test.select_context_menu("Rename")
        await ui_test.emulate_char_press("renamed_collection")
        await ui_test.human_delay(20)

        rename_window = ui_test.find(window_name)
        self.assertTrue(rename_window)
        button = rename_window.find("**/Button[*].text=='Ok'")
        self.assertTrue(button)
        await ui_test.emulate_mouse_move_and_click(button.center)

        await ui_test.human_delay(20)

        helper = CollectionHelper("/DistantLight.collection:renamed_collection")
        self.assertTrue(helper.is_valid())

    async def test_create(self):
        """
        Create a collection via context menu
        """

        ret = omni.kit.commands.execute("CreatePrim", prim_type="DistantLight", attributes={})
        await ui_test.human_delay(20)

        coll_window = ui_test.find("Collection")
        self.assertTrue(coll_window)
        collection_tree = coll_window.find("Frame/Frame[0]/*/*/*/TreeView[0]")
        self.assertTrue(collection_tree)
        collection_tree.widget.set_expanded(None, True, True)
        await coll_window.focus()
        await ui_test.human_delay(100)

        distant_light_prim = collection_tree.find("**/Label[*].text=='DistantLight'")
        await ui_test.human_delay(20)
        self.assertTrue(distant_light_prim)

        await ui_test.emulate_mouse_move_and_click(distant_light_prim.center, right_click=True)
        await ui_test.human_delay(20)
        await ui_test.select_context_menu("Create Collection")

        helper = CollectionHelper("/DistantLight.collection:collection")
        self.assertTrue(helper.is_valid())
