# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

# The following line is used to mark the start of the code that is to be pulled into the documentation
# example-begin simready_explorer_api_sample
import asyncio
from typing import List, Tuple

import omni.kit.app
import omni.simready.explorer as sre
import omni.usd
from pxr import Gf, Sdf, Usd


async def main():
    # 1. Find all residential wooden chair assets.
    # We use multiple search terms, some will be matched in the tags, others in the asset names
    assets = await sre.find_assets(search_words=["residential", "chair", "wood"])
    print(f"Found {len(assets)} chairs")

    # 2. Prepare to configure the assets
    # All SimReady Assets have a Physics behavior, which is implemented as a
    # variantset named PhysicsVariant. To enable rigid body physics on an asset,
    # this variantset needs to be set to "RigidBody".
    variants = {"PhysicsVariant": "RigidBody"}

    # 3. Add all assets found in step (1) to the current stage as a payload
    added_prim_paths: List[Sdf.Path] = []
    for i, asset in enumerate(assets):
        pos = -200 + 200 * i
        res, prim_path = sre.add_asset_to_stage(
            asset.main_url, position=Gf.Vec3d(pos, 0, -pos), variants=variants, payload=True
        )
        if res:
            print(f"Added '{prim_path}' from '{asset.main_url}'")

    # 4. Find an ottoman
    assets = await sre.find_assets(search_words=["ottoman"])
    print(f"Found {len(assets)} ottomans")

    # 5. Replace the first chair with an ottoman
    if assets and added_prim_paths:
        usd_context: omni.usd.UsdContext = omni.usd.get_context()
        stage: Usd.Stage = usd_context.get_stage() if usd_context else None
        await omni.kit.app.get_app().next_update_async()
        res, prim_path = sre.add_asset_to_stage_using_prims(
            usd_context,
            stage,
            assets[0].main_url,
            variants=variants,
            replace_prims=True,
            prim_paths=[added_prim_paths[0]],
        )
        if res:
            print(f"Replaced assets '{added_prim_paths[0]}' with '{prim_path}' from '{assets[0].main_url}'")


asyncio.ensure_future(main())
# example-end simready_explorer_api_sample
