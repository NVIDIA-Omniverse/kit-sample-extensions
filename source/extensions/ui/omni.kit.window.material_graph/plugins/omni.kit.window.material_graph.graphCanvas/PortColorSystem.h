// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <string>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// High-level USD value-type bucket used to pick a base hue and layout rules.
enum class TypeCategory
{
    FLOAT_SCALAR,
    FLOAT_VECTOR,
    COLOR,
    INTEGER,
    BOOLEAN,
    STRING,
    ASSET,
    MATRIX,
    VECTOR_SPATIAL,
    TEXTURE_COORD,
    QUATERNION,
    FRAME,
    OTHER
};

// Returns the default hue in degrees (0–360) for a category before offsets and modifiers.
inline float baseHueForCategory(TypeCategory cat)
{
    switch (cat)
    {
        case TypeCategory::FLOAT_SCALAR:
            return 210.0f;
        case TypeCategory::FLOAT_VECTOR:
            return 195.0f;
        case TypeCategory::COLOR:
            return 175.0f; // Teal-cyan (shifted from green to free green for structural UI)
        case TypeCategory::INTEGER:
            return 45.0f;
        case TypeCategory::BOOLEAN:
            return 0.0f;
        case TypeCategory::STRING:
            return 300.0f;
        case TypeCategory::ASSET:
            return 30.0f;
        case TypeCategory::MATRIX:
            return 260.0f;
        case TypeCategory::VECTOR_SPATIAL:
            return 180.0f;
        case TypeCategory::TEXTURE_COORD:
            return 170.0f;
        case TypeCategory::QUATERNION:
            return 280.0f;
        case TypeCategory::FRAME:
            return 320.0f;
        case TypeCategory::OTHER:
            return 0.0f;
    }
    return 0.0f;
}

// Returns a lowercased copy of the string for case-insensitive type parsing.
inline std::string toLowerStr(const std::string& s)
{
    std::string r = s;
    for (auto& c : r)
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return r;
}

// True if s begins with the given ASCII prefix (prefix must be null-terminated).
inline bool startsWith(const std::string& s, const char* prefix)
{
    for (int i = 0; prefix[i]; ++i)
    {
        if (i >= static_cast<int>(s.size()) || s[i] != prefix[i])
            return false;
    }
    return true;
}

// True if sub appears as a substring anywhere in s.
inline bool containsStr(const std::string& s, const char* sub)
{
    return s.find(sub) != std::string::npos;
}

// Classifies a lowercased USD type name into a TypeCategory using prefix and keyword rules.
inline TypeCategory parseTypeCategory(const std::string& lower)
{
    if (startsWith(lower, "color"))
        return TypeCategory::COLOR;
    if (startsWith(lower, "normal"))
        return TypeCategory::VECTOR_SPATIAL;
    if (startsWith(lower, "vector"))
        return TypeCategory::VECTOR_SPATIAL;
    if (startsWith(lower, "point"))
        return TypeCategory::VECTOR_SPATIAL;
    if (startsWith(lower, "texcoord"))
        return TypeCategory::TEXTURE_COORD;
    if (startsWith(lower, "quat"))
        return TypeCategory::QUATERNION;
    if (startsWith(lower, "matrix"))
        return TypeCategory::MATRIX;
    if (startsWith(lower, "frame"))
        return TypeCategory::FRAME;
    if (lower == "bool")
        return TypeCategory::BOOLEAN;
    if (lower == "asset")
        return TypeCategory::ASSET;
    if (lower == "string" || lower == "token")
        return TypeCategory::STRING;
    if (startsWith(lower, "int") || startsWith(lower, "uint") || lower == "int64")
        return TypeCategory::INTEGER;
    if (startsWith(lower, "float") || startsWith(lower, "double") || startsWith(lower, "half"))
    {
        for (char c : lower)
            if (c >= '2' && c <= '4')
                return TypeCategory::FLOAT_VECTOR;
        return TypeCategory::FLOAT_SCALAR;
    }
    return TypeCategory::OTHER;
}

// Reads a 2–4 vector dimension before an optional precision suffix and array marker.
inline int extractDimension(const std::string& lower)
{
    size_t end = lower.size();
    if (end >= 2 && lower.compare(end - 2, 2, "[]") == 0)
        end -= 2;
    if (end >= 5 && lower.compare(end - 5, 5, "array") == 0)
        end -= 5;
    if (end > 0 && (lower[end - 1] == 'f' || lower[end - 1] == 'd' || lower[end - 1] == 'h'))
        --end;

    if (end > 0 && lower[end - 1] >= '2' && lower[end - 1] <= '4' &&
        (end == 1 || !std::isdigit(static_cast<unsigned char>(lower[end - 2]))))
        return lower[end - 1] - '0';
    return 1;
}

// True if the type name denotes an array (brackets or the word "array").
inline bool detectArray(const std::string& lower)
{
    return containsStr(lower, "[]") || containsStr(lower, "array");
}

// Floating-point storage class inferred from the type name string.
enum class Precision
{
    HALF,
    FLOAT,
    DOUBLE
};

// Infers half, double, or float precision from the lowercased type name.
inline Precision detectPrecision(const std::string& lower)
{
    if (startsWith(lower, "half") || containsStr(lower, "half"))
        return Precision::HALF;
    if (startsWith(lower, "double") || containsStr(lower, "double"))
        return Precision::DOUBLE;
    return Precision::FLOAT;
}

// Converts HSV to packed ABGR with alpha in the high byte (default opaque).
inline uint32_t hsvToAbgr(float h, float s, float v, uint8_t alpha = 0xFF)
{
    h = std::fmod(h, 360.0f);
    if (h < 0)
        h += 360.0f;
    float c = v * s;
    float x = c * (1.0f - std::abs(std::fmod(h / 60.0f, 2.0f) - 1.0f));
    float m = v - c;
    float r1 = 0, g1 = 0, b1 = 0;
    if (h < 60)
    {
        r1 = c;
        g1 = x;
    }
    else if (h < 120)
    {
        r1 = x;
        g1 = c;
    }
    else if (h < 180)
    {
        g1 = c;
        b1 = x;
    }
    else if (h < 240)
    {
        g1 = x;
        b1 = c;
    }
    else if (h < 300)
    {
        r1 = x;
        b1 = c;
    }
    else
    {
        r1 = c;
        b1 = x;
    }
    uint8_t ri = static_cast<uint8_t>((r1 + m) * 255.0f);
    uint8_t gi = static_cast<uint8_t>((g1 + m) * 255.0f);
    uint8_t bi = static_cast<uint8_t>((b1 + m) * 255.0f);
    return (static_cast<uint32_t>(alpha) << 24) | (static_cast<uint32_t>(bi) << 16) | (static_cast<uint32_t>(gi) << 8) |
           static_cast<uint32_t>(ri);
}

// Small deterministic FNV-style hash of the string for per-type hue jitter.
inline uint32_t simpleHash(const std::string& s)
{
    uint32_t h = 2166136261u;
    for (char c : s)
    {
        h ^= static_cast<uint32_t>(c);
        h *= 16777619u;
    }
    return h;
}

// Computes the display ABGR color for a USD value type name using category, dimension, precision, and array rules.
inline uint32_t GetPortColorABGR(const std::string& typeName)
{
    std::string lower = toLowerStr(typeName);

    TypeCategory cat = parseTypeCategory(lower);
    int dim = extractDimension(lower);
    bool isArray = detectArray(lower);
    Precision prec = detectPrecision(lower);

    float hue = baseHueForCategory(cat);

    // Hash offset for collision avoidance (±8 degrees)
    float hashOffset = (static_cast<float>(simpleHash(lower) % 1600) / 100.0f) - 8.0f;
    hue += hashOffset;

    // Base saturation and value
    float sat = 0.55f;
    float val = 0.72f;

    // Dimension modifier: higher dim → brighter
    if (dim >= 2)
        val += 0.03f * static_cast<float>(dim - 1);

    // Precision modifier
    if (prec == Precision::HALF)
        sat -= 0.06f;
    if (prec == Precision::DOUBLE)
        sat += 0.05f;

    // Array modifier: slightly darker
    if (isArray)
        val -= 0.08f;

    // OTHER category → neutral gray
    if (cat == TypeCategory::OTHER)
    {
        sat = 0.0f;
        val = 0.55f;
    }

    // Clamp
    sat = std::max(0.0f, std::min(0.65f, sat));
    val = std::max(0.55f, std::min(0.85f, val));

    return hsvToAbgr(hue, sat, val);
}

} // namespace materialGraph
} // namespace kit
} // namespace omni
