from unittest.mock import patch

import omni.kit.commands
import omni.kit.material.library
import omni.kit.test
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.kit.test_suite.helpers import arrange_windows, get_test_data_path, open_stage, wait_stage_loading

from ..window import CollectionWindow


class TestCollectionStageWindow(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        # wait until material library has read mdl list. This prevents menus refreshing during test
        await omni.kit.material.library.get_mdl_list_async()
        # show window
        self.window = CollectionWindow()
        await ui_test.human_delay(10)
        # make sure windows don't overlap
        await arrange_windows()
        self.window.position_x = 0
        self.window.position_y = 0

    async def tearDown(self):
        # hide window
        self.window.destroy()
        self.window = None
        await ui_test.human_delay(10)

    async def test_stage_window_create_prim(self):
        # load stage
        await open_stage(get_test_data_path(__name__, "default_stage.usda"))
        await wait_stage_loading()

        # expand stage window treeview
        stage_widget = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        stage_widget.widget.set_expanded(None, True, True)

        # expand collection treeview
        collection_widget = ui_test.find("Collection//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        collection_widget.widget.set_expanded(None, True, True)
        await ui_test.human_delay(10)

        # verify collection list
        names = [w.widget.text for w in collection_widget.find_all("**/Label[*].name=='object_name'")]
        self.assertEqual(
            set(names), set(["Environment", "defaultLight", "collection:lightLink", "collection:shadowLink"])
        )

        # create prim
        omni.kit.commands.execute("CreatePrim", prim_type="Cube", attributes={})

        # create collection on prim
        await ui_test.human_delay(10)
        stage_widget = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        self.assertTrue(stage_widget)
        await stage_widget.find(f"**/StringField[*].model._prim_path=='/World/Cube'").right_click()
        await ui_test.human_delay(10)
        await ui_test.select_context_menu(f"Create/Collection")
        await ui_test.human_delay(100)

        # expand collection treeview
        collection_widget = ui_test.find("Collection//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        self.assertTrue(collection_widget)
        collection_widget.widget.set_expanded(None, True, True)
        await ui_test.human_delay(100)

        # verify collection list
        names = [w.widget.text for w in collection_widget.find_all("**/Label[*].name=='object_name'")]
        self.assertEqual(
            set(names),
            set(
                [
                    "Environment",
                    "defaultLight",
                    "collection:lightLink",
                    "collection:shadowLink",
                    "World",
                    "Cube",
                    "collection:collection",
                ]
            ),
        )

        # Test selection changes in collection widget
        # Create test prims
        ret = omni.kit.commands.execute("CreatePrim", prim_type="Cube", attributes={})
        await ui_test.human_delay(10)

        # Find and click on a collection item
        cube_item = collection_widget.find("**/Label[*].text=='Cube'")
        self.assertTrue(cube_item)
        await ui_test.emulate_mouse_move_and_click(cube_item.center)
        await ui_test.human_delay(10)

        # Verify selection
        selection = omni.usd.get_context().get_selection()
        selected_paths = selection.get_selected_prim_paths()
        self.assertEqual(selected_paths, ["/World/Cube"])

    async def test_collection_watch_reattach(self):
        # Verify no exception is raised in _reattach() when get_stage_id() returns -1 (OMPE-72501).
        # A proxy delegates all context calls to the real context except get_stage_id(), so
        # open_stage and wait_stage_loading work normally while CollectionWatch sees -1.
        # Warning message from CollectionWatch._reattach is added to stdoutFailPatterns.include
        # in extension.toml to track if an exception is raised.
        real_context = omni.usd.get_context()

        class _InvalidStageIdContext:
            def get_stage_id(self):
                return -1

            def __getattr__(self, name):
                return getattr(real_context, name)

        with patch("omni.usd.get_context", return_value=_InvalidStageIdContext()):
            await open_stage(get_test_data_path(__name__, "default_stage.usda"))
            await wait_stage_loading()
