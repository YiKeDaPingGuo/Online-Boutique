from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "processed"
DATA_DIR = OUT_DIR / "data"
LABEL_DIR = OUT_DIR / "label"
META_DIR = OUT_DIR / "metadata"
CONFIG_DIR = OUT_DIR / "configs"

CSV_FILES = [
    "normal_train.csv",
    "normal_valid.csv",
    "fault_cpu_frontend.csv",
    "fault_delay_cart.csv",
    "fault_kill_product.csv",
]

FAULT_WINDOWS = {
    "fault_cpu_frontend.csv": (
        "2026-06-05 13:16:00",
        "2026-06-05 13:23:00",
        "cpu_stress",
        "frontend",
    ),
    "fault_delay_cart.csv": (
        "2026-06-05 13:33:00",
        "2026-06-05 13:39:00",
        "network_delay",
        "cartservice",
    ),
    "fault_kill_product.csv": (
        "2026-06-05 13:49:00",
        "2026-06-05 13:56:00",
        "pod_kill",
        "productcatalogservice",
    ),
}


def ensure_dirs():
    for path in [DATA_DIR, LABEL_DIR, META_DIR, CONFIG_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_raw_csv(name):
    path = BASE_DIR / name
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def make_label(name, timestamps):
    label = pd.Series(0, index=timestamps.index, dtype=int)
    if name in FAULT_WINDOWS:
        start, end, _, _ = FAULT_WINDOWS[name]
        start = pd.Timestamp(start)
        end = pd.Timestamp(end)
        label.loc[(timestamps >= start) & (timestamps <= end)] = 1
    return label


def write_detector_config(file_stem, row_count, col_count):
    window = 5
    windows_per_cycle = 3
    config = f"""sample_score_method:
  lesinn:
    phi: 10
    t: 5
  moving_average:
    window: 5
    stride: 1
anomaly_scoring:
  anomaly_score_example:
    percentage: 90
    topn: 2
global:
  random_state: 42
data:
  path: '../mydata/external/ll_data/processed/data/{file_stem}.csv'
  label_path: '../mydata/external/ll_data/processed/label/{file_stem}.csv'
  save_path: '../mydata/external/ll_data/processed/result/{file_stem}'
  row_begin: 0
  row_end: {row_count}
  col_begin: 0
  col_end: {col_count}
  rec_windows_per_cycle: {windows_per_cycle}
  header: null
  reconstruct:
    window: {window}
    stride: 5
  detect:
    window: 5
    stride: 1
detector_arguments:
  workers: 1
  anomaly_scoring: 'anomaly_score_example'
  sample_score_method: 'moving_average_score'
  cluster_threshold: 0.01
  sample_rate: 0.6
  latest_windows: 5
  scale: 5
  rho: 0.1
  sigma: 0.5
  retry_limit: 10
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

    numeric_all = pd.concat(
        [df.drop(columns=["timestamp"]) for df in raw.values()],
        ignore_index=True,
    ).apply(pd.to_numeric, errors="coerce")

    kept_columns = [
        col for col in numeric_all.columns
        if not numeric_all[col].isna().all()
    ]
    dropped_columns = [
        col for col in numeric_all.columns
        if numeric_all[col].isna().all()
    ]

    (META_DIR / "kept_columns.txt").write_text(
        "\n".join(kept_columns) + "\n", encoding="utf-8"
    )
    (META_DIR / "dropped_all_empty_columns.txt").write_text(
        "\n".join(dropped_columns) + "\n", encoding="utf-8"
    )

    summary_rows = []
    processed_frames = {}
    processed_labels = {}

    for name, df in raw.items():
        timestamps = df["timestamp"]
        features = df[kept_columns].apply(pd.to_numeric, errors="coerce")
        features = features.interpolate(limit_direction="both").fillna(0.0)
        label = make_label(name, timestamps)

        stem = Path(name).stem
        features.to_csv(DATA_DIR / f"{stem}.csv", index=False, header=False)
        label.to_csv(LABEL_DIR / f"{stem}.csv", index=False, header=False)

        processed_frames[stem] = features
        processed_labels[stem] = label

        fault_type = "normal"
        target_service = ""
        if name in FAULT_WINDOWS:
            _, _, fault_type, target_service = FAULT_WINDOWS[name]

        summary_rows.append({
            "file": name,
            "processed_data": f"data/{stem}.csv",
            "processed_label": f"label/{stem}.csv",
            "rows": len(features),
            "columns": features.shape[1],
            "start_time": timestamps.min(),
            "end_time": timestamps.max(),
            "positive_labels": int(label.sum()),
            "fault_type": fault_type,
            "target_service": target_service,
        })
        write_detector_config(stem, len(features), features.shape[1])

    test_order = [
        "normal_valid",
        "fault_cpu_frontend",
        "fault_delay_cart",
        "fault_kill_product",
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
        "fault_type": "mixed",
        "target_service": "frontend/cartservice/productcatalogservice",
    })

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(META_DIR / "summary.csv", index=False)

    result_dir = OUT_DIR / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    print("Processed ll_data into:", OUT_DIR)
    print(summary.to_string(index=False))
    print()
    print("Kept columns:", len(kept_columns))
    print("Dropped all-empty columns:", len(dropped_columns))


if __name__ == "__main__":
    main()
