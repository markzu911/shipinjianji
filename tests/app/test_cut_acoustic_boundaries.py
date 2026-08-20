from __future__ import annotations

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
