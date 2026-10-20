<!-- SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary -->
<!-- -->
<!-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual -->
<!-- property and proprietary rights in and to this material, related -->
<!-- documentation and any modifications thereto. Any use, reproduction, -->
<!-- disclosure or distribution of this material and related documentation -->
<!-- without an express license agreement from NVIDIA CORPORATION or -->
<!-- its affiliates is strictly prohibited. -->

# AnimGraph Schema[omni.anim.graph.schema]

Provides codeless USD animation graph schemas. The definition lives in this extension's
`animGraphSchema/schema.usda`; the normal repository build generates `animGraphSchema/resources/`.

Import `omni.anim.graph.schema` to register the resource plugin and access schema name
constants for standard USD APIs such as `Usd.Prim.IsA`, `HasAPI`, and `ApplyAPI`.
