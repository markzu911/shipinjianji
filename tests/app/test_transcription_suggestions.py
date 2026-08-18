from __future__ import annotations

import io
import json
from array import array
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


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
            "asrWords": [
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
    assert [
        (word["start"], word["end"]) for word in updated_words
    ] == [
        (word["start"], word["end"]) for word in words
    ]

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

    segments = app_module.build_sentence_segments(
        semantic_words,
        asr_words=words,
    )
    assert [
        word
        for segment in segments
        for word in segment["asrWords"]
    ] == words


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
