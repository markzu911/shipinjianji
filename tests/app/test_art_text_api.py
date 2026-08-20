from __future__ import annotations

import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


def test_art_text_can_use_original_video_without_cut(sample_video: Path):
    job_id = "11111111-1111-1111-1111-111111111111"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {
                "text": "原视频文案",
                "duration": 1.0,
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "原视频文案",
                        "words": [],
                    }
                ],
            },
            "edit": None,
            "art": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    overlay = {
        "text": "重点",
        "font": "bold",
        "fontSize": 42,
        "color": "#FFD84D",
        "strokeColor": "#071018",
        "strokeWidth": 3,
        "shadow": True,
        "x": 0.5,
        "y": 0.2,
        "start": 0.0,
        "end": 0.8,
    }

    with TestClient(app_module.app) as client:
        edited_response = client.post(
            f"/api/transcriptions/{job_id}/art-text",
            json={"source": "edited", "overlays": [overlay]},
        )
        original_video_response = client.get(
            f"/api/transcriptions/{job_id}/original-video"
        )
        art_response = client.post(
            f"/api/transcriptions/{job_id}/art-text",
            json={"source": "original", "overlays": [overlay]},
        )
        final_job_response = client.get(f"/api/transcriptions/{job_id}")
        art_video_response = client.get(
            f"/api/transcriptions/{job_id}/art-text-video"
        )

    assert edited_response.status_code == 409
    assert original_video_response.status_code == 200
    assert original_video_response.headers["content-type"] == "video/mp4"
    assert art_response.status_code == 202
    art = final_job_response.json()["art"]
    assert art["status"] == "completed"
    assert art["source"] == "original"
    assert art["outputDuration"] == 1.0
    assert art_video_response.status_code == 200
    assert 0.8 < app_module.probe_video(sample_video.parent / "art-text.mp4") < 1.2


def test_art_text_rejects_invalid_overlay_time():
    overlay = app_module.TextOverlay(
        text="标题",
        font="modern",
        fontSize=48,
        color="#FFFFFF",
        strokeColor="#000000",
        strokeWidth=2,
        shadow=True,
        x=0.5,
        y=0.2,
        start=0.8,
        end=1.2,
    )

    with pytest.raises(ValueError, match="时间超出视频范围"):
        app_module.normalize_text_overlays([overlay], 1.0)


def test_art_text_preserves_original_timeline_anchor():
    overlay = app_module.TextOverlay(
        text="剪后同步",
        font="modern",
        fontSize=48,
        color="#FFFFFF",
        strokeColor="#000000",
        strokeWidth=2,
        shadow=True,
        x=0.5,
        y=0.2,
        start=1.0,
        end=2.0,
        sourceStart=3.5,
        sourceEnd=4.5,
    )

    normalized = app_module.normalize_text_overlays([overlay], 3.0)

    assert normalized[0]["start"] == 1.0
    assert normalized[0]["end"] == 2.0
    assert normalized[0]["sourceStart"] == 3.5
    assert normalized[0]["sourceEnd"] == 4.5


def test_transcript_art_text_overlap_ends_at_next_real_start_time():
    shared = {
        "font": "modern",
        "fontSize": 48,
        "color": "#FFFFFF",
        "strokeColor": "#000000",
        "strokeWidth": 2,
        "shadow": True,
        "x": 0.5,
        "y": 0.9,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "lineSpacing": 0,
        "artStyle": "impact",
        "trackId": "transcript-full",
        "trackType": "transcript",
    }
    overlays = [
        app_module.TextOverlay(text="第一句", start=0.4, end=0.8, **shared),
        app_module.TextOverlay(text="第二句", start=0.75, end=1.1, **shared),
    ]

    normalized = app_module.normalize_text_overlays(overlays, 2.0)

    assert normalized[0]["end"] == 0.75
    assert normalized[1]["start"] == 0.75
    assert normalized[0]["end"] <= normalized[1]["start"]


def test_transcript_art_text_clamps_sub_millisecond_overlap_without_moving_next_cue():
    timing_items = [
        {
            "text": "上一句",
            "start": 0.4,
            "end": 0.8006,
            "sourceStart": 10.0,
            "sourceEnd": 10.4006,
            "characterTimings": [
                {"start": 0.4, "end": 0.55},
                {"start": 0.55, "end": 0.7},
                {"start": 0.7, "end": 0.8006},
            ],
        },
        {
            "text": "下一句",
            "start": 0.8004,
            "end": 1.2,
            "sourceStart": 11.0,
            "sourceEnd": 11.4,
            "characterTimings": [
                {"start": 0.8004, "end": 0.9},
                {"start": 0.9, "end": 1.05},
                {"start": 1.05, "end": 1.2},
            ],
        },
    ]
    next_cue_before = copy.deepcopy(timing_items[1])

    app_module.normalize_transcript_timing_group(timing_items)

    assert timing_items[0]["end"] == timing_items[1]["start"] == 0.8004
    assert timing_items[0]["characterTimings"][-1]["end"] <= 0.8004
    assert timing_items[1] == next_cue_before

    shared = {
        "font": "modern",
        "fontSize": 48,
        "color": "#FFFFFF",
        "strokeColor": "#000000",
        "strokeWidth": 2,
        "shadow": True,
        "x": 0.5,
        "y": 0.9,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "lineSpacing": 0,
        "artStyle": "impact",
        "trackId": "transcript-full",
        "trackType": "transcript",
    }
    overlays = [
        app_module.TextOverlay(
            text="上一句",
            start=0.4,
            end=0.8006,
            sourceStart=10.0,
            sourceEnd=10.4006,
            characterTimings=[
                {"start": 0.4, "end": 0.55},
                {"start": 0.55, "end": 0.7},
                {"start": 0.7, "end": 0.8006},
            ],
            **shared,
        ),
        app_module.TextOverlay(
            text="下一句",
            start=0.8004,
            end=1.2,
            sourceStart=11.0,
            sourceEnd=11.4,
            characterTimings=[
                {"start": 0.8004, "end": 0.9},
                {"start": 0.9, "end": 1.05},
                {"start": 1.05, "end": 1.2},
            ],
            **shared,
        ),
    ]

    normalized = app_module.normalize_text_overlays(overlays, 2.0)
    previous, current = normalized

    assert previous["end"] == current["start"] == 0.8
    assert previous["characterTimings"][-1]["end"] <= previous["end"]
    assert current["text"] == "下一句"
    assert current["start"] == 0.8
    assert current["characterTimings"][0]["start"] == 0.8004
    assert current["sourceStart"] == 11.0
    assert current["sourceEnd"] == 11.4


def test_ai_art_suggestions_are_normalized_and_filled_to_requested_count():
    transcript = {
        "text": "先明确目标。再执行行动。",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 3.0,
                "text": "先明确目标。",
                "words": [],
            },
            {
                "id": 1,
                "start": 4.0,
                "end": 8.0,
                "text": "再执行行动。",
                "words": [],
            },
        ],
    }

    suggestions = app_module.normalize_ai_art_suggestions(
        [
            {
                "text": "重点来了！",
                "start": 1.0,
                "end": 3.0,
                "position": "bottom-right",
                "artStyle": "neon",
                "direction": "horizontal",
                "reason": "右下角有留白",
            }
        ],
        transcript,
        8.0,
        3,
    )

    assert len(suggestions) == 3
    assert suggestions[0]["text"] == "重点来了"
    assert suggestions[0]["start"] == 1.0
    assert suggestions[0]["end"] == 3.0
    assert suggestions[0]["position"] == "bottom-right"
    assert suggestions[0]["x"] == 0.8
    assert suggestions[0]["y"] == 0.82
    assert suggestions[0]["artStyle"] == "neon"
    assert suggestions[0]["reason"] == "右下角有留白"
    assert all(item["text"] for item in suggestions)
    assert all(0 <= item["start"] < item["end"] <= 8.0 for item in suggestions)
    assert all(item["position"] in app_module.AI_ART_POSITIONS for item in suggestions)


def test_ai_art_suggestion_endpoint_uses_original_video_and_can_be_cleared(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "22222222-2222-2222-2222-222222222222"
    transcript = {
        "text": "先明确目标，再执行行动。",
        "duration": 1.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.0,
                "text": "先明确目标，再执行行动。",
                "words": [],
            }
        ],
    }
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": transcript,
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "updatedAt": app_module.utc_now(),
        }
        app_module.JOB_FILES[job_id] = sample_video

    captured = {}

    def fake_generate(
        input_path,
        source_transcript,
        duration,
        count,
        existing_overlays,
        progress_callback,
    ):
        captured.update(
            {
                "input_path": input_path,
                "transcript": source_transcript,
                "duration": duration,
                "count": count,
                "existing": existing_overlays,
            }
        )
        progress_callback(72, "正在生成测试草稿")
        return app_module.normalize_ai_art_suggestions(
            [],
            source_transcript,
            duration,
            count,
        )

    monkeypatch.setattr(
        app_module,
        "generate_art_text_suggestions",
        fake_generate,
    )

    with TestClient(app_module.app) as client:
        edited_response = client.post(
            f"/api/transcriptions/{job_id}/art-text/suggestions",
            json={"source": "edited", "count": 2, "existingOverlays": []},
        )
        too_many_response = client.post(
            f"/api/transcriptions/{job_id}/art-text/suggestions",
            json={"source": "original", "count": 21, "existingOverlays": []},
        )
        response = client.post(
            f"/api/transcriptions/{job_id}/art-text/suggestions",
            json={"source": "original", "count": 2, "existingOverlays": []},
        )
        job_response = client.get(f"/api/transcriptions/{job_id}")
        clear_response = client.delete(
            f"/api/transcriptions/{job_id}/art-text/suggestions"
        )
        cleared_job_response = client.get(f"/api/transcriptions/{job_id}")

    assert edited_response.status_code == 409
    assert too_many_response.status_code == 400
    assert response.status_code == 202, response.text
    suggestion_job = job_response.json()["artSuggestion"]
    assert suggestion_job["status"] == "completed"
    assert suggestion_job["source"] == "original"
    assert suggestion_job["count"] == 2
    assert len(suggestion_job["suggestions"]) == 2
    assert captured == {
        "input_path": sample_video,
        "transcript": transcript,
        "duration": 1.0,
        "count": 2,
        "existing": [],
    }
    assert clear_response.status_code == 200
    assert clear_response.json() == {"status": "cleared"}
    assert cleared_job_response.json()["artSuggestion"] is None


def test_ai_art_suggestion_endpoint_accepts_live_edited_draft_without_edit_file(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "23232323-2323-2323-2323-232323232323"
    original_transcript = {
        "text": "删除内容保留重点",
        "duration": 1.0,
        "segments": [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "删除内容保留重点"}
        ],
    }
    draft_transcript = {
        "text": "保留重点",
        "duration": 0.6,
        "segments": [
            {
                "id": "retained-1",
                "start": 0.1,
                "end": 0.6,
                "sourceStart": 0.5,
                "sourceEnd": 1.0,
                "text": "保留重点",
                "words": [
                    {
                        "text": "保留重点",
                        "start": 0.1,
                        "end": 0.6,
                        "sourceStart": 0.5,
                        "sourceEnd": 1.0,
                    }
                ],
            }
        ],
    }
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": original_transcript,
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "updatedAt": app_module.utc_now(),
        }
        app_module.JOB_FILES[job_id] = sample_video

    captured = {}

    def fake_generate(
        input_path,
        source_transcript,
        duration,
        count,
        existing_overlays,
        progress_callback,
    ):
        captured.update(
            input_path=input_path,
            transcript=source_transcript,
            duration=duration,
        )
        return app_module.normalize_ai_art_suggestions(
            [], source_transcript, duration, count
        )

    monkeypatch.setattr(app_module, "generate_art_text_suggestions", fake_generate)

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/art-text/suggestions",
            json={
                "source": "edited",
                "count": 1,
                "existingOverlays": [],
                "draftTranscript": draft_transcript,
                "draftDuration": 0.6,
            },
        )

    assert response.status_code == 202, response.text
    assert captured == {
        "input_path": sample_video,
        "transcript": draft_transcript,
        "duration": 0.6,
    }


@pytest.mark.parametrize("field", ["words", "asrWords"])
def test_live_art_transcript_rejects_oversized_nested_timing_lists(field: str):
    with pytest.raises(ValueError, match="词级文案过长"):
        app_module.validate_live_art_transcript(
            {
                "segments": [
                    {
                        "text": "保留重点",
                        "start": 0.0,
                        "end": 1.0,
                        field: [{}]
                        * (app_module.MAX_LIVE_ART_TRANSCRIPT_TIMED_ITEMS + 1),
                    }
                ]
            },
            1.0,
            1.0,
        )


def test_art_frame_samples_separate_original_seek_from_edited_label():
    samples = app_module.select_art_frame_samples(
        {
            "segments": [
                {
                    "text": "保留重点",
                    "start": 3.21,
                    "end": 4.21,
                    "sourceStart": 7.29,
                    "sourceEnd": 8.29,
                }
            ]
        },
        8.0,
        1,
    )

    anchored = min(samples, key=lambda sample: abs(sample["displayTime"] - 3.71))
    assert anchored["displayTime"] == pytest.approx(3.71)
    assert anchored["mediaTime"] == pytest.approx(7.79)
    assert all(
        sample["mediaTime"] - sample["displayTime"] == pytest.approx(4.08)
        for sample in samples
    )


def test_art_frame_samples_fill_unanchored_single_segment_after_deduplication():
    samples = app_module.select_art_frame_samples(
        {
            "segments": [
                {
                    "text": "保留重点",
                    "start": 0.0,
                    "end": 1.0,
                }
            ]
        },
        1.0,
        1,
    )

    assert len(samples) == 4
    assert all(sample["mediaTime"] == sample["displayTime"] for sample in samples)


def test_art_contact_sheet_seeks_media_time_and_labels_display_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    seeks: list[float] = []
    labels: list[str] = []

    def fake_run(command, **_kwargs):
        seeks.append(float(command[command.index("-ss") + 1]))
        app_module.Image.new("RGB", (16, 9), "black").save(command[-1], "JPEG")
        return type("Completed", (), {"returncode": 0})()

    original_draw = app_module.ImageDraw.Draw

    def recording_draw(image):
        delegate = original_draw(image)

        class DrawProxy:
            def rectangle(self, *args, **kwargs):
                return delegate.rectangle(*args, **kwargs)

            def text(self, position, value, *args, **kwargs):
                labels.append(str(value))
                return delegate.text(position, value, *args, **kwargs)

        return DrawProxy()

    monkeypatch.setattr(app_module.subprocess, "run", fake_run)
    monkeypatch.setattr(app_module.ImageDraw, "Draw", recording_draw)
    output = app_module.create_art_contact_sheet(
        tmp_path / "original.mp4",
        tmp_path,
        [{"mediaTime": 7.79, "displayTime": 3.71}],
    )

    assert output.is_file()
    assert seeks == [pytest.approx(7.79)]
    assert labels == ["FRAME 01  3.7s"]
