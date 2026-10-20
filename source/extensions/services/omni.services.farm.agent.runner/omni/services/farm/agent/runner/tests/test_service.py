# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
import asyncio
import platform
from unittest import skipIf
from unittest.mock import patch

import omni.kit.test

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
from omni.services.client import AsyncClient
from omni.services.core import main
from omni.services.facilities import log

from .. import _runner
from .test_common import MockTaskManager, router


class Test1(omni.kit.test.AsyncTestCase):
    # This test needs to run first.
    async def setUp(self):
        self._url_prefix = "/agent"
        self._controller_client = AsyncClient(f"local://{self._url_prefix}", app=main.get_app())
        self._logger = log.CarbLogFacility()
        self._local_services = AsyncClient("local://", app=main.get_app())
        self._runner = _runner.Runner(
            self._controller_client, self._local_services, self._logger, main.get_app(), "abcd"
        )

    async def test_an_unreachable_controller(self):
        with patch("traceback.format_exc"):  # Quiet expected error messages
            with self.assertRaises(Exception):
                await self._runner.run(isTesting=True)


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class Test2(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        _fake_data = {
            "abcd": {
                "task_id": "abcd",
                "task_type": "CR-test-202233rc14b",
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
                "userid": "userId1",
                "status": "submitted",
                "reason": "",
            }
        }

        self._fake_task_manager = MockTaskManager(_fake_data)
        self._url_prefix = "/agent"

        router.register_facility("task_manager", self._fake_task_manager)
        main.register_router(router, prefix=self._url_prefix)

        self._controller_client = AsyncClient(f"local://{self._url_prefix}", app=main.get_app())
        self._logger = log.CarbLogFacility()
        self._local_services = AsyncClient("local://", app=main.get_app())
        self._future = None
        self._checkin_future = None
        self._task = "abcd"
        self._runner = _runner.Runner(
            self._controller_client, self._local_services, self._logger, main.get_app(), self._task
        )

    # After running each test
    async def tearDown(self):
        if self._checkin_future:
            self._checkin_future.cancel()

    @skipIf(
        platform.system().lower() == "windows",
        "Breaks on windows with this error:  Failed to import python module omni.services.facilities.monitoring.metrics. Error: No module named 'prometheus_client'.",
    )
    async def test_task_failure(self):
        # asyncio.gather runs awaitables in parallel and waits for all of them to finish
        with patch("traceback.format_exc"):  # Quiet expected error messages
            await self._runner.run(isTesting=True)

        # fake usd file is unreachable and task should be marked as errored
        task_data = await self._fake_task_manager.get_task(self._task)
        self.assertEqual(task_data["status"], "errored")
        self.assertEqual(task_data["reason"], "Could not open abcd.usd")
