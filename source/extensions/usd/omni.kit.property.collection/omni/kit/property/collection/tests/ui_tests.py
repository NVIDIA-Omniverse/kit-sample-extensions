import omni.kit.commands
import omni.kit.test
import omni.usd
from omni.kit import ui_test
from omni.kit.core.collection.usd import CollectionHelper
from omni.kit.window.collection import CollectionWindowExtension
from omni.kit.window.collection.window import CollectionWindow
from pxr import Sdf


async def select_prims(paths, usd_context=omni.usd.get_context()):
    usd_context.get_selection().set_selected_prim_paths(paths, True)
    await ui_test.human_delay()


class TestPropertyWindow(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        usd_context = omni.usd.get_context()
        usd_context.new_stage()
        self.window = CollectionWindow()
        await ui_test.human_delay(15)
        ret = omni.kit.commands.execute("CreatePrim", prim_type="Cone", attributes={})
        ret = omni.kit.commands.execute("CreateCollection", prim_path="/Cone", collection_name="fred")
        await ui_test.human_delay(100)

    async def tearDown(self):
        self.window.destroy()
        self.window = None

    async def _select_collection(self):

        # find and Select the "fred" collection in the collection window
        coll_window = ui_test.find("Collection")
        await coll_window.focus()
        collection_tree = coll_window.find("Frame/Frame[0]/*/*/*/TreeView[0]")
        self.assertTrue(collection_tree)

        collection_tree.widget.set_expanded(None, True, True)
        await ui_test.human_delay(10)

        fred = collection_tree.find("**/Label_collection:fred")
        self.assertTrue(fred)
        await ui_test.emulate_mouse_move_and_click(fred.center)

        property_window = ui_test.find("Property")
        self.assertTrue(property_window)
        await property_window.focus()

        collapsable_frame = ui_test.find("Property//Frame/**/CollapsableFrame[*].title=='Collection Properties'")
        collapsable_frame.widget.collapsed = False
        await ui_test.human_delay(10)
        return collapsable_frame

    async def test_expansion_rule_setting(self):

        collapsable_frame = await self._select_collection()

        expansion_rule_combo_box = collapsable_frame.find_all("/**/ComboBox[*]")[0]
        self.assertTrue(expansion_rule_combo_box)

        col_helper_fred = CollectionHelper("/Cone.collection:fred")
        self.assertTrue(col_helper_fred.is_valid())

        expansion_rule_combo_box.model.get_item_value_model(None, 0).set_value(1)

        expansion_rule_attr = col_helper_fred.get_collection_api().GetExpansionRuleAttr()
        val = expansion_rule_attr.Get()
        self.assertTrue(val == "expandPrims")

        expansion_rule_combo_box.model.get_item_value_model(None, 0).set_value(2)

        val = expansion_rule_attr.Get()
        self.assertTrue(val == "expandPrimsAndProperties")

        expansion_rule_combo_box.model.get_item_value_model(None, 0).set_value(0)

        val = expansion_rule_attr.Get()
        self.assertTrue(val == "explicitOnly")

    async def test_includeRoot_setting(self):

        collapsable_frame = await self._select_collection()

        include_root_check_box = collapsable_frame.find_all("/**/CheckBox[*]")[0]
        self.assertTrue(include_root_check_box)

        await ui_test.emulate_mouse_move_and_click(include_root_check_box.center)

        col_helper_fred = CollectionHelper("/Cone.collection:fred")
        self.assertTrue(col_helper_fred.is_valid())

        include_root_attr = col_helper_fred.get_collection_api().GetIncludeRootAttr()
        val = include_root_attr.Get()
        self.assertTrue(val is True)

        await ui_test.emulate_mouse_move_and_click(include_root_check_box.center)

        val = include_root_attr.Get()
        self.assertTrue(val is False)

    async def test_include_button(self):

        ret = omni.kit.commands.execute("CreatePrim", prim_type="Sphere", attributes={})

        collapsable_frame = await self._select_collection()

        buttons = collapsable_frame.find_all("/**/Button[0]")
        self.assertTrue(len(buttons) >= 2)

        includes_button = buttons[0]
        await ui_test.emulate_mouse_move_and_click(includes_button.center)

        await ui_test.emulate_mouse_move_and_click(buttons[0].center)

        target_window = ui_test.find("Select Targets")  # Window title changed slightly in 105
        if target_window is None:
            target_window = ui_test.find("Select Target(s)")  # Older 104 version
        self.assertTrue(target_window)
        await target_window.focus()

        stage_tree = target_window.find("Frame/**/ScrollingFrame/TreeView[*].visible==True")
        src_item = stage_tree.find("**/StringField[*].model._prim_path=='/Sphere'")
        self.assertTrue(src_item)

        await ui_test.emulate_mouse_move_and_click(src_item.center)

        add_button = target_window.find("/**/Button[*].text=='Select'")
        self.assertTrue(add_button)

        await ui_test.emulate_mouse_move_and_click(add_button.center)

        col_helper_fred = CollectionHelper("/Cone.collection:fred")
        self.assertTrue(col_helper_fred.is_valid())

        members = col_helper_fred.get_members()
        self.assertTrue(len(members) == 1)

        self.assertTrue(Sdf.Path("/Sphere") == members[0])
