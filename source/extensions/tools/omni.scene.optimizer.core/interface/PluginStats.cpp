// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "PluginStats.h"

// Usd Optimize
#include <usd_optimize/core/Coalescer.h>
#include <usd_optimize/core/Log.h>
#include <usd_optimize/core/Stats.h>
#include <usd_optimize/core/UsdIncludes.h>

// Kit
#include <omni/timeline/ITimeline.h>

// Carbonite
#include <carb/settings/ISettings.h>

// USD
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usdUtils/stageCache.h>


PXR_NAMESPACE_USING_DIRECTIVE

namespace omni::scene::optimizer
{

// Core types (Coalescer, Stats collection helpers, etc.) are provided by the usd_optimize library.
using namespace usd_optimize;


// Delay to wait for more incoming events before triggering an update
constexpr std::chrono::milliseconds s_delay(500);


StatsHandler::StatsHandler()
{
    // Set up for updating stats. Gate this on IStageUpdate being available, as that's our mechanism
    // for responding and updating.
    if (carb::getCachedInterface<omni::kit::IStageUpdate>())
    {
        // We are very fortunate that the kit Statistics window updates a carb setting when its visibility
        // changes, which means we can use that to toggle whether we are updating stats or not to avoid
        // overhead if the window isn't open.
        const auto settings = carb::getCachedInterface<carb::settings::ISettings>();
        m_statsSettingSubscriptionId = settings->subscribeToNodeChangeEvents(
            "/profiler/enableDeviceUtilizationQuery",
            [](const carb::dictionary::Item* changedItem, carb::dictionary::ChangeEventType, void* _this)
            {
                const auto dictionary = carb::getCachedInterface<carb::dictionary::IDictionary>();
                static_cast<StatsHandler*>(_this)->toggleStats(dictionary->getAsBool(changedItem));
            },
            this);
    }
}


StatsHandler::~StatsHandler()
{
    // Clean up if we were monitoring stats - in particular the subscriptions.
    toggleStats(false);

    // Unsubscribe from settings change events
    if (m_statsSettingSubscriptionId)
    {
        const auto settings = carb::getCachedInterface<carb::settings::ISettings>();
        settings->unsubscribeToChangeEvents(m_statsSettingSubscriptionId);
        m_statsSettingSubscriptionId = nullptr;
    }
}


void StatsHandler::setStageId(long int stageId)
{
    m_stageId = stageId;
}


void StatsHandler::setReset(bool reset)
{
    m_reset = reset;
}


// Toggle whether we will respond to scene state changes and collect SO stats.
//
// The stats can be expensive to collect on larger scenes - far too expensive to be able
// to run them on-demand on the main thread in response to user input/scene changes. We
// can alleviate this by coalescing repeated events and deferring to a background thread,
// but even doing that will add a bunch of overhead each time a scene update is received.
// What we can do though is only handle stats if the kit statistics window is actually open.
// There will still be some overhead in order to handle them, but at least it's sort of opt-in
// and not permanently active.
void StatsHandler::toggleStats(bool enabled)
{

    // enabled=true means the statistics window has become visible, and we therefore
    // want to start providing data to carb stats.
    if (enabled)
    {
        // Create a coalescer. This is used to avoid triggering repeated stat updates
        // when say a user is interactively moving a prim, which fires many repeated
        // events.
        m_coalescer = std::make_unique<Coalescer>(std::bind(&StatsHandler::updateTriggered, this), s_delay);

        // Register for changes that mean we'd probably want to update the stats.
        omni::kit::StageUpdateNodeDescV2 desc = {};
        desc.displayName = "omni.scene.optimizer.core";
        desc.order = 99; // Some arbitrary number that is high to be "lower priority"

        // Set "this" as the userData so we can use it in the callbacks below.
        desc.userData = this;

        // Below we configure how to respond to various events - prims being added, etc.
        // Note that we want to ensure we do the absolute bare minimum possible in these
        // callbacks, as they can be called often and we are introducing overhead to all
        // of Kit.

        // USD stage opened
        // Note: when registering the update node this will always fire, meaning we don't
        // need to manually trigger an update for initial population.
        desc.onAttach = [](const long int stageId, double, void* userData)
        {
            static_cast<StatsHandler*>(userData)->setStageId(stageId);
            static_cast<StatsHandler*>(userData)->triggerUpdate();
        };

        // USD stage closed
        desc.onDetach = [](void* userData)
        {
            static_cast<StatsHandler*>(userData)->setStageId(-1);
            static_cast<StatsHandler*>(userData)->setReset(true);
            static_cast<StatsHandler*>(userData)->triggerUpdate();
        };

        // Prim added
        desc.onPrimAdd = [](const SdfPath&, void* userData) { static_cast<StatsHandler*>(userData)->triggerUpdate(); };

        // Prim/property change
        desc.onPrimOrPropertyChange = [](const SdfPath& primOrPropertyPath, void* userData)
        {
            // Skip updates triggered by the default camera to avoid unnecessary recomputation.
            static const SdfPath omniPerspective("/OmniverseKit_Persp");
            if (primOrPropertyPath == omniPerspective)
            {
                return;
            }

            static_cast<StatsHandler*>(userData)->triggerUpdate();
        };

        // Prim removed
        desc.onPrimRemove = [](const PXR_NS::SdfPath&, void* userData)
        { static_cast<StatsHandler*>(userData)->triggerUpdate(); };

        // Playback stopped
        desc.onStop = [](void* userData) { static_cast<StatsHandler*>(userData)->triggerUpdate(); };

        // Playback paused
        desc.onPause = [](void* userData) { static_cast<StatsHandler*>(userData)->triggerUpdate(); };

        // Create the stageUpdateNode to enable notifications
        const auto stageUpdate = carb::getCachedInterface<omni::kit::IStageUpdate>()->getStageUpdate();
        m_stageUpdateNode = stageUpdate->createStageUpdateNodeV2(desc);
    }
    else
    {
        // If we have a stageUpdateNode, destroy it to stop receiving notifications.
        if (m_stageUpdateNode)
        {
            const auto stageUpdate = carb::getCachedInterface<omni::kit::IStageUpdate>()->getStageUpdate();
            stageUpdate->destroyStageUpdateNode(m_stageUpdateNode);
            m_stageUpdateNode = nullptr;
        }

        // Then clean up the coalescer
        if (m_coalescer)
        {
            // Mark cancelled.
            // This will prevent any further triggers before we can wait/release it.
            m_coalescer->cancel();

            // Now - it is possible that there is an active thread on the coalescer. We don't want to block
            // waiting for it, though. Move the existing object to a thread, and if it is active we can wait
            // on that thread.  This means the object stays alive until that final thread wakes up and can
            // gracefully exit, while not blocking.
            std::thread(
                [](CoalescerUPtr&& coalescer)
                {
                    // Return. We are just allowing the unique_ptr to destruct on this thread,
                    // as it will wait().
                    return;
                },
                std::move(m_coalescer))
                .detach();

            // Set as null after moving, ready to go again if necessary.
            m_coalescer = nullptr;
        }

        // Clear stats. We are disabling so we don't know what will happen now, and the stats
        // window may be reopened. This (currently) happens on the main thread but is just
        // zeroing out the existing stats so hopefully isn't too bad.
        clearStats();
    }
}


// Schedule a stats update via the coalescer
void StatsHandler::triggerUpdate() const
{
    if (m_coalescer)
    {
        m_coalescer->trigger();
    }
}


// Create/update a carb stat
void StatsHandler::createStat(const std::string& id,
                              const std::string& name,
                              const uint64_t value,
                              const std::string& parentId)
{
    using namespace carb::stats;

    const auto iStats = carb::getCachedInterface<IStats>();

    // Find or insert.
    // Note: We can use iStats getOrCreate functions, but they state they are thread-safe
    // and have overhead. Caching them here should alleviate this somewhat, although we
    // purposely avoid doing anything per-frame anyway.
    auto statIdIt = m_stats.insert(std::make_pair(id, nullptr));

    // If we didn't find the id, create it
    if (statIdIt.second)
    {
        if (parentId.empty())
        {
            StatDesc statDesc{};
            statDesc.statName = id.c_str();
            statDesc.statDescription = name.c_str();
            statDesc.scopeId = m_scopeId;
            statDesc.type = StatType::eUint64;

            statIdIt.first->second = iStats->getOrCreateStat(statDesc);
        }
        else
        {
            auto parentIt = m_stats.find(parentId);
            if (parentIt == m_stats.end())
            {
                // Log coding error - this should only happen if we messed up the code
                USD_OPTIMIZE_LOG_WARN("Coding Error: parent should have been created first");
                return;
            }

            NestedStatDesc statDesc{};
            statDesc.statName = id.c_str();
            statDesc.statDescription = name.c_str();
            statDesc.scopeId = m_scopeId;
            statDesc.parentStatId = parentIt->second;
            statDesc.type = StatType::eUint64;

            statIdIt.first->second = iStats->getOrCreateNestedStat(statDesc);
        }
    }

    iStats->setStatUint64(statIdIt.first->second, value);

    // Track "current" stats we have processed
    m_processed.insert(statIdIt.first->second);
}


// Reset any registered stat to zero.
// Doesn't appear we can remove stats from carb, but at least we can zero them out.
void StatsHandler::clearStats() const
{
    const auto iStats = carb::getCachedInterface<carb::stats::IStats>();
    for (const auto& statIt : m_stats)
    {
        iStats->setStatUint64(statIt.second, 0);
    }
}


// Remove any stats that were not updated. This could mean that there is no
// longer data, for example a primvar was removed. We need to zero out the
// old stats (as we can't remove stats) and we can then remove them from
// the main stats map for next time.
void StatsHandler::clearOldStats()
{
    const auto iStats = carb::getCachedInterface<carb::stats::IStats>();

    for (auto statIt = m_stats.begin(); statIt != m_stats.end();)
    {
        if (m_processed.find(statIt->second) == m_processed.end())
        {
            iStats->setStatUint64(statIt->second, 0);
            m_stats.erase(statIt++);
        }
        else
        {
            ++statIt;
        }
    }

    m_processed.clear();
}


// The stats update has actually been requested after coalescing...
void StatsHandler::updateTriggered()
{
    // If there is no stageId or reset is explicitly enabled, then zero out any current
    // stats. This means on opening a new stage we won't have leftover values (e.g. when
    // the new stage doesn't have a prim type that existed in the previous stage).
    {
        std::lock_guard lock(m_mutex);
        if (m_stageId == -1 || m_reset)
        {
            clearStats();
            m_reset = false;

            // Now if there is no stageId for some reason (somehow no new stage attached?) then
            // early-out as there's nothing more to do.
            if (m_stageId == -1)
            {
                return;
            }
        }
    }

    // Get the current time
    UsdTimeCode timeCode = UsdTimeCode::Default();

    const auto iTimeline = carb::getCachedInterface<timeline::ITimeline>();
    if (iTimeline)
    {
        const auto timeline = iTimeline->getTimeline();
        timeCode = timeline->getCurrentTime() * timeline->getTimeCodesPerSecond();
    }

    // Get usd stage
    const auto& stageId = UsdStageCache::Id::FromLongInt(m_stageId);
    const UsdStageWeakPtr usdStage = UsdUtilsStageCache::Get().Find(stageId);

    // Collect stats.
    // Uses mostly default args, we don't currently want the more expensive stuff like disjoint meshes.
    StatArgs args;
    args.setTimeCode(timeCode);
    args.setCountPrimvars(true);
    const StatCountersUPtr stats = _collectSceneStats(usdStage, args);

    // Use a mutex at this point.
    // If the stats take time to collect, it's possible that this function is called again
    // before it completed. Collecting the stats is fine, the issue is that we could
    // potentially have older stats updated after newer ones. We also use a map to cache
    // the StatID's, so locking solves both those issues.
    std::lock_guard lock(m_mutex);

    // Ensure scope has been created
    if (m_scopeId == nullptr)
    {
        using namespace carb::stats;

        ScopeDesc scopeDesc{};
        scopeDesc.scopeName = "USD Stage (Scene Optimizer)";
        scopeDesc.scopeDescription = "Scene Optimizer USD stage statistics";
        scopeDesc.flags = kScopeFlagNone;

        m_scopeId = carb::getCachedInterface<IStats>()->getOrCreateScope(scopeDesc);

        // Sanity check.
        if (m_scopeId == nullptr)
        {
            USD_OPTIMIZE_LOG_WARN("Failed to create carb::stats Scope");
            return;
        }
    }

    // Reset processed stats - this will be updated each createStat call
    m_processed.clear();

    // Topology stats
    createStat("totalFaces", "# Faces", stats->faces);
    createStat("totalGeometries", "# Geometries", stats->geometries);
    createStat("totalVertices", "# Vertices", stats->vertices);

    // Totals
    // Parent stats have a value, but then add their children also. So we have to compensate
    // for that here by subtracting them, so it can add them again...
    const size_t total = stats->prims - stats->invisible - stats->inactive;
    createStat("totalPrims", "Total Prims", total);
    createStat("totalPrimsInvisible", "Invisible", stats->invisible, "totalPrims");
    createStat("totalPrimsInactive", "Inactive", stats->inactive, "totalPrims");

    // Instances
    createStat("totalInstances", "Instances", stats->instances);
    createStat("totalInstanceable", "Instanceable", stats->instanceable);
    createStat("totalPrototypes", "Instance Prototypes", stats->prototypes);

    uint64_t materials = 0;
    uint64_t materialsUnique = 0;
    uint64_t emptyLeaves = 0;

    // Per Type
    for (const auto& primTypeInfo : stats->primTypes)
    {
        const auto& perType = primTypeInfo.second;

        // Special cases
        if (primTypeInfo.first == "Material")
        {
            materials = perType.count;
            materialsUnique = perType.uniqueMaterials.size();
            continue;
        }

        // Accumulate any leaves
        if (perType.leaf)
        {
            emptyLeaves += perType.leaf;
        }

        std::string id = "type" + primTypeInfo.first;
        std::string name = "Type: " + primTypeInfo.first;
        createStat(id, name, perType.count);
    }

    // Materials
    createStat("totalMaterials", "Materials", materials);
    createStat("uniqueMaterials", "Materials (Unique)", materialsUnique);

    // Leaf
    createStat("leafPrims", "Empty Leaves", emptyLeaves);

    // Primvar Attr Counts
    createStat("primvarAttrs", "Primvar Attributes", 0);
    for (const auto& [name, info] : stats->primvars)
    {
        createStat("primvarAttr" + name.GetString(), name.GetString(), info.count, "primvarAttrs");
    }

    // Primvar Value Counts
    createStat("primvarValues", "Primvar Values", 0);
    for (const auto& [name, info] : stats->primvars)
    {
        createStat("primvarValue" + name.GetString(), name.GetString(), info.valueCount, "primvarValues");
    }

    // Clear any old statistics that were no longer included
    clearOldStats();
}


} // namespace omni::scene::optimizer
