# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""
This module will run all variants in the stage that has been opened.
It will await stage loading complete before doing so and will also await stage ready for each variant that has been set.
If a caching graph is found in the stage - OmniGraph prim with the name 'CacheGeneration', it will emit the signal 'GenerateCache' for the graph to run. The graph has it's own mechanism to delay after a variant has been set.
If no graph is found, Python will be used to cycle through all variants. The StateManager is queried for each variant, until the staged has stopped loading the necessary data before moving on to the next variant.

Example Usage to generate cache (change to your local paths):
D:/Builds/kit-app-template/_build/windows-x86_64/release/kit/kit.exe D:/Builds/kit-app-template/_build/windows-x86_64/release/apps/my_company.my_usd_viewer.kit  --/UJITSO/datastore/localCachePath="C:/configurator/cache" --/UJITSO/writeCacheWithAssetRoot="C:/configurator/" --exec C:/Code/configurator-samples/scripts/cache/run_variants.py --/log/file=C:/configurator/ujitso.log --/app/auto_load_usd='C:/configurator/product_configurator_base.usd' --no-window
-- Used copy_configurator.py to copy to different folder

Example Usage to validate cache (change to your local paths):
D:/Builds/kit-app-template/_build/windows-x86_64/release/kit/kit.exe D:/Builds/kit-app-template/_build/windows-x86_64/release/apps/my_company.my_usd_viewer.kit  --/UJITSO/datastore/localCachePath="C:/moved/configurator/cache" --/UJITSO/readCacheWithAssetRoot="C:/moved/configurator/" --/UJITSO/failedDepLoadingLogging=true --exec C:/Code/configurator-samples/scripts/cache/run_variants.py --/log/file=C:/moved/configurator/cache_validation.log --/app/auto_load_usd='C:/moved/configurator/product_configurator_base.usd' --no-window
-- After this ran validate_log.py to get any invalid cache results out.
"""

import asyncio
import time

import carb
import omni.kit.app
import omni.usd
from carb.eventdispatcher import get_eventdispatcher

# max wait time if we found an action graph named cache generation
MAX_WAIT_TIME = 3600  # 1 hour
CONFIGURATOR_READY_EVENT_NAME = "ConfiguratorReady"
TRIGGER_EVENT_NAME = "GenerateCache"
COMPLETION_EVENT_NAME = "CacheGenerationComplete"
completed = False


class StateManager:
    """This class keep taps on the event stream inside the kit app. It signals when a stage is fully loaded.
    When setting variants, this class is used to query when the variant has been set and the stage is no longer busy.
    """

    def __init__(self):
        super().__init__()
        self._event_stream = omni.kit.app.get_app().get_message_bus_event_stream()
        self._dispatcher = get_eventdispatcher()
        context = omni.usd.get_context()
        self._stage_subs = [
            self._dispatcher.observe_event(
                observer_name="configurator_publisher", event_name=context.stage_event_name(event), on_event=func
            )
            for event, func in (
                (omni.usd.StageEventType.OPENING, self._on_stage_opening),
                (omni.usd.StageEventType.OPENED, self._on_stage_opened),
                (omni.usd.StageEventType.CLOSED, self._on_stage_closed),
            )
        ]
        self._event_sub = None
        self._initialized = False
        self._non_default_stage = False
        self._variant_work = False

    def _on_stage_opening(self, event: carb.eventdispatcher.Event):
        """
        Start observing RTX streaning status while stage is loading.

        Args:
            event (carb.eventdispatcher.Event): Event type
        """
        GLOBAL_RTX_STREAMING_STATUS_EVENT = "omni.streamingstatus:streaming_status"
        omni.log.verbose(
            f"Configurator Loaded Signal - OPENING STAGE - event subscription to RTX streaming manager created"
        )
        self._event_sub = self._dispatcher.observe_event(
            observer_name="streaming_status_listener",
            event_name=GLOBAL_RTX_STREAMING_STATUS_EVENT,
            on_event=self.on_msg_bus_payload,
        )

    def _on_stage_opened(self, event: carb.eventdispatcher.Event):
        """
        Evaluate if the stage is default while it has been opened.

        Args:
            event (carb.eventdispatcher.Event): Event type
        """
        omni.log.verbose(
            f"Configurator Loaded Signal - OPENED STAGE - Configurator initialization evaluation async called"
        )
        asyncio.ensure_future(self._evaluate_initialization())

    def _on_stage_closed(self, event: carb.eventdispatcher.Event):
        """
        Reset state while stage is closed.

        Args:
            event (carb.eventdispatcher.Event): Event type
        """
        omni.log.verbose(f"Configurator Loaded Signal - CLOSED STAGE - Resetting extension state")
        self._reset_state()

    def on_msg_bus_payload(self, event: carb.eventdispatcher.Event) -> None:
        """Streaming status event listener

        Args:
            event (carb.eventdispatcher.Event): Contains payload sender and type
        """
        isBusy = event.payload["isBusy"]
        if not isBusy:
            carb.log_verbose("Configurator Loaded Signal - Streaming Manager Not busy - evaluating stage for default")
            path = omni.usd.get_context().get_stage().GetRootLayer().resolvedPath.GetPathString()
            if path:
                carb.log_verbose(
                    f"Configurator Loaded Signal - Streaming Manager Not busy - Stage IS NOT default - {path}"
                )
                self._non_default_stage = True
                if self._initialized and self._non_default_stage:
                    self._variant_work = False
            else:
                carb.log_verbose(f"Configurator Loaded Signal - Streaming Manager Not busy - Stage IS default")
                self._non_default_stage = False
            carb.log_verbose(
                f"Configurator Loaded Signal - Streaming Manager Not busy - Stage initialized (weather default or not)"
            )
            self._initialized = True

    async def _evaluate_initialization(self):
        """Evaluate initialization
        If initialized and we are using a non default stage, a signal is emitted that the configurator is ready.
        Note: Even if a default stage is loaded, the initialized state is True, but the _non_default_stage is False
        """
        while not self._initialized:
            await omni.kit.app.get_app().next_update_async()
        if self._non_default_stage:
            for _ in range(2):
                await omni.kit.app.get_app().next_update_async()
            self._event_stream.push(carb.events.type_from_string(CONFIGURATOR_READY_EVENT_NAME))
            carb.log_info(f"Stage Fully Loaded - Signal Emitted name:{CONFIGURATOR_READY_EVENT_NAME}")

    def on_shutdown(self) -> None:
        """Clean up subscriptions"""
        if self._stage_subs:
            for subscribe in self._stage_subs:
                subscribe.reset()
            self._stage_subs = None
        if self._event_sub:
            self._event_sub.reset()
            self._event_sub = None

    def _reset_state(self):
        """Reset the internal state - ready for new stage to be loaded"""
        self._initialized = False
        self._non_default_stage = False
        if self._event_sub:
            self._event_sub.reset()
            self._event_sub = None
        carb.log_verbose(f"Configurator Loaded Signal - STATE RESET")

    @property
    def initialized(self) -> bool:
        """State of initialization

        Returns:
            bool: True/False
        """
        return self._initialized

    @property
    def variant_work(self) -> bool:
        """State of variant work

        Returns:
            bool: True/False
        """
        return self._variant_work

    @variant_work.setter
    def variant_work(self, value: bool) -> None:
        """State of initialization"""
        if self._variant_work == value:
            return
        self._variant_work = value


def get_prims_with_variant_sets():
    """Get all prims with variant sets"""
    context = omni.usd.get_context()
    stage = context.get_stage()
    if not stage:
        return []
    return [prim for prim in stage.Traverse() if prim.GetVariantSets().GetNames()]


def _has_cache_generation_graph(stage):
    """Find if the stage has a cache generation graph."""
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


def on_complete(event: carb.events.IEvent):
    """On completion of event

    Args:
        event (carb.events.IEvent): carb event
    """
    print("Variant run completed.")
    carb.log_info("Variant run completed.")
    global completed
    completed = True


async def run():
    """
    This function runs through all variants either through graph or Python.
    It will also evaluate the readiness of the stage before going to the next variant for the Python implementation.
    The graph has it's own delay mechanism.
    """
    return_code = 0
    state_manager = StateManager()
    while not state_manager.initialized:
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

    stage = omni.usd.get_context().get_stage()
    has_graph = _has_cache_generation_graph(stage)
    if has_graph:
        event_stream = omni.kit.app.get_app().get_message_bus_event_stream()
        # register event callback for cache generation complete
        sub = event_stream.create_subscription_to_pop_by_type(
            carb.events.type_from_string(COMPLETION_EVENT_NAME), on_complete
        )

        print("Sending event to trigger action graph...")
        carb.log_info("Sending event to trigger action graph...")
        event_stream.push(carb.events.type_from_string(TRIGGER_EVENT_NAME))

        wait_time = MAX_WAIT_TIME
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
        print("No caching graph found - Python triggering variants...")
        carb.log_info("No caching graph found - Python triggering variants...")
        prims = get_prims_with_variant_sets()
        for prim in prims:
            variant_sets = prim.GetVariantSets()
            for variant_set_name in variant_sets.GetNames():
                usd_variant_set = variant_sets.GetVariantSet(variant_set_name)
                variant_names = usd_variant_set.GetVariantNames()
                for variant_name in variant_names:
                    print(f"Setting variant for {prim} - {variant_name} - {variant_set_name}")
                    carb.log_info(f"Setting variant for {prim} - {variant_name} - {variant_set_name}")
                    state_manager.variant_work = True
                    usd_variant_set.SetVariantSelection(variant_name)
                    for _ in range(250):
                        await omni.kit.app.get_app().next_update_async()
                        if not state_manager.variant_work:
                            for _ in range(50):
                                await omni.kit.app.get_app().next_update_async()
                            carb.log_info("interupting loop - no variant work is happening")
                            break
    omni.kit.app.get_app().post_quit(return_code)


if __name__ == "__main__":
    asyncio.ensure_future(run())
