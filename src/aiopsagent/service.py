from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from aiops_agent.agent.graph import build_graph
from aiops_agent.checks import run_preflight
from aiops_agent.config import AppConfig, load_config


DEFAULT_CONFIG_PATH = os.getenv("AIOPS_CONFIG", "config/online_boutique.yaml")


def run_diagnosis(config: AppConfig) -> dict[str, Any]:
    graph = build_graph(config)
    result = graph.invoke(
        {
            "config": config,
            "metrics": [],
            "anomalies": [],
            "root_causes": [],
            "actions": [],
            "executed_actions": [],
            "report": "",
            "errors": [],
        }
    )
    return {
        "status": "anomalous" if result["anomalies"] else "healthy",
        "metrics": result["metrics"],
        "anomalies": result["anomalies"],
        "root_causes": result["root_causes"],
        "actions": result["actions"],
        "executed_actions": result["executed_actions"],
        "errors": result["errors"],
        "report": result["report"],
    }


def load_request_config(payload: dict[str, Any]) -> AppConfig:
    config_path = payload.get("config_path") or DEFAULT_CONFIG_PATH
    config = load_config(str(config_path))
    overrides = payload.get("config_overrides") or {}
    if overrides:
        data = config.model_dump()
        _merge_dict(data, overrides)
        config = AppConfig.model_validate(data)
    return config


def _merge_dict(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_dict(base[key], value)
        else:
            base[key] = value


class AIOpsRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            if self.path == "/healthz":
                self._send_json({"status": "ok"})
                return
            if self.path == "/readyz":
                self._handle_ready()
                return
            if self.path == "/api/v1/capabilities":
                self._send_json(
                    {
                        "name": "aiopsagent",
                        "interfaces": [
                            "GET /healthz",
                            "GET /readyz",
                            "GET /api/v1/capabilities",
                            "GET /api/v1/config",
                            "POST /api/v1/preflight",
                            "POST /api/v1/diagnose",
                            "POST /api/v1/events",
                        ],
                        "datasources": ["prometheus", "mock", "csv"],
                        "remediation_modes": ["dry-run", "execute"],
                    }
                )
                return
            if self.path == "/api/v1/config":
                config = load_config(DEFAULT_CONFIG_PATH)
                self._send_json(config.model_dump())
                return
            self._send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def do_POST(self) -> None:
        try:
            if self.path == "/api/v1/preflight":
                payload = self._read_json()
                config = load_request_config(payload)
                checks = [
                    {"status": status, "name": name, "message": message}
                    for status, name, message in run_preflight(config)
                ]
                self._send_json({"checks": checks, "has_error": any(item["status"] == "error" for item in checks)})
                return
            if self.path == "/api/v1/diagnose":
                payload = self._read_json()
                config = load_request_config(payload)
                self._send_json(run_diagnosis(config))
                return
            if self.path == "/api/v1/events":
                payload = self._read_json()
                self._send_json(
                    {
                        "status": "accepted",
                        "message": "Event ingestion interface is reserved for oversee, loadgenerator, and future test tools.",
                        "event": payload,
                    },
                    status=202,
                )
                return
            self._send_json({"error": "not found"}, status=404)
        except json.JSONDecodeError as exc:
            self._send_json({"error": f"invalid json: {exc}"}, status=400)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)

    def _handle_ready(self) -> None:
        try:
            load_config(DEFAULT_CONFIG_PATH)
            self._send_json({"status": "ready", "config_path": DEFAULT_CONFIG_PATH})
        except Exception as exc:
            self._send_json({"status": "not-ready", "error": str(exc)}, status=503)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw_body = self.rfile.read(length)
        return json.loads(raw_body.decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.getenv("AIOPS_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), AIOpsRequestHandler)
    print(f"aiopsagent listening on {host}:{port} with config {DEFAULT_CONFIG_PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
