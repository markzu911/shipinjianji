from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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
