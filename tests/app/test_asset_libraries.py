from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


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
