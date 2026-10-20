// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "StageUpdateBase.h"

namespace omni
{
namespace renderer
{

StageUpdateBase::UsdNoticeListener::UsdNoticeListener(StageUpdateBase* stageUpdateBase)
    : m_stageUpdateBase(stageUpdateBase)
{
    m_usdNoticeListenerKey = PXR_NS::TfNotice::Register(PXR_NS::TfCreateWeakPtr(this), &UsdNoticeListener::handleNotice);
}

StageUpdateBase::UsdNoticeListener::~UsdNoticeListener()
{
    if (m_usdNoticeListenerKey.IsValid())
    {
        PXR_NS::TfNotice::Revoke(m_usdNoticeListenerKey);
    }
}

void StageUpdateBase::UsdNoticeListener::handleNotice(const PXR_NS::UsdNotice::ObjectsChanged& objectsChanged)
{
    TRACE_FUNCTION();

    // Ignore this if the stage has changed
    PXR_NS::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage();
    if (stage != objectsChanged.GetStage())
        return;

    std::vector<PXR_NS::SdfPath> primPathsToResync, primPathsToRemove;

    for (const auto& path : objectsChanged.GetResyncedPaths())
    {
        if (path.IsAbsoluteRootOrPrimPath())
        {
            const auto& primPath = path.GetAbsoluteRootOrPrimPath();
            auto prim = stage->GetPrimAtPath(primPath);

            if (prim.IsValid())
            {
                primPathsToResync.push_back(primPath);
            }
            else
            {
                primPathsToRemove.push_back(primPath);
            }
        }
    }

    for (const auto& path : objectsChanged.GetChangedInfoOnlyPaths())
    {
        const auto& primPath = path.GetAbsoluteRootOrPrimPath();
        m_stageUpdateBase->OnPrimChange(primPath);
    }

    for (auto& primPath : primPathsToRemove)
    {
        m_stageUpdateBase->OnPrimRemove(primPath);
    }
    for (auto& primPath : primPathsToResync)
    {
        m_stageUpdateBase->OnPrimRemove(primPath);
        m_stageUpdateBase->OnPrimAdd(primPath);
    }
}

void StageUpdateBase::Startup()
{
    omni::kit::StageUpdateNodeDesc desc = { 0 };
    desc.displayName = "SceneVisualization";
    desc.order = 101; // graph is 100, need to run after that
    desc.userData = this;
    desc.onUpdate =
        [](float currentTime, float elapsedSecs, const omni::kit::StageUpdateSettings* updateSettings, void* userData)
    { static_cast<StageUpdateBase*>(userData)->Update(currentTime, elapsedSecs, updateSettings); };
    desc.onAttach = [](long int stageId, double metersPerUnit, void* userData)
    { static_cast<StageUpdateBase*>(userData)->Attach(stageId, metersPerUnit); };
    desc.onDetach = [](void* userData) { static_cast<StageUpdateBase*>(userData)->Detach(); };
    desc.onPrimOrPropertyChange = [](const PXR_NS::SdfPath& primOrPropertyPath, void* userData)
    { static_cast<StageUpdateBase*>(userData)->OnPrimOrPropertyChange(primOrPropertyPath); };

    omni::kit::StageUpdatePtr iStageUpdate =
        carb::getFramework()->tryAcquireInterface<omni::kit::IStageUpdate>()->getStageUpdate();
    CARB_ASSERT(m_StageUpdateNode == nullptr);
    m_StageUpdateNode = iStageUpdate->createStageUpdateNode(desc);
    m_usdNoticeListener.reset(new UsdNoticeListener(this));
}

void StageUpdateBase::Shutdown()
{
    m_usdNoticeListener.reset();

    omni::kit::StageUpdatePtr iStageUpdate =
        carb::getFramework()->tryAcquireInterface<omni::kit::IStageUpdate>()->getStageUpdate();
    CARB_ASSERT(m_StageUpdateNode != nullptr);
    iStageUpdate->destroyStageUpdateNode(m_StageUpdateNode);
    m_StageUpdateNode = nullptr;
}


} // namespace renderer
} // namespace omni
