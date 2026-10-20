// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "PreUsdHeaders.h"
#include <pxr/usd/usdUtils/stageCache.h>
#include <pxr/usd/usd/notice.h>
#include <pxr/usd/usd/attributeQuery.h>
#include "PostUsdHeaders.h"
// clang-format on

#include "AttrQueryCache.h"
#define USD_CONTEXT_INCLUDES
#include <omni/usd/UsdContext.h>

UsdAttrQueryCache* UsdAttrQueryCache::singleton = nullptr;

UsdAttrQueryCache& UsdAttrQueryCache::get()
{
    return *singleton;
}

UsdAttrQueryCache::UsdAttrQueryCache()
{
    singleton = this;

    auto usdContext = omni::usd::UsdContext::getContext();
    auto ed = carb::getCachedInterface<carb::eventdispatcher::IEventDispatcher>();
    const static carb::RStringKey name("AttrQueryCache");

    // Subscribe to stage open event using observeEvent
    stageEventSub[0] = ed->observeEvent(name, carb::eventdispatcher::kDefaultOrder,
                                        usdContext->stageEventName(omni::usd::StageEventType::eOpened),
                                        [this](const carb::eventdispatcher::Event& event) { onStageOpened(); });
    // Subscribe to stage close event using observeEvent
    stageEventSub[1] = ed->observeEvent(name, carb::eventdispatcher::kDefaultOrder,
                                        usdContext->stageEventName(omni::usd::StageEventType::eClosed),
                                        [this](const carb::eventdispatcher::Event& event) { onStageClosing(); });
}

UsdAttrQueryCache::~UsdAttrQueryCache()
{
    singleton = nullptr;
    TfNotice::Revoke(noticeKey);
}

void UsdAttrQueryCache::onStageOpened()
{
    stage = omni::usd::UsdContext::getContext()->getStage();
    noticeKey = TfNotice::Register(TfCreateWeakPtr(this), &UsdAttrQueryCache::handleNotice, stage);
}

void UsdAttrQueryCache::onStageClosing()
{
    stage.Reset();
    attrQueries.clear();
    TfNotice::Revoke(noticeKey);
}

void UsdAttrQueryCache::handleNotice(const UsdNotice::ObjectsChanged& objectsChanged)
{
    std::set<SdfPath> resyncAttrs;

    for (auto& path : objectsChanged.GetResyncedPaths())
    {
        for (auto& entry : attrQueries)
        {
            if (entry.first.HasPrefix(path))
                resyncAttrs.insert(entry.first);
        }
    }

    for (auto& path : resyncAttrs)
    {
        attrQueries.erase(path);
    }
}

const UsdAttributeQuery& UsdAttrQueryCache::getAttrQuery(const SdfPath& path)
{
    auto itr = attrQueries.find(path);
    if (itr != attrQueries.end())
        return itr->second;

    auto& attrQuery = attrQueries[path];
    if (stage)
    {
        attrQuery = UsdAttributeQuery(stage->GetAttributeAtPath(path));
    }

    return attrQuery;
}
