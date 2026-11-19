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

#include <carb/Interface.h>
#include <carb/InterfaceUtils.h>

#include <omni/graph/core/ComputeGraph.h>
#include <omni/kit/IApp.h>
#include <omni/scenevisualization/ISceneVisualization.h>
#include <omni/usd/Selection.h>
#include <omni/usd/UsdContext.h>
#include <tbb/concurrent_unordered_map.h>

#include <bitset>
#include <unordered_map>

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include "StageUpdateBase.h"
#include "Utils.h"

namespace omni
{
namespace renderer
{

class SceneDeclutterImpl : public ISceneDeclutter, public StageUpdateBase
{
public:
    // these enums control what we draw. will begin or terminate drawing on selection if not already, as appropriate
    enum ViewFlags : size_t
    {
        POINTS,
        NORMALS,
        WIREFRAME,
        TANGENTS,
        NUM_FLAGS
    };

    // these enums only control how we draw - we will not begin drawing something that wasn't already visible before,
    //  and so we can handle toggles of this type much more simply.
    enum ViewOptions : size_t
    {
        USE_VERTEX_COLOR,
        USE_WIDTHS_PRIMVAR,
        SELECTED,
        NUM_OPTIONS
    };
    // NOTE: since the refactor in 105.4.0, this enum is no longer necessary;
    // it can be phased out of the AdjustVisualization functions.
    enum OptionActions
    {
        TOGGLE,
        DISABLE,
        ENABLE
    };

    void onStartup();
    void onShutdown();
    static bool isPathDescendantOfPaths(const PXR_NS::SdfPath& primPath, const PXR_NS::SdfPathVector& paths);
    static void applySchemaToPrim(PXR_NS::UsdPrim prim);
    static void removeSchemaIfNothingVisualized(PXR_NS::UsdPrim prim);
    static bool isEligibleForVisualization(PXR_NS::UsdPrim prim);
    static PXR_NS::SdfPathVector getVisualizedPrimsFromMetadata(PXR_NS::UsdStageWeakPtr stage);
    void onSelectionChanged();
    void onPointWidthChanged(const float pointWidth);
    void onLineWidthChanged(const float lineWidth);
    void onUseWidthsPrimvarChanged(const bool useWidthsPrimvar);
    void Update(const float elapsedTime);
    void ApplyPendingUpdates();
    virtual void RegisterDrawableNodeType(const omni::graph::core::NodeTypeObj& nodeType,
                                          DrawNodeFuncPtr drawFuncPtr) override;
    virtual void RegisterDrawablePrimType(const PXR_NS::TfToken& primType, DrawPrimFuncPtr drawFuncPtr) override;
    virtual void TogglePoints() override;
    virtual void ToggleNormals() override;
    virtual void ToggleWireframe() override;
    virtual void ToggleTangents() override;
    virtual void ToggleUseVertexColor() override;
    void Toggle(const PXR_NS::TfToken attrName);

private:
    class VisualizeObject // node or prim
    {
    public:
        VisualizeObject(float pointWidth, float lineWidth, bool useWidthsPrimvar)
            : m_PointWidth(pointWidth), m_LineWidth(lineWidth)
        {
            m_CurrentViewOptions[USE_WIDTHS_PRIMVAR] = useWidthsPrimvar;
        }
        virtual ~VisualizeObject()
        {
        }
        virtual bool QueryViewFlag(ViewFlags flag)
        {
            return m_CurrentViewFlags[flag];
        }
        virtual void SetViewFlag(ViewFlags flag, bool value)
        {
            m_CurrentViewFlags[flag] = value;
            DrawFlagsDirty();
        }
        virtual bool QueryViewOption(ViewOptions option)
        {
            return m_CurrentViewOptions[option];
        }
        virtual void SetViewOption(ViewOptions option, bool value)
        {
            m_CurrentViewOptions[option] = value;
            DrawFlagsDirty();
        }
        virtual bool IsDrawingAnything()
        {
            return m_CurrentViewFlags.any();
        }
        virtual void SetSelected(bool selected)
        {
            SetViewOption(SELECTED, selected);
        }
        virtual void SetPointWidth(float pointWidth)
        {
            m_PointWidth = pointWidth;
            if (m_CurrentViewFlags[POINTS])
            {
                DrawFlagsDirty();
            }
        }
        virtual void SetLineWidth(float lineWidth)
        {
            m_LineWidth = lineWidth;
            if (m_CurrentViewFlags[NORMALS] || m_CurrentViewFlags[WIREFRAME] || m_CurrentViewFlags[TANGENTS])
            {
                DrawFlagsDirty();
            }
        }
        virtual void SetUseWidthsPrimvar(bool useWidthsPrimvar)
        {
            SetViewOption(USE_WIDTHS_PRIMVAR, useWidthsPrimvar);
        }

    protected:
        virtual void DrawFlagsDirty() = 0;
        std::bitset<NUM_FLAGS> m_CurrentViewFlags; // flags we were last draw with
        std::bitset<NUM_OPTIONS> m_CurrentViewOptions; // options we were last draw with
        float m_PointWidth; // diameter
        float m_LineWidth;
        // TODO: point width, line width, and the useWidthsPrimvar view option do not vary per-object.
        // They could be specified once instead of maintained redundantly in every visualization object....
    };

    class VisualizeNode : public INodeVisualizer::IDrawCallback, public VisualizeObject
    {
    public:
        VisualizeNode(float pointWidth,
                      float lineWidth,
                      bool useWidthsPrimvar,
                      const omni::graph::core::NodeObj& nodeObj,
                      DrawNodeFuncPtr drawFuncPtrIn,
                      INodeVisualizer& nodeVisualizer)
            : VisualizeObject(pointWidth, lineWidth, useWidthsPrimvar),
              m_DrawFuncPtr(drawFuncPtrIn),
              m_NodeVisualizer(nodeVisualizer)
        {
            m_VisualizerHandle = m_NodeVisualizer.AddNodeDraw(nodeObj, this);
        }

        virtual ~VisualizeNode()
        {
            const INodeVisualizer::IDrawCallback* ret = m_NodeVisualizer.RemoveNodeDraw(m_VisualizerHandle);
            CARB_ASSERT(ret == this); // better get back what we put in
        }

    private:
        virtual void DrawFlagsDirty() override
        {
            m_NodeVisualizer.ForceNodeDirty(m_VisualizerHandle);
        }

        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface,
                          const omni::graph::core::NodeObj& nodeObj) const
        {
            Options options = { m_CurrentViewFlags[POINTS],
                                m_CurrentViewFlags[NORMALS],
                                m_CurrentViewFlags[WIREFRAME],
                                m_CurrentViewFlags[TANGENTS],
                                m_CurrentViewOptions[USE_VERTEX_COLOR],
                                m_CurrentViewOptions[USE_WIDTHS_PRIMVAR],
                                m_CurrentViewOptions[SELECTED],
                                m_PointWidth,
                                m_LineWidth };
            (*m_DrawFuncPtr)(drawingInterface, nodeObj, options);
        }
        const DrawNodeFuncPtr m_DrawFuncPtr;
        INodeVisualizer& m_NodeVisualizer;
        INodeVisualizer::RegistrationHandle m_VisualizerHandle = INodeVisualizer::INVALID_REGISTRATION_HANDLE;
    };

    class VisualizePrim : public IPrimVisualizer::IDrawCallback, public VisualizeObject
    {
    public:
        VisualizePrim(float pointWidth,
                      float lineWidth,
                      bool useWidthsPrimvar,
                      PXR_NS::SdfPath primPath,
                      DrawPrimFuncPtr drawFuncPtrIn,
                      IPrimVisualizer& primVisualizer,
                      bool markSelected)
            : VisualizeObject(pointWidth, lineWidth, useWidthsPrimvar),
              m_DrawFuncPtr(drawFuncPtrIn),
              m_PrimVisualizer(primVisualizer),
              m_primPath(primPath)
        {
            // When a VisualizePrim is created, we set this flag if the USD prim is selected or is the child of a
            // selected prim. After this, onSelectionChanged will handle subsequent selection updates.
            m_CurrentViewOptions[SELECTED] = markSelected;

            m_VisualizerHandle = m_PrimVisualizer.AddPrimDraw(primPath, this);
        }

        virtual ~VisualizePrim()
        {
            const IPrimVisualizer::IDrawCallback* ret = m_PrimVisualizer.RemovePrimDraw(m_VisualizerHandle);
            CARB_ASSERT(ret == this); // better get back what we put in
        }

        virtual void SetViewFlag(ViewFlags flag, bool value)
        {
            static const PXR_NS::TfType schemaType =
                PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

            VisualizeObject::SetViewFlag(flag, value);

            PXR_NS::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage();
            CARB_ASSERT(stage);
            PXR_NS::UsdPrim prim = stage->GetPrimAtPath(m_primPath);

            if (prim.IsValid() && !prim.IsInstanceProxy())
            {
                PXR_NS::TfToken token;
                switch (flag)
                {
                case POINTS:
                    token = t_drawPoints;
                    break;
                case NORMALS:
                    token = t_drawNormals;
                    break;
                case WIREFRAME:
                    token = t_drawWireframe;
                    break;
                case TANGENTS:
                    token = t_drawTangents;
                default:
                    break;
                }

                if (!token.IsEmpty())
                {
                    // We want to avoid triggering USD notices if we don't need to -- thus the checks
                    // against currentValue before setting an attribute value.

                    if (prim.HasAPI(schemaType))
                    {
                        PXR_NS::UsdAttribute attr = prim.GetAttribute(token);
                        bool currentValue;
                        CARB_ASSERT(attr.IsValid());
                        attr.Get(&currentValue);
                        // Avoid unnecessary edits by only setting the value if it differs from current value.
                        if (value != currentValue)
                        {
                            attr.Set(value);
                        }
                    }
                }
            }
        }

        virtual void SetViewOption(ViewOptions option, bool value)
        {
            static const PXR_NS::TfType schemaType =
                PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

            VisualizeObject::SetViewOption(option, value);


            PXR_NS::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage();
            CARB_ASSERT(stage);
            PXR_NS::UsdPrim prim = stage->GetPrimAtPath(m_primPath);

            if (prim.IsValid() && !prim.IsInstanceProxy())
            {
                PXR_NS::TfToken token;
                switch (option)
                {
                case USE_VERTEX_COLOR:
                    token = t_useVertexColor;
                    break;
                default:
                    break;
                }

                if (!token.IsEmpty())
                {
                    // We want to avoid triggering USD notices if we don't need to -- thus the checks
                    // against currentValue before setting an attribute value.

                    if (prim.HasAPI(schemaType))
                    {
                        PXR_NS::UsdAttribute attr = prim.GetAttribute(token);
                        bool currentValue;
                        CARB_ASSERT(attr.IsValid());
                        attr.Get(&currentValue);
                        // Avoid unnecessary edits by only setting the value if it differs from current value.
                        if (value != currentValue)
                        {
                            attr.Set(value);
                        }
                    }
                }
            }
        }

    private:
        virtual void DrawFlagsDirty() override
        {
            m_PrimVisualizer.ForcePrimDirty(m_VisualizerHandle);
        }

        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface, PXR_NS::SdfPath primPath) const
        {
            PXR_NS::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage();
            CARB_ASSERT(stage);
            PXR_NS::UsdPrim prim = stage->GetPrimAtPath(primPath);
            // Prim visibility trumps all else -- if the prim is invisible, we won't do anything here.
            if (!prim.IsA<PXR_NS::UsdGeomImageable>())
                return;
            PXR_NS::UsdGeomImageable imageable(prim);
            if (imageable.ComputeVisibility() == PXR_NS::UsdGeomTokens->invisible)
                return;

            Options options = { m_CurrentViewFlags[POINTS],
                                m_CurrentViewFlags[NORMALS],
                                m_CurrentViewFlags[WIREFRAME],
                                m_CurrentViewFlags[TANGENTS],
                                m_CurrentViewOptions[USE_VERTEX_COLOR],
                                m_CurrentViewOptions[USE_WIDTHS_PRIMVAR],
                                m_CurrentViewOptions[SELECTED],
                                m_PointWidth,
                                m_LineWidth };
            (*m_DrawFuncPtr)(drawingInterface, prim, options);
        }
        const DrawPrimFuncPtr m_DrawFuncPtr;
        IPrimVisualizer& m_PrimVisualizer;
        IPrimVisualizer::RegistrationHandle m_VisualizerHandle = IPrimVisualizer::INVALID_REGISTRATION_HANDLE;
        IPrimVisualizer::RegistrationHandle visualizerHandle = IPrimVisualizer::INVALID_REGISTRATION_HANDLE;
        PXR_NS::SdfPath m_primPath;
    };

    typedef tbb::concurrent_unordered_map<PXR_NS::SdfPath, VisualizeObject*, PXR_NS::SdfPath::Hash> VisualizedObjects;
    typedef std::unordered_map<std::string, DrawNodeFuncPtr> NodeTypeDrawFuncs;
    typedef std::unordered_map<std::string, DrawPrimFuncPtr> PrimTypeDrawFuncs;
    struct InternalState
    {
        omni::graph::core::GraphObj m_GraphObj;
        INodeVisualizer* m_NodeVisualizer = nullptr;
        IPrimVisualizer* m_PrimVisualizer = nullptr;

        // respond to selection events
        carb::events::ISubscriptionPtr m_stageEvtSub;

        // repond to update ticks
        carb::events::ISubscriptionPtr m_updateSub;

        // receive settings updates
        carb::settings::ISettings* m_settings = nullptr;
        carb::dictionary::SubscriptionId* m_pointWidthChangedSub = nullptr;
        carb::dictionary::SubscriptionId* m_lineWidthChangedSub = nullptr;
        carb::dictionary::SubscriptionId* m_useWidthsPrimvarChangedSub = nullptr;

        // currently drawing these nodes/prims
        VisualizedObjects m_VisualizedObjects;

        // prims to be considered for add on next update
        std::set<PXR_NS::SdfPath> m_primAddSet;
        // prims that have changed to be considered on next update
        std::set<PXR_NS::SdfPath> m_primChangeSet;
        // removed prims to be considered on next update
        std::set<PXR_NS::SdfPath> m_primRemoveSet;

        // node drawing functions associated with node types
        NodeTypeDrawFuncs m_NodeTypeDrawFuncs;
        PrimTypeDrawFuncs m_PrimTypeDrawFuncs;

        PXR_NS::SdfPathVector m_selectedPrimPaths;
    };


    // overload 1 - change what we draw. begin drawing something if we aren't already & if possible .
    OptionActions AdjustVisualization(PXR_NS::UsdPrim& prim, ViewFlags flag, OptionActions action);
    // overload 2 - change how we draw. this doesn't change whether we draw something, so we will not
    //  acdtually
    OptionActions AdjustVisualization(PXR_NS::UsdPrim& prim, ViewOptions option, OptionActions action);

    void InitializeVisualizationFromPrimAttributes(PXR_NS::UsdPrim& prim);
    void AdjustVisualizationFromPrimAttributes(PXR_NS::UsdPrim& prim);

    // StageUpdateBase overrides
    virtual void Attach(long int stageId, double metersPerUnit) override;
    virtual void Detach() override;
    virtual void OnPrimAdd(const PXR_NS::SdfPath& primPath) override;
    virtual void OnPrimRemove(const PXR_NS::SdfPath& primPath) override;
    virtual void OnPrimChange(const PXR_NS::SdfPath& primPath) override;

    VisualizedObjects::iterator VisualizedPrimRemoved(VisualizedObjects::iterator it);
    void VisualizeInstanceProxies(PXR_NS::UsdPrim instancePrim, const Options& options);
    void InitializeFromStage(long int stageId);

    InternalState* m_InternalState = nullptr;
};

} // namespace renderer
} // namespace omni
