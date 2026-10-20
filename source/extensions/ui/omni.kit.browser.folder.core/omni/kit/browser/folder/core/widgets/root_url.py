# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["describe_root_url"]

import re
from typing import Optional

import omni.client

# "C:", "C:/", "c:\" - a whole local drive.
_DRIVE_ROOT = re.compile(r"^[A-Za-z]:[/\\]?$")
# "//server/share", "\\\\server\\share" - a whole network share, with nothing below it.
_UNC_ROOT = re.compile(r"^[/\\]{2}[^/\\]+[/\\][^/\\]+[/\\]?$")


def describe_root_url(url: Optional[str]) -> Optional[str]:
    """
    Classify a url that would scan an unreasonable amount if added as a collection.

    Returns a short human phrase naming what it is ("an entire server", "an entire drive"), or
    None when the url is an ordinary folder.

    Pure string inspection: no listing, no stat, no probing of how big the target actually is.
    Measuring first would mean walking the tree to decide whether walking the tree is a good idea,
    and the answer for these cases is knowable from the url alone.
    """
    if not url:
        return None

    candidate = url.strip()
    if not candidate:
        return None

    # Local drive and network-share roots. Checked before break_url because a bare "C:" has no
    # scheme and break_url would give it one.
    plain = candidate.replace("\\", "/")
    if _DRIVE_ROOT.match(candidate) or _DRIVE_ROOT.match(plain):
        return "an entire drive"
    if _UNC_ROOT.match(candidate):
        return "an entire network share"
    if plain in ("/", "//"):
        return "the filesystem root"

    try:
        broken = omni.client.break_url(candidate)
    except Exception:  # noqa: BLE001 - an unparsable url is not our problem here
        return None

    scheme = (broken.scheme or "").lower()
    path = (broken.path or "").replace("\\", "/")

    if scheme == "omniverse" and path.strip("/") == "":
        return "an entire server"
    if scheme == "file" and (path.strip("/") == "" or _DRIVE_ROOT.match(path.lstrip("/"))):
        return "an entire drive"

    return None
