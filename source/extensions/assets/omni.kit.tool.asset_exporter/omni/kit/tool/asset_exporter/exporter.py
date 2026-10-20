import asyncio
import os
import tempfile
from pathlib import Path

import carb
import omni.client
import omni.kit.asset_converter as converter
import omni.kit.notification_manager as nm
import omni.kit.window.content_browser as content
import omni.usd
from omni.kit.tool.collect import get_instance as get_collect_instance
from omni.kit.usdz_export import usdz_export
from pxr import Usd, UsdShade, UsdUtils

from .common import BAKE_MDL_SUPPORTED, BAKE_MDL_UNSUPPORTED_MESSAGE
from .progress_popup import ProgressPopup


class Exporter:
    def on_startup(self):
        self._waiting_popup_convert = None

    def on_shutdown(self):  # pragma: no cover
        pass

    def _show_waiting_popup_convert(self):
        if not self._waiting_popup_convert:
            self._waiting_popup_convert = ProgressPopup("Converting...", status_text="Preparing...")

        self._waiting_popup_convert.status_text = "Preparing..."
        self._waiting_popup_convert.progress = 0.0
        self._waiting_popup_convert.show()

    async def _start_usd_export_internal(
        self, stage: Usd.Stage, output_path, asset_convert_context, is_collected=False
    ):
        def convert_progress_callback(progress, total):
            self._waiting_popup_convert.progress = float(progress) / total

        self._show_waiting_popup_convert()

        usd_path = stage.GetRootLayer().identifier
        usd_path = usd_path.replace("\\", "/")
        usd_file_name = os.path.basename(usd_path)
        self._waiting_popup_convert.status_text = f"Exporting {usd_file_name}..."
        carb.log_info(f"Exporting {usd_path} to {output_path}...")

        stage_cache = UsdUtils.StageCache.Get()
        stage_id = stage_cache.GetId(stage).ToString()
        if not stage_id:
            new_stage = True
            stage_id = stage_cache.Insert(stage)
        else:
            new_stage = False

        if not stage_id:
            carb.log_error(f"Failed to export {usd_path} since it's not cached in UsdStageCache.")
            nm.post_notification(
                f"Failed to export {os.path.basename(usd_file_name)} since it's not cached in UsdStageCache.",
                status=nm.NotificationStatus.WARNING,
            )
            return

        is_usdz = Path(output_path).suffix.lower() == ".usdz"

        if is_usdz:
            converter_task = wrapped_usdz_export(usd_path, output_path)
        else:
            if not is_collected:
                converter_task = converter.get_instance().create_converter_task(
                    stage_id, output_path, convert_progress_callback, asset_convert_context
                )
            else:
                # for collected stage, we use the path to converter
                converter_task = converter.get_instance().create_converter_task(
                    usd_path, output_path, convert_progress_callback, asset_convert_context
                )
            self._waiting_popup_convert.set_cancel_fn(lambda: converter_task.cancel())

        try:
            if is_usdz:
                results = await asyncio.gather(converter_task)
                success = results[0]
            else:
                success = await converter_task.wait_until_finished()
            if not success:
                nm.post_notification(
                    f"Failed to export {usd_file_name}.\n" "Please check console for more details.",
                    status=nm.NotificationStatus.WARNING,
                )
        finally:
            self._waiting_popup_convert.set_cancel_fn(None)
            self._waiting_popup_convert.progress = 0.0
            self._waiting_popup_convert.hide()
            self._refresh_current_directory()

            if new_stage:
                stage_cache.Erase(stage_id)

    def create_usd_export_task(self, stage: Usd.Stage, output_path, asset_converter_context):
        usd_path = stage.GetRootLayer().identifier
        usd_path = usd_path.replace("\\", "/")
        usd_file_name = os.path.basename(usd_path)

        # OM-44603: collect the usd_path and open the collected path in a new stage
        # and then bake it's material and then export the baked stage
        # Check the file is usd and is exist
        if asset_converter_context.bake_mdl_material and not BAKE_MDL_SUPPORTED:
            # Kit 111 EA1: say so instead of silently exporting unbaked materials.
            carb.log_warn(BAKE_MDL_UNSUPPORTED_MESSAGE)
            nm.post_notification(BAKE_MDL_UNSUPPORTED_MESSAGE, status=nm.NotificationStatus.WARNING)
            asset_converter_context.bake_mdl_material = False
        if asset_converter_context.bake_mdl_material and not stage.GetRootLayer().anonymous:
            collect_instance = get_collect_instance()
            manager = omni.kit.app.get_app().get_extension_manager()
            manager.set_extension_enabled_immediate("omni.mdl.distill_and_bake", True)
            with tempfile.TemporaryDirectory() as tmp_dir:

                def export_internal():
                    try:
                        import omni.mdl.distill_and_bake

                        collected_file = os.path.join(os.path.realpath(tmp_dir), usd_file_name)
                        new_stage = Usd.Stage.Open(collected_file)
                        for prim in new_stage.Traverse():
                            if UsdShade.Material(prim):
                                distiller = omni.mdl.distill_and_bake.MdlDistillAndBake(
                                    prim, baking_to_new_material=asset_converter_context.export_mdl_gltf_extension
                                )
                                distiller.distill()
                        new_stage.Save()
                        asyncio.ensure_future(
                            self._start_usd_export_internal(new_stage, output_path, asset_converter_context, True)
                        )
                    except ImportError:
                        return asyncio.ensure_future(
                            self._start_usd_export_internal(stage, output_path, asset_converter_context)
                        )

                from omni.kit.usd.collect.collector import FlatCollectionTextureOptions

                collect_instance._start_collecting(
                    usd_path, tmp_dir, False, True, False, FlatCollectionTextureOptions.FLAT, export_internal
                )
        else:
            return asyncio.ensure_future(self._start_usd_export_internal(stage, output_path, asset_converter_context))

    def _refresh_current_directory(self):
        content_window = content.get_content_window()
        if content_window:
            content_window.refresh_current_directory()


async def wrapped_usdz_export(identifier, export_path):
    await usdz_export(identifier, export_path)

    result, _ = await omni.client.stat_async(export_path)
    if result == omni.client.Result.OK:
        return True
    else:
        return False
