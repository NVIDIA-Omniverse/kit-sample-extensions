# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import json
import os
from argparse import Namespace
from functools import partial
from pathlib import Path
from typing import Callable, Dict, List

import carb
import carb.settings
import omni.client
import omni.client.utils as clientutils
import omni.ext
import omni.kit.menu.utils
import omni.kit.notification_manager as nm
import omni.kit.pipapi
import omni.ui as ui
import omni.usd
from omni.kit.window.file_importer import get_file_importer

from .asset_publish_options import AssetPublishOptions
from .package_utils import (
    OPTIMIZER_MAX_ERROR_DEFAULT,
    SETTINGS_KIT_APPLICATION_PATH,
    SETTINGS_LAST_CONFIG,
    SETTINGS_MAX_ERROR,
    ProgressStage,
)
from .styles import UI_STYLES
from .widgets import (
    MODE_UPLOAD,
    BoolSettingsModel,
    CollectorSettingsWindow,
    CollectorSwitches,
    InfoBar,
    Phases,
    PhaseSettingsWindow,
    PhasesWidget,
    ProgressBar,
    StatusBar,
    ValidatorSettingsModel,
    ValidatorSettingsWindow,
)

# from boto3.exceptions import S3UploadFailedError
# from botocore.exceptions import ClientError

# try:
#     import aioshutil
# except ImportError:
#     omni.kit.pipapi.install("aioshutil", module="aioshutil")
#     import aioshutil
# try:
#     import aioboto3
# except ImportError:
#     omni.kit.pipapi.install("aioboto3", module="aioboto3")
#     import aioboto3
# try:
#     from boto3.session import Session
#     from boto3.s3.transfer import TransferConfig, S3Transfer
#     from boto3.exceptions import  S3UploadFailedError
#     from botocore.exceptions import ClientError
#     from botocore.config import Config
# except ImportError:
#     omni.kit.pipapi.install("boto3", module="boto3")
#     from boto3.session import Session
#     from boto3.s3.transfer import TransferConfig, S3Transfer
#     from boto3.exceptions import  S3UploadFailedError
#     from botocore.exceptions import ClientError
#     from botocore.config import Config
# try:
#     import requests
# except ImportError:
#     omni.kit.pipapi.install("requests", module="requests")
#     import requests
# try:
#     from tqdm import tqdm
# except ImportError:
#     omni.kit.pipapi.install("tqdm", module="tqdm")
#     from tqdm import tqdm

DEFAULT_API_URL = "https://builds.developer.nvidiagrid.net/api/1"
DEFAULT_NUM_THREADS = 10
DEFAULT_UPLOAD_RETRIES = 3
DEFAULT_ASSET_NAME = "product_configurator_base"
GDN_ASSET_PUBLISHER_MENU_PATH = "Tools/Product Configurator/Publish To GDN"


def _get_default_options():  # pragma: no cover
    options = Namespace()
    options.target = (
        "GEFORCENOW"  # What NVIDIA service should receive the uploaded build ('GEFORCENOW' or 'GAMEREADYSERVICES')
    )
    options.url = DEFAULT_API_URL  # Base URL for the upload API
    options.retry_count = DEFAULT_UPLOAD_RETRIES  # Amount of retries for upload
    options.debug = False  # Outputs more verbose logging to assist with debugging/troubleshooting
    options.quiet = False  # Mutes most output for use in scripts/automation
    options.num_threads = DEFAULT_NUM_THREADS  # Number of threads to concurrently upload the file in chunks
    options.release_date = ""  # Scheduled date for the build to go live in GeForce NOW, in ISO-8601 format
    options.semantic_version = ""  # External version identifier; e.g., 1.0.0
    options.change_version = ""  # Internal change version identifier; e.g., Git commit hash or Perforce CL number
    options.launch_command = None  # Command required to launch the build, including any parameters or flags
    return options


def _get_stage():
    context = omni.usd.get_context()
    return context.get_stage()


class PublisherWindow(ui.Window):

    def set_publish_clicked_fn(self, publish_clicked_fn: Callable[[AssetPublishOptions], None]):
        self.__publish_clicked_fn = publish_clicked_fn

    def __init__(self, **kargs):
        super().__init__("Configurator Publisher", width=800, height=355, **kargs)

        self.frame.set_build_fn(self.__build_fn)

        self.flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | omni.ui.WINDOW_FLAGS_MENU_BAR
            # | ui.WINDOW_FLAGS_NO_CLOSE
        )

        self.__publish_clicked_fn = None
        self.__publish_task = None
        self.__task_cancelled = False

        self._carb_settings = carb.settings.get_settings()
        self._phase_models = {}
        for phase in Phases:
            model = BoolSettingsModel(f"persistent/configurator_publisher/{phase.value}")
            self._phase_models[phase] = model
            model.add_value_changed_fn(lambda _: self._set_ui_state())

        self._collector_models = {}
        for switch in CollectorSwitches:
            model = BoolSettingsModel(f"persistent/configurator_publisher/{switch.value}")
            self._collector_models[switch] = model

        self._temp_directory = self._carb_settings.get("persistent/configurator_publisher/temp_dir")
        self._optimizer_max_error = self._carb_settings.get(SETTINGS_MAX_ERROR)
        self._optimizer_config = self._carb_settings.get(SETTINGS_LAST_CONFIG)
        self._kit_application_path = self._carb_settings.get(SETTINGS_KIT_APPLICATION_PATH)

        self.__usd_file_field = None
        self.__optimizer_config_field = None
        self.__temp_dir_field = None
        self.__kit_application_path_field = None
        self.__zip_name_field = None
        # self.__token_field = None
        # self.__product_id_field = None
        self.__publish_button = None
        self.__phase_widget = None

        self.__status_bar = None
        self.__progress_bar = None
        self.__info_bar = None
        self.__prompt = None

        self._phase_settings_window = None
        self._collector_settings_window = None
        self._token_file_start_path = None

        self._validator_settings_window = None
        self._validator_settings_model = ValidatorSettingsModel()

    def destroy(self):
        super().destroy()

        if self._phase_settings_window:
            self._phase_settings_window.visible = False
            self._phase_settings_window.destroy()
            self._phase_settings_window = None

        if self._collector_settings_window:
            self._collector_settings_window.visible = False
            self._collector_settings_window.destroy()
            self._collector_settings_window = None

        if self._validator_settings_window:
            self._validator_settings_window.visible = False
            self._validator_settings_window.destroy()
            self._validator_settings_window = None

        if self._phase_models:
            for _, model in self._phase_models.items():
                model.destroy()
            self._phase_models = None

        if self._collector_models:
            for _, model in self._collector_models.items():
                model.destroy()
            self._collector_models = None

        if self._validator_settings_model:
            self._validator_settings_model.destroy()
            self._validator_settings_model = None

        if self.__publish_task:
            self.__publish_task.cancel()
            self.__publish_task = None

        if self.__prompt:
            self.__prompt.destroy()

    def __build_fn(self):
        menu_bar = self.menu_bar
        with menu_bar:
            with ui.Menu("Settings"):
                ui.MenuItem("Steps...", triggered_fn=self._phase_settings_ui)
                ui.MenuItem("Collector...", triggered_fn=self._collector_settings_ui)
                ui.MenuItem("Validator...", triggered_fn=self._validator_settings_ui)

        with self.frame:
            with ui.VStack(spacing=5, height=0, styles=UI_STYLES):
                ui.Line(style={"color": ui.color.gray})
                ui.Spacer(height=3)
                with ui.HStack(height=0):
                    ui.Spacer(width=20)
                    ui.Label(
                        "Asset Path:",
                        height=24,
                        width=110,
                        tooltip="The asset to collect, optimize, cache, package, and publish",
                    )
                    self.__usd_file_field = ui.StringField(
                        height=24, tooltip="The asset to collect, optimize, cache, package, and publish"
                    )
                    ui.Spacer(width=5)
                    ui.Button(
                        "Browse...",
                        height=24,
                        width=60,
                        tooltip="Browse to a usd asset",
                        clicked_fn=partial(self.__on_file_selection, self.__usd_file_field, False),
                        enabled=True,
                    )
                    ui.Button(
                        "Set From Current Stage",
                        height=24,
                        width=110,
                        tooltip="Set asset path from current stage",
                        clicked_fn=self._set_from_current_stage,
                        enabled=True,
                    )
                    ui.Spacer(width=40)
                with ui.HStack(height=0):
                    ui.Spacer(width=20)
                    ui.Label(
                        "Temp Dir:",
                        height=24,
                        tooltip="Directory to host all intermediate files, like collected files, cache, etc\n(zip is created in the root of the directory).",
                        width=110,
                    )
                    self.__temp_dir_field = ui.StringField(
                        height=24,
                        tooltip="Directory to host all intermediate files, like collected files, cache, etc\n(zip is created in the root of the directory).",
                    )
                    if self._temp_directory:
                        self.__temp_dir_field.model.set_value(self._temp_directory)
                    ui.Spacer(width=5)
                    ui.Button(
                        "Browse...",
                        height=24,
                        width=60,
                        tooltip="Browse to temp folder",
                        clicked_fn=partial(self.__on_file_selection, self.__temp_dir_field, True),
                        enabled=True,
                    )
                    ui.Spacer(width=40)
                with ui.HStack(height=0):
                    ui.Spacer(width=20)
                    ui.Label(
                        "Optimizer Max Mean Error:",
                        height=24,
                        tooltip="Max Mean Error (float) setting for scene optimizer config",
                        width=110,
                    )
                    ui.Spacer(width=5)
                    self.__optimizer_max_error_field = ui.StringField(
                        height=24, tooltip="Max Mean Error (float) setting for scene optimizer config"
                    )
                    if self._optimizer_max_error is not None:
                        self.__optimizer_max_error_field.model.set_value(str(self._optimizer_max_error))
                    ui.Spacer(width=40)
                with ui.HStack(height=0):
                    ui.Spacer(width=20)
                    ui.Label(
                        "Optimizer Config:",
                        height=24,
                        tooltip="Config file for scene optimizer",
                        width=110,
                    )
                    self.__optimizer_config_field = ui.StringField(
                        height=24, tooltip="Config file for scene optimizer."
                    )
                    if self._optimizer_config:
                        self.__optimizer_config_field.model.set_value(self._optimizer_config)
                    ui.Spacer(width=5)
                    ui.Button(
                        "Browse...",
                        height=24,
                        width=60,
                        tooltip="Browse to config file",
                        clicked_fn=partial(
                            self.__on_file_selection, self.__optimizer_config_field, False, select_config=True
                        ),
                        enabled=True,
                    )
                    ui.Spacer(width=40)
                with ui.HStack(height=0):
                    ui.Spacer(width=20)
                    ui.Label(
                        "Kit Application Path:",
                        height=24,
                        tooltip="Path of the installed Kit application (.bat/.sh) used for UJITSO cache generation.",
                        width=110,
                    )
                    ui.Spacer(width=5)
                    self.__kit_application_path_field = ui.StringField(
                        height=24,
                        tooltip="Path of the installed Kit application (.bat/.sh) used for UJITSO cache generation.",
                    )
                    if self._kit_application_path:
                        self.__kit_application_path_field.model.set_value(self._kit_application_path)
                    ui.Spacer(width=5)
                    ui.Button(
                        "Browse...",
                        height=24,
                        width=60,
                        tooltip="Browse to Kit application location",
                        clicked_fn=partial(
                            self.__on_file_selection, self.__kit_application_path_field, select_kit_application=True
                        ),
                        enabled=True,
                    )
                    ui.Spacer(width=40)
                with ui.HStack(height=0):
                    ui.Spacer(width=20)
                    ui.Label(
                        "Zip Name:",
                        height=24,
                        tooltip="The name of the zip package (extension .zip not necessary).",
                        width=110,
                    )
                    self.__zip_name_field = ui.StringField(
                        height=24,
                        tooltip="The name of the zip package (extension .zip not necessary).",
                    )
                    ui.Spacer(width=40)
                # FIXME: Add GDN upload later when ready
                # with ui.HStack(height=0):
                #     ui.Spacer(width=20)
                #     ui.Label(
                #         "Application Id:",
                #         height=24,
                #         tooltip="The application id found on the GDN portal (Packages)",
                #         width=110,
                #     )
                #     self.__product_id_field = ui.StringField(
                #         height=24, tooltip="The application id found on the GDN portal (Packages)"
                #     )
                #     # self._product_id_field.model.set_value(default_product_id)
                #     ui.Spacer(width=40)
                # with ui.HStack(height=0):
                #     ui.Spacer(width=20)
                #     ui.Label("Token:", height=24, tooltip="Token", width=110)
                #     self.__token_field = ui.StringField(height=24, tooltip="Token")
                #     ui.Spacer(width=5)
                #     ui.Button(
                #         "Load...",
                #         height=24,
                #         width=60,
                #         tooltip="Load token from text file",
                #         clicked_fn=partial(self.__on_file_selection, self.__token_field, False, True),
                #         enabled=True,
                #     )
                #     ui.Spacer(width=40)
                ui.Spacer(height=5)
                with ui.HStack(height=0, style=UI_STYLES):
                    ui.Spacer(width=40)
                    self.__publish_button = ui.Button(
                        "Run Process", height=60, clicked_fn=self.run_process, style_type_name_override="PublishButton"
                    )
                    ui.Spacer(width=40)

                self.__phase_widget = PhasesWidget(self._phase_models)
                self.__status_bar = StatusBar()
                with ui.HStack(height=0, style=UI_STYLES):
                    self.__progress_bar = ProgressBar()
                    self.__cancel_button = ui.Button(
                        "Cancel", width=80, clicked_fn=self.cancel, style_type_name_override="PublishButton"
                    )
                self.__info_bar = InfoBar()
                ui.Spacer(height=5)

        self.__usd_file_field.model.add_value_changed_fn(lambda _: self._set_ui_state())
        self.__temp_dir_field.model.add_value_changed_fn(lambda _: self._set_ui_state())
        # self.__product_id_field.model.add_value_changed_fn(lambda _: self._set_ui_state())
        # self.__token_field.model.add_value_changed_fn(lambda _: self._set_ui_state())
        self.__zip_name_field.model.add_value_changed_fn(lambda _: self._set_ui_state())

        # If we are already in a stage, try use that as the collect path first
        self._set_from_current_stage()
        self.__status_bar._set_state_idle()
        self.__progress_bar.hide()
        self.__cancel_button.visible = False
        self.__info_bar.hide()
        self._resize()
        self._set_ui_state()

    def _phase_settings_ui(self):
        if self._phase_settings_window:
            self._phase_settings_window.visible = True
            return
        self._phase_settings_window = PhaseSettingsWindow(self._phase_models)

    def _collector_settings_ui(self):
        if self._collector_settings_window:
            self._collector_settings_window.visible = True
            return
        self._collector_settings_window = CollectorSettingsWindow(self._collector_models)

    def _validator_settings_ui(self):
        if self._validator_settings_window:
            self._validator_settings_window.visible = True
            return
        self._validator_settings_window = ValidatorSettingsWindow(self._validator_settings_model)

    def _set_ui_state(self):
        phase_enabled = False
        for model in self._phase_models.values():
            if model.get_value_as_bool():
                phase_enabled = True
                break

        if phase_enabled is False:
            self.__publish_button.enabled = False
            return

        asset_path = self.__usd_file_field.model.get_value_as_string()
        temp_path = self.__temp_dir_field.model.get_value_as_string()
        # product_id = self.__product_id_field.model.get_value_as_string()
        zip_name = self.__zip_name_field.model.get_value_as_string()
        # token = self.__token_field.model.get_value_as_string()

        if self._phase_models[Phases.COLLECT].get_value_as_bool():
            if not asset_path:
                self.__publish_button.enabled = False
                return
            else:
                result, list_entry = omni.client.stat(asset_path)
                if result != omni.client.Result.OK:
                    self.__publish_button.enabled = False
                    return

            if not temp_path:
                self.__publish_button.enabled = False
                return
            else:
                result, list_entry = omni.client.stat(temp_path)
                if result != omni.client.Result.OK:
                    self.__publish_button.enabled = False
                    return

        if self._phase_models[Phases.PACKAGE].get_value_as_bool():
            if not zip_name.strip():
                self.__publish_button.enabled = False
                return
            if not temp_path:
                self.__publish_button.enabled = False
                return
            else:
                result, list_entry = omni.client.stat(temp_path)
                if result != omni.client.Result.OK:
                    self.__publish_button.enabled = False
                    return

        # if self._phase_models[Phases.UPLOAD].get_value_as_bool():
        #     if not product_id:
        #         self.__publish_button.enabled = False
        #         return

        #     if not token:
        #         self.__publish_button.enabled = False
        #         return

        self.__publish_button.enabled = True

    def _resize(self):
        self.height = 0

    def run_process(self):
        self.__task_cancelled = False
        self.__info_bar.hide()
        self.__status_bar._set_state_busy()
        asyncio.ensure_future(self.__on_run_process_clicked())
        self._resize()

    def cancel(self):
        self.__show_prompt()

    async def _upload(self):  # pragma: no cover
        from .upload import create_build_entry

        zip_path = self._get_zip_path()
        options = _get_default_options()
        options.app_id = self.__product_id_field.model.get_value_as_string()
        options.key = self.__token_field.model.get_value_as_string()
        options.file = zip_path
        file_name = os.path.split(zip_path)[1]
        file_size = os.stat(zip_path).st_size
        self._upload_progress_model.total = file_size

        data = {
            "appId": options.app_id,
            "fileDetails": {"fileName": file_name, "fileSize": file_size},
            "target": options.target,
        }

        if options.launch_command:
            data["launchCommand"] = options.launch_command
        if options.change_version:
            data["changeVersion"] = options.change_version
        if options.semantic_version:
            data["semanticVersion"] = options.semantic_version
        if options.release_date:
            data["scheduledRelease"] = options.release_date

        success, data = create_build_entry(options.url, data, options.key)
        if not success:
            try:
                d_data = json.loads(data)
                if "message" in d_data.keys():
                    self._upload_success = success
                    self._upload_message = d_data["message"]
                    self._uploaded = True
                    return
                else:
                    self._upload_success = success
                    self._upload_message = data
                    self._uploaded = True
                    return
            except Exception:
                self._upload_success = success
                self._upload_message = data
                self._uploaded = True
                return

        upload_config = data
        asyncio.ensure_future(self._upload_file(upload_config, zip_path, file_size, options.num_threads, options.quiet))

    async def _upload_file(
        self, upload_config: Dict, file_path: str, file_size: int, num_threads: int, quiet: bool
    ):  # pragma: no cover
        from .upload import do_upload

        self.__progress_bar.show(MODE_UPLOAD)
        self._resize()
        self._uploaded = 0

        def upload_progress(chunk):
            self._uploaded += chunk
            self._upload_progress_model.set_value(self._uploaded / self._upload_progress_model.total)
            self._upload_progress_model.current = self._uploaded

        do_upload(upload_config, file_path, num_threads, callback=upload_progress)

        self._upload_success = True
        self._upload_message = "Asset collected, packaged, and uploaded"
        self._uploaded = True
        # Trying to get aiboto3 working, but I am not able to figure out what is going on....

        # session = aioboto3.Session(
        #     aws_access_key_id=upload_config['s3UploadCredentials']['accessKeyId'],
        #     aws_secret_access_key=upload_config['s3UploadCredentials']['secretAccessKey'],
        #     aws_session_token=upload_config['s3UploadCredentials']['sessionToken'],
        #     region_name=upload_config['region'])
        # s3_client = session.client('s3', config=Config(s3={'use_accelerate_endpoint': True}))

        # async with s3_client as client:
        #     try:
        #         with open(file_path, 'rb') as fd:
        #             await client.upload_fileobj(fd, upload_config['bucket'], upload_config['objectKey'])
        #     except Exception as exc:
        #         print((f"Unable to upload {file_path} to {upload_config['bucket']}:{upload_config['objectKey']}: {exc} ({type(exc)})"))
        #         raise Exception from exc

    def _set_from_current_stage(self):
        stage = _get_stage()
        if stage is None:
            return
        if not stage.GetRootLayer().realPath:
            return
        self.__info_bar.hide()
        self.__usd_file_field.model.set_value(stage.GetRootLayer().realPath)
        self._resize()

    def _get_zip_path(self):  # pragma: no cover
        temp_folder = self.__temp_dir_field.model.get_value_as_string()
        temp_folder_path = Path(temp_folder)
        temp_parent_dir = temp_folder_path.parent.as_posix()
        zip_name = self.__zip_name_field.model.get_value_as_string()
        if zip_name.endswith(".zip"):
            zip_name = zip_name.split(".zip")[0]
        if zip_name == "":
            zip_name = temp_folder_path.stem

        return f"{temp_parent_dir}/{zip_name}.zip"

    def __on_file_selection(
        self,
        target_string_field: ui.StringField,
        select_temp_folder=False,
        select_token=False,
        select_config=False,
        select_kit_application=False,
    ):  # pragma: no cover
        def __on_select(filename: str, dirname: str, selections: List[str]):
            dirname = clientutils.normalize_url(dirname)
            if dirname and dirname[-1] != "/":
                dirname += "/"

            file_url = clientutils.make_absolute_url_if_possible(dirname, filename)
            target_string_field.model.set_value(file_url)
            if target_string_field == self.__usd_file_field:
                url = omni.client.break_url(file_url)
                file_name = os.path.basename(url.path)
                file_name, _ = os.path.splitext(file_name)

                # Append checkpoint version to package name also by default
                if url.query:
                    branch_checkpoint = omni.client.get_branch_and_checkpoint_from_query(url.query)
                    if branch_checkpoint:
                        _, checkpoint = branch_checkpoint
                        if checkpoint != 0:
                            file_name += "_v" + str(checkpoint)

                self.__zip_name_field.model.set_value(file_name)

        if select_kit_application:
            file_extension_types = [("*.bat, *.sh, *.exe", "Kit Application")]
            title = "Select Kit Application"
        elif select_temp_folder:
            file_extension_types = [("*.*", "All Files")]
            title = "Select Folder"
        elif select_token:
            title = "Select Token File"
            file_extension_types = [(".txt", "TXT"), ("*.*", "All Files")]
        elif select_config:
            title = "Select Config File"
            file_extension_types = [(".json", "JSON"), ("*.*", "All Files")]
        else:
            title = "Select USD File"
            file_extension_types = [("*.usd, *.usda, *.usdc", "USD Files")]

        current_url = target_string_field.model.get_value_as_string()
        if not current_url or not current_url.strip():
            current_url = None

        file_importer = get_file_importer()
        file_importer.show_window(
            title,
            import_handler=__on_select,
            import_button_label="Select",
            filename_url=current_url,
            file_extension_types=file_extension_types,
            show_only_folders=select_temp_folder,
        )

    def __validate_inputs(self):
        if (
            not self.__usd_file_field.model.get_value_as_string()
            and self._phase_models[Phases.COLLECT].get_value_as_bool()
        ):
            return False, "Invalid USD stage file."
        if not self.__temp_dir_field.model.get_value_as_string():
            return False, "Invalid temp folder."
        if (
            not self.__zip_name_field.model.get_value_as_string()
            and self._phase_models[Phases.PACKAGE].get_value_as_bool()
        ):
            return False, "Invalid zip name."
        return True, ""

    async def __on_run_process_clicked(self):
        asset_publish_options = AssetPublishOptions()
        asset_publish_options.usd_file_path = self.__usd_file_field.model.get_value_as_string()
        asset_publish_options.temp_folder_path = self.__temp_dir_field.model.get_value_as_string()
        asset_publish_options.optimizer_config_path = self.__optimizer_config_field.model.get_value_as_string()
        asset_publish_options.optimizer_max_mean_error = self.__optimizer_max_error_field.model.get_value_as_float()
        asset_publish_options.output_zip_name = self.__zip_name_field.model.get_value_as_string()
        asset_publish_options.kit_application_path = self.__kit_application_path_field.model.get_value_as_string()

        if self._validator_settings_model:
            categories, rules = self._validator_settings_model.get_enabled_categories_and_rules()
            asset_publish_options.validator_enabled_categories = categories
            asset_publish_options.validator_enabled_rules = rules

        value = self.__optimizer_max_error_field.model.get_value_as_string().strip()
        if value:
            try:
                value = float(value)
                self._carb_settings.set(SETTINGS_MAX_ERROR, value)
                asset_publish_options.optimizer_max_mean_error = value
            except Exception:
                self.__optimizer_max_error_field.model.set_value("")
                message = "Invalid input is given, value of Max Mean Error must be float."
                carb.log_warn(message)
                nm.post_notification(message, status=nm.NotificationStatus.WARNING)

        self._carb_settings.set(SETTINGS_KIT_APPLICATION_PATH, asset_publish_options.kit_application_path)
        self._carb_settings.set(SETTINGS_LAST_CONFIG, asset_publish_options.optimizer_config_path)
        self._carb_settings.set("persistent/configurator_publisher/temp_dir", asset_publish_options.temp_folder_path)

        valid, error_msg = self.__validate_inputs()
        if not valid:
            self.__status_bar._set_state_idle()
            self.__progress_bar.hide()
            self.__info_bar.show(False, error_msg)
            self._resize()
            return

        def progress_cb(current, total, progress_stage: ProgressStage, result: bool = None, msg: str = ""):
            # if the task is cancelled, don't report furthur progress; (because in try/finally the package function will
            # still run until total progress is met)
            if self.__task_cancelled:
                return

            print(f"Progress: {current} / {total}")
            self.__progress_bar.on_collect_progress(current, total)
            self._resize()
            if current >= total and current > 0:
                # mark as complete
                self.__status_bar._set_state_idle()
                self.__progress_bar.hide()
                self.__progress_bar.stop()
                self.__cancel_button.visible = False
                self.__info_bar.show(result, msg)
                self.__publish_button.enabled = True
            else:
                if progress_stage == ProgressStage.COLLECTING:
                    self.__status_bar._set_state_busy("Collecting...")
                if progress_stage == ProgressStage.VALIDATING:
                    self.__status_bar._set_state_busy("Validating...")
                elif progress_stage == ProgressStage.BAKING_SBSAR:
                    self.__status_bar._set_state_busy("Baking SBSAR...")
                elif progress_stage == ProgressStage.OPTIMIZE_SCENE:
                    self.__status_bar._set_state_busy("Optimizing scene...")
                elif progress_stage == ProgressStage.GENERATING_UJITSO_CACHE:
                    self.__status_bar._set_state_busy("Generating UJITSO Cache...")
                elif progress_stage == ProgressStage.PACKAGING:
                    self.__status_bar._set_state_busy("PACKAGING...")

        self.__publish_button.enabled = False
        self.__cancel_button.visible = True
        self.__progress_bar.start()
        if self.__publish_clicked_fn:
            kwargs = {
                "collect_stage": self._phase_models[Phases.COLLECT].get_value_as_bool(),
                "optimize_scene": self._phase_models[Phases.OPTIMIZE].get_value_as_bool(),
                "generate_ujitso_cache": self._phase_models[Phases.CACHE].get_value_as_bool(),
                "package": self._phase_models[Phases.PACKAGE].get_value_as_bool(),
                "validate_stage": self._phase_models[Phases.VALIDATE].get_value_as_bool(),
            }

            async def __task():
                await self.__publish_clicked_fn(asset_publish_options, progress_callback=progress_cb, **kwargs)

            self.__publish_task = asyncio.create_task(__task())
            try:
                return await self.__publish_task
            except asyncio.CancelledError:
                carb.log_info(f"Cancelling task ... {self.__publish_task}")
                raise
            except Exception as e:
                raise
            finally:
                self.__publish_task = None

    def __on_cancel_clicked(self):
        if self.__publish_task is not None:
            self.__publish_task.cancel()
        self.__publish_task = None
        self.__task_cancelled = True

        self.__status_bar._set_state_idle()
        self.__info_bar.show(False, "Task cancelled.")
        self.__progress_bar.stop()
        self.__cancel_button.visible = False
        self.__publish_button.enabled = True
        self._resize()
        carb.log_info("Task is cancelled by user.")

    def __show_prompt(self):
        from omni.kit.widget.prompt import Prompt

        def on_confirm():
            self.__on_cancel_clicked()

        if not self.__prompt:
            self.__prompt = Prompt(
                title="Cancelling Current Task",
                text="Are you sure about cancelling the current running task?",
                ok_button_text="Confirm",
                cancel_button_text="Cancel",
                ok_button_fn=on_confirm,
            )
        self.__prompt.show()
        window = ui.Workspace.get_window(self.__prompt._title)
        if window:
            window.focus()

    @property
    def publish_task(self):
        return self.__publish_task
