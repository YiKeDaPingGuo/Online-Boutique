from __future__ import annotations

from aiops_agent.config import AppConfig
from aiops_agent.datasource import CSVDataSource, DataSource, MockDataSource, PrometheusDataSource


def make_datasource(config: AppConfig) -> DataSource:
    if config.datasource.type == "mock":
        return MockDataSource(config)
    if config.datasource.type == "prometheus":
        return PrometheusDataSource(config)
    if config.datasource.type == "csv":
        return CSVDataSource(config)
    raise ValueError(f"Unsupported datasource: {config.datasource.type}")

