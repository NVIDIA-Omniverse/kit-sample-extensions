# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Health check provider registry."""

import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# Valid probe types for health check providers.
VALID_PROBE_TYPES = ("livez", "readyz", "startupz")

DEFAULT_PROBE_TYPES = ["livez", "readyz"]


@dataclass
class HealthCheckResult:
    """Result from a health check provider."""

    healthy: bool
    message: Optional[str] = None


@dataclass
class _ProviderEntry:
    """Internal record for a registered health check provider."""

    check: Callable[[], HealthCheckResult]
    probe_types: List[str]


class HealthCheckRegistry:
    """Thread-safe registry for health check providers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._providers: Dict[str, _ProviderEntry] = {}

    def register(
        self,
        name: str,
        check: Callable[[], HealthCheckResult],
        probe_types: Optional[List[str]] = None,
    ) -> None:
        """Register a health check provider.

        Args:
            name: Unique provider name.
            check: Callable returning a HealthCheckResult.
            probe_types: Probe types this provider participates in.
                Defaults to ["livez", "readyz"].

        Raises:
            ValueError: If any probe type is not in VALID_PROBE_TYPES.
        """
        if probe_types is None:
            probe_types = list(DEFAULT_PROBE_TYPES)
        invalid = [p for p in probe_types if p not in VALID_PROBE_TYPES]
        if invalid:
            raise ValueError(f"Invalid probe types {invalid}. " f"Valid types: {VALID_PROBE_TYPES}")
        with self._lock:
            self._providers[name] = _ProviderEntry(check=check, probe_types=probe_types)

    def deregister(self, name: str) -> None:
        """Remove a provider from the registry."""
        with self._lock:
            self._providers.pop(name, None)

    def get_provider(self, name: str) -> Optional[_ProviderEntry]:
        """Get a single provider entry by name, or None."""
        with self._lock:
            entry = self._providers.get(name)
            if entry is None:
                return None
            return _ProviderEntry(check=entry.check, probe_types=list(entry.probe_types))

    def get_providers_for_probe(self, probe_type: str) -> Dict[str, _ProviderEntry]:
        """Return a snapshot of providers registered for a given probe type."""
        with self._lock:
            return {
                name: _ProviderEntry(check=entry.check, probe_types=list(entry.probe_types))
                for name, entry in self._providers.items()
                if probe_type in entry.probe_types
            }

    def get_all_providers(self) -> Dict[str, _ProviderEntry]:
        """Return a snapshot of all registered providers."""
        with self._lock:
            return {
                name: _ProviderEntry(check=entry.check, probe_types=list(entry.probe_types))
                for name, entry in self._providers.items()
            }
