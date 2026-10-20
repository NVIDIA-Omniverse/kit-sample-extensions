// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include <OgnArraySetByKeysDatabase.h>
#include <omni/graph/core/StringUtils.h>
#include <omni/graph/core/ogn/ComputeHelpers.h>
#include <carb/logging/Log.h>
#include <algorithm>
// clang-format on

namespace omni
{
namespace anim
{
namespace shared
{
using omni::graph::core::ogn::array;

// unnamed namespace to avoid multiple declaration when linking
namespace
{

template <typename BaseType>
bool tryComputeAssumingType(OgnArraySetByKeysDatabase& db)
{
    auto const inputArray = db.inputs.array().template get<BaseType[]>();
    auto const inputArrayOrig = db.inputs.arrayOrig().template get<BaseType[]>();
    auto const inputKeys = db.inputs.keys().template get<OgnToken[]>();
    auto const inputKeysOrig = *db.inputs.keysOrig().template get<OgnToken[]>();
    size_t const inputArraySize = db.inputs.array().size();
    size_t const inputArrayOrigSize = db.inputs.arrayOrig().size();
    size_t const inputKeysSize = inputKeys.size();
    size_t const inputKeysOrigSize = inputKeysOrig.size();
    auto outputArray = db.outputs.array().template get<BaseType[]>();

    if (!inputArray || !inputArrayOrig || !inputKeys)
        return false;

    size_t nb = std::min(inputArraySize, inputKeysSize);
    size_t nbOrig = std::min(inputArrayOrigSize, inputKeysOrigSize);

    (*outputArray).resize(inputArrayOrigSize);
    if (nb == 0 || nbOrig == 0)
        return true;

    memcpy(outputArray->data(), inputArrayOrig->data(), sizeof(BaseType) * inputArrayOrigSize);
    // in the future it would be nicer if we can store the mapping and reuse it

    for (size_t i = 0; i < nbOrig; i++)
    {
        // find the index of the keys
        auto it = std::find(inputKeys->begin(), inputKeys->end(), inputKeysOrig[i]);
        if (it != inputKeys->end())
        {
            const size_t index = static_cast<size_t>(it - inputKeys->begin());
            if (index < inputArraySize)
                memcpy(outputArray->data() + i, inputArray->data() + index, sizeof(BaseType));
        }
    }

    return true;
}
} // namespace

class OgnArraySetByKeys
{
public:
    static bool compute(OgnArraySetByKeysDatabase& db)
    {
        auto& inputType = db.inputs.array().type();
        auto& inputOrigType = db.inputs.arrayOrig().type();

        if (inputType != inputOrigType)
        {
            db.logWarning("Failed to resolve input types");
            return false;
        }

        try
        {
            switch (inputOrigType.baseType)
            {
                case BaseDataType::eBool:
                    return tryComputeAssumingType<bool>(db);
                case BaseDataType::eToken:
                    return tryComputeAssumingType<omni::graph::core::NameToken>(db);
                case BaseDataType::eDouble:
                    switch (inputOrigType.componentCount)
                    {
                        case 1:
                            return tryComputeAssumingType<double>(db);
                        case 2:
                            return tryComputeAssumingType<double[2]>(db);
                        case 3:
                            return tryComputeAssumingType<double[3]>(db);
                        case 4:
                            return tryComputeAssumingType<double[4]>(db);
                        case 9:
                            return tryComputeAssumingType<double[9]>(db);
                        case 16:
                            return tryComputeAssumingType<double[16]>(db);
                        default:
                            break;
                    }
                case BaseDataType::eFloat:
                    switch (inputOrigType.componentCount)
                    {
                        case 1:
                            return tryComputeAssumingType<float>(db);
                        case 2:
                            return tryComputeAssumingType<float[2]>(db);
                        case 3:
                            return tryComputeAssumingType<float[3]>(db);
                        case 4:
                            return tryComputeAssumingType<float[4]>(db);
                        default:
                            break;
                    }
                case BaseDataType::eHalf:
                    switch (inputOrigType.componentCount)
                    {
                        case 1:
                            return tryComputeAssumingType<pxr::GfHalf>(db);
                        case 2:
                            return tryComputeAssumingType<pxr::GfHalf[2]>(db);
                        case 3:
                            return tryComputeAssumingType<pxr::GfHalf[3]>(db);
                        case 4:
                            return tryComputeAssumingType<pxr::GfHalf[4]>(db);
                        default:
                            break;
                    }
                case BaseDataType::eInt:
                    switch (inputOrigType.componentCount)
                    {
                        case 1:
                            return tryComputeAssumingType<int32_t>(db);
                        case 2:
                            return tryComputeAssumingType<int32_t[2]>(db);
                        case 3:
                            return tryComputeAssumingType<int32_t[3]>(db);
                        case 4:
                            return tryComputeAssumingType<int32_t[4]>(db);
                        default:
                            break;
                    };
                case BaseDataType::eInt64:
                    return tryComputeAssumingType<int64_t>(db);
                case BaseDataType::eUChar:
                    return tryComputeAssumingType<unsigned char>(db);
                case BaseDataType::eUInt:
                    return tryComputeAssumingType<uint32_t>(db);
                case BaseDataType::eUInt64:
                    return tryComputeAssumingType<uint64_t>(db);
                default:
                    break;
            }

            db.logWarning("Failed to resolve input types");
        }
        catch (ogn::compute::InputError const& error)
        {
            db.logError(error.what());
        }
        return false;
    }

    static void onConnectionTypeResolve(const NodeObj& node)
    {
        auto const inputArray = node.iNode->getAttributeByToken(node, inputs::array.token());
        auto const inputArrayOrig = node.iNode->getAttributeByToken(node, inputs::arrayOrig.token());
        auto const outputArray = node.iNode->getAttributeByToken(node, outputs::array.token());
        auto const inputArrayType = inputArrayOrig.iAttribute->getResolvedType(inputArrayOrig);

        if (inputArrayType.baseType != BaseDataType::eUnknown)
        {
            std::array<AttributeObj, 2> attrs{ inputArrayOrig, outputArray };
            // all should have the same tuple count
            std::array<uint8_t, 2> tupleCounts{ inputArrayType.componentCount, inputArrayType.componentCount };
            // value type can not be an array because we don't support arrays-of-arrays
            std::array<uint8_t, 2> arrayDepths{ 1, 1 };
            std::array<AttributeRole, 2> rolesBuf{ inputArrayType.role, AttributeRole::eUnknown };
            node.iNode->resolvePartiallyCoupledAttributes(
                node, attrs.data(), tupleCounts.data(), arrayDepths.data(), rolesBuf.data(), attrs.size());
        }
    }
};

REGISTER_OGN_NODE()

} // namespace shared
} // namespace anim
} // namespace omni
