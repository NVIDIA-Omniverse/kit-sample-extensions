// SPDX-FileCopyrightText: Copyright (c) 2019-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// This include must come first
// clang-format off
#include "UsdHeaders.h"
// clang-format on

#include "UsdResolve.h"

#include <carb/logging/Log.h>
#include <carb/profiler/Profile.h>

#include <pxr/usd/usdGeom/xformCommonAPI.h>
#include <pxr/usd/usdPhysics/metrics.h>
#include <pxr/usd/usdPhysics/tokens.h>


#ifdef _MSC_VER
#    pragma warning(disable : 4506) // = Gf no inline function
#endif

using namespace pxr;
using namespace carb;
using namespace omni::usd;

UsdResolve::UsdResolve() : mCustomCallbackIds(0), mCustomRuleIds(0), mAuthoringLayer(nullptr)
{
}

UsdResolve::~UsdResolve()
{
    mCustomCallbacksMap.clear();
    mCustomRulesMap.clear();
}


bool UsdResolve::checkStage(long stageId)
{
    CARB_PROFILE_ZONE(0, "UsdResolve:checkStage");
    UsdStageWeakPtr stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
    if (!stage)
    {
        CARB_LOG_ERROR("MetricAssembler: Stage not found.");
        return false;
    }

    UnitsInfo stageUnits;
    LayerUnitsMap layerUnitsMap;
    return getLayerUnits(stage, stageUnits, layerUnitsMap);
}

UnitsInfo getUnitsFromLayer(SdfLayerHandle layer, bool& mpuFound, bool& kgpuFound, bool& axisFound)
{
    SdfPath const& absRoot = SdfPath::AbsoluteRootPath();
    SdfDataRefPtr metaData = layer->GetMetadata();

    UnitsInfo units;

    // meters per units
    {
        VtValue value;
        if (metaData->Has(absRoot, UsdGeomTokens->metersPerUnit, &value))
        {
            units.metersPerUnit = value.Get<double>();
            mpuFound = true;
        }
        else
        {
            mpuFound = false;
        }
    }

    // upAxis
    {
        VtValue value;
        if (metaData->Has(absRoot, UsdGeomTokens->upAxis, &value))
        {
            units.upAxis = value.Get<TfToken>();
            axisFound = true;
        }
        else
        {
            axisFound = false;
        }
    }


    // kilograms per units
    {
        VtValue value;
        if (metaData->Has(absRoot, UsdPhysicsTokens->kilogramsPerUnit, &value))
        {
            units.kilogramsPerUnit = value.Get<double>();
            kgpuFound = true;
        }
        else
        {
            kgpuFound = false;
        }
    }

    return units;
}

UnitsInfo getStageRootUnits(UsdStageWeakPtr stage)
{
    bool mpuValid = false;
    bool kgpuValid = false;
    bool upAxisValid = false;
    UnitsInfo stageUnits = getUnitsFromLayer(stage->GetRootLayer(), mpuValid, kgpuValid, upAxisValid);

    if (!mpuValid)
    {
        stageUnits.metersPerUnit = UsdGeomGetStageMetersPerUnit(stage);
    }
    if (!kgpuValid)
    {
        stageUnits.kilogramsPerUnit = UsdPhysicsGetStageKilogramsPerUnit(stage);
    }
    if (!upAxisValid)
    {
        stageUnits.upAxis = UsdGeomGetStageUpAxis(stage);
    }

    return stageUnits;
}

inline bool layerUnitsDivergent(const UnitsInfo& units0, const UnitsInfo& units1)
{
    const double layerToleranceEpsilon = 0.01;

    if (abs(units0.metersPerUnit - units1.metersPerUnit) >
            std::max(units0.metersPerUnit, units1.metersPerUnit) * layerToleranceEpsilon ||
        abs(units0.kilogramsPerUnit - units1.kilogramsPerUnit) >
            std::max(units0.kilogramsPerUnit, units1.kilogramsPerUnit) * layerToleranceEpsilon ||
        units0.upAxis != units1.upAxis)
    {
        return true;
    }

    return false;
}

bool UsdResolve::changeStageUnits(long stageId, const UnitsInfo& newUnits)
{
    CARB_PROFILE_ZONE(0, "UsdResolve:changeStageUnits");
    UsdStageWeakPtr stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
    if (!stage)
    {
        CARB_LOG_ERROR("MetricAssembler: Stage not found.");
        return false;
    }

    UnitsInfo stageUnits;
    LayerUnitsMap layerUnitsMap;
    getLayerUnits(stage, stageUnits, layerUnitsMap, true);

    const bool divergentUnits = layerUnitsDivergent(stageUnits, newUnits);
    if (!divergentUnits)
    {
        CARB_LOG_INFO("MetricAssembler: changeStageUnits early exit newUnits identical to current stage units.");
        return true;
    }

    // change the units based on the desired newUnits
    traverseHierarchy(stageId, stage->Traverse(UsdTraverseInstanceProxies()), newUnits, layerUnitsMap, true);

    // write the new units to the metadata part
    UsdGeomSetStageMetersPerUnit(stage, newUnits.metersPerUnit);
    UsdPhysicsSetStageKilogramsPerUnit(stage, newUnits.kilogramsPerUnit);
    UsdGeomSetStageUpAxis(stage, newUnits.upAxis);
    return true;
}

bool UsdResolve::checkLayers(
    const char* layer0Id, const char* layer1Id, long stageId, UnitsInfo* layerInfo0, UnitsInfo* layerInfo1)
{
    CARB_PROFILE_ZONE(0, "UsdResolve:checkLayers");
    SdfLayerHandle layer0 = SdfLayer::Find(layer0Id);
    if (!layer0)
    {
        CARB_LOG_ERROR("MetricAssembler: Layer0 not found.");
        return false;
    }
    SdfLayerHandle layer1 = SdfLayer::Find(layer1Id);
    if (!layer1)
    {
        CARB_LOG_ERROR("MetricAssembler: Layer0 not found.");
        return false;
    }

    UsdStageWeakPtr stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));

    bool mpuValid0 = false;
    bool kgpuValid0 = false;
    bool upAxisValid0 = false;
    UnitsInfo layer0Units = getUnitsFromLayer(layer0, mpuValid0, kgpuValid0, upAxisValid0);

    bool mpuValid1 = false;
    bool kgpuValid1 = false;
    bool upAxisValid1 = false;
    UnitsInfo layer1Units = getUnitsFromLayer(layer1, mpuValid1, kgpuValid1, upAxisValid1);

    // if stage is provided we can fill in the default units making full unit divergency check
    if (stage)
    {
        UnitsInfo stageUnits = getStageRootUnits(stage);
        if (!mpuValid0)
        {
            layer0Units.metersPerUnit = stageUnits.metersPerUnit;
        }
        if (!kgpuValid0)
        {
            layer0Units.kilogramsPerUnit = stageUnits.kilogramsPerUnit;
        }
        if (!upAxisValid0)
        {
            layer0Units.upAxis = stageUnits.upAxis;
        }

        if (!mpuValid1)
        {
            layer1Units.metersPerUnit = stageUnits.metersPerUnit;
        }
        if (!kgpuValid1)
        {
            layer1Units.kilogramsPerUnit = stageUnits.kilogramsPerUnit;
        }
        if (!upAxisValid1)
        {
            layer1Units.upAxis = stageUnits.upAxis;
        }

        if (layerInfo0)
        {
            *layerInfo0 = layer0Units;
        }
        if (layerInfo1)
        {
            *layerInfo1 = layer1Units;
        }
        return layerUnitsDivergent(layer0Units, layer1Units);
    }
    else
    {
        if (mpuValid0 && mpuValid1)
        {
            if (layer0Units.metersPerUnit != layer1Units.metersPerUnit)
                return true;
        }
        if (kgpuValid0 && kgpuValid1)
        {
            if (layer0Units.kilogramsPerUnit != layer1Units.kilogramsPerUnit)
                return true;
        }
        if (upAxisValid0 && upAxisValid1)
        {
            if (layer0Units.upAxis != layer1Units.upAxis)
                return true;
        }
    }
    return false;
}

bool UsdResolve::resolveStage(long stageId)
{
    CARB_PROFILE_ZONE(0, "UsdResolve:resolveStage");
    UsdStageWeakPtr stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
    if (!stage)
    {
        CARB_LOG_ERROR("MetricAssembler: Stage not found.");
        return false;
    }

    UnitsInfo stageUnits;
    LayerUnitsMap layerUnitsMap;
    const bool divergentUnits = getLayerUnits(stage, stageUnits, layerUnitsMap);

    if (divergentUnits)
    {
        traverseHierarchy(stageId, stage->Traverse(UsdTraverseInstanceProxies()), stageUnits, layerUnitsMap);
    }

    return divergentUnits;
}

bool UsdResolve::resolveHierarchy(long stageId, const pxr::SdfPath& primPath)
{
    CARB_PROFILE_ZONE(0, "UsdResolve:traverseHierarchy");
    UsdStageWeakPtr stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
    if (!stage)
    {
        CARB_LOG_ERROR("MetricAssembler: Stage not found.");
        return false;
    }

    const UsdPrim prim = stage->GetPrimAtPath(primPath);
    if (!prim)
    {
        CARB_LOG_ERROR("MetricAssembler: Prim not found.");
        return false;
    }

    UnitsInfo stageUnits;
    LayerUnitsMap layerUnitsMap;
    const bool divergentUnits = getLayerUnits(stage, stageUnits, layerUnitsMap);

    if (divergentUnits)
    {
        traverseHierarchy(stageId, UsdPrimRange(prim, UsdTraverseInstanceProxies()), stageUnits, layerUnitsMap);
    }

    return divergentUnits;
}

bool UsdResolve::getLayerUnits(pxr::UsdStageWeakPtr stage,
                               UnitsInfo& stageUnitsOut,
                               LayerUnitsMap& layerUnitsMap,
                               bool insertRootLayer)
{
    bool divergentUnits = false;
    const SdfLayerHandle rootLayer = stage->GetRootLayer();
    bool mpuValid = false;
    bool kgpuValid = false;
    bool upAxisValid = false;
    UnitsInfo stageUnits = getStageRootUnits(stage);
    CARB_LOG_VERBOSE("MetricAssembler: RootLayer units: MPU (%f), KGPU (%f), upAxis (%s)", stageUnits.metersPerUnit,
                     stageUnits.kilogramsPerUnit, stageUnits.upAxis.GetText());

    const SdfLayerHandle sessionLayer = stage->GetSessionLayer();
    const SdfLayerHandleVector userLayers = stage->GetUsedLayers();
    for (const SdfLayerHandle& layer : userLayers)
    {
        if (layer != rootLayer && layer != sessionLayer)
        {
            UnitsInfo layerUnits = getUnitsFromLayer(layer, mpuValid, kgpuValid, upAxisValid);
            if (!mpuValid)
            {
                CARB_LOG_INFO("MetricAssembler: Layer (%s), MPU not found, falling back to stage units.",
                              layer->GetRealPath().c_str());
                layerUnits.metersPerUnit = stageUnits.metersPerUnit;
            }
            if (!kgpuValid)
            {
                CARB_LOG_INFO("MetricAssembler: Layer (%s), KGPU not found, falling back to stage units.",
                              layer->GetRealPath().c_str());
                layerUnits.kilogramsPerUnit = stageUnits.kilogramsPerUnit;
            }
            if (!upAxisValid)
            {
                CARB_LOG_INFO("MetricAssembler: Layer (%s), upAxis not found, falling back to stage units.",
                              layer->GetRealPath().c_str());
                layerUnits.upAxis = stageUnits.upAxis;
            }
            CARB_LOG_VERBOSE("MetricAssembler: Layer (%s) units: MPU (%f), KGPU (%f), upAxis (%s)",
                             layer->GetRealPath().c_str(), stageUnits.metersPerUnit, stageUnits.kilogramsPerUnit,
                             stageUnits.upAxis.GetText());

            if (layerUnitsDivergent(layerUnits, stageUnits))
            {
                divergentUnits = true;
            }

            layerUnitsMap[layer] = layerUnits;
        }
    }

    if (insertRootLayer)
    {
        layerUnitsMap[rootLayer] = stageUnits;
    }

    stageUnitsOut = stageUnits;

    return divergentUnits;
}

inline bool checkLayerStackAuthoring(const SdfPath& path, const SdfLayerRefPtrVector& divergentLayerStack)
{
    for (const SdfLayerRefPtr& stackLayer : divergentLayerStack)
    {
        const bool authoredAtHigherLayer = stackLayer->GetAttributeAtPath(path) == nullptr ? false : true;
        if (authoredAtHigherLayer)
        {
            return true;
        }
    }
    return false;
}

void UsdResolve::traverseHierarchy(long stageId,
                                   const pxr::UsdPrimRange& primRange,
                                   const UnitsInfo& stageUnits,
                                   const LayerUnitsMap& layerUnitsMap,
                                   bool forceXformOpCommonAPI)
{
    const bool hasCustomRulesOrCallbacks = !mCustomRulesMap.empty() || !mCustomCallbacksMap.empty();

    for (ResolveCallbackMap::const_reference ref : mCustomCallbacksMap)
    {
        if (ref.second.first.resolveStartFn)
        {
            ref.second.first.resolveStartFn(stageId, ref.second.first.userData);
        }
    }

    carb::settings::ISettings* settings = carb::getCachedInterface<carb::settings::ISettings>();
    const bool conformToXformCommonAPI =
        forceXformOpCommonAPI ? true : settings->getAsBool(kMetricsAssemblerConformToXformCommonAPI);

    PrimUnitMap primUnitMap;
    PXR_NS::SdfChangeBlock changeBlock;
    for (UsdPrimRange::const_iterator iter = primRange.begin(); iter != primRange.end(); ++iter)
    {
        const UsdPrim& subPrim = *iter;
        const SdfPath subPrimPath = subPrim.GetPath();

        if (!subPrim.IsValid() || subPrim.IsPseudoRoot())
        {
            continue;
        }

        SdfLayerRefPtr divergentLayer = nullptr;
        SdfLayerRefPtrVector divergentLayerStack;
        UnitsInfo divergentUnits;
        bool divergentLayerFound = false;
        bool topLevelDivergency = false;
        bool prependOp = false;

        // check parent for divergency, this might not always work, needs investigation
        {
            UsdPrim parent = subPrim.GetParent();
            while (parent && !parent.IsPseudoRoot())
            {
                PrimUnitMap::const_iterator fit = primUnitMap.find(parent);
                if (fit != primUnitMap.end())
                {
                    divergentLayerFound = true;
                    divergentUnits = fit->second.units;
                    divergentLayer = fit->second.layer;
                    divergentLayerStack = fit->second.divergentLayerStack;
                    // if we have a layer inserted with the toplevel divergency at default prim, we cant scale there
                    // we set the topLevelPrim to childs of default prim
                    if (parent == parent.GetStage()->GetDefaultPrim() && subPrim.GetParent() == parent)
                    {
                        topLevelDivergency = true;
                        prependOp = true;
                    }
                    break;
                }
                parent = parent.GetParent();
            }
        }

        if (!divergentLayerFound)
        {
            UsdPrimCompositionQuery query(subPrim);
            std::vector<UsdPrimCompositionQueryArc> arcs = query.GetCompositionArcs();
            for (size_t i = 0; i < arcs.size(); i++)
            {
                const UsdPrimCompositionQueryArc& currentArc = arcs[i];
                PcpNodeRef nodeRef = currentArc.GetTargetNode();
                PcpLayerStackRefPtr pcpLayerStack = nodeRef.GetLayerStack();
                SdfLayerRefPtrVector layerStack = pcpLayerStack->GetLayers();
                if (!layerStack.empty())
                {
                    for (size_t j = 0; j < layerStack.size(); j++)
                    {
                        const SdfLayerRefPtr testLayer = layerStack[j];
                        const SdfLayerHandle testLayerHandle = testLayer;
                        LayerUnitsMap::const_iterator fit = layerUnitsMap.find(testLayerHandle);
                        if (fit != layerUnitsMap.end())
                        {
                            if (layerUnitsDivergent(stageUnits, fit->second))
                            {
                                divergentUnits = fit->second;
                                divergentLayerFound = true;
                                topLevelDivergency = true;
                                divergentLayer = testLayer;
                                primUnitMap[subPrim] = { divergentUnits, divergentLayer, divergentLayerStack };
                                break;
                            }
                        }
                        divergentLayerStack.push_back(testLayer);
                    }
                }

                if (divergentLayerFound)
                    break;
            }
        }

        if (!divergentLayerFound)
        {
            CARB_LOG_VERBOSE("MetricAssembler: Skip prim not divergent %s", subPrim.GetPrimPath().GetText());
            continue;
        }

        CARB_LOG_VERBOSE("MetricAssembler: Prim divergent %s", subPrim.GetPrimPath().GetText());

        bool skipPrim = false;
        for (ResolveCallbackMap::const_reference ref : mCustomCallbacksMap)
        {
            if (ref.second.first.resolvePrimFn)
            {
                if (mAuthoringLayer)
                {
                    pxr::UsdEditContext editContext(subPrim.GetStage(), mAuthoringLayer);
                    if (!ref.second.first.resolvePrimFn(subPrim, stageUnits, divergentUnits, ref.second.first.userData))
                    {
                        skipPrim = true;
                        break;
                    }
                }
                else
                {
                    if (!ref.second.first.resolvePrimFn(subPrim, stageUnits, divergentUnits, ref.second.first.userData))
                    {
                        skipPrim = true;
                        break;
                    }
                }
            }
        }
        if (skipPrim)
            continue;

        // resolve xformOp changes
        UsdGeomXformable xform(subPrim);
        if (topLevelDivergency && xform && subPrim != subPrim.GetStage()->GetDefaultPrim())
        {
            // xfromOp changes should be resolved in the current authoring layer
            {
                resolveXformOp(xform, stageUnits, divergentUnits, divergentLayerStack, prependOp,
                               conformToXformCommonAPI, !forceXformOpCommonAPI);
            }
        }

        // skip attribute traversal and prune children if no custom rules or callbacks are registered
        if (!hasCustomRulesOrCallbacks)
        {
            // prune children - they would only inherit divergency with no rules to apply
            // exception: default prim's direct children may need xformOp resolution
            if (subPrim != subPrim.GetStage()->GetDefaultPrim())
            {
                iter.PruneChildren();
            }
            continue;
        }

        UsdAttributeVector attributes = subPrim.GetAuthoredAttributes();
        for (UsdAttribute& attr : attributes)
        {
            {
                // check if the attribute was not already overriden by upper layer
                const bool alreadyAuthored = checkLayerStackAuthoring(attr.GetPath(), divergentLayerStack);
                if (alreadyAuthored)
                {
                    CARB_LOG_VERBOSE(
                        "MetricAssembler: Attribute already authored in higher layer: %s", attr.GetName().GetText());
                    continue;
                }

                bool skipAttribute = false;
                int metersExponent = 0;
                int kilogramsExponent = 0;
                getAttributeRule(attr.GetName(), metersExponent, kilogramsExponent);
                for (ResolveCallbackMap::const_reference ref : mCustomCallbacksMap)
                {
                    if (ref.second.first.resolveAttributeFn &&
                        (ref.second.second.empty() || ref.second.second.find(attr.GetName()) != ref.second.second.end()))
                    {
                        if (mAuthoringLayer)
                        {
                            pxr::UsdEditContext editContext(subPrim.GetStage(), mAuthoringLayer);
                            if (!ref.second.first.resolveAttributeFn(subPrim, attr, stageUnits, divergentUnits,
                                                                     metersExponent, kilogramsExponent,
                                                                     ref.second.first.userData))
                            {
                                skipAttribute = true;
                                break;
                            }
                        }
                        else
                        {
                            if (!ref.second.first.resolveAttributeFn(subPrim, attr, stageUnits, divergentUnits,
                                                                     metersExponent, kilogramsExponent,
                                                                     ref.second.first.userData))
                            {
                                skipAttribute = true;
                                break;
                            }
                        }
                    }
                }
                if (skipAttribute)
                {
                    CARB_LOG_VERBOSE("MetricAssembler: Attribute skip requested: %s", attr.GetName().GetText());
                    continue;
                }
                if (metersExponent == 0 && kilogramsExponent == 0)
                {
                    CARB_LOG_VERBOSE(
                        "MetricAssembler: Attribute resolve skipped no rule to apply: %s", attr.GetName().GetText());
                    continue;
                }

                if (subPrim.IsInstanceProxy())
                {
                    CARB_LOG_ERROR(
                        "MetricAssembler: Attribute resolve skipped for prim: %s, prim belongs to a Scene Graph Instance",
                        subPrim.GetPrimPath().GetText());
                    break;
                }

                // resolve
                CARB_LOG_VERBOSE("MetricAssembler: Resolving attr: %s with metersExp: %d, kilogramsExp: %d",
                                 attr.GetName().GetText(), metersExponent, kilogramsExponent);
                if (mAuthoringLayer)
                {
                    pxr::UsdEditContext editContext(subPrim.GetStage(), mAuthoringLayer);
                    resolveAttribute(attr, stageUnits, divergentUnits, metersExponent, kilogramsExponent);
                }
                else
                {
                    resolveAttribute(attr, stageUnits, divergentUnits, metersExponent, kilogramsExponent);
                }
            }
        }
    }

    for (ResolveCallbackMap::const_reference ref : mCustomCallbacksMap)
    {
        if (ref.second.first.resolveEndFn)
        {
            ref.second.first.resolveEndFn(stageId, ref.second.first.userData);
        }
    }
}

void applyXRotationCorrection(float correction, GfVec3f& rotation, const UsdGeomXformCommonAPI::RotationOrder rotOrder)
{
    switch (rotOrder)
    {
        case UsdGeomXformCommonAPI::RotationOrder::RotationOrderXYZ:
        case UsdGeomXformCommonAPI::RotationOrder::RotationOrderXZY:
            rotation[0] += correction;
            break;
        case UsdGeomXformCommonAPI::RotationOrder::RotationOrderYXZ:
        case UsdGeomXformCommonAPI::RotationOrder::RotationOrderZXY:
            rotation[1] += correction;
            break;
        case UsdGeomXformCommonAPI::RotationOrder::RotationOrderYZX:
        case UsdGeomXformCommonAPI::RotationOrder::RotationOrderZYX:
            rotation[2] += correction;
            break;
    };
}

static const TfToken gTokScale = UsdGeomXformOp::GetOpName(UsdGeomXformOp::TypeScale);
static const TfToken gTokRotateXYZ = UsdGeomXformOp::GetOpName(UsdGeomXformOp::TypeRotateXYZ);

bool setPrimXformOp(UsdGeomXformable& primXform, const GfVec3f& value, const TfToken& opToken)
{
    bool scaleSet = false;

    bool resetXformStack = false;
    const std::vector<UsdGeomXformOp> xformOps = primXform.GetOrderedXformOps(&resetXformStack);
    for (const UsdGeomXformOp& op : xformOps)
    {
        const TfToken opName = op.GetOpName();
        const UsdGeomXformOp::Precision opPrecision = op.GetPrecision();

        if (opName == opToken)
        {
            if (opPrecision == UsdGeomXformOp::PrecisionFloat)
            {
                op.Set(GfVec3f(value));
                scaleSet = true;
            }
            else if (opPrecision == UsdGeomXformOp::PrecisionDouble)
            {
                op.Set(GfVec3d(value));
                scaleSet = true;
            }
        }
    }

    return scaleSet;
}


void UsdResolve::resolveXformOp(pxr::UsdGeomXformable& xform,
                                const UnitsInfo& stageUnits,
                                const UnitsInfo& divergentUnits,
                                const SdfLayerRefPtrVector& divergentLayerStack,
                                bool prependOp,
                                bool conformToXformCommonAPI,
                                bool writeMetadata)
{
    const bool stageUpAxisDivergent = stageUnits.upAxis != divergentUnits.upAxis;
    const bool mpuDivergent = abs(stageUnits.metersPerUnit - divergentUnits.metersPerUnit) > 1e-04;
    if (!stageUpAxisDivergent && !mpuDivergent)
        return;

    // If conformToXformCommonAPI then we dont add unitsResolve but apply the changes directly
    // this does have a side effect that this change is destructive, we cant recover from this nor resolve
    // again. Not recommended to use by default.
    bool xformOpCommonAPIApplied = false;
    if (conformToXformCommonAPI)
    {
        pxr::UsdGeomXformCommonAPI xformCommonAPI = pxr::UsdGeomXformCommonAPI(xform.GetPrim());

        if (xformCommonAPI)
        {
            static TfToken gCommonAPIResolveWritten("metricsAssembler:commonAPIResolveWritten");
            VtValue v;
            bool resolveWritten = false;

            if (xform.GetPrim().GetMetadataByDictKey(SdfFieldKeys->CustomData, gCommonAPIResolveWritten, &v))
            {
                resolveWritten = v.Get<bool>();
            }

            if (resolveWritten)
            {
                xformOpCommonAPIApplied = true;
            }
            else
            {
                GfVec3d translation;
                GfVec3f rotation;
                GfVec3f scale;
                GfVec3f pivot;
                UsdGeomXformCommonAPI::RotationOrder rotOrder;
                const bool retVal = xformCommonAPI.GetXformVectors(
                    &translation, &rotation, &scale, &pivot, &rotOrder, UsdTimeCode::Default());

                if (retVal)
                {
                    // resolve upAxis divergence, only Y and Z are supported
                    if (stageUpAxisDivergent)
                    {
                        CARB_LOG_VERBOSE(
                            "MetricAssembler: Divergent upAxis found: %s", xform.GetPrim().GetPrimPath().GetText());
                        if (divergentUnits.upAxis == UsdGeomTokens->z)
                        {
                            // from Z to Y
                            const float correction = -90.0;
                            applyXRotationCorrection(correction, rotation, rotOrder);
                            if ((rotOrder != UsdGeomXformCommonAPI::RotationOrder::RotationOrderXYZ) ||
                                !setPrimXformOp(xform, rotation, gTokRotateXYZ))
                            {
                                xformCommonAPI.SetRotate(rotation, rotOrder);
                            }
                        }
                        else if (divergentUnits.upAxis == UsdGeomTokens->y)
                        {
                            // from Y to Z
                            const float correction = 90.0;
                            applyXRotationCorrection(correction, rotation, rotOrder);
                            if ((rotOrder != UsdGeomXformCommonAPI::RotationOrder::RotationOrderXYZ) ||
                                !setPrimXformOp(xform, rotation, gTokRotateXYZ))
                            {
                                xformCommonAPI.SetRotate(rotation, rotOrder);
                            }
                        }
                    }

                    // resolve MPU divergency
                    if (mpuDivergent)
                    {
                        CARB_LOG_VERBOSE(
                            "MetricAssembler: Applying scale divergency: %s", xform.GetPrim().GetPrimPath().GetText());
                        const float mpuDivergency = (float)divergentUnits.metersPerUnit / (float)stageUnits.metersPerUnit;
                        scale = scale * mpuDivergency;
                        if (!setPrimXformOp(xform, scale, gTokScale))
                        {
                            xformCommonAPI.SetScale(scale);
                        }
                    }

                    if (writeMetadata)
                    {
                        xform.GetPrim().SetMetadataByDictKey(
                            SdfFieldKeys->CustomData, gCommonAPIResolveWritten, VtValue(true));
                    }

                    xformOpCommonAPIApplied = true;
                }
            }
        }
    }

    if (!xformOpCommonAPIApplied)
    {
        static TfToken divergencySuffixToken("unitsResolve");
        static TfToken pivotSuffixToken("pivot");

        GfVec3d appliedResolveScale(1.0);
        double appliedResolveRotate(0.0);

        UsdPrim parent = xform.GetPrim().GetParent();
        const UsdStageWeakPtr stage = xform.GetPrim().GetStage();
        while (parent && parent != stage->GetPseudoRoot())
        {
            if (parent.IsA<UsdGeomXformable>())
            {
                pxr::UsdGeomXformable xf(parent);
                bool resetXformStack;
                std::vector<UsdGeomXformOp> xformOps = xf.GetOrderedXformOps(&resetXformStack);
                for (const UsdGeomXformOp& op : xformOps)
                {
                    const std::vector<std::string> splitName = op.SplitName();
                    if (splitName.back() == divergencySuffixToken.GetString())
                    {
                        if (op.GetOpType() == UsdGeomXformOp::Type::TypeScale)
                        {
                            GfVec3d localScale(0.0);
                            op.Get(&localScale);
                            appliedResolveScale = GfCompMult(appliedResolveScale, localScale);
                        }
                        else if (op.GetOpType() == UsdGeomXformOp::Type::TypeRotateX)
                        {
                            double localRot(0.0);
                            op.Get(&localRot);
                            appliedResolveRotate = appliedResolveRotate + localRot;
                        }
                    }
                }
            }
            parent = parent.GetParent();
        }

        bool resetXformStack;
        std::vector<UsdGeomXformOp> xformOps = xform.GetOrderedXformOps(&resetXformStack);
        SdfPath rotateXYZPath;
        bool scaleApplied = false;
        bool rotateApplied = false;
        bool pivotInverseApplied = false;
        UsdGeomXformOp pivotXformOp;
        for (const UsdGeomXformOp& op : xformOps)
        {
            const std::vector<std::string> splitName = op.SplitName();
            if (splitName.back() == divergencySuffixToken.GetString())
            {
                CARB_LOG_VERBOSE("MetricAssembler: Found already applied units transformation: %s",
                                 xform.GetPrim().GetPrimPath().GetText());
                if (op.GetOpType() == UsdGeomXformOp::Type::TypeScale)
                {
                    scaleApplied = true;
                }
                else if (op.GetOpType() == UsdGeomXformOp::Type::TypeRotateX)
                {
                    rotateApplied = true;
                }
            }
            else if (op.IsInverseOp() && splitName.back() == pivotSuffixToken.GetString())
            {
                pivotInverseApplied = true;
                pivotXformOp = op;
            }
        }

        UsdGeomXformOp rotateUROp;
        UsdGeomXformOp scaleUROp;

        // resolve upAxis divergence, only Y and Z are supported
        if (!rotateApplied)
        {
            if (stageUpAxisDivergent)
            {
                UsdGeomXformOp fixRotOp;
                CARB_LOG_VERBOSE("MetricAssembler: Divergent upAxis found: %s", xform.GetPrim().GetPrimPath().GetText());
                if (divergentUnits.upAxis == UsdGeomTokens->z)
                {
                    // from Z to Y
                    const double correction = -90.0 - appliedResolveRotate;
                    fixRotOp = xform.AddRotateXOp(UsdGeomXformOp::PrecisionDouble, divergencySuffixToken);
                    fixRotOp.Set(correction);
                }
                else if (divergentUnits.upAxis == UsdGeomTokens->y)
                {
                    // from Y to Z
                    const double correction = 90.0 - appliedResolveRotate;
                    fixRotOp = xform.AddRotateXOp(UsdGeomXformOp::PrecisionDouble, divergencySuffixToken);
                    fixRotOp.Set(correction);
                }
                rotateUROp = fixRotOp;
            }
        }

        // resolve MPU divergency
        if (!scaleApplied)
        {
            if (mpuDivergent)
            {
                CARB_LOG_VERBOSE(
                    "MetricAssembler: Applying scale divergency: %s", xform.GetPrim().GetPrimPath().GetText());
                const double mpuDivergency = divergentUnits.metersPerUnit / stageUnits.metersPerUnit;
                const GfVec3d mpuDivergencyVec = GfCompDiv(GfVec3d(mpuDivergency), appliedResolveScale);
                scaleUROp = xform.AddScaleOp(UsdGeomXformOp::PrecisionDouble, divergencySuffixToken);
                scaleUROp.Set(mpuDivergencyVec);
            }
        }

        if (prependOp && (rotateUROp || scaleUROp))
        {
            bool resetStack;
            std::vector<UsdGeomXformOp> xformOpOrder = xform.GetOrderedXformOps(&resetStack);
            std::vector<UsdGeomXformOp> newOrder;
            if (rotateUROp && scaleUROp)
            {
                newOrder.push_back(rotateUROp);
                newOrder.push_back(scaleUROp);
                xformOpOrder.pop_back();
                xformOpOrder.pop_back();
            }
            else
            {
                newOrder.push_back(xformOpOrder.back());
                xformOpOrder.pop_back();
            }

            for (size_t i = 0; i < xformOpOrder.size(); i++)
            {
                newOrder.push_back(xformOpOrder[i]);
            }
            xform.SetXformOpOrder(newOrder, resetStack);
        }

        if (!prependOp && pivotInverseApplied)
        {
            bool resetStack;
            std::vector<UsdGeomXformOp> xformOpOrder = xform.GetOrderedXformOps(&resetStack);
            std::vector<UsdGeomXformOp> newOrder;
            for (size_t i = 0; i < xformOpOrder.size(); i++)
            {
                if (!xformOpOrder[i].IsInverseOp())
                {
                    newOrder.push_back(xformOpOrder[i]);
                }
                else
                {
                    const std::vector<std::string> splitName = xformOpOrder[i].SplitName();
                    if (splitName.back() == pivotSuffixToken.GetString())
                    {
                        continue;
                    }
                    else
                    {
                        newOrder.push_back(xformOpOrder[i]);
                    }
                }
            }
            newOrder.push_back(pivotXformOp);
            xform.SetXformOpOrder(newOrder, resetStack);
        }
    }
}

void updateValueAtTime(pxr::UsdAttribute& attribute, double metersResolve, double kilogramsResolve, pxr::UsdTimeCode timeCode)
{
    VtValue value;
    attribute.Get(&value, timeCode);

    if (value.IsHolding<float>())
    {
        const float resolvedValue = value.Get<float>() * (float)metersResolve * (float)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<double>())
    {
        const double resolvedValue = value.Get<double>() * (double)metersResolve * (double)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<GfHalf>())
    {
        const GfHalf resolvedValue = value.Get<GfHalf>() * (float)metersResolve * (float)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<GfVec2h>())
    {
        const GfVec2h resolvedValue = value.Get<GfVec2h>() * (double)metersResolve * (double)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<GfVec2f>())
    {
        const GfVec2f resolvedValue = value.Get<GfVec2f>() * (double)metersResolve * (double)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<GfVec2d>())
    {
        const GfVec2d resolvedValue = value.Get<GfVec2d>() * (double)metersResolve * (double)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<GfVec3h>())
    {
        const GfVec3h resolvedValue = value.Get<GfVec3h>() * (double)metersResolve * (double)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<GfVec3f>())
    {
        const GfVec3f resolvedValue = value.Get<GfVec3f>() * (double)metersResolve * (double)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else if (value.IsHolding<GfVec3d>())
    {
        const GfVec3d resolvedValue = value.Get<GfVec3d>() * (double)metersResolve * (double)kilogramsResolve;
        attribute.Set(resolvedValue, timeCode);
    }
    else
    {
        CARB_LOG_ERROR_ONCE("MetricAssembler: Failed to resolve value (type %s), for attribute: %s",
                            value.GetTypeName().c_str(), attribute.GetName().GetText());
    }
}

void UsdResolve::resolveAttribute(pxr::UsdAttribute& attribute,
                                  const UnitsInfo& stageUnits,
                                  const UnitsInfo& divergentUnits,
                                  int metersExponent,
                                  int kilogramsExponent)
{
    // resolvedValue = value * (MPU / stageMPU) ^ metersExponent * (KGPU / stageKGPU) ^ kilogramsExponent
    const double metersResolve =
        metersExponent ? pow(divergentUnits.metersPerUnit / stageUnits.metersPerUnit, metersExponent) : 1;
    const double kilogramsResolve =
        kilogramsExponent ? pow(divergentUnits.kilogramsPerUnit / stageUnits.kilogramsPerUnit, kilogramsExponent) : 1;

    if (attribute.ValueMightBeTimeVarying())
    {
        std::vector<double> timeCodes;
        if (attribute.GetTimeSamples(&timeCodes))
        {
            for (const double& time : timeCodes)
            {
                const UsdTimeCode currentTimeCode(time);
                updateValueAtTime(attribute, metersResolve, kilogramsResolve, currentTimeCode);
            }
        }
    }
    else
    {
        updateValueAtTime(attribute, metersResolve, kilogramsResolve, UsdTimeCode::Default());
    }
}

void UsdResolve::getAttributeRule(const pxr::TfToken& attributeName, int& metersExponent, int& kilogramsExponent)
{
    ResolveRuleMap::const_iterator fit = mCustomRulesMap.find(attributeName);
    if (fit != mCustomRulesMap.end())
    {
        metersExponent = fit->second.metersExponent;
        kilogramsExponent = fit->second.kilogramExponent;
        return;
    }
    metersExponent = 0;
    kilogramsExponent = 0;
}

size_t UsdResolve::registerCustomCallback(IMetricsAssemblerCallback& customCallback,
                                          const std::vector<pxr::TfToken>* attributeResolveFnTokens)
{
    const size_t id = ++mCustomCallbackIds;
    AttributeTokenSet tokenSet;
    if (attributeResolveFnTokens)
    {
        for (const pxr::TfToken& t : *attributeResolveFnTokens)
        {
            tokenSet.insert(t);
        }
    }

    mCustomCallbacksMap[id] = std::make_pair(customCallback, tokenSet);
    return id;
}

void UsdResolve::unregisterCustomCallback(size_t id)
{
    ResolveCallbackMap::iterator fit = mCustomCallbacksMap.find(id);
    if (fit != mCustomCallbacksMap.end())
    {
        mCustomCallbacksMap.erase(fit);
    }
    else
    {
        CARB_LOG_ERROR("MetricAssembler: Failed to unregister custom callback.");
    }
}

size_t UsdResolve::registerCustomResolveRule(pxr::TfToken attributeName, int metersExponent, int kilogramsExponent)
{
    {
        ResolveRuleMap::const_iterator fit = mCustomRulesMap.find(attributeName);
        if (fit != mCustomRulesMap.end())
        {
            CARB_LOG_ERROR("MetricAssembler: AttributeName already registred: %s", attributeName.GetText());
            return kInvalidRegistryId;
        }
    }
    const size_t id = ++mCustomRuleIds;
    mCustomRulesMap[attributeName] = { metersExponent, kilogramsExponent, id };
    return id;
}

void UsdResolve::unregisterCustomResolveRule(size_t id)
{
    bool ruleFound = false;
    ResolveRuleMap::iterator it = mCustomRulesMap.begin();
    while (it != mCustomRulesMap.end())
    {
        if (it->second.id == id)
        {
            mCustomRulesMap.erase(it);
            ruleFound = true;
            break;
        }
        it++;
    }
    if (!ruleFound)
    {
        CARB_LOG_ERROR("MetricAssembler: Failed to unregister custom rule.");
    }
}

void UsdResolve::setResolveLayer(const char* layerIdentifier)
{
    if (layerIdentifier)
    {
        mAuthoringLayer = SdfLayer::Find(layerIdentifier);
    }
    else
    {
        mAuthoringLayer = nullptr;
    }
}
