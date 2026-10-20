// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#include "AnimationStage.h"
#include "StageAttributeAccess.h"
#include <pxr/usd/usdUtils/stageCache.h>
#include <stdexcept>

namespace omni::anim::shared::stage
{
class AnimationStage::State
{
public:
    uint64_t m_stageId = 0;
    StageAccess m_access;
    std::recursive_mutex m_mutex;
    bool m_active = false;

    void bind()
    {
        if (!m_access.stage || !m_access.stage->IsValid())
        {
            m_access = {};
            m_access.stage = usdrt::ovstage::Stage::Attach(m_stageId);
            if (!m_access.stage) throw std::runtime_error("Kit has not published this stage's ovstage binding yet");

        }
        if (!m_access.stage->IsReadReady()) throw std::runtime_error("Kit ovstage is updating; retry on the next update");
        m_access.generation = m_access.stage->GetGeneration();
        m_access.ordinal = m_access.stage->GetSealedOrdinal();
        m_access.edits.clear();
    }
    void submit()
    {
        AttributeAccess(&m_access).checkFrame();
        if (!m_access.edits.empty() && !m_access.stage->SetBatchForFrame(
            m_access.edits.data(),m_access.edits.size(),m_access.generation,m_access.ordinal))
            throw std::runtime_error("Kit rejected the animation batch for this stage generation/frame");
    }
};
AnimationStage::~AnimationStage() = default;
void AnimationStage::attach(const PXR_NS::UsdStageRefPtr& source, double /*timeCode*/)
{
    detach();
    if (!source) throw std::invalid_argument("Cannot bind an empty stage");
    const auto id = PXR_NS::UsdUtilsStageCache::Get().GetId(source);
    if (!id.IsValid()) throw std::invalid_argument("The stage must have a Kit stage-cache identity");
    m_state = std::make_shared<State>();
    m_state->m_stageId = uint64_t(id.ToLongInt());

    // OPENED can precede Kit's population publication. Resolve lazily at begin(),
    // and resolve again after Kit revokes/replaces a provider generation.
}
void AnimationStage::detach() { m_state.reset(); }
AnimationStage::Phase AnimationStage::begin(double timeCode) const
{
    if (!m_state) throw std::logic_error("Animation stage is not attached");
    return Phase(m_state,timeCode);
}
AnimationStage::Phase::Phase(std::shared_ptr<State> state, double /*timeCode*/)
    : m_state(std::move(state)), m_lock(m_state->m_mutex)
{
    if (m_state->m_active) throw std::logic_error("Nested stage phases are unsupported");
    m_state->bind();
    m_state->m_active = true;
}
AnimationStage::Phase::~Phase()
{
    if (!m_finished)
    {
        // Unsubmitted edits are local owned values and can be discarded safely.
        m_state->m_access.edits.clear();
        m_state->m_active = false;
    }
}
AnimationStage::View AnimationStage::Phase::view() const
{
    if (m_finished) throw std::logic_error("Animation stage phase is closed");
    return {&m_state->m_access,m_state->m_access.ordinal,m_state->m_access.ordinal};
}
void AnimationStage::Phase::finish()
{
    if (m_finished) throw std::logic_error("Animation stage phase is closed");
    m_state->submit();
    m_state->m_access.edits.clear();
    m_state->m_active = false;
    m_finished = true;
    m_lock.unlock();
}

} // namespace omni::anim::shared::stage
