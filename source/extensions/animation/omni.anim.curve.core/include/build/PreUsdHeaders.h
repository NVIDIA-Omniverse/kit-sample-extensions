// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// !!! DO NOT INCLUDE THIS FILE IN A HEADER !!!
// When you include this file in a cpp file, add the file name to premake5.lua's pchFiles list!

// The usd headers drag in heavy dependencies and are very slow to build.
// Make it PCH to speed up building time.

#ifdef _MSC_VER
#    pragma warning(push)
#    pragma warning(disable : 4244) // = Conversion from double to float / int to float
#    pragma warning(disable : 4267) // conversion from size_t to int
#    pragma warning(disable : 4305) // argument truncation from double to float
#    pragma warning(disable : 4800) // int to bool
#    pragma warning(disable : 4996) // call to std::copy with parameters that may be unsafe
#    ifndef NOMINMAX
#        define NOMINMAX // Make sure nobody #defines min or max
#    endif
#    include <Windows.h> // Include this here so we can curate
#    undef small // defined in rpcndr.h
#elif defined(__GNUC__)
#    pragma GCC diagnostic push
#    pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#    pragma GCC diagnostic ignored "-Wunused-local-typedefs"
#    pragma GCC diagnostic ignored "-Wunused-function"
// This suppresses deprecated header warnings, which is impossible with pragmas.
// Alternative is to specify -Wno-deprecated build option, but that disables other useful warnings too.
#    ifdef __DEPRECATED
#        define OMNI_USD_SUPPRESS_DEPRECATION_WARNINGS
#        undef __DEPRECATED
#    endif
#endif
