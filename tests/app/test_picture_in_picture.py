from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import server.app as app_module


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
