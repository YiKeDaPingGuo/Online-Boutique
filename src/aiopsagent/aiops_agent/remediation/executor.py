from __future__ import annotations

import subprocess

from aiops_agent.config import AppConfig
from aiops_agent.types import Action


class ActionExecutor:
    def __init__(self, config: AppConfig):
        self.config = config

    def execute(self, actions: list[Action]) -> list[Action]:
        executed: list[Action] = []
        for action in actions:
            result = dict(action)
            if self.config.remediation.mode != "execute":
                result["status"] = "dry-run"
                executed.append(result)
                continue

            if action["require_confirm"] and not self.config.remediation.allow_execute_without_confirm:
                result["status"] = "blocked-confirmation-required"
                executed.append(result)
                continue

            if action["risk"] == "high" and not self.config.remediation.allow_execute_without_confirm:
                result["status"] = "blocked-high-risk"
                executed.append(result)
                continue

            try:
                completed = subprocess.run(
                    action["command"],
                    shell=True,
                    check=False,
                    text=True,
                    capture_output=True,
                    timeout=30,
                )
                result["status"] = "succeeded" if completed.returncode == 0 else "failed"
                result["rationale"] = (
                    f"{result['rationale']} stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
                )
            except Exception as exc:
                result["status"] = "failed"
                result["rationale"] = f"{result['rationale']} execution_error={exc}"

            executed.append(result)
        return executed

