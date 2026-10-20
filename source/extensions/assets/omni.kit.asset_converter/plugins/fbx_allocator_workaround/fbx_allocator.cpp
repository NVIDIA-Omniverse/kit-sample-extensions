// SPDX-FileCopyrightText: Copyright (c) 2019-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0 AND CC-BY-4.0
//
#include "fbx_allocator.h"

#include <fbxsdk.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <mutex>

namespace
{
constexpr size_t kFbxAlignment = 16;

// Every request is rounded up to a multiple of 16 bytes (at least 16): size classes of 16 and up are 16-byte
// aligned in glibc, the MSVC CRT and mimalloc. Returns 0 when rounding overflows.
size_t RoundUpForFbx(size_t size)
{
    if (size > std::numeric_limits<size_t>::max() - (kFbxAlignment - 1))
    {
        return 0;
    }
    const size_t rounded = (size + kFbxAlignment - 1) & ~(kFbxAlignment - 1);
    return rounded == 0 ? kFbxAlignment : rounded;
}

bool IsFbxAligned(const void* ptr)
{
    return (reinterpret_cast<std::uintptr_t>(ptr) & (kFbxAlignment - 1)) == 0;
}

#if !defined(_WIN32)
// Defensive: an allocator that still returns a misaligned block for a 16-byte multiple gets replaced by an
// aligned_alloc block. Its memory is released with free(), so FbxAlignedFree and blocks the FBX SDK allocated
// before these handlers were installed stay compatible. (Windows: the MSVC CRT and mimalloc align these sizes,
// and _aligned_malloc memory could not be released with free.)
void* AlignOrReplace(void* ptr, size_t rounded, size_t bytesToKeep)
{
    if (!ptr || IsFbxAligned(ptr))
    {
        return ptr;
    }
    void* aligned = std::aligned_alloc(kFbxAlignment, rounded);
    if (!aligned)
    {
        return ptr;  // Keep the (misaligned) block rather than lose it.
    }
    std::memcpy(aligned, ptr, bytesToKeep);
    std::free(ptr);
    return aligned;
}
#endif

void* FbxAlignedMalloc(size_t size)
{
    const size_t rounded = RoundUpForFbx(size);
    if (rounded == 0)
    {
        return nullptr;
    }
    void* ptr = std::malloc(rounded);
#if !defined(_WIN32)
    ptr = AlignOrReplace(ptr, rounded, 0);
#endif
    return ptr;
}

void* FbxAlignedCalloc(size_t count, size_t size)
{
    if (size != 0 && count > std::numeric_limits<size_t>::max() / size)
    {
        return nullptr;
    }
    const size_t total = count * size;
    void* ptr = FbxAlignedMalloc(total);
    if (ptr)
    {
        std::memset(ptr, 0, total);
    }
    return ptr;
}

void* FbxAlignedRealloc(void* ptr, size_t size)
{
    if (!ptr)
    {
        return FbxAlignedMalloc(size);
    }
    const size_t rounded = RoundUpForFbx(size);
    if (rounded == 0)
    {
        return nullptr;
    }
    void* resized = std::realloc(ptr, rounded);
#if !defined(_WIN32)
    resized = AlignOrReplace(resized, rounded, size);
#endif
    return resized;
}

void FbxAlignedFree(void* ptr)
{
    std::free(ptr);
}
} // namespace

int usdConvertAssetFbxAllocatorHandlersVersion()
{
    return 1;
}

void InstallFbxAllocatorHandlers()
{
    static std::once_flag once;
    std::call_once(once,
                   []()
                   {
                       fbxsdk::FbxSetMallocHandler(FbxAlignedMalloc);
                       fbxsdk::FbxSetCallocHandler(FbxAlignedCalloc);
                       fbxsdk::FbxSetReallocHandler(FbxAlignedRealloc);
                       fbxsdk::FbxSetFreeHandler(FbxAlignedFree);
                   });
}
