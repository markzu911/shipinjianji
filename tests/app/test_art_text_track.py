from __future__ import annotations

import unicodedata
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


def _build_track_words(tokens: list[str]) -> list[dict[str, object]]:
    return [
        {
            "text": token,
            "start": round(index * 0.3, 3),
            "end": round((index + 1) * 0.3, 3),
        }
        for index, token in enumerate(tokens)
    ]


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


def test_reliable_word_timings_are_not_reprojected_around_audio_pause():
    timings = app_module.transcript_art_text_character_timings(
        [{"text": "你身边人人都觉得", "start": 0.0, "end": 8.0}],
        0.0,
        8.0,
        [{"start": 1.2, "end": 4.2}],
    )

    assert len(timings) == 8
    assert timings[0] == {"start": 0.0, "end": 1.0}
    assert timings[2] == {"start": 2.0, "end": 3.0}


def test_quiet_sentence_tail_does_not_move_first_reliable_character():
    timings = app_module.transcript_art_text_character_timings(
        [{"text": "我也这么想", "start": 3.21, "end": 4.21}],
        3.11,
        5.0,
        [{"start": 3.96, "end": 5.0}],
    )

    assert timings[0]["start"] == pytest.approx(3.21, abs=0.01)


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


def test_static_transcript_overlays_keep_authoritative_character_timings():
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

    assert overlays[0]["start"] == pytest.approx(0.0)
    assert overlays[0]["end"] <= overlays[1]["start"]
    assert overlays[0]["characterTimings"] == [
        {"start": 0.0, "end": 0.25},
        {"start": 0.25, "end": 0.5},
    ]
