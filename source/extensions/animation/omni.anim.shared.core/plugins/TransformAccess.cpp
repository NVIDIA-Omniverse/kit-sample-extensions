// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#include "TransformAccess.h"
#include "StageAttributeAccess.h"
#include <pxr/base/gf/matrix4d.h>
#include <algorithm>
#include <cmath>

namespace omni::anim::shared::stage
{
namespace
{
Matrix identity() { return {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1}; }
std::string parent(std::string_view path)
{
    const auto slash = path.find_last_of('/');
    return slash == 0 ? "/" : std::string(path.substr(0, slash));
}
std::optional<Matrix> world(const AttributeAccess& access, std::string_view path, ovstage_ordinal_t ordinal)
{
    if (path == "/") return identity();
    if (auto value = access.readValue<Matrix>(path, "omni:fabric:worldMatrix", {kDLFloat,64,16}, ordinal))
        return value;
    // Scope/untyped prims inherit the nearest ancestor transform. A missing prim
    // must not be reported as a valid identity or silently read through USD.
    if (!access.readValue<ovx_token_t>(path, "usd-prim-type", {kDLUInt,64,1}, ordinal))
        return std::nullopt;
    for (auto ancestor = parent(path); ancestor != "/"; ancestor = parent(ancestor))
        if (auto value = access.readValue<Matrix>(ancestor, "omni:fabric:worldMatrix", {kDLFloat,64,16}, ordinal))
            return value;
    return identity();
}
}
std::optional<Matrix> readTransform(AnimationStage::View view, std::string_view path, bool local)
{
    if (path.empty() || path.front() != '/' || (path.size() > 1 && path.back() == '/'))
        throw std::invalid_argument("Transform path must be absolute");
    AttributeAccess access(view.instance);
    auto result = world(access, path, view.readOrdinal);
    if (!result || !local || path == "/") return result;
    const auto parentWorld = world(access, parent(path), view.readOrdinal);
    if (!parentWorld) return std::nullopt;
    PXR_NS::GfMatrix4d matrix, parentMatrix;
    std::copy(result->begin(), result->end(), matrix.data());
    std::copy(parentWorld->begin(), parentWorld->end(), parentMatrix.data());
    const double determinant = parentMatrix.GetDeterminant();
    if (!std::isfinite(determinant) || std::abs(determinant) < 1e-12)
        throw std::runtime_error("Cannot compute a relative transform with a singular parent");
    matrix = matrix * parentMatrix.GetInverse();
    std::copy(matrix.data(), matrix.data() + 16, result->begin());
    return result;
}
}
