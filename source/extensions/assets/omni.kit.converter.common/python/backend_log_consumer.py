# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.log


class BackendLogConsumer:
    """
    Backend log consumer for backend converters library.
    Filters and logs messages that start with the specified prefix.
    """

    def __init__(self, log_prefix: str):
        """
        BackendLogConsumer initialization

        Args:
            log_prefix (str): Log prefix to filter messages (e.g., "[omni.converter.dgn_log]")
        """
        self._log_prefix = log_prefix

    def should_process(self, msg: str) -> bool:
        """
        Check if a message should be processed by this consumer

        Args:
            msg (str): Raw log message

        Returns:
            bool: True if message starts with our prefix
        """
        return msg.startswith(self._log_prefix)

    def process_line(self, msg: str) -> None:
        """
        Process and log a diagnostic message

        Args:
            msg (str): Raw log message
        """
        if not self.should_process(msg):
            return

        # Remove prefix
        clean_msg = msg[len(self._log_prefix) :].strip()

        # Parse message type from tokens
        if "*error*" in clean_msg:
            # Extract message after *error* token
            error_msg = clean_msg.split("*error*", 1)[1] if "*error*" in clean_msg else clean_msg
            omni.log.error(error_msg)

        elif "*warn*" in clean_msg:
            # Extract message after *warn* token
            warn_msg = clean_msg.split("*warn*", 1)[1] if "*warn*" in clean_msg else clean_msg
            omni.log.warn(warn_msg)

        elif "*status*" in clean_msg:
            # Extract message after *status* token
            status_msg = clean_msg.split("*status*", 1)[1] if "*status*" in clean_msg else clean_msg
            omni.log.info(status_msg)

        else:
            # Log any other diagnostic messages
            omni.log.info(f"Converter Diagnostic: {clean_msg}")
