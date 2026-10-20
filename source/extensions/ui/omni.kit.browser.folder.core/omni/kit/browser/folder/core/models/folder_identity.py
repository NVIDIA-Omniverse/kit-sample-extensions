# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = [
    "local_url_key",
    "normalize_url",
    "resolve_folder_key",
    "derive_folder_key",
    "find_links_async",
    "local_path_of",
    "shutdown_link_checker",
]

import asyncio
import concurrent.futures
import os
import re
from typing import Dict, Iterable, Optional

import carb
import omni.client

# "/C:/Users" as file:// urls spell it. Only a drive letter earns the leading slash back.
_FILE_URL_DRIVE = re.compile(r"^/[A-Za-z]:")
# "C:/x" and "C:\x", against "omniverse://host/x" - told apart without parsing either.
_DRIVE_PATH = re.compile(r"^[A-Za-z]:[/\\]")
_URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


def normalize_url(url: str) -> str:
    """
    One spelling for a local path, so two of them cannot look like two files.

    Windows reaches the same file under either case of its drive letter, and the browser compares
    urls as strings: a collection added as ``c:/x`` whose listing reports ``C:/x`` matches none of
    its own cached files and shows every one of them twice. omni.client reports an upper case drive,
    so that is what everything is brought to.

    This is the spelling that gets stored and shown, so only the drive letter is touched: the rest
    of a local path is what the user typed, and every remote url is left alone. Deciding whether two
    urls are the same thing is a different question - see :func:`local_url_key`.
    """
    if len(url) >= 2 and url[1] == ":" and url[0].isalpha():
        return url[0].upper() + url[1:]
    return url


def local_url_key(url: str) -> str:
    """
    A key that is equal for any two spellings of one local path, and exact for anything remote.

    Windows is case-insensitive for the whole path, not only the drive letter, and ``file:///c:/x``
    is another spelling of ``C:/x`` - so comparing urls as strings still counts one file as two, and
    the browser shows it twice. os.path.normcase is the rule the filesystem itself uses: it folds
    case on Windows and changes nothing on posix, where two spellings really are two files.

    Remote urls come back unchanged. Case can be significant off the local filesystem, and no rule
    here can know which server cares.
    """
    if not url:
        return url

    # Answered without omni.client wherever possible. break_url is a round trip out of Python and
    # this runs per file, on both sides of every comparison: at 7.8 us a call it more than doubled
    # the cost of matching a folder against its cache - 229 ms against 101 ms over 3,000 files.
    # A drive path, a UNC path and a plain path are all decided by looking at them.
    #
    # A drive is a letter, a colon and one separator. The second test is what tells "c:/x" from
    # "c://host/x": a single letter is a legal url scheme, and folding one of those would call two
    # hosts the same place whenever they differed only in case.
    drive = url[1:2] == ":" and url[2:4] != "//"
    if drive or url[:2] in ("//", "\\\\") or "://" not in url:
        return _fold(url)
    if url[:5].lower() != "file:":
        return url  # remote, and case can be significant there

    path = local_path_of(url)
    return url if path is None else _fold(path)


def _fold(path: str) -> str:
    """
    The filesystem's own rule: case folded on Windows, unchanged where two spellings are two files.

    normcase settles the separators too, so nothing is rewritten here beyond a trailing one.
    """
    if len(path) > 1 and path[-1] in "/\\":
        path = path[:-1]
    return os.path.normcase(path)


# One shared worker for the reparse-point checks. They are metadata calls - microseconds each, but
# hundreds of thousands of them over a drive - and every one of them on the event loop is a tick the
# app does not get. A single thread is enough: the calls are serialised by the disk anyway.
_link_checker: Optional[concurrent.futures.ThreadPoolExecutor] = None


def _checker() -> concurrent.futures.ThreadPoolExecutor:
    global _link_checker
    if _link_checker is None:
        _link_checker = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="folder-links")
    return _link_checker


def local_path_of(url: str) -> Optional[str]:
    """
    The filesystem path a url refers to, or None when it is not local.

    A ``file://`` url can name a host, and two of them are two different shares: dropping it left
    ``file://a/share/x`` and ``file://b/share/x`` looking like one path, which is one collection as
    far as the browser is concerned. A named host comes back as the UNC path it is, which is also
    what the filesystem calls it.
    """
    try:
        broken = omni.client.break_url(url)
        scheme = (broken.scheme or "").lower()
        path = broken.path or url
        host = broken.host or ""
    except Exception:  # noqa: BLE001
        return None
    if scheme not in ("", "file"):
        return None
    if scheme == "file" and _FILE_URL_DRIVE.match(path):
        path = path[1:]
    if host and host.lower() != "localhost":
        return f"//{host}{path if path.startswith('/') else '/' + path}"
    return path


def _is_link(path: str) -> bool:
    """True if this directory is a junction, a symlink or any other reparse point."""
    try:
        stat = os.lstat(path)
    except (OSError, ValueError):
        # Unreadable. Treat as a link so it gets resolved properly rather than trusted blindly.
        return True
    tag = getattr(stat, "st_reparse_tag", 0)
    if tag:
        return True
    return os.path.islink(path)


def find_links(urls: Iterable[str]) -> Dict[str, str]:
    """
    Of these folder urls, which are links - and what do they resolve to? **Runs on a worker.**

    Only links need resolving, and they are rare: everything else takes its key from its parent for
    free. Returns a mapping of url to resolved key, containing only the links.
    """
    found = {}
    for url in urls:
        path = local_path_of(url)
        if path is None or not _is_link(path):
            continue
        found[url] = resolve_folder_key(url)
    return found


async def find_links_async(urls: Iterable[str]) -> Dict[str, str]:
    """
    Same, off the event loop, one round trip for a whole folder's children.

    This is the difference between a syscall per directory on the loop - measured at 0.155 ms for
    realpath and 0.056 ms for lstat, hundreds of thousands of times over a drive - and one await per
    folder listing. Falls back to running inline if the pool has gone away during teardown.
    """
    urls = list(urls)
    if not urls:
        return {}
    try:
        return await asyncio.wrap_future(_checker().submit(find_links, urls))
    except RuntimeError:  # pool shut down
        return find_links(urls)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - a failed check must not end the traverse
        carb.log_warn(f"Could not check {len(urls)} folder(s) for links: {exc}")
        return {}


def shutdown_link_checker() -> None:
    """Drop the worker. Called when a model is destroyed; the next use builds another."""
    global _link_checker
    executor, _link_checker = _link_checker, None
    if executor is not None:
        executor.shutdown(wait=False)


def derive_folder_key(parent_key: str, name: str) -> str:
    """
    A child's key, from its parent's, with no filesystem call at all.

    Valid precisely because the walk is top-down and the parent has already been resolved: if no
    part of the path is a link, the real path of a child is the real path of its parent plus the
    child's name. Children that *are* links are resolved properly instead - see
    :func:`find_links_async` - which is the whole reason this can be free for everything else.
    """
    return _normalise(f"{parent_key.rstrip('/')}/{name}")


def resolve_folder_key(url: str) -> str:
    r"""
    Identity of the directory a url actually points at.

    Used to recognise a directory the traverse has already walked, under whatever name it is
    reached by. Windows junctions point at their own parent, so a walk that trusts the listing
    descends forever. ``omni.client`` cannot help: a junction and a real directory come back from
    ``list``/``stat`` with byte-identical flags, so resolving through the links is the only signal.

    Local paths resolve to the directory on disk, case folded on Windows because the filesystem is.
    Remote urls key on the url itself, which is the only identity available for them.

    Args:
        url (str): Folder url.
    Return an opaque string; equal keys mean the same directory.
    """
    try:
        broken = omni.client.break_url(url)
        scheme = (broken.scheme or "").lower()
        path = broken.path or url
    except Exception:  # noqa: BLE001 - an unparsable url is still usable as its own key
        return url.rstrip("/\\")

    if scheme not in ("", "file"):
        # omniverse://, http:// and friends. Trailing slash only, since anything cleverer would be
        # guessing at a server's idea of equality.
        return url.rstrip("/")

    if scheme == "file" and _FILE_URL_DRIVE.match(path):
        # file:///C:/x arrives as /C:/x, which is not a path any OS call accepts.
        path = path[1:]

    host = broken.host or ""
    if host and host.lower() != "localhost":
        # file://server/share names a share, and the path alone is the same for every server that
        # has one - two of them would key as one directory and the second one's content would be
        # dropped as already visited. The same fix local_url_key needed.
        path = f"//{host}{path if path.startswith('/') else '/' + path}"

    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        # Unresolvable - too long, or a device that will not answer. Fall back to the literal path
        # so the folder is still its own key and the walk carries on.
        return _normalise(path)

    return _normalise(real)


def _normalise(path: str) -> str:
    """
    One spelling per directory.

    Separators are folded because realpath hands back backslashes on Windows while a key derived
    from a parent is built with forward slashes; two spellings of one directory would defeat the
    very comparison these keys exist for.
    """
    text = path.replace("\\", "/").rstrip("/")
    return text.lower() if os.name == "nt" else text
