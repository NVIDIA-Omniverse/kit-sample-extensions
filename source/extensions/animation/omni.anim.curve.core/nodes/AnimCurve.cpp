// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

#include "../plugins/IAnimCurve.h"

#include <animationSchema/animationCurveAPI.h>
#include <omni/fabric/IFabric.h>
#include <omni/fabric/IToken.h>
#include <omni/fabric/stage/StageReaderWriterUsd.h>
#include <omni/timeline/ITimeline.h>

#include <AnimCurveDatabase.h>
#include <regex>

using namespace omni;

constexpr double oldInfTime = 1.79769e+308;

class AnimCurve : protected carb::events::IEventListener
{
public:
    static bool updateNodeVersion(const GraphContextObj& context, const NodeObj& node, int oldVersion, int newVersion)
    {
        if (newVersion >= 2 && oldVersion < 2)
        {
            // Set time to nan if time is oldInfTime
            auto stageId = context.iContext->getStageId(context);
            auto stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
            if (!stage)
                return true;

            auto prim = stage->GetPrimAtPath(SdfPath(node.iNode->getPrimPath(node)));
            if (!prim)
                return true;

            bool isOldInfTime = false;
            bool foundValue = false;

            // Get time from layer to avoid TCPS and layer offset.
            auto& primIndex = prim.GetPrimIndex();
            for (const PcpNodeRef& node : primIndex.GetNodeRange())
            {
                for (auto layer : node.GetLayerStack()->GetLayers())
                {
                    auto primSpec = layer->GetPrimAtPath(node.GetPath());
                    if (!primSpec)
                        continue;

                    auto attrSpec = primSpec->GetAttributeAtPath(
                        primSpec->GetPath().AppendProperty(TfToken(AnimCurveAttributes::inputs::Time.name())));
                    if (!attrSpec)
                        continue;

                    if (!attrSpec->HasDefaultValue())
                        continue;

                    auto time = attrSpec->GetDefaultValue().Get<SdfTimeCode>();
                    isOldInfTime = time == oldInfTime;
                    foundValue = true;
                    break;
                }

                if (foundValue)
                    break;
            }

            if (!isOldInfTime)
            {
                auto animCurve = new AnimCurve;
                node.iNode->setUserData(node, animCurve);

                animCurve->needSetUseGlobalTimeFalse = true;
            }
        }

        do
        {
            // Copy curve data from animation data to curve node
            if (oldVersion >= 5)
                break;

            auto stageId = context.iContext->getStageId(context);
            auto stage = UsdUtilsStageCache::Get().Find(UsdStageCache::Id::FromLongInt(stageId));
            if (!stage)
                break;

            auto prim = stage->GetPrimAtPath(SdfPath(node.iNode->getPrimPath(node)));
            if (!prim)
                break;

            auto rel = prim.GetRelationship(TfToken("inputs:AnimData"));
            if (!rel)
                break;

            rel.SetHidden(true);

            SdfPathVector paths;
            rel.GetTargets(&paths);

            if (paths.empty())
                break;

            auto animDataPrim = stage->GetPrimAtPath(paths[0]);
            if (!animDataPrim)
                break;

            SdfChangeBlock changeBlock;

            auto curveApi = AnimationSchemaAnimationCurveAPI(animDataPrim);
            auto curveNames = curveApi.GetCurves();
            for (auto curveName : curveNames)
            {
                for (auto prop : animDataPrim.GetAuthoredPropertiesInNamespace(curveName))
                {
                    prop.FlattenTo(prim);
                }
            }
        } while (false);

        return oldVersion < newVersion;
    }

    static void initialize(const GraphContextObj& context, const NodeObj& nodeObj)
    {
        auto animCurve = (AnimCurve*)nodeObj.iNode->getUserData(nodeObj);
        if (!animCurve)
        {
            animCurve = new AnimCurve;
            nodeObj.iNode->setUserData(nodeObj, animCurve);
        }

        if (animCurve->needSetUseGlobalTimeFalse)
        {
            auto attr = nodeObj.iNode->getAttribute(nodeObj, "inputs:UseGlobalTime");
            auto dataHandle = attr.iAttribute->getAttributeDataHandle(attr, kAuthoringGraphIndex);
            void* data = nullptr;
            context.iAttributeData->getDataW(&data, context, &dataHandle, 1);
            *(bool*)data = false;
        }

        auto individualOutputsAttr =
            nodeObj.iNode->getAttributeByToken(nodeObj, AnimCurveAttributes::inputs::IndividualOutputs.token());
        individualOutputsAttr.iAttribute->registerValueChangedCallback(individualOutputsAttr, onValueChanged, true);

        extern carb::events::IEventStream* getEventStream();
        animCurve->eventSub =
            getEventStream()->createSubscriptionToPop(animCurve, carb::events::kDefaultOrder, "AnimCurve");

        // Hides attribute of old node
        if (nodeObj.iNode->getAttributeExists(nodeObj, "inputs:AnimData"))
        {
            auto animDataAttr = nodeObj.iNode->getAttribute(nodeObj, "inputs:AnimData");
            animDataAttr.iAttribute->setMetadata(animDataAttr, "hidden", "true");
        }

        // Hides curve data attributes
        auto attrCount = nodeObj.iNode->getAttributeCount(nodeObj);
        std::vector<AttributeObj> attrs;
        attrs.resize(attrCount);
        nodeObj.iNode->getAttributes(nodeObj, attrs.data(), attrs.size());
        for (auto& attr : attrs)
        {
            auto name = attr.iAttribute->getName(attr);
            if (TfStringStartsWith(name, "inputs:") || TfStringStartsWith(name, "outputs:") ||
                TfStringStartsWith(name, "outputs_"))
                continue;

            attr.iAttribute->setMetadata(attr, "hidden", "true");
        }
    }

    static void release(const NodeObj& nodeObj)
    {
        auto animCurve = (AnimCurve*)nodeObj.iNode->getUserData(nodeObj);
        nodeObj.iNode->setUserData(nodeObj, nullptr);
        delete animCurve;
    }

    static bool compute(AnimCurveDatabase& db)
    {
        auto animCurve = (AnimCurve*)db.abi_node().iNode->getUserData(db.abi_node());
        return animCurve->computeInternal(db);
    }

protected:
    typedef std::map<TfToken, double> CurveValues;

    SdfPath animDataPath;
    bool animDataResync = true;
    bool individualOutputsStrChanged = true;
    bool needSetUseGlobalTimeFalse = false;
    std::set<TfToken> changedCurves;
    std::vector<std::regex> regexes;
    double lastTime = std::numeric_limits<double>::quiet_NaN();
    carb::ObjectPtr<carb::events::ISubscription> eventSub;

    virtual void onEvent(carb::events::IEvent* e) override
    {
        auto iDir = carb::getCachedInterface<carb::dictionary::IDictionary>();
        auto item = iDir->getItem(e->payload, "paths");
        if (!item)
            return;

        std::vector<const char*> pathStrs;
        pathStrs.resize(iDir->getArrayLength(item));

        iDir->getStringBufferArray(item, pathStrs.data(), pathStrs.size());

        for (auto& str : pathStrs)
        {
            auto path = SdfPath(str);
            if (path.GetPrimPath() == animDataPath)
            {
                if (path.IsPrimPath())
                {
                    animDataResync = true;
                    return;
                }
                else
                    changedCurves.insert(path.GetNameToken());
            }
        }
    }

    virtual size_t addRef() override
    {
        return 1;
    }
    virtual size_t release() override
    {
        return 1;
    }

    bool isCurveChanged(const TfToken& curveName) const
    {
        if (animDataResync)
            return true;

        return changedCurves.find(curveName) != changedCurves.end();
    }

    CurveValues evaluateCurves(AnimCurveDatabase& db, double time)
    {
        // Prepare for evaluation
        if (changedCurves.empty() && !animDataResync && time == lastTime && !individualOutputsStrChanged)
            return {};

        // if (!db.inputs.AnimData.isValid())
        //     return {};

        // if (std::strlen(db.inputs.AnimData.path()) == 0)
        //     return {};

        long stageId = db.abi_context().iContext->getStageId(db.abi_context());
        auto stage = UsdUtilsStageCache::Get().Find(pxr::UsdStageCache::Id::FromLongInt(stageId));
        if (!stage)
            return {};

        if (animDataPath.IsEmpty())
            animDataPath = SdfPath(db.abi_node().iNode->getPrimPath(db.abi_node()));

        extern std::map<TfToken, const omni::anim::IAnimCurve::Curve*> getCurves(
            const SdfPath& prim, bool mustBeAnimData);
        auto curves = getCurves(animDataPath, true);

        std::map<TfToken, double> curveValues;
        for (auto& curve : curves)
        {
            // Check if it's necessary to update.
            if (!isCurveChanged(curve.first) && time == lastTime && !individualOutputsStrChanged)
                continue;

            extern bool evaluate(const pxr::SdfPath& curvePath, double time, double& value);
            double value;
            const auto ret = evaluate(animDataPath.AppendProperty(curve.first), time, value);
            if (!ret)
                continue;

            curveValues[curve.first] = value;
        }

        return curveValues;
    }

    void updateOutputBundle(AnimCurveDatabase& db, const CurveValues& curveValues)
    {
        // Add curve value to bundle
        auto& animFrame = db.outputs.AnimFrame();

        for (auto& curveEntry : curveValues)
        {
            omni::graph::core::NameToken hAttrName(curveEntry.first.GetText());
            const graph::core::Type doubleType(graph::core::BaseDataType::eDouble);
            auto nodeAttr = animFrame.addAttribute(hAttrName, doubleType);
            *nodeAttr.getCpu<double>() = curveEntry.second;
        }

        // Remove curves that are changed but not evaluated.
        if (changedCurves.empty() && !animDataResync)
            return;

        std::vector<omni::graph::core::NameToken> invalidCurveNames;

        for (auto& curveAttr : animFrame)
        {
            TfToken name(curveAttr.name().getText());
            if (isCurveChanged(name) && curveValues.find(name) == curveValues.end())
                invalidCurveNames.push_back(curveAttr.name());
        }
        if (invalidCurveNames.size() > 0)
            animFrame.removeAttributes(invalidCurveNames.size(), invalidCurveNames.data());
    }

    void updateIndividualOutputValues(AnimCurveDatabase& db, const CurveValues& curveValues)
    {
        for (auto& [curveName, value] : curveValues)
        {
            auto attrName = std::string("outputs:") + curveName.GetText();
            if (!db.abi_node().iNode->getAttributeExists(db.abi_node(), attrName.c_str()))
                continue;

            auto attrObj = db.abi_node().iNode->getAttribute(db.abi_node(), attrName.c_str());

            auto hAttrData = attrObj.iAttribute->getAttributeDataHandle(attrObj, db.getInstanceIndex());
            void* attrOut = nullptr;
            db.abi_context().iAttributeData->getDataW(&attrOut, db.abi_context(), &hAttrData, 1);
            *(double*)attrOut = value;
        }
    }

    bool computeInternal(AnimCurveDatabase& db)
    {
        // Resolve time
        double time;
        if (db.inputs.UseGlobalTime())
        {
            time = db.abi_context().iContext->getFrame(db.abi_context());
        }
        else
        {
            time = db.inputs.Time().GetValue();
        }

        // Evaluate curves
        auto tcps = carb::getCachedInterface<omni::timeline::ITimeline>()->getTimeline()->getTimeCodesPerSecond();

        time = time / tcps;
        CurveValues curveValues = evaluateCurves(db, time);

        // Update output bundle
        updateOutputBundle(db, curveValues);

        // Update individual outputs
        updateIndividualOutputValues(db, curveValues);

        // Set attributes to prim
        SdfPath tgtPath;
        if (!db.inputs.Prim().empty())
        {
            std::string pathStr = db.inputs.Prim()[0].getString();
            if (SdfPath::IsValidPathString(pathStr))
            {
                tgtPath = SdfPath(pathStr);
            }
        }
        if (!curveValues.empty() && !tgtPath.IsEmpty())
        {
            extern void updateTgtPrim(
                const SdfPath& prim, const std::map<TfToken, double>& curveValues, const GraphContextObj&);
            updateTgtPrim(tgtPath, curveValues, db.abi_context());
        }

        // Reset timeData
        animDataResync = false;
        changedCurves.clear();
        individualOutputsStrChanged = false;
        lastTime = time;

        return true;
    }

    void updateIndividualOutputs(const NodeObj& nodeObj, const std::string& patternStr) const
    {
        // Create regular expressions
        std::vector<std::regex> regexes;

        auto patternStrs = TfStringTokenizeToSet(patternStr, " \t\n,;");
        for (auto& str : patternStrs)
        {
            std::string regexStr;
            regexStr += "^";
            for (auto& ch : str)
            {
                switch (ch)
                {
                case '?':
                    regexStr.push_back('.');
                    break;
                case '*':
                    regexStr += ".*";
                    break;
                default:
                    regexStr.push_back(ch);
                }
            }
            regexStr += "$";

            regexes.push_back(std::regex(regexStr, std::regex_constants::icase | std::regex_constants::optimize));
        }

        auto matchCurveName = [&](const char* name)
        {
            for (auto& regex : regexes)
            {
                if (std::regex_search(name, regex))
                {
                    return true;
                }
            }

            return false;
        };

        // Remove outputs
        std::vector<AttributeObj> attrs;
        attrs.resize(nodeObj.iNode->getAttributeCount(nodeObj));
        nodeObj.iNode->getAttributes(nodeObj, attrs.data(), attrs.size());
        for (auto& attrObj : attrs)
        {
            if (attrObj.iAttribute->getPortType(attrObj) != AttributePortType::kAttributePortType_Output ||
                attrObj.iAttribute->getResolvedType(attrObj) != Type(omni::graph::core::BaseDataType::eDouble))
                continue;

            std::string fullAttrName = attrObj.iAttribute->getName(attrObj);
            auto curveName = fullAttrName.substr(std::string("outputs:").length());

            if (!matchCurveName(curveName.c_str()))
            {
                if (attrObj.iAttribute->getDownstreamConnectionCount(attrObj) == 0)
                    nodeObj.iNode->removeAttribute(nodeObj, fullAttrName.c_str());
            }
        }

        // Add outputs
        extern std::map<TfToken, const omni::anim::IAnimCurve::Curve*> getCurves(
            const SdfPath& prim, bool mustBeAnimData = false);

        auto nodePath = SdfPath(nodeObj.iNode->getPrimPath(nodeObj));

        auto curves = getCurves(nodePath);
        for (auto& curve : curves)
        {
            if (!matchCurveName(curve.first.GetText()))
                continue;

            double value = 0;

            nodeObj.iNode->createAttribute(
                nodeObj, curve.first.GetText(), graph::core::Type(graph::core::BaseDataType::eDouble), &value, nullptr,
                graph::core::kAttributePortType_Output, graph::core::kExtendedAttributeType_Regular, nullptr);
        }
    }

    void onAttrChanged(const AttributeObj& attrObj, const void* value)
    {
        const std::string attrName = attrObj.iAttribute->getName(attrObj);
        if (attrName == AnimCurveAttributes::inputs::IndividualOutputs.name())
        {
            individualOutputsStrChanged = true;

            auto nodeObj = attrObj.iAttribute->getNode(attrObj);
            auto graphObj = nodeObj.iNode->getGraph(nodeObj);
            auto contextObj = graphObj.iGraph->getDefaultGraphContext(graphObj);
            size_t elementCount = 0;
            auto dataHandle = attrObj.iAttribute->getConstAttributeDataHandle(attrObj, kAuthoringGraphIndex);
            contextObj.iAttributeData->getElementCount(&elementCount, contextObj, &dataHandle, 1);

            auto str = std::string(*((const char**)value), elementCount);

            updateIndividualOutputs(nodeObj, str);
        }
        // else if (attrName == AnimCurveAttributes::inputs::AnimData.name())
        //{
        //     animDataPath = SdfPath();
        //     animDataResync = true;
        // }
    }

    static void onValueChanged(const AttributeObj& attrObj, const void* value)
    {
        auto nodeObj = attrObj.iAttribute->getNode(attrObj);
        auto animCurve = (AnimCurve*)nodeObj.iNode->getUserData(nodeObj);
        animCurve->onAttrChanged(attrObj, value);
    }
};


REGISTER_OGN_NODE()
