from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    type: Literal["mock", "prometheus", "csv"] = "mock"
    mock_file: Optional[str] = None
    csv_file: Optional[str] = None


class PrometheusConfig(BaseModel):
    base_url: str = "http://localhost:9090"
    query_step_seconds: int = 30
    timeout_seconds: int = 10
    metric_mapping_file: str = "config/metric_mapping.yaml"


class KubernetesConfig(BaseModel):
    namespace: str = "online-boutique"


class ChaosMeshConfig(BaseModel):
    namespace: str = "chaos-mesh"
    experiment_namespace: str = "online-boutique"
    known_experiments: dict[str, str] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    enabled: bool = False
    provider: str = "volcengine-ark"
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    api_key_env: str = "ARK_API_KEY"
    model: str = "ep-20260528104127-tn2f7"
    temperature: float = 0.2


class DetectorConfig(BaseModel):
    type: Literal["rule", "paper"] = "rule"
    thresholds: dict[str, float] = Field(default_factory=dict)


class RemediationConfig(BaseModel):
    mode: Literal["dry-run", "execute"] = "dry-run"
    require_confirm: bool = True
    allow_execute_without_confirm: bool = False


class OutputConfig(BaseModel):
    dir: str = "outputs"


class AppConfig(BaseModel):
    project_name: str = "AIOps Agent for Online Boutique"
    services: list[str]
    window_minutes: int = 10
    top_k: int = 3
    datasource: DataSourceConfig = Field(default_factory=DataSourceConfig)
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)
    kubernetes: KubernetesConfig = Field(default_factory=KubernetesConfig)
    chaosmesh: ChaosMeshConfig = Field(default_factory=ChaosMeshConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    remediation: RemediationConfig = Field(default_factory=RemediationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(path: str) -> AppConfig:
    config_path = Path(path)
    data: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)
