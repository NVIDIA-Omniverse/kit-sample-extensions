// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#pragma once
#include "AnimationStage.h"
#include <array>
#include <optional>
#include <string_view>
namespace omni::anim::shared::stage
{
using Matrix = std::array<double, 16>;
// Returns world or parent-relative transform. Scene values come only from
// ovstage; USD matrix types are used for arithmetic in the implementation.
std::optional<Matrix> readTransform(AnimationStage::View view, std::string_view path, bool local);
}
