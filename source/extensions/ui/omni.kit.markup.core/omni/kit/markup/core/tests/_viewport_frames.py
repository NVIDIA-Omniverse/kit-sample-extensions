# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio

import omni.kit.app


async def wait_for_viewport_frames(frames: int = 3):
    """Kit 111: the viewport renders each newly opened stage with OVRTX and presents its first frame ~0.4 s later
    (about 30 app updates); markup thumbnail captures complete only once frames are presented. Wait for presented
    frames after opening a stage so tests don't race that warm-up. Kit 110's test viewport has no renderer and never
    presents a frame, so only wait on Kit 111+."""
    if float(omni.kit.app.get_app().get_kit_version_short()) < 111.0:
        return
    from omni.kit.viewport.utility import get_active_viewport

    viewport = get_active_viewport()
    if viewport:
        await asyncio.wait_for(viewport.wait_for_rendered_frames(frames), timeout=30)
