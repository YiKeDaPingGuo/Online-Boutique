from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support


CASES = [
    (
        "processed/full_log_based/test_all",
        Path("mydata/processed/full_log_based/result/test_all_score.txt"),
        Path("mydata/processed/full_log_based/label/test_all.csv"),
    ),
    (
        "processed/no_delay_legacy/test_no_delay_sr09",
        Path("mydata/processed/no_delay_legacy/result/test_no_delay_sr09_score.txt"),
        Path("mydata/processed/no_delay_legacy/label/test_no_delay.csv"),
    ),
    (
        "processed/signal_log_based/test_all_signal",
        Path("mydata/processed/signal_log_based/result/test_all_signal_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_all_signal.csv"),
    ),
    (
        "processed/signal_log_based/test_all_signal_w10",
        Path("mydata/processed/signal_log_based/result/test_all_signal_w10_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_all_signal.csv"),
    ),
    (
        "processed/signal_log_based/test_no_delay_signal",
        Path("mydata/processed/signal_log_based/result/test_no_delay_signal_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_no_delay_signal.csv"),
    ),
    (
        "processed/signal_log_based/test_no_delay_signal_w10",
        Path("mydata/processed/signal_log_based/result/test_no_delay_signal_w10_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_no_delay_signal.csv"),
    ),
    (
        "processed/signal_log_based/test_cpu_frontend_signal",
        Path("mydata/processed/signal_log_based/result/test_cpu_frontend_signal_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_cpu_frontend_signal.csv"),
    ),
    (
        "processed/signal_log_based/test_mem_recommendation_signal",
        Path("mydata/processed/signal_log_based/result/test_mem_recommendation_signal_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_mem_recommendation_signal.csv"),
    ),
    (
        "processed/signal_log_based/test_delay_cart_repeat_500ms_signal",
        Path("mydata/processed/signal_log_based/result/test_delay_cart_repeat_500ms_signal_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_delay_cart_repeat_500ms_signal.csv"),
    ),
    (
        "processed/signal_log_based/test_kill_product_repeat_signal",
        Path("mydata/processed/signal_log_based/result/test_kill_product_repeat_signal_score.txt"),
        Path("mydata/processed/signal_log_based/label/test_kill_product_repeat_signal.csv"),
    ),
    (
        "processed/signal_observed/test_all_signal_observed_w10",
        Path("mydata/processed/signal_observed/result/test_all_signal_observed_w10_score.txt"),
        Path("mydata/processed/signal_observed/label/test_all_signal_observed.csv"),
    ),
]


def best_threshold(scores, labels, higher_is_anomaly=True):
    thresholds = np.unique(scores)
    if len(thresholds) > 500:
        thresholds = np.quantile(scores, np.linspace(0, 1, 500))
    rows = []
    for threshold in thresholds:
        if higher_is_anomaly:
            pred = (scores >= threshold).astype(int)
        else:
            pred = (scores <= threshold).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels,
            pred,
            average="binary",
            zero_division=0,
        )
        rows.append((threshold, precision, recall, f1, int(pred.sum())))
    return max(rows, key=lambda row: row[3])


def fixed_topk(scores, labels, k):
    k = min(k, len(scores))
    order = np.argsort(scores)[::-1]
    pred = np.zeros_like(labels)
    pred[order[:k]] = 1
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        pred,
        average="binary",
        zero_division=0,
    )
    return precision, recall, f1, int(pred.sum())


def main():
    results = []
    for name, score_path, label_path in CASES:
        if not score_path.exists():
            continue
        scores = np.loadtxt(score_path)
        labels = np.loadtxt(label_path, dtype=int, delimiter=",")
        labels = labels.reshape(-1)
        high = best_threshold(scores, labels, higher_is_anomaly=True)
        low = best_threshold(scores, labels, higher_is_anomaly=False)
        top_label_count = fixed_topk(scores, labels, int(labels.sum()))
        results.append({
            "case": name,
            "n": len(scores),
            "positive_labels": int(labels.sum()),
            "score_min": float(scores.min()),
            "score_max": float(scores.max()),
            "score_mean": float(scores.mean()),
            "score_std": float(scores.std()),
            "best_high_threshold": high[0],
            "best_high_precision": high[1],
            "best_high_recall": high[2],
            "best_high_f1": high[3],
            "best_high_predicted": high[4],
            "best_low_threshold": low[0],
            "best_low_precision": low[1],
            "best_low_recall": low[2],
            "best_low_f1": low[3],
            "best_low_predicted": low[4],
            "topk_precision": top_label_count[0],
            "topk_recall": top_label_count[1],
            "topk_f1": top_label_count[2],
            "topk_predicted": top_label_count[3],
        })

    out = pd.DataFrame(results)
    out_path = Path("mydata/score_analysis.csv")
    out.to_csv(out_path, index=False)
    print(out.to_string(index=False))
    print("Saved:", out_path)


if __name__ == "__main__":
    main()
