# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""Script to batch process USD files with Scene Optimizer operations"""

import argparse
from pathlib import Path

import carb
import omni
import omni.usd
from pxr import Sdf, UsdGeom, UsdShade, UsdUtils

usd_context = omni.usd.get_context()


def remove_prim_spec(layer: Sdf.Layer, prim_spec_path):
    prim_spec = layer.GetPrimAtPath(prim_spec_path)
    if not prim_spec:
        return False

    if prim_spec.nameParent:
        name_parent = prim_spec.nameParent
    else:
        name_parent = layer.pseudoRoot

    if not name_parent:
        return False

    name = prim_spec.name
    if name in name_parent.nameChildren:
        del name_parent.nameChildren[name]

    return True


def optimize_files_in_dir(input_dir, output_dir, default_optimizer_json, input_glob="*.usd,*.usda,*.usdc"):
    """Runs optimization configurations over all USD files in directory"""

    patterns = input_glob.split(",")
    input_files = []
    for ext in patterns:
        input_files.extend(Path(input_dir).rglob(ext))

    for i, input_file in enumerate(input_files):
        # we are doing the optimization in place
        output_file = str(input_file)
        input_file = str(input_file)

        if not omni.usd.get_context().open_stage(input_file):
            continue

        stage = omni.usd.get_context().get_stage()
        root_layer = stage.GetRootLayer()

        all_prim_paths = []
        old_prim_spec_properties = {}
        for prim in stage.Traverse():
            # Filter prims to only optimize prims defined in the opened USD file.
            if not prim.IsA(UsdGeom.Mesh) and not prim.IsA(UsdShade.Material) and not prim.IsA(UsdShade.Shader):
                continue

            prim_spec = root_layer.GetPrimAtPath(prim.GetPath())
            if (
                prim_spec
                and prim_spec.specifier == Sdf.SpecifierDef
                and not prim_spec.hasPayloads
                and not prim_spec.hasReferences
            ):
                all_prim_paths.append(prim.GetPath())
            else:
                if not prim_spec:
                    old_prim_spec_properties[prim.GetPath()] = None
                else:
                    old_prim_spec_properties[prim.GetPath()] = set(list(prim_spec.properties.keys()))

        if not all_prim_paths:
            carb.log_info(f"++ [{i}/{len(input_files)}] Skip Optimizing {input_file} as no interested prims found.")
            continue

        carb.log_info(f"++ [{i}/{len(input_files)}] Optimizing {input_file} > {output_file}")
        context = omni.scene.optimizer.core.ExecutionContext()
        context.usdStageId = UsdUtils.StageCache().Get().Insert(stage).ToLongInt()
        context.generateReport = 1
        context.captureStats = 1

        # If a config file exists for a specific file use that instead of default input
        optimizer_json_file = Path(Path(input_file).parent, Path(input_file).stem + ".json")

        if optimizer_json_file.is_file():
            config_file = optimizer_json_file
        else:
            config_file = default_optimizer_json
        myArgs = {"jsonFile": str(config_file)}

        message = f"Optimizing file {input_file} with config {config_file}"
        print(message)
        carb.log_info(message)
        omni.kit.commands.execute("SceneOptimizerJsonParser", context=context, args=myArgs)
        context = None

        # FIXME: Optimizer cannot run optimization per USD file, which will also optimize meshes
        # from payloads/references. This is a WA for now to clear that.
        with Sdf.ChangeBlock():
            for prim_path, properties in old_prim_spec_properties.items():
                if properties is None:
                    remove_prim_spec(root_layer, prim_path)
                else:
                    prim_spec = root_layer.GetPrimAtPath(prim_path)
                    if prim_spec:
                        to_remove_properties = []
                        for p in prim_spec.properties.keys():
                            if str(p) not in properties:
                                to_remove_properties.append(p)

                        for p in to_remove_properties:
                            del prim_spec.properties[p]

        # Export stage to a new file
        stage.GetRootLayer().Export(output_file)

        # Close each stage to avoid kit crashes
        omni.usd.get_context().close_stage()


def main():
    parser = argparse.ArgumentParser(
        description="Optimize USD files in a directory.",
        epilog="Example: /path/to/kit --enable 'omni.scene.optimizer.core' --enable 'omni.usd' --exec 'python_script_name.py /path/to/input /path/to/output /path/to/config.json --input_glob=*.usd' ",
    )
    parser.add_argument("input_dir", help="Directory containing input files")
    parser.add_argument("output_dir", help="Directory to save optimized files")
    parser.add_argument("json_config", help="JSON configuration file for the optimizer")
    parser.add_argument("--input_glob", default="*", help="Glob pattern to match input files (default: *)")

    args = parser.parse_args()

    try:
        optimize_files_in_dir(args.input_dir, args.output_dir, args.json_config, input_glob=args.input_glob)
    finally:
        omni.kit.app.get_app().post_quit(0)


if __name__ == "__main__":
    main()
