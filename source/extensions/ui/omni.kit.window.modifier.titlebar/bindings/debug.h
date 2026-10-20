// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <carb/logging/Log.h>

#define GLOBAL_DEBUG 0

#if GLOBAL_DEBUG || defined(LOCAL_DEBUG) || !defined(NDEBUG)
#    define DEBUG_CODE
#endif

#ifdef DEBUG_CODE
#    define DBG_PRINT(...)                                                                                             \
        {                                                                                                              \
            printf("[TITLEBAR] ");                                                                                     \
            printf(__VA_ARGS__);                                                                                       \
        }

class TraceScope
{
public:
    TraceScope(const char* scope) : m_scope(scope)
    {
        CARB_LOG_INFO("Enter %s\n", m_scope);
    }

    ~TraceScope()
    {
        CARB_LOG_INFO("Leave %s\n", m_scope);
    }

private:
    const char* m_scope;
};

#    define TRACE_SCOPE(x) TraceScope __scope(x)

#else
#    define DBG_PRINT(format, ...) void(0)
#    define DBG_WPRINT(format, ...) void(0)
#    define TRACE_SCOPE(x) void(0)
#endif
