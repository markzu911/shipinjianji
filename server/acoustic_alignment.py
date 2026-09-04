from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import threading
import unicodedata
import uuid
import weakref
from pathlib import Path
from typing import Any, Callable

from .funasr_runtime import load_funasr_auto_model


ALIGNMENT_SCHEMA_VERSION = 1
ALIGNER_NAME = "funasr-fa-zh"
MODEL_ALIAS = "fa-zh"
MODEL_REVISION = "v2.0.4"
MODEL_WEIGHT_SHA256 = (
    "F34EDE558AF831FB504206B25F1C2F27CA2F77753C26C4DD38D03323153B6F73"
)
MODEL_WEIGHT_SIZE = 158_469_618
SAMPLE_RATE = 16_000
ALIGNMENT_SIDECAR_FILENAME = "acoustic-alignment.json"


AlignmentRunner = Callable[[Path, list[str], Path], list[dict[str, Any]]]
AudioExtractor = Callable[[Path, Path, float, float], None]

_MODEL_LOCK = threading.Lock()
_INFERENCE_LOCK = threading.Lock()
_MODELS: dict[str, Any] = {}
_VERIFIED_MODEL_ROOTS: set[str] = set()
_SOURCE_FINGERPRINT_LOCK = threading.Lock()
_SOURCE_FINGERPRINTS: dict[tuple[str, int, int], str] = {}
_SOURCE_FINGERPRINT_CACHE_LIMIT = 64
_SIDECAR_LOCKS_LOCK = threading.Lock()
_SIDECAR_LOCKS: weakref.WeakValueDictionary[str, threading.Lock] = (
    weakref.WeakValueDictionary()
)


class AlignmentFailure(RuntimeError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def spoken_characters(text: str) -> list[str]:
    return [
        character
        for character in str(text or "")
        if not character.isspace()
        and not unicodedata.category(character).startswith("P")
    ]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def source_fingerprint(media_path: Path) -> str:
    stat = media_path.stat()
    key = (str(media_path.resolve()), stat.st_size, stat.st_mtime_ns)
    with _SOURCE_FINGERPRINT_LOCK:
        cached = _SOURCE_FINGERPRINTS.get(key)
    if cached is not None:
        return cached
    fingerprint = _sha256_file(media_path)
    with _SOURCE_FINGERPRINT_LOCK:
        for stale_key in [
            cached_key
            for cached_key in _SOURCE_FINGERPRINTS
            if cached_key[0] == key[0] and cached_key != key
        ]:
            _SOURCE_FINGERPRINTS.pop(stale_key, None)
        if len(_SOURCE_FINGERPRINTS) >= _SOURCE_FINGERPRINT_CACHE_LIMIT:
            _SOURCE_FINGERPRINTS.pop(next(iter(_SOURCE_FINGERPRINTS)))
        _SOURCE_FINGERPRINTS[key] = fingerprint
    return fingerprint


def alignment_sidecar_path(job_directory: Path) -> Path:
    return job_directory / ALIGNMENT_SIDECAR_FILENAME


def _sidecar_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _SIDECAR_LOCKS_LOCK:
        return _SIDECAR_LOCKS.setdefault(key, threading.Lock())


def _stable_fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _segment_reference(segment: dict[str, Any]) -> tuple[list[str], float, float]:
    characters = spoken_characters(str(segment.get("text") or ""))
    try:
        start = float(segment.get("start"))
        end = float(segment.get("end"))
    except (TypeError, ValueError) as exc:
        raise AlignmentFailure("invalid_segment_envelope", "句段时间无效。") from exc
    if (
        not characters
        or not math.isfinite(start)
        or not math.isfinite(end)
        or start < 0
        or end <= start
    ):
        raise AlignmentFailure("invalid_segment_envelope", "句段文字或时间无效。")
    return characters, start, end


def _segment_key(
    source_hash: str,
    characters: list[str],
    start: float,
    end: float,
) -> tuple[str, str]:
    text_fingerprint = _stable_fingerprint(characters)
    return (
        _stable_fingerprint(
            {
                "schemaVersion": ALIGNMENT_SCHEMA_VERSION,
                "sourceFingerprint": source_hash,
                "spokenTextFingerprint": text_fingerprint,
                "envelopeStart": round(start, 3),
                "envelopeEnd": round(end, 3),
                "aligner": ALIGNER_NAME,
                "modelRevision": MODEL_REVISION,
            }
        ),
        text_fingerprint,
    )


def extract_segment_audio(
    media_path: Path,
    output_path: Path,
    start: float,
    end: float,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AlignmentFailure("ffmpeg_unavailable", "未找到 FFmpeg。")
    command = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start:.6f}",
        "-to",
        f"{end:.6f}",
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60 * 30,
        check=False,
    )
    if completed.returncode != 0 or not output_path.is_file():
        details = completed.stderr.strip().splitlines()
        reason = details[-1] if details else "FFmpeg 未生成句段音频"
        raise AlignmentFailure("segment_decode_failed", reason)


def _verify_model_weight(model_cache_dir: Path) -> None:
    root_key = str(model_cache_dir.resolve())
    if root_key in _VERIFIED_MODEL_ROOTS:
        return
    candidates = [
        path
        for path in model_cache_dir.rglob("model.pt")
        if path.stat().st_size == MODEL_WEIGHT_SIZE
    ]
    if not candidates:
        raise AlignmentFailure(
            "model_weight_missing",
            "fa-zh 模型权重不存在或大小不匹配。",
        )
    if not any(_sha256_file(path) == MODEL_WEIGHT_SHA256 for path in candidates):
        raise AlignmentFailure("model_checksum_mismatch", "fa-zh 模型校验失败。")
    _VERIFIED_MODEL_ROOTS.add(root_key)


def _load_model(model_cache_dir: Path) -> Any:
    cache_key = str(model_cache_dir.resolve())
    with _MODEL_LOCK:
        cached = _MODELS.get(cache_key)
        if cached is not None:
            return cached
        model_cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["MODELSCOPE_CACHE"] = str(model_cache_dir)
        try:
            import torch
            AutoModel = load_funasr_auto_model()
        except (ImportError, OSError) as exc:
            raise AlignmentFailure(
                "runtime_unavailable",
                "本地语音对齐运行时不可用。",
            ) from exc
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        try:
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
        except AlignmentFailure:
            raise
        except Exception as exc:
            raise AlignmentFailure("model_load_failed", "fa-zh 模型加载失败。") from exc
        _MODELS[cache_key] = model
        return model


def run_funasr_alignment(
    audio_path: Path,
    reference_characters: list[str],
    model_cache_dir: Path,
) -> list[dict[str, Any]]:
    model = _load_model(model_cache_dir)
    reference_text = " ".join(reference_characters)
    try:
        with _INFERENCE_LOCK:
            result = model.generate(
                input=(str(audio_path), reference_text),
                data_type=("sound", "text"),
                disable_pbar=True,
            )
    except Exception as exc:
        raise AlignmentFailure("inference_failed", "fa-zh 句段对齐失败。") from exc
    item = result[0] if isinstance(result, list) and result else result
    timestamps = item.get("timestamp") if isinstance(item, dict) else None
    if not isinstance(timestamps, list):
        raise AlignmentFailure("missing_timestamps", "fa-zh 未返回字符时间。")
    characters: list[dict[str, Any]] = []
    for character, timestamp in zip(reference_characters, timestamps):
        if not isinstance(timestamp, (list, tuple)) or len(timestamp) < 2:
            raise AlignmentFailure("invalid_timestamp_shape", "fa-zh 时间格式无效。")
        try:
            start = float(timestamp[0]) / 1000.0
            end = float(timestamp[1]) / 1000.0
        except (TypeError, ValueError) as exc:
            raise AlignmentFailure("invalid_timestamp", "fa-zh 时间值无效。") from exc
        characters.append({"text": character, "start": start, "end": end})
    if len(timestamps) != len(reference_characters):
        raise AlignmentFailure("character_count_mismatch", "fa-zh 字符数量不匹配。")
    return characters


def validate_segment_alignment(
    reference_characters: list[str],
    raw_characters: list[dict[str, Any]],
    envelope_start: float,
    envelope_end: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(raw_characters) != len(reference_characters):
        raise AlignmentFailure("character_count_mismatch", "对齐字符数量不匹配。")
    duration = envelope_end - envelope_start
    validated: list[dict[str, Any]] = []
    previous_start = -1.0
    previous_end = -1.0
    for expected, raw in zip(reference_characters, raw_characters, strict=True):
        if str(raw.get("text") or "") != expected:
            raise AlignmentFailure("character_order_mismatch", "对齐字符顺序不匹配。")
        try:
            local_start = float(raw.get("start"))
            local_end = float(raw.get("end"))
        except (TypeError, ValueError) as exc:
            raise AlignmentFailure("invalid_timestamp", "对齐时间无效。") from exc
        if (
            not math.isfinite(local_start)
            or not math.isfinite(local_end)
            or local_start < 0
            or local_end <= local_start
            or local_start < previous_start - 0.001
            or local_end < previous_end - 0.001
            or (
                abs(local_start - previous_start) <= 0.001
                and abs(local_end - previous_end) <= 0.001
            )
            or local_end > duration + 0.05
        ):
            raise AlignmentFailure("non_monotonic_timestamps", "对齐时间不单调。")
        previous_start = local_start
        previous_end = local_end
        validated.append(
            {
                "text": expected,
                "start": round(envelope_start + local_start, 3),
                "end": round(envelope_start + local_end, 3),
            }
        )
    return validated, {
        "valid": True,
        "reason": None,
        "expectedCharacterCount": len(reference_characters),
        "alignedCharacterCount": len(validated),
        "confidence": None,
        "fullSegment": True,
    }


def _coarse_token_deviation(
    segment: dict[str, Any],
    reference_characters: list[str],
    aligned_characters: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_characters: list[dict[str, float | str]] = []
    raw_items = segment.get("asrWords")
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            characters = spoken_characters(str(item.get("text") or ""))
            try:
                start = float(item.get("start"))
                end = float(item.get("end"))
            except (TypeError, ValueError):
                continue
            if (
                not characters
                or not math.isfinite(start)
                or not math.isfinite(end)
                or end <= start
            ):
                continue
            duration = end - start
            for index, character in enumerate(characters):
                raw_characters.append(
                    {
                        "text": character,
                        "start": start + duration * index / len(characters),
                        "end": start + duration * (index + 1) / len(characters),
                    }
                )
    mapping_valid = (
        [str(item["text"]) for item in raw_characters] == reference_characters
    )
    if not mapping_valid:
        return {
            "coarseTokenMappingValid": False,
            "coarseTokenMaxBoundaryDeviationSeconds": None,
            "coarseTokenMaxEscapeSeconds": None,
        }
    boundary_deviations: list[float] = []
    escapes: list[float] = []
    for raw, aligned in zip(raw_characters, aligned_characters, strict=True):
        raw_start = float(raw["start"])
        raw_end = float(raw["end"])
        aligned_start = float(aligned["start"])
        aligned_end = float(aligned["end"])
        boundary_deviations.extend(
            (abs(aligned_start - raw_start), abs(aligned_end - raw_end))
        )
        escapes.extend(
            (
                max(0.0, raw_start - aligned_start),
                max(0.0, aligned_end - raw_end),
            )
        )
    return {
        "coarseTokenMappingValid": True,
        "coarseTokenMaxBoundaryDeviationSeconds": round(
            max(boundary_deviations, default=0.0),
            3,
        ),
        "coarseTokenMaxEscapeSeconds": round(max(escapes, default=0.0), 3),
    }


def _load_sidecar(path: Path, source_hash: str) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != ALIGNMENT_SCHEMA_VERSION
        or payload.get("sourceFingerprint") != source_hash
        or payload.get("aligner") != ALIGNER_NAME
        or payload.get("modelRevision") != MODEL_REVISION
        or not isinstance(payload.get("segments"), list)
    ):
        return {}
    return payload


def _validated_cached_record(
    record: dict[str, Any] | None,
    *,
    segment_index: int,
    segment_key: str,
    text_fingerprint: str,
    reference: list[str],
    envelope_start: float,
    envelope_end: float,
) -> dict[str, Any] | None:
    if (
        not isinstance(record, dict)
        or record.get("segmentKey") != segment_key
        or record.get("spokenTextFingerprint") != text_fingerprint
        or not isinstance(record.get("validation"), dict)
        or record["validation"].get("valid") is not True
        or not isinstance(record.get("characters"), list)
    ):
        return None
    try:
        if (
            abs(float(record.get("envelopeStart")) - envelope_start) > 0.001
            or abs(float(record.get("envelopeEnd")) - envelope_end) > 0.001
        ):
            return None
        local_characters = [
            {
                "text": str(item.get("text") or ""),
                "start": float(item.get("start")) - envelope_start,
                "end": float(item.get("end")) - envelope_start,
            }
            for item in record["characters"]
            if isinstance(item, dict)
        ]
        characters, structural_validation = validate_segment_alignment(
            reference,
            local_characters,
            envelope_start,
            envelope_end,
        )
    except (AlignmentFailure, TypeError, ValueError):
        return None
    validation = dict(record["validation"])
    validation.update(structural_validation)
    return {
        **record,
        "segmentIndex": segment_index,
        "characters": characters,
        "validation": validation,
    }


def _write_sidecar(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_acoustic_alignment_cache(
    media_path: Path,
    segments: list[dict[str, Any]],
    job_directory: Path,
    model_cache_dir: Path,
    *,
    alignment_runner: AlignmentRunner | None = None,
    audio_extractor: AudioExtractor | None = None,
    segment_indexes: set[int] | None = None,
) -> dict[str, Any]:
    sidecar_path = alignment_sidecar_path(job_directory)
    with _sidecar_lock(sidecar_path):
        return _ensure_acoustic_alignment_cache_unlocked(
            media_path,
            segments,
            job_directory,
            model_cache_dir,
            alignment_runner=alignment_runner,
            audio_extractor=audio_extractor,
            segment_indexes=segment_indexes,
        )


def load_acoustic_alignment_cache(
    media_path: Path,
    segments: list[dict[str, Any]],
    job_directory: Path,
) -> dict[str, Any] | None:
    """Read and revalidate an existing sidecar without running alignment."""
    if not media_path.is_file():
        return None
    try:
        source_hash = source_fingerprint(media_path)
    except OSError:
        return None
    cached = _load_sidecar(alignment_sidecar_path(job_directory), source_hash)
    if not cached:
        return None
    cached_records = {
        str(item.get("segmentKey")): item
        for item in cached.get("segments") or []
        if isinstance(item, dict) and item.get("segmentKey")
    }
    records: list[dict[str, Any]] = []
    for segment_index, segment in enumerate(segments):
        try:
            reference, envelope_start, envelope_end = _segment_reference(segment)
        except AlignmentFailure:
            continue
        segment_key, text_fingerprint = _segment_key(
            source_hash,
            reference,
            envelope_start,
            envelope_end,
        )
        record = _validated_cached_record(
            cached_records.get(segment_key),
            segment_index=segment_index,
            segment_key=segment_key,
            text_fingerprint=text_fingerprint,
            reference=reference,
            envelope_start=envelope_start,
            envelope_end=envelope_end,
        )
        if record is not None:
            records.append(record)
    if not records:
        return None
    return {
        **cached,
        "segments": records,
        "summary": {
            **(cached.get("summary") or {}),
            "validSegmentCount": len(records),
            "reusedSegmentCount": len(records),
        },
    }


def _ensure_acoustic_alignment_cache_unlocked(
    media_path: Path,
    segments: list[dict[str, Any]],
    job_directory: Path,
    model_cache_dir: Path,
    *,
    alignment_runner: AlignmentRunner | None,
    audio_extractor: AudioExtractor | None,
    segment_indexes: set[int] | None,
) -> dict[str, Any]:
    if not media_path.is_file():
        raise AlignmentFailure("source_missing", "原视频不存在。")
    source_hash = source_fingerprint(media_path)
    sidecar_path = alignment_sidecar_path(job_directory)
    cached = _load_sidecar(sidecar_path, source_hash)
    cached_records = {
        str(item.get("segmentKey")): item
        for item in cached.get("segments") or []
        if isinstance(item, dict) and item.get("segmentKey")
    }
    runner = alignment_runner or run_funasr_alignment
    extractor = audio_extractor or extract_segment_audio
    records: list[dict[str, Any]] = []
    reused = 0
    eligible_segment_count = 0
    for segment_index, segment in enumerate(segments):
        try:
            reference, envelope_start, envelope_end = _segment_reference(segment)
        except AlignmentFailure:
            continue
        eligible_segment_count += 1
        segment_key, text_fingerprint = _segment_key(
            source_hash,
            reference,
            envelope_start,
            envelope_end,
        )
        record = _validated_cached_record(
            cached_records.get(segment_key),
            segment_index=segment_index,
            segment_key=segment_key,
            text_fingerprint=text_fingerprint,
            reference=reference,
            envelope_start=envelope_start,
            envelope_end=envelope_end,
        )
        if record is not None:
            records.append(record)
            reused += 1
            continue
        if segment_indexes is not None and segment_index not in segment_indexes:
            continue
        audio_path = job_directory / f".acoustic-segment-{segment_key[:16]}.wav"
        try:
            extractor(media_path, audio_path, envelope_start, envelope_end)
            raw_characters = runner(audio_path, reference, model_cache_dir)
            characters, validation = validate_segment_alignment(
                reference,
                raw_characters,
                envelope_start,
                envelope_end,
            )
            validation.update(
                _coarse_token_deviation(segment, reference, characters)
            )
        except AlignmentFailure as exc:
            characters = []
            validation = {
                "valid": False,
                "reason": exc.reason,
                "message": str(exc),
                "expectedCharacterCount": len(reference),
                "alignedCharacterCount": 0,
                "confidence": None,
                "fullSegment": True,
                "coarseTokenMappingValid": None,
                "coarseTokenMaxBoundaryDeviationSeconds": None,
                "coarseTokenMaxEscapeSeconds": None,
            }
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            characters = []
            validation = {
                "valid": False,
                "reason": "alignment_runtime_failed",
                "message": str(exc),
                "expectedCharacterCount": len(reference),
                "alignedCharacterCount": 0,
                "confidence": None,
                "fullSegment": True,
                "coarseTokenMappingValid": None,
                "coarseTokenMaxBoundaryDeviationSeconds": None,
                "coarseTokenMaxEscapeSeconds": None,
            }
        finally:
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                pass
        records.append(
            {
                "segmentIndex": segment_index,
                "segmentKey": segment_key,
                "spokenTextFingerprint": text_fingerprint,
                "envelopeStart": round(envelope_start, 3),
                "envelopeEnd": round(envelope_end, 3),
                "characters": characters,
                "validation": validation,
            }
        )
    valid_segment_count = sum(
        bool(item["validation"]["valid"]) for item in records
    )
    payload = {
        "schemaVersion": ALIGNMENT_SCHEMA_VERSION,
        "sourceFingerprint": source_hash,
        "aligner": ALIGNER_NAME,
        "modelRevision": MODEL_REVISION,
        "segments": records,
        "summary": {
            "status": (
                "completed"
                if eligible_segment_count > 0
                and valid_segment_count == eligible_segment_count
                else "partial"
                if valid_segment_count > 0
                else "unavailable"
            ),
            "segmentCount": len(records),
            "totalSegmentCount": eligible_segment_count,
            "validSegmentCount": valid_segment_count,
            "reusedSegmentCount": reused,
        },
    }
    _write_sidecar(sidecar_path, payload)
    return payload
