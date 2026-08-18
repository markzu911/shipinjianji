from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


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
