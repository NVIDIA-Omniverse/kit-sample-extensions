// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <pybind11/numpy.h>

#include <cstring>
#include <carb/BindingsPythonUtils.h>
#include <carb/Framework.h>
#include <carb/events/IEvents.h>
#include <carb/profiler/Profile.h>

#include <IMeshRaycast.h>
#include <type_traits>
#include <vector>

CARB_BINDINGS("omni.meshraycast.python")

DISABLE_PYBIND11_DYNAMIC_CAST(carb::events::IEventStream)
DISABLE_PYBIND11_DYNAMIC_CAST(omni::meshraycast::IMeshRaycast);

namespace omni
{
namespace meshraycast
{
struct RaycastContext // ignore definition. Only need it as a pointer
{
};
} // namespace meshraycast
} // namespace omni

namespace
{

struct OverlapVerticesEntryPy
{
    size_t meshIndex;
    std::vector<size_t> vertexIndices;
    std::vector<size_t> faceIndices;
};

struct CurveTessellateResultEntryPy
{
    std::vector<usdrt::GfVec3f> positions;
    std::vector<usdrt::GfVec3f> tangents;
};

// (N, 3) float32 copy of a vector of usdrt::GfVec3f. Returned instead of the vector itself: converting
// omni::math::linalg::vec3<float> to Python needs a module that registers that C++ type (classic usdrt's _Gf), and
// Kit 111's OVStage usdrt provider implements usdrt.Gf over pxr.Gf without registering it ("Unregistered type").
static py::array_t<float> toFloat3Array(const std::vector<usdrt::GfVec3f>& values)
{
    static_assert(sizeof(usdrt::GfVec3f) == 3 * sizeof(float), "GfVec3f is three packed floats");
    py::array_t<float> result({ static_cast<py::ssize_t>(values.size()), static_cast<py::ssize_t>(3) });
    if (!values.empty())
        std::memcpy(result.mutable_data(), values.data(), values.size() * sizeof(usdrt::GfVec3f));
    return result;
}

PYBIND11_MODULE(_meshraycast, m)
{
    using namespace omni::meshraycast;
    m.doc() = "pybind11 omni.meshraycast bindings";

    py::enum_<RaycastEventType>(m, "RaycastEventType", R"(
        Raycast Event Type.
        )")
        .value("BVH_REBUILT", RaycastEventType::eBvhRebuilt);

    py::enum_<BvhRefreshRate>(m, "BvhRefreshRate", R"(
        BVH Refresh Interval.
        )")
        .value("SLOW", BvhRefreshRate::eSlow)
        .value("FAST", BvhRefreshRate::eFast);

    py::class_<HitResult>(m, "HitResult")
        .def_readonly("meshIndex", &HitResult::meshIndex) // should be snake_case, keep for backward compatibility
        .def_readonly("mesh_index", &HitResult::meshIndex)
        .def_readonly("position", &HitResult::position)
        .def_readonly("normal", &HitResult::normal)
        .def_readonly("face_index", &HitResult::faceIndex);
    ;

    py::class_<RaycastContext>(m, "RaycastContext");

    py::class_<BoundResult>(m, "BoundResult")
        .def_readonly("meshIndex", &BoundResult::meshIndex)
        .def_readonly("distance", &BoundResult::distance);

    py::class_<OverlapVerticesEntryPy>(m, "OverlapVerticesEntry")
        .def_readonly("meshIndex", &OverlapVerticesEntryPy::meshIndex)
        .def_readonly("vertexIndices", &OverlapVerticesEntryPy::vertexIndices)
        .def_readonly("faceIndices", &OverlapVerticesEntryPy::faceIndices);

    py::class_<CurveTessellateResultEntryPy>(m, "CurveTessellateResult")
        .def_property_readonly("positions",
                               [](const CurveTessellateResultEntryPy& entry) { return toFloat3Array(entry.positions); })
        .def_property_readonly("tangents",
                               [](const CurveTessellateResultEntryPy& entry) { return toFloat3Array(entry.tangents); });

    carb::defineInterfaceClass<IMeshRaycast>(
        m, "IMeshRaycast", "acquire_mesh_raycast_interface", "release_mesh_raycast_interface")
        .def("create_context", &IMeshRaycast::createContext, py::return_value_policy::reference)
        .def("destroy_context", &IMeshRaycast::destroyContext)
        .def("set_bvh_refresh_rate", &IMeshRaycast::setBvhRefreshRate)
        .def("get_bvh_refresh_rate", &IMeshRaycast::getBvhRefreshRate)
        .def(
            "set_hit_filter_fn",
            [](IMeshRaycast* _this, std::function<bool(const char* meshPath)> fn, RaycastContext* context) {
                _this->setHitFilterFn(carb::wrapPythonCallback(std::move(fn)));
            },
            py::arg("fn"), py::arg("context") = py::cast<py::none>(Py_None))
        .def(
            "set_allowed_mesh_paths",
            [](IMeshRaycast* _this, const std::vector<std::string>& paths, RaycastContext* context) {
                std::vector<const char*> pathCstrs;

                pathCstrs.reserve(paths.size());
                for (const auto& path : paths)
                {
                    pathCstrs.push_back(path.c_str());
                }

                _this->setAllowedMeshPaths(pathCstrs.data(), pathCstrs.size(), context);
            },
            py::arg("paths"), py::arg("context") = py::cast<py::none>(Py_None))
        .def(
            "set_disallowed_mesh_paths",
            [](IMeshRaycast* _this, const std::vector<std::string>& paths, bool includeDescendents,
               RaycastContext* context) {
                std::vector<const char*> pathCstrs;

                pathCstrs.reserve(paths.size());
                for (const auto& path : paths)
                {
                    pathCstrs.push_back(path.c_str());
                }

                _this->setDisallowedMeshPaths(pathCstrs.data(), pathCstrs.size(), includeDescendents, context);
            },
            py::arg("paths"), py::arg("include_descendents"), py::arg("context") = py::cast<py::none>(Py_None))
        .def("closestRaycast", &IMeshRaycast::closestRaycast, py::arg("origin"), py::arg("dir"), py::arg("dist"),
             py::arg("context") = py::cast<py::none>(Py_None))
        .def("closestRaycastBound", &IMeshRaycast::closestRaycastBound, py::arg("origin"), py::arg("dir"),
             py::arg("dist"), py::arg("context") = py::cast<py::none>(Py_None))
        .def("closestRaycastMesh", &IMeshRaycast::closestRaycastMesh)
        .def(
            "spherecast",
            [](IMeshRaycast* _this, const carb::Float3& origin, const carb::Float3& dir, float radius, float dist,
               const RaycastContext* context) {
                OverlapResult result = _this->spherecast(origin, dir, radius, dist, context);
                using DataType = std::remove_pointer<decltype(result.meshIndices)>::type;
                std::vector<DataType> overlapResult;
                if (result.size)
                {
                    overlapResult.resize(result.size);
                    memcpy(overlapResult.data(), result.meshIndices, sizeof(DataType) * result.size);
                    _this->freeOverlapResult(result);
                }
                return overlapResult;
            },
            py::arg("origin"), py::arg("dir"), py::arg("radius"), py::arg("dist"),
            py::arg("context") = py::cast<py::none>(Py_None))
        .def(
            "overlap_vertices",
            [](IMeshRaycast* _this, const carb::Float3& origin, float radius, const RaycastContext* context) {
                CARB_PROFILE_FUNCTION(1);

                OverlapVerticesResult result = _this->overlapVertices(origin, radius, context);
                std::vector<OverlapVerticesEntryPy> pyResult;

                pyResult.resize(result.meshSize);
                size_t vertexOffset = 0;
                size_t faceOffset = 0;
                for (size_t i = 0; i < result.meshSize; i++)
                {
                    auto& entry = pyResult[i];
                    entry.meshIndex = result.meshIndices[i];

                    size_t vertexCount = result.vertexIndicesSize[i];
                    entry.vertexIndices.resize(vertexCount);
                    memcpy(entry.vertexIndices.data(), &result.vertexIndices[vertexOffset], sizeof(size_t) * vertexCount);
                    vertexOffset += vertexCount;

                    size_t faceCount = result.faceIndicesSize[i];
                    entry.faceIndices.resize(faceCount);
                    memcpy(entry.faceIndices.data(), &result.faceIndices[faceOffset], sizeof(size_t) * faceCount);
                    faceOffset += faceCount;
                }
                _this->freeOverlapVerticesResult(result);

                return pyResult;
            },
            py::arg("origin"), py::arg("radius"), py::arg("context") = py::cast<py::none>(Py_None))
        .def("getFloodPoints",
             [](IMeshRaycast* _this, const std::string& meshPath, const float density, const bool forceCooking) {
                 std::vector<carb::Float3> positions;
                 std::vector<carb::Float3> normals;

                 _this->getFloodPoints(meshPath, density, forceCooking, positions, normals);

                 py::dict results;
                 results["positions"] = positions;
                 results["normals"] = normals;

                 return results;
             })
        .def("get_mesh_path_from_index", &IMeshRaycast::getMeshPathFromIndex)
        .def("get_mesh_paths",
             [](IMeshRaycast* _this) {
                 std::vector<const char*> pathCstrs;

                 pathCstrs.resize(_this->getMeshPathCount());
                 _this->getMeshPaths(pathCstrs.data(), pathCstrs.size());

                 return std::vector<std::string>(pathCstrs.begin(), pathCstrs.end());
             })
        .def("get_mesh_raycast_event_stream", &IMeshRaycast::getMeshRaycastEventStream)
        .def("get_vertex_local_positions",
             [](IMeshRaycast* _this, const std::string& meshPath, const std::vector<size_t>& vertIdxs) {
                 CARB_PROFILE_FUNCTION(1);

                 std::vector<carb::Float3> positions;
                 _this->getVertexLocalPositions(meshPath.c_str(), vertIdxs, positions);
                 return positions;
             })
        .def("tessellate_curve",
             [](IMeshRaycast* _this, const std::string& path, size_t stepsPerSegment, bool fillTangents) {
                 CARB_PROFILE_FUNCTION(1);

                 CurveTessellateResult result = _this->tessellateCurve(path.c_str(), stepsPerSegment, fillTangents);

                 std::vector<CurveTessellateResultEntryPy> pyResult;
                 pyResult.reserve(result.curveCount);

                 size_t positionOffset = 0;
                 size_t tangentOffset = 0;
                 for (size_t i = 0; i < result.curveCount; i++)
                 {
                     size_t positionCount = result.positionCounts[i];
                     size_t tangentCount = result.tangentCounts[i];

                     CurveTessellateResultEntryPy entry;
                     entry.positions.resize(positionCount);
                     if (positionCount)
                     {
                         memcpy(entry.positions.data(), result.positions + positionOffset,
                                sizeof(usdrt::GfVec3f) * positionCount);
                     }
                     entry.tangents.resize(tangentCount);
                     if (tangentCount)
                     {
                         memcpy(entry.tangents.data(), result.tangents + tangentOffset,
                                sizeof(usdrt::GfVec3f) * tangentCount);
                     }

                     pyResult.push_back(std::move(entry));

                     positionOffset += positionCount;
                     tangentOffset += tangentCount;
                 }

                 _this->freeCurveTessellateResult(result);

                 return pyResult;
             })
        .def("sample_curve_segment_at_t",
             [](IMeshRaycast* _this, const std::string& path, size_t curveIndex, size_t segmentIndex, float t) {
                 CARB_PROFILE_FUNCTION(1);

                 // [position, tangent] as (x, y, z) tuples, or [] when sampling fails. Plain tuples, not
                 // usdrt::GfVec3f: see toFloat3Array (Kit 111's usdrt.Gf does not register the C++ type).
                 usdrt::GfVec3f position, tangent;
                 py::list ret;
                 if (_this->sampleCurveSegmentAtT(path.c_str(), curveIndex, segmentIndex, t, &position, &tangent))
                 {
                     ret.append(py::make_tuple(position[0], position[1], position[2]));
                     ret.append(py::make_tuple(tangent[0], tangent[1], tangent[2]));
                 }
                 return ret;
             });
}
} // namespace
