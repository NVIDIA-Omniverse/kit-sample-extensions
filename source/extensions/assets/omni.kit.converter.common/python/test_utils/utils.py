# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
import shutil
from pathlib import Path
from typing import NamedTuple

import carb
import omni.kit.test
import psutil


def create_readonly_file(file_path: str):
    """Create a readonly file"""
    f = open(file_path, "w")
    os.chmod(file_path, 0o440)
    f.close()


def cleanup_file(file_path: str, read_only=False):
    """Delete a file, if readonly, calls chmod first"""
    if not os.path.isfile(file_path):
        return

    if read_only:
        os.chmod(file_path, 0o770)
    os.remove(file_path)


def get_ext_root_path() -> Path:
    return Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.converter.common}"))


def get_repo_root_path() -> Path:
    return get_ext_root_path().parent.parent.parent.parent.parent


def make_output_dir(dir_name: str) -> Path:
    """
    Makes and returns an empty output directory
    """
    test_output_path = Path(omni.kit.test.get_test_output_path()) / dir_name
    if os.path.exists(test_output_path):
        shutil.rmtree(test_output_path)
    test_output_path.mkdir(parents=True, exist_ok=True)
    return test_output_path


def _get_memory_usage(pid: int) -> NamedTuple:
    """Get current memory use info of the calling process."""
    process = psutil.Process(pid)
    mem_info = process.memory_info()
    return mem_info


def _get_total_memory() -> int:
    """Get total physical memory."""
    return psutil.virtual_memory().total


def _get_available_memory() -> int:
    """Get available memory."""
    return psutil.virtual_memory().available


def _bytes_to_mb(bytes_value) -> float:
    """Convert bytes to megabytes."""
    return bytes_value / (1024 * 1024)


def _log_memory_usage_stats(pid: int) -> float:
    # Get meory usage and convert to MB
    memory_usage = _get_memory_usage(pid)
    memory_usage_mb = _bytes_to_mb(memory_usage.rss)

    # Get total memory and convert to MB
    total_memory = _get_total_memory()
    total_memory_mb = _bytes_to_mb(total_memory)

    # Get available memory and convert to MB
    available_memory = _get_available_memory()
    available_memory_mb = _bytes_to_mb(available_memory)

    # Calculate percentage of memory used by the process
    percentage_used = (memory_usage_mb / total_memory_mb) * 100

    carb.log_info(f"| Total Memory: {total_memory_mb:.2f} MB | Available Memory: {available_memory_mb:.2f} MB")
    carb.log_info(
        f"| Percentage of Memory Used by Process: {percentage_used:.2f}% | Memory Usage: {memory_usage_mb:.2f} MB"
    )

    return memory_usage_mb
