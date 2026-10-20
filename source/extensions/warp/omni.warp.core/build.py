# SPDX-FileCopyrightText: Copyright (c) 2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

HERE = os.path.dirname(__file__)
WARP_PATH = os.path.join(HERE, "warp")
WARP_BUILD_SCRIPT = os.path.join(WARP_PATH, "build_lib.py")
LAST_BUILD_FILE = os.path.join(HERE, ".last_build")


def get_tree_state() -> str:
    # Warp is a pinned source snapshot, not a nested Git checkout.
    # Inspect the source itself so exported archives need no Git or migration
    # records. Generated outputs must not invalidate the next incremental build.
    root = Path(WARP_PATH)
    if not (root / "build_lib.py").is_file():
        raise FileNotFoundError(f"Warp source is incomplete: {root / 'build_lib.py'}")
    ignored_dirs = {".git", "__pycache__", ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                    ".venv", "venv", "warp_lang.egg-info", ".idea", ".vscode", ".vs", ".history", "outputs"}
    ignored_paths = {"_build", "_repo", "_conan", "_deps", "build", "dist", "docs/_build", "warp/bin",
                     "external/llvm-project", "asv/env", "asv/results", "asv/html", "asv/warp-lang",
                     ".claude/worktrees", ".worktrees"}
    ignored_suffixes = {".pyc", ".pyo", ".so", ".dll", ".pyd", ".dylib", ".o", ".obj", ".a", ".lib",
                        ".exp", ".pdb", ".log", ".bak"}

    def walk_error(error):
        raise error

    h = hashlib.sha256(b"warp-source-state-v1\0")
    for directory, dirs, files in os.walk(root, onerror=walk_error):
        relative_dir = Path(directory).relative_to(root)
        dirs[:] = sorted(name for name in dirs
                         if name not in ignored_dirs
                         and (relative_dir / name).as_posix() not in ignored_paths
                         and not (relative_dir.parts[:1] == ("docs",) and name == "_generated"))
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() in ignored_suffixes or name in {".git", ".Python", "build_warp_time_trace.json"}:
                continue
            relative = path.relative_to(root).as_posix().encode("utf-8")
            h.update(len(relative).to_bytes(4, "big"))
            h.update(relative)
            content = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    content.update(chunk)
            h.update(content.digest())
    return h.hexdigest()


def run(
    pip_path: str,
    msvc_path: str,
    winsdk_path: str,
    cuda_path: str,
) -> int:
    key = f"{platform.system().lower()}-{platform.machine()}"
    state = get_tree_state()

    try:
        with open(LAST_BUILD_FILE) as file:
            last_build_states = json.load(file)
    except FileNotFoundError:
        last_build_states = {}

    if last_build_states.get(key, None) == state:
        # Nothing to do.
        return 0

    py_paths = (pip_path, WARP_PATH)
    py_paths_str = os.pathsep.join(py_paths)

    env = os.environ.copy()

    if env.get("PYTHONPATH", ""):
        env["PYTHONPATH"] = f"{py_paths_str}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = py_paths_str

    cmd = (sys.executable, WARP_BUILD_SCRIPT, "--cuda-path", cuda_path)

    if os.name == "nt":
        # Complete the MSVC path to include the directory with the actual MSVC version.
        msvc_root_path = os.path.join(msvc_path, "VC", "Tools", "MSVC")
        msvc_version_dirs = tuple(
            x for x in os.listdir(msvc_root_path) if os.path.isdir(os.path.join(msvc_root_path, x))
        )
        msvc_path = os.path.join(msvc_root_path, max(msvc_version_dirs))

        cmd += ("--msvc-path", msvc_path, "--sdk-path", winsdk_path)

    result = subprocess.run(cmd, env=env)
    if result.returncode:
        return result.returncode

    last_build_states[key] = state
    with open(LAST_BUILD_FILE, "w") as file:
        json.dump(last_build_states, file)

    return 0


if __name__ == "__main__":
    parser = ArgumentParser(description="Warp build script wrapper for Kit")
    parser.add_argument(
        "--pip-path", type=str, required=True, help="Path to the pip bundle necessary to run Warp's build script"
    )
    parser.add_argument("--msvc-path", type=str, required=True, help="Path to MSVC's compiler")
    parser.add_argument("--winsdk-path", type=str, required=True, help="Path to Windows SDK")
    parser.add_argument("--cuda-path", type=str, required=True, help="Path to CUDA's toolkit")
    args = parser.parse_args(sys.argv[1:])
    sys.exit(run(args.pip_path, args.msvc_path, args.winsdk_path, args.cuda_path))
