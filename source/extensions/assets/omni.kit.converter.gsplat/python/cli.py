# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""CLI shim for ``python -m omni.kit.converter.gsplat.cli``; delegates to ``usd_convert_gsplat``."""

from usd_convert_gsplat.cli import main, parse_args

__all__ = ["main", "parse_args"]

if __name__ == "__main__":
    main()
