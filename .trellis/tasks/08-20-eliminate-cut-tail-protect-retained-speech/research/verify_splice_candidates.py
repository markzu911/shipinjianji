"""Compare real FFmpeg splice candidates with secondary ASR and PCM evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel


SAMPLE_RATE = 16_000
CANDIDATES = {
    "old-37.190": 37.190,
    "fa-37.810": 37.810,
    "quiet-39.680": 39.680,
}
LEFT_CONTEXT_START = 30.0
DELETE_START = 33.160
DELETED_TAIL = (37.570, 37.810)
RETAINED_ONSET = (39.850, 40.150)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--whisper-model", type=Path, required=True)
    return parser.parse_args()


def decode_pcm(path: Path) -> np.ndarray:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "f32le",
        "pipe:1",
    ]
    completed = subprocess.run(command, check=True, capture_output=True)
    return np.frombuffer(completed.stdout, dtype=np.float32).copy()


def pcm_window(samples: np.ndarray, start: float, end: float) -> np.ndarray:
    first = max(0, round(start * SAMPLE_RATE))
    last = min(len(samples), round(end * SAMPLE_RATE))
    return samples[first:last]


def normalized_correlation(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) != len(right) or not len(left):
        return 0.0
    left = left.astype(np.float64) - float(np.mean(left))
    right = right.astype(np.float64) - float(np.mean(right))
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator else 0.0


def best_aligned_correlation(
    reference: np.ndarray,
    observed: np.ndarray,
    *,
    max_lag_seconds: float,
) -> dict[str, float]:
    max_lag = round(max_lag_seconds * SAMPLE_RATE)
    best = {"correlation": -1.0, "lagSeconds": 0.0, "rmsRatio": 0.0}
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            ref = reference[-lag:]
            obs = observed[: len(ref)]
        else:
            ref = reference[: len(reference) - lag]
            obs = observed[lag : lag + len(ref)]
        correlation = normalized_correlation(ref, obs)
        if correlation <= best["correlation"]:
            continue
        ref_rms = float(np.sqrt(np.mean(np.square(ref, dtype=np.float64))))
        obs_rms = float(np.sqrt(np.mean(np.square(obs, dtype=np.float64))))
        best = {
            "correlation": correlation,
            "lagSeconds": lag / SAMPLE_RATE,
            "rmsRatio": obs_rms / ref_rms if ref_rms else 0.0,
        }
    return best


def best_window_correlation(reference: np.ndarray, corridor: np.ndarray) -> dict[str, float]:
    if len(corridor) < len(reference):
        return {"correlation": 0.0, "offsetSeconds": 0.0}
    step = max(1, round(0.005 * SAMPLE_RATE))
    best = {"correlation": -1.0, "offsetSeconds": 0.0}
    for offset in range(0, len(corridor) - len(reference) + 1, step):
        correlation = normalized_correlation(
            reference,
            corridor[offset : offset + len(reference)],
        )
        if correlation > best["correlation"]:
            best = {
                "correlation": correlation,
                "offsetSeconds": offset / SAMPLE_RATE,
            }
    return best


def transcribe(model: WhisperModel, path: Path) -> dict[str, object]:
    segments, info = model.transcribe(
        str(path),
        language="zh",
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    rows = []
    for segment in segments:
        rows.append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": [
                    {
                        "start": word.start,
                        "end": word.end,
                        "word": word.word,
                        "probability": word.probability,
                    }
                    for word in (segment.words or [])
                ],
            }
        )
    return {
        "languageProbability": info.language_probability,
        "segments": rows,
    }


def main() -> None:
    args = parse_args()
    source_pcm = decode_pcm(args.source)
    deleted_tail = pcm_window(source_pcm, *DELETED_TAIL)
    retained_onset = pcm_window(source_pcm, *RETAINED_ONSET)
    model = WhisperModel(str(args.whisper_model), device="cpu", compute_type="int8")

    report = {}
    left_duration = DELETE_START - LEFT_CONTEXT_START
    for name, recovery_time in CANDIDATES.items():
        candidate_path = args.candidate_dir / f"splice-{name}.mp4"
        candidate_pcm = decode_pcm(candidate_path)
        retained_output_start = left_duration + RETAINED_ONSET[0] - recovery_time
        retained_output_end = retained_output_start + (
            RETAINED_ONSET[1] - RETAINED_ONSET[0]
        )
        observed_retained = pcm_window(
            candidate_pcm,
            retained_output_start - 0.02,
            retained_output_end + 0.02,
        )
        report[name] = {
            "recoveryTime": recovery_time,
            "asr": transcribe(model, candidate_path),
            "deletedTailFingerprintInFirstRight800ms": best_window_correlation(
                deleted_tail,
                pcm_window(candidate_pcm, left_duration, left_duration + 0.8),
            ),
            "retainedOnsetOutputRange": [retained_output_start, retained_output_end],
            "retainedOnsetIntegrity": best_aligned_correlation(
                retained_onset,
                observed_retained,
                max_lag_seconds=0.02,
            ),
        }
    # ASCII escaping keeps Chinese ASR text intact in Windows terminals whose
    # active code page does not match Python's UTF-8 stdout encoding.
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
