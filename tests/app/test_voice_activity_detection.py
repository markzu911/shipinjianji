from __future__ import annotations

import sys
import threading
import types
import wave
from pathlib import Path

import pytest

from server import voice_activity_detection as vad


def write_pcm_wav(
    path: Path,
    *,
    duration: float = 0.2,
    sample_rate: int = vad.SAMPLE_RATE,
    channels: int = 1,
) -> None:
    frame_count = round(duration * sample_rate)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\0\0" * frame_count * channels)


def test_vad_model_identity_is_pinned() -> None:
    assert vad.MODEL_ALIAS == "fsmn-vad"
    assert vad.MODEL_ID == "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    assert vad.MODEL_REVISION == "v2.0.4"
    assert vad.MODEL_WEIGHT_SIZE == 1_721_366
    assert vad.MODEL_WEIGHT_SHA256 == (
        "B3BE75BE477F0780277F3BAE0FE489F48718F585F3A6E45D7DD1FBB1A4255FC5"
    )


def test_analyze_local_voice_activity_normalizes_and_merges_public_ranges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "window.wav"
    write_pcm_wav(audio_path, duration=0.5)
    monkeypatch.setattr(
        vad,
        "run_funasr_voice_activity",
        lambda *_args: [
            {"start": 0.01, "end": 0.2},
            {"start": 0.2, "end": 0.4},
        ],
    )

    result = vad.analyze_local_voice_activity(
        audio_path,
        0.5,
        tmp_path / "models",
    )

    assert result["status"] == "completed"
    assert result["speechRanges"] == [
        {"start": 0.01, "end": 0.2},
        {"start": 0.2, "end": 0.4},
    ]
    assert result["modelRevision"] == "v2.0.4"


def test_public_vad_ranges_are_merged_and_milliseconds_are_normalized() -> None:
    assert vad._public_speech_ranges(
        [{"value": [[0, 100], [100, 250], [400, 500]]}],
        0.5,
    ) == [
        {"start": 0.0, "end": 0.25},
        {"start": 0.4, "end": 0.5},
    ]


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({}, "invalid_result_shape"),
        ([{"value": [[100]]}], "invalid_result_shape"),
        ([{"value": [["x", 100]]}], "invalid_result_value"),
        ([{"value": [[200, 100]]}], "invalid_result_range"),
        ([{"value": [[0, 600]]}], "invalid_result_range"),
        ([{"value": [[300, 400], [100, 200]]}], "invalid_result_order"),
    ],
)
def test_public_vad_ranges_reject_invalid_results(payload, reason: str) -> None:
    with pytest.raises(vad.VoiceActivityFailure) as error:
        vad._public_speech_ranges(payload, 0.5)
    assert error.value.reason == reason


@pytest.mark.parametrize(
    ("sample_rate", "channels"),
    [(8_000, 1), (vad.SAMPLE_RATE, 2)],
)
def test_analyze_rejects_non_16k_mono_wav(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sample_rate: int,
    channels: int,
) -> None:
    audio_path = tmp_path / "invalid.wav"
    write_pcm_wav(
        audio_path,
        sample_rate=sample_rate,
        channels=channels,
    )
    monkeypatch.setattr(
        vad,
        "run_funasr_voice_activity",
        lambda *_args: pytest.fail("invalid audio must not run VAD"),
    )

    result = vad.analyze_local_voice_activity(
        audio_path,
        0.2,
        tmp_path / "models",
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "invalid_audio_format"


def test_analyze_maps_inference_failure_to_stable_reason(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "window.wav"
    write_pcm_wav(audio_path)

    def fail(*_args):
        raise vad.VoiceActivityFailure("inference_failed", "private details")

    monkeypatch.setattr(vad, "run_funasr_voice_activity", fail)
    result = vad.analyze_local_voice_activity(
        audio_path,
        0.2,
        tmp_path / "models",
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "inference_failed"
    assert "private details" not in str(result)


def test_run_vad_serializes_inference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    active = 0
    maximum_active = 0
    gate = threading.Barrier(3)
    state_lock = threading.Lock()

    class Model:
        def generate(self, **_kwargs):
            nonlocal active, maximum_active
            with state_lock:
                active += 1
                maximum_active = max(maximum_active, active)
            threading.Event().wait(0.02)
            with state_lock:
                active -= 1
            return [{"value": [[0, 100]]}]

    monkeypatch.setattr(vad, "_load_model", lambda _path: Model())
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            gate.wait()
            vad.run_funasr_voice_activity(
                tmp_path / "unused.wav",
                0.1,
                tmp_path / "models",
            )
        except BaseException as exc:  # pragma: no cover - assertion reports it
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    gate.wait()
    for thread in threads:
        thread.join()

    assert errors == []
    assert maximum_active == 1


def test_vad_model_load_is_cached_per_resolved_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    created: list[dict[str, object]] = []

    class Model:
        pass

    def create_model(**kwargs):
        created.append(kwargs)
        return Model()

    monkeypatch.setitem(
        sys.modules,
        "torch",
        types.SimpleNamespace(set_num_threads=lambda _count: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "funasr",
        types.SimpleNamespace(AutoModel=create_model),
    )
    monkeypatch.setattr(vad, "_verify_model_weight", lambda _path: None)
    model_dir = tmp_path / "models"

    first = vad._load_model(model_dir)
    second = vad._load_model(model_dir)

    assert first is second
    assert len(created) == 1
    assert created[0]["model"] == vad.MODEL_ALIAS
    assert created[0]["model_revision"] == vad.MODEL_REVISION
    assert created[0]["device"] == "cpu"
    assert created[0]["disable_update"] is True


def test_vad_model_verification_failure_is_stable_and_not_reloaded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    load_count = 0

    def create_model(**_kwargs):
        nonlocal load_count
        load_count += 1
        return object()

    def reject_weight(_path: Path) -> None:
        raise vad.VoiceActivityFailure(
            "model_checksum_mismatch",
            "private model path",
        )

    monkeypatch.setitem(
        sys.modules,
        "torch",
        types.SimpleNamespace(set_num_threads=lambda _count: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "funasr",
        types.SimpleNamespace(AutoModel=create_model),
    )
    monkeypatch.setattr(vad, "_verify_model_weight", reject_weight)
    model_dir = tmp_path / "models"

    for _attempt in range(2):
        with pytest.raises(vad.VoiceActivityFailure) as error:
            vad._load_model(model_dir)
        assert error.value.reason == "model_checksum_mismatch"

    assert load_count == 1
