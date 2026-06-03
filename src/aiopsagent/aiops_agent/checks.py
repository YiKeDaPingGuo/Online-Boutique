from __future__ import annotations

from pathlib import Path

import requests

from aiops_agent.config import AppConfig
from aiops_agent.datasource.factory import make_datasource


def run_preflight(config: AppConfig) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []

    if config.services:
        results.append(("ok", "services", f"{len(config.services)} services configured"))
    else:
        results.append(("error", "services", "no service configured"))

    if config.datasource.type == "prometheus":
        results.extend(_check_prometheus(config))
    elif config.datasource.type == "mock":
        path = Path(config.datasource.mock_file or "")
        results.append(_check_file("mock_file", path))
    elif config.datasource.type == "csv":
        path = Path(config.datasource.csv_file or "")
        results.append(_check_file("csv_file", path))

    try:
        datasource = make_datasource(config)
        sample = datasource.collect()
        results.append(("ok", "datasource", f"collected {len(sample)} metric points"))
    except Exception as exc:
        results.append(("error", "datasource", str(exc)))

    return results


def _check_prometheus(config: AppConfig) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    mapping = Path(config.prometheus.metric_mapping_file)
    results.append(_check_file("metric_mapping", mapping))

    try:
        response = requests.get(
            f"{config.prometheus.base_url.rstrip('/')}/api/v1/status/runtimeinfo",
            timeout=config.prometheus.timeout_seconds,
        )
        if response.ok:
            results.append(("ok", "prometheus", f"connected to {config.prometheus.base_url}"))
        else:
            results.append(("error", "prometheus", f"HTTP {response.status_code} from {config.prometheus.base_url}"))
    except Exception as exc:
        results.append(("error", "prometheus", f"connection failed: {exc}"))

    return results


def _check_file(name: str, path: Path) -> tuple[str, str, str]:
    if path.exists():
        return ("ok", name, str(path))
    return ("error", name, f"file not found: {path}")

