# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import carb.settings
import omni.anim.curve.core
import omni.graph.core as og
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.usd
from carb.input import KeyboardInput as key


class TestTimelineNode(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        extension_root_folder = Path(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        )
        self._test_files = extension_root_folder.joinpath("data/tests/usd")
        self._settings = carb.settings.get_settings()

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()

    async def test_timeline_node(self):
        await self._test_timeline_node_impl()

    async def _load_stage(self):
        usd_context = omni.usd.get_context()
        self._app = omni.kit.app.get_app()

        filename = "timeline_node_test.usda"
        test_file_path = self._test_files.joinpath(filename).absolute()
        await usd_context.open_stage_async(str(test_file_path))

        for i in range(10):
            await self._app.next_update_async()

        self._stage = usd_context.get_stage()

    async def _test_timeline_node_impl(self):
        await self._load_stage()

        graph = self._stage.GetPrimAtPath("/World/ActionGraph")
        self.assertEqual(graph.GetTypeName(), "OmniGraph")

        test_graph = og.get_graph_by_path(graph.GetPrimPath().pathString)

        # Test play from start
        await self._test_node_outputs(test_graph, key.J, 2)

        # Test play from start with a Delay node (latent state) connected in between (OM-96686)
        await self._test_node_outputs(test_graph, key.Y, 3, offset=1)

        # Test play from end
        await self._test_node_outputs(test_graph, key.K, 2, reverse=True)

        # Test play
        await self._test_node_outputs(test_graph, key.M, 2)

        # Test reverse
        await self._test_node_outputs(test_graph, key.N, 2, reverse=True)

        # Test stop
        await self._test_node_outputs(test_graph, key.J, 1)

        curr_value = self._get_timeline_node_output("output")
        # stop execution, value should not keep going
        await self._test_node_outputs(
            test_graph,
            key.O,
            2,
            override_expected_value=curr_value,
        )

        # Test set time
        await ui_test.emulate_keyboard_press(key.J)
        await og.Controller.evaluate(graph)
        # fast-forward time to 1
        await self._test_node_outputs(test_graph, key.L, 1.5, offset=-1)

    async def _test_node_outputs(
        self,
        graph,
        keypress: key | None,
        duration: float,
        offset: float = 0,
        reverse: bool = False,
        override_expected_value: float | None = None,
    ):
        ctx = graph.get_default_graph_context()
        start_counter_value = self._get_counter_node_count()
        if keypress is not None:
            await ui_test.emulate_keyboard_press(keypress, human_delay_speed=1)

        # counter node count incremented by 1 for each keypress. This is to get the exact frame where graph starts playing.
        while start_counter_value == self._get_counter_node_count():
            await og.Controller.evaluate(graph)

        start_time = ctx.get_time_since_start()

        while True:
            curr_time = ctx.get_time_since_start()
            advanced_time = curr_time - start_time
            if advanced_time >= duration:
                break
            await og.Controller.evaluate(graph)

            if advanced_time >= offset:
                self._test_y_within_range(
                    advanced_time,
                    offset,
                    reverse,
                    override_expected_value,
                )

    def _test_y_within_range(
        self,
        time: float,
        offset: float,
        reverse: bool,
        override_expected_value: float | None = None,
    ):
        anim_time = time - offset
        if reverse:
            anim_time = 2 - anim_time

        # For non-looping node
        anim_time = max(0, min(anim_time, 2))

        # check the node output value is in range with directly evaluated value
        expected_output = (
            override_expected_value if override_expected_value is not None else self._evaluate_curve_at_time(anim_time)
        )
        actual_output = self._get_timeline_node_output("output")
        self.assertAlmostEqual(
            actual_output,
            expected_output,
            msg=f"{actual_output} is not close to {expected_output} at {time}",
            delta=10,
        )

    def _evaluate_curve_at_time(self, time: float):
        curve_plugin = omni.anim.curve.core.acquire_interface()
        return curve_plugin.evaluate("/World/ActionGraph/timeline.outputs:output:x", time)

    def _get_timeline_node_output(self, output_name: str):
        attribute = og.ObjectLookup.attribute(f"/World/ActionGraph/timeline.outputs:{output_name}")
        return og.Controller.get(attribute=attribute)

    def _get_counter_node_count(self):
        attribute = og.ObjectLookup.attribute("/World/ActionGraph/counter.outputs:count")
        return og.Controller.get(attribute=attribute)
