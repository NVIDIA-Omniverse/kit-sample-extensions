import asyncio
import os
import socket
import traceback
from typing import Any, Dict

import carb
import omni.kit.app
from omni.services import client
from omni.services.facilities import base

from .sys_monitor import SysMonitor


class Runner(object):

    def __init__(
        self, remote_services: client.AsyncClient, services: client.AsyncClient, log: base.Facility, app, task: str
    ):
        self._agent_name = socket.getfqdn() + "_" + str(os.getpid())
        self._remote_services = remote_services
        self._services = services
        self._should_stop = asyncio.Event()
        self._has_active_task = False
        self._log = log
        self._app = app
        self._active_tasks = []
        self._task = task
        self._exit_code = 0

    def stop(self):
        self._should_stop.set()

    async def _cancel_active_tasks(self):
        for function, task in self._active_tasks:
            self._log.warning(f"Cancelling: {task}")
            await self._remote_services.render.reset(usd_file=task, function=function, __method__="post")

        await self._remote_services.agent.remove(agent=self._agent_name, __method__="post")

    async def run(self, isTesting=False):
        try:
            await self._run()
        except Exception as exc:
            carb.log_error(f"Failed to execute task: {str(type(exc))} {exc}")
            self._exit_code = -1
            # if we receive an exception, controller is unreacheable
            raise
        finally:
            if isTesting is False:
                self._stop_process(self._exit_code)

    async def _collect_and_send_metrics(self):
        # Retrieve task metrics information, if any is available:
        metrics = ""
        try:
            metrics = await self._services.metrics()
        except Exception as exc:
            pass

        # Retrieve task progress information, if any is available:
        progress = {}
        try:
            progress = await self._services.progress.retrieve()
        except Exception as exc:
            carb.log_warn(f'Could not retrieve progress for task "{self._task}": {str(exc)}')

        for attempt in range(5):
            try:
                return await self._remote_services.task.checkin(
                    task_id=self._task,
                    status="running",
                    comment="checkin",
                    metrics=metrics.decode("utf-8") if isinstance(metrics, bytes) else metrics,
                    current_step_index=progress.get("current_step_index", None),
                    total_step_count=progress.get("total_step_count", None),
                    progress=progress.get("progress", None),
                    status_message=progress.get("status_message", None),
                    time_remaining=progress.get("time_remaining", None),
                    __method__="post",
                )
            except Exception as exc:
                # There is likely to be a race condition at the moment in the agent that can cause it to hang for a certain amount of time.
                # FIXME: Bit of a sledge hammer approach
                carb.log_verbose(f"Failed to checkin with agent. attempt: {attempt} : {str(exc)}")
                await asyncio.sleep(1)
        else:
            carb.log_error(f"Failed to checkin with agent after 5 attempts.")

    async def checkin(self, checkin_interval=10):
        while True:
            if self._has_active_task:
                await self._collect_and_send_metrics()
            await asyncio.sleep(checkin_interval)

    async def _run(self):
        # TODO: newer version of omni.services.client will support .get/.post etc.
        # result = await self._remote_services.task.retrieve.get(task_id=self._task)
        try:
            result = await self._remote_services.task.retrieve(task_id=self._task, __method__="get")
        except Exception as exc:
            carb.log_error(f"Failed to retrieve {self._task}: Error was {exc}\n{traceback.format_exc()}")
            # if we fail to retrieve the task, raise an exception
            raise

        carb.log_info(f"Received task: {result}")

        function = result["task_function"]
        kwargs = result["task_function_args"]

        metadata = result.get("metadata")
        if metadata:
            await self._process_metadata(metadata)

        callable_function = self._services
        for function_part in function.split("."):
            callable_function = getattr(callable_function, function_part)

        self._has_active_task = True
        try:
            await self._remote_services.task.started.post(task_id=self._task, agent_name=self._agent_name)
        except Exception as exc:
            # Not a big deal if we fail to mark the task as started
            pass
        sys_monitor = SysMonitor().start()
        try:
            await callable_function(**kwargs)
            await self._collect_and_send_metrics()
        except Exception as exc:
            # Setting to false prior to updating remote agent to avoid any race conditions
            self._has_active_task = False
            carb.log_error(f"Failed to run task: {self._task}. Error was: {exc}\n{traceback.format_exc()}")
            try:
                await self._remote_services.task.errored.post(task_id=self._task, status="errored", comment=str(exc))
            except Exception as exc:
                carb.log_warn(f'Failed to error task "{self._task}": {str(exc)}\n{traceback.format_exc()}')
                # if we fail to mark the task as error, raise an exception
                raise
        else:
            # Setting to false prior to updating remote agent to avoid any race conditions
            self._has_active_task = False
            num_gpus, duration, stats = sys_monitor.gather_stats()
            try:
                await self._remote_services.task.finished.post(
                    task_id=self._task,
                    num_gpus=num_gpus,
                    duration=duration,
                    avg_gpu_utilization=(
                        sum([v.get("avg_utilization") for v in stats.values()]) / num_gpus if num_gpus else 0
                    ),
                    max_gpu_utilization=max([v.get("max_utilization") for v in stats.values()], default=0),
                    avg_memory=sum([v.get("avg_memory") for v in stats.values()]) / num_gpus if num_gpus else 0,
                    max_memory=max([v.get("max_memory") for v in stats.values()], default=0),
                )
            except Exception as exc:
                carb.log_warn(f'Failed to finish task "{self._task}": {str(exc)}\n{traceback.format_exc()}')
                # if we fail to mark the task as finished, raise an exception
                raise

    async def _process_metadata(self, metadata: Dict[str, Any]) -> None:
        carb.log_info("Processing task metadata.")
        # TODO: unroll metadata to enable registries and extensions.

    def _stop_process(self, exit_code=0):
        carb.log_info(f"stopping process: {exit_code}.")
        omni.kit.app.get_app().post_quit(exit_code)
