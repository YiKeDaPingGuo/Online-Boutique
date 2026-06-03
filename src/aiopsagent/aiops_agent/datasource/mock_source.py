from __future__ import annotations

import json
from pathlib import Path

from aiops_agent.datasource.base import DataSource
from aiops_agent.types import MetricPoint


class MockDataSource(DataSource):
    def collect(self) -> list[MetricPoint]:
        if not self.config.datasource.mock_file:
            raise ValueError("datasource.mock_file is required for mock datasource")

        path = Path(self.config.datasource.mock_file)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [MetricPoint(**item) for item in raw]

