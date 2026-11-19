import asyncio
import os
from typing import Dict, List, Union

import carb
import omni.client.utils as clientutils
import omni.kit.asset_converter as asset_converter
import omni.kit.notification_manager as nm
import omni.kit.window.content_browser as content
import omni.usd
from omni.kit.asset_converter import OmniClientWrapper
from omni.kit.widget.prompt import PromptButtonInfo, PromptManager
from pxr import Sdf

from .progress_popup import ProgressPopup
from .utils import Utils

__all__ = ["BuiltinImporter"]


class BuiltinImporter:
    def on_startup(self):
        self._asset_converter = asset_converter.get_instance()
        self._waiting_popup_convert = None
        self._waiting_popup_upload = None
        self._upload_future = None

    def on_shutdown(self):
        if self._waiting_popup_convert:
            self._waiting_popup_convert.destroy()

        if self._waiting_popup_upload:
            self._waiting_popup_upload.destroy()

        try:
            self._upload_future.cancel()
            self._upload_future = None
        except Exception as _:
            pass

    def _show_waiting_popup_convert(self):
        if not self._waiting_popup_convert:
            self._waiting_popup_convert = ProgressPopup("Converting...", status_text="Preparing...")

        self._waiting_popup_convert.status_text = "Preparing..."
        self._waiting_popup_convert.progress = 0.0
        self._waiting_popup_convert.show()

    def _show_waiting_popup_upload(self):
        if not self._waiting_popup_upload:
            self._waiting_popup_upload = ProgressPopup("Uploading...", status_text="Preparing...")

        self._waiting_popup_upload.status_text = "Uploading..."
        self._waiting_popup_upload.progress = 0.0
        self._waiting_popup_upload.show()

    async def create_import_task(
        self,
        converting_assets: bool,
        asset_absolute_paths: List[str],
        asset_relative_paths: List[str],
        output_dir: str,
        output_file_name: str,
        output_file_format: str,
        asset_upload_context: asset_converter.AssetConverterContext,
    ):
        def convert_progress_callback(progress, total):
            self._waiting_popup_convert.progress = float(progress) / total

        def get_convert_asset_output_path(absolute_path, relative_path, create_subdir):
            dirname = os.path.dirname(relative_path)
            target_output_dir = output_dir or os.path.dirname(absolute_path)
            # if output_file_name was not provided, find it from the relative path
            target_file_name = output_file_name or os.path.splitext(os.path.basename(relative_path))[0]
            if len(output_file_format) > 0:
                file_name_with_ext = target_file_name + output_file_format
            else:
                file_name_with_ext = target_file_name + ".usd"
            if not output_dir and not output_file_name:
                subdir_name = target_file_name
            elif create_subdir:
                subdir_name = target_file_name
            else:
                subdir_name = ""

            asset_export_path = os.path.join(target_output_dir, dirname, subdir_name, file_name_with_ext)
            asset_export_path = asset_export_path.replace("\\", "/")

            return asset_export_path

        current_stage_url = omni.usd.get_context().get_stage_url()
        close_and_reopen = False
        if converting_assets and len(asset_absolute_paths) == 1:
            asset_export_path = get_convert_asset_output_path(asset_absolute_paths[0], asset_relative_paths[0], False)
            if clientutils.equal_urls(current_stage_url, asset_export_path):
                confirmed = False

                def on_ok_button_clicked():
                    nonlocal confirmed
                    confirmed = True

                prompt = PromptManager.post_simple_prompt(
                    "Warning",
                    f"Target file {os.path.basename(asset_export_path)} has already been opened. Do you want to "
                    "close and re-open it after import?",
                    ok_button_info=PromptButtonInfo("CONFIRM", on_ok_button_clicked),
                    cancel_button_info=PromptButtonInfo("CANCEL"),
                )

                while prompt.is_visible():
                    await omni.kit.app.get_app().next_update_async()

                if not confirmed:
                    return {}
                else:
                    close_and_reopen = True

        if not converting_assets:
            self._show_waiting_popup_upload()
        else:
            self._show_waiting_popup_convert()

        uploaded_files = 0
        converted_assets: Dict[str, Union[str, None]] = {}
        multiple_files = len(asset_absolute_paths) > 1
        for absolute_path, relative_path in zip(asset_absolute_paths, asset_relative_paths):
            if converting_assets:
                asset_export_path = get_convert_asset_output_path(absolute_path, relative_path, multiple_files)
                if multiple_files and os.path.normpath(current_stage_url) == os.path.normpath(asset_export_path):
                    nm.post_notification(
                        f"Failed to convert file {os.path.basename(absolute_path)} as it's opened already."
                    )
                    continue

                if self._waiting_popup_convert and not self._waiting_popup_convert.is_visible():
                    break
                self._waiting_popup_convert.status_text = f"Converting {os.path.basename(absolute_path)}..."
                await OmniClientWrapper.create_folder(os.path.dirname(asset_export_path))
                writeable = await OmniClientWrapper.writeable_async(asset_export_path)
                if not writeable:
                    nm.post_notification(
                        f"Failed to convert, export path is not writeable:\n{asset_export_path}",
                        status=nm.NotificationStatus.WARNING,
                    )
                    continue
                carb.log_info(f"Importing {absolute_path} to {asset_export_path}...")

                # OM-63255: Skip import to avoid crash if it's opend in stage already.
                export_layer = Sdf.Find(asset_export_path)
                if export_layer:
                    success = True
                else:
                    converter_task = self._asset_converter.create_converter_task(
                        absolute_path,
                        asset_export_path,
                        convert_progress_callback,
                        asset_upload_context,
                        None,
                        close_and_reopen,
                    )

                    self._waiting_popup_convert.set_cancel_fn(lambda: converter_task.cancel())
                    success = await converter_task.wait_until_finished()

                if success:
                    converted_assets[absolute_path] = asset_export_path
                else:
                    nm.post_notification(
                        f"Failed to convert file {os.path.basename(absolute_path)}.\n"
                        "Please check console for more details.",
                        status=nm.NotificationStatus.WARNING,
                    )
                    converted_assets[absolute_path] = None
                self._waiting_popup_convert.set_cancel_fn(None)
                self._waiting_popup_convert.progress = 0.0
            else:
                if self._waiting_popup_upload and not self._waiting_popup_upload.is_visible():
                    break

                self._waiting_popup_upload.status_text = f"Uploading {os.path.basename(absolute_path)}..."
                asset_export_path = Utils.compute_absolute_path(output_dir, True, relative_path, False)
                carb.log_info(f"Uploading {absolute_path} to {asset_export_path}...")
                if absolute_path != asset_export_path:
                    await OmniClientWrapper.copy(absolute_path, asset_export_path)
                uploaded_files += 1
                self._waiting_popup_upload.progress = float(uploaded_files) / len(asset_absolute_paths)

        if not converting_assets and self._waiting_popup_upload:
            self._waiting_popup_upload.hide()
        elif converting_assets and self._waiting_popup_convert:
            self._waiting_popup_convert.hide()

        self._refresh_current_directory()

        return converted_assets

    def _refresh_current_directory(self):
        content_window = content.get_content_window()
        content_window.refresh_current_directory()
