// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// clang-format off
#include "PreUsdHeaders.h"
#include <pxr/usd/usd/notice.h>
#include <pxr/usd/usdUtils/stageCache.h>
#include <pxr/usd/usd/primRange.h>
#include <pxr/usd/usd/attributeQuery.h>
#include <pxr/usd/usdLux/distantLight.h>
#include <pxr/usd/usdLux/diskLight.h>
#include <pxr/usd/usdLux/cylinderLight.h>
#include <pxr/usd/usdLux/rectLight.h>
#include <pxr/usd/usdLux/sphereLight.h>
#include <pxr/usd/usdShade/shader.h>
#include <pxr/usd/usdShade/material.h>
#include <pxr/usd/usd/editContext.h>
#include <animationSchema/animationData.h>
#include <animationSchema/animationCurveAPI.h>
#include <animationSchema/animationDataAPI.h>
#include <animationSchemaTools/UsdTools.h>
#include "PostUsdHeaders.h"
#include <shared_mutex>
// clang-format on

#define CARB_EXPORTS
#define USD_CONTEXT_INCLUDES

#include "AnimCurveEvent.h"
#include "AttrQueryCache.h"
#include "IAnimCurve.h"
#include "SimplificationUtils.h"

#include <carb/Framework.h>
#include <carb/PluginUtils.h>
#include <carb/eventdispatcher/IEventDispatcher.h>
#include <carb/events/EventsAdapterUtils.h>
#include <carb/events/EventsUtils.h>
#include <carb/events/IEvents.h>
#include <carb/logging/Log.h>

#include <omni/fabric/FabricUSD.h>
#include <omni/fabric/IFabric.h>
#include <omni/graph/core/ComputeGraph.h>
#include <omni/graph/core/OgnHelpers.h>
#include <omni/graph/core/unstable/INodeTypeForwarding.h>
#include <omni/kit/IApp.h>
#include <omni/timeline/ITimeline.h>
#include <omni/timeline/TimelineTypes.h>
#include <omni/usd/Selection.h>
#include <omni/usd/UsdContext.h>

using namespace pxr::AnimationSchemaAnimationCurve;
using namespace carb;

const struct carb::PluginImplDesc kPluginImpl = { "omni.anim.curve.core.plugin", "Animation Curve Data Runtime",
                                                  "NVIDIA", carb::PluginHotReload::eEnabled, "dev" };

CARB_PLUGIN_IMPL(kPluginImpl, omni::anim::IAnimCurve)
CARB_PLUGIN_IMPL_DEPS(carb::logging::ILogging,
                      carb::events::IEvents,
                      carb::dictionary::IDictionary,
                      omni::graph::core::ComputeGraph)
DECLARE_OGN_NODES();

int ticksPerSec;

class AnimCurveMain : public TfWeakBase
{
public:
    AnimCurveMain()
    {
        ticksPerSec = (int)AnimationSchemaAnimationCurveAPI::GetTicksPerSecond();

        auto usdContext = omni::usd::UsdContext::getContext();
        if (!usdContext)
        {
            CARB_LOG_ERROR("Can't get UsdContext.");
            return;
        }

        auto framework = carb::getFramework();
        auto events = framework->acquireInterface<carb::events::IEvents>();
        if (events)
            curveEventStream = events->createEventStream();

        // TODO: 'omni::kit::IApp::getUpdateEventStream': Use Events 2.0
        CARB_IGNOREWARNING_MSC_WITH_PUSH(4996)
        auto iApp = carb::getCachedInterface<omni::kit::IApp>();
        appUpdateEventSub = carb::events::createSubscriptionToPop(
            iApp->getUpdateEventStream(), [&](carb::events::IEvent* event) { this->onAppUpdate(event); }, 0,
            "AnimCurveMain");

        stageEventSub = carb::events::createSubscriptionToPop(
            usdContext->getStageEventStream().get(), [&](carb::events::IEvent* event) { this->onStageEvent(event); }, 0,
            "AnimCurveMain");
        CARB_IGNOREWARNING_MSC_POP

        auto timeline = carb::getCachedInterface<omni::timeline::ITimeline>()->getTimeline();
        if (timeline)
        {
            carb::RString kEvents[] = { omni::timeline::kGlobalEventCurrentTimeTicked,
                                        omni::timeline::kGlobalEventTimeCodesPerSecondChanged,
                                        omni::timeline::kGlobalEventStop };

            // resize timelineEventSubs accordingly.
            timelineEventSubs.clear();
            timelineEventSubs.resize(CARB_COUNTOF(kEvents));

            // timelineEventSubs items setup
            auto ed = carb::getCachedInterface<carb::eventdispatcher::IEventDispatcher>();
            const static carb::RStringKey name("omni.anim.curve.core");
            for (size_t i = 0; i < CARB_COUNTOF(kEvents); ++i)
            {
                timelineEventSubs[i] = ed->observeEvent(
                    name, carb::eventdispatcher::kDefaultOrder, kEvents[i],
                    [this](const carb::eventdispatcher::Event& event)
                    {
                        static const carb::RStringKey currentTime("currentTime");
                        auto time = event.getValueOr<double>(currentTime, 0);
                        onGlobalTimeChanged(time);
                    },
                    timeline->getEventKey() // Important to have this filter
                );
            }
        }

        propUpdateEvent = carb::events::typeFromString("omni.usd.property.usd.additional_changed_path");
        propUpdateEventStr = RString("omni.usd.property.usd.additional_changed_path");
        propUpdateEventStrImmediate = RString("omni.usd.property.usd.additional_changed_path:immediate");
        carb::events::registerEventAlias(propUpdateEvent, propUpdateEventStr, propUpdateEventStrImmediate);
        onStageOpened();
    }

    ~AnimCurveMain()
    {

        TfNotice::Revoke(noticeKey);
    }

    void onGlobalTimeChanged(double time)
    {
        //// Update old animation
        // updateOldAnim(time);

        // Update key icon for property pannel
        auto selectedPaths = omni::usd::UsdContext::getContext()->getSelection()->getSelectedPrimPaths();
        auto ed = carb::getCachedInterface<carb::eventdispatcher::IEventDispatcher>();
        for (auto& path : selectedPaths)
        {
            auto itr = tgtPrims.find(SdfPath(path));
            if (itr == tgtPrims.end())
                continue;

            std::set<std::string> attrNames;
            for (auto& entry : itr->second.curves)
            {
                std::string attrName;
                attrName.assign(entry.first.GetString().begin(), entry.first.GetString().end() - 2);
                attrNames.insert(attrName);
            }

            for (auto& attrName : attrNames)
            {
                ed->dispatchEvent(
                    propUpdateEventStr, std::make_pair(RStringKey("path"), (path + "." + attrName).c_str()));
            }
        }
    }

    void onStageOpened()
    {
        auto stage = omni::usd::UsdContext::getContext()->getStage();
        if (!stage)
            return;

        noticeKey = TfNotice::Register(TfCreateWeakPtr(this), &AnimCurveMain::handleUsdChanges, stage);

        // Discover authored graph nodes on USD, as in the Kit 111 animation graph fix.
        loadStageUsd();
    }

    void loadStageUsd()
    {
        // Function to read curves
        auto loadCurves = [](const UsdPrim& prim)
        {
            // Load curve names
            std::map<TfToken, omni::anim::IAnimCurve::Curve> curves;

            for (auto& attr : prim.GetAttributes())
            {
                auto tokens = SdfPath::TokenizeIdentifierAsTokens(attr.GetName().GetString());
                if (tokens.size() < 3)
                    continue;

                if (tokens.back() != AnimationSchemaTokens->times)
                {
                    continue;
                }

                auto& token = *(tokens.rbegin() + 1);
                if (token.size() > 1)
                    continue;

                auto compName = *token.GetText();
                if (compName >= 'w' && compName <= 'z')
                {
                    curves[TfToken(attr.GetNamespace().GetText())];
                }
            }

            // Load curve keys
            for (auto& entry : curves)
            {
                std::vector<AnimationSchemaAnimationCurve::Key> keys;

                VtArray<double> values;
                VtArray<double> inTangentValues, outTangentValues;
                VtArray<int64_t> times, inTangentTimes, outTangentTimes;
                VtArray<TfToken> inTangentTypes, outTangentTypes;
                VtArray<bool> tangentBrokens, tangentWeighteds;

                auto getCurveInfos = [&](const TfToken& inPostfix, auto& infos)
                {
                    auto postfix = TfToken(inPostfix.GetText());
                    auto attrNameStr = entry.first.GetString() + ":" + postfix.GetText();
                    auto attrName = TfToken(attrNameStr);
                    if (!prim.HasAttribute(attrName))
                        return false;

                    auto attr = prim.GetAttribute(attrName);
                    attr.Get(&infos);
                    if (infos.size() != times.size())
                    {
                        auto errorMsg =
                            std::string() + "Curve property array " +
                            SdfPath(prim.GetPath().GetText()).AppendProperty(TfToken(attrName.GetText())).GetText() +
                            " size " + std::to_string(infos.size()) + " doesn't match time array size " +
                            std::to_string(times.size());

                        CARB_LOG_ERROR("%s", errorMsg.c_str());

                        return false;
                    }
                    return true;
                };

                auto& Tokens = *AnimationSchemaTokens;
                bool ok = getCurveInfos(Tokens.times, times);
                ok = ok && getCurveInfos(Tokens.values, values);
                ok = ok && getCurveInfos(Tokens.inTangentValues, inTangentValues);
                ok = ok && getCurveInfos(Tokens.inTangentTimes, inTangentTimes);
                ok = ok && getCurveInfos(Tokens.inTangentTypes, inTangentTypes);
                ok = ok && getCurveInfos(Tokens.outTangentValues, outTangentValues);
                ok = ok && getCurveInfos(Tokens.outTangentTimes, outTangentTimes);
                ok = ok && getCurveInfos(Tokens.outTangentTypes, outTangentTypes);
                ok = ok && getCurveInfos(Tokens.tangentBrokens, tangentBrokens);
                ok = ok && getCurveInfos(Tokens.tangentWeighteds, tangentWeighteds);
                if (!ok)
                    continue;

                // Fill key arrays
                keys.resize(times.size());

                for (unsigned index = 0; index < times.size(); ++index)
                {
                    auto& key = keys[index];
                    key.value = values[index];
                    key.time = times[index];
                    key.inTangent.time = inTangentTimes[index];
                    key.inTangent.value = inTangentValues[index];
                    key.inTangent.type = TfToken(inTangentTypes[index].GetText());
                    key.outTangent.time = outTangentTimes[index];
                    key.outTangent.value = outTangentValues[index];
                    key.outTangent.type = TfToken(outTangentTypes[index].GetText());
                    key.tangentBroken = tangentBrokens[index];
                    key.tangentWeighted = tangentWeighteds[index];
                }

                AnimationSchemaAnimationCurveAPI::ValidateKeys(keys);
                entry.second.keys = keys;

                // Load other properties
                TfToken preInfinity;
                auto preAttrName =
                    TfToken(entry.first.GetString() + ":" + AnimationSchemaTokens->preInfinityType.GetText());
                prim.GetAttribute(preAttrName).Get(&preInfinity);
                if (preInfinity.IsEmpty())
                    entry.second.preInfinityType = AnimationSchemaTokens->constant;
                else
                    entry.second.preInfinityType = TfToken(preInfinity.GetText());

                TfToken postInfinity;
                auto postAttrName =
                    TfToken(entry.first.GetString() + ":" + AnimationSchemaTokens->postInfinityType.GetText());
                prim.GetAttribute(postAttrName).Get(&postInfinity);
                if (postInfinity.IsEmpty())
                    entry.second.postInfinityType = AnimationSchemaTokens->constant;
                else
                    entry.second.postInfinityType = TfToken(postInfinity.GetText());

                entry.second.animData =
                    omni::usd::UsdContext::getContext()->getStage()->GetPrimAtPath(SdfPath(prim.GetPath().GetText()));
            }

            return curves;
        };

        std::unique_lock<std::shared_timed_mutex> writeLock(cacheMutex);

        // Read from curve nodes and timeline nodes
        auto stage = omni::usd::UsdContext::getContext()->getStage();
        if (!stage)
            return;

        for (const auto& prim : stage->Traverse())
        {
            if (prim.GetTypeName() != TfToken("OmniGraphNode"))
                continue;
            // Check if it's a curve node or timeline node.

            TfToken nodeType;
            prim.GetAttribute(TfToken("node:type")).Get(&nodeType);

            if (nodeType != "omni.anim.curve.core.AnimCurve" && nodeType != "omni.anim.Timeline")
                continue;

            // Load curves
            auto usdPath = SdfPath(prim.GetPath().GetText());

            auto& animData = animDatas[usdPath];
            animData.curves = loadCurves(prim);

            // Load target prim info
            auto& curveNodeData = animCurveNodes[usdPath];
            auto rel = prim.GetRelationship(TfToken("inputs:Prim"));
            SdfPathVector paths;
            rel.GetTargets(&paths);
            if (!paths.empty())
            {
                curveNodeData.tgtPrim = SdfPath(paths.front().GetText());
                auto& tgtPrimData = tgtPrims[curveNodeData.tgtPrim];
                for (auto& entry : animData.curves)
                {
                    tgtPrimData.curves[entry.first] = usdPath;
                }
            }
        }

        // Pump events
        if (!animDatas.empty())
        {
            carb::events::IEventPtr event = getEventStream()->createEvent(
                omni::anim::IAnimCurve::CurveEventType::Added, carb::events::kGlobalSenderId);

            std::vector<const char*> paths;
            for (auto& entry : animDatas)
            {
                paths.push_back(entry.first.GetText());
            }
            for (auto& entry : tgtPrims)
            {
                paths.push_back(entry.first.GetText());
            }

            auto iDir = carb::getCachedInterface<carb::dictionary::IDictionary>();
            auto pathsItem = iDir->createItem(event->payload, "paths", carb::dictionary::ItemType::eBool);

            iDir->setStringArray(pathsItem, paths.data(), paths.size());

            getEventStream()->push(event.get());
            getEventStream()->pump();
        }
    }

    void onStageEvent(carb::events::IEvent* event)
    {
        switch ((omni::usd::StageEventType)event->type)
        {
        case omni::usd::StageEventType::eOpened:
        {
            onStageOpened();
            break;
        }
        case omni::usd::StageEventType::eClosing:
            TfNotice::Revoke(noticeKey);
            noticeKey = TfNotice::Key();
            animDatas.clear();
            animCurveNodes.clear();
            tgtPrims.clear();
            break;
        }
    }

    bool isUpdatingUsd() const
    {
        return updatingUsd;
    }

    carb::events::IEventStream* getEventStream() const
    {
        return curveEventStream.get();
    }

    bool evaluate(const pxr::SdfPath& curvePath, double time, double& value) const
    {
        std::shared_lock<std::shared_timed_mutex> lock(cacheMutex);

        auto curves = getCurves(curvePath.GetPrimPath());
        auto itr = curves.find(curvePath.GetNameToken());
        if (itr == curves.end())
            return false;

        return getInterpolatedValue(*itr->second, time, value);
    }

    std::vector<SdfPath> getCurvePrims(const SdfPath& prim) const
    {
        auto itrAnimData = animDatas.find(prim);
        if (itrAnimData != animDatas.end())
        {
            return { prim };
        }

        // auto itrCurveNode = animCurveNodes.find(prim);
        // if (itrCurveNode != animCurveNodes.end())
        //{
        //     return { itrCurveNode->second.animData };
        // }

        std::set<SdfPath> animPrims;
        for (auto& entry : animCurveNodes)
        {
            if (entry.second.tgtPrim == prim)
            {
                animPrims.insert(entry.first);
            }
        }

        std::vector<SdfPath> animPrimVec;
        animPrimVec.assign(animPrims.begin(), animPrims.end());

        return animPrimVec;
    }

    std::map<TfToken, const omni::anim::IAnimCurve::Curve*> getCurves(const SdfPath& prim, bool mustBeAnimData = false) const
    {
        if (prim.IsEmpty())
            return {};

        auto itrAnimData = animDatas.find(prim);
        if (itrAnimData != animDatas.end())
        {
            std::map<TfToken, const omni::anim::IAnimCurve::Curve*> curves;
            for (auto& entry : itrAnimData->second.curves)
            {
                curves[entry.first] = &entry.second;
            }

            return curves;
        }

        if (mustBeAnimData)
            return {};

        // auto itr = animCurveNodes.find(prim);
        // if (itr != animCurveNodes.end())
        //{
        //     return getCurves(itr->second.animData);
        // }

        auto itrTgtPrim = tgtPrims.find(prim);
        if (itrTgtPrim != tgtPrims.end())
        {
            std::map<TfToken, const omni::anim::IAnimCurve::Curve*> curves;

            for (auto& entryCurve : itrTgtPrim->second.curves)
            {
                auto itr = animDatas.find(entryCurve.second);
                curves[entryCurve.first] = &itr->second.curves.find(entryCurve.first)->second;
            }

            return curves;
        }

        for (auto& animData : getCurvePrims(prim))
        {
            std::map<TfToken, const omni::anim::IAnimCurve::Curve*> curves;
            auto newCurves = getCurves(animData);
            curves.insert(newCurves.begin(), newCurves.end());
            return curves;
        }

        return {};
    }

    std::vector<SdfPath> getCurveNodes(const pxr::SdfPath& prim /*, const pxr::SdfPath& animData*/) const
    {
        std::vector<SdfPath> curveNodes;
        for (auto& entry : animCurveNodes)
        {
            if (!prim.IsEmpty() && entry.second.tgtPrim != prim)
                continue;

            // if (!animData.IsEmpty() && entry.second.animData != animData)
            //     continue;

            curveNodes.push_back(entry.first);
        }

        return curveNodes;
    }

    bool setOverridenKeys(const pxr::SdfPath& curvePath, const std::vector<pxr::AnimationSchemaAnimationCurve::Key>& keys)
    {
        std::unique_lock<std::shared_timed_mutex> writeLock(cacheMutex);

        auto itr = animDatas.find(curvePath.GetPrimPath());
        if (itr == animDatas.end())
            return false;

        auto itrCurve = itr->second.curves.find(curvePath.GetNameToken());
        if (itrCurve == itr->second.curves.end())
            return false;

        itrCurve->second.overridenKeys = keys;

        return true;
    }

    void pumpKeysOverridenEvent(const std::vector<SdfPath>& curvePaths)
    {
        // Compose event paths
        std::set<SdfPath> animDataCurves;

        for (auto& path : curvePaths)
        {
            auto curves = getCurves(path.GetPrimPath());
            auto itr = curves.find(path.GetNameToken());
            if (itr == curves.end())
                continue;

            if (itr->second->animData)
                animDataCurves.insert(itr->second->animData.GetPath().AppendProperty(path.GetNameToken()));
        }

        std::set<SdfPath> sdfPaths = animDataCurves;

        // for (auto& entry : animCurveNodes)
        //{
        //     for (auto& path : animDataCurves)
        //     {
        //         if (path.GetPrimPath() == entry.second.animData)
        //         {
        //             sdfPaths.insert(entry.first.AppendProperty(path.GetNameToken()));
        //         }
        //     }
        // }

        for (auto& entry : tgtPrims)
        {
            for (auto& curveEntry : entry.second.curves)
            {
                if (animDataCurves.find(curveEntry.second.AppendProperty(curveEntry.first)) != animDataCurves.end())
                    sdfPaths.insert(entry.first.AppendProperty(curveEntry.first));
            }
        }

        // Dispatch event
        std::vector<const char*> paths;

        for (auto& path : sdfPaths)
        {
            if (std::find(paths.begin(), paths.end(), path.GetString()) == paths.end())
            {
                paths.push_back(path.GetText());
            }
        }

        carb::events::IEventPtr event = getEventStream()->createEvent(
            omni::anim::IAnimCurve::CurveEventType::KeysOverriden, carb::events::kGlobalSenderId);
        carb::dictionary::IDictionary* iDir = carb::getCachedInterface<carb::dictionary::IDictionary>();
        carb::dictionary::Item* item = iDir->createItem(event->payload, "paths", carb::dictionary::ItemType::eBool);
        iDir->setStringArray(item, paths.data(), paths.size());

        getEventStream()->push(event.get());
        getEventStream()->pump();
    }

    void updateTgtPrim(const SdfPath& primSdfPath,
                       const std::map<TfToken, double>& curveValues,
                       const omni::graph::core::GraphContextObj& graphContextObj) const
    {
        if (curveValues.empty() || primSdfPath.IsEmpty())
            return;

        // Kit 111 has no Fabric stage reader/writer (omni::fabric::IStageReaderWriter is not provided), so the values
        // go to USD directly. They go to the session layer, where the Fabric write-back used to put them; the node is
        // scheduled "usd-write".
        auto stageId = graphContextObj.iContext->getStageId(graphContextObj);
        auto stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
        if (!stage)
            return;

        UsdEditContext editContext(stage, stage->GetEditTargetForLocalLayer(stage->GetSessionLayer()));
        updateTgtPrim(stage, primSdfPath, curveValues);
    }

    // Writes the curve values to the target prim's attributes at the stage's edit target. The attributes are looked
    // up on the graph's own stage: the attribute query cache only learns about stages opened after this plugin started.
    void updateTgtPrim(const UsdStageRefPtr& stage, const SdfPath& prim, const std::map<TfToken, double>& curveValues) const
    {
        if (curveValues.empty())
            return;

        updatingUsd = true;
        std::shared_ptr<void> callOnReturn(nullptr, [&](auto) { updatingUsd = false; });

        SdfChangeBlock changeBlock;

        std::map<TfToken, std::map<int, double>> attrValues;

        for (auto& entry : curveValues)
        {
            auto attrName = entry.first.GetString();
            attrName.assign(attrName.begin(), attrName.end() - 2);

            auto& values = attrValues[TfToken(attrName)];
            values[compNameToIndex(entry.first.GetString().back())] = entry.second;
        }

        for (auto& entry : attrValues)
        {
            auto attr = stage->GetAttributeAtPath(prim.AppendProperty(entry.first));
            if (!attr)
                continue;

            // Token attribute
            if (attr.GetTypeName() == SdfValueTypeNames->Token)
            {
                VtTokenArray tokens;
                attr.GetMetadata(SdfFieldKeys->AllowedTokens, &tokens);
                auto value = entry.second.begin()->second;

                int index = (int)std::round(value);
                if (index < 0 || index >= tokens.size())
                    continue;

                attr.Clear();
                attr.Set(tokens[index]);

                continue;
            }

            // Value attribute. Start from its current value so components the curves don't drive keep it. Without a
            // default (e.g. only time samples) that is its value at the current time, else its type's default value.
            VtValue attrValue;
            if (!attr.Get(&attrValue) || attrValue.IsEmpty())
            {
                auto timeline = carb::getCachedInterface<omni::timeline::ITimeline>()->getTimeline();
                attr.Get(&attrValue, UsdTimeCode(timeline->getCurrentTime() * timeline->getTimeCodesPerSecond()));
            }
            if (attrValue.IsEmpty())
                attrValue = attr.GetTypeName().GetDefaultValue();

            bool valueSet = false;
            for (auto& compEntry : entry.second)
            {
                extern bool setVtValue(double value, int index, VtValue& vtValue);
                if (setVtValue(compEntry.second, compEntry.first, attrValue))
                    valueSet = true;
            }

            if (!valueSet)
                continue;

            extern bool setAttrValue(UsdAttribute & attr, const VtValue& value);
            attr.Clear(); // Trigger change for property icon in property window.
            setAttrValue(attr, attrValue);
        }
    }

private:
    struct AnimCurveData
    {
        SdfPath tgtPrim;
    };

    struct AnimDataData
    {
        std::map<TfToken, omni::anim::IAnimCurve::Curve> curves;
    };

    struct TgtPrimData
    {
        std::map<TfToken, SdfPath> curves;
    };

    carb::ObjectPtr<carb::events::ISubscription> stageEventSub;
    std::vector<carb::eventdispatcher::ObserverGuard> timelineEventSubs;
    carb::ObjectPtr<carb::events::ISubscription> appUpdateEventSub;
    TfNotice::Key noticeKey;
    UsdAttrQueryCache attrQueryCache;
    std::map<SdfPath, AnimCurveData> animCurveNodes;
    std::map<SdfPath, AnimDataData> animDatas;
    std::map<SdfPath, TgtPrimData> tgtPrims;
    mutable std::shared_timed_mutex cacheMutex;
    carb::events::EventType propUpdateEvent = 0;
    carb::RString propUpdateEventStr = RString("");
    carb::RString propUpdateEventStrImmediate = RString("");
    mutable bool updatingUsd = false; // Editor should ignore TfNotice when the Curve runtime is updating the target
                                      // prim
    carb::events::IEventStreamPtr curveEventStream;

    struct EventPath
    {
        SdfPath path;
        bool added = true;
    };
    std::vector<EventPath> changedTgtPrimCurves;

    static int compNameToIndex(char comp)
    {
        static int comps[] = { 3, 0, 1, 2 };
        auto index = comp - 'w';
        if (index >= 0 && index < 4)
            return comps[index];
        else
            return -1;
    }

    static char indexToCompName(int i)
    {
        static char comps[] = { 'x', 'y', 'z', 'w' };
        return comps[i];
    }

    void handleUsdChanges(const UsdNotice::ObjectsChanged& objectsChanged)
    {
        if (updatingUsd)
            return;

        SdfPathVector changedPaths, resyncedPaths;
        for (auto path : objectsChanged.GetResyncedPaths())
        {
            changedPaths.push_back(path);
            resyncedPaths.push_back(path);
        }
        for (auto path : objectsChanged.GetChangedInfoOnlyPaths())
        {
            if (path.IsPropertyPath())
                changedPaths.push_back(path);
        }

        applyPendingChanges(objectsChanged.GetStage(), changedPaths, resyncedPaths);
    }

    static SdfPath getRelPath(UsdRelationship rel)
    {
        if (!rel)
            return SdfPath();

        SdfPathVector paths;
        rel.GetTargets(&paths);
        if (paths.empty())
            return SdfPath();

        return paths.front();
    };

    omni::anim::IAnimCurve::Curve loadCurve(const UsdPrim& animData, const TfToken& curveName)
    {
        omni::anim::IAnimCurve::Curve curve;

        AnimationSchemaAnimationCurveAPI curveApi(animData);

        curveApi.GetKeys(curveName, curve.keys);

        AnimationSchemaAnimationCurveAPI::ValidateKeys(curve.keys);

        curve.preInfinityType = curveApi.GetInfinityType(curveName, Infinity::Pre);
        if (infinityTypeMap.find(curve.preInfinityType) == infinityTypeMap.end())
            curve.preInfinityType = AnimationSchemaTokens->constant;

        curve.postInfinityType = curveApi.GetInfinityType(curveName, Infinity::Post);
        if (infinityTypeMap.find(curve.postInfinityType) == infinityTypeMap.end())
            curve.postInfinityType = AnimationSchemaTokens->constant;

        curve.animData = animData.GetPrim();

        return curve;
    }

    static bool isAnimCurve(const UsdPrim& prim)
    {
        if (prim.GetTypeName() != "OmniGraphNode" && prim.GetTypeName() != "ComputeNode")
            return false;

        TfToken nodeType;
        prim.GetAttribute(TfToken("node:type")).Get(&nodeType);
        return nodeType == "omni.anim.curve.core.AnimCurve";
    }

    static bool isTimelineNode(const UsdPrim& prim)
    {
        if (prim.GetTypeName() != "OmniGraphNode" && prim.GetTypeName() != "ComputeNode")
            return false;

        TfToken nodeType;
        prim.GetAttribute(TfToken("node:type")).Get(&nodeType);
        return nodeType == "omni.anim.Timeline";
    }

    void applyPendingChanges(UsdStageWeakPtr stage,
                             const std::vector<SdfPath>& changedPaths,
                             const std::vector<SdfPath>& resyncedPaths)
    {
        // Helper functions
        auto isChanged = [&](const SdfPath& path)
        {
            for (auto& changedPath : changedPaths)
            {
                if (path.HasPrefix(changedPath))
                    return true;
            }
            return false;
        };

        // The write lock
        std::unique_lock<std::shared_timed_mutex> writeLock(cacheMutex);

        // Remove resynced animation data and changed curves
        std::map<SdfPath, std::vector<TfToken>> oldAnimDatas;
        for (auto& entry : animDatas)
        {
            for (auto& curveEntry : entry.second.curves)
            {
                if (curveEntry.second.keys.empty())
                    continue;

                oldAnimDatas[entry.first].push_back(curveEntry.first);
            }
        }

        std::set<SdfPath> infinityChangedOnly;

        std::map<SdfPath, std::set<TfToken>> invalidCurves;
        for (auto& entry : animDatas)
        {
            if (isChanged(entry.first))
            {
                invalidCurves[entry.first];
                continue;
            }

            for (auto& curveEntry : entry.second.curves)
            {
                auto prefix = curveEntry.first.GetString() + ":";

                bool keysChanged = false;
                bool curveChanged = false;

                for (auto& path : changedPaths)
                {
                    if (!path.IsPropertyPath() || !path.HasPrefix(entry.first))
                        continue;

                    auto name = path.GetName();

                    if (!TfStringStartsWith(name, prefix))
                        continue;

                    curveChanged = true;

                    auto postfix = name.substr(prefix.size());
                    if (postfix != AnimationSchemaTokens->postInfinityType &&
                        postfix != AnimationSchemaTokens->preInfinityType)
                        keysChanged = true;

                    invalidCurves[entry.first].insert(curveEntry.first);

                    if (keysChanged)
                        break;
                }

                if (curveChanged && !keysChanged)
                    infinityChangedOnly.insert(entry.first.AppendProperty(curveEntry.first));
            }

            auto itr = invalidCurves.find(entry.first);
            if (itr != invalidCurves.end())
            {
                for (auto& curve : itr->second)
                {
                    entry.second.curves.erase(curve);
                }
            }
        }

        for (auto& entry : invalidCurves)
        {
            if (entry.second.empty())
                animDatas.erase(entry.first);
        }

        // Add changed curves
        std::map<SdfPath, std::vector<TfToken>> addedCurves;
        for (auto& entry : animDatas)
        {
            auto animDataChanged = false;
            for (auto& path : changedPaths)
            {
                if (path.HasPrefix(entry.first))
                {
                    animDataChanged = true;
                    break;
                }
            }

            if (!animDataChanged)
                continue;

            auto animPrim = stage->GetPrimAtPath(entry.first);
            for (auto curveName : AnimationSchemaAnimationCurveAPI(animPrim).GetCurves())
            {
                if (entry.second.curves.find(curveName) != entry.second.curves.end())
                    continue;

                entry.second.curves[curveName] = loadCurve(animPrim, curveName);
                addedCurves[entry.first].push_back(curveName);
            }
        }

        // Add resynced animation data
        for (auto& path : changedPaths)
        {
            if (!path.IsAbsoluteRootOrPrimPath())
                continue;

            for (auto prim : UsdPrimRange(stage->GetPrimAtPath(path)))
            {
                if (!isAnimCurve(prim) && !isTimelineNode(prim))
                    continue;

                auto& animDataData = animDatas[prim.GetPath()];
                auto& curves = addedCurves[prim.GetPath()];

                for (auto& curveName : AnimationSchemaAnimationCurveAPI(prim).GetCurves())
                {
                    animDataData.curves[curveName] = loadCurve(prim, curveName);
                    curves.push_back(curveName);
                }
            }
        }

        // Remove resynced curve nodes or reload
        auto oldAnimCurveNodes = animCurveNodes;
        std::vector<SdfPath> resyncedAnimCurveNodes;
        for (auto& entry : animCurveNodes)
        {
            if (isChanged(entry.first))
            {
                resyncedAnimCurveNodes.push_back(entry.first);
                continue;
            }

            auto prim = stage->GetPrimAtPath(entry.first);

            if (isChanged(entry.first.AppendProperty(TfToken("inputs:Prim"))))
                entry.second.tgtPrim = getRelPath(prim.GetRelationship(TfToken("inputs:Prim")));

            // if (isChanged(entry.first.AppendProperty(TfToken("inputs:AnimData"))))
            //     entry.second.animData = getRelPath(prim.GetRelationship(TfToken("inputs:AnimData")));
        }

        for (auto& node : resyncedAnimCurveNodes)
        {
            animCurveNodes.erase(node);
        }

        auto addCurveNode = [this, &addedCurves](const UsdPrim& prim)
        {
            auto& nodeData = animCurveNodes[prim.GetPath()];
            nodeData.tgtPrim = getRelPath(prim.GetRelationship(TfToken("inputs:Prim")));
            // nodeData.animData = getRelPath(prim.GetRelationship(TfToken("inputs:AnimData")));

            auto& animDataData = animDatas[prim.GetPath()];
            addedCurves[prim.GetPath()];

            for (auto& curveName : AnimationSchemaAnimationCurveAPI(prim).GetCurves())
            {
                animDataData.curves[curveName] = loadCurve(prim, curveName);
            }
        };

        // Add resynced curve nodes
        for (auto& path : resyncedPaths)
        {
            if (!path.IsAbsoluteRootOrPrimPath())
            {
                continue;
            }

            for (auto prim : UsdPrimRange(stage->GetPrimAtPath(path)))
            {
                if (isAnimCurve(prim) || isTimelineNode(prim))
                    addCurveNode(prim);
            }
        }

        for (auto& path : changedPaths)
        {
            if (!path.IsPropertyPath())
                continue;

            auto prim = stage->GetPrimAtPath(path.GetPrimPath());
            if (!prim)
                continue;

            if (path.GetNameToken() == "node:type" && (isAnimCurve(prim) || isTimelineNode(prim)))
                addCurveNode(prim);
        }

        // Update target prim cache
        auto oldTgtPrims = std::move(tgtPrims);
        for (auto& entry : animCurveNodes)
        {
            auto tgtPrim = stage->GetPrimAtPath(entry.second.tgtPrim);
            if (!tgtPrim)
                continue;

            auto itr = animDatas.find(entry.first);
            if (itr == animDatas.end())
                continue;

            for (auto& entryCurve : itr->second.curves)
            {
                auto attrName = entryCurve.first.GetString().substr(0, entryCurve.first.size() - 2);
                if (tgtPrim.GetAttribute(TfToken(attrName)))
                    tgtPrims[tgtPrim.GetPath()].curves[entryCurve.first] = itr->first;
            }
        }

        // Trigger add prim event
        auto ed = carb::getCachedInterface<carb::eventdispatcher::IEventDispatcher>();
        auto selectedPaths = omni::usd::UsdContext::getContext()->getSelection()->getSelectedPrimPaths();
        auto updatePropIcon = [&](const SdfPath& primPath, const std::map<TfToken, SdfPath>& curves)
        {
            if (std::find(selectedPaths.begin(), selectedPaths.end(), primPath.GetString()) == selectedPaths.end())
                return;

            std::set<std::string> attrNames;
            for (auto& entry : curves)
            {
                std::string attrName;
                attrName.assign(entry.first.GetString().begin(), entry.first.GetString().end() - 2);
                attrNames.insert(attrName);
            }

            for (auto& attrName : attrNames)
            {
                ed->dispatchEvent(propUpdateEventStr,
                                  std::make_pair(RStringKey("path"), (primPath.GetString() + "." + attrName).c_str()));
            }
        };

        using namespace omni::anim;

        for (auto& entry : tgtPrims)
        {
            if (oldTgtPrims.find(entry.first) == oldTgtPrims.end())
            {
                PushPrimAddedEvent(getEventStream(), entry.first);
                updatePropIcon(entry.first, entry.second.curves);
            }
        }

        for (auto& entry : animCurveNodes)
        {
            auto itrAnimData = animDatas.find(entry.first);
            if (itrAnimData == animDatas.end())
                continue;

            if (itrAnimData->second.curves.empty())
                continue;

            bool hadCurves = false;
            do
            {
                auto itrOld = oldAnimCurveNodes.find(entry.first);
                if (itrOld == oldAnimCurveNodes.end())
                    break;

                auto itrAnim = oldAnimDatas.find(itrOld->first);
                if (itrAnim == oldAnimDatas.end())
                    break;

                hadCurves = !itrAnim->second.empty();
            } while (false);

            if (!hadCurves)
            {
                PushPrimAddedEvent(getEventStream(), entry.first);
            }
        }

        // for (auto& entry : animDatas)
        //{
        //     if (entry.second.curves.empty())
        //         continue;

        //    bool hadCurves = false;
        //    do
        //    {
        //        auto itrOld = oldAnimDatas.find(entry.first);
        //        if (itrOld == oldAnimDatas.end())
        //            break;

        //        hadCurves = !itrOld->second.empty();
        //    } while (false);

        //    if (!hadCurves)
        //        PushPrimAddedEvent(getEventStream(), entry.first);
        //}

        // Trigger remove prim event
        for (auto& entry : oldTgtPrims)
        {
            if (tgtPrims.find(entry.first) == tgtPrims.end())
            {
                PushPrimRemovedEvent(getEventStream(), entry.first);
                updatePropIcon(entry.first, entry.second.curves);
            }
        }

        for (auto& entry : oldAnimCurveNodes)
        {
            auto itrAnim = oldAnimDatas.find(entry.first);
            if (itrAnim == oldAnimDatas.end())
                continue;

            if (itrAnim->second.empty())
                continue;

            bool haveCurves = false;
            do
            {
                auto itr = animCurveNodes.find(entry.first);
                if (itr == animCurveNodes.end())
                    break;

                auto itrAnim = animDatas.find(itr->first);
                if (itrAnim == animDatas.end())
                    break;

                haveCurves = !itrAnim->second.curves.empty();
            } while (false);

            if (!haveCurves)
                PushPrimRemovedEvent(getEventStream(), entry.first);
        }

        // for (auto& entry : oldAnimDatas)
        //{
        //     if (entry.second.empty())
        //         continue;

        //    bool haveCurves = false;
        //    do
        //    {
        //        auto itr = animDatas.find(entry.first);
        //        if (itr == animDatas.end())
        //            break;

        //        haveCurves = !itr->second.curves.empty();
        //    } while (false);

        //    if (!haveCurves)
        //        PushPrimRemovedEvent(getEventStream(), entry.first);
        //}

        // Trigger update event

        // Handle animation data
        std::map<SdfPath, IAnimCurve::CurveEventType> curveEvents;
        for (auto& entry : animDatas)
        {
            for (auto& entryCurve : addedCurves[entry.first])
            {
                if (invalidCurves[entry.first].find(entryCurve) == invalidCurves[entry.first].end())
                {
                    curveEvents[entry.first.AppendProperty(entryCurve)] = IAnimCurve::CurveEventType::Added;
                }
                else
                {
                    curveEvents[entry.first.AppendProperty(entryCurve)] = IAnimCurve::CurveEventType::Updated;
                }
            }

            for (auto& entryCurve : invalidCurves[entry.first])
            {
                if (entry.second.curves.find(entryCurve) == entry.second.curves.end())
                {
                    curveEvents[entry.first.AppendProperty(entryCurve)] = IAnimCurve::CurveEventType::Removed;
                }
            }
        }

        // Handle target prims
        for (auto& entry : tgtPrims)
        {
            auto itr = oldTgtPrims.find(entry.first);
            if (itr == oldTgtPrims.end())
                continue;

            std::map<TfToken, SdfPath> changedCurves;

            for (auto& entryCurve : entry.second.curves)
            {
                auto itrOld = itr->second.curves.find(entryCurve.first);
                if (itrOld == itr->second.curves.end())
                {
                    curveEvents[entry.first.AppendProperty(entryCurve.first)] = IAnimCurve::CurveEventType::Added;
                    changedCurves[entryCurve.first];
                }
                else
                {
                    auto curvePathInAnim = entryCurve.second.AppendProperty(entryCurve.first);
                    auto itrCurveEvent = curveEvents.find(curvePathInAnim);
                    if (itrCurveEvent != curveEvents.end())
                    {
                        auto curvePathInTgt = entry.first.AppendProperty(entryCurve.first);
                        curveEvents[curvePathInTgt] = IAnimCurve::CurveEventType::Updated;
                        changedCurves[entryCurve.first];

                        if (infinityChangedOnly.find(curvePathInAnim) != infinityChangedOnly.end())
                            infinityChangedOnly.insert(curvePathInTgt);
                    }
                }
            }

            for (auto& entryCurve : itr->second.curves)
            {
                auto itrNew = entry.second.curves.find(entryCurve.first);
                if (itrNew == entry.second.curves.end())
                {
                    curveEvents[entry.first.AppendProperty(entryCurve.first)] = IAnimCurve::CurveEventType::Removed;
                    changedCurves[entryCurve.first];
                }
            }

            updatePropIcon(entry.first, changedCurves);
        }

        // Push curve updated events
        std::vector<const char*> paths;

        for (auto& entry : curveEvents)
        {
            if (entry.second != IAnimCurve::CurveEventType::Updated)
                continue;

            paths.push_back(entry.first.GetText());
        }

        // for (auto& entry : animCurveNodes)
        //{
        //     for (auto& curveEntry : curveEvents)
        //     {
        //         if (curveEntry.first.GetPrimPath() != entry.first)
        //             continue;

        //        auto curvePathInNode = entry.first.AppendProperty(curveEntry.first.GetNameToken());
        //        paths.push_back(curvePathInNode.GetText());

        //        if (infinityChangedOnly.find(curveEntry.first) != infinityChangedOnly.end())
        //        {
        //            infinityChangedOnly.insert(curvePathInNode);
        //        }
        //    }
        //}

        auto iDir = carb::getCachedInterface<carb::dictionary::IDictionary>();

        if (!paths.empty())
        {
            carb::events::IEventPtr event =
                getEventStream()->createEvent(IAnimCurve::CurveEventType::Updated, carb::events::kGlobalSenderId);

            auto pathsItem = iDir->createItem(event->payload, "paths", carb::dictionary::ItemType::eBool);
            iDir->setStringArray(pathsItem, paths.data(), paths.size());

            auto updateInfosItem = iDir->createItem(event->payload, "updateInfos", carb::dictionary::ItemType::eBool);

            std::vector<std::string> updateInfos;

            for (auto path : paths)
            {
                if (infinityChangedOnly.find(SdfPath(path)) != infinityChangedOnly.end())
                {
                    updateInfos.push_back("infinity");
                }
                else
                {
                    updateInfos.push_back("");
                }
            }

            paths.clear();
            for (auto& str : updateInfos)
            {
                paths.push_back(str.c_str());
            }

            iDir->setStringArray(updateInfosItem, paths.data(), paths.size());

            getEventStream()->push(event.get());
        }

        // Push curve added events
        paths.clear();
        for (auto& entry : curveEvents)
        {
            if (entry.second != IAnimCurve::CurveEventType::Added)
                continue;

            paths.push_back(entry.first.GetText());
        }

        if (!paths.empty())
        {
            carb::events::IEventPtr event =
                getEventStream()->createEvent(IAnimCurve::CurveEventType::Added, carb::events::kGlobalSenderId);

            auto pathsItem = iDir->createItem(event->payload, "paths", carb::dictionary::ItemType::eBool);
            iDir->setStringArray(pathsItem, paths.data(), paths.size());

            getEventStream()->push(event.get());
        }

        // Push curve removed events
        paths.clear();
        for (auto& entry : curveEvents)
        {
            if (entry.second != IAnimCurve::CurveEventType::Removed)
                continue;

            paths.push_back(entry.first.GetText());
        }

        if (!paths.empty())
        {
            carb::events::IEventPtr event =
                getEventStream()->createEvent(IAnimCurve::CurveEventType::Removed, carb::events::kGlobalSenderId);

            auto pathsItem = iDir->createItem(event->payload, "paths", carb::dictionary::ItemType::eBool);
            iDir->setStringArray(pathsItem, paths.data(), paths.size());

            getEventStream()->push(event.get());
        }

        getEventStream()->pump();

        // Cache target prim changes for later use
        for (auto& entry : oldTgtPrims)
        {
            // Check if a curve is removed
            auto itr = tgtPrims.find(entry.first);

            for (auto& curve : entry.second.curves)
            {
                if (itr == tgtPrims.end() || itr->second.curves.find(curve.first) == itr->second.curves.end())
                    changedTgtPrimCurves.push_back({ entry.first.AppendProperty(curve.first), false });
            }
        }

        for (auto& entry : tgtPrims)
        {
            // Check if a curve is added
            auto itr = oldTgtPrims.find(entry.first);

            for (auto& curve : entry.second.curves)
            {
                if (itr == oldTgtPrims.end() || itr->second.curves.find(curve.first) == itr->second.curves.end())
                    changedTgtPrimCurves.push_back({ entry.first.AppendProperty(curve.first), true });
            }
        }
    }

    bool getInterpolatedValue(const omni::anim::IAnimCurve::Curve& curve, double time, double& interpolatedValue) const
    {
        extern bool getInterpolatedValue(const std::vector<AnimationSchemaAnimationCurve::Key>& curveKeys,
                                         adsk::InfinityType preInfinityType, adsk::InfinityType postInfinityType,
                                         double time, double& interpolatedValue);


        auto& keys = curve.overridenKeys.empty() ? curve.keys : curve.overridenKeys;
        return getInterpolatedValue(keys, infinityTypeMap.find(curve.preInfinityType)->second,
                                    infinityTypeMap.find(curve.postInfinityType)->second, time, interpolatedValue);
    }

    void onAppUpdate(carb::events::IEvent* e)
    {
        auto curvePaths = std::move(this->changedTgtPrimCurves);
        if (curvePaths.empty())
            return;

        auto stage = omni::usd::UsdContext::getContext()->getStage();
        if (!stage)
            return;

        UsdEditContext editContext(stage, stage->GetEditTargetForLocalLayer(stage->GetSessionLayer()));

        SdfChangeBlock changeBlock;

        for (auto& curvePath : curvePaths)
        {
            static TfToken customDataKey("nonpersistant");
            auto pathStr = curvePath.path.GetString();

            auto attrPath = SdfPath(TfStringGetBeforeSuffix(curvePath.path.GetString(), ':'));
            auto attr = stage->GetAttributeAtPath(SdfPath(attrPath));
            if (!attr)
                continue;

            if (curvePath.added)
            {
                attr.SetCustomDataByKey(customDataKey, VtValue(true));
            }
            else
            {
                attr.ClearDefault();
                attr.ClearCustomDataByKey(customDataKey);

                auto layer = stage->GetSessionLayer();
                layer->RemovePropertyIfHasOnlyRequiredFields(layer->GetPropertyAtPath(attrPath));
                layer->RemovePrimIfInert(layer->GetPrimAtPath(attrPath.GetPrimPath()));
            }
        }
    }
};


std::unique_ptr<AnimCurveMain> animCurveMain;

std::vector<SdfPath> getCurvePrims(const SdfPath& prim)
{
    return animCurveMain->getCurvePrims(prim);
}

std::map<TfToken, const omni::anim::IAnimCurve::Curve*> getCurves(const SdfPath& prim, bool mustBeAnimData = false)
{
    return animCurveMain->getCurves(prim, mustBeAnimData);
}

CARB_EXPORT void carbOnPluginStartup()
{
    animCurveMain.reset(new AnimCurveMain);
    INITIALIZE_OGN_NODES();

    // Node renaming
    auto computeGraph = carb::getCachedInterface<omni::graph::core::ComputeGraph>();
    if (computeGraph)
    {
        auto iNodeTypeForwarding = computeGraph->getNodeTypeForwardingInterface();
        if (iNodeTypeForwarding)
        {
            for (int i = 5; i >= 0; --i)
            {
                iNodeTypeForwarding->defineForward(
                    "omni.anim.curve.AnimCurve", i, "omni.anim.curve.core.AnimCurve", i, "omni.anim.curve.core");
            }
        }
    }
}

CARB_EXPORT void carbOnPluginShutdown()
{
    RELEASE_OGN_NODES();
    animCurveMain.reset();
}

// carbonite interface for this plugin (may contain multiple compute nodes)
bool isUpdatingUsd()
{
    return animCurveMain->isUpdatingUsd();
}

carb::events::IEventStream* getEventStream()
{
    return animCurveMain->getEventStream();
}

bool isAttrSupported(const SdfPath& attrPath)
{
    auto stage = omni::usd::UsdContext::getContext()->getStage();
    if (!stage)
        return false;

    auto attr = stage->GetAttributeAtPath(attrPath);

    if (attr.GetVariability() != SdfVariabilityVarying)
        return false;

    extern bool isValueTypeSupported(const TfType& type);
    if (isValueTypeSupported(attr.GetTypeName().GetType()))
        return true;

    if (attr.GetTypeName() == SdfValueTypeNames->Token)
    {
        VtTokenArray tokens;
        attr.GetMetadata(SdfFieldKeys->AllowedTokens, &tokens);
        if (!tokens.empty())
            return true;
    }

    return false;
}

bool evaluate(const pxr::SdfPath& curvePath, double time, double& value)
{
    return animCurveMain->evaluate(curvePath, time, value);
}

void updateTgtPrim(const SdfPath& prim,
                   const std::map<TfToken, double>& curveValues,
                   const omni::graph::core::GraphContextObj& graphContextObj)
{
    animCurveMain->updateTgtPrim(prim, curveValues, graphContextObj);
}

bool setOverridenKeys(const pxr::SdfPath& curvePath, const std::vector<pxr::AnimationSchemaAnimationCurve::Key>& keys)
{
    return animCurveMain->setOverridenKeys(curvePath, keys);
}

void pumpKeysOverridenEvent(const std::vector<SdfPath>& curvePaths)
{
    animCurveMain->pumpKeysOverridenEvent(curvePaths);
}

std::vector<SdfPath> getCurveNodes(const pxr::SdfPath& prim /*, const pxr::SdfPath& animData*/)
{
    return animCurveMain->getCurveNodes(prim /*, animData*/);
}

bool convertToAttrPrecision(const pxr::SdfPath& attrPath, double& value)
{
    auto stage = omni::usd::UsdContext::getContext()->getStage();
    if (!stage)
        return false;

    auto attr = stage->GetAttributeAtPath(attrPath);
    if (!attr)
        return false;

    extern bool convertToAttrPrecision(const UsdAttribute& attr, double& value);

    return convertToAttrPrecision(attr, value);
}

void fillInterface(omni::anim::IAnimCurve& iface)
{
    iface = { isUpdatingUsd,
              getEventStream,
              getCurvePrims,
              [](const pxr::SdfPath& prim) { return getCurves(prim); },
              pumpKeysOverridenEvent,
              isAttrSupported,
              evaluate,
              []() { return ticksPerSec; },
              getCurveNodes,
              nullptr,
              setOverridenKeys,
              convertToAttrPrecision,
              omni::anim::simplifyCatmull };
}
