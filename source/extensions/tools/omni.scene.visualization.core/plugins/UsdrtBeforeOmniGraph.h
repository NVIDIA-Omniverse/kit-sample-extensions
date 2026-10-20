// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

// Include this before any OmniGraph header in a translation unit that also uses usdrt.
//
// Kit 111's omni/graph/core/ogn/Types.h ends with a global `using namespace omni::graph::core;`, and
// omni::graph::core now declares its own Type, BaseDataType and AttributeRole. usdrt headers that name
// those types unqualified (after `using namespace omni::fabric;`) are ambiguous when parsed after an
// OmniGraph header. This plugin now uses Kit's usdrt.scenegraph.ovstage facade (the Fabric-backed usdrt
// provider is not loaded next to omni.graph in Kit 111); its headers are parsed first for the same reason.
#include <usdrt/scenegraph/ovstage/Stage.h>
#include <usdrt/scenegraph/ovstage/WorldTransforms.h>
