# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from logging import Logger, getLogger
from typing import Any, Callable, Dict, Optional

import carb
from omni.services.facilities.base import Facility


class PythonLogFacility(Facility):
    """
    Omniverse Service Log Facility implemented using the Python `logging` module.

    The Omniverse framework recommends using the native `logging` module when developing features in Python, over the
    previous recommendation of using the Carbonite framework's `carb.log_*(...)` methods. This now allows developers to
    use the already-established features of the native Python module for their logging needs, while also redirecting log
    streams to the equivalent Carbonite `carb.log_*(...)` handlers, in order to reuse any constructs which may have
    already been established over time.

    This Facility thus leverages the Python `logging` module, using the `stacklevel` argument of the various calls in
    order to register the filenames, function names and line number of the original call sites (and not these attributes
    within this wrapping layer, in the current file).

    """

    def __init__(self, logger_name: Optional[str] = None) -> None:
        """
        Constructor.

        Args:
            logger_name (Optional[str]): Name to provide to the underlying Python logger for this instance of the
                Facility.

        Returns:
            None

        """
        super().__init__()

        self._logger = getLogger(name=logger_name)

    def stop(self) -> None:
        """Callback executed upon stopping the instance of the Facility."""
        self._logger = None

        return super().stop()

    def _include_correlation_id(self) -> bool:
        """
        Check whether it is desired for the Correlation ID of the current context to be included in the entry recorded
        to the log.

        Args:
            None

        Returns:
            bool: A flag indicating whether it is desired for the Correlation ID of the current context to be included
                in the entry recorded to the log.

        """
        settings = carb.settings.get_settings_interface()
        should_include_correlation_id_if_available = settings.get_as_bool(
            "/exts/omni.services.facilities.log/includeCorrelationIdIfAvailable"
        )
        return should_include_correlation_id_if_available

    def _get_correlation_id(self) -> Optional[str]:
        """
        Return the Correlation ID of the current context, if any is defined.

        Args:
            None

        Returns:
            Optional[str]: The Correlation ID of the current context, if any is defined.

        """
        try:
            from omni.services.core.requests import get_correlation_id

            return get_correlation_id()
        except ImportError:
            pass
        return None

    def _format_message(self, message: str) -> str:
        """
        Format the given message so it can be recorded to the log using the desired structure (e.g. using its
        Correlation ID, if any is defined in the current context).

        Args:
            message (str): Message to record to the log.

        Returns:
            str: The given message, formatted according to the desired structure.

        """
        if self._include_correlation_id():
            correlation_id = self._get_correlation_id()
            if correlation_id is not None:
                return f"[CorrelationID={correlation_id}] {message}"
        return message

    def _record_log_entry(self, log_method: Callable[[str, Dict[Any, Any]], None], message: str) -> None:
        """
        Record the given message using the given method of the `Logger` instance, in order to use the appropriate
        severity for the log entry.

        NOTE: The `stacklevel` argument provided to the `Logger`'s log method indicates the number of steps of the stack
        to walk back when attempting to resolve the origin of the call in order to deduce the filename, function name
        and line number of the original caller. This prevents the information in the log event from being recorded as
        originating from this call site, and instead properly mapping back to the source.

        Args:
            log_method (Callable[[str, Dict[Any, Any]], None]): Method of the `Logger` instance with which to record the
                log entry.
            message (str): Message to record to the log.

        Returns:
            None

        """
        formatted_message = self._format_message(message=message)
        log_method(msg=formatted_message, stacklevel=3)

    def verbose(self, message: str) -> None:
        """
        Log the given message using the `VERBOSE` severity.

        Args:
            message (str): Message to log using the `VERBOSE` severity.

        Returns:
            None

        """
        self._record_log_entry(log_method=self._logger.debug, message=message)

    def info(self, message: str) -> None:
        """
        Log the given message using the `INFO` severity.

        Args:
            message (str): Message to log using the `INFO` severity.

        Returns:
            None

        """
        self._record_log_entry(log_method=self._logger.info, message=message)

    def warning(self, message: str) -> None:
        """
        Log the given message using the `WARNING` severity.

        Args:
            message (str): Message to log using the `WARNING` severity.

        Returns:
            None

        """
        self._record_log_entry(log_method=self._logger.warn, message=message)

    def error(self, message: str) -> None:
        """
        Log the given message using the `ERROR` severity.

        Args:
            message (str): Message to log using the `ERROR` severity.

        Returns:
            None

        """
        self._record_log_entry(log_method=self._logger.error, message=message)

    def fatal(self, message: str) -> None:
        """
        Log the given message using the `FATAL` severity.

        Args:
            message (str): Message to log using the `FATAL` severity.

        Returns:
            None

        """
        self._record_log_entry(log_method=self._logger.critical, message=message)

    def get_logger(self) -> Logger:
        """
        Return the instance of the Python logger used by the Facility.

        Args:
            None

        Returns:
            Logger: The instance of the Python logger used by the Facility.

        """
        return self._logger
