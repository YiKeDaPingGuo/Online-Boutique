from pathlib import Path

import pandas as pd


MYDATA_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = MYDATA_DIR / "processed" / "full_log_based"
OUT_DIR = MYDATA_DIR / "processed" / "no_delay_legacy"
DATA_DIR = OUT_DIR / "data"
LABEL_DIR = OUT_DIR / "label"
CONFIG_DIR = OUT_DIR / "configs"
META_DIR = OUT_DIR / "metadata"
RESULT_DIR = OUT_DIR / "result"

PARTS = [
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
    window=40,
    stride=40,
    sample_rate=0.6,
    data_name=None,
):
    if data_name is None:
        data_name = name
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
  path: '../mydata/processed/no_delay_legacy/data/{data_name}.csv'
  label_path: '../mydata/processed/no_delay_legacy/label/{data_name}.csv'
  save_path: '../mydata/processed/no_delay_legacy/result/{name}'
  row_begin: 0
  row_end: {rows}
  col_begin: 0
  col_end: {columns}
  rec_windows_per_cycle: 3
  header: null
  reconstruct:
    window: {window}
    stride: {stride}
  detect:
    window: 20
    stride: 5
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


def main():
    ensure_dirs()

    data_frames = []
    label_frames = []
    summary = []
    for part in PARTS:
        data = pd.read_csv(SRC_DIR / "data" / f"{part}.csv", header=None)
        label = pd.read_csv(SRC_DIR / "label" / f"{part}.csv", header=None)
        data_frames.append(data)
        label_frames.append(label)
        summary.append({
            "part": part,
            "rows": len(data),
            "columns": data.shape[1],
            "positive_labels": int(label.iloc[:, 0].sum()),
        })

    combined_data = pd.concat(data_frames, ignore_index=True)
    combined_label = pd.concat(label_frames, ignore_index=True)
    combined_data.to_csv(DATA_DIR / "test_no_delay.csv", index=False, header=False)
    combined_label.to_csv(LABEL_DIR / "test_no_delay.csv", index=False, header=False)

    write_config(
        "test_no_delay",
        rows=len(combined_data),
        columns=combined_data.shape[1],
        window=40,
        stride=40,
        sample_rate=0.6,
    )
    write_config(
        "test_no_delay_sr09",
        rows=len(combined_data),
        columns=combined_data.shape[1],
        window=40,
        stride=40,
        sample_rate=0.9,
        data_name="test_no_delay",
    )

    summary.append({
        "part": "test_no_delay",
        "rows": len(combined_data),
        "columns": combined_data.shape[1],
        "positive_labels": int(combined_label.iloc[:, 0].sum()),
    })
    pd.DataFrame(summary).to_csv(META_DIR / "summary.csv", index=False)

    readme = """# no_delay_legacy

This dataset removes `fault_delay_cart_repeat_500ms.csv` from the combined test set.

Included parts:

- normal_valid
- fault_cpu_frontend
- fault_mem_recommendation
- fault_kill_product_repeat

Run from `detector/`:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\\mydata\\processed\\no_delay_legacy\\configs\\test_no_delay.yml
```

There is also a higher sample-rate config:

```powershell
conda run -n jumpstarter python run_detector.py -c ..\\mydata\\processed\\no_delay_legacy\\configs\\test_no_delay_sr09.yml
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print("Created:", OUT_DIR)
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
