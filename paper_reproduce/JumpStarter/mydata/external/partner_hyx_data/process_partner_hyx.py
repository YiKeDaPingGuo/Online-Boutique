from pathlib import Path
import pickle

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "processed"
DATA_DIR = OUT_DIR / "data"
LABEL_DIR = OUT_DIR / "label"
CONFIG_DIR = OUT_DIR / "configs"
META_DIR = OUT_DIR / "metadata"
RESULT_DIR = OUT_DIR / "result"


def ensure_dirs():
    for path in [DATA_DIR, LABEL_DIR, CONFIG_DIR, META_DIR, RESULT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_pickle(name):
    with (BASE_DIR / name).open("rb") as fh:
        return pickle.load(fh)


def write_config(name, rows, columns, window):
    stride = max(1, window // 2)
    det_window = max(2, window // 2)
    det_stride = 1
    ma_window = max(2, window // 2)
    windows_per_cycle = 3
    latest_windows = max(10, window * 2)

    config = f"""sample_score_method:
  lesinn:
    phi: 10
    t: 5
  moving_average:
    window: {ma_window}
    stride: 1
anomaly_scoring:
  anomaly_score_example:
    percentage: 90
    topn: 2
global:
  random_state: 42
data:
  path: '../mydata/external/partner_hyx_data/processed/data/{name}.csv'
  label_path: '../mydata/external/partner_hyx_data/processed/label/{name}.csv'
  save_path: '../mydata/external/partner_hyx_data/processed/result/{name}_w{window}'
  row_begin: 0
  row_end: {rows}
  col_begin: 0
  col_end: {columns}
  rec_windows_per_cycle: {windows_per_cycle}
  header: null
  reconstruct:
    window: {window}
    stride: {stride}
  detect:
    window: {det_window}
    stride: {det_stride}
detector_arguments:
  workers: 1
  anomaly_scoring: 'anomaly_score_example'
  sample_score_method: 'moving_average_score'
  cluster_threshold: 0.01
  sample_rate: 0.6
  latest_windows: {latest_windows}
  scale: 5
  rho: 0.1
  sigma: 0.5
  retry_limit: 20
  without_grouping: one_by_one
  without_localize_sampling: true
"""
    (CONFIG_DIR / f"{name}_w{window}.yml").write_text(config, encoding="utf-8")


def segment_summary(labels):
    changes = np.where(labels[1:] != labels[:-1])[0] + 1
    starts = np.r_[0, changes]
    ends = np.r_[changes, len(labels)]
    rows = []
    for start, end in zip(starts, ends):
        rows.append({
            "label": int(labels[start]),
            "start": int(start),
            "end_exclusive": int(end),
            "length": int(end - start),
        })
    return pd.DataFrame(rows)


def main():
    ensure_dirs()

    train = np.asarray(load_pickle("boutique_train.pkl"), dtype=np.float64)
    test = np.asarray(load_pickle("boutique_test.pkl"), dtype=np.float64)
    test_label = np.asarray(load_pickle("boutique_test_label.pkl"), dtype=int).reshape(-1)

    if train.ndim != 2 or test.ndim != 2:
        raise ValueError("train/test must be 2D arrays")
    if train.shape[1] != test.shape[1]:
        raise ValueError("train/test dimension mismatch")
    if len(test_label) != test.shape[0]:
        raise ValueError("test label length mismatch")

    train_label = np.zeros(train.shape[0], dtype=int)
    train_plus_test = np.vstack([train, test])
    train_plus_test_label = np.concatenate([train_label, test_label])

    all_data = np.vstack([train, test])
    active_columns = np.where(np.nanstd(all_data, axis=0) > 0)[0]
    std_order = np.argsort(np.nanstd(all_data[:, active_columns], axis=0))[::-1]
    top30_columns = active_columns[std_order[:min(30, len(active_columns))]]
    (META_DIR / "active_columns.txt").write_text(
        "\n".join(str(int(i)) for i in active_columns) + "\n",
        encoding="utf-8",
    )
    (META_DIR / "top30_columns.txt").write_text(
        "\n".join(str(int(i)) for i in top30_columns) + "\n",
        encoding="utf-8",
    )
    (META_DIR / "dropped_constant_columns.txt").write_text(
        "\n".join(str(i) for i in range(train.shape[1]) if i not in set(active_columns)) + "\n",
        encoding="utf-8",
    )

    datasets = {
        "test_only_full": (test, test_label),
        "train_plus_test_full": (train_plus_test, train_plus_test_label),
        "test_only_active": (test[:, active_columns], test_label),
        "train_plus_test_active": (train_plus_test[:, active_columns], train_plus_test_label),
        "test_only_top30": (test[:, top30_columns], test_label),
        "train_plus_test_top30": (train_plus_test[:, top30_columns], train_plus_test_label),
    }

    summary_rows = []
    for name, (data, label) in datasets.items():
        pd.DataFrame(data).to_csv(DATA_DIR / f"{name}.csv", index=False, header=False)
        pd.Series(label).to_csv(LABEL_DIR / f"{name}.csv", index=False, header=False)
        for window in [5, 10, 20]:
            write_config(name, data.shape[0], data.shape[1], window)
        summary_rows.append({
            "dataset": name,
            "rows": data.shape[0],
            "columns": data.shape[1],
            "positive_labels": int(label.sum()),
            "negative_labels": int((label == 0).sum()),
        })

    seg = segment_summary(test_label)
    seg.to_csv(META_DIR / "test_label_segments.csv", index=False)
    anomaly_lengths = seg.loc[seg["label"] == 1, "length"]
    normal_lengths = seg.loc[seg["label"] == 0, "length"]

    stats = {
        "train_rows": train.shape[0],
        "test_rows": test.shape[0],
        "full_columns": train.shape[1],
        "active_columns": len(active_columns),
        "top30_columns": len(top30_columns),
        "test_positive_labels": int(test_label.sum()),
        "test_negative_labels": int((test_label == 0).sum()),
        "segment_count": len(seg),
        "anomaly_segment_count": int((seg["label"] == 1).sum()),
        "anomaly_segment_min": int(anomaly_lengths.min()),
        "anomaly_segment_median": float(anomaly_lengths.median()),
        "anomaly_segment_max": int(anomaly_lengths.max()),
        "normal_segment_median": float(normal_lengths.median()),
    }
    pd.DataFrame([stats]).to_csv(META_DIR / "summary_stats.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(META_DIR / "datasets.csv", index=False)

    readme = """# partner_hyx_data processed

This directory converts the partner HYX pickle data into JumpStarter CSV inputs.

Generated datasets:

- `test_only_full`: original 156 dimensions, test only.
- `train_plus_test_full`: normal train prepended to test, 156 dimensions.
- `test_only_active`: constant dimensions dropped, test only.
- `train_plus_test_active`: constant dimensions dropped, normal train prepended to test.

Window configs are generated for `w5`, `w10`, and `w20`.

Recommended first trial:

```powershell
cd detector
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\\mydata\\external\\partner_hyx_data\\processed\\configs\\train_plus_test_active_w10.yml
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print("Processed partner_hyx_data into:", OUT_DIR)
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(pd.DataFrame([stats]).to_string(index=False))


if __name__ == "__main__":
    main()
