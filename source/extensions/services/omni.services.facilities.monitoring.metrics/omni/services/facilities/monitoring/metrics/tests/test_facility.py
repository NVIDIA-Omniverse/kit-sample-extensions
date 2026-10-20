# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.test
from omni.services.facilities.monitoring.metrics.facilities import MetricsFacility


class TestMetricsFacility(omni.kit.test.AsyncTestCase):
    async def setUp(self):

        self._metrics = MetricsFacility("my_service")

    async def tearDown(self):
        self._metrics = None

    async def test_create_gauge(self):
        wrapper = self._metrics.gauge("test_gauge", "Test Gauge")
        metric = wrapper.collect()[0]
        self.assertEqual(metric.name, "my_service_test_gauge")
        self.assertEqual(metric.samples[0].value, 0.0)

    async def test_create_histogram(self):
        wrapper = self._metrics.histogram("test_histogram", "Test Histogram")
        metric = wrapper.collect()[0]
        self.assertEqual(metric.name, "my_service_test_histogram")
        self.assertEqual(metric.samples[0].value, 0.0)

    async def test_create_counter(self):
        wrapper = self._metrics.histogram("test_counter", "Test Counter")
        metric = wrapper.collect()[0]
        self.assertEqual(metric.name, "my_service_test_counter")
        self.assertEqual(metric.samples[0].value, 0.0)

    async def test_create_summaries(self):
        wrapper = self._metrics.summaries("test_summary", "Test Summary")
        metric = wrapper.collect()[0]
        self.assertEqual(metric.name, "my_service_test_summary")
        self.assertEqual(metric.samples[0].value, 0.0)

    async def test_create_infos(self):
        wrapper = self._metrics.infos("test_infos", "Test Infos")
        metric = wrapper.collect()[0]
        self.assertEqual(metric.name, "my_service_test_infos")
        self.assertEqual(metric.samples[0].value, 1.0)

    async def test_create_enums(self):
        wrapper = self._metrics.enums("test_enums", "Test Enums", states=["waiting", "late", "started"])
        metric = wrapper.collect()[0]
        self.assertEqual(metric.name, "my_service_test_enums")
        self.assertEqual(metric.samples[0].value, 1)
