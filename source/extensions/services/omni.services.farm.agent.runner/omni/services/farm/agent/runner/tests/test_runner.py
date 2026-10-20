# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
import pathlib
import platform
import tempfile
from unittest import skipIf
from unittest.mock import patch

import omni.kit.app
import omni.kit.test

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
from omni.services.client import AsyncClient
from omni.services.core import main
from omni.services.facilities import log

from .. import _runner
from .test_common import MockTaskManager, router


# Tests to confirm that runner reports appropriate stats during execution.
class TestRunnerReportsStats(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._fake_task_manager = MockTaskManager({})
        self._url_prefix = "/agent"

        router.register_facility("task_manager", self._fake_task_manager)
        main.register_router(router, prefix=self._url_prefix)

    # After running each test
    async def tearDown(self):
        pass

    def _prep_runner(self, task: str) -> _runner.Runner:
        controller_client = AsyncClient(f"local://{self._url_prefix}", app=main.get_app())
        local_services = AsyncClient("local://", app=main.get_app())
        runner = _runner.Runner(controller_client, local_services, log.CarbLogFacility(), main.get_app(), task)
        return runner

    @skipIf(platform.system().lower() == "windows", "Breaks on windows.")
    async def test_stats_reported_when_task_succeeds(self):
        extension_folder_path = pathlib.Path(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        )
        test_data_dir = extension_folder_path.joinpath("data", "tests")
        # Without an output folder the captured frames are copied to "/<frame>.png", which only works as root.
        output_dir = tempfile.TemporaryDirectory()
        self.addCleanup(output_dir.cleanup)

        self._fake_task_manager.set_data(
            {
                "my_render_task": {
                    "task_id": "my_render_task",
                    "task_type": "render",
                    "task_args": {},
                    "task_function": "render.run",
                    "task_function_args": {
                        "usd_file": f"{test_data_dir}/test_render/test_render.usd",
                        "render_settings": {
                            "range_type": 0,
                            "capture_every_nth_frames": 1,
                            "fps": 30,
                            "output_folder": output_dir.name,
                        },
                        "render_start_delay": 10,
                        "bad_frame_size_threshold": 0,
                        "max_bad_frame_threshold": 3,
                    },
                    "task_requirements": {},
                    "userid": "user_id",
                    "status": "submitted",
                    "reason": "",
                }
            }
        )

        runner = self._prep_runner("my_render_task")
        await runner.run(isTesting=True)

        task = self._fake_task_manager.data.get("my_render_task")
        self.assertNotEqual(task, None)
        self.assertEqual(task.get("status"), "finished")
        self.assertNotEqual(task.get("stats"), None)

        # If GPU's were used, then confirm that GPU stats were collected
        if task.get("stats")["num_gpus"] > 0:
            print("> Render stats: ", task.get("stats"))
            self.assertTrue(task.get("stats")["duration"] > 0.0)
            self.assertTrue(task.get("stats")["max_gpu_utilization"] > 0.0)

    async def test_error_reported_when_task_fails(self):
        self._fake_task_manager.set_data(
            {
                "abcd": {
                    "task_id": "abcd",
                    "task_type": "render",
                    "task_args": {},
                    "task_function": "render.run",
                    "task_function_args": {
                        "usd_file": "abcd.usd",
                        "render_settings": {
                            "range_type": 0,
                            "capture_every_nth_frames": 1,
                            "fps": 30,
                        },
                        "render_start_delay": 10,
                        "bad_frame_size_threshold": 0,
                        "max_bad_frame_threshold": 3,
                    },
                    "task_requirements": {},
                    "userid": "user_id",
                    "status": "submitted",
                    "reason": "",
                }
            }
        )

        runner = self._prep_runner("abcd")
        with patch("traceback.format_exc"):  # Quiet expected error messages
            await runner.run(isTesting=True)

        task = self._fake_task_manager.data.get("abcd")
        self.assertNotEqual(task, None)
        self.assertEqual(task.get("status"), "errored")
        self.assertEqual(task.get("reason"), "Could not open abcd.usd")
