// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

// Preserve nullable strings and array call semantics with Carbonite v2.
#include <carb/settings/ISettings.h>

#include <cstddef>
#include <vector>

namespace ovcompat
{

inline carb::cpp::string_view sv(const char* s)
{
    return s ? carb::cpp::string_view(carb::cpp::unsafe_length, s) : carb::cpp::string_view{};
}

inline const char* getStringBuffer(const carb::settings::ISettings& s, const char* path, size_t* pLen = nullptr)
{
    auto v = s.getStringView(sv(path));
    if (!v)
    {
        if (pLen)
            *pLen = 0;
        return nullptr;
    }
    if (pLen)
        *pLen = v->size();
    return v->c_str();
}

inline const char* getStringBuffer(const carb::settings::ISettings* s, const char* path, size_t* pLen = nullptr)
{
    if (!s)
    {
        if (pLen)
            *pLen = 0;
        return nullptr;
    }
    return getStringBuffer(*s, path, pLen);
}

inline void getStringBufferArray(const carb::settings::ISettings& s, const char* path, const char** out, size_t n)
{
    if (!out || n == 0)
        return;
    for (size_t i = 0; i < n; ++i)
        out[i] = nullptr;
    std::vector<carb::cpp::zstring_view> tmp(n);
    size_t got = s.getStringArray(sv(path), tmp.data(), n);
    if (got > n)
        got = n;
    for (size_t i = 0; i < got; ++i)
        out[i] = tmp[i].c_str();
}

inline void getStringBufferArray(const carb::settings::ISettings* s, const char* path, const char** out, size_t n)
{
    if (s)
        getStringBufferArray(*s, path, out, n);
}

inline void unsubscribeToChangeEvents(const carb::settings::ISettings& s, carb::dictionary::SubscriptionId* id)
{
    s.unsubscribeFromChangeEvents(id);
}

inline void unsubscribeToChangeEvents(const carb::settings::ISettings* s, carb::dictionary::SubscriptionId* id)
{
    if (s)
        unsubscribeToChangeEvents(*s, id);
}

} // namespace ovcompat
