# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.usd
import pydantic
from omni.services.core import routers

router = routers.ServiceAPIRouter()


class UsdStageModel(pydantic.BaseModel):
    uri: str = pydantic.Field(..., title="USD stage to open", description="USD Stage to open")


@router.post("/stage", description="Open a USD stage", summary="Open a USD stage")
async def open_stage(data: UsdStageModel):
    uri = data.uri
    success, error = await omni.usd.get_context().open_stage_async(uri)
    if not success:
        return {"status": f"failed to open {uri}: {str(error)}"}

    return {"status": "success"}


@router.get("/stage", description="Get the current stage", summary="Get the current stage")
def get_current_stage():
    uri = omni.usd.get_context().get_stage_url()
    return {"file_uri": uri}
