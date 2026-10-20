# Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Log download functionality for reading Kit log files and returning them as a payload."""

import asyncio
import base64
import os
from typing import Dict, Optional

import carb
import carb.settings

# Maximum file size that read_log_file will load into memory.
# Callers such as the extension may enforce a stricter limit before reaching
# this function, but this constant acts as a hard lower-level guard so that
# read_log_file is safe to call directly (e.g. from tests or other extensions).
MAX_LOG_DOWNLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


async def read_log_file(log_path: Optional[str] = None) -> Optional[Dict]:
    """
    Read a log file from disk and return its content as a base64-encoded payload dict.

    The caller is responsible for dispatching the returned payload.  Large payloads are
    handled transparently by ``omni.kit.livestream.messaging``'s splitting/reassembly
    layer — no manual chunking is required here.

    Args:
        log_path: Path to the log file. If None, reads from the ``/log/file`` setting.

    Returns:
        A dict with keys ``filename``, ``content`` (base64-encoded string), and ``size``
        (raw byte count) on success, or ``None`` on failure.
    """
    try:
        if not log_path:
            settings = carb.settings.get_settings()
            log_path = settings.get_as_string("/log/file")

        carb.log_info(f"[LogDownload] Log download request - log_path: {log_path}")

        if not log_path:
            carb.log_error("[LogDownload] No log file path specified")
            return None

        if not os.path.exists(log_path):
            carb.log_error(f"[LogDownload] Log file not found: {log_path}")
            return None

        try:
            file_size = os.path.getsize(log_path)
        except OSError as e:
            carb.log_error(f"[LogDownload] Could not stat log file '{log_path}': {e}")
            return None

        if file_size > MAX_LOG_DOWNLOAD_SIZE_BYTES:
            carb.log_error(
                f"[LogDownload] Log file too large to download: {file_size} bytes "
                f"(limit is {MAX_LOG_DOWNLOAD_SIZE_BYTES} bytes): {log_path}"
            )
            return None

        carb.log_info(f"[LogDownload] Reading log file: {log_path}")

        def _read_bytes(path: str) -> bytes:
            with open(path, "rb") as f:
                return f.read()

        try:
            log_bytes = await asyncio.to_thread(_read_bytes, log_path)
        except Exception as e:
            carb.log_error(f"[LogDownload] Failed to read log file: {e}")
            return None

        filename = os.path.basename(log_path)
        total_size = len(log_bytes)
        content = base64.b64encode(log_bytes).decode("utf-8")

        carb.log_info(f"[LogDownload] Read {total_size} bytes from {filename}")

        return {
            "filename": filename,
            "content": content,
            "size": total_size,
        }

    except Exception as e:
        carb.log_error(f"[LogDownload] Unexpected error reading log file: {e}")
        return None
