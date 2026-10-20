# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import prometheus_client as prometheus
from omni.services.facilities import base
from prometheus_client import registry as _registry
from prometheus_client.metrics import MetricWrapperBase


class MetricsFacility(base.Facility):

    def __init__(self, service: str):
        self._service = service

        self._metrics = {
            prometheus.Gauge: {},
            prometheus.Histogram: {},
            prometheus.Counter: {},
            prometheus.Counter: {},
            prometheus.Summary: {},
            prometheus.Info: {},
            prometheus.Enum: {},
        }

    def gauge(self, name, documentation, **kwargs):
        return self._get_metrics_wrapper(prometheus.Gauge, name, documentation, **kwargs)

    def histogram(self, name, documentation, **kwargs):
        return self._get_metrics_wrapper(prometheus.Histogram, name, documentation, **kwargs)

    def counter(self, name, documentation, **kwargs):
        return self._get_metrics_wrapper(prometheus.Counter, name, documentation, **kwargs)

    def summaries(self, name, documentation, **kwargs):
        return self._get_metrics_wrapper(prometheus.Summary, name, documentation, **kwargs)

    def infos(self, name, documentation, **kwargs):
        return self._get_metrics_wrapper(prometheus.Info, name, documentation, **kwargs)

    def enums(self, name, documentation, **kwargs):
        return self._get_metrics_wrapper(prometheus.Enum, name, documentation, **kwargs)

    def _get_metrics_wrapper(
        self,
        class_,
        name,
        documentation,
        labelnames=None,
        namespace=None,
        subsystem=None,
        unit=None,
        registry=None,
        **kwargs,
    ) -> MetricWrapperBase:

        namespace = f"{self._service}_{namespace}" if namespace else self._service
        key = hash((name, documentation, labelnames, namespace, subsystem, unit, registry, tuple(kwargs)))

        metric_watcher = self._metrics[class_].get(key)
        if metric_watcher:
            return metric_watcher

        metric_watcher = class_(
            name,
            documentation,
            labelnames=labelnames or (),
            namespace=namespace,
            subsystem=subsystem or "",
            unit=unit or "",
            registry=registry or _registry.REGISTRY,
            **kwargs,
        )

        self._metrics[class_][key] = metric_watcher
        return metric_watcher
