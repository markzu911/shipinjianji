"""Run the pinned fa-zh model against a read-only WAV fixture."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from pathlib import Path

import psutil


MODEL_ID = "fa-zh"
MODEL_REVISION = "v2.0.4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--offset", type=float, default=0.0)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--threads", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.audio.is_file():
        raise SystemExit(f"audio does not exist: {args.audio}")

    process = psutil.Process(os.getpid())
    peak_rss = process.memory_info().rss
    monitoring = True

    def monitor_memory() -> None:
        nonlocal peak_rss
        while monitoring:
            peak_rss = max(peak_rss, process.memory_info().rss)
            time.sleep(0.02)

    monitor = threading.Thread(target=monitor_memory, daemon=True)
    monitor.start()

    import_started = time.perf_counter()
    import torch
    from funasr import AutoModel

    import_seconds = time.perf_counter() - import_started
    torch.set_num_threads(args.threads)

    load_started = time.perf_counter()
    model = AutoModel(
        model=MODEL_ID,
        model_revision=MODEL_REVISION,
        hub="ms",
        device="cpu",
        ncpu=args.threads,
        disable_update=True,
        disable_pbar=True,
        log_level="WARNING",
    )
    load_seconds = time.perf_counter() - load_started

    reference_tokens = [token for token in args.text.split(" ") if token]
    runs = []
    for _ in range(args.repeats):
        started = time.perf_counter()
        result = model.generate(
            input=(str(args.audio), args.text),
            data_type=("sound", "text"),
            disable_pbar=True,
        )
        elapsed = time.perf_counter() - started
        item = result[0] if isinstance(result, list) and result else result
        timestamps = item.get("timestamp", []) if isinstance(item, dict) else []
        characters = []
        for token, timestamp in zip(reference_tokens, timestamps):
            start_ms, end_ms = timestamp[:2]
            characters.append(
                {
                    "text": token,
                    "localStart": round(float(start_ms) / 1000.0, 6),
                    "localEnd": round(float(end_ms) / 1000.0, 6),
                    "sourceStart": round(args.offset + float(start_ms) / 1000.0, 6),
                    "sourceEnd": round(args.offset + float(end_ms) / 1000.0, 6),
                }
            )
        runs.append(
            {
                "elapsedSeconds": elapsed,
                "result": item,
                "characters": characters,
                "tokenCountMatches": len(reference_tokens) == len(timestamps),
            }
        )

    monitoring = False
    monitor.join(timeout=1.0)
    peak_rss = max(peak_rss, process.memory_info().rss)
    print(
        json.dumps(
            {
                "model": MODEL_ID,
                "modelRevision": MODEL_REVISION,
                "audio": str(args.audio),
                "referenceText": args.text,
                "offset": args.offset,
                "versions": {
                    "torch": torch.__version__,
                },
                "importSeconds": import_seconds,
                "loadSeconds": load_seconds,
                "peakRssBytes": peak_rss,
                "runs": runs,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
