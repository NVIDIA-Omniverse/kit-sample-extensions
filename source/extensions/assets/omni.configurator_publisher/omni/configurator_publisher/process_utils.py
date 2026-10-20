# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["run_kit"]

import asyncio
import subprocess
import sys

import carb
import omni

EXTENSION_FOLDER = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)


async def _run_process(args, timeout=None, capture_stdout=False):
    return_code = 0
    fail_messages = []
    proc = None
    stdout = None

    try:
        cmd = " ".join(args)
        carb.log_info(f">>> running proces: {cmd}")
        print(f">>> running proces: {cmd}")

        async def run_proc():
            nonlocal proc
            proc = await asyncio.create_subprocess_exec(*args, stderr=subprocess.STDOUT, bufsize=0)

            await proc.wait()

            nonlocal return_code, stdout
            return_code = proc.returncode

            if capture_stdout:
                stdout = []
                async for line in proc.stdout:
                    stdout.append(line.decode(errors="replace").replace("\r\n", "\n").replace("\r", "\n"))

            proc = None

        await asyncio.wait_for(run_proc(), timeout)
    except subprocess.CalledProcessError as e:
        return_code = e.returncode
        fail_messages.append(f"subprocess.CalledProcessError was raised: {e.output}")
    except asyncio.TimeoutError:
        fail_messages.append(f"Process timed out (timeout: {timeout}). Terminating.")
        if proc:
            proc.terminate()
    except asyncio.CancelledError:
        fail_messages.append("Task cancelled. Terminating process.")
        if proc:
            proc.terminate()

    return (return_code, fail_messages, stdout)


async def run_kit(args, timeout=None, **kwargs):
    kit_file = kwargs.pop("kit_file", f"{EXTENSION_FOLDER}/data/default.kit")
    kit_application = kwargs.pop("kit_application", None)
    log_file_path = kwargs.pop("log_file", None)

    if kit_application is None:
        launch_args = [sys.argv[0], kit_file] + args
    else:
        # FIXME: This is a somewhat temporary solution for this, because asking the user to choose a kit file to execute
        # is hard, but using the .bat directly causes issue when trying to terminate the subprocess
        import os
        import shlex

        app_dir = os.path.dirname(kit_application)
        kit_file = None
        kit_exe = None
        # parse the content of the .bat file to get the kit file and kit app to use
        app_args = None
        with open(kit_application, "r") as f:
            for l in f.readlines():
                if ".kit" in l:
                    app_args = l
                    break

        if not app_args:
            msg = "Error parsing the kit application file."
            print("-" * 30)
            print(msg)
            print("-" * 30)
            return (-1, msg, None)

        is_linux = sys.platform.startswith("linux")
        script_dir = "$SCRIPT_DIR" if is_linux else "dp0"
        for app_arg in shlex.split(app_args):
            if "kit.exe" in app_arg:
                kit_exe = app_arg.split(script_dir)[-1].lstrip("/")
            elif ".kit" in app_arg:
                kit_file = app_arg.split(script_dir)[-1].lstrip("/")
            elif is_linux and "/kit" in app_arg:
                kit_exe = app_arg.split(script_dir)[-1].lstrip("/")

        if not kit_file or not kit_exe:
            msg = "No kit file found from the kit application file."
            print("-" * 30)
            print(msg)
            print("-" * 30)
            return (-1, msg, None)

        launch_args = [os.path.join(app_dir, kit_exe), os.path.join(app_dir, kit_file)] + args

    if log_file_path:
        launch_args += [f"--/log/file={log_file_path}"]

    launch_args += [
        "--/log/flushStandardStreamOutput=1",
        "--/app/fastShutdown=1",
        "--/crashreporter/gatherUserStory=0",
        "--/app/file/ignoreUnsavedOnExit=true",
        "--/app/content/emptyStageOnStart=false",
        "--/app/auto_load_usd=''",  # WA for USD Player XR as it uses this setting as default stage load.
        "--no-window",
    ]

    paths = carb.settings.get_settings().get("/app/exts/folders") or []
    for folder in paths:
        launch_args.extend(["--ext-folder", folder])

    return await _run_process(launch_args, timeout, **kwargs)
