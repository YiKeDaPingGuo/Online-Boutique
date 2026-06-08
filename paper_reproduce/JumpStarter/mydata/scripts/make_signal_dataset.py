from pathlib import Path

import pandas as pd


MYDATA_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = MYDATA_DIR / "processed" / "full_log_based"
OUT_DIR = MYDATA_DIR / "processed" / "signal_log_based"
DATA_DIR = OUT_DIR / "data"
LABEL_DIR = OUT_DIR / "label"
CONFIG_DIR = OUT_DIR / "configs"
META_DIR = OUT_DIR / "metadata"
RESULT_DIR = OUT_DIR / "result"

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


def ensure_dirs():
    for path in [DATA_DIR, LABEL_DIR, CONFIG_DIR, META_DIR, RESULT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def write_config(
    name,
    rows,
    columns,
    data_name=None,
    sample_rate=0.5,
    rec_window=20,
    rec_stride=20,
    det_window=10,
    det_stride=2,
    moving_average_window=10,
    moving_average_stride=2,
    latest_windows=20,
):
    if data_name is None:
        data_name = name
    config = f"""sample_score_method:
  lesinn:
    phi: 10
    t: 5
  moving_average:
    window: {moving_average_window}
    stride: {moving_average_stride}
anomaly_scoring:
  anomaly_score_example:
    percentage: 90
    topn: 2
global:
  random_state: 42
data:
  path: '../mydata/processed/signal_log_based/data/{data_name}.csv'
  label_path: '../mydata/processed/signal_log_based/label/{data_name}.csv'
  save_path: '../mydata/processed/signal_log_based/result/{name}'
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
  latest_windows: {latest_windows}
  scale: 5
  rho: 0.1
  sigma: 0.5
  retry_limit: 20
  without_grouping: one_by_one
  without_localize_sampling: true
"""
    (CONFIG_DIR / f"{name}.yml").write_text(config, encoding="utf-8")


def build_dataset(name, parts, selected_indices):
    data_frames = []
    label_frames = []
    rows = []

    for part in parts:
        data = pd.read_csv(SRC_DIR / "data" / f"{part}.csv", header=None)
        label = pd.read_csv(SRC_DIR / "label" / f"{part}.csv", header=None)
        data = data.iloc[:, selected_indices]
        data_frames.append(data)
        label_frames.append(label)
        rows.append({
            "dataset": name,
            "part": part,
            "rows": len(data),
            "columns": data.shape[1],
            "positive_labels": int(label.iloc[:, 0].sum()),
        })

    combined_data = pd.concat(data_frames, ignore_index=True)
    combined_label = pd.concat(label_frames, ignore_index=True)
    combined_data.to_csv(DATA_DIR / f"{name}.csv", index=False, header=False)
    combined_label.to_csv(LABEL_DIR / f"{name}.csv", index=False, header=False)
    write_config(name, len(combined_data), combined_data.shape[1])
    write_config(
        f"{name}_w10",
        len(combined_data),
        combined_data.shape[1],
        data_name=name,
        sample_rate=0.5,
        rec_window=10,
        rec_stride=10,
        det_window=5,
        det_stride=1,
        moving_average_window=5,
        moving_average_stride=1,
        latest_windows=20,
    )

    rows.append({
        "dataset": name,
        "part": name,
        "rows": len(combined_data),
        "columns": combined_data.shape[1],
        "positive_labels": int(combined_label.iloc[:, 0].sum()),
    })
    return rows


def main():
    ensure_dirs()

    feature_columns = (SRC_DIR / "metadata" / "feature_columns.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    selected_columns = [
        col for col in feature_columns
        if not col.endswith("_latency")
    ]
    selected_indices = [
        feature_columns.index(col)
        for col in selected_columns
    ]

    (META_DIR / "selected_columns.txt").write_text(
        "\n".join(selected_columns) + "\n",
        encoding="utf-8",
    )
    (META_DIR / "dropped_columns.txt").write_text(
        "\n".join([col for col in feature_columns if col not in selected_columns]) + "\n",
        encoding="utf-8",
    )

    summary_rows = []
    summary_rows.extend(build_dataset("test_all_signal", FULL_PARTS, selected_indices))
    summary_rows.extend(build_dataset("test_no_delay_signal", NO_DELAY_PARTS, selected_indices))
    for fault_part in FULL_PARTS[1:]:
        dataset_name = "test_" + fault_part.replace("fault_", "") + "_signal"
        summary_rows.extend(
            build_dataset(dataset_name, ["normal_valid", fault_part], selected_indices)
        )
    pd.DataFrame(summary_rows).to_csv(META_DIR / "summary.csv", index=False)

    readme = """# signal_log_based

This tuning dataset drops all `_latency` columns and keeps:

- cpu
- mem
- request_rate
- error_rate

It creates two combined test sets:

- `test_all_signal`: includes all faults.
- `test_no_delay_signal`: excludes `fault_delay_cart_repeat_500ms`.

Run from `detector/`:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\\mydata\\processed\\signal_log_based\\configs\\test_all_signal.yml
conda run -n jumpstarter python run_detector.py -c ..\\mydata\\processed\\signal_log_based\\configs\\test_no_delay_signal.yml
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print("Created:", OUT_DIR)
    print(pd.DataFrame(summary_rows).to_string(index=False))


if __name__ == "__main__":
    main()
