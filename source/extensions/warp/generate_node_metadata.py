# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to generate the nodes.json file that lists all the nodes for an OmniGraph extension."""

import json
import os
import sys
from argparse import ArgumentParser


def run(
    ext_path: str,
) -> int:
    # fmt: off
    ogn_file_paths = tuple(
        os.path.join(dir_path, file_name)
        for (dir_path, _, file_names) in os.walk(ext_path, followlinks=True)
        for file_name in file_names if file_name.endswith(".ogn")
    )
    # fmt: on

    metadata = {}
    for file_path in ogn_file_paths:
        with open(file_path) as file:
            contents = json.load(file)
            key = next(iter(contents.keys()))
            data = contents[key]
            metadata[key] = {
                "description": data.get("description", ""),
                "version": data.get("version", 1),
                "uiName": data.get("uiName", ""),
                "language": data.get("language", ""),
            }

    ogn_path = os.path.join(ext_path, "ogn")
    os.makedirs(ogn_path, exist_ok=True)

    out_path = os.path.join(ogn_path, "nodes.json")
    with open(out_path, "w") as file:
        json.dump({"nodes": metadata}, file, indent=4)

    return 0


if __name__ == "__main__":
    parser = ArgumentParser(description="Warp build script wrapper for Kit")
    parser.add_argument("--extension-path", type=str, help="Path to the extension")
    args = parser.parse_args(sys.argv[1:])
    sys.exit(run(args.extension_path))
