# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import time
from asyncio.tasks import Task
from typing import Any

import carb
from omni.kit.usd.collect import Collector, CollectorTaskType
from omni.kit.usd.collect.omni_client_wrapper import OmniClientWrapper


def wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_running_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)

    return run


class _DummySave(object):
    """Dummy Save object to intercept saving of USD file.

    The collectors.collect function is one big function that can't be subclassed without copying/pasting the entire functionality.
    USD files are not treated in the same way as all other files and rely on being written directly during collection rather than written to a temporary location to be copied.

    This DummyLayer will behave like the actual SDF.Layer object except when saving at which point it also adds an upload callback.

    TODO: refactor the collect tool and break it down into smaller chunks so that functions can be overwritten more easily during subclassing.
    """

    def __init__(self, original_save, source, upload_callback) -> None:
        super().__init__()
        self._save = original_save
        self._source = source
        self._upload_callback = upload_callback

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        self._save()
        asyncio.ensure_future(self._upload_callback(source=self._source))


class BaseUploadCollector(Collector):
    """Collect stage related assets and upload them

    Inherit from this base class and implement the async _upload function.
    """

    def __init__(
        self,
        usd_path: str,
        collect_dir: str,
        usd_only: bool,
        flat_collection: bool,
        material_only: bool,
        ignore_missing_assets: bool = True,
    ):
        self._remote_root_location = collect_dir
        self._temp_directory = carb.tokens.get_tokens_interface().resolve("${temp}")
        self._ignore_missing_assets = ignore_missing_assets
        super().__init__(
            usd_path=usd_path,
            collect_dir=self._temp_directory,
            usd_only=usd_only,
            flat_collection=flat_collection,
            material_only=material_only,
        )

    def _configure_task(self, task: Task, target: str, task_type: CollectorTaskType, source: str = None):
        """Configure task attributes and submit for watching after task creation.

        Args:
            task (Task): Task to configure.
            target (str): Target of the task.

        Kwargs:
            source (str): If this is a copy task the source of the file that is copied
        """
        task.target = target
        task.task_type = task_type
        task.start_time = time.time()
        # NOTE: yes, this logic is a little strange, but leaving it untouched
        if source:
            task.source = target
        else:
            task.source = ""
        self._current_tasks.add(task)

    async def add_copy_task(self, source: str, target: str, skip_if_existed: bool = False):
        """Submit a new copy task.

        Args:
            source (str): Source to copy.
            target (str): Target the source should be copied to.
        """
        carb.log_info(f"Adding copy task from '{source}' to '{target}'")
        task = asyncio.ensure_future(self._copy(source, target))
        self._configure_task(task, target, task_type=CollectorTaskType.COPY_TASK, source=source)
        if len(self._current_tasks) >= self.MAX_CONCURRENT_TASKS:
            await self.wait_all_unfinished_tasks()

    async def add_write_task(self, target: str, content):
        """Submit a new file write task.

        Args:
            target (str): Target to write the content to.
            content: The content to write.
        """
        carb.log_info(f"Adding write task to '{target}'")
        task = asyncio.ensure_future(self._write(target, content))
        self._configure_task(task, target, task_type=CollectorTaskType.WRITE_TASK)
        if len(self._current_tasks) >= self.MAX_CONCURRENT_TASKS:
            await self.wait_all_unfinished_tasks()

    async def add_upload_task(self, source: str):
        """Submit a new file upload task.

        Args:
            source (str): Source to upload.
        """
        target = self._get_remote_location(source, self._temp_directory, self._remote_root_location)
        carb.log_info(f"Adding upload task from '{source}' to '{target}'")
        task = asyncio.ensure_future(self._upload(source, target))
        self._configure_task(task, target, task_type=CollectorTaskType.COPY_TASK, source=source)
        if len(self._current_tasks) >= self.MAX_CONCURRENT_TASKS:
            await self.wait_all_unfinished_tasks()

    async def _copy(self, source: str, target: str) -> bool:
        """Copy the source file to the temporary target location and submit an upload task to upload to final S3 location.

        Args:
            source (str): Source to copy.
            target (str): Target the source should be copied to.
        """
        res = await OmniClientWrapper.copy(source, target)
        if not res:
            msg = f"Unable to copy '{source}' to '{target}', therefore S3 upload will be skipped."
            if self._ignore_missing_assets:
                carb.log_warn(msg)
            else:
                raise Exception(msg)
        else:
            await self.add_upload_task(source=target)
        return res

    async def _write(self, target: str, content) -> bool:
        """Write the content to the temporary target location and submit an upload task to upload to final S3 location.

        Args:
            target (str): Target to write the content to.
            content: The content to write.
        """
        res = await OmniClientWrapper.write(target, content)
        if not res:
            msg = f"Unable to write to '{target}', therefore S3 upload will be skipped."
            if self._ignore_missing_assets:
                carb.log_warn(msg)
            else:
                raise Exception(msg)
        else:
            await self.add_upload_task(source=target)
        return res

    async def _upload(self, source, target) -> bool:
        """Upload the source to the target location.

        Args:
            source (str): source to copy.
            target (str): target the source should be copied to.
        """
        raise NotImplementedError("_upload needs to be implemented")

    def _get_remote_location(self, source: str, local_root: str, remote_root: str):
        """Calculate the remote location based on the source path.

        Args:
            source (str): source location
            local_root (str): The root of the source location
            remote_root (str): The root of the remote location.
        """
        path = source.replace(local_root, "")
        return "".join((remote_root, path))

    async def open_or_create_layer(self, layer_path: str, clear=True):
        """Open or create a layer for the given layer_path

        Args:
            layer_path (str): Path of the layer

        Note:
            This is slightly horrible as a solution as the Save function is overwritten.
            Currently no other way to catch the saving of the layer so it can be uploaded
        """
        layer = await super().open_or_create_layer(layer_path, clear=clear)

        original_save = layer.Save
        layer.Save = wrap(_DummySave(original_save, layer_path, self.add_upload_task))
        return layer

    def _remove_all_materials_and_bindings(self, stage_path):
        """Remove all materials and bindings of the given stage

        Args:
            stage_path (str): Path of the stage

        """
        super()._remove_all_materials_and_bindings(stage_path)
        asyncio.ensure_future(self.add_upload_task(source=stage_path))
