// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// The only FBX SDK declarations fbx_allocator.cpp needs: the four allocator-handler setters of Autodesk FBX SDK
// 2020.3.7, with the signatures libfbxsdk.so exports. This avoids staging the FBX SDK itself; the library links
// against the converter package's own libfbxsdk.so.
#pragma once
#include <cstddef>

namespace fbxsdk
{
typedef void* (*FbxMallocProc)(size_t);
typedef void* (*FbxCallocProc)(size_t, size_t);
typedef void* (*FbxReallocProc)(void*, size_t);
typedef void (*FbxFreeProc)(void*);
void FbxSetMallocHandler(FbxMallocProc handler);
void FbxSetCallocHandler(FbxCallocProc handler);
void FbxSetReallocHandler(FbxReallocProc handler);
void FbxSetFreeHandler(FbxFreeProc handler);
} // namespace fbxsdk
