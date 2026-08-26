from __future__ import annotations

import copy
import math
from array import array
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


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


def test_cut_draft_is_persisted_versioned_restored_and_cleared(
    monkeypatch: pytest.MonkeyPatch,
):
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

    snapshot_calls: list[str] = []
    original_save_cut_draft = app_module.save_cut_draft
    original_remove_cut_draft = app_module.remove_cut_draft

    def checked_save_cut_draft(saved_job_id: str, draft: dict[str, object]):
        assert not app_module.JOBS_LOCK.locked()
        original_save_cut_draft(saved_job_id, draft)

    def checked_remove_cut_draft(removed_job_id: str):
        assert not app_module.JOBS_LOCK.locked()
        original_remove_cut_draft(removed_job_id)

    def checked_persist_job_snapshot(persisted_job_id: str, **_kwargs) -> bool:
        assert not app_module.JOBS_LOCK.locked()
        snapshot_calls.append(persisted_job_id)
        return True

    monkeypatch.setattr(app_module, "save_cut_draft", checked_save_cut_draft)
    monkeypatch.setattr(app_module, "remove_cut_draft", checked_remove_cut_draft)
    monkeypatch.setattr(
        app_module,
        "persist_job_snapshot",
        checked_persist_job_snapshot,
    )

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
        stored_draft_text = app_module.cut_draft_path(job_id).read_text(
            encoding="utf-8"
        )
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
    assert saved.json()["retainedTranscript"] == {
        "text": "",
        "segments": [],
        "duration": 6.5,
        "audioQuietRanges": [],
    }
    draft = saved.json()["cutDraft"]
    assert "retainedTranscript" not in draft
    assert "retainedTranscript" not in stored_draft_text
    assert "retainedTranscript" not in app_module.CutDraftRequest.model_fields
    assert draft["schemaVersion"] == 1
    assert draft["revision"] == 1
    assert draft["automaticNoSpeechInitialized"] is True
    assert draft["textRanges"][0]["key"] == "1.000-2.000"
    assert draft["textRanges"][0]["start"] == 1.0
    assert draft["textRanges"][0]["end"] == 2.0
    assert draft["textRanges"][0]["adjacentSilenceBefore"] == 0.0
    assert draft["textRanges"][0]["adjacentSilenceAfter"] == 0.0
    assert draft["noSpeechRanges"] == [
        {"key": "silence-1", "start": 4.0, "end": 5.5}
    ]
    assert draft["timelineRanges"] == [
        {
            "start": 7.0,
            "end": 8.0,
            "originalStart": 7.0,
            "originalEnd": 8.0,
        }
    ]
    assert draft_file_exists_after_save is True
    assert stale.status_code == 409
    assert "其他页面更新" in stale.json()["detail"]
    assert restored.status_code == 200
    assert restored.json()["cutDraft"] == draft
    assert restored.json()["retainedTranscript"] == saved.json()["retainedTranscript"]
    assert rendered_job.json()["cutDraft"] == draft
    assert cleared.status_code == 200
    assert cleared.json() == {"status": "cleared"}
    assert after_clear.json()["cutDraft"] is None
    assert not app_module.cut_draft_path(job_id).exists()
    assert snapshot_calls == [job_id, job_id]


def test_cut_draft_commit_survives_async_snapshot_metadata_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "38383838-3838-4838-8838-383838383838"
    app_module.cut_draft_path(job_id).parent.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }

    def fail_snapshot(_job_id: str, **_kwargs):
        raise OSError("snapshot unavailable")

    monkeypatch.setattr(app_module, "persist_job_snapshot", fail_snapshot)
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
        restored = client.get(f"/api/transcriptions/{job_id}/cut-draft")

    assert saved.status_code == 200
    assert restored.json()["cutDraft"]["revision"] == 1
    assert app_module.cut_draft_path(job_id).is_file()
    with app_module.PROJECT_FAILURES_LOCK:
        assert any(
            item["id"] == job_id and "snapshot unavailable" in item["error"]
            for item in app_module.PROJECT_SNAPSHOT_FAILURES
        )


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


def test_legacy_cut_draft_loads_with_empty_split_points():
    job_id = "45454545-4545-4545-8545-454545454545"
    path = app_module.cut_draft_path(job_id)
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schemaVersion": 1, "revision": 3, "timelineRanges": []}',
        encoding="utf-8",
    )

    draft = app_module.load_cut_draft(job_id)

    assert draft is not None
    assert draft["revision"] == 3
    assert draft["splitPoints"] == []


def test_cut_draft_persists_split_points_and_exact_adjacent_clip_range(
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "46464646-4646-4646-8646-464646464646"
    app_module.cut_draft_path(job_id).parent.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }

    def fail_acoustic_load(*_args, **_kwargs):
        raise AssertionError("split_exact must not load forced-alignment evidence")

    def fail_pcm_decode(*_args, **_kwargs):
        raise AssertionError("split_exact must not decode or inspect PCM")

    monkeypatch.setattr(
        app_module,
        "load_job_acoustic_alignment",
        fail_acoustic_load,
    )
    monkeypatch.setattr(
        app_module,
        "decode_cut_draft_audio_samples",
        fail_pcm_decode,
    )

    payload = {
        "revision": 0,
        "textRanges": [],
        "noSpeechRanges": [],
        "splitPoints": [
            {"key": "split-b", "sourceTime": 7.0},
            {"key": "split-a", "sourceTime": 3.0},
        ],
        "timelineRanges": [
            {
                "key": "timeline-exact-a-b",
                "start": 3.0,
                "end": 7.0,
                "originalStart": 3.0,
                "originalEnd": 7.0,
                "boundaryMode": "split_exact",
                "splitClipKey": "split-clip:split-a:split-b",
            }
        ],
    }

    with TestClient(app_module.app) as client:
        saved = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=payload,
        )
        restored = client.get(f"/api/transcriptions/{job_id}/cut-draft")

    assert saved.status_code == 200
    draft = saved.json()["cutDraft"]
    assert draft["schemaVersion"] == 1
    assert draft["splitPoints"] == [
        {"key": "split-a", "sourceTime": 3.0},
        {"key": "split-b", "sourceTime": 7.0},
    ]
    assert draft["timelineRanges"] == [
        {
            "key": "timeline-exact-a-b",
            "start": 3.0,
            "end": 7.0,
            "originalStart": 3.0,
            "originalEnd": 7.0,
            "boundaryMode": "split_exact",
            "splitClipKey": "split-clip:split-a:split-b",
        }
    ]
    assert draft["acousticAlignment"]["status"] == "not_required"
    assert [item["fallbackReason"] for item in draft["boundaryDiagnostics"]] == [
        "split_boundary_exact",
        "split_boundary_exact",
    ]
    assert restored.json()["cutDraft"] == draft


def test_split_points_do_not_change_manual_timeline_range_alignment_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "47474747-4747-4747-8747-474747474747"
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"source")
    app_module.cut_draft_path(job_id).parent.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    acoustic_calls: list[list[dict[str, float]]] = []
    pcm_calls = 0

    def load_alignment(_path, _segments, relevant_ranges):
        acoustic_calls.append(relevant_ranges)
        return None, {"status": "unavailable"}

    def decode_pcm(_path: Path) -> array:
        nonlocal pcm_calls
        pcm_calls += 1
        return array("h", [0]) * (10 * app_module.CUT_BOUNDARY_SAMPLE_RATE)

    monkeypatch.setattr(app_module, "load_job_acoustic_alignment", load_alignment)
    monkeypatch.setattr(app_module, "decode_cut_draft_audio_samples", decode_pcm)

    with TestClient(app_module.app) as client:
        saved = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={
                "revision": 0,
                "textRanges": [],
                "noSpeechRanges": [],
                "splitPoints": [{"key": "split-a", "sourceTime": 3.0}],
                "timelineRanges": [
                    {
                        "key": "manual-range",
                        "start": 7.0,
                        "end": 8.0,
                        "originalStart": 7.0,
                        "originalEnd": 8.0,
                    }
                ],
            },
        )

    assert saved.status_code == 200
    timeline_range = saved.json()["cutDraft"]["timelineRanges"][0]
    assert "boundaryMode" not in timeline_range
    assert "splitClipKey" not in timeline_range
    assert acoustic_calls == [[{"start": 7.0, "end": 8.0}]]
    assert pcm_calls == 1


@pytest.mark.parametrize(
    ("start", "end", "clip_key"),
    [
        (3.0, 8.0, "split-clip:split-a:split-b"),
        (3.0, 7.0, "split-clip:source-start:split-b"),
    ],
)
def test_cut_draft_rejects_split_exact_range_without_matching_adjacent_anchors(
    start: float,
    end: float,
    clip_key: str,
):
    job_id = "47474747-4747-4747-8747-474747474747"
    app_module.cut_draft_path(job_id).parent.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }

    with TestClient(app_module.app) as client:
        response = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={
                "revision": 0,
                "splitPoints": [
                    {"key": "split-a", "sourceTime": 3.0},
                    {"key": "split-b", "sourceTime": 7.0},
                ],
                "timelineRanges": [
                    {
                        "start": start,
                        "end": end,
                        "originalStart": start,
                        "originalEnd": end,
                        "boundaryMode": "split_exact",
                        "splitClipKey": clip_key,
                    }
                ],
            },
        )

    assert response.status_code == 400
    assert "相邻的源时间分割边界" in response.json()["detail"]


@pytest.mark.parametrize(
    ("split_points", "timeline_ranges", "expected_detail"),
    [
        (
            [{"key": "source-start", "sourceTime": 3.0}],
            [],
            "保留边界名称",
        ),
        (
            [{"key": "split-a", "sourceTime": 3.0}],
            [
                {
                    "start": 4.0,
                    "end": 5.0,
                    "splitClipKey": "split-clip:source-start:split-a",
                }
            ],
            "普通语音安全区间",
        ),
        (
            [{"key": "split-a", "sourceTime": 3.0}],
            [
                {
                    "start": 0.0,
                    "end": 3.0,
                    "boundaryMode": "split_exact",
                    "splitClipKey": "split-clip:source-start:split-a",
                },
                {
                    "start": 0.0,
                    "end": 3.0,
                    "boundaryMode": "split_exact",
                    "splitClipKey": "split-clip:source-start:split-a",
                },
            ],
            "不能重复删除",
        ),
    ],
)
def test_cut_draft_rejects_ambiguous_split_identity_contracts(
    split_points: list[dict[str, object]],
    timeline_ranges: list[dict[str, object]],
    expected_detail: str,
):
    job_id = "48484848-4848-4848-8848-484848484848"
    app_module.cut_draft_path(job_id).parent.mkdir(parents=True)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 10.0,
            "result": {"segments": []},
            "cutDraft": None,
        }

    with TestClient(app_module.app) as client:
        response = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={
                "revision": 0,
                "splitPoints": split_points,
                "timelineRanges": timeline_ranges,
            },
        )

    assert response.status_code == 400
    assert expected_detail in response.json()["detail"]


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
                {"text": "A", "start": 0.0, "end": 0.8},
                {"text": "B", "start": 1.0, "end": 2.0},
                {"text": "C", "start": 2.3, "end": 3.0},
            ],
            "asrWords": [
                {"text": "A", "start": 0.0, "end": 0.8},
                {"text": "B", "start": 1.0, "end": 2.0},
                {"text": "C", "start": 2.3, "end": 3.0},
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
    assert aligned["end"] < 2.3
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


def test_cut_draft_pcm_cache_preserves_ranges_diagnostics_and_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "37373737-3737-4737-8737-373737373737"
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"source")
    segments = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.18},
                {"text": "得你", "start": 0.18, "end": 0.6},
            ],
        }
    ]
    alignment_cache = {
        "segments": [
            {
                "segmentIndex": 0,
                "validation": {"valid": True},
                "characters": [
                    {"text": "觉", "start": 0.05, "end": 0.18},
                    {"text": "得", "start": 0.2, "end": 0.5},
                    {"text": "你", "start": 0.8, "end": 0.98},
                ],
            }
        ]
    }
    alignment_summary = {"status": "completed", "reusedSegmentCount": 0}
    monkeypatch.setattr(
        app_module,
        "load_job_acoustic_alignment",
        lambda *_args, **_kwargs: (alignment_cache, alignment_summary),
    )
    decode_calls = 0

    def decode(_path: Path) -> array:
        nonlocal decode_calls
        decode_calls += 1
        return array("h", [4_000]) * app_module.CUT_BOUNDARY_SAMPLE_RATE

    monkeypatch.setattr(app_module, "decode_cut_audio_samples", decode)
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 1.0,
            "result": {"segments": segments},
            "cutDraft": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    payload = {
        "revision": 0,
        "automaticNoSpeechInitialized": True,
        "textRanges": [
            {
                "key": "delete-jue-de",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        "noSpeechRanges": [],
        "timelineRanges": [
            {
                "key": "manual-jue-de",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
    }

    def reset_draft() -> None:
        app_module.remove_cut_draft(job_id)
        with app_module.JOBS_LOCK:
            app_module.JOBS[job_id]["cutDraft"] = None
        app_module.CUT_DRAFT_PCM_CACHE.clear()

    with TestClient(app_module.app) as client:
        monkeypatch.setattr(app_module, "CUT_DRAFT_PCM_CACHE_MAX_BYTES", 0)
        disabled_response = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=payload,
        )
        reset_draft()
        monkeypatch.setattr(
            app_module,
            "CUT_DRAFT_PCM_CACHE_MAX_BYTES",
            1024 * 1024,
        )
        enabled_response = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=payload,
        )
        enabled_draft = enabled_response.json()["cutDraft"]
        cached_response = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={**payload, "revision": enabled_draft["revision"]},
        )

    assert disabled_response.status_code == 200
    assert enabled_response.status_code == 200
    assert cached_response.status_code == 200
    disabled_draft = disabled_response.json()["cutDraft"]
    cached_draft = cached_response.json()["cutDraft"]
    equivalent_fields = (
        "revision",
        "textRanges",
        "timelineRanges",
        "boundaryDiagnostics",
        "acousticAlignment",
    )
    assert {
        key: disabled_draft[key] for key in equivalent_fields
    } == {key: enabled_draft[key] for key in equivalent_fields}
    assert enabled_draft["revision"] == 1
    assert cached_draft["revision"] == 2
    for key in equivalent_fields[1:]:
        assert cached_draft[key] == enabled_draft[key]
    assert decode_calls == 2


def test_cut_draft_put_persists_shared_forced_alignment_for_text_and_timeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "38383838-3838-4838-8838-383838383838"
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"source")
    segments = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.18},
                {"text": "得你", "start": 0.18, "end": 0.6},
            ],
        }
    ]
    alignment_calls: list[Path] = []

    def cached_alignment(
        media_path: Path,
        _segments: list[dict[str, object]],
        _job_dir: Path,
        _model_dir: Path,
        **_kwargs,
    ) -> dict[str, object]:
        alignment_calls.append(media_path)
        return {
            "segments": [
                {
                    "segmentIndex": 0,
                    "validation": {"valid": True},
                    "characters": [
                        {"text": "觉", "start": 0.05, "end": 0.18},
                        {"text": "得", "start": 0.2, "end": 0.5},
                        {"text": "你", "start": 0.8, "end": 0.98},
                    ],
                }
            ],
            "summary": {
                "status": "completed",
                "reusedSegmentCount": int(len(alignment_calls) > 1),
            },
        }

    forced_boundary_calls: list[tuple[str, str]] = []
    original_forced_boundary = app_module.forced_alignment_transition_boundary

    def count_forced_boundary(
        left: dict[str, object],
        right: dict[str, object],
        *args,
        **kwargs,
    ):
        forced_boundary_calls.append((str(left["text"]), str(right["text"])))
        return original_forced_boundary(left, right, *args, **kwargs)

    monkeypatch.setattr(
        app_module,
        "ensure_acoustic_alignment_cache",
        cached_alignment,
    )
    monkeypatch.setattr(
        app_module,
        "forced_alignment_transition_boundary",
        count_forced_boundary,
    )
    monkeypatch.setattr(
        app_module,
        "decode_cut_audio_samples",
        lambda _path: array("h", [4_000]) * app_module.CUT_BOUNDARY_SAMPLE_RATE,
    )
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 1.0,
            "result": {"segments": segments},
            "cutDraft": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    payload = {
        "revision": 0,
        "textRanges": [
            {
                "key": "delete-jue-de",
                "start": 0.0,
                "end": 0.4,
                "originalStart": 0.0,
                "originalEnd": 0.4,
            }
        ],
        "noSpeechRanges": [],
        "timelineRanges": [
            {
                "key": "manual-speech",
                "start": 0.0,
                "end": 0.42,
            },
            {
                "key": "manual-quiet",
                "start": 0.56,
                "end": 0.7,
            },
        ],
    }
    with TestClient(app_module.app) as client:
        first = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json=payload,
        )
        first_draft = first.json()["cutDraft"]
        restored = client.get(f"/api/transcriptions/{job_id}/cut-draft")
        second = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={
                **payload,
                "revision": first_draft["revision"],
                "textRanges": first_draft["textRanges"],
                "timelineRanges": first_draft["timelineRanges"],
            },
        )

    assert first.status_code == 200
    assert first_draft["textRanges"][0]["end"] == 0.5
    assert first_draft["textRanges"][0]["originalEnd"] == 0.4
    assert first_draft["timelineRanges"] == [
        {
            "key": "manual-speech",
            "start": 0.0,
            "end": 0.5,
            "originalStart": 0.0,
            "originalEnd": 0.42,
        },
        {
            "key": "manual-quiet",
            "start": 0.56,
            "end": 0.7,
            "originalStart": 0.56,
            "originalEnd": 0.7,
        },
    ]
    assert restored.json()["cutDraft"] == first_draft
    assert any(
        diagnostic["entryType"] == "text"
        and diagnostic["final"] == 0.5
        and diagnostic["retainedSpeechHardLimit"] == 0.8
        for diagnostic in first_draft["boundaryDiagnostics"]
    )
    assert any(
        diagnostic["entryType"] == "timeline"
        and diagnostic["rangeKey"] == "manual-quiet"
        and diagnostic["fallbackReason"] == "non_speech_range_exact"
        for diagnostic in first_draft["boundaryDiagnostics"]
    )
    assert first_draft["acousticAlignment"]["reusedSegmentCount"] == 0
    assert second.status_code == 200
    second_draft = second.json()["cutDraft"]
    assert second_draft["textRanges"] == first_draft["textRanges"]
    assert second_draft["timelineRanges"] == first_draft["timelineRanges"]
    assert second_draft["acousticAlignment"]["reusedSegmentCount"] == 1
    assert alignment_calls == [video_path, video_path]
    assert forced_boundary_calls == [("得", "你"), ("得", "你")]


def test_cut_draft_put_uses_natural_character_boundaries_not_raw_asr_tokens():
    job_id = "37373737-3737-4737-8737-373737373737"
    (app_module.jobs_directory() / job_id).mkdir(parents=True)
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 1.2,
            "text": "一起给一起给",
            "words": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给", "start": 0.4, "end": 0.6},
                {"text": "一起", "start": 0.6, "end": 1.0},
                {"text": "给", "start": 1.0, "end": 1.2},
            ],
            "asrWords": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给一", "start": 0.4, "end": 0.8},
                {"text": "起给", "start": 0.8, "end": 1.2},
            ],
        },
        {
            "id": 1,
            "start": 1.4,
            "end": 2.0,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 1.4, "end": 1.8},
                {"text": "你", "start": 1.8, "end": 2.0},
            ],
            "asrWords": [
                {"text": "觉", "start": 1.4, "end": 1.6},
                {"text": "得你", "start": 1.6, "end": 2.0},
            ],
        },
    ]
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "status": "completed",
            "duration": 3.0,
            "result": {"segments": segments},
            "cutDraft": None,
        }

    with TestClient(app_module.app) as client:
        response = client.put(
            f"/api/transcriptions/{job_id}/cut-draft",
            json={
                "revision": 0,
                "textRanges": [
                    {
                        "key": "forged-partial-word",
                        "start": 0.01,
                        "end": 0.59,
                        "originalStart": 0.01,
                        "originalEnd": 0.59,
                    },
                    {
                        "key": "forged-de-ni-partial",
                        "start": 1.41,
                        "end": 1.79,
                        "originalStart": 1.41,
                        "originalEnd": 1.79,
                    },
                ],
                "noSpeechRanges": [],
                "timelineRanges": [{"start": 2.05, "end": 2.1}],
            },
        )

    assert response.status_code == 200
    draft = response.json()["cutDraft"]
    assert draft["textRanges"][0]["start"] == 0.0
    assert draft["textRanges"][0]["end"] == 0.6
    assert draft["textRanges"][0]["originalStart"] == 0.0
    assert draft["textRanges"][0]["originalEnd"] == 0.6
    assert draft["textRanges"][1]["start"] == 1.4
    assert draft["textRanges"][1]["end"] == 1.8
    assert draft["textRanges"][1]["originalStart"] == 1.4
    assert draft["textRanges"][1]["originalEnd"] == 1.8
    assert draft["timelineRanges"] == [
        {
            "start": 2.05,
            "end": 2.1,
            "originalStart": 2.05,
            "originalEnd": 2.1,
        }
    ]

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
    assert media_ranges == [
        {"start": 0.0, "end": 0.6},
        {"start": 1.4, "end": 1.8},
        {"start": 2.05, "end": 2.1},
    ]
    assert transcript_ranges == media_ranges


def test_text_ranges_use_character_units_but_manual_timeline_ranges_stay_exact():
    segments = [
        {
            "start": 0.0,
            "end": 2.0,
            "text": "多字词保留",
            "words": [
                {"text": "多", "start": 0.0, "end": 0.25},
                {"text": "字词", "start": 0.25, "end": 1.0},
                {"text": "保留", "start": 1.2, "end": 2.0},
            ],
            "asrWords": [
                {"text": "多字词", "start": 0.0, "end": 1.0},
                {"text": "保留", "start": 1.2, "end": 2.0},
            ],
        }
    ]

    assert app_module.canonicalize_transcript_semantic_ranges(
        [{"start": 0.3, "end": 0.4}],
        segments,
        3.0,
    ) == [{"start": 0.25, "end": 0.625}]
    assert app_module.resolve_cut_draft_delete_ranges(
        {
            "textRanges": [],
            "noSpeechRanges": [],
            "timelineRanges": [{"start": 0.25, "end": 0.5}],
        },
        [],
        segments,
        3.0,
    ) == [{"start": 0.25, "end": 0.5}]

    legacy_segments = [{**segments[0], "asrWords": None}]
    assert app_module.canonicalize_transcript_semantic_ranges(
        [{"start": 0.3, "end": 0.4}],
        legacy_segments,
        3.0,
    ) == [{"start": 0.25, "end": 0.625}]


def test_character_units_fall_back_per_segment_in_mixed_transcript():
    segments = [
        {
            "start": 0.0,
            "end": 0.8,
            "text": "原始词",
            "words": [
                {"text": "原", "start": 0.0, "end": 0.4},
                {"text": "始词", "start": 0.4, "end": 0.8},
            ],
            "asrWords": [{"text": "原始词", "start": 0.0, "end": 0.8}],
        },
        {
            "start": 1.0,
            "end": 1.8,
            "text": "旧段一",
            "words": [{"text": "旧段一", "start": 1.0, "end": 1.8}],
        },
        {
            "start": 2.0,
            "end": 2.8,
            "text": "旧段二",
            "words": [{"text": "旧段二", "start": 2.0, "end": 2.8}],
            "asrWords": [],
        },
        {
            "start": 3.0,
            "end": 3.8,
            "text": "整段回退",
            "words": [],
            "asrWords": [{"text": "无效", "start": 3.0, "end": 3.0}],
        },
    ]

    character_units = app_module.transcript_character_units(segments)

    assert [item["text"] for item in character_units] == [
        "原",
        "始",
        "词",
        "旧",
        "段",
        "一",
        "旧",
        "段",
        "二",
        "整",
        "段",
        "回",
        "退",
    ]
    assert app_module.collect_speech_intervals(segments, 4.0) == [
        (0.0, 0.8),
        (1.0, 1.8),
        (2.0, 2.8),
        (3.0, 3.8),
    ]
    assert app_module.protect_recognized_speech_from_quiet_ranges(
        [{"start": 1.0, "end": 1.8}, {"start": 2.0, "end": 2.8}],
        segments,
    ) == []
    assert app_module.canonicalize_transcript_semantic_ranges(
        [{"start": 1.05, "end": 1.1}, {"start": 2.05, "end": 2.1}],
        segments,
        4.0,
    ) == [{"start": 1.0, "end": 1.267}, {"start": 2.0, "end": 2.267}]


def test_semantic_range_ignores_overlapping_raw_asr_token():
    segments = [
        {
            "start": 0.0,
            "end": 0.5,
            "text": "为",
            "words": [{"text": "为", "start": 0.0, "end": 0.5}],
            "asrWords": [],
        },
        {
            "start": 0.5,
            "end": 1.0,
            "text": "啥",
            "words": [{"text": "啥", "start": 0.5, "end": 1.0}],
            "asrWords": [{"text": "为啥", "start": 0.0, "end": 1.0}],
        },
    ]

    assert app_module.canonicalize_transcript_semantic_ranges(
        [{"start": 0.1, "end": 0.2}],
        segments,
        1.0,
    ) == [{"start": 0.0, "end": 0.5}]


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
            "edit": {
                "status": "completed",
                "ranges": [{"start": 0.4, "end": 0.8}],
                "transcriptRanges": [{"start": 0.4, "end": 0.8}],
                "outputDuration": 1.0,
                "transcript": {"text": "旧的剪后文案"},
            },
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
    expected_edit_transcript = app_module.build_retained_transcript(
        job["result"]["segments"],
        job["edit"]["transcriptRanges"],
        job["edit"]["outputDuration"],
        timeline_delete_ranges=job["edit"]["ranges"],
    )
    assert job["edit"]["transcript"] == expected_edit_transcript
    assert job["edit"]["transcript"]["text"] != "旧的剪后文案"


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
                {"text": "保留", "start": 0.0, "end": 0.8},
                {"text": "删除", "start": 1.0, "end": 2.0},
                {"text": "保留", "start": 2.2, "end": 3.0},
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


def test_retained_transcript_does_not_drop_next_natural_word_character():
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.0,
            "text": "一起给一起给",
            "words": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给", "start": 0.4, "end": 0.6},
                {"text": "一起", "start": 0.6, "end": 1.0},
                {"text": "给", "start": 1.0, "end": 1.2},
            ],
            "asrWords": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给一", "start": 0.4, "end": 0.8},
                {"text": "起给", "start": 0.8, "end": 1.2},
            ],
        }
    ]

    retained = app_module.build_retained_transcript(
        segments,
        [{"start": 0.0, "end": 0.6}],
        1.4,
        timeline_delete_ranges=[{"start": 0.0, "end": 0.6}],
    )

    assert retained["text"] == "一起给"
    assert retained["segments"][0]["asrWords"] == [
        {
            "text": "一",
            "start": 0.0,
            "end": 0.2,
            "sourceStart": 0.6,
            "sourceEnd": 0.8,
        },
        {
            "text": "起给",
            "start": 0.2,
            "end": 0.6,
            "sourceStart": 0.8,
            "sourceEnd": 1.2,
        },
    ]

    de_ni_segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 0.6,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "觉", "start": 0.0, "end": 0.2},
                {"text": "得你", "start": 0.2, "end": 0.6},
            ],
        }
    ]
    retained_de_ni = app_module.build_retained_transcript(
        de_ni_segments,
        [{"start": 0.0, "end": 0.4}],
        0.2,
        timeline_delete_ranges=[{"start": 0.0, "end": 0.4}],
    )

    assert retained_de_ni["text"] == "你"
    assert retained_de_ni["segments"][0]["words"] == [
        {
            "text": "你",
            "start": 0.0,
            "end": 0.2,
            "sourceStart": 0.4,
            "sourceEnd": 0.6,
        }
    ]
    assert retained_de_ni["segments"][0]["asrWords"] == [
        {
            "text": "你",
            "start": 0.0,
            "end": 0.2,
            "sourceStart": 0.4,
            "sourceEnd": 0.6,
        }
    ]


def test_retained_transcript_keeps_semantic_text_when_coarse_time_is_in_media_cut():
    segments = [
        {
            "start": 27.0,
            "end": 31.0,
            "text": "所有人一起给一起给你画",
            "words": [
                {"text": "所有人", "start": 27.0, "end": 28.454},
                {"text": "一起给", "start": 28.454, "end": 29.171},
                {"text": "一起", "start": 29.171, "end": 29.649},
                {"text": "给你画", "start": 29.649, "end": 31.0},
            ],
        }
    ]
    semantic_ranges = [{"start": 28.454, "end": 29.171}]
    media_ranges = [{"start": 28.299, "end": 29.807}]

    retained = app_module.build_retained_transcript(
        segments,
        semantic_ranges,
        29.492,
        timeline_delete_ranges=media_ranges,
    )

    assert retained["text"] == "所有人一起给你画"
    assert "".join(
        word["text"] for word in retained["segments"][0]["words"]
    ) == "所有人一起给你画"
    assert all(
        math.isfinite(word[boundary])
        for word in retained["segments"][0]["words"]
        for boundary in ("start", "end")
    )
    assert all(
        word["end"] > word["start"]
        for word in retained["segments"][0]["words"]
    )


def test_retained_transcript_uses_valid_forced_timing_and_rejects_bad_order():
    text = "你身边你身边人人都觉得你身边人人都觉得"
    segments = [
        {
            "start": 33.16,
            "end": 42.5,
            "text": text,
            "words": [
                {"text": "你身边你身边人人都觉得", "start": 33.16, "end": 37.12},
                {"text": "你", "start": 37.12, "end": 37.48},
                {"text": "身边人人都觉得", "start": 37.48, "end": 42.5},
            ],
        }
    ]
    forced_characters = []
    for index, character in enumerate(text):
        if index < 10:
            start = 33.2 + index * 0.44
        elif index == 10:
            start = 37.65
        elif index == 11:
            start = 39.85
        else:
            start = 40.05 + (index - 12) * 0.28
        forced_characters.append(
            {"text": character, "start": round(start, 3), "end": round(start + 0.18, 3)}
        )
    alignment_cache = {
        "segments": [
            {
                "segmentIndex": 0,
                "validation": {"valid": True},
                "characters": forced_characters,
            }
        ]
    }
    semantic_ranges = [{"start": 33.16, "end": 37.12}]
    media_ranges = [{"start": 32.73, "end": 37.79}]

    retained = app_module.build_retained_transcript(
        segments,
        semantic_ranges,
        37.44,
        timeline_delete_ranges=media_ranges,
        alignment_cache=alignment_cache,
    )
    assert retained["text"].startswith("你身边人人都觉得")
    assert retained["segments"][0]["sourceStart"] == pytest.approx(39.85)
    assert retained["segments"][0]["start"] == pytest.approx(34.79)
    assert retained["segments"][0]["words"][0]["sourceStart"] == pytest.approx(
        39.85
    )
    assert retained["segments"][0]["words"][0]["sourceEnd"] == pytest.approx(
        40.03
    )

    malformed = copy.deepcopy(alignment_cache)
    malformed["segments"][0]["characters"][12]["start"] = 35.0
    fallback = app_module.build_retained_transcript(
        segments,
        semantic_ranges,
        37.44,
        timeline_delete_ranges=media_ranges,
        alignment_cache=malformed,
    )
    assert fallback["text"].startswith("你身边人人都觉得")
    assert fallback["segments"][0]["sourceStart"] == pytest.approx(37.12)

    non_monotonic_end = copy.deepcopy(alignment_cache)
    non_monotonic_end["segments"][0]["characters"][11]["end"] = 40.5
    rejected_end = app_module.build_retained_transcript(
        segments,
        semantic_ranges,
        37.44,
        timeline_delete_ranges=media_ranges,
        alignment_cache=non_monotonic_end,
    )
    assert rejected_end["segments"][0]["sourceStart"] == pytest.approx(37.12)

    outside_envelope = copy.deepcopy(alignment_cache)
    outside_envelope["segments"][0]["characters"][-1]["end"] = 43.0
    rejected_envelope = app_module.build_retained_transcript(
        segments,
        semantic_ranges,
        37.44,
        timeline_delete_ranges=media_ranges,
        alignment_cache=outside_envelope,
    )
    assert rejected_envelope["segments"][0]["sourceStart"] == pytest.approx(
        37.12
    )


def test_retained_transcript_distributes_multiple_collapsed_tail_characters():
    retained = app_module.build_retained_transcript(
        [
            {
                "start": 0.0,
                "end": 10.0,
                "text": "前删一起",
                "words": [
                    {"text": "前", "start": 0.0, "end": 1.0},
                    {"text": "删", "start": 8.0, "end": 9.0},
                    {"text": "一", "start": 9.0, "end": 9.5},
                    {"text": "起", "start": 9.5, "end": 10.0},
                ],
            }
        ],
        [{"start": 8.0, "end": 9.0}],
        8.0,
        timeline_delete_ranges=[{"start": 8.0, "end": 10.0}],
    )

    assert retained["text"] == "前一起"
    tail_words = retained["segments"][0]["words"][-2:]
    assert [word["text"] for word in tail_words] == ["一", "起"]
    assert all(word["end"] > word["start"] for word in tail_words)
    assert tail_words[0]["end"] <= tail_words[1]["start"]
    assert tail_words[1]["end"] <= retained["duration"]


def test_retained_transcript_honors_explicit_empty_physical_ranges():
    retained = app_module.build_retained_transcript(
        [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "甲乙",
                "words": [
                    {"text": "甲", "start": 0.0, "end": 0.5},
                    {"text": "乙", "start": 0.5, "end": 1.0},
                ],
            }
        ],
        [{"start": 0.0, "end": 0.5}],
        1.0,
        timeline_delete_ranges=[],
    )

    assert retained["text"] == "乙"
    assert retained["segments"][0]["start"] == pytest.approx(0.5)


def test_completed_edit_preserves_explicit_empty_semantic_ranges():
    retained = app_module.build_existing_edit_retained_transcript(
        [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "甲乙",
                "words": [
                    {"text": "甲", "start": 0.0, "end": 0.5},
                    {"text": "乙", "start": 0.5, "end": 1.0},
                ],
            }
        ],
        {
            "status": "completed",
            "ranges": [{"start": 0.0, "end": 0.5}],
            "requestedRanges": [{"start": 0.0, "end": 0.5}],
            "transcriptRanges": [],
            "outputDuration": 0.5,
        },
        [],
        None,
    )

    assert retained is not None
    assert retained["text"] == "甲乙"


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


def test_quiet_ranges_partially_or_fully_covering_text_never_delete_it():
    segments = [
        {
            "start": 1.0,
            "end": 2.0,
            "text": "保留文案",
            "words": [{"text": "保留文案", "start": 1.0, "end": 2.0}],
        }
    ]

    protected = app_module.protect_recognized_speech_from_quiet_ranges(
        [
            {"start": 0.5, "end": 2.5},
            {"start": 1.1, "end": 1.9},
        ],
        segments,
    )

    assert protected == [
        {"start": 0.5, "end": 1.0},
        {"start": 2.0, "end": 2.5},
    ]


def test_automatic_ranges_do_not_merge_across_a_short_retained_word():
    segments = [
        {
            "start": 0.0,
            "end": 2.0,
            "text": "保留删除短删除保留",
            "words": [
                {"text": "保留", "start": 0.0, "end": 0.4},
                {"text": "删除", "start": 0.4, "end": 0.9},
                {"text": "短", "start": 0.95, "end": 1.03},
                {"text": "删除", "start": 1.08, "end": 1.5},
                {"text": "保留", "start": 1.5, "end": 2.0},
            ],
        }
    ]
    draft = {
        "textRanges": [
            {
                "start": 0.4,
                "end": 0.95,
                "originalStart": 0.4,
                "originalEnd": 0.9,
            },
            {
                "start": 1.03,
                "end": 1.5,
                "originalStart": 1.08,
                "originalEnd": 1.5,
            },
        ],
        "noSpeechRanges": [],
        "timelineRanges": [],
    }

    resolved = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        segments,
        2.0,
    )

    assert resolved == [
        {"start": 0.4, "end": 0.95},
        {"start": 1.03, "end": 1.5},
    ]
    draft["timelineRanges"] = [{"start": 0.95, "end": 1.03}]
    explicitly_deleted = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        segments,
        2.0,
    )
    assert explicitly_deleted == [{"start": 0.4, "end": 1.5}]


def test_partial_manual_word_delete_does_not_expand_adjacent_automatic_cuts():
    segments = [
        {
            "start": 0.8,
            "end": 1.28,
            "text": "删除短词删除",
            "words": [
                {"text": "删除", "start": 0.8, "end": 1.0},
                {"text": "短词", "start": 1.0, "end": 1.08},
                {"text": "删除", "start": 1.08, "end": 1.28},
            ],
        }
    ]
    draft = {
        "textRanges": [
            {
                "start": 0.8,
                "end": 1.0,
                "originalStart": 0.8,
                "originalEnd": 1.0,
            },
            {
                "start": 1.08,
                "end": 1.28,
                "originalStart": 1.08,
                "originalEnd": 1.28,
            },
        ],
        "noSpeechRanges": [],
        "timelineRanges": [{"start": 1.0, "end": 1.04}],
    }

    resolved = app_module.resolve_cut_draft_delete_ranges(
        draft,
        [],
        segments,
        2.0,
    )

    assert resolved == [
        {"start": 0.8, "end": 1.04},
        {"start": 1.08, "end": 1.28},
    ]
    retained = app_module.build_retained_transcript(
        segments,
        resolved,
        1.56,
        timeline_delete_ranges=resolved,
    )
    assert retained["text"] == "词"


def test_cut_draft_alignment_without_asr_words_falls_back_to_semantic_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    sample_rate = app_module.CUT_BOUNDARY_SAMPLE_RATE
    samples = array("h", [6_000]) * (sample_rate * 5)
    for valley in (1.6, 3.5):
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
            "start": 0.5,
            "end": 4.0,
            "text": "前文删除后文",
            "words": [
                {"text": "前文", "start": 0.5, "end": 1.8},
                {"text": "删除", "start": 2.0, "end": 3.0},
                {"text": "后文", "start": 3.1, "end": 4.0},
            ],
        }
    ]

    aligned = app_module.align_cut_draft_text_ranges_to_audio(
        media_path,
        [
            {
                "key": "2.000-3.000",
                "start": 1.4,
                "end": 3.8,
                "originalStart": 2.0,
                "originalEnd": 3.0,
            }
        ],
        segments,
        5.0,
    )[0]

    assert aligned["start"] == 2.0
    assert aligned["end"] == 3.0
    assert aligned["originalStart"] == 2.0
    assert aligned["originalEnd"] == 3.0
