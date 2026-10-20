import asyncio

import carb
import carb.settings
import omni.ext
from omni.services import client
from omni.services.core import main
from omni.services.facilities import log

from . import _runner


class RunnerServiceExtension(omni.ext.IExt):

    def __init__(self) -> None:
        super().__init__()
        self._runner = None
        self._checkin_future = None
        self._future = None

    def on_startup(self, ext_id):
        ext_name = ext_id.split("-")[0]
        _settings = carb.settings.get_settings_interface()
        logger = log.CarbLogFacility()

        controller_address = _settings.get(f"exts/{ext_name}/controller")
        interval = _settings.get_as_int(f"exts/{ext_name}/checkin_interval")
        task = _settings.get(f"exts/{ext_name}/assigned_task")

        if not controller_address:
            carb.log_warn("Controller address is not set, not starting runner")
            return

        controller_services = client.AsyncClient(controller_address)
        local_services = client.AsyncClient("local://", app=main.get_app())

        self._runner = _runner.Runner(controller_services, local_services, logger, main.get_app(), task)

        self._checkin_future = asyncio.ensure_future(self._runner.checkin(interval))
        self._future = asyncio.ensure_future(self._runner.run())

    def on_shutdown(self):
        if self._runner:
            self._runner.stop()
            self._runner = None

        if self._future:
            self._future.cancel()

        if self._checkin_future:
            self._checkin_future.cancel()
