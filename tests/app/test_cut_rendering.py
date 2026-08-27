from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


def test_retained_transcript_uses_edited_video_timeline():
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 1.0,
            "text": "保留删除保留",
            "words": [
                {"text": "保留", "start": 0.0, "end": 0.25},
                {"text": "删除", "start": 0.25, "end": 0.55},
                {"text": "保留", "start": 0.55, "end": 1.0},
            ],
        }
    ]

    result = app_module.build_retained_transcript(
        segments,
        [{"start": 0.25, "end": 0.55}],
        0.7,
    )

    assert result["text"] == "保留保留"
    assert result["duration"] == 0.7
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][0]["end"] == 0.7
    assert result["segments"][0]["words"] == [
        {
            "text": "保留",
            "start": 0.0,
            "end": 0.25,
            "sourceStart": 0.0,
            "sourceEnd": 0.25,
        },
        {
            "text": "保留",
            "start": 0.25,
            "end": 0.7,
            "sourceStart": 0.55,
            "sourceEnd": 1.0,
        },
    ]


def test_retained_transcript_retimes_after_text_and_silence_deletions():
    segments = [
        {
            "id": 0,
            "start": 0.5,
            "end": 1.0,
            "text": "甲",
            "words": [{"text": "甲", "start": 0.5, "end": 1.0}],
        },
        {
            "id": 1,
            "start": 2.0,
            "end": 3.0,
            "text": "删除",
            "words": [{"text": "删除", "start": 2.0, "end": 3.0}],
        },
        {
            "id": 2,
            "start": 5.0,
            "end": 6.0,
            "text": "乙",
            "words": [{"text": "乙", "start": 5.0, "end": 6.0}],
        },
        {
            "id": 3,
            "start": 8.0,
            "end": 9.0,
            "text": "丙",
            "words": [{"text": "丙", "start": 8.0, "end": 9.0}],
        },
    ]

    result = app_module.build_retained_transcript(
        segments,
        [{"start": 2.0, "end": 3.0}],
        6.2,
        timeline_delete_ranges=[
            {"start": 1.2, "end": 4.0},
            {"start": 6.0, "end": 7.0},
        ],
    )

    assert result["text"] == "甲乙丙"
    assert result["duration"] == 6.2
    assert [
        (segment["text"], segment["start"], segment["end"])
        for segment in result["segments"]
    ] == [
        ("甲", 0.5, 1.0),
        ("乙", 2.2, 3.2),
        ("丙", 4.2, 5.2),
    ]


def test_retained_transcript_can_remove_one_character_without_losing_the_word():
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 0.9,
            "text": "凌云志，",
            "words": [
                {"text": "凌云志，", "start": 0.0, "end": 0.9},
            ],
        }
    ]

    result = app_module.build_retained_transcript(
        segments,
        [{"start": 0.3, "end": 0.6}],
        0.6,
    )

    assert result["text"] == "凌志，"
    assert result["segments"][0]["words"] == [
        {
            "text": "凌",
            "start": 0.0,
            "end": 0.3,
            "sourceStart": 0.0,
            "sourceEnd": 0.3,
        },
        {
            "text": "志，",
            "start": 0.3,
            "end": 0.6,
            "sourceStart": 0.6,
            "sourceEnd": 0.9,
        },
    ]


def test_cut_endpoint_renders_preview_video(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ASR_API_KEY", "test-key")

    def fake_transcribe(audio_path: Path, progress_callback):
        progress_callback(90)
        return {
            "text": "保留删除保留",
            "language": "zh",
            "languageProbability": None,
            "duration": 1.0,
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 1.0,
                    "text": "保留删除保留",
                    "words": [
                        {"text": "保留", "start": 0.0, "end": 0.25},
                        {"text": "删除", "start": 0.25, "end": 0.55},
                        {"text": "保留", "start": 0.55, "end": 1.0},
                    ],
                }
            ],
        }

    monkeypatch.setattr(app_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(
        app_module,
        "suggest_deletions",
        lambda segments, api_key: ([], "completed"),
    )
    monkeypatch.setattr(
        app_module,
        "snap_delete_ranges_to_audio",
        lambda *args, **kwargs: pytest.fail(
            "生成视频不应再次改变当前预览的剪辑区间"
        ),
    )

    with TestClient(app_module.app) as client, sample_video.open("rb") as handle:
        upload_response = client.post(
            "/api/transcriptions",
            files={"file": (sample_video.name, handle, "video/mp4")},
        )
        job_id = upload_response.json()["id"]
        with app_module.JOBS_LOCK:
            app_module.JOBS[job_id]["pictureInPicture"] = {
                "status": "completed",
                "source": "original",
                "overlays": [],
            }

        cut_response = client.post(
            f"/api/transcriptions/{job_id}/cuts",
            json={
                "ranges": [{"start": 0.25, "end": 0.55}],
            },
        )
        job_response = client.get(f"/api/transcriptions/{job_id}")
        video_response = client.get(
            f"/api/transcriptions/{job_id}/edited-video"
        )
        history_after_cut_response = client.get("/api/history")
        save_edit_response = client.post(
            f"/api/transcriptions/{job_id}/history",
            json={"kind": "edited", "name": "第一版剪辑"},
        )
        duplicate_save_edit_response = client.post(
            f"/api/transcriptions/{job_id}/history",
            json={"kind": "edited", "name": "不会重复保存"},
        )
        with app_module.JOBS_LOCK:
            app_module.JOBS[job_id]["pictureInPicture"] = {
                "status": "completed",
                "source": "edited",
                "overlays": [],
            }
        art_response = client.post(
            f"/api/transcriptions/{job_id}/art-text",
            json={
                "overlays": [
                    {
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
                        "end": 0.6,
                        "direction": "vertical",
                        "textAlign": "right",
                        "charsPerLine": 2,
                        "letterSpacing": 4,
                        "lineSpacing": 6,
                        "artStyle": "metal",
                    }
                ]
            },
        )
        final_job_response = client.get(f"/api/transcriptions/{job_id}")
        art_video_response = client.get(
            f"/api/transcriptions/{job_id}/art-text-video"
        )
        history_after_art_response = client.get("/api/history")
        save_art_response = client.post(
            f"/api/transcriptions/{job_id}/history",
            json={"kind": "art", "name": "客户艺术字版"},
        )
        history_response = client.get("/api/history")

    assert cut_response.status_code == 202
    edit = job_response.json()["edit"]
    assert edit["status"] == "completed"
    assert job_response.json()["pictureInPicture"] is None
    assert edit["ranges"] == [{"start": 0.25, "end": 0.55}]
    assert edit["requestedRanges"] == [{"start": 0.25, "end": 0.55}]
    assert edit["outputDuration"] == 0.7
    assert edit["transcript"]["text"] == "保留保留"
    assert [
        segment["editableSegmentId"]
        for segment in edit["transcript"]["segments"]
    ] == [0, 0]
    assert edit["transcript"]["segments"][1]["words"][0] == {
        "text": "保留",
        "start": 0.25,
        "end": 0.7,
        "sourceStart": 0.55,
        "sourceEnd": 1.0,
    }
    assert video_response.status_code == 200
    assert video_response.headers["content-type"] == "video/mp4"
    assert history_after_cut_response.json()["count"] == 0
    assert save_edit_response.status_code == 201
    assert save_edit_response.json()["kind"] == "edited"
    assert save_edit_response.json()["name"] == "第一版剪辑"
    assert duplicate_save_edit_response.status_code == 201
    assert duplicate_save_edit_response.json()["id"] == save_edit_response.json()["id"]
    output_path = app_module.DATA_DIR / "jobs" / job_id / "edited.mp4"
    assert output_path.is_file()
    assert 0.45 < app_module.probe_video(output_path) < 0.8
    assert art_response.status_code == 202
    assert final_job_response.json()["pictureInPicture"] is None
    art = final_job_response.json()["art"]
    assert art["status"] == "completed"
    assert art["source"] == "edited"
    assert art["overlays"][0]["text"] == "重点"
    assert art["overlays"][0]["direction"] == "vertical"
    assert art["overlays"][0]["textAlign"] == "right"
    assert art["overlays"][0]["artStyle"] == "metal"
    assert art_video_response.status_code == 200
    assert art_video_response.headers["content-type"] == "video/mp4"
    assert history_after_art_response.json()["count"] == 1
    assert save_art_response.status_code == 201
    assert save_art_response.json()["kind"] == "art"
    assert save_art_response.json()["name"] == "客户艺术字版"
    assert history_response.status_code == 200
    assert history_response.json()["count"] == 2
    assert history_response.json()["editedCount"] == 1
    assert history_response.json()["artCount"] == 1
    assert "historyId" not in edit
    assert "historyName" not in edit
    assert "historyId" not in art
    assert "historyName" not in art
    assert {item["name"] for item in history_response.json()["versions"]} == {
        "第一版剪辑",
        "客户艺术字版",
    }
    art_output_path = app_module.DATA_DIR / "jobs" / job_id / "art-text.mp4"
    art_layer_path = app_module.DATA_DIR / "jobs" / job_id / "art-text-0.png"
    assert art_output_path.is_file()
    assert art_layer_path.is_file()
    assert 0.5 < app_module.probe_video(art_output_path) < 0.9


def test_cut_endpoint_uses_saved_shared_media_range_and_semantic_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "37373737-3737-4737-8737-373737373737"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
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
    draft = {
        "schemaVersion": 1,
        "revision": 1,
        "automaticNoSpeechInitialized": True,
        "textRanges": [
            {
                "key": "1.000-2.000",
                "start": 0.82,
                "end": 2.14,
                "originalStart": 1.0,
                "originalEnd": 2.0,
            }
        ],
        "noSpeechRanges": [],
        "timelineRanges": [],
    }
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": "source.mp4",
            "status": "completed",
            "duration": 3.0,
            "result": {"segments": segments, "suggestions": []},
            "cutDraft": draft,
            "edit": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    def fake_render_cut_video(
        _input_path: Path,
        output_path: Path,
        ranges: list[dict[str, float]],
        _duration: float,
    ) -> None:
        assert ranges == [{"start": 0.82, "end": 2.14}]
        output_path.write_bytes(b"edited")

    monkeypatch.setattr(app_module, "render_cut_video", fake_render_cut_video)
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: (_ for _ in ()).throw(RuntimeError("no decoded audio")),
    )

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/cuts",
            json={"ranges": [{"start": 0.82, "end": 2.14}]},
        )
        job = client.get(f"/api/transcriptions/{job_id}").json()

    assert response.status_code == 202
    assert job["edit"]["ranges"] == [{"start": 0.82, "end": 2.14}]
    assert job["edit"]["requestedRanges"] == [{"start": 0.82, "end": 2.14}]
    assert job["edit"]["transcriptRanges"] == [{"start": 1.0, "end": 2.0}]
    assert job["edit"]["transcript"]["text"] == "保留保留"


def test_cut_endpoint_revision_uses_authoritative_persisted_draft(
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "39393939-3939-4939-8939-393939393939"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
    segments = [
        {
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
    draft = {
        "schemaVersion": 1,
        "revision": 3,
        "textRanges": [
            {
                "key": "delete-text",
                "start": 0.82,
                "end": 2.14,
                "originalStart": 1.0,
                "originalEnd": 2.0,
            }
        ],
        "noSpeechRanges": [],
        "timelineRanges": [],
    }
    app_module.save_cut_draft(job_id, draft)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": "source.mp4",
            "status": "completed",
            "duration": 3.0,
            "result": {"segments": segments, "suggestions": []},
            "cutDraft": None,
            "edit": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    captured: list[tuple[list[dict[str, float]], list[dict[str, float]]]] = []
    monkeypatch.setattr(
        app_module,
        "process_cut_job",
            lambda _job_id, media, semantic, _attempt_id=None: captured.append(
                (media, semantic)
            ),
    )
    monkeypatch.setattr(
        app_module,
        "resolve_cut_draft_acoustic_boundaries",
        lambda *_args, **_kwargs: pytest.fail("生成阶段不得重新执行声学对齐"),
    )

    with TestClient(app_module.app) as client:
        stale = client.post(
            f"/api/transcriptions/{job_id}/cuts",
            json={
                "ranges": [{"start": 0.95, "end": 2.05}],
                "cutDraftRevision": 2,
            },
        )
        current = client.post(
            f"/api/transcriptions/{job_id}/cuts",
            json={
                "ranges": [{"start": 0.95, "end": 2.05}],
                "cutDraftRevision": 3,
            },
        )

    assert stale.status_code == 409
    assert "草稿版本" in stale.json()["detail"]
    assert current.status_code == 202
    assert captured == [
        (
            [{"start": 0.82, "end": 2.14}],
            [{"start": 1.0, "end": 2.0}],
        )
    ]
    assert current.json()["ranges"] == [{"start": 0.82, "end": 2.14}]
    assert current.json()["transcriptRanges"] == [{"start": 1.0, "end": 2.0}]


def test_cut_revision_rejects_authoritative_draft_without_delete_ranges():
    draft = {
        "schemaVersion": 1,
        "revision": 3,
        "textRanges": [],
        "noSpeechRanges": [],
        "timelineRanges": [],
    }

    with pytest.raises(ValueError, match="至少选择一个"):
        app_module.resolve_generation_cut_ranges(
            [],
            3.0,
            draft,
            [],
            [],
            cut_draft_revision=3,
        )

    assert app_module.resolve_generation_cut_ranges(
        [],
        3.0,
        draft,
        [],
        [],
        cut_draft_revision=3,
        allow_empty_request=True,
    ) == ([], [])


def test_cut_endpoint_keeps_ni_when_raw_asr_token_crosses_text_boundary(
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "48484848-4848-4848-8848-484848484848"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
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
    draft = {
        "schemaVersion": 1,
        "revision": 1,
        "automaticNoSpeechInitialized": True,
        "textRanges": [
            {
                "key": "0.000-0.400",
                "start": 0.0,
                "end": 0.44,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        "noSpeechRanges": [],
        "timelineRanges": [],
    }
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": "source.mp4",
            "status": "completed",
            "duration": 1.0,
            "result": {"segments": segments, "suggestions": []},
            "cutDraft": draft,
            "edit": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    def fake_render_cut_video(
        _input_path: Path,
        output_path: Path,
        ranges: list[dict[str, float]],
        _duration: float,
    ) -> None:
        assert ranges == [{"start": 0.0, "end": 0.44}]
        output_path.write_bytes(b"edited")

    monkeypatch.setattr(app_module, "render_cut_video", fake_render_cut_video)
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: (_ for _ in ()).throw(RuntimeError("no decoded audio")),
    )

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/cuts",
            json={"ranges": [{"start": 0.0, "end": 0.44}]},
        )
        job = client.get(f"/api/transcriptions/{job_id}").json()

    assert response.status_code == 202, response.text
    assert job["edit"]["ranges"] == [{"start": 0.0, "end": 0.44}]
    assert job["edit"]["transcriptRanges"] == [{"start": 0.0, "end": 0.4}]
    assert job["edit"]["transcript"]["text"] == "你"
    assert job["edit"]["transcript"]["segments"][0]["asrWords"] == [
        {
            "text": "你",
            "start": 0.0,
            "end": 0.16,
            "sourceStart": 0.4,
            "sourceEnd": 0.6,
        }
    ]


def test_probe_video_dimensions(sample_video: Path):
    assert app_module.probe_video_dimensions(sample_video) == (320, 180)


def test_cut_render_normalizes_output_audio(tmp_path: Path, monkeypatch):
    captured: dict[str, object] = {}

    def fake_run_ffmpeg(command, **options):
        captured["command"] = command
        Path(command[-1]).write_bytes(b"rendered")
        return type("Result", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(app_module, "run_ffmpeg", fake_run_ffmpeg)
    output_path = tmp_path / "edited.mp4"

    app_module.render_cut_video(
        tmp_path / "source.mp4",
        output_path,
        [{"start": 1.0, "end": 2.0}],
        4.0,
    )

    command = captured["command"]
    filter_graph = command[command.index("-filter_complex") + 1]
    assert app_module.CUT_AUDIO_LOUDNESS_FILTER in filter_graph
    assert output_path.read_bytes() == b"rendered"
