// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#pragma once
#include "StageAttributeAccess.h"
#include <pxr/usd/usd/stage.h>
#include <limits>
#include <memory>
#include <mutex>

namespace omni::anim::shared::stage
{
// Extension-local binding to Kit's already-populated ovstage. Kit owns the
// provider and publication; phases collect owned edits for Kit to commit.
// Attach/detach calls remain serialized by the owning extension.
class AnimationStage
{
    class State;
public:
    struct View
    {
        StageAccess* instance;
        ovstage_ordinal_t readOrdinal;
        ovstage_ordinal_t writeOrdinal;
    };
    class Phase
    {
    public:
        ~Phase();
        Phase(const Phase&) = delete;
        Phase& operator=(const Phase&) = delete;
        View view() const;
        void finish();
    private:
        friend class AnimationStage;
        Phase(std::shared_ptr<State> state, double timeCode);
        std::shared_ptr<State> m_state;
        std::unique_lock<std::recursive_mutex> m_lock;
        bool m_finished = false;
    };
    AnimationStage() = default;
    ~AnimationStage();
    AnimationStage(const AnimationStage&) = delete;
    AnimationStage& operator=(const AnimationStage&) = delete;
    void attach(const PXR_NS::UsdStageRefPtr& source,
                double timeCode = std::numeric_limits<double>::quiet_NaN());
    void detach();
    explicit operator bool() const { return bool(m_state); }
    Phase begin(double timeCode = std::numeric_limits<double>::quiet_NaN()) const;
private:
    // A phase retains state through completion if its owner detaches. This
    // ownership is entirely local to the extension, with no exported interface.
    std::shared_ptr<State> m_state;
};
} // namespace omni::anim::shared::stage
