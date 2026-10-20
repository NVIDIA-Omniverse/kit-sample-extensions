# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["ProgressStage", "collect_and_package"]

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Callable, List

import carb
import omni.client
import omni.client.utils as clientutils
import omni.kit.app
from omni.kit.usd.collect import Collector, CollectorException

from .asset_publish_options import AssetPublishOptions
from .path_utils import PathUtils
from .process_utils import run_kit

try:
    from usd.schema.sbsar import SbsarMaterialAPI
except ImportError:
    SbsarMaterialAPI = None
from pxr import Sdf, Usd

from .enums import CollectorSwitches, ProgressStage
from .ext_utils import get_enabled_collector_extension_version

EXTENSION_DIR = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
UJITSO_CACHE_FOLDER_NAME = "cache"
DEFAULT_OPTIMIZER_CONFIG = f"{EXTENSION_DIR}/data/default_scene_optimizer_config.json"
KIT_FILE_OPTIMIZER = f"{EXTENSION_DIR}/data/optimizer.kit"
KIT_FILE_VALIDATOR = f"{EXTENSION_DIR}/data/validator.kit"
OPTIMIZER_MAX_ERROR_DEFAULT = 0.01
SETTINGS_LAST_PACKAGE_DIR = "persistent/configurator_publisher/last_package_dir"
SETTINGS_LAST_CONFIG = "persistent/configurator_publisher/optimizer/last_config_path"
SETTINGS_MAX_ERROR = "persistent/configurator_publisher/optimizer/max_mean_error"
SETTINGS_KIT_APPLICATION_PATH = "persistent/configurator_publisher/kit_application_path"


async def _get_temp_folder(temp_folder_path):
    result, stat = await omni.client.stat_async(temp_folder_path)

    if result != omni.client.Result.OK or not (stat.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN):
        carb.log_error(f"Temp folder {temp_folder_path} doesn't exist.")
        return ""

    temp_folder_path = clientutils.normalize_url(temp_folder_path)
    if temp_folder_path[-1] != "/":
        temp_folder_path += "/"
    return temp_folder_path


async def _get_stage_path(usd_file_path):
    result, _ = await omni.client.stat_async(usd_file_path)
    if result != omni.client.Result.OK:
        carb.log_error(f"Failed to collect stage {usd_file_path} as it doesn't exist.")
        return ""

    usd_file_path = clientutils.normalize_url(usd_file_path)
    return usd_file_path


async def _rename_stage_root(target_stage_root, default_asset_name=AssetPublishOptions.DEFAULT_ASSET_NAME):
    new_name = clientutils.make_absolute_url_if_possible(target_stage_root, default_asset_name)
    extension = PathUtils.get_extension_from_url(target_stage_root)
    new_name += extension
    if not clientutils.equal_urls(target_stage_root, new_name):
        result, _ = await omni.client.move_async(target_stage_root, new_name)
        if result != omni.client.Result.OK:
            carb.log_error(f"Failed to rename {target_stage_root} to {new_name}.")
            return None
    return new_name


async def _async_write(content: str, url: str):
    content = bytes(content.encode("utf-8"))
    carb.log_info(f"Writing {url}...")
    success = False
    try:
        result = await omni.client.write_file_async(url, content)
        if result != omni.client.Result.OK:
            carb.log_warn(f"Cannot write {url}, error code: {result}.")
        else:
            success = True
    except Exception as e:
        carb.log_warn(f"Cannot write {url}: {str(e)}.")
    finally:
        carb.log_info(f"Writing {url} done...")

    return success


async def _async_read(url: str):
    carb.log_info(f"Reading {url}...")
    try:
        result, _, content = await omni.client.read_file_async(url)
        if result == omni.client.Result.OK:
            return memoryview(content).tobytes().decode("utf-8")
        else:
            carb.log_warn(f"Cannot read {url}, error code: {result}.")
    except Exception as e:
        carb.log_warn(f"Cannot read {url}: {str(e)}.")
    finally:
        carb.log_info(f"Reading {url} done.")
    return None


async def collect(usd_file_path, package_dir, baking_sbsar=True, progress_callback=None):
    setting_values = {}
    for switch in CollectorSwitches:
        setting_path = f"persistent/configurator_publisher/{switch.value}"
        value = carb.settings.get_settings().get(setting_path) or False
        setting_values[switch] = value

    collector_ext_version = get_enabled_collector_extension_version()
    if collector_ext_version >= (2, 2, 14):
        from omni.kit.usd.collect import DefaultPrimOnlyOptions

        collector = Collector(
            usd_file_path,
            package_dir,
            default_prim_only=setting_values[CollectorSwitches.DEFAULT_PRIM_ONLY],
            default_prim_option=DefaultPrimOnlyOptions.ALL_LAYERS,
            convert_usda_to_usdc=setting_values[CollectorSwitches.ASCII_TO_BINARY],
            flat_collection=setting_values[CollectorSwitches.FLAT_COLLECTION],
        )
    elif collector_ext_version >= (2, 2, 12):
        collector = Collector(
            usd_file_path,
            package_dir,
            convert_usda_to_usdc=setting_values[CollectorSwitches.ASCII_TO_BINARY],
            flat_collection=setting_values[CollectorSwitches.FLAT_COLLECTION],
        )
    else:
        collector = Collector(
            usd_file_path, package_dir, flat_collection=setting_values[CollectorSwitches.FLAT_COLLECTION]
        )

    target_stage_root = None
    all_sbsar_files = set()
    source_target_mapping = None

    def __finished_callback():
        nonlocal target_stage_root, source_target_mapping

        # FIXME: Fix collect tool to return stage root
        # _source_target_path_mapping records all mapping from source file path collected to target file path.
        target_stage_root = collector._source_target_path_mapping.get(usd_file_path, None)

        # FIXME: It accesses private variable to get all sbsar assets.
        for _, target_file_path in collector._source_target_path_mapping.items():
            ext = PathUtils.get_extension_from_url(target_file_path)
            if ext == ".sbsar":
                all_sbsar_files.add(target_file_path)

        # OMPRW-412: Dump collector mapping result to a temp file for later phase to use
        # We have to copy it as in old version of collector, _source_target_path_mapping will
        # be released after finish_callback is returned.
        source_target_mapping = collector._source_target_path_mapping.copy()

    try:
        progress_callback()
        await collector.collect(progress_callback, __finished_callback)
    except CollectorException as e:
        carb.log_error(f"Failed to collect stage {usd_file_path}: {str(e)}.")
        return None, set(), None

    collector.destroy()

    # OMPRW-412: inspect collector path results and copy over scene optimizer configs
    # next to their collected result if there are any.
    if source_target_mapping:
        try:
            carb.log_info("Copying scene optimizer configs...")
            success = await copy_optimizer_config(
                source_target_mapping, usd_file_path, AssetPublishOptions.DEFAULT_ASSET_NAME
            )
        except Exception:
            success = False
    else:
        success = False

    if not success:
        carb.log_error("Failed to copy scene optimizer configs.")
        return None, set(), None

    # Some frames to release for python gc.
    for _ in range(10):
        await omni.kit.app.get_app().next_update_async()

    # Rename once collection is done as GDN requires the entry USD to be with specified name.
    target_stage_root = await _rename_stage_root(target_stage_root)
    if target_stage_root is None:
        carb.log_error(f"Failed to rename collected stage.")

        return None, set(), None

    if baking_sbsar:
        target_stage = Usd.Stage.Open(target_stage_root)
    else:
        target_stage = None

    return target_stage, all_sbsar_files, target_stage_root


async def run_validator(
    collect_folder: str, categories: List[str], rules: List[str], log_file_path=None, kit_file=None
):
    if not categories and not rules:
        return

    args = ""
    for c in categories:
        args += f" -c {c}"

    for r in rules:
        args += f" -r {r}"

    asset_validator_core_path = carb.tokens.get_tokens_interface().resolve("${omni.asset_validator.core}/")
    return_code, fail_messages, stdout = await run_kit(
        [
            "--enable",
            "omni.asset_validator.core",
            "--/log/fileLogLevel=error",
            "--exec",
            f"{EXTENSION_DIR}/scripts/omni_asset_validator.py --fix -d 0 {args} {collect_folder}",
        ],
        log_file=log_file_path,
        kit_file=kit_file,
    )

    return (return_code, fail_messages, stdout)


async def bake_sbsar(target_stage, current_progress=None, progress_callback=None):  # pragma: no cover
    for prim in target_stage.TraverseAll():
        sbsar_api = SbsarMaterialAPI(prim)
        if not sbsar_api:
            continue

        sbsar_path = sbsar_api.GetSbsarPayloadPath().replace(":SDF_FORMAT_ARGS:payload=1", "")
        url = omni.client.break_url(sbsar_path)
        sbsar_path = url.path
        if not sbsar_path:
            continue

        if progress_callback and current_progress is not None:
            current_progress += 1
            progress_callback()
        sbsar_params = prim.GetMetadata("sbsarParameters")
        current_res_index = sbsar_api.GetSbsarinfoResolutionIndexAttr().Get()
        resolution = None
        for v in SbsarMaterialAPI.SbsarBakeResolution.allValues:
            if current_res_index == v:
                resolution = v.name

        sbsar_baking_folder = clientutils.make_absolute_url_if_possible(sbsar_path, "sbsar_baked/")

        carb.log_info(
            f"Exporting Adobe Substance Archive {sbsar_path} to {sbsar_baking_folder} at resolution {resolution}"
        )

        res = SbsarMaterialAPI.BakeSbsarFile(
            sbsar_path, sbsar_baking_folder, "__default__", getattr(SbsarMaterialAPI, resolution), 1, sbsar_params
        )

        refs_and_layers = omni.usd.get_composed_references_from_prim(prim)
        for old_ref, layer in refs_and_layers:
            absolute_url = clientutils.make_absolute_url_if_possible(layer.identifier, old_ref.assetPath)
            if clientutils.equal_urls(absolute_url, sbsar_path):
                new_ref_path = res.GetOutputFile()
                new_ref_path = clientutils.make_relative_url_if_possible(
                    target_stage.GetRootLayer().identifier, new_ref_path
                )
                new_ref = Sdf.Reference(assetPath=new_ref_path, primPath=old_ref.primPath)
                carb.log_info(f"Replacing reference {old_ref} with {new_ref}")

                with omni.kit.undo.disabled():
                    omni.kit.commands.execute(
                        "ReplaceReference",
                        stage=target_stage,
                        prim_path=str(prim.GetPath()),
                        old_reference=old_ref,
                        new_reference=new_ref,
                    )

                # Remove useless sbsar file
                await omni.client.delete_async(sbsar_path)

                break

    target_stage.Save()


async def copy_optimizer_config(path_mapping, usd_stage_path, stage_root_profile_name):
    # Copy optimization profile to target folder
    target_usd_file = path_mapping.get(usd_stage_path, None)
    if not target_usd_file:
        return False

    # find config json file if any
    for src_file, target_file_path in path_mapping.items():
        ext = PathUtils.get_extension_from_url(src_file)
        if ext in (".usd", ".usda", ".usdc"):
            config = src_file.rsplit(".", 1)[0] + ".json"
            result, _ = await omni.client.stat_async(config)
            if result == omni.client.Result.OK:
                # copy config json to destination
                if src_file == usd_stage_path:
                    dest_path = clientutils.make_absolute_url_if_possible(
                        target_usd_file, f"{stage_root_profile_name}.json"
                    )
                else:
                    dest_path = target_file_path.rsplit(".", 1)[0] + ".json"

                try:
                    result = await omni.client.copy_async(config, dest_path, omni.client.CopyBehavior.OVERWRITE)
                    if result != omni.client.Result.OK:
                        carb.log_error(f"Cannot copy from {config} to {dest_path}, error code: {result}.")
                        return False
                    carb.log_info(f"Copied config file {config} to {dest_path}.")
                except Exception as e:
                    carb.log_error(f"Cannot copy from {config} to {dest_path}, error: {str(e)}.")
                    return False

    return True


async def replace_max_mean_error(config, value):
    content = await _async_read(config)
    if content is None:
        carb.log_error(f"Failed to load config: {config}")
        return
    original_config = json.loads(content)
    for item in original_config:
        if "maxMeanError" in item:
            item["maxMeanError"] = value
            break
    await _async_write(json.dumps(original_config), config)
    carb.log_info(f"Updated maxMeanError to {value}.")
    print(f"Updated maxMeanError to {value}.")


async def collect_and_package(
    publish_options: AssetPublishOptions, progress_callback: Callable[[int, int, ProgressStage], None] = None, **kwargs
):
    """Collect and package stage as a zip package."""
    collect_stage = kwargs.get("collect_stage", True)
    validate_stage = kwargs.get("validate_stage", True)
    baking_sbsar = kwargs.get("baking_sbsar", True)
    optimize_scene = kwargs.get("optimize_scene", True)
    generate_ujitso_cache = kwargs.get("generate_ujitso_cache", True)
    create_zip = kwargs.get("package", True)
    package_dir = None
    output_path = ""
    all_sbsar_files = set()
    target_stage = None
    target_stage_root = None

    task_success = True
    error_message = None

    def report_progress(progress=None, total=None, result=None, msg=None):
        nonlocal current_progress, total_progress, progress_stage, task_success, error_message

        # Sets them for refreshing progress from collect tool
        if progress:
            current_progress = progress

        if total:
            # Plus 2 for zipping and generating UJITSO cache
            total_progress = total + 2

        if current_progress > total_progress:
            current_progress = total_progress

        if result is not None:
            task_success = result

        if msg is not None:
            error_message = msg

        if progress_callback:
            progress_callback(current_progress, total_progress, progress_stage, result=task_success, msg=error_message)

    carb.log_info(f"Starting to process stage {publish_options.usd_file_path}")

    progress_stage = ProgressStage.COLLECTING
    current_progress = 0
    total_progress = 0
    if collect_stage:
        total_progress += 1
    if validate_stage:
        total_progress += 1
    if baking_sbsar:
        total_progress += 1
    if optimize_scene:
        total_progress += 1
    if generate_ujitso_cache:
        total_progress += 1

    try:
        temp_folder_path = await _get_temp_folder(publish_options.temp_folder_path)
        if not temp_folder_path:
            current_progress += 1
            report_progress(result=False, msg="Temp folder doesn't exist.")
            return False, None

        # default to True because if we are running single steps, we don't want to wait and check if this is written
        mapping_file_generated = True

        # Step 1: Collect stage into temp folder
        usd_file_path = await _get_stage_path(publish_options.usd_file_path)
        if collect_stage:
            if not usd_file_path:
                current_progress += 1
                report_progress(result=False, msg="Stage doesn't exist.")
                return False, None

            stage_name = usd_file_path.rsplit(".", 1)[0].split("/")[-1]
            package_dir = clientutils.make_absolute_url_if_possible(
                temp_folder_path, f"{stage_name}_collected_{str(uuid.uuid4())[:8]}/"
            )
            carb.settings.get_settings().set(SETTINGS_LAST_PACKAGE_DIR, package_dir)

            target_stage, all_sbsar_files, target_stage_root = await collect(
                usd_file_path, package_dir, baking_sbsar=baking_sbsar, progress_callback=report_progress
            )
            output_path = target_stage_root
            if not target_stage_root:
                current_progress += 1
                report_progress(result=False, msg="Failed to collect stage.")
                return False, None
        else:
            # Try to use the last collected package path if we are not running collect.
            package_dir = carb.settings.get_settings().get(SETTINGS_LAST_PACKAGE_DIR)
            if package_dir:
                result, _ = await omni.client.stat_async(package_dir)
                if result != omni.client.Result.OK:
                    package_dir = None
                else:
                    target_stage_root = clientutils.make_absolute_url_if_possible(
                        package_dir, f"{AssetPublishOptions.DEFAULT_ASSET_NAME}.usd"
                    )
                    result, _ = await omni.client.stat_async(target_stage_root)
                    if result != omni.client.Result.OK:
                        target_stage_root = None

        if not package_dir:
            carb.log_error("Asset Path file is not inside a collection folder. Unable to run process.")
            current_progress += 1
            report_progress(
                result=False, msg="Asset Path file is not inside a collection folder. Unable to run process."
            )
            return False, None

        package_dir = clientutils.normalize_url(package_dir)
        if package_dir[-1] != "/":
            package_dir += "/"

        if validate_stage:
            progress_stage = ProgressStage.VALIDATING
            report_progress()
            categories = publish_options.validator_enabled_categories
            rules = publish_options.validator_enabled_rules
            if not categories and not rules:
                carb.log_error(
                    "Validate step is enabled, however, no valid categories or rules are specified to run it."
                )
                report_progress(result=False, msg="No valid categories or rules are specified for validator.")

                return False, None

            log_file_path = clientutils.make_absolute_url_if_possible(package_dir, "validator.log")
            return_code, error_messages, _ = await run_validator(
                package_dir, categories, rules, log_file_path, kit_file=KIT_FILE_VALIDATOR
            )
            current_progress += 1
            if return_code != 0:
                carb.log_error(f"Failed to validate scene:{error_messages}.")
                report_progress(
                    result=False,
                    msg=f"Failed to validate scene, return code: {return_code}. See {log_file_path} for more details.",
                )
                return False, None
            else:
                carb.log_info("Finished validate scene.")
                report_progress()

        # Step 2: Baking sbsar files and replacing all references.
        if baking_sbsar and all_sbsar_files and SbsarMaterialAPI:  # pragma: no cover
            if not target_stage and target_stage_root:
                target_stage = Usd.Stage.Open(target_stage_root)

            if not target_stage:
                carb.log_error("Cannot bake SBSAR materials as collected stage doesn't exist.")
                current_progress += 1
                report_progress(result=False, msg="Cannot bake SBSAR materials as collected stage doesn't exist.")
                return False, None

            progress_stage = ProgressStage.BAKING_SBSAR
            total_progress += len(all_sbsar_files) + 1
            report_progress()
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            await bake_sbsar(target_stage, current_progress=current_progress, progress_callback=report_progress)
            report_progress()

        # Release stage to remove temp dir
        target_stage = None

        # Step 3: Run scene optimize
        if optimize_scene:
            carb.log_info("Starting to optimize scene...")
            progress_stage = ProgressStage.OPTIMIZE_SCENE
            report_progress()

            # If config file is still not specified, use default one.
            config = publish_options.optimizer_config_path
            if not config:
                carb.log_warn("No config file specified, using the default config.")
                # copy the default optimizer config to our temp package location
                config = omni.client.combine_urls(package_dir, "global_optimizer_config.json")
                result = await omni.client.copy_async(
                    DEFAULT_OPTIMIZER_CONFIG, config, omni.client.CopyBehavior.OVERWRITE
                )
                if result != omni.client.Result.OK:
                    carb.log_warn(f"Cannot copy from {DEFAULT_OPTIMIZER_CONFIG} to {config}, error code: {result}.")
                    # in the rare case where config failed on copy, use the extension data path as fallback
                    config = DEFAULT_OPTIMIZER_CONFIG

            # update maxMeanError based on user input if the value is not default
            if not publish_options.optimizer_config_path and publish_options.optimizer_max_mean_error is not None:
                await replace_max_mean_error(config, publish_options.optimizer_max_mean_error)

            log_file_path = clientutils.make_absolute_url_if_possible(package_dir, "optimizer.log")
            return_code, fail_messages, _ = await run_kit(
                [
                    "--enable",
                    "omni.scene.optimizer.core",
                    "--exec",
                    f"{EXTENSION_DIR}/scripts/optimize_scene.py {package_dir} {package_dir} "
                    f"{config} --input_glob=*.usd,*.usda,*.usdc",
                ],
                log_file=log_file_path,
                kit_file=KIT_FILE_OPTIMIZER,
            )

            if return_code != 0:
                carb.log_error(f"Failed to optimize scene: {fail_messages}.")
                current_progress += 1
                report_progress(
                    result=False,
                    msg=f"Failed to optimize scene, return code: {return_code}. See {log_file_path} for more details.",
                )
                return False, None
            else:
                carb.log_info("Finished optimizing scene.")
                output_path = package_dir
                current_progress += 1
                report_progress()

        # Step 3: Generating DerivedDataCache if necessary in another process.
        if generate_ujitso_cache:
            carb.log_info("Starting to generate UJITSO cache...")

            progress_stage = ProgressStage.GENERATING_UJITSO_CACHE
            report_progress()

            if not target_stage_root:
                error = "Cannot find the package directory to run cache generation on."
                carb.log_error(error)
                current_progress += 1
                report_progress(result=False, msg=error)

                return False, None

            if not publish_options.kit_application_path:
                carb.log_error("Cannot find the kit application to generate cache.")
                current_progress += 1
                report_progress(result=False, msg="Cannot find the kit application to generate cache.")
                return False, None

            derived_cache_folder = clientutils.make_absolute_url_if_possible(package_dir, UJITSO_CACHE_FOLDER_NAME)

            log_file_path = clientutils.make_absolute_url_if_possible(package_dir, "ujitso.log")
            return_code, fail_messages, stdout = await run_kit(
                [
                    "--enable",
                    "omni.ujitso.client",
                    "--/app/useFabricSceneDelegate=true",
                    "--/renderer/multiGpu/enabled=false",
                    "--/renderer/multiGpu/activeGpus=0",
                    "--/app/window/fullscreen=false",
                    "--/rtx-transient/resourcemanager/enableTextureStreaming=true",
                    "--/rtx/materialDb/syncLoads=true",
                    "--/rtx/hydra/materialSyncLoads=true",
                    "--/rtx/hydra/perMaterialSyncLoads=true",
                    "--/rtx/hydra/geometrySyncLoads=true",
                    "--/omni.kit.plugin/syncUsdLoads=true",
                    "--/rtx-transient/hydra/geometrystreaming/syncLoad=true",
                    "--/rtx-transient/resourcemanager/loaderPostProcessVramThreshold=2.0",
                    "--/rtx-transient/resourcemanager/UJITSO/GPUMemoryBudgetMB=512",
                    "--/UJITSO/enabled=true",
                    "--/UJITSO/textures=true",
                    "--/UJITSO/geometry=true",
                    "--/UJITSO/materials=true",
                    f'--/UJITSO/datastore/localCachePath="{derived_cache_folder}"',
                    f'--/UJITSO/writeCacheWithAssetRoot="{package_dir}"',
                    "--exec",
                    f"{EXTENSION_DIR}/scripts/cache_variants.py {target_stage_root}",
                ],
                kit_application=publish_options.kit_application_path,
                log_file=log_file_path,
            )

            if return_code != 0:
                carb.log_error(f"Failed to generate UJITSO cache:{fail_messages}, {return_code}.")
                current_progress += 1
                report_progress(
                    result=False,
                    msg=f"Failed to generate UJITSO cache, return code: {return_code}. See {log_file_path} for more details.",
                )
                return False, None
            else:
                carb.log_info("Finished to generate UJITSO cache.")
                output_path = derived_cache_folder
                current_progress += 1
                report_progress()

        # Step 4: Zip all files
        # Before zipping, we need to rename the root USD.
        if create_zip:
            target_zip_path = clientutils.make_absolute_url_if_possible(
                temp_folder_path, publish_options.output_zip_name
            )
            ext = PathUtils.get_extension_from_url(target_zip_path)
            if ext not in [".zip", ".7z", ".usdz"]:
                target_zip_path += ".zip"
            progress_stage = ProgressStage.PACKAGING
            report_progress()
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            absolute_paths, relative_paths = await PathUtils.list_folder_async(package_dir)
            total_progress += len(absolute_paths)
            report_progress()

            batch = 0
            import zipfile

            with zipfile.ZipFile(
                str(target_zip_path), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5
            ) as zip_writer:
                for absolute_path, relative_path in zip(absolute_paths, relative_paths):
                    _, ext = os.path.splitext(relative_path)
                    if ext == ".log" or os.path.basename(relative_path).startswith("Streamer Server Log"):
                        continue

                    try:
                        zip_writer.write(absolute_path, relative_path)
                    except Exception as e:
                        carb.log_warn(f"Failed to package file {absolute_path}: {str(e)}")
                        continue

                    current_progress += 1
                    report_progress()

                    if batch >= 5:
                        # Don't block main thread
                        batch = 0
                        await omni.kit.app.get_app().next_update_async()
                    else:
                        batch += 1

            zip_writer = None
            output_path = target_zip_path

        current_progress += 1
        progress_stage = ProgressStage.DONE
        report_progress()
    finally:
        # Finalize it no matter it's failed or not to ensure status is reported.
        progress_stage = ProgressStage.DONE
        while current_progress < total_progress:
            current_progress += 1
            report_progress()

    carb.log_info(f"Finished to collect and package stage to {output_path}")

    return True, output_path
