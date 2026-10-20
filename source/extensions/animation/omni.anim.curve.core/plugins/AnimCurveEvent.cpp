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

#include "AnimCurveEvent.h"

#include "IAnimCurve.h"

#include <carb/logging/Log.h>

using namespace pxr;

void _PushAttrEvent(carb::events::IEventStream* eventStream,
                    omni::anim::IAnimCurve::CurveEventType targetType,
                    const SdfPath& primPath,
                    const TfToken& attrToken,
                    const omni::anim::IAnimCurve::CurveEventType* sourceTypes)
{
    // get paths
    std::vector<const char*> paths;
    std::string primPathStr = primPath.GetString();
    std::string attrTokenStr = attrToken.GetString();
    std::string channelStr[4] = { ":x", ":y", ":z", ":w" };
    std::string messageStr[4];
    for (int i = 0; i < 4; i++)
    {
        if (sourceTypes[i] == targetType)
        {
            messageStr[i] = primPathStr + "." + attrTokenStr + channelStr[i];
            paths.push_back(messageStr[i].c_str());
        }
    }

    if (paths.size() == 0)
    {
        // no channel is effective. push is not necessary.
        return;
    }

    // send paths in event
    carb::events::IEventPtr event = eventStream->createEvent(targetType, carb::events::kGlobalSenderId);
    carb::dictionary::IDictionary* iDir = carb::getCachedInterface<carb::dictionary::IDictionary>();
    carb::dictionary::Item* item = iDir->createItem(event->payload, "paths", carb::dictionary::ItemType::eBool);
    iDir->setStringArray(item, paths.data(), paths.size());
    eventStream->push(event.get());
}

void _PushAttrAddedEvent(carb::events::IEventStream* eventStream,
                         const SdfPath& primPath,
                         const TfToken& attrToken,
                         const omni::anim::IAnimCurve::CurveEventType* sourceTypes)
{
    _PushAttrEvent(eventStream, omni::anim::IAnimCurve::CurveEventType::Added, primPath, attrToken, sourceTypes);
}

void _PushAttrRemovedEvent(carb::events::IEventStream* eventStream,
                           const SdfPath& primPath,
                           const TfToken& attrToken,
                           const omni::anim::IAnimCurve::CurveEventType* sourceTypes)
{
    _PushAttrEvent(eventStream, omni::anim::IAnimCurve::CurveEventType::Removed, primPath, attrToken, sourceTypes);
}

void _PushAttrUpdatedEvent(carb::events::IEventStream* eventStream,
                           const SdfPath& primPath,
                           const TfToken& attrToken,
                           const omni::anim::IAnimCurve::CurveEventType* sourceTypes)
{
    _PushAttrEvent(eventStream, omni::anim::IAnimCurve::CurveEventType::Updated, primPath, attrToken, sourceTypes);
}

void _PushPrimEvent(carb::events::IEventStream* eventStream,
                    const SdfPath& primPath,
                    const omni::anim::IAnimCurve::CurveEventType& et)
{
    // send paths in event
    carb::events::IEventPtr event = eventStream->createEvent(et, carb::events::kGlobalSenderId);
    carb::dictionary::IDictionary* iDir = carb::getCachedInterface<carb::dictionary::IDictionary>();
    carb::dictionary::Item* item = iDir->createItem(event->payload, "paths", carb::dictionary::ItemType::eBool);
    std::vector<const char*> paths;
    // paths only has 1 element
    paths.push_back(primPath.GetText());
    iDir->setStringArray(item, paths.data(), paths.size());
    eventStream->push(event.get());
}

void PushPrimAddedEvent(carb::events::IEventStream* eventStream, const SdfPath& primPath)
{
#ifdef _DEBUG
    CARB_LOG_WARN("Pushing anim prim-added event: %s", primPath.GetText());
#endif
    _PushPrimEvent(eventStream, primPath, omni::anim::IAnimCurve::CurveEventType::Added);
}

void PushPrimRemovedEvent(carb::events::IEventStream* eventStream, const SdfPath& primPath)
{
#ifdef _DEBUG
    CARB_LOG_WARN("Pushing anim prim-removed event: %s", primPath.GetText());
#endif
    _PushPrimEvent(eventStream, primPath, omni::anim::IAnimCurve::CurveEventType::Removed);
}

void PushPrimUpdatedEvent(carb::events::IEventStream* eventStream, const SdfPath& primPath)
{
#ifdef _DEBUG
    CARB_LOG_WARN("Pushing anim prim-updated event: %s", primPath.GetText());
#endif
    _PushPrimEvent(eventStream, primPath, omni::anim::IAnimCurve::CurveEventType::Updated);
}

void PushPrimAttrUpdatedEvent(carb::events::IEventStream* eventStream,
                              const SdfPath& primPath,
                              const AnimAttrsEventType& aaet)
{
    for (auto it = aaet.begin(); it != aaet.end(); it++)
    {
        pxr::TfToken attrToken = it->first;
        const omni::anim::IAnimCurve::CurveEventType* cet = it->second;

#ifdef _DEBUG
        for (int i = 0; i < 4; i++)
        {
            const char* channelChar[] = { "x", "y", "z", "w" };
            const char* actChar[] = { "added", "removed", "updated" };
            if (cet[i] == -1)
            {
                continue;
            }

            CARB_LOG_WARN("Pushing anim attr-%s event: %s.%s:%s", actChar[cet[i]], primPath.GetText(),
                          attrToken.GetText(), channelChar[i]);
        }
        // CARB_LOG_WARN("Pushing anim attr-*** event: %s, %i, %i, %i, %i", attrToken.GetText(), cet[0], cet[1], cet[2],
        // cet[3]);
#endif

        // conditionally push attr events
        _PushAttrAddedEvent(eventStream, primPath, attrToken, cet);
        _PushAttrRemovedEvent(eventStream, primPath, attrToken, cet);
        _PushAttrUpdatedEvent(eventStream, primPath, attrToken, cet);
    }
}


void PushKeyAddedEvent(carb::events::IEventStream* eventStream)
{
    // nop currently
}
void PushKeyRemovedEvent(carb::events::IEventStream* eventStream)
{
    // nop currently
}
void PushKeyUpdatedEvent(carb::events::IEventStream* eventStream)
{
    // nop currently
}
