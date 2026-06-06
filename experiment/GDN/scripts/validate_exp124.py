#!/usr/bin/env python3
"""Validate GDN pipeline for experiments 1, 2, and 4 only.

Experiment 1: normal_train.csv
Experiment 2: normal_valid.csv (threshold calibration)
Experiment 4: fault_delay_cart.csv (network delay on cartservice)
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_gdn_reproduction import (  # noqa: E402
    LightweightGDN,
    build_windows,
    load_metrics,
    minmax_fit_transform,
    robust_scores,
)

FAULT_WINDOW = ("2026-06-05 13:33:00", "2026-06-05 13:39:00")


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")


def label_fault_rows(timestamps: list[str]) -> np.ndarray:
    start, end = map(parse_ts, FAULT_WINDOW)
    return np.array([1 if start <= parse_ts(ts) <= end else 0 for ts in timestamps], dtype=int)


def main():
    exp_dir = SCRIPT_DIR.parent
    data_dir = exp_dir / "data"
    result_dir = exp_dir / "results"
    result_dir.mkdir(parents=True, exist_ok=True)

    train_raw, _, _, feature_cols = load_metrics(data_dir / "normal_train.csv")
    valid_raw, _, _, _ = load_metrics(data_dir / "normal_valid.csv")
    test_raw, _, test_times_raw, _ = load_metrics(data_dir / "fault_delay_cart.csv")
    test_labels = label_fault_rows(test_times_raw)

    train, valid, test = minmax_fit_transform(train_raw, valid_raw, test_raw)
    window = 5
    x_train, y_train, _ = build_windows(train, window)
    x_valid, y_valid, _ = build_windows(valid, window)
    x_test, y_test, labels = build_windows(test, window, test_labels)
    test_times = test_times_raw[window:]

    torch.manual_seed(5)
    model = LightweightGDN(len(feature_cols), window, dim=64, topk=15)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    loader = DataLoader(TensorDataset(x_train, y_train), batch_size=32, shuffle=True)

    for epoch in range(1, 121):
        model.train()
        losses = []
        for xb, yb in loader:
            pred = model(xb)
            loss = loss_fn(pred, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        if epoch in (1, 20, 40, 60, 80, 100, 120):
            print(f"epoch={epoch:03d} train_loss={np.mean(losses):.6f}")

    model.eval()
    with torch.no_grad():
        valid_pred = model(x_valid).numpy()
        test_pred = model(x_test).numpy()

    valid_errors = np.abs(y_valid.numpy() - valid_pred)
    test_errors = np.abs(y_test.numpy() - test_pred)
    feature_scores, anomaly_scores = robust_scores(test_errors, valid_errors)
    _, valid_scores = robust_scores(valid_errors, valid_errors)
    threshold = float(valid_scores.max())
    pred_labels = (anomaly_scores > threshold).astype(int)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, pred_labels, average="binary", zero_division=0
    )

    result_path = result_dir / "gdn_exp124_scores.csv"
    with result_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "score", "threshold", "prediction", "attack"])
        for ts, score, pred, label in zip(test_times, anomaly_scores, pred_labels, labels):
            writer.writerow([ts, float(score), threshold, int(pred), int(label)])

    mean_feature_score = feature_scores.mean(axis=0)
    top_indices = np.argsort(mean_feature_score)[::-1][:10]
    top_path = result_dir / "gdn_exp124_top_features.csv"
    with top_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "feature", "mean_score"])
        for rank, idx in enumerate(top_indices, start=1):
            writer.writerow([rank, feature_cols[idx], float(mean_feature_score[idx])])

    attack_total = int(labels.sum())
    attack_detected = int(((labels == 1) & (pred_labels == 1)).sum())
    normal_total = int((labels == 0).sum())
    false_positive = int(((labels == 0) & (pred_labels == 1)).sum())

    print("\n================ Exp 1/2/4 Validation ================")
    print("train: data/normal_train.csv (61 rows)")
    print("valid: data/normal_valid.csv (21 rows)")
    print("test:  data/fault_delay_cart.csv (29 rows)")
    print(f"fault window: {FAULT_WINDOW[0]} -> {FAULT_WINDOW[1]}")
    print(f"features: {len(feature_cols)}")
    print(f"threshold: {threshold:.6f}")
    print(f"precision: {precision:.4f}")
    print(f"recall:    {recall:.4f}")
    print(f"f1:        {f1:.4f}")
    print(f"attack rows: {attack_total}, detected: {attack_detected}")
    print(f"normal rows: {normal_total}, false positive: {false_positive}")
    print(f"scores:   {result_path}")
    print(f"features: {top_path}")


if __name__ == "__main__":
    main()
