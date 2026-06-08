from pathlib import Path

import pandas as pd


MYDATA_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = MYDATA_DIR / "raw_self"
OUT_DIR = MYDATA_DIR / "processed" / "signal_observed"
DATA_DIR = OUT_DIR / "data"
LABEL_DIR = OUT_DIR / "label"
CONFIG_DIR = OUT_DIR / "configs"
META_DIR = OUT_DIR / "metadata"
RESULT_DIR = OUT_DIR / "result"

RAW_FILES = [
    "normal_valid.csv",
    "fault_cpu_frontend.csv",
    "fault_mem_recommendation.csv",
    "fault_delay_cart_repeat_500ms.csv",
    "fault_kill_product_repeat.csv",
]

FULL_PARTS = [
    "normal_valid",
    "fault_cpu_frontend",
    "fault_mem_recommendation",
    "fault_delay_cart_repeat_500ms",
    "fault_kill_product_repeat",
]

NO_DELAY_PARTS = [
    "normal_valid",
    "fault_cpu_frontend",
    "fault_mem_recommendation",
    "fault_kill_product_repeat",
]

# Observed-impact labels: windows are based on visible metric changes in CSVs,
# not only on Chaos Mesh injection intervals.
OBSERVED_WINDOWS = {
    "fault_cpu_frontend.csv": [
        ("2026-06-07 14:33:53", "2026-06-07 14:44:53"),
    ],
    "fault_mem_recommendation.csv": [
        ("2026-06-07 15:38:49", "2026-06-07 15:48:19"),
    ],
    "fault_delay_cart_repeat_500ms.csv": [
        ("2026-06-07 19:30:09", "2026-06-07 19:33:39"),
        ("2026-06-07 19:37:09", "2026-06-07 19:42:10"),
        ("2026-06-07 19:45:40", "2026-06-07 19:56:10"),
    ],
    "fault_kill_product_repeat.csv": [
        ("2026-06-07 20:42:55", "2026-06-07 20:45:25"),
        ("2026-06-07 20:48:25", "2026-06-07 20:49:55"),
        ("2026-06-07 20:53:55", "2026-06-07 20:55:25"),
    ],
}


def ensure_dirs():
    for path in [DATA_DIR, LABEL_DIR, CONFIG_DIR, META_DIR, RESULT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_raw_csv(name):
    df = pd.read_csv(RAW_DIR / name)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def make_label(name, timestamps):
    label = pd.Series(0, index=timestamps.index, dtype=int)
    for start, end in OBSERVED_WINDOWS.get(name, []):
        start = pd.Timestamp(start)
        end = pd.Timestamp(end)
        label.loc[(timestamps >= start) & (timestamps <= end)] = 1
    return label


def write_config(
    name,
    rows,
    columns,
    data_name=None,
    sample_rate=0.5,
    rec_window=10,
    rec_stride=10,
    det_window=5,
    det_stride=1,
):
    data_name = data_name or name
    config = f"""sample_score_method:
  lesinn:
    phi: 10
    t: 5
  moving_average:
    window: {det_window}
    stride: 1
anomaly_scoring:
  anomaly_score_example:
    percentage: 90
    topn: 2
global:
  random_state: 42
data:
  path: '../mydata/processed/signal_observed/data/{data_name}.csv'
  label_path: '../mydata/processed/signal_observed/label/{data_name}.csv'
  save_path: '../mydata/processed/signal_observed/result/{name}'
  row_begin: 0
  row_end: {rows}
  col_begin: 0
  col_end: {columns}
  rec_windows_per_cycle: 3
  header: null
  reconstruct:
    window: {rec_window}
    stride: {rec_stride}
  detect:
    window: {det_window}
    stride: {det_stride}
detector_arguments:
  workers: 1
  anomaly_scoring: 'anomaly_score_example'
  sample_score_method: 'moving_average_score'
  cluster_threshold: 0.01
  sample_rate: {sample_rate}
  latest_windows: 20
  scale: 5
  rho: 0.1
  sigma: 0.5
  retry_limit: 20
  without_grouping: one_by_one
  without_localize_sampling: true
"""
    (CONFIG_DIR / f"{name}.yml").write_text(config, encoding="utf-8")


def write_segments(stem, df, label):
    rows = []
    positive_indices = list(label[label == 1].index)
    if not positive_indices:
        return rows

    start = previous = positive_indices[0]
    for index in positive_indices[1:]:
        if index == previous + 1:
            previous = index
            continue
        rows.append({
            "file": f"{stem}.csv",
            "start_row": start,
            "end_row": previous,
            "count": previous - start + 1,
            "start_time": df.loc[start, "timestamp"],
            "end_time": df.loc[previous, "timestamp"],
        })
        start = previous = index

    rows.append({
        "file": f"{stem}.csv",
        "start_row": start,
        "end_row": previous,
        "count": previous - start + 1,
        "start_time": df.loc[start, "timestamp"],
        "end_time": df.loc[previous, "timestamp"],
    })
    return rows


def build_dataset(name, parts, processed_frames, processed_labels):
    data_frames = [processed_frames[part] for part in parts]
    label_frames = [processed_labels[part] for part in parts]
    data = pd.concat(data_frames, ignore_index=True)
    label = pd.concat(label_frames, ignore_index=True)

    data.to_csv(DATA_DIR / f"{name}.csv", index=False, header=False)
    label.to_csv(LABEL_DIR / f"{name}.csv", index=False, header=False)
    write_config(f"{name}_w10", len(data), data.shape[1], data_name=name)

    return {
        "dataset": name,
        "parts": "+".join(parts),
        "rows": len(data),
        "columns": data.shape[1],
        "positive_labels": int(label.sum()),
    }


def main():
    ensure_dirs()

    raw = {name: read_raw_csv(name) for name in RAW_FILES}
    reference_columns = list(raw[RAW_FILES[0]].columns)
    for name, df in raw.items():
        if list(df.columns) != reference_columns:
            raise ValueError(f"{name} columns differ from normal_valid.csv")

    feature_columns = [
        column
        for column in reference_columns
        if column != "timestamp" and not column.endswith("_latency")
    ]
    (META_DIR / "feature_columns.txt").write_text(
        "\n".join(feature_columns) + "\n", encoding="utf-8"
    )

    processed_frames = {}
    processed_labels = {}
    summary_rows = []
    segment_rows = []

    for name, df in raw.items():
        stem = Path(name).stem
        features = df[feature_columns].apply(pd.to_numeric, errors="coerce")
        missing_values = int(features.isna().sum().sum())
        features = features.interpolate(limit_direction="both").fillna(0.0)
        label = make_label(name, df["timestamp"])

        features.to_csv(DATA_DIR / f"{stem}.csv", index=False, header=False)
        label.to_csv(LABEL_DIR / f"{stem}.csv", index=False, header=False)

        processed_frames[stem] = features
        processed_labels[stem] = label

        summary_rows.append({
            "dataset": stem,
            "parts": stem,
            "rows": len(features),
            "columns": features.shape[1],
            "positive_labels": int(label.sum()),
            "start_time": df["timestamp"].min(),
            "end_time": df["timestamp"].max(),
            "missing_values_before_fill": missing_values,
        })
        segment_rows.extend(write_segments(stem, df, label))

    summary_rows.append(build_dataset(
        "test_all_signal_observed",
        FULL_PARTS,
        processed_frames,
        processed_labels,
    ))
    summary_rows.append(build_dataset(
        "test_no_delay_signal_observed",
        NO_DELAY_PARTS,
        processed_frames,
        processed_labels,
    ))

    single_fault_sets = {
        "test_cpu_frontend_signal_observed": ["normal_valid", "fault_cpu_frontend"],
        "test_mem_recommendation_signal_observed": ["normal_valid", "fault_mem_recommendation"],
        "test_delay_cart_repeat_500ms_signal_observed": ["normal_valid", "fault_delay_cart_repeat_500ms"],
        "test_kill_product_repeat_signal_observed": ["normal_valid", "fault_kill_product_repeat"],
    }
    for dataset_name, parts in single_fault_sets.items():
        summary_rows.append(build_dataset(dataset_name, parts, processed_frames, processed_labels))

    pd.DataFrame(summary_rows).to_csv(META_DIR / "summary.csv", index=False)
    pd.DataFrame(segment_rows).to_csv(META_DIR / "observed_label_segments.csv", index=False)

    readme = """# signal_observed

This directory contains the observed-impact label version of `mydata`.

Compared with `../signal_log_based`, this version keeps the same 44 input
features (`cpu/mem/request_rate/error_rate`) but regenerates labels from
visible metric changes in the CSV files.

Label meaning:

```text
label=1 means the sampling point is inside an observed service-impact window.
```

Recommended config:

```text
configs/test_all_signal_observed_w10.yml
```

The window is 10 sampling points. With a 30-second interval, this is about
5 minutes.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"\nWrote observed-impact dataset to: {OUT_DIR}")


if __name__ == "__main__":
    main()
