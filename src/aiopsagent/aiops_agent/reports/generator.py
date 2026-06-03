from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from langchain_openai import ChatOpenAI

from aiops_agent.config import AppConfig
from aiops_agent.types import Action, Anomaly, MetricPoint, RootCause


class ReportGenerator:
    def __init__(self, config: AppConfig):
        self.config = config
        self._load_local_env()

    def generate(
        self,
        metrics: list[MetricPoint],
        anomalies: list[Anomaly],
        root_causes: list[RootCause],
        actions: list[Action],
        executed_actions: list[Action],
        errors: list[str],
    ) -> str:
        llm_summary = self._llm_summary(metrics, anomalies, root_causes, actions, executed_actions, errors)
        report = self._markdown(metrics, anomalies, root_causes, actions, executed_actions, errors, llm_summary)
        output_dir = Path(self.config.output.dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "diagnosis_report.md"
        temp_path = output_dir / "diagnosis_report.md.tmp"
        temp_path.write_text(report, encoding="utf-8")
        temp_path.replace(report_path)
        return report

    def _llm_summary(
        self,
        metrics: list[MetricPoint],
        anomalies: list[Anomaly],
        root_causes: list[RootCause],
        actions: list[Action],
        executed_actions: list[Action],
        errors: list[str],
    ) -> str:
        if not self.config.llm.enabled:
            return "LLM disabled. Report generated from deterministic diagnosis results."

        api_key = os.getenv(self.config.llm.api_key_env)
        if not api_key:
            return f"LLM skipped because environment variable {self.config.llm.api_key_env} is not set."

        try:
            llm = ChatOpenAI(
                openai_api_key=api_key,
                openai_api_base=self.config.llm.base_url,
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
            )
            prompt = (
                "你是云原生智能运维专家。请基于以下结构化结果，用中文生成简洁诊断结论，"
                "包含系统状态、最可能根因、证据、建议动作。不要编造未给出的指标。\n\n"
                f"metrics={metrics}\n"
                f"anomalies={anomalies}\n"
                f"root_causes={root_causes}\n"
                f"actions={actions}\n"
                f"executed_actions={executed_actions}\n"
                f"errors={errors}\n"
            )
            return llm.invoke(prompt).content
        except Exception as exc:
            return f"LLM summary failed: {exc}"

    def _load_local_env(self) -> None:
        env_path = Path(".env")
        if not env_path.exists():
            return

        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

    def _markdown(
        self,
        metrics: list[MetricPoint],
        anomalies: list[Anomaly],
        root_causes: list[RootCause],
        actions: list[Action],
        executed_actions: list[Action],
        errors: list[str],
        llm_summary: str,
    ) -> str:
        now = datetime.now(timezone.utc).isoformat()
        status = "异常" if anomalies else "健康"
        lines = [
            "# AIOps Diagnosis Report",
            "",
            f"- Time: {now}",
            f"- Project: {self.config.project_name}",
            f"- Namespace: {self.config.kubernetes.namespace}",
            f"- Window: {self.config.window_minutes} minutes",
            f"- Status: {status}",
            "",
            "## Agent Summary",
            "",
            str(llm_summary),
            "",
            "## Root Cause Candidates",
            "",
        ]
        if root_causes:
            for index, cause in enumerate(root_causes, start=1):
                lines.append(f"{index}. {cause['service']} score={cause['score']}")
                for item in cause["evidence"]:
                    lines.append(f"   - {item}")
        else:
            lines.append("No root cause candidate found.")

        lines.extend(["", "## Anomalies", ""])
        if anomalies:
            for anomaly in anomalies:
                lines.append(
                    f"- {anomaly['service']} {anomaly['metric']}: value={anomaly['value']}, "
                    f"threshold={anomaly['threshold']}, score={anomaly['score']}"
                )
        else:
            lines.append("No anomaly detected.")

        lines.extend(["", "## Suggested Actions", ""])
        if actions:
            for action in actions:
                lines.append(
                    f"- [{action['status']}] {action['action_type']} {action['target_service']} "
                    f"risk={action['risk']} command=`{action['command']}`"
                )
                lines.append(f"  - rationale: {action['rationale']}")
        else:
            lines.append("No action required.")

        lines.extend(["", "## Action Execution", ""])
        if executed_actions:
            for action in executed_actions:
                lines.append(
                    f"- [{action['status']}] {action['action_type']} {action['target_service']} "
                    f"risk={action['risk']}"
                )
        else:
            lines.append("No action executed.")

        lines.extend(["", "## Metric Snapshot", ""])
        for point in metrics:
            lines.append(f"- {point['service']}: {point['metrics']}")

        if errors:
            lines.extend(["", "## Errors", ""])
            for error in errors:
                lines.append(f"- {error}")

        return "\n".join(lines) + "\n"
