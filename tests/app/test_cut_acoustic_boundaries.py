from __future__ import annotations

import copy
from array import array
from pathlib import Path

import pytest

import server.app as app_module


def test_shared_acoustic_boundary_removes_tail_inside_raw_ge_yi_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * (sample_rate * 2)
    valley_start = round(0.64 * sample_rate)
    valley_end = round(0.68 * sample_rate)
    samples[valley_start:valley_end] = array("h", [0]) * (
        valley_end - valley_start
    )
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: samples,
    )
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 1.2,
            "text": "一起给一起给",
            "words": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给", "start": 0.4, "end": 0.6},
                {"text": "一起", "start": 0.6, "end": 1.0},
                {"text": "给", "start": 1.0, "end": 1.2},
            ],
            "asrWords": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给一", "start": 0.4, "end": 0.8},
                {"text": "起给", "start": 0.8, "end": 1.2},
            ],
        }
    ]

    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        media_path,
        [
            {
                "key": "0.000-0.600",
                "start": 0.0,
                "end": 0.6,
                "originalStart": 0.0,
                "originalEnd": 0.6,
            }
        ],
        segments,
        2.0,
    )[0]

    assert aligned["start"] == 0.0
    assert 0.64 <= aligned["end"] <= 0.68
    assert aligned["end"] < 0.7
    assert aligned["originalEnd"] == 0.6
    assert aligned["adjacentSilenceAfter"] == pytest.approx(
        aligned["end"] - 0.6,
        abs=0.001,
    )


def test_shared_acoustic_boundary_removes_tail_inside_raw_de_ni_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [5_000]) * sample_rate
    valley_start = round(0.42 * sample_rate)
    valley_end = round(0.46 * sample_rate)
    samples[valley_start:valley_end] = array("h", [0]) * (
        valley_end - valley_start
    )
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: samples,
    )
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 0.6,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.18},
                {"text": "得你", "start": 0.18, "end": 0.6},
            ],
        }
    ]

    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        media_path,
        [
            {
                "key": "0.000-0.400",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        segments,
        1.0,
    )[0]

    assert 0.42 <= aligned["end"] <= 0.46
    assert aligned["end"] < 0.495
    assert aligned["originalEnd"] == 0.4


@pytest.mark.parametrize("amplitude", [0, 240, 4_000])
def test_shared_acoustic_boundary_requires_a_meaningful_valley(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    amplitude: int,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [amplitude]) * sample_rate
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: samples,
    )
    segments = [
        {
            "start": 0.0,
            "end": 0.6,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.18},
                {"text": "得你", "start": 0.18, "end": 0.6},
            ],
        }
    ]

    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        media_path,
        [
            {
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        segments,
        1.0,
    )[0]

    assert aligned["start"] == 0.0
    assert aligned["end"] == 0.4
    assert aligned["adjacentSilenceAfter"] == 0.0


def test_shared_acoustic_boundary_rejects_mismatched_asr_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [5_000]) * sample_rate
    valley_start = round(0.42 * sample_rate)
    valley_end = round(0.46 * sample_rate)
    samples[valley_start:valley_end] = array("h", [0]) * (
        valley_end - valley_start
    )
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: samples,
    )
    segments = [
        {
            "start": 0.0,
            "end": 0.6,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.18},
                {"text": "得他", "start": 0.18, "end": 0.6},
            ],
        }
    ]

    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        media_path,
        [
            {
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        segments,
        1.0,
    )[0]

    assert aligned["start"] == 0.0
    assert aligned["end"] == 0.4


def test_shared_acoustic_boundary_only_moves_in_the_deletion_direction():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    segments = [
        {
            "start": 0.0,
            "end": 0.8,
            "text": "删留",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "留", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [{"text": "删留", "start": 0.0, "end": 0.8}],
        }
    ]

    end_samples = array("h", [6_000]) * sample_rate
    for valley_start, valley_end, amplitude in (
        (0.27, 0.33, 0),
        (0.47, 0.53, 700),
    ):
        first = round(valley_start * sample_rate)
        last = round(valley_end * sample_rate)
        end_samples[first:last] = array("h", [amplitude]) * (last - first)
    end_target = app_module.build_shared_acoustic_delete_boundaries(
        segments,
        [{"start": 0.0, "end": 0.4}],
        1.0,
        end_samples,
        sample_rate,
    )[0]

    start_samples = array("h", [6_000]) * sample_rate
    for valley_start, valley_end, amplitude in (
        (0.27, 0.33, 700),
        (0.47, 0.53, 0),
    ):
        first = round(valley_start * sample_rate)
        last = round(valley_end * sample_rate)
        start_samples[first:last] = array("h", [amplitude]) * (last - first)
    start_target = app_module.build_shared_acoustic_delete_boundaries(
        segments,
        [{"start": 0.4, "end": 0.8}],
        1.0,
        start_samples,
        sample_rate,
    )[0]

    assert 0.47 <= end_target["end"] <= 0.53
    assert end_target["end"] >= 0.4
    assert 0.27 <= start_target["start"] <= 0.33
    assert start_target["start"] <= 0.4


@pytest.mark.parametrize(
    ("delete_range", "boundary_key", "valley_start", "valley_end"),
    [
        ({"start": 0.0, "end": 0.4}, "end", 0.47, 0.53),
        ({"start": 0.4, "end": 0.8}, "start", 0.27, 0.33),
    ],
)
def test_shared_acoustic_boundary_is_stable_across_non_clipping_gain(
    delete_range: dict[str, float],
    boundary_key: str,
    valley_start: float,
    valley_end: float,
):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    segments = [
        {
            "start": 0.0,
            "end": 0.8,
            "text": "删留",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "留", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [{"text": "删留", "start": 0.0, "end": 0.8}],
        }
    ]

    boundaries = []
    for gain in (1, 2, 4):
        samples = array("h", [240 * gain]) * sample_rate
        first = round(valley_start * sample_rate)
        last = round(valley_end * sample_rate)
        samples[first:last] = array("h", [20 * gain]) * (last - first)
        target = app_module.build_shared_acoustic_delete_boundaries(
            segments,
            [delete_range],
            1.0,
            samples,
            sample_rate,
        )[0]
        boundaries.append(target[boundary_key])

    assert max(boundaries) - min(boundaries) <= (
        app_module.CUT_BOUNDARY_STEP_SECONDS + 0.001
    )
    if boundary_key == "end":
        assert 0.47 <= boundaries[0] <= 0.53
        assert all(0.4 <= boundary <= 0.6 for boundary in boundaries)
    else:
        assert 0.27 <= boundaries[0] <= 0.33
        assert all(0.2 <= boundary <= 0.4 for boundary in boundaries)


def test_ai_suggestion_and_cut_draft_share_low_volume_acoustic_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [240]) * sample_rate
    first = round(0.54 * sample_rate)
    last = round(0.66 * sample_rate)
    samples[first:last] = array("h", [20]) * (last - first)
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: samples,
    )
    segments = [
        {
            "start": 0.0,
            "end": 0.8,
            "text": "删留",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "留", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [{"text": "删留", "start": 0.0, "end": 0.8}],
        }
    ]
    suggestions = [
        {
            "id": "delete-first-character",
            "type": "口误",
            "text": "删",
            "start": 0.0,
            "end": 0.4,
            "ranges": [{"start": 0.0, "end": 0.4}],
        }
    ]

    suggestion_range = app_module.snap_suggestion_ranges_to_audio(
        segments,
        suggestions,
        1.0,
        samples,
    )[0]["ranges"][0]
    draft_range = app_module.align_cut_draft_text_ranges_to_audio(
        media_path,
        [
            {
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        segments,
        1.0,
    )[0]

    assert suggestion_range["start"] == draft_range["start"] == 0.0
    assert suggestion_range["end"] == draft_range["end"]
    assert draft_range["end"] == 0.6
    assert suggestion_range["originalEnd"] == draft_range["originalEnd"] == 0.4


def test_shared_acoustic_boundary_rejects_character_center_on_monotonic_slope():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    segments = [
        {
            "start": 0.0,
            "end": 0.8,
            "text": "删留",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "留", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [{"text": "删留", "start": 0.0, "end": 0.8}],
        }
    ]

    first = round(0.4 * sample_rate)
    last = round(0.6 * sample_rate)
    falling = [
        round(300 - 275 * index / (last - first - 1))
        for index in range(last - first)
    ]
    first = round(0.2 * sample_rate)
    last = round(0.4 * sample_rate)
    rising = [
        round(25 + 275 * index / (last - first - 1))
        for index in range(last - first)
    ]

    for gain in (1, 4, 16, 64):
        end_samples = array("h", [300 * gain]) * sample_rate
        first = round(0.4 * sample_rate)
        last = round(0.6 * sample_rate)
        end_samples[first:last] = array(
            "h", (amplitude * gain for amplitude in falling)
        )
        end_target = app_module.build_shared_acoustic_delete_boundaries(
            segments,
            [{"start": 0.0, "end": 0.4}],
            1.0,
            end_samples,
            sample_rate,
        )[0]

        start_samples = array("h", [300 * gain]) * sample_rate
        first = round(0.2 * sample_rate)
        last = round(0.4 * sample_rate)
        start_samples[first:last] = array(
            "h", (amplitude * gain for amplitude in rising)
        )
        start_target = app_module.build_shared_acoustic_delete_boundaries(
            segments,
            [{"start": 0.4, "end": 0.8}],
            1.0,
            start_samples,
            sample_rate,
        )[0]

        assert end_target["end"] == 0.4
        assert start_target["start"] == 0.4


@pytest.mark.parametrize(
    ("delete_range", "boundary_key", "quiet_start", "quiet_end", "expected"),
    [
        ({"start": 0.0, "end": 0.4}, "end", 0.54, 0.66, 0.6),
        ({"start": 0.4, "end": 0.8}, "start", 0.14, 0.26, 0.2),
    ],
)
def test_shared_acoustic_directional_endpoint_is_stable_across_gain(
    delete_range: dict[str, float],
    boundary_key: str,
    quiet_start: float,
    quiet_end: float,
    expected: float,
):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    segments = [
        {
            "start": 0.0,
            "end": 0.8,
            "text": "删留",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "留", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [{"text": "删留", "start": 0.0, "end": 0.8}],
        }
    ]

    boundaries = []
    for gain in (1, 4, 16, 32, 64):
        samples = array("h", [240 * gain]) * sample_rate
        first = round(quiet_start * sample_rate)
        last = round(quiet_end * sample_rate)
        samples[first:last] = array("h", [20 * gain]) * (last - first)
        target = app_module.build_shared_acoustic_delete_boundaries(
            segments,
            [delete_range],
            1.0,
            samples,
            sample_rate,
        )[0]
        boundaries.append(target[boundary_key])

    assert boundaries == [expected] * len(boundaries)


def test_shared_acoustic_boundary_reaches_true_pause_inside_adjacent_token():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    segments = [
        {
            "start": 0.2,
            "end": 0.9,
            "text": "尾在",
            "words": [
                {"text": "尾", "start": 0.2, "end": 0.6},
                {"text": "在", "start": 0.6, "end": 0.9},
            ],
            "asrWords": [
                {"text": "尾", "start": 0.2, "end": 0.6},
                {"text": "在", "start": 0.6, "end": 0.9},
            ],
        }
    ]

    boundaries = []
    for gain in (1, 4, 16, 64):
        samples = array("h", [240 * gain]) * sample_rate
        quiet_start = round(0.28 * sample_rate)
        quiet_end = round(0.40 * sample_rate)
        samples[quiet_start:quiet_end] = array("h", [10 * gain]) * (
            quiet_end - quiet_start
        )
        relative_valley_start = round(0.48 * sample_rate)
        relative_valley_end = round(0.54 * sample_rate)
        samples[relative_valley_start:relative_valley_end] = array(
            "h", [80 * gain]
        ) * (relative_valley_end - relative_valley_start)

        target = app_module.build_shared_acoustic_delete_boundaries(
            segments,
            [{"start": 0.6, "end": 0.9}],
            1.0,
            samples,
            sample_rate,
        )[0]
        boundaries.append(target["start"])
        assert target["end"] == 0.9

    assert max(boundaries) - min(boundaries) <= (
        app_module.CUT_BOUNDARY_STEP_SECONDS + 0.001
    )
    assert all(0.32 <= boundary <= 0.40 for boundary in boundaries)


def test_shared_acoustic_token_extension_requires_quiet_inside_token():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * sample_rate
    quiet_start = round(0.08 * sample_rate)
    quiet_end = round(0.18 * sample_rate)
    samples[quiet_start:quiet_end] = array("h", [0]) * (
        quiet_end - quiet_start
    )
    segments = [
        {
            "start": 0.2,
            "end": 0.9,
            "text": "尾在",
            "words": [
                {"text": "尾", "start": 0.2, "end": 0.6},
                {"text": "在", "start": 0.6, "end": 0.9},
            ],
            "asrWords": [
                {"text": "尾", "start": 0.2, "end": 0.6},
                {"text": "在", "start": 0.6, "end": 0.9},
            ],
        }
    ]

    target = app_module.build_shared_acoustic_delete_boundaries(
        segments,
        [{"start": 0.6, "end": 0.9}],
        1.0,
        samples,
        sample_rate,
    )[0]

    assert target["start"] == 0.6
    assert target["end"] == 0.9


def test_shared_acoustic_delete_end_cannot_reach_pause_after_retained_character():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * sample_rate
    quiet_start = round(0.72 * sample_rate)
    quiet_end = round(0.78 * sample_rate)
    samples[quiet_start:quiet_end] = array("h", [0]) * (
        quiet_end - quiet_start
    )
    segments = [
        {
            "start": 0.0,
            "end": 0.8,
            "text": "删保",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "保", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [
                {"text": "删保", "start": 0.0, "end": 0.8},
            ],
        }
    ]

    target = app_module.build_shared_acoustic_delete_boundaries(
        segments,
        [{"start": 0.0, "end": 0.4}],
        1.0,
        samples,
        sample_rate,
    )[0]

    assert target["start"] == 0.0
    assert target["end"] == 0.4


def test_resolved_draft_preserves_saved_shared_physical_boundary():
    segments = [
        {
            "start": 0.0,
            "end": 0.6,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.18},
                {"text": "得你", "start": 0.18, "end": 0.6},
            ],
        }
    ]
    draft = {
        "textRanges": [
            {
                "key": "0.000-0.400",
                "start": 0.0,
                "end": 0.44,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        "noSpeechRanges": [{"key": "quiet", "start": 0.5, "end": 0.58}],
        "timelineRanges": [],
    }

    assert app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        segments,
        1.0,
    ) == [{"start": 0.0, "end": 0.44}]
    assert app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        segments,
        1.0,
        use_text_semantic_boundaries=True,
    ) == [{"start": 0.0, "end": 0.4}]


def test_media_cut_boundaries_snap_to_waveform_valleys_without_changing_text():
    sample_rate = 16_000
    samples = array("h", [6_000]) * (sample_rate * 2)
    # Both valleys sit outside the primary ASR correction window. High energy
    # at the primary candidates must trigger the guarded extended search.
    for valley in (0.10, 1.60):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)

    requested_ranges = [{"start": 0.5, "end": 1.0}]
    media_ranges = app_module.snap_delete_ranges_to_samples(
        requested_ranges,
        2.0,
        samples,
        sample_rate,
    )

    assert 0.09 <= media_ranges[0]["start"] <= 0.12
    assert 1.58 <= media_ranges[0]["end"] <= 1.61

    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.0,
            "text": "ABC",
            "words": [
                {"text": "A", "start": 0.0, "end": 0.5},
                {"text": "B", "start": 0.5, "end": 1.0},
                {"text": "C", "start": 1.0, "end": 2.0},
            ],
        }
    ]
    output_duration = 2.0 - (
        media_ranges[0]["end"] - media_ranges[0]["start"]
    )
    retained = app_module.build_retained_transcript(
        segments,
        requested_ranges,
        output_duration,
        timeline_delete_ranges=media_ranges,
    )

    assert retained["text"] == "AC"
    assert retained["segments"][0]["words"][0]["text"] == "A"
    assert retained["segments"][0]["words"][1]["text"] == "C"
    assert retained["segments"][0]["words"][0]["end"] == media_ranges[0]["start"]
    assert retained["segments"][0]["words"][1]["start"] == media_ranges[0]["start"]


def test_media_cut_boundaries_can_reach_a_delayed_acoustic_tail_boundary():
    sample_rate = 16_000
    samples = array("h", [6_000]) * (sample_rate * 2)
    for valley in (0.10, 1.60):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)

    requested_ranges = [{"start": 0.5, "end": 1.0}]
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.0,
            "text": "保留删除保留",
            "words": [
                {"text": "保留", "start": 0.0, "end": 0.5},
                {"text": "删除", "start": 0.5, "end": 1.0},
                {"text": "保留", "start": 1.0, "end": 2.0},
            ],
        }
    ]
    boundary_limits = app_module.build_transcript_delete_boundary_limits(
        segments,
        requested_ranges,
        2.0,
        end_tail_guard_seconds=app_module.CUT_END_TAIL_GUARD_SECONDS,
    )

    media_ranges = app_module.snap_delete_ranges_to_samples(
        requested_ranges,
        2.0,
        samples,
        sample_rate,
        boundary_limits=boundary_limits,
    )
    retained = app_module.build_retained_transcript(
        segments,
        requested_ranges,
        0.9,
        timeline_delete_ranges=media_ranges,
    )

    assert boundary_limits == [{"start": 0.5, "end": 1.75}]
    assert media_ranges[0]["start"] == requested_ranges[0]["start"]
    assert 1.58 <= media_ranges[0]["end"] <= 1.62
    assert retained["text"] == "保留保留"
    assert all(
        word["end"] > word["start"]
        for word in retained["segments"][0]["words"]
    )


def test_media_cut_boundaries_extend_to_remove_a_high_energy_word_tail():
    sample_rate = 16_000
    samples = array("h", [6_000]) * (sample_rate * 3)
    for valley in (1.12, 2.14):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)

    requested_ranges = [{"start": 1.0, "end": 2.0}]
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 3.0,
            "text": "保留删除保留",
            "words": [
                {"text": "保留", "start": 0.0, "end": 1.0},
                {"text": "删除", "start": 1.0, "end": 2.0},
                {"text": "保留", "start": 2.0, "end": 3.0},
            ],
        }
    ]
    boundary_limits = app_module.build_transcript_delete_boundary_limits(
        segments,
        requested_ranges,
        3.0,
        end_tail_guard_seconds=app_module.CUT_END_TAIL_GUARD_SECONDS,
    )
    media_ranges = app_module.snap_delete_ranges_to_samples(
        requested_ranges,
        3.0,
        samples,
        sample_rate,
        boundary_limits=boundary_limits,
    )

    assert boundary_limits == [{"start": 1.0, "end": 2.75}]
    assert media_ranges[0]["start"] == requested_ranges[0]["start"]
    assert 2.12 <= media_ranges[0]["end"] <= 2.16
    assert media_ranges[0]["end"] >= requested_ranges[0]["end"]


def test_media_cut_boundaries_extend_a_quietly_recorded_word_tail():
    sample_rate = 16_000
    samples = array("h", [30]) * (sample_rate * 3)
    speech_start = round(1.7 * sample_rate)
    speech_end = round(2.04 * sample_rate)
    samples[speech_start:speech_end] = array("h", [80]) * (
        speech_end - speech_start
    )

    media_ranges = app_module.snap_delete_ranges_to_samples(
        [{"start": 1.0, "end": 2.0}],
        3.0,
        samples,
        sample_rate,
        boundary_limits=[{"start": 1.0, "end": 2.75}],
    )

    assert media_ranges[0]["start"] == 1.0
    assert media_ranges[0]["end"] > 2.04


def test_ai_suggestion_ranges_do_not_extend_into_next_retained_word():
    sample_rate = 16_000
    samples = array("h", [6_000]) * (sample_rate * 3)
    for valley in (1.12, 2.14):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)

    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 3.0,
            "text": "保留删除保留",
            "words": [
                {"text": "保留", "start": 0.0, "end": 1.0},
                {"text": "删除", "start": 1.0, "end": 2.0},
                {"text": "保留", "start": 2.0, "end": 3.0},
            ],
        }
    ]
    suggestions = [
        {
            "id": "suggestion-1-1",
            "type": "重复",
            "reason": "检测到相邻内容重复，保留后一次表达",
            "confidence": 0.99,
            "text": "删除",
            "start": 1.0,
            "end": 2.0,
            "ranges": [{"start": 1.0, "end": 2.0}],
        }
    ]

    # A quiet valley at 2.14 sits inside the retained "保留" (2.0-3.0). A
    # suggestion must never extend past the next retained word's start (2.0),
    # otherwise the cut would swallow a kept character (e.g. "你身边..." would
    # become "身边...").
    snapped = app_module.snap_suggestion_ranges_to_audio(
        segments,
        suggestions,
        3.0,
        samples,
    )
    assert snapped[0]["start"] == suggestions[0]["start"]
    assert snapped[0]["end"] == suggestions[0]["end"]
    assert snapped[0]["ranges"][0]["start"] == snapped[0]["start"]
    assert snapped[0]["ranges"][0]["end"] == snapped[0]["end"]

    # Without decoded audio the suggestion must pass through unchanged so the
    # ASR ranges remain usable even when boundary analysis is unavailable.
    unchanged = app_module.snap_suggestion_ranges_to_audio(
        segments,
        suggestions,
        3.0,
        None,
    )
    assert unchanged == suggestions


def test_suggestion_snapping_does_not_follow_raw_de_ni_token_into_ni():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * (sample_rate * 2)
    valley_start = round(0.53 * sample_rate)
    valley_end = round(0.57 * sample_rate)
    samples[valley_start:valley_end] = array("h", [0]) * (
        valley_end - valley_start
    )
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 0.6,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.2},
                {"text": "得你", "start": 0.2, "end": 0.6},
            ],
        }
    ]
    suggestions = [
        {
            "id": "delete-jue-de",
            "type": "口误",
            "text": "觉得",
            "start": 0.0,
            "end": 0.4,
            "ranges": [{"start": 0.0, "end": 0.4}],
        }
    ]

    limits = app_module.build_transcript_delete_boundary_limits(
        segments,
        suggestions[0]["ranges"],
        2.0,
    )
    snapped = app_module.snap_suggestion_ranges_to_audio(
        segments,
        suggestions,
        2.0,
        samples,
    )

    assert limits == [{"start": 0.0, "end": 0.4}]
    assert snapped[0]["ranges"] == [
        {
            "start": 0.0,
            "end": 0.4,
            "originalStart": 0.0,
            "originalEnd": 0.4,
        }
    ]
    assert snapped[0]["end"] == 0.4


def test_suggestion_snapping_does_not_merge_across_short_retained_character():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * sample_rate
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 0.8,
            "text": "删短删",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "短", "start": 0.4, "end": 0.48},
                {"text": "删", "start": 0.48, "end": 0.8},
            ],
            "asrWords": [{"text": "删短删", "start": 0.0, "end": 0.8}],
        }
    ]
    suggestions = [
        {
            "id": "delete-around-short-character",
            "type": "重复",
            "text": "删删",
            "start": 0.0,
            "end": 0.8,
            "ranges": [
                {"start": 0.0, "end": 0.4},
                {"start": 0.48, "end": 0.8},
            ],
        }
    ]

    snapped = app_module.snap_suggestion_ranges_to_audio(
        segments,
        suggestions,
        1.0,
        samples,
    )

    assert snapped[0]["ranges"] == [
        {
            "start": 0.0,
            "end": 0.4,
            "originalStart": 0.0,
            "originalEnd": 0.4,
        },
        {
            "start": 0.48,
            "end": 0.8,
            "originalStart": 0.48,
            "originalEnd": 0.8,
        },
    ]


def test_shared_acoustic_boundaries_preserve_short_retained_character_core():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * sample_rate
    for valley_start, valley_end in ((0.33, 0.37), (0.50, 0.54)):
        first = round(valley_start * sample_rate)
        last = round(valley_end * sample_rate)
        samples[first:last] = array("h", [0]) * (last - first)
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 0.8,
            "text": "删短删",
            "words": [
                {"text": "删", "start": 0.0, "end": 0.4},
                {"text": "短", "start": 0.4, "end": 0.48},
                {"text": "删", "start": 0.48, "end": 0.8},
            ],
            "asrWords": [{"text": "删短删", "start": 0.0, "end": 0.8}],
        }
    ]
    suggestions = [
        {
            "id": "delete-around-short-character-with-valleys",
            "type": "重复",
            "text": "删删",
            "start": 0.0,
            "end": 0.8,
            "ranges": [
                {"start": 0.0, "end": 0.4},
                {"start": 0.48, "end": 0.8},
            ],
        }
    ]

    snapped = app_module.snap_suggestion_ranges_to_audio(
        segments,
        suggestions,
        1.0,
        samples,
    )[0]["ranges"]

    assert snapped[0]["end"] == 0.4
    assert snapped[1]["start"] == 0.48
    assert snapped[0]["end"] < snapped[1]["start"]


def test_ai_suggestion_ranges_remove_gap_tail_without_crossing_next_word():
    sample_rate = 16_000
    samples = array("h", [4_000]) * (sample_rate * 3)
    for valley in (0.9, 1.6):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)

    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.8,
            "text": "保留删除保留",
            "words": [
                {"text": "保留", "start": 0.0, "end": 0.9},
                {"text": "删除", "start": 1.0, "end": 1.5},
                {"text": "保留", "start": 1.8, "end": 2.8},
            ],
            "asrWords": [
                {"text": "保留", "start": 0.0, "end": 0.9},
                {"text": "删除", "start": 1.0, "end": 1.5},
                {"text": "保留", "start": 1.8, "end": 2.8},
            ],
        }
    ]
    suggestions = [
        {
            "id": "suggestion-1-1",
            "type": "重复",
            "reason": "检测到相邻内容重复，保留后一次表达",
            "confidence": 0.99,
            "text": "删除",
            "start": 1.0,
            "end": 1.5,
            "ranges": [{"start": 1.0, "end": 1.5}],
        }
    ]

    # The deleted word's ASR end (1.5) leaves a gap before the retained word
    # (1.8). A quiet valley at 1.6 in that gap removes the residual tail, but
    # the end must stay before the next retained word's start (1.8).
    snapped = app_module.snap_suggestion_ranges_to_audio(
        segments,
        suggestions,
        2.8,
        samples,
    )
    assert 1.55 <= snapped[0]["end"] <= 1.8
    assert snapped[0]["end"] >= suggestions[0]["end"]
    assert snapped[0]["end"] < 1.8


def test_media_cut_boundaries_extend_back_to_remove_an_early_word_head():
    sample_rate = 16_000
    samples = array("h", [6_000]) * (sample_rate * 3)
    for valley in (0.78, 2.0):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)

    requested_ranges = [{"start": 1.0, "end": 2.0}]
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 3.0,
            "text": "保留删除保留",
            "words": [
                {"text": "保留", "start": 0.0, "end": 1.0},
                {"text": "删除", "start": 1.0, "end": 2.0},
                {"text": "保留", "start": 2.0, "end": 3.0},
            ],
        }
    ]
    boundary_limits = app_module.build_transcript_delete_boundary_limits(
        segments,
        requested_ranges,
        3.0,
        start_head_guard_seconds=app_module.CUT_START_HEAD_GUARD_SECONDS,
    )
    media_ranges = app_module.snap_delete_ranges_to_samples(
        requested_ranges,
        3.0,
        samples,
        sample_rate,
        boundary_limits=boundary_limits,
    )

    assert boundary_limits == [{"start": 0.5, "end": 2.0}]
    assert 0.76 <= media_ranges[0]["start"] <= 0.8
    assert media_ranges[0]["start"] <= requested_ranges[0]["start"]
    assert media_ranges[0]["end"] == requested_ranges[0]["end"]


def test_media_cut_boundaries_leave_an_already_quiet_word_end_unchanged():
    sample_rate = 16_000
    samples = array("h", [6_000]) * (sample_rate * 2)
    for valley in (1.0, 1.2):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)

    requested_ranges = [{"start": 0.5, "end": 1.0}]
    boundary_limits = [{"start": 0.5, "end": 1.3}]
    media_ranges = app_module.snap_delete_ranges_to_samples(
        requested_ranges,
        2.0,
        samples,
        sample_rate,
        boundary_limits=boundary_limits,
    )

    assert media_ranges == requested_ranges


def test_audio_quiet_ranges_detect_pause_hidden_inside_asr_word_block():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000]) * (sample_rate * 4)
    quiet_start = round(1.0 * sample_rate)
    quiet_end = round(3.2 * sample_rate)
    samples[quiet_start:quiet_end] = array("h", [0]) * (quiet_end - quiet_start)

    ranges = app_module.detect_audio_quiet_ranges(samples, 4.0)

    assert ranges == [{"start": 1.0, "end": 3.2}]
    suggestions = app_module.detect_no_speech_ranges(
        [
            {
                "start": 0.0,
                "end": 4.0,
                "text": "你身边人人都觉得",
                "words": [{"text": "你身边人人都觉得", "start": 0.0, "end": 4.0}],
            }
        ],
        4.0,
        samples,
    )
    assert [(item["start"], item["end"], item["audioState"]) for item in suggestions] == [
        (1.2, 3.0, "quiet")
    ]


def test_retained_transcript_maps_audio_quiet_ranges_to_edited_timeline():
    transcript = app_module.build_retained_transcript(
        [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "保留内容",
                "words": [{"text": "保留内容", "start": 1.0, "end": 5.0}],
            }
        ],
        [],
        4.0,
        timeline_delete_ranges=[{"start": 0.0, "end": 1.0}],
        audio_quiet_ranges=[{"start": 2.0, "end": 3.5}],
    )

    assert transcript["audioQuietRanges"] == [{"start": 1.0, "end": 2.5}]


def _forced_de_ni_alignment_cache() -> dict[str, object]:
    return {
        "segments": [
            {
                "segmentIndex": 0,
                "validation": {
                    "valid": True,
                    "coarseTokenMaxBoundaryDeviationSeconds": 2.4,
                },
                "characters": [
                    {"text": "觉", "start": 0.05, "end": 0.18},
                    {"text": "得", "start": 0.2, "end": 0.5},
                    {"text": "你", "start": 0.8, "end": 0.98},
                ],
            }
        ]
    }


def _de_ni_segments() -> list[dict[str, object]]:
    return [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.18},
                {"text": "得你", "start": 0.18, "end": 0.6},
            ],
        }
    ]


def _repeated_de_ni_segments() -> list[dict[str, object]]:
    deleted_text = "你身边你身边人人都觉得"
    retained_text = "你身边人人都觉得一个月赚一万"
    return [
        {
            "start": 33.16,
            "end": 47.12,
            "text": deleted_text + retained_text,
            "words": [
                {"text": deleted_text, "start": 33.16, "end": 37.12},
                {"text": retained_text, "start": 37.12, "end": 47.12},
            ],
            "asrWords": [
                {"text": deleted_text, "start": 33.16, "end": 37.12},
                {"text": retained_text, "start": 37.12, "end": 47.12},
            ],
        }
    ]


def _repeated_de_ni_alignment_cache() -> dict[str, object]:
    text = "你身边你身边人人都觉得你身边人人都觉得一个月赚一万"
    characters: list[dict[str, object]] = []
    for index, character in enumerate(text):
        if index < 10:
            start = 33.20 + index * 0.435
            end = start + 0.40
        elif index == 10:
            start, end = 37.55, 37.791
        elif index == 11:
            start, end = 39.85, 40.05
        else:
            start = 40.05 + (index - 12) * 0.30
            end = start + 0.28
        characters.append(
            {"text": character, "start": round(start, 3), "end": round(end, 3)}
        )
    return {
        "segments": [
            {
                "segmentIndex": 0,
                "validation": {
                    "valid": True,
                    "coarseTokenMaxBoundaryDeviationSeconds": 2.4,
                },
                "characters": characters,
            }
        ]
    }


def _repeated_de_ni_gap_samples(gain: int = 1) -> array:
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000 * gain]) * round(47.5 * sample_rate)
    quiet_start = round(37.70 * sample_rate)
    quiet_end = round(39.85 * sample_rate)
    samples[quiet_start:quiet_end] = array("h", [20 * gain]) * (
        quiet_end - quiet_start
    )
    return samples


def _cross_segment_segments(
    *,
    deleted_end: float = 0.4,
    retained_start: float = 0.8,
    deleted_text: str = "删",
    retained_text: str = "留",
) -> list[dict[str, object]]:
    return [
        {
            "start": 0.0,
            "end": deleted_end,
            "text": deleted_text,
            "words": [{"text": deleted_text, "start": 0.0, "end": deleted_end}],
            "asrWords": [{"text": deleted_text, "start": 0.0, "end": deleted_end}],
        },
        {
            "start": retained_start,
            "end": 1.2,
            "text": retained_text,
            "words": [
                {"text": retained_text, "start": retained_start, "end": 1.2}
            ],
            "asrWords": [
                {"text": retained_text, "start": retained_start, "end": 1.2}
            ],
        },
    ]


def _cross_segment_alignment_cache(
    *,
    deleted_end: float = 0.68,
    retained_start: float = 0.74,
    deleted_text: str = "删",
    retained_text: str = "留",
) -> dict[str, object]:
    return {
        "segments": [
            {
                "segmentIndex": 0,
                "validation": {"valid": True},
                "characters": [
                    {"text": deleted_text, "start": 0.05, "end": deleted_end}
                ],
            },
            {
                "segmentIndex": 1,
                "validation": {"valid": True},
                "characters": [
                    {"text": retained_text, "start": retained_start, "end": 1.1}
                ],
            },
        ]
    }


def _cross_segment_delayed_tail_samples() -> array:
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000]) * round(1.2 * sample_rate)
    for start, end, amplitude in (
        (0.32, 0.43, 100),
        (0.43, 0.58, 3_000),
        (0.58, 0.65, 100),
    ):
        start_index = round(start * sample_rate)
        end_index = round(end * sample_rate)
        samples[start_index:end_index] = array("h", [amplitude]) * (
            end_index - start_index
        )
    return samples


def _cross_segment_early_head_samples() -> array:
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000]) * round(1.2 * sample_rate)
    valley_start = round(0.55 * sample_rate)
    valley_end = round(0.63 * sample_rate)
    samples[valley_start:valley_end] = array("h", [100]) * (
        valley_end - valley_start
    )
    return samples


def _forced_deleted_head_segments() -> list[dict[str, object]]:
    return [
        {
            "start": 0.0,
            "end": 1.2,
            "text": "人一留",
            "words": [
                {"text": "人", "start": 0.0, "end": 0.85},
                {"text": "一", "start": 0.85, "end": 1.0},
                {"text": "留", "start": 1.0, "end": 1.2},
            ],
            "asrWords": [
                {"text": "人", "start": 0.0, "end": 0.85},
                {"text": "一", "start": 0.85, "end": 1.0},
                {"text": "留", "start": 1.0, "end": 1.2},
            ],
        }
    ]


def _forced_deleted_head_alignment_cache() -> dict[str, object]:
    return {
        "segments": [
            {
                "segmentIndex": 0,
                "validation": {"valid": True},
                "characters": [
                    {"text": "人", "start": 0.05, "end": 0.5},
                    {"text": "一", "start": 0.8, "end": 0.95},
                    {"text": "留", "start": 0.97, "end": 1.15},
                ],
            }
        ]
    }


def _forced_deleted_head_samples(gain: int = 1) -> array:
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000 * gain]) * round(1.2 * sample_rate)
    quiet_start = round(0.5 * sample_rate)
    deleted_attack = round(0.75 * sample_rate)
    samples[quiet_start:deleted_attack] = array("h", [20 * gain]) * (
        deleted_attack - quiet_start
    )
    return samples


@pytest.mark.parametrize("gain", [1, 2, 4])
def test_forced_delete_start_clears_early_deleted_head_for_text_and_timeline(
    gain: int,
):
    samples = _forced_deleted_head_samples(gain)
    diagnostics: list[dict[str, object]] = []
    forced_boundary_cache = {}
    text_range = {
        "key": f"forced-deleted-head-text-{gain}",
        "start": 0.85,
        "end": 1.0,
        "originalStart": 0.85,
        "originalEnd": 1.0,
    }
    timeline_range = {
        **text_range,
        "key": f"forced-deleted-head-timeline-{gain}",
    }

    aligned_text = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [text_range],
        _forced_deleted_head_segments(),
        1.2,
        alignment_cache=_forced_deleted_head_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
        forced_boundary_cache=forced_boundary_cache,
    )[0]
    aligned_timeline = app_module.align_cut_draft_timeline_ranges_to_audio(
        [timeline_range],
        _forced_deleted_head_segments(),
        1.2,
        alignment_cache=_forced_deleted_head_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
        forced_boundary_cache=forced_boundary_cache,
    )[0]

    assert 0.735 <= aligned_text["start"] <= 0.75
    assert aligned_timeline["start"] == aligned_text["start"]
    assert aligned_text["originalStart"] == 0.85
    assert aligned_timeline["originalStart"] == 0.85
    text_diagnostic = next(
        item
        for item in diagnostics
        if item.get("direction") == "delete_start"
        and item.get("entryType") != "timeline"
    )
    timeline_diagnostic = next(
        item
        for item in diagnostics
        if item.get("endpoint") == "start"
        and item.get("entryType") == "timeline"
    )
    for diagnostic in (text_diagnostic, timeline_diagnostic):
        assert diagnostic["forcedCandidate"] == 0.8
        assert diagnostic["final"] == aligned_text["start"]
        assert diagnostic["retainedSpeechHardLimit"] == 0.5
        assert diagnostic["pcmCorroborated"] is True
        assert diagnostic["pcmValleyStart"] is not None
        assert diagnostic["pcmValleyEnd"] is not None
        assert diagnostic["pcmValleyEnd"] <= diagnostic["pcmAttackStart"] <= 0.8
        assert diagnostic["pcmAdjustment"] < 0.0
        assert diagnostic["trustReason"] == "forced_deleted_head_pcm_valley"


@pytest.mark.parametrize(
    "shape",
    ["immediate_onset", "brief_dip", "single_point", "monotonic_rise"],
)
def test_forced_delete_start_without_sustained_quiet_keeps_candidate(shape: str):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000]) * round(1.2 * sample_rate)
    if shape == "brief_dip":
        start = round(0.68 * sample_rate)
        end = round(0.685 * sample_rate)
        samples[start:end] = array("h", [20]) * (end - start)
    elif shape == "single_point":
        samples[round(0.68 * sample_rate)] = 0
    elif shape == "monotonic_rise":
        ramp_start = round(0.2 * sample_rate)
        ramp_end = round(0.82 * sample_rate)
        ramp_width = ramp_end - ramp_start
        samples = array(
            "h",
            (
                200
                if index < ramp_start
                else round(
                    200
                    + 3_800
                    * min(1.0, (index - ramp_start) / ramp_width)
                )
                for index in range(round(1.2 * sample_rate))
            ),
        )
        corroborated, evidence = (
            app_module.corroborate_forced_deleted_head_with_pcm(
                0.5,
                0.8,
                samples,
                sample_rate,
            )
        )
        assert corroborated is None
        assert evidence["pcmCorroborated"] is False
    diagnostics: list[dict[str, object]] = []

    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": f"forced-deleted-head-{shape}",
                "start": 0.85,
                "end": 1.0,
                "originalStart": 0.85,
                "originalEnd": 1.0,
            }
        ],
        _forced_deleted_head_segments(),
        1.2,
        alignment_cache=_forced_deleted_head_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
    )[0]

    if shape == "monotonic_rise":
        assert 0.797 <= aligned["start"] <= 0.8
    else:
        assert aligned["start"] == 0.8
    diagnostic = next(
        item for item in diagnostics if item.get("direction") == "delete_start"
    )
    assert diagnostic["retainedSpeechHardLimit"] == 0.5
    assert diagnostic["pcmCorroborated"] is False
    assert diagnostic["trustReason"] == "forced_transition"


def test_forced_delete_start_uses_first_corroborated_attack_after_retained_limit():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000]) * round(1.2 * sample_rate)
    for start, end, amplitude in (
        (0.5, 0.6, 20),
        (0.6, 0.66, 4_000),
        (0.66, 0.7, 20),
    ):
        start_index = round(start * sample_rate)
        end_index = round(end * sample_rate)
        samples[start_index:end_index] = array("h", [amplitude]) * (
            end_index - start_index
        )

    corroborated, evidence = app_module.corroborate_forced_deleted_head_with_pcm(
        0.5,
        0.8,
        samples,
        sample_rate,
    )

    assert corroborated is not None
    assert 0.585 <= corroborated <= 0.6
    assert evidence["pcmAttackStart"] <= 0.605


def test_forced_delete_start_accepts_short_sustained_quiet_corridor():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000]) * round(1.2 * sample_rate)
    quiet_start = round(0.5 * sample_rate)
    quiet_end = round(0.52 * sample_rate)
    samples[quiet_start:quiet_end] = array("h", [20]) * (
        quiet_end - quiet_start
    )

    corroborated, evidence = app_module.corroborate_forced_deleted_head_with_pcm(
        0.5,
        0.8,
        samples,
        sample_rate,
    )

    assert corroborated is not None
    assert 0.505 <= corroborated <= 0.52
    assert evidence["pcmAttackStart"] <= 0.525


@pytest.mark.parametrize("shape", ["uniform_low", "light_noise"])
def test_forced_delete_start_low_energy_without_attack_is_not_corroborated(
    shape: str,
):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    sample_count = round(1.2 * sample_rate)
    if shape == "uniform_low":
        samples = array("h", [200]) * sample_count
    else:
        samples = array(
            "h",
            (200 + ((index // 80) % 5) * 8 for index in range(sample_count)),
        )

    corroborated, evidence = app_module.corroborate_forced_deleted_head_with_pcm(
        0.5,
        0.8,
        samples,
        sample_rate,
    )

    assert corroborated is None
    assert evidence["pcmCorroborated"] is False


def test_full_segment_delete_uses_adjacent_segment_forced_boundary():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "whole-first-segment",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=_cross_segment_alignment_cache(),
        samples=array("h", [3_000])
        * round(1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == 0.68
    assert aligned["originalEnd"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["transitionScope"] == "cross_segment"
    assert diagnostic["structureValid"] is True
    assert diagnostic["boundaryTrustworthy"] is True
    assert diagnostic["trustReason"] == "forced_transition"
    assert diagnostic["retainedSpeechHardLimit"] == 0.74
    assert aligned["end"] < diagnostic["retainedSpeechHardLimit"]


def test_cross_segment_same_character_trusts_non_overlapping_forced_boundary():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "whole-first-segment-same-character",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _cross_segment_segments(deleted_text="啊", retained_text="啊"),
        1.2,
        alignment_cache=_cross_segment_alignment_cache(
            deleted_text="啊",
            retained_text="啊",
        ),
        samples=array("h", [3_000])
        * round(1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == 0.68
    diagnostic = diagnostics[0]
    assert diagnostic["transitionScope"] == "cross_segment"
    assert diagnostic["repeatAmbiguous"] is False
    assert diagnostic["repeatOverlapText"] == ""
    assert diagnostic["boundaryTrustworthy"] is True
    assert diagnostic["trustReason"] == "forced_transition"


def test_full_segment_delete_start_uses_adjacent_segment_forced_boundary():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "whole-second-segment",
                "start": 0.8,
                "end": 1.2,
                "originalStart": 0.8,
                "originalEnd": 1.2,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=_cross_segment_alignment_cache(),
        samples=array("h", [3_000])
        * round(1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE),
        diagnostics=diagnostics,
    )[0]

    assert aligned["start"] == 0.74
    assert aligned["originalStart"] == 0.8
    diagnostic = diagnostics[0]
    assert diagnostic["direction"] == "delete_start"
    assert diagnostic["transitionScope"] == "cross_segment"
    assert diagnostic["boundaryTrustworthy"] is True
    assert diagnostic["trustReason"] == "forced_transition"
    assert diagnostic["retainedSpeechHardLimit"] == 0.68
    assert aligned["start"] > diagnostic["retainedSpeechHardLimit"]


def test_cross_segment_forced_delete_start_does_not_use_deleted_head_pcm():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "cross-segment-forced-delete-start",
                "start": 0.8,
                "end": 1.2,
                "originalStart": 0.8,
                "originalEnd": 1.2,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=_cross_segment_alignment_cache(
            deleted_end=0.5,
            retained_start=0.8,
        ),
        samples=_forced_deleted_head_samples(),
        diagnostics=diagnostics,
    )[0]

    assert aligned["start"] == 0.8
    diagnostic = next(
        item for item in diagnostics if item.get("direction") == "delete_start"
    )
    assert diagnostic["transitionScope"] == "cross_segment"
    assert diagnostic["pcmCorroborated"] is False
    assert diagnostic["trustReason"] == "forced_transition"


def test_full_segment_delete_uses_cross_segment_sustained_pcm_valley():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "whole-first-segment-waveform",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=None,
        samples=_cross_segment_delayed_tail_samples(),
        diagnostics=diagnostics,
    )[0]

    assert 0.58 <= aligned["end"] <= 0.65
    assert aligned["originalEnd"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["transitionScope"] == "cross_segment"
    assert diagnostic["structureValid"] is False
    assert diagnostic["boundaryTrustworthy"] is True
    assert diagnostic["trustReason"] == "cross_segment_pcm_valley"
    assert diagnostic["pcmCorroborated"] is True
    assert aligned["end"] < diagnostic["retainedSpeechHardLimit"]


def test_timeline_full_segment_delete_uses_cross_segment_pcm_without_forced():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "timeline-whole-first-segment-waveform",
                "start": 0.0,
                "end": 0.42,
                "originalStart": 0.0,
                "originalEnd": 0.42,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=None,
        samples=_cross_segment_delayed_tail_samples(),
        diagnostics=diagnostics,
    )[0]

    assert 0.58 <= aligned["end"] <= 0.65
    assert aligned["originalEnd"] == 0.42
    end_diagnostic = next(
        item for item in diagnostics if item.get("endpoint") == "end"
    )
    assert end_diagnostic["transitionScope"] == "cross_segment"
    assert end_diagnostic["boundaryTrustworthy"] is True
    assert end_diagnostic["trustReason"] == "cross_segment_pcm_valley"


def test_full_segment_delete_start_pcm_is_shared_by_text_and_timeline():
    samples = _cross_segment_early_head_samples()
    text_diagnostics: list[dict[str, object]] = []
    aligned_text = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "whole-second-segment-waveform",
                "start": 0.8,
                "end": 1.2,
                "originalStart": 0.8,
                "originalEnd": 1.2,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=None,
        samples=samples,
        diagnostics=text_diagnostics,
    )[0]
    timeline_diagnostics: list[dict[str, object]] = []
    aligned_timeline = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "timeline-whole-second-segment-waveform",
                "start": 0.78,
                "end": 1.2,
                "originalStart": 0.78,
                "originalEnd": 1.2,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=None,
        samples=samples,
        diagnostics=timeline_diagnostics,
    )[0]

    assert 0.55 <= aligned_text["start"] <= 0.63
    assert aligned_text["originalStart"] == 0.8
    assert aligned_timeline["start"] == aligned_text["start"]
    assert aligned_timeline["originalStart"] == 0.78
    text_start = next(
        item for item in text_diagnostics if item.get("direction") == "delete_start"
    )
    timeline_start = next(
        item for item in timeline_diagnostics if item.get("endpoint") == "start"
    )
    for diagnostic in (text_start, timeline_start):
        assert diagnostic["transitionScope"] == "cross_segment"
        assert diagnostic["boundaryTrustworthy"] is True
        assert diagnostic["trustReason"] == "cross_segment_pcm_valley"
        assert diagnostic["pcmCorroborated"] is True
        assert aligned_text["start"] > diagnostic["retainedSpeechHardLimit"]


def test_timeline_range_inside_unaligned_cross_segment_gap_stays_exact():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "timeline-cross-segment-gap",
                "start": 0.5,
                "end": 0.7,
                "originalStart": 0.5,
                "originalEnd": 0.7,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=None,
        samples=_cross_segment_delayed_tail_samples(),
        diagnostics=diagnostics,
    )[0]

    assert aligned["start"] == aligned["originalStart"] == 0.5
    assert aligned["end"] == aligned["originalEnd"] == 0.7
    assert {item["fallbackReason"] for item in diagnostics} == {
        "non_speech_range_exact"
    }


def test_full_segment_delete_without_cross_segment_valley_stays_semantic():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "whole-first-segment-no-valley",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _cross_segment_segments(),
        1.2,
        alignment_cache=None,
        samples=array("h", [300])
        * round(1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == aligned["originalEnd"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["transitionScope"] == "cross_segment"
    assert diagnostic["boundaryTrustworthy"] is False
    assert diagnostic["pcmCorroborated"] is False
    assert diagnostic["fallbackReason"] == "cross_segment_pcm_not_corroborated"


def test_full_segment_delete_does_not_cross_immediate_retained_speech():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "whole-first-segment-overlap",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _cross_segment_segments(retained_start=0.42),
        1.2,
        alignment_cache=_cross_segment_alignment_cache(
            deleted_end=0.58,
            retained_start=0.44,
        ),
        samples=array("h", [4_000])
        * round(1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == aligned["originalEnd"] == 0.4
    assert aligned["end"] <= 0.44
    diagnostic = diagnostics[0]
    assert diagnostic["transitionScope"] == "cross_segment"
    assert diagnostic["boundaryTrustworthy"] is False
    assert diagnostic["forcedFallbackReason"] == "alignment_transition_overlap"
    assert diagnostic["fallbackReason"] == "cross_segment_pcm_not_corroborated"


def test_timeline_cross_segment_snap_uses_trusted_transition_not_final_distance():
    segments = _cross_segment_segments(deleted_end=0.6, retained_start=0.9)
    alignment_cache = _cross_segment_alignment_cache(
        deleted_end=0.85,
        retained_start=0.9,
    )
    samples = array("h", [3_000]) * round(
        1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE
    )

    near_diagnostics: list[dict[str, object]] = []
    near = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "near-semantic-transition",
                "start": 0.0,
                "end": 0.42,
                "originalStart": 0.0,
                "originalEnd": 0.42,
            }
        ],
        segments,
        1.2,
        alignment_cache=alignment_cache,
        samples=samples,
        diagnostics=near_diagnostics,
    )[0]
    far_diagnostics: list[dict[str, object]] = []
    far = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "far-from-semantic-transition",
                "start": 0.0,
                "end": 0.31,
                "originalStart": 0.0,
                "originalEnd": 0.31,
            }
        ],
        segments,
        1.2,
        alignment_cache=alignment_cache,
        samples=samples,
        diagnostics=far_diagnostics,
    )[0]

    assert near["end"] == 0.85
    assert near["end"] - near["originalEnd"] > 0.20
    assert far["end"] == far["originalEnd"] == 0.31
    near_end = next(
        item for item in near_diagnostics if item.get("endpoint") == "end"
    )
    far_end = next(item for item in far_diagnostics if item.get("endpoint") == "end")
    assert near_end["boundaryTrustworthy"] is True
    assert near_end["transitionScope"] == "cross_segment"
    assert near_end["fallbackReason"] is None
    assert far_end["fallbackReason"] == "no_transition_within_snap_distance"


def test_timeline_does_not_snap_when_only_physical_final_is_nearby():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "near-physical-far-semantic",
                "start": 0.0,
                "end": 0.82,
                "originalStart": 0.0,
                "originalEnd": 0.82,
            }
        ],
        _cross_segment_segments(deleted_end=0.6, retained_start=0.9),
        1.2,
        alignment_cache=_cross_segment_alignment_cache(
            deleted_end=0.85,
            retained_start=0.9,
        ),
        samples=array("h", [3_000])
        * round(1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == aligned["originalEnd"] == 0.82
    end_diagnostic = next(
        item for item in diagnostics if item.get("endpoint") == "end"
    )
    assert end_diagnostic["boundaryTrustworthy"] is True
    assert end_diagnostic["forcedCandidate"] == 0.85
    assert end_diagnostic["fallback"] == 0.82
    assert end_diagnostic["final"] == 0.82
    assert end_diagnostic["fallbackReason"] == "no_transition_within_snap_distance"


def test_forced_alignment_uses_deleted_tail_without_consuming_quiet_gap():
    samples = array("h", [4_000]) * app_module.CUT_BOUNDARY_SAMPLE_RATE
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "deleted-ge-de",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _de_ni_segments(),
        1.0,
        alignment_cache=_forced_de_ni_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == 0.5
    assert aligned["end"] < 0.8
    assert diagnostics[0]["alignmentSource"] == "funasr-fa-zh"
    assert diagnostics[0]["retainedSpeechHardLimit"] == 0.8
    assert diagnostics[0]["boundaryTrustworthy"] is True
    assert diagnostics[0]["repeatAmbiguous"] is False
    assert diagnostics[0]["coarseTokenMaxBoundaryDeviationSeconds"] == 2.4
    assert diagnostics[0]["fallbackReason"] is None


def test_repeated_de_ni_forced_gap_is_trusted_by_text_and_timeline():
    resolved_boundaries: list[float] = []
    for gain in (1, 2, 4):
        diagnostics: list[dict[str, object]] = []
        forced_boundary_cache = {}
        samples = _repeated_de_ni_gap_samples(gain)
        text_range = {
            "key": "real-repeat-de-ni-text",
            "start": 33.16,
            "end": 37.12,
            "originalStart": 33.16,
            "originalEnd": 37.12,
        }
        timeline_range = {
            **text_range,
            "key": "real-repeat-de-ni-timeline",
        }

        aligned_text = app_module.align_cut_draft_text_ranges_to_audio(
            Path("unused.mp4"),
            [text_range],
            _repeated_de_ni_segments(),
            47.5,
            alignment_cache=_repeated_de_ni_alignment_cache(),
            samples=samples,
            diagnostics=diagnostics,
            forced_boundary_cache=forced_boundary_cache,
        )[0]
        aligned_timeline = app_module.align_cut_draft_timeline_ranges_to_audio(
            [timeline_range],
            _repeated_de_ni_segments(),
            47.5,
            alignment_cache=_repeated_de_ni_alignment_cache(),
            samples=samples,
            diagnostics=diagnostics,
            forced_boundary_cache=forced_boundary_cache,
        )[0]

        resolved_boundaries.append(aligned_text["end"])
        assert aligned_text["end"] == pytest.approx(37.791, abs=0.001)
        assert aligned_timeline["end"] == aligned_text["end"]
        assert aligned_text["originalEnd"] == 37.12
        assert aligned_timeline["originalEnd"] == 37.12
        diagnostic = diagnostics[0]
        assert diagnostic["structureValid"] is True
        assert diagnostic["repeatAmbiguous"] is True
        assert diagnostic["repeatOverlapText"] == "你身边人人都觉得"
        assert diagnostic["forcedCandidate"] == 37.791
        assert diagnostic["retainedSpeechHardLimit"] == 39.85
        assert diagnostic["boundaryTrustworthy"] is True
        assert diagnostic["trustReason"] == "forced_pcm_gap"
        assert diagnostic["pcmCorroborated"] is False
        assert diagnostic["pcmGapCorroborated"] is True
        assert diagnostic["pcmGapStart"] == 37.791
        assert diagnostic["pcmGapEnd"] == 39.85
        timeline_diagnostic = next(
            item
            for item in diagnostics
            if item.get("entryType") == "timeline" and item.get("endpoint") == "end"
        )
        assert timeline_diagnostic["trustReason"] == "forced_pcm_gap"
        assert timeline_diagnostic["retainedSpeechHardLimit"] == 39.85

    assert max(resolved_boundaries) - min(resolved_boundaries) <= 0.001


def test_forced_quiet_gap_pcm_evidence_is_symmetric_and_gain_independent():
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    for gain in (1, 3):
        samples = array("h", [4_000 * gain]) * (sample_rate * 3)
        quiet_start = round(0.8 * sample_rate)
        quiet_end = round(2.2 * sample_rate)
        samples[quiet_start:quiet_end] = array("h", [20 * gain]) * (
            quiet_end - quiet_start
        )

        delete_end, end_evidence = (
            app_module.corroborate_forced_transition_quiet_gap(
                0.3,
                0.8,
                2.2,
                samples,
                sample_rate,
                deletion_on_left=True,
            )
        )
        delete_start, start_evidence = (
            app_module.corroborate_forced_transition_quiet_gap(
                2.7,
                2.2,
                0.8,
                samples,
                sample_rate,
                deletion_on_left=False,
            )
        )

        assert delete_end == 0.8
        assert delete_start == 2.2
        assert end_evidence["pcmGapCorroborated"] is True
        assert start_evidence["pcmGapCorroborated"] is True
        assert end_evidence["pcmGapStart"] == start_evidence["pcmGapStart"] == 0.8
        assert end_evidence["pcmGapEnd"] == start_evidence["pcmGapEnd"] == 2.2

    uniform = array("h", [300]) * (sample_rate * 3)
    rejected, evidence = app_module.corroborate_forced_transition_quiet_gap(
        0.3,
        0.8,
        2.2,
        uniform,
        sample_rate,
        deletion_on_left=True,
    )
    assert rejected is None
    assert evidence["pcmGapCorroborated"] is False


def _ambiguous_repeat_segments() -> list[dict[str, object]]:
    return [
        {
            "start": 0.0,
            "end": 2.0,
            "text": "所以说啊所以说啊",
            "words": [
                {"text": "所以说啊", "start": 0.0, "end": 0.4},
                {"text": "所以说啊", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [
                {"text": "所以说啊", "start": 0.0, "end": 0.4},
                {"text": "所以说啊", "start": 0.4, "end": 0.8},
            ],
        }
    ]


def _ambiguous_repeat_alignment_cache() -> dict[str, object]:
    return {
        "segments": [
            {
                "segmentIndex": 0,
                "validation": {
                    "valid": True,
                    "coarseTokenMaxBoundaryDeviationSeconds": 0.9,
                },
                "characters": [
                    {"text": "所", "start": 0.05, "end": 0.12},
                    {"text": "以", "start": 0.12, "end": 0.20},
                    {"text": "说", "start": 0.20, "end": 0.30},
                    {"text": "啊", "start": 1.05, "end": 1.30},
                    {"text": "所", "start": 1.30, "end": 1.38},
                    {"text": "以", "start": 1.38, "end": 1.46},
                    {"text": "说", "start": 1.46, "end": 1.58},
                    {"text": "啊", "start": 1.58, "end": 1.72},
                ],
            }
        ]
    }


def _ambiguous_repeat_samples(gain: int = 1) -> array:
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [3_000 * gain]) * (sample_rate * 2)
    valley_start = round(1.08 * sample_rate)
    valley_end = round(1.16 * sample_rate)
    samples[valley_start:valley_end] = array("h", [20 * gain]) * (
        valley_end - valley_start
    )
    return samples


def _wrong_direction_repeat_alignment_cache() -> dict[str, object]:
    cache = _ambiguous_repeat_alignment_cache()
    characters = cache["segments"][0]["characters"]
    characters[3].update({"start": 0.24, "end": 0.32})
    characters[4].update({"start": 1.30, "end": 1.38})
    return cache


def _fallback_repeat_alignment_cache() -> dict[str, object]:
    cache = _wrong_direction_repeat_alignment_cache()
    cache["segments"][0]["characters"][3]["end"] = 0.4
    return cache


def _wrong_direction_repeat_samples(
    gain: int = 1,
    *,
    retained_speech: bool = True,
) -> array:
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [20 * gain]) * (sample_rate * 2)
    for start, end, amplitude in (
        (0.00, 0.68, 3_000),
        (0.82, 0.90, 1_500),
    ):
        first = round(start * sample_rate)
        last = round(end * sample_rate)
        samples[first:last] = array("h", [amplitude * gain]) * (last - first)
    if retained_speech:
        first = round(1.30 * sample_rate)
        last = round(1.72 * sample_rate)
        samples[first:last] = array("h", [3_000 * gain]) * (last - first)
    return samples


def _wrong_direction_repeat_start_alignment_cache() -> dict[str, object]:
    cache = _ambiguous_repeat_alignment_cache()
    characters = cache["segments"][0]["characters"]
    characters[3].update({"start": 0.12, "end": 0.20})
    characters[4].update({"start": 0.50, "end": 0.58})
    return cache


def _wrong_direction_repeat_start_samples(gain: int = 1) -> array:
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [20 * gain]) * (sample_rate * 2)
    retained_end = round(0.20 * sample_rate)
    samples[:retained_end] = array("h", [3_000 * gain]) * retained_end
    burst_start = round(0.31 * sample_rate)
    burst_end = round(0.37 * sample_rate)
    samples[burst_start:burst_end] = array("h", [1_500 * gain]) * (
        burst_end - burst_start
    )
    deleted_start = round(0.50 * sample_rate)
    deleted_end = round(0.90 * sample_rate)
    samples[deleted_start:deleted_end] = array("h", [3_000 * gain]) * (
        deleted_end - deleted_start
    )
    return samples


@pytest.mark.parametrize(
    ("left_text", "right_text", "expected_overlap"),
    [
        ("所以说啊", "所以说啊", "所以说啊"),
        ("前面所以", "所以后面", "所以"),
        ("啊", "啊", "啊"),
        ("删除", "保留", ""),
    ],
)
def test_repeat_transition_detection_uses_adjacent_semantic_runs(
    left_text: str,
    right_text: str,
    expected_overlap: str,
):
    characters = [*left_text, *right_text]
    units = [
        {
            "text": character,
            "_segmentIndex": 0,
            "_characterIndex": index,
        }
        for index, character in enumerate(characters)
    ]
    deleted = [True] * len(left_text) + [False] * len(right_text)

    context = app_module.build_acoustic_transition_context(
        units,
        deleted,
        len(left_text) - 1,
    )

    assert context["repeatAmbiguous"] is bool(expected_overlap)
    assert context["repeatOverlapText"] == expected_overlap
    assert context["repeatOverlapLength"] == len(expected_overlap)


def test_ambiguous_repeat_transition_requires_pcm_and_is_shared_by_timeline():
    text_boundaries: list[float] = []
    for gain in (1, 2, 4):
        diagnostics: list[dict[str, object]] = []
        forced_boundary_cache = {}
        aligned_text = app_module.align_cut_draft_text_ranges_to_audio(
            Path("unused.mp4"),
            [
                {
                    "key": "first-repeat",
                    "start": 0.0,
                    "end": 0.4,
                    "originalStart": 0.0,
                    "originalEnd": 0.4,
                }
            ],
            _ambiguous_repeat_segments(),
            2.0,
            alignment_cache=_ambiguous_repeat_alignment_cache(),
            samples=_ambiguous_repeat_samples(gain),
            diagnostics=diagnostics,
            forced_boundary_cache=forced_boundary_cache,
        )[0]
        aligned_timeline = app_module.align_cut_draft_timeline_ranges_to_audio(
            [
                {
                    "key": "manual-first-repeat",
                    "start": 0.0,
                    "end": 0.4,
                    "originalStart": 0.0,
                    "originalEnd": 0.4,
                }
            ],
            _ambiguous_repeat_segments(),
            2.0,
            alignment_cache=_ambiguous_repeat_alignment_cache(),
            samples=_ambiguous_repeat_samples(gain),
            diagnostics=diagnostics,
            forced_boundary_cache=forced_boundary_cache,
        )[0]

        text_boundaries.append(aligned_text["end"])
        assert 1.08 <= aligned_text["end"] <= 1.18
        assert aligned_timeline["end"] == aligned_text["end"]
        assert aligned_text["originalEnd"] == 0.4
        assert aligned_timeline["originalEnd"] == 0.4
        diagnostic = diagnostics[0]
        assert diagnostic["structureValid"] is True
        assert diagnostic["boundaryTrustworthy"] is True
        assert diagnostic["trustReason"] == "forced_pcm_valley"
        assert diagnostic["repeatAmbiguous"] is True
        assert diagnostic["repeatOverlapText"] == "所以说啊"
        assert diagnostic["repeatOverlapLength"] == 4
        assert diagnostic["forcedCandidate"] == 1.3
        assert diagnostic["pcmCorroborated"] is True
        assert diagnostic["pcmValleyStart"] < diagnostic["pcmValleyEnd"]
        assert aligned_text["end"] < diagnostic["retainedSpeechHardLimit"]
        assert aligned_timeline["end"] - aligned_timeline["originalEnd"] > 0.20
        timeline_diagnostic = next(
            item
            for item in diagnostics
            if item.get("entryType") == "timeline" and item.get("endpoint") == "end"
        )
        assert timeline_diagnostic["boundaryTrustworthy"] is True
        assert timeline_diagnostic["repeatAmbiguous"] is True
        assert timeline_diagnostic["pcmCorroborated"] is True
        assert timeline_diagnostic["fallbackReason"] is None

    assert max(text_boundaries) - min(text_boundaries) <= 0.001


def test_wrong_direction_repeat_uses_terminal_retained_corridor_for_both_entries():
    resolved_boundaries: list[float] = []
    for gain in (1, 2, 4):
        diagnostics: list[dict[str, object]] = []
        forced_boundary_cache = {}
        samples = _wrong_direction_repeat_samples(gain)
        text_range = {
            "key": f"wrong-direction-repeat-text-{gain}",
            "start": 0.0,
            "end": 0.4,
            "originalStart": 0.0,
            "originalEnd": 0.4,
        }
        timeline_range = {
            **text_range,
            "key": f"wrong-direction-repeat-timeline-{gain}",
        }

        aligned_text = app_module.align_cut_draft_text_ranges_to_audio(
            Path("unused.mp4"),
            [text_range],
            _ambiguous_repeat_segments(),
            2.0,
            alignment_cache=_wrong_direction_repeat_alignment_cache(),
            samples=samples,
            diagnostics=diagnostics,
            forced_boundary_cache=forced_boundary_cache,
        )[0]
        aligned_timeline = app_module.align_cut_draft_timeline_ranges_to_audio(
            [timeline_range],
            _ambiguous_repeat_segments(),
            2.0,
            alignment_cache=_wrong_direction_repeat_alignment_cache(),
            samples=samples,
            diagnostics=diagnostics,
            forced_boundary_cache=forced_boundary_cache,
        )[0]

        resolved_boundaries.append(aligned_text["end"])
        assert 1.295 <= aligned_text["end"] <= 1.30
        assert aligned_timeline["end"] == aligned_text["end"]
        assert aligned_text["originalEnd"] == 0.4
        assert aligned_timeline["originalEnd"] == 0.4
        diagnostic = diagnostics[0]
        assert diagnostic["structureValid"] is True
        assert diagnostic["repeatAmbiguous"] is True
        assert diagnostic["forcedCandidate"] == 0.32
        assert diagnostic["forcedFallbackReason"] == "alignment_wrong_direction"
        assert diagnostic["boundaryTrustworthy"] is True
        assert diagnostic["trustReason"] == "repeat_retained_pcm_valley"
        assert diagnostic["pcmCorroborated"] is True
        assert diagnostic["pcmValleyStart"] >= 0.90
        assert diagnostic["pcmValleyEnd"] == 1.30
        assert diagnostic["retainedSpeechHardLimit"] == 1.30
        assert aligned_text["end"] <= diagnostic["retainedSpeechHardLimit"]
        timeline_diagnostic = next(
            item
            for item in diagnostics
            if item.get("entryType") == "timeline" and item.get("endpoint") == "end"
        )
        assert timeline_diagnostic["final"] == diagnostic["final"]
        assert timeline_diagnostic["trustReason"] == "repeat_retained_pcm_valley"

    assert max(resolved_boundaries) - min(resolved_boundaries) <= 0.001


def test_repeat_candidate_at_fallback_uses_terminal_retained_corridor():
    diagnostics: list[dict[str, object]] = []
    forced_boundary_cache = {}
    text_range = {
        "key": "fallback-repeat-text",
        "start": 0.0,
        "end": 0.4,
        "originalStart": 0.0,
        "originalEnd": 0.4,
    }
    timeline_range = {**text_range, "key": "fallback-repeat-timeline"}
    samples = _wrong_direction_repeat_samples()

    aligned_text = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [text_range],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_fallback_repeat_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
        forced_boundary_cache=forced_boundary_cache,
    )[0]
    aligned_timeline = app_module.align_cut_draft_timeline_ranges_to_audio(
        [timeline_range],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_fallback_repeat_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
        forced_boundary_cache=forced_boundary_cache,
    )[0]

    assert 1.295 <= aligned_text["end"] <= 1.30
    assert aligned_timeline["end"] == aligned_text["end"]
    assert aligned_text["originalEnd"] == aligned_timeline["originalEnd"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["forcedCandidate"] == 0.4
    assert diagnostic["pcmGapCorroborated"] is False
    assert diagnostic["pcmCorroborated"] is True
    assert diagnostic["pcmValleyStart"] >= 0.90
    assert diagnostic["retainedSpeechHardLimit"] == 1.30
    assert diagnostic["trustReason"] == "repeat_retained_pcm_valley"


def test_wrong_direction_repeat_without_retained_speech_stays_semantic():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "wrong-direction-no-retained-speech",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_wrong_direction_repeat_alignment_cache(),
        samples=_wrong_direction_repeat_samples(retained_speech=False),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == aligned["originalEnd"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["structureValid"] is True
    assert diagnostic["forcedCandidate"] == 0.32
    assert diagnostic["forcedFallbackReason"] == "alignment_wrong_direction"
    assert diagnostic["boundaryTrustworthy"] is False
    assert diagnostic["pcmCorroborated"] is False
    assert diagnostic["retainedSpeechHardLimit"] == 1.3
    assert diagnostic["fallbackReason"] == "repeat_retained_pcm_not_corroborated"


def test_repeat_terminal_probe_failure_preserves_retained_hard_limit():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": "fallback-repeat-no-retained-speech",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_fallback_repeat_alignment_cache(),
        samples=_wrong_direction_repeat_samples(retained_speech=False),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == aligned["originalEnd"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["forcedCandidate"] == 0.4
    assert diagnostic["boundaryTrustworthy"] is False
    assert diagnostic["pcmCorroborated"] is False
    assert diagnostic["retainedSpeechHardLimit"] == 1.3
    assert diagnostic["fallbackReason"] == "repeat_pcm_not_corroborated"


@pytest.mark.parametrize("retained_limit", [None, float("nan"), 0.3])
def test_repeat_retained_corridor_rejects_missing_or_wrong_side_hard_limit(
    retained_limit: float | None,
):
    boundary, evidence = app_module.corroborate_repeat_retained_limit_with_pcm(
        0.4,
        retained_limit,
        _wrong_direction_repeat_samples(),
        app_module.CUT_BOUNDARY_SAMPLE_RATE,
        deletion_on_left=True,
    )

    assert boundary is None
    assert evidence["pcmCorroborated"] is False
    assert evidence["retainedSpeechHardLimit"] is None


@pytest.mark.parametrize(
    ("deletion_on_left", "fallback", "retained_limit", "impulse_time"),
    [
        (True, 0.4, 1.3, 1.4),
        (False, 0.4, 0.2, 0.1),
    ],
)
def test_repeat_retained_corridor_rejects_one_sample_impulse(
    deletion_on_left: bool,
    fallback: float,
    retained_limit: float,
    impulse_time: float,
):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [20]) * (sample_rate * 2)
    samples[round(impulse_time * sample_rate)] = 32_767

    boundary, evidence = app_module.corroborate_repeat_retained_limit_with_pcm(
        fallback,
        retained_limit,
        samples,
        sample_rate,
        deletion_on_left=deletion_on_left,
    )

    assert boundary is None
    assert evidence["pcmCorroborated"] is False
    assert evidence["retainedSpeechHardLimit"] is None


def test_wrong_direction_repeat_delete_start_is_symmetric_and_shared():
    samples = _wrong_direction_repeat_start_samples()
    diagnostics: list[dict[str, object]] = []
    forced_boundary_cache = {}
    text_range = {
        "key": "wrong-direction-repeat-start-text",
        "start": 0.4,
        "end": 0.8,
        "originalStart": 0.4,
        "originalEnd": 0.8,
    }
    timeline_range = {
        **text_range,
        "key": "wrong-direction-repeat-start-timeline",
    }

    aligned_text = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [text_range],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_wrong_direction_repeat_start_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
        forced_boundary_cache=forced_boundary_cache,
    )[0]
    aligned_timeline = app_module.align_cut_draft_timeline_ranges_to_audio(
        [timeline_range],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_wrong_direction_repeat_start_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
        forced_boundary_cache=forced_boundary_cache,
    )[0]

    assert 0.20 <= aligned_text["start"] <= 0.205
    assert aligned_timeline["start"] == aligned_text["start"]
    assert aligned_text["originalStart"] == 0.4
    assert aligned_timeline["originalStart"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["direction"] == "delete_start"
    assert diagnostic["forcedCandidate"] == 0.5
    assert diagnostic["forcedFallbackReason"] == "alignment_wrong_direction"
    assert diagnostic["boundaryTrustworthy"] is True
    assert diagnostic["trustReason"] == "repeat_retained_pcm_valley"
    assert diagnostic["retainedSpeechHardLimit"] == 0.2
    assert aligned_text["start"] >= diagnostic["retainedSpeechHardLimit"]


@pytest.mark.parametrize("failure", ["no_retained_speech", "overlap"])
def test_forced_quiet_gap_rejects_unprotected_candidates(failure: str):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [4_000]) * (sample_rate * 2)
    retained_limit = 1.4
    quiet_start = round(0.85 * sample_rate)
    quiet_end = round(1.4 * sample_rate)
    samples[quiet_start:quiet_end] = array("h", [20]) * (
        quiet_end - quiet_start
    )
    if failure == "no_retained_speech":
        samples[round(1.4 * sample_rate) :] = array("h", [20]) * (
            len(samples) - round(1.4 * sample_rate)
        )
    if failure == "overlap":
        retained_limit = 0.84

    boundary, evidence = app_module.corroborate_forced_transition_quiet_gap(
        0.6,
        0.85,
        retained_limit,
        samples,
        sample_rate,
        deletion_on_left=True,
    )

    assert boundary is None
    assert evidence["pcmGapCorroborated"] is False


def test_repeat_pcm_corroboration_tracks_retained_speech_limit_on_both_sides():
    samples = _ambiguous_repeat_samples()
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE

    delete_end, end_evidence = app_module.corroborate_repeated_transition_with_pcm(
        0.4,
        1.3,
        samples,
        sample_rate,
        deletion_on_left=True,
    )
    delete_start, start_evidence = (
        app_module.corroborate_repeated_transition_with_pcm(
            1.3,
            0.4,
            samples,
            sample_rate,
            deletion_on_left=False,
        )
    )

    assert delete_end is not None
    assert delete_start is not None
    assert end_evidence["retainedSpeechHardLimit"] > delete_end
    assert start_evidence["retainedSpeechHardLimit"] < delete_start


@pytest.mark.parametrize(
    ("fallback_amplitude", "valley_amplitude", "expected_corroborated"),
    [(100, 105, False), (105, 100, True)],
)
def test_ambiguous_repeat_valley_must_not_exceed_semantic_fallback_energy(
    fallback_amplitude: int,
    valley_amplitude: int,
    expected_corroborated: bool,
):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [3_000]) * (sample_rate * 2)
    for start, end, amplitude in (
        (0.30, 0.50, fallback_amplitude),
        (1.04, 1.20, valley_amplitude),
    ):
        start_index = round(start * sample_rate)
        end_index = round(end * sample_rate)
        samples[start_index:end_index] = array("h", [amplitude]) * (
            end_index - start_index
        )

    boundary, evidence = app_module.corroborate_repeated_transition_with_pcm(
        0.4,
        1.3,
        samples,
        sample_rate,
        deletion_on_left=True,
    )

    assert (boundary is not None) is expected_corroborated
    assert evidence["pcmCorroborated"] is expected_corroborated
    if expected_corroborated:
        assert evidence["retainedSpeechHardLimit"] > boundary
    else:
        assert evidence["retainedSpeechHardLimit"] is None


@pytest.mark.parametrize("shape", ["uniform", "single_point", "monotonic"])
def test_ambiguous_repeat_transition_without_sustained_valley_falls_back(shape: str):
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    if shape == "uniform":
        samples = array("h", [300]) * (sample_rate * 2)
    elif shape == "single_point":
        samples = array("h", [3_000]) * (sample_rate * 2)
        samples[round(1.12 * sample_rate)] = 0
    else:
        samples = array(
            "h",
            (
                max(100, 4_000 - round(3_000 * index / (sample_rate * 2)))
                for index in range(sample_rate * 2)
            ),
        )
    diagnostics: list[dict[str, object]] = []

    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        Path("unused.mp4"),
        [
            {
                "key": f"repeat-{shape}",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_ambiguous_repeat_alignment_cache(),
        samples=samples,
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == 0.4
    diagnostic = diagnostics[0]
    assert diagnostic["structureValid"] is True
    assert diagnostic["boundaryTrustworthy"] is False
    assert diagnostic["repeatAmbiguous"] is True
    assert diagnostic["pcmCorroborated"] is False
    assert diagnostic["fallbackReason"] == "repeat_pcm_not_corroborated"


def test_timeline_repeat_transition_over_snap_limit_requires_pcm_trust():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "manual-untrusted-repeat",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        _ambiguous_repeat_segments(),
        2.0,
        alignment_cache=_ambiguous_repeat_alignment_cache(),
        samples=array("h", [300]) * (app_module.CUT_BOUNDARY_SAMPLE_RATE * 2),
        diagnostics=diagnostics,
    )[0]

    assert aligned["end"] == aligned["originalEnd"] == 0.4
    end_diagnostic = next(
        item
        for item in diagnostics
        if item.get("entryType") == "timeline" and item.get("endpoint") == "end"
    )
    assert end_diagnostic["repeatAmbiguous"] is True
    assert end_diagnostic["pcmCorroborated"] is False
    assert end_diagnostic["boundaryTrustworthy"] is False
    assert end_diagnostic["fallbackReason"] == "repeat_pcm_not_corroborated"


def test_timeline_range_near_speech_snaps_but_preserves_original_semantics():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "manual-1",
                "start": 0.0,
                "end": 0.42,
                "originalStart": 0.0,
                "originalEnd": 0.42,
            }
        ],
        _de_ni_segments(),
        1.0,
        alignment_cache=_forced_de_ni_alignment_cache(),
        samples=array("h", [4_000]) * app_module.CUT_BOUNDARY_SAMPLE_RATE,
        diagnostics=diagnostics,
    )[0]

    assert aligned == {
        "key": "manual-1",
        "start": 0.0,
        "end": 0.5,
        "originalStart": 0.0,
        "originalEnd": 0.42,
    }
    assert diagnostics[-1]["endpoint"] == "end"
    assert diagnostics[-1]["alignmentSource"] == "funasr-fa-zh"


def test_timeline_range_entirely_inside_forced_quiet_gap_stays_exact():
    diagnostics: list[dict[str, object]] = []
    aligned = app_module.align_cut_draft_timeline_ranges_to_audio(
        [
            {
                "key": "quiet-only",
                "start": 0.56,
                "end": 0.7,
                "originalStart": 0.56,
                "originalEnd": 0.7,
            }
        ],
        _de_ni_segments(),
        1.0,
        alignment_cache=_forced_de_ni_alignment_cache(),
        samples=array("h", [0]) * app_module.CUT_BOUNDARY_SAMPLE_RATE,
        diagnostics=diagnostics,
    )[0]

    assert aligned["start"] == 0.56
    assert aligned["end"] == 0.7
    assert {item["fallbackReason"] for item in diagnostics} == {
        "non_speech_range_exact"
    }


def test_timeline_physical_range_and_semantic_range_are_projected_separately():
    draft = {
        "textRanges": [],
        "noSpeechRanges": [],
        "timelineRanges": [
            {
                "start": 0.0,
                "end": 0.5,
                "originalStart": 0.0,
                "originalEnd": 0.42,
            }
        ],
    }

    media = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        _de_ni_segments(),
        1.0,
    )
    semantic = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        _de_ni_segments(),
        1.0,
        use_text_semantic_boundaries=True,
    )

    assert media == [{"start": 0.0, "end": 0.5}]
    assert semantic == [{"start": 0.0, "end": 0.42}]


def _pcm_cache_equivalence_case(case_name: str) -> dict[str, object]:
    if case_name == "cross-segment-end":
        return {
            "segments": _cross_segment_segments(),
            "alignment": None,
            "samples": _cross_segment_delayed_tail_samples(),
            "duration": 1.2,
            "text": {
                "key": "cross-end-text",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            },
            "timeline": {
                "key": "cross-end-timeline",
                "start": 0.0,
                "end": 0.42,
                "originalStart": 0.0,
                "originalEnd": 0.42,
            },
        }
    if case_name == "cross-segment-start":
        return {
            "segments": _cross_segment_segments(),
            "alignment": None,
            "samples": _cross_segment_early_head_samples(),
            "duration": 1.2,
            "text": {
                "key": "cross-start-text",
                "start": 0.8,
                "end": 1.2,
                "originalStart": 0.8,
                "originalEnd": 1.2,
            },
            "timeline": {
                "key": "cross-start-timeline",
                "start": 0.78,
                "end": 1.2,
                "originalStart": 0.78,
                "originalEnd": 1.2,
            },
        }
    if case_name == "repeated-de-ni":
        return {
            "segments": _repeated_de_ni_segments(),
            "alignment": _repeated_de_ni_alignment_cache(),
            "samples": _repeated_de_ni_gap_samples(),
            "duration": 47.5,
            "text": {
                "key": "repeated-de-ni-text",
                "start": 33.16,
                "end": 37.12,
                "originalStart": 33.16,
                "originalEnd": 37.12,
            },
            "timeline": {
                "key": "repeated-de-ni-timeline",
                "start": 33.16,
                "end": 37.12,
                "originalStart": 33.16,
                "originalEnd": 37.12,
            },
        }
    if case_name == "yi-qi-gei":
        sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
        samples = array("h", [6_000]) * (sample_rate * 2)
        valley_start = round(0.64 * sample_rate)
        valley_end = round(0.68 * sample_rate)
        samples[valley_start:valley_end] = array("h", [0]) * (
            valley_end - valley_start
        )
        segments = [
            {
                "start": 0.0,
                "end": 1.2,
                "text": "一起给一起给",
                "words": [
                    {"text": "一起", "start": 0.0, "end": 0.4},
                    {"text": "给", "start": 0.4, "end": 0.6},
                    {"text": "一起", "start": 0.6, "end": 1.0},
                    {"text": "给", "start": 1.0, "end": 1.2},
                ],
                "asrWords": [
                    {"text": "一起", "start": 0.0, "end": 0.4},
                    {"text": "给一", "start": 0.4, "end": 0.8},
                    {"text": "起给", "start": 0.8, "end": 1.2},
                ],
            }
        ]
        return {
            "segments": segments,
            "alignment": None,
            "samples": samples,
            "duration": 2.0,
            "text": {
                "key": "yi-qi-gei-text",
                "start": 0.0,
                "end": 0.6,
                "originalStart": 0.0,
                "originalEnd": 0.6,
            },
            "timeline": {
                "key": "yi-qi-gei-timeline",
                "start": 0.0,
                "end": 0.6,
                "originalStart": 0.0,
                "originalEnd": 0.6,
            },
        }
    if case_name == "immediate-retained-speech":
        return {
            "segments": _cross_segment_segments(retained_start=0.42),
            "alignment": _cross_segment_alignment_cache(
                deleted_end=0.58,
                retained_start=0.44,
            ),
            "samples": array("h", [4_000])
            * round(1.2 * app_module.CUT_BOUNDARY_SAMPLE_RATE),
            "duration": 1.2,
            "text": {
                "key": "immediate-text",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            },
            "timeline": {
                "key": "immediate-timeline",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            },
        }
    if case_name == "retained-hard-limit-end":
        return {
            "segments": _ambiguous_repeat_segments(),
            "alignment": _wrong_direction_repeat_alignment_cache(),
            "samples": _wrong_direction_repeat_samples(),
            "duration": 2.0,
            "text": {
                "key": "hard-limit-end-text",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            },
            "timeline": {
                "key": "hard-limit-end-timeline",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            },
        }
    if case_name == "retained-hard-limit-start":
        return {
            "segments": _ambiguous_repeat_segments(),
            "alignment": _wrong_direction_repeat_start_alignment_cache(),
            "samples": _wrong_direction_repeat_start_samples(),
            "duration": 2.0,
            "text": {
                "key": "hard-limit-start-text",
                "start": 0.4,
                "end": 0.8,
                "originalStart": 0.4,
                "originalEnd": 0.8,
            },
            "timeline": {
                "key": "hard-limit-start-timeline",
                "start": 0.4,
                "end": 0.8,
                "originalStart": 0.4,
                "originalEnd": 0.8,
            },
        }
    raise AssertionError(f"Unhandled PCM cache equivalence case: {case_name}")


@pytest.mark.parametrize(
    "case_name",
    [
        "cross-segment-end",
        "cross-segment-start",
        "repeated-de-ni",
        "yi-qi-gei",
        "immediate-retained-speech",
        "retained-hard-limit-end",
        "retained-hard-limit-start",
    ],
)
def test_pcm_cache_toggle_preserves_acoustic_boundary_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case_name: str,
):
    case = _pcm_cache_equivalence_case(case_name)
    media_path = tmp_path / f"{case_name}.mp4"
    media_path.write_bytes(b"source")
    samples = case["samples"]
    decode_calls = 0

    def decode(_path: Path) -> array:
        nonlocal decode_calls
        decode_calls += 1
        return samples

    def load_alignment(*_args, **_kwargs):
        return (
            copy.deepcopy(case["alignment"]),
            {"status": "completed", "case": case_name},
        )

    monkeypatch.setattr(app_module, "decode_cut_audio_samples", decode)
    monkeypatch.setattr(app_module, "load_job_acoustic_alignment", load_alignment)

    def resolve(max_bytes: int):
        monkeypatch.setattr(
            app_module,
            "CUT_DRAFT_PCM_CACHE_MAX_BYTES",
            max_bytes,
        )
        return app_module.resolve_cut_draft_acoustic_boundaries(
            media_path,
            [copy.deepcopy(case["text"])],
            [copy.deepcopy(case["timeline"])],
            copy.deepcopy(case["segments"]),
            case["duration"],
        )

    app_module.CUT_DRAFT_PCM_CACHE.clear()
    disabled = resolve(0)
    app_module.CUT_DRAFT_PCM_CACHE.clear()
    enabled = resolve(len(samples) * samples.itemsize + 1)
    cached = resolve(len(samples) * samples.itemsize + 1)

    assert enabled == disabled
    assert cached == enabled
    assert decode_calls == 2
