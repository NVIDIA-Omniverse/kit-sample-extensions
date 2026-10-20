# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import asyncio
import json
import os
import re
import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import boto3
import carb
import omni.client as omni_client
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.ui as ui
import omni.usd
import wrapp
from omni.kit.async_engine import run_coroutine
from pxr import Gf, Sdf, Tf, Usd, UsdGeom

try:
    import omni.kit.notification_manager
except ImportError:
    omni.kit.notification_manager = None

from .consistents import WRAPP_EXPLORER_DRAG_PREFIX

REFRESH_ANIMATION_TIMEOUT = 15.0


@dataclass
class AssetRepo:
    """Asset repository information."""

    display_name: str
    publish_uri: str
    install_path: str


class ProgressBarNotification:
    def __init__(
        self,
    ):
        self.progress = 0
        self.notification = None
        self.progress_bar = None

    def destroy(self) -> None:
        if self.notification:
            self.notification.dismiss()
        self.notification = None

        if self.progress_bar:
            self.progress_bar.destroy()
        self.progress_bar = None

        self.progress = 0

    def post(self, message: str, progress: float) -> None:
        carb.log_info(message)
        if not omni.kit.notification_manager:
            return
        self.notification = omni.kit.notification_manager.post_notification(
            f"{message}\n\n\n",
            hide_after_timeout=False,
        )
        self.update(progress)

    def _get_gradient_color(self, progress: float) -> int:
        """Calculate gradient color from mid-blue to dark blue based on progress (0.0 to 1.0)."""
        # Remap progress from [0, 1] to [0.5, 1] for color interpolation
        # Mid-blue (progress=0): RGB(142, 159, 215)
        # Dark blue (progress=1): RGB(30, 64, 175)
        progress = max(0.0, min(1.0, progress))  # Clamp to [0, 1]
        t = 0.5 + (progress * 0.5)  # Remap to [0.5, 1.0]
        r = int(255 - (255 - 30) * t)
        g = int(255 - (255 - 64) * t)
        b = int(255 - (255 - 175) * t)
        return 0xFF000000 | (b << 16) | (g << 8) | r

    def update(self, progress: float) -> None:
        self.progress = progress
        if not self.notification or not self.notification._prompt:
            return
        color = self._get_gradient_color(progress)
        if not self.progress_bar:
            with self.notification._prompt._layout:
                with ui.VStack():
                    ui.Spacer(height=ui.Fraction(0.8))
                    with ui.HStack(height=10):
                        ui.Spacer(width=ui.Fraction(0.2))
                        self.progress_bar = ui.ProgressBar(width=300, style={"color": color})
                        ui.Spacer(width=ui.Fraction(0.2))
                    ui.Spacer(height=36)
        else:
            self.progress_bar.model.set_value(progress)
            self.progress_bar.set_style({"color": color})


class WrappInstallQueue:
    """A queue manager that ensures wrapp.install operations run sequentially.

    This class maintains a queue of installation tasks and processes them one by one,
    preventing concurrent installations that could cause conflicts.

    Usage:
        # Get the singleton instance
        queue = WrappInstallQueue.get_instance()

        # Queue an installation (returns a future)
        future = queue.queue_install(
            package_name="my-package",
            package_version="1.0.0",
            install_dir="/path/to/install",
        )

        # Optionally wait for completion
        await future
    """

    _instance: Optional["WrappInstallQueue"] = None

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._is_processing: bool = False
        from .extension import get_instance  # Avoid circular import

        self._browser_model = get_instance().browser_model
        self._queue_finished_callback = self._browser_model.reload_installed_folder

    @classmethod
    def get_instance(cls) -> "WrappInstallQueue":
        """Get the singleton instance of the install queue."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def queue_install(
        self,
        package_name: str,
        package_version: str,
        install_dir: str,
        target_package: Optional[str] = None,
        wrapp_repo_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> asyncio.Future:
        """Queue a wrapp install operation and wait for it to complete.

        Args:
            package_name: Name of the package to install.
            package_version: Version of the package to install.
            install_dir: Directory to install the package to.
            target_package: Optional target package URL.
            wrapp_repo_url: Optional wrapp repository URL.
            tags: Optional list of tags.
            progress_callback: Optional callback for progress updates.

        Returns:
            bool: True if installation succeeded, False otherwise.
        """
        future = asyncio.get_event_loop().create_future()
        notification = log_info_with_notification(f"{package_name} queued for WRAPP install")

        install_args = {
            "operation": "install",
            "package_name": package_name,
            "package_version": package_version,
            "install_dir": install_dir,
            "target_package": target_package,
            "wrapp_repo_url": wrapp_repo_url,
            "tags": tags,
            "progress_callback": progress_callback,
            "future": future,
            "notification": notification,
        }
        await self._queue.put(install_args)
        carb.log_info(f"Queued wrapp install: '{package_name}' version '{package_version}'")

        # Start processing if not already running
        await self._ensure_processing()
        return await future

    async def queue_uninstall(
        self,
        package_name: str,
        package: Optional[str] = None,
        install_dir: Optional[str] = None,
        force: bool = False,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> asyncio.Future:
        """Queue a wrapp uninstall operation and wait for it to complete."""
        future = asyncio.get_event_loop().create_future()
        notification = log_info_with_notification(f"{package_name} queued for WRAPP uninstall")

        uninstall_args = {
            "operation": "uninstall",
            "package_name": package_name,
            "package": package,
            "install_dir": install_dir,
            "force": force,
            "progress_callback": progress_callback,
            "future": future,
            "notification": notification,
        }
        await self._queue.put(uninstall_args)
        carb.log_info(f"Queued wrapp uninstall: '{package_name}'")

        # Start processing if not already running
        await self._ensure_processing()
        return future

    async def _ensure_processing(self) -> None:
        """Ensure the queue processor is running."""
        if not self._is_processing:
            self._is_processing = True
            run_coroutine(self._process_queue())

    async def _process_queue(self) -> None:
        """Process queued install/uninstall tasks one by one."""
        try:
            while True:
                try:
                    # Get next task with a small timeout to allow checking for empty queue
                    task_args = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    # Queue is empty, stop processing
                    break

                operation = task_args.get("operation")
                notification = task_args.get("notification")
                if notification:
                    notification.dismiss()
                if operation == "install":
                    await self._execute_install(task_args)
                elif operation == "uninstall":
                    await self._execute_uninstall(task_args)
                else:
                    carb.log_error(f"Unknown operation type: {operation}")
                self._queue.task_done()
        finally:
            self._is_processing = False
            if self._queue_finished_callback:
                self._queue_finished_callback()

    async def _execute_install(self, install_args: Dict[str, Any]) -> None:
        """Execute a single installation task.

        Args:
            task: Dictionary containing installation parameters and future.
        """
        package_name = install_args.get("package_name")
        package_version = install_args.get("package_version")
        install_dir = install_args.get("install_dir")
        target_package = install_args.get("target_package")
        wrapp_repo_url = install_args.get("wrapp_repo_url")
        tags = install_args.get("tags")
        progress_callback = install_args.get("progress_callback")
        future = install_args.get("future")
        try:

            await wrapp_install_async(
                package_name=package_name,
                package_version=package_version,
                install_dir=install_dir,
                target_package=target_package,
                wrapp_repo_url=wrapp_repo_url,
                tags=tags,
                progress_callback=progress_callback,
            )
        except Exception as e:
            carb.log_error(f"Queued install failed for '{package_name}' version '{package_version}': {e}")
            future.set_exception(e)
        else:
            future.set_result(True)

    async def _execute_uninstall(self, uninstall_args: Dict[str, Any]) -> None:
        """Execute a single uninstall task.

        Args:
            uninstall_args: Dictionary containing uninstall parameters and future.
        """
        package_name = uninstall_args.get("package_name")
        package = uninstall_args.get("package")
        install_dir = uninstall_args.get("install_dir")
        force = uninstall_args.get("force", False)
        progress_callback = uninstall_args.get("progress_callback")
        future = uninstall_args.get("future")
        try:
            await wrapp_uninstall_async(
                package_name=package_name,
                package=package,
                install_dir=install_dir,
                force=force,
                progress_callback=progress_callback,
            )
        except Exception as e:
            carb.log_error(f"Queued uninstall failed for '{package_name}': {e}")
            future.set_exception(e)
        else:
            future.set_result(True)

    @property
    def pending_count(self) -> int:
        """Get the number of pending installations in the queue."""
        return self._queue.qsize()

    @property
    def is_processing(self) -> bool:
        """Check if the queue is currently processing installations."""
        return self._is_processing

    async def wait_for_all(self) -> None:
        """Wait for all queued installations to complete."""
        await self._queue.join()


@asynccontextmanager
async def wrapp_scheduler_context(message: str = "", progress_callback: Callable[[float], None] = None):
    """Get the one and only WRAPP scheduler context for this module."""
    progress_bar_notification = ProgressBarNotification()

    def _progress_callback(progress_report: wrapp.ProgressReport) -> None:
        progress = progress_report.progress()

        async def _update_progress_async() -> None:
            await omni.kit.app.get_app().next_update_async()
            progress_bar_notification.update(progress)
            if progress_callback:
                progress_callback(progress)

        call_async(_update_progress_async())

    try:
        scheduler = wrapp.SchedulerContext(
            params=wrapp.SchedulingParameters(
                jobs=200,
                file_transfer_jobs=50,
                progress_report_callback=_progress_callback,
                progress_report=wrapp.ProgressReportVerbosity.normal,
            ),
        )
        scheduler.start_scheduler()
        if message:
            progress_bar_notification.post(message, 0.0)
        yield scheduler
    finally:
        await asyncio.sleep(1)  # Wait for the progress bar to be updated
        await scheduler.stop_scheduler()
        progress_bar_notification.destroy()


def log_info_with_notification(
    message: str, hide_after_timeout=True, duration: int = 5
) -> Optional[omni.kit.notification_manager.manager.Notification]:
    """Log an info message and display a notification.

    Args:
        message (str): The info message to log and display
    """
    carb.log_info(message)
    if omni.kit.notification_manager:
        return omni.kit.notification_manager.post_notification(
            message, hide_after_timeout=hide_after_timeout, duration=duration
        )


def log_warning_with_notification(message: str) -> None:
    """Log a warning message and display a notification.

    Args:
        message (str): The warning message to log and display
    """
    carb.log_warn(message)
    if omni.kit.notification_manager:
        omni.kit.notification_manager.post_notification(
            message, duration=5, status=omni.kit.notification_manager.notification_info.NotificationStatus.WARNING
        )


def call_async(coroutine: Awaitable, callback: Optional[Callable] = None) -> asyncio.Future:
    """Execute an asynchronous function and handle its completion.

    Args:
        coroutine (Awaitable): The async function to execute
        callback (Optional[Callable, optional): Function to call when async operation completes. Defaults to None.
    """

    def future_done(future):
        # Make sure to log an exception if there is one.
        if not future.exception():
            return
        carb.log_error(f"Failed async call: {future} {future.exception()}")
        raise future.exception()

    future = run_coroutine(coroutine)
    future.add_done_callback(future_done)
    if callback:
        future.add_done_callback(callback)
    return future


def get_stage_dir_and_name(stage: Optional["Usd.Stage"] = None) -> str:
    """Get the directory of the given stage or current stage."""
    stage = omni.usd.get_context().get_stage() if not stage else stage
    if not stage:
        return "", ""

    normalized_stage_path = omni_client.normalize_url(stage.GetRootLayer().realPath)
    if "/" in normalized_stage_path:
        stage_dir, stage_name = normalized_stage_path.rsplit("/", 1)
    else:
        stage_dir = ""
        stage_name = normalized_stage_path
    return stage_dir, stage_name


async def new_wrapp_package_for_stage(stage: Optional["Usd.Stage"] = None, version: str = "0.0.1") -> Optional[str]:
    """Create a new WRAPP package for the given stage.

    Args:
        stage (Optional[Usd.Stage], optional): USD stage to create WRAPP package for.
            Uses current stage if None. Defaults to None.
        version (str, optional): Version of the WRAPP package. Defaults to "0.0.1".

    Returns:
        Optional[str]: The name of the new WRAPP package

    Raises:
        ValueError: If no stage or stage directory is provided
    """
    stage_dir, stage_name = get_stage_dir_and_name(stage)

    if not stage_dir:
        raise ValueError("No stage directory found for new_wrapp_package_for_stage")

    wrapp_package_name = os.path.splitext(stage_name)[0]
    async with wrapp_scheduler_context():
        await wrapp.commands.new(
            wrapp_package_name,
            version,
            stage_dir,
            create_catalog=False,
            tags=False,
            ignores=None,
            local_hash=False,
        )
    wrapp_path = f"{stage_dir}/.{wrapp_package_name}.wrapp"
    carb.log_info(f"New WRAPP package created: {wrapp_path}")
    return wrapp_path


async def get_wrapp_url_for_stage(
    stage: Optional["Usd.Stage"] = None, create_if_missing: bool = False
) -> Optional[str]:
    """Get the WRAPP URL from the given stage or current stage.

    Args:
        stage (Optional[Usd.Stage], optional): USD stage to get WRAPP URL from. Uses current stage if None. Defaults to None.
        create_if_missing (bool, optional): Whether to create a new WRAPP package if none is found. Defaults to False.
    Returns:
        Optional[str]: The WRAPP URL if found, None otherwise
    """
    stage_dir, _ = get_stage_dir_and_name(stage)
    if not stage_dir:
        return

    result, entries = omni_client.list(stage_dir)
    if result != omni_client.Result.OK:
        return

    wrapp_files = [entry.relative_path for entry in entries if entry.relative_path.endswith(".wrapp")]
    if not wrapp_files and create_if_missing:
        return await new_wrapp_package_for_stage(stage)

    if len(wrapp_files) > 1:
        carb.log_warn(
            f"Multiple WRAPP files found in {stage_dir}: {wrapp_files}. Using the first one [{wrapp_files[0]}]"
        )

    return f"{stage_dir}/{wrapp_files[0]}" if wrapp_files else None


def get_default_wrapp_repo_config_url_for_stage(stage: Optional["Usd.Stage"] = None) -> str:
    """Get the .wrapp_repo.config URL from the given stage or current stage. If no stage or in memory stage, an empty string is returned."""
    stage_dir, _ = get_stage_dir_and_name(stage)
    if not stage_dir:
        return ""
    return f"{stage_dir}/.wrapp_repo.config"


async def get_wrapp_repo_config_url_for_stage(stage: Optional["Usd.Stage"] = None) -> str:
    """Get the .wrapp_repo.config URL from the given stage or current stage. If not found, an empty string is returned.

    Args:
        stage (Optional[Usd.Stage], optional): USD stage to get WRAPP URL from. Uses current stage if None. Defaults to None.
    Returns:
        Optional[str]: The .wrapp_repo.config URL if found, None otherwise
    """
    config_path = get_default_wrapp_repo_config_url_for_stage(stage)
    if not config_path:
        return ""

    result, _ = await omni_client.stat_async(config_path)

    return config_path if result == omni_client.Result.OK else ""


async def load_wrapp_dependencies_json(wrapp_url: str) -> Optional[List[Dict[str, Any]]]:
    """Load dependencies from a .wrapp file.

    Args:
        url (str): URL of the .wrapp file

    Returns:
        List[Dict]: List of dependencies if found, None otherwise
    """
    # TODO: We should replace this with wrapp api when querying direct dependencies is supported - OMPE-53092
    wrapp_url = omni_client.normalize_url(wrapp_url)
    # Load json file to get assets list
    result, _, content = await omni_client.read_file_async(wrapp_url)
    if result != omni_client.Result.OK:
        return None

    carb.log_info(f"Loading dependencies from {wrapp_url}")
    try:
        return json.loads(memoryview(content).tobytes().decode("utf-8")).get("dependencies", [])
    except json.JSONDecodeError as e:
        carb.log_error(f"Failed to parse JSON from {wrapp_url}: {str(e)}")
        return None


async def load_wrapp_repo_config_json(wrapp_config_url: str) -> Optional[List[Dict[str, Any]]]:
    """Load asset_repos from a .wrapp_repo.config file.

    Args:
        url (str): URL of the .wrapp_repo.config file

    Returns:
        List[Dict]: List of repository tuples if found, None otherwise
    """
    wrapp_config_url = omni_client.normalize_url(wrapp_config_url)
    # Load json file to get assets list
    # TODO: if this is s3 and off vpn, we should setup s3 credentials via omni_client.set_s3_configuration
    result, _, content = await omni_client.read_file_async(wrapp_config_url)
    if result != omni_client.Result.OK:
        return None

    carb.log_info(f"Loading dependencies from {wrapp_config_url}")
    return json.loads(memoryview(content).tobytes().decode("utf-8"))


async def load_asset_repos_from_wrapp_config(wrapp_config_url: str) -> AsyncGenerator[Tuple[str, AssetRepo], None]:
    """Parse WRAPP configuration to extract repository information.
    There are two types of configuration files:
    - .wrapp_project.config: A dictionary with the repository name as the key and the repository URL and install path as the value.
                                This is new format introduced in mega Content Pipeline.

    - .wrapp_repo.config: A list of tuples, each containing a repository name, URL, and install path.
                            This is previously generated by the wrapp UI.

    Args:
        wrapp_config_url (str): URL of the .wrapp_repo.config file

    Yields:
        Tuple[str, AssetRepo]: Repository name and Asset repository information
    """
    wrapp_config_url = omni_client.normalize_url(wrapp_config_url)
    if not (asset_repos := await load_wrapp_repo_config_json(wrapp_config_url)):
        carb.log_warn(f"No wrapp asset repos found. Not loading repositories from {wrapp_config_url}")
        return

    asset_repo_root = ""
    try:
        # NOTE:This is Content Pipeline specific.
        # If there is a workspace, we use the project root as the anchor point for relative paths.
        import omni.cip.workspace

        asset_repo_root = omni.cip.workspace.ProjectModel().project_root_uri
    except ImportError:
        asset_repo_root = get_stage_dir_and_name()[0]

    asset_repos = asset_repos.get("assets", asset_repos.get("asset_repos"))
    if not asset_repos:
        carb.log_warn("No asset repositories found in configuration")
        return

    # If the asset_repos is a dictionary, it is the new format introduced in Content Pipeline.
    if isinstance(asset_repos, dict):
        for repo_name, settings in asset_repos.items():
            display_name = settings.get("display_name", repo_name)
            # WRAPP Repository URL to browse
            publish_uri = settings.get("publish_uri", "")
            if publish_uri.startswith(("./", "../")):
                publish_uri = omni_client.normalize_url(omni_client.combine_urls(asset_repo_root, publish_uri))

            # Install path
            install_path = f"{settings.get('install_path', '').rstrip('/')}/"

            yield repo_name, AssetRepo(display_name=display_name, publish_uri=publish_uri, install_path=install_path)

    # This is the old format that is generated by the wrapp UI.
    # Should be deprecated in the future.
    elif isinstance(asset_repos, list):
        for repo_name, publish_uri, install_path in asset_repos:
            # WRAPP Repository URL to browse
            if publish_uri.startswith(("./", "../")):
                publish_uri = omni_client.combine_urls(asset_repo_root, publish_uri)

            # Install path
            install_path = f"{install_path.rstrip('/')}/" if install_path else ""

            yield repo_name, AssetRepo(display_name=repo_name, publish_uri=publish_uri, install_path=install_path)
    else:
        carb.log_warn(f"Invalid asset_repos configuration: {asset_repos}")
        return


async def save_asset_repos_to_wrapp_config(
    wrapp_config_url: str, asset_repos: Dict[str, AssetRepo] = None, overwrite: bool = True
) -> str:
    """Parse WRAPP configuration to extract repository information.
    There are two types of configuration files:
    - .wrapp_project.config: A dictionary with the repository name as the key and the repository URL and install path as the value.
                                This is new format introduced in mega Content Pipeline.

    - .wrapp_repo.config: A list of tuples, each containing a repository name, URL, and install path.
                            This is previously generated by the wrapp UI.

    Args:
        wrapp_config_url (str): URL of the .wrapp_repo.config file
        asset_repos (Dict[str, AssetRepo], optional): Dictionary of asset repos to save. Defaults to None.
        overwrite (bool, optional): Whether to overwrite the existing asset repos. Defaults to True.
    """
    if asset_repos is None:
        asset_repos = {}

    wrapp_config_url = omni_client.normalize_url(wrapp_config_url)
    if not (wrapp_config_json := await load_wrapp_repo_config_json(wrapp_config_url)):
        wrapp_config_json = {
            "format_version": {"version_string": "3.0"},
            "version": "0.1.0",
            "deployment_uri": "",
            "working_repo": "",
            "publish_repo": "",
            "asset_type": "",
            "asset_repos": {},
        }

    # Load existing asset repos
    # asset_repos as Dict
    if "assets" in wrapp_config_json:
        asset_repos_key = "assets"
        asset_repos_from_config = wrapp_config_json["assets"]
        if overwrite:
            asset_repos_from_config = {}

    # asset_repos can be a List or Dict
    else:
        asset_repos_key = "asset_repos"
        asset_repos_from_config = wrapp_config_json.get("asset_repos")
        if overwrite:
            if isinstance(asset_repos_from_config, dict) or asset_repos_from_config is None:
                asset_repos_from_config = {}
            elif isinstance(asset_repos_from_config, list):
                asset_repos_from_config = []

    for repo_name, repo in asset_repos.items():
        # Install path
        install_path = f"{repo.install_path.rstrip('/')}/"
        # If the asset_repos is a dictionary, it is the new format introduced in Content Pipeline.
        if isinstance(asset_repos_from_config, dict):
            asset_repos_from_config[repo_name] = {
                "display_name": repo.display_name,
                "publish_uri": repo.publish_uri,
                "install_path": install_path,
            }
        # If the asset_repos is a list, it is the older format.
        elif isinstance(asset_repos_from_config, list):
            key = (repo_name, repo.publish_uri, install_path)
            if key not in {
                (repo_name, publish_uri, install_path)
                for repo_name, publish_uri, install_path in asset_repos_from_config
            }:
                asset_repos_from_config.append((repo_name, repo.publish_uri, repo.install_path))

    if isinstance(asset_repos_from_config, dict):
        # For dict, sort by keys and recreate the dict
        asset_repos_from_config = dict(sorted(asset_repos_from_config.items(), key=lambda x: x[0].lower()))
    elif isinstance(asset_repos_from_config, list):
        # For list, sort by repo name (first element of tuple)
        asset_repos_from_config = sorted(asset_repos_from_config, key=lambda x: x[0].lower())

    # Assign the sorted asset repos back to the config
    wrapp_config_json[asset_repos_key] = asset_repos_from_config

    await omni_client.write_file_async(wrapp_config_url, json.dumps(wrapp_config_json, indent=4).encode("utf-8"))
    return wrapp_config_url


async def wrapp_install(
    package_name,
    package_version,
    install_dir,
    target_package=None,
    wrapp_repo_url=None,
    tags=None,
    progress_callback=None,
):
    await WrappInstallQueue.get_instance().queue_install(
        package_name, package_version, install_dir, target_package, wrapp_repo_url, tags, progress_callback
    )


async def wrapp_uninstall(package_name, package=None, install_dir=None, force=False, progress_callback=None):
    await WrappInstallQueue.get_instance().queue_uninstall(package_name, package, install_dir, force, progress_callback)


async def wrapp_install_async(
    package_name,
    package_version,
    install_dir,
    target_package=None,
    wrapp_repo_url=None,
    tags=None,
    progress_callback=None,
):
    kwargs = {}
    target_package = target_package if target_package else await get_wrapp_url_for_stage(create_if_missing=True)
    if target_package:
        kwargs["package"] = target_package
    else:
        log_warning_with_notification(
            f"Invalid target_package provided: {target_package}. "
            f"Wrapp installation dependencies '{package_name}' version '{package_version}' will not be recorded."
        )

    if wrapp_repo_url:
        kwargs["repo"] = wrapp_repo_url
    if tags:
        kwargs["tags"] = tags

    install_dir = omni_client.normalize_url(install_dir)

    message = f"'{package_name}' version '{package_version}' to {install_dir}."
    async with wrapp_scheduler_context(
        message=f"Installing {message}", progress_callback=progress_callback
    ) as scheduler:
        try:
            await wrapp.install(
                package_name,
                package_version,
                install_dir,
                scheduler=scheduler,
                **kwargs,
            )
            carb.log_info(f"Installed {message}")
        except Exception as e:
            log_warning_with_notification(f"Failed to install {message}:\n{e}")


async def wrapp_uninstall_async(package_name, package=None, install_dir=None, force=False, progress_callback=None):
    if not package and not install_dir:
        log_warning_with_notification(
            f"package file not found: {package} and no install directory provided. "
            f"Unable to uninstall '{package_name}'."
        )
        return

    message = f"'{package_name}' from {install_dir}."
    async with wrapp_scheduler_context(
        message=f"Uninstalling {message}", progress_callback=progress_callback
    ) as scheduler:
        try:
            await wrapp.uninstall(
                package_name,
                install_location=install_dir or "",
                package=package,
                force=force,
                scheduler=scheduler,
            )
            await delete_directory(install_dir)
            carb.log_info(f"'{package_name}' uninstalled.")
        except Exception as e:
            log_warning_with_notification(f"Failed to uninstall {message}:\n{e}")


async def delete_directory(directory: str) -> None:
    # Delete the install directory
    url_result = omni_client.break_url_reference(directory)
    if url_result.scheme and url_result.scheme == "omniverse":
        # Nucleus path - check if exists and delete
        result, _ = await omni_client.stat_async(directory)
        if result == omni_client.Result.OK:
            await omni_client.delete_async(directory)
    elif os.path.exists(directory):
        shutil.rmtree(directory)


async def add_wrapp_asset_to_stage(
    stage: Usd.Stage, asset: "WrappAsset", parent_path: str, as_payload: bool = False
) -> str:
    """Add a WRAPP asset to a stage at a specific path.

    Args:
        stage (Usd.Stage): The stage to add the asset to
        asset (WrappAsset): The WRAPP asset to add
        parent_path (str): The path to add the asset under
        as_payload (bool, optional): Whether to add as payload. Defaults to False.

    Returns:
        str: The path to the asset in the stage

    Raises:
        Exception: If adding the asset to stage fails
        ValueError: If stage or asset is invalid
    """
    stage_dir, _ = get_stage_dir_and_name(stage)

    install_dir = omni_client.normalize_url(f"{stage_dir}/{asset.relative_destination}")

    await wrapp_install(
        asset.name,
        asset.version,
        install_dir,
        wrapp_repo_url=asset.wrapp_repo_url,
    )
    url = f"{install_dir}/{omni_client.normalize_url(asset.url).split('/')[-1]}"
    result, added_prim_path = add_asset_to_stage(url, parent_path=Sdf.Path(parent_path), payload=as_payload)
    if not result:
        raise Exception(f"Failed to add asset to stage: {asset.url}")
    return added_prim_path


async def wrapp_list_repo(wrapp_repo_url: str):
    """List the contents of a WRAPP repository.

    Args:
        wrapp_repo_url (str): URL of the WRAPP repository

    Returns:
        AsyncGenerator[Tuple[str, List[str]], None]: Asset root path and versions
    """
    async with wrapp_scheduler_context():
        try:
            # We don't gain any performance by using async for here.. the list_repo is a blocking call for returning the results
            for asset_root_path, versions in await wrapp.list_repo(wrapp_repo_url):
                yield asset_root_path, versions
        except Exception:
            # No package found
            carb.log_info(f"Not able to list all packages for {wrapp_repo_url}")


def add_single_asset_from_drag(drag_mime_data: str, context: str = "", prim_path: Optional[Sdf.Path] = None) -> bool:
    """
    Add a single WRAPP asset to stage from drag mime data.

    Args:
        drag_mime_data (str): Mime data describe asset to add. See more in WrappBrowserModel.get_drag_mime_data()

    Kwargs:
        context (str): Name of usd content. Default ""
        prim_path (Optional[Sdf.Path]): Parent prim path to add asset. Default None means default prim.

    """
    usd_context = omni.usd.get_context(context)
    if not usd_context:
        carb.log_error("Failed to drop asset since usd context not found!")
        return False

    stage = usd_context.get_stage()
    if not stage:
        carb.log_error("Failed to drop asset since usd stage not found!")
        return False

    if drag_mime_data.startswith(WRAPP_EXPLORER_DRAG_PREFIX):
        drag_mime_data = drag_mime_data[len(WRAPP_EXPLORER_DRAG_PREFIX) :]
    else:
        log_warning_with_notification("Invalid drag mime data provided. Skip adding asset to stage from drag.")
        return False

    raw_data = json.loads(drag_mime_data)

    if stage.GetRootLayer().realPath:
        package_name = raw_data.get("name")
        package_version = raw_data.get("version")
        source_package_url = raw_data.get("url")  # The full url of the asset - including the usd file
        wrapp_repo_url = raw_data.get("wrapp_repo_url")  # The url of the wrapp repo - the folder contains .packages
        relative_destination = raw_data.get(
            "relative_destination"
        )  # The relative destination of the asset - wrapp_assets/package_name
        target_package = raw_data.get(
            "target_package"
        )  # The path to the destination package wrap file that records the asset dependencies

        install_dir = f'{"/".join(omni_client.normalize_url(stage.GetRootLayer().realPath).split("/")[:-1])}/{relative_destination}'
        raw_data["url"] = f'{install_dir}/{source_package_url.split("/")[-1]}'

        call_async(
            wrapp_install(
                package_name,
                package_version,
                install_dir,
                target_package,
                wrapp_repo_url,
                tags=False,
            ),
            lambda *args, **kwargs: add_asset_with_variant_to_stage(raw_data, context=context, prim_path=prim_path),
        )

    else:
        as_payload = carb.settings.get_settings().get("/persistent/app/stage/dragDropImport") == "payload"
        # No working area found, skipping wrapp installation. Reference/payload to the asset source directly.
        log_warning_with_notification(
            f"No working area found, skipping wrapp installation. "
            f"Asset {source_package_url} added to the current stage as {'payload' if as_payload else 'reference'}"
        )
        add_asset_with_variant_to_stage(raw_data, context=context, prim_path=prim_path)

    return True


def add_asset_from_drag(drag_mime_data: str, context: str = "", prim_path: Optional[Sdf.Path] = None) -> bool:
    """
    Add WRAPP assets to stage from drag mime data.

    Args:
        drag_mime_data (str): Mime data describe assets to add. See more in WrappBrowserModel.get_drag_mime_data()

    Kwargs:
        context (str): Name of usd content. Default ""
        prim_path (Optional[Sdf.Path]): Parent prim path to add asset. Default None means default prim.

    """
    mime_datas = drag_mime_data.split("\n")
    for data in mime_datas:
        add_single_asset_from_drag(data, context=context, prim_path=prim_path)


def add_asset_to_stage(
    url: str,
    parent_path: Sdf.Path = Sdf.Path.emptyPath,
    position: Gf.Vec3d = Gf.Vec3d(0, 0, 0),
    variants: Optional[Dict[str, str]] = None,
    payload: bool = False,
    instanceable: bool = False,
) -> Tuple[bool, Sdf.Path]:
    """Adds an asset to the current stage.

    Args:
        url (str): Url of asset to add.
        parent_path (Sdf.Path): Path of parent prim to add asset to. If empty path, add to default prim or pseudo root.
        position (Gf.Vec3d): Position to add asset at.
        payload (bool): If True, add asset as payload, otherwise as reference.
        variants (Optional[Dict[str, str]]): Variants to set on added asset. Dictionary of variant set name and value.

    Returns:
        Tuple[bool, Sd.Path]: Tuple of success, and path to added prim.

    .. note::

        The actions of this function are undoable. If you want to add an asset without undo, use the following:

    .. code-block:: python

        with omni.kit.undo.disabled():
            add_asset_to_stage(...)
    """

    if not url:
        carb.log_error("Failed to add asset since url not defined!")
        return False, ""
    usd_context: omni.usd.UsdContext = omni.usd.get_context()
    stage: Usd.Stage = usd_context.get_stage() if usd_context else None
    if stage is None:
        carb.log_error(f"No valid stage found; cannot add {url}.")
        return False, ""

    # Creation and translation of the prim is done in a single undo group
    with omni.kit.undo.group():
        # Add the asset to the stage
        added_prim_path, _, _ = _add_asset_to_stage_helper(
            usd_context, stage, url, prim_path=parent_path, payload=payload, instanceable=instanceable
        )
        # Translate the added prim to the specified position
        omni.kit.commands.execute("TransformPrimSRTCommand", path=added_prim_path, new_translation=position)

    # Set the variants on the added prim
    if added_prim_path and variants:
        configure_prim(stage, added_prim_path, variants)

    return True, Sdf.Path(added_prim_path)


def normalize_sdf_path(sdf_layer_path: str):
    return sdf_layer_path.replace("\\", "/")


def make_relative_to_layer(stage: Usd.Stage, url: str) -> str:
    # XXX: PyBind omni::usd::UsdUtils::makePathRelativeToLayer
    stage_layer = stage.GetEditTarget().GetLayer()
    if not stage_layer.anonymous and not Sdf.Layer.IsAnonymousLayerIdentifier(url):
        stage_layer_path = stage_layer.realPath
        if normalize_sdf_path(stage_layer_path) == url:
            carb.log_warn(f"Cannot reference {url} onto itself")
            return url
        relative_url = omni_client.make_relative_url(stage_layer_path, url)
        if relative_url:
            # omniverse path can have '\'
            return relative_url.replace("\\", "/")
    return url


def make_prim_path(stage: Usd.Stage, url: str, prim_path: Sdf.Path = None, prim_name: str = None):
    """Make a new/unique prim path for the given url"""
    if prim_path is None or prim_path.isEmpty:
        if stage.HasDefaultPrim():
            prim_path = stage.GetDefaultPrim().GetPath()
        else:
            prim_path = Sdf.Path.absoluteRootPath

    if prim_name is None:
        prim_name = Tf.MakeValidIdentifier(os.path.basename(os.path.splitext(url)[0]))

    return Sdf.Path(omni.usd.get_stage_next_free_path(stage, prim_path.AppendChild(prim_name).pathString, False))


def _add_asset_to_stage_helper(
    usd_context: omni.usd.UsdContext,
    stage: Usd.Stage,
    url: str,
    prim_path: Sdf.Path = None,
    payload: str = "",
    instanceable: str = "",
) -> Tuple[Sdf.Path, Usd.EditContext, str]:
    """Add a Usd.Prim to an exiting Usd.Stage, pointing to the url
    Args:
        usd_context (omni.usd.UsdContext): Usd context to add asset to.
        stage (Usd.Stage): Usd stage to add asset to.
        url (str): Url to asset to add.
    Kwargs:
        prim_path (Sdf.Path): Parent prim path to add asset to.
        payload (str): "payload" or "reference". If empty, use the setting at "/persistent/app/stage/dragDropImport".
        instanceable (str): "instanceable" or "noninstanceable". If empty (default), use the setting at "/persistent/app/stage/instanceableOnCreatingReference".
        selected_prims (List[Usd.Prim]): List of selected prims. If not empty (default), use the first prim's payload/reference status.
    """
    # Get a realtive URL if possible
    relative_url = make_relative_to_layer(stage, url)

    # When in auto authoring mode, don't create it in the current edit target
    # as it will be cleared each time to be moved to default edit layer.
    edit_context = None
    try:
        import omni.kit.usd.layers as layers

        layers_interface = layers.get_layers(usd_context)
        edit_mode = layers_interface.get_edit_mode()
        if edit_mode == layers.LayerEditMode.AUTO_AUTHORING:
            default_identifier = layers.get_default_edit_layer_identifier()
            edit_layer = Sdf.Layer.Find(default_identifier)
            if edit_layer is None:
                edit_layer = stage.GetRootLayer()
            edit_context = Usd.EditContext(stage, edit_layer)
    except ImportError:
        pass

    new_prim_path = make_prim_path(stage, url, prim_path=prim_path)
    if not instanceable:
        as_instanceable = carb.settings.get_settings().get("/persistent/app/stage/instanceableOnCreatingReference")
    else:
        as_instanceable = instanceable == "instanceable"

    # Determine if we should create a payload or reference
    if not payload:
        create_as_payload = carb.settings.get_settings().get("/persistent/app/stage/dragDropImport") == "payload"
    else:
        create_as_payload = payload == "payload"

    # Add asset to stage
    cmd_name = "CreatePayloadCommand" if create_as_payload else "CreateReferenceCommand"
    omni.kit.commands.execute(
        cmd_name, usd_context=usd_context, path_to=new_prim_path, asset_path=url, instanceable=as_instanceable
    )

    return (new_prim_path, edit_context, relative_url)


def set_prim_variants(stage: Usd.Stage, prim_path: Sdf.Path, variants: Dict[str, str]):
    """
    Set the variants on the provided prim.
    """
    prim = stage.GetPrimAtPath(prim_path)
    if prim:
        vsets = prim.GetVariantSets()
        for name, value in variants.items():
            carb.log_info(f"Try to set variant for {prim_path}: {name} -> {value}")
            vset = vsets.GetVariantSet(name)
            if vset:
                vset.SetVariantSelection(value)


def configure_prim(stage: Usd.Stage, prim_path: Sdf.Path, variants: Dict[str, str]) -> None:
    """Configure the variants of the given prim."""
    if not stage or not prim_path or prim_path.emptyPath or not variants:
        return
    # Set the variants on the prim at prim_path
    set_prim_variants(stage, prim_path, variants)


def add_asset_with_variant_to_stage(
    raw_data: dict, context: str = "", prim_path: Optional[Sdf.Path] = None
) -> Tuple[bool, str]:
    """Add WRAPP asset to stage from raw data.

    Args:
        raw_data (dict): Json data describe asset to add. See more in WrappBrowserModel.get_drag_mime_data()

    Kwargs:
        context (str): Name of usd content. Default ""
        prim_path (Optional[Sdf.Path]): Parent prim path to add asset. Default None means default prim.

    Returns:
        Tuple of success and added prim path.

    """
    usd_context = omni.usd.get_context(context)
    if not usd_context:
        carb.log_error("Failed to drop asset since usd context not found!")
        return False, ""
    stage = usd_context.get_stage()
    if not stage:
        carb.log_error("Failed to drop asset since usd stage not found!")
        return False, ""
    url = raw_data.get("url", "")
    if not url:
        carb.log_error("Failed to drop asset since url not defined!")
        return False, ""
    payload = raw_data.get("payload", "")
    instanceable = raw_data.get("instanceable", "")

    # Add the asset to stage
    dropped_path, _, _ = _add_asset_to_stage_helper(
        usd_context, stage, url, prim_path=prim_path, payload=payload, instanceable=instanceable
    )

    # Set variants on the added asset
    if dropped_path:
        variants = raw_data.get("variants", {})
        configure_prim(stage, dropped_path, variants)

    return True, dropped_path


def get_average_position_of_prims(prims: List[Usd.Prim]) -> Gf.Vec3d:
    """Get the average position of a list of prims.

    Args:
        prims (List[Usd.Prim]): The list of prims to get the average position of.

    Returns:
      The average 3D position of the prims, or the origin if no prims provided.
    """

    position = Gf.Vec3d(0)
    for prim in prims:
        if prim.IsA(UsdGeom.Xformable):
            position += omni.usd.get_world_transform_matrix(prim).ExtractTranslation()
    if len(prims) > 0:
        position /= len(prims)
    return position


def add_asset_to_stage_using_prims(
    usd_context: omni.usd.UsdContext,
    stage: Usd.Stage,
    url: str,
    variants: Optional[Dict[str, str]] = None,
    replace_prims: bool = False,
    prim_paths: List[Sdf.Path] = [],
) -> Tuple[bool, Sdf.Path]:
    """Add an asset to a stage using a list of prims.

    The asset will be added to the average position of the provided prims, or the origin if no prims supplied.
    The asset will be added as a reference or payload based on whether the first provided prim has authored references or payloads.
    If no prims specified, the setting at "/persistent/app/stage/dragDropImport" is used.
    If the new asset is to replace the prims, the asset's parent will be the common ancestor of all prims.
    If no prims specified, the default prim or pseudo root will be used as the parent prim of the added asset.

    Args:
        usd_context (omni.usd.UsdContext): UsdContext to add asset to.
        stage (Usd.Stage): Stage to add asset to.
        url (str): Url of asset to add.
        variants (Optional[Dict[str, str]]): Variants to set on the added prim.
        replace_prims (bool): If True, replace the selection with the new asset.
        prim_paths (List[Sdf.Path]): List of prims to use for adding the asset.

    Returns:
        Tuple of success and added prim path.

    .. note::
        The actions of this function are undoable. If you want to add an asset without undo, use the following:

    .. code-block:: python

        with omni.kit.undo.disabled():
            add_asset_to_stage_using_prims(...)
    """
    if not url:
        carb.log_error("Failed to add asset since url not defined!")
        return False, ""
    if usd_context is None or stage is None:
        carb.log_error(f"No valid stage found; cannot add {url}.")
        return False, ""

    prims = [
        stage.GetPrimAtPath(path)
        for path in prim_paths
        if stage.GetPrimAtPath(path) and stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)
    ]

    # If replacing prims, all prims must be deletable\replaceable
    if replace_prims:
        for prim in prims:
            if not prim.IsValid() or (
                prim.GetMetadata("no_delete") is not None and prim.GetMetadata("no_delete") is True
            ):
                carb.log_error("Failed to add asset since cannot replace specified prims!")
                return False, ""

    # Get average position of prims
    position: Gf.Vec3d = get_average_position_of_prims(prims)

    # If prims specified, use the first prim's payload/reference status
    create_option = ""
    if prims and len(prims) > 0:
        for prim in prims:
            if prim.HasAuthoredReferences():
                create_option = "reference"
                break
            if prim.HasAuthoredPayloads():
                create_option = "payload"
                break

    # Determine parent path for new prim
    if replace_prims and prims and len(prims) > 0:
        parent_path: Sdf.Path = Sdf.Path.emptyPath
        for prim in prims:
            if parent_path == Sdf.Path.emptyPath:
                parent_path: Sdf.Path = prim.GetParent().GetPath()
            else:
                parent_path: Sdf.Path = parent_path.GetCommonPrefix(prim.GetParent().GetPath())
    elif stage.HasDefaultPrim():
        parent_path: Sdf.Path = stage.GetDefaultPrim().GetPath()
    else:
        parent_path: Sdf.Path = Sdf.Path.absoluteRootPath

    # Deletion, creation and translation of prims is done in a single undo group
    with omni.kit.undo.group():
        # If replacing prims, delete them before adding new ones to prevent potential name collision
        if replace_prims and prim_paths and len(prim_paths) > 0:
            omni.kit.commands.execute("DeletePrimsCommand", paths=prim_paths)
        # Add asset to stage
        added_prim_path, _, _ = _add_asset_to_stage_helper(
            usd_context, stage, url, prim_path=parent_path, payload=create_option, instanceable=""
        )
        # Translate the added prim to the specified position
        omni.kit.commands.execute("TransformPrimSRTCommand", path=added_prim_path, new_translation=position)

    # Set the variants on the added prim
    if added_prim_path and variants:
        configure_prim(stage, added_prim_path, variants)

    return True, added_prim_path


def get_selected_xformable_prim_paths(usd_context: omni.usd.UsdContext, stage: Usd.Stage) -> List[Sdf.Path]:
    """Get the list of selected Xformable prim paths in the stage.

    Args:
        usd_context (omni.usd.UsdContext): The USD context to get the selection from.
        stage (Usd.Stage): The stage to get the selection from.

    Returns:
        The list of prim paths of the selected Xformable prims in the stage,
        or an empty list if there's nothing selected.
    """

    if usd_context is None or stage is None:
        return []
    selection = usd_context.get_selection()
    return [
        path
        for path in selection.get_selected_prim_paths()
        if stage.GetPrimAtPath(path) and stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)
    ]


def get_s3_region_and_bucket(s3_uri: str, default_region: str = None) -> tuple[str, str]:
    if is_s3_http_uri(s3_uri):
        # Try to get the default region from the http uri if not provided
        if not default_region:
            match = re.search(r"https?://[^.]+\.s3\.([^.]+)\.amazonaws\.com", s3_uri)
            if match:
                default_region = match.group(1)

        s3_uri = http_to_s3_uri(s3_uri)

    if not is_s3_uri(s3_uri):
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Unable to get region and bucket.")

    url = omni_client.break_url(s3_uri)

    # The bucket is the url.host, ie: s3://{bucket}/{path}
    bucket = url.host
    # Try to get the region from the environment
    region = default_region or os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION"))
    if not region:
        raise ValueError(
            f"Could not get region from s3 uri: {s3_uri}, either set AWS_REGION or AWS_DEFAULT_REGION environment variable."
        )

    bucket_uri = omni_client.make_url(scheme="https", host=f"{bucket}.s3.{region}.amazonaws.com")
    return region, bucket, bucket_uri


def is_s3_uri(uri: str) -> bool:
    """
    Returns true if the URI is to a resource in an s3 bucket
    """
    return str.lower(uri).startswith("s3://")


def is_s3_http_uri(uri: str) -> bool:
    """
    Returns true if the URI is to a resource in an aws s3 bucket

    Args:
        uri (str): The URI to check.

    Returns:
        bool: True if the URI is to a resource in an aws s3 bucket, False otherwise.
    """
    uri = uri.lower()
    if not (uri.startswith("http://") or uri.startswith("https://")):
        return False

    # Remove protocol
    host_and_path = uri.split("://", 1)[1]
    # Split into host and remaining path
    host = host_and_path if "/" not in host_and_path else host_and_path.split("/", 1)[0]

    # Check if host is something.amazonaws.com
    if not host.endswith(".amazonaws.com"):
        return False

    # Common S3 host patterns
    if "s3." in host or "s3-" in host:
        return True

    return False


def http_to_s3_uri(http_url: str) -> str:
    """
    Convert an HTTP S3 URL to the S3 URI format.

    Args:
        http_url (str): The HTTP URL to convert.

    Returns:
        str: The corresponding S3 URI.
    """
    if not is_s3_http_uri(http_url):
        raise ValueError(f"Invalid S3 HTTP URI: {http_url}")

    parsed = urlparse(http_url)
    # Extract bucket name from the hostname
    bucket_name = parsed.netloc.split(".")[0]
    # Extract object key from the path
    object_key = parsed.path.lstrip("/")
    # Construct the S3 URI
    s3_uri = f"s3://{bucket_name}/{object_key}"
    return s3_uri


def s3_to_http_uri(s3_uri: str, region: str = None) -> str:
    """
    Convert an S3 URI to an HTTPS URI.

    Args:
        s3_uri (str): The S3 URI, e.g. 's3://my-bucket/path/to/file.txt'
        region (str, optional): Region string (e.g., 'us-west-2').

    Returns:
        str: HTTPS URI equivalent of the S3 URI.
    """
    if not is_s3_uri(s3_uri):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")

    region = region or os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION"))
    _, _, bucket_uri = get_s3_region_and_bucket(s3_uri, region)

    if not bucket_uri:
        raise ValueError(f"Invalid S3 URI, missing bucket: {s3_uri}")

    object_key = urlparse(s3_uri).path

    if object_key:
        http_uri = f"{bucket_uri.rstrip('/')}/{object_key.lstrip('/')}"
    else:
        http_uri = bucket_uri

    return http_uri


def set_omni_client_s3_configuration(bucket_uri: str, bucket: str, region: str):
    # Create a Boto3 session, get credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    result = omni_client.set_s3_configuration(
        url=bucket_uri,
        bucket=bucket,
        region=region,
        accessKeyId=credentials.access_key,
        secretAccessKey=credentials.secret_key,
        cloudfrontUrl=None,
        cloudfrontForList=False,
        writeConfig=False,
    )
    if result != omni_client.Result.OK:
        raise RuntimeError(f"Failed to set S3 configuration using omni.client! Error: {result}.")


def get_settings_dialog(
    click_okay_handler: Callable | None = None,
    click_cancel_handler: Callable | None = None,
    asset_repos: Dict[str, AssetRepo] = None,
) -> "SettingsDialog":
    """Get the settings dialog for the package explorer.
    If the omni.cip.workspace and omni.cip.wrapp_ui extensions are available, use the SettingsDialog from the omni.cip.wrapp_ui extension.
    Otherwise, use the SettingsDialog from the package explorer.
    Note that the if the SettingsDialog from the omni.cip.wrapp_ui extension is used, the asset_repos parameter is ignored.
    """
    try:
        from omni.cip.workspace import ProjectModel
        from omni.cip.wrapp_ui.settings_dialog import SettingsDialog

        return SettingsDialog(
            workspace=ProjectModel().workspace,
            click_okay_handler=click_okay_handler,
            click_cancel_handler=click_cancel_handler,
        )
    except Exception:
        from .settings_dialog import SettingsDialog

        return SettingsDialog(
            click_okay_handler=click_okay_handler,
            click_cancel_handler=click_cancel_handler,
            asset_repos=asset_repos,
        )
