// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#pragma once
#include "TransformAccess.h"
#include <mutex>
namespace omni::anim::shared::stage
{
class StageContext
{
public:
    void attach(const PXR_NS::UsdStageRefPtr& source)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        attachLocked(source);
    }
    void detach()
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_stage.detach();
        m_source = nullptr;
    }
    std::optional<Matrix> transform(const PXR_NS::UsdStageRefPtr& source, std::string_view path,
                                    bool local, double timeCode)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        attachLocked(source);
        if (!m_stage) return std::nullopt;
        auto phase = m_stage.begin(timeCode);
        std::optional<Matrix> result;
        try { result = readTransform(phase.view(), path, local); }
        catch (...)
        {
            // A failed read has no partial writes to abandon. Keep this stage
            // usable by the next node evaluation.
            phase.finish();
            throw;
        }
        phase.finish();
        return result;
    }
private:
    void attachLocked(const PXR_NS::UsdStageRefPtr& source)
    {
        if (m_source == source && m_stage) return;
        m_stage.detach();
        m_source = nullptr;
        if (source)
        {
            m_stage.attach(source);
            m_source = source;
        }
    }
    std::mutex m_mutex;
    PXR_NS::UsdStageRefPtr m_source;
    AnimationStage m_stage;
};
// Plugin-local symbol, not an exported interface or registry.
StageContext& getStageContext();
}
