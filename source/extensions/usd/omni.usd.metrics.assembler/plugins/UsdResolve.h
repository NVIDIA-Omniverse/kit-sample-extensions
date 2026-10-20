// SPDX-FileCopyrightText: Copyright (c) 2019-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <omni/usd/IMetricsAssembler.h>

#include <map>
#include <unordered_map>

namespace omni
{
namespace usd
{
struct ResolveRule
{
    int metersExponent;
    int kilogramExponent;
    size_t id;
};

struct LayerUnitInfo
{
    UnitsInfo units;
    pxr::SdfLayerRefPtr layer;
    pxr::SdfLayerRefPtrVector divergentLayerStack;
};

using ResolveRuleMap = std::unordered_map<pxr::TfToken, ResolveRule, pxr::TfToken::HashFunctor>;
using AttributeTokenSet = std::unordered_set<pxr::TfToken, pxr::TfToken::HashFunctor>;
using ResolveCallbackMap = std::unordered_map<size_t, std::pair<IMetricsAssemblerCallback, AttributeTokenSet>>;
using LayerUnitsMap = std::map<pxr::SdfLayerHandle, UnitsInfo>;
using PrimUnitMap = std::map<const pxr::UsdPrim, LayerUnitInfo>;

class UsdResolve
{
public:
    UsdResolve();
    ~UsdResolve();

    bool checkStage(long stageId);
    bool checkLayers(const char* layer0, const char* layer1, long stageId, UnitsInfo* layerInfo0, UnitsInfo* layerInfo1);
    bool resolveStage(long stageId);
    bool resolveHierarchy(long stageId, const pxr::SdfPath& primPath);

    size_t registerCustomCallback(IMetricsAssemblerCallback& customCallback,
                                  const std::vector<pxr::TfToken>* attributeResolveFnTokens);
    void unregisterCustomCallback(size_t id);

    size_t registerCustomResolveRule(pxr::TfToken attributeName, int metersExponent, int kilogramsExponent);
    void unregisterCustomResolveRule(size_t id);

    void setResolveLayer(const char* resolveLayer);

    bool changeStageUnits(long stageId, const UnitsInfo& newUnits);

private:
    void traverseHierarchy(long stageId,
                           const pxr::UsdPrimRange& range,
                           const UnitsInfo& stageUnits,
                           const LayerUnitsMap& layerUnitsMap,
                           bool forceXformOpCommonAPI = false);
    bool getLayerUnits(pxr::UsdStageWeakPtr stage,
                       UnitsInfo& stageUnits,
                       LayerUnitsMap& layerUnitsMap,
                       bool insertRootLayer = false);
    void getAttributeRule(const pxr::TfToken& attributeName, int& metersExponent, int& kilogramsExponent);
    void resolveAttribute(pxr::UsdAttribute& attribute,
                          const UnitsInfo& stageUnits,
                          const UnitsInfo& divergentUnits,
                          int metersExponent,
                          int kilogramsExponent);
    void resolveXformOp(pxr::UsdGeomXformable& xform,
                        const UnitsInfo& stageUnits,
                        const UnitsInfo& divergentUnits,
                        const pxr::SdfLayerRefPtrVector& divergentLayerStack,
                        bool prependOp,
                        bool conformToXformCommonAPI,
                        bool writeMetadata);

private:
    size_t mCustomCallbackIds;
    ResolveCallbackMap mCustomCallbacksMap;

    size_t mCustomRuleIds;
    ResolveRuleMap mCustomRulesMap;

    pxr::SdfLayerRefPtr mAuthoringLayer;
};

} // namespace usd
} // namespace omni
