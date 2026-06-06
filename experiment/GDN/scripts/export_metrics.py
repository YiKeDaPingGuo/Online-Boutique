#!/usr/bin/env python3
"""Export Online Boutique Prometheus metrics to CSV for GDN experiment."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request

SERVICES = [
    "frontend",
    "cartservice",
    "checkoutservice",
    "productcatalogservice",
    "recommendationservice",
    "paymentservice",
    "currencyservice",
    "shippingservice",
    "emailservice",
    "adservice",
    "redis-cart",
]

CORE_METRICS = {
    "cpu": 'sum(rate(container_cpu_usage_seconds_total{{namespace="{ns}", pod=~"{svc}.*"}}[1m]))',
    "mem": 'sum(container_memory_working_set_bytes{{namespace="{ns}", pod=~"{svc}.*"}})',
}

NETWORK_METRICS = {
    "net_rx": 'sum(rate(container_network_receive_bytes_total{{namespace="{ns}", pod=~"{svc}.*", interface!="lo"}}[1m]))',
    "net_tx": 'sum(rate(container_network_transmit_bytes_total{{namespace="{ns}", pod=~"{svc}.*", interface!="lo"}}[1m]))',
}


def prom_query(base_url: str, query: str, start: int | None = None, end: int | None = None, step: int | None = None):
    if start is None:
        params = urllib.parse.urlencode({"query": query})
        url = f"{base_url.rstrip('/')}/api/v1/query?{params}"
    else:
        params = urllib.parse.urlencode(
            {"query": query, "start": start, "end": end, "step": step}
        )
        url = f"{base_url.rstrip('/')}/api/v1/query_range?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("status") != "success":
        raise RuntimeError(payload)
    return payload["data"]["result"]


def network_metrics_available(base_url: str, namespace: str, sample_service: str = "frontend") -> bool:
    """Return True when pod-level network metrics exist in Prometheus."""
    probes = [
        f'container_network_receive_bytes_total{{namespace="{namespace}", pod=~"{sample_service}.*"}}',
        f'sum(rate(container_network_receive_bytes_total{{namespace="{namespace}", pod=~"{sample_service}.*", interface!="lo"}}[5m]))',
    ]
    for query in probes:
        if prom_query(base_url, query):
            return True
    return False


def select_metric_templates(include_network: bool, base_url: str, namespace: str):
    metrics = dict(CORE_METRICS)
    if not include_network:
        return metrics, []

    if network_metrics_available(base_url, namespace):
        metrics.update(NETWORK_METRICS)
        return metrics, []

    skipped = list(NETWORK_METRICS.keys())
    print(
        "Warning: pod-level container_network_* metrics are unavailable in this cluster. "
        "Exporting cpu/mem only.",
        file=sys.stderr,
    )
    return metrics, skipped


def main():
    parser = argparse.ArgumentParser(description="Export Prometheus metrics to CSV")
    parser.add_argument("--prometheus", default="http://127.0.0.1:19090")
    parser.add_argument("--namespace", default="onlineboutique")
    parser.add_argument("--start", help='Start time, e.g. "2026-06-05 14:00:00"')
    parser.add_argument("--end", help='End time, e.g. "2026-06-05 14:30:00"')
    parser.add_argument("--step", type=int, default=30, help="Step seconds, default 30")
    parser.add_argument("--output", help="Output CSV path")
    parser.add_argument(
        "--include-network",
        action="store_true",
        help="Try to include net_rx/net_tx when Prometheus exposes pod-level network metrics",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Only check which metrics are available and exit",
    )
    args = parser.parse_args()

    metrics, skipped = select_metric_templates(args.include_network, args.prometheus, args.namespace)
    available = ["cpu", "mem"]
    if "net_rx" in metrics:
        available.extend(["net_rx", "net_tx"])

    if args.probe_only:
        print(f"namespace: {args.namespace}")
        print(f"available metrics: {', '.join(available)}")
        if skipped:
            print(f"skipped metrics: {', '.join(skipped)}")
        return

    if not args.start or not args.end or not args.output:
        parser.error("--start, --end, and --output are required unless --probe-only is set")

    start_ts = int(dt.datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S").timestamp())
    end_ts = int(dt.datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S").timestamp())

    columns = ["timestamp"]
    for svc in SERVICES:
        for metric in metrics:
            columns.append(f"{svc}_{metric}")

    series_map = {}
    empty_columns = []
    for svc in SERVICES:
        for metric_name, template in metrics.items():
            col = f"{svc}_{metric_name}"
            query = template.format(ns=args.namespace, svc=svc)
            result = prom_query(args.prometheus, query, start_ts, end_ts, args.step)
            values = {}
            if result:
                for ts, val in result[0].get("values", []):
                    values[int(float(ts))] = val
            if not values:
                empty_columns.append(col)
            series_map[col] = values

    timestamps = sorted({ts for col_values in series_map.values() for ts in col_values.keys()})
    if not timestamps:
        raise RuntimeError("No metric data returned for the requested time range")

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for ts in timestamps:
            row = [dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")]
            for col in columns[1:]:
                row.append(series_map.get(col, {}).get(ts, ""))
            writer.writerow(row)

    print(f"Exported {len(timestamps)} rows to {args.output}")
    print(f"Metric columns: {len(columns) - 1} ({', '.join(sorted(set(m for m in metrics)))})")
    if empty_columns:
        print(f"Warning: {len(empty_columns)} columns had no data in this time range")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
