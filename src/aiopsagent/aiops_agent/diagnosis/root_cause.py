from __future__ import annotations

from collections import defaultdict

from aiops_agent.types import Anomaly, RootCause


WEIGHTS = {
    "cpu_usage": 0.2,
    "memory_usage": 0.15,
    "request_latency_p95": 0.35,
    "error_rate": 0.25,
    "pod_ready": 0.05,
}


class RootCauseAnalyzer:
    def __init__(self, top_k: int):
        self.top_k = top_k

    def rank(self, anomalies: list[Anomaly]) -> list[RootCause]:
        scores: dict[str, float] = defaultdict(float)
        evidence: dict[str, list[str]] = defaultdict(list)

        for anomaly in anomalies:
            metric = anomaly["metric"]
            weighted_score = anomaly["score"] * WEIGHTS.get(metric, 0.1)
            scores[anomaly["service"]] += weighted_score
            evidence[anomaly["service"]].append(anomaly["reason"])

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [
            {
                "service": service,
                "score": round(score, 4),
                "evidence": evidence[service],
            }
            for service, score in ranked[: self.top_k]
        ]

