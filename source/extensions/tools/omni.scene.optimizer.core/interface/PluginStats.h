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

// Usd Optimize
#include <usd_optimize/core/Coalescer.h>
#include <usd_optimize/core/UsdIncludes.h> // needed *before* IStageUpdate to prevent issues

// Kit
#include <omni/kit/IStageUpdate.h>

// Carbonite
#include <carb/dictionary/IDictionary.h>
#include <carb/stats/Stats.h>

// C++
#include <atomic>
#include <map>
#include <mutex>
#include <set>

namespace omni::scene::optimizer
{


/// SO Stage Statistics handler
///
/// Helper class for the ISceneOptimizer interface to manage providing statistics to
/// carb::stats for the kit Statistics window.
///
/// This class listens for stage updates (new stage, prim added/modified/removed, playback
/// paused, etc.) and then runs the Scene Optimizer statistics gathering code. The results
/// are provided to carb::stats.
///
/// Note that currently adding or removing a property to/from a prim does not trigger
/// an update. Changing the value of an attribute however does.
///
/// Updates are coalesced to reduce the number of times stats are queried/updated, and
/// the logic is all gated on whether the Statistics window is actually open. On a large
/// scene, opening the window may result in a brief delay before the statistics populate,
/// as with other updates.
class StatsHandler
{

public:
    /// Constructor
    StatsHandler();

    /// Destructor
    ~StatsHandler();

    /// Set the stageId
    ///
    /// \param stageId Stage ID to collect stats for
    void setStageId(long int stageId);

    /// Toggle reset
    ///
    /// If \p reset is enabled then prior to collecting stats next time, all existing
    /// stat values will be reset to zero. This means when opening a new stage we can
    /// ensure values that won't exist in the new stage are cleared before updating
    /// the others - basically because we can't _remove_ existing stats. So we just
    /// set them to zero.
    ///
    /// \param reset Set the reset flag
    void setReset(bool reset);

    /// Toggle whether Scene Optimizer updates carb::stats.
    ///
    /// If \p enabled is true, start monitoring for stage updates and running Scene Optimizer
    /// stats collection to update carb::stats. Updates happen at various points - new stage,
    /// prim added/update/removed, playback paused/stopped.
    ///
    /// If \p enabled is false, unregister from stage updates and reset any carb stats to
    /// zero.
    ///
    /// \param enabled If true, enable stats.
    void toggleStats(bool enabled);

    /// Mark that we want to update stats.
    void triggerUpdate() const;

    /// Called after an update is triggered.
    void updateTriggered();

private:
    void createStat(const std::string& id,
                    const std::string& name,
                    const uint64_t value,
                    const std::string& parentId = std::string());

    void clearStats() const;

    void clearOldStats();

    carb::dictionary::SubscriptionId* m_statsSettingSubscriptionId = nullptr;
    std::atomic<long int> m_stageId = -1;
    std::atomic<bool> m_reset = false;
    std::mutex m_mutex;
    carb::stats::ScopeId m_scopeId = nullptr;
    std::map<std::string, carb::stats::StatId> m_stats;
    std::set<carb::stats::StatId> m_processed;
    omni::kit::StageUpdateNode* m_stageUpdateNode = nullptr;
    usd_optimize::CoalescerUPtr m_coalescer = nullptr;
};


} // namespace omni::scene::optimizer
