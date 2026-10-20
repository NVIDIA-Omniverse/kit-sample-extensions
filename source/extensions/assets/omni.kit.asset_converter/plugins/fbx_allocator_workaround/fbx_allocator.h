// SPDX-FileCopyrightText: Copyright (c) 2019-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0 AND CC-BY-4.0
//
#pragma once

// Installs FBX SDK allocator handlers that never return a block aligned to less than 16 bytes.
//
// Autodesk FBX SDK 2020.3.7 assumes its small internal allocations are 16-byte aligned. Allocators such as
// mimalloc return 8-byte aligned blocks for requests of 8 bytes or less (Kit 111's Linux kit executable
// exports mimalloc as the process allocator), and the FBX SDK then silently drops animation keys on import.
//
// Thread-safe and idempotent; installs the handlers once per process. Call before the first
// FbxManager::Create (FbxManagerCreator does).
void InstallFbxAllocatorHandlers();

#if defined(_WIN32)
#    define FBX_ALLOCATOR_EXPORT __declspec(dllexport)
#else
#    define FBX_ALLOCATOR_EXPORT __attribute__((visibility("default")))
#endif

// Exported marker (returns 1): a library that contains these handlers says so, so a host that carries its own copy
// as a workaround for older converter builds (KSE omni.kit.asset_converter) can detect that it is no longer needed.
extern "C" FBX_ALLOCATOR_EXPORT int usdConvertAssetFbxAllocatorHandlersVersion();
