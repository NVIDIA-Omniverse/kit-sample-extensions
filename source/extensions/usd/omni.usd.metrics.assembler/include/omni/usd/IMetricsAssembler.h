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

#include <carb/Interface.h>

namespace omni
{
namespace usd
{

const size_t kInvalidRegistryId = 0xFFffFFffFF;

/// Settings for the operation mode, determines what happens when divergency is found
///
/// Expected integer values:
///     DISABLED = 0
///     WARN = 1
///     ASK = 2
///     AUTO = 3
static constexpr char kMetricsAssemblerOperationMode[] = "/metricsAssembler/operationMode";

static constexpr char kMetricsAssemblerParamsChangeListenerEnabled[] = "/metricsAssembler/changeListenerEnabled";

static constexpr char kMetricsAssemblerShowUnitsOverlay[] = "/metricsAssembler/showUnitsOverlay"; // OBSOLETE

// If true, additional xformOps with unitsResolve suffix are not created, instead XformCommonAPI is used to adjust the
// xformOp stack
static constexpr char kMetricsAssemblerConformToXformCommonAPI[] = "/metricsAssembler/conformToXformCommonAPI";

/// Units information
struct UnitsInfo
{
    double metersPerUnit;
    double kilogramsPerUnit;
    pxr::TfToken upAxis;
};

/// Call when resolve starts
///
/// \param[in] stageId USD stageId.
/// \param[in] userData Provided user data.
typedef void (*ResolveStart)(long stageId, void* userData);

/// Call when resolve ends
///
/// \param[in] stageId USD stageId.
/// \param[in] userData Provided user data.
typedef void (*ResolveEnd)(long stageId, void* userData);

/// Resolve given USD prim
///
/// \param[in] usdPrim USD prim to resolve.
/// \param[in/out] attribute Current attribute to resolve.
/// \param[in] stageUnits Stage units.
/// \param[in] resolveUnits Units to resolve.
/// \param[in/out] metersExponent Current metersExponent, can be modified by the function.
/// \param[in/out] kilogramsExponent Current kilogramsExponent, can be modified by the function.
/// \param[in] userData Provided user data.
/// \return Return false to skip prim resolve
typedef bool (*ResolvePrim)(const pxr::UsdPrim& usdPrim,
                            const UnitsInfo& stageUnits,
                            const UnitsInfo& resolveUnits,
                            void* userData);

/// Resolve given USD prim attribute
///
/// \param[in] usdPrim USD prim to resolve.
/// \param[in/out] attribute Current attribute to resolve.
/// \param[in] stageUnits Stage units.
/// \param[in] resolveUnits Units to resolve.
/// \param[in/out] metersExponent Current metersExponent, can be modified by the function.
/// \param[in/out] kilogramsExponent Current kilogramsExponent, can be modified by the function.
/// \param[in] userData Provided user data.
/// \return Return false to skip prim resolve
typedef bool (*ResolveAttribute)(const pxr::UsdPrim& usdPrim,
                                 pxr::UsdAttribute& attribute,
                                 const UnitsInfo& stageUnits,
                                 const UnitsInfo& resolveUnits,
                                 int& metersExponent,
                                 int& kilogramsExponent,
                                 void* userData);

/// Custom joint strcuture holding function pointers for callbacks
struct IMetricsAssemblerCallback
{
    ResolveStart resolveStartFn = { nullptr };
    ResolveEnd resolveEndFn = { nullptr };
    ResolvePrim resolvePrimFn = { nullptr };
    ResolveAttribute resolveAttributeFn = { nullptr };
    void* userData = { nullptr };
};

/// Metrics Assemblerinterface
struct IMetricsAssembler
{
    CARB_PLUGIN_INTERFACE("omni::usd::IMetricsAssembler", 1, 0)

    /// Check given USD stage for units divergency
    /// \param[in] stageId USD stage id.
    /// \return True if divergent stage units were found.
    bool(CARB_ABI* checkStage)(long stageId);

    /// Check given two layers for units divergency
    /// \param[in] layer0Id Layer0 identifier.
    /// \param[in] layer1Id Layer1 identifier.
    /// \param[in] stageId USD stage id. Providing stageId will setup default units for undefined units. If 0 provided
    /// only defined units are compared. \param[out] layerInfo0 Layer0 units information. \param[out] layerInfo1 Layer1
    /// units information. \return True if divergent units were found.
    bool(CARB_ABI* checkLayers)(
        const char* layer0Id, const char* layer1Id, long stageId, UnitsInfo* layerInfo0, UnitsInfo* layerInfo1);

    /// Resolve given USD stage
    /// \param[in] stageId USD stage id.
    /// \return True if divergent stage units were found.
    bool(CARB_ABI* resolveStage)(long stageId);

    /// Resolve given USD stage hierarchy starting with given prim path.
    /// \param[in] stageId USD stage id.
    /// \param[in] primPath Prim path where to start traversing.
    /// \return True if divergent stage units were found.
    bool(CARB_ABI* resolveHierarchy)(long stageId, const pxr::SdfPath& primPath);

    /// Set layer where to write the changes.
    /// \param[in] layerIdentifier Layer identifier.
    void(CARB_ABI* setResolveLayer)(const char* layerIdentifier);

    /// Register custom asset resolver callback to run custom rules
    /// \param[in] customCallback Custom callback.
    /// \param[in] optional but recommended list of attribute tokens, when an attribute with this token name is resolved
    /// the resolveAttributeFn is called otherwise its not called. If nullptr the resolve is called from each attribute,
    /// this will have performance implications. \return Registry id required for unregister.
    size_t(CARB_ABI* registerCustomCallback)(IMetricsAssemblerCallback& customCallback,
                                             const std::vector<pxr::TfToken>* attributeResolveFnTokens);

    /// Unregister custom asset resolver callback to run custom rules
    /// \param[in] id Custom callback id.
    void(CARB_ABI* unregisterCustomCallback)(size_t id);

    /// Register custom asset resolver rule
    ///
    /// The applied rule works like this:
    /// resolvedValue = value * (MPU/stageMPU)^metersExponent * (KGPU/stageKGPU)^kilogramsExponent
    ///
    /// \param[in] attributeName Attribute name.
    /// \param[in] metersExponent Meters exponent to apply.
    /// \param[in] kilogramsExponent Kilograms exponent to apply.
    /// \return Registry id required for unregister.
    size_t(CARB_ABI* registerCustomResolveRule)(pxr::TfToken attributeName, int metersExponent, int kilogramsExponent);

    /// Unregister custom resolve rule.
    /// \param[in] id Custom rule id.
    void(CARB_ABI* unregisterCustomResolveRule)(size_t id);

    /// Change stage units
    ///
    /// \note This operation is destructive and will happen with the current active target layer
    ///       Additionally the xformOpCommonAPI is used for the xformOp stack transformation.
    ///
    /// \param[in] stageId USD stage id.
    /// \param[in] newUnits New desired units for the stage
    /// \return True if operation was succesfull.
    bool(CARB_ABI* changeStageUnits)(long stageId, const UnitsInfo& newUnits);
};

} // namespace usd
} // namespace omni
