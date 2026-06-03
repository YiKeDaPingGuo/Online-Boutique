from __future__ import annotations

from aiops_agent.config import AppConfig
from aiops_agent.types import Anomaly
from aiops_agent.types import Action, RootCause


class RemediationPlanner:
    def __init__(self, config: AppConfig):
        self.config = config

    def suggest(self, root_causes: list[RootCause], anomalies: list[Anomaly]) -> list[Action]:
        actions: list[Action] = []
        anomalies_by_service = self._group_anomalies(anomalies)
        for cause in root_causes:
            service = cause["service"]
            namespace = self.config.kubernetes.namespace
            service_anomalies = anomalies_by_service.get(service, [])
            experiment = self.config.chaosmesh.known_experiments.get(service)

            actions.append(
                {
                    "action_type": "inspect_pods",
                    "target_service": service,
                    "namespace": namespace,
                    "command": f"kubectl get pods -n {namespace} -l app={service} -o wide",
                    "risk": "low",
                    "require_confirm": False,
                    "status": "planned" if self.config.remediation.mode == "execute" else "dry-run",
                    "rationale": "Collect pod readiness, restart count, and node placement before remediation.",
                }
            )

            if experiment:
                actions.append(
                    {
                        "action_type": "delete_chaos_experiment",
                        "target_service": service,
                        "namespace": self.config.chaosmesh.experiment_namespace,
                        "command": (
                            f"kubectl delete networkchaos,podchaos,stresschaos {experiment} "
                            f"-n {self.config.chaosmesh.experiment_namespace} --ignore-not-found"
                        ),
                        "risk": "medium",
                        "require_confirm": self.config.remediation.require_confirm,
                        "status": "planned" if self.config.remediation.mode == "execute" else "dry-run",
                        "rationale": "A known ChaosMesh experiment targets this service; remove it before restarting pods.",
                    }
                )

            risk = "high" if any(item["metric"] == "pod_ready" for item in service_anomalies) else "medium"
            actions.append(
                {
                    "action_type": "restart_deployment",
                    "target_service": service,
                    "namespace": namespace,
                    "command": f"kubectl rollout restart deployment/{service} -n {namespace}",
                    "risk": risk,
                    "require_confirm": self.config.remediation.require_confirm,
                    "status": "planned" if self.config.remediation.mode == "execute" else "dry-run",
                    "rationale": "Restart only after evidence collection and optional ChaosMesh cleanup.",
                }
            )
        return actions

    def _group_anomalies(self, anomalies: list[Anomaly]) -> dict[str, list[Anomaly]]:
        grouped: dict[str, list[Anomaly]] = {}
        for anomaly in anomalies:
            grouped.setdefault(anomaly["service"], []).append(anomaly)
        return grouped
