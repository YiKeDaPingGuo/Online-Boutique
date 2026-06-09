"""
Prometheus 数据导出脚本（双模式）
- oversee 模式: 从 default 命名空间的 Prometheus 导出 oversee 微服务指标
- cluster 模式: 从 monitoring 命名空间的 Prometheus 导出集群指标

用法:
  终端1（端口转发）:
    kubectl port-forward svc/prometheus -n default 9090:9090     # oversee
    kubectl port-forward svc/prometheus -n monitoring 9090:9090   # cluster

  终端2（运行本脚本）:
    python export_prometheus_data.py

依赖:
  pip install requests
"""

import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

# 本地时区（北京时间 UTC+8）
try:
    import zoneinfo
    LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Shanghai")
except Exception:
    # 兼容 Python 3.8 及以下
    LOCAL_TZ = timezone(timedelta(hours=8), "CST")


import requests

# ============================================================
# 输出目录（所有数据集中放在这里）
# ============================================================
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "exported_data", "exported_data_all")

# ============================================================
# 配置: 每个导出任务 = Prometheus地址 + 时间范围 + 指标组
# ============================================================
EXPORT_TASKS = [
    {
        "name": "oversee_24h",
        "prometheus_url": "http://localhost:9090",
        "hours": 24,
        "step": 15,
        "groups": {
            "oversee_requests": [
                "online_boutique_requests_total",
                "online_boutique_request_latency",
                "online_boutique_errors_total",
            ],
            "oversee_http": [
                "http_server_requests_seconds_count",
                "http_server_requests_seconds_sum",
                "http_server_requests_seconds_max",
            ],
            "oversee_jvm_memory": [
                "jvm_memory_used_bytes",
                "jvm_memory_committed_bytes",
                "jvm_memory_max_bytes",
            ],
            "oversee_cpu": [
                "process_cpu_usage",
                "system_cpu_usage",
                "system_load_average_1m",
            ],
            "oversee_jvm_gc": [
                "jvm_gc_pause_seconds_count",
                "jvm_gc_pause_seconds_sum",
                "jvm_gc_memory_allocated_bytes_total",
                "jvm_gc_memory_promoted_bytes_total",
            ],
            "oversee_threads": [
                "jvm_threads_live_threads",
                "jvm_threads_daemon_threads",
                "jvm_threads_peak_threads",
            ],
            "oversee_disk": [
                "disk_free_bytes",
                "disk_total_bytes",
            ],
        },
    },
    {
        "name": "cluster_24h",
        "prometheus_url": "http://localhost:9091",
        "hours": 24,
        "step": 30,
        "groups": {
            "cluster_node_cpu": [
                "node_cpu_seconds_total",
                "node_load1",
                "node_load5",
                "node_load15",
                "node_procs_running",
                "node_procs_blocked",
            ],
            "cluster_node_memory": [
                "node_memory_MemTotal_bytes",
                "node_memory_MemFree_bytes",
                "node_memory_MemAvailable_bytes",
                "node_memory_Buffers_bytes",
                "node_memory_Cached_bytes",
            ],
            "cluster_node_disk": [
                "node_filesystem_avail_bytes",
                "node_filesystem_size_bytes",
                "node_filesystem_free_bytes",
            ],
            "cluster_node_network": [
                "node_network_receive_bytes_total",
                "node_network_transmit_bytes_total",
            ],
            "cluster_node_diskio": [
                "node_disk_read_bytes_total",
                "node_disk_written_bytes_total",
                "node_disk_io_time_seconds_total",
            ],
            "cluster_pod_resources": [
                "kube_pod_container_resource_requests",
                "kube_pod_container_resource_limits",
                "container_cpu_usage_seconds_total",
                "container_memory_working_set_bytes",
            ],
            "cluster_node_info": [
                "node_boot_time_seconds",
                "node_nf_conntrack_entries",
            ],
        },
    },
]


# ============================================================
# 核心逻辑
# ============================================================


def query_prometheus(
    url: str,
    metric: str,
    start_time: datetime,
    end_time: datetime,
    step: int,
) -> list[dict[str, Any]]:
    """通过 Prometheus HTTP API 查询某个指标在时间范围内的数据"""
    params = {
        "query": metric,
        "start": start_time.timestamp(),
        "end": end_time.timestamp(),
        "step": step,
    }
    try:
        resp = requests.get(f"{url}/api/v1/query_range", params=params, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        if result["status"] != "success":
            print(f"    [警告] 查询失败: {result.get('error', '未知错误')}")
            return []

        return result["data"]["result"]
    except requests.RequestException as e:
        print(f"    [错误] 请求异常: {e}")
        return []


def flatten_series(series_list: list[dict[str, Any]], metric_name: str) -> list[dict[str, Any]]:
    """将 Prometheus time-series 展平为行记录"""
    rows = []
    for series in series_list:
        labels = series.get("metric", {})
        values = series.get("values", [])
        for ts_str, val_str in values:
            try:
                val = float(val_str)
            except (ValueError, TypeError):
                continue
            row = {
                "timestamp": int(ts_str),
                "datetime": datetime.fromtimestamp(int(ts_str), tz=LOCAL_TZ).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "metric": metric_name,
                "value": val,
            }
            for k, v in labels.items():
                if k != "__name__":
                    row[f"label_{k}"] = v
            rows.append(row)
    return rows


def export_task(task: dict):
    """执行一个导出任务"""
    name = task["name"]
    url = task["prometheus_url"]
    hours = task["hours"]
    step = task["step"]
    groups = task["groups"]

    end_time = datetime.now(LOCAL_TZ)
    start_time = end_time - timedelta(hours=hours)

    print(f"\n{'='*60}")
    print(f"任务: {name}")
    print(f" Prometheus: {url}")
    print(f" 时间范围: {start_time.strftime('%m-%d %H:%M')} ~ {end_time.strftime('%m-%d %H:%M')} ({hours}h)")
    print(f" 采样间隔: {step}s")
    print(f"{'='*60}")

    # 检查连接
    try:
        resp = requests.get(f"{url}/api/v1/query", params={"query": "up"}, timeout=5)
        if resp.status_code != 200:
            print(f" [跳过] 无法连接到 {url}")
            return
    except requests.RequestException:
        print(f" [跳过] 无法连接到 {url}")
        return

    total_rows = 0
    for group_name, metrics in groups.items():
        all_rows: list[dict[str, Any]] = []
        print(f"\n  [{group_name}]")
        for metric in metrics:
            print(f"   查询: {metric} ...", end=" ", flush=True)
            series_list = query_prometheus(url, metric, start_time, end_time, step)
            if not series_list:
                print("无数据")
                continue
            rows = flatten_series(series_list, metric)
            all_rows.extend(rows)
            print(f"{len(rows)} 条")

        if not all_rows:
            print(f"   [{group_name}] 无数据，跳过")
            continue

        fieldnames = ["timestamp", "datetime", "metric", "value"]
        label_fields = sorted({k for row in all_rows for k in row if k.startswith("label_")})
        fieldnames.extend(label_fields)

        filename = f"{name}_{group_name}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"   => 已导出 {len(all_rows)} 行 -> {filename}")
        total_rows += len(all_rows)

    print(f"\n [{name}] 完成，共导出 {total_rows} 条数据")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"所有数据将保存至: {os.path.abspath(OUTPUT_DIR)}")
    print(f"(请确保已在新终端执行对应的 port-forward)")

    for task in EXPORT_TASKS:
        export_task(task)

    print(f"\n{'='*60}")
    print("全部导出完毕！")
    print(f"数据保存在: {os.path.abspath(OUTPUT_DIR)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
