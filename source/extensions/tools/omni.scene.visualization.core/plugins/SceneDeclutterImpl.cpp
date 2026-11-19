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
#include "SceneDeclutterImpl.h"

#include <carb/dictionary/DictionaryUtils.h>

#include <pxr/usd/usd/primRange.h>
#include <usdrt/scenegraph/ovstage/Stage.h>

#include <algorithm>
#include <string>
#include <vector>

namespace omni
{
namespace renderer
{

namespace
{

// Kit 111: discover through Kit's populated ovstage (usdrt.scenegraph.ovstage facade). Kit's OPENED event can
// precede its ovstage publication, and a query can fail while Kit updates; then use the authored USD stage, which
// carries the same applied-schema metadata.
PXR_NS::SdfPathVector findPrimsWithAppliedAPI(const PXR_NS::UsdStageRefPtr& stage, long int stageId, const PXR_NS::TfToken& api)
{
    PXR_NS::SdfPathVector result;
    if (auto ovStage = usdrt::ovstage::Stage::Attach(uint64_t(stageId)); ovStage && ovStage->IsReadReady())
    {
        usdrt::ovstage::PrimQuery query;
        query.appliedSchemasAny = { api.GetString() };
        std::vector<std::string> paths;
        if (ovStage->QueryPrimPaths(query, paths))
        {
            result.reserve(paths.size());
            for (const auto& path : paths)
                result.emplace_back(path);
            return result;
        }
    }
    for (const PXR_NS::UsdPrim& prim : stage->Traverse())
    {
        const auto schemas = prim.GetAppliedSchemas();
        if (std::find(schemas.begin(), schemas.end(), api) != schemas.end())
            result.push_back(prim.GetPath());
    }
    return result;
}

} // namespace

void SceneDeclutterImpl::onStartup()
{
    CARB_ASSERT(m_InternalState == nullptr);
    m_InternalState = new InternalState;

    m_InternalState->m_NodeVisualizer = carb::getFramework()->tryAcquireInterface<omni::renderer::INodeVisualizer>();
    m_InternalState->m_PrimVisualizer = carb::getFramework()->tryAcquireInterface<omni::renderer::IPrimVisualizer>();

    const int32_t updatePriority = 101; // run after graph ?

    omni::kit::IApp* app = carb::getCachedInterface<omni::kit::IApp>();
    m_InternalState->m_updateSub = carb::events::createSubscriptionToPop(
        app->getUpdateEventStream(),
        [this](carb::events::IEvent* e)
        {
            float dt = carb::dictionary::getCachedDictionaryInterface()->get<float>(e->payload, "dt");
            Update(dt);
        },
        updatePriority, "SceneVisualization update");

    m_InternalState->m_stageEvtSub = carb::events::createSubscriptionToPop(
        omni::usd::UsdContext::getContext()->getStageEventStream().get(),
        [this](carb::events::IEvent* e)
        {
            switch (static_cast<omni::usd::StageEventType>(e->type))
            {
            case omni::usd::StageEventType::eSelectionChanged:
                onSelectionChanged();
                break;
            default:
                break;
            }
        },
        updatePriority, "SceneVisualization stage event");

    m_InternalState->m_settings = carb::getCachedInterface<carb::settings::ISettings>();
    if (m_InternalState->m_settings)
    {
        m_InternalState->m_settings->setDefaultFloat(kSettingsPointWidth, 4.f);
        m_InternalState->m_settings->setDefaultFloat(kSettingsLineWidth, 1.f);
        m_InternalState->m_settings->setDefaultBool(kSettingsApplyToDescendants, true);
        m_InternalState->m_settings->setDefaultBool(kSettingsUseSceneVisPrim, false);
        m_InternalState->m_settings->setDefaultBool(kSettingsUseWidthsPrimvar, false);

        // get Settings updates to resize existing objects when preferences are adjusted
        m_InternalState->m_pointWidthChangedSub = m_InternalState->m_settings->subscribeToNodeChangeEvents(
            kSettingsPointWidth,
            [](const carb::dictionary::Item* changedItem, carb::dictionary::ChangeEventType changeEventType, void* userData)
            {
                if (changeEventType == carb::dictionary::ChangeEventType::eChanged)
                {
                    carb::dictionary::IDictionary* dict =
                        carb::getFramework()->acquireInterface<carb::dictionary::IDictionary>();
                    const float pointWidth = dict->getAsFloat(changedItem);
                    SceneDeclutterImpl* sceneDeclutterImpl = reinterpret_cast<SceneDeclutterImpl*>(userData);
                    sceneDeclutterImpl->onPointWidthChanged(pointWidth);
                }
            },
            this);

        m_InternalState->m_lineWidthChangedSub = m_InternalState->m_settings->subscribeToNodeChangeEvents(
            kSettingsLineWidth,
            [](const carb::dictionary::Item* changedItem, carb::dictionary::ChangeEventType changeEventType, void* userData)
            {
                if (changeEventType == carb::dictionary::ChangeEventType::eChanged)
                {
                    carb::dictionary::IDictionary* dict =
                        carb::getFramework()->acquireInterface<carb::dictionary::IDictionary>();
                    const float lineWidth = dict->getAsFloat(changedItem);
                    SceneDeclutterImpl* sceneDeclutterImpl = reinterpret_cast<SceneDeclutterImpl*>(userData);
                    sceneDeclutterImpl->onLineWidthChanged(lineWidth);
                }
            },
            this);
        m_InternalState->m_useWidthsPrimvarChangedSub = m_InternalState->m_settings->subscribeToNodeChangeEvents(
            kSettingsUseWidthsPrimvar,
            [](const carb::dictionary::Item* changedItem, carb::dictionary::ChangeEventType changeEventType, void* userData)
            {
                if (changeEventType == carb::dictionary::ChangeEventType::eChanged)
                {
                    carb::dictionary::IDictionary* dict =
                        carb::getFramework()->acquireInterface<carb::dictionary::IDictionary>();
                    const bool useWidthsPrimvar = dict->getAsBool(changedItem);
                    SceneDeclutterImpl* sceneDeclutterImpl = reinterpret_cast<SceneDeclutterImpl*>(userData);
                    sceneDeclutterImpl->onUseWidthsPrimvarChanged(useWidthsPrimvar);
                }
            },
            this);
    }

    StageUpdateBase::Startup();

    // we know how to draw Mesh objects. // TODO: can add the other parametric types here as well
    // good lord, is it really this hard to query the name name of a UsdGeomMesh, without just hard-coding it?
    auto& schemaRegistry = pxr::UsdSchemaRegistry::GetInstance();
    const PXR_NS::TfToken meshTypename = schemaRegistry.GetSchemaTypeName<PXR_NS::UsdGeomMesh>();
    RegisterDrawablePrimType(meshTypename, &MeshUtils::DrawMeshFromUSD);

    const PXR_NS::TfToken curveTypename = schemaRegistry.GetSchemaTypeName<PXR_NS::UsdGeomBasisCurves>();
    RegisterDrawablePrimType(curveTypename, &MeshUtils::DrawBasisCurvesFromUSD);

    omni::usd::UsdContext* usdContext = omni::usd::UsdContext::getContext();

    InitializeFromStage(usdContext->getStageId());
}

void SceneDeclutterImpl::onShutdown()
{
    CARB_ASSERT(m_InternalState != nullptr);

    CARB_ASSERT(m_InternalState->m_VisualizedObjects.empty());

    StageUpdateBase::Shutdown();

    carb::getFramework()->releaseInterface(m_InternalState->m_NodeVisualizer);
    carb::getFramework()->releaseInterface(m_InternalState->m_PrimVisualizer);

    delete m_InternalState;
}

bool SceneDeclutterImpl::isPathDescendantOfPaths(const PXR_NS::SdfPath& primPath, const PXR_NS::SdfPathVector& paths)
{
    bool isDescendant = false;
    for (const auto& path : paths)
    {
        if (primPath.HasPrefix(path))
        {
            isDescendant = true;
            break;
        }
    }
    return isDescendant;
}

void SceneDeclutterImpl::applySchemaToPrim(PXR_NS::UsdPrim prim)
{
    static carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
    static const PXR_NS::TfType visSchemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);
    static const PXR_NS::TfToken metadataSchema("OmniSceneVisualizationMetadata");
    static const PXR_NS::TfToken metadataPrimName("SceneVisualizationMetadata");
    static const PXR_NS::TfToken metadataRelationshipName("visualizedPrims");

    if (!prim.HasAPI(visSchemaType))
    {
        prim.ApplyAPI(visSchemaType);
        if (settings->getAsBool(kSettingsUseSceneVisPrim))
        {
            auto stage = prim.GetStage();
            const PXR_NS::SdfPath metadataPath = stage->GetPseudoRoot().GetPath().AppendChild(metadataPrimName);
            PXR_NS::UsdPrim metadataPrim = stage->GetPrimAtPath(metadataPath);
            if (!metadataPrim)
            {
                metadataPrim = stage->DefinePrim(metadataPath, metadataSchema);
                metadataPrim.SetHidden(true);
            }
            CARB_ASSERT(metadataPrim.IsA(PXR_NS::UsdSchemaRegistry::GetConcreteTypeFromSchemaTypeName(metadataSchema)));
            PXR_NS::UsdRelationship rel = metadataPrim.GetRelationship(metadataRelationshipName);
            CARB_ASSERT(rel.IsValid());
            rel.AddTarget(prim.GetPath());
        }
    }

    // TODO: remove schema, and remove prim from metadata list, when all visualization options are disabled...
}

void SceneDeclutterImpl::removeSchemaIfNothingVisualized(PXR_NS::UsdPrim prim)
{
    // XXX currently this is not safe to do, since it will trigger additional USD notices
    // while we are in the middle of processing changes...
    static carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
    static const PXR_NS::TfType visSchemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);
    static const PXR_NS::TfToken metadataSchema("OmniSceneVisualizationMetadata");
    static const PXR_NS::TfToken metadataPrimName("SceneVisualizationMetadata");
    static const PXR_NS::TfToken metadataRelationshipName("visualizedPrims");

    static std::vector<PXR_NS::TfToken> schemaTokens = { t_drawWireframe, t_drawPoints, t_drawNormals, t_drawTangents,
                                                         t_useVertexColor };

    bool hasEnabledAttribute = false;
    for (const auto& token : schemaTokens)
    {
        if (prim.HasAttribute(token))
        {
            bool value;
            prim.GetAttribute(token).Get(&value);
            if (value)
            {
                hasEnabledAttribute = true;
                break;
            }
        }
    }
    if (!hasEnabledAttribute)
    {
        prim.RemoveAPI(visSchemaType);
        for (const auto& token : schemaTokens)
        {
            if (prim.HasAttribute(token))
            {
                prim.RemoveProperty(token);
            }
        }
        if (settings->getAsBool(kSettingsUseSceneVisPrim))
        {
            auto stage = prim.GetStage();
            const PXR_NS::SdfPath metadataPath = stage->GetPseudoRoot().GetPath().AppendChild(metadataPrimName);
            if (PXR_NS::UsdPrim metadataPrim = stage->GetPrimAtPath(metadataPath))
            {
                CARB_ASSERT(
                    metadataPrim.IsA(PXR_NS::UsdSchemaRegistry::GetConcreteTypeFromSchemaTypeName(metadataSchema)));
                PXR_NS::UsdRelationship rel = metadataPrim.GetRelationship(metadataRelationshipName);
                CARB_ASSERT(rel.IsValid());
                rel.RemoveTarget(prim.GetPath());
            }
        }
    }
}

bool SceneDeclutterImpl::isEligibleForVisualization(PXR_NS::UsdPrim prim)
{
    static const PXR_NS::TfType schemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

    return prim.HasAPI(schemaType) || prim.IsInstance() || prim.IsA<PXR_NS::UsdGeomMesh>() ||
           prim.IsA<PXR_NS::UsdGeomBasisCurves>();
}

PXR_NS::SdfPathVector SceneDeclutterImpl::getVisualizedPrimsFromMetadata(PXR_NS::UsdStageWeakPtr stage)
{
    static const PXR_NS::TfToken metadataPrimName("SceneVisualizationMetadata");
    static const PXR_NS::TfToken metadataRelationshipName("visualizedPrims");

    const PXR_NS::SdfPath metadataPath = stage->GetPseudoRoot().GetPath().AppendChild(metadataPrimName);
    PXR_NS::UsdPrim metadataPrim = stage->GetPrimAtPath(metadataPath);
    PXR_NS::SdfPathVector pathsList;
    if (metadataPrim)
    {
        if (PXR_NS::UsdRelationship rel = metadataPrim.GetRelationship(metadataRelationshipName))
        {
            rel.GetTargets(&pathsList);
        }
    }
    return pathsList;
}
void SceneDeclutterImpl::onSelectionChanged()
{
    // save the selected paths for use elsewhere
    m_InternalState->m_selectedPrimPaths = omni::usd::UsdContext::getContext()->getSelection()->getSelectedPrimPathsV2();
    // update visualization objects
    for (auto& val : m_InternalState->m_VisualizedObjects)
    {
        val.second->SetSelected(isPathDescendantOfPaths(val.first, m_InternalState->m_selectedPrimPaths));
    }
}
void SceneDeclutterImpl::onPointWidthChanged(const float pointWidth)
{
    for (auto& val : m_InternalState->m_VisualizedObjects)
    {
        val.second->SetPointWidth(pointWidth);
    }
}
void SceneDeclutterImpl::onLineWidthChanged(const float lineWidth)
{
    for (auto& val : m_InternalState->m_VisualizedObjects)
    {
        val.second->SetLineWidth(lineWidth);
    }
}
void SceneDeclutterImpl::onUseWidthsPrimvarChanged(const bool useWidthsPrimvar)
{
    for (auto& val : m_InternalState->m_VisualizedObjects)
    {
        val.second->SetUseWidthsPrimvar(useWidthsPrimvar);
    }
}
void SceneDeclutterImpl::Update(const float elapsedTime)
{
    ApplyPendingUpdates();
}
void SceneDeclutterImpl::ApplyPendingUpdates()
{
    CARB_PROFILE_ZONE(1, "Applying Pending Updates");

    PXR_NS::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage();
    if (!stage)
        return;

    for (const PXR_NS::SdfPath& primPath : m_InternalState->m_primRemoveSet)
    {
        //  We only get a notice for the top level prim that has been removed.
        // StageUpdate gets around this by using cached information in omni hydra.
        // But here we'll just compare prim paths
        for (VisualizedObjects::iterator it = m_InternalState->m_VisualizedObjects.begin();
             it != m_InternalState->m_VisualizedObjects.end();)
        {
            const PXR_NS::SdfPath& path = it->first;
            if (path.HasPrefix(primPath))
            {
                it = VisualizedPrimRemoved(it);
            }
            else
            {
                it++;
            }
        }
    }
    m_InternalState->m_primRemoveSet.clear();

    for (const PXR_NS::SdfPath& primPath : m_InternalState->m_primAddSet)
    {
        PXR_NS::UsdPrim prim = stage->GetPrimAtPath(primPath);
        if (!prim.IsValid())
        {
            //  In some cases when a prim is reparented we may handle a notice that
            // gives us the pre-reparenting prim path. But by the time we get here
            // that path is no longer valid.
            continue;
        }

        // The condition here is to avoid a lot of USD warnings about
        // appending properties to '/' (it seems somehow `HasAttribute'
        // ends up calling `AppendProperty'...)
        if (!prim.IsPseudoRoot())
        {
            AdjustVisualizationFromPrimAttributes(prim);
        }

        // In the case of rename / reparent, only the topmost prim will appear in the
        // primAddSet, so we also need to check its descendants for viz attributes
        // (Note we don't bother checking descendants that are proxy instances,
        // since these do not carry viz attributes anyway)
        for (auto childPrim : prim.GetAllDescendants())
        {
            AdjustVisualizationFromPrimAttributes(childPrim);
        }
    }
    m_InternalState->m_primAddSet.clear();

    for (const PXR_NS::SdfPath& primPath : m_InternalState->m_primChangeSet)
    {
        PXR_NS::UsdPrim prim = stage->GetPrimAtPath(primPath);
        if (!prim.IsValid())
        {
            continue;
        }

        if (!prim.IsPseudoRoot())
        {
            AdjustVisualizationFromPrimAttributes(prim);
        }
    }
    m_InternalState->m_primChangeSet.clear();
}

void SceneDeclutterImpl::RegisterDrawableNodeType(const omni::graph::core::NodeTypeObj& nodeType,
                                                  DrawNodeFuncPtr drawFuncPtr)
{
    const std::string nodeTypeStr = nodeType.iNodeType->getNodeType();
    m_InternalState->m_NodeTypeDrawFuncs[nodeTypeStr] = drawFuncPtr;
}

void SceneDeclutterImpl::RegisterDrawablePrimType(const PXR_NS::TfToken& primType, DrawPrimFuncPtr drawFuncPtr)
{
    const std::string primTypeStr = primType.GetString();
    m_InternalState->m_PrimTypeDrawFuncs[primTypeStr] = drawFuncPtr;
}

void SceneDeclutterImpl::TogglePoints()
{
    Toggle(t_drawPoints);
}
void SceneDeclutterImpl::ToggleNormals()
{
    Toggle(t_drawNormals);
}
void SceneDeclutterImpl::ToggleWireframe()
{
    Toggle(t_drawWireframe);
}
void SceneDeclutterImpl::ToggleTangents()
{
    Toggle(t_drawTangents);
}
void SceneDeclutterImpl::ToggleUseVertexColor()
{
    Toggle(t_useVertexColor);
}

void SceneDeclutterImpl::Toggle(const PXR_NS::TfToken attrName)
{
    static const PXR_NS::TfType schemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

    PXR_NS::UsdStageWeakPtr stage = omni::usd::UsdContext::getContext()->getStage(); // feels dirty to be fetching stage
                                                                                     // here
    if (!stage)
        return;

    bool applyToDescendants = true;
    if (m_InternalState->m_settings)
    {
        applyToDescendants = m_InternalState->m_settings->getAsBool(kSettingsApplyToDescendants);
    }

    bool previouslyEnabled = false;

    // we'll derive the new state from the first object in selection that we can apply to
    for (const PXR_NS::SdfPath& primPath : m_InternalState->m_selectedPrimPaths)
    {
        bool foundAttribute = false;
        if (PXR_NS::UsdPrim prim = stage->GetPrimAtPath(primPath))
        {
            if (isEligibleForVisualization(prim))
            {
                if (prim.HasAttribute(attrName))
                {
                    prim.GetAttribute(attrName).Get(&previouslyEnabled);
                }
                foundAttribute = true;
            }

            if (foundAttribute)
            {
                break;
            }

            if (applyToDescendants)
            {
                for (auto child : prim.GetFilteredDescendants(pxr::UsdTraverseInstanceProxies()))
                {
                    if (isEligibleForVisualization(child))
                    {
                        if (child.HasAttribute(attrName))
                        {
                            child.GetAttribute(attrName).Get(&previouslyEnabled);
                        }
                        foundAttribute = true;
                        break;
                    }
                }

                if (foundAttribute)
                {
                    break;
                }
            }
        }
    }

    const bool enabled = !previouslyEnabled;
    for (const PXR_NS::SdfPath& primPath : m_InternalState->m_selectedPrimPaths)
    {
        if (PXR_NS::UsdPrim prim = stage->GetPrimAtPath(primPath))
        {
            if (isEligibleForVisualization(prim))
            {
                PXR_NS::UsdAttribute attr = prim.GetAttribute(attrName);
                if (!attr)
                {
                    attr = prim.CreateAttribute(attrName, pxr::SdfValueTypeNames->Bool);
                }
                bool currentValue = false;
                attr.Get(&currentValue);
                if (currentValue != enabled)
                {
                    attr.Set(enabled);
                }
            }
            if (applyToDescendants)
            {
                for (auto child : prim.GetFilteredDescendants(PXR_NS::UsdTraverseInstanceProxies()))
                {
                    if (isEligibleForVisualization(child))
                    {
                        PXR_NS::UsdAttribute attr = child.GetAttribute(attrName);
                        if (!attr)
                        {
                            attr = child.CreateAttribute(attrName, pxr::SdfValueTypeNames->Bool);
                        }
                        bool currentValue = false;
                        attr.Get(&currentValue);
                        if (currentValue != enabled)
                        {
                            attr.Set(enabled);
                        }
                    }
                }
            }
        }
    }
}

// overload 1 - change what we draw. begin drawing something if we aren't already & if possible .
SceneDeclutterImpl::OptionActions SceneDeclutterImpl::AdjustVisualization(PXR_NS::UsdPrim& prim,
                                                                          ViewFlags flag,
                                                                          OptionActions action)
{
    static const PXR_NS::TfType schemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

    CARB_PROFILE_ZONE(1, "Adjust Visualization Flag");

    VisualizedObjects::iterator itObject = m_InternalState->m_VisualizedObjects.find(prim.GetPath());

    // if we don't currently have a record of this object, we aren't drawing it, and if we are disabling it,
    // then we will continue to not draw it. in other words, we can skip this object entirely
    if (action != DISABLE && itObject == m_InternalState->m_VisualizedObjects.end())
    {
        float pointWidth = 1.f, lineWidth = 1.f;
        bool useWidthsPrimvar = false;
        if (m_InternalState->m_settings)
        {
            pointWidth = m_InternalState->m_settings->getAsFloat(kSettingsPointWidth);
            lineWidth = m_InternalState->m_settings->getAsFloat(kSettingsLineWidth);
            useWidthsPrimvar = m_InternalState->m_settings->getAsBool(kSettingsUseWidthsPrimvar);
        }

        // not already drawing it, and we want to. is it a compute node or a just a prim?
        omni::graph::core::NodeObj nodeObj =
            m_InternalState->m_GraphObj.iGraph->getNode(m_InternalState->m_GraphObj, prim.GetPath().GetText());
        if (nodeObj.nodeHandle)
        {
            omni::graph::core::INodeType iNodeType = nodeObj.iNode->getNodeType(nodeObj);
            const char* nodeTypeStr = iNodeType.getNodeType();
            NodeTypeDrawFuncs::iterator itNodeDrawFuncs = m_InternalState->m_NodeTypeDrawFuncs.find(nodeTypeStr);
            if (itNodeDrawFuncs != m_InternalState->m_NodeTypeDrawFuncs.end())
            {
                // jackpot, we know how to draw this
                DrawNodeFuncPtr drawNodeFuncPtr = itNodeDrawFuncs->second;
                VisualizeNode* visualizeNode = new VisualizeNode(pointWidth, lineWidth, useWidthsPrimvar, nodeObj,
                                                                 drawNodeFuncPtr, *m_InternalState->m_NodeVisualizer);

                VisualizedObjects::value_type val(prim.GetPath(), visualizeNode);
                itObject = m_InternalState->m_VisualizedObjects.insert(val).first;
            }
        }

        // otherwise, see if we know how to draw it based on its prim type
        if (itObject == m_InternalState->m_VisualizedObjects.end())
        {
            // XXX OM-67364 using the m_PrimTypeDrawFuncs map requires a draw function to be registered
            // for each specified type that requires drawing; inheritance is not supported since the lookup
            // is based on string typenames.
            // What we *should* do is distribute the ISceneVisualization header so client extensions can
            // call RegisterDrawablePrimType for other types as well. But before we do that the header
            // should really be cleaned up.
            //
            // In the meantime, we can instead ignore the m_PrimTypeDrawFuncs map and just pick the draw
            // function based on IsA relationships... since we're only supporting Mesh and BasisCurves right now anyway
#if 0
            const PXR_NS::TfToken primType = prim.GetTypeName();

            PrimTypeDrawFuncs::iterator itPrimDrawFuncs = m_InternalState->m_PrimTypeDrawFuncs.find(primType.GetString());
            if (itPrimDrawFuncs != m_InternalState->m_PrimTypeDrawFuncs.end())
            {
                DrawPrimFuncPtr drawFuncPtr = itPrimDrawFuncs->second;
                VisualizePrim* visualizePrim = new VisualizePrim(pointWidth, lineWidth, useWidthsPvimar, prim.GetPath(), drawFuncPtr, *m_InternalState->m_PrimVisualizer);

                VisualizedObjects::value_type val(prim.GetPath(), visualizePrim);
                itObject = m_InternalState->m_VisualizedObjects.insert(val).first;
            }
#else
            DrawPrimFuncPtr drawFuncPtr = nullptr;
            if (prim.IsA<PXR_NS::UsdGeomMesh>())
            {
                drawFuncPtr = &MeshUtils::DrawMeshFromUSD;
            }
            else if (prim.IsA<PXR_NS::UsdGeomBasisCurves>())
            {
                drawFuncPtr = &MeshUtils::DrawBasisCurvesFromUSD;
            }

            if (drawFuncPtr != nullptr)
            {
                VisualizePrim* visualizePrim =
                    new VisualizePrim(pointWidth, lineWidth, useWidthsPrimvar, prim.GetPath(), drawFuncPtr,
                                      *m_InternalState->m_PrimVisualizer,
                                      isPathDescendantOfPaths(prim.GetPath(), m_InternalState->m_selectedPrimPaths));

                VisualizedObjects::value_type val(prim.GetPath(), visualizePrim);
                itObject = m_InternalState->m_VisualizedObjects.insert(val).first;
            }
#endif
        }
    }

    if (itObject != m_InternalState->m_VisualizedObjects.end())
    {
        VisualizeObject* object = itObject->second;
        bool currentlyEnabled = object->QueryViewFlag(flag);

        bool possibleFlagStates[3] = { !currentlyEnabled, // TOGGLE
                                       false, // DISABLE
                                       true }; // ENABLE
        bool newFlagState = possibleFlagStates[action];

        object->SetViewFlag(flag, newFlagState);

        // need to fixup possible toggle action into actual enable/disable
        action = newFlagState ? ENABLE : DISABLE;

        // house keeping
        if (!object->IsDrawingAnything())
        {
            VisualizedPrimRemoved(itObject);
        }
    }
    else if (prim.IsValid() && prim.IsInstance())
    {
        // In this case, we have a prim we do not know how to visualize e.g. a transform,
        // but because it's an instance prim we're going to store viz attributes on it
        // so we can subsequently visualize any instance proxies that are descendants.
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
            // Slightly weird here: if we aren't enabling a visualization option, there's no reason
            // to add an unecessary attribute to the prim if it doesn't exist already.
            //
            // Once the attribute does exist (because its corresponding option has been enabled),
            // it will continue to exist regardless of its value -- so a user can toggle
            // its value and not have it unexpectedly disappear.
            PXR_NS::UsdAttribute attr = prim.GetAttribute(token);
            bool currentlyEnabled = false;
            if (attr.IsValid())
            {
                attr.Get(&currentlyEnabled);
            }

            bool possibleFlagStates[3] = { !currentlyEnabled, // TOGGLE
                                           false, // DISABLE
                                           true }; // ENABLE
            bool newFlagState = possibleFlagStates[action];

            if (prim.HasAPI(schemaType))
            {
                attr = prim.GetAttribute(token);
                CARB_ASSERT(attr.IsValid());
                attr.Get(&currentlyEnabled);
                // Only set the state if the value is different to avoid unnecessary edits
                if (newFlagState != currentlyEnabled)
                {
                    attr.Set(newFlagState);
                }
            }

            action = newFlagState ? ENABLE : DISABLE;
        }
    }

    return action;
}

// overload 2 - change how we draw. this doesn't change whether we draw something, so we will not
//  acdtually
SceneDeclutterImpl::OptionActions SceneDeclutterImpl::AdjustVisualization(PXR_NS::UsdPrim& prim,
                                                                          ViewOptions option,
                                                                          OptionActions action)
{
    static const PXR_NS::TfType schemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

    CARB_PROFILE_ZONE(1, "Adjust Visualization Option");

    VisualizedObjects::iterator itObject = m_InternalState->m_VisualizedObjects.find(prim.GetPath());

    if (itObject != m_InternalState->m_VisualizedObjects.end())
    {
        VisualizeObject* object = itObject->second;
        CARB_ASSERT(object->IsDrawingAnything());

        bool currentlyEnabled = object->QueryViewOption(option);

        bool possibleOptionStates[3] = { !currentlyEnabled, // TOGGLE
                                         false, // DISABLE
                                         true }; // ENABLE
        bool newOptionState = possibleOptionStates[action];

        object->SetViewOption(option, newOptionState);

        // need to fixup possible toggle action into actual enable/disable
        action = newOptionState ? ENABLE : DISABLE;
    }
    else if (prim.IsValid() && prim.IsInstance())
    {
        // In this case, we have a prim we do not know how to visualize e.g. a transform,
        // but because it's an instance prim we're going to store viz attributes on it
        // so we can subsequently visualize any instance proxies that are descendants.
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
            // Slightly weird here: if we aren't enabling a visualization option, there's no reason
            // to add an unecessary attribute to the prim if it doesn't exist already.
            //
            // Once the attribute does exist (because its corresponding option has been enabled),
            // it will continue to exist regardless of its value -- so a user can toggle
            // its value and not have it unexpectedly disappear.
            PXR_NS::UsdAttribute attr = prim.GetAttribute(token);
            bool currentlyEnabled = false;
            if (attr.IsValid())
            {
                attr.Get(&currentlyEnabled);
            }

            bool possibleFlagStates[3] = { !currentlyEnabled, // TOGGLE
                                           false, // DISABLE
                                           true }; // ENABLE
            bool newFlagState = possibleFlagStates[action];

            if (prim.HasAPI(schemaType))
            {
                attr = prim.GetAttribute(token);
                CARB_ASSERT(attr.IsValid());
                attr.Get(&currentlyEnabled);
                // Only set the state if the value is different to avoid unnecessary edits
                if (newFlagState != currentlyEnabled)
                {
                    attr.Set(newFlagState);
                }
            }

            action = newFlagState ? ENABLE : DISABLE;
        }
    }

    return action;
}

void SceneDeclutterImpl::InitializeVisualizationFromPrimAttributes(PXR_NS::UsdPrim& prim)
{
    // This function is largely the same as AdjustVisualizationFromPrimAttributes, except it's called
    // at scene initialization -- so we only need to check for the scenevis schema and enable
    // visualization; don't need to care about adding/removing schemas or disabling visualization.

    static const PXR_NS::TfType schemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

    CARB_PROFILE_ZONE(1, "Initialize Visualization From Prim Attributes");

    Options options;

    // for OM-78114 we found that for large scenes, the initial traversal on stage load
    // takes a long time just to check whether there is anything to visualize.
    // We can sort of alleviate this by applying a schema on a prim when anything
    // is being visualized, so on scene load we check for a schema instead of a
    // list of attributes
    if (prim.HasAPI(schemaType))
    {
        CARB_PROFILE_ZONE(1, "Check Prim Attributes");

        if (prim.HasAttribute(t_drawWireframe))
            prim.GetAttribute(t_drawWireframe).Get(&options.drawWireframe);

        if (prim.HasAttribute(t_drawPoints))
            prim.GetAttribute(t_drawPoints).Get(&options.drawPoints);

        if (prim.HasAttribute(t_drawNormals))
            prim.GetAttribute(t_drawNormals).Get(&options.drawNormals);

        if (prim.HasAttribute(t_drawTangents))
            prim.GetAttribute(t_drawTangents).Get(&options.drawTangents);

        if (prim.HasAttribute(t_useVertexColor))
            prim.GetAttribute(t_useVertexColor).Get(&options.useVertexColor);
    }

    const bool anyOptionEnabled = options.drawWireframe || options.drawPoints || options.drawNormals ||
                                  options.drawTangents || options.useVertexColor;

    if (anyOptionEnabled)
    {
        CARB_PROFILE_ZONE(1, "Initialize All Visualization Options for Prim");
        // In general, we want to adjust visualization options if any have been changed -- whether the change
        // is that they're enabled or they're disabled.
        // However, in the special case of initializing prims from a newly loaded stage, we only need to
        // set up visualization for enabled settings (since no visualization currently exists to be disabled).
        // So we can save ourselves a map lookup per prim in the stage, which can add up for stages with
        // many prims but few visualized prims.
        AdjustVisualization(prim, WIREFRAME, options.drawWireframe ? ENABLE : DISABLE);
        AdjustVisualization(prim, POINTS, options.drawPoints ? ENABLE : DISABLE);
        AdjustVisualization(prim, NORMALS, options.drawNormals ? ENABLE : DISABLE);
        AdjustVisualization(prim, TANGENTS, options.drawTangents ? ENABLE : DISABLE);
        AdjustVisualization(prim, USE_VERTEX_COLOR, options.useVertexColor ? ENABLE : DISABLE);

        if (prim.IsInstance())
        {
            VisualizeInstanceProxies(prim, options);
        }
    }
}

void SceneDeclutterImpl::AdjustVisualizationFromPrimAttributes(PXR_NS::UsdPrim& prim)
{
    static const PXR_NS::TfType schemaType =
        PXR_NS::UsdSchemaRegistry::GetAPITypeFromSchemaTypeName(t_sceneVisualizationAPI);

    CARB_PROFILE_ZONE(1, "Adjust Visualization From Prim Attributes");

    Options options;

    {
        CARB_PROFILE_ZONE(1, "Check Prim Attributes");

        if (prim.HasAttribute(t_drawWireframe))
            prim.GetAttribute(t_drawWireframe).Get(&options.drawWireframe);

        if (prim.HasAttribute(t_drawPoints))
            prim.GetAttribute(t_drawPoints).Get(&options.drawPoints);

        if (prim.HasAttribute(t_drawNormals))
            prim.GetAttribute(t_drawNormals).Get(&options.drawNormals);

        if (prim.HasAttribute(t_drawTangents))
            prim.GetAttribute(t_drawTangents).Get(&options.drawTangents);

        if (prim.HasAttribute(t_useVertexColor))
            prim.GetAttribute(t_useVertexColor).Get(&options.useVertexColor);
    }

    const bool anyOptionEnabled = options.drawWireframe || options.drawPoints || options.drawNormals ||
                                  options.drawTangents || options.useVertexColor;

    // If a vis attribute has been enabled on a prim for the first time, we want to apply the scenevis schema.
    // If no more vis attributes are enabled, we want to clean up the scenevis schema.
    // In either of these cases, we'll get a usd notice to resync this prim, which will result in the final
    // else branch being evaluated in a separate function call.
    // We don't want to do schema applies/removes deeper in the AdjustVisualization callstack because we'll
    // end up with a mess of recursive calls.
    if (anyOptionEnabled && !prim.HasAPI(schemaType))
    {
        applySchemaToPrim(prim);
    }
    else if (!anyOptionEnabled && prim.HasAPI(schemaType))
    {
        removeSchemaIfNothingVisualized(prim);
    }
    else
    {
        CARB_PROFILE_ZONE(1, "Adjust All Visualization Options for Prim");
        AdjustVisualization(prim, WIREFRAME, options.drawWireframe ? ENABLE : DISABLE);
        AdjustVisualization(prim, POINTS, options.drawPoints ? ENABLE : DISABLE);
        AdjustVisualization(prim, NORMALS, options.drawNormals ? ENABLE : DISABLE);
        AdjustVisualization(prim, TANGENTS, options.drawTangents ? ENABLE : DISABLE);
        AdjustVisualization(prim, USE_VERTEX_COLOR, options.useVertexColor ? ENABLE : DISABLE);

        if (prim.IsInstance())
        {
            VisualizeInstanceProxies(prim, options);
        }
    }
}

// StageUpdateBase overrides
void SceneDeclutterImpl::Attach(long int stageId, double metersPerUnit)
{
    // this logic seems questionable, but it came from OG's python bindings (including FIXME). apparently no other way
    // to get the graph associated
    //  with this stage.
    omni::graph::core::ComputeGraph* iComputeGraph =
        carb::getFramework()->acquireInterface<omni::graph::core::ComputeGraph>();
    size_t graphCount = iComputeGraph->getGraphCount();
    bool validGraph = false;
    if (graphCount > 0)
    {
        // FIXME: We currently really only have 1 graph active, so the "current" graph is just defined as the
        // first one.  As the situation changes, we may need to update this.
        std::vector<omni::graph::core::GraphObj> graphBuffer(graphCount);
        validGraph = iComputeGraph->getGraphs(graphBuffer.data(), graphBuffer.size());
        m_InternalState->m_GraphObj = graphBuffer[0];
    }
    CARB_ASSERT(validGraph);

    // See whether any prims in this stage have visualization flags enabled.
    InitializeFromStage(stageId);
}

void SceneDeclutterImpl::Detach()
{
    m_InternalState->m_GraphObj = omni::graph::core::GraphObj();
    m_InternalState->m_selectedPrimPaths.clear();

    // all prims are gone, but we won't get notified via OnPrimRemove
    while (m_InternalState->m_VisualizedObjects.empty() == false)
    {
        VisualizedPrimRemoved(m_InternalState->m_VisualizedObjects.begin());
    }
}

void SceneDeclutterImpl::OnPrimAdd(const PXR_NS::SdfPath& primPath)
{
    //  We cannot assume the prim being added is already valid during this notification;
    // save this prim but defer handling it till the next update
    m_InternalState->m_primAddSet.insert(primPath);
}

void SceneDeclutterImpl::OnPrimRemove(const PXR_NS::SdfPath& primPath)
{
    // when a prim is removed we want to clean up our visualized objects.
    // But rather than do so as soon as the usd notice is received, we'll
    // save these paths and handle everything together on the update tick.
    m_InternalState->m_primRemoveSet.insert(primPath);
}

void SceneDeclutterImpl::OnPrimChange(const PXR_NS::SdfPath& primPath)
{
    m_InternalState->m_primChangeSet.insert(primPath);
}

SceneDeclutterImpl::VisualizedObjects::iterator SceneDeclutterImpl::VisualizedPrimRemoved(VisualizedObjects::iterator it)
{
    VisualizeObject* object = it->second;
    delete object;
    return m_InternalState->m_VisualizedObjects.unsafe_erase(it);
}

void SceneDeclutterImpl::VisualizeInstanceProxies(PXR_NS::UsdPrim instancePrim, const Options& options)
{
    CARB_PROFILE_ZONE(1, "Visualize Instance Proxies");

    CARB_ASSERT(instancePrim.IsInstance());
    for (auto instanceProxy : instancePrim.GetFilteredDescendants(PXR_NS::UsdTraverseInstanceProxies()))
    {
        AdjustVisualization(instanceProxy, WIREFRAME, options.drawWireframe ? ENABLE : DISABLE);
        AdjustVisualization(instanceProxy, POINTS, options.drawPoints ? ENABLE : DISABLE);
        AdjustVisualization(instanceProxy, NORMALS, options.drawNormals ? ENABLE : DISABLE);
        AdjustVisualization(instanceProxy, TANGENTS, options.drawTangents ? ENABLE : DISABLE);
        AdjustVisualization(instanceProxy, USE_VERTEX_COLOR, options.useVertexColor ? ENABLE : DISABLE);
    }
}

void SceneDeclutterImpl::InitializeFromStage(long int stageId)
{
    auto stage = PXR_NS::UsdUtilsStageCache::Get().Find(PXR_NS::UsdStageCache::Id::FromLongInt(stageId));

    CARB_PROFILE_ZONE(1, "Initialize Visualization From Stage");

    if (!stage)
        return;


    if (m_InternalState->m_settings->getAsBool(kSettingsUseSceneVisPrim))
    {
        const PXR_NS::SdfPathVector visualizedPrims = getVisualizedPrimsFromMetadata(stage);
        for (const auto& path : visualizedPrims)
        {
            PXR_NS::UsdPrim prim = stage->GetPrimAtPath(path);
            // second condition here is to avoid a lot of USD warnings about
            // appending properties to '/' (it seems somehow `HasAttribute'
            // ends up calling `AppendProperty'...)
            if (prim.IsValid() && !prim.IsPseudoRoot())
            {
                InitializeVisualizationFromPrimAttributes(prim);
            }
        }
    }
    else
    {
        for (const PXR_NS::SdfPath& primPath : findPrimsWithAppliedAPI(stage, stageId, t_sceneVisualizationAPI))
        {
            PXR_NS::UsdPrim prim = stage->GetPrimAtPath(primPath);
            if (prim.IsValid())
            {
                InitializeVisualizationFromPrimAttributes(prim);
            }
        }
    }
}


} // namespace renderer
} // namespace omni
