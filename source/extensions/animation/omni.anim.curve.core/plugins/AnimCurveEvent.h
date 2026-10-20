// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

//// clang-format off
// #include "UsdPCH.h"
//// clang-format on

#include "AnimCurveUtils.h"
#include "IAnimCurve.h"

#include <carb/events/IEvents.h>

#define ATTR_ANIMATABLE_CHANNEL 4

typedef std::map<pxr::TfToken, omni::anim::IAnimCurve::CurveEventType[ATTR_ANIMATABLE_CHANNEL]> AnimAttrsEventType;

void PushPrimAddedEvent(carb::events::IEventStream* eventStream, const pxr::SdfPath& primPath);

void PushPrimRemovedEvent(carb::events::IEventStream* eventStream, const pxr::SdfPath& primPath);

void PushPrimUpdatedEvent(carb::events::IEventStream* eventStream, const pxr::SdfPath& primPath);

void PushPrimAttrUpdatedEvent(carb::events::IEventStream* eventStream,
                              const pxr::SdfPath& primPath,
                              const AnimAttrsEventType& aaet);

// void GetEventType(const std::map<pxr::TfToken, std::vector<int>>& eventAttrChannels,
//                   const std::map<pxr::TfToken, AnimBindingData::AttrData>& oldAttrs,
//                   const std::map<pxr::TfToken, AnimBindingData::AttrData>& attrs,
//                   AnimAttrsEventType& aaet);
