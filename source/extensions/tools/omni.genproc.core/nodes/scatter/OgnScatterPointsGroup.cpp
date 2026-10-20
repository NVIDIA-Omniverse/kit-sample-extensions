// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.


#include "PhysXUtils.h"
#include "Scatter.h"
#include "Triangulate.h"
#include "UsdPCH.h"
#include "Utils.h"

#include <omni/geometry/Curves.h>
#include <omni/graph/core/BundlePrims.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/ramp/IRamp.h>
#include <physx/include/cooking/PxCooking.h>
#include <physx/include/geometry/PxBVH.h>
#include <physx/include/geometry/PxBoxGeometry.h>
#include <physx/include/geometry/PxGeometryQuery.h>

#include <OgnScatterPointsGroupDatabase.h>
#include <algorithm>
#include <numeric>
#include <unordered_map>
#include <vector>

using namespace omni::genproc;
using namespace omni::geometry::curves;

using omni::math::linalg::safeCastToOmni;
using omni::math::linalg::vec3f;

static omni::ramp::IRamp* s_iRamp = nullptr;

static inline uint64_t deterministic_string_hash(std::string const& s)
{
    constexpr int p = 257;
    constexpr int m = 1000000009;
    uint64_t hash_value = 0;
    uint64_t p_pow = 1;
    for (char c : s)
    {
        hash_value = (hash_value + (c - 'a' + 1) * p_pow) % m;
        p_pow = (p_pow * p) % m;
    }
    return hash_value;
}

static inline void simple_shuffle(uint32_t* permBegin, uint32_t* permEnd, std::mt19937_64& random)
{
    uint32_t permSize = (uint32_t)std::distance(permBegin, permEnd);
    std::uniform_int_distribution<uint32_t> dist;
    for (uint32_t i = permSize - 1; i > 0; --i)
    {
        std::uniform_int_distribution<uint32_t>::param_type range{ 0, i };
        std::swap(permBegin[i], permBegin[dist(random, range)]);
    }
}

static inline float nextRandomFloat(std::mt19937_64& r)
{
    // This is dividing by 2 to the 64, for the range to be in [0,1].
    return r() * (1.0f / 18446744073709551616.0f);
}

static inline void uniformBarycentric(std::mt19937_64& random, float& u, float& v)
{
    u = nextRandomFloat(random);
    v = nextRandomFloat(random);
    if (u + v > 1.f)
    {
        u = 1.f - u;
        v = 1.f - v;
    }
}

struct PerlinNoise
{
    static constexpr uint32_t size = 256;
    static constexpr unsigned mask = size - 1;
    uint32_t permutations[size * 2];

    PerlinNoise(std::mt19937_64& random)
    {
        std::iota(permutations, permutations + size, 0);
        simple_shuffle(permutations, permutations + size, random);
        memcpy(permutations + size, permutations, sizeof(uint32_t) * size);
    }

    static inline float quintic(float t)
    {
        return t * t * t * (t * (t * 6 - 15) + 10);
    }

    inline uint32_t hash(const int x, const int y, const int z) const
    {
        return permutations[permutations[permutations[x] + y] + z];
    }

    inline float gradientDotV(const uint32_t perm, const float x, const float y, const float z) const
    {
        constexpr uint32_t dotsCount = 16;
        const float dots[dotsCount] = {
            x + y, //(1, 1, 0)
            -x + y, //(-1, 1, 0)
            x - y, // (1, -1, 0)
            -x - y, // (-1, -1, 0)
            x + z, // (1, 0, 1)
            -x + z, // (-1, 0, 1)
            x - z, // (1, 0, -1)
            -x - z, // (-1, 0, -1)
            y + z, // (0, 1, 1)
            -y + z, // (0, -1, 1)
            y - z, // (0, 1, -1)
            -y - z, // (0, -1, -1)
            x + y, // (1, 1, 0)
            -x + y, // (-1, 1, 0)
            -y + z, // (0, -1, 1)
            -y - z, // (0, -1, -1)
        };
        return dots[perm & (dotsCount - 1)];
    }

    float evaluate(const vec3f& p) const
    {
        int xfloor = (int)std::floor(p[0]);
        int yfloor = (int)std::floor(p[1]);
        int zfloor = (int)std::floor(p[2]);

        int xi0 = xfloor & mask;
        int yi0 = yfloor & mask;
        int zi0 = zfloor & mask;

        int xi1 = (xi0 + 1) & mask;
        int yi1 = (yi0 + 1) & mask;
        int zi1 = (zi0 + 1) & mask;

        float tx = p[0] - xfloor;
        float ty = p[1] - yfloor;
        float tz = p[2] - zfloor;

        float u = quintic(tx);
        float v = quintic(ty);
        float w = quintic(tz);

        // generate vectors going from the grid points to p
        float x0 = tx, x1 = tx - 1;
        float y0 = ty, y1 = ty - 1;
        float z0 = tz, z1 = tz - 1;

        float a = gradientDotV(hash(xi0, yi0, zi0), x0, y0, z0);
        float b = gradientDotV(hash(xi1, yi0, zi0), x1, y0, z0);
        float c = gradientDotV(hash(xi0, yi1, zi0), x0, y1, z0);
        float d = gradientDotV(hash(xi1, yi1, zi0), x1, y1, z0);
        float e = gradientDotV(hash(xi0, yi0, zi1), x0, y0, z1);
        float f = gradientDotV(hash(xi1, yi0, zi1), x1, y0, z1);
        float g = gradientDotV(hash(xi0, yi1, zi1), x0, y1, z1);
        float h = gradientDotV(hash(xi1, yi1, zi1), x1, y1, z1);

        float k0 = a;
        float k1 = (b - a);
        float k2 = (c - a);
        float k3 = (e - a);
        float k4 = (a + d - b - c);
        float k5 = (a + f - b - e);
        float k6 = (a + g - c - e);
        float k7 = (b + c + e + h - a - d - f - g);

        return k0 + k1 * u + k2 * v + k3 * w + k4 * u * v + k5 * u * w + k6 * v * w + k7 * u * v * w;
    }
};

class OgnScatterPointsGroup
{
public:
    enum class ScatterMethod : int
    {
        eSurface,
        eVolume,
        eBoth
    };

    enum class ZoneSign : int
    {
        eAdditive,
        eSubtractive
    };

    enum class SourceType : int
    {
        eCurve,
        eVolume
    };

    enum class SamplingChannel : int32_t
    {
        eR,
        eG,
        eB,
        eA,
    };

    struct InputChangeRecord
    {
        bool paramChanged = false;
        bool rampChanged = false;
        bool basesChanged = false;
        bool cameraChanged = false;
        bool curvesChanged = false;
        bool texturesChanged = false;
        bool textureFiltersChanged = false;
        bool groupsChanged = false;
        bool volumesChanged = false;

        bool hasAnyChange() const
        {
            return paramChanged || rampChanged || basesChanged || cameraChanged || curvesChanged || texturesChanged ||
                   textureFiltersChanged || groupsChanged || volumesChanged;
        }
    };

    struct PrototypeSettings
    {
        vec3f rotation = vec3f(0.f);
        vec3f rotationRandom = vec3f(0.f);
        vec3f scale = vec3f(1.f);
        float scaleRandom = 0.f;
        vec3f offset = vec3f(.0);
        vec3f offsetRandom = vec3f(0.0);
        int noiseModulation = 0;
        float noiseExponential = 1.f;
    };

    struct GroupSettings
    {
        int desiredPoints = 100;
        int method = 0;
        uint64_t randomSeed = 0;
        int pruneCollision = 0;
        PrototypeSettings protoSettings;
        std::vector<float> protoPercents;
        std::unordered_map<int, PrototypeSettings> settingsOverrides;
    };

    struct ScatterGroup
    {
        std::string name;
        int visible = 1;
        std::vector<int> objectIndices;
        GroupSettings settings;
    };

    struct Ramp
    {
        size_t keysCount = 0;
        const float* positions = nullptr;
        const float* values = nullptr;
        const int* interpolations = nullptr;
    };

    struct TextureInfo
    {
        uint32_t width;
        uint32_t height;
        uint8_t bitDepth;
        uint8_t componentCount;
        const uint8_t* data;

        TextureInfo(uint32_t _width, uint32_t _height, uint8_t _bitDepth, uint8_t _componentCount, const uint8_t* _data)
            : width(_width), height(_height), bitDepth(_bitDepth), componentCount(_componentCount), data(_data)
        {
        }
    };

    using TextureInfoPtr = std::shared_ptr<TextureInfo>;

    struct TextureFilter
    {
        int32_t baseIndex = -1;
        bool additive = true;
        int32_t textureIndex = -1;
        SamplingChannel channel = SamplingChannel::eR;
        std::unordered_set<int32_t> objectIndices;
    };

    struct BaseMeshes
    {
        std::vector<size_t> meshIndices;
        std::vector<vec3f> points;
        std::vector<int> triIndices;
        std::vector<vec3f> normals;
        std::vector<vec2f> texcoords;
        std::vector<double> triangleAreaSums;
        std::vector<float> scatterWeights;
        std::vector<int> objectIndices;
        UniquePhysXPtr<physx::PxTriangleMesh> mesh;
        physx::PxTriangleMeshGeometry geometry;
        bool geometryDirty = false;
        bool hasWeights = false;
        bool hasObjectIndices = false;
        float elevationLow = std::numeric_limits<float>::max();
        float elevationHigh = std::numeric_limits<float>::min();
        Ramp weightsRamp;
        Ramp objectIndicesRamp;
        std::vector<TextureInfoPtr> textures;
        std::unordered_map<int32_t, std::vector<TextureFilter>> textureFilters; // map from base index -> a vector of
                                                                                // filters on that base. If index is -1
                                                                                // it applies to all bases
    };

    struct ScatterSource
    {
        ZoneSign zoneSign;
        SourceType sourceType;
        std::vector<int> objectIndices;
        std::vector<vec3f> points;
        // Control points of curve source for intersection test
        std::vector<vec3f> controlPoints;
        std::vector<int> triIndices;
        // Volume source has normals and texcoords
        std::vector<vec3f> normals;
        std::vector<vec2f> texcoords;
        std::vector<double> triangleAreaSums;
        physx::PxTriangleMeshGeometry geometry;
        // Filtered triangles indices used to accelerate region check
        std::vector<int> filteredTris;
        std::vector<float> pathKnots;
        // Curve path width ramp data
        std::vector<float> pathWidthRampPositions;
        std::vector<float> pathWidthRampValues;
        std::vector<int> pathWidthRampInterpolations;
        double boundVolume;
        float maxBoundArea;
        int cachedPrimIndex;
        float curvePathWidth;
        bool curvePathRegion;
        bool geometryDirty;
    };

    struct Prototype
    {
        pxr::SdfPath path;
        vec3f boundMin;
        vec3f boundMax;
    };

    struct PointSample
    {
        vec3f point;
        vec3f rotation;
        vec3f scale;
        vec3f offset;
        float u;
        float v;
        int vindex;
    };

    struct OverlapData : public physx::PxBVH::OverlapCallback
    {
        OverlapData() : m_hitsCount(0)
        {
        }

        bool reportHit(physx::PxU32 boundsIndex)
        {
            m_hitsCount++;
            return true;
        }

        uint32_t m_hitsCount;
    };

    using ScatterGroups = std::unordered_map<std::string, ScatterGroup>;
    using ScatterSources = std::vector<ScatterSource>;
    using PhysXMeshes = std::vector<UniquePhysXPtr<physx::PxTriangleMesh>>;
    using PhysXGeometries = std::vector<physx::PxTriangleMeshGeometry>;
    using Prototypes = std::vector<Prototype>;

    static void getPrototypeSettings(OgnScatterPointsGroupDatabase& db,
                                     ConstBundlePrim* prim,
                                     PrototypeSettings& settings,
                                     PrototypeSettings* defaultSettings = nullptr)
    {
        BundleAttrib const* rotationAttr = prim->getConstAttr(db.tokens.rotation);
        if (rotationAttr)
        {
            settings.rotation = *rotationAttr->getData<vec3f>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.rotation = defaultSettings->rotation;
        }
        BundleAttrib const* rotationRandomAttr = prim->getConstAttr(db.tokens.rotationRandom);
        if (rotationRandomAttr)
        {
            settings.rotationRandom = *rotationRandomAttr->getData<vec3f>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.rotationRandom = defaultSettings->rotationRandom;
        }
        BundleAttrib const* scaleAttr = prim->getConstAttr(db.tokens.scale);
        if (scaleAttr)
        {
            settings.scale = *scaleAttr->getData<vec3f>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.scale = defaultSettings->scale;
        }
        BundleAttrib const* scaleRandomAttr = prim->getConstAttr(db.tokens.scaleRandom);
        if (scaleRandomAttr)
        {
            settings.scaleRandom = *scaleRandomAttr->getData<float>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.scaleRandom = defaultSettings->scaleRandom;
        }
        BundleAttrib const* offsetAttr = prim->getConstAttr(db.tokens.offset);
        if (offsetAttr)
        {
            settings.offset = *offsetAttr->getData<vec3f>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.offset = defaultSettings->offset;
        }
        BundleAttrib const* offsetRandomAttr = prim->getConstAttr(db.tokens.offsetRandom);
        if (offsetRandomAttr)
        {
            settings.offsetRandom = *offsetRandomAttr->getData<vec3f>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.offsetRandom = defaultSettings->offsetRandom;
        }
        BundleAttrib const* noiseModulationAttr = prim->getConstAttr(db.tokens.noiseModulation);
        if (noiseModulationAttr)
        {
            settings.noiseModulation = *noiseModulationAttr->getData<int>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.noiseModulation = defaultSettings->noiseModulation;
        }
        BundleAttrib const* noiseExponentialAttr = prim->getConstAttr(db.tokens.noiseExponential);
        if (noiseExponentialAttr)
        {
            settings.noiseExponential = *noiseExponentialAttr->getData<float>();
        }
        else if (defaultSettings != nullptr)
        {
            settings.noiseExponential = defaultSettings->noiseExponential;
        }
    }

    static ScatterGroups getScatterGroups(OgnScatterPointsGroupDatabase& db)
    {
        const GraphContextObj& context = db.abi_context();

        ScatterGroups groups;
        ConstBundlePrims groupPrims(context, db.inputs.groups().abi_bundleHandle());
        const size_t groupPrimsCount = groupPrims.getPrimCount();

        std::vector<size_t> overridePrimIndices;
        overridePrimIndices.reserve(groupPrimsCount);
        for (size_t primIndex = 0; primIndex < groupPrimsCount; ++primIndex)
        {
            ConstBundlePrim* groupPrim = groupPrims.getConstPrim(primIndex);
            if (!groupPrim)
            {
                continue;
            }

            BundleAttrib const* settingsOverrideAttr = groupPrim->getConstAttr(db.tokens.settingsOverride);
            if (settingsOverrideAttr && *settingsOverrideAttr->getData<int>() != 0)
            {
                overridePrimIndices.push_back(primIndex);
                continue;
            }

            ScatterGroup group;
            pxr::SdfPath primPath{ groupPrim->path().getText() };
            group.name = primPath.GetName();

            BundleAttrib const* visibleAttr = groupPrim->getConstAttr(db.tokens.visible);
            if (visibleAttr)
            {
                group.visible = *visibleAttr->getData<int>();
            }

            BundleAttrib const* objectIndicesAttr = groupPrim->getConstAttr(db.tokens.objectIndices);
            if (objectIndicesAttr)
            {
                const size_t attrSize = objectIndicesAttr->size();
                group.objectIndices.resize(attrSize);
                memcpy(group.objectIndices.data(), objectIndicesAttr->getData<int>(), sizeof(int) * attrSize);
            }
            const size_t prototypesCount = group.objectIndices.size();

            GroupSettings& groupSettings = group.settings;
            BundleAttrib const* desiredPointsAttr = groupPrim->getConstAttr(db.tokens.desiredPoints);
            if (desiredPointsAttr)
            {
                groupSettings.desiredPoints = std::max(0, *desiredPointsAttr->getData<int>());
            }
            BundleAttrib const* protoPercentsAttr = groupPrim->getConstAttr(db.tokens.prototypePercents);
            if (protoPercentsAttr)
            {
                const size_t attrSize = protoPercentsAttr->size();
                CARB_ASSERT((attrSize == 0 || attrSize == prototypesCount),
                            "prototype percents in group mismatch with the quantity of the prototypes");
                groupSettings.protoPercents.resize(attrSize);
                memcpy(groupSettings.protoPercents.data(), protoPercentsAttr->getData<float>(), sizeof(float) * attrSize);
            }
            BundleAttrib const* scatterMethodAttr = groupPrim->getConstAttr(db.tokens.scatterMethod);
            if (scatterMethodAttr)
            {
                groupSettings.method = *scatterMethodAttr->getData<int>();
            }
            BundleAttrib const* randomSeedAttr = groupPrim->getConstAttr(db.tokens.randomSeed);
            if (randomSeedAttr)
            {
                groupSettings.randomSeed = *randomSeedAttr->getData<uint64_t>();
            }
            BundleAttrib const* pruneCollisionAttr = groupPrim->getConstAttr(db.tokens.pruneCollision);
            if (pruneCollisionAttr)
            {
                groupSettings.pruneCollision = *pruneCollisionAttr->getData<int>();
            }

            getPrototypeSettings(db, groupPrim, groupSettings.protoSettings);

            groups[group.name] = group;
        }

        for (size_t primIndex : overridePrimIndices)
        {
            ConstBundlePrim* overridePrim = groupPrims.getConstPrim(primIndex);
            BundleAttrib const* groupNameAttr = overridePrim->getConstAttr(db.tokens.groupName);
            BundleAttrib const* objectIndexAttr = overridePrim->getConstAttr(db.tokens.objectIndex);
            if (!groupNameAttr || !objectIndexAttr)
                continue;
            const std::string groupName = groupNameAttr->getData<NameToken>()->getString();
            auto& groupSettings = groups[groupName].settings;
            PrototypeSettings settingsOverride;
            getPrototypeSettings(db, overridePrim, settingsOverride, &groupSettings.protoSettings);
            const int objectIndex = *objectIndexAttr->getData<int>();
            groupSettings.settingsOverrides[objectIndex] = settingsOverride;
        }

        return groups;
    }

    // TODO: this function was written at a time when we were directly accessing prim-in-bundle dirtyIDs.
    // This is now deprecated, so as a half-measure we have removed the logic to set primDirty = false.
    // But a more complete refactor of this logic is warranted.
    static void cachePrimDirtyID(
        ConstBundlePrim* prim, BundlePrims& cachedPrims, NameToken dirtyIDToken, bool& primDirty, int& cachedPrimIndex)
    {
        const NameToken primPath = prim->path();
        primDirty = true;
        cachedPrimIndex = -1;
        for (size_t cachedIndex = 0, cachedCount = cachedPrims.getPrimCount(); cachedIndex < cachedCount; ++cachedIndex)
        {
            BundlePrim* cachedPrim = cachedPrims.getPrim(cachedIndex);
            if (cachedPrim && cachedPrim->path() == primPath)
            {
                cachedPrimIndex = (int)cachedIndex;
                return;
            }
        }
        cachedPrimIndex = (int)cachedPrims.getPrimCount();
        cachedPrims.addPrims(1);
        BundlePrim* cachedPrim = cachedPrims.getPrim(cachedPrimIndex);
        cachedPrim->setPath(primPath);
    }

    static std::vector<float> calculateCurvePathKnots(std::vector<vec3f>& tessPoints)
    {
        std::vector<float> pathKnots;
        const size_t pointsCount = tessPoints.size();
        if (pointsCount == 0)
            return pathKnots;
        pathKnots.resize(pointsCount);
        pathKnots[0] = 0.f;

        float pathLength = 0.f;
        for (size_t i = 1; i < pointsCount; ++i)
        {
            pathLength += (tessPoints[i - 1] - tessPoints[i]).GetLength();
            pathKnots[i] = pathLength;
        }
        for (size_t i = 1; i < pointsCount; ++i)
        {
            pathKnots[i] = pathKnots[i] / pathLength;
        }
        return pathKnots;
    }

    static bool triangleProjectIntersectWithCurve(const vec3f& v0,
                                                  const vec3f& v1,
                                                  const vec3f& v2,
                                                  const std::vector<vec3f>& curvePoints)
    {
        // Projection along X axis
        vec2f v0x{ v0[1], v0[2] };
        vec2f v1x{ v1[1], v1[2] };
        vec2f v2x{ v2[1], v2[2] };
        // Projection along Y axis
        vec2f v0y{ v0[0], v0[2] };
        vec2f v1y{ v1[0], v1[2] };
        vec2f v2y{ v2[0], v2[2] };
        // Projection along Z axis
        vec2f v0z{ v0[0], v0[1] };
        vec2f v1z{ v1[0], v1[1] };
        vec2f v2z{ v2[0], v2[1] };

        auto checkTriangle = [](const vec2f& v0, const vec2f& v1, const vec2f& v2)
        {
            constexpr float epsilon = 1.e-6f;
            vec2f e0 = v1 - v0;
            vec2f e1 = v2 - v0;
            float l0 = e0.GetLength();
            float l1 = e1.GetLength();
            if (l0 < epsilon || l1 < epsilon)
                return false;
            const float abscos = abs(e0.Dot(e1)) / (l0 * l1);
            return abs(abscos - 1.f) > epsilon;
        };
        const bool isTriangles[] = { checkTriangle(v0x, v1x, v2x), checkTriangle(v0y, v1y, v2y),
                                     checkTriangle(v0z, v1z, v2z) };

        auto sameSide = [](const vec2f& p, const vec2f& q, const vec2f& a, const vec2f& b)
        {
            float sp = (p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0]);
            float sq = (q[0] - a[0]) * (b[1] - a[1]) - (q[1] - a[1]) * (b[0] - a[0]);
            return sp * sq;
        };

        auto checkIntersection =
            [sameSide](const vec2f& p0, const vec2f& p1, const vec2f& v0, const vec2f& v1, const vec2f& v2)
        {
            const float s1 = sameSide(p0, v2, v0, v1);
            const float s2 = sameSide(p1, v2, v0, v1);
            if (s1 < 0.f && s2 < 0.f)
                return false;
            const float s3 = sameSide(p0, v0, v1, v2);
            const float s4 = sameSide(p1, v0, v1, v2);
            if (s3 < 0.f && s4 < 0.f)
                return false;
            const float s5 = sameSide(p0, v1, v2, v0);
            const float s6 = sameSide(p1, v1, v2, v0);
            if (s5 < 0.f && s6 < 0.f)
                return false;
            const float s7 = sameSide(v0, v1, p0, p1);
            const float s8 = sameSide(v1, v2, p0, p1);
            if (s7 > 0.f && s8 > 0.f)
                return false;
            return true;
        };

        const size_t curvePointsCount = curvePoints.size();
        for (size_t i = 1; i < curvePointsCount; ++i)
        {
            const vec3f& a = curvePoints[i - 1];
            const vec3f& b = curvePoints[i];

            if (isTriangles[0])
            {
                const vec2f ax{ a[1], a[2] };
                const vec2f bx{ b[1], b[2] };
                if (checkIntersection(ax, bx, v0x, v1x, v2x))
                    return true;
            }
            if (isTriangles[1])
            {
                const vec2f ay{ a[0], a[2] };
                const vec2f by{ b[0], b[2] };
                if (checkIntersection(ay, by, v0y, v1y, v2y))
                    return true;
            }
            if (isTriangles[2])
            {
                const vec2f az{ a[0], a[1] };
                const vec2f bz{ b[0], b[1] };
                if (checkIntersection(az, bz, v0z, v1z, v2z))
                    return true;
            }
        }
        return false;
    }

    static bool pointWithinCurvePath(const vec3f& point,
                                     const std::vector<vec3f>& curvePoints,
                                     const std::vector<float>& curvePathKnots,
                                     const float width,
                                     omni::ramp::IRamp* s_iRamp,
                                     const size_t numRampKeys,
                                     const float* rampPos,
                                     const float* rampVal,
                                     const int* rampInt)
    {
        constexpr float epsilon = 1.e-6f;
        const size_t curvePointsCount = curvePoints.size();
        float radius = width * 0.5f;
        std::vector<float> widthMuls(curvePointsCount, 1.f);
        s_iRamp->sampleFloatArray(
            curvePointsCount, widthMuls.data(), curvePathKnots.data(), 0, numRampKeys, rampPos, rampVal, rampInt);
        float lastT = 0.f;
        for (size_t i = 1; i < curvePointsCount; ++i)
        {
            const vec3f a = curvePoints[i - 1];
            const vec3f b = curvePoints[i];
            const vec3f ab = b - a;
            const float abLenSq = ab.GetLengthSq();
            if (abLenSq <= epsilon)
                continue;
            const vec3f pa = point - a;
            float t = pa.Dot(ab) / abLenSq;
            t = std::max(0.f, std::min(1.f, t));
            const vec3f onSegment = a + ab * t;
            const float widthMul = (1.f - t) * widthMuls[i - 1] + t * widthMuls[i];
            radius *= widthMul;
            const float distSq = (point - onSegment).GetLengthSq();
            if (distSq <= radius * radius)
                return true;
        }
        return false;
    }


    static void initCurveSources(OgnScatterPointsGroupDatabase& db, ScatterSources& curveSources, PhysXMeshes& sourceMeshes)
    {
        const GraphContextObj& context = db.abi_context();

        if (!db.inputs.has_curveSources())
            return;

        const size_t curveStepsPerpSegment = db.inputs.curveStepsPerSegment();
        ConstBundlePrims curvePrims(context, db.inputs.curveSources().abi_bundleHandle());
        const size_t curvePrimsCount = curvePrims.getPrimCount();
        curveSources.reserve(curvePrimsCount);
        sourceMeshes.reserve(curvePrimsCount);

        bool transformDirty = db.inputs.curveSources.changes().hasChanged();

        std::vector<matrix4d> transforms;
        getPrimTransforms(curvePrims, transforms);

        BundlePrims cachedCurves(context, db.state.cachedCurveSources().abi_bundleHandle());

        for (size_t primIndex = 0; primIndex < curvePrimsCount; ++primIndex)
        {
            ConstBundlePrim* curvePrim = curvePrims.getConstPrim(primIndex);
            if (!curvePrim || curvePrim->type() != db.tokens.BasisCurves)
            {
                CARB_LOG_WARN_ONCE("ScatterPointsGroup: prim %s is not a curve source.", curvePrim->path().getText());
                continue;
            }
            const matrix4d& curveTransform = transforms[primIndex];

            bool primDirty = true;
            int cachedPrimIndex = -1;
            cachePrimDirtyID(curvePrim, cachedCurves, db.tokens.dirtyID, primDirty, cachedPrimIndex);

            BundleAttrib const* pointsInAttr = curvePrim->getConstAttr(db.tokens.points);
            BundleAttrib const* curveVertexCountsAttr = curvePrim->getConstAttr(db.tokens.curveVertexCounts);
            BundleAttrib const* curveBasisAttr = curvePrim->getConstAttr(db.tokens.basis);
            BundleAttrib const* wrapTypeAttr = curvePrim->getConstAttr(db.tokens.wrap);
            // Note: it's ok if curveVertexCountsAttr does not exist, in the case of a single curve
            if (pointsInAttr == nullptr || curveBasisAttr == nullptr || wrapTypeAttr == nullptr)
            {
                CARB_LOG_WARN_ONCE(
                    "ScatterPointsGroup: prim %s has no basis curve attributes.", curvePrim->path().getText());
                continue;
            }
            const size_t pointsInCount = pointsInAttr->size();
            if (pointsInCount == 0)
            {
                CARB_LOG_WARN_ONCE("ScatterPointsGroup: prim %s has no points.", curvePrim->path().getText());
                continue;
            }
            const vec3f* const points = pointsInAttr->getData<vec3f>();
            const int* curveVertexCounts =
                curveVertexCountsAttr == nullptr ? nullptr : curveVertexCountsAttr->getData<int>();
            const size_t curveCount = curveVertexCounts == nullptr ? 0 : curveVertexCountsAttr->size();
            const NameToken* basisToken = curveBasisAttr->getData<NameToken>();
            const NameToken* wrapToken = wrapTypeAttr->getData<NameToken>();
            if (points == nullptr || basisToken == nullptr || wrapToken == nullptr)
            {
                CARB_LOG_WARN_ONCE(
                    "ScatterPointsGroup: prim %s has no valid basis curve data.", curvePrim->path().getText());
                continue;
            }
            eBasisCurveWrap curveWrapType;
            if (*wrapToken == db.tokens.nonperiodic)
            {
                curveWrapType = eBasisCurveWrap::NonPeriodic;
            }
            else if (*wrapToken == db.tokens.periodic)
            {
                curveWrapType = eBasisCurveWrap::Periodic;
            }
            else if (*wrapToken == db.tokens.pinned)
            {
                curveWrapType = eBasisCurveWrap::Pinned;
            }
            else
            {
                CARB_LOG_WARN_ONCE(
                    "ScatterPointsGroup: prim %s has no valid curve wrap type.", curvePrim->path().getText());
                continue;
            }
            eBasisCurveType curveBasisType;
            if (*basisToken == db.tokens.bspline)
            {
                curveBasisType = eBasisCurveType::BSpline;
            }
            else if (*basisToken == db.tokens.bezier)
            {
                curveBasisType = eBasisCurveType::Bezier;
            }
            else if (*basisToken == db.tokens.catmullRom)
            {
                curveBasisType = eBasisCurveType::CatmullRom;
            }
            else
            {
                CARB_LOG_WARN_ONCE(
                    "ScatterPointsGroup: prim %s has no valid curve basis type.", curvePrim->path().getText());
                continue;
            }
            const size_t estimatedCount = SplineCurve{ curveWrapType, curveBasisType }.getTessellationPointCount(
                pointsInCount, curveStepsPerpSegment);

            ScatterSource source;
            source.cachedPrimIndex = cachedPrimIndex;
            source.geometryDirty = transformDirty || primDirty;
            source.sourceType = SourceType::eCurve;
            // Flattened tessellated points and triangulated indices arrays
            std::vector<vec3f>& srcControlPoints = source.controlPoints;
            std::vector<vec3f>& tessPositions = source.points;
            std::vector<float>& pathKnots = source.pathKnots;
            srcControlPoints.reserve(pointsInCount);
            tessPositions.reserve(estimatedCount);
            pathKnots.reserve(estimatedCount);
            std::vector<int>& trigIndices = source.triIndices;
            trigIndices.reserve(estimatedCount * 3);

            for (size_t curveIndex = 0, startIndex = 0, tessStartIndex = 0;
                 curveIndex < (curveCount == 0 ? 1 : curveCount); curveIndex++)
            {
                const size_t count = (curveCount == 0 ? pointsInCount : curveVertexCounts[curveIndex]);
                std::vector<vec3f> controlPoints(count);
                std::transform(points + startIndex, points + startIndex + count, controlPoints.begin(),
                               [&](const vec3f& x) { return curveTransform.Transform(x); });

                startIndex += count;

                SplineCurve curve(curveWrapType, curveBasisType);
                std::vector<vec3f> tessCurvePoints;
                curve.tessellate(controlPoints.data(), controlPoints.size(), tessCurvePoints, curveStepsPerpSegment);
                tessPositions.insert(tessPositions.end(), tessCurvePoints.begin(), tessCurvePoints.end());
                srcControlPoints.insert(srcControlPoints.end(), controlPoints.begin(), controlPoints.end());

                std::vector<float> tessPathKnots = calculateCurvePathKnots(tessCurvePoints);
                pathKnots.insert(pathKnots.end(), tessPathKnots.begin(), tessPathKnots.end());

                const uint32_t tessCount = (uint32_t)tessCurvePoints.size();
                std::vector<uint32_t> curveTrig =
                    triangulatePolygon(tessCurvePoints.data(), tessCount, TriangleAreaWeightFunction<float>{});
                // Flatten triangulated indices
                for (size_t tIndex = 0, tCount = curveTrig.size(); tIndex < tCount; ++tIndex)
                {
                    trigIndices.push_back(curveTrig[tIndex] + (int)tessStartIndex);
                }
                tessStartIndex += tessCount;
            }

            sourceMeshes.push_back({});
            auto& sourceMesh = sourceMeshes.back();
            triPointsToPxTriangleMesh(
                tessPositions.data(), tessPositions.size(), trigIndices.data(), trigIndices.size(), sourceMesh);
            triangleAreaCDF(source.points, source.triIndices, source.triangleAreaSums);
            source.geometry = sourceMesh.get();

            bool isAdditive = true;
            BundleAttrib const* zoneSignAttr = curvePrim->getConstAttr(db.tokens.zoneSign);
            if (zoneSignAttr)
            {
                auto* zoneSignData = zoneSignAttr->getData<NameToken>();
                if (zoneSignData)
                {
                    isAdditive = *zoneSignData == db.tokens.additive;
                }
            }
            source.zoneSign = isAdditive ? ZoneSign::eAdditive : ZoneSign::eSubtractive;

            BundleAttrib const* objectIndicesAttr = curvePrim->getConstAttr(db.tokens.objectIndices);
            if (objectIndicesAttr)
            {
                const size_t attrSize = objectIndicesAttr->size();
                source.objectIndices.resize(attrSize);
                memcpy(source.objectIndices.data(), objectIndicesAttr->getData<int>(), sizeof(int) * attrSize);
            }

            source.curvePathRegion = false;
            BundleAttrib const* curvePathRegionAttr = curvePrim->getConstAttr(db.tokens.curvePathRegion);
            if (curvePathRegionAttr)
            {
                auto* curvePathRegionData = curvePathRegionAttr->getData<int>();
                if (curvePathRegionData && *curvePathRegionData != 0)
                {
                    source.curvePathRegion = true;
                }
            }

            source.curvePathWidth = 0.f;
            BundleAttrib const* curvePathWidthAttr = curvePrim->getConstAttr(db.tokens.curvePathWidth);
            if (curvePathWidthAttr)
            {
                auto* curvePathWidthData = curvePathWidthAttr->getData<float>();
                if (curvePathWidthData)
                {
                    source.curvePathWidth = *curvePathWidthData;
                }
            }

            BundleAttrib const* curvePathWidthRampPosAttr =
                curvePrim->getConstAttr(db.tokens.curvePathWidthRampPositions);
            if (curvePathWidthRampPosAttr)
            {
                const size_t attrSize = curvePathWidthRampPosAttr->size();
                source.pathWidthRampPositions.resize(attrSize);
                memcpy(source.pathWidthRampPositions.data(), curvePathWidthRampPosAttr->getData<float>(),
                       sizeof(float) * attrSize);
            }

            BundleAttrib const* curvePathWidthRampValAttr = curvePrim->getConstAttr(db.tokens.curvePathWidthRampValues);
            if (curvePathWidthRampValAttr)
            {
                const size_t attrSize = curvePathWidthRampValAttr->size();
                source.pathWidthRampValues.resize(attrSize);
                memcpy(source.pathWidthRampValues.data(), curvePathWidthRampValAttr->getData<float>(),
                       sizeof(float) * attrSize);
            }

            BundleAttrib const* curvePathWidthRampIntAttr =
                curvePrim->getConstAttr(db.tokens.curvePathWidthRampInterpolations);
            if (curvePathWidthRampIntAttr)
            {
                const size_t attrSize = curvePathWidthRampIntAttr->size();
                source.pathWidthRampInterpolations.resize(attrSize);
                memcpy(source.pathWidthRampInterpolations.data(), curvePathWidthRampIntAttr->getData<int>(),
                       sizeof(int) * attrSize);
            }

            curveSources.push_back(source);
        }
    }

    static void initVolumeSources(OgnScatterPointsGroupDatabase& db,
                                  ScatterSources& volumeSources,
                                  PhysXMeshes& sourceMeshes)
    {
        const GraphContextObj& context = db.abi_context();

        if (!db.inputs.has_volumeSources())
            return;

        ConstBundlePrims volumePrims(context, db.inputs.volumeSources().abi_bundleHandle());
        const size_t volumePrimsCount = volumePrims.getPrimCount();
        volumeSources.reserve(volumePrimsCount);
        sourceMeshes.reserve(sourceMeshes.size() + volumePrimsCount);

        bool transformDirty = db.inputs.volumeSources.changes().hasChanged();

        // NOTE: transforms are unused in this function -- is that intended?
        std::vector<matrix4d> transforms;
        getPrimTransforms(volumePrims, transforms);

        BundlePrims cachedVolumes(context, db.state.cachedVolumeSources().abi_bundleHandle());

        for (size_t primIndex = 0; primIndex < volumePrimsCount; ++primIndex)
        {
            ConstBundlePrim* volumePrim = volumePrims.getConstPrim(primIndex);
            if (!volumePrim || volumePrim->type() != db.tokens.Mesh)
            {
                CARB_LOG_WARN_ONCE("ScatterPointsGroup: prim %s is not a volume source.", volumePrim->path().getText());
                continue;
            }

            bool primDirty = true;
            int cachedPrimIndex = -1;
            cachePrimDirtyID(volumePrim, cachedVolumes, db.tokens.dirtyID, primDirty, cachedPrimIndex);

            ScatterSource source;
            const bool validMesh = primInBundleToTriangles(volumePrims, primIndex, source.points, source.triIndices,
                                                           &source.normals, nullptr, nullptr, &source.texcoords);
            if (!validMesh)
            {
                continue;
            }
            source.cachedPrimIndex = cachedPrimIndex;
            source.geometryDirty = transformDirty || primDirty;
            source.sourceType = SourceType::eVolume;
            triangleAreaCDF(source.points, source.triIndices, source.triangleAreaSums);
            sourceMeshes.push_back({});
            auto& sourceMesh = sourceMeshes.back();
            triPointsToPxTriangleMesh(source.points.data(), source.points.size(), source.triIndices.data(),
                                      source.triIndices.size(), sourceMesh);
            source.geometry = sourceMesh.get();

            physx::PxVec3 dims = sourceMesh->getLocalBounds().getDimensions();
            source.boundVolume = dims.x * dims.y * dims.z;
            source.maxBoundArea = std::max(dims.x * dims.y, std::max(dims.y * dims.z, dims.z * dims.x));

            bool isAdditive = true;
            BundleAttrib const* zoneSignAttr = volumePrim->getConstAttr(db.tokens.zoneSign);
            if (zoneSignAttr)
            {
                auto* zoneSignData = zoneSignAttr->getData<NameToken>();
                if (zoneSignData)
                {
                    isAdditive = *zoneSignData == db.tokens.additive;
                }
            }
            source.zoneSign = isAdditive ? ZoneSign::eAdditive : ZoneSign::eSubtractive;

            BundleAttrib const* objectIndicesAttr = volumePrim->getConstAttr(db.tokens.objectIndices);
            if (objectIndicesAttr)
            {
                const size_t attrSize = objectIndicesAttr->size();
                source.objectIndices.resize(attrSize);
                memcpy(source.objectIndices.data(), objectIndicesAttr->getData<int>(), sizeof(int) * attrSize);
            }
            volumeSources.push_back(source);
        }
    }

    static void initBaseMeshes(OgnScatterPointsGroupDatabase& db,
                               BaseMeshes& bases,
                               ScatterSources& scatterSources,
                               const ScatterGroups& scatterGroups,
                               InputChangeRecord& inputChangeRecord)
    {
        const GraphContextObj& context = db.abi_context();
        if (!db.inputs.has_bases())
            return;

        ConstBundlePrims baseMeshesPrims(context, db.inputs.bases().abi_bundleHandle());
        const size_t primsCount = baseMeshesPrims.getPrimCount();
        if (primsCount == 0)
            return;

        if (inputChangeRecord.basesChanged)
        {
            primsInBundleToTriangles(baseMeshesPrims, bases.points, bases.triIndices, &bases.normals, nullptr, nullptr,
                                     &bases.texcoords, &bases.meshIndices);
            const size_t baseMeshesPointsCount = bases.points.size();
            triPointsToPxTriangleMesh(bases.points.data(), baseMeshesPointsCount, bases.triIndices.data(),
                                      bases.triIndices.size(), bases.mesh);
            bases.geometry = bases.mesh.get();
            triangleAreaCDF(bases.points, bases.triIndices, bases.triangleAreaSums);

            std::vector<vec3f>& points = bases.points;
            std::vector<float>& weights = bases.scatterWeights;
            std::vector<int>& objectIndices = bases.objectIndices;
            weights.reserve(baseMeshesPointsCount);
            objectIndices.reserve(baseMeshesPointsCount);

            size_t accumulatePointsCount = 0;
            float& elevLow = bases.elevationLow;
            float& elevHigh = bases.elevationHigh;
            for (size_t primIndex = 0; primIndex < primsCount; primIndex++)
            {
                ConstBundlePrim* meshPrim = baseMeshesPrims.getConstPrim(primIndex);
                if (meshPrim->type() != db.tokens.Mesh)
                {
                    continue;
                }

                BundleAttrib const* pointsAttr = meshPrim->getConstAttr(db.tokens.points);
                if (pointsAttr == nullptr || pointsAttr->size() == 0)
                {
                    continue;
                }
                const size_t primPointsCount = pointsAttr->size();
                for (size_t pi = accumulatePointsCount; pi < accumulatePointsCount + primPointsCount; ++pi)
                {
                    const float height = points[pi][1];
                    elevLow = std::min(height, elevLow);
                    elevHigh = std::max(height, elevHigh);
                }
                accumulatePointsCount += primPointsCount;

                BundleAttrib const* weightsAttr = meshPrim->getConstAttr(db.tokens.primvars_scatterWeights);
                if (weightsAttr)
                {
                    bases.hasWeights = true;
                    const size_t weightsCount = weightsAttr->size();
                    const float* weightVals = weightsAttr->getData<float>();
                    for (size_t wi = 0; wi < weightsCount; ++wi)
                    {
                        const float wv = std::max(weightVals[wi], 0.f);
                        weights.push_back(wv);
                    }
                }
                else
                {
                    for (size_t pi = 0; pi < primPointsCount; ++pi)
                    {
                        weights.push_back(0.f);
                    }
                }
                BundleAttrib const* objectIndicesAttr = meshPrim->getConstAttr(db.tokens.primvars_objectIndices);
                if (objectIndicesAttr)
                {
                    bases.hasObjectIndices = true;
                    const size_t objIdxCount = objectIndicesAttr->size();
                    const float* objIdxVals = objectIndicesAttr->getData<float>();
                    for (size_t oi = 0; oi < objIdxCount; ++oi)
                    {
                        const int objIdx = (int)objIdxVals[oi];
                        objectIndices.push_back(objIdx);
                    }
                }
                else
                {
                    for (size_t pi = 0; pi < primPointsCount; ++pi)
                    {
                        objectIndices.push_back(-1);
                    }
                }
            }
            // Cache geometry
            BundlePrims cachedBaseMeshes(context, db.state.cachedBaseMeshes().abi_bundleHandle());
            BundlePrim& cachedCommon = cachedBaseMeshes.getCommonAttrs();

            BundleAttrib* cachedPointsAttr = cachedCommon.getAttr(db.tokens.points);
            vec3f* cachedPointsData = nullptr;
            bool pointsDirty = false;
            if (!cachedPointsAttr)
            {
                pointsDirty = true;
                cachedPointsAttr = cachedCommon.addAttr(
                    db.tokens.points, { BaseDataType::eFloat, 3, 1, AttributeRole::eNone }, baseMeshesPointsCount);
            }
            else
            {
                const size_t cachedPointsCount = cachedPointsAttr->size();
                if (cachedPointsCount != baseMeshesPointsCount)
                {
                    pointsDirty = true;
                    cachedPointsAttr->resize(baseMeshesPointsCount);
                }
                else
                {
                    cachedPointsData = cachedPointsAttr->getData<vec3f>();
                    pointsDirty =
                        memcmp(cachedPointsData, bases.points.data(), baseMeshesPointsCount * sizeof(vec3f)) != 0;
                }
            }
            if (pointsDirty)
            {
                cachedPointsData = cachedPointsAttr->getData<vec3f>();
                memcpy(cachedPointsData, bases.points.data(), baseMeshesPointsCount * sizeof(vec3f));
            }

            BundleAttrib* cachedTriIndicesAttr = cachedCommon.getAttr(db.tokens.triIndices);
            const size_t triIndicesCount = bases.triIndices.size();
            int* cachedTriIndicesData = nullptr;
            bool indicesDirty = false;
            if (!cachedTriIndicesAttr)
            {
                indicesDirty = true;
                cachedTriIndicesAttr = cachedCommon.addAttr(
                    db.tokens.triIndices, { BaseDataType::eInt, 1, 1, AttributeRole::eNone }, triIndicesCount);
            }
            else
            {
                const size_t cachedTriIndicesCount = cachedTriIndicesAttr->size();
                if (cachedTriIndicesCount != triIndicesCount)
                {
                    indicesDirty = true;
                    cachedTriIndicesAttr->resize(triIndicesCount);
                }
                else
                {
                    cachedTriIndicesData = cachedTriIndicesAttr->getData<int>();
                    indicesDirty =
                        memcmp(cachedTriIndicesData, bases.triIndices.data(), triIndicesCount * sizeof(int)) != 0;
                }
            }
            if (indicesDirty)
            {
                cachedTriIndicesData = cachedTriIndicesAttr->getData<int>();
                memcpy(cachedTriIndicesData, bases.triIndices.data(), triIndicesCount * sizeof(int));
            }
            bases.geometryDirty = pointsDirty || indicesDirty;
        }

        Ramp& weightsRamp = bases.weightsRamp;
        weightsRamp.keysCount = db.inputs.weightsRampPositions().size();
        weightsRamp.positions = db.inputs.weightsRampPositions().data();
        weightsRamp.values = db.inputs.weightsRampValues().data();
        weightsRamp.interpolations = db.inputs.weightsRampInterpolations().data();
        Ramp& objectIndicesRamp = bases.objectIndicesRamp;
        objectIndicesRamp.keysCount = db.inputs.objectIndicesRampPositions().size();
        objectIndicesRamp.positions = db.inputs.objectIndicesRampPositions().data();
        objectIndicesRamp.values = db.inputs.objectIndicesRampValues().data();
        objectIndicesRamp.interpolations = db.inputs.objectIndicesRampInterpolations().data();

        if (inputChangeRecord.texturesChanged && !bases.meshIndices.empty())
        {
            bases.textures.clear();

            ConstBundlePrims texturePrims(db.abi_context(), db.inputs.textures().abi_bundleHandle());
            size_t texCount = texturePrims.getPrimCount();

            bases.textures.resize(texCount);

            for (size_t i = 0; i < texCount; i++)
            {
                ConstBundlePrim* texPrim = texturePrims.getPrim(i);

                auto validAttr = texPrim->getConstAttr(db.tokens.valid);
                if (validAttr && validAttr->get<bool>())
                {
                    auto width = texPrim->getConstAttr(db.tokens.width)->get<uint32_t>();
                    auto height = texPrim->getConstAttr(db.tokens.height)->get<uint32_t>();
                    auto bitDepth = texPrim->getConstAttr(db.tokens.bitDepth)->get<uint8_t>();
                    auto componentCount = texPrim->getConstAttr(db.tokens.componentCount)->get<uint8_t>();

                    const uint8_t* data = texPrim->getConstAttr(db.tokens.data)->getConstData<uint8_t>();

                    bases.textures[i] = std::make_shared<TextureInfo>(width, height, bitDepth, componentCount, data);
                }
            }
        }

        if (inputChangeRecord.textureFiltersChanged)
        {
            bases.textureFilters.clear();

            ConstBundlePrims textureFilterPrims(db.abi_context(), db.inputs.textureFilters().abi_bundleHandle());
            size_t filterCount = textureFilterPrims.getPrimCount();

            for (size_t i = 0; i < filterCount; i++)
            {
                ConstBundlePrim* filterPrim = textureFilterPrims.getPrim(i);

                auto baseIndexAttr = filterPrim->getConstAttr(db.tokens.baseIndex);
                if (!baseIndexAttr)
                {
                    // must have base
                    continue;
                }

                int32_t baseIndex = baseIndexAttr->get<int32_t>();

                auto& filters = bases.textureFilters[baseIndex];
                filters.push_back({});
                TextureFilter& filter = filters.back();

                filter.baseIndex = baseIndex;

                auto channelAttr = filterPrim->getConstAttr(db.tokens.channel);
                if (channelAttr)
                {
                    auto channelToken = channelAttr->get<NameToken>();

                    if (channelToken == db.tokens.r)
                    {
                        filter.channel = SamplingChannel::eR;
                    }
                    if (channelToken == db.tokens.g)
                    {
                        filter.channel = SamplingChannel::eG;
                    }
                    if (channelToken == db.tokens.b)
                    {
                        filter.channel = SamplingChannel::eB;
                    }
                    if (channelToken == db.tokens.a)
                    {
                        filter.channel = SamplingChannel::eA;
                    }
                }

                auto zoneSignAttr = filterPrim->getConstAttr(db.tokens.zoneSign);
                if (zoneSignAttr)
                {
                    auto* zoneSignData = zoneSignAttr->getData<NameToken>();
                    if (zoneSignData)
                    {
                        filter.additive = *zoneSignData == db.tokens.additive;
                    }
                }

                // if has groupName, using objectIndices in group instead of filter's objectIndices
                bool usingGroupPrototypes = false;
                auto groupNameAttr = filterPrim->getConstAttr(db.tokens.groupName);
                if (groupNameAttr)
                {
                    const std::string groupName = groupNameAttr->getData<NameToken>()->getString();
                    auto iter = scatterGroups.find(groupName);
                    if (iter != scatterGroups.end())
                    {
                        usingGroupPrototypes = true;
                        auto group = iter->second;
                        const size_t attrSize = group.objectIndices.size();
                        filter.objectIndices.reserve(attrSize);
                        for (size_t i = 0; i < attrSize; i++)
                        {
                            filter.objectIndices.insert(group.objectIndices[i]);
                        }
                    }
                }

                if (!usingGroupPrototypes)
                {
                    auto objectIndicesAttr = filterPrim->getConstAttr(db.tokens.objectIndices);
                    if (objectIndicesAttr)
                    {
                        const size_t attrSize = objectIndicesAttr->size();
                        filter.objectIndices.reserve(attrSize);

                        const int32_t* data = objectIndicesAttr->getData<int32_t>();
                        for (size_t i = 0; i < attrSize; i++)
                        {
                            filter.objectIndices.insert(data[i]);
                        }
                    }
                }


                auto textureIndexAttr = filterPrim->getConstAttr(db.tokens.textureIndex);
                if (textureIndexAttr)
                {
                    filter.textureIndex = textureIndexAttr->get<int32_t>();
                }
            }
        }

        validateRegions(db, scatterSources, bases);
    }

    struct OutputPoints
    {
        std::vector<vec3f> points;
        std::vector<vec3f> normals;
        std::vector<vec3f> tangents;
        std::vector<vec3f> binormals;
        std::vector<vec3f> rotations;
        std::vector<vec3f> scales;
        std::vector<int> objectIndices;

        size_t size() const
        {
            return points.size();
        }

        void reserve(size_t size)
        {
            points.reserve(size);
            normals.reserve(size);
            tangents.reserve(size);
            binormals.reserve(size);
            rotations.reserve(size);
            scales.reserve(size);
            objectIndices.reserve(size);
        }
    };

    static void scatterForGroup(OgnScatterPointsGroupDatabase& db,
                                std::mt19937_64& random,
                                const Prototypes& prototypes,
                                const ScatterGroup& group,
                                const BaseMeshes& bases,
                                const ScatterSources& scatterSources,
                                OutputPoints& outputPoints)
    {
        double time = db.inputs.time();
        const uint64_t timeBasedSeed = reinterpret_cast<uint64_t&>(time);
        const uint64_t randomSeed = db.inputs.randomSeed();

        const uint32_t groupPointsBegin = (uint32_t)outputPoints.size();
        const GroupSettings& groupSettings = group.settings;

        const int groupDesiredPoint = groupSettings.desiredPoints;
        outputPoints.reserve(outputPoints.size() + groupDesiredPoint);
        size_t protosCount = group.objectIndices.size();
        std::vector<int> groupObjectIndices;
        if (protosCount != 0)
        {
            groupObjectIndices = group.objectIndices;
        }
        else
        {
            protosCount = prototypes.size();
            groupObjectIndices.resize(protosCount);
            std::iota(groupObjectIndices.begin(), groupObjectIndices.end(), 0);
        }

        // Normalize the prototype desired points
        std::vector<int> protoDesiredPoints(protosCount);
        if (groupSettings.protoPercents.size() != protosCount)
        {
            std::fill(protoDesiredPoints.begin(), protoDesiredPoints.end(), groupDesiredPoint / (int)protosCount);
        }
        else
        {
            const float sumPercents =
                std::accumulate(groupSettings.protoPercents.begin(), groupSettings.protoPercents.end(), 0.f);
            int accuDesiredPoints = 0;
            for (size_t i = 0; i < protosCount - 1; ++i)
            {
                protoDesiredPoints[i] = (int)(groupDesiredPoint * groupSettings.protoPercents[i] / sumPercents);
                accuDesiredPoints += protoDesiredPoints[i];
            }
            protoDesiredPoints[protosCount - 1] = groupDesiredPoint - accuDesiredPoints;
        }
        bool validBaseMeshes = !bases.points.empty();

        for (size_t oiIdx = 0, oiCount = groupObjectIndices.size(); oiIdx < oiCount; ++oiIdx)
        {
            const int protoIndex = groupObjectIndices[oiIdx];
            const pxr::SdfPath& protoPath = prototypes[protoIndex].path;
            // Random seed for each prototype, so it won't jitter with the change of the other prototypes
            const uint64_t protoSeed = deterministic_string_hash(protoPath.GetString());
            const uint64_t combinedSeed = timeBasedSeed ^ randomSeed ^ protoSeed ^ groupSettings.randomSeed;
            random.seed(combinedSeed);

            std::vector<size_t> additiveCurves;
            std::vector<size_t> subtractiveCurves;
            std::vector<size_t> additiveVolumes;
            std::vector<size_t> subtractiveVolumes;

            auto iterSettingsOverride = groupSettings.settingsOverrides.find(protoIndex);
            const PrototypeSettings& protoSettings = (iterSettingsOverride != groupSettings.settingsOverrides.end()) ?
                                                         iterSettingsOverride->second :
                                                         groupSettings.protoSettings;

            for (size_t srcIdx = 0, sourcesCount = scatterSources.size(); srcIdx < sourcesCount; ++srcIdx)
            {
                const ScatterSource& source = scatterSources[srcIdx];
                const auto& srcObjIndics = source.objectIndices;
                if (!srcObjIndics.empty() &&
                    std::find(srcObjIndics.begin(), srcObjIndics.end(), protoIndex) == srcObjIndics.end())
                    continue;
                const bool isAdditive = (source.zoneSign == ZoneSign::eAdditive);
                if (source.sourceType == SourceType::eCurve)
                {
                    if (isAdditive)
                    {
                        additiveCurves.push_back(srcIdx);
                    }
                    else
                    {
                        subtractiveCurves.push_back(srcIdx);
                    }
                }
                else
                {
                    if (isAdditive)
                    {
                        additiveVolumes.push_back(srcIdx);
                    }
                    else
                    {
                        subtractiveVolumes.push_back(srcIdx);
                    }
                }
            }
            const int desiredPoints = protoDesiredPoints[oiIdx];
            if (groupSettings.method == (int)ScatterMethod::eSurface)
            {
                if (validBaseMeshes)
                {
                    scatterSurfaces(desiredPoints, protoIndex, random, combinedSeed, protoSettings, bases,
                                    scatterSources, additiveCurves, subtractiveCurves, additiveVolumes,
                                    subtractiveVolumes, outputPoints);
                }
                else
                {
                    CARB_LOG_WARN("ScatterPointsGroup: no valid base mesh to apply surface method.");
                }
            }
            else if (groupSettings.method == (int)ScatterMethod::eVolume)
            {
                scatterVolumes(desiredPoints, protoIndex, protoSettings, random, scatterSources, additiveVolumes,
                               subtractiveVolumes, outputPoints);
            }
            else if (groupSettings.method == (int)ScatterMethod::eBoth)
            {
                if (validBaseMeshes)
                {
                    scatterBoth(desiredPoints, protoIndex, random, combinedSeed, protoSettings, bases, scatterSources,
                                additiveCurves, subtractiveCurves, additiveVolumes, subtractiveVolumes, outputPoints);
                }
                else
                {
                    CARB_LOG_WARN("ScatterPointsGroup: no valid base mesh to apply both method.");
                }
            }
        }

        const uint32_t groupPointsEnd = (uint32_t)outputPoints.size();
        if (groupSettings.pruneCollision && (groupPointsEnd - groupPointsBegin > 0))
        {
            random.seed(timeBasedSeed ^ randomSeed ^ groupSettings.randomSeed);
            pruneCollidingPoints(outputPoints, groupPointsBegin, groupPointsEnd, prototypes, random);
        }
    }

    static void pruneCollidingPoints(OutputPoints& outputPoints,
                                     const uint32_t pointsBegin,
                                     const uint32_t pointsEnd,
                                     const Prototypes& prototypes,
                                     std::mt19937_64& random)
    {
        const uint32_t pointsCount = pointsEnd - pointsBegin;
        // Construct BVH
        std::vector<physx::PxBounds3> boundsData(pointsCount);
        for (size_t pidx = pointsBegin; pidx < pointsEnd; ++pidx)
        {
            const vec3f position = outputPoints.points[pidx];
            const vec3f scale = outputPoints.scales[pidx];
            const int objectIdx = outputPoints.objectIndices[pidx];
            const vec3f protoBoundMin = prototypes[objectIdx].boundMin;
            const vec3f protoBoundMax = prototypes[objectIdx].boundMax;
            vec3f boundMin = GfCompMult(protoBoundMin, scale) + position;
            vec3f boundMax = GfCompMult(protoBoundMax, scale) + position;
            boundsData[pidx - pointsBegin] = physx::PxBounds3{ physx::PxVec3{ boundMin[0], boundMin[1], boundMin[2] },
                                                               physx::PxVec3{ boundMax[0], boundMax[1], boundMax[2] } };
        }
        physx::PxBVHDesc bvhDesc;
        bvhDesc.bounds.count = pointsCount;
        bvhDesc.bounds.data = boundsData.data();
        bvhDesc.bounds.stride = sizeof(physx::PxBounds3);
        bvhDesc.enlargement = 0.f;
        physx::PxBVH* bvh = PxCreateBVH(bvhDesc);
        if (!bvh)
            return;

        constexpr uint32_t maxHits = 4;
        uint32_t overlapHits[maxHits];
        std::vector<uint32_t> collisions;
        collisions.reserve(pointsCount);
        uint32_t sumHits = 0;

        for (uint32_t pidx = 0; pidx < pointsCount; ++pidx)
        {
            const physx::PxBounds3 bound = boundsData[pidx];

            // XXX this is a minimally invasive workaround -- previously, we had this line:
            // const uint32_t hitsCount = bvh->overlap(bound, maxHits, overlapHits);
            // which accepted a PxBounds3 argument and returned a number of overlap hits.
            // That deprecated function has now been removed, but we could maybe get the
            // same behavior by creating a box (represented by half extents; the translation component
            // of the aabb gets stored in a PxTransform) and supplying a callback to count the number
            // of hits.
            // Note that I don't know whether this callback is called in parallel, etc. -- we need
            // to check with the physx team and/or change our approach here and supplying a callback to count the number
            // of hits.
            // Note that I don't know whether this callback is called in parallel, etc. -- we need
            // to check with the physx team and/or change our approach here.

            physx::PxBoxGeometry box(0.5f * (bound.maximum - bound.minimum));
            physx::PxTransform transform(0.5f * (bound.maximum + bound.minimum));
            OverlapData overlapData;
            bvh->overlap(box, transform, overlapData);

            // overlap with some other bounds
            if (overlapData.m_hitsCount > 1)
            {
                sumHits += overlapData.m_hitsCount;
                collisions.push_back(pidx);
            }
        }
        uint32_t collisionsCount = (uint32_t)collisions.size();
        std::unordered_set<uint32_t> prunes;
        prunes.reserve(collisionsCount);

        while (collisionsCount > 0)
        {
            const uint32_t avgHits = sumHits / collisionsCount;
            uint32_t pruneCount = std::max(1u, collisionsCount / avgHits);
            // prune random points
            simple_shuffle(collisions.data(), collisions.data() + collisionsCount, random);
            for (uint32_t cidx = 0; cidx < pruneCount; ++cidx)
            {
                const uint32_t pidx = collisions[cidx];
                prunes.insert(pidx);
                bvh->updateBounds(pidx, physx::PxBounds3::empty());
            }
            bvh->partialRefit();

            // Re-run overlap test
            const uint32_t remainsCount = collisionsCount - pruneCount;
            std::vector<uint32_t> remains;
            remains.reserve(remainsCount);
            for (uint32_t ridx = pruneCount; ridx < collisionsCount; ++ridx)
            {
                const uint32_t pidx = collisions[ridx];
                remains.push_back(pidx);
            }
            collisions.clear();
            sumHits = 0;
            for (uint32_t pidx : remains)
            {
                const physx::PxBounds3 bound = boundsData[pidx];
                // XXX see above note on PhysX overlap call.
                physx::PxBoxGeometry box(0.5f * (bound.maximum - bound.minimum));
                physx::PxTransform transform(0.5f * (bound.maximum + bound.minimum));

                OverlapData overlapData;
                bvh->overlap(box, transform, overlapData);
                if (overlapData.m_hitsCount > 1)
                {
                    sumHits += overlapData.m_hitsCount;
                    collisions.push_back(pidx);
                }
            }
            collisionsCount = (uint32_t)collisions.size();
        }

        uint32_t pruneCount = (uint32_t)prunes.size();
        if (pruneCount != 0)
        {
            auto pruneOutputVec3 = [&](std::vector<vec3f>& output)
            {
                uint32_t pidx = 0;
                auto itEnd = std::remove_if(output.begin() + pointsBegin, output.end(),
                                            [&](const vec3f& p) { return (prunes.find(pidx++) != prunes.end()); });
                output.erase(itEnd, output.end());
            };

            pruneOutputVec3(outputPoints.points);
            pruneOutputVec3(outputPoints.normals);
            pruneOutputVec3(outputPoints.tangents);
            pruneOutputVec3(outputPoints.binormals);
            pruneOutputVec3(outputPoints.rotations);
            pruneOutputVec3(outputPoints.scales);

            uint32_t pidx = 0;
            auto itEnd =
                std::remove_if(outputPoints.objectIndices.begin() + pointsBegin, outputPoints.objectIndices.end(),
                               [&](const int objectIdx)
                               {
                                   if (prunes.find(pidx++) != prunes.end())
                                   {
                                       return true;
                                   }
                                   return false;
                               });
            outputPoints.objectIndices.erase(itEnd, outputPoints.objectIndices.end());
        }
        PX_RELEASE(bvh)
    }


    static void randomizeAttributes(
        std::mt19937_64& random, const PrototypeSettings& protoSettings, vec3f& rotation, vec3f& scale, vec3f& offset)
    {
        rotation = protoSettings.rotation;
        const vec3f& rotRnd = protoSettings.rotationRandom;
        vec3f rotRndSample;
        rotRndSample[0] = nextRandomFloat(random);
        rotRndSample[1] = nextRandomFloat(random);
        rotRndSample[2] = nextRandomFloat(random);
        if (rotRnd[0] > 0.001f)
        {
            rotation[0] += (rotRndSample[0] - 0.5f) * rotRnd[0];
        }
        if (rotRnd[1] > 0.001f)
        {
            rotation[1] += (rotRndSample[1] - 0.5f) * rotRnd[1];
        }
        if (rotRnd[2] > 0.001f)
        {
            rotation[2] += (rotRndSample[2] - 0.5f) * rotRnd[2];
        }

        scale = protoSettings.scale;
        const float sclRnd = protoSettings.scaleRandom;
        const float sclRndSample = nextRandomFloat(random);
        if (sclRnd <= -0.001f || sclRnd >= 0.001f)
        {
            float scl = (sclRndSample - 0.5f) * sclRnd;
            scale[0] += scl;
            scale[1] += scl;
            scale[2] += scl;
        }

        offset = protoSettings.offset;
        const float offsetRndSample = nextRandomFloat(random);
        offset += protoSettings.offsetRandom * (offsetRndSample - 0.5f) * 2.f;
    }

    using BoundsVec = std::pair<vec3f, vec3f>;
    static BoundsVec getBounds(const physx::PxTriangleMeshGeometry& geometry, const float loose = 0.05f)
    {
        const physx::PxBounds3 bounds = geometry.triangleMesh->getLocalBounds();
        vec3f bmin{ bounds.minimum.x, bounds.minimum.y, bounds.minimum.z };
        vec3f bmax{ bounds.maximum.x, bounds.maximum.y, bounds.maximum.z };
        bmin -= loose * (bmax - bmin);
        bmax += loose * (bmax - bmin);
        return { bmin, bmax };
    }

    static inline bool pointProjectInsideBounds(const omni::math::linalg::vec3f& point,
                                                const omni::math::linalg::vec3f& bmin,
                                                const omni::math::linalg::vec3f& bmax)
    {
        constexpr float distanceThreshold = 1E-4f;
        const vec3f dvec = bmax - bmin;
        // Only test the non-trivial bound dimensions
        const bool outsideDimensions =
            ((dvec[0] > distanceThreshold) && ((point[0] < bmin[0]) || (point[0] > bmax[0]))) ||
            ((dvec[1] > distanceThreshold) && ((point[1] < bmin[1]) || (point[1] > bmax[1]))) ||
            ((dvec[2] > distanceThreshold) && ((point[2] < bmin[2]) || (point[2] > bmax[2])));
        return !outsideDimensions;
    }


    static void scatterSurfaces(const int desiredPoints,
                                const int protoIndex,
                                std::mt19937_64& random,
                                const uint64_t combinedSeed,
                                const PrototypeSettings& protoSettings,
                                const BaseMeshes& bases,
                                const ScatterSources& scatterSources,
                                const std::vector<size_t>& addCrvIndices,
                                const std::vector<size_t>& subCrvIndices,
                                const std::vector<size_t>& addVolIndices,
                                const std::vector<size_t>& subVolIndices,
                                OutputPoints& outputPoints)
    {
        const auto& cdf = bases.triangleAreaSums;
        const auto& triIndices = bases.triIndices;
        const size_t trianglesCount = triIndices.size() / 3;
        const auto& points = bases.points;
        const size_t pointsCount = points.size();
        const auto& weights = bases.scatterWeights;
        const auto& normals = bases.normals;
        const auto& texcoords = bases.texcoords;
        const bool validTex = (texcoords.size() == triIndices.size());
        const auto& objectIndices = bases.objectIndices;

        auto regionTest = [&bases, &scatterSources, &addCrvIndices, &subCrvIndices, &addVolIndices,
                           &subVolIndices](const vec3f& point)
        {
            for (const size_t subCrv : subCrvIndices)
            {
                const ScatterSource& source = scatterSources[subCrv];
                BoundsVec bounds = getBounds(source.geometry);
                if (source.curvePathRegion)
                {
                    if (pointWithinCurvePath(point, source.points, source.pathKnots, source.curvePathWidth, s_iRamp,
                                             source.pathWidthRampPositions.size(), source.pathWidthRampPositions.data(),
                                             source.pathWidthRampValues.data(), source.pathWidthRampInterpolations.data()))
                        return false;
                }
                else
                {
                    if (pointProjectInsideBounds(point, bounds.first, bounds.second) &&
                        pointInMeshRegion(point, bases.geometry, scatterSources[subCrv].geometry, true))
                        return false;
                }
            }
            for (const size_t subVol : subVolIndices)
            {
                physx::PxU32 nearIndex;
                physx::PxVec3 nearPoint, normal;
                if (omni::genproc::IsPointWithinMesh(physx::PxVec3(point[0], point[1], point[2]),
                                                     scatterSources[subVol].geometry, nearIndex, nearPoint, normal))
                    return false;
            }
            if (addCrvIndices.empty() && addVolIndices.empty())
            {
                return true;
            }
            for (const size_t addCrv : addCrvIndices)
            {
                const ScatterSource& source = scatterSources[addCrv];
                BoundsVec bounds = getBounds(source.geometry);
                if (source.curvePathRegion)
                {
                    if (pointWithinCurvePath(point, source.points, source.pathKnots, source.curvePathWidth, s_iRamp,
                                             source.pathWidthRampPositions.size(), source.pathWidthRampPositions.data(),
                                             source.pathWidthRampValues.data(), source.pathWidthRampInterpolations.data()))
                        return true;
                }
                else
                {
                    if (pointProjectInsideBounds(point, bounds.first, bounds.second) &&
                        pointInMeshRegion(point, bases.geometry, scatterSources[addCrv].geometry, true))
                        return true;
                }
            }
            for (const size_t addVol : addVolIndices)
            {
                physx::PxU32 nearIndex;
                physx::PxVec3 nearPoint, normal;
                if (omni::genproc::IsPointWithinMesh(physx::PxVec3(point[0], point[1], point[2]),
                                                     scatterSources[addVol].geometry, nearIndex, nearPoint, normal))
                    return true;
            }
            return false;
        };

        // Find triangle candidates
        std::vector<bool> filteredTris(trianglesCount, true);
        if (!addCrvIndices.empty() || !addVolIndices.empty() || !subCrvIndices.empty() || !subVolIndices.empty())
        {
            const bool emptyAdditives = addCrvIndices.empty() && addVolIndices.empty();
            for (int ti = 0; ti < (int)trianglesCount; ++ti)
            {
                filteredTris[ti] = emptyAdditives;
                for (const size_t addCrv : addCrvIndices)
                {
                    const std ::vector<int>& filtered = scatterSources[addCrv].filteredTris;
                    if (std::binary_search(filtered.begin(), filtered.end(), ti))
                    {
                        filteredTris[ti] = true;
                        break;
                    }
                }
                if (!filteredTris[ti])
                {
                    for (const size_t addVol : addVolIndices)
                    {
                        const std ::vector<int>& filtered = scatterSources[addVol].filteredTris;
                        if (std::binary_search(filtered.begin(), filtered.end(), ti))
                        {
                            filteredTris[ti] = true;
                            break;
                        }
                    }
                }
                if (!filteredTris[ti])
                {
                    continue;
                }
                for (const size_t subCrv : subCrvIndices)
                {
                    const std ::vector<int>& filtered = scatterSources[subCrv].filteredTris;
                    if (std::binary_search(filtered.begin(), filtered.end(), ti))
                    {
                        filteredTris[ti] = false;
                        break;
                    }
                }
                if (filteredTris[ti])
                {
                    for (const size_t subVol : subVolIndices)
                    {
                        const std ::vector<int>& filtered = scatterSources[subVol].filteredTris;
                        if (std::binary_search(filtered.begin(), filtered.end(), ti))
                        {
                            filteredTris[ti] = false;
                            break;
                        }
                    }
                }
            }
        }

        std::vector<float> weightsRampValues(pointsCount, 1.f);
        const Ramp& weightsRamp = bases.weightsRamp;
        const float elevLow = bases.elevationLow;
        const float elevHigh = bases.elevationHigh;
        if (weightsRamp.keysCount > 0)
        {
            std::vector<float> normalizedElevations(pointsCount);
            for (size_t pi = 0; pi < pointsCount; ++pi)
            {
                normalizedElevations[pi] = (points[pi][1] - elevLow) / (elevHigh - elevLow);
            }
            s_iRamp->sampleFloatArray(pointsCount, weightsRampValues.data(), normalizedElevations.data(), 0,
                                      weightsRamp.keysCount, weightsRamp.positions, weightsRamp.values,
                                      weightsRamp.interpolations);
        }

        std::vector<float> triangleWeights;
        if (protoSettings.noiseModulation)
        {
            PerlinNoise perlin(random);
            triangleWeights.resize(trianglesCount);
            float sumWeights = 0.f;
            float sumNoisedWeights = 0.f;
            for (size_t ti = 0; ti < trianglesCount; ++ti)
            {
                if (!filteredTris[ti])
                    continue;
                const int vi0 = triIndices[ti * 3];
                const int vi1 = triIndices[ti * 3 + 1];
                const int vi2 = triIndices[ti * 3 + 2];
                const vec3f centroid = (points[vi0] + points[vi1] + points[vi2]) / 3.f;
                const float noise = perlin.evaluate(centroid);
                const float baseWeight = bases.hasWeights ? (weights[vi0] + weights[vi1] + weights[vi2]) / 3.f : 1.f;
                const float noisedWeight = std::pow(noise + baseWeight, protoSettings.noiseExponential);
                sumNoisedWeights += noisedWeight;
                sumWeights += baseWeight;
                triangleWeights[ti] = noisedWeight;
            }
            for (size_t ti = 0; ti < trianglesCount; ++ti)
            {
                if (!filteredTris[ti])
                    continue;
                const int vi0 = triIndices[ti * 3];
                const int vi1 = triIndices[ti * 3 + 1];
                const int vi2 = triIndices[ti * 3 + 2];
                triangleWeights[ti] = triangleWeights[ti] / sumNoisedWeights * sumWeights;
            }
            // Reseed to not affect the order shuffle and the probability
            random.seed(combinedSeed);
        }
        double sumValidArea = 0.0;
        double sumValidWeightedArea = 0.0;
        struct ValidTriangle
        {
            size_t index;
            double weightedArea;
            ValidTriangle(size_t idx, double area) : index(idx), weightedArea(area)
            {
            }
        };
        std::vector<ValidTriangle> validTriangles;
        validTriangles.reserve(trianglesCount);
        // Shuffle the orders to avoid the bias when reaching the desired points before iterating all the triangles.
        std::vector<uint32_t> triangleOrders(trianglesCount);
        std::iota(triangleOrders.begin(), triangleOrders.end(), 0u);
        simple_shuffle(triangleOrders.data(), triangleOrders.data() + trianglesCount, random);
        for (const uint32_t ti : triangleOrders)
        {
            if (!filteredTris[ti])
                continue;
            const double area = cdf[ti + 1] - cdf[ti];
            sumValidArea += area;
            const int vi0 = triIndices[ti * 3];
            const int vi1 = triIndices[ti * 3 + 1];
            const int vi2 = triIndices[ti * 3 + 2];
            const float w0 = weights[vi0] * weightsRampValues[vi0];
            const float w1 = weights[vi1] * weightsRampValues[vi1];
            const float w2 = weights[vi2] * weightsRampValues[vi2];
            const float weight =
                protoSettings.noiseModulation ? triangleWeights[ti] : (bases.hasWeights ? (w0 + w1 + w2) / 3.f : 1.f);
            const double weightedArea = weight * area;
            if (weightedArea > 0.f)
            {
                sumValidWeightedArea += weightedArea;
                validTriangles.emplace_back(ti, weightedArea);
            }
        }

        const double weightedRatio = sumValidWeightedArea / sumValidArea;
        const bool weightExceeds = weightedRatio > 1.0;
        const int totalExpectedPoints = weightExceeds ? desiredPoints : (int)(weightedRatio * desiredPoints);
        // Precalculate probability for better distribution.
        std::vector<float> probabilities(trianglesCount);
        for (float& prob : probabilities)
        {
            prob = nextRandomFloat(random);
        }

        std::uniform_int_distribution<int> uniIntDist(0, 2);
        int totalSucceeds = 0;
        float expectedPointsSum = 0.f;

        for (const ValidTriangle& triangle : validTriangles)
        {
            // Allow exceeding expected to avoid fighting before reaching the desired limit.
            if (totalSucceeds == desiredPoints)
                break;

            // Reseed for each triangle to avoid jittering caused by the weight change on other triangles.
            const size_t tIdx = triangle.index;
            random.seed(tIdx ^ combinedSeed);
            const size_t geoIdx = 3 * tIdx;
            const int vindices[] = { triIndices[geoIdx], triIndices[geoIdx + 1], triIndices[geoIdx + 2] };
            const float expectedPoints =
                weightExceeds ? (float)(triangle.weightedArea / sumValidWeightedArea * totalExpectedPoints) :
                                (float)(triangle.weightedArea / sumValidArea * desiredPoints);
            const float expectedFloor = std::floor(expectedPoints);
            const int adjustedPoints =
                (int)expectedFloor + ((expectedPoints - expectedFloor >= probabilities[tIdx]) ? 1 : 0);
            const int maxAttempts = adjustedPoints * 100;
            int attempts = 0;
            std::vector<PointSample> samples;
            while (attempts < maxAttempts && (int)samples.size() < adjustedPoints)
            {
                ++attempts;
                PointSample sample;
                uniformBarycentric(random, sample.u, sample.v);
                const vec3f& p0 = points[vindices[0]];
                const vec3f& p1 = points[vindices[1]];
                const vec3f& p2 = points[vindices[2]];
                sample.point = sampleTriangle(p0, p1, p2, sample.u, sample.v);
                randomizeAttributes(random, protoSettings, sample.rotation, sample.scale, sample.offset);
                sample.vindex = uniIntDist(random);
                if (regionTest(sample.point))
                {
                    samples.push_back(sample);
                }
            }

            const vec3f& n0 = normals[geoIdx];
            const vec3f& n1 = normals[geoIdx + 1];
            const vec3f& n2 = normals[geoIdx + 2];
            const Ramp& objectIndicesRamp = bases.objectIndicesRamp;
            for (int si = 0, samplesCount = (int)samples.size(); si < samplesCount; ++si)
            {
                const PointSample& sample = samples[si];

                int32_t objectIndex;
                if (bases.hasObjectIndices)
                {
                    int vObjIdx = objectIndices[vindices[sample.vindex]];
                    objectIndex = vObjIdx == -1 ? protoIndex : vObjIdx;
                }
                else if (objectIndicesRamp.keysCount > 0)
                {
                    const float rampPosition = (sample.point[1] - elevLow) / (elevHigh - elevLow);
                    const int rampProtoIndex = (int)s_iRamp->getFloatAtPositionFromData(
                        rampPosition, objectIndicesRamp.keysCount, objectIndicesRamp.positions,
                        objectIndicesRamp.values, objectIndicesRamp.interpolations);
                    objectIndex = rampProtoIndex >= 0 ? rampProtoIndex : protoIndex;
                }
                else
                {
                    objectIndex = protoIndex;
                }

                // Filter against texture
                if (validTex)
                {
                    if (!filterSampleWithTextures(bases, geoIdx, sample, objectIndex))
                    {
                        continue;
                    }
                }

                outputPoints.objectIndices.push_back(objectIndex);

                vec3f normal = sampleTriangle(n0, n1, n2, sample.u, sample.v).GetNormalized();
                vec3f tangent{ 1.f, 0.f, 0.f };
                vec3f binormal{ 0.f, 0.f, 1.f };
                if (validTex)
                {
                    calculateTangent(geoIdx, points, triIndices, texcoords, normal, tangent, binormal);
                }
                vec3f point =
                    sample.point + tangent * sample.offset[0] + normal * sample.offset[1] + binormal * sample.offset[2];

                outputPoints.points.push_back(point);
                outputPoints.normals.push_back(normal);
                outputPoints.tangents.push_back(tangent);
                outputPoints.binormals.push_back(binormal);
                outputPoints.rotations.push_back(sample.rotation);
                outputPoints.scales.push_back(sample.scale);

                ++totalSucceeds;
                if (totalSucceeds == desiredPoints)
                    break;
            }
        }
    }

    static void scatterVolumes(const int desiredPoints,
                               const int protoIndex,
                               const PrototypeSettings& protoSettings,
                               std::mt19937_64& random,
                               const ScatterSources& scatterSources,
                               const std::vector<size_t>& addVolIndices,
                               const std::vector<size_t>& subVolIndices,
                               OutputPoints& outputPoints)
    {
        double volSum = 0.0;
        for (const size_t volAdd : addVolIndices)
        {
            volSum += scatterSources[volAdd].boundVolume;
        }
        int succeeds = 0;
        static const physx::PxTransform s_identityPose = physx::PxTransform(physx::PxIdentity);

        for (const size_t volAdd : addVolIndices)
        {
            const ScatterSource& addVolSrc = scatterSources[volAdd];
            const std::vector<vec3f>& points = addVolSrc.points;
            const std::vector<vec3f>& normals = addVolSrc.normals;
            const std::vector<int>& triIndices = addVolSrc.triIndices;
            const std::vector<vec2f>& texcoords = addVolSrc.texcoords;
            const bool validTex = (texcoords.size() == triIndices.size());
            const physx::PxTriangleMeshGeometry& geometry = addVolSrc.geometry;
            // Distribute the desired points to the additive volumes proportionally
            int volDesiredPoint = (int)((desiredPoints - succeeds) * (addVolSrc.boundVolume / volSum));
            volSum -= addVolSrc.boundVolume;
            physx::PxBounds3 meshBounds;
            physx::PxGeometryQuery::computeGeomBounds(meshBounds, geometry, s_identityPose);
            const physx::PxU32* mapping = geometry.triangleMesh->getTrianglesRemap();

            const int maxAttempts = 100 * volDesiredPoint;
            int volSucceeds = 0;
            int attempts = 0;
            auto regionTest = [&geometry, &scatterSources, &subVolIndices](const physx::PxVec3& point)
            {
                for (const size_t subVol : subVolIndices)
                {
                    physx::PxU32 nearIndex;
                    physx::PxVec3 nearPoint, normal;
                    if (omni::genproc::IsPointWithinMesh(
                            point, scatterSources[subVol].geometry, nearIndex, nearPoint, normal))
                    {
                        return false;
                    }
                }
                return true;
            };
            while (volSucceeds < volDesiredPoint && attempts < maxAttempts)
            {
                ++attempts;
                const float x = randomFloatBetween(random, meshBounds.minimum.x, meshBounds.maximum.x);
                const float y = randomFloatBetween(random, meshBounds.minimum.y, meshBounds.maximum.y);
                const float z = randomFloatBetween(random, meshBounds.minimum.z, meshBounds.maximum.z);
                physx::PxU32 nearIndex;
                physx::PxVec3 nearPoint, normal;
                physx::PxVec3 physxPoint{ x, y, z };

                vec3f rotation;
                vec3f scale;
                vec3f offset;
                randomizeAttributes(random, protoSettings, rotation, scale, offset);
                if (omni::genproc::IsPointWithinMesh(physxPoint, geometry, nearIndex, nearPoint, normal) &&
                    regionTest(physxPoint))
                {
                    ++succeeds;
                    ++volSucceeds;
                    const uint32_t geoIdx = mapping[nearIndex] * 3;
                    const uint32_t v0 = triIndices[geoIdx];
                    const uint32_t v1 = triIndices[geoIdx + 1];
                    const uint32_t v2 = triIndices[geoIdx + 2];
                    float u, v;
                    calculateBarycentric(
                        points[v0], points[v1], points[v2], vec3f{ nearPoint.x, nearPoint.y, nearPoint.z }, u, v);

                    const vec3f& n0 = normals[geoIdx];
                    const vec3f& n1 = normals[geoIdx + 1];
                    const vec3f& n2 = normals[geoIdx + 2];
                    vec3f normal = sampleTriangle(n0, n1, n2, u, v);
                    normal.Normalize();
                    vec3f tangent{ 1.f, 0.f, 0.f };
                    vec3f binormal{ 0.f, 0.f, 1.f };
                    if (validTex)
                    {
                        calculateTangent(geoIdx, points, triIndices, texcoords, normal, tangent, binormal);
                    }
                    vec3f point = vec3f{ x, y, z } + tangent * offset[0] + normal * offset[1] + binormal * offset[2];

                    outputPoints.points.push_back(point);
                    outputPoints.normals.push_back(normal);
                    outputPoints.tangents.push_back(tangent);
                    outputPoints.binormals.push_back(binormal);
                    outputPoints.rotations.push_back(rotation);
                    outputPoints.scales.push_back(scale);
                    outputPoints.objectIndices.push_back(protoIndex);
                }
            }
        }
    }

    static void scatterBoth(const int desiredPoints,
                            const int protoIndex,
                            std::mt19937_64& random,
                            const uint64_t combinedSeed,
                            const PrototypeSettings& protoSettings,
                            const BaseMeshes& bases,
                            const ScatterSources& scatterSources,
                            const std::vector<size_t>& addCrvIndices,
                            const std::vector<size_t>& subCrvIndices,
                            const std::vector<size_t>& addVolIndices,
                            const std::vector<size_t>& subVolIndices,
                            OutputPoints& outputPoints)
    {
        const int surfaceDesiredPoints = desiredPoints / 2;
        scatterSurfaces(surfaceDesiredPoints, protoIndex, random, combinedSeed, protoSettings, bases, scatterSources,
                        addCrvIndices, subCrvIndices, {}, {}, outputPoints);
        // Reset seed to avoid jittering from the change of surface mode
        random.seed(combinedSeed);
        const int volumeDesiredPoints = desiredPoints - surfaceDesiredPoints;

        const std::vector<vec3f>& points = bases.points;
        const std::vector<vec3f>& normals = bases.normals;
        const std::vector<int>& triIndices = bases.triIndices;
        const std::vector<vec2f>& texcoords = bases.texcoords;
        const bool validTex = (texcoords.size() == triIndices.size());
        const physx::PxTriangleMeshGeometry& geometry = bases.geometry;
        static const physx::PxTransform s_identityPose = physx::PxTransform(physx::PxIdentity);
        physx::PxBounds3 meshBounds;
        physx::PxGeometryQuery::computeGeomBounds(meshBounds, geometry, s_identityPose);
        const physx::PxU32* mapping = geometry.triangleMesh->getTrianglesRemap();

        const int maxAttempts = 100 * volumeDesiredPoints;
        int succeeds = 0;
        int attempts = 0;
        auto regionTest = [&geometry, &scatterSources, &addVolIndices, &subVolIndices](const physx::PxVec3& point)
        {
            bool insideAdditive = false;
            for (const size_t addVol : addVolIndices)
            {
                physx::PxU32 nearIndex;
                physx::PxVec3 nearPoint, normal;
                if (omni::genproc::IsPointWithinMesh(point, scatterSources[addVol].geometry, nearIndex, nearPoint, normal))
                {
                    insideAdditive = true;
                }
            }
            if (!insideAdditive)
            {
                return false;
            }
            for (const size_t subVol : subVolIndices)
            {
                physx::PxU32 nearIndex;
                physx::PxVec3 nearPoint, normal;
                if (omni::genproc::IsPointWithinMesh(point, scatterSources[subVol].geometry, nearIndex, nearPoint, normal))
                {
                    return false;
                }
            }
            return true;
        };
        while (succeeds < volumeDesiredPoints && attempts < maxAttempts)
        {
            ++attempts;
            const float x = randomFloatBetween(random, meshBounds.minimum.x, meshBounds.maximum.x);
            const float y = randomFloatBetween(random, meshBounds.minimum.y, meshBounds.maximum.y);
            const float z = randomFloatBetween(random, meshBounds.minimum.z, meshBounds.maximum.z);
            physx::PxU32 nearIndex;
            physx::PxVec3 nearPoint, normal;
            physx::PxVec3 physxPoint{ x, y, z };

            vec3f rotation;
            vec3f scale;
            vec3f offset;
            randomizeAttributes(random, protoSettings, rotation, scale, offset);
            if (omni::genproc::IsPointWithinMesh(physxPoint, geometry, nearIndex, nearPoint, normal) &&
                regionTest(physxPoint))
            {
                ++succeeds;
                const uint32_t geoIdx = mapping[nearIndex] * 3;
                const uint32_t v0 = triIndices[geoIdx];
                const uint32_t v1 = triIndices[geoIdx + 1];
                const uint32_t v2 = triIndices[geoIdx + 2];
                float u, v;
                calculateBarycentric(
                    points[v0], points[v1], points[v2], vec3f{ nearPoint.x, nearPoint.y, nearPoint.z }, u, v);

                const vec3f& n0 = normals[geoIdx];
                const vec3f& n1 = normals[geoIdx + 1];
                const vec3f& n2 = normals[geoIdx + 2];
                vec3f normal = sampleTriangle(n0, n1, n2, u, v);
                normal.Normalize();
                vec3f tangent{ 1.f, 0.f, 0.f };
                vec3f binormal{ 0.f, 0.f, 1.f };
                if (validTex)
                {
                    calculateTangent(geoIdx, points, triIndices, texcoords, normal, tangent, binormal);
                }
                vec3f point = vec3f{ x, y, z } + tangent * offset[0] + normal * offset[1] + binormal * offset[2];

                outputPoints.points.push_back(point);
                outputPoints.normals.push_back(normal);
                outputPoints.tangents.push_back(tangent);
                outputPoints.binormals.push_back(binormal);
                outputPoints.rotations.push_back(rotation);
                outputPoints.scales.push_back(scale);
                outputPoints.objectIndices.push_back(protoIndex);
            }
        }
    }

    static pxr::UsdPrimVector getCameraPaths(const pxr::UsdStageWeakPtr stage, const pxr::UsdPrim& thisPrim)
    {
        pxr::UsdPrimVector cameraPrims;
        const pxr::UsdRelationship cameraRelationship = thisPrim.GetRelationship(pxr::TfToken("inputs:camera"));
        pxr::SdfPathVector importPaths;
        if (cameraRelationship)
        {
            cameraRelationship.GetTargets(&importPaths);
        }

        for (const pxr::SdfPath& importPath : importPaths)
        {
            const pxr::SdfPath primPath = importPath.GetParentPath();
            const pxr::UsdPrim importPrim = stage->GetPrimAtPath(primPath);
            const pxr::UsdRelationship primRelationship = importPrim.GetRelationship(pxr::TfToken("inputs:prim"));
            if (primRelationship)
            {
                pxr::SdfPathVector primPaths;
                primRelationship.GetTargets(&primPaths);

                for (const pxr::SdfPath& primPath : primPaths)
                {
                    pxr::UsdPrim prim = stage->GetPrimAtPath(primPath);
                    if (prim.IsValid() && prim.IsA<pxr::UsdGeomCamera>())
                    {
                        cameraPrims.push_back(prim);
                    }
                }
            }
        }

        return cameraPrims;
    }

    static void filterPointsWithCamera(OgnScatterPointsGroupDatabase& db,
                                       const pxr::UsdPrim& thisPrim,
                                       OutputPoints& outputPoints,
                                       std::vector<uint64_t>& validIndices)
    {
        const auto stage = thisPrim.GetStage();
        pxr::UsdPrimVector cameraPrims = getCameraPaths(stage, thisPrim);
        auto& points = outputPoints.points;
        const size_t pointsCount = points.size();
        validIndices.reserve(pointsCount);

        const double currentUsdTimecode = db.inputs.usdTimecode();
        const double frustumOffset = db.inputs.frustumOffset();

        std::vector<pxr::GfFrustum> frustums;
        frustums.reserve(cameraPrims.size());
        for (const auto& cameraPrim : cameraPrims)
        {
            pxr::UsdGeomCamera usdCamera{ cameraPrim };
            const pxr::GfCamera camera = usdCamera.GetCamera(currentUsdTimecode);
            pxr::GfFrustum frustum = camera.GetFrustum();
            pxr::GfRange2d fWindow = frustum.GetWindow();
            pxr::GfVec2d fWindowMin = fWindow.GetMin();
            fWindowMin[0] -= frustumOffset;
            fWindowMin[1] -= frustumOffset;
            fWindow.SetMin(fWindowMin);
            pxr::GfVec2d fWindowMax = fWindow.GetMax();
            fWindowMax[0] += frustumOffset;
            fWindowMax[1] += frustumOffset;
            fWindow.SetMax(fWindowMax);
            frustum.SetWindow(fWindow);
            frustums.push_back(frustum);
        }

        for (size_t pIdx = 0; pIdx < pointsCount; ++pIdx)
        {
            const pxr::GfVec3d gfPoint{ points[pIdx][0], points[pIdx][1], points[pIdx][2] };
            for (const auto& frustum : frustums)
            {
                if (frustum.Intersects(gfPoint))
                {
                    validIndices.push_back(pIdx);
                    break;
                }
            }
        }
    }

    static void repeatUV(float& u, float& v)
    {
        u = u - floor(u);
        v = v - floor(v);
    }

    template <typename T>
    static bool shouldAccept(const uint8_t* pixel,
                             const uint8_t componentCount,
                             const SamplingChannel channel,
                             const bool additive)
    {
        if (static_cast<int32_t>(channel) >= componentCount)
        {
            // channel doesn't exit, accept anyway
            return true;
        }

        const T* pixelChannel = reinterpret_cast<const T*>(pixel) + static_cast<int32_t>(channel);


        if (additive)
        {
            // Accept the pixel if non-zero
            return *pixelChannel != 0;
        }
        else
        {
            // subtractive, accept the pixel if zero
            return *pixelChannel == 0;
        }

        return true;
    }

    static bool filterSampleWithTextures(const TextureFilter& filter,
                                         const BaseMeshes& bases,
                                         const size_t geoIdx,
                                         const PointSample& sample,
                                         const int32_t protoIndex)
    {
        bool accept = true;

        // If filter has specified the object/prototype index it applies to, check current index and only apply
        // filter if matches.
        if (!filter.objectIndices.empty() && filter.objectIndices.find(protoIndex) == filter.objectIndices.end())
        {
            return accept;
        }

        // bad config that trying to sample a texture out of boundary
        if (filter.textureIndex >= bases.textures.size())
        {
            return accept;
        }

        auto& tex = bases.textures[filter.textureIndex];
        // the texture can be invalid if loaded from a bad file path
        if (!tex)
        {
            return accept;
        }

        const auto& texcoords = bases.texcoords;
        const auto& w0 = texcoords[geoIdx];
        const auto& w1 = texcoords[geoIdx + 1];
        const auto& w2 = texcoords[geoIdx + 2];

        vec2f texcoord = sampleTriangle(w0, w1, w2, sample.u, sample.v);
        repeatUV(texcoord[0], texcoord[1]);

        uint32_t x = (uint32_t)(tex->width * texcoord[0]); // TODO interpolation
        uint32_t y = (uint32_t)(tex->height * (1.f - texcoord[1]));

        // Since for now the texture filter only checks for 0 or non-0, that signed vs unsigned, int vs float (e.g.
        // interpretation) doesn't matter, 0 is alway 0.
        // revisit this when more complicated filtering is needed and we should load interpretation
        // TODO BGRA order?
        const uint8_t* pixel = tex->data + ((tex->width * y + x) * tex->bitDepth / 8 * tex->componentCount);

        switch (tex->bitDepth)
        {
        case 8:
            accept = shouldAccept<uint8_t>(pixel, tex->componentCount, filter.channel, filter.additive);
            break;
        case 16:
            accept = shouldAccept<uint16_t>(pixel, tex->componentCount, filter.channel, filter.additive);
            break;
        case 32:
            accept = shouldAccept<uint32_t>(pixel, tex->componentCount, filter.channel, filter.additive);
            break;
        }

        return accept;
    }

    static bool filterSampleWithTextures(const BaseMeshes& bases,
                                         const size_t geoIdx,
                                         const PointSample& sample,
                                         const int32_t protoIndex)
    {
        bool accept = true;
        size_t meshIndex = bases.meshIndices[geoIdx];

        // First, check if we have universal filters (baseIndex == -1)
        // Then, check if we have filters specific for the base this sample is on
        const int32_t indicesArray[2] = { -1, (int32_t)meshIndex };
        for (size_t i = 0; i < 2; i++)
        {
            const auto filtersEntry = bases.textureFilters.find(indicesArray[i]);
            if (filtersEntry != bases.textureFilters.end())
            {
                const auto& filters = filtersEntry->second;
                for (const TextureFilter& filter : filters)
                {
                    accept &= filterSampleWithTextures(filter, bases, geoIdx, sample, protoIndex);
                }
            }
        }

        return accept;
    }

    static void outputToBundle(OgnScatterPointsGroupDatabase& db,
                               const OutputPoints& outputPoints,
                               const bool filteredWithCamera,
                               std::vector<uint64_t>& validIndices)
    {
        const GraphContextObj& context = db.abi_context();

        BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
        outputPrims.clearContents();

        const size_t validOutputsCount = filteredWithCamera ? validIndices.size() : outputPoints.points.size();
        BundlePrim& outputPrim = outputPrims.getCommonAttrs();

        BundleAttrib* outputPointsAttr = outputPrim.addAttr(
            db.tokens.points, Type(BaseDataType::eFloat, 3, 1, AttributeRole::ePosition), validOutputsCount);
        vec3f* points = outputPointsAttr->getData<vec3f>();

        BundleAttrib* outputRotationsAttr = outputPrim.addAttr(
            db.tokens.rotations, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eNone), validOutputsCount);
        vec3f* rotations = outputRotationsAttr->getData<vec3f>();

        BundleAttrib* outputScalesAttr = outputPrim.addAttr(
            db.tokens.scales, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eNone), validOutputsCount);
        vec3f* scales = outputScalesAttr->getData<vec3f>();

        BundleAttrib* outputObjectIndicesAttr = outputPrim.addAttr(
            db.tokens.objectIndices, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone), validOutputsCount);
        int* objectIndices = outputObjectIndicesAttr->getData<int>();

        BundleAttrib* outputNormalsAttr = outputPrim.addAttr(
            db.tokens.normals, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eNormal), validOutputsCount);
        vec3f* normals = outputNormalsAttr->getData<vec3f>();

        BundleAttrib* outputTangentsAttr = outputPrim.addAttr(
            db.tokens.tangents, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eVector), validOutputsCount);
        vec3f* tangents = outputTangentsAttr->getData<vec3f>();

        BundleAttrib* outputBinormalsAttr = outputPrim.addAttr(
            db.tokens.binormals, Type(BaseDataType::eFloat, 3, 1, AttributeRole::eVector), validOutputsCount);
        vec3f* binormals = outputBinormalsAttr->getData<vec3f>();

        if (filteredWithCamera)
        {
            for (uint64_t idx = 0; idx < validOutputsCount; ++idx)
            {
                const uint64_t validIdx = validIndices[idx];
                points[idx] = outputPoints.points[validIdx];
                rotations[idx] = outputPoints.rotations[validIdx];
                scales[idx] = outputPoints.scales[validIdx];
                objectIndices[idx] = outputPoints.objectIndices[validIdx];
                normals[idx] = outputPoints.normals[validIdx];
                tangents[idx] = outputPoints.tangents[validIdx];
                binormals[idx] = outputPoints.binormals[validIdx];
            }
        }
        else
        {
            memcpy(points, outputPoints.points.data(), validOutputsCount * sizeof(vec3f));
            memcpy(rotations, outputPoints.rotations.data(), validOutputsCount * sizeof(vec3f));
            memcpy(scales, outputPoints.scales.data(), validOutputsCount * sizeof(vec3f));
            memcpy(objectIndices, outputPoints.objectIndices.data(), validOutputsCount * sizeof(int));
            memcpy(normals, outputPoints.normals.data(), validOutputsCount * sizeof(vec3f));
            memcpy(tangents, outputPoints.tangents.data(), validOutputsCount * sizeof(vec3f));
            memcpy(binormals, outputPoints.binormals.data(), validOutputsCount * sizeof(vec3f));
        }
    }

    static InputChangeRecord isInputsChanged(OgnScatterPointsGroupDatabase& db)
    {
        InputChangeRecord result;
        const GraphContextObj& context = db.abi_context();
        result.paramChanged = db.inputs.active() != db.state.prevActive() ||
                              db.inputs.curveStepsPerSegment() != db.state.prevCurveStepsPerSegment() ||
                              db.inputs.filterUsingCamera() != db.state.prevFilterUsingCamera() ||
                              db.inputs.frustumOffset() != db.state.prevFrustumOffset() ||
                              db.inputs.playbackEvaluation() != db.state.prevPlaybackEvaluation() ||
                              db.inputs.playbackStartFrame() != db.state.prevPlaybackStartFrame() ||
                              db.inputs.randomSeed() != db.state.prevRandomSeed() ||
                              db.inputs.time() != db.state.prevTime() ||
                              db.inputs.usdTimecode() != db.state.prevUsdTimecode();
        if (result.paramChanged)
        {
            db.state.prevActive() = db.inputs.active();
            db.state.prevCurveStepsPerSegment() = db.inputs.curveStepsPerSegment();
            db.state.prevFilterUsingCamera() = db.inputs.filterUsingCamera();
            db.state.prevFrustumOffset() = db.inputs.frustumOffset();
            db.state.prevPlaybackEvaluation() = db.inputs.playbackEvaluation();
            db.state.prevPlaybackStartFrame() = db.inputs.playbackStartFrame();
            db.state.prevRandomSeed() = db.inputs.randomSeed();
            db.state.prevTime() = db.inputs.time();
            db.state.prevUsdTimecode() = db.inputs.usdTimecode();
        }

        auto rampFloatsChanged = [](const ogn::ArrayInput<const float, ogn::kCpu>::array_t& rampArray,
                                    ogn::ArrayState<float, ogn::kCpu>::array_t& prevArray)
        {
            bool changed = rampArray.size() != prevArray.size() ||
                           !std::equal(rampArray.begin(), rampArray.end(), prevArray.begin());
            if (changed)
                prevArray = rampArray;
            return changed;
        };
        auto rampIntsChanged = [](const ogn::ArrayInput<const int, ogn::kCpu>::array_t& rampArray,
                                  ogn::ArrayState<int, ogn::kCpu>::array_t& prevArray)
        {
            bool changed = rampArray.size() != prevArray.size() ||
                           !std::equal(rampArray.begin(), rampArray.end(), prevArray.begin());
            if (changed)
                prevArray = rampArray;
            return changed;
        };
        const auto& weightRampPositions = db.inputs.weightsRampPositions();
        const auto& weightRampValues = db.inputs.weightsRampValues();
        const auto& weightRampInterpolations = db.inputs.weightsRampInterpolations();
        CARB_ASSERT(weightRampPositions.size() == weightRampValues.size() &&
                    weightRampValues.size() == weightRampInterpolations.size());
        result.rampChanged |= rampFloatsChanged(weightRampPositions, db.state.prevWeightsRampPositions());
        result.rampChanged |= rampFloatsChanged(weightRampValues, db.state.prevWeightsRampValues());
        result.rampChanged |= rampIntsChanged(weightRampInterpolations, db.state.prevWeightsRampInterpolations());

        const auto& objectIndicesRampPositions = db.inputs.objectIndicesRampPositions();
        const auto& objectIndicesRampValues = db.inputs.objectIndicesRampValues();
        const auto& objectIndicesRampInterpolations = db.inputs.objectIndicesRampInterpolations();
        CARB_ASSERT(objectIndicesRampPositions.size() == objectIndicesRampValues.size() &&
                    objectIndicesRampValues.size() == objectIndicesRampInterpolations.size());
        result.rampChanged |= rampFloatsChanged(objectIndicesRampPositions, db.state.prevObjectIndicesRampPositions());
        result.rampChanged |= rampFloatsChanged(objectIndicesRampValues, db.state.prevObjectIndicesRampValues());
        result.rampChanged |=
            rampIntsChanged(objectIndicesRampInterpolations, db.state.prevObjectIndicesRampInterpolations());

        if (db.inputs.has_curveSources())
        {
            ConstBundlePrims curvePrims(context, db.inputs.curveSources().abi_bundleHandle());
            if (curvePrims.getPrimCount() > 0)
            {
                result.curvesChanged = result.curvesChanged || db.inputs.curveSources.changes().hasChanged();
            }
        }

        if (db.inputs.has_camera())
        {
            ConstBundlePrims cameraPrim(context, db.inputs.camera().abi_bundleHandle());
            if (cameraPrim.getPrimCount() > 0)
            {
                result.cameraChanged = result.cameraChanged || db.inputs.camera.changes().hasChanged();
            }
        }

        if (db.inputs.has_textures())
        {
            result.texturesChanged = result.texturesChanged || db.inputs.textures.changes().hasChanged();
        }

        {
            ConstBundlePrims groupPrims(context, db.inputs.groups().abi_bundleHandle());
            if (groupPrims.getPrimCount() > 0)
            {
                result.groupsChanged = result.groupsChanged || db.inputs.groups.changes().hasChanged();
            }
        }

        if (db.inputs.has_bases())
        {
            ConstBundlePrims baseMeshPrims(context, db.inputs.bases().abi_bundleHandle());
            if (baseMeshPrims.getPrimCount() > 0)
            {
                result.basesChanged = result.basesChanged || db.inputs.bases.changes().hasChanged();
            }
        }

        if (db.inputs.has_volumeSources())
        {
            ConstBundlePrims volumePrims(context, db.inputs.volumeSources().abi_bundleHandle());
            if (volumePrims.getPrimCount() > 0)
            {
                result.volumesChanged = result.volumesChanged || db.inputs.volumeSources.changes().hasChanged();
            }
        }

        if (db.inputs.has_textureFilters())
        {
            ConstBundlePrims textureFilterPrims(context, db.inputs.textureFilters().abi_bundleHandle());
            result.textureFiltersChanged =
                result.textureFiltersChanged || db.inputs.textureFilters.changes().hasChanged();
        }

        return result;
    }

    static void validateRegions(OgnScatterPointsGroupDatabase& db, ScatterSources& scatterSource, const BaseMeshes& bases)
    {
        const GraphContextObj& context = db.abi_context();
        ConstBundlePrims baseMeshesHandle(context, db.inputs.bases().abi_bundleHandle());
        BundlePrims cachedCurveSources(context, db.state.cachedCurveSources().abi_bundleHandle());
        BundlePrims cachedVolumeSources(context, db.state.cachedVolumeSources().abi_bundleHandle());

        auto getTriBounds = [](const vec3f& v0, const vec3f& v1, const vec3f& v2) -> BoundsVec
        {
            vec3f bmin{
                std::min(std::min(v0[0], v1[0]), v2[0]),
                std::min(std::min(v0[1], v1[1]), v2[1]),
                std::min(std::min(v0[2], v1[2]), v2[2]),
            };
            vec3f bmax{
                std::max(std::max(v0[0], v1[0]), v2[0]),
                std::max(std::max(v0[1], v1[1]), v2[1]),
                std::max(std::max(v0[2], v1[2]), v2[2]),
            };
            return { bmin, bmax };
        };

        auto intersectBounds = [](const BoundsVec& a, const BoundsVec& b) -> int
        {
            constexpr float epsilon = 1.e-6f;
            int counts = 0;
            const vec3f& mina = a.first;
            const vec3f& minb = b.first;
            const vec3f& maxa = a.second;
            const vec3f& maxb = b.second;
            counts += ((mina[0] > maxb[0] + epsilon) || (minb[0] > maxa[0] + epsilon)) ? 0 : 1;
            counts += ((mina[1] > maxb[1] + epsilon) || (minb[1] > maxa[1] + epsilon)) ? 0 : 1;
            counts += ((mina[2] > maxb[2] + epsilon) || (minb[2] > maxa[2] + epsilon)) ? 0 : 1;
            return counts;
        };

        auto boundsContains = [](const BoundsVec& a, const BoundsVec& b) -> bool
        {
            constexpr float epsilon = 1.e-6f;
            const vec3f& mina = a.first;
            const vec3f& minb = b.first;
            const vec3f& maxa = a.second;
            const vec3f& maxb = b.second;
            return (mina[0] + epsilon < minb[0]) && (maxa[0] > maxb[0] + epsilon) && (mina[1] + epsilon < minb[1]) &&
                   (maxa[1] > maxb[1] + epsilon) && (mina[2] + epsilon < minb[2]) && (maxa[2] > maxb[2] + epsilon);
        };

        auto validateCurve = [getTriBounds, intersectBounds, boundsContains, &bases](ScatterSource& scatterSource)
        {
            const std::vector<vec3f>& points = bases.points;
            const size_t pointsCount = points.size();
            const std::vector<int>& triIndices = bases.triIndices;
            const int trisCount = (int)triIndices.size() / 3;
            std::vector<int>& filteredTris = scatterSource.filteredTris;
            filteredTris.reserve(trisCount);
            const BoundsVec srcBounds = getBounds(scatterSource.geometry);

            if (scatterSource.zoneSign == ZoneSign::eAdditive)
            {
                if (!scatterSource.curvePathRegion)
                {
                    std::vector<int> testedPoints(pointsCount, -1);
                    for (int ti = 0; ti < trisCount; ++ti)
                    {
                        for (int pi = 0; pi < 3; ++pi)
                        {
                            const size_t pIdx = triIndices[ti * 3 + pi];
                            const vec3f& point = points[pIdx];
                            if (testedPoints[pIdx] == -1)
                            {
                                testedPoints[pIdx] =
                                    (int)(pointProjectInsideBounds(point, srcBounds.first, srcBounds.second) &&
                                          pointInMeshRegion(point, bases.geometry, scatterSource.geometry, true));
                            }
                            if (testedPoints[pIdx] == 1)
                            {
                                filteredTris.push_back(ti);
                                break;
                            }
                        }
                    }
                }
                // If not able to find any candidate or the curve is used as a path, fall back to the intersect test.
                if (filteredTris.empty() || scatterSource.curvePathRegion)
                {
                    for (int ti = 0; ti < trisCount; ++ti)
                    {
                        const vec3f& v0 = points[triIndices[ti * 3]];
                        const vec3f& v1 = points[triIndices[ti * 3 + 1]];
                        const vec3f& v2 = points[triIndices[ti * 3 + 2]];
                        const BoundsVec triBounds = getTriBounds(v0, v1, v2);
                        const int intersectCounts = intersectBounds(triBounds, srcBounds);
                        if (intersectCounts > 0 &&
                            triangleProjectIntersectWithCurve(v0, v1, v2, scatterSource.controlPoints))
                        {
                            filteredTris.push_back(ti);
                        }
                    }
                }
            }
            else
            {
                std::vector<int> testedPoints(pointsCount, -1);
                // For subtractive source, a triangle with the contained bound and all the 3 vertices within is
                // included.
                if (scatterSource.curvePathRegion)
                {
                    for (int ti = 0; ti < trisCount; ++ti)
                    {
                        const vec3f& v0 = points[triIndices[ti * 3]];
                        const vec3f& v1 = points[triIndices[ti * 3 + 1]];
                        const vec3f& v2 = points[triIndices[ti * 3 + 2]];
                        const BoundsVec triBounds = getTriBounds(v0, v1, v2);
                        if (!boundsContains(srcBounds, triBounds))
                            continue;
                        bool allIn = true;
                        for (int pi = 0; pi < 3; ++pi)
                        {
                            const size_t pIdx = triIndices[ti * 3 + pi];
                            if (testedPoints[pIdx] == -1)
                            {
                                testedPoints[pIdx] = (int)pointWithinCurvePath(
                                    points[pIdx], scatterSource.points, scatterSource.pathKnots,
                                    scatterSource.curvePathWidth, s_iRamp, scatterSource.pathWidthRampPositions.size(),
                                    scatterSource.pathWidthRampPositions.data(), scatterSource.pathWidthRampValues.data(),
                                    scatterSource.pathWidthRampInterpolations.data());
                            }
                            if (testedPoints[pIdx] == 0)
                            {
                                allIn = false;
                                break;
                            }
                        }
                        if (allIn)
                        {
                            filteredTris.push_back(ti);
                        }
                    }
                }
                else
                {
                    // For subtractive region, a triangle with the bound intersected at least one dimension and all the
                    // 3 vertices within is included
                    for (int ti = 0; ti < trisCount; ++ti)
                    {
                        const vec3f& v0 = points[triIndices[ti * 3]];
                        const vec3f& v1 = points[triIndices[ti * 3 + 1]];
                        const vec3f& v2 = points[triIndices[ti * 3 + 2]];
                        const BoundsVec triBounds = getTriBounds(v0, v1, v2);
                        if (!intersectBounds(triBounds, srcBounds) == 0)
                            continue;
                        bool allIn = true;
                        for (int pi = 0; pi < 3; ++pi)
                        {
                            const size_t pIdx = triIndices[ti * 3 + pi];
                            const vec3f point = points[pIdx];
                            if (testedPoints[pIdx] == -1)
                            {
                                testedPoints[pIdx] =
                                    (int)(pointProjectInsideBounds(point, srcBounds.first, srcBounds.second) &&
                                          pointInMeshRegion(point, bases.geometry, scatterSource.geometry, true));
                            }
                            if (testedPoints[pIdx] == 0)
                            {
                                allIn = false;
                                break;
                            }
                        }
                        if (allIn)
                        {
                            filteredTris.push_back(ti);
                        }
                    }
                }
            }
        };

        auto validateVolume = [&bases](ScatterSource& scatterSource)
        {
            const std::vector<vec3f>& points = bases.points;
            const size_t pointsCount = points.size();
            const std::vector<int>& triIndices = bases.triIndices;
            const int trisCount = (int)triIndices.size() / 3;
            std::vector<int>& filteredTris = scatterSource.filteredTris;
            filteredTris.reserve(trisCount);
            std::vector<int> testedPoints(pointsCount, -1);

            if (scatterSource.zoneSign == ZoneSign::eAdditive)
            {
                // For the additive volume, a triangle with any vertex within is included
                for (int ti = 0; ti < trisCount; ++ti)
                {
                    for (int pi = 0; pi < 3; ++pi)
                    {
                        const size_t pIdx = triIndices[ti * 3 + pi];
                        const vec3f point = points[pIdx];
                        physx::PxU32 nearIndex;
                        physx::PxVec3 nearPoint, normal;
                        if (testedPoints[pIdx] == -1)
                        {
                            testedPoints[pIdx] = (int)omni::genproc::IsPointWithinMesh(
                                physx::PxVec3(point[0], point[1], point[2]), scatterSource.geometry, nearIndex,
                                nearPoint, normal);
                        }
                        if (testedPoints[pIdx] == 1)
                        {
                            filteredTris.push_back(ti);
                            break;
                        }
                    }
                }
            }
            else
            {
                // For the subtractive volume, a triangle with all 3 vertices within is included
                for (int ti = 0; ti < trisCount; ++ti)
                {
                    bool allIn = true;
                    for (int pi = 0; pi < 3; ++pi)
                    {
                        const size_t pIdx = triIndices[ti * 3 + pi];
                        const vec3f point = points[pIdx];
                        physx::PxU32 nearIndex;
                        physx::PxVec3 nearPoint, normal;
                        if (testedPoints[pIdx] == -1)
                        {
                            testedPoints[pIdx] = (int)omni::genproc::IsPointWithinMesh(
                                physx::PxVec3(point[0], point[1], point[2]), scatterSource.geometry, nearIndex,
                                nearPoint, normal);
                        }
                        if (testedPoints[pIdx] == 0)
                        {
                            allIn = false;
                            break;
                        }
                    }
                    if (allIn)
                    {
                        filteredTris.push_back(ti);
                    }
                }
            }
        };

        for (ScatterSource& scatterSource : scatterSource)
        {
            if (scatterSource.cachedPrimIndex == -1)
                continue;
            const bool isCurveSource = scatterSource.sourceType == SourceType::eCurve;
            BundlePrim* cachedPrim = isCurveSource ? cachedCurveSources.getPrim(scatterSource.cachedPrimIndex) :
                                                     cachedVolumeSources.getPrim(scatterSource.cachedPrimIndex);
            if (cachedPrim == nullptr)
                continue;
            BundleAttrib* cachedFilteredTrisAttr = cachedPrim->getAttr(db.tokens.filteredTris);
            std::vector<int>& filteredTris = scatterSource.filteredTris;

            if (scatterSource.geometryDirty || cachedFilteredTrisAttr == nullptr || bases.geometryDirty)
            {
                if (isCurveSource)
                {
                    validateCurve(scatterSource);
                }
                else
                {
                    validateVolume(scatterSource);
                }
                const size_t filteredTrisCount = filteredTris.size();
                cachedFilteredTrisAttr = cachedPrim->addAttr(
                    db.tokens.filteredTris, Type(BaseDataType::eInt, 1, 1, AttributeRole::eNone), filteredTrisCount);
                if (cachedFilteredTrisAttr)
                {
                    memcpy(cachedFilteredTrisAttr->getData<int>(), filteredTris.data(), filteredTrisCount * sizeof(int));
                }
            }
            else
            {
                int* cachedFilteredTris = cachedFilteredTrisAttr->getData<int>();
                const size_t filteredTrisCount = cachedFilteredTrisAttr->size();
                filteredTris.resize(filteredTrisCount);
                memcpy(filteredTris.data(), cachedFilteredTris, filteredTrisCount * sizeof(int));
            }
        }
    }

    static Prototypes getScatterPrototypes(const pxr::UsdPrim& prim)
    {
        pxr::UsdRelationship prototypesRel = prim.GetRelationship(pxr::TfToken("inputs:prototypes"));
        pxr::SdfPathVector prototypePaths;
        prototypesRel.GetTargets(&prototypePaths);

        const size_t prototypesCount = prototypePaths.size();
        Prototypes prototypes(prototypesCount);

        const auto stage = prim.GetStage();
        const pxr::UsdTimeCode defaultTime = pxr::UsdTimeCode::Default();
        pxr::UsdGeomXformCache xformCache(defaultTime);
        const pxr::TfTokenVector purposes = { pxr::UsdGeomTokens->default_, pxr::UsdGeomTokens->proxy };
        pxr::UsdGeomBBoxCache bboxCache(defaultTime, purposes, true);

        for (size_t i = 0; i < prototypesCount; ++i)
        {
            Prototype& prototype = prototypes[i];
            prototype.path = prototypePaths[i];
            pxr::UsdPrim protoPrim = stage->GetPrimAtPath(prototype.path);
            if (protoPrim.IsValid())
            {
                const pxr::GfRange3d bbox = bboxCache.ComputeLocalBound(protoPrim).GetBox();
                prototype.boundMin = vec3f(safeCastToOmni(bbox.GetMin()));
                prototype.boundMax = vec3f(safeCastToOmni(bbox.GetMax()));
            }
            else
            {
                prototype.boundMin = vec3f(0.f);
                prototype.boundMax = vec3f(0.f);
            }
        }
        return prototypes;
    }

    static bool compute(OgnScatterPointsGroupDatabase& db)
    {
        auto& nodeObj = db.abi_node();
        const GraphContextObj& context = db.abi_context();
        const IGraphContext* const iContext = context.iContext;

        InputChangeRecord inputChangeRecord = isInputsChanged(db);
        if (!inputChangeRecord.hasAnyChange())
            return true;

        if (!db.inputs.active())
        {
            BundlePrims outputPrims(context, db.outputs.bundle().abi_bundleHandle());
            outputPrims.clearContents();
            return true;
        }

        OgnScatterPointsGroup& internalState = db.internalState<OgnScatterPointsGroup>();

        // random setup
        const auto& pbe = db.inputs.playbackEvaluation();
        const auto& pbsf = db.inputs.playbackStartFrame();
        const double currentUsdTimecode = db.inputs.usdTimecode();
        if (pbe && pbsf > currentUsdTimecode)
        {
            // Before or at the playback start frame,
            // and we don't need to worry about changes to camera prim
            return true;
        }
        std::mt19937_64 random;

        pxr::UsdPrim thisPrim = getUsdPrimFromNode(context, nodeObj);
        if (!thisPrim.IsValid())
            return false;

        Prototypes prototypes = getScatterPrototypes(thisPrim);
        ScatterGroups scatterGroups = getScatterGroups(db);

        ScatterSources scatterSources;
        PhysXMeshes sourceMeshes;
        initCurveSources(db, scatterSources, sourceMeshes);
        initVolumeSources(db, scatterSources, sourceMeshes);

        BaseMeshes& bases = internalState.baseMeshes;
        initBaseMeshes(db, bases, scatterSources, scatterGroups, inputChangeRecord);

        OutputPoints outputPoints;
        for (const auto& group : scatterGroups)
        {
            if (group.second.visible != 0)
                scatterForGroup(db, random, prototypes, group.second, bases, scatterSources, outputPoints);
        }
        const bool filteredWithCamera = db.inputs.filterUsingCamera() && db.inputs.has_camera();
        std::vector<uint64_t> validIndices;
        if (filteredWithCamera)
        {
            filterPointsWithCamera(db, thisPrim, outputPoints, validIndices);
        }

        outputToBundle(db, outputPoints, filteredWithCamera, validIndices);

        return true;
    }

    static void initialize(const GraphContextObj& contextObj, const NodeObj& nodeObj)
    {
        s_iRamp = carb::getFramework()->acquireInterface<omni::ramp::IRamp>();
    }

private:
    BaseMeshes baseMeshes;
};

REGISTER_OGN_NODE()
