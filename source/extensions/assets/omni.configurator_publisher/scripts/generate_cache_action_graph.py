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
import time

import carb
import omni.client
import omni.kit.app
import omni.kit.async_engine
import omni.usd
from pxr import Usd

# max wait time if we found an action graph named cache generation
MAX_WAIT_TIME = 3600  # 1 hour
# max wait time if there's no action graph named cache generation found, we will send the event and wait for a shorter
# period of time, because mostly likely nothing's gonna happen (with a slight chance that their's a graph with a
# different name)
MAX_WAIT_TIME_NO_GRAPH = 100
TRIGGER_EVENT_NAME = "GenerateCache"
COMPLETION_EVENT_NAME = "CacheGenerationComplete"

completed = False

print("Starting to run action graph to generate cache...")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to USD stage.")

    try:
        options = parser.parse_args()
    except Exception as e:
        carb.log_error(str(e))
        return

    omni.kit.async_engine.run_coroutine(open_stage_async(options.path))


def _has_cache_generation_graph(stage):
    """Try to find if the stage has a cache generation graph."""
    if not stage:
        return False

    found = False
    for prim in stage.TraverseAll():
        if prim.GetTypeName() != "OmniGraph":
            continue
        if prim.GetName() == "CacheGeneration":
            found = True
            break
    return found


def on_complete(event):
    print("Cache generation completed.")
    carb.log_info("Cache generation completed.")
    global completed
    completed = True


async def open_stage_async(path: str):
    async def _open_stage_internal(path):
        # Otherwise, use normal stage open.
        context = omni.usd.get_context()
        # If the stage cannot be closed
        state = context.get_stage_state()
        while not context.can_open_stage() or (
            state != omni.usd.StageState.OPENED and state != omni.usd.StageState.CLOSED
        ):
            print(f"Another stage is in progress of opening, waiting...")
            carb.log_info(f"Another stage is in progress of opening, waiting...")
            await asyncio.sleep(1.0)
            state = context.get_stage_state()

        if context.get_stage_state() == omni.usd.StageState.OPENED:
            # FIXME: Waits for asset loading to avoid crash.
            while True:
                _, files_loaded, total_files = omni.usd.get_context().get_stage_loading_status()
                if files_loaded or total_files:
                    print("Waiting for assets loading...")
                    carb.log_info("Waiting for assets loading...")
                    await asyncio.sleep(1)
                    continue
                break
            await context.close_stage_async()

        print(f"Opening stage {path}...")
        success, error = await omni.usd.get_context().open_stage_async(path)

        if not success:
            carb.log_error(f"Failed to open stage {path}: {error}.")
            print(f"Failed to open stage {path}: {error}.")
        else:
            print(f"Open stage {path} successfully.")
            carb.log_info(f"Open stage {path} successfully.")

    return_code = 0
    try:
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

        result, _ = await omni.client.stat_async(path)
        if result == omni.client.Result.OK:
            await _open_stage_internal(path)

        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        stage = omni.usd.get_context().get_stage()

        # Try to find if the graph is defined in our stage
        has_graph = _has_cache_generation_graph(stage)
        if has_graph:
            event_stream = omni.kit.app.get_app().get_message_bus_event_stream()
            # register event callback for cache generation complete
            sub = event_stream.create_subscription_to_pop_by_type(
                carb.events.type_from_string(COMPLETION_EVENT_NAME), on_complete
            )

            print("Sending event to trigger action graph...")
            event_stream.push(carb.events.type_from_string(TRIGGER_EVENT_NAME))

            wait_time = MAX_WAIT_TIME  # Around 20mins
            start_time = time.time()
            while True:
                global completed
                if completed:
                    break
                await asyncio.sleep(1.0)
                if time.time() - start_time > wait_time:
                    print("Exceeded max wait time, cache generation failed.")
                    carb.log_info("Exceeded max wait time, cache generation failed.")
                    return_code = -1
                    break
        else:
            message = "No action graph is found in the stage, skip sending cache generation event."
            print(message)
            carb.log_info(message)

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
        omni.kit.app.get_app().post_quit(return_code)


main()
