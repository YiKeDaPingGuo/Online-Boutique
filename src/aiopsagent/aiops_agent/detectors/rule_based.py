from __future__ import annotations

from aiops_agent.config import DetectorConfig
from aiops_agent.types import Anomaly, MetricPoint


DEFAULT_THRESHOLDS = {
    "cpu_usage": 0.8,
    "memory_usage": 0.8,
    "request_latency_p95": 500.0,
    "error_rate": 0.05,
    "pod_ready": 0.5,
}


class RuleBasedDetector:
    def __init__(self, config: DetectorConfig):
        self.thresholds = DEFAULT_THRESHOLDS | config.thresholds

    def detect(self, metrics: list[MetricPoint]) -> list[Anomaly]:
        anomalies: list[Anomaly] = []
        for point in metrics:
            for metric, threshold in self.thresholds.items():
                if metric not in point["metrics"]:
                    continue
                value = point["metrics"][metric]
                abnormal = value > threshold
                if metric == "pod_ready":
                    abnormal = value < threshold
                if not abnormal:
                    continue

                score = self._score(metric, value, threshold)
                anomalies.append(
                    {
                        "service": point["service"],
                        "metric": metric,
                        "value": value,
                        "threshold": threshold,
                        "score": score,
                        "reason": self._reason(metric, value, threshold),
                    }
                )
        return anomalies

    def _score(self, metric: str, value: float, threshold: float) -> float:
        if metric == "pod_ready":
            return 1.0 if value < threshold else 0.0
        if threshold <= 0:
            return min(value, 1.0)
        return min(max(value / threshold - 1.0, 0.0) + 0.5, 1.0)

    def _reason(self, metric: str, value: float, threshold: float) -> str:
        if metric == "pod_ready":
            return f"pod_ready={value:.2f}, below threshold {threshold:.2f}"
        return f"{metric}={value:.4f}, above threshold {threshold:.4f}"

