// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "SceneVisualizationImpl.h"

namespace omni
{
namespace renderer
{

void SceneVisualizationImpl::onStartup()
{
    CARB_ASSERT(m_InternalState == nullptr);

    m_InternalState = new InternalState;
    m_InternalState->m_DebugDraw = carb::getFramework()->tryAcquireInterface<omni::renderer::IDebugDraw>();
}
void SceneVisualizationImpl::onShutdown()
{
    CARB_ASSERT(m_InternalState != nullptr);

    CARB_ASSERT(m_InternalState->m_DrawRecordings.empty());

    carb::getFramework()->releaseInterface(m_InternalState->m_DebugDraw);
    delete m_InternalState;
}


void SceneVisualizationImpl::DestroyRecording(RecordingHandle handle)
{
    DrawRecordings::iterator it = m_InternalState->m_DrawRecordings.find(handle);
    bool found = (it != m_InternalState->m_DrawRecordings.end());
    CARB_ASSERT(found);
    if (found)
    {
        const Recording& recording = it->second;

        // makes no sense to have an instance of invalid
        CARB_ASSERT(recording.lineBuffer != EMPTY_SIMPLEXBUFFER ||
                    recording.lineRenderInstanceBuffer == IDebugDraw::eInvalidBuffer);
        CARB_ASSERT(recording.pointBuffer != EMPTY_SIMPLEXBUFFER ||
                    recording.pointRenderInstanceBuffer == IDebugDraw::eInvalidBuffer);

        if (recording.lineBuffer != EMPTY_SIMPLEXBUFFER)
        {
            CARB_ASSERT(recording.lineBuffer != IDebugDraw::eInvalidBuffer);

            // chance we weren't actually rendering it
            if (recording.lineRenderInstanceBuffer != IDebugDraw::eInvalidBuffer)
            {
                m_InternalState->m_DebugDraw->deallocateRenderInstanceBuffer(recording.lineRenderInstanceBuffer);
            }
            m_InternalState->m_DebugDraw->deallocateLineBuffer(recording.lineBuffer);
        }
        if (recording.pointBuffer != EMPTY_SIMPLEXBUFFER)
        {
            CARB_ASSERT(recording.pointBuffer != IDebugDraw::eInvalidBuffer);

            // chance we aren't actually rendering it
            if (recording.pointRenderInstanceBuffer != IDebugDraw::eInvalidBuffer)
            {
                m_InternalState->m_DebugDraw->deallocateRenderInstanceBuffer(recording.pointRenderInstanceBuffer);
            }
            m_InternalState->m_DebugDraw->deallocatePointBuffer(recording.pointBuffer);
        }
        m_InternalState->m_DrawRecordings.erase(it);
    }
}
void SceneVisualizationImpl::EstablishDrawing(RecordingHandle handle, const Float44& matrix)
{
    DrawRecordings::iterator it = m_InternalState->m_DrawRecordings.find(handle);
    bool found = (it != m_InternalState->m_DrawRecordings.end());
    CARB_ASSERT(found);
    if (found)
    {
        Recording& recording = it->second;
        if (recording.lineBuffer != EMPTY_SIMPLEXBUFFER)
        {
            if (recording.lineRenderInstanceBuffer == IDebugDraw::eInvalidBuffer)
            {
                const size_t instanceCount = 1; // for now
                recording.lineRenderInstanceBuffer =
                    m_InternalState->m_DebugDraw->allocateRenderInstanceBuffer(recording.lineBuffer, instanceCount);
            }

            const float* matrixBegin = &matrix.rows[0].x; // FIXME: back up this crazy cast with a static_assert
            m_InternalState->m_DebugDraw->setRenderInstance(
                recording.lineRenderInstanceBuffer, 0, matrixBegin, 0x0, recording.uid);
        }

        if (recording.pointBuffer != EMPTY_SIMPLEXBUFFER)
        {
            if (recording.pointRenderInstanceBuffer == IDebugDraw::eInvalidBuffer)
            {
                const size_t instanceCount = 1;
                recording.pointRenderInstanceBuffer =
                    m_InternalState->m_DebugDraw->allocateRenderInstanceBuffer(recording.pointBuffer, instanceCount);
            }

            const float* matrixBegin = &matrix.rows[0].x; // FIXME: same as above
            m_InternalState->m_DebugDraw->setRenderInstance(
                recording.pointRenderInstanceBuffer, 0, matrixBegin, 0x0, recording.uid);
        }
    }
}

void SceneVisualizationImpl::TerminateDrawing(RecordingHandle handle)
{
    DrawRecordings::iterator it = m_InternalState->m_DrawRecordings.find(handle);
    bool found = (it != m_InternalState->m_DrawRecordings.end());
    CARB_ASSERT(found);
    if (found)
    {
        Recording& recording = it->second;
        if (recording.lineBuffer != EMPTY_SIMPLEXBUFFER)
        {
            CARB_ASSERT(recording.lineBuffer != IDebugDraw::eInvalidBuffer);
            m_InternalState->m_DebugDraw->deallocateRenderInstanceBuffer(recording.lineRenderInstanceBuffer);
            recording.lineRenderInstanceBuffer = IDebugDraw::eInvalidBuffer;
        }

        if (recording.pointBuffer != EMPTY_SIMPLEXBUFFER)
        {
            CARB_ASSERT(recording.pointBuffer != IDebugDraw::eInvalidBuffer);
            m_InternalState->m_DebugDraw->deallocateRenderInstanceBuffer(recording.pointRenderInstanceBuffer);
            recording.pointRenderInstanceBuffer = IDebugDraw::eInvalidBuffer;
        }
    }
}

void SceneVisualizationImpl::DrawImmediate(const IDrawCallback& drawFunc)
{
    ImmediateExecuteDrawingCommands drawImmediate(*m_InternalState->m_DebugDraw);
    drawFunc.Draw(drawImmediate);
}

ISceneVisualization::RecordingHandle SceneVisualizationImpl::Record(const IDrawCallback& drawFunc, const uint32_t uid)
{
    RecordDrawingCommands recordDrawingCommands(*m_InternalState->m_DebugDraw);
    drawFunc.Draw(recordDrawingCommands);

    SimplexBuffer lineBuffer = recordDrawingCommands.m_LineBuffer;
    SimplexBuffer pointBuffer = recordDrawingCommands.m_PointBuffer;

    // special case - if this call didn't actually render anything, then throw away the line. an empty
    //   line buffer eventually causes asserts down in the renderer
    bool renderedAnyLine = (recordDrawingCommands.m_NextLineIndex > 0);
    if (renderedAnyLine == false)
    {
        m_InternalState->m_DebugDraw->deallocateLineBuffer(lineBuffer);
        lineBuffer = EMPTY_SIMPLEXBUFFER;
    }
    bool renderedAnyPoint = (recordDrawingCommands.m_NextPointIndex > 0);
    if (renderedAnyPoint == false)
    {
        m_InternalState->m_DebugDraw->deallocatePointBuffer(pointBuffer);
        pointBuffer = EMPTY_SIMPLEXBUFFER;
    }

    RenderInstanceBuffer lineRenderInstance = IDebugDraw::eInvalidBuffer; // none yet
    RenderInstanceBuffer pointRenderInstance = IDebugDraw::eInvalidBuffer; // none yet
    Recording recording = { lineBuffer, pointBuffer, lineRenderInstance, pointRenderInstance, uid };

    RecordingHandle recordingHandle = m_InternalState->m_NextRecordingHandle++;
    m_InternalState->m_DrawRecordings[recordingHandle] = recording;

    return recordingHandle;
}


} // namespace renderer
} // namespace omni
