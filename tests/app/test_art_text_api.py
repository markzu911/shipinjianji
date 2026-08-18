from __future__ import annotations

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
