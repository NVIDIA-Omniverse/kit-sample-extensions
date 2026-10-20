// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <chrono>

// #ifdef _WIN32
// #include <filesystem>
// namespace fs = std::filesystem;
// #endif

#ifdef __linux__
#    include <experimental/filesystem>
namespace fs = std::experimental::filesystem;
#endif

#include <iostream>
#include <string>
#include <vector>

// #include "types.h"

using Vec2f = PXR_NS::GfVec2f;
using Vec3f = PXR_NS::GfVec3f;
using Vec4f = PXR_NS::GfVec4f;

using Vec2d = PXR_NS::GfVec2d;
using Vec3d = PXR_NS::GfVec3d;
using Vec4d = PXR_NS::GfVec4d;

using Vec2i = PXR_NS::GfVec2i;
using Vec3i = PXR_NS::GfVec3i;
using Vec4i = PXR_NS::GfVec4i;

using Mat2f = PXR_NS::GfMatrix4f;
using Mat3f = PXR_NS::GfMatrix4f;
using Mat4f = PXR_NS::GfMatrix4f;

using Mat2d = PXR_NS::GfMatrix4d;
using Mat3d = PXR_NS::GfMatrix4d;
using Mat4d = PXR_NS::GfMatrix4d;

using Range2f = PXR_NS::GfRange2f;
using Range3f = PXR_NS::GfRange3f;

using Range2d = PXR_NS::GfRange2d;
using Range3d = PXR_NS::GfRange3d;

class Timer
{
public:
    Timer()
    {
        reset();
    }

    void reset(void)
    {
        m_start = clock_type::now();
        m_running = true;
    }

    void stop(void)
    {
        m_stop = clock_type::now();
        m_running = false;
    }

    template <typename T = float>
    T get_elapsed_s(void) const
    {
        time_point_type const stop = (m_running) ? clock_type::now() : m_stop;
        std::chrono::duration<T, std::nano> const time_diff_ns = stop - m_start;
        return time_diff_ns.count() * T(std::nano::num) / T(std::nano::den);
    }

private:
    using clock_type = std::chrono::steady_clock;
    using time_point_type = clock_type::time_point;

private:
    time_point_type m_start, m_stop;
    bool m_running = false;
};


// I don't use the below function...
// std::vector<fs::path>
// get_file_paths(std::string const &folder, std::string const &prefix = "",
//                std::string const &suffix = ".geojson") {
//   if (!fs::exists(folder))
//     throw std::runtime_error("directory does not exist: '" + folder + "'");

//   std::vector<fs::path> paths;
//   for (auto const &dir_entry : fs::directory_iterator(folder)) {
//     if (!dir_entry.is_regular_file())
//       continue;

//     std::string const stem = dir_entry.path().stem().string(); // changed here
//     std::string const file_name = dir_entry.path().filename().string(); // changed here

//     // check prefix
//     if (file_name.rfind(prefix, 0) == std::string::npos) {
//       continue;
//     }
//     // check suffix
//     if (file_name.find(suffix, file_name.size() - suffix.size()) ==
//         std::string::npos) {
//       continue;
//     }

//     std::cout << "Adding shape file: " << dir_entry.path() << "\n";
//     paths.push_back(dir_entry.path());
//   }

//   return paths;
// }

// // TODO: better place for this than utils?
// template <typename VecType>
// VecType latlong_to_uv(Range2d const &bbox, VecType coords) {
//   auto const length = bbox.GetSize();
//   return VecType{ static_cast<float>((coords[0] - bbox.GetMin()[0]) / length[0]),   // added static casts to float
//                  static_cast<float>((coords[1] - bbox.GetMin()[1]) / length[1])};   // added static casts to float
// }

// template <typename T>
// auto get_sampling_function_from_image(Image<T> const &img, Range2d const &bbox,
//                                       float const scaling_factor = 1.0f) {
//   float norm_factor = 1.0f;
//   // TODO: This is weird, uint8_t usually uses 0-255 to represent 0-1 but we
//   // have elevation data encoded as meters. this should be encapsuled as a
//   // seperate remapping process
//   if constexpr (std::is_same<T, uint8_t>()) {
//     norm_factor = 1.0f / 255.0f;
//   }
//   norm_factor *= scaling_factor;

//   // TODO: not ideal to take a reference here but copying would be expensive.
//   // could work with reference counted pointers but that increases complexity
//   // and introduces additional indirection during sampling
//   auto sampling_func = [&img, bbox, norm_factor](Vec2f const &lat_long) {
//     auto const uv = latlong_to_uv(bbox, lat_long);
//     return static_cast<float>(norm_factor * img.sample(uv[0], uv[1]));
//   };

//   return sampling_func;
// }
