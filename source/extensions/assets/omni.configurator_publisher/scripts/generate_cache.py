# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import argparse
import asyncio

import carb
import omni.client
import omni.kit.app
import omni.kit.async_engine
import omni.usd
from pxr import Usd

MAX_VARIANT_PERMUTATION_LIMIT = 1000000


print("Starting to generate cache...")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to USD stage.")

    try:
        options = parser.parse_args()
    except Exception as e:
        carb.log_error(str(e))
        return

    omni.kit.async_engine.run_coroutine(open_stage_async(options.path))


def get_prims_with_variant_sets(stage):
    """Get all prims with variant sets"""
    if not stage:
        return []

    return [prim.GetPath() for prim in stage.Traverse() if prim.GetVariantSets().GetNames()]


async def open_stage_async(path: str):
    async def _open_stage_internal(path):
        # Otherwise, use normal stage open.
        print(f"Opening stage {path}...")
        success, error = await omni.usd.get_context().open_stage_async(path)

        if not success:
            carb.log_error(f"Failed to open stage {path}: {error}.")
            print(f"Failed to open stage {path}: {error}.")
        else:
            print(f"Open stage {path} successfully.")
            carb.log_info(f"Open stage {path} successfully.")

    try:
        result, _ = await omni.client.stat_async(path)
        if result == omni.client.Result.OK:
            await _open_stage_internal(path)

        for _ in range(1, 3):
            await omni.kit.app.get_app().next_update_async()

        print("Go through all variants...")

        stage = omni.usd.get_context().get_stage()
        count = 0
        for prim in Usd.PrimRange(stage.GetPseudoRoot()):
            variant_sets = prim.GetVariantSets()
            variant_sets_names = prim.GetVariantSets().GetNames()
            if not variant_sets:
                continue

            for variant_set_name in variant_sets_names:
                usd_variant_set = variant_sets.GetVariantSet(variant_set_name)
                variant_names = usd_variant_set.GetVariantNames()

                for variant_name in variant_names:
                    print(
                        f"Permutation [ {count+1} ]:  Applying Variant {prim} --> {variant_set_name} : {variant_name}"
                    )
                    carb.log_info(
                        f"Permutation [ {count+1} ]: Applying Variant {prim} --> {variant_set_name} : {variant_name}"
                    )
                    usd_variant_set.SetVariantSelection(variant_name)

                count = count + 1
                if count > MAX_VARIANT_PERMUTATION_LIMIT:
                    print(
                        f"Permutation of variants has exceeded limit of {MAX_VARIANT_PERMUTATION_LIMIT}, "
                        "skipping the rest for now."
                    )
                    carb.log_warn(
                        f"Permutation of variants has exceeded limit of {MAX_VARIANT_PERMUTATION_LIMIT}, "
                        "skipping the rest for now."
                    )
                    break

        print(f"A total of [ {count} ] permutations gerenated.")
        carb.log_info(f"A total of [ {count} ] permutations gerenated.")

        # Wait for stage loading
        print("Waiting for stage loading...")
        carb.log_info("Waiting for stage loading...")
        while True:
            _, files_loaded, total_files = omni.usd.get_context().get_stage_loading_status()
            if files_loaded or total_files:
                print("Waiting for assets loading...")
                carb.log_info("Waiting for assets loading...")
                await asyncio.sleep(1)
                continue
            break
    finally:
        omni.kit.app.get_app().post_quit(0)


main()
