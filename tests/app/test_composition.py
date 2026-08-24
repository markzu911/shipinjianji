from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


def test_original_art_and_picture_in_picture_are_blocked_after_cut_starts(
    sample_video: Path,
):
    job_id = "12121212-1212-1212-1212-121212121212"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "原视频文案", "duration": 1.0, "segments": []},
            "edit": {"status": "processing", "progress": 35},
            "art": None,
            "artSuggestion": None,
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    with TestClient(app_module.app) as client:
        suggestion_response = client.post(
            f"/api/transcriptions/{job_id}/art-text/suggestions",
            json={"source": "original", "count": 1, "existingOverlays": []},
        )
        art_response = client.post(
            f"/api/transcriptions/{job_id}/art-text",
            json={"source": "original", "overlays": []},
        )
        pip_response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture",
            json={"source": "original", "overlays": []},
        )

    for response in (suggestion_response, art_response, pip_response):
        assert response.status_code == 409
        assert "视频正在剪辑" in response.json()["detail"]
        assert "完成后再进行其他操作" in response.json()["detail"]


def test_preview_composition_renders_cut_art_and_pip_in_one_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "77777777-7777-4777-8777-777777777777"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
    asset_id = "preview-composition-image"
    (job_dir / f"picture-in-picture-{asset_id}.png").write_bytes(b"png")
    calls: list[tuple[str, Path, Path, list[dict[str, object]]]] = []

    def fake_cut(
        input_path: Path,
        output_path: Path,
        ranges: list[dict[str, float]],
        duration: float,
    ) -> None:
        calls.append(("cut", input_path, output_path, ranges))
        output_path.write_bytes(b"edited")

    def fake_art(
        input_path: Path,
        output_path: Path,
        overlays: list[dict[str, object]],
    ) -> None:
        calls.append(("art", input_path, output_path, overlays))
        output_path.write_bytes(b"art")

    def fake_pip(
        input_path: Path,
        output_path: Path,
        overlays: list[dict[str, object]],
    ) -> None:
        calls.append(("pip", input_path, output_path, overlays))
        output_path.write_bytes(b"pip")

    monkeypatch.setattr(
        app_module,
        "snap_delete_ranges_to_audio",
        lambda *args, **kwargs: pytest.fail(
            "组合生成不应再次改变当前预览的剪辑区间"
        ),
    )
    monkeypatch.setattr(app_module, "render_cut_video", fake_cut)
    monkeypatch.setattr(app_module, "render_art_text_video", fake_art)
    monkeypatch.setattr(app_module, "render_picture_in_picture_video", fake_pip)

    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": "source.mp4",
            "duration": 1.0,
            "status": "completed",
            "result": {
                "text": "删除保留字幕",
                "duration": 1.0,
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "删除保留字幕",
                        "words": [
                            {"text": "删除", "start": 0.2, "end": 0.4},
                            {"text": "保留字幕", "start": 0.4, "end": 0.9},
                        ],
                    }
                ],
            },
            "cutDraft": {
                "schemaVersion": 1,
                "revision": 1,
                "automaticNoSpeechInitialized": True,
                "textRanges": [
                    {
                        "key": "0.200-0.400",
                        "start": 0.2,
                        "end": 0.44,
                        "originalStart": 0.2,
                        "originalEnd": 0.4,
                    }
                ],
                "noSpeechRanges": [],
                "timelineRanges": [],
            },
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [
                {
                    "id": asset_id,
                    "text": "保留字幕",
                    "prompt": "测试插图",
                    "source": "original",
                    "start": 0.4,
                    "end": 0.7,
                    "imageUrl": f"/api/transcriptions/{job_id}/picture-in-picture/images/{asset_id}",
                }
            ],
            "pictureInPictureVideos": [],
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/compose",
            json={
                "target": "all",
                "ranges": [{"start": 0.2, "end": 0.44}],
                "artSource": "original",
                "artOverlays": [
                    {
                        "text": "保留字幕",
                        "font": "bold",
                        "fontSize": 42,
                        "color": "#FFD84D",
                        "strokeColor": "#071018",
                        "strokeWidth": 3,
                        "shadow": True,
                        "x": 0.5,
                        "y": 0.8,
                        "start": 0.4,
                        "end": 0.7,
                        "artStyle": "impact",
                        "sourceStart": 0.6,
                        "sourceEnd": 0.9,
                    }
                ],
                "pictureInPictureSource": "original",
                "pictureInPictureOverlays": [
                    {
                        "assetId": asset_id,
                        "start": 0.4,
                        "end": 0.7,
                        "sourceStart": 0.6,
                        "sourceEnd": 0.9,
                        "x": 0.78,
                        "y": 0.22,
                        "width": 0.32,
                    }
                ],
            },
        )
        job_response = client.get(f"/api/transcriptions/{job_id}")

    assert response.status_code == 202
    assert [call[0] for call in calls] == ["cut", "art", "pip"]
    assert calls[1][1] == job_dir / "edited.mp4"
    assert calls[2][1] == job_dir / "art-text.mp4"
    assert calls[0][3] == [{"start": 0.2, "end": 0.44}]
    assert calls[1][3][0]["start"] == 0.4
    assert calls[1][3][0]["end"] == 0.7
    assert calls[2][3][0]["start"] == 0.4
    assert calls[2][3][0]["end"] == 0.7
    payload = job_response.json()
    assert payload["edit"]["status"] == "completed"
    assert payload["edit"]["outputDuration"] == 0.76
    assert payload["art"]["status"] == "completed"
    assert payload["pictureInPicture"]["status"] == "completed"
    assert payload["pictureInPicture"]["stage"] == "当前预览已生成视频"
    assert payload["composition"]["status"] == "completed"
    assert payload["composition"]["outputUrl"].endswith("/composition-video")
    assert payload["composition"]["historyId"].startswith("history-")
    assert job_dir.is_dir()
    assert video_path.is_file()
    assert (job_dir / "project-state.json").is_file()

    with TestClient(app_module.app) as client:
        output_response = client.get(
            f"/api/transcriptions/{job_id}/composition-video"
        )
        history_response = client.get("/api/history")
    assert output_response.status_code == 200
    assert output_response.content == b"pip"
    assert history_response.json()["count"] == 1
    assert history_response.json()["versions"][0]["kind"] == "composed"


def test_preview_composition_revision_uses_authoritative_cut_draft(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "79797979-7979-4979-8979-797979797979"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
    draft = {
        "schemaVersion": 1,
        "revision": 5,
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
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": "source.mp4",
            "duration": 3.0,
            "status": "completed",
            "result": {"segments": segments, "suggestions": []},
            "cutDraft": draft,
            "edit": None,
            "art": None,
            "pictureInPicture": None,
            "composition": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    captured: list[tuple[list[dict[str, float]], list[dict[str, float]]]] = []

    def capture_composition(
        _job_id: str,
        media: list[dict[str, float]],
        semantic: list[dict[str, float]],
        *_args,
    ) -> None:
        captured.append((media, semantic))

    monkeypatch.setattr(
        app_module,
        "process_preview_composition_job",
        capture_composition,
    )
    monkeypatch.setattr(
        app_module,
        "resolve_cut_draft_acoustic_boundaries",
        lambda *_args, **_kwargs: pytest.fail("生成阶段不得重新执行声学对齐"),
    )

    with TestClient(app_module.app) as client:
        stale = client.post(
            f"/api/transcriptions/{job_id}/compose",
            json={
                "target": "all",
                "ranges": [{"start": 0.95, "end": 2.05}],
                "cutDraftRevision": 4,
            },
        )
        current = client.post(
            f"/api/transcriptions/{job_id}/compose",
            json={
                "target": "all",
                "ranges": [{"start": 0.95, "end": 2.05}],
                "cutDraftRevision": 5,
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
    with app_module.JOBS_LOCK:
        edit = app_module.JOBS[job_id]["edit"]
    assert edit["ranges"] == [{"start": 0.82, "end": 2.14}]
    assert edit["transcriptRanges"] == [{"start": 1.0, "end": 2.0}]


def test_preview_composition_allows_unchanged_timeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "88888888-8888-4888-8888-888888888888"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
    calls: list[list[dict[str, float]]] = []

    def fake_cut(
        input_path: Path,
        output_path: Path,
        ranges: list[dict[str, float]],
        duration: float,
    ) -> None:
        calls.append(ranges)
        output_path.write_bytes(b"unchanged")

    monkeypatch.setattr(app_module, "render_cut_video", fake_cut)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": "source.mp4",
            "duration": 1.0,
            "status": "completed",
            "result": {
                "text": "保留全部",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "保留全部",
                        "words": [
                            {"text": "保留全部", "start": 0.0, "end": 1.0}
                        ],
                    }
                ],
            },
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [],
            "pictureInPictureVideos": [],
            "pictureInPicture": None,
            "composition": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/compose",
            json={"target": "all", "ranges": []},
        )
        payload = client.get(f"/api/transcriptions/{job_id}").json()

    assert response.status_code == 202
    assert calls == [[]]
    assert payload["edit"]["outputDuration"] == 1.0
    assert payload["composition"]["status"] == "completed"
    assert job_dir.is_dir()
    assert video_path.is_file()
    assert (job_dir / "project-state.json").is_file()

    with TestClient(app_module.app) as client:
        output_response = client.get(
            f"/api/transcriptions/{job_id}/composition-video"
        )
    assert output_response.status_code == 200
    assert output_response.content == b"unchanged"


def test_failed_preview_composition_preserves_recoverable_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "99999999-9999-4999-8999-999999999999"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")

    def fail_cut(*args, **kwargs) -> None:
        raise RuntimeError("测试生成失败")

    monkeypatch.setattr(app_module, "render_cut_video", fail_cut)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": "source.mp4",
            "duration": 1.0,
            "status": "completed",
            "result": {
                "text": "生成失败",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "生成失败",
                        "words": [
                            {"text": "生成失败", "start": 0.0, "end": 1.0}
                        ],
                    }
                ],
            },
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [],
            "pictureInPictureVideos": [],
            "pictureInPicture": None,
            "composition": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/compose",
            json={"target": "all", "ranges": []},
        )
        payload = client.get(f"/api/transcriptions/{job_id}").json()

    assert response.status_code == 202
    assert payload["composition"]["status"] == "failed"
    assert payload["composition"]["error"] == "测试生成失败"
    assert job_dir.is_dir()
    assert video_path.is_file()
    assert (job_dir / "project-state.json").is_file()
    assert not list(job_dir.glob(".*.tmp.mp4"))
    assert app_module.JOB_FILES[job_id] == video_path
