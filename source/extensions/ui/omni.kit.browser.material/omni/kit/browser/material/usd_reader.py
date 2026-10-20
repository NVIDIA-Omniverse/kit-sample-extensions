# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""
Reading materials out of a USD file.

Opening a stage is synchronous C++ that cannot yield, so on the event loop it blocks the app for as
long as it takes. What made that unbearable was not the open but what an open could reach: a file
naming an unreachable host cost minutes. That is caught before the open now, by the foreign-arc
gate, which leaves a read at milliseconds.

The open runs on a worker by default - ``usd_reader.threaded`` - and only plain data comes back:
prim path strings and a default flag, never a live USD object, so nothing that outlives the worker
can reach into USD from the loop.
"""

__all__ = ["UsdMaterialInfo", "read_usd_materials_async", "shutdown_usd_readers"]

import asyncio
import concurrent.futures
import re
from typing import List, NamedTuple, Optional, Tuple

import carb
import carb.settings
from pxr import Sdf, Usd, UsdShade

SETTING_THREADED = "/exts/omni.kit.browser.material/usd_reader/threaded"
DEFAULT_THREADED = True
# One worker, and not a settable count. USD's Python bindings hold the GIL across Stage.Open, so
# extra threads cannot parallelise it, and in parallel they have deadlocked in
# Sdf_Identity::_UnregisterOrDelete. One worker still keeps the open off the event loop.
POOL_WORKERS = 1

# True (default): an arc whose target is in another storage location - another server, or remote
# against local - is left alone, payloads and references alike. Same-location and relative arcs
# still compose; the point is the network, not the directory. False composes the lot, so one arc
# naming an unreachable host stops the scan inside Usd.Stage.Open for as long as it retries.
SETTING_SKIP_FOREIGN_ARCS = "/exts/omni.kit.browser.material/usd_reader/skip_foreign_arcs"
DEFAULT_SKIP_FOREIGN_ARCS = True

# A drive path, checked before anything url-shaped: urlsplit reads the drive letter as a scheme,
# so "C:/x" would otherwise look like a remote host.
_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\/]")
_URL_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*)://([^/]*)")
_LOCAL = ("local",)

_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
_accepting = False


class UsdMaterialInfo(NamedTuple):
    """One material found in a USD file. Plain data - safe to hand back to the event loop."""

    path: str
    is_default: bool


def start_usd_readers() -> None:
    """
    Open the pool. Called from the extension's on_startup.

    On by default. A file is opened on a worker, so the app keeps drawing through it: scanning a
    library holding one 10,000 prim file, the main thread was inside the reader in 0 of 50 samples
    with this on, and in almost all of them with it off - the app stopped responding for as long as
    that one open took. ``threaded = false`` reads on the loop instead, which costs the app those
    frames and buys nothing back. Scanning the 2,649 material library end to end, three runs each,
    only this setting changed: 8.4 s threaded against 8.7 s on the loop from local disk, 14.3 s
    against 14.2 s from S3 - the same, within the spread - while the app ran at 96 fps threaded and
    25 fps on the loop. One worker holding the GIL across the open cannot be slower than the loop
    holding it; all that changes is which thread waits.

    Nothing is opened here, and the worker is not warmed. Warming meant opening a stage, which on
    the startup path initialises USD before the extensions that register schemas have finished -
    omni.kit.property.usd then cannot find OmniPlaybackAPI. It bought about 10 ms of one-off
    per-thread cost, and off the loop even that lands on the worker rather than the app.

    Because nothing here touches USD, a run in ``/app/warmupMode`` needs no special case: it was
    the warm-up that could not share a startup with schema registration, not the pool.

    The pool is one worker either way. What is worth choosing is whether to use one at all.
    """
    global _executor, _accepting
    if not _threaded():
        _accepting = True
        return
    if _executor is None:
        _executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=POOL_WORKERS, thread_name_prefix="usd-material-reader"
        )
    _accepting = True


def _threaded() -> bool:
    """Read the gate. A missing setting means the default, not False."""
    value = carb.settings.get_settings().get(SETTING_THREADED)
    return DEFAULT_THREADED if value is None else bool(value)


def shutdown_usd_readers() -> None:
    """
    Close the pool. Called from the extension's on_shutdown.

    Does not wait: a reader holds no model or UI reference and returns plain data, so one still
    running at teardown is harmless - it finishes and its result is dropped. Waiting would put a
    stage open on the shutdown path, which is the freeze this work exists to remove.
    """
    global _executor, _accepting
    _accepting = False
    executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)


def _location_of(url: str) -> Optional[Tuple[str, ...]]:
    """
    Where a url lives, for deciding whether two things sit in the same place.

    Returns None for a relative path, which by definition resolves next to whatever refers to it
    and so is always in the same location as its referrer.
    """
    if not url:
        # An empty asset path is an internal payload: same layer, same location.
        return None
    text = url.strip().replace("\\", "/")
    if _DRIVE_PATH.match(text):
        return _LOCAL
    if text.startswith("//") and not _URL_SCHEME.match(text):
        # A UNC share is a host, not local storage: it is only the same place as another path on
        # the same server.
        return ("unc", text[2:].split("/", 1)[0].lower())
    match = _URL_SCHEME.match(text)
    if match is None:
        return None  # relative
    scheme = match.group(1).lower()
    host = match.group(2).lower()
    if scheme == "file":
        # file:// can name a host - file://server/share is a remote path wearing a local looking
        # scheme, and calling it local is what lets it through to Usd.Stage.Open and the retry
        # budget this gate exists to avoid.
        return _LOCAL if host in ("", "localhost") else ("unc", host)
    return (scheme, host)


def _payload_targets(prim) -> List[str]:
    """Every payload asset path authored on this prim, across its whole prim stack."""
    targets = []
    for spec in prim.GetPrimStack():
        payloads = getattr(spec, "payloadList", None)
        if payloads is None:
            continue
        for item in payloads.GetAddedOrExplicitItems():
            targets.append(item.assetPath)
    return targets


def _has_authored_payload(stage) -> bool:
    """
    Does anything in this stage's own layers author a payload? **No composition.**

    Usd.Stage.FindLoadable composes to answer, and composing is the expensive part - 418 ms on a
    400 KB asset with no payloads at all. Walking the authored specs answers the same question in
    18 ms for the common case, a file with no payloads whatsoever.

    Limitation, deliberate: this sees the stage's own layer stack, not layers pulled in by a
    reference, so a payload authored inside a referenced layer stays unloaded - the same outcome as
    opening with LoadNone, and the safe direction to be wrong in.
    """
    for layer in stage.GetLayerStack(includeSessionLayers=False):
        found = [False]

        def visit(path, layer=layer, found=found):
            if found[0]:
                return
            spec = layer.GetPrimAtPath(path)
            payloads = getattr(spec, "payloadList", None) if spec is not None else None
            if payloads is not None and payloads.GetAddedOrExplicitItems():
                found[0] = True

        layer.Traverse(Sdf.Path("/"), visit)
        if found[0]:
            return True
    return False


def _load_local_payloads(stage, url: str) -> int:
    """
    Load only the payloads that live where the file itself lives.

    A payload pointing somewhere else is the hang: composing it makes USD resolve that location,
    and an unreachable server costs connection timeouts and retries with the GIL held. A 1 KB file
    whose payload named a dead server measured 141 seconds against 4 ms for the same file with the
    payload left alone - the freeze this gate exists for. A payload sitting beside its referrer costs
    microseconds, so those are still loaded and the materials inside them still found.

    Return how many prims were loaded.
    """
    if not _has_authored_payload(stage):
        # Nothing to decide, and finding that out must not cost a composition - see above.
        return 0

    origin = _location_of(url)
    wanted = set()
    skipped = 0
    for path in stage.FindLoadable():
        prim = stage.GetPrimAtPath(path)
        if not prim:
            continue
        # A target whose location is None is relative, so it inherits the origin's - same place.
        foreign = [t for t in _payload_targets(prim) if (_location_of(t) or origin) != origin]
        if foreign:
            skipped += 1
            carb.log_info(f"Not loading payload {foreign[0]} of {url}: different location")
            continue
        wanted.add(path)
    if wanted:
        stage.LoadAndUnload(wanted, set())
    if skipped:
        carb.log_info(f"{url}: left {skipped} foreign payload(s) unloaded")
    return len(wanted)


def _foreign_arcs(url: str) -> List[str]:
    """
    The layers this file composes at open time that live somewhere other than the file itself.

    ``load=Usd.Stage.LoadNone`` defers payloads and nothing else, so a reference, sublayer or clip
    naming an unreachable server is fetched by ``Usd.Stage.Open`` itself - 139 s for one 2.8 KB file
    naming a dead host, which is ``omni.client``'s 120 s retry budget per first contact and cannot
    be lowered for one caller alone.

    ``Sdf.Layer.FindOrOpen`` parses this one layer and resolves nothing, so it never reaches the
    network. It costs about 3.5 ms on the median file, and the ``Usd.Stage.Open`` that follows is no
    slower for it, because Sdf hands back the layer it has already parsed.

    Payloads are left out: ``LoadNone`` defers those already and :func:`_load_local_payloads`
    decides them. Returns the foreign asset paths, empty if there are none or the layer cannot be
    read - in which case the open goes ahead and reports the problem in the usual way.
    """
    try:
        layer = Sdf.Layer.FindOrOpen(url)
    except Exception as exc:  # noqa: BLE001 - a malformed file is Usd.Stage.Open's to report
        carb.log_info(f"Could not open layer {url} to check its arcs: {exc}")
        return []
    if layer is None:
        return []
    origin = _location_of(url)
    try:
        # References, payloads, sublayers and clips in one call, already anchored to this layer.
        deps = layer.GetCompositionAssetDependencies()
    except Exception as exc:  # noqa: BLE001
        carb.log_info(f"Could not read the arcs of {url}: {exc}")
        return []
    # Location first, payload walk only if it can still change the answer: _payload_only_paths walks
    # every prim spec, the location test is string work, and foreign arcs are rare - 16 files in a
    # 6,000 file sweep. A target whose location is None is relative, so it inherits the origin's.
    foreign = [dep for dep in deps if (_location_of(dep) or origin) != origin]
    if not foreign:
        return []
    deferred = _payload_only_paths(layer)
    return [dep for dep in foreign if dep not in deferred]


def _payload_only_paths(layer) -> set:
    """
    Asset paths this layer reaches by payload and by no other arc.

    Those are not this gate's problem: ``LoadNone`` already defers them, and
    :func:`_load_local_payloads` then decides which to load back, so a file whose only foreign arc
    is a payload can still be composed - and should be, because composing it finds the materials
    behind its *local* references. A path used as both a payload and a reference is not deferred and
    so is not in here.
    """
    payloads, others = set(), set(layer.subLayerPaths)

    def visit(path):
        spec = layer.GetPrimAtPath(path)
        if spec is None:
            return
        for listing, sink in (("payloadList", payloads), ("referenceList", others)):
            arcs = getattr(spec, listing, None)
            if arcs is None:
                continue
            for item in arcs.GetAddedOrExplicitItems():
                if item.assetPath:
                    sink.add(item.assetPath)

    layer.Traverse(Sdf.Path("/"), visit)
    return payloads - others


def _materials_in_layer(url: str) -> List[UsdMaterialInfo]:
    """
    The materials authored directly in this file, read from the layer without composing anything.

    Used for a file that reaches somewhere else, where composing is what costs minutes. Walking the
    specs finds every material the file declares itself, which is what a library scan is looking
    for; what it cannot find is a material arriving through one of this file's own references, even
    a local one. That is the deliberate trade: those materials were never reachable in bounded time
    anyway, because getting to them means composing the foreign arc that made this file expensive.
    """
    try:
        layer = Sdf.Layer.FindOrOpen(url)
    except Exception:  # noqa: BLE001
        return []
    if layer is None:
        return []
    default_prim = layer.defaultPrim
    found: List[UsdMaterialInfo] = []

    def visit(path, found=found):
        spec = layer.GetPrimAtPath(path)
        if spec is None or spec.typeName != "Material":
            return
        # The default prim is a root prim, so only a root-level material can be one.
        is_default = bool(default_prim) and path.pathString == f"/{default_prim}"
        found.append(UsdMaterialInfo(path.pathString, is_default))

    layer.Traverse(Sdf.Path("/"), visit)
    return found


def _read_usd_materials(url: str, skip_foreign_arcs: bool = True) -> Optional[List[UsdMaterialInfo]]:
    """
    Open a USD file and list its materials. **Runs on a worker thread.**

    Returns None when the stage could not be opened. Everything returned is a plain string or bool;
    the stage and its prims stay on this thread and are released before returning, which is what
    lets USD reclaim the layer.

    Args:
        url (str): File to read.
        skip_foreign_arcs (bool): True leaves alone anything the file reaches that lives somewhere
            else - see :func:`_foreign_arcs` and :func:`_load_local_payloads`. False composes
            everything, which can block for minutes on an arc naming an unreachable server.

    The flag is passed in rather than read here: this runs on a worker, and carb settings are read
    on the loop so they stay single-threaded.
    """
    if skip_foreign_arcs:
        foreign = _foreign_arcs(url)
        if foreign:
            # Never open the stage: opening it is what composes the arc, and composing it is the
            # freeze. Report what the file declares on its own instead.
            carb.log_info(f"Not composing {url}: {foreign[0]} is in a different location")
            return _materials_in_layer(url)
    try:
        if skip_foreign_arcs:
            stage = Usd.Stage.Open(url, load=Usd.Stage.LoadNone)
        else:
            stage = Usd.Stage.Open(url)
    except Exception as exc:  # noqa: BLE001 - a malformed file must not kill the scan
        # A file USD cannot parse raises rather than returning an invalid stage, and a traverse
        # walking a whole drive will meet plenty of those.
        carb.log_warn(f"Could not open {url}: {exc}")
        return None
    if not stage:
        return None
    if skip_foreign_arcs:
        _load_local_payloads(stage, url)
    default_prim = stage.GetDefaultPrim() if stage.HasDefaultPrim() else None
    found = [
        UsdMaterialInfo(prim.GetPath().pathString, bool(default_prim and prim == default_prim))
        for prim in stage.TraverseAll()
        if prim.IsA(UsdShade.Material)
    ]
    del stage
    return found


def _skip_foreign_arcs() -> bool:
    """Read the gate. Called on the loop, never in a worker, so carb settings stay single-threaded."""
    value = carb.settings.get_settings().get(SETTING_SKIP_FOREIGN_ARCS)
    return DEFAULT_SKIP_FOREIGN_ARCS if value is None else bool(value)


async def read_usd_materials_async(url: str) -> Optional[List[UsdMaterialInfo]]:
    """
    Read a USD file's materials without blocking the event loop.

    Falls back to reading inline when the pool is closed - during teardown, or in a test app that
    never started it - so callers never have to care whether it is running.
    """
    skip = _skip_foreign_arcs()
    if not _accepting or _executor is None:
        return _read_usd_materials(url, skip)

    # submit + wrap_future rather than run_in_executor: this keeps the concurrent future, which is
    # the only handle that can cancel work that has not started yet.
    try:
        future = _executor.submit(_read_usd_materials, url, skip)
    except RuntimeError:  # pool closed between the check and here
        return _read_usd_materials(url, skip)
    try:
        return await asyncio.wrap_future(future)
    except asyncio.CancelledError:
        # Cancels the job if it has not started; a running one finishes and is discarded.
        future.cancel()
        raise
    except Exception as exc:  # noqa: BLE001 - a bad USD file must not kill the scan
        carb.log_warn(f"Could not read materials from {url}: {exc}")
        return None
