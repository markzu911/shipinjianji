from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import server.app as app_module
from server import voice_activity_detection


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
        "CUT_DRAFT_PCM_CACHE_MAX_BYTES",
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

    def isolated_acoustic_alignment(
        _media_path: Path,
        segments: list[dict[str, object]],
        _job_directory: Path,
        _model_cache_dir: Path,
        **_kwargs,
    ) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            "sourceFingerprint": "test-runtime-isolated",
            "aligner": app_module.ACOUSTIC_ALIGNER_NAME,
            "modelRevision": app_module.ACOUSTIC_ALIGNMENT_MODEL_REVISION,
            "segments": [],
            "summary": {
                "status": "unavailable",
                "reason": "test_runtime_isolated",
                "segmentCount": 0,
                "totalSegmentCount": len(segments),
                "validSegmentCount": 0,
                "reusedSegmentCount": 0,
            },
        }

    monkeypatch.setattr(
        app_module,
        "ensure_acoustic_alignment_cache",
        isolated_acoustic_alignment,
    )
    monkeypatch.setattr(
        app_module,
        "analyze_local_voice_activity",
        lambda *_args, **_kwargs: {
            "status": "unavailable",
            "reason": "test_runtime_isolated",
            "speechRanges": [],
            "vad": voice_activity_detection.VAD_NAME,
            "modelId": voice_activity_detection.MODEL_ID,
            "modelRevision": voice_activity_detection.MODEL_REVISION,
        },
    )
    voice_activity_detection.clear_voice_activity_runtime_cache()
    with app_module.JOBS_LOCK:
        app_module.JOBS.clear()
        app_module.JOB_FILES.clear()
    with app_module.PROJECT_FAILURES_LOCK:
        app_module.PROJECT_RECOVERY_FAILURES.clear()
        app_module.PROJECT_SNAPSHOT_FAILURES.clear()
    with app_module.JOB_ATTEMPT_LOCKS_GUARD:
        app_module.JOB_ATTEMPT_LOCKS.clear()
    app_module.CUT_DRAFT_PCM_CACHE.clear()
    voice_activity_detection.clear_voice_activity_runtime_cache()
    yield
    for name, value in runtime_settings.items():
        setattr(app_module, name, value)
    app_module.dashscope.base_http_api_url = dashscope_http_url
    app_module.dashscope.base_websocket_api_url = dashscope_websocket_url
    app_module.CUT_DRAFT_PCM_CACHE.clear()
    with app_module.PROJECT_FAILURES_LOCK:
        app_module.PROJECT_RECOVERY_FAILURES.clear()
        app_module.PROJECT_SNAPSHOT_FAILURES.clear()
    with app_module.JOB_ATTEMPT_LOCKS_GUARD:
        app_module.JOB_ATTEMPT_LOCKS.clear()


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
