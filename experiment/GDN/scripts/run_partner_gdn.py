#!/usr/bin/env python3
"""Run the lightweight GDN reproduction on partner-provided pickle data."""

from __future__ import annotations

import argparse
import csv
import pickle
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


def load_pickle_array(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        data = pickle.load(f)
    return np.asarray(data)


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
        h = torch.relu(self.window_proj(x))
        idx = self.learned_topk()
        self_idx = torch.arange(self.feature_count, device=x.device).unsqueeze(1)
        node_ids = torch.cat([self_idx, idx.to(x.device)], dim=1)

        neighbor_h = h[:, node_ids, :]
        target_h = h.unsqueeze(2).expand(-1, -1, node_ids.shape[1], -1)
        neighbor_emb = self.embedding[node_ids].unsqueeze(0).expand(x.shape[0], -1, -1, -1)
        target_emb = self.embedding.unsqueeze(0).unsqueeze(2).expand(
            x.shape[0], -1, node_ids.shape[1], -1
        )

        att_in = torch.cat([target_h, neighbor_h, target_emb, neighbor_emb], dim=-1)
        weights = torch.softmax(self.attention(att_in), dim=2)
        agg = torch.sum(weights * neighbor_h, dim=2)
        return self.output(agg * self.embedding.unsqueeze(0)).squeeze(-1)


def split_train_valid(train_raw: np.ndarray, valid_ratio: float):
    if not 0 < valid_ratio < 0.5:
        raise ValueError("--valid-ratio must be between 0 and 0.5")
    split_idx = int(len(train_raw) * (1.0 - valid_ratio))
    if split_idx <= 0 or split_idx >= len(train_raw):
        raise ValueError("Invalid validation split for training data")
    return train_raw[:split_idx], train_raw[split_idx:]


def minmax_fit_transform(train: np.ndarray, *others: np.ndarray):
    min_v = train.min(axis=0)
    max_v = train.max(axis=0)
    scale = np.where(max_v - min_v == 0, 1.0, max_v - min_v)
    out = [(train - min_v) / scale]
    out.extend((x - min_v) / scale for x in others)
    return out


def clip_values(train: np.ndarray, valid: np.ndarray, test: np.ndarray, clip: float | None):
    if clip is None:
        return train, valid, test
    return (
        np.clip(train, -clip, clip),
        np.clip(valid, -clip, clip),
        np.clip(test, -clip, clip),
    )


def robust_scores(errors: np.ndarray, reference_errors: np.ndarray):
    median = np.median(reference_errors, axis=0)
    q75 = np.percentile(reference_errors, 75, axis=0)
    q25 = np.percentile(reference_errors, 25, axis=0)
    iqr = np.where(q75 - q25 == 0, 1e-6, q75 - q25)
    per_feature = (errors - median) / iqr
    return per_feature, per_feature.max(axis=1)


def threshold_from_valid(valid_scores: np.ndarray, strategy: str, multiplier: float):
    if strategy == "max":
        return float(valid_scores.max() * multiplier)
    if strategy == "p99":
        return float(np.percentile(valid_scores, 99) * multiplier)
    if strategy == "mean3std":
        return float((valid_scores.mean() + 3 * valid_scores.std()) * multiplier)
    raise ValueError(f"Unsupported threshold strategy: {strategy}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--partner-dir",
        default=str(Path(__file__).resolve().parents[1] / "partner_data"),
        help="Directory containing boutique_train/test/test_label pkl files",
    )
    parser.add_argument("--valid-ratio", type=float, default=0.2)
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--topk", type=int, default=15)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--clip", type=float, default=None)
    parser.add_argument(
        "--threshold-strategy",
        choices=["max", "p99", "mean3std"],
        default="max",
        help="How to set the anomaly threshold from validation scores",
    )
    parser.add_argument("--threshold-multiplier", type=float, default=1.0)
    args = parser.parse_args()

    partner_dir = Path(args.partner_dir)
    exp_dir = Path(__file__).resolve().parents[1]
    result_dir = exp_dir / "results"
    result_dir.mkdir(parents=True, exist_ok=True)

    train_all = load_pickle_array(partner_dir / "boutique_train.pkl").astype("float32")
    test_raw = load_pickle_array(partner_dir / "boutique_test.pkl").astype("float32")
    test_labels = load_pickle_array(partner_dir / "boutique_test_label.pkl").astype(int)

    if len(test_raw) != len(test_labels):
        raise ValueError("Test data and labels have different lengths")

    train_raw, valid_raw = split_train_valid(train_all, args.valid_ratio)
    train, valid, test = minmax_fit_transform(train_raw, valid_raw, test_raw)
    train, valid, test = clip_values(train, valid, test, args.clip)

    x_train, y_train, _ = build_windows(train, args.window)
    x_valid, y_valid, _ = build_windows(valid, args.window)
    x_test, y_test, labels = build_windows(test, args.window, test_labels)
    test_times = list(range(args.window, len(test_raw)))

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    model = LightweightGDN(train.shape[1], args.window, args.dim, args.topk)
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
    threshold = threshold_from_valid(
        valid_scores, args.threshold_strategy, args.threshold_multiplier
    )
    pred_labels = (anomaly_scores > threshold).astype(int)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, pred_labels, average="binary", zero_division=0
    )
    tp = int(((pred_labels == 1) & (labels == 1)).sum())
    fp = int(((pred_labels == 1) & (labels == 0)).sum())
    fn = int(((pred_labels == 0) & (labels == 1)).sum())
    tn = int(((pred_labels == 0) & (labels == 0)).sum())

    score_path = result_dir / "gdn_partner_scores.csv"
    with score_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "score", "threshold", "prediction", "attack"])
        for ts, score, pred, label in zip(test_times, anomaly_scores, pred_labels, labels):
            writer.writerow([ts, float(score), threshold, int(pred), int(label)])

    feature_path = result_dir / "gdn_partner_top_features.csv"
    mean_feature_score = feature_scores.mean(axis=0)
    top_indices = np.argsort(mean_feature_score)[::-1][:10]
    with feature_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "feature_index", "mean_score"])
        for rank, idx in enumerate(top_indices, start=1):
            writer.writerow([rank, int(idx), float(mean_feature_score[idx])])

    print("\n================ Partner GDN Result ================")
    print(f"train rows: {len(train_raw)}")
    print(f"valid rows: {len(valid_raw)}")
    print(f"test rows:  {len(test_raw)}")
    print(f"features:   {train.shape[1]}")
    print(f"threshold strategy: {args.threshold_strategy}")
    print(f"threshold: {threshold:.6f}")
    print(f"precision: {precision:.4f}")
    print(f"recall:    {recall:.4f}")
    print(f"f1:        {f1:.4f}")
    print(f"tp/fp/fn/tn: {tp}/{fp}/{fn}/{tn}")
    print(f"scores:    {score_path}")
    print(f"features:  {feature_path}")


if __name__ == "__main__":
    main()
