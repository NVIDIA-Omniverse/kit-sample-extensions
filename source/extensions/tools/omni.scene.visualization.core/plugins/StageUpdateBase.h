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

#include <omni/kit/IStageUpdate.h>
#include <omni/scenevisualization/ISceneVisualization.h>
#include <omni/usd/UsdContext.h>

namespace omni
{
namespace renderer
{


class StageUpdateBase
{
protected:
    class UsdNoticeListener : public PXR_NS::TfWeakBase
    {
    public:
        UsdNoticeListener(StageUpdateBase* stageUpdateBase);
        virtual ~UsdNoticeListener();
        void handleNotice(const PXR_NS::UsdNotice::ObjectsChanged& objectsChanged);

    private:
        StageUpdateBase* m_stageUpdateBase;
        PXR_NS::TfNotice::Key m_usdNoticeListenerKey;
    };

    void Startup();
    void Shutdown();

    virtual void Attach(long int stageId, double metersPerUnit)
    {
    }
    virtual void Detach()
    {
    }
    virtual void Update(float currentTime, float elapsedSecs, const omni::kit::StageUpdateSettings* updateSettings)
    {
    }
    virtual void OnPrimAdd(const PXR_NS::SdfPath& primPath)
    {
    }
    virtual void OnPrimOrPropertyChange(const PXR_NS::SdfPath& primOrPropertyPath)
    {
    }
    virtual void OnPrimRemove(const PXR_NS::SdfPath& primPath)
    {
    }
    virtual void OnPrimChange(const PXR_NS::SdfPath& primPath)
    {
    }

    // respond to usd events and stage events
    omni::kit::StageUpdateNode* m_StageUpdateNode = nullptr;
    std::unique_ptr<UsdNoticeListener> m_usdNoticeListener;
};

} // namespace renderer
} // namespace omni
