// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include "GraphCanvasWidget.h"

#include <cstring>

namespace omni
{
namespace kit
{
namespace materialGraph
{

// Begins an inline rename for the given stable node id, copies the current name into
// the edit buffer, and clears focus/commit flags so the UI can take keyboard focus.
void GraphCanvasWidget::startRename(uint32_t stableId, const std::string& currentName)
{
    m_renameActive = true;
    m_renameNodeId = stableId;
    m_renameFocusSet = false;
    m_renameCommitted = false;
    std::memset(m_renameBuf, 0, sizeof(m_renameBuf));
    std::snprintf(m_renameBuf, sizeof(m_renameBuf), "%s", currentName.c_str());
}

// Returns the committed rename (node id and new string) once, then clears the commit
// flag; returns a zero id and empty string if nothing was committed since last call.
std::pair<uint32_t, std::string> GraphCanvasWidget::consumeRenameResult()
{
    if (!m_renameCommitted)
        return { 0, {} };
    m_renameCommitted = false;
    return { m_renameResultNodeId, std::move(m_renameResult) };
}

// Begins inline editing of a backdrop node's description: same pattern as rename but
// uses the description buffer and node id fields.
void GraphCanvasWidget::startDescEdit(uint32_t stableId, const std::string& currentDesc)
{
    m_descEditActive = true;
    m_descEditNodeId = stableId;
    m_descEditFocusSet = false;
    m_descEditCommitted = false;
    std::memset(m_descEditBuf, 0, sizeof(m_descEditBuf));
    std::snprintf(m_descEditBuf, sizeof(m_descEditBuf), "%s", currentDesc.c_str());
}

// Returns the committed description edit once (node id and new text), or empty if
// there was no commit since the last consume.
std::pair<uint32_t, std::string> GraphCanvasWidget::consumeDescEditResult()
{
    if (!m_descEditCommitted)
        return { 0, {} };
    m_descEditCommitted = false;
    return { m_descEditResultNodeId, std::move(m_descEditResult) };
}

} // namespace materialGraph
} // namespace kit
} // namespace omni
