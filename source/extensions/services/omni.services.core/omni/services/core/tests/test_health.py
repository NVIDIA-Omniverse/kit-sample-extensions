# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests for the health check registry, provider API, and probe endpoints."""

import concurrent.futures

import carb
from omni.kit.test import AsyncTestCase
from omni.services.core import main as services_main

from ..health import DEFAULT_PROBE_TYPES, HealthCheckRegistry, HealthCheckResult
from . import base


def _ok():
    return HealthCheckResult(healthy=True, message="ok")


def _fail():
    return HealthCheckResult(healthy=False, message="down")


class TestHealthCheckRegistry(AsyncTestCase):

    def setUp(self):
        super().setUp()
        self.registry = HealthCheckRegistry()

    async def test_result_defaults(self):
        r = HealthCheckResult(healthy=True)
        self.assertTrue(r.healthy)
        self.assertIsNone(r.message)

    async def test_register_and_get_provider(self):
        self.registry.register("a", _ok)
        entry = self.registry.get_provider("a")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.probe_types, DEFAULT_PROBE_TYPES)
        self.assertTrue(entry.check().healthy)

    async def test_get_provider_missing(self):
        self.assertIsNone(self.registry.get_provider("missing"))

    async def test_default_probe_types(self):
        self.registry.register("a", _ok)
        self.assertEqual(self.registry.get_provider("a").probe_types, ["livez", "readyz"])

    async def test_custom_probe_types(self):
        self.registry.register("a", _ok, probe_types=["startupz"])
        self.assertEqual(self.registry.get_provider("a").probe_types, ["startupz"])

    async def test_invalid_probe_type(self):
        with self.assertRaises(ValueError):
            self.registry.register("a", _ok, probe_types=["bogus"])

    async def test_deregister(self):
        self.registry.register("a", _ok)
        self.registry.deregister("a")
        self.assertIsNone(self.registry.get_provider("a"))

    async def test_deregister_missing_is_noop(self):
        self.registry.deregister("nonexistent")

    async def test_get_providers_for_probe(self):
        self.registry.register("a", _ok, probe_types=["livez", "readyz"])
        self.registry.register("b", _fail, probe_types=["readyz"])
        self.registry.register("c", _ok, probe_types=["startupz"])

        self.assertEqual(set(self.registry.get_providers_for_probe("livez").keys()), {"a"})
        self.assertEqual(set(self.registry.get_providers_for_probe("readyz").keys()), {"a", "b"})
        self.assertEqual(set(self.registry.get_providers_for_probe("startupz").keys()), {"c"})

    async def test_get_all_providers(self):
        self.registry.register("a", _ok)
        self.registry.register("b", _fail, probe_types=["startupz"])
        self.assertEqual(set(self.registry.get_all_providers().keys()), {"a", "b"})

    async def test_register_overwrites(self):
        self.registry.register("a", _ok, probe_types=["livez"])
        self.registry.register("a", _fail, probe_types=["startupz"])
        entry = self.registry.get_provider("a")
        self.assertEqual(entry.probe_types, ["startupz"])
        self.assertFalse(entry.check().healthy)

    async def test_snapshots_are_independent(self):
        """Mutating a returned snapshot doesn't affect the registry."""
        self.registry.register("a", _ok)
        snap = self.registry.get_all_providers()
        snap["a"].probe_types.append("startupz")
        self.assertEqual(self.registry.get_provider("a").probe_types, DEFAULT_PROBE_TYPES)

    async def test_concurrent_register_deregister(self):
        """Concurrent registration and deregistration shouldn't raise."""

        def register_batch(start):
            for i in range(start, start + 50):
                self.registry.register(f"p{i}", _ok)

        def deregister_batch(start):
            for i in range(start, start + 50):
                self.registry.deregister(f"p{i}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(register_batch, 0),
                pool.submit(register_batch, 50),
                pool.submit(deregister_batch, 0),
                pool.submit(deregister_batch, 50),
            ]
            for f in futures:
                f.result()


class TestHealthProviderAPI(AsyncTestCase):
    """Tests for the module-level health provider functions."""

    def setUp(self):
        super().setUp()
        self._registered = []

    def tearDown(self):
        for name in self._registered:
            services_main.deregister_health_provider(name)
        super().tearDown()

    def _register(self, name, check, probe_types=None):
        """Register a provider and track it for tearDown cleanup."""
        services_main.register_health_provider(name, check, probe_types)
        self._registered.append(name)

    async def test_register_and_deregister(self):
        self._register("test.provider", _ok)
        entry = services_main._singleton._health_registry.get_provider("test.provider")
        self.assertIsNotNone(entry)
        self.assertTrue(entry.check().healthy)

        services_main.deregister_health_provider("test.provider")
        self._registered.remove("test.provider")
        entry = services_main._singleton._health_registry.get_provider("test.provider")
        self.assertIsNone(entry)

    async def test_get_health_providers_active_status(self):
        self._register("test.active", _ok)
        self._register("test.inactive", _fail)

        settings = carb.settings.get_settings()
        settings.set(
            "/exts/omni.services.core/health/activeProviders",
            ["test.active"],
        )

        result = services_main.get_health_providers()
        self.assertIn("test.active", result)
        self.assertIn("test.inactive", result)
        self.assertTrue(result["test.active"]["active"])
        self.assertFalse(result["test.inactive"]["active"])

    async def test_get_health_providers_includes_probe_types(self):
        self._register("test.custom", _ok, probe_types=["startupz"])

        settings = carb.settings.get_settings()
        settings.set("/exts/omni.services.core/health/activeProviders", [])

        result = services_main.get_health_providers()
        self.assertEqual(result["test.custom"]["probe_types"], ["startupz"])


class TestBuiltinAppReadyProvider(AsyncTestCase):
    """Tests for the built-in omni.kit.app health provider."""

    async def test_builtin_provider_registered_on_startup(self):
        registry = services_main._singleton._health_registry
        entry = registry.get_provider("omni.kit.app")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.probe_types, ["livez", "readyz", "startupz"])

    async def test_builtin_provider_healthy_after_app_ready(self):
        """By test time the app-ready event has already fired."""
        registry = services_main._singleton._health_registry
        entry = registry.get_provider("omni.kit.app")
        result = entry.check()
        self.assertTrue(result.healthy)
        self.assertEqual(result.message, "App ready")

    async def test_builtin_provider_unhealthy_before_app_ready(self):
        ext = services_main._singleton
        original = ext._app_ready
        try:
            ext._app_ready = False
            entry = ext._health_registry.get_provider("omni.kit.app")
            result = entry.check()
            self.assertFalse(result.healthy)
            self.assertEqual(result.message, "App not ready")
        finally:
            ext._app_ready = original

    async def test_active_providers_default_includes_builtin(self):
        settings = carb.settings.get_settings()
        active = settings.get("/exts/omni.services.core/health/activeProviders")
        self.assertIn("omni.kit.app", active)


class TestProbeEndpoints(base.BaseServiceTest):
    """Tests for /livez, /readyz, /startupz endpoints."""

    _ACTIVE_SETTING = "/exts/omni.services.core/health/activeProviders"

    def setUp(self):
        super().setUp()
        self._settings = carb.settings.get_settings()
        self._orig_active = self._settings.get(self._ACTIVE_SETTING)
        self._registered = []

    def tearDown(self):
        for name in self._registered:
            services_main.deregister_health_provider(name)
        self._settings.set(self._ACTIVE_SETTING, self._orig_active)
        super().tearDown()

    def _register(self, name, check, probe_types=None):
        services_main.register_health_provider(name, check, probe_types)
        self._registered.append(name)

    async def test_livez_default_healthy(self):
        result, status = await self._get_request_async("/livez")
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "healthy")

    async def test_readyz_default_healthy(self):
        result, status = await self._get_request_async("/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "healthy")

    async def test_startupz_default_healthy(self):
        result, status = await self._get_request_async("/startupz")
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "healthy")

    async def test_unhealthy_provider_returns_503(self):
        self._register("test.down", _fail)
        self._settings.set(self._ACTIVE_SETTING, ["omni.kit.app", "test.down"])
        result, status = await self._get_request_async("/readyz")
        self.assertEqual(status, 503)
        self.assertEqual(result["status"], "unhealthy")
        self.assertFalse(result["providers"]["test.down"]["healthy"])

    async def test_provider_registered_but_not_active_is_ignored(self):
        self._register("test.inactive", _fail)
        # Only omni.kit.app is active (default); test.inactive not listed.
        self._settings.set(self._ACTIVE_SETTING, ["omni.kit.app"])
        result, status = await self._get_request_async("/readyz")
        self.assertEqual(status, 200)
        self.assertNotIn("test.inactive", result["providers"])

    async def test_multiple_providers_one_unhealthy(self):
        self._register("test.ok", _ok)
        self._register("test.down", _fail)
        self._settings.set(self._ACTIVE_SETTING, ["test.ok", "test.down"])
        result, status = await self._get_request_async("/livez")
        self.assertEqual(status, 503)
        self.assertTrue(result["providers"]["test.ok"]["healthy"])
        self.assertFalse(result["providers"]["test.down"]["healthy"])

    async def test_provider_exception_treated_as_unhealthy(self):
        def _raise():
            raise RuntimeError("boom")

        self._register("test.err", _raise)
        self._settings.set(self._ACTIVE_SETTING, ["test.err"])
        result, status = await self._get_request_async("/readyz")
        self.assertEqual(status, 503)
        self.assertFalse(result["providers"]["test.err"]["healthy"])
        self.assertIn("boom", result["providers"]["test.err"]["message"])

    async def test_empty_active_list_always_healthy(self):
        self._settings.set(self._ACTIVE_SETTING, [])
        result, status = await self._get_request_async("/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["providers"], {})

    async def test_probe_type_filtering(self):
        """A readyz-only provider should not appear in /livez."""
        self._register("test.readyz_only", _fail, probe_types=["readyz"])
        self._settings.set(self._ACTIVE_SETTING, ["test.readyz_only"])

        result, status = await self._get_request_async("/livez")
        self.assertEqual(status, 200)
        self.assertNotIn("test.readyz_only", result["providers"])

        result, status = await self._get_request_async("/readyz")
        self.assertEqual(status, 503)
        self.assertIn("test.readyz_only", result["providers"])

    async def test_evaluation_order_matches_settings(self):
        self._register("test.b", _ok)
        self._register("test.a", _ok)
        self._settings.set(self._ACTIVE_SETTING, ["test.a", "test.b"])
        result, status = await self._get_request_async("/livez")
        self.assertEqual(list(result["providers"].keys()), ["test.a", "test.b"])

    async def test_separate_check_per_probe(self):
        """Register the same provider name twice with different probe types;
        the second call overwrites the first."""
        self._register("test.split", _ok, probe_types=["livez"])
        # Re-register with a different probe type — overwrites.
        services_main.register_health_provider("test.split", _fail, probe_types=["readyz"])
        self._settings.set(self._ACTIVE_SETTING, ["test.split"])

        result, status = await self._get_request_async("/livez")
        self.assertEqual(status, 200)
        self.assertNotIn("test.split", result["providers"])

        result, status = await self._get_request_async("/readyz")
        self.assertEqual(status, 503)
        self.assertIn("test.split", result["providers"])

    async def test_startupz_extensible(self):
        """A custom provider can register for startupz."""
        self._register("test.slow_start", _fail, probe_types=["startupz"])
        self._settings.set(self._ACTIVE_SETTING, ["omni.kit.app", "test.slow_start"])
        result, status = await self._get_request_async("/startupz")
        self.assertEqual(status, 503)
        self.assertFalse(result["providers"]["test.slow_start"]["healthy"])


class TestDiscoveryEndpoint(base.BaseServiceTest):
    """Tests for GET /healthz/providers."""

    _ACTIVE_SETTING = "/exts/omni.services.core/health/activeProviders"

    def setUp(self):
        super().setUp()
        self._settings = carb.settings.get_settings()
        self._orig_active = self._settings.get(self._ACTIVE_SETTING)
        self._registered = []

    def tearDown(self):
        for name in self._registered:
            services_main.deregister_health_provider(name)
        self._settings.set(self._ACTIVE_SETTING, self._orig_active)
        super().tearDown()

    def _register(self, name, check, probe_types=None):
        services_main.register_health_provider(name, check, probe_types)
        self._registered.append(name)

    async def test_discovery_lists_providers(self):
        self._register("test.disc", _ok, probe_types=["startupz"])
        self._settings.set(self._ACTIVE_SETTING, ["omni.kit.app", "test.disc"])
        result, status = await self._get_request_async("/healthz/providers")
        self.assertEqual(status, 200)
        self.assertIn("omni.kit.app", result)
        self.assertTrue(result["omni.kit.app"]["active"])
        self.assertIn("test.disc", result)
        self.assertTrue(result["test.disc"]["active"])
        self.assertEqual(result["test.disc"]["probe_types"], ["startupz"])

    async def test_discovery_matches_programmatic(self):
        self._register("test.prog", _ok)
        self._settings.set(self._ACTIVE_SETTING, ["omni.kit.app"])
        http_result, status = await self._get_request_async("/healthz/providers")
        self.assertEqual(status, 200)
        prog_result = services_main.get_health_providers()
        self.assertEqual(http_result, prog_result)
