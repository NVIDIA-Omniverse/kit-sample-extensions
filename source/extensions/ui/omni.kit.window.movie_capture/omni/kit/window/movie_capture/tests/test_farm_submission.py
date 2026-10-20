# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import omni.client
from omni.kit.capture.viewport import CaptureExtension, CaptureOptions
from omni.kit.test import AsyncTestCase
from omni.kit.window.popup_dialog import MessageDialog
from omni.services.core.main import deregister_router, register_router
from omni.services.core.routers import ServiceAPIRouter
from omni.usd import UsdContext

from ..output_settings_widget import OutputSettingsWidget
from ..utils.farm_queue_utils import ADVANCED_RENDERING_FEATURES_SETTINGS_KEY

_submitted_arguments: List[Dict[str, Any]] = []


class MockAsyncServiceClient(object):
    """Mock `AsyncClient` imitating the Tasks Services on the Farm Queue."""

    def __init__(self, uri: str, app: Any = None, task_id: str = "<Task ID>"):
        self._uri = uri
        self._app = app
        self._TASK_ID = task_id

    def __getattr__(self, name: str) -> Any:
        if name == "tasks":
            return MockAsyncServiceClient(uri=self._uri, app=self._app)
        if name == "submit":
            return self._submit
        return {}  # pragma: no cover

    async def _submit(self, **kwargs):
        _submitted_arguments.append(kwargs)
        return {
            "task_id": self._TASK_ID,
        }

    def stop(self) -> None:
        pass  # pragma: no cover


class MockListEntry:
    """Mock `omni.client.ListEntry` from Nucleus, used to generate file checkpoints for mocking purposes."""

    def __init__(self, checkpoint_id: int) -> None:
        """
        Constructor.

        Args:
            checkpoint_id (int): Unique identifier of the given checkpoint (minimual value: `1`).

        Returns:
            None

        """
        self._checkpoint_id = checkpoint_id

    @property
    def relative_path(self) -> str:
        """
        Return data similar to `omni.client.ListEntry.relative_path`, which accounts for the query parameters of the
        file path.

        Args:
            None

        Returns:
            str: The equivalent of the query section of a file path.

        """
        return f"&{self._checkpoint_id}"


class TestFarmSubmissionTestCase(AsyncTestCase):
    """Test case for submitting Movie Capture tasks to Omniverse Farm."""

    def setUp(self) -> None:
        super().setUp()

        # Default number of checkpoints to generate for mock files:
        self._TEST_MAX_CHECKPOINT_ID = 2

        # Test parameters:
        self._FARM_URL = "<FARM URL>"
        self._TASK_TYPE = "<TASK TYPE>"
        self._START_DELAY = 0
        self._BATCH_COUNT = 1
        self._TASK_COMMENT = "<TASK COMMENT>"
        self._PRIORITY = 65535
        self._METADATA = {
            "extensions": [],
            "registries": [],
        }
        self._BAD_FRAME_SIZE_THRESHOLD = 0
        self._MAX_BAD_FRAME_THRESHOLD = 0

        self._capture_instance = CaptureExtension.get_instance()
        self._capture_instance.options = CaptureOptions()
        self._output_settings_widget = OutputSettingsWidget(
            collect_capture_settings_fn=self._on_collect_capture_settings,
            capture_instance=self._capture_instance,
        )
        self._output_settings_widget._build_ui_output_capture()

    def tearDown(self) -> None:
        global _submitted_arguments
        _submitted_arguments = []

        self._output_settings_widget.destroy()
        self._capture_instance = None

        return super().tearDown()

    def _on_collect_capture_settings(
        self, to_capture_sequence: bool, to_send_to_farm=False
    ) -> Tuple[CaptureOptions, Dict[str, Any]]:
        """
        Mock implementation of the callback providing capture and Farm settings for the rendering of a task.

        Args:
            _ (bool): Unused.

        Returns:
            Tuple[CaptureOptions, Dict[str, Any]]: A Tuple of `CaptureOptions` and Farm settings to use for the
                rendering of a task on the remote Farm.

        """
        capture_options = self._capture_instance.options
        farm_settings = {
            "farm_url": self._FARM_URL,
            "task_type": self._TASK_TYPE,
            "start_delay": self._START_DELAY,
            "batch_count": self._BATCH_COUNT,
            "task_comment": self._TASK_COMMENT,
            "priority": self._PRIORITY,
            "metadata": self._METADATA,
            "bad_frame_size_threshold": self._BAD_FRAME_SIZE_THRESHOLD,
            "max_bad_frame_threshold": self._MAX_BAD_FRAME_THRESHOLD,
        }
        return capture_options, farm_settings

    def _default_list_checkpoints(self, **kwargs) -> Tuple[omni.client.Result, List[MockListEntry]]:
        """
        Mock implementation for listing checkpoints of a file hosted on Nucleus, through `omni.client`.

        Args:
            kwargs (Dict[Any, Any]): Arguments provided to `omni.client.list_checkpoints(...)`.

        Returns:
            Tuple[omni.client.Result, List[MockListEntry]]: The result of the evaluation of the mock implementation,
                returning a Tuple of the result of the evaluation along with the list of checkpoints for the file.

        """
        mock_checkpoint_entries: List[MockListEntry] = []
        for i in range(self._TEST_MAX_CHECKPOINT_ID):
            checkpoint_id = i + 1  # Nucleus checkpoints start at index `1`.
            mock_checkpoint_entries.append(MockListEntry(checkpoint_id=checkpoint_id))
        return (omni.client.Result.OK, mock_checkpoint_entries)

    async def test_sending_a_farm_render_request_calls_the_collect_capture_settings(self) -> None:
        """Validate that sending a render task to Farm uses the expected default configuration."""
        capture_options, farm_settings = self._on_collect_capture_settings(
            to_capture_sequence=True, to_send_to_farm=True
        )

        TEST_USD_VERSION = 11
        TEST_USD_FILE = f"omniverse://server/path/to/stage.usd?&{TEST_USD_VERSION}"

        with (
            patch.object(UsdContext, "get_stage_url", return_value=TEST_USD_FILE),
            patch.object(
                self._output_settings_widget,
                "_collect_capture_settings_fn",
                wraps=self._output_settings_widget._collect_capture_settings_fn,
            ) as mock_collect_capture_settings,
            patch.object(
                self._output_settings_widget,
                "_get_versioned_stage_url",
                wraps=self._output_settings_widget._get_versioned_stage_url,
            ) as mock_get_versioned_stage_url,
            patch.object(
                self._output_settings_widget, "_dispatch_for_remote_rendering", return_value=asyncio.Future()
            ) as mock_dispach_for_remote_rendering,
        ):
            # Trigger the call to send a render task to the Farm Queue:
            dialog = MessageDialog()
            self._output_settings_widget._send_render_request_to_queue(dialog=dialog)

            # Ensure the call reached the expected methods, with the expected values:
            mock_collect_capture_settings.assert_called_once_with(to_capture_sequence=True, to_send_to_farm=True)
            mock_get_versioned_stage_url.assert_called_once_with(stage_url=TEST_USD_FILE)
            mock_dispach_for_remote_rendering.assert_called_once_with(
                server=farm_settings["farm_url"],
                task_type=farm_settings["task_type"],
                usd_file=TEST_USD_FILE,
                options=capture_options.to_dict()
                | {"texture_streaming_memory_budget": farm_settings.get("texture_streaming_memory_budget", 0.1)},
                render_start_delay=farm_settings["start_delay"],
                task_comment=farm_settings["task_comment"],
                batch_count=farm_settings["batch_count"],
                priority=farm_settings["priority"],
                metadata=self._METADATA,
                bad_frame_size_threshold=farm_settings["bad_frame_size_threshold"],
                max_bad_frame_threshold=farm_settings["max_bad_frame_threshold"],
                should_upload_to_s3=farm_settings.get("upload_to_s3", False),
                skip_upload=farm_settings.get("skip_upload", False),
                generate_shader_cache=farm_settings.get("generate_shader_cache", False),
            )

    async def test_default_farm_rendering_options(self) -> None:
        """Validate the default behavior of the rendering task submission to Farm."""
        capture_options, farm_settings = self._on_collect_capture_settings(
            to_capture_sequence=True, to_send_to_farm=True
        )

        TEST_USD_VERSION = 11
        TEST_USD_FILE = f"omniverse://server/path/to/stage.usd?&{TEST_USD_VERSION}"

        dialog = MessageDialog()
        self._output_settings_widget._send_render_request_to_queue(dialog=dialog)

        with patch("omni.services.client.AsyncClient", wraps=MockAsyncServiceClient) as mock_async_client:
            await self._output_settings_widget._dispatch_for_remote_rendering(
                server=farm_settings["farm_url"],
                task_type=farm_settings["task_type"],
                usd_file=TEST_USD_FILE,
                options=capture_options.to_dict(),
                render_start_delay=farm_settings["start_delay"],
                task_comment=farm_settings["task_comment"],
                batch_count=farm_settings["batch_count"],
                priority=farm_settings["priority"],
                metadata=self._METADATA,
                bad_frame_size_threshold=farm_settings["bad_frame_size_threshold"],
                max_bad_frame_threshold=farm_settings["max_bad_frame_threshold"],
                should_upload_to_s3=farm_settings.get("upload_to_s3", False),
                skip_upload=farm_settings.get("skip_upload", False),
                generate_shader_cache=farm_settings.get("generate_shader_cache", False),
            )

            # Ensure the render task was submitted to the expected Farm Queue URL:
            mock_async_client.assert_called_with(uri=f"{farm_settings['farm_url']}/queue/management")

            self.assertGreater(a=len(_submitted_arguments), b=0)
            self.assertEqual(
                first=_submitted_arguments[0],
                second={
                    "user": await self._output_settings_widget._get_user_name(),
                    "task_type": farm_settings["task_type"],
                    "task_args": {},
                    "task_function": "render.run",
                    "task_function_args": {
                        "usd_file": TEST_USD_FILE,
                        "render_settings": {
                            **capture_options.to_dict(),
                        },
                        "render_start_delay": farm_settings["start_delay"],
                        "bad_frame_size_threshold": farm_settings["bad_frame_size_threshold"],
                        "max_bad_frame_threshold": farm_settings["max_bad_frame_threshold"],
                    },
                    "task_requirements": {},
                    "task_comment": farm_settings["task_comment"],
                    "priority": farm_settings["priority"],
                    "metadata": {
                        "batches": {
                            "batch_id": _submitted_arguments[0]
                            .get("metadata", {})
                            .get("batches", {})
                            .get("batch_id", None),
                            "index": 0,
                            "last_index": 0,
                        },
                    },
                },
            )

    async def test_stages_are_uploaded_to_s3_if_requesed(self) -> None:
        """Validate that USD Stages are uploaded to S3 buckets if requested."""
        TEST_INGRESS_BUCKET_URL = "s3://ingress_server.com/bucket"
        TEST_USD_FILE_SERVER = "path"
        TEST_USD_FILE_DIRECTORY = "to"
        TEST_USD_FILE_LOCATION = f"/{TEST_USD_FILE_DIRECTORY}/stage.usd"
        TEST_USD_FILE = f"omniverse://{TEST_USD_FILE_SERVER}{TEST_USD_FILE_LOCATION}"
        TEST_EGRESS_BUCKET = "egress_server.com/bucket"
        TEST_INGRESS_BUCKET = "<INGRESS BUCKET>"
        TEST_AWS_PROFILE = "<AWS Profile>"

        capture_options, farm_settings = self._on_collect_capture_settings(
            to_capture_sequence=True, to_send_to_farm=True
        )
        # Edit some settings to allow reading the "Advanced Render Settings" from a locally-hosted Farm Queue URL,
        # acting as the remote Farm in order to pretend it requesting that USD Stages be uploaded to S3:
        farm_settings["farm_url"] = "local://"
        farm_settings["upload_to_s3"] = True

        # Host a local Service, acting as the remote Farm Queue's setting Service in order to feed its "Advanced Render
        # Settings":
        router = ServiceAPIRouter()

        @router.get("/queue/settings")
        async def settings() -> Dict[str, Any]:
            return {
                "settings": {
                    f"{ADVANCED_RENDERING_FEATURES_SETTINGS_KEY}": {
                        "ingress_bucket": TEST_INGRESS_BUCKET,
                        "ingress_bucket_url": TEST_INGRESS_BUCKET_URL,
                        "egress_bucket": TEST_EGRESS_BUCKET,
                        "farm_utilities_server": farm_settings["farm_url"],
                        "aws_profile": TEST_AWS_PROFILE,
                    },
                },
            }

        register_router(router=router)

        with patch("omni.services.client.AsyncClient", wraps=MockAsyncServiceClient) as mock_async_client:
            await self._output_settings_widget._dispatch_for_remote_rendering(
                server=farm_settings["farm_url"],
                task_type=farm_settings["task_type"],
                usd_file=TEST_USD_FILE,
                options=capture_options.to_dict(),
                render_start_delay=farm_settings["start_delay"],
                task_comment=farm_settings["task_comment"],
                batch_count=farm_settings["batch_count"],
                priority=farm_settings["priority"],
                metadata=self._METADATA,
                bad_frame_size_threshold=farm_settings["bad_frame_size_threshold"],
                max_bad_frame_threshold=farm_settings["max_bad_frame_threshold"],
                should_upload_to_s3=farm_settings.get("upload_to_s3", False),
                skip_upload=farm_settings.get("skip_upload", False),
                generate_shader_cache=farm_settings.get("generate_shader_cache", False),
            )

            # Ensure the render task was submitted to the expected Farm Queue URL:
            mock_async_client.assert_called_with(uri=f"{farm_settings['farm_url']}/queue/management")

            # Validate that 2 jobs were submitted to the Farm (a "render.run" then a "stage-collect-gtc-s3"):
            self.assertGreaterEqual(a=len(_submitted_arguments), b=2)

            # Validate data submitted to Farm about the "render.run" job:
            self.assertEqual(
                first=_submitted_arguments[0],
                second={
                    "user": await self._output_settings_widget._get_user_name(),
                    "task_type": farm_settings["task_type"],
                    "task_args": {},
                    "task_function": "render.run",
                    "task_function_args": {
                        "usd_file": f"{TEST_INGRESS_BUCKET_URL}{TEST_USD_FILE_LOCATION}",
                        "render_settings": {
                            **capture_options.to_dict(),
                            "output_folder": f"s3://{TEST_EGRESS_BUCKET}",
                        },
                        "render_start_delay": farm_settings["start_delay"],
                        "bad_frame_size_threshold": farm_settings["bad_frame_size_threshold"],
                        "max_bad_frame_threshold": farm_settings["max_bad_frame_threshold"],
                    },
                    "task_requirements": {},
                    "task_comment": farm_settings["task_comment"],
                    "priority": farm_settings["priority"],
                    "metadata": {
                        "batches": {
                            "batch_id": _submitted_arguments[0]
                            .get("metadata", {})
                            .get("batches", {})
                            .get("batch_id", None),
                            "index": 0,
                            "last_index": 0,
                        },
                    },
                    # Additional fields added when uploading to S3:
                    "status": "paused",
                },
            )

            # Validate data submitted to Farm about the "stage-collect-gtc-s3" job:
            self.assertEqual(
                first=_submitted_arguments[1],
                second={
                    "user": await self._output_settings_widget._get_user_name(),
                    "task_type": "stage-collect-gtc-s3",
                    "task_args": {},
                    "task_function": "collect.process.s3",
                    "task_function_args": {
                        "usd_path": TEST_USD_FILE,
                        "collect_dir": TEST_USD_FILE_DIRECTORY,
                        "s3_bucket": TEST_INGRESS_BUCKET,
                        "aws_profile": TEST_AWS_PROFILE,
                    },
                    "task_requirements": {},
                    "task_comment": f"Collecting {TEST_USD_FILE}",
                    "priority": farm_settings["priority"],
                    "metadata": {
                        "dependants": [
                            {
                                "source_queue": farm_settings["farm_url"],
                                "task_ids": ["<Task ID>"],
                                "task_type": self._TASK_TYPE,
                                "task_function": "render.run",
                            },
                        ],
                    },
                },
            )

        deregister_router(router=router)

    async def test_shader_cache_tasks_are_generated_if_requesed(self) -> None:
        """Validate that shader cache tasks are generated if requested."""
        TEST_INGRESS_BUCKET_URL = "s3://ingress_server.com/bucket"
        TEST_USD_FILE_SERVER = "path"
        TEST_USD_FILE_DIRECTORY = "to"
        TEST_USD_FILE_LOCATION = f"/{TEST_USD_FILE_DIRECTORY}/stage.usd"
        TEST_USD_FILE = f"omniverse://{TEST_USD_FILE_SERVER}{TEST_USD_FILE_LOCATION}"
        TEST_EGRESS_BUCKET = "egress_server.com/bucket"
        TEST_INGRESS_BUCKET = "<INGRESS BUCKET>"
        TEST_AWS_PROFILE = "<AWS Profile>"

        capture_options, farm_settings = self._on_collect_capture_settings(
            to_capture_sequence=True, to_send_to_farm=True
        )
        # Edit some settings to allow reading the "Advanced Render Settings" from a locally-hosted Farm Queue URL,
        # acting as the remote Farm in order to pretend it requesting that USD Stages be uploaded to S3:
        farm_settings["farm_url"] = "local://"
        farm_settings["upload_to_s3"] = True
        farm_settings["generate_shader_cache"] = True

        # Host a local Service, acting as the remote Farm Queue's setting Service in order to feed its "Advanced Render
        # Settings":
        router = ServiceAPIRouter()

        @router.get("/queue/settings")
        async def settings() -> Dict[str, Any]:
            return {
                "settings": {
                    f"{ADVANCED_RENDERING_FEATURES_SETTINGS_KEY}": {
                        "ingress_bucket": TEST_INGRESS_BUCKET,
                        "ingress_bucket_url": TEST_INGRESS_BUCKET_URL,
                        "egress_bucket": TEST_EGRESS_BUCKET,
                        "farm_utilities_server": farm_settings["farm_url"],
                        "aws_profile": TEST_AWS_PROFILE,
                    },
                },
            }

        register_router(router=router)

        with patch("omni.services.client.AsyncClient", wraps=MockAsyncServiceClient) as mock_async_client:
            await self._output_settings_widget._dispatch_for_remote_rendering(
                server=farm_settings["farm_url"],
                task_type=farm_settings["task_type"],
                usd_file=TEST_USD_FILE,
                options=capture_options.to_dict(),
                render_start_delay=farm_settings["start_delay"],
                task_comment=farm_settings["task_comment"],
                batch_count=farm_settings["batch_count"],
                priority=farm_settings["priority"],
                metadata=self._METADATA,
                bad_frame_size_threshold=farm_settings["bad_frame_size_threshold"],
                max_bad_frame_threshold=farm_settings["max_bad_frame_threshold"],
                should_upload_to_s3=farm_settings.get("upload_to_s3", False),
                skip_upload=farm_settings.get("skip_upload", False),
                generate_shader_cache=farm_settings.get("generate_shader_cache", False),
            )

            # Ensure the render task was submitted to the expected Farm Queue URL:
            mock_async_client.assert_called_with(uri=f"{farm_settings['farm_url']}/queue/management")

            # Validate that 3 jobs were submitted to the Farm:
            #   1. "render.run" (validated by the test above)
            #   2. "stage-collect-gtc-s3" (validated by the test above)
            #   3. "generate-shader-cache" (validated by the current test)
            self.assertGreaterEqual(a=len(_submitted_arguments), b=3)

            # Validate data submitted to Farm about the "generate-shader-cache" job:
            self.assertEqual(
                first=_submitted_arguments[2],
                second={
                    "user": await self._output_settings_widget._get_user_name(),
                    "task_type": "generate-shader-cache",
                    "task_args": {},
                    "task_function": "shaders.generate",
                    "task_function_args": {
                        "usd_file": TEST_USD_FILE,
                        "shader_upload_location": f"{TEST_USD_FILE_DIRECTORY}/cache",
                    },
                    "task_requirements": {},
                    "task_comment": f'Generating shader cache for "{TEST_USD_FILE}".',
                    "priority": farm_settings["priority"],
                    "metadata": {
                        "dependants": [
                            {
                                "source_queue": farm_settings["farm_url"],
                                "task_ids": ["<Task ID>"],
                                "task_type": "stage-collect-gtc-s3",
                                "task_function": "collect.process.s3",
                            },
                        ],
                    },
                },
            )

        deregister_router(router=router)

    async def test_checking_and_unversioned_usd_stage_returns_the_expected_value(self) -> None:
        """Validate that checking and unversioned USD Stage for a version returns `False`."""
        TEST_USD_FILE = "omniverse://server/path/to/stage.usd"

        is_versioned = self._output_settings_widget._stage_url_is_versioned(stage_url=TEST_USD_FILE)

        self.assertFalse(expr=is_versioned)

    async def test_checking_for_the_version_of_a_version_usd_stage_returns_the_expected_value(self) -> None:
        """Validate that returning the version of a USD Stage returns the expected value."""
        TEST_USD_VERSION = 11
        TEST_USD_FILE = f"omniverse://server/path/to/stage.usd?&{TEST_USD_VERSION}"

        checkpoint_id = self._output_settings_widget._get_current_stage_checkpoint_version(stage_url=TEST_USD_FILE)

        self.assertIsNotNone(obj=checkpoint_id)
        self.assertEqual(first=checkpoint_id, second=TEST_USD_VERSION)

    async def test_checking_for_the_latest_version_of_a_usd_stage_returns_the_expected_value(self) -> None:
        """
        Validate that getting the version of an unversioned USD Stage returns the highest checkpoint ID available on
        Nucleus.
        """
        TEST_USD_FILE = "omniverse://server/path/to/stage.usd"

        with patch.object(
            omni.client, "list_checkpoints", wraps=self._default_list_checkpoints
        ) as mock_list_checkpoins:
            is_versioned = self._output_settings_widget._stage_url_is_versioned(stage_url=TEST_USD_FILE)
            stage_version = self._output_settings_widget._get_current_stage_checkpoint_version(stage_url=TEST_USD_FILE)

            mock_list_checkpoins.assert_called_once_with(url=TEST_USD_FILE)
            self.assertFalse(expr=is_versioned)
            self.assertIsNotNone(obj=stage_version)
            self.assertEqual(first=stage_version, second=self._TEST_MAX_CHECKPOINT_ID)

    async def test_getting_the_versioned_stage_url_of_an_unversioned_stage_returns_the_expected_value(self) -> None:
        """Validate that getting the versioned URL of an unversioned stage returns the expected value."""
        TEST_USD_FILE = "omniverse://server/path/to/stage.usd"

        with patch.object(omni.client, "list_checkpoints", wraps=self._default_list_checkpoints):
            versioned_stage_url = self._output_settings_widget._get_versioned_stage_url(stage_url=TEST_USD_FILE)

            self.assertEqual(first=versioned_stage_url, second=f"{TEST_USD_FILE}?&{self._TEST_MAX_CHECKPOINT_ID}")

    async def test_getting_the_versioned_stage_url_of_a_versioned_stage_returns_the_same_url(self) -> None:
        """Validate that getting the versioned URL of a versioned stage returns the same URL."""
        TEST_USD_FILE = "omniverse://server/path/to/stage.usd?&11"

        with patch.object(omni.client, "list_checkpoints", wraps=self._default_list_checkpoints):
            versioned_stage_url = self._output_settings_widget._get_versioned_stage_url(stage_url=TEST_USD_FILE)

            self.assertEqual(first=versioned_stage_url, second=TEST_USD_FILE)

    async def test_getting_the_versioned_stage_url_of_a_stage_with_no_checkpoints_returns_none(self) -> None:
        """Validate that getting the versioned URL of a stage with no checkpoints returns `None`."""
        # Ensure no mock entries are generated when listing the checkpoints for this test:
        self._TEST_MAX_CHECKPOINT_ID = 0
        TEST_USD_FILE = "omniverse://server/path/to/stage.usd"

        with patch.object(omni.client, "list_checkpoints", wraps=self._default_list_checkpoints):
            stage_version = self._output_settings_widget._get_current_stage_checkpoint_version(stage_url=TEST_USD_FILE)

            self.assertIsNone(obj=stage_version)
