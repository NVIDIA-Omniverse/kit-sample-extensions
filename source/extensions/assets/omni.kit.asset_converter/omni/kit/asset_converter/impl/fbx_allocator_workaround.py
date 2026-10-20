# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Kit 111 (Linux) workaround: FBX SDK allocator handlers with a 16-byte minimum alignment.

Kit 111's Linux ``kit`` executable exports mimalloc as the process allocator. mimalloc returns 8-byte aligned
blocks for requests of 8 bytes or less, and Autodesk FBX SDK 2020.3.7 (bundled in usd-convert-asset) then
silently drops animation keys. usd-convert-asset-internal#6 makes the converter install these handlers itself;
until the pinned package has it, this extension installs the same handlers (``libomni.kit.asset_converter.fbx_allocator.so``,
built from #6's ``fbx_allocator.cpp``) once, at startup, before the first conversion.

TODO: remove this module and its native library at the usd_convert_asset pin bump to the first 9.2.x with
usd-convert-asset-internal#6 (that converter exports ``usdConvertAssetFbxAllocatorHandlersVersion``).
"""
import ctypes
import sys
from pathlib import Path

import asset_converter_native_bindings
import carb

_LIBRARY_NAME = "libomni.kit.asset_converter.fbx_allocator.so"

# The handlers are process-wide and never uninstalled, so the library that holds them must stay loaded for the
# process lifetime: if it were unloaded (extension shutdown or hot-reload), the FBX SDK's next allocation would
# call into freed code and crash. Not restoring the FBX SDK's default handlers is safe: every block these handlers
# return is released with free(), the same as the defaults. ctypes never dlclose()s a library, and this reference
# is never dropped; a reload of this module re-opens the same loaded copy, where std::call_once makes the install
# a no-op.
_library = None


def install_fbx_allocator_handlers(extension_path: str) -> bool:
    """Install the FBX SDK allocator handlers once per process, unless the staged converter already does.

    Returns True when this extension's handlers are installed.
    """
    global _library
    if not sys.platform.startswith("linux"):
        return False  # On Windows the converter sets its own handlers.
    if _library is not None:
        return True

    libs_dir = Path(asset_converter_native_bindings.__file__).parent / "libs"
    if not (libs_dir / "libfbxsdk.so").exists():
        return False  # No FBX SDK in the converter package (aarch64), so no workaround is built.
    try:
        converter = ctypes.CDLL(str(libs_dir / "libusd_convert_asset.so"))
        if hasattr(converter, "usdConvertAssetFbxAllocatorHandlersVersion"):
            carb.log_info("usd-convert-asset installs its own FBX SDK allocator handlers; workaround not needed")
            return False
    except OSError as error:
        carb.log_warn(f"Cannot inspect usd-convert-asset for FBX SDK allocator handlers: {error}")

    library_path = Path(extension_path) / "bin" / _LIBRARY_NAME
    try:
        library = ctypes.CDLL(str(library_path))
        library.omniKitAssetConverterInstallFbxAllocatorHandlers()
    except (OSError, AttributeError) as error:
        carb.log_error(f"FBX SDK allocator handlers not installed; FBX animation may be lost: {error}")
        return False
    _library = library
    carb.log_info("Installed FBX SDK allocator handlers (16-byte minimum alignment)")
    return True
