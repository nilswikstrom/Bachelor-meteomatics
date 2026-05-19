"""
sender_test_runner_metgm.py — Automated test runner for METGM UDP file transfers.

Runs (N files) x 3 redundancy levels x 25 runs per configuration.
Reads all METGM files from METGM/andøya/ and METGM/setermoen/.

Usage:
    python sender_test_runner_metgm.py --ip 172.16.3.40 --port 5001 --config metgm_baseline
    python sender_test_runner_metgm.py --ip 172.16.3.40 --port 5001 --config metgm_<<name-of-IT-system>>_pa  ## CHANGE <<name-of-IT-system>>

File layout expected:
    script/
    ├── sender_test_runner_metgm.py
    ├── sender_udp.py
    ├── METGM/
    │   ├── andøya/
    │   │   └── <metgm files>
    │   └── setermoen/
    │       └── <metgm files>
    └── logs/
        └── sender_metgm_baseline.csv
"""

import argparse
import contextlib
import csv
import hashlib
import io
import math
import os
import sys
import time
from datetime import datetime

from sender_udp import send_file


MAX_PAYLOAD = 1400  # Must match sender_udp.py

REDUNDANCY_LEVELS = [
    ("none",   1),
    ("low",    3),
    ("normal", 5),
]

RUNS_PER_COMBO = 25

CSV_COLUMNS = [
    "seq_nr",
    "timestamp",
    "config",
    "filename",
    "filesize_bytes",
    "sha256_source",
    "redundancy_level",
    "repeats",
    "packets_sent",
    "transfer_time_ms",
    "throughput_mbps",
]


def script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def load_test_files() -> list:
    """Return sorted list of (label, filepath, filesize) from METGM/andøya/ and METGM/setermoen/."""
    metgm_dir = os.path.join(script_dir(), "METGM")
    subfolders = ["andøya", "setermoen"]

    files = []
    for subfolder in subfolders:
        folder_path = os.path.join(metgm_dir, subfolder)
        if not os.path.isdir(folder_path):
            print(f"[WARN] Folder not found, skipping: {folder_path}")
            continue
        for entry in sorted(os.listdir(folder_path)):
            full_path = os.path.join(folder_path, entry)
            if os.path.isfile(full_path):
                label = f"{subfolder}/{entry}"
                files.append((label, full_path, os.path.getsize(full_path)))

    if not files:
        print(f"[ERROR] No files found in {metgm_dir}/andøya or {metgm_dir}/setermoen")
        sys.exit(1)

    print(f"[SETUP] Found {len(files)} METGM file(s):")
    for name, _, size in files:
        print(f"        {name} ({size} bytes)")

    return files


def compute_sha256(filepath: str) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def load_completed_seq_nrs(csv_path: str) -> set:
    completed = set()
    if not os.path.isfile(csv_path):
        return completed
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                completed.add(int(row["seq_nr"]))
            except (KeyError, ValueError):
                pass
    return completed


def open_csv(csv_path: str, is_new: bool):
    f = open(csv_path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
    if is_new:
        writer.writeheader()
    return f, writer


def run_tests(ip: str, port: int, config: str, delay_between: int) -> None:
    test_files = load_test_files()
    total_runs = len(test_files) * len(REDUNDANCY_LEVELS) * RUNS_PER_COMBO
    print(f"[SETUP] Total runs this session: {total_runs}")

    logs_dir = os.path.join(script_dir(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Log file uses metgm_ prefix to separate from METCM logs
    csv_path = os.path.join(logs_dir, f"sender_{config}.csv")
    is_new_file = not os.path.isfile(csv_path)

    completed = load_completed_seq_nrs(csv_path)
    if completed:
        print(f"[RESUME] Found {len(completed)} already-completed run(s) — resuming ...")

    csv_file, writer = open_csv(csv_path, is_new_file)

    seq_nr = 0
    try:
        for filename, filepath, filesize in test_files:
            sha256_source = compute_sha256(filepath)

            for redundancy_label, repeats in REDUNDANCY_LEVELS:
                for run_nr in range(1, RUNS_PER_COMBO + 1):

                    overall_index = seq_nr + 1

                    if seq_nr in completed:
                        print(f"[SKIP]  [{overall_index}/{total_runs}] {filename} | {redundancy_label} | run {run_nr}")
                        seq_nr += 1
                        continue

                    print(f"[{overall_index}/{total_runs}] {filename} | {redundancy_label} | run {run_nr}")

                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                    captured = io.StringIO()
                    t_start = time.monotonic()
                    try:
                        with contextlib.redirect_stdout(captured):
                            send_file(ip=ip, port=port, filepath=filepath,
                                      repeats=repeats, delay_ms=5)
                    except SystemExit as exc:
                        print(f"\n[ERROR] send_file exited with code {exc.code}")
                        csv_file.flush()
                        csv_file.close()
                        sys.exit(1)
                    t_end = time.monotonic()

                    transfer_time_ms = (t_end - t_start) * 1000.0
                    packets_sent = math.ceil(filesize / MAX_PAYLOAD)
                    throughput_mbps = (filesize * 8) / (transfer_time_ms / 1000) / 1_000_000

                    writer.writerow({
                        "seq_nr":           seq_nr,
                        "timestamp":        timestamp,
                        "config":           config,
                        "filename":         filename,
                        "filesize_bytes":   filesize,
                        "sha256_source":    sha256_source,
                        "redundancy_level": redundancy_label,
                        "repeats":          repeats,
                        "packets_sent":     packets_sent,
                        "transfer_time_ms": round(transfer_time_ms, 3),
                        "throughput_mbps":  round(throughput_mbps, 6),
                    })
                    csv_file.flush()
                    seq_nr += 1

                    if overall_index < total_runs:
                        time.sleep(delay_between)

    finally:
        csv_file.close()

    print(f"\n[DONE] All {total_runs} runs complete.")
    print(f"[DONE] Log written to: {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automated UDP transfer test runner for METGM files.")
    parser.add_argument("--ip", required=True, help="Receiver IP address")
    parser.add_argument("--port", type=int, required=True, help="UDP port")
    parser.add_argument("--config", required=True, help="Configuration label (metgm_baseline / metgm_<<name-of-IT-system>>_pa)")  ## CHANGE <<name-of-IT-system>>
    parser.add_argument("--delay-between", type=int, default=3, dest="delay_between",
                        metavar="SECONDS", help="Seconds between runs (default: 3)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_tests(ip=args.ip, port=args.port, config=args.config, delay_between=args.delay_between)
