from pathlib import Path

import omni.graph.core as og
import omni.kit.commands
import omni.kit.test
import omni.timeline
from pxr import Gf


class TestSpawnCore(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        extension_root_folder = Path(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        )
        self._USD_DIR = extension_root_folder.joinpath("data/usd")

    def _create_node(self, graph, node_type: str, node_name: str):
        (_, [node], _, _) = og.Controller.edit(graph, {og.Controller.Keys.CREATE_NODES: (node_name, node_type)})
        return node

    async def test_spawn_commands(self):
        await omni.usd.get_context().new_stage_async()

        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Sphere")

        # spawn a sphere
        omni.kit.commands.execute("SpawnEntityCommand", source_paths=["/Sphere"], transform=Gf.Matrix4d())
        await omni.kit.app.get_app().next_update_async()

        # find the sphere
        ret, entityNames = omni.kit.commands.execute("FindEntityCommand", source_path="/Sphere")
        self.assertEqual(entityNames[0], "Sphere")
        await omni.kit.app.get_app().next_update_async()

        # remove the sphere
        omni.kit.commands.execute("DestroyEntityCommand", entity_names=["Sphere"])
        await omni.kit.app.get_app().next_update_async()

        # check it is removed
        ret, entityNames = omni.kit.commands.execute("FindEntityCommand", source_path="/Sphere")
        self.assertFalse(entityNames)

        # clean template data
        await omni.kit.stage_template.core.new_stage_async()

    async def test_nodes(self):
        test_file_path = self._USD_DIR.joinpath("test_spawn.usda").absolute()
        await omni.usd.get_context().open_stage_async(str(test_file_path))

        await omni.kit.app.get_app().next_update_async()

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()

        for i in range(10):
            await omni.kit.app.get_app().next_update_async()

        timeline.stop()

        # clean template data
        await omni.kit.stage_template.core.new_stage_async()
