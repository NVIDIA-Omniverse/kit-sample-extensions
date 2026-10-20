# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import abc
import os
from urllib.parse import urlparse

import carb.settings
import omni.client


class FileCopyError(Exception):
    """Raised when there has been an issue copying a file"""


class BaseFileTask(object):
    """Abstract base file task"""

    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__()
        self._input_path = input_path
        self._output_path = output_path

    @property
    def input_path(self):
        return self._input_path

    @property
    def output_path(self):
        return self._output_path

    @abc.abstractmethod
    async def run(self):
        """
        Run the processing of the task.

        Needs to be implemented when subclassing BaseFileTask.
        """
        pass

    def _calculate_output_path(self, root: str, separator: str = "/") -> str:
        """
        Calculate output path

        Depending on wether 'append_task_id' is set to true, will append the task_id to the output path.

        Args:
            root (str): Root directory
            separator (str): Directory separator. Default: /
        """
        if not carb.settings.get_settings_interface().get_as_bool("exts/omni.services.render/append_task_id"):
            return root

        task_id = (
            carb.settings.get_settings_interface().get("exts/omni.services.farm.agent.runner/assigned_task") or None
        )
        if not task_id:
            return root

        return separator.join((root, task_id))


class OmniClientFileTask(BaseFileTask):
    """Base class for omni.client based file tasks"""

    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__(input_path, output_path)
        self._separator = os.sep

    async def run(self):
        filename = os.path.basename(self._input_path)

        output_path = self._calculate_output_path(self._output_path, self._separator)
        output_file = f"{self._separator}".join((output_path, filename))

        result = await omni.client.copy_async(self._input_path, output_file)
        if result == omni.client.Result.ERROR_ALREADY_EXISTS:
            result = await omni.client.delete_async(output_file)
            result = await omni.client.copy_async(self._input_path, output_file)

        if result != omni.client.Result.OK:
            carb.log_error(f"Failed to copy file: {self._input_path}, {output_file}, {result}")
            raise FileCopyError(f"Failed to copy file: {self._input_path}, {output_file}, {result}")


class NucleusFileTask(OmniClientFileTask):
    """Upload file to Nucleus"""

    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__(input_path, output_path)
        self._separator = "/"


class FSFileTask(OmniClientFileTask):
    """Upload file to standard file type systems"""


class S3FileTask(BaseFileTask):
    """Upload file to S3 compatible storage"""

    async def run(self):
        # move import here to avoid startup test error
        import aioboto3

        session = aioboto3.Session(
            # profile_name=aws_profile,
            # region_name=aws_region,
        )

        parsed_url = urlparse(self._output_path)
        bucket_name = parsed_url.netloc

        # Remove leading slashes
        filename = os.path.basename(self._input_path)
        output_path = parsed_url.path.lstrip("/")
        output_path = self._calculate_output_path(output_path)
        output_path = "/".join((output_path, filename))

        async with session.client("s3") as client:
            try:
                with open(self._input_path, "rb") as fd:
                    await client.upload_fileobj(fd, bucket_name, output_path)
            except Exception as exc:
                carb.log_error(
                    f"Unable to upload {self._input_path} to {bucket_name}:{output_path}: {exc} ({type(exc)})"
                )
                raise FileCopyError(str(exc)) from exc
