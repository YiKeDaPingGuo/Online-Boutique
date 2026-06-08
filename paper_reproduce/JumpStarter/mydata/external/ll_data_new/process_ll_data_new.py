from pathlib import Path
import json

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "processed"
DATA_DIR = OUT_DIR / "data"
LABEL_DIR = OUT_DIR / "label"
META_DIR = OUT_DIR / "metadata"
CONFIG_DIR = OUT_DIR / "configs"
RESULT_DIR = OUT_DIR / "result"

CSV_FILES = [
    "normal_train.csv",
    "normal_valid.csv",
    "fault_cpu_frontend.csv",
    "fault_delay_cart.csv",
    "fault_kill_product.csv",
]

FAULT_JSON = {
    "fault_cpu_frontend.csv": "cpu_fault_run.json",
    "fault_delay_cart.csv": "delay_fault_run.json",
    "fault_kill_product.csv": "kill_fault_run.json",
}

FAULT_META = {
    "normal_train.csv": ("normal", ""),
    "normal_valid.csv": ("normal", ""),
    "fault_cpu_frontend.csv": ("cpu_stress", "frontend"),
    "fault_delay_cart.csv": ("network_delay", "cartservice"),
    "fault_kill_product.csv": ("pod_kill_or_service_fault", "productcatalogservice"),
}


def ensure_dirs():
    for path in [DATA_DIR, LABEL_DIR, META_DIR, CONFIG_DIR, RESULT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_raw_csv(name):
    df = pd.read_csv(BASE_DIR / name)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def load_fault_window(name):
    json_name = FAULT_JSON.get(name)
    if not json_name:
        return []
    with (BASE_DIR / json_name).open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    return [(pd.Timestamp(payload["fault_start"]), pd.Timestamp(payload["fault_end"]))]


def make_label(name, timestamps):
    label = pd.Series(0, index=timestamps.index, dtype=int)
    for start, end in load_fault_window(name):
        label.loc[(timestamps >= start) & (timestamps <= end)] = 1
    return label


def write_detector_config(file_stem, row_count, col_count, window):
    detect_window = max(2, window // 2)
    stride = max(1, window // 2)
    config = f"""sample_score_method:
  lesinn:
    phi: 10
    t: 5
  moving_average:
    window: {detect_window}
    stride: 1
anomaly_scoring:
  anomaly_score_example:
    percentage: 90
    topn: 2
global:
  random_state: 42
data:
  path: '../mydata/external/ll_data_new/processed/data/{file_stem}.csv'
  label_path: '../mydata/external/ll_data_new/processed/label/{file_stem}.csv'
  save_path: '../mydata/external/ll_data_new/processed/result/{file_stem}_w{window}'
  row_begin: 0
  row_end: {row_count}
  col_begin: 0
  col_end: {col_count}
  rec_windows_per_cycle: 3
  header: null
  reconstruct:
    window: {window}
    stride: {stride}
  detect:
    window: {detect_window}
    stride: 1
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
    (CONFIG_DIR / f"{file_stem}_w{window}.yml").write_text(config, encoding="utf-8")


def main():
    ensure_dirs()

    raw = {name: read_raw_csv(name) for name in CSV_FILES}
    reference_columns = list(raw[CSV_FILES[0]].columns)
    for name, df in raw.items():
        if list(df.columns) != reference_columns:
            raise ValueError(f"{name} columns differ from normal_train.csv")

    candidate_feature_columns = [col for col in reference_columns if col != "timestamp"]
    feature_columns = [
        col
        for col in candidate_feature_columns
        if any(raw[name][col].notna().any() for name in CSV_FILES)
    ]
    dropped_columns = [
        col for col in candidate_feature_columns if col not in feature_columns
    ]
    (META_DIR / "feature_columns.txt").write_text(
        "\n".join(feature_columns) + "\n", encoding="utf-8"
    )
    (META_DIR / "dropped_all_missing_columns.txt").write_text(
        "\n".join(dropped_columns) + ("\n" if dropped_columns else ""),
        encoding="utf-8",
    )

    processed_frames = {}
    processed_labels = {}
    summary_rows = []

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
        intervals = timestamps.diff().dt.total_seconds().dropna()
        summary_rows.append({
            "file": name,
            "processed_data": f"data/{stem}.csv",
            "processed_label": f"label/{stem}.csv",
            "rows": len(features),
            "columns": features.shape[1],
            "start_time": timestamps.min(),
            "end_time": timestamps.max(),
            "duration_minutes": (timestamps.max() - timestamps.min()).total_seconds() / 60,
            "median_interval_seconds": intervals.median() if len(intervals) else "",
            "positive_labels": int(label.sum()),
            "missing_values_before_fill": missing_values,
            "duplicate_timestamps": duplicate_timestamps,
            "fault_type": fault_type,
            "target_service": target_service,
        })

    test_order = [
        "normal_valid",
        "fault_cpu_frontend",
        "fault_delay_cart",
        "fault_kill_product",
    ]
    combined_data = pd.concat([processed_frames[name] for name in test_order], ignore_index=True)
    combined_label = pd.concat([processed_labels[name] for name in test_order], ignore_index=True)
    combined_data.to_csv(DATA_DIR / "test_all.csv", index=False, header=False)
    combined_label.to_csv(LABEL_DIR / "test_all.csv", index=False, header=False)

    summary_rows.append({
        "file": "test_all.csv",
        "processed_data": "data/test_all.csv",
        "processed_label": "label/test_all.csv",
        "rows": len(combined_data),
        "columns": combined_data.shape[1],
        "start_time": "",
        "end_time": "",
        "duration_minutes": "",
        "median_interval_seconds": "",
        "positive_labels": int(combined_label.sum()),
        "missing_values_before_fill": 0,
        "duplicate_timestamps": 0,
        "fault_type": "mixed",
        "target_service": "frontend/cartservice/productcatalogservice",
    })

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(META_DIR / "summary.csv", index=False)

    for window in [5, 10, 15]:
        write_detector_config("test_all", len(combined_data), combined_data.shape[1], window)

    readme = """# ll_data_new processed dataset

Generated by `../process_ll_data_new.py`.

- Sampling interval: 30 seconds.
- Raw feature columns: 44 metrics plus `timestamp`.
- Model feature columns: 22 metrics. The 22 all-missing `*_net_rx` and
  `*_net_tx` columns are dropped before writing `data/*.csv`.
- Labels are generated from `*_fault_run.json`.
- `data/test_all.csv` combines `normal_valid.csv` and the three fault CSV files.
- Candidate windows:
  - `w5`: 5 points, about 2.5 minutes.
  - `w10`: 10 points, about 5 minutes.
  - `w15`: 15 points, about 7.5 minutes.

Because each fault file is only 19 points long and each fault window is about
5 minutes, `w10` is the main candidate and `w5` is a short-window comparison.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print(summary.to_string(index=False))
    print(f"\nWrote processed dataset to: {OUT_DIR}")


if __name__ == "__main__":
    main()
