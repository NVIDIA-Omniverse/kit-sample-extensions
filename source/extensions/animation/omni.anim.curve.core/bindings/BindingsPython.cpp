// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "PreUsdHeaders.h"
#include <omni/usd/UsdContextIncludes.h>
#include <animationSchema/animationCurveTypes.h>
#include "PostUsdHeaders.h"
// clang-format on

#include "../plugins/IAnimCurve.h"
#include "../plugins/SimplificationUtils.h"

#include <carb/BindingsPythonUtils.h>
#include <carb/events/IEvents.h>

CARB_BINDINGS("omni.anim.curve.core.python")
DISABLE_PYBIND11_DYNAMIC_CAST(carb::events::IEventStream);

using namespace pxr;

namespace
{
struct ReadOnlyKey : public AnimationSchemaAnimationCurve::Key
{
};

PYBIND11_MODULE(_animcurve, m)
{
    // clang-format offPLUG_FLAG_NONE
    m.doc() = "pybind11 omni.anim.curve.core bindings";

    using namespace omni::anim;
    using namespace carb;
    using namespace AnimationSchemaAnimationCurve;

    py::enum_<IAnimCurve::CurveEventType>(m, "CurveEventType")
        .value("Added", IAnimCurve::CurveEventType::Added)
        .value("Removed", IAnimCurve::CurveEventType::Removed)
        .value("Updated", IAnimCurve::CurveEventType::Updated)
        .value("KeySelectionChanged", IAnimCurve::CurveEventType::KeySelectionChanged);

    py::class_<Tangent>(m, "Tangent")
        .def_readwrite("time", &Tangent::time)
        .def_readwrite("value", &Tangent::value)
        .def_property(
            "type", [](Tangent& tangent) { return tangent.type.GetString(); },
            [](Tangent& tangent, std::string& token) { tangent.type = TfToken(token); });

    py::class_<Key>(m, "Key")
        .def(py::init())
        .def(py::init(
            [](const ReadOnlyKey& readOnlyKey)
            {
                Key key;
                key = readOnlyKey;
                return key;
            }))
        .def_readwrite("time", &Key::time)
        .def_readwrite("value", &Key::value)
        .def_readwrite("inTangent", &Key::inTangent)
        .def_readwrite("outTangent", &Key::outTangent)
        .def_readwrite("tangentBroken", &Key::tangentBroken)
        .def_readwrite("tangentWeighted", &Key::tangentWeighted);

    py::class_<ReadOnlyKey, Key>(m, "ReadOnlyKey")
        .def_readonly("time", &Key::time)
        .def_readonly("value", &Key::value)
        .def_readonly("inTangent", &Key::inTangent)
        .def_readonly("outTangent", &Key::outTangent)
        .def_readonly("tangentBroken", &Key::tangentBroken)
        .def_readonly("tangentWeighted", &Key::tangentWeighted);

    struct PyCurve
    {
        const IAnimCurve::Curve& curve;
        pxr::SdfPath curvePath;
    };

    py::class_<PyCurve>(m, "Curve")
        .def_property_readonly(
            "keys", [](const PyCurve& pyCurve) { return (const std::vector<ReadOnlyKey>&)pyCurve.curve.keys; })
        .def_property(
            "overriden_keys", [](const PyCurve& pyCurve) { return pyCurve.curve.overridenKeys; },
            [](PyCurve& pyCurve, const std::vector<pxr::AnimationSchemaAnimationCurve::Key>& keys)
            {
                auto iAnimCurve = carb::getCachedInterface<omni::anim::IAnimCurve>();
                if (!iAnimCurve)
                    return;

                iAnimCurve->setOverridenKeys(pyCurve.curvePath, keys);
            })
        .def_property_readonly(
            "anim_data", [](const PyCurve& pyCurve) { return pyCurve.curve.animData.GetPath().GetString(); })
        .def_property_readonly(
            "pre_infinity_type", [](const PyCurve& pyCurve) { return pyCurve.curve.preInfinityType.GetText(); })
        .def_property_readonly(
            "post_infinity_type", [](const PyCurve& pyCurve) { return pyCurve.curve.postInfinityType.GetText(); });
    ;

    defineInterfaceClass<IAnimCurve>(m, "AnimCurve", "acquire_interface", "release_interface")
        .def("is_updating_usd", wrapInterfaceFunction(&IAnimCurve::isUpdatingUsd))
        .def("get_event_stream", wrapInterfaceFunction(&IAnimCurve::getEventStream))
        .def("get_curve_prims",
             [](IAnimCurve* iAnimCurve, const char* primPath)
             {
                 std::vector<std::string> primPaths;
                 for (auto& prim : iAnimCurve->getCurvePrims(SdfPath(primPath)))
                     primPaths.push_back(prim.GetString());

                 return primPaths;
             })
        .def("get_curves",
             [](IAnimCurve* iAnimCurve, const char* primPath)
             {
                 std::map<std::string, PyCurve> curves;
                 for (auto& curve : iAnimCurve->getCurves(SdfPath(primPath)))
                 {
                     auto curvePath = curve.second->animData.GetPath().AppendProperty(curve.first);
                     curves.insert(std::make_pair(curve.first.GetText(), PyCurve{ *curve.second, curvePath }));
                 }

                 return curves;
             })
        .def("pump_keys_overriden_event",
             [](IAnimCurve* iAnimCurve, const std::vector<std::string>& curvePaths)
             {
                 std::vector<SdfPath> curveSdfPaths;
                 for (auto& path : curvePaths)
                 {
                     curveSdfPaths.push_back(SdfPath(path));
                 }
                 iAnimCurve->pumpKeysOverridenEvent(curveSdfPaths);
             })
        .def("is_attr_supported", [](IAnimCurve* iAnimCurve, const char* attrPath)
             { return iAnimCurve->isAttrSupported(SdfPath(attrPath)); })
        .def("evaluate",
             [](IAnimCurve* iAnimCurve, const char* curvePath, double time) -> py::object
             {
                 double value;
                 if (iAnimCurve->evaluate(SdfPath(curvePath), time, value))
                     return py::cast(value);
                 else
                     return py::none();
             })
        .def("get_ticks_per_second", wrapInterfaceFunction(&IAnimCurve::getTicksPerSecond))
        .def("get_curve_nodes",
             [](IAnimCurve* iAnimCurve, const char* prim /*, const char* animData*/)
             {
                 std::vector<std::string> nodes;
                 for (auto& node : iAnimCurve->getCurveNodes(
                          prim ? SdfPath(prim) : SdfPath() /*, animData ? SdfPath(animData) : SdfPath()*/))
                 {
                     nodes.push_back(node.GetString());
                 }

                 return nodes;
             })
        .def("convert_to_attr_precision",
             [](IAnimCurve* iAnimCurve, const char* attrPath, double value) -> py::object
             {
                 SdfPath path(attrPath);
                 if (iAnimCurve->convertToAttrPrecision(path, value))
                 {
                     return py::cast(value);
                 }
                 else
                 {
                     return py::none();
                 }
             })
        .def("simplify_catmull", wrapInterfaceFunction(&IAnimCurve::simplifyCatmull));
}
}
