from __future__ import annotations

from typing import TypedDict

from aiops_agent.config import AppConfig


class MetricPoint(TypedDict):
    timestamp: str
    service: str
    namespace: str
    metrics: dict[str, float]


class Anomaly(TypedDict):
    service: str
    metric: str
    value: float
    threshold: float
    score: float
    reason: str


class RootCause(TypedDict):
    service: str
    score: float
    evidence: list[str]


class Action(TypedDict):
    action_type: str
    target_service: str
    namespace: str
    command: str
    risk: str
    require_confirm: bool
    status: str
    rationale: str


class AgentState(TypedDict):
    config: AppConfig
    metrics: list[MetricPoint]
    anomalies: list[Anomaly]
    root_causes: list[RootCause]
    actions: list[Action]
    executed_actions: list[Action]
    report: str
    errors: list[str]
