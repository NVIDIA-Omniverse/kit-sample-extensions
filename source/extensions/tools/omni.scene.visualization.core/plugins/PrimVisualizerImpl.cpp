// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "UsdrtBeforeOmniGraph.h"
#include "PrimVisualizerImpl.h"

#include <omni/usd/UsdManager.h>
#include <usdrt/scenegraph/ovstage/WorldTransforms.h>

#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

namespace omni
{
namespace renderer
{

void PrimVisualizerImpl::onStartup()
{
    CARB_ASSERT(m_InternalState == nullptr);
    m_InternalState = new InternalState;

    // none of this is safe to do in the constructor/destructor because framework init hasn't completed yet
    StageUpdateBase::Startup();
    m_InternalState->sceneVisualization =
        carb::getFramework()->tryAcquireInterface<omni::renderer::ISceneVisualization>();
}
void PrimVisualizerImpl::onShutdown()
{
    CARB_ASSERT(m_InternalState != nullptr);
    CARB_ASSERT(m_InternalState->primDrawMap.empty());

    carb::getFramework()->releaseInterface(m_InternalState->sceneVisualization);
    m_InternalState->sceneVisualization = nullptr;
    StageUpdateBase::Shutdown();

    delete m_InternalState;
}

IPrimVisualizer::RegistrationHandle PrimVisualizerImpl::AddPrimDraw(PXR_NS::SdfPath primPath,
                                                                    const IDrawCallback* drawCallback)
{
    DrawData drawData;
    drawData.primPath = primPath;
    drawData.drawCallback = drawCallback;

    // postpone recording & instance creation until Update, where we have a timecode (and can calc an xform)
    drawData.recordingHandle = ISceneVisualization::INVALID_RECORDING_HANDLE;
    drawData.isDirty = true;

    size_t thisPrimdDrawMapHandle = m_InternalState->nextPrimDrawMapHandle++;
    m_InternalState->primDrawMap[thisPrimdDrawMapHandle] = drawData;
    return thisPrimdDrawMapHandle;
}

void PrimVisualizerImpl::ForcePrimDirty(RegistrationHandle handle)
{
    PrimDrawMap::iterator it = m_InternalState->primDrawMap.find(handle);
    bool found = (it != m_InternalState->primDrawMap.end());
    CARB_ASSERT(found);
    if (found)
    {
        DrawData& drawData = it->second;
        drawData.isDirty = true;
    }
}

const IPrimVisualizer::IDrawCallback* PrimVisualizerImpl::RemovePrimDraw(RegistrationHandle handle)
{
    PrimDrawMap::iterator it = m_InternalState->primDrawMap.find(handle);
    bool found = (it != m_InternalState->primDrawMap.end());
    CARB_ASSERT(found);

    const IDrawCallback* drawCallback = nullptr;
    if (found)
    {
        const DrawData& drawData = it->second;
        drawCallback = drawData.drawCallback;

        // since we postpone generation of the recording handle until Update, it might not be valid yet.
        if (drawData.recordingHandle != ISceneVisualization::INVALID_RECORDING_HANDLE)
        {
            m_InternalState->sceneVisualization->DestroyRecording(drawData.recordingHandle);
        }
        m_InternalState->primDrawMap.unsafe_erase(it);
    }

    return drawCallback;
}

IPrimVisualizer::RegistrationHandle PrimVisualizerImpl::LookupRegistrationHandle(PXR_NS::SdfPath primPath,
                                                                                 const IDrawCallback* drawCallback)
{
    for (PrimDrawMap::value_type val : m_InternalState->primDrawMap)
    {
        const DrawData& drawData = val.second;
        if (drawData.primPath == primPath && drawData.drawCallback == drawCallback)
        {
            RegistrationHandle registrationHandle = val.first;
            return registrationHandle;
        }
    }
    return INVALID_REGISTRATION_HANDLE;
}

// StageUpdateBase overrides
void PrimVisualizerImpl::Attach(long int stageId, double metersPerUnit)
{
    m_InternalState->stage = PXR_NS::UsdUtilsStageCache::Get().Find(PXR_NS::UsdStageCache::Id::FromLongInt(stageId));
    m_InternalState->usdContext = omni::usd::UsdManager::getContextFromStageId(stageId);
    m_InternalState->stageId = stageId;
    // Kit's OPENED event can precede its ovstage publication: bind lazily in Update().
    m_InternalState->ovStage = nullptr;
}

void PrimVisualizerImpl::Detach()
{
    m_InternalState->usdContext = nullptr;
    m_InternalState->stage = nullptr;
    m_InternalState->stageId = 0;
    m_InternalState->ovStage = nullptr;
}

void PrimVisualizerImpl::Update(float currentTime, float elapsedSecs, const omni::kit::StageUpdateSettings* updateSettings)
{
    // the cache is unaware of changes made to the stage (dragging a prim etc), and will continue to report the old
    // location so clear it every frame. does it still offer any value?
    m_InternalState->xformCache.Clear();

    auto& stage = m_InternalState->stage;
    auto& usdContext = m_InternalState->usdContext;

    if (!usdContext || !stage)
        return;

    double timecodesPerSecond = stage->GetTimeCodesPerSecond();
    double currentTimecode = currentTime * timecodesPerSecond;
    bool timeChanged = (currentTimecode != m_InternalState->xformCache.GetTime());
    m_InternalState->xformCache.SetTime(currentTimecode);

    // World transforms of the drawn prims. Kit 111 keeps runtime transforms (animation, physics) in its ovstage, not
    // in USD: read them there in one batch when Kit has rows for the prim, else use the authored USD transform. This
    // replaces the Fabric _worldPosition/_worldOrientation/_worldScale change tracker: a recording is regenerated
    // when its prim's world transform differs from the one it was drawn with.
    std::vector<std::string> ovPaths;
    std::vector<RegistrationHandle> ovHandles;
    for (const PrimDrawMap::value_type& val : m_InternalState->primDrawMap)
    {
        if (stage->GetPrimAtPath(val.second.primPath))
        {
            ovPaths.push_back(val.second.primPath.GetString());
            ovHandles.push_back(val.first);
        }
    }
    std::unordered_map<RegistrationHandle, PXR_NS::GfMatrix4d> ovWorld;
    if (!ovPaths.empty())
    {
        auto& ovStage = m_InternalState->ovStage;
        if (!ovStage || !ovStage->IsValid())
            ovStage = usdrt::ovstage::Stage::Attach(uint64_t(m_InternalState->stageId));
        std::vector<usdrt::ovstage::WorldTransformResult> results;
        usdrt::ovstage::Diagnostic diagnostic;
        if (ovStage && ovStage->IsReadReady() &&
            usdrt::ovstage::ReadWorldTransforms(*ovStage, ovPaths, ovStage->GetGeneration(),
                                                ovStage->GetSealedOrdinal(), &results, &diagnostic) &&
            results.size() == ovPaths.size())
        {
            for (size_t i = 0; i < results.size(); ++i)
            {
                if (results[i].diagnostic.status != usdrt::ovstage::Status::eOk)
                    continue;
                PXR_NS::GfMatrix4d world;
                static_assert(sizeof(results[i].matrix) == 16 * sizeof(double), "row-major 4x4 double");
                std::memcpy(world.data(), results[i].matrix.data(), sizeof(results[i].matrix));
                ovWorld.emplace(ovHandles[i], world);
            }
        }
    }

    for (PrimDrawMap::value_type& val : m_InternalState->primDrawMap)
    {
        // need to check transform and visibility for this currentTime
        DrawData& drawData = val.second;
        if (PXR_NS::UsdPrim prim = stage->GetPrimAtPath(drawData.primPath))
        {
            /// strange dilemma = if this is imagable, we can compute it's visibility, and seems
            //  we should hide it if invisible. but something we try to draw that is not an imagable
            //  always gets a pass?
            // if (PXR_NS::UsdGeomImageable)
            // bool visible = (prim.ComputeVisibility(xformCache.GetTime()) != UsdGeomTokens->inherited)

            if (timeChanged)
            {
                // until we can check if specific properties are timecoded, assume everything is animated
                drawData.isDirty = true;
            }

            const auto ovIt = ovWorld.find(val.first);
            const PXR_NS::GfMatrix4d transform = (ovIt != ovWorld.end()) ?
                                                     ovIt->second :
                                                     m_InternalState->xformCache.GetLocalToWorldTransform(prim);
            if (!drawData.hasDrawnTransform || transform != drawData.drawnTransform)
            {
                drawData.isDirty = true;
            }

            if (drawData.isDirty)
            {
                // might not have a recording yet if this is our first time through, this is OK
                if (drawData.recordingHandle != ISceneVisualization::INVALID_RECORDING_HANDLE)
                {
                    // if it's dirty, throw it away and regenerate below
                    m_InternalState->sceneVisualization->DestroyRecording(drawData.recordingHandle);
                    drawData.recordingHandle = ISceneVisualization::INVALID_RECORDING_HANDLE;
                }
                drawData.isDirty = false; // consume
            }

            // if prim data was dirty, or this is our first time through, generate the draw recording
            bool missingRecording = (drawData.recordingHandle == ISceneVisualization::INVALID_RECORDING_HANDLE);
            if (missingRecording)
            {
                struct DrawPrim : ISceneVisualization::IDrawCallback
                {
                    DrawPrim(DrawData& drawData) : m_DrawDataRef(drawData)
                    {
                    }
                    virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface) const override
                    {
                        m_DrawDataRef.drawCallback->Draw(drawingInterface, m_DrawDataRef.primPath);
                    }
                    DrawData& m_DrawDataRef;
                };
                DrawPrim drawPrim(drawData);
                // this `uid + 1' happens all over the place in the code... to counteract a -1 within the picking code
                // :(
                const uint32_t uid = usdContext->getGizmoUID(drawData.primPath) + 1;
                drawData.recordingHandle = m_InternalState->sceneVisualization->Record(drawPrim, uid);

                m_InternalState->sceneVisualization->EstablishDrawing(drawData.recordingHandle, transform);
                drawData.drawnTransform = transform;
                drawData.hasDrawnTransform = true;
            }
        }
        else
        {
            // prim no longer exists - leave the registration in place (caller still expected to eventually
            //  clean up), but we should make sure it no longer draws on screen.
            if (drawData.recordingHandle != ISceneVisualization::INVALID_RECORDING_HANDLE)
            {
                m_InternalState->sceneVisualization->DestroyRecording(drawData.recordingHandle);
                drawData.recordingHandle = ISceneVisualization::INVALID_RECORDING_HANDLE;
            }
            drawData.hasDrawnTransform = false;
        }
    }
}


void PrimVisualizerImpl::OnPrimOrPropertyChange(const PXR_NS::SdfPath& primOrPropertyPath)
{
    // this is fairly inefficient, but easy.
    for (PrimDrawMap::value_type& val : m_InternalState->primDrawMap)
    {
        // TODO: if prim path matches exactly, make dirty. else if a prefix (parent),
        //  dirty transform/visibility
        DrawData& drawData = val.second;
        if (drawData.primPath.HasPrefix(primOrPropertyPath))
        {
            // primOrPropertyPath seems to always be a prim path. if it were a property path,
            //  we could check if it were visibility only, and avoid the isDirty nuclear option
            //  (which completely regenerates the drawing recording).

            drawData.isDirty = true;
        }
    }
}

void PrimVisualizerImpl::OnPrimRemove(const PXR_NS::SdfPath& primPath)
{
    // if a prim is removed, we should stop any attempts to draw it.
    for (PrimDrawMap::value_type& val : m_InternalState->primDrawMap)
    {
        DrawData& drawData = val.second;
        if (drawData.primPath == primPath)
        {
            // we need to leave this record here so we can hand it back to the caller on Remove
            m_InternalState->sceneVisualization->DestroyRecording(drawData.recordingHandle);
            drawData.recordingHandle = ISceneVisualization::INVALID_RECORDING_HANDLE;
        }
    }
}

} // namespace renderer
} // namespace omni
