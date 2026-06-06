#!/usr/bin/env python3
"""Lightweight GDN reproduction for Online Boutique metrics.

This script keeps the paper's core workflow:
1. learn sensor/metric embeddings;
2. build a TopK dependency graph from embedding cosine similarity;
3. use attention over graph neighbors to forecast the next time step;
4. score anomalies with robust-normalized forecasting errors.

It avoids torch-geometric so the experiment can run reliably on Windows.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


DROP_COLUMNS = {"timestamp", "index", "attack"}


def load_metrics(path: Path, has_label: bool = False, feature_cols: list[str] | None = None):
    df = pd.read_csv(path)
    if feature_cols is None:
        feature_cols = [c for c in df.columns if c not in DROP_COLUMNS]
    else:
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            raise ValueError(f"{path} is missing expected feature columns: {missing[:5]}")
    x = df[feature_cols].replace("", 0).fillna(0).astype("float32").to_numpy()
    labels = df["attack"].astype(int).to_numpy() if has_label and "attack" in df.columns else None
    timestamps = df["timestamp"].tolist() if "timestamp" in df.columns else list(range(len(df)))
    return x, labels, timestamps, feature_cols


def build_windows(values: np.ndarray, window: int, labels: np.ndarray | None = None):
    xs, ys, label_out = [], [], []
    for idx in range(window, len(values)):
        xs.append(values[idx - window : idx].T)
        ys.append(values[idx])
        if labels is not None:
            label_out.append(labels[idx])
    x_tensor = torch.tensor(np.stack(xs), dtype=torch.float32)
    y_tensor = torch.tensor(np.stack(ys), dtype=torch.float32)
    if labels is None:
        return x_tensor, y_tensor, None
    return x_tensor, y_tensor, np.array(label_out, dtype=int)


class LightweightGDN(nn.Module):
    def __init__(self, feature_count: int, window: int, dim: int, topk: int):
        super().__init__()
        self.feature_count = feature_count
        self.topk = min(topk, feature_count - 1)
        self.embedding = nn.Parameter(torch.randn(feature_count, dim) * 0.02)
        self.window_proj = nn.Linear(window, dim)
        self.attention = nn.Sequential(
            nn.Linear(dim * 4, dim),
            nn.LeakyReLU(0.2),
            nn.Linear(dim, 1),
        )
        self.output = nn.Sequential(
            nn.Linear(dim, dim),
            nn.ReLU(),
            nn.Linear(dim, 1),
        )

    def learned_topk(self):
        emb = nn.functional.normalize(self.embedding, dim=1)
        sim = emb @ emb.T
        sim.fill_diagonal_(-1e9)
        return torch.topk(sim, self.topk, dim=0).indices.T

    def forward(self, x):
        # x: [batch, feature, window]
        h = torch.relu(self.window_proj(x))
        idx = self.learned_topk()

        all_outputs = []
        for target in range(self.feature_count):
            neighbors = idx[target]
            node_ids = torch.cat(
                [torch.tensor([target], device=x.device), neighbors.to(x.device)]
            )

            target_h = h[:, target : target + 1, :]
            neighbor_h = h[:, node_ids, :]
            target_h_rep = target_h.repeat(1, neighbor_h.shape[1], 1)

            target_emb = self.embedding[target].view(1, 1, -1).repeat(x.shape[0], neighbor_h.shape[1], 1)
            neighbor_emb = self.embedding[node_ids].view(1, neighbor_h.shape[1], -1).repeat(x.shape[0], 1, 1)

            att_in = torch.cat([target_h_rep, neighbor_h, target_emb, neighbor_emb], dim=-1)
            weights = torch.softmax(self.attention(att_in), dim=1)
            agg = torch.sum(weights * neighbor_h, dim=1)

            # 节点嵌入用于保留不同指标的个性化行为。
            z = agg * self.embedding[target]
            all_outputs.append(self.output(z).squeeze(-1))

        return torch.stack(all_outputs, dim=1)


def minmax_fit_transform(train, *others):
    min_v = train.min(axis=0)
    max_v = train.max(axis=0)
    scale = np.where(max_v - min_v == 0, 1.0, max_v - min_v)
    out = [(train - min_v) / scale]
    out.extend((x - min_v) / scale for x in others)
    return out


def robust_scores(errors: np.ndarray, reference_errors: np.ndarray):
    median = np.median(reference_errors, axis=0)
    q75 = np.percentile(reference_errors, 75, axis=0)
    q25 = np.percentile(reference_errors, 25, axis=0)
    iqr = np.where(q75 - q25 == 0, 1e-6, q75 - q25)
    per_feature = (errors - median) / iqr
    return per_feature, per_feature.max(axis=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--topk", type=int, default=15)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    exp_dir = Path(args.experiment_dir)
    data_dir = exp_dir / "data"
    gdn_dir = exp_dir.parent / "gdn-reproduce" / "data" / "onlineboutique"
    result_dir = exp_dir / "results"
    result_dir.mkdir(parents=True, exist_ok=True)

    list_path = gdn_dir / "list.txt"
    if list_path.exists():
        feature_cols = [line.strip() for line in list_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        feature_cols = None

    train_raw, _, _, feature_cols = load_metrics(
        data_dir / "normal_train.csv", feature_cols=feature_cols
    )
    valid_raw, _, _, _ = load_metrics(data_dir / "normal_valid.csv", feature_cols=feature_cols)
    test_raw, test_labels, timestamps, _ = load_metrics(
        gdn_dir / "test.csv",
        has_label=True,
        feature_cols=feature_cols,
    )

    train, valid, test = minmax_fit_transform(train_raw, valid_raw, test_raw)
    x_train, y_train, _ = build_windows(train, args.window)
    x_valid, y_valid, _ = build_windows(valid, args.window)
    x_test, y_test, labels = build_windows(test, args.window, test_labels)
    test_times = timestamps[args.window :]

    torch.manual_seed(5)
    model = LightweightGDN(len(feature_cols), args.window, args.dim, args.topk)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()
    loader = DataLoader(TensorDataset(x_train, y_train), batch_size=args.batch, shuffle=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        losses = []
        for xb, yb in loader:
            pred = model(xb)
            loss = loss_fn(pred, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        if epoch == 1 or epoch % 20 == 0 or epoch == args.epochs:
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

    result_path = result_dir / "gdn_lightweight_scores.csv"
    with result_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "score", "threshold", "prediction", "attack"])
        for ts, score, pred, label in zip(test_times, anomaly_scores, pred_labels, labels):
            writer.writerow([ts, float(score), threshold, int(pred), int(label)])

    mean_feature_score = feature_scores.mean(axis=0)
    top_indices = np.argsort(mean_feature_score)[::-1][:10]
    top_path = result_dir / "gdn_lightweight_top_features.csv"
    with top_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "feature", "mean_score"])
        for rank, idx in enumerate(top_indices, start=1):
            writer.writerow([rank, feature_cols[idx], float(mean_feature_score[idx])])

    print("\n================ GDN Reproduction Result ================")
    print(f"threshold: {threshold:.6f}")
    print(f"precision: {precision:.4f}")
    print(f"recall:    {recall:.4f}")
    print(f"f1:        {f1:.4f}")
    print(f"scores:    {result_path}")
    print(f"features:  {top_path}")


if __name__ == "__main__":
    main()
