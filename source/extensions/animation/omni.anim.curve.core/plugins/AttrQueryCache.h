// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once
#include <carb/eventdispatcher/IEventDispatcher.h>

using namespace pxr;

class UsdAttrQueryCache : public TfWeakBase
{
public:
    UsdAttrQueryCache();
    ~UsdAttrQueryCache();

    static UsdAttrQueryCache& get();

    const UsdAttributeQuery& getAttrQuery(const SdfPath& path);

protected:
    void onStageOpened();
    void onStageClosing();
    void handleNotice(const UsdNotice::ObjectsChanged& objectsChanged);

    static UsdAttrQueryCache* singleton;

    carb::eventdispatcher::ObserverGuard stageEventSub[2];
    UsdStageWeakPtr stage;
    TfNotice::Key noticeKey;
    std::map<SdfPath, UsdAttributeQuery> attrQueries;
};
