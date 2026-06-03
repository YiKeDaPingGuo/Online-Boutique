from __future__ import annotations

import re
from pathlib import Path
from string import Template

import requests
import yaml

from aiops_agent.datasource.base import DataSource
from aiops_agent.types import MetricPoint


class PrometheusDataSource(DataSource):
    def collect(self) -> list[MetricPoint]:
        mapping_path = Path(self.config.prometheus.metric_mapping_file)
        mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
        points_by_service: dict[str, MetricPoint] = {}

        for service in self.config.services:
            points_by_service[service] = {
                "timestamp": "",
                "service": service,
                "namespace": self.config.kubernetes.namespace,
                "metrics": {},
            }
            for metric_name, metric_cfg in mapping["metrics"].items():
                query = Template(metric_cfg["query"]).safe_substitute(
                    namespace=self.config.kubernetes.namespace,
                    service=service,
                )
                value = self._query_scalar(query)
                points_by_service[service]["metrics"][metric_name] = value

        return list(points_by_service.values())

    def _query_scalar(self, query: str) -> float:
        response = requests.get(
            f"{self.config.prometheus.base_url.rstrip('/')}/api/v1/query",
            params={"query": query},
            timeout=self.config.prometheus.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("data", {}).get("result", [])
        if not results:
            return 0.0
        value = results[0].get("value", [None, "0"])[1]
        if isinstance(value, str) and re.match(r"^-?\d+(\.\d+)?$", value):
            return float(value)
        return 0.0

