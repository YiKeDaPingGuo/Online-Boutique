from pathlib import Path

import pandas as pd


MYDATA_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = MYDATA_DIR / "raw_self"
OUT_DIR = MYDATA_DIR / "processed" / "full_log_based"
DATA_DIR = OUT_DIR / "data"
LABEL_DIR = OUT_DIR / "label"
META_DIR = OUT_DIR / "metadata"
CONFIG_DIR = OUT_DIR / "configs"
RESULT_DIR = OUT_DIR / "result"

CSV_FILES = [
    "normal_train.csv",
    "normal_valid.csv",
    "fault_cpu_frontend.csv",
    "fault_mem_recommendation.csv",
    "fault_delay_cart_repeat_500ms.csv",
    "fault_kill_product_repeat.csv",
]

# Label windows are based on mydata/experiment-log.md.
# For repeated network delay and pod kill, these are the expanded evaluation windows.
LABEL_WINDOWS = {
    "fault_cpu_frontend.csv": [
        ("2026-06-07 14:33:28", "2026-06-07 14:43:28"),
    ],
    "fault_mem_recommendation.csv": [
        ("2026-06-07 15:38:26", "2026-06-07 15:48:26"),
    ],
    "fault_delay_cart_repeat_500ms.csv": [
        ("2026-06-07 19:29:14", "2026-06-07 19:34:15"),
        ("2026-06-07 19:36:25", "2026-06-07 19:41:26"),
        ("2026-06-07 19:45:03", "2026-06-07 19:52:04"),
    ],
    "fault_kill_product_repeat.csv": [
        ("2026-06-07 20:42:32", "2026-06-07 20:44:32"),
        ("2026-06-07 20:47:53", "2026-06-07 20:49:53"),
        ("2026-06-07 20:53:15", "2026-06-07 20:55:15"),
    ],
}

FAULT_META = {
    "normal_train.csv": ("normal", ""),
    "normal_valid.csv": ("normal", ""),
    "fault_cpu_frontend.csv": ("cpu_stress", "frontend"),
    "fault_mem_recommendation.csv": ("memory_stress", "recommendationservice"),
    "fault_delay_cart_repeat_500ms.csv": ("network_delay_500ms_repeat", "cartservice"),
    "fault_kill_product_repeat.csv": ("pod_kill_repeat", "productcatalogservice"),
}


def ensure_dirs():
    for path in [DATA_DIR, LABEL_DIR, META_DIR, CONFIG_DIR, RESULT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_raw_csv(name):
    path = RAW_DIR / name
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def make_label(name, timestamps):
    label = pd.Series(0, index=timestamps.index, dtype=int)
    for start, end in LABEL_WINDOWS.get(name, []):
        start = pd.Timestamp(start)
        end = pd.Timestamp(end)
        label.loc[(timestamps >= start) & (timestamps <= end)] = 1
    return label


def write_detector_config(file_stem, row_count, col_count):
    config = f"""sample_score_method:
  lesinn:
    phi: 10
    t: 5
  moving_average:
    window: 20
    stride: 5
anomaly_scoring:
  anomaly_score_example:
    percentage: 90
    topn: 2
global:
  random_state: 42
data:
  path: '../mydata/processed/full_log_based/data/{file_stem}.csv'
  label_path: '../mydata/processed/full_log_based/label/{file_stem}.csv'
  save_path: '../mydata/processed/full_log_based/result/{file_stem}'
  row_begin: 0
  row_end: {row_count}
  col_begin: 0
  col_end: {col_count}
  rec_windows_per_cycle: 3
  header: null
  reconstruct:
    window: 40
    stride: 40
  detect:
    window: 20
    stride: 5
detector_arguments:
  workers: 1
  anomaly_scoring: 'anomaly_score_example'
  sample_score_method: 'moving_average_score'
  cluster_threshold: 0.01
  sample_rate: 0.6
  latest_windows: 20
  scale: 5
  rho: 0.1
  sigma: 0.5
  retry_limit: 20
  without_grouping: one_by_one
  without_localize_sampling: true
"""
    (CONFIG_DIR / f"{file_stem}.yml").write_text(config, encoding="utf-8")


def main():
    ensure_dirs()

    raw = {name: read_raw_csv(name) for name in CSV_FILES}
    reference_columns = list(raw[CSV_FILES[0]].columns)
    for name, df in raw.items():
        if list(df.columns) != reference_columns:
            raise ValueError(f"{name} columns differ from normal_train.csv")

    feature_columns = [col for col in reference_columns if col != "timestamp"]
    (META_DIR / "feature_columns.txt").write_text(
        "\n".join(feature_columns) + "\n", encoding="utf-8"
    )

    summary_rows = []
    processed_frames = {}
    processed_labels = {}

    for name, df in raw.items():
        timestamps = df["timestamp"]
        features = df[feature_columns].apply(pd.to_numeric, errors="coerce")
        missing_values = int(features.isna().sum().sum())
        duplicate_timestamps = int(timestamps.duplicated().sum())
        features = features.interpolate(limit_direction="both").fillna(0.0)
        label = make_label(name, timestamps)

        stem = Path(name).stem
        features.to_csv(DATA_DIR / f"{stem}.csv", index=False, header=False)
        label.to_csv(LABEL_DIR / f"{stem}.csv", index=False, header=False)

        processed_frames[stem] = features
        processed_labels[stem] = label
        fault_type, target_service = FAULT_META[name]

        summary_rows.append({
            "file": name,
            "processed_data": f"data/{stem}.csv",
            "processed_label": f"label/{stem}.csv",
            "rows": len(features),
            "columns": features.shape[1],
            "start_time": timestamps.min(),
            "end_time": timestamps.max(),
            "positive_labels": int(label.sum()),
            "missing_values_before_fill": missing_values,
            "duplicate_timestamps": duplicate_timestamps,
            "fault_type": fault_type,
            "target_service": target_service,
        })
        if len(features) >= 120:
            write_detector_config(stem, len(features), features.shape[1])

    test_order = [
        "normal_valid",
        "fault_cpu_frontend",
        "fault_mem_recommendation",
        "fault_delay_cart_repeat_500ms",
        "fault_kill_product_repeat",
    ]
    combined_data = pd.concat(
        [processed_frames[name] for name in test_order],
        ignore_index=True,
    )
    combined_label = pd.concat(
        [processed_labels[name] for name in test_order],
        ignore_index=True,
    )
    combined_data.to_csv(DATA_DIR / "test_all.csv", index=False, header=False)
    combined_label.to_csv(LABEL_DIR / "test_all.csv", index=False, header=False)
    write_detector_config("test_all", len(combined_data), combined_data.shape[1])

    summary_rows.append({
        "file": "test_all.csv",
        "processed_data": "data/test_all.csv",
        "processed_label": "label/test_all.csv",
        "rows": len(combined_data),
        "columns": combined_data.shape[1],
        "start_time": "",
        "end_time": "",
        "positive_labels": int(combined_label.sum()),
        "missing_values_before_fill": 0,
        "duplicate_timestamps": 0,
        "fault_type": "mixed",
        "target_service": "frontend/recommendationservice/cartservice/productcatalogservice",
    })

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(META_DIR / "summary.csv", index=False)

    readme = """# processed Online Boutique dataset

这个目录由 `../process_mydata.py` 生成，用于把 `mydata` 原始 CSV 转成 JumpStarter 输入格式。

## 内容

- `data/`：去掉 `timestamp` 和 header 后的纯数值 CSV。
- `label/`：和 `data/` 同行数的 0/1 label。
- `configs/`：可直接传给 `detector/run_detector.py` 的配置。
- `metadata/summary.csv`：每个文件的行数、列数、时间范围、正样本数量。
- `metadata/feature_columns.txt`：进入模型的 55 个指标列。
- `result/`：JumpStarter 运行结果目录。

## Label 规则

- normal 文件全部标为 0。
- CPU / memory stress 使用故障开始到故障结束时间段标为 1。
- repeated network delay 使用日志中建议的扩展异常段。
- repeated pod kill 使用每次 kill 后 2 分钟恢复窗口。

## 运行

从项目根目录重新处理：

```powershell
python mydata\\process_mydata.py
```

从 `detector/` 目录运行合并测试集：

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\\mydata\\processed\\configs\\test_all.yml
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print("Processed mydata into:", OUT_DIR)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
