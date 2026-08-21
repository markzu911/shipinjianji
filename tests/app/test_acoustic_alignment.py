from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import server.app as app_module
from server import acoustic_alignment


def _fake_extractor(
    _media_path: Path,
    output_path: Path,
    _start: float,
    _end: float,
) -> None:
    output_path.write_bytes(b"segment")


def _monotonic_result(
    _audio_path: Path,
    reference: list[str],
    _model_cache_dir: Path,
) -> list[dict[str, object]]:
    return [
        {"text": character, "start": index * 0.1, "end": index * 0.1 + 0.08}
        for index, character in enumerate(reference)
    ]


def test_app_suite_fixture_never_enters_real_funasr_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")
    monkeypatch.setattr(
        acoustic_alignment,
        "_load_model",
        lambda _cache_dir: pytest.fail("普通应用测试不得加载真实 FunASR 模型"),
    )

    summary = app_module.prepare_job_acoustic_alignment(
        media_path,
        [{"text": "测试文案", "start": 0.0, "end": 1.0}],
    )

    assert summary["status"] == "unavailable"
    assert summary["reason"] == "test_runtime_isolated"
    assert not (app_module.DATA_DIR / "models").exists()


def test_alignment_uses_complete_segment_text_and_reuses_sidecar(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")
    model_cache = tmp_path / "models"
    segments = [
        {
            "text": "一起给一起给。",
            "start": 2.0,
            "end": 4.0,
            "asrWords": [
                {"text": "一起", "start": 2.0, "end": 2.4},
                {"text": "给一", "start": 2.4, "end": 2.8},
                {"text": "起给", "start": 2.8, "end": 3.2},
            ],
        }
    ]
    calls: list[tuple[list[str], float, float]] = []

    def extractor(
        media: Path,
        output: Path,
        start: float,
        end: float,
    ) -> None:
        assert media == media_path
        calls.append(([], start, end))
        output.write_bytes(b"complete-segment")

    def runner(
        audio: Path,
        reference: list[str],
        cache_dir: Path,
    ) -> list[dict[str, object]]:
        assert audio.read_bytes() == b"complete-segment"
        assert cache_dir == model_cache
        calls[-1] = (reference, calls[-1][1], calls[-1][2])
        return _monotonic_result(audio, reference, cache_dir)

    first = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        segments,
        tmp_path,
        model_cache,
        alignment_runner=runner,
        audio_extractor=extractor,
    )
    second = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        segments,
        tmp_path,
        model_cache,
        alignment_runner=lambda *_args: pytest.fail("cache was not reused"),
        audio_extractor=lambda *_args: pytest.fail("audio was decoded again"),
    )

    assert calls == [(list("一起给一起给"), 2.0, 4.0)]
    assert first["segments"][0]["characters"][2] == {
        "text": "给",
        "start": 2.2,
        "end": 2.28,
    }
    assert second["summary"]["reusedSegmentCount"] == 1
    assert not list(tmp_path.glob(".acoustic-segment-*.wav"))
    assert not list(tmp_path.glob(".acoustic-alignment.json.*.tmp"))


def test_alignment_text_change_invalidates_only_changed_segment(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")
    original = [
        {"text": "第一句", "start": 0.0, "end": 1.0},
        {"text": "第二句", "start": 1.0, "end": 2.0},
    ]
    acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        original,
        tmp_path,
        tmp_path / "models",
        alignment_runner=_monotonic_result,
        audio_extractor=_fake_extractor,
    )
    calls: list[str] = []

    def runner(
        audio: Path,
        reference: list[str],
        cache_dir: Path,
    ) -> list[dict[str, object]]:
        calls.append("".join(reference))
        return _monotonic_result(audio, reference, cache_dir)

    changed = [original[0], {"text": "修改句", "start": 1.0, "end": 2.0}]
    payload = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        changed,
        tmp_path,
        tmp_path / "models",
        alignment_runner=runner,
        audio_extractor=_fake_extractor,
    )

    assert calls == ["修改句"]
    assert payload["summary"]["reusedSegmentCount"] == 1


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ([{"text": "得", "start": 0.1, "end": 0.2}], "character_count_mismatch"),
        (
            [
                {"text": "得", "start": 0.2, "end": 0.4},
                {"text": "你", "start": 0.1, "end": 0.3},
            ],
            "non_monotonic_timestamps",
        ),
        (
            [
                {"text": "得", "start": 0.1, "end": float("nan")},
                {"text": "你", "start": 0.3, "end": 0.4},
            ],
            "non_monotonic_timestamps",
        ),
        (
            [
                {"text": "你", "start": 0.1, "end": 0.2},
                {"text": "得", "start": 0.3, "end": 0.4},
            ],
            "character_order_mismatch",
        ),
        (
            [
                {"text": "得", "start": 0.1, "end": 0.3},
                {"text": "你", "start": 0.1, "end": 0.3},
            ],
            "non_monotonic_timestamps",
        ),
    ],
)
def test_alignment_rejects_invalid_character_structure(raw, reason):
    with pytest.raises(acoustic_alignment.AlignmentFailure) as error:
        acoustic_alignment.validate_segment_alignment(
            list("得你"),
            raw,
            10.0,
            11.0,
        )
    assert error.value.reason == reason


def test_funasr_adapter_rejects_non_numeric_timestamps(monkeypatch, tmp_path: Path):
    class InvalidTimestampModel:
        def generate(self, **_kwargs):
            return [{"timestamp": [["invalid", 200]]}]

    monkeypatch.setattr(
        acoustic_alignment,
        "_load_model",
        lambda _model_cache_dir: InvalidTimestampModel(),
    )

    with pytest.raises(acoustic_alignment.AlignmentFailure) as error:
        acoustic_alignment.run_funasr_alignment(
            tmp_path / "segment.wav",
            ["得"],
            tmp_path / "models",
        )

    assert error.value.reason == "invalid_timestamp"


def test_alignment_failure_is_diagnostic_and_does_not_raise(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")

    def unavailable(*_args):
        raise acoustic_alignment.AlignmentFailure(
            "runtime_unavailable",
            "runtime missing",
        )

    payload = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        [{"text": "完整句段", "start": 5.0, "end": 6.0}],
        tmp_path,
        tmp_path / "models",
        alignment_runner=unavailable,
        audio_extractor=_fake_extractor,
    )

    assert payload["summary"]["status"] == "unavailable"
    assert payload["segments"][0]["validation"] == {
        "valid": False,
        "reason": "runtime_unavailable",
        "message": "runtime missing",
        "expectedCharacterCount": 4,
        "alignedCharacterCount": 0,
        "confidence": None,
        "fullSegment": True,
        "coarseTokenMappingValid": None,
        "coarseTokenMaxBoundaryDeviationSeconds": None,
        "coarseTokenMaxEscapeSeconds": None,
    }

    recovered = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        [{"text": "完整句段", "start": 5.0, "end": 6.0}],
        tmp_path,
        tmp_path / "models",
        alignment_runner=_monotonic_result,
        audio_extractor=_fake_extractor,
    )
    assert recovered["summary"]["status"] == "completed"
    assert recovered["summary"]["reusedSegmentCount"] == 0
    assert recovered["segments"][0]["validation"]["valid"] is True


def test_alignment_allows_character_times_outside_coarse_asr_token(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")
    segment = {
        "text": "觉得你",
        "start": 10.0,
        "end": 15.0,
        "asrWords": [{"text": "得你", "start": 10.2, "end": 10.6}],
    }

    def runner(*_args):
        return [
            {"text": "觉", "start": 0.1, "end": 0.3},
            {"text": "得", "start": 1.0, "end": 1.2},
            {"text": "你", "start": 3.0, "end": 3.2},
        ]

    payload = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        [segment],
        tmp_path,
        tmp_path / "models",
        alignment_runner=runner,
        audio_extractor=_fake_extractor,
    )

    assert payload["segments"][0]["validation"]["valid"] is True
    assert payload["segments"][0]["validation"]["coarseTokenMappingValid"] is False
    assert payload["segments"][0]["characters"][-1] == {
        "text": "你",
        "start": 13.0,
        "end": 13.2,
    }


def test_alignment_revalidates_structurally_corrupt_valid_cache(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")
    segments = [{"text": "得你", "start": 1.0, "end": 2.0}]
    acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        segments,
        tmp_path,
        tmp_path / "models",
        alignment_runner=_monotonic_result,
        audio_extractor=_fake_extractor,
    )
    sidecar_path = acoustic_alignment.alignment_sidecar_path(tmp_path)
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["segments"][0]["characters"] = []
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    calls: list[str] = []

    def runner(audio, reference, cache_dir):
        calls.append("".join(reference))
        return _monotonic_result(audio, reference, cache_dir)

    recovered = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        segments,
        tmp_path,
        tmp_path / "models",
        alignment_runner=runner,
        audio_extractor=_fake_extractor,
    )

    assert calls == ["得你"]
    assert recovered["summary"]["reusedSegmentCount"] == 0
    assert len(recovered["segments"][0]["characters"]) == 2


def test_alignment_lazily_fills_only_requested_segments(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")
    segments = [
        {"text": "第一句", "start": 0.0, "end": 1.0},
        {"text": "第二句", "start": 1.0, "end": 2.0},
    ]
    calls: list[str] = []

    def runner(audio, reference, cache_dir):
        calls.append("".join(reference))
        return _monotonic_result(audio, reference, cache_dir)

    partial = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        segments,
        tmp_path,
        tmp_path / "models",
        alignment_runner=runner,
        audio_extractor=_fake_extractor,
        segment_indexes={1},
    )
    completed = acoustic_alignment.ensure_acoustic_alignment_cache(
        media_path,
        segments,
        tmp_path,
        tmp_path / "models",
        alignment_runner=runner,
        audio_extractor=_fake_extractor,
        segment_indexes={0},
    )

    assert calls == ["第二句", "第一句"]
    assert partial["summary"] == {
        "status": "partial",
        "segmentCount": 1,
        "totalSegmentCount": 2,
        "validSegmentCount": 1,
        "reusedSegmentCount": 0,
    }
    assert completed["summary"]["status"] == "completed"
    assert completed["summary"]["validSegmentCount"] == 2
    assert completed["summary"]["reusedSegmentCount"] == 1


def test_alignment_serializes_same_sidecar_in_process(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source-media")
    segments = [{"text": "得你", "start": 1.0, "end": 2.0}]
    calls: list[str] = []

    def runner(audio, reference, cache_dir):
        calls.append("".join(reference))
        time.sleep(0.05)
        return _monotonic_result(audio, reference, cache_dir)

    def ensure():
        return acoustic_alignment.ensure_acoustic_alignment_cache(
            media_path,
            segments,
            tmp_path,
            tmp_path / "models",
            alignment_runner=runner,
            audio_extractor=_fake_extractor,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: ensure(), range(2)))

    assert calls == ["得你"]
    assert sorted(item["summary"]["reusedSegmentCount"] for item in results) == [0, 1]
