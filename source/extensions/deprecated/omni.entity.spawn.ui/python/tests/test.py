import os

import omni.entity.spawn.ui
import omni.kit.commands
import omni.kit.test
import omni.kit.ui_test as ui_test

from ..scripts.utils import create_default_spawn_graph

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestSpawnUI(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._spawn_instance = omni.entity.spawn.ui.get_instance()

    async def test_nothing(self):
        pass

    """
    async def test_spawn_graph_creation(self):
        await omni.usd.get_context().new_stage_async()
        # show wizard window
        # menu = self._spawn_instance._menu[1]
        # menu.onclick_fn()
        # await ui_test.human_delay(10)
        create_default_spawn_graph()

        # show spawn graph property
        context = omni.usd.get_context()
        result = context.get_selection().set_selected_prim_paths(["/MySpawnGraph"], True)
        await ui_test.human_delay(10)
        self.assertTrue(result)

        result = context.get_selection().set_selected_prim_paths(["/MySpawnGraph/SpawnEntity"], True)
        await ui_test.human_delay(10)
        self.assertTrue(result)

        result = context.get_selection().set_selected_prim_paths(["/MySpawnGraph/DestroyEntity"], True)
        await ui_test.human_delay(10)
        self.assertTrue(result)

        # clean template data
        await omni.kit.stage_templates.new_stage_async()
    """
