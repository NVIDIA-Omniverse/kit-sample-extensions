// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <carb/BindingsPythonUtils.h>
#include <carb/events/IEvents.h>

#include <omni/curvemanipulator/ICurveManipulator.h>


CARB_BINDINGS("omni.curve.manipulator.python")

DISABLE_PYBIND11_DYNAMIC_CAST(carb::events::IEventStream)

using namespace carb;
using namespace omni::curvemanipulator;

namespace omni
{
namespace curvemanipulator
{
class CurveManipulatorContext;
}
}

namespace
{

struct CurveManipulatorContextPy
{
public:
    CurveManipulatorContextPy(CurveManipulatorContext* _context) : context(_context)
    {
    }

    CurveManipulatorContext* context;
};

PYBIND11_MODULE(_omni_curve_manipulator, m)
{
    m.doc() = "pybind11 omni.curve.manipulator bindings";

    py::enum_<CurvesEventType>(m, "CurvesEventType", R"(
        Curves Event Type.
        )")
        .value("INSERT", CurvesEventType::eInsert)
        .value("BEGIN_ADD", CurvesEventType::eBeginAdd)
        .value("ADDING", CurvesEventType::eAdding)
        .value("END_ADD", CurvesEventType::eEndAdd)
        .value("ADD_MULTIPLE_POINTS", CurvesEventType::eAddMultiplePoints)
        .value("BEGIN_CURVE_EDIT", CurvesEventType::eBeginCurveEdit)
        .value("END_CURVE_EDIT", CurvesEventType::eEndCurveEdit)
        .value("CURVE_EDIT_MODE_CHANGED", CurvesEventType::eCurveEditModeChanged);
    ;

    py::enum_<CurveEditingModeType>(m, "CurveEditingModeType", R"(
        Curves Editing Mode Type.
        )")
        .value("DRAG", CurveEditingModeType::eDrag)
        .value("DRAW", CurveEditingModeType::eDraw);
    ;

    py::class_<CurveManipulatorContextPy>(m, "CurveManipulatorContext");

    defineInterfaceClass<ICurveManipulator>(m, "ICurveManipulator", "acquire_interface", "release_interface")
        .def(
            "create_context",
            [](ICurveManipulator* _this, const char* usdContextName)
            { return CurveManipulatorContextPy(_this->createContext(usdContextName)); },
            py::arg("usdContextName") = "")
        .def("destroy_context", [](ICurveManipulator* _this, CurveManipulatorContextPy& context)
             { _this->destroyContext(context.context); })
        .def("enable_curve_editing_mode",
             [](ICurveManipulator* _this, CurveManipulatorContextPy& context, const std::vector<std::string>& paths,
                CurveEditingModeType mode)
             {
                 std::vector<const char*> cpaths;
                 cpaths.reserve(paths.size());
                 for (const auto& path : paths)
                 {
                     cpaths.push_back(path.c_str());
                 }

                 _this->enableCurveEditingMode(context.context, cpaths.data(), cpaths.size(), mode);
             })
        .def("is_in_curve_editing_mode", [](ICurveManipulator* _this, const CurveManipulatorContextPy& context)
             { return _this->isInCurveEditingMode(context.context); })
        .def("disable_curve_editing_mode", [](ICurveManipulator* _this, CurveManipulatorContextPy& context)
             { _this->disableCurveEditingMode(context.context); })
        .def("get_editing_curve_paths",
             [](const ICurveManipulator* _this, const CurveManipulatorContextPy& context)
             {
                 std::vector<std::string> paths;
                 std::vector<const char*> cpaths;
                 size_t count = _this->getEditingCurvePathsCount(context.context);
                 if (count)
                 {
                     cpaths.resize(count);
                     _this->getEditingCurvePaths(context.context, cpaths.data());

                     paths.reserve(count);
                     for (const char* cpath : cpaths)
                     {
                         paths.emplace_back(cpath);
                     }
                 }

                 return paths;
             })
        .def("get_curves_event_stream", [](ICurveManipulator* _this, CurveManipulatorContextPy& context)
             { return _this->getCurvesEventStream(context.context); })
        .def("get_curve_editing_mode", [](ICurveManipulator* _this, const CurveManipulatorContextPy& context)
             { return _this->getCurveEditingMode(context.context); })
        .def("set_curve_editing_mode",
             [](ICurveManipulator* _this, CurveManipulatorContextPy& context, CurveEditingModeType mode)
             { _this->setCurveEditingMode(context.context, mode); })
        .def("set_adding_curve_to_basis_curves",
             [](ICurveManipulator* _this, CurveManipulatorContextPy& context, bool value)
             { _this->setAddingCurveToBasisCurves(context.context, value); })
        .def("on_raycast",
             [](ICurveManipulator* _this, const CurveManipulatorContextPy& context, const carb::Float3& origin,
                const carb::Float3& dir, bool input, bool end, const char* cameraPath, const carb::Float4& rect,
                const std::vector<double>& viewProjMatrix, const carb::Double3* snapWorldPos)
             {
                 return _this->onRaycast(
                     context.context, origin, dir, input, end, cameraPath, rect, viewProjMatrix.data(), snapWorldPos);
             });
    ;
}
} // namespace
