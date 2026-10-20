# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
import omni.kit.app
from omni.kit.capture.viewport import CaptureOptions
from omni.services import client
from omni.services.core import main as _main


async def _run(render_settings):
    try:
        _services = client.AsyncClient("local://", _main.get_app())
        return await _services.render.run(**render_settings)
    except Exception as exc:
        carb.log_error(exc)
    finally:
        omni.kit.app.get_app().post_quit()


def main():
    parser = argparse.ArgumentParser("Render service")

    parser.add_argument("--usd-file", type=str, help="USD file to render", default="Foo")

    parser.add_argument(
        "--render_start_delay", type=int, help="Time to wait after stage has loaded before render starts.", default=10
    )

    parser.add_argument(
        "--render_stage_load_timeout", type=int, help="Time to wait to receive stage loaded event", default=100
    )

    parser.add_argument("--load_async", action="store_true", help="Load stage async")

    options = CaptureOptions()
    for key, value in options.to_dict().items():
        parser.add_argument(f"--{key}", type=type(value), help=key, default=value)

    try:
        args = vars(parser.parse_args())
    except SystemExit:
        omni.kit.app.get_app().post_quit()
        return

    render_settings = {
        "usd_file": args.pop("usd_file"),
        "render_start_delay": args.pop("render_start_delay"),
        "load_async": args.pop("load_async"),
        "render_stage_load_timeout": args.pop("render_stage_load_timeout"),
        "render_settings": args,
    }

    try:
        asyncio.ensure_future(_run(render_settings))
    except Exception as exc:
        carb.log_error(f"Failed to run render: {exc}")


main()
