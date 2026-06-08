import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


PROMETHEUS_URL = "http://localhost:9090"

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

METRICS = [
    "cpu",
    "mem",
    "request_rate",
    "latency",
    "error_rate",
]


def query_prometheus(promql):
    params = urllib.parse.urlencode({"query": promql})
    url = PROMETHEUS_URL + "/api/v1/query?" + params

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)
    except Exception as e:
        print("[WARN] Prometheus request failed:", e)
        print("[WARN] Query:", promql)
        return 0.0

    if result.get("status") != "success":
        print("[WARN] Prometheus query not successful:", result)
        print("[WARN] Query:", promql)
        return 0.0

    data = result.get("data", {}).get("result", [])

    if not data:
        return 0.0

    try:
        return float(data[0]["value"][1])
    except Exception:
        return 0.0


def build_query(service, metric, rate_window):
    pod_regex = service + "-.*"

    if metric == "cpu":
        return (
            "sum("
            'rate(container_cpu_usage_seconds_total{namespace="onlineboutique",pod=~"'
            + pod_regex +
            '"}[' + rate_window + "])"
            ")"
        )

    if metric == "mem":
        return (
            "sum("
            'container_memory_working_set_bytes{namespace="onlineboutique",pod=~"'
            + pod_regex +
            '"}'
            ")"
        )

    if metric == "request_rate":
        return (
            "sum("
            'rate(online_boutique_requests_total{service="'
            + service +
            '"}[' + rate_window + "])"
            ")"
        )

    if metric == "latency":
        return (
            "avg("
            'online_boutique_request_latency{service="'
            + service +
            '"}'
            ")"
        )

    if metric == "error_rate":
        return (
            "sum("
            'rate(online_boutique_errors_total{service="'
            + service +
            '"}[' + rate_window + "])"
            ")"
        )

    raise ValueError("Unknown metric: " + metric)


def build_header():
    header = ["timestamp"]
    for service in SERVICES:
        for metric in METRICS:
            header.append(service + "_" + metric)
    return header


def collect(output, minutes, interval, rate_window):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    header = build_header()

    start_time = time.time()
    end_time = start_time + minutes * 60

    print("=" * 80)
    print("Online Boutique metrics collector")
    print("Output file   :", output)
    print("Duration      :", minutes, "minutes")
    print("Interval      :", interval, "seconds")
    print("Rate window   :", rate_window)
    print("Prometheus URL:", PROMETHEUS_URL)
    print("=" * 80)
    print("Tip: Press Ctrl+C to stop early.")
    print()

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        row_count = 0

        try:
            while time.time() < end_time:
                loop_start = time.time()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row = [timestamp]

                for service in SERVICES:
                    for metric in METRICS:
                        promql = build_query(service, metric, rate_window)
                        value = query_prometheus(promql)
                        row.append(value)

                writer.writerow(row)
                f.flush()

                row_count += 1
                print("[{0:04d}] collected at {1}".format(row_count, timestamp))

                elapsed = time.time() - loop_start
                sleep_time = max(0, interval - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print()
            print("[INFO] Stopped by user.")

    print()
    print("[DONE] Saved {0} rows to {1}".format(row_count, output))


def main():
    parser = argparse.ArgumentParser(
        description="Collect Online Boutique metrics from Prometheus and save to CSV."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV file path, e.g. normal_test.csv",
    )
    parser.add_argument(
        "--minutes",
        type=float,
        default=10,
        help="Collection duration in minutes. Default: 10",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30,
        help="Collection interval in seconds. Default: 30",
    )
    parser.add_argument(
        "--rate-window",
        default="2m",
        help="Prometheus rate window. Default: 2m",
    )

    args = parser.parse_args()

    collect(
        output=args.output,
        minutes=args.minutes,
        interval=args.interval,
        rate_window=args.rate_window,
    )


if __name__ == "__main__":
    main()