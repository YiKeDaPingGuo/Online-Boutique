from __future__ import annotations

import csv
from pathlib import Path

from aiops_agent.datasource.base import DataSource
from aiops_agent.types import MetricPoint


class CSVDataSource(DataSource):
    def collect(self) -> list[MetricPoint]:
        if not self.config.datasource.csv_file:
            raise ValueError("datasource.csv_file is required for csv datasource")

        path = Path(self.config.datasource.csv_file)
        points: list[MetricPoint] = []
        with path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                metrics = {
                    key: float(value)
                    for key, value in row.items()
                    if key not in {"timestamp", "service", "namespace"} and value not in {"", None}
                }
                points.append(
                    {
                        "timestamp": row["timestamp"],
                        "service": row["service"],
                        "namespace": row.get("namespace") or self.config.kubernetes.namespace,
                        "metrics": metrics,
                    }
                )
        return points

