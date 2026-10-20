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

#include "StageUpdateBase.h"

#include <omni/scenevisualization/ISceneVisualization.h>
#include <tbb/concurrent_unordered_map.h>
#include <usdrt/scenegraph/ovstage/Stage.h>

#include <memory>

namespace omni
{
namespace renderer
{

class PrimVisualizerImpl : public IPrimVisualizer, public StageUpdateBase
{
public:
    void onStartup();
    void onShutdown();
    RegistrationHandle AddPrimDraw(PXR_NS::SdfPath primPath, const IDrawCallback* drawCallback) override;
    void ForcePrimDirty(RegistrationHandle handle) override;
    const IDrawCallback* RemovePrimDraw(RegistrationHandle handle) override;
    RegistrationHandle LookupRegistrationHandle(PXR_NS::SdfPath primPath, const IDrawCallback* drawCallback) override;
    // StageUpdateBase overrides
    void Attach(long int stageId, double metersPerUnit) override;
    void Detach() override;
    void Update(float currentTime, float elapsedSecs, const omni::kit::StageUpdateSettings* updateSettings) override;
    void OnPrimOrPropertyChange(const PXR_NS::SdfPath& primOrPropertyPath) override;
    void OnPrimRemove(const PXR_NS::SdfPath& primPath) override;

private:
    struct DrawData
    {
        const IDrawCallback* drawCallback = nullptr;

        PXR_NS::SdfPath primPath;

        // recording handle. instance has no handle (yet)
        ISceneVisualization::RecordingHandle recordingHandle = ISceneVisualization::INVALID_RECORDING_HANDLE;

        // update this via TfNotice. maybe instead of dirty, we just immediately throw away the instance
        bool isDirty = false;

        // World transform the current recording was established with; a different one dirties the recording.
        PXR_NS::GfMatrix4d drawnTransform{ 1.0 };
        bool hasDrawnTransform = false;
    };
    typedef tbb::concurrent_unordered_map<RegistrationHandle, DrawData> PrimDrawMap;

    // same reason as Impl above, need to keep this all
    struct InternalState
    {
        PXR_NS::UsdStageWeakPtr stage = nullptr;
        long int stageId = 0;
        // Kit's ovstage binding for the stage (Kit 111 runtime transforms). Resolved lazily: Kit can publish it
        // after the stage opens, and replaces it when a provider generation is revoked.
        usdrt::ovstage::StageRefPtr ovStage = nullptr;
        omni::usd::UsdContext* usdContext = nullptr;

        PrimDrawMap primDrawMap;
        size_t nextPrimDrawMapHandle = 1;

        ISceneVisualization* sceneVisualization = nullptr;

        PXR_NS::UsdGeomXformCache xformCache;
    };
    InternalState* m_InternalState = nullptr;
};

} // namespace renderer
} // namespace omni
