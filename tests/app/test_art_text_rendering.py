from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from PIL import Image

import server.app as app_module


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
