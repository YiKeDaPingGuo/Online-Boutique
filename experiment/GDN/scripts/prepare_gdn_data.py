#!/usr/bin/env python3
"""Convert Online Boutique experiment CSVs into GDN dataset format."""

import argparse
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_FAULT_WINDOWS = [
    ("2026-06-05 13:16:00", "2026-06-05 13:23:00"),
    ("2026-06-05 13:33:00", "2026-06-05 13:39:00"),
    ("2026-06-05 13:49:00", "2026-06-05 13:56:00"),
]


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")


def load_fault_windows(log_path: Path):
    if not log_path.exists():
        return DEFAULT_FAULT_WINDOWS

    text = log_path.read_text(encoding="utf-8")
    starts = re.findall(r"故障注入时间：(.+)", text)
    ends = re.findall(r"故障结束时间：(.+)", text)
    windows = list(zip(starts, ends))
    return windows or DEFAULT_FAULT_WINDOWS


def expand_fault_windows(fault_windows, recovery_minutes: int):
    if recovery_minutes <= 0:
        return fault_windows
    expanded = []
    for start, end in fault_windows:
        end_ts = parse_ts(end) + timedelta(minutes=recovery_minutes)
        expanded.append((start, end_ts.strftime("%Y-%m-%d %H:%M:%S")))
    return expanded


def in_fault_window(ts: datetime, fault_windows) -> int:
    for start, end in fault_windows:
        if parse_ts(start) <= ts <= parse_ts(end):
            return 1
    return 0


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = [c for c in reader.fieldnames if c != "timestamp"]
    return rows, fields


def field_has_values(rows, field: str) -> bool:
    for row in rows:
        raw = row.get(field, "")
        if str(raw).strip() != "":
            return True
    return False


def filter_empty_fields(all_rows, fields):
    kept = [field for field in fields if any(field_has_values(rows, field) for rows in all_rows)]
    dropped = [field for field in fields if field not in kept]
    return kept, dropped


def write_gdn_csv(path: Path, rows, fields, fault_windows, with_attack=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["index"] + fields + (["attack"] if with_attack else [])
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for idx, row in enumerate(rows):
            values = [idx]
            for field in fields:
                raw = row.get(field, "")
                values.append("0" if raw == "" else raw)
            if with_attack:
                ts = parse_ts(row["timestamp"])
                values.append(in_fault_window(ts, fault_windows))
            writer.writerow(values)


def merge_fault_rows(paths):
    merged = {}
    for path in paths:
        rows, _ = read_csv(path)
        for row in rows:
            merged[row["timestamp"]] = row
    return [merged[k] for k in sorted(merged.keys())]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parents[1] / "data"),
        help="Directory containing exported CSV files",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[2] / "gdn-reproduce" / "data" / "onlineboutique"),
        help="GDN dataset output directory",
    )
    parser.add_argument(
        "--log-file",
        default=str(Path(__file__).resolve().parents[1] / "experiment-log.md"),
        help="Experiment log containing fault injection windows",
    )
    parser.add_argument(
        "--recovery-minutes",
        type=int,
        default=2,
        help="Extend each fault end time by N minutes when labeling attack=1",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    fault_windows = expand_fault_windows(
        load_fault_windows(Path(args.log_file)),
        args.recovery_minutes,
    )

    train_rows, fields = read_csv(data_dir / "normal_train.csv")
    valid_rows, _ = read_csv(data_dir / "normal_valid.csv")
    fault_rows = merge_fault_rows(
        [
            data_dir / "fault_cpu_frontend.csv",
            data_dir / "fault_delay_cart.csv",
            data_dir / "fault_kill_product.csv",
        ]
    )
    fields, dropped_fields = filter_empty_fields([train_rows, valid_rows, fault_rows], fields)

    write_gdn_csv(output_dir / "train.csv", train_rows, fields, fault_windows, with_attack=False)
    write_gdn_csv(output_dir / "test.csv", fault_rows, fields, fault_windows, with_attack=True)

    with (output_dir / "list.txt").open("w", encoding="utf-8") as f:
        for field in fields:
            f.write(f"{field}\n")

    print(f"GDN dataset written to: {output_dir}")
    print(f"Features: {len(fields)}")
    if dropped_fields:
        print(f"Dropped empty features: {len(dropped_fields)}")
        print("  " + ", ".join(dropped_fields[:8]) + (" ..." if len(dropped_fields) > 8 else ""))
    print(f"Train rows: {len(train_rows)}")
    print(f"Test rows: {len(fault_rows)}")
    attack_rows = sum(in_fault_window(parse_ts(r["timestamp"]), fault_windows) for r in fault_rows)
    print(f"Attack label windows (recovery +{args.recovery_minutes} min):")
    for start, end in fault_windows:
        print(f"  - {start} -> {end}")
    print(f"Attack rows: {attack_rows}")
    print(f"Normal rows in test: {len(fault_rows) - attack_rows}")


if __name__ == "__main__":
    main()
