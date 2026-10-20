# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""Parse STRING_LIST option text: comma-separated tokens and/or JSON string arrays."""

import json
from typing import List

__all__ = ["parse_string_list_ui_text"]


def parse_string_list_ui_text(raw: str) -> List[str]:
    """Parse user input as a list of strings.

    - If input looks like a JSON array ([...]), parse it and return all non-empty strings.
      If JSON is invalid or contains non-string elements, treat the whole input as plain text.
    """
    if raw is None:
        return []
    text = raw.strip()
    if not text:
        return []

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, list):
            invalid = False
            out: List[str] = []
            for el in parsed:
                if el is None:
                    continue
                if isinstance(el, str):
                    s = el.strip()
                    if s:
                        out.append(s)
                else:
                    invalid = True
                    break
            if not invalid:
                return out
            if text:
                return [text]

    return [item.strip() for item in raw.split(",") if item.strip()]
