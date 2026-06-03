from __future__ import annotations

import argparse
import json
from pathlib import Path

from aiops_agent.agent.graph import build_graph
from aiops_agent.checks import run_preflight
from aiops_agent.config import load_config


def diagnose(config_path: str) -> None:
    config = load_config(config_path)
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

    output_dir = Path(config.output.dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "diagnosis_result.json"
    temp_json_path = output_dir / "diagnosis_result.json.tmp"
    temp_json_path.write_text(
        json.dumps(
            {
                "anomalies": result["anomalies"],
                "root_causes": result["root_causes"],
                "actions": result["actions"],
                "executed_actions": result["executed_actions"],
                "errors": result["errors"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temp_json_path.replace(json_path)

    print(result["report"])
    print(f"\nReport: {output_dir / 'diagnosis_report.md'}")
    print(f"JSON:   {json_path}")


def check(config_path: str) -> None:
    config = load_config(config_path)
    results = run_preflight(config)
    has_error = False
    for status, name, message in results:
        if status == "error":
            has_error = True
        print(f"[{status.upper()}] {name}: {message}")
    if has_error:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph AIOps Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    diagnose_parser = subparsers.add_parser("diagnose", help="Run one diagnosis cycle")
    diagnose_parser.add_argument("--config", required=True, help="Path to YAML config")

    check_parser = subparsers.add_parser("check", help="Validate config and datasource connectivity")
    check_parser.add_argument("--config", required=True, help="Path to YAML config")

    args = parser.parse_args()
    if args.command == "diagnose":
        diagnose(args.config)
    elif args.command == "check":
        check(args.config)


if __name__ == "__main__":
    main()
