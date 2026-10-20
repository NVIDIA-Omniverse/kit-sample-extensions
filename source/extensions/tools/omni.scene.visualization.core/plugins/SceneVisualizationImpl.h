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

#include "carb/dictionary/IDictionary.h"

#include <carb/Interface.h>
#include <carb/InterfaceUtils.h>

#include <omni/renderer/IDebugDraw.h>
#include <omni/scenevisualization/ISceneVisualization.h>

namespace omni
{
namespace renderer
{

class SceneVisualizationImpl : public ISceneVisualization
{
public:
    void onStartup();
    void onShutdown();
    virtual void DestroyRecording(RecordingHandle handle) override;
    virtual void EstablishDrawing(RecordingHandle handle, const Float44& matrix) override;
    virtual void TerminateDrawing(RecordingHandle handle) override;
    virtual void DrawImmediate(const IDrawCallback& drawFunc);
    virtual RecordingHandle Record(const IDrawCallback& drawFunc, const uint32_t uid);

    // base drawing interface - does the heavy lifting, leaves communicating with IDebugDraw to subclasses
    class DrawingImpBase : public IDrawingInterface
    {
    public:
        // TODO: refactor these virtuals into a policy so functions can be inlined
        virtual void OnPoint(const carb::Float3& pointPos, uint32_t pointColor, float width) = 0;
        virtual void OnLine(const carb::Float3& startPos,
                            uint32_t startColor,
                            float startWidth,
                            const carb::Float3& endPos,
                            uint32_t endColor,
                            float endWidth) = 0;

        virtual void DrawPointsImp(size_t pointCount, const IPointDataFetcher& iPointFetcher) override
        {
            for (size_t i = 0; i < pointCount; ++i)
            {
                carb::Float3 pt;
                carb::ColorRgba color;
                float width;
                iPointFetcher.Fetch(i, pt, color, width);
                uint32_t colorAsInt = ConvertColor(color);

                OnPoint(pt, colorAsInt, width);
            }
        }


        virtual void DrawLinesImp(size_t lineCount, const ILineDataFetcher& iLineFetcher) override
        {
            for (size_t i = 0; i < lineCount; ++i)
            {
                carb::Float3 pt1;
                carb::Float3 dir;
                carb::ColorRgba color;
                float width;
                iLineFetcher.Fetch(i, pt1, dir, color, width); // TODO: should we allow 2 colors?

                const carb::Float3& pt2 = { pt1.x + dir.x, pt1.y + dir.y, pt1.z + dir.z };

                uint32_t colorAsInt = ConvertColor(color);

                OnLine(pt1, colorAsInt, width, pt2, colorAsInt, width);
            }
        }

        virtual void DrawLineStripImp(size_t pointCount, const ILineStripDataFetcher& iLineFetcher) override
        {
            if (pointCount > 1)
            {
                // prime the loop
                carb::Float3 lastPoint;
                carb::ColorRgba lastColorF4;
                float lastWidth;
                iLineFetcher.Fetch(0, lastPoint, lastColorF4, lastWidth);
                uint32_t lastColor = ConvertColor(lastColorF4);

                for (size_t i = 1; i < pointCount; ++i)
                {
                    carb::Float3 nextPoint;
                    carb::ColorRgba nextColorF4;
                    float nextWidth;
                    iLineFetcher.Fetch(i, nextPoint, nextColorF4, nextWidth);
                    uint32_t nextColor = ConvertColor(nextColorF4);

                    OnLine(lastPoint, lastColor, lastWidth, nextPoint, nextColor, nextWidth);

                    lastPoint = nextPoint;
                    lastColor = nextColor;
                    lastWidth = nextWidth;
                }
            }
        }

        virtual void DrawIndexedLinesImp(size_t lineCount, const IIndexedLineDataFetcher& iLineFetcher) override
        {
            for (size_t i = 0; i < lineCount; i += 2)
            {
                carb::Float3 point0;
                carb::Float3 point1;
                carb::ColorRgba color0F4;
                carb::ColorRgba color1F4;
                float width0;
                float width1;
                iLineFetcher.Fetch(i, point0, color0F4, width0);
                iLineFetcher.Fetch(i + 1, point1, color1F4, width1);
                const uint32_t color0 = ConvertColor(color0F4);
                const uint32_t color1 = ConvertColor(color1F4);

                OnLine(point0, color0, width0, point1, color1, width1);
            }
        }

        static uint32_t ConvertColor(carb::ColorRgba colorRgba)
        {
            union
            {
                uint32_t asInt;
                uint8_t asBytes[4]; // bgra
            } colorUnion;
            colorUnion.asBytes[0] = uint8_t(colorRgba.b * 255);
            colorUnion.asBytes[1] = uint8_t(colorRgba.g * 255);
            colorUnion.asBytes[2] = uint8_t(colorRgba.r * 255);
            colorUnion.asBytes[3] = uint8_t(colorRgba.a * 255);

            return colorUnion.asInt;
        }
    };


    class ImmediateExecuteDrawingCommands : public DrawingImpBase
    {
    public:
        ImmediateExecuteDrawingCommands(omni::renderer::IDebugDraw& debugDraw) : m_DebugDraw(debugDraw)
        {
        }

        virtual void OnPoint(const carb::Float3& pointPos, uint32_t pointColor, float width)
        {
            m_DebugDraw.drawPoint(pointPos, pointColor, width);
        }

        virtual void OnLine(const carb::Float3& startPos,
                            uint32_t startColor,
                            float startWidth,
                            const carb::Float3& endPos,
                            uint32_t endColor,
                            float endWidth)
        {
            m_DebugDraw.drawLine(startPos, startColor, startWidth, endPos, endColor, endWidth);
        }

        omni::renderer::IDebugDraw& m_DebugDraw;
    };

    class RecordDrawingCommands : public DrawingImpBase
    {
    public:
        RecordDrawingCommands(omni::renderer::IDebugDraw& debugDraw) : m_DebugDraw(debugDraw)
        {
            m_LineBuffer = m_DebugDraw.allocateLineBuffer(0);
            m_PointBuffer = m_DebugDraw.allocatePointBuffer(0);
        }

        virtual void OnPoint(const carb::Float3& pointPos, uint32_t pointColor, float width)
        {
            m_DebugDraw.setPoint(m_PointBuffer, m_NextPointIndex, pointPos, pointColor, width);
            ++m_NextPointIndex;
        }

        virtual void OnLine(const carb::Float3& startPos,
                            uint32_t startColor,
                            float startWidth,
                            const carb::Float3& endPos,
                            uint32_t endColor,
                            float endWidth)
        {
            m_DebugDraw.setLine(
                m_LineBuffer, m_NextLineIndex, startPos, startColor, startWidth, endPos, endColor, endWidth);
            ++m_NextLineIndex;
        }

        omni::renderer::IDebugDraw& m_DebugDraw;
        omni::renderer::SimplexBuffer m_LineBuffer = 0;
        omni::renderer::SimplexBuffer m_PointBuffer = 0;
        size_t m_NextLineIndex = 0;
        size_t m_NextPointIndex = 0;
    };


private:
    static const omni::renderer::SimplexBuffer EMPTY_SIMPLEXBUFFER = -1;
    struct Recording
    {
        omni::renderer::SimplexBuffer lineBuffer = IDebugDraw::eInvalidBuffer;
        omni::renderer::SimplexBuffer pointBuffer = IDebugDraw::eInvalidBuffer;
        omni::renderer::RenderInstanceBuffer lineRenderInstanceBuffer = IDebugDraw::eInvalidBuffer;
        omni::renderer::RenderInstanceBuffer pointRenderInstanceBuffer = IDebugDraw::eInvalidBuffer;
        uint32_t uid = 0;
    };
    typedef std::unordered_map<RecordingHandle, Recording> DrawRecordings;

    // internal state is necessary (at time of writing) to work around a bug in the COM-style carbonite interfaces
    //  see OM-25736, and
    //  https://nvidia.slack.com/archives/CCSV6PBR6/p1610399261393800?thread_ts=1610398300.392400&cid=CCSV6PBR6
    struct InternalState
    {
        omni::renderer::IDebugDraw* m_DebugDraw;
        DrawRecordings m_DrawRecordings;
        RecordingHandle m_NextRecordingHandle = 1;
    };
    InternalState* m_InternalState = nullptr;
};

} // namespace renderer
} // namespace omni
