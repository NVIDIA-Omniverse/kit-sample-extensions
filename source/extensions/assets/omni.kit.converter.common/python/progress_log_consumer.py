# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from enum import Enum

import omni.log


class ProgressStepType(Enum):
    UNKNOWN = 0
    BEGIN = 1
    PROGRESS = 2
    END = 3


class ProgressLogConsumer:

    def __init__(self, log_prefix: str):
        """
        ProgressLogConsumer intialization

        :args
            log_prefix (str): Log prefix. We'll only attempt to parse a line if it starts with this prefix.
        """
        self._log_prefix = log_prefix

    def extract_line(self, msg: str):
        """
        Extract message into step/progress info
        """
        if not msg.startswith(self._log_prefix):
            return [ProgressStepType.UNKNOWN]
        # Remove log prefix before parsing.
        msg = msg[len(self._log_prefix) :]
        decoded_msg = msg.split("*")
        # Split completion records only at the protocol delimiters; diagnostic messages may contain '*'.
        if msg.startswith("*end*"):
            _, code, message = msg.split("*", 3)[1:]
            return [ProgressStepType.END, int(code), message.rstrip("\r\n")]
        # Handle existing progress messages
        if "step" in decoded_msg and "prog" in decoded_msg:
            prog_index = decoded_msg.index("prog")
            if decoded_msg[prog_index + 2].startswith("Begin"):
                # Beginning step
                return [ProgressStepType.BEGIN, decoded_msg[prog_index + 2]]
            else:
                # Log progress
                return [
                    ProgressStepType.PROGRESS,
                    decoded_msg[prog_index + 2],
                    float(decoded_msg[prog_index + 1]) / 100,
                ]
        # Handle end/result message
        elif "end" in decoded_msg:
            end_index = decoded_msg.index("end")
            # Return format = [END type, result code, result message]
            return [ProgressStepType.END, int(decoded_msg[end_index + 1]), decoded_msg[end_index + 2]]
        return [ProgressStepType.UNKNOWN]
