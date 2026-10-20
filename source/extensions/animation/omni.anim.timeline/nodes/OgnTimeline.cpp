// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "UsdPCH.h"
// clang-format on

#include <carb/Framework.h>
#include <carb/Types.h>
#include <carb/extras/StringUtils.h>
#include <carb/logging/Log.h>

#include <animationSchema/animationCurveAPI.h>

#include <IAnimCurve.h>
#include <OgnTimelineDatabase.h>
#include <cmath>
#include <string>
#include <unordered_map>
#include <vector>

using namespace pxr;

class OgnTimeline
{

    enum class PlayDirection
    {
        eForward,
        eBackward,
    };

public:
    bool m_playing = false;
    bool m_stopping = false;
    double m_startWallTime = 0.0;
    double m_startTimelineTime = 0.0;
    double m_currentTimelineTime = 0.0;
    PlayDirection m_playingDirection;
    pxr::SdfPath animData;
    std::unordered_map<std::string, std::string> m_curves; // attribute name -> curve name
    std::vector<std::string> m_invalidCurveNames;

    static bool updateNodeVersion(const GraphContextObj& context, const NodeObj& node, int oldVersion, int newVersion)
    {
        do
        {
            // Copy curve data from animation data to curve node
            if (oldVersion >= 2)
                break;

            auto stageId = context.iContext->getStageId(context);
            auto stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
            if (!stage)
                break;

            auto nodePrim = stage->GetPrimAtPath(SdfPath(node.iNode->getPrimPath(node)));
            if (!nodePrim)
                break;

            auto animDataPath = nodePrim.GetPath().AppendChild(TfToken("animationData"));
            auto animData = stage->GetPrimAtPath(animDataPath);
            if (!animData)
                break;

            SdfChangeBlock changeBlock;

            auto curveApi = AnimationSchemaAnimationCurveAPI(animData);
            auto curveNames = curveApi.GetCurves();
            for (auto curveName : curveNames)
            {
                for (auto prop : animData.GetAuthoredPropertiesInNamespace(curveName))
                {
                    prop.FlattenTo(nodePrim);
                }
            }
        } while (false);

        return oldVersion < newVersion;
    }

    static bool isActiveState(const ExecutionAttributeState& state)
    {
        return state != kExecutionAttributeStateDisabled;
    }

    static bool compute(OgnTimelineDatabase& db)
    {
        auto& nodeObj = db.abi_node();
        const INode* const iNode = nodeObj.iNode;

        const auto& contextObj = db.abi_context();
        const IGraphContext* const iContext = contextObj.iContext;

        OgnTimeline& state = db.perInstanceState<OgnTimeline>();
        const double now = iContext->getTimeSinceStart(contextObj);

        const auto playState = (ExecutionAttributeState)db.inputs.play();
        const auto playFromStartState = (ExecutionAttributeState)db.inputs.playFromStart();
        const auto reverseState = (ExecutionAttributeState)db.inputs.reverse();
        const auto reverseFromEndState = (ExecutionAttributeState)db.inputs.reverseFromEnd();
        const auto stopState = (ExecutionAttributeState)db.inputs.stop();
        const auto setNewTimeState = (ExecutionAttributeState)db.inputs.setNewTime();

        const double length = db.inputs.length();
        const double framerate = db.inputs.framerate();

        auto& updated = db.outputs.updated();
        auto& finished = db.outputs.finished();

        auto animCurve = carb::getCachedInterface<omni::anim::IAnimCurve>();

        if (state.m_stopping)
        {
            state.m_playing = state.m_stopping = false;
            updated = kExecutionAttributeStateDisabled;
            finished = kExecutionAttributeStateLatentFinish;
            return true;
        }

        if (isActiveState(setNewTimeState))
        {
            state.m_startTimelineTime = db.inputs.newTime();
            state.m_startWallTime = now;
        }

        bool firstTick = false;
        if (!state.m_playing)
        {
            if (isActiveState(playState) || isActiveState(playFromStartState) || isActiveState(reverseState) ||
                isActiveState(reverseFromEndState))
            {
                // This is the first entry, start ticking
                updated = kExecutionAttributeStateDisabled;
                finished = kExecutionAttributeStateLatentPush;

                auto curvePrims = animCurve->getCurvePrims(SdfPath(nodeObj.iNode->getPrimPath(nodeObj)));
                if (!curvePrims.empty())
                    state.animData = curvePrims[0];

                size_t attributeCount = iNode->getAttributeCount(nodeObj);
                std::vector<AttributeObj> attrs;
                attrs.resize(attributeCount);
                state.m_curves.clear();

                // Get the curves on the Timeline node
                // If a new curve is added while Timeline is playing, it will not be played until current Timeline node
                // execution has finished.
                std::string curveName;
                if (iNode->getAttributes(nodeObj, attrs.data(), attrs.size()))
                {
                    auto curveNames = animCurve->getCurves(SdfPath(nodeObj.iNode->getPrimPath(nodeObj)));

                    for (const auto& attributeObj : attrs)
                    {
                        // only check for dynamically created attributes
                        if (!attributeObj.iAttribute->isDynamic(attributeObj))
                        {
                            continue;
                        }

                        const char* attrName = attributeObj.iAttribute->getName(attributeObj);
                        static const char kAttrPrefix[] = "outputs:";
                        static constexpr size_t kAttrPrefixLen = sizeof(kAttrPrefix) - 1;
                        if (strncmp(attrName, kAttrPrefix, kAttrPrefixLen) == 0)
                        {
                            curveName.reserve(strlen(attrName) + 2);
                            curveName.assign(attrName);
                            curveName += ":x";

                            if (curveNames.find(TfToken(curveName)) != curveNames.end())
                                state.m_curves[attrName] = curveName;
                        }
                    }
                }

                state.m_invalidCurveNames.reserve(state.m_curves.size());
                state.m_playing = true;
                firstTick = true;
            }
        }
        else
        {
            if (isActiveState(stopState))
            {
                // If set it to kExecutionAttributeStateLatentFinish directly while playing, it triggers this error:
                // Latent node /World/ActionGraph/timeline finished (kExecutionAttributeStateLatentFinish) without
                // starting (kExecutionAttributeStateLatentPush). Pending fix, see
                // https://nvidia.slack.com/archives/CN05UCXT5/p1641928651123200?thread_ts=1641926754.116500&cid=CN05UCXT5
#if 0
                updated = kExecutionAttributeStateDisabled;
                finished = kExecutionAttributeStateLatentFinish;
                state.m_playing = false;
#else
                state.m_stopping = true;
#endif
            }
        }

        // update play state and tick the node
        if (state.m_playing && !state.m_stopping)
        {
            if (isActiveState(playState))
            {
                state.m_playingDirection = PlayDirection::eForward;
                state.m_startWallTime = now;
                state.m_startTimelineTime = state.m_currentTimelineTime;
            }
            else if (isActiveState(playFromStartState))
            {
                state.m_playingDirection = PlayDirection::eForward;
                state.m_startWallTime = now;
                state.m_startTimelineTime = state.m_currentTimelineTime = 0.0;
            }
            else if (isActiveState(reverseState))
            {
                state.m_playingDirection = PlayDirection::eBackward;
                state.m_startWallTime = now;
                state.m_startTimelineTime = state.m_currentTimelineTime;
            }
            else if (isActiveState(reverseFromEndState))
            {
                state.m_playingDirection = PlayDirection::eBackward;
                state.m_startWallTime = now;
                state.m_startTimelineTime = state.m_currentTimelineTime = length;
            }

            // Tick the animation curve(s)
            double elapsedTime = now - state.m_startWallTime;

            if (state.m_playingDirection == PlayDirection::eForward)
            {
                state.m_currentTimelineTime = state.m_startTimelineTime + elapsedTime;
            }
            else
            {
                state.m_currentTimelineTime = state.m_startTimelineTime - elapsedTime;
            }

            // wrap around the time if looping
            if (db.inputs.loop())
            {
                state.m_currentTimelineTime =
                    state.m_currentTimelineTime - std::floor(state.m_currentTimelineTime / length) * length;
            }

            db.outputs.nodeTime() = state.m_currentTimelineTime;

            if (state.m_playingDirection == PlayDirection::eForward && state.m_currentTimelineTime >= length ||
                state.m_playingDirection == PlayDirection::eBackward && state.m_currentTimelineTime <= 0.0)
            {
                if (!db.inputs.loop())
                {
                    updated = kExecutionAttributeStateDisabled;
                    finished = firstTick ? kExecutionAttributeStateDisabled : kExecutionAttributeStateLatentFinish;
                    state.m_playing = false;
                    return true;
                }
            }

            double sampledValue = 0.0;

            for (const auto& curveEntry : state.m_curves)
            {
                auto attributeObj = iNode->getAttribute(nodeObj, curveEntry.first.c_str());
                if (attributeObj.iAttribute->isValid(attributeObj))
                {
                    if (animCurve->evaluate(state.animData.AppendProperty(TfToken(curveEntry.second)),
                                            state.m_currentTimelineTime, sampledValue))
                    {
                        auto dataHandle =
                            attributeObj.iAttribute->getAttributeDataHandle(attributeObj, db.getInstanceIndex());

                        void* data;
                        contextObj.iAttributeData->getDataW(&data, contextObj, &dataHandle, 1);

                        double* outputData = reinterpret_cast<double*>(data);
                        *outputData = sampledValue;
                    }
                }
                else
                {
                    state.m_invalidCurveNames.push_back(curveEntry.first);
                }
            }

            // clear out invalid curves (if it's removed while Timeline node is playing)
            for (const auto& name : state.m_invalidCurveNames)
            {
                state.m_curves.erase(name);
            }
            state.m_invalidCurveNames.clear();

            updated = firstTick ? kExecutionAttributeStateDisabled : kExecutionAttributeStateEnabled;
        }

        if (!firstTick)
        {
            finished = kExecutionAttributeStateDisabled;
        }

        return true;
    }
};

REGISTER_OGN_NODE()
