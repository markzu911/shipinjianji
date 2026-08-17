from __future__ import annotations

import asyncio
import base64
import io
import json
import subprocess
import unicodedata
from array import array
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import server.app as app_module


@pytest.fixture(autouse=True)
def isolated_jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    runtime_setting_names = (
        "ASR_MODEL",
        "PUNCTUATION_MODEL",
        "SUGGESTION_MODEL",
        "ART_SUGGESTION_MODEL",
        "ART_TEXT_SEGMENTATION_MODEL",
        "PIP_PROMPT_MODEL",
        "PIP_IMAGE_MODEL",
        "PIP_VIDEO_MODEL",
        "ARK_API_BASE_URL",
        "DASHSCOPE_HTTP_API_URL",
        "DASHSCOPE_WEBSOCKET_URL",
    )
    runtime_settings = {
        name: getattr(app_module, name) for name in runtime_setting_names
    }
    dashscope_http_url = app_module.dashscope.base_http_api_url
    dashscope_websocket_url = app_module.dashscope.base_websocket_api_url
    monkeypatch.setattr(app_module, "DATA_DIR", tmp_path)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ASR_API_KEY", raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    with app_module.JOBS_LOCK:
        app_module.JOBS.clear()
        app_module.JOB_FILES.clear()
    yield
    for name, value in runtime_settings.items():
        setattr(app_module, name, value)
    app_module.dashscope.base_http_api_url = dashscope_http_url
    app_module.dashscope.base_websocket_api_url = dashscope_websocket_url


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    path = tmp_path / "sample.mp4"
    command = [
        app_module.get_ffmpeg_binary("ffmpeg"),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=#152433:s=320x180:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=1",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return path


def test_health_reports_media_tools():
    with TestClient(app_module.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["ffmpeg"] is True
    assert response.json()["ffprobe"] is True
    assert response.json()["provider"] == "aliyun-bailian"
    assert response.json()["model"] == "paraformer-realtime-v2"
    assert response.json()["punctuationModel"] == "qwen-plus"
    assert response.json()["suggestionModel"] == "qwen3.7-max"
    assert response.json()["artSuggestionModel"] == "qwen3.6-flash"
    assert response.json()["pictureInPictureImageModel"] == (
        "doubao-seedream-5-0-lite-260128"
    )
    assert response.json()["pictureInPictureVideoModel"] == (
        "doubao-seedance-2-0-260128"
    )
    assert response.json()["seedreamConfigured"] is False
    assert response.json()["seedanceConfigured"] is False
    assert response.json()["configured"] is False


def test_model_settings_mask_credentials_and_list_current_models(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-secret-value")
    monkeypatch.setenv("ARK_API_KEY", "ark-secret-value")

    with TestClient(app_module.app) as client:
        response = client.get("/api/settings/models")

    assert response.status_code == 200
    response_text = response.text
    assert "dashscope-secret-value" not in response_text
    assert "ark-secret-value" not in response_text
    providers = {item["id"]: item for item in response.json()["providers"]}
    assert providers["dashscope"]["configured"] is True
    assert providers["dashscope"]["maskedValue"] == "••••••••"
    assert {item["model"] for item in providers["dashscope"]["models"]} >= {
        app_module.ASR_MODEL,
        app_module.PUNCTUATION_MODEL,
        app_module.SUGGESTION_MODEL,
    }
    assert providers["volcengine"]["configured"] is True
    assert {item["model"] for item in providers["volcengine"]["models"]} == {
        app_module.PIP_IMAGE_MODEL,
        app_module.PIP_VIDEO_MODEL,
    }


def test_model_settings_update_persists_and_applies_without_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text("DATA_DIR=./data\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "ENV_FILE", env_file)

    with TestClient(app_module.app) as client:
        response = client.put(
            "/api/settings/models/dashscope",
            json={
                "apiKey": "new-dashscope-key",
                "models": {
                    "asr": "custom-asr-model",
                    "punctuation": "custom-punctuation-model",
                    "suggestion": "custom-suggestion-model",
                    "artTextSegmentation": "custom-segmentation-model",
                    "artSuggestion": "custom-art-model",
                    "pipPrompt": "custom-prompt-model",
                },
                "requestUrls": {
                    "http": "https://bailian.example.com/api/v1/",
                    "websocket": "wss://bailian.example.com/api-ws/v1/inference",
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["provider"]["configured"] is True
    assert response.json()["provider"]["maskedValue"] == "••••••••"
    assert "new-dashscope-key" not in response.text
    assert app_module.get_asr_api_key() == "new-dashscope-key"
    assert app_module.ASR_MODEL == "custom-asr-model"
    assert app_module.PUNCTUATION_MODEL == "custom-punctuation-model"
    assert app_module.SUGGESTION_MODEL == "custom-suggestion-model"
    assert app_module.ART_TEXT_SEGMENTATION_MODEL == "custom-segmentation-model"
    assert app_module.ART_SUGGESTION_MODEL == "custom-art-model"
    assert app_module.PIP_PROMPT_MODEL == "custom-prompt-model"
    assert app_module.DASHSCOPE_HTTP_API_URL == "https://bailian.example.com/api/v1"
    assert app_module.DASHSCOPE_WEBSOCKET_URL == (
        "wss://bailian.example.com/api-ws/v1/inference"
    )
    assert app_module.dashscope.base_http_api_url == (
        "https://bailian.example.com/api/v1"
    )
    env_text = env_file.read_text(encoding="utf-8")
    assert "DASHSCOPE_API_KEY='new-dashscope-key'" in env_text
    assert "ASR_MODEL='custom-asr-model'" in env_text
    assert "DASHSCOPE_HTTP_API_URL='https://bailian.example.com/api/v1'" in env_text


def test_model_settings_update_volcengine_without_replacing_existing_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text("ARK_API_KEY='existing-ark-key'\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "ENV_FILE", env_file)
    monkeypatch.setenv("ARK_API_KEY", "existing-ark-key")

    with TestClient(app_module.app) as client:
        response = client.put(
            "/api/settings/models/volcengine",
            json={
                "apiKey": None,
                "models": {
                    "image": "custom-image-model",
                    "video": "custom-video-model",
                },
                "requestUrls": {
                    "api": "https://ark.example.com/api/v3/",
                },
            },
        )

    assert response.status_code == 200
    assert app_module.get_ark_api_key() == "existing-ark-key"
    assert app_module.PIP_IMAGE_MODEL == "custom-image-model"
    assert app_module.PIP_VIDEO_MODEL == "custom-video-model"
    assert app_module.ARK_API_BASE_URL == "https://ark.example.com/api/v3"
    env_text = env_file.read_text(encoding="utf-8")
    assert "ARK_API_KEY='existing-ark-key'" in env_text
    assert "SEEDREAM_MODEL='custom-image-model'" in env_text
    assert "SEEDANCE_MODEL='custom-video-model'" in env_text


def test_model_settings_clear_removes_current_and_legacy_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DASHSCOPE_API_KEY='current-key'\nASR_API_KEY='legacy-key'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_module, "ENV_FILE", env_file)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "current-key")
    monkeypatch.setenv("ASR_API_KEY", "legacy-key")

    with TestClient(app_module.app) as client:
        response = client.delete("/api/settings/models/dashscope")

    assert response.status_code == 200
    assert response.json()["provider"]["configured"] is False
    assert "DASHSCOPE_API_KEY" not in env_file.read_text(encoding="utf-8")
    assert "ASR_API_KEY" not in env_file.read_text(encoding="utf-8")
    assert app_module.get_asr_api_key() == ""


def test_model_settings_reject_invalid_provider_and_whitespace_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(app_module, "ENV_FILE", env_file)

    with TestClient(app_module.app) as client:
        invalid_provider = client.put(
            "/api/settings/models/unknown",
            json={"apiKey": "valid-looking-key"},
        )
        invalid_key = client.put(
            "/api/settings/models/volcengine",
            json={"apiKey": "invalid key"},
        )
        invalid_url = client.put(
            "/api/settings/models/volcengine",
            json={"requestUrls": {"api": "ark.example.com/api/v3"}},
        )
        unknown_model = client.put(
            "/api/settings/models/volcengine",
            json={"models": {"unknown": "model-id"}},
        )

    assert invalid_provider.status_code == 404
    assert invalid_key.status_code == 422
    assert invalid_url.status_code == 422
    assert unknown_model.status_code == 422
    assert env_file.read_text(encoding="utf-8") == ""


def test_model_settings_allow_updates_from_remote_clients(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(app_module, "ENV_FILE", env_file)

    with TestClient(app_module.app, client=("192.168.1.25", 53000)) as client:
        settings = client.get("/api/settings/models")
        update = client.put(
            "/api/settings/models/dashscope",
            json={"apiKey": "remote-key"},
        )
    assert settings.status_code == 200
    assert update.status_code == 200
    assert app_module.get_asr_api_key() == "remote-key"
    assert "DASHSCOPE_API_KEY='remote-key'" in env_file.read_text(encoding="utf-8")


def test_model_settings_page_is_available():
    with TestClient(app_module.app) as client:
        response = client.get("/settings")

    assert response.status_code == 200
    assert "模型设置" in response.text
    assert "/settings.js" in response.text


def test_job_cleanup_removes_only_stale_inactive_job_directories(tmp_path: Path):
    jobs_dir = app_module.jobs_directory()
    history_dir = app_module.history_library_directory() / (
        "history-11111111111111111111111111111111"
    )
    old_id = "11111111-1111-4111-8111-111111111111"
    new_id = "22222222-2222-4222-8222-222222222222"
    active_id = "33333333-3333-4333-8333-333333333333"
    overflow_ids = [
        "44444444-4444-4444-8444-444444444444",
        "55555555-5555-4555-8555-555555555555",
        "66666666-6666-4666-8666-666666666666",
    ]

    def make_job_dir(job_id: str, age_days: float, content: bytes = b"x") -> Path:
        path = jobs_dir / job_id
        path.mkdir(parents=True)
        (path / "source.mp4").write_bytes(content)
        modified_at = app_module.time.time() - age_days * 86400
        app_module.os.utime(path, (modified_at, modified_at))
        return path

    old_dir = make_job_dir(old_id, 9, b"old")
    new_dir = make_job_dir(new_id, 1, b"new")
    active_dir = make_job_dir(active_id, 20, b"active")
    invalid_dir = jobs_dir / "not-a-job-id"
    invalid_dir.mkdir()
    history_dir.mkdir(parents=True)
    (history_dir / "video.mp4").write_bytes(b"history")
    with app_module.JOBS_LOCK:
        app_module.JOBS[active_id] = {"id": active_id, "status": "processing"}
        app_module.JOB_FILES[active_id] = active_dir / "source.mp4"

    preview = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
        dry_run=True,
    )

    assert preview["dryRun"] is True
    assert preview["wouldDelete"] == 1
    assert preview["deleted"] == 0
    assert preview["items"][0]["id"] == old_id
    assert preview["items"][0]["reasons"] == ["expired"]
    assert old_dir.exists()

    result = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
        dry_run=False,
    )

    assert result["deleted"] == 1
    assert result["freedBytes"] >= len(b"old")
    assert not old_dir.exists()
    assert new_dir.exists()
    assert active_dir.exists()
    assert invalid_dir.exists()
    assert history_dir.exists()

    for index, job_id in enumerate(overflow_ids):
        make_job_dir(job_id, 2 + index, bytes([index]))

    overflow_result = app_module.cleanup_job_directories(
        max_age_days=999,
        max_directories=2,
        dry_run=False,
    )

    deleted_ids = {item["id"] for item in overflow_result["items"]}
    assert deleted_ids == set(overflow_ids[1:])
    assert (jobs_dir / overflow_ids[0]).exists()
    assert active_dir.exists()


def test_job_cleanup_removes_stale_completed_in_memory_job(tmp_path: Path):
    job_id = "abababab-abab-4bab-8bab-abababababab"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"completed")
    old_time = app_module.time.time() - 8 * 86400
    app_module.os.utime(job_dir, (old_time, old_time))
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {"id": job_id, "status": "completed"}
        app_module.JOB_FILES[job_id] = video_path

    result = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
    )

    assert result["deleted"] == 1
    assert not job_dir.exists()
    assert job_id not in app_module.JOBS
    assert job_id not in app_module.JOB_FILES


def test_periodic_storage_cleanup_runs_after_interval(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[bool] = []
    monkeypatch.setattr(
        app_module,
        "run_storage_maintenance",
        lambda: calls.append(True),
    )

    async def exercise() -> None:
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            app_module.periodic_storage_cleanup(stop_event, interval_seconds=0.01)
        )
        for _ in range(50):
            if calls:
                break
            await asyncio.sleep(0.01)
        stop_event.set()
        await task

    asyncio.run(exercise())

    assert calls


def test_job_cleanup_api_supports_preview_and_execution(tmp_path: Path):
    jobs_dir = app_module.jobs_directory()
    old_id = "77777777-7777-4777-8777-777777777777"
    old_dir = jobs_dir / old_id
    old_dir.mkdir(parents=True)
    (old_dir / "source.mp4").write_bytes(b"cleanup")
    old_time = app_module.time.time() - 4 * 86400
    app_module.os.utime(old_dir, (old_time, old_time))

    with TestClient(app_module.app) as client:
        preview_response = client.post(
            "/api/maintenance/jobs/cleanup",
            json={"maxAgeDays": 3, "maxDirectories": 0, "dryRun": True},
        )
        execute_response = client.post(
            "/api/maintenance/jobs/cleanup",
            json={"maxAgeDays": 3, "maxDirectories": 0, "dryRun": False},
        )

    assert preview_response.status_code == 200
    assert preview_response.json()["wouldDelete"] == 1
    assert execute_response.status_code == 200
    assert execute_response.json()["deleted"] == 1
    assert not old_dir.exists()


def test_failed_transcription_removes_job_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "duration": 1.0,
            "status": "queued",
            "error": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    monkeypatch.setattr(
        app_module,
        "extract_audio",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("测试解析失败")
        ),
    )

    app_module.process_job(job_id)

    with app_module.JOBS_LOCK:
        job = app_module.JOBS[job_id]
    assert job["status"] == "failed"
    assert job["error"] == "测试解析失败"
    assert not job_dir.exists()
    assert job_id not in app_module.JOB_FILES


def test_history_versions_are_persistent_manageable_and_reusable(
    sample_video: Path,
):
    transcript = {
        "text": "历史版本可以继续编辑。",
        "language": "zh",
        "languageProbability": 0.99,
        "duration": 1.0,
        "mediaDuration": 1.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.0,
                "text": "历史版本可以继续编辑。",
                "words": [
                    {"text": "历史版本", "start": 0.0, "end": 0.45},
                    {"text": "可以继续编辑。", "start": 0.45, "end": 1.0},
                ],
            }
        ],
    }
    edited = app_module.save_history_version(
        job_id="source-job",
        kind="edited",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename="口播原片.mp4",
    )
    art = app_module.save_history_version(
        job_id="source-job",
        kind="art",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename="口播原片.mp4",
    )

    with app_module.JOBS_LOCK:
        app_module.JOBS.clear()
        app_module.JOB_FILES.clear()

    with TestClient(app_module.app) as client:
        history_response = client.get("/api/history")
        rename_response = client.patch(
            f"/api/history/{edited['id']}",
            json={"name": "客户确认版"},
        )
        video_response = client.get(f"/api/history/{edited['id']}/video")
        thumbnail_response = client.get(
            f"/api/history/{edited['id']}/thumbnail"
        )
        use_response = client.post(f"/api/history/{art['id']}/use")
        reused_job = client.get(
            f"/api/transcriptions/{use_response.json()['id']}"
        )
        delete_response = client.delete(f"/api/history/{edited['id']}")
        remaining_response = client.get("/api/history")

    assert history_response.status_code == 200
    assert history_response.json()["count"] == 2
    assert history_response.json()["editedCount"] == 1
    assert history_response.json()["artCount"] == 1
    assert {item["kind"] for item in history_response.json()["versions"]} == {
        "edited",
        "art",
    }
    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "客户确认版"
    assert video_response.status_code == 200
    assert video_response.headers["content-type"] == "video/mp4"
    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == "image/jpeg"
    assert use_response.status_code == 201
    assert use_response.json()["status"] == "completed"
    assert use_response.json()["historySource"]["id"] == art["id"]
    assert reused_job.json()["result"]["text"] == transcript["text"]
    assert reused_job.json()["result"]["editableSegments"]
    assert delete_response.status_code == 200
    assert not app_module.history_version_directory(edited["id"]).exists()
    assert remaining_response.json()["count"] == 1
    assert remaining_response.json()["versions"][0]["id"] == art["id"]


def test_history_version_uses_custom_name_or_bounded_safe_default(
    sample_video: Path,
):
    transcript = {
        "text": "安全命名。",
        "duration": 1.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.0,
                "text": "安全命名。",
                "words": [{"text": "安全命名。", "start": 0.0, "end": 1.0}],
            }
        ],
    }
    custom = app_module.save_history_version(
        job_id="custom-name-job",
        kind="art",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename="原片.mp4",
        custom_name="  客户确认版  ",
    )
    default = app_module.save_history_version(
        job_id="safe-default-job",
        kind="edited",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename=f"{'非常长的原视频名称' * 40}.mp4",
    )

    assert custom["name"] == "客户确认版"
    assert 1 <= len(default["name"]) <= 80
    assert "剪辑版" in default["name"]
    assert not any(character in default["name"] for character in '<>:"/\\|?*')


def test_history_limit_keeps_latest_twenty_and_removes_old_directories(
    tmp_path: Path,
):
    records = []
    for index in range(22):
        history_id = f"history-{index:032x}"
        version_dir = app_module.history_version_directory(history_id)
        version_dir.mkdir(parents=True)
        (version_dir / "video.mp4").write_bytes(str(index).encode())
        records.append(
            {
                "id": history_id,
                "name": f"版本 {index}",
                "kind": "composed",
                "duration": 1.0,
                "fileSize": 1,
                "sourceJobId": "source-job",
                "videoFilename": "video.mp4",
                "transcriptFilename": "transcript.json",
                "thumbnailFilename": None,
                "createdAt": f"2026-01-{index + 1:02d}T00:00:00+00:00",
                "updatedAt": f"2026-01-{index + 1:02d}T00:00:00+00:00",
            }
        )
    app_module.save_history_versions_unlocked(records)

    result = app_module.trim_history_versions(max_stored=20)
    retained = app_module.load_history_versions_unlocked()

    assert result["deleted"] == 2
    assert len(retained) == 20
    assert {record["id"] for record in retained} == {
        record["id"] for record in records[2:]
    }
    assert not app_module.history_version_directory(records[0]["id"]).exists()
    assert not app_module.history_version_directory(records[1]["id"]).exists()


def test_frontend_assets_are_versioned_and_not_cached():
    with TestClient(app_module.app) as client:
        page_response = client.get("/")
        styles_response = client.get("/styles.css")
        script_response = client.get("/app.js")
        feedback_script_response = client.get("/ui-feedback.js")
        timeline_script_response = client.get("/timeline-model.js")
        editor_suite_script_response = client.get("/editor-suite.js")
        art_page_response = client.get("/art-text")
        art_script_response = client.get("/art-text.js")
        pip_page_response = client.get("/picture-in-picture")
        pip_script_response = client.get("/picture-in-picture.js")
        template_page_response = client.get("/fonts")
        template_script_response = client.get("/art-template-library.js")
        template_api_response = client.get("/api/art-templates")
        font_page_response = client.get("/font-manager")
        font_script_response = client.get("/font-manager.js")

    assert page_response.status_code == 200
    assert styles_response.status_code == 200
    assert "/app.js?v=20260817-01" in page_response.text
    assert "/styles.css?v=20260814-13" in page_response.text
    assert "/ui-feedback.js?v=20260807-03" in page_response.text
    assert "/timeline-model.js?v=20260810-01" in page_response.text
    assert "/editor-suite.js?v=20260814-02" in page_response.text
    assert timeline_script_response.status_code == 200
    assert timeline_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert "function createStore" in timeline_script_response.text
    assert "function createPointerSession" in timeline_script_response.text
    assert page_response.text.index("/timeline-model.js") < page_response.text.index(
        "/editor-suite.js"
    )
    assert 'class="preview-grid"' in page_response.text
    assert 'data-preview-grid-toggle' in page_response.text
    assert 'data-douyin-preview-toggle' in page_response.text
    assert 'class="cut-preview-mode-controls"' in page_response.text
    assert 'id="editorSuiteDouyinChrome"' in page_response.text
    assert 'class="douyin-status-bar"' not in page_response.text
    assert 'class="douyin-location"' not in page_response.text
    assert 'id="page-title" class="sr-only"' in page_response.text
    assert 'class="hero"' not in page_response.text
    assert "30 FPS" not in page_response.text
    assert "剪辑版与艺术字版分别保存，选择任一版本即可继续处理" not in page_response.text
    assert "汇总文字剪辑、AI 建议、空白剪辑和时间轴" not in page_response.text
    assert "剪辑是可选步骤，你可以直接为原视频添加艺术字或画中画" not in page_response.text
    assert "记录当前视频的剪辑操作" not in page_response.text
    assert "剪辑已完成。你可以基于剪辑视频" not in page_response.text
    assert "原视频仍保留，可重新选择文字生成新版本" not in page_response.text
    assert 'class="progress-live-status"' in page_response.text
    assert 'id="extractStatus">等待处理' in page_response.text
    assert 'id="transcribeStatus">等待处理' in page_response.text
    assert "Paraformer 返回句子和词级时间戳" not in page_response.text
    assert ".progress-live-status {" in styles_response.text
    assert "counter-reset: process-stage;" in styles_response.text
    progress_card_rule = styles_response.text.rsplit(
        "body:not(.has-result) .page-shell:has(#progressCard:not([hidden])) #progressCard {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "min-height: 0;" in progress_card_rule
    assert 'data-editor-suite-nav data-stage="cut"' in page_response.text
    header_start = page_response.text.index('<header class="site-header">')
    editor_suite_start = page_response.text.index('data-editor-suite-nav data-stage="cut"')
    header_actions_start = page_response.text.index('<div class="header-actions">')
    assert header_start < editor_suite_start < header_actions_start
    assert editor_suite_script_response.status_code == 200
    assert "editor-suite:move-finish" in editor_suite_script_response.text
    assert "editor-suite:timeline-action" in editor_suite_script_response.text
    assert "setTimelineTracks" in editor_suite_script_response.text
    assert "job.pictureInPicture?.composition" in editor_suite_script_response.text
    assert "job.art?.composition" in editor_suite_script_response.text
    assert "最终导出会同时保留两种效果" in editor_suite_script_response.text
    assert 'id="editorSuitePreviewOverlay"' in page_response.text
    assert 'id="editorSuiteTimelineLayer"' in page_response.text
    assert 'aria-label="艺术字和画中画叠加片段"' in page_response.text
    assert 'id="editorSuiteInspectorHost"' in page_response.text
    assert 'id="editorSuiteGenerateDock"' not in page_response.text
    assert "data-editor-generate=" not in page_response.text
    assert editor_suite_script_response.text.count("data-editor-suite-generate") == 2
    assert 'data-generation-kind' not in page_response.text
    assert editor_suite_script_response.text.count(
        'class="editor-suite-generate-button"'
    ) == 1
    assert "const generateButtons" not in editor_suite_script_response.text
    assert "const directGenerationSources" not in editor_suite_script_response.text
    assert 'generateButton?.addEventListener("click", generateCurrentPreview)' in (
        editor_suite_script_response.text
    )
    assert 'id="cut-preview-title"' not in page_response.text
    assert 'id="editorSuiteTimelineTitle"' not in page_response.text
    assert 'url.searchParams.set("embedded", "1")' in editor_suite_script_response.text
    assert 'window.history[method]' in editor_suite_script_response.text
    assert 'type: "editor-suite:sync-time"' in editor_suite_script_response.text
    assert 'type: "editor-suite:open-tool"' in editor_suite_script_response.text
    assert 'data.type === "editor-suite:job-state"' in editor_suite_script_response.text
    assert "const cutTabbar" not in editor_suite_script_response.text
    assert "cutTabbar.hidden" not in editor_suite_script_response.text
    assert "cutPanelStack.hidden = !isCut" in editor_suite_script_response.text
    inline_support_start = editor_suite_script_response.text.index(
        "function supportsInlineWorkspace()"
    )
    inline_support_end = editor_suite_script_response.text.index(
        "function currentJobId()", inline_support_start
    )
    inline_support_contract = editor_suite_script_response.text[
        inline_support_start:inline_support_end
    ]
    assert 'stage === "cut"' in inline_support_contract
    assert "cutPanelStack" in inline_support_contract
    assert "cutTabbar" not in inline_support_contract
    assert 'type: "editor-suite:generate-video"' not in editor_suite_script_response.text
    assert 'target: "all"' in editor_suite_script_response.text
    assert '/compose`' in editor_suite_script_response.text
    assert "data-editor-suite-download" in editor_suite_script_response.text
    assert "syncGenerationButton" in editor_suite_script_response.text
    assert "workspaceSourceTime" in editor_suite_script_response.text
    assert 'classList.toggle("has-effect-track", nextState.visible)' in editor_suite_script_response.text
    assert "timelineTrackOffset" in editor_suite_script_response.text
    assert "timelineTrackCount" in editor_suite_script_response.text
    assert 'segment.dataset.timelineTrackIndex' in editor_suite_script_response.text
    assert "select-art-timeline" in editor_suite_script_response.text
    assert "adjust-art-timeline" in editor_suite_script_response.text
    assert 'ensureToolFrame("art", artHref);' in editor_suite_script_response.text
    assert "Math.abs(nextTime - workspaceCurrentTime()) > 0.05" in editor_suite_script_response.text
    assert "Math.abs(childTime - workspaceCurrentTime()) > 0.05" in editor_suite_script_response.text
    assert "function syncMirroredPlayback" in editor_suite_script_response.text
    assert "function scheduleFrameSync" in editor_suite_script_response.text
    assert 'for (const name of frameEntries.keys()) syncFrameTime(name);' in (
        editor_suite_script_response.text
    )
    frame_sync_start = editor_suite_script_response.text.index(
        "function scheduleFrameSync()"
    )
    frame_sync_end = editor_suite_script_response.text.index(
        "function renderActiveTool()", frame_sync_start
    )
    assert 'if (activeTool === "cut") return;' not in (
        editor_suite_script_response.text[frame_sync_start:frame_sync_end]
    )
    assert 'inspectorHost.classList.toggle("is-background", isCut)' in (
        editor_suite_script_response.text
    )
    assert "renderedPreviewState" in editor_suite_script_response.text
    assert "function normalizedToolHref" in editor_suite_script_response.text
    assert 'url.searchParams.delete("embedded")' in editor_suite_script_response.text
    assert "current.frame.dataset.toolHref !== toolHref" in (
        editor_suite_script_response.text
    )
    assert '["art", "pip"]' in editor_suite_script_response.text
    assert 'canvas.dataset.effectKind = layer.kind' in (
        editor_suite_script_response.text
    )
    assert 'kind: "shared"' in editor_suite_script_response.text
    assert "if (effectKind !== activeTool) return;" in (
        editor_suite_script_response.text
    )
    assert 'activeTool !== "cut" && Boolean(state)' not in (
        editor_suite_script_response.text
    )
    assert 'previewVideo?.addEventListener(eventName, scheduleFrameSync)' in editor_suite_script_response.text
    assert "height: auto !important;" in styles_response.text
    assert ".editor-suite-inspector-host" in styles_response.text
    timeline_layer_start = styles_response.text.index(".editor-suite-timeline-layer {")
    timeline_layer_end = styles_response.text.index("}", timeline_layer_start)
    timeline_layer_styles = styles_response.text[timeline_layer_start:timeline_layer_end]
    assert "background: transparent;" in timeline_layer_styles
    assert "border-bottom: 0;" in timeline_layer_styles
    assert 'body[data-active-editor-tool="art"] #cutFrameTimelineText' not in styles_response.text
    assert 'body[data-active-editor-tool="pip"] #cutFrameTimelineText' not in styles_response.text
    assert ".editor-suite-generate-dock" not in styles_response.text
    assert ".editor-suite-generate-button" in styles_response.text
    assert ".editor-suite-generation-runtime" in styles_response.text
    assert ".editor-suite-nav" in styles_response.text
    assert "body.has-result .site-header .editor-suite-nav" in styles_response.text
    assert "body.has-result .site-header .editor-suite-copy" in styles_response.text
    assert "height: calc(100dvh - 65px);" in styles_response.text
    assert feedback_script_response.status_code == 200
    assert 'className = "app-dialog-shell"' in feedback_script_response.text
    assert "window.appConfirm" in feedback_script_response.text
    assert "window.appGeneration" in feedback_script_response.text
    assert "generation-overlay" in styles_response.text
    assert "window.appGeneration?.show" in art_script_response.text
    assert "window.appGeneration?.show" in script_response.text
    assert "window.appGeneration?.show" in pip_script_response.text
    assert "window.confirm" not in script_response.text
    assert 'id="cutOperationLock"' in page_response.text
    assert "setCutOperationLock" in script_response.text
    assert ".cut-operation-lock" in styles_response.text
    assert 'setAttribute("inert", "")' in script_response.text
    assert 'class="ambient-scan"' in page_response.text
    assert 'id="uploadPreview"' in page_response.text
    assert 'id="selectedVideoPreview"' in page_response.text
    assert 'id="changeFileButton"' in page_response.text
    assert 'id="historySourceTab"' in page_response.text
    assert 'id="historySourcePanel"' in page_response.text
    assert 'id="historyList"' in page_response.text
    assert 'id="historyCountBadge"' in page_response.text
    assert "URL.createObjectURL(file)" in script_response.text
    assert "URL.revokeObjectURL(selectedPreviewUrl)" in script_response.text
    assert 'fetch("/api/history")' in script_response.text
    assert "useHistoryVersion" in script_response.text
    assert "renameHistoryVersion" in script_response.text
    assert "deleteHistoryVersion" in script_response.text
    assert ".history-card {" in styles_response.text
    assert ".history-kind-badge {" in styles_response.text
    assert 'id="skipToArtButton"' in page_response.text
    assert 'id="directPipButton"' in page_response.text
    assert 'id="textSuggestionsTab"' not in page_response.text
    assert 'id="suggestionsBlock"' not in page_response.text
    assert 'id="selectAllSuggestionsButton"' not in page_response.text
    assert 'id="suggestionList"' not in page_response.text
    assert 'id="textSilenceTab"' not in page_response.text
    assert 'id="textSilencePanel"' not in page_response.text
    assert 'id="selectAllNoSpeechButton"' not in page_response.text
    assert 'id="noSpeechState"' not in page_response.text
    assert 'id="noSpeechList"' not in page_response.text
    assert 'id="directToolsPrompt"' in page_response.text
    assert 'id="continuePipButton"' in page_response.text
    assert 'selectAllSuggestionsButton.addEventListener("click"' not in script_response.text
    assert "AI 删减建议" not in page_response.text
    assert "已全部删除" not in script_response.text
    assert "const ignoredSuggestions" not in script_response.text
    assert "setCurrentNoSpeechSuggestions" in script_response.text
    assert "seedAutomaticNoSpeechRanges" in script_response.text
    assert "selectedNoSpeechRanges" in script_response.text
    assert "renderNoSpeechSegmentItem" in script_response.text
    assert "一键删除可删片段" not in page_response.text
    assert "可删片段已删除" not in script_response.text
    assert "previewNoSpeechSuggestion" in script_response.text
    assert "setOriginalSourceActionsAllowed(!job.edit?.status);" in script_response.text
    assert "setOriginalSourceActionsAllowed(false);" in script_response.text
    assert "continuePipButton.href" in script_response.text
    assert "source=edited" in script_response.text
    assert 'id="restartProjectButton"' in page_response.text
    assert 'id="result-title"' not in page_response.text
    assert 'class="result-stats"' not in page_response.text
    assert 'id="newUploadButton"' not in page_response.text
    assert "const newUploadButton" not in script_response.text
    assert 'id="cutPreviewVideo"' in page_response.text
    assert 'id="cutFrameTimeline"' in page_response.text
    assert 'id="cutFrameTimelineScroll"' in page_response.text
    assert 'id="cutFrameTimelineTrack"' in page_response.text
    assert 'id="cutFrameTimelineText"' in page_response.text
    assert 'id="cutFrameTimelineThumbnails"' in page_response.text
    assert 'id="cutFrameTimelineRanges"' in page_response.text
    assert 'id="timelineRangeConfirmActions"' not in page_response.text
    assert 'id="cancelTimelineRangeButton"' not in page_response.text
    assert 'id="confirmTimelineRangeButton"' not in page_response.text
    assert "松开后弹窗确认" not in page_response.text
    assert "选区可微调，再次点击确认删除" in page_response.text
    assert "触碰文字时仅吸附完整文字边界" in page_response.text
    assert 'id="clearSelectionButton" class="secondary-button" type="button" disabled hidden' in page_response.text
    assert 'clearSelectionButton.addEventListener("click"' not in script_response.text
    assert 'id="textEditorPreviewPane"' in page_response.text
    assert 'id="textTranscriptTab"' not in page_response.text
    assert 'id="textTranscriptPanel"' not in page_response.text
    assert 'id="transcriptText"' not in page_response.text
    assert 'id="transcriptSegmentList"' not in page_response.text
    assert "识别全文" not in page_response.text
    assert "saveTranscriptText" not in script_response.text
    assert 'class="text-editor-tabbar"' not in page_response.text
    assert 'id="textCutsTab"' not in page_response.text
    assert 'data-text-editor-tab=' not in page_response.text
    assert 'data-text-editor-panel=' not in page_response.text
    assert 'id="textCutsPanel"' in page_response.text
    assert 'aria-labelledby="text-cuts-title"' in page_response.text
    assert 'data-text-editor-tab="silence"' not in page_response.text
    assert 'data-text-editor-panel="silence"' not in page_response.text
    assert 'id="cutUndoButton"' not in page_response.text
    assert 'id="cutRedoButton"' not in page_response.text
    assert 'id="cutHistoryStatus"' not in page_response.text
    assert 'id="cutHistoryList"' not in page_response.text
    assert 'id="textHistoryTab"' not in page_response.text
    assert 'id="textHistoryPanel"' not in page_response.text
    assert "操作记录" not in page_response.text
    assert "function undoCutHistory()" in script_response.text
    assert "function redoCutHistory()" in script_response.text
    assert "handleGlobalCutHistoryShortcut" in script_response.text
    assert "isNativeUndoTarget" in script_response.text
    assert "video-editor:cut-history:${jobId}" in script_response.text
    assert 'stageCutHistoryOperation("删除时间轴区间")' in script_response.text
    assert 'aria-controls="textSilencePanel"' not in page_response.text
    assert 'data-text-editor-tab="output"' not in page_response.text
    assert '>生成结果</button>' not in page_response.text
    output_panel_start = page_response.text.index('id="textOutputPanel"')
    output_panel_end = page_response.text.index('id="textCutsPanel"')
    output_panel_markup = page_response.text[output_panel_start:output_panel_end]
    assert page_response.text.count('id="generateCutButton"') == 1
    assert 'id="generateCutButton"' in output_panel_markup
    assert 'id="outputCutSummary"' in output_panel_markup
    assert 'id="outputCutSelectionDetail"' in output_panel_markup
    assert 'class="editor-suite-generation-runtime"' in output_panel_markup
    assert 'aria-hidden="true"' in output_panel_markup
    assert 'id="generateNoSpeechCutButton"' not in page_response.text
    assert "generateNoSpeechCutButton" not in script_response.text
    assert 'generateCutButton.addEventListener("click", generateCut)' in script_response.text
    assert 'activateTextEditorPanel("output")' not in script_response.text
    assert "updateOriginalSourceActionsVisibility" in script_response.text
    assert "source=original" in script_response.text
    assert "picture-in-picture?job=" in script_response.text
    assert "/original-video`" in script_response.text
    assert "buildCutTimelineThumbnails" in script_response.text
    assert "renderCutTimelineTextSegments" in script_response.text
    assert "cutTimelinePixelsPerSecond" in script_response.text
    assert "CUT_TIMELINE_TEXT_LINES" in script_response.text
    assert "Math.ceil(total / majorStep) + 1" in script_response.text
    assert ".cut-timeline-text-segment {" in styles_response.text
    assert ".cut-frame-timeline .frame-timeline-thumb img {" in styles_response.text
    assert "background-repeat: repeat-x" in styles_response.text
    assert "beginCutTimelineSelection" in script_response.text
    assert "beginTimelineRangeAdjustment" in script_response.text
    assert "skipSelectedRangeDuringPlayback" in script_response.text
    assert "时间轴已自动拼接" in script_response.text
    assert "function getEditedTimelineSpans" in script_response.text
    assert "function editedTimeToSourceTime" in script_response.text
    assert "function sourceTimeToEditedTime" in script_response.text
    assert "getRetainedSegmentParts" in script_response.text
    assert "function updateCutSegmentTimestamps" in script_response.text
    assert 'currentBadge.textContent = "播放中"' in script_response.text
    assert 'playButton.className = "segment-play-button"' in script_response.text
    assert 'playButton.dataset.segmentPreview = "true"' in script_response.text
    assert 'playButton.setAttribute("aria-label", `播放文案：${run.text}`)' in (
        script_response.text
    )
    assert "function previewTextSegment(item)" in script_response.text
    assert "transcriptPreviewRange" in script_response.text
    assert 'event.target.closest(".segment-play-button")' in script_response.text
    assert "function getActiveTranscriptSegmentIndex" in script_response.text
    assert 'nextItem.setAttribute("aria-current", "true")' in script_response.text
    assert "scrollActiveTranscriptSegmentIntoView" in script_response.text
    assert "updateActiveTranscriptSegment(sourceCurrent" in script_response.text
    assert ".segment-item.is-playback-active" in styles_response.text
    assert 'id="cutDraftSaveStatus"' in page_response.text
    assert "function restorePersistedCutDraft" in script_response.text
    assert "function applyPersistedCutDraftAlignment" in script_response.text
    assert "function reconcileCurrentCutHistorySnapshot" in script_response.text
    assert "function scheduleCutDraftSave" in script_response.text
    assert "function clearPersistedCutDraft" in script_response.text
    assert "function resolvePersistedCutDraft" in script_response.text
    assert "window.localStorage.setItem(key" in script_response.text
    assert "/cut-draft`" in script_response.text
    assert "keepalive: true" in script_response.text
    assert "function setCurrentSuggestions" in script_response.text
    assert "function seedAutomaticSuggestionRanges" in script_response.text
    assert "function seedAutomaticNoSpeechRanges" in script_response.text
    assert "if (suggestion.deletable === false) continue" in script_response.text
    assert "const persistedDraft = resolvePersistedCutDraft(" in script_response.text
    assert "job.cutDraft ?? null" in script_response.text
    assert "if (persistedDraft === null)" in script_response.text
    assert "restorePersistedCutDraft(persistedDraft)" in script_response.text
    assert "automaticNoSpeechInitialized" in script_response.text
    assert 'noSpeechStatus === "completed" && !automaticNoSpeechInitialized' in (
        script_response.text
    )
    assert ".cut-draft-save-status" in styles_response.text
    assert 'item.dataset.noSpeechId = range.id' in script_response.text
    assert '"no-speech-restore"' in script_response.text
    assert 'item.classList.toggle("is-removed-from-timeline", !timing)' in script_response.text
    assert "function protectRestoredNoSpeechFromTextRanges" in script_response.text
    assert "...protectRestoredNoSpeechFromTextRanges(textRanges)" in script_response.text
    assert 'stageCutHistoryOperation("恢复空白片段")' in script_response.text
    assert 'stageCutHistoryOperation("删除空白片段")' in script_response.text
    assert "window.EditorSuite?.setCutDraft(state)" in script_response.text
    assert "function buildLiveCutDraftState" in script_response.text
    assert "sourceDuration: cutTimelineDuration()" in script_response.text
    assert "ranges: edit.ranges || edit.requestedRanges || []" in script_response.text
    assert "transcript: edit.transcript || null" in script_response.text
    assert "sourceStart: part.sourceStart" in script_response.text
    assert "sourceStart: wordSourceStart" in script_response.text
    assert "words: part.words" in script_response.text
    assert "const downstreamReady" in editor_suite_script_response.text
    assert "按当前剪后时间添加" in editor_suite_script_response.text
    assert "点击生成视频会一次完成剪辑、艺术字和画中画合成" in (
        editor_suite_script_response.text
    )
    assert "function generationTarget()" not in editor_suite_script_response.text
    assert "function generateCurrentPreview()" in editor_suite_script_response.text
    assert 'target: "all"' in editor_suite_script_response.text
    assert "generationPayload" in editor_suite_script_response.text
    assert 'type: "editor-suite:cut-draft"' in editor_suite_script_response.text
    assert "workspaceCurrentTime" in editor_suite_script_response.text
    assert "setCutDraft," in editor_suite_script_response.text
    assert "const total = editedCutTimelineDuration(spans);" in script_response.text
    assert "function previewSelectedCutRange" in script_response.text
    assert "正在左侧预览裁剪衔接" in script_response.text
    assert script_response.text.count("previewSelectedCutRange(") >= 4
    assert "function getRecognizedSpeechRanges" in script_response.text
    assert "function getRecognizedWordRanges" in script_response.text
    assert "function expandRangeToAdjacentSilence" in script_response.text
    assert "function alignManualRangeToTranscript" in script_response.text
    assert "当前拖动范围落在文字内部" in script_response.text
    assert "边界落在无法安全裁剪的文字内部" in script_response.text
    assert "getEditableSegmentCoverageEnd" in script_response.text
    assert "adjacentSilenceBefore" in script_response.text
    manual_align_start = script_response.text.index(
        "function alignManualRangeToTranscript"
    )
    manual_align_end = script_response.text.index(
        "function getCommittedTimelineDeleteRanges", manual_align_start
    )
    manual_align_script = script_response.text[manual_align_start:manual_align_end]
    assert "expandRangeToAdjacentSilence" not in manual_align_script
    assert "adjacentSilenceBefore: 0" in manual_align_script
    assert "拖动自定义区间" in page_response.text
    assert "时间轴拖动按自定义区间处理" in page_response.text
    assert "前后紧邻的无声区" not in page_response.text
    assert "timelineDeleteRanges" in script_response.text
    assert "getCommittedTimelineDeleteRanges" in script_response.text
    assert "confirmPendingTimelineRange" in script_response.text
    assert "cancelPendingTimelineRange" in script_response.text
    assert "requestTimelineRangeConfirmation" in script_response.text
    assert "timelineRangeConfirmationOpen" in script_response.text
    assert 'cancelButton.className = "cut-timeline-range-cancel"' in script_response.text
    assert 'cancelButton.dataset.timelineRangeAction = "cancel"' in script_response.text
    assert 'cancelIcon.setAttribute("icon", "ph:x-bold")' in script_response.text
    assert 'cancelPendingTimelineRange("已取消时间轴选区。")' in script_response.text
    assert ".cut-timeline-range-cancel {" in styles_response.text
    assert ".cut-timeline-range-cancel iconify-icon {" in styles_response.text
    assert 'rangeElement.dataset.cancelSide' not in script_response.text
    selection_start = script_response.text.index(
        "function beginCutTimelineSelection"
    )
    selection_end = script_response.text.index(
        "function beginTimelineRangeAdjustment", selection_start
    )
    selection_script = script_response.text[selection_start:selection_end]
    assert "requestTimelineRangeConfirmation" not in selection_script
    adjustment_start = selection_end
    adjustment_end = script_response.text.index(
        "function cancelPendingTimelineRange", adjustment_start
    )
    adjustment_script = script_response.text[adjustment_start:adjustment_end]
    assert 'finishEvent.type === "pointerup"' in adjustment_script
    assert 'mode === "move"' in adjustment_script
    assert "if (!hasDragged)" in adjustment_script
    confirmation_start = script_response.text.index(
        "async function requestTimelineRangeConfirmation"
    )
    confirmation_end = script_response.text.index(
        "function adjustTimelineRangeWithKeyboard", confirmation_start
    )
    confirmation_script = script_response.text[
        confirmation_start:confirmation_end
    ]
    assert "cancelPendingTimelineRange();" not in confirmation_script
    assert "已保留待确认区间" in confirmation_script
    assert 'eyebrow: "时间轴滑动删除"' in script_response.text
    assert 'title: "删除这个时间轴区间？"' in script_response.text
    assert 'confirmText: "确认删除"' in script_response.text
    assert "已取消时间轴选区。" in script_response.text
    assert "hasPendingRange || getMergedSelection().length === 0" in script_response.text
    assert "已调整待确认区间" in script_response.text
    assert "CUT_TIMELINE_MIN_RANGE" in script_response.text
    assert "activateTextEditorPanel" not in script_response.text
    assert "splitTextIntoCharacterTokens" in script_response.text
    assert "formatPreciseTime" in script_response.text
    assert "点击左侧圆圈删除整段，再次点击可撤销" not in page_response.text
    assert "仅提示疑似口误、重复、语气词和无效片段" not in page_response.text
    assert "仅检测超过 1.5 秒的无文字区间" not in page_response.text
    assert "圆圈切换删除，点击文案调整分段" in page_response.text
    assert "点击文字删除会一并收紧前后无声区" in page_response.text
    assert "再次点击可撤销" in page_response.text
    assert 'time.textContent = formatTime(segmentStart)' in script_response.text
    assert 'segmentText.className = "segment-text"' in script_response.text
    assert "function suggestionTextRangeKeysAtTime" in script_response.text
    assert "function buildSegmentTextRuns" in script_response.text
    assert "previous.presentationKey === presentationKey" in script_response.text
    assert "item.dataset.displayStart" in script_response.text
    assert "item.dataset.displayEnd" in script_response.text
    assert "item.dataset.displayKey" in script_response.text
    assert '"is-restored-fragment"' in script_response.text
    assert "fragment.append(item)" in script_response.text
    assert 'className = "segment-text-run segment-restore-button"' in script_response.text
    assert "restoreButton.dataset.rangeKeys" in script_response.text
    assert "所有 AI 建议都需由用户确认" not in page_response.text
    assert 'stageCutHistoryOperation("恢复已删除文字")' in script_response.text
    assert "segment-edit-hint" not in script_response.text
    assert "grid-template-columns: 44px 52px minmax(0, 1fr) 44px" in (
        styles_response.text
    )
    assert ".segment-play-button {" in styles_response.text
    assert ".segment-play-button:focus-visible" in styles_response.text
    assert "@media (max-width: 480px)" in styles_response.text
    assert "grid-template-columns: 44px minmax(0, 1fr) 44px" in (
        styles_response.text
    )
    assert "selectSegmentButton.disabled =" in script_response.text
    assert '`${allSelected ? "恢复删除文字" : "删除文字"}：${run.text}`' in script_response.text
    assert 'id="segmentEditDialog"' in page_response.text
    assert 'id="splitSegmentButton"' in page_response.text
    assert 'id="mergeSegmentUpButton"' in page_response.text
    assert 'id="mergeSegmentDownButton"' in page_response.text
    assert "applyEditableSegmentOperation" in script_response.text
    assert "/editable-segments`" in script_response.text
    assert ".segment-edit-dialog {" in styles_response.text
    assert ".cut-timeline-text-segment-label {" in styles_response.text
    assert "text-align-last: justify" in styles_response.text
    assert ".timeline-range-confirm-actions {" not in styles_response.text
    assert ".cut-timeline-delete-range.is-pending {" in styles_response.text
    assert "transcript-segment-text" not in script_response.text
    assert ".text-editor-tabbar {" not in styles_response.text
    assert ".text-editor-tab {" not in styles_response.text
    assert ".cut-history-toolbar {" not in styles_response.text
    assert ".cut-history-panel {" not in styles_response.text
    assert "min-height: 44px" in styles_response.text
    assert 'activateTextEditorPanel("cuts");' not in script_response.text
    assert 'job.edit ? "output" : "cuts"' not in script_response.text
    assert 'words.className = "word-list transcript-word-list"' not in script_response.text
    assert 'characters.className = "word-list"' not in script_response.text
    assert 'event.target.closest(".word-chip")' not in script_response.text
    assert "`${selectedSegmentCount} 段文字`" in script_response.text
    assert r"/\p{P}|\s/u" in script_response.text
    assert 'toDataURL("image/jpeg"' in script_response.text
    assert page_response.headers["cache-control"] == "no-store, max-age=0"
    assert script_response.headers["cache-control"] == "no-store, max-age=0"
    assert feedback_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert "--editor-timeline-track-height: 112px" in styles_response.text
    assert "--editor-timeline-ruler-height: 28px" in styles_response.text
    assert "--editor-timeline-track-height: 74px" in styles_response.text
    assert "--cut-timeline-text-height: 30px" in styles_response.text
    assert ".cut-frame-timeline .frame-timeline-tick-label" in styles_response.text
    assert "top: -7px" in styles_response.text
    assert "width: 100% !important" in styles_response.text
    assert "transform: rotate(0.55deg)" not in styles_response.text
    assert "margin-left: 13px" not in styles_response.text
    assert "margin-left: 9px" not in styles_response.text
    assert "grid-template-columns: 38px minmax(0, 1fr)" in styles_response.text
    assert ".segment-restore-button {" in styles_response.text
    assert ".segment-restore-button:focus-visible" in styles_response.text
    assert ".segment-item.is-no-speech-fragment {" in styles_response.text
    assert ".segment-no-speech-button {" in styles_response.text
    assert ".output-cut-builder {" in styles_response.text
    assert ".cut-timeline-no-speech-range {" in styles_response.text
    assert "grid-template-columns: minmax(0, 1fr) auto" in styles_response.text
    assert styles_response.text.count("height: var(--editor-timeline-track-height)") == 4
    assert "#cutPreviewPlayer:fullscreen .cut-frame-timeline" in styles_response.text
    assert "display: none !important" in styles_response.text
    assert "height: min(72dvh, 840px, calc(100dvh - 112px))" in styles_response.text
    assert art_page_response.status_code == 200
    assert "/art-text.js?v=20260814-02" in art_page_response.text
    assert 'class="cut-progress art-generation-progress full-row"' in art_page_response.text
    assert "art-particle art-particle-1" in art_page_response.text
    assert "解析时间轴" in art_page_response.text
    assert ".art-generation-progress" in styles_response.text
    assert "@keyframes art-particle-float" in styles_response.text
    assert "@keyframes art-panel-scan" in styles_response.text
    assert "/styles.css?v=20260814-10" in art_page_response.text
    assert "/ui-feedback.js?v=20260807-03" in art_page_response.text
    assert 'id="overlayCoordinateReadout"' in art_page_response.text
    assert 'id="positionPresetGrid"' in art_page_response.text
    assert 'id="positionXPercent"' in art_page_response.text
    assert 'id="positionYPercent"' in art_page_response.text
    assert 'aria-label="手动输入艺术字坐标"' in art_page_response.text
    assert "commitPositionCoordinate" in art_script_response.text
    assert ".position-coordinate-fields {" in styles_response.text
    assert "/timeline-model.js?v=20260810-01" in art_page_response.text
    assert "/editor-suite.js?v=20260814-02" in art_page_response.text
    assert 'class="preview-grid"' in art_page_response.text
    assert 'data-preview-grid-toggle' in art_page_response.text
    assert "从保留文案中选择一句" not in art_page_response.text
    assert "播放或拖动视频进度" not in art_page_response.text
    assert "AI 会结合口播文案和低清关键帧拼图" not in art_page_response.text
    assert "关键帧仅临时上传到阿里云百炼，用于本次分析" in art_page_response.text
    assert "可修改文案、时间、位置和模板" not in art_page_response.text
    assert "生成后仍可返回修改参数" not in art_page_response.text
    assert 'data-editor-suite-nav data-stage="art"' in art_page_response.text
    assert 'data-workbench-tab="transcript"' not in art_page_response.text
    assert 'id="transcriptTab"' not in art_page_response.text
    assert 'class="transcript-quick-action"' in art_page_response.text
    assert "一键添加视频文案" in art_page_response.text
    assert "默认使用“热血立体”" in art_page_response.text
    assert "生成统一字号字幕" in art_script_response.text
    assert "TRANSCRIPT_TRACK_MAX_CHARS_PER_CUE = 12" in art_script_response.text
    assert "正在自动整理全文艺术字的内容和时间" in art_script_response.text
    assert "normalizeTranscriptTrackTiming" not in art_script_response.text
    assert "segments: retainedTranscriptSegments" in art_script_response.text
    assert "payload.draftTranscript = cutTranscript;" in art_script_response.text
    assert "Number(pendingCutDraft.duration) || duration" in art_script_response.text
    assert (
        art_script_response.text.count(
            "requestDraftVersion !== transcriptTrackDraftVersion"
        )
        == 2
    )
    assert "window.setTimeout(addFullTranscriptTrack, 0);" in art_script_response.text
    assert "comparableCaptionText(pendingTranscript.text)" not in art_script_response.text
    assert "cutDraftTranscriptTrackCues" in art_script_response.text
    assert "cutDraftTimedTranscriptWords" in art_script_response.text
    assert "segmentLower.indexOf(wordLower, textOffset)" in art_script_response.text
    assert "timedWords.at(-1).text += segmentContent.slice(textOffset)" in (
        art_script_response.text
    )
    assert "replaceTranscriptTrackFromCutDraft" in art_script_response.text
    assert "不会使用剪辑前的旧文案" in art_script_response.text
    assert 'type: "editor-suite:request-cut-draft"' in art_script_response.text
    assert 'data.type === "editor-suite:request-cut-draft"' in (
        editor_suite_script_response.text
    )
    assert "scheduleTranscriptTrackRefresh();" in art_script_response.text
    assert "trackRefreshPending ||" in art_script_response.text
    assert (
        'validationError === "全文艺术字轨道与当前视频文案不一致。"'
        in art_script_response.text
    )
    assert "请删除后重新生成" not in art_script_response.text
    assert "segmentationMethod" in art_script_response.text
    assert "/art-text/transcript-track" in art_script_response.text
    assert "全文艺术字轨道" in art_script_response.text
    assert "rebuildTranscriptTrackLayout" in art_script_response.text
    assert 'fontSize.addEventListener("change"' in art_script_response.text
    assert "trackType" in art_script_response.text
    assert (
        'const TRANSCRIPT_TRACK_DEFAULT_POSITION = { x: 0.5, y: 0.9 };'
        in art_script_response.text
    )
    assert "x: TRANSCRIPT_TRACK_DEFAULT_POSITION.x" in art_script_response.text
    assert "y: TRANSCRIPT_TRACK_DEFAULT_POSITION.y" in art_script_response.text
    assert 'class="art-editor-body"' in art_page_response.text
    assert 'data-workbench-tab="ai"' in art_page_response.text
    assert 'data-workbench-tab="output"' not in art_page_response.text
    assert 'data-workbench-panel="output"' not in art_page_response.text
    assert "生成下载" not in art_page_response.text
    assert 'activateWorkbenchPanel("output")' not in art_script_response.text
    art_output_runtime = art_page_response.text[
        art_page_response.text.index('id="outputPanel"') :
        art_page_response.text.index('id="generateArtVideo"')
    ]
    assert 'class="editor-suite-generation-runtime"' in art_output_runtime
    assert 'aria-hidden="true"' in art_output_runtime
    assert 'id="restartProjectButton"' in art_page_response.text
    assert 'id="aiSuggestionCount"' in art_page_response.text
    assert 'id="aiSuggestionReview"' in art_page_response.text
    assert 'id="selectAllRetainedSegments"' in art_page_response.text
    assert 'id="addSelectedRetainedSegments"' in art_page_response.text
    assert 'id="addAllRetainedSegments"' in art_page_response.text
    assert 'id="retainedBulkMessage"' in art_page_response.text
    assert 'id="retainedText"' in art_page_response.text
    assert 'id="saveRetainedText"' in art_page_response.text
    assert 'id="retainedEditStatus"' in art_page_response.text
    assert "saveRetainedTranscript" in art_script_response.text
    assert 'method: "PUT"' in art_script_response.text
    assert "/transcript`" in art_script_response.text
    assert ".retained-transcript-editor {" in styles_response.text
    assert 'id="applyCurrentSettingsToAll"' in art_page_response.text
    assert 'id="applyAllSettingsMessage"' in art_page_response.text
    assert 'id="fitArtToTranscript"' in art_page_response.text
    assert 'id="artHistoryName"' not in art_page_response.text
    assert 'id="cutHistoryName"' not in page_response.text
    assert "data-editor-suite-save" in editor_suite_script_response.text
    assert "saveCurrentVersion" in editor_suite_script_response.text
    assert '/history`' in editor_suite_script_response.text
    assert 'id="artTimeFitMessage"' in art_page_response.text
    assert 'id="frameTimeline"' in art_page_response.text
    assert 'id="frameTimelineSeek"' in art_page_response.text
    assert 'id="frameTimelineRuler"' in art_page_response.text
    assert 'id="frameTimelineJumpInput"' in art_page_response.text
    assert 'id="frameTimelineJumpButton"' in art_page_response.text
    assert 'id="frameTimelineThumbnails"' in art_page_response.text
    assert 'id="frameTimelineSegments"' in art_page_response.text
    assert 'aria-label="艺术字时间轴"' in art_page_response.text
    assert 'id="frameTimelineScroll"' in art_page_response.text
    assert 'class="frame-timeline editor-layer-timeline"' in art_page_response.text
    overlay_selection_start = art_page_response.text.index(
        'class="overlay-selection-block"'
    )
    custom_text_start = art_page_response.text.index('class="custom-text-row"')
    detail_settings_start = art_page_response.text.index('class="art-detail-heading"')
    overlay_controls_start = art_page_response.text.index('id="overlayControls"')
    assert (
        overlay_selection_start
        < custom_text_start
        < detail_settings_start
        < overlay_controls_start
    )
    assert "点击选择后，在下方修改" in art_page_response.text
    assert 'id="continuePictureInPicture"' in art_page_response.text
    assert 'id="transcriptStyleGrid"' in art_page_response.text
    assert "先选择字幕艺术字类型" in art_page_response.text
    assert "picture-in-picture?job=" in art_script_response.text
    assert 'class="position-grid"' not in art_page_response.text
    assert "positionButtons" not in art_script_response.text
    assert 'id="artVideo" controls' not in art_page_response.text
    assert 'id="finalVideo" controls' not in art_page_response.text
    assert 'data-video-id="artVideo"' in art_page_response.text
    assert 'data-video-id="finalVideo"' in art_page_response.text
    assert art_page_response.text.count("data-media-controls") == 2
    assert "确认后才会添加" in art_page_response.text
    for art_style in (
        "impact",
        "neon",
        "metal",
        "sticker",
        "clean",
        "gradient",
        "comic",
        "ice",
        "ink",
        "ribbon",
        "luxury",
    ):
        assert f'data-art-style="{art_style}"' in art_page_response.text
    assert "restartProjectButton.addEventListener" in art_script_response.text
    assert "activateWorkbenchPanel" in art_script_response.text
    assert "positionPreviewOverlay" in art_script_response.text
    assert "isOverlayVisibleAtTime" in art_script_response.text
    assert "currentTime < end" in art_script_response.text
    assert ".filter(({ overlay }) => isOverlayVisibleAtTime(overlay, currentTime))" in art_script_response.text
    assert "loadFontLibrary" in art_script_response.text
    assert "applyRequestedTemplateSelection" in art_script_response.text
    assert "preferredArtTemplateSettings" in art_script_response.text
    assert "/art-text/suggestions" in art_script_response.text
    assert "confirmAiSuggestionDrafts" in art_script_response.text
    assert "addRetainedSegmentsAsOverlays" in art_script_response.text
    assert "isRetainedSegmentAdded" in art_script_response.text
    assert "normalizeOverlayRange(segment.start, segment.end)" in art_script_response.text
    assert "normalizeOverlayRange(start, end)" in art_script_response.text
    assert "applySelectedSettingsToAllOverlays" in art_script_response.text
    assert "matchingTranscriptSegment" in art_script_response.text
    assert "fitSelectedArtTimeToTranscript" in art_script_response.text
    assert "文案和时间保持不变" in art_script_response.text
    assert "balanceHorizontalLine" in art_script_response.text
    assert "setTranscriptTrackTemplate" in art_script_response.text
    assert 'const TRANSCRIPT_TRACK_DEFAULT_STYLE = "impact";' in art_script_response.text
    assert "selectedStyle = TRANSCRIPT_TRACK_DEFAULT_STYLE" in art_script_response.text
    assert "一键添加视频文案" in art_script_response.text
    assert "setupExternalVideoControls" in art_script_response.text
    assert "requestFullscreen" in art_script_response.text
    assert "buildFrameTimelineThumbnails" in art_script_response.text
    assert "updateFrameTimelineScale" in art_script_response.text
    assert "editor-layer-timeline-segment-label" in art_script_response.text
    assert "renderFrameTimelineRuler" in art_script_response.text
    assert "parseFrameTimelineTimeInput" in art_script_response.text
    assert "jumpToFrameTimelineTime" in art_script_response.text
    assert "refreshFrameTimeline" in art_script_response.text
    assert "renderFrameTimelineOverlaySegments" in art_script_response.text
    assert "FRAME_TIMELINE_TRACK_HEIGHT = 30" in art_script_response.text
    assert "trackIndexes.set(trackKey, trackIndexes.size)" in art_script_response.text
    assert "segment.dataset.timelineTrackIndex" in art_script_response.text
    assert "timelineTrackCount" in art_script_response.text
    assert "beginFrameTimelineSegmentAdjustment" in art_script_response.text
    assert "updateManualOverlayTimelineRange" in art_script_response.text
    assert "function syncFrameTimelineSegmentRange(overlay)" in art_script_response.text
    manual_range_start = art_script_response.text.index(
        "function updateManualOverlayTimelineRange(overlay, start, end)"
    )
    manual_range_end = art_script_response.text.index(
        "function beginFrameTimelineSegmentAdjustment", manual_range_start
    )
    assert "syncFrameTimelineSegmentRange(overlay);" in (
        art_script_response.text[manual_range_start:manual_range_end]
    )
    assert "data-art-time-drag" in art_script_response.text
    assert "segment.dataset.effectStart" in art_script_response.text
    assert "segment.dataset.effectEnd" in art_script_response.text
    assert 'kind: "art"' in art_script_response.text
    assert 'type: "editor-suite:tool-state"' in art_script_response.text
    assert "updateEditorSuiteJobState" in art_script_response.text
    assert "artGenerationObserver" in art_script_response.text
    assert "applyEditorCutDraft" in art_script_response.text
    assert "function retainedTimelineSpans" in art_script_response.text
    assert "function editedRangeForSourceOverlay" in art_script_response.text
    assert "anchorOverlayToSourceTimeline" in art_script_response.text
    assert "buildTranscriptWordMatchIndex" in art_script_response.text
    assert "matchOverlayToTranscriptWords" in art_script_response.text
    assert "previous.end = current.start;" in art_script_response.text
    assert "已按剪后文案的词级时间匹配" in art_script_response.text
    assert "persistEmbeddedArtDraft" in art_script_response.text
    assert "sourceStart: segment.sourceStart" in art_script_response.text
    assert "payload.draftTranscript =" in art_script_response.text
    assert "scheduleTranscriptTrackRefresh" in art_script_response.text
    cut_sync_start = art_script_response.text.index(
        "function applyEditorCutDraft(data)"
    )
    cut_sync_end = art_script_response.text.index(
        "function handleEditorHostMessage", cut_sync_start
    )
    cut_sync_script = art_script_response.text[cut_sync_start:cut_sync_end]
    assert "scheduleTranscriptTrackRefresh();" not in cut_sync_script
    assert "replaceTranscriptTrackFromCutDraft(" in cut_sync_script
    assert "editorHostCurrentTime" in art_script_response.text
    assert "previewVisibilitySignature" in art_script_response.text
    assert "renderPreview({ timeOnly: true })" in art_script_response.text
    assert "renderArtTextCharacters" in art_script_response.text
    assert "alignCharacterTimingsToAudioActivity" in art_script_response.text
    assert "audioQuietRanges: retainedAudioQuietRanges" in art_script_response.text
    assert "compactArtStyleSample" in art_script_response.text
    assert "speechAnimationPreviewSignature" in art_script_response.text
    assert "characterTimings" in art_script_response.text
    assert "spokenDuration + 0.18" in art_script_response.text
    assert '"center-highlight"' in art_script_response.text
    assert '"character-bounce"' in art_script_response.text
    assert "getEditedAudioQuietRanges" in script_response.text
    assert "audioQuietRanges: getEditedAudioQuietRanges(spans)" in script_response.text
    assert "resolveOverlappingRepeatAndQuietRanges" in script_response.text
    assert "protectRecognizedSpeechFromQuietRanges" in script_response.text
    art_sync_start = art_script_response.text.index(
        'if (data.type === "editor-suite:sync-time")'
    )
    art_sync_end = art_script_response.text.index(
        'if (data.type !== "editor-suite:move-effect"', art_sync_start
    )
    art_sync_script = art_script_response.text[art_sync_start:art_sync_end]
    assert "artVideo.currentTime = nextTime" not in art_sync_script
    assert "artVideo.pause()" not in art_sync_script
    assert "已按当前剪后文案实时同步" in art_script_response.text
    assert "剪辑视频生成后即可使用 AI 全文分句" not in art_script_response.text
    assert "beginFrameTimelineScrub" in art_script_response.text
    assert "artTimelineStore" in art_script_response.text
    assert "createPointerSession" in art_script_response.text
    assert 'data.type === "editor-suite:timeline-action"' in art_script_response.text
    assert "toDataURL(\"image/jpeg\"" in art_script_response.text
    assert "const edgeOffset = Math.min(0.04, total / 2)" in art_script_response.text
    assert 'videoSource === "original" && payload.edit?.status' in art_script_response.text
    assert art_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert art_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert pip_page_response.status_code == 200
    assert "/picture-in-picture.js?v=20260812-01" in pip_page_response.text
    assert "/ui-feedback.js?v=20260807-03" in pip_page_response.text
    assert "/styles.css?v=20260812-02" in pip_page_response.text
    assert "/timeline-model.js?v=20260810-01" in pip_page_response.text
    assert "/editor-suite.js?v=20260814-02" in pip_page_response.text
    assert 'class="preview-grid"' in pip_page_response.text
    assert 'data-preview-grid-toggle' in pip_page_response.text
    assert 'data-editor-suite-nav data-stage="pip"' in pip_page_response.text
    assert 'name="assetType" value="video"' in pip_page_response.text
    assert "Seedance 动态镜头" in pip_page_response.text
    assert 'class="pip-editor-body"' in pip_page_response.text
    assert 'id="pipTimelineScroll"' in pip_page_response.text
    assert 'class="frame-timeline editor-layer-timeline pip-timeline"' in pip_page_response.text
    assert 'id="segmentList"' in pip_page_response.text
    assert "time.textContent = formatTime(segment.start)" in pip_script_response.text
    assert "beginPipTimelineSegmentAdjustment" in pip_script_response.text
    assert "pipTimelineStore" in pip_script_response.text
    assert "handle.dataset.timelineResize = mode" in pip_script_response.text
    assert "grid-template-columns: 28px minmax(0, 1fr)" in styles_response.text
    assert "grid-template-columns: 46px minmax(0, 1fr)" in styles_response.text
    assert 'id="pipPrompt"' in pip_page_response.text
    assert 'id="writePipPrompt"' in pip_page_response.text
    assert 'id="promptWriterStatus"' in pip_page_response.text
    assert 'id="pipStartTime"' in pip_page_response.text
    assert 'id="pipEndTime"' in pip_page_response.text
    assert 'id="fitPipToTranscript"' in pip_page_response.text
    assert 'id="pipTimeMessage"' in pip_page_response.text
    assert 'id="pipAspectRatioOptions"' in pip_page_response.text
    for aspect_ratio in ("1:1", "3:4", "4:3", "16:9", "9:16"):
        assert f'value="{aspect_ratio}"' in pip_page_response.text
    assert 'id="generatePipImage"' in pip_page_response.text
    assert "applyEditorCutDraft" in pip_script_response.text
    assert "persistEmbeddedPipDraft" in pip_script_response.text
    assert "start: item.start" in pip_script_response.text
    assert "sourceStart: segment.sourceStart ?? null" in pip_script_response.text
    assert 'id="imageProgress" class="pip-inline-progress pip-tech-progress"' in pip_page_response.text
    assert "pip-tech-particle pip-tech-particle-5" in pip_page_response.text
    assert 'id="generatedList"' in pip_page_response.text
    assert 'id="pipOverlayLayer"' in pip_page_response.text
    assert "选择一段口播文字，生成对应画面" not in pip_page_response.text
    assert "每个画中画独立一条轨道" not in pip_page_response.text
    assert "时间轴显示当前视频" not in pip_page_response.text
    assert "画中画出现后可直接按住拖动摆放" not in pip_page_response.text
    assert "previewHint" not in pip_script_response.text
    assert "PIP_TIMELINE_TRACK_HEIGHT = 30" in pip_script_response.text
    assert "segment.dataset.timelineTrackIndex" in pip_script_response.text
    assert 'const trackLabel = `画中画${index + 1}`;' in pip_script_response.text
    assert "label.textContent = trackLabel" in pip_script_response.text
    assert (
        'segment.title = `${trackLabel} ${formatRange(item.start, item.end)}`'
        in pip_script_response.text
    )
    assert "timelineTrackCount" in pip_script_response.text
    assert 'type: "editor-suite:select-pip-timeline"' in editor_suite_script_response.text
    assert 'data.type === "editor-suite:select-pip-timeline"' in pip_script_response.text
    assert "拖动边框缩放" in pip_page_response.text
    assert "beginPictureResize" in pip_script_response.text
    assert "pictureResizeWidth" in pip_script_response.text
    assert 'handle.className = "pip-resize-handle"' in pip_script_response.text
    assert 'data.type === "editor-suite:resize-effect"' in pip_script_response.text
    assert 'type: "editor-suite:resize-effect"' in editor_suite_script_response.text
    assert ".pip-resize-handle" in styles_response.text
    assert '[data-pip-resize="se"]' in styles_response.text
    assert 'kind: "pip"' in pip_script_response.text
    assert 'type: "editor-suite:tool-state"' in pip_script_response.text
    assert "updateEditorSuiteJobState" in pip_script_response.text
    assert "pipGenerationObserver" in pip_script_response.text
    assert 'id="pipTimelineThumbnails"' in pip_page_response.text
    assert 'id="generatePipVideo"' in pip_page_response.text
    assert 'class="pip-output-section editor-suite-generation-runtime"' in pip_page_response.text
    assert 'document.querySelector(".pip-output-section")?.scrollIntoView' not in pip_script_response.text
    assert "Seedream · Seedance" in pip_page_response.text
    assert 'assetType === "video" ? "videos" : "images"' in pip_script_response.text
    assert "pollGeneratedAssets" in pip_script_response.text
    assert "imageProgress.dataset.assetType = assetType" in pip_script_response.text
    assert '"--pip-progress"' in pip_script_response.text
    assert "writePromptDraft" in pip_script_response.text
    assert "fitPipTimeToTranscript" in pip_script_response.text
    assert "currentPipTimeRange" in pip_script_response.text
    assert "start: timeRange.start" in pip_script_response.text
    assert "end: timeRange.end" in pip_script_response.text
    assert "/picture-in-picture/prompt" in pip_script_response.text
    assert 'const endpoint = useComposition ? "compose" : "picture-in-picture"' in (
        pip_script_response.text
    )
    assert "pictureInPictureOverlays: overlays" in pip_script_response.text
    assert 'const endpoint = useComposition ? "compose" : "art-text"' in (
        art_script_response.text
    )
    assert "AI 根据文字智能生成" in pip_script_response.text
    assert "aspectRatio: currentImageAspectRatio()" in pip_script_response.text
    assert '"original", "edited", "art"' in pip_script_response.text
    assert "source: requestedSource" in pip_script_response.text
    assert "renderPreview" in pip_script_response.text
    assert "editorHostCurrentTime" in pip_script_response.text
    assert "previewVisibilitySignature" in pip_script_response.text
    assert "renderPreview({ timeOnly: true })" in pip_script_response.text
    pip_sync_start = pip_script_response.text.index(
        'if (data.type === "editor-suite:sync-time")'
    )
    pip_sync_end = pip_script_response.text.index(
        'if (data.type !== "editor-suite:move-effect"', pip_sync_start
    )
    pip_sync_script = pip_script_response.text[pip_sync_start:pip_sync_end]
    assert "pipVideo.currentTime = nextTime" not in pip_sync_script
    assert "pipVideo.pause()" not in pip_sync_script
    assert "buildPipTimelineThumbnails" in pip_script_response.text
    assert 'toDataURL("image/jpeg"' in pip_script_response.text
    assert "beginPictureDrag" in pip_script_response.text
    assert "setPointerCapture" in pip_script_response.text
    assert "constrainPictureItemToStage" in pip_script_response.text
    assert 'requestedSource === "original"' in pip_script_response.text
    assert "payload.edit?.status" in pip_script_response.text
    assert "参考当前视频画面的色调、光线和质感" in pip_page_response.text
    assert "min-height: 132px" in styles_response.text
    assert ".pip-output-progress.pip-tech-progress" in styles_response.text
    assert "@keyframes pip-tech-particle-drift" in styles_response.text
    assert ".pip-generated-card.is-processing .pip-image-preview-button::after" in styles_response.text
    assert "#pipVideoPlayer:fullscreen .pip-video-stage" in styles_response.text
    assert "height: calc(100dvh - 88px)" in styles_response.text
    assert "updatePipTimelineScale" in pip_script_response.text
    assert "pipTimelineMajorStep" in pip_script_response.text
    assert pip_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert editor_suite_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert pip_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert template_page_response.status_code == 200
    assert "/styles.css?v=20260812-02" in template_page_response.text
    assert "/art-template-library.js?v=20260812-02" in template_page_response.text
    assert "当前模板主色" in template_page_response.text
    assert 'id="templateCardGrid"' in template_page_response.text
    assert 'id="useTemplateButton"' in template_page_response.text
    assert 'id="openTemplateUpload"' in template_page_response.text
    assert 'id="templateUploadDialog"' in template_page_response.text
    assert 'id="renameTemplateButton"' in template_page_response.text
    assert 'id="deleteTemplateButton"' in template_page_response.text
    assert "艺术字效果模板库" in template_page_response.text
    assert "上传和管理可编辑效果模板" not in template_page_response.text
    assert "templateDetailNote" not in template_page_response.text
    assert "templateDetailNote" not in template_script_response.text
    assert "点击恢复后重新出现在模板库" in template_page_response.text
    assert "/api/art-templates" in template_script_response.text
    assert "preferredArtTemplateSettings" in template_script_response.text
    assert "characterLayout" in art_script_response.text
    assert "is-character-staggered" in template_script_response.text
    assert "const effects = normalizedTemplateEffects(template, color);" in (
        template_script_response.text
    )
    assert "function fitEffectPreviewText(element)" in (
        template_script_response.text
    )
    assert "const templateColors = new Map();" in template_script_response.text
    assert "function templateColorFor(template)" in template_script_response.text
    assert "templateColors.set(template.id, templatePreviewColor.value);" in (
        template_script_response.text
    )
    assert 'window.addEventListener("resize", scheduleEffectPreviewFit);' in (
        template_script_response.text
    )
    assert 'method: "PATCH"' in template_script_response.text
    assert 'method: "DELETE"' in template_script_response.text
    assert "loadArtTemplateLibrary" in art_script_response.text
    assert "ART_STYLE_BASES" in art_script_response.text
    assert "renderTemplateCharacters" in template_script_response.text
    assert 'type: "character-bounce"' in template_script_response.text
    assert template_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert template_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert template_api_response.status_code == 200
    assert template_api_response.json()["count"] == 11
    assert template_api_response.json()["builtinCount"] == 11
    assert template_api_response.json()["uploadedCount"] == 0
    assert {
        template["id"]
        for template in template_api_response.json()["templates"]
    } == app_module.ART_TEXT_STYLES
    assert font_page_response.status_code == 200
    assert "/styles.css?v=20260812-02" in font_page_response.text
    assert "/font-manager.js?v=" in font_page_response.text
    assert 'id="fontUploadForm"' in font_page_response.text
    assert 'id="fontCardGrid"' in font_page_response.text
    assert "上传 TTF 或 OTF 字体" not in font_page_response.text
    assert "可以查看完整预览、设置默认字体" not in font_page_response.text
    assert "请确认拥有字体使用权" in font_page_response.text
    assert "/api/fonts" in font_script_response.text
    assert "registerUploadedFont" in font_script_response.text
    assert font_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert font_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert ".hero" not in styles_response.text
    assert "studio-wave-breathe" not in styles_response.text
    assert ".section-helper" not in styles_response.text
    assert ".next-step-copy" not in styles_response.text
    assert ".output-note" not in styles_response.text
    assert ".template-library-note" not in styles_response.text


def test_timeline_model_shares_selection_drag_resize_and_persistence():
    script = r"""
const timeline = require('./web/timeline-model.js');
const commits = [];
const store = timeline.createStore({
  duration: 12,
  tracks: [
    { id: 'cut:deletions', kind: 'cut', clips: [
      { id: 'cut:1', start: 1, end: 2, minDuration: 0.1 }
    ] },
    { id: 'art:overlay:1', kind: 'art', clips: [
      { id: 'art:1', start: 2, end: 4, minDuration: 0.1 }
    ] },
    { id: 'pip:track:1', kind: 'pip', clips: [
      { id: 'pip:1', start: 5, end: 8, minDuration: 0.1, payload: { width: 0.3 } }
    ] }
  ]
}, { onCommit: (state, reason) => commits.push({ state, reason }) });

store.selectClip('art:1');
const move = timeline.createPointerSession(store, {
  clipId: 'art:1', mode: 'move', startClientX: 100,
  trackWidth: 1200, duration: 12
});
move.update(300);
move.finish();
const moved = store.findClip('art:1');
if (moved.start !== 4 || moved.end !== 6) throw new Error('move failed');

const resize = timeline.createPointerSession(store, {
  clipId: 'pip:1', mode: 'start', startClientX: 0,
  trackWidth: 1200, duration: 12
});
resize.update(200);
resize.finish();
const resized = store.findClip('pip:1');
if (resized.start !== 7 || resized.end !== 8) throw new Error('resize failed');

const boundaryMove = timeline.createPointerSession(store, {
  clipId: 'art:1', mode: 'move', startClientX: 0,
  trackWidth: 1200, duration: 12
});
boundaryMove.update(2400);
boundaryMove.finish({ commit: false });
const bounded = store.findClip('art:1');
if (bounded.start !== 10 || bounded.end !== 12) {
  throw new Error('boundary move changed clip duration');
}

const boundaryResize = timeline.createPointerSession(store, {
  clipId: 'pip:1', mode: 'start', startClientX: 0,
  trackWidth: 1200, duration: 12
});
boundaryResize.update(1200);
boundaryResize.finish({ commit: false });
const minSized = store.findClip('pip:1');
if (minSized.start !== 7.9 || minSized.end !== 8) {
  throw new Error('boundary resize moved the fixed edge');
}

store.patchClipPayload('pip:1', { width: 0.42 }, { commit: true });
if (store.findClip('pip:1').payload.width !== 0.42) throw new Error('payload failed');

const values = new Map();
const storage = {
  setItem: (key, value) => values.set(key, value),
  getItem: (key) => values.get(key) || null
};
if (!timeline.saveDraft(storage, 'project', store.snapshot(), { name: 'draft' })) {
  throw new Error('save failed');
}
const restored = timeline.loadDraft(storage, 'project');
if (restored.metadata.name !== 'draft') throw new Error('metadata failed');
if (restored.timeline.tracks.length !== 3) throw new Error('tracks failed');
if (commits.length !== 3) throw new Error('commit mechanism failed');
console.log(JSON.stringify({ commits: commits.length, selection: store.snapshot().selection }));
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the timeline model unit test.")

    payload = json.loads(result.stdout)
    assert payload["commits"] == 3
    assert payload["selection"]["clipId"] == "pip:1"


def test_douyin_preview_is_inline_only():
    with TestClient(app_module.app) as client:
        page_response = client.get("/")
        removed_page_response = client.get("/douyin-preview")
        removed_script_response = client.get("/douyin-preview.js")
        styles_response = client.get("/styles.css")
        editor_suite_script_response = client.get("/editor-suite.js")
        feedback_script_response = client.get("/ui-feedback.js")

    assert page_response.status_code == 200
    assert removed_page_response.status_code == 404
    assert removed_script_response.status_code == 404
    assert styles_response.status_code == 200
    assert editor_suite_script_response.status_code == 200
    assert feedback_script_response.status_code == 200

    assert 'data-douyin-preview-toggle' in page_response.text
    assert 'id="editorSuiteDouyinChrome"' in page_response.text
    assert 'class="douyin-action-bar"' in page_response.text
    assert 'class="douyin-bottom-nav"' in page_response.text
    assert ".douyin-caption-block {" in styles_response.text
    assert ".douyin-action-bar {" in styles_response.text
    assert ".douyin-top-bar {" in styles_response.text
    assert ".douyin-feed-tabs {" in styles_response.text
    assert ".douyin-status-bar {" not in styles_response.text
    assert 'class="douyin-status-bar"' not in page_response.text
    assert 'class="douyin-content-type"' not in page_response.text
    assert "font-size: clamp(8px, 3.8cqw, 13px)" in styles_response.text
    assert "font-size: clamp(7px, 3.2cqw, 11px)" in styles_response.text
    assert 'class="douyin-action-button is-liked"' in page_response.text
    assert page_response.text.count('class="douyin-action-button') == 4
    assert page_response.text.count('tabindex="-1"') >= 4
    assert 'class="douyin-music-disc"' in page_response.text
    assert "douyin-shoot-same" not in page_response.text
    assert ".douyin-location {" not in styles_response.text
    assert ".douyin-content-type {" not in styles_response.text
    assert "--iphone-screen-width: 440" in styles_response.text
    assert "--iphone-screen-height: 956" in styles_response.text
    assert "--iphone-safe-top: 6.4854%" in styles_response.text
    assert "--iphone-safe-bottom: 3.5565%" in styles_response.text
    assert "--iphone-safe-top-space: 14.0909cqw" in styles_response.text
    assert "--iphone-safe-bottom-space: 7.7273cqw" in styles_response.text
    assert "var(--iphone-safe-top) + var(--douyin-header-content-height)" in (
        styles_response.text
    )
    assert "var(--iphone-safe-bottom) + var(--douyin-tabbar-content-height)" in (
        styles_response.text
    )
    assert "--douyin-video-bottom: var(--douyin-tabbar-height)" in (
        styles_response.text
    )
    assert "aspect-ratio: 440 / 956 !important" in styles_response.text
    assert "padding: var(--iphone-safe-top-space) var(--douyin-side-inset) 0" in (
        styles_response.text
    )
    assert "padding: 0 var(--douyin-side-inset) var(--iphone-safe-bottom-space)" in (
        styles_response.text
    )
    assert "bottom: var(--douyin-content-bottom)" in styles_response.text
    assert "object-fit: contain" in styles_response.text
    douyin_video_rule = styles_response.text.split(
        ".cut-video-stage.is-douyin-preview #cutPreviewVideo {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "top: 0;" in douyin_video_rule
    assert "height: calc(100% - var(--douyin-video-bottom));" in douyin_video_rule
    assert "object-fit: cover;" in douyin_video_rule
    douyin_base_video_rule = styles_response.text.split(
        ".editor-suite-douyin-base-video {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "top: 0;" in douyin_base_video_rule
    assert (
        "height: calc(100% - var(--douyin-video-bottom, 0%));"
        in douyin_base_video_rule
    )
    assert "object-fit: cover;" in douyin_base_video_rule
    assert "const fitScale = douyinPreviewEnabled ? Math.max : Math.min;" in (
        editor_suite_script_response.text
    )
    assert "const scale = fitScale(" in editor_suite_script_response.text
    douyin_overlay_rule = styles_response.text.split(
        ".cut-video-stage.is-douyin-preview .editor-suite-preview-overlay {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "inset: 0 0 var(--douyin-video-bottom);" in douyin_overlay_rule
    douyin_top_bar_rule = styles_response.text.rsplit(
        ".douyin-top-bar {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "background: transparent;" in douyin_top_bar_rule
    assert "backdrop-filter: none;" in douyin_top_bar_rule
    douyin_bottom_nav_rule = styles_response.text.rsplit(
        ".douyin-bottom-nav {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "background: transparent;" in douyin_bottom_nav_rule
    assert ".cut-video-stage.is-douyin-preview .editor-suite-preview-overlay" in (
        styles_response.text
    )
    assert "width: min(100%, 360px) !important" in styles_response.text
    assert ".editor-suite-douyin-base-video" in styles_response.text
    assert "grid-template-rows: minmax(0, 1fr)" in styles_response.text
    assert "container-type: inline-size" in styles_response.text
    assert "--douyin-action-gap: 5.6818cqw" in styles_response.text
    assert "--douyin-action-right: 1.3636%" in styles_response.text
    assert "--douyin-action-top: 48.954%" in styles_response.text
    assert "clamp(20px, 7.7273cqw, 34px)" in styles_response.text
    assert "bottom: 9.728%" in styles_response.text
    assert "clamp(20px, 10cqw, 34px)" in styles_response.text
    assert ".douyin-music-disc {" in styles_response.text
    assert ".douyin-safety-zone" not in styles_response.text
    assert "@keyframes art-character-bounce" in styles_response.text
    assert "prefers-reduced-motion: reduce" in styles_response.text
    assert ".art-style-sample.has-character-effect" in styles_response.text
    assert "animation-fill-mode: forwards" in styles_response.text
    assert ".art-character.is-character-staggered" in styles_response.text
    assert ".template-card-preview.has-character-effect" in styles_response.text
    assert "flex: 0 0 178px" in styles_response.text

    assert 'data-douyin-preview href' not in editor_suite_script_response.text
    assert "setDouyinPreviewLink" not in editor_suite_script_response.text
    assert "setDouyinPreviewAvailable" in editor_suite_script_response.text
    assert "setDouyinPreviewEnabled" in editor_suite_script_response.text
    assert "function updateDouyinBaseVideo" in editor_suite_script_response.text
    assert "has-douyin-edited-base" in editor_suite_script_response.text
    assert "douyinVideoZoom" not in editor_suite_script_response.text
    assert "is-douyin-preview" in editor_suite_script_response.text
    assert "/douyin-preview?job=" not in editor_suite_script_response.text
    assert "repeat(3, minmax(0, 1fr))" in styles_response.text
    assert "is-douyin-preview" in feedback_script_response.text
    assert "stage.parentElement?.querySelector" in feedback_script_response.text


def test_art_template_library_upload_rename_render_and_delete(tmp_path: Path):
    template_payload = {
        "name": "我的蓝色立体字",
        "sample": "蓝色",
        "description": "蓝色主色与深蓝描边的立体艺术字。",
        "baseStyle": "impact",
        "color": "#59C7FF",
        "strokeColor": "#102A43",
        "letterSpacing": 6,
        "textColorMode": "center-highlight",
        "secondaryColor": "#FFFFFF",
        "animation": {
            "type": "character-bounce",
            "duration": 0.56,
            "stagger": 0.07,
            "amplitude": 0.18,
        },
        "characterLayout": {
            "type": "staggered",
            "rotationPattern": [-8, 6, -4],
            "verticalOffsetPattern": [0.06, -0.04, 0.03],
        },
    }

    with TestClient(app_module.app) as client:
        upload_response = client.post(
            "/api/art-templates",
            files={
                "file": (
                    "blue-impact.arttext",
                    io.BytesIO(
                        json.dumps(
                            template_payload,
                            ensure_ascii=False,
                        ).encode("utf-8")
                    ),
                    "application/json",
                )
            },
        )
        assert upload_response.status_code == 201
        uploaded = upload_response.json()
        assert uploaded["source"] == "uploaded"
        assert uploaded["id"].startswith("custom-art-")
        assert uploaded["baseStyle"] == "impact"
        assert uploaded["textColorMode"] == "center-highlight"
        assert uploaded["secondaryColor"] == "#FFFFFF"
        assert uploaded["letterSpacing"] == 6
        assert uploaded["animation"] == template_payload["animation"]
        assert uploaded["characterLayout"] == template_payload["characterLayout"]

        library_response = client.get("/api/art-templates")
        assert library_response.json()["uploadedCount"] == 1
        assert library_response.json()["count"] == 12

        rename_response = client.patch(
            f"/api/art-templates/{uploaded['id']}",
            json={"name": "蓝色重点标题"},
        )
        assert rename_response.status_code == 200
        assert rename_response.json()["name"] == "蓝色重点标题"

        normalized = app_module.normalize_text_overlays(
            [
                app_module.TextOverlay(
                    text="自定义艺术字",
                    font="bold",
                    fontSize=48,
                    color=uploaded["color"],
                    strokeColor=uploaded["strokeColor"],
                    strokeWidth=2,
                    shadow=True,
                    x=0.5,
                    y=0.5,
                    start=0,
                    end=1,
                    letterSpacing=uploaded["letterSpacing"],
                    artStyle=uploaded["id"],
                    textColorMode=uploaded["textColorMode"],
                    secondaryColor=uploaded["secondaryColor"],
                    animation=app_module.ArtTextAnimation(
                        **uploaded["animation"]
                    ),
                    characterLayout=app_module.ArtTextCharacterLayout(
                        **uploaded["characterLayout"]
                    ),
                )
            ],
            1,
        )
        assert normalized[0]["artStyle"] == uploaded["id"]
        assert normalized[0]["textColorMode"] == "center-highlight"
        assert normalized[0]["secondaryColor"] == "#FFFFFF"
        assert normalized[0]["letterSpacing"] == 6
        assert normalized[0]["animation"]["type"] == "character-bounce"
        assert normalized[0]["characterLayout"] == template_payload["characterLayout"]
        output_path = tmp_path / "custom-art-template-layer.png"
        app_module.render_art_text_layer(output_path, normalized[0])
        assert output_path.is_file()

        delete_response = client.delete(
            f"/api/art-templates/{uploaded['id']}"
        )
        assert delete_response.status_code == 200
        assert delete_response.json() == {"status": "deleted"}
        assert app_module.resolve_art_text_style(uploaded["id"]) is None


def test_art_template_library_rejects_font_upload():
    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/art-templates",
            files={
                "file": (
                    "wrong-font.ttf",
                    io.BytesIO(b"not an art template"),
                    "font/ttf",
                )
            },
        )
    assert response.status_code == 400
    assert "不支持字体文件" in response.json()["detail"]


def test_art_template_library_rejects_unknown_character_animation():
    payload = {
        "name": "错误动画",
        "sample": "测试",
        "baseStyle": "comic",
        "color": "#FFF36A",
        "strokeColor": "#0A0A0A",
        "animation": {"type": "spin-away"},
    }
    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/art-templates",
            files={
                "file": (
                    "invalid-animation.arttext",
                    io.BytesIO(
                        json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    ),
                    "application/json",
                )
            },
        )

    assert response.status_code == 400
    assert "动画类型无效" in response.json()["detail"]


def test_art_template_hide_and_restore():
    with TestClient(app_module.app) as client:
        before = client.get("/api/art-templates").json()
        assert before["hiddenCount"] == 0
        assert any(t["id"] == "impact" for t in before["templates"])

        hide_response = client.delete("/api/art-templates/impact")
        assert hide_response.status_code == 200
        assert hide_response.json() == {"status": "hidden"}

        hidden = client.get("/api/art-templates").json()
        assert hidden["hiddenCount"] == 1
        assert hidden["builtinCount"] == before["builtinCount"] - 1
        assert not any(t["id"] == "impact" for t in hidden["templates"])
        assert any(t["id"] == "impact" for t in hidden["hiddenBuiltins"])

        restore_response = client.post("/api/art-templates/impact/restore")
        assert restore_response.status_code == 200
        assert restore_response.json() == {"status": "restored"}

        restored = client.get("/api/art-templates").json()
        assert restored["hiddenCount"] == 0
        assert any(t["id"] == "impact" for t in restored["templates"])

        missing_delete = client.delete("/api/art-templates/not-a-template")
        assert missing_delete.status_code == 404
        missing_restore = client.post(
            "/api/art-templates/not-a-template/restore"
        )
        assert missing_restore.status_code == 404


def test_art_position_presets_crud():
    with TestClient(app_module.app) as client:
        create_response = client.post(
            "/api/art-position-presets",
            json={"name": "右上角", "x": 0.8, "y": 0.2},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["id"].startswith("pos-")
        assert created["name"] == "右上角"
        assert created["x"] == 0.8
        assert created["y"] == 0.2
        assert created["createdAt"] is not None

        list_response = client.get("/api/art-position-presets")
        assert list_response.status_code == 200
        assert list_response.json()["count"] == 1
        assert list_response.json()["presets"][0]["id"] == created["id"]

        patch_response = client.patch(
            f"/api/art-position-presets/{created['id']}",
            json={"name": "右上标题", "x": 0.82, "y": 0.18},
        )
        assert patch_response.status_code == 200
        updated = patch_response.json()
        assert updated["name"] == "右上标题"
        assert updated["x"] == 0.82
        assert updated["y"] == 0.18

        delete_response = client.delete(
            f"/api/art-position-presets/{created['id']}"
        )
        assert delete_response.status_code == 200
        assert delete_response.json() == {"status": "deleted"}

        missing_response = client.delete(
            f"/api/art-position-presets/{created['id']}"
        )
        assert missing_response.status_code == 404


def test_art_position_presets_validation():
    with TestClient(app_module.app) as client:
        empty_name_response = client.post(
            "/api/art-position-presets",
            json={"name": "   ", "x": 0.5, "y": 0.5},
        )
        assert empty_name_response.status_code == 400
        assert "名称不能为空" in empty_name_response.json()["detail"]

        clamp_response = client.post(
            "/api/art-position-presets",
            json={"name": "越界坐标", "x": 1.5, "y": -0.3},
        )
        assert clamp_response.status_code == 201
        assert clamp_response.json()["x"] == 0.95
        assert clamp_response.json()["y"] == 0.05

        duplicate_name_response = client.post(
            "/api/art-position-presets",
            json={"name": "重复名称", "x": 0.5, "y": 0.5},
        )
        assert duplicate_name_response.status_code == 201

        missing_patch_response = client.patch(
            "/api/art-position-presets/pos-does-not-exist",
            json={"name": "改名"},
        )
        assert missing_patch_response.status_code == 404


def test_font_library_upload_rename_render_and_delete(tmp_path: Path):
    source_font = app_module.ART_TEXT_FONTS["classic"]
    if not source_font.is_file():
        pytest.skip("Windows test font is unavailable")

    with TestClient(app_module.app) as client:
        initial_response = client.get("/api/fonts")
        assert initial_response.status_code == 200
        assert initial_response.json()["builtinCount"] >= 1

        with source_font.open("rb") as handle:
            upload_response = client.post(
                "/api/fonts",
                files={"file": ("custom-title.ttf", handle, "font/ttf")},
            )
        assert upload_response.status_code == 201
        uploaded = upload_response.json()
        assert uploaded["source"] == "uploaded"
        assert uploaded["id"].startswith("custom-")
        assert uploaded["fileUrl"].endswith("/file")

        rename_response = client.patch(
            f"/api/fonts/{uploaded['id']}",
            json={"name": "我的标题字体"},
        )
        assert rename_response.status_code == 200
        assert rename_response.json()["name"] == "我的标题字体"

        file_response = client.get(uploaded["fileUrl"])
        assert file_response.status_code == 200
        assert len(file_response.content) > 1000

        output_path = tmp_path / "custom-font-layer.png"
        app_module.render_art_text_layer(
            output_path,
            {
                "text": "自定义字体",
                "font": uploaded["id"],
                "fontSize": 48,
                "color": "#FFFFFF",
                "strokeColor": "#071018",
                "strokeWidth": 2,
                "shadow": True,
                "direction": "horizontal",
                "textAlign": "center",
                "charsPerLine": 10,
                "letterSpacing": 0,
                "lineSpacing": 8,
                "artStyle": "clean",
            },
        )
        assert output_path.is_file()

        delete_response = client.delete(f"/api/fonts/{uploaded['id']}")
        assert delete_response.status_code == 200
        assert delete_response.json() == {"status": "deleted"}
        assert app_module.resolve_art_text_font_path(uploaded["id"]) is None


def test_font_library_rejects_non_font_upload():
    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/fonts",
            files={"file": ("notes.txt", io.BytesIO(b"not a font"), "text/plain")},
        )
    assert response.status_code == 400
    assert ".ttf" in response.json()["detail"]


def test_transcript_is_normalized_to_simplified_chinese():
    assert app_module.to_simplified("這是一個視頻轉文字測試") == "这是一个视频转文字测试"


def test_rejects_unsupported_file_type(tmp_path: Path):
    invalid = tmp_path / "notes.txt"
    invalid.write_text("not a video", encoding="utf-8")

    with TestClient(app_module.app) as client, invalid.open("rb") as handle:
        response = client.post(
            "/api/transcriptions",
            files={"file": (invalid.name, handle, "text/plain")},
        )

    assert response.status_code == 400
    assert "仅支持" in response.json()["detail"]


def test_requires_online_asr_api_key():
    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/transcriptions",
            files={"file": ("sample.mp4", io.BytesIO(b"video"), "video/mp4")},
        )

    assert response.status_code == 503
    assert "DASHSCOPE_API_KEY" in response.json()["detail"]


def test_paraformer_returns_simplified_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    audio_path = tmp_path / "speech.mp3"
    audio_path.write_bytes(b"fake mp3")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    class FakeResponse:
        status_code = 200
        message = ""

        @staticmethod
        def get_sentence():
            return [
                {
                    "text": "這是測試。",
                    "begin_time": 0,
                    "end_time": 1200,
                    "words": [
                        {
                            "text": "這是",
                            "punctuation": "",
                            "begin_time": 0,
                            "end_time": 300,
                        },
                        {
                            "text": "測試",
                            "punctuation": "。",
                            "begin_time": 700,
                            "end_time": 1100,
                        },
                    ],
                }
            ]

    class FakeRecognition:
        def __init__(self, **options):
            assert options == {
                "model": "paraformer-realtime-v2",
                "format": "mp3",
                "sample_rate": 16000,
                "language_hints": ["zh", "en"],
                "semantic_punctuation_enabled": True,
                "callback": None,
            }

        @staticmethod
        def call(path, **options):
            assert path == str(audio_path)
            assert options == {"timestamp_alignment_enabled": True}
            return FakeResponse()

    monkeypatch.setattr(app_module, "Recognition", FakeRecognition)
    monkeypatch.setattr(
        app_module,
        "polish_punctuation",
        lambda text, api_key: "这是测试。",
    )
    progress: list[int] = []

    result = app_module.transcribe_audio(audio_path, progress.append)

    assert result["text"] == "这是测试。"
    assert result["segments"] == [
        {
            "id": 0,
            "start": 0.0,
            "end": 1.1,
            "text": "这是测试。",
            "words": [
                {"text": "这是", "start": 0.0, "end": 0.3},
                {"text": "测试。", "start": 0.7, "end": 1.1},
            ],
        }
    ]
    assert progress == [55, 78, 95]


def test_punctuation_polish_rebuilds_sentence_segments():
    words = [
        {"text": "少年", "start": 0.0, "end": 0.4},
        {"text": "应有", "start": 0.4, "end": 0.8},
        {"text": "凌云志，", "start": 0.8, "end": 1.4},
        {"text": "敢叫", "start": 1.4, "end": 1.8},
        {"text": "日月", "start": 1.8, "end": 2.2},
        {"text": "换新天，", "start": 2.2, "end": 2.8},
        {"text": "生如", "start": 2.8, "end": 3.2},
        {"text": "夏花。", "start": 3.2, "end": 3.8},
    ]

    updated_words = app_module.apply_punctuation_to_words(
        words,
        "少年应有凌云志，敢叫日月换新天。\n生如夏花。",
    )
    assert updated_words is not None

    segments = app_module.build_sentence_segments(updated_words)

    assert [segment["text"] for segment in segments] == [
        "少年应有凌云志，敢叫日月换新天。",
        "生如夏花。",
    ]
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 2.8
    assert segments[1]["start"] == 2.8
    assert segments[1]["end"] == 3.8


def test_editable_transcript_segments_follow_clause_boundaries():
    words = [
        {"text": "\u4f60\u957f\u671f", "start": 0.0, "end": 0.4},
        {"text": "\u5f85\u5728", "start": 0.4, "end": 0.8},
        {"text": "\u4ec0\u4e48\u6837\u7684\u73af\u5883\u91cc\uff0c", "start": 0.8, "end": 1.8},
        {"text": "\u88ab\u4ec0\u4e48\u6837\u7684\u8ba4\u77e5", "start": 1.8, "end": 2.7},
        {"text": "\u80c6\u91cf\u548c\u6807\u51c6\u5f71\u54cd\u7740\u3002", "start": 2.7, "end": 3.8},
        {"text": "\u4f46\u662f", "start": 4.0, "end": 4.5},
        {"text": "\u597d\u7684\u73af\u5883\u4f1a\u5e2e\u4f60\u3002", "start": 4.5, "end": 5.5},
    ]
    source = [
        {
            "id": 0,
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "text": "".join(word["text"] for word in words),
            "words": words,
        }
    ]

    editable = app_module.build_editable_transcript_segments(source)

    assert [item["text"] for item in editable] == [
        "\u4f60\u957f\u671f\u5f85\u5728\u4ec0\u4e48\u6837\u7684\u73af\u5883\u91cc\uff0c",
        "\u88ab\u4ec0\u4e48\u6837\u7684\u8ba4\u77e5\u80c6\u91cf\u548c\u6807\u51c6\u5f71\u54cd\u7740\u3002",
        "\u4f46\u662f\u597d\u7684\u73af\u5883\u4f1a\u5e2e\u4f60\u3002",
    ]
    assert "".join(item["text"] for item in editable) == source[0]["text"]
    assert all(
        item["words"]
        and item["start"] == item["words"][0]["start"]
        and item["end"] == item["words"][-1]["end"]
        for item in editable
    )


def test_semantic_tokenization_replaces_mechanical_asr_chunks():
    words = [
        {"text": "用奋", "start": 0.0, "end": 0.4},
        {"text": "斗作", "start": 0.4, "end": 0.8},
        {"text": "笔，", "start": 0.8, "end": 1.2},
        {"text": "创激", "start": 1.2, "end": 1.6},
        {"text": "昂青", "start": 1.6, "end": 2.0},
        {"text": "春。", "start": 2.0, "end": 2.4},
    ]

    semantic_words = app_module.retokenize_words(words)

    assert [word["text"] for word in semantic_words] == [
        "用",
        "奋斗",
        "作笔，",
        "创",
        "激昂",
        "青春。",
    ]
    assert semantic_words == [
        {"text": "用", "start": 0.0, "end": 0.2},
        {"text": "奋斗", "start": 0.2, "end": 0.6},
        {"text": "作笔，", "start": 0.6, "end": 1.2},
        {"text": "创", "start": 1.2, "end": 1.4},
        {"text": "激昂", "start": 1.4, "end": 1.8},
        {"text": "青春。", "start": 1.8, "end": 2.4},
    ]


def test_ai_suggestions_are_validated_and_mapped_to_word_ranges(
    monkeypatch: pytest.MonkeyPatch,
):
    segments = [
        {
            "words": [
                {"text": "大家好！", "start": 0.0, "end": 0.4},
                {"text": "今天", "start": 0.4, "end": 0.8},
                {"text": "是", "start": 0.8, "end": 1.2},
                {"text": "星期三？", "start": 1.2, "end": 1.6},
                {"text": "不对，", "start": 1.6, "end": 2.0},
                {"text": "今天", "start": 2.0, "end": 2.4},
                {"text": "是", "start": 2.4, "end": 2.8},
                {"text": "星期四。", "start": 2.8, "end": 3.2},
                {"text": "开始。", "start": 3.2, "end": 3.6},
            ]
        }
    ]

    class FakeGeneration:
        @staticmethod
        def call(**options):
            assert options["model"] == "qwen3.7-max"
            assert options["response_format"] == {"type": "json_object"}
            assert options["enable_thinking"] is False
            assert "请只输出 JSON" in options["messages"][0]["content"]

            class Response:
                status_code = 200
                output = type(
                    "Output",
                    (),
                    {
                        "choices": [
                            type(
                                "Choice",
                                (),
                                {
                                    "message": type(
                                        "Message",
                                        (),
                                        {
                                            "content": json.dumps(
                                                {
                                                    "suggestions": [
                                                        {
                                                            "start_index": 1,
                                                            "end_index": 3,
                                                            "type": "口误",
                                                            "reason": "说错日期后立即改口",
                                                            "confidence": 0.96,
                                                        },
                                                        {
                                                            "start_index": 4,
                                                            "end_index": 4,
                                                            "type": "口误",
                                                            "reason": "自我纠正过渡词",
                                                            "confidence": 0.9,
                                                        },
                                                        {
                                                            "start_index": 5,
                                                            "end_index": 7,
                                                            "type": "口误",
                                                            "reason": "错误地选择了改口后的正确表达",
                                                            "confidence": 0.85,
                                                        },
                                                        {
                                                            "start_index": 0,
                                                            "end_index": 8,
                                                            "type": "无效片段",
                                                            "reason": "范围过大",
                                                            "confidence": 0.99,
                                                        },
                                                        {
                                                            "start_index": 8,
                                                            "end_index": 8,
                                                            "type": "语气词",
                                                            "reason": "置信度不足",
                                                            "confidence": 0.2,
                                                        },
                                                    ]
                                                },
                                                ensure_ascii=False,
                                            )
                                        },
                                    )()
                                },
                            )()
                        ]
                    },
                )()

            return Response()

    monkeypatch.setattr(app_module, "Generation", FakeGeneration)

    suggestions, status = app_module.suggest_deletions(segments, "test-key")

    assert status == "completed"
    assert suggestions == [
        {
            "id": "suggestion-1-4",
            "type": "口误",
            "reason": "检测到说错后立即改口，保留改口后的正确表达",
            "confidence": 0.96,
            "text": "今天是星期三？不对，",
            "start": 0.4,
            "end": 2.0,
            "startIndex": 1,
            "endIndex": 4,
            "ranges": [
                {"start": 0.4, "end": 0.8},
                {"start": 0.8, "end": 1.2},
                {"start": 1.2, "end": 1.6},
                {"start": 1.6, "end": 2.0},
            ],
        }
    ]


def test_repeated_restart_is_detected_even_when_ai_returns_no_suggestion(
    monkeypatch: pytest.MonkeyPatch,
):
    tokens = [
        "你",
        "身边",
        "你",
        "身边",
        "人人",
        "都",
        "觉得",
        "你",
        "身边",
        "人人",
        "都",
        "觉得",
        "一个月",
        "赚",
        "一万",
        "就",
        "顶天",
        "了，",
        "你",
        "很",
        "难",
        "真的",
        "坚信",
        "自己",
        "能",
        "赚",
        "十万。",
    ]
    words = [
        {
            "text": token,
            "start": round(index * 0.2, 3),
            "end": round((index + 1) * 0.2, 3),
        }
        for index, token in enumerate(tokens)
    ]
    segments = [
        {
            "id": 0,
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "text": "".join(tokens),
            "words": words,
        }
    ]

    class FakeGeneration:
        @staticmethod
        def call(**options):
            assert "你身边你身边人人都觉得" in options["messages"][0]["content"]

            class Response:
                status_code = 200
                output = type(
                    "Output",
                    (),
                    {
                        "choices": [
                            type(
                                "Choice",
                                (),
                                {
                                    "message": type(
                                        "Message",
                                        (),
                                        {"content": '{"suggestions":[]}'},
                                    )()
                                },
                            )()
                        ]
                    },
                )()

            return Response()

    monkeypatch.setattr(app_module, "Generation", FakeGeneration)

    suggestions, status = app_module.suggest_deletions(segments, "test-key")

    assert status == "completed"
    assert len(suggestions) == 1
    assert suggestions[0]["type"] == "重复"
    assert suggestions[0]["startIndex"] == 0
    assert suggestions[0]["endIndex"] == 6
    assert suggestions[0]["text"] == "你身边你身边人人都觉得"
    assert suggestions[0]["reason"] == (
        "检测到重复起句后重新表述，保留最后一次完整表达"
    )

    output_duration = words[-1]["end"] - suggestions[0]["end"]
    retained = app_module.build_retained_transcript(
        segments,
        suggestions[0]["ranges"],
        output_duration,
    )
    assert retained["text"] == (
        "你身边人人都觉得一个月赚一万就顶天了，"
        "你很难真的坚信自己能赚十万。"
    )

    assert app_module.detect_repeated_speech_ranges(
        [
            {"text": "你好。", "start": 0.0, "end": 0.5},
            {"text": "你好。", "start": 0.5, "end": 1.0},
        ]
    ) == []


def test_abandoned_opinion_leadin_is_removed_without_touching_main_clause(
    monkeypatch: pytest.MonkeyPatch,
):
    tokens = [
        "你",
        "觉得",
        "你",
        "身边",
        "人人",
        "都",
        "觉得",
        "一个月",
        "赚",
        "一万",
        "就",
        "顶天",
        "了，",
        "你",
        "很",
        "难",
        "真的",
        "坚信",
        "自己",
        "能",
        "赚",
        "十万。",
    ]
    words = [
        {
            "text": token,
            "start": round(index * 0.2, 3),
            "end": round((index + 1) * 0.2, 3),
        }
        for index, token in enumerate(tokens)
    ]
    segments = [
        {
            "id": 0,
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "text": "".join(tokens),
            "words": words,
        }
    ]

    class FakeGeneration:
        @staticmethod
        def call(**options):
            class Response:
                status_code = 200
                output = type(
                    "Output",
                    (),
                    {
                        "choices": [
                            type(
                                "Choice",
                                (),
                                {
                                    "message": type(
                                        "Message",
                                        (),
                                        {"content": '{"suggestions":[]}'},
                                    )()
                                },
                            )()
                        ]
                    },
                )()

            return Response()

    monkeypatch.setattr(app_module, "Generation", FakeGeneration)

    suggestions, status = app_module.suggest_deletions(segments, "test-key")

    assert status == "completed"
    assert len(suggestions) == 1
    assert suggestions[0]["type"] == "错句"
    assert suggestions[0]["startIndex"] == 0
    assert suggestions[0]["endIndex"] == 1
    assert suggestions[0]["text"] == "你觉得"
    retained = app_module.build_retained_transcript(
        segments,
        suggestions[0]["ranges"],
        words[-1]["end"] - suggestions[0]["end"],
    )
    assert retained["text"] == (
        "你身边人人都觉得一个月赚一万就顶天了，"
        "你很难真的坚信自己能赚十万。"
    )


def test_repetition_rule_protects_the_copy_it_intends_to_keep(
    monkeypatch: pytest.MonkeyPatch,
):
    tokens = ["在", "在", "另一群", "人", "眼中", "就是", "家常便饭。"]
    words = [
        {
            "text": token,
            "start": round(index * 0.2, 3),
            "end": round((index + 1) * 0.2, 3),
        }
        for index, token in enumerate(tokens)
    ]
    segments = [
        {
            "id": 0,
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "text": "".join(tokens),
            "words": words,
        }
    ]

    class FakeGeneration:
        @staticmethod
        def call(**options):
            class Response:
                status_code = 200
                output = type(
                    "Output",
                    (),
                    {
                        "choices": [
                            type(
                                "Choice",
                                (),
                                {
                                    "message": type(
                                        "Message",
                                        (),
                                        {
                                            "content": json.dumps(
                                                {
                                                    "suggestions": [
                                                        {
                                                            "start_index": 1,
                                                            "end_index": 1,
                                                            "type": "重复",
                                                            "reason": "重复的在",
                                                            "confidence": 0.99,
                                                        }
                                                    ]
                                                },
                                                ensure_ascii=False,
                                            )
                                        },
                                    )()
                                },
                            )()
                        ]
                    },
                )()

            return Response()

    monkeypatch.setattr(app_module, "Generation", FakeGeneration)

    suggestions, status = app_module.suggest_deletions(segments, "test-key")

    assert status == "completed"
    assert len(suggestions) == 1
    assert suggestions[0]["startIndex"] == 0
    assert suggestions[0]["endIndex"] == 0
    retained = app_module.build_retained_transcript(
        segments,
        suggestions[0]["ranges"],
        words[-1]["end"] - suggestions[0]["end"],
    )
    assert retained["text"] == "在另一群人眼中就是家常便饭。"


def test_repetition_rules_override_partial_ai_ranges_and_merge_abandoned_restarts(
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeGeneration:
        @staticmethod
        def call(**options):
            transcript = options["messages"][1]["content"]
            ai_suggestions = (
                [
                    {
                        "start_index": 1,
                        "end_index": 1,
                        "type": "重复",
                        "reason": "只识别到局部重复",
                        "confidence": 1.0,
                    }
                ]
                if "一个月" in transcript and "家常便饭" not in transcript
                else []
            )

            class Response:
                status_code = 200
                output = type(
                    "Output",
                    (),
                    {
                        "choices": [
                            type(
                                "Choice",
                                (),
                                {
                                    "message": type(
                                        "Message",
                                        (),
                                        {
                                            "content": json.dumps(
                                                {"suggestions": ai_suggestions},
                                                ensure_ascii=False,
                                            )
                                        },
                                    )()
                                },
                            )()
                        ]
                    },
                )()

            return Response()

    monkeypatch.setattr(app_module, "Generation", FakeGeneration)

    def build_segments(tokens: list[str]) -> list[dict]:
        words = [
            {
                "text": token,
                "start": round(index * 0.2, 3),
                "end": round((index + 1) * 0.2, 3),
            }
            for index, token in enumerate(tokens)
        ]
        return [
            {
                "id": 0,
                "start": words[0]["start"],
                "end": words[-1]["end"],
                "text": "".join(tokens),
                "words": words,
            }
        ]

    first_segments = build_segments(
        [
            "你",
            "身边",
            "人人",
            "都",
            "觉得",
            "身边",
            "人人",
            "都",
            "觉得",
            "一个月",
            "赚",
            "一万",
            "就",
            "顶天",
            "了，",
            "你",
            "很",
            "难",
            "真的",
            "坚信",
            "自己",
            "能",
            "赚",
            "十万。",
        ]
    )
    first_suggestions, first_status = app_module.suggest_deletions(
        first_segments, "test-key"
    )

    assert first_status == "completed"
    assert len(first_suggestions) == 1
    assert first_suggestions[0]["startIndex"] == 1
    assert first_suggestions[0]["endIndex"] == 4
    assert first_suggestions[0]["text"] == "身边人人都觉得"
    first_retained = app_module.build_retained_transcript(
        first_segments,
        first_suggestions[0]["ranges"],
        first_segments[0]["end"]
        - (first_suggestions[0]["end"] - first_suggestions[0]["start"]),
    )
    assert first_retained["text"] == (
        "你身边人人都觉得一个月赚一万就顶天了，"
        "你很难真的坚信自己能赚十万。"
    )

    second_segments = build_segments(
        [
            "在",
            "另",
            "一群",
            "人",
            "眼中，",
            "在",
            "另",
            "一",
            "在",
            "另",
            "一群",
            "人",
            "眼中",
            "就是",
            "家常便饭。",
        ]
    )
    second_suggestions, second_status = app_module.suggest_deletions(
        second_segments, "test-key"
    )

    assert second_status == "completed"
    assert len(second_suggestions) == 1
    assert second_suggestions[0]["startIndex"] == 0
    assert second_suggestions[0]["endIndex"] == 7
    assert second_suggestions[0]["text"] == "在另一群人眼中，在另一"
    second_retained = app_module.build_retained_transcript(
        second_segments,
        second_suggestions[0]["ranges"],
        second_segments[0]["end"]
        - (second_suggestions[0]["end"] - second_suggestions[0]["start"]),
    )
    assert second_retained["text"] == "在另一群人眼中就是家常便饭。"


def test_repetition_rules_still_work_when_ai_analysis_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    class FailingGeneration:
        @staticmethod
        def call(**options):
            raise RuntimeError("temporary model failure")

    monkeypatch.setattr(app_module, "Generation", FailingGeneration)

    def segments_from_text(text: str) -> list[dict]:
        character_words: list[dict] = []
        timestamp = 0.0
        for character in text:
            if not app_module.content_characters(character):
                if character_words:
                    character_words[-1]["text"] += character
                continue
            character_words.append(
                {
                    "text": character,
                    "start": round(timestamp, 3),
                    "end": round(timestamp + 0.1, 3),
                }
            )
            timestamp += 0.1
        return app_module.build_sentence_segments(
            app_module.retokenize_words(character_words)
        )

    examples = [
        (
            "真不是他突然变聪明了，是他突然发现了原来自己以前"
            "不敢想的是在另一群人眼中，在另一在另一群人眼中"
            "就是家常便饭。",
            "在另一群人眼中，在另一",
            "真不是他突然变聪明了，是他突然发现了原来自己以前"
            "不敢想的是在另一群人眼中就是家常便饭。",
        ),
        (
            "人这辈子最难突破的从来不是自己的能力，"
            "而是你身边所有人一起给一起给你画的那条正常的线。",
            "一起给",
            "人这辈子最难突破的从来不是自己的能力，"
            "而是你身边所有人一起给你画的那条正常的线。",
        ),
    ]

    for source_text, deleted_text, expected_text in examples:
        segments = segments_from_text(source_text)
        suggestions, status = app_module.suggest_deletions(
            segments, "test-key"
        )

        assert status == "completed"
        assert len(suggestions) == 1
        assert suggestions[0]["text"] == deleted_text
        retained = app_module.build_retained_transcript(
            segments,
            suggestions[0]["ranges"],
            segments[-1]["end"]
            - (suggestions[0]["end"] - suggestions[0]["start"]),
        )
        assert retained["text"] == expected_text


def test_upload_extracts_audio_and_returns_transcript(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ASR_API_KEY", "test-key")

    def fake_transcribe(audio_path: Path, progress_callback):
        assert audio_path.exists()
        assert audio_path.suffix == ".mp3"
        progress_callback(80)
        return {
            "text": "这是一段测试文字。",
            "language": "zh",
            "languageProbability": 0.99,
            "duration": 1.0,
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 1.0,
                    "text": "这是一段测试文字。",
                    "words": [],
                }
            ],
        }

    monkeypatch.setattr(app_module, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(
        app_module,
        "suggest_deletions",
        lambda segments, api_key: ([], "completed"),
    )
    with TestClient(app_module.app) as client, sample_video.open("rb") as handle:
        response = client.post(
            "/api/transcriptions",
            files={"file": (sample_video.name, handle, "video/mp4")},
        )
        assert response.status_code == 202
        job_id = response.json()["id"]
        result_response = client.get(f"/api/transcriptions/{job_id}")

    result = result_response.json()
    assert result["status"] == "completed"
    assert result["progress"] == 100
    assert result["result"]["text"] == "这是一段测试文字。"
    assert result["result"]["suggestions"] == []
    assert result["result"]["suggestionStatus"] == "completed"
    assert result["result"]["noSpeechStatus"] == "completed"
    assert isinstance(result["result"]["noSpeechSuggestions"], list)
    assert result["result"]["mediaDuration"] == result["duration"]
    assert (app_module.DATA_DIR / "jobs" / job_id / "speech.mp3").exists()


def test_no_speech_detection_keeps_boundaries_and_protects_video_edges():
    sample_rate = 16_000
    samples = array("h", [0]) * (sample_rate * 12)
    # The second middle gap has background sound. It remains a suggestion, but
    # receives a lower-confidence warning so the user must listen first.
    background_start = round(5.7 * sample_rate)
    background_end = round(8.8 * sample_rate)
    samples[background_start:background_end] = array(
        "h", [2_000]
    ) * (background_end - background_start)
    segments = [
        {
            "start": 2.0,
            "end": 3.0,
            "words": [{"text": "第一句", "start": 2.0, "end": 3.0}],
        },
        {
            "start": 5.0,
            "end": 5.5,
            "words": [{"text": "第二句", "start": 5.0, "end": 5.5}],
        },
        {
            "start": 9.0,
            "end": 10.0,
            "words": [{"text": "第三句", "start": 9.0, "end": 10.0}],
        },
    ]

    suggestions = app_module.detect_no_speech_ranges(
        segments,
        12.0,
        samples,
        sample_rate,
    )

    assert [item["kind"] for item in suggestions] == [
        "leading",
        "middle",
        "middle",
        "trailing",
    ]
    assert suggestions[0]["protected"] is True
    assert suggestions[0]["start"] == 0.0
    assert suggestions[0]["end"] == 1.8
    assert suggestions[1]["start"] == 3.2
    assert suggestions[1]["end"] == 4.8
    assert suggestions[1]["audioState"] == "quiet"
    assert suggestions[2]["start"] == 5.7
    assert suggestions[2]["end"] == 8.8
    assert suggestions[2]["audioState"] == "ambient"
    assert suggestions[-1]["protected"] is True
    assert suggestions[-1]["start"] == 10.2
    assert suggestions[-1]["end"] == 12.0


def test_no_speech_detection_ignores_short_conversational_pauses():
    suggestions = app_module.detect_no_speech_ranges(
        [
            {"start": 0.0, "end": 1.0, "words": []},
            {"start": 2.4, "end": 3.0, "words": []},
        ],
        3.0,
    )

    assert suggestions == []


def test_transcript_word_can_be_corrected_without_changing_timestamps():
    job_id = "11111111-1111-4111-8111-111111111111"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 1.0,
            "result": {
                "text": "保留错词删除",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "保留错词删除",
                        "words": [
                            {"text": "保留", "start": 0.0, "end": 0.25},
                            {"text": "错词", "start": 0.25, "end": 0.55},
                            {"text": "删除", "start": 0.55, "end": 1.0},
                        ],
                    }
                ],
            },
            "edit": {
                "status": "completed",
                "ranges": [{"start": 0.55, "end": 1.0}],
                "outputDuration": 0.55,
                "transcript": None,
            },
        }

    with TestClient(app_module.app) as client:
        response = client.patch(
            f"/api/transcriptions/{job_id}/transcript",
            json={"segmentIndex": 0, "wordIndex": 1, "text": "正词"},
        )
        refreshed = client.get(f"/api/transcriptions/{job_id}")

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["text"] == "保留正词删除"
    assert result["segments"][0]["text"] == "保留正词删除"
    assert result["segments"][0]["words"][1] == {
        "text": "正词",
        "start": 0.25,
        "end": 0.55,
    }
    assert response.json()["editTranscript"]["text"] == "保留正词"
    assert refreshed.json()["edit"]["transcript"]["text"] == "保留正词"


def test_transcript_word_correction_rejects_blank_text():
    job_id = "22222222-2222-4222-8222-222222222222"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "result": {
                "text": "原文",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "原文",
                        "words": [],
                    }
                ],
            },
            "edit": None,
        }

    with TestClient(app_module.app) as client:
        response = client.patch(
            f"/api/transcriptions/{job_id}/transcript",
            json={"segmentIndex": 0, "wordIndex": None, "text": "   "},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "修正后的文字不能为空。"


def test_full_transcript_edits_are_aligned_to_the_matching_words():
    job_id = "33333333-3333-4333-8333-333333333333"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 2.0,
            "result": {
                "text": "少年应有凌云志。\n生如夏花。",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 1.0,
                        "text": "少年应有凌云志。",
                        "words": [
                            {"text": "少年", "start": 0.0, "end": 0.3},
                            {"text": "应有", "start": 0.3, "end": 0.6},
                            {"text": "凌云志。", "start": 0.6, "end": 1.0},
                        ],
                    },
                    {
                        "id": 1,
                        "start": 1.0,
                        "end": 2.0,
                        "text": "生如夏花。",
                        "words": [
                            {"text": "生如", "start": 1.0, "end": 1.4},
                            {"text": "夏花。", "start": 1.4, "end": 2.0},
                        ],
                    },
                ],
            },
            "edit": {
                "status": "completed",
                "ranges": [],
                "outputDuration": 2.0,
                "transcript": None,
            },
            "art": {"status": "completed", "overlays": []},
            "artSuggestion": {"status": "completed", "suggestions": []},
            "pictureInPicture": {
                "status": "completed",
                "source": "art",
                "overlays": [],
            },
        }

    with TestClient(app_module.app) as client:
        response = client.put(
            f"/api/transcriptions/{job_id}/transcript",
            json={"text": "少年应有凌云智。\n生如鲜花。"},
        )
        refreshed = client.get(f"/api/transcriptions/{job_id}").json()

    assert response.status_code == 200
    assert response.json()["changedWords"] == 2
    result = response.json()["result"]
    assert result["text"] == "少年应有凌云智。\n生如鲜花。"
    assert result["segments"][0]["words"][2] == {
        "text": "凌云智。",
        "start": 0.6,
        "end": 1.0,
    }
    assert result["segments"][1]["words"][1] == {
        "text": "鲜花。",
        "start": 1.4,
        "end": 2.0,
    }
    assert refreshed["edit"]["transcript"]["text"] == "少年应有凌云智。生如鲜花。"
    assert refreshed["art"] is None
    assert refreshed["artSuggestion"] is None
    assert refreshed["pictureInPicture"] is None


def test_cut_draft_is_persisted_versioned_restored_and_cleared():
    job_id = "33333333-3333-4333-8333-333333333333"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }

    payload = {
        "revision": 0,
        "automaticNoSpeechInitialized": True,
        "textRanges": [
            {
                "key": "1.000-2.000",
                "start": 0.8,
                "end": 2.2,
                "text": "删除这一段",
                "originalStart": 1.0,
                "originalEnd": 2.0,
                "adjacentSilenceBefore": 0.2,
                "adjacentSilenceAfter": 0.2,
            }
        ],
        "noSpeechRanges": [
            {"key": "silence-1", "start": 4.0, "end": 5.5}
        ],
        "timelineRanges": [{"start": 7.0, "end": 8.0}],
    }

    with TestClient(app_module.app) as client:
        saved = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=payload,
        )
        draft_file_exists_after_save = app_module.cut_draft_path(job_id).is_file()
        stale = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=payload,
        )
        with app_module.JOBS_LOCK:
            app_module.JOBS[job_id]["cutDraft"] = None
        restored = client.get(
            f"/api/transcriptions/{job_id}/cut-draft"
        )
        rendered_job = client.get(f"/api/transcriptions/{job_id}")
        cleared = client.delete(
            f"/api/transcriptions/{job_id}/cut-draft"
        )
        after_clear = client.get(
            f"/api/transcriptions/{job_id}/cut-draft"
        )

    assert saved.status_code == 200
    draft = saved.json()["cutDraft"]
    assert draft["schemaVersion"] == 1
    assert draft["revision"] == 1
    assert draft["automaticNoSpeechInitialized"] is True
    assert draft["textRanges"][0]["key"] == "1.000-2.000"
    assert draft["textRanges"][0]["start"] == 0.8
    assert draft["noSpeechRanges"] == [
        {"key": "silence-1", "start": 4.0, "end": 5.5}
    ]
    assert draft["timelineRanges"] == [{"start": 7.0, "end": 8.0}]
    assert draft_file_exists_after_save is True
    assert stale.status_code == 409
    assert "其他页面更新" in stale.json()["detail"]
    assert restored.status_code == 200
    assert restored.json()["cutDraft"] == draft
    assert rendered_job.json()["cutDraft"] == draft
    assert cleared.status_code == 200
    assert cleared.json() == {"status": "cleared"}
    assert after_clear.json()["cutDraft"] is None
    assert not app_module.cut_draft_path(job_id).exists()


def test_cut_draft_preserves_explicitly_empty_text_ranges():
    job_id = "34343434-3434-4434-8434-343434343434"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }

    with TestClient(app_module.app) as client:
        saved = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={
                "revision": 0,
                "automaticNoSpeechInitialized": True,
                "textRanges": [],
                "noSpeechRanges": [],
                "timelineRanges": [],
            },
        )
        restored = client.get(f"/api/transcriptions/{job_id}/cut-draft")

    assert saved.status_code == 200
    draft = saved.json()["cutDraft"]
    assert draft is not None
    assert draft["automaticNoSpeechInitialized"] is True
    assert draft["textRanges"] == []
    assert draft["noSpeechRanges"] == []
    assert draft["timelineRanges"] == []
    assert restored.json()["cutDraft"] == draft


def test_cut_draft_defaults_automatic_no_speech_marker_for_legacy_clients():
    job_id = "35353535-3535-4535-8535-353535353535"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }

    with TestClient(app_module.app) as client:
        saved = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={
                "revision": 0,
                "textRanges": [],
                "noSpeechRanges": [],
                "timelineRanges": [],
            },
        )

    assert saved.status_code == 200
    assert saved.json()["cutDraft"]["automaticNoSpeechInitialized"] is False


def test_cut_draft_aligns_text_media_ranges_before_preview_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "36363636-3636-4636-8636-363636363636"
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"source")
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * (sample_rate * 3)
    for valley in (0.78, 2.14):
        start = round((valley - 0.03) * sample_rate)
        end = round((valley + 0.03) * sample_rate)
        samples[start:end] = array("h", [0]) * (end - start)
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: samples,
    )

    segments = [
        {
            "start": 0.0,
            "end": 3.0,
            "text": "ABC",
            "words": [
                {"text": "A", "start": 0.0, "end": 1.0},
                {"text": "B", "start": 1.0, "end": 2.0},
                {"text": "C", "start": 2.0, "end": 3.0},
            ],
        }
    ]
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 3.0,
            "result": {"segments": segments},
            "cutDraft": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    payload = {
        "revision": 0,
        "textRanges": [
            {
                "key": "1.000-2.000",
                "start": 1.0,
                "end": 2.0,
                "text": "B",
                "originalStart": 1.0,
                "originalEnd": 2.0,
            }
        ],
        "noSpeechRanges": [],
        "timelineRanges": [],
    }
    with TestClient(app_module.app) as client:
        first = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=payload,
        )
        first_draft = first.json()["cutDraft"]
        second_payload = {
            **payload,
            "revision": first_draft["revision"],
            "textRanges": first_draft["textRanges"],
        }
        second = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=second_payload,
        )

    assert first.status_code == 200
    aligned = first_draft["textRanges"][0]
    assert 0.76 <= aligned["start"] <= 0.8
    assert 2.12 <= aligned["end"] <= 2.16
    assert aligned["originalStart"] == 1.0
    assert aligned["originalEnd"] == 2.0
    assert aligned["adjacentSilenceBefore"] == pytest.approx(
        1.0 - aligned["start"],
        abs=0.001,
    )
    assert aligned["adjacentSilenceAfter"] == pytest.approx(
        aligned["end"] - 2.0,
        abs=0.001,
    )
    assert second.status_code == 200
    assert second.json()["cutDraft"]["textRanges"] == first_draft["textRanges"]


def test_editable_transcript_segments_can_split_and_merge_by_selected_text():
    job_id = "44444444-4444-4444-8444-444444444444"
    source_segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 1.4,
            "text": "少年应有凌云志。",
            "words": [
                {"text": "少年", "start": 0.0, "end": 0.4},
                {"text": "应有", "start": 0.4, "end": 0.8},
                {"text": "凌云志。", "start": 0.8, "end": 1.4},
            ],
        }
    ]
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "result": {
                "text": "少年应有凌云志。",
                "segments": source_segments,
                "editableSegments": app_module.build_editable_transcript_segments(
                    source_segments
                ),
            },
            "edit": None,
            "art": None,
        }

    with TestClient(app_module.app) as client:
        invalid_merge = client.put(
            f"/api/transcriptions/{job_id}/editable-segments",
            json={"segmentIndex": 0, "action": "merge_up"},
        )
        split_response = client.put(
            f"/api/transcriptions/{job_id}/editable-segments",
            json={
                "segmentIndex": 0,
                "action": "split",
                "selectionStart": 2,
                "selectionEnd": 4,
            },
        )
        merge_up_response = client.put(
            f"/api/transcriptions/{job_id}/editable-segments",
            json={"segmentIndex": 1, "action": "merge_up"},
        )
        merge_down_response = client.put(
            f"/api/transcriptions/{job_id}/editable-segments",
            json={"segmentIndex": 0, "action": "merge_down"},
        )

    assert invalid_merge.status_code == 400
    assert invalid_merge.json()["detail"] == "第一段没有可向上合并的段落。"

    assert split_response.status_code == 200
    split_segments = split_response.json()["editableSegments"]
    assert [segment["text"] for segment in split_segments] == [
        "少年",
        "应有",
        "凌云志。",
    ]
    assert [(segment["start"], segment["end"]) for segment in split_segments] == [
        (0.0, 0.4),
        (0.4, 0.8),
        (0.8, 1.4),
    ]

    assert merge_up_response.status_code == 200
    assert [
        segment["text"]
        for segment in merge_up_response.json()["editableSegments"]
    ] == ["少年应有", "凌云志。"]

    assert merge_down_response.status_code == 200
    merged_segments = merge_down_response.json()["editableSegments"]
    assert [segment["id"] for segment in merged_segments] == [0]
    assert merged_segments[0]["text"] == "少年应有凌云志。"
    assert merged_segments[0]["start"] == 0.0
    assert merged_segments[0]["end"] == 1.4


def test_editable_transcript_segments_can_update_text_and_sync_source():
    job_id = "55555555-5555-5555-8555-555555555555"
    source_segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 1.4,
            "text": "少年应有凌云志。",
            "words": [
                {"text": "少年", "start": 0.0, "end": 0.4},
                {"text": "应有", "start": 0.4, "end": 0.8},
                {"text": "凌云志。", "start": 0.8, "end": 1.4},
            ],
        }
    ]
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "result": {
                "text": "少年应有凌云志。",
                "segments": source_segments,
                "editableSegments": app_module.build_editable_transcript_segments(
                    source_segments
                ),
            },
            "edit": None,
            "art": None,
        }

    with TestClient(app_module.app) as client:
        response = client.put(
            f"/api/transcriptions/{job_id}/editable-segments",
            json={"segmentIndex": 0, "action": "text", "text": "少年应怀凌云志。"},
        )

    assert response.status_code == 200
    assert response.json()["editableSegments"][0]["text"] == "少年应怀凌云志。"
    with app_module.JOBS_LOCK:
        job = app_module.JOBS[job_id]
    assert job["result"]["segments"][0]["text"] == "少年应怀凌云志。"
    assert app_module.content_characters(
        "".join(word["text"] for word in job["result"]["segments"][0]["words"])
    ) == app_module.content_characters("少年应怀凌云志。")
    assert job["result"]["text"] == "少年应怀凌云志。"


def test_editing_text_keeps_track_timeline_stable():
    job_id = "66666666-6666-6666-8666-666666666666"
    source_segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 1.0,
            "text": "我们相信AI很强。",
            "words": [
                {"text": "我们", "start": 0.0, "end": 0.3},
                {"text": "相信", "start": 0.3, "end": 0.5},
                {"text": "AI", "start": 0.5, "end": 0.7},
                {"text": "很强。", "start": 0.7, "end": 1.0},
            ],
        },
        {
            "id": 1,
            "start": 1.0,
            "end": 2.0,
            "text": "第二段内容。",
            "words": [
                {"text": "第二", "start": 1.0, "end": 1.4},
                {"text": "段", "start": 1.4, "end": 1.7},
                {"text": "内容。", "start": 1.7, "end": 2.0},
            ],
        },
    ]
    shared = {
        "trackType": "transcript",
        "trackId": "transcript-full",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFFFFF",
        "strokeColor": "#071018",
        "strokeWidth": 0,
        "shadow": True,
        "x": 0.5,
        "y": 0.82,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 0,
        "artStyle": "impact",
    }
    track_overlays = [
        {**shared, "text": "我们相信AI很强", "start": 0.0, "end": 1.0},
        {**shared, "text": "第二段内容", "start": 1.0, "end": 2.0},
    ]
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 2.0,
            "result": {
                "text": "我们相信AI很强。\n第二段内容。",
                "segments": source_segments,
                "editableSegments": app_module.build_editable_transcript_segments(
                    source_segments
                ),
            },
            "art": {"overlays": track_overlays, "status": "completed"},
            "edit": None,
        }
    try:
        with TestClient(app_module.app) as client:
            response = client.put(
                f"/api/transcriptions/{job_id}/editable-segments",
                json={
                    "segmentIndex": 0,
                    "action": "text",
                    "text": "我们相信AI很厉害。",
                },
            )
        assert response.status_code == 200
        with app_module.JOBS_LOCK:
            job = app_module.JOBS[job_id]
        cue_a = job["art"]["overlays"][0]
        cue_b = job["art"]["overlays"][1]

        # The edited segment's cue text updates...
        assert "很厉害" in cue_a["text"]
        # ...but its TIMES stay exactly the same.
        assert cue_a["start"] == 0.0
        assert cue_a["end"] == 1.0
        # The untouched segment's cue is completely unchanged.
        assert cue_b["text"] == "第二段内容"
        assert cue_b["start"] == 1.0
        assert cue_b["end"] == 2.0
        # The old rendered art video is stale; it must be regenerated.
        assert job["art"]["status"] is None
        assert job["art"]["outputUrl"] is None
    finally:
        with app_module.JOBS_LOCK:
            app_module.JOBS.pop(job_id, None)


def test_delete_ranges_are_merged_and_cannot_remove_everything():
    ranges = [
        app_module.DeleteRange(start=0.2, end=0.4),
        app_module.DeleteRange(start=0.49, end=0.6),
    ]

    assert app_module.normalize_delete_ranges(ranges, 1.0) == [
        {"start": 0.2, "end": 0.6}
    ]

    with pytest.raises(ValueError, match="不能删除整段视频"):
        app_module.normalize_delete_ranges(
            [app_module.DeleteRange(start=0, end=1)],
            1.0,
        )


def test_overlapping_quiet_range_cannot_delete_the_retained_repeat_take():
    words = [
        {"text": "你", "start": 33.16, "end": 33.52},
        {"text": "身边", "start": 33.52, "end": 34.24},
        {"text": "你", "start": 34.24, "end": 34.60},
        {"text": "身边", "start": 34.60, "end": 35.32},
        {"text": "人人", "start": 35.32, "end": 36.04},
        {"text": "都", "start": 36.04, "end": 36.40},
        {"text": "觉得", "start": 36.40, "end": 37.12},
        {"text": "你", "start": 37.12, "end": 37.48},
        {"text": "身边", "start": 37.48, "end": 38.20},
        {"text": "人人", "start": 38.20, "end": 38.92},
        {"text": "都", "start": 38.92, "end": 39.28},
        {"text": "觉得", "start": 39.28, "end": 40.00},
    ]
    segments = [
        {
            "start": 33.16,
            "end": 40.0,
            "text": "".join(word["text"] for word in words),
            "words": words,
        }
    ]
    suggestion = {
        "type": "\u91cd\u590d",
        "startIndex": 0,
        "endIndex": 6,
        "start": 33.16,
        "end": 37.12,
        "ranges": [{"start": 33.16, "end": 37.12}],
    }
    draft = {
        "textRanges": [
            {
                "key": "33.160-37.120",
                "start": 32.28,
                "end": 37.12,
                "originalStart": 33.16,
                "originalEnd": 37.12,
            }
        ],
        "noSpeechRanges": [
            {"key": "quiet", "start": 37.8, "end": 39.68}
        ],
        "timelineRanges": [],
    }

    resolved = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [suggestion],
        segments,
        40.0,
    )

    assert resolved == [{"start": 32.28, "end": 37.12}]
    retained = app_module.build_retained_transcript(
        segments,
        resolved,
        35.16,
    )
    assert retained["text"] == "你身边人人都觉得"


def test_cut_draft_keeps_semantic_text_ranges_separate_from_media_boundaries():
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

    media_ranges = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        segments,
        3.0,
    )
    transcript_ranges = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        segments,
        3.0,
        use_text_semantic_boundaries=True,
    )

    assert media_ranges == [{"start": 0.82, "end": 2.14}]
    assert transcript_ranges == [{"start": 1.0, "end": 2.0}]
    retained = app_module.build_retained_transcript(
        segments,
        transcript_ranges,
        1.68,
        timeline_delete_ranges=media_ranges,
    )
    assert retained["text"] == "保留保留"


def test_quiet_range_is_trimmed_to_the_gap_between_recognized_words():
    segments = [
        {
            "start": 100.937,
            "end": 103.42,
            "text": "你的极限，周围",
            "words": [
                {"text": "你", "start": 100.937, "end": 101.151},
                {"text": "的", "start": 101.151, "end": 101.366},
                {"text": "极限，", "start": 101.366, "end": 101.795},
                {"text": "周围", "start": 103.08, "end": 103.42},
            ],
        }
    ]

    protected = app_module.protect_recognized_speech_from_quiet_ranges(
        [{"start": 101.16, "end": 103.12}],
        segments,
    )

    assert protected == [{"start": 101.795, "end": 103.08}]


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
        {"text": "保留", "start": 0.0, "end": 0.25},
        {"text": "保留", "start": 0.25, "end": 0.7},
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
        {"text": "凌", "start": 0.0, "end": 0.3},
        {"text": "志，", "start": 0.3, "end": 0.6},
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
    assert edit["transcript"]["segments"][0]["words"][1] == {
        "text": "保留",
        "start": 0.25,
        "end": 0.7,
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


def test_cut_endpoint_uses_semantic_draft_ranges_for_retained_transcript(
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


def test_picture_in_picture_writes_editable_prompt_from_selected_text(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "20202020-2020-2020-2020-202020202020"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {
                "text": "青年应当勇于创新。",
                "duration": 1.0,
                "segments": [],
            },
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [],
            "pictureInPictureVideos": [],
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    captured: dict[str, object] = {}

    class FakeMessage:
        content = "年轻科研人员在明亮实验室观察精密仪器，中近景，冷蓝色调，柔和侧光，写实专业质感"

    class FakeChoice:
        message = FakeMessage()

    class FakeOutput:
        choices = [FakeChoice()]

    class FakeResponse:
        status_code = 200
        message = ""
        output = FakeOutput()

    def fake_call(**kwargs):
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(app_module.Generation, "call", fake_call)

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture/prompt",
            json={
                "text": "青年应当勇于创新。",
                "start": 0.1,
                "end": 0.8,
                "assetType": "image",
                "source": "original",
                "aspectRatio": "3:4",
            },
        )

    assert response.status_code == 200
    assert response.json()["prompt"].startswith("年轻科研人员")
    assert response.json()["model"] == "qwen-plus"
    assert response.json()["styleMatched"] is True
    assert captured["model"] == "qwen-plus"
    user_message = captured["messages"][1]["content"]
    assert "青年应当勇于创新" in user_message
    assert "画面比例：3:4" in user_message
    assert "原视频视觉风格" in user_message


def test_picture_in_picture_generates_image_with_requested_seedream_model(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "22222222-2222-2222-2222-222222222222"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "测试文案", "duration": 1.0, "segments": []},
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [],
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    image_buffer = io.BytesIO()
    Image.new("RGB", (160, 90), "#38cfa4").save(image_buffer, "PNG")
    encoded_image = base64.b64encode(image_buffer.getvalue()).decode("ascii")
    captured: dict[str, object] = {}

    class FakeSeedreamResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "model": "doubao-seedream-5-0-lite-260128",
                "data": [{"b64_json": encoded_image}],
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return FakeSeedreamResponse()

    monkeypatch.setenv("ARK_API_KEY", "test-ark-key")
    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture/images",
            json={
                "text": "青年应当勇于创新。",
                "start": 0.1,
                "end": 0.8,
                "mode": "auto",
                "prompt": "",
                "source": "original",
                "aspectRatio": "3:4",
            },
        )
        image_response = client.get(response.json()["imageUrl"])

    assert response.status_code == 201
    assert response.json()["model"] == "doubao-seedream-5-0-lite-260128"
    assert response.json()["source"] == "original"
    assert response.json()["start"] == 0.1
    assert response.json()["end"] == 0.8
    assert response.json()["aspectRatio"] == "3:4"
    assert captured["url"].endswith("/api/v3/images/generations")
    assert captured["headers"]["Authorization"] == "Bearer test-ark-key"
    request_payload = captured["json"]
    assert request_payload["model"] == "doubao-seedream-5-0-lite-260128"
    assert request_payload["size"] == "1728x2304"
    assert request_payload["sequential_image_generation"] == "disabled"
    assert request_payload["response_format"] == "b64_json"
    assert request_payload["watermark"] is False
    assert "青年应当勇于创新" in request_payload["prompt"]
    assert "严格继承参考帧" in request_payload["prompt"]
    assert "3:4 图片" in request_payload["prompt"]
    prefix, reference_data = request_payload["image"][0].split(",", 1)
    assert prefix == "data:image/jpeg;base64"
    with Image.open(io.BytesIO(base64.b64decode(reference_data))) as frame:
        assert frame.size == (960, 540)
    assert response.json()["styleMatched"] is True
    assert response.json()["styleReferenceTime"] == 0.45
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"


def test_picture_in_picture_image_uses_source_anchor_without_edited_video(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "44444444-4444-4444-4444-444444444444"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "测试文案", "duration": 1.0, "segments": []},
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [],
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    image_buffer = io.BytesIO()
    Image.new("RGB", (160, 90), "#38cfa4").save(image_buffer, "PNG")
    encoded_image = base64.b64encode(image_buffer.getvalue()).decode("ascii")

    class FakeSeedreamResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "model": "doubao-seedream-5-0-lite-260128",
                "data": [{"b64_json": encoded_image}],
            }

    monkeypatch.setenv("ARK_API_KEY", "test-ark-key")
    monkeypatch.setattr(
        app_module.httpx,
        "post",
        lambda url, **kwargs: FakeSeedreamResponse(),
    )

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture/images",
            json={
                "text": "青年应当勇于创新。",
                "start": 0.1,
                "end": 0.4,
                "mode": "auto",
                "prompt": "",
                # The "edited" video does not exist (edit is None), but the
                # source anchors let the style reference fall back to the
                # original video so PiP material can still be generated.
                "source": "edited",
                "sourceStart": 0.2,
                "sourceEnd": 0.6,
                "aspectRatio": "3:4",
            },
        )

    assert response.status_code == 201
    assert response.json()["source"] == "edited"
    assert response.json()["styleMatched"] is True
    # Reference frame midpoint comes from the original source anchors.
    assert response.json()["styleReferenceTime"] == 0.4


def test_picture_in_picture_generation_requires_ark_key(sample_video: Path):
    job_id = "33333333-3333-3333-3333-333333333333"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "status": "completed",
            "art": {"status": "completed", "outputDuration": 1.0},
        }
        app_module.JOB_FILES[job_id] = sample_video

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture/images",
            json={
                "text": "测试",
                "start": 0.0,
                "end": 0.8,
                "mode": "auto",
            },
        )

    assert response.status_code == 503
    assert "ARK_API_KEY" in response.json()["detail"]


def test_picture_in_picture_rejects_unsupported_image_aspect_ratio():
    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/transcriptions/33333333-3333-3333-3333-333333333333/"
            "picture-in-picture/images",
            json={
                "text": "测试文案",
                "start": 0.1,
                "end": 0.8,
                "mode": "auto",
                "prompt": "",
                "source": "original",
                "aspectRatio": "2:1",
            },
        )

    assert response.status_code == 422


def test_seedance_video_asset_can_be_generated_previewed_and_rendered(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "66666666-6666-6666-6666-666666666666"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "测试文案", "duration": 1.0, "segments": []},
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [],
            "pictureInPictureVideos": [],
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    captured: dict[str, object] = {}

    def fake_seedance_generate(
        prompt,
        output_path,
        aspect_ratio,
        generation_duration,
        on_status,
    ):
        captured.update(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            generation_duration=generation_duration,
        )
        on_status("Seedance 正在生成动态画面…", 55, "seedance-task-1")
        output_path.write_bytes(sample_video.read_bytes())
        return "seedance-task-1"

    monkeypatch.setenv("ARK_API_KEY", "test-ark-key")
    monkeypatch.setattr(
        app_module,
        "generate_picture_in_picture_video_asset",
        fake_seedance_generate,
    )

    with TestClient(app_module.app) as client:
        create_response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture/videos",
            json={
                "text": "青年应当勇于创新。",
                "start": 0.2,
                "end": 0.8,
                "mode": "custom",
                "prompt": "云层缓慢流动，镜头轻微推进",
                "source": "original",
                "aspectRatio": "9:16",
            },
        )
        asset_id = create_response.json()["id"]
        completed_job = client.get(f"/api/transcriptions/{job_id}").json()
        video_record = completed_job["pictureInPictureVideos"][0]
        asset_response = client.get(video_record["assetUrl"])
        render_response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture",
            json={
                "source": "original",
                "overlays": [
                    {
                        "assetId": asset_id,
                        "x": 0.78,
                        "y": 0.22,
                        "width": 0.32,
                    }
                ],
            },
        )
        rendered_job = client.get(f"/api/transcriptions/{job_id}").json()

    assert create_response.status_code == 202
    assert create_response.json()["model"] == "doubao-seedance-2-0-260128"
    assert create_response.json()["generationDuration"] == 4
    assert captured["aspect_ratio"] == "9:16"
    assert captured["generation_duration"] == 4
    assert "云层缓慢流动" in str(captured["prompt"])
    assert "视觉风格必须贴合原视频" in str(captured["prompt"])
    assert video_record["status"] == "completed"
    assert video_record["providerTaskId"] == "seedance-task-1"
    assert asset_response.status_code == 200
    assert asset_response.headers["content-type"] == "video/mp4"
    assert render_response.status_code == 202
    picture_in_picture = rendered_job["pictureInPicture"]
    assert picture_in_picture["status"] == "completed"
    assert picture_in_picture["overlays"][0]["assetType"] == "video"
    assert picture_in_picture["overlays"][0]["assetId"] == asset_id
    assert 0.8 < app_module.probe_video(
        sample_video.parent / "picture-in-picture.mp4"
    ) < 1.2


def test_seedance_copyright_failure_retries_with_safe_prompt(
    sample_video: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "88888888-8888-4888-8888-888888888888"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "test", "duration": 1.0, "segments": []},
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [],
            "pictureInPictureVideos": [],
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    prompts: list[str] = []

    def fake_seedance_generate(
        prompt,
        output_path,
        aspect_ratio,
        generation_duration,
        on_status,
    ):
        prompts.append(prompt)
        if len(prompts) == 1:
            raise RuntimeError(
                "Seedance 视频生成失败：The request failed because the output "
                "video may be related to copyright restrictions. Request id: test"
            )
        output_path.write_bytes(sample_video.read_bytes())
        return "seedance-safe-task"

    monkeypatch.setenv("ARK_API_KEY", "test-ark-key")
    monkeypatch.setattr(
        app_module,
        "generate_picture_in_picture_video_asset",
        fake_seedance_generate,
    )

    with TestClient(app_module.app) as client:
        create_response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture/videos",
            json={
                "text": "Make a famous wizard school cutaway",
                "start": 0.2,
                "end": 0.8,
                "mode": "custom",
                "prompt": "Harry Potter magic castle, cinematic flying candles",
                "source": "original",
                "aspectRatio": "16:9",
            },
        )
        completed_job = client.get(f"/api/transcriptions/{job_id}").json()

    assert create_response.status_code == 202
    assert len(prompts) == 2
    assert "Harry Potter" in prompts[0]
    assert "Harry Potter" not in prompts[1]
    assert "flying candles" not in prompts[1]
    video_record = completed_job["pictureInPictureVideos"][0]
    assert video_record["status"] == "completed"
    assert video_record["providerTaskId"] == "seedance-safe-task"
    assert video_record["promptFallbackApplied"] is True
    assert video_record["retryReason"] == "copyright_restriction"


def test_seedance_copyright_error_is_user_facing():
    error = RuntimeError(
        "The request failed because the output video may be related to "
        "copyright restrictions. Request id: test"
    )

    assert app_module.is_seedance_copyright_restriction(str(error)) is True
    assert "版权保护" in app_module.seedance_user_facing_error(error)
    assert "品牌" in app_module.seedance_user_facing_error(error)


def test_seedance_task_uses_official_content_generation_api(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}

    class FakeSeedanceResponse:
        status_code = 200
        is_success = True

        @staticmethod
        def json():
            return {"id": "cgt-test-task"}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return FakeSeedanceResponse()

    monkeypatch.setenv("ARK_API_KEY", "test-ark-key")
    monkeypatch.setattr(app_module.httpx, "post", fake_post)

    task_id = app_module.create_seedance_video_task(
        "云层缓慢流动",
        "16:9",
        5,
    )

    assert task_id == "cgt-test-task"
    assert captured["url"] == (
        "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
    )
    assert captured["headers"]["Authorization"] == "Bearer test-ark-key"
    assert captured["json"] == {
        "model": "doubao-seedance-2-0-260128",
        "content": [{"type": "text", "text": "云层缓慢流动"}],
        "resolution": "720p",
        "ratio": "16:9",
        "duration": 5,
        "generate_audio": False,
        "watermark": False,
    }


def test_seedance_video_generation_requires_ark_key(sample_video: Path):
    job_id = "77777777-7777-7777-7777-777777777777"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "测试", "duration": 1.0, "segments": []},
        }
        app_module.JOB_FILES[job_id] = sample_video

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture/videos",
            json={
                "text": "测试",
                "start": 0.0,
                "end": 0.8,
                "mode": "auto",
                "source": "original",
            },
        )

    assert response.status_code == 503
    assert "ARK_API_KEY" in response.json()["detail"]


def test_picture_in_picture_video_is_rendered_for_selected_text_time(
    sample_video: Path,
):
    job_id = "44444444-4444-4444-4444-444444444444"
    image_id = "55555555-5555-5555-5555-555555555555"
    image_path = sample_video.parent / f"picture-in-picture-{image_id}.png"
    Image.new("RGB", (320, 180), "#ffd84d").save(image_path, "PNG")
    image_url = (
        f"/api/transcriptions/{job_id}/picture-in-picture/images/{image_id}"
    )
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "测试文案", "duration": 1.0, "segments": []},
            "edit": None,
            "art": None,
            "artSuggestion": None,
            "pictureInPictureImages": [
                {
                    "id": image_id,
                    "text": "测试文案",
                    "prompt": "一张黄色插图",
                    "source": "original",
                    "start": 0.2,
                    "end": 0.8,
                    "imageUrl": image_url,
                }
            ],
            "pictureInPicture": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/picture-in-picture",
            json={
                "source": "original",
                "overlays": [
                    {
                        "imageId": image_id,
                        "x": 0.78,
                        "y": 0.22,
                        "width": 0.32,
                    }
                ]
            },
        )
        job_response = client.get(f"/api/transcriptions/{job_id}")
        video_response = client.get(
            f"/api/transcriptions/{job_id}/picture-in-picture-video"
        )

    assert response.status_code == 202
    picture_in_picture = job_response.json()["pictureInPicture"]
    assert picture_in_picture["status"] == "completed"
    assert picture_in_picture["source"] == "original"
    assert picture_in_picture["overlays"][0]["start"] == 0.2
    assert picture_in_picture["overlays"][0]["end"] == 0.8
    assert picture_in_picture["overlays"][0]["width"] == 0.32
    assert video_response.status_code == 200
    assert video_response.headers["content-type"] == "video/mp4"
    output_path = sample_video.parent / "picture-in-picture.mp4"
    assert output_path.is_file()
    assert 0.8 < app_module.probe_video(output_path) < 1.2


def test_picture_in_picture_overlay_accepts_live_retimed_range(tmp_path: Path):
    asset_id = "draft-retimed-asset"
    (tmp_path / f"picture-in-picture-{asset_id}.png").write_bytes(b"png")
    overlay = app_module.PictureInPictureOverlay(
        assetId=asset_id,
        start=0.4,
        end=0.9,
        x=0.78,
        y=0.22,
        width=0.32,
    )

    normalized = app_module.normalize_picture_in_picture_overlays(
        [overlay],
        1.0,
        [
            {
                "id": asset_id,
                "type": "image",
                "source": "edited",
                "start": 1.2,
                "end": 1.8,
                "assetUrl": "/asset.png",
            }
        ],
        tmp_path,
        "edited",
    )

    assert normalized[0]["start"] == 0.4
    assert normalized[0]["end"] == 0.9


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
                            {"text": "保留字幕", "start": 0.6, "end": 0.9},
                        ],
                    }
                ],
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
                "ranges": [{"start": 0.2, "end": 0.4}],
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
    assert calls[0][3] == [{"start": 0.2, "end": 0.4}]
    assert calls[1][3][0]["start"] == 0.4
    assert calls[1][3][0]["end"] == 0.7
    assert calls[2][3][0]["start"] == 0.4
    assert calls[2][3][0]["end"] == 0.7
    payload = job_response.json()
    assert payload["edit"]["status"] == "completed"
    assert payload["edit"]["outputDuration"] == 0.8
    assert payload["art"]["status"] == "completed"
    assert payload["pictureInPicture"]["status"] == "completed"
    assert payload["pictureInPicture"]["stage"] == "当前预览已生成视频"
    assert payload["composition"]["status"] == "completed"
    assert payload["composition"]["outputUrl"].endswith("/composition-video")
    assert payload["composition"]["historyId"].startswith("history-")
    assert not job_dir.exists()

    with TestClient(app_module.app) as client:
        output_response = client.get(
            f"/api/transcriptions/{job_id}/composition-video"
        )
        history_response = client.get("/api/history")
    assert output_response.status_code == 200
    assert output_response.content == b"pip"
    assert history_response.json()["count"] == 1
    assert history_response.json()["versions"][0]["kind"] == "composed"


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
    assert not job_dir.exists()

    with TestClient(app_module.app) as client:
        output_response = client.get(
            f"/api/transcriptions/{job_id}/composition-video"
        )
    assert output_response.status_code == 200
    assert output_response.content == b"unchanged"


def test_failed_preview_composition_removes_job_working_directory(
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
    assert not job_dir.exists()
    assert job_id not in app_module.JOB_FILES


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


def test_art_text_formats_horizontal_and_vertical_layouts():
    horizontal = {
        "text": "甲乙丙丁戊",
        "direction": "horizontal",
        "charsPerLine": 2,
        "letterSpacing": 4,
        "lineSpacing": 8,
    }
    vertical = {
        "text": "甲乙丙丁戊",
        "direction": "vertical",
        "charsPerLine": 3,
        "letterSpacing": 4,
        "lineSpacing": 4,
    }

    assert app_module.format_overlay_text(horizontal) == (
        "甲\u200a\u200a乙\n丙\u200a\u200a丁\n戊"
    )
    assert app_module.format_overlay_text(vertical) == (
        "丁\u200a\u200a甲\n戊\u200a\u200a乙\n"
        "\u3000\u200a\u200a丙"
    )


def test_full_transcript_art_track_uses_word_times_and_single_line_cues():
    words = [
        {"text": "如果", "start": 0.0, "end": 0.28},
        {"text": "你", "start": 0.28, "end": 0.42},
        {"text": "圈子", "start": 0.42, "end": 0.72},
        {"text": "里", "start": 0.72, "end": 0.86},
        {"text": "从来", "start": 0.82, "end": 1.12},
        {"text": "没有人", "start": 1.12, "end": 1.48},
        {"text": "拿到过", "start": 1.48, "end": 1.82},
        {"text": "结果，", "start": 1.82, "end": 2.16},
        {"text": "那", "start": 2.16, "end": 2.28},
        {"text": "你", "start": 2.28, "end": 2.40},
        {"text": "第一次", "start": 2.40, "end": 2.78},
        {"text": "碰到", "start": 2.78, "end": 3.02},
        {"text": "机会，", "start": 3.02, "end": 3.34},
        {"text": "第一反应", "start": 3.34, "end": 3.84},
        {"text": "肯定", "start": 3.84, "end": 4.10},
        {"text": "不是", "start": 4.10, "end": 4.36},
        {"text": "冲上去，", "start": 4.36, "end": 4.78},
        {"text": "而是", "start": 4.78, "end": 5.04},
        {"text": "先怀疑。", "start": 5.04, "end": 5.50},
    ]
    transcript = {
        "text": "".join(word["text"] for word in words),
        "segments": [
            {
                "text": "".join(word["text"] for word in words),
                "start": words[0]["start"],
                "end": words[-1]["end"],
                "words": words,
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        5.5,
        1080,
        font_id="bold",
        font_size=54,
        letter_spacing=0,
        stroke_width=3,
    )

    assert result["trackId"] == "transcript-full"
    assert result["trackType"] == "transcript"
    assert result["cueCount"] == len(result["cues"])
    assert result["cueCount"] > 1
    assert "".join(cue["text"] for cue in result["cues"]) == (
        app_module.content_characters(transcript["text"])
    )
    assert [cue["text"] for cue in result["cues"]] == [
        "如果你圈子里从来没有人",
        "拿到过结果",
        "那你第一次碰到机会",
        "第一反应肯定不是冲上去",
        "而是先怀疑",
    ]
    assert all(
        len(app_module.content_characters(cue["text"]))
        <= app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE
        for cue in result["cues"]
    )
    assert all("\n" not in cue["text"] for cue in result["cues"])
    assert all(
        current["start"] >= previous["end"]
        for previous, current in zip(result["cues"], result["cues"][1:])
    )
    assert result["cues"][0]["start"] == words[0]["start"]
    assert result["cues"][0]["end"] == words[5]["end"]
    assert result["cues"][1]["start"] == words[5]["end"]
    assert result["cues"][-1]["end"] == words[-1]["end"]
    assert result["cues"][0]["characterTimings"][:3] == [
        {"start": 0.0, "end": 0.14},
        {"start": 0.14, "end": 0.28},
        {"start": 0.28, "end": 0.42},
    ]
    assert all(
        len(cue["characterTimings"])
        == len(app_module.content_characters(cue["text"]))
        for cue in result["cues"]
    )

def test_full_transcript_art_track_keeps_complete_sentences_and_avoids_orphans():
    words = [
        {"text": "人生", "start": 0.0, "end": 0.8},
        {"text": "是", "start": 0.8, "end": 1.2},
        {"text": "自己", "start": 1.2, "end": 1.8},
        {"text": "选出来的，", "start": 1.8, "end": 3.0},
        {"text": "说实话，", "start": 3.0, "end": 4.2},
        {"text": "以前", "start": 4.2, "end": 5.0},
        {"text": "我也", "start": 5.0, "end": 5.8},
        {"text": "这么", "start": 5.8, "end": 6.6},
        {"text": "想。", "start": 6.6, "end": 7.0},
    ]
    transcript = {
        "text": "".join(word["text"] for word in words),
        "segments": [
            {
                "text": "".join(word["text"] for word in words),
                "start": 0.0,
                "end": 7.0,
                "words": words,
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        7.0,
        1080,
        font_id="bold",
        font_size=30,
        letter_spacing=0,
        stroke_width=3,
    )

    assert [cue["text"] for cue in result["cues"]] == [
        "人生是自己选出来的",
        "说实话以前我也这么想",
    ]
    assert all(
        len(app_module.content_characters(cue["text"])) >= 2
        for cue in result["cues"]
    )


def test_full_transcript_art_track_keeps_requested_large_font_size():
    words = [
        {"text": "人生", "start": 0.0, "end": 0.8},
        {"text": "是", "start": 0.8, "end": 1.2},
        {"text": "自己", "start": 1.2, "end": 1.8},
        {"text": "选出来的，", "start": 1.8, "end": 3.0},
        {"text": "说实话，", "start": 3.0, "end": 4.2},
        {"text": "以前", "start": 4.2, "end": 5.0},
        {"text": "我也", "start": 5.0, "end": 5.8},
        {"text": "这么", "start": 5.8, "end": 6.6},
        {"text": "想。", "start": 6.6, "end": 7.0},
    ]
    transcript = {
        "text": "".join(word["text"] for word in words),
        "segments": [
            {
                "text": "".join(word["text"] for word in words),
                "start": 0.0,
                "end": 7.0,
                "words": words,
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        7.0,
        1080,
        font_id="bold",
        font_size=70,
        letter_spacing=0,
        stroke_width=3,
    )

    assert result["fontSize"] == 70
    assert [cue["text"] for cue in result["cues"]] == [
        "人生是自己选出来的",
        "说实话以前我也这么想",
    ]
    assert all(
        len(app_module.content_characters(cue["text"]))
        <= app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE
        for cue in result["cues"]
    )


def test_full_transcript_art_track_uses_ai_semantic_breaks_and_limits_width():
    tokens = [
        "人",
        "这辈子",
        "最难",
        "突破的",
        "从来",
        "不是",
        "自己的",
        "能力，",
        "而是",
        "你身边",
        "所有人",
        "一起",
        "给你",
        "画的",
        "那条",
        "正常的",
        "线。",
    ]
    words = [
        {
            "text": token,
            "start": round(index * 0.3, 3),
            "end": round((index + 1) * 0.3, 3),
        }
        for index, token in enumerate(tokens)
    ]
    transcript = {
        "text": "".join(tokens),
        "segments": [
            {
                "text": "".join(tokens),
                "start": words[0]["start"],
                "end": words[-1]["end"],
                "words": words,
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        words[-1]["end"],
        1080,
        font_id="bold",
        font_size=70,
        letter_spacing=0,
        stroke_width=3,
        semantic_breaks=[3, 7, 11, 16],
        segmentation_method="ai",
    )

    cue_texts = [cue["text"] for cue in result["cues"]]
    assert "".join(cue_texts) == app_module.content_characters(
        transcript["text"]
    )
    assert cue_texts == [
        "人这辈子最难突破的",
        "从来不是自己的能力",
        "而是你身边所有人一起",
        "给你画的那条正常的线",
    ]
    assert all(
        len(app_module.content_characters(text))
        <= app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE
        for text in cue_texts
    )
    assert result["segmentationMethod"] == "ai"
    font = app_module.ImageFont.truetype(
        str(app_module.resolve_art_text_font_path("bold")),
        70,
    )
    assert all(
        app_module.measure_single_line_art_text(text, font, 0, 3)
        <= 1080 * 0.88 * 1.18
        for text in cue_texts
    )
    assert not any(
        len(app_module.content_characters(text)) < 5 for text in cue_texts
    )
    assert any(text.startswith("而是") for text in cue_texts)


def test_ai_transcript_art_text_segmentation_returns_valid_word_boundaries(
    monkeypatch: pytest.MonkeyPatch,
):
    words = [
        {"text": "这是", "start": 0.0, "end": 0.4},
        {"text": "第一句，", "start": 0.4, "end": 0.9},
        {"text": "这是", "start": 0.9, "end": 1.3},
        {"text": "第二句。", "start": 1.3, "end": 1.9},
    ]
    response = SimpleNamespace(
        status_code=app_module.HTTPStatus.OK,
        output=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"break_after":[1,3]}',
                    )
                )
            ]
        ),
    )
    captured: dict[str, object] = {}

    def fake_generation_call(**kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr(
        app_module.Generation,
        "call",
        fake_generation_call,
    )

    assert app_module.generate_transcript_art_text_breaks(
        words,
        max_characters=12,
        api_key="test-key",
    ) == [1, 3]
    assert captured["model"] == app_module.ART_TEXT_SEGMENTATION_MODEL
    assert captured["timeout"] == 12
    assert captured["enable_thinking"] is False
    system_prompt = captured["messages"][0]["content"]
    # The prompt must prefer a whole sentence on one line and only split a
    # sentence that exceeds the requested budget (12 here).
    assert "整句作为一条字幕" in system_prompt
    assert "12 个汉字时，才" in system_prompt
    assert "不能从一个词中间硬切" in system_prompt


@pytest.mark.parametrize(
    ("tokens", "semantic_breaks", "expected"),
    [
        (
            [
                "人",
                "这辈子",
                "最",
                "难",
                "突破的",
                "从来",
                "不是",
                "自己的",
                "能力。",
            ],
            [2, 8],
            ["人这辈子最难", "突破的从来", "不是自己的能力"],
        ),
        (
            [
                "人",
                "这辈子",
                "最",
                "难",
                "突破的",
                "从来",
                "不是",
                "自己的",
                "能力。",
            ],
            [1, 8],
            ["人这辈子最难", "突破的从来", "不是自己的能力"],
        ),
        (
            [
                "你",
                "身边",
                "人人",
                "都",
                "觉得",
                "一个月",
                "赚",
                "一万",
                "就",
                "顶天",
                "了。",
            ],
            [6, 10],
            ["你身边人人都", "觉得一个月赚", "一万就顶天了"],
        ),
    ],
)
def test_full_transcript_art_track_repairs_ai_breaks_inside_phrases(
    tokens: list[str],
    semantic_breaks: list[int],
    expected: list[str],
):
    words = [
        {
            "text": token,
            "start": round(index * 0.3, 3),
            "end": round((index + 1) * 0.3, 3),
        }
        for index, token in enumerate(tokens)
    ]
    transcript = {
        "text": "".join(tokens),
        "segments": [
            {
                "text": "".join(tokens),
                "start": 0.0,
                "end": words[-1]["end"],
                "words": words,
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        words[-1]["end"],
        720,
        font_id="bold",
        font_size=70,
        letter_spacing=0,
        stroke_width=3,
        semantic_breaks=semantic_breaks,
        segmentation_method="ai",
    )

    assert [cue["text"] for cue in result["cues"]] == expected
    assert all(
        len(app_module.content_characters(cue["text"]))
        <= app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE
        for cue in result["cues"]
    )


def _build_track_words(tokens: list[str]) -> list[dict[str, object]]:
    return [
        {
            "text": token,
            "start": round(index * 0.3, 3),
            "end": round((index + 1) * 0.3, 3),
        }
        for index, token in enumerate(tokens)
    ]


def test_transcript_art_text_track_keeps_two_short_sentences_separate():
    tokens = ["我同意。", "走吧。"]
    words = _build_track_words(tokens)
    transcript = {
        "text": "".join(tokens),
        "segments": [
            {
                "text": "".join(tokens),
                "start": 0.0,
                "end": words[-1]["end"],
                "words": words,
            }
        ],
    }
    result = app_module.build_transcript_art_text_track(
        transcript,
        words[-1]["end"],
        1080,
        font_id="bold",
        font_size=54,
        letter_spacing=0,
        stroke_width=3,
    )

    # Two complete short sentences must not be jammed onto one line.
    assert [cue["text"] for cue in result["cues"]] == ["我同意", "走吧"]


def test_transcript_art_text_track_folds_single_character_sentence_into_next():
    tokens = ["对。", "我们今天出发。"]
    words = _build_track_words(tokens)
    transcript = {
        "text": "".join(tokens),
        "segments": [
            {
                "text": "".join(tokens),
                "start": 0.0,
                "end": words[-1]["end"],
                "words": words,
            }
        ],
    }
    result = app_module.build_transcript_art_text_track(
        transcript,
        words[-1]["end"],
        1080,
        font_id="bold",
        font_size=54,
        letter_spacing=0,
        stroke_width=3,
    )

    # A single-character sentence becomes a spoken lead-in instead of a lone
    # one-character line.
    assert [cue["text"] for cue in result["cues"]] == ["对我们今天出发"]


def test_transcript_art_text_track_splits_unpunctuated_long_phrase_naturally():
    tokens = [
        "我",
        "觉得",
        "这个",
        "世界",
        "真的",
        "很",
        "美好",
        "我们",
        "一定",
        "要",
        "坚持",
        "到底",
    ]
    words = _build_track_words(tokens)
    transcript = {
        "text": "".join(tokens),
        "segments": [
            {
                "text": "".join(tokens),
                "start": 0.0,
                "end": words[-1]["end"],
                "words": words,
            }
        ],
    }
    result = app_module.build_transcript_art_text_track(
        transcript,
        words[-1]["end"],
        1080,
        font_id="bold",
        font_size=54,
        letter_spacing=0,
        stroke_width=3,
    )
    cues = [cue["text"] for cue in result["cues"]]

    assert len(cues) >= 2
    assert "".join(cues) == app_module.content_characters(transcript["text"])
    assert all(
        2
        <= len(app_module.content_characters(cue["text"]))
        <= app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE
        for cue in result["cues"]
    )


def test_transcript_art_text_character_limit_adapts_to_font_and_width():
    font_path = app_module.resolve_art_text_font_path("bold")
    small_font = app_module.ImageFont.truetype(str(font_path), 54)
    big_font = app_module.ImageFont.truetype(str(font_path), 90)

    small_limit = app_module.transcript_art_text_character_limit(
        small_font,
        1080,
        0,
        3,
    )
    big_limit = app_module.transcript_art_text_character_limit(
        big_font,
        1080,
        0,
        3,
    )

    # The 54px font fits the safe line fully (up to the semantic ceiling); the
    # 90px font is width-bound to fewer characters per line.
    assert 10 <= small_limit <= app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE
    assert 6 <= big_limit < small_limit


def test_art_text_splitter_prefers_audio_pause_boundaries():
    # No punctuation, but the audio pauses at the natural phrase boundaries.
    # The splitter must honor those pauses — a general, content-independent
    # signal — instead of falling back to an arbitrary balanced cut.
    tokens = [
        "咱们",
        "判断",
        "一件事",
        "靠不靠谱",
        "很少",
        "去琢磨",
        "这件事",
        "本身",
        "行不行",
        "第一",
        "反应",
        "都是",
        "身边",
        "也没有",
        "人干成过",
    ]
    pause_after = {"靠不靠谱", "行不行", "都是"}
    words = []
    cursor = 0.0
    for token in tokens:
        words.append(
            {
                "text": token,
                "start": round(cursor, 3),
                "end": round(cursor + 0.3, 3),
                "segmentIndex": 0,
            }
        )
        cursor += 0.3
        if token in pause_after:
            cursor += 0.4
    transcript = {
        "text": "".join(tokens),
        "segments": [
            {
                "text": "".join(tokens),
                "start": 0.0,
                "end": cursor,
                "words": words,
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        cursor,
        1080,
        font_id="bold",
        font_size=54,
        letter_spacing=0,
        stroke_width=3,
    )
    cues = [cue["text"] for cue in result["cues"]]

    # The pause after "靠不靠谱" makes it the first break even though a
    # balanced cut would prefer a point closer to the arithmetic middle.
    assert cues[0] == "咱们判断一件事靠不靠谱"
    assert all(
        2 <= len(app_module.content_characters(cue)) <= 12 for cue in cues
    )


def test_full_transcript_art_track_rejects_missing_word_timestamps():
    transcript = {
        "text": "只有段落时间",
        "segments": [
            {
                "text": "只有段落时间",
                "start": 0.0,
                "end": 1.0,
                "words": [],
            }
        ],
    }

    with pytest.raises(ValueError, match="缺少词级时间戳"):
        app_module.build_transcript_art_text_track(
            transcript,
            1.0,
            1080,
            font_id="bold",
            font_size=54,
            letter_spacing=0,
            stroke_width=3,
        )


def test_full_transcript_art_track_repairs_zero_duration_boundary_words():
    transcript = {
        "text": "你身边人人都觉得。",
        "segments": [
            {
                "text": "你身边人人都觉得。",
                "start": 22.92,
                "end": 24.36,
                "words": [
                    {"text": "你", "start": 22.92, "end": 22.92},
                    {"text": "身边", "start": 22.92, "end": 23.28},
                    {"text": "人人", "start": 23.28, "end": 24.0},
                    {"text": "都觉得。", "start": 24.0, "end": 24.36},
                ],
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        24.36,
        1080,
        font_id="bold",
        font_size=54,
        letter_spacing=0,
        stroke_width=3,
    )

    assert "".join(cue["text"] for cue in result["cues"]) == (
        app_module.content_characters(transcript["text"])
    )
    assert all(cue["end"] > cue["start"] for cue in result["cues"])


def test_full_transcript_art_track_keeps_spoken_clause_and_word_time_together():
    words = [
        {"text": "你", "start": 22.92, "end": 22.92},
        {"text": "身边", "start": 22.92, "end": 23.28},
        {"text": "人人", "start": 23.28, "end": 24.0},
        {"text": "都", "start": 24.0, "end": 24.36},
        {"text": "觉得", "start": 24.36, "end": 25.08},
        {"text": "一个月", "start": 25.08, "end": 26.16},
        {"text": "赚", "start": 26.16, "end": 26.52},
        {"text": "一万", "start": 26.52, "end": 27.24},
        {"text": "就", "start": 27.24, "end": 27.6},
        {"text": "顶天", "start": 27.6, "end": 28.32},
        {"text": "了，", "start": 28.32, "end": 29.04},
        {"text": "你", "start": 29.054, "end": 29.278},
        {"text": "很", "start": 29.278, "end": 29.503},
        {"text": "难", "start": 29.503, "end": 29.728},
        {"text": "真的", "start": 29.728, "end": 30.176},
        {"text": "坚信", "start": 30.176, "end": 30.626},
        {"text": "自己", "start": 30.626, "end": 31.075},
        {"text": "能", "start": 31.075, "end": 31.299},
        {"text": "赚", "start": 31.299, "end": 31.524},
        {"text": "十万。", "start": 31.524, "end": 32.2},
    ]
    transcript = {
        "text": "".join(word["text"] for word in words),
        "segments": [
            {
                "text": "".join(word["text"] for word in words),
                "start": 22.92,
                "end": 32.2,
                "words": words,
            }
        ],
    }

    result = app_module.build_transcript_art_text_track(
        transcript,
        32.2,
        1080,
        font_id="bold",
        font_size=54,
        letter_spacing=0,
        stroke_width=3,
    )

    assert [
        {key: cue[key] for key in ("text", "start", "end")}
        for cue in result["cues"]
    ] == [
        {
            "text": "你身边人人都觉得",
            "start": 22.92,
            "end": 25.08,
        },
        {
            "text": "一个月赚一万就顶天了",
            "start": 25.08,
            "end": 29.04,
        },
        {
            "text": "你很难真的坚信",
            "start": 29.054,
            "end": 30.626,
        },
        {
            "text": "自己能赚十万",
            "start": 30.626,
            "end": 32.2,
        },
    ]
    assert all(
        len(cue["characterTimings"])
        == len(app_module.content_characters(cue["text"]))
        for cue in result["cues"]
    )
    assert all(
        len(app_module.content_characters(cue["text"]))
        <= app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE
        for cue in result["cues"]
    )
    assert all(
        not any(unicodedata.category(char).startswith("P") for char in cue["text"])
        for cue in result["cues"]
    )


def test_transcript_track_allows_many_cues_but_keeps_one_shared_style():
    shared = {
        "font": "bold",
        "fontSize": 42,
        "color": "#FFD84D",
        "strokeColor": "#071018",
        "strokeWidth": 3,
        "shadow": True,
        "x": 0.5,
        "y": 0.82,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 0,
        "artStyle": "impact",
        "trackId": "transcript-full",
        "trackType": "transcript",
    }
    cues = [
        app_module.TextOverlay(
            text=f"第{index}句",
            start=index * 0.1,
            end=index * 0.1 + 0.08,
            **shared,
        )
        for index in range(30)
    ]

    normalized = app_module.normalize_text_overlays(cues, 3.0)

    assert len(normalized) == 30
    assert all(item["charsPerLine"] == 0 for item in normalized)
    inconsistent = [*cues]
    inconsistent[-1] = inconsistent[-1].model_copy(update={"color": "#FFFFFF"})
    with pytest.raises(ValueError, match="同一套样式"):
        app_module.normalize_text_overlays(inconsistent, 3.0)


def test_spoken_character_bounce_requires_matching_transcript_timings():
    shared = {
        "text": "同步",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFF36A",
        "strokeColor": "#0A0A0A",
        "strokeWidth": 4,
        "shadow": True,
        "x": 0.5,
        "y": 0.82,
        "start": 0.2,
        "end": 1.0,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 0,
        "artStyle": "comic",
        "trackId": "transcript-full",
        "trackType": "transcript",
        "animation": app_module.ArtTextAnimation(type="character-bounce"),
    }
    overlay = app_module.TextOverlay(
        **shared,
        characterTimings=[
            app_module.ArtTextCharacterTiming(start=0.2, end=0.5),
            app_module.ArtTextCharacterTiming(start=0.5, end=0.9),
        ],
    )

    normalized = app_module.normalize_text_overlays([overlay], 1.2)

    assert normalized[0]["characterTimings"] == [
        {"start": 0.2, "end": 0.5},
        {"start": 0.5, "end": 0.9},
    ]
    with pytest.raises(ValueError, match="缺少词级时间"):
        app_module.normalize_text_overlays(
            [app_module.TextOverlay(**shared)],
            1.2,
        )


def test_transcript_track_rejects_legacy_long_cue_before_rendering():
    shared = {
        "font": "bold",
        "fontSize": 42,
        "color": "#FFD84D",
        "strokeColor": "#071018",
        "strokeWidth": 3,
        "shadow": True,
        "x": 0.5,
        "y": 0.82,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 0,
        "artStyle": "impact",
        "trackId": "transcript-full",
        "trackType": "transcript",
    }
    overlay = app_module.TextOverlay(
        text="你身边人人都觉得一个月赚一万就顶天了",
        start=0.0,
        end=2.0,
        **shared,
    )

    with pytest.raises(
        ValueError,
        match=f"最多只能显示 {app_module.TRANSCRIPT_ART_TEXT_MAX_CHARS_PER_CUE} 个字",
    ):
        app_module.normalize_text_overlays([overlay], 3.0)


def test_transcript_track_endpoint_uses_selected_video_transcript(
    sample_video: Path,
):
    job_id = "31313131-3131-3131-3131-313131313131"
    words = [
        {"text": "词级", "start": 0.0, "end": 0.4},
        {"text": "同步。", "start": 0.4, "end": 0.9},
    ]
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {
                "text": "词级同步。",
                "duration": 1.0,
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 0.9,
                        "text": "词级同步。",
                        "words": words,
                    }
                ],
            },
            "edit": None,
            "art": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/art-text/transcript-track",
            json={
                "source": "original",
                "font": "bold",
                "fontSize": 42,
                "letterSpacing": 0,
                "strokeWidth": 3,
            },
        )

    assert response.status_code == 200
    assert response.json()["trackType"] == "transcript"
    assert "".join(cue["text"] for cue in response.json()["cues"]) == "词级同步"
    assert len(response.json()["cues"][0]["characterTimings"]) == 4


def test_transcript_track_endpoint_uses_live_cut_draft_with_source_anchors(
    sample_video: Path,
):
    job_id = "32323232-3232-3232-3232-323232323232"
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "filename": sample_video.name,
            "duration": 1.0,
            "status": "completed",
            "result": {"text": "原始文案", "duration": 1.0, "segments": []},
            "edit": None,
            "art": None,
        }
        app_module.JOB_FILES[job_id] = sample_video

    draft_words = [
        {
            "text": "实时",
            "start": 0.0,
            "end": 0.25,
            "sourceStart": 0.2,
            "sourceEnd": 0.45,
        },
        {
            "text": "同步。",
            "start": 0.25,
            "end": 0.6,
            "sourceStart": 0.45,
            "sourceEnd": 0.8,
        },
    ]
    draft_transcript = {
        "text": "实时同步。",
        "segments": [
            {
                "text": "实时同步。",
                "start": 0.0,
                "end": 0.6,
                "sourceStart": 0.2,
                "sourceEnd": 0.8,
                "words": draft_words,
            }
        ],
    }

    with TestClient(app_module.app) as client:
        response = client.post(
            f"/api/transcriptions/{job_id}/art-text/transcript-track",
            json={
                "source": "original",
                "font": "bold",
                "fontSize": 42,
                "letterSpacing": 0,
                "strokeWidth": 3,
                "draftTranscript": draft_transcript,
                "draftDuration": 0.6,
            },
        )

    assert response.status_code == 200
    result = response.json()
    assert result["segmentationMethod"] == "local"
    cues = result["cues"]
    assert "".join(cue["text"] for cue in cues) == "实时同步"
    assert cues[0]["start"] == 0.0
    assert cues[-1]["end"] == 0.6
    assert cues[0]["sourceStart"] == 0.2
    assert cues[-1]["sourceEnd"] == 0.8

    updated_draft = {
        "text": "同步。",
        "segments": [
            {
                "text": "同步。",
                "start": 0.0,
                "end": 0.35,
                "sourceStart": 0.45,
                "sourceEnd": 0.8,
                "words": [
                    {
                        "text": "同步。",
                        "start": 0.0,
                        "end": 0.35,
                        "sourceStart": 0.45,
                        "sourceEnd": 0.8,
                    }
                ],
            }
        ],
    }
    with TestClient(app_module.app) as client:
        updated_response = client.post(
            f"/api/transcriptions/{job_id}/art-text/transcript-track",
            json={
                "source": "original",
                "font": "bold",
                "fontSize": 42,
                "letterSpacing": 0,
                "strokeWidth": 3,
                "draftTranscript": updated_draft,
                "draftDuration": 0.35,
            },
        )

    assert updated_response.status_code == 200
    updated_cues = updated_response.json()["cues"]
    assert "".join(cue["text"] for cue in updated_cues) == "同步"
    assert updated_cues[0]["start"] == 0.0
    assert updated_cues[-1]["end"] == 0.35
    assert updated_cues[0]["sourceStart"] == 0.45


def test_art_text_balances_lines_and_keeps_closing_punctuation_off_line_start():
    overlay = {
        "text": "青年也应心系家国，坚守“位卑不敢忘忧国”，照亮青春星火。",
        "direction": "horizontal",
        "charsPerLine": 10,
        "letterSpacing": 0,
        "lineSpacing": 8,
    }

    lines = app_module.format_overlay_text(overlay).splitlines()

    assert lines == [
        "青年也应心系家国，",
        "坚守“位卑不敢忘忧",
        "国”，照亮青春星火。",
    ]
    assert max(map(len, lines)) - min(map(len, lines)) <= 1
    assert not any(
        line[0] in app_module.LINE_START_FORBIDDEN_PUNCTUATION
        for line in lines
    )


def test_balanced_multiline_art_text_renders_with_uniform_line_heights(
    tmp_path: Path,
):
    output_path = tmp_path / "balanced-lines.png"
    overlay = {
        "text": "青年也应心系家国，坚守“位卑不敢忘忧国”，照亮青春星火。",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFFFFF",
        "strokeColor": "#071018",
        "strokeWidth": 0,
        "shadow": False,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 10,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "clean",
    }

    app_module.render_art_text_layer(output_path, overlay)

    with app_module.Image.open(output_path) as rendered:
        alpha = rendered.getchannel("A")
        occupied_rows = [
            row
            for row in range(rendered.height)
            if alpha.crop((0, row, rendered.width, row + 1)).getbbox()
        ]
    bands: list[list[int]] = []
    for row in occupied_rows:
        if not bands or row > bands[-1][-1] + 1:
            bands.append([row])
        else:
            bands[-1].append(row)

    assert len(bands) == 3
    line_heights = [len(band) for band in bands]
    assert max(line_heights) - min(line_heights) <= 2


def test_all_art_text_templates_render_transparent_layers(tmp_path: Path):
    assert app_module.ART_TEXT_STYLES == {
        "impact",
        "neon",
        "metal",
        "sticker",
        "clean",
        "gradient",
        "comic",
        "ice",
        "ink",
        "ribbon",
        "luxury",
    }
    overlay = {
        "text": "艺术字",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFD84D",
        "strokeColor": "#071018",
        "strokeWidth": 3,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 10,
        "letterSpacing": 2,
        "lineSpacing": 8,
    }

    for art_style in app_module.ART_TEXT_STYLES:
        output_path = tmp_path / f"{art_style}.png"
        app_module.render_art_text_layer(
            output_path,
            {**overlay, "artStyle": art_style},
        )
        with app_module.Image.open(output_path) as rendered:
            assert rendered.mode == "RGBA"
            assert rendered.width > 80
            assert rendered.height > 50
            assert rendered.getbbox() is not None


def test_every_art_text_effect_layer_reuses_fixed_multiline_positions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original_text = app_module.ImageDraw.ImageDraw.text
    recorded_y_positions: list[float] = []

    def record_text(draw, xy, text, *args, **kwargs):
        recorded_y_positions.append(float(xy[1]))
        return original_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(app_module.ImageDraw.ImageDraw, "text", record_text)
    overlay = {
        "text": "同步\n同步\n同步\n同步",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFD84D",
        "strokeColor": "#15110A",
        "strokeWidth": 3,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 8,
    }
    expected_advance = overlay["fontSize"] + overlay["lineSpacing"]

    for art_style in app_module.ART_TEXT_STYLES:
        recorded_y_positions.clear()
        app_module.render_art_text_layer(
            tmp_path / f"fixed-lines-{art_style}.png",
            {**overlay, "artStyle": art_style},
        )

        assert recorded_y_positions
        assert len(recorded_y_positions) % 4 == 0
        for start in range(0, len(recorded_y_positions), 4):
            layer_positions = recorded_y_positions[start : start + 4]
            assert [
                round(layer_positions[index + 1] - layer_positions[index], 4)
                for index in range(3)
            ] == [expected_advance] * 3


def test_exported_templates_follow_preview_shadow_toggle_contract(
    tmp_path: Path,
):
    overlay = {
        "text": "预览一致",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFD84D",
        "strokeColor": "#15110A",
        "strokeWidth": 3,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 10,
        "letterSpacing": 0,
        "lineSpacing": 8,
    }
    always_on_effect_styles = app_module.ART_TEXT_STYLES - {"ink", "clean"}

    for art_style in app_module.ART_TEXT_STYLES:
        rendered_pixels = []
        for shadow in (False, True):
            output_path = tmp_path / f"{art_style}-{shadow}.png"
            app_module.render_art_text_layer(
                output_path,
                {
                    **overlay,
                    "artStyle": art_style,
                    "shadow": shadow,
                },
            )
            with Image.open(output_path).convert("RGBA") as rendered:
                rendered_pixels.append(rendered.tobytes())

        if art_style in always_on_effect_styles:
            assert rendered_pixels[0] == rendered_pixels[1]
        else:
            assert rendered_pixels[0] != rendered_pixels[1]


def test_impact_art_text_keeps_preview_like_thin_rim_and_soft_shadow(
    tmp_path: Path,
):
    output_path = tmp_path / "impact-preview-match.png"
    overlay = {
        "text": "预览效果",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFD84D",
        "strokeColor": "#15110A",
        "strokeWidth": 3,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 10,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "impact",
    }

    app_module.render_art_text_layer(output_path, overlay)

    with Image.open(output_path).convert("RGBA") as rendered:
        pixels = list(rendered.get_flattened_data())
    white_pixels = sum(
        1
        for red, green, blue, alpha in pixels
        if alpha > 220 and red > 235 and green > 235 and blue > 235
    )
    yellow_pixels = sum(
        1
        for red, green, blue, alpha in pixels
        if alpha > 220 and red > 220 and 150 < green < 235 and blue < 120
    )

    assert white_pixels > 0
    assert yellow_pixels > 0
    assert white_pixels > yellow_pixels * 0.03
    assert white_pixels < yellow_pixels * 0.18


def test_center_highlight_art_text_renders_white_edges_and_yellow_center(
    tmp_path: Path,
):
    output_path = tmp_path / "center-highlight.png"
    overlay = {
        "text": "别再乱买衣服啦!",
        "font": "bold",
        "fontSize": 72,
        "color": "#FFF36A",
        "strokeColor": "#0A0A0A",
        "strokeWidth": 4,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "comic",
        "textColorMode": "center-highlight",
        "secondaryColor": "#FFFFFF",
    }

    app_module.render_art_text_layer(output_path, overlay)

    with Image.open(output_path).convert("RGBA") as rendered:
        pixels = list(rendered.get_flattened_data())
    white_pixels = sum(
        1
        for red, green, blue, alpha in pixels
        if alpha > 220 and red > 238 and green > 238 and blue > 238
    )
    yellow_pixels = sum(
        1
        for red, green, blue, alpha in pixels
        if alpha > 220 and red > 230 and green > 210 and blue < 150
    )

    assert white_pixels > 100
    assert yellow_pixels > 100


def test_character_bounce_art_text_asset_contains_multiple_frames(
    tmp_path: Path,
):
    output_path = tmp_path / "character-bounce.png"
    overlay = {
        "text": "别再乱买衣服啦!",
        "font": "bold",
        "fontSize": 72,
        "color": "#FFF36A",
        "strokeColor": "#0A0A0A",
        "strokeWidth": 4,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "comic",
        "textColorMode": "center-highlight",
        "secondaryColor": "#FFFFFF",
        "animation": {
            "type": "character-bounce",
            "duration": 0.56,
            "stagger": 0.07,
            "amplitude": 0.18,
        },
        "start": 0.0,
        "end": 2.0,
        "characterTimings": [
            {"start": index * 0.2, "end": index * 0.2 + 0.16}
            for index in range(8)
        ],
    }

    assert app_module.render_art_text_asset(output_path, overlay) is True
    with Image.open(output_path) as rendered:
        assert rendered.is_animated
        assert rendered.n_frames >= 24
        rendered.seek(0)
        first_frame = rendered.convert("RGBA").tobytes()
        rendered.seek(rendered.n_frames // 2)
        middle_frame = rendered.convert("RGBA").tobytes()

    assert first_frame != middle_frame


def test_character_bounce_without_speech_times_stays_static(tmp_path: Path):
    output_path = tmp_path / "untimed-character-bounce.png"
    overlay = {
        "text": "没有时间",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFF36A",
        "strokeColor": "#0A0A0A",
        "strokeWidth": 3,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "comic",
        "animation": {"type": "character-bounce"},
    }

    assert app_module.render_art_text_asset(output_path, overlay) is False
    with Image.open(output_path) as rendered:
        assert not rendered.is_animated


def test_impact_art_text_has_no_opaque_duplicate_glyph_below_text(
    tmp_path: Path,
):
    output_path = tmp_path / "impact-no-duplicate-shadow.png"
    overlay = {
        "text": "正常阴影",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFD84D",
        "strokeColor": "#15110A",
        "strokeWidth": 3,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 10,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "impact",
    }

    app_module.render_art_text_layer(output_path, overlay)

    with Image.open(output_path).convert("RGBA") as rendered:
        yellow_rows = []
        opaque_dark_rows = []
        for row in range(rendered.height):
            pixels = rendered.crop(
                (0, row, rendered.width, row + 1)
            ).get_flattened_data()
            if any(
                alpha > 220
                and red > 220
                and 150 < green < 235
                and blue < 120
                for red, green, blue, alpha in pixels
            ):
                yellow_rows.append(row)
            if any(
                alpha > 220 and red < 50 and green < 50 and blue < 50
                for red, green, blue, alpha in pixels
            ):
                opaque_dark_rows.append(row)

    assert yellow_rows
    assert opaque_dark_rows
    assert max(opaque_dark_rows) - max(yellow_rows) <= 5


def test_art_text_video_uses_short_relative_ffmpeg_command_for_many_cues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    input_path = tmp_path / "source.mp4"
    output_path = tmp_path / "art-text.mp4"
    input_path.write_bytes(b"source")
    captured: dict[str, object] = {}

    monkeypatch.setattr(app_module, "probe_video_dimensions", lambda path: (1080, 1920))
    monkeypatch.setattr(app_module, "render_art_text_layer", lambda *args, **kwargs: None)

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        (Path(kwargs["cwd"]) / command[-1]).write_bytes(b"rendered")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(app_module, "run_ffmpeg", fake_run)
    overlays = [
        {
            "text": f"第{index + 1}条同步文案",
            "font": "bold",
            "fontSize": 70,
            "color": "#FFD84D",
            "strokeColor": "#15110A",
            "strokeWidth": 3,
            "shadow": True,
            "x": 0.5,
            "y": 0.82,
            "start": index * 0.5,
            "end": index * 0.5 + 0.48,
            "direction": "horizontal",
            "textAlign": "center",
            "charsPerLine": 0,
            "letterSpacing": 0,
            "lineSpacing": 0,
            "artStyle": "impact",
        }
        for index in range(180)
    ]

    app_module.render_art_text_video(input_path, output_path, overlays)

    command = captured["command"]
    assert "-filter_complex_script" in command
    assert "-filter_complex" not in command
    assert captured["cwd"] == input_path.parent
    assert str(input_path) not in command
    assert len(subprocess.list2cmdline(command)) < 12000
    assert output_path.is_file()


def test_character_bounce_video_plays_asset_once_from_overlay_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    input_path = tmp_path / "source.mp4"
    output_path = tmp_path / "animated-art-text.mp4"
    input_path.write_bytes(b"source")
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        app_module,
        "probe_video_dimensions",
        lambda path: (1080, 1920),
    )
    monkeypatch.setattr(
        app_module,
        "render_art_text_asset",
        lambda *args, **kwargs: True,
    )

    def fake_run_ffmpeg(command, **kwargs):
        captured["command"] = command
        filter_path = Path(kwargs["cwd"]) / command[
            command.index("-filter_complex_script") + 1
        ]
        captured["filter"] = filter_path.read_text(encoding="utf-8")
        (Path(kwargs["cwd"]) / command[-1]).write_bytes(b"rendered")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(app_module, "run_ffmpeg", fake_run_ffmpeg)
    overlay = {
        "text": "逐字跃动",
        "font": "bold",
        "fontSize": 72,
        "color": "#FFF36A",
        "strokeColor": "#0A0A0A",
        "strokeWidth": 4,
        "shadow": True,
        "x": 0.5,
        "y": 0.5,
        "start": 1.25,
        "end": 3.0,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "comic",
        "animation": {"type": "character-bounce"},
    }

    app_module.render_art_text_video(input_path, output_path, [overlay])

    assert "-stream_loop" not in captured["command"]
    assert ["-i", "art-text-0.png"] == captured["command"][
        captured["command"].index("art-text-0.png") - 1 :
        captured["command"].index("art-text-0.png") + 1
    ]
    assert "[1:v]setpts=PTS-STARTPTS+1.250/TB[art0]" in captured["filter"]
    assert "[0:v][art0]overlay=" in captured["filter"]
    assert output_path.is_file()


def test_multiline_impact_art_text_keeps_every_line_visually_uniform(
    tmp_path: Path,
):
    output_path = tmp_path / "impact-multiline.png"
    overlay = {
        "text": (
            "如果你圈子里从来没有人拿\n"
            "到过结果，那你第一次碰到机\n"
            "会，第一反应肯定不是冲上去，\n"
            "而是先怀疑，先自我否定。"
        ),
        "font": "bold",
        "fontSize": 54,
        "color": "#FFD84D",
        "strokeColor": "#15110A",
        "strokeWidth": 3,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "impact",
    }

    app_module.render_art_text_layer(output_path, overlay)

    with Image.open(output_path).convert("RGBA") as rendered:
        yellow_rows = []
        for row in range(rendered.height):
            pixels = rendered.crop(
                (0, row, rendered.width, row + 1)
            ).get_flattened_data()
            if any(
                alpha > 220
                and red > 220
                and 150 < green < 235
                and blue < 120
                for red, green, blue, alpha in pixels
            ):
                yellow_rows.append(row)

    bands = []
    for row in yellow_rows:
        if not bands or row > bands[-1][-1] + 1:
            bands.append([row])
        else:
            bands[-1].append(row)

    assert len(bands) == 4
    assert max(map(len, bands)) - min(map(len, bands)) <= 1


def test_art_text_render_padding_is_trimmed_without_moving_anchor(
    tmp_path: Path,
):
    output_path = tmp_path / "trimmed-impact.png"
    overlay = {
        "text": "预览和生成保持一致",
        "font": "bold",
        "fontSize": 54,
        "color": "#FFD84D",
        "strokeColor": "#15110A",
        "strokeWidth": 3,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 10,
        "letterSpacing": 0,
        "lineSpacing": 8,
        "artStyle": "impact",
    }

    app_module.render_art_text_layer(output_path, overlay)

    with Image.open(output_path).convert("RGBA") as rendered:
        visible_bounds = rendered.getbbox()
        assert visible_bounds is not None
        left, top, right, bottom = visible_bounds
        margins = (
            left,
            top,
            rendered.width - right,
            rendered.height - bottom,
        )
        assert max(margins) <= 16


def test_art_text_layer_is_scaled_into_video_safe_area(tmp_path: Path):
    output_path = tmp_path / "safe-art-text.png"
    overlay = {
        "text": "SAFE TITLE " * 8,
        "font": "bold",
        "fontSize": 180,
        "color": "#FFD84D",
        "strokeColor": "#071018",
        "strokeWidth": 12,
        "shadow": True,
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 0,
        "letterSpacing": 8,
        "lineSpacing": 20,
        "artStyle": "impact",
    }

    app_module.render_art_text_layer(
        output_path,
        overlay,
        max_size=(294, 166),
    )

    with app_module.Image.open(output_path) as rendered:
        assert rendered.width <= 294
        assert rendered.height <= 166
        assert rendered.getbbox() is not None


def test_probe_video_dimensions(sample_video: Path):
    assert app_module.probe_video_dimensions(sample_video) == (320, 180)


def test_missing_job_returns_404():
    with TestClient(app_module.app) as client:
        response = client.get("/api/transcriptions/not-found")

    assert response.status_code == 404


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


def test_character_bounce_timings_skip_real_audio_pause():
    timings = app_module.transcript_art_text_character_timings(
        [{"text": "你身边人人都觉得", "start": 0.0, "end": 8.0}],
        0.0,
        8.0,
        [{"start": 1.2, "end": 4.2}],
    )

    assert len(timings) == 8
    assert all(not 1.2 <= timing["start"] < 4.2 for timing in timings)
    assert any(timing["start"] >= 4.2 for timing in timings)


def test_supplied_audio_aligned_timings_are_not_clamped_back_into_silence():
    timings = app_module.transcript_art_text_character_timings(
        [
            {
                "text": "AB",
                "start": 0.0,
                "end": 0.5,
                "characterTimings": [
                    {"start": 2.0, "end": 2.25},
                    {"start": 2.25, "end": 2.5},
                ],
            }
        ],
        0.0,
        0.5,
        [{"start": 0.0, "end": 2.0}],
    )

    assert timings == [
        {"start": 2.0, "end": 2.25},
        {"start": 2.25, "end": 2.5},
    ]


def test_character_bounce_overlay_starts_at_voice_after_leading_pause():
    overlays = app_module.align_text_overlays_to_audio_activity(
        [
            {
                "text": "开始",
                "start": 0.0,
                "end": 4.0,
                "animation": {"type": "character-bounce"},
                "characterTimings": [
                    {"start": 0.0, "end": 2.0},
                    {"start": 2.0, "end": 4.0},
                ],
            }
        ],
        [{"start": 0.0, "end": 2.0}],
    )

    assert overlays[0]["start"] == pytest.approx(2.0)
    assert all(timing["start"] >= 2.0 for timing in overlays[0]["characterTimings"])


def test_static_transcript_overlays_share_segment_audio_alignment():
    overlays = app_module.align_text_overlays_to_audio_activity(
        [
            {
                "text": "AB",
                "start": 0.0,
                "end": 0.5,
                "trackType": app_module.TRANSCRIPT_ART_TEXT_TRACK_TYPE,
                "animation": {"type": "none"},
                "characterTimings": [
                    {"start": 0.0, "end": 0.25},
                    {"start": 0.25, "end": 0.5},
                ],
            },
            {
                "text": "CD",
                "start": 2.0,
                "end": 3.0,
                "trackType": app_module.TRANSCRIPT_ART_TEXT_TRACK_TYPE,
                "animation": {"type": "none"},
                "characterTimings": [
                    {"start": 2.0, "end": 2.5},
                    {"start": 2.5, "end": 3.0},
                ],
            },
        ],
        [{"start": 0.0, "end": 2.0}],
        [{"start": 0.0, "end": 3.0, "text": "ABCD"}],
    )

    assert overlays[0]["start"] == pytest.approx(2.0)
    assert overlays[0]["end"] <= overlays[1]["start"]
    assert all(
        timing["start"] >= 2.0
        for overlay in overlays
        for timing in overlay["characterTimings"]
    )


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
