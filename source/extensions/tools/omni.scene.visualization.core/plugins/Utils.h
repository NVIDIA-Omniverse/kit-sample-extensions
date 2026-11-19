// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

// clang-format off
#include "UsdPCH.h"
// clang-format on

namespace omni
{
namespace renderer
{

static const pxr::TfToken t_sceneVisualizationAPI("OmniSceneVisualizationAPI");
static const pxr::TfToken t_drawWireframe("omni:scene:visualization:drawWireframe");
static const pxr::TfToken t_drawPoints("omni:scene:visualization:drawPoints");
static const pxr::TfToken t_drawNormals("omni:scene:visualization:drawNormals");
static const pxr::TfToken t_drawTangents("omni:scene:visualization:drawTangents");
static const pxr::TfToken t_useVertexColor("omni:scene:visualization:useVertexColor");

}
}
