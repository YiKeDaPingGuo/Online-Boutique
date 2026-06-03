from __future__ import annotations

from aiops_agent.detectors.rule_based import RuleBasedDetector
from aiops_agent.types import Anomaly, MetricPoint


class PaperAlgorithmAdapter:
    """Adapter reserved for the paper reproduction team's algorithm.

    Replace the fallback implementation with a call such as:
    `from paper_impl import run_algorithm`.
    """

    def __init__(self, fallback: RuleBasedDetector):
        self.fallback = fallback

    def detect(self, metrics: list[MetricPoint]) -> list[Anomaly]:
        return self.fallback.detect(metrics)

