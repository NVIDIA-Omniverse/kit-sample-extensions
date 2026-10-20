# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import re

import omni.log


class CoreExtLogConsumer:
    """
    Forwards log messages from a Kit subprocess back to the parent process via omni.log.

    Kit subprocess stdout lines containing [LEVEL][source] are parsed and re-emitted
    at the appropriate severity level. This prevents log messages from core extensions
    (e.g. omni.kit.converter.hoops_core) from being silently dropped when they run
    inside a child Kit process.

    Two source patterns are matched:
      - The extension name (with optional submodule path), e.g.
        [Info] [omni.kit.converter.hoops_core.impl.helper] message
      - __main__, since error/warn-level omni.log calls in the subprocess script
        context resolve to __main__ rather than the extension module, e.g.
        [Error] [__main__] message
    """

    _INFO_LEVELS = frozenset({"Info", "INFO"})
    _WARN_LEVELS = frozenset({"Warning", "Warn", "WARN"})
    _ERROR_LEVELS = frozenset({"Error", "ERROR"})

    def __init__(self, source_ext_name: str):
        """
        Args:
            source_ext_name: The extension name to filter on (e.g. "omni.kit.converter.hoops_core").
        """
        escaped_name = re.escape(source_ext_name)
        all_levels = "|".join(self._INFO_LEVELS | self._WARN_LEVELS | self._ERROR_LEVELS)
        # Match the extension name (with optional submodule suffix) or __main__
        source_pattern = rf"(?:{escaped_name}[^\]]*|__main__)"
        self._pattern = re.compile(rf"\[({all_levels})\]\s*\[{source_pattern}\]\s*(.*)")

    def process_line(self, line: str) -> bool:
        """
        Parse a subprocess stdout line and re-emit matching messages via omni.log.

        Args:
            line: A single decoded stdout line from the Kit subprocess.

        Returns:
            True if the line matched and was forwarded, False otherwise.
        """
        match = self._pattern.search(line)
        if not match:
            return False

        level = match.group(1)
        message = match.group(2).strip()
        if not message:
            return False

        if level in self._INFO_LEVELS:
            omni.log.info(message)
        elif level in self._WARN_LEVELS:
            omni.log.warn(message)
        elif level in self._ERROR_LEVELS:
            omni.log.error(message)

        return True
