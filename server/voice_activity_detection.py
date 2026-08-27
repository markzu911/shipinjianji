from __future__ import annotations

import hashlib
import math
import os
import threading
import wave
from pathlib import Path
from typing import Any


VAD_NAME = "funasr-fsmn-vad"
MODEL_ALIAS = "fsmn-vad"
MODEL_ID = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
MODEL_REVISION = "v2.0.4"
MODEL_WEIGHT_SIZE = 1_721_366
MODEL_WEIGHT_SHA256 = (
    "B3BE75BE477F0780277F3BAE0FE489F48718F585F3A6E45D7DD1FBB1A4255FC5"
)
SAMPLE_RATE = 16_000


_MODEL_LOCK = threading.Lock()
_INFERENCE_LOCK = threading.Lock()
_MODELS: dict[str, Any] = {}
_MODEL_FAILURES: dict[str, str] = {}
_VERIFIED_MODEL_ROOTS: set[str] = set()


class VoiceActivityFailure(RuntimeError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _verify_local_wav(audio_path: Path, duration: float) -> None:
    if not math.isfinite(duration) or duration <= 0:
        raise VoiceActivityFailure("invalid_duration", "局部音频时长无效。")
    if not audio_path.is_file():
        raise VoiceActivityFailure("source_missing", "局部音频不存在。")
    try:
        with wave.open(str(audio_path), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frame_count = source.getnframes()
    except (OSError, EOFError, wave.Error) as exc:
        raise VoiceActivityFailure(
            "invalid_audio_format",
            "局部音频不是有效 WAV。",
        ) from exc
    if channels != 1 or sample_width != 2 or sample_rate != SAMPLE_RATE:
        raise VoiceActivityFailure(
            "invalid_audio_format",
            "局部音频必须是 16 kHz 单声道 PCM WAV。",
        )
    decoded_duration = frame_count / SAMPLE_RATE
    if abs(decoded_duration - duration) > max(0.05, 1 / SAMPLE_RATE):
        raise VoiceActivityFailure(
            "invalid_audio_duration",
            "局部音频时长与声明不一致。",
        )


def _verify_model_weight(model_cache_dir: Path) -> None:
    root_key = str(model_cache_dir.resolve())
    if root_key in _VERIFIED_MODEL_ROOTS:
        return
    try:
        candidates = [
            path
            for path in model_cache_dir.rglob("model.pt")
            if path.stat().st_size == MODEL_WEIGHT_SIZE
        ]
    except OSError as exc:
        raise VoiceActivityFailure(
            "model_weight_unreadable",
            "FSMN-VAD 模型权重无法读取。",
        ) from exc
    if not candidates:
        raise VoiceActivityFailure(
            "model_weight_missing",
            "FSMN-VAD 模型权重不存在或大小不匹配。",
        )
    if not any(_sha256_file(path) == MODEL_WEIGHT_SHA256 for path in candidates):
        raise VoiceActivityFailure(
            "model_checksum_mismatch",
            "FSMN-VAD 模型校验失败。",
        )
    _VERIFIED_MODEL_ROOTS.add(root_key)


def _load_model(model_cache_dir: Path) -> Any:
    cache_key = str(model_cache_dir.resolve())
    with _MODEL_LOCK:
        cached = _MODELS.get(cache_key)
        if cached is not None:
            return cached
        prior_failure = _MODEL_FAILURES.get(cache_key)
        if prior_failure:
            raise VoiceActivityFailure(
                prior_failure,
                "FSMN-VAD 本地运行时不可用。",
            )
        try:
            model_cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ["MODELSCOPE_CACHE"] = str(model_cache_dir)
            try:
                import torch
                from funasr import AutoModel
            except (ImportError, OSError) as exc:
                raise VoiceActivityFailure(
                    "runtime_unavailable",
                    "FSMN-VAD 本地运行时不可用。",
                ) from exc
            torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
            model = AutoModel(
                model=MODEL_ALIAS,
                model_revision=MODEL_REVISION,
                hub="ms",
                device="cpu",
                ncpu=max(1, min(4, os.cpu_count() or 1)),
                disable_update=True,
                disable_pbar=True,
                log_level="WARNING",
            )
            _verify_model_weight(model_cache_dir)
        except VoiceActivityFailure as exc:
            _MODEL_FAILURES[cache_key] = exc.reason
            raise
        except Exception as exc:
            _MODEL_FAILURES[cache_key] = "model_load_failed"
            raise VoiceActivityFailure(
                "model_load_failed",
                "FSMN-VAD 模型加载失败。",
            ) from exc
        _MODELS[cache_key] = model
        return model


def _public_speech_ranges(result: Any, duration: float) -> list[dict[str, float]]:
    item = result[0] if isinstance(result, list) and result else result
    raw_ranges = None
    if isinstance(item, dict):
        raw_ranges = item.get("value")
        if raw_ranges is None:
            raw_ranges = item.get("timestamp")
    if raw_ranges is None and result == []:
        raw_ranges = []
    if not isinstance(raw_ranges, list):
        raise VoiceActivityFailure(
            "invalid_result_shape",
            "FSMN-VAD 返回结构无效。",
        )

    normalized: list[tuple[float, float]] = []
    for raw_range in raw_ranges:
        if not isinstance(raw_range, (list, tuple)) or len(raw_range) < 2:
            raise VoiceActivityFailure(
                "invalid_result_shape",
                "FSMN-VAD 返回区间格式无效。",
            )
        try:
            start = float(raw_range[0]) / 1000.0
            end = float(raw_range[1]) / 1000.0
        except (TypeError, ValueError) as exc:
            raise VoiceActivityFailure(
                "invalid_result_value",
                "FSMN-VAD 返回时间无效。",
            ) from exc
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
            or end > duration + 0.01
        ):
            raise VoiceActivityFailure(
                "invalid_result_range",
                "FSMN-VAD 返回区间越界。",
            )
        start = max(0.0, min(start, duration))
        end = max(start, min(end, duration))
        if normalized and start < normalized[-1][0] - 0.001:
            raise VoiceActivityFailure(
                "invalid_result_order",
                "FSMN-VAD 返回区间顺序无效。",
            )
        if normalized and start <= normalized[-1][1] + 0.001:
            normalized[-1] = (normalized[-1][0], max(normalized[-1][1], end))
        else:
            normalized.append((start, end))
    return [
        {"start": round(start, 6), "end": round(end, 6)}
        for start, end in normalized
    ]


def run_funasr_voice_activity(
    audio_path: Path,
    duration: float,
    model_cache_dir: Path,
) -> list[dict[str, float]]:
    model = _load_model(model_cache_dir)
    try:
        with _INFERENCE_LOCK:
            result = model.generate(input=str(audio_path), disable_pbar=True)
    except Exception as exc:
        raise VoiceActivityFailure(
            "inference_failed",
            "FSMN-VAD 局部推理失败。",
        ) from exc
    return _public_speech_ranges(result, duration)


def analyze_local_voice_activity(
    audio_path: Path,
    duration: float,
    model_cache_dir: Path,
) -> dict[str, Any]:
    """Return validated public speech ranges or a stable fallback reason."""
    try:
        _verify_local_wav(audio_path, duration)
        speech_ranges = run_funasr_voice_activity(
            audio_path,
            duration,
            model_cache_dir,
        )
    except VoiceActivityFailure as exc:
        return {
            "status": "unavailable",
            "reason": exc.reason,
            "speechRanges": [],
            "vad": VAD_NAME,
            "modelId": MODEL_ID,
            "modelRevision": MODEL_REVISION,
        }
    except (OSError, RuntimeError) as exc:
        return {
            "status": "unavailable",
            "reason": "runtime_failed",
            "speechRanges": [],
            "vad": VAD_NAME,
            "modelId": MODEL_ID,
            "modelRevision": MODEL_REVISION,
        }
    return {
        "status": "completed",
        "reason": None,
        "speechRanges": speech_ranges,
        "vad": VAD_NAME,
        "modelId": MODEL_ID,
        "modelRevision": MODEL_REVISION,
    }


def clear_voice_activity_runtime_cache() -> None:
    """Reset process caches for isolated tests."""
    with _MODEL_LOCK:
        _MODELS.clear()
        _MODEL_FAILURES.clear()
        _VERIFIED_MODEL_ROOTS.clear()
