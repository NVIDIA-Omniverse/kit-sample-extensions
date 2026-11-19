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
from pxr import UsdUtils

usd_context = omni.usd.get_context()


def optimize_files_in_dir(input_dir, output_dir, optimizer_json, input_glob="*"):
    """Runs optimization configurations over all USD files in single directory"""

    input_files = list(Path(input_dir).glob(input_glob))

    for i, input_file in enumerate(input_files):
        output_file = Path(output_dir, input_file.name)
        output_file = str(output_file)
        input_file = str(input_file)

        if not omni.usd.get_context().open_stage(input_file):
            raise ValueError(f"Could not open file {input_file}")

        stage = omni.usd.get_context().get_stage()

        # Check to see if native prims exist along side payloads or references
        for prim in stage.Traverse():
            # check to see if prim is a payload or reference
            if not (prim.HasAuthoredPayloads() or prim.HasAuthoredReferences()):
                carb.log_warn(f"++ [{i}/{len(input_files)}] Optimizing {input_file} > {output_file}")

                context = omni.scene.optimizer.core.ExecutionContext()
                context.usdStageId = UsdUtils.StageCache().Get().Insert(stage).ToLongInt()
                context.generateReport = 1
                context.captureStats = 1

                # If a config file exists for a specific file use that instead of default input
                optimizer_json_file = Path(input_dir, Path(input_file).stem + ".json")

                if optimizer_json_file.is_file():
                    myArgs = {"jsonFile": str(optimizer_json_file)}
                else:
                    myArgs = {"jsonFile": optimizer_json}

                omni.kit.commands.execute("SceneOptimizerJsonParser", context=context, args=myArgs)

            # Export stage to a new file
            stage.GetRootLayer().Export(output_file)

            # Close each stage to avoid kit crashes
            omni.usd.get_context().close_stage()
            break


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

    optimize_files_in_dir(args.input_dir, args.output_dir, args.json_config, input_glob=args.input_glob)


if __name__ == "__main__":
    main()
