from __future__ import annotations

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
    monkeypatch.setattr(app_module, "DATA_DIR", tmp_path)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ASR_API_KEY", raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    with app_module.JOBS_LOCK:
        app_module.JOBS.clear()
        app_module.JOB_FILES.clear()
    yield


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
        app_module.JOBS[active_id] = {"id": active_id}
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


def test_frontend_assets_are_versioned_and_not_cached():
    with TestClient(app_module.app) as client:
        page_response = client.get("/")
        styles_response = client.get("/styles.css")
        script_response = client.get("/app.js")
        feedback_script_response = client.get("/ui-feedback.js")
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
    assert "/app.js?v=20260730-03" in page_response.text
    assert "/styles.css?v=20260730-08" in page_response.text
    assert "/ui-feedback.js?v=20260729-03" in page_response.text
    assert feedback_script_response.status_code == 200
    assert 'className = "app-dialog-shell"' in feedback_script_response.text
    assert "window.appConfirm" in feedback_script_response.text
    assert "window.confirm" not in script_response.text
    assert 'id="cutOperationLock"' in page_response.text
    assert "setCutOperationLock" in script_response.text
    assert ".cut-operation-lock" in styles_response.text
    assert 'setAttribute("inert", "")' in script_response.text
    assert 'id="ambientCanvas"' in page_response.text
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
    assert 'id="selectAllSuggestionsButton"' in page_response.text
    assert 'id="selectAllNoSpeechButton"' in page_response.text
    assert 'id="noSpeechState"' in page_response.text
    assert 'id="noSpeechList"' in page_response.text
    assert 'id="directToolsPrompt"' in page_response.text
    assert 'id="continuePipButton"' in page_response.text
    assert 'selectAllSuggestionsButton.addEventListener("click"' in script_response.text
    assert "currentSuggestions.every" in script_response.text
    assert "一键标记删除" in page_response.text
    assert "一键标记删除" in script_response.text
    assert "取消全部标记" in script_response.text
    assert "renderNoSpeechSuggestions" in script_response.text
    assert "selectedNoSpeechRanges" in script_response.text
    assert "一键标记可删片段" in page_response.text
    assert "一键标记可删片段" in script_response.text
    assert "previewNoSpeechSuggestion" in script_response.text
    assert "setOriginalSourceActionsAllowed(!job.edit?.status);" in script_response.text
    assert "setOriginalSourceActionsAllowed(false);" in script_response.text
    assert "continuePipButton.href" in script_response.text
    assert "source=edited" in script_response.text
    assert 'id="restartProjectButton"' in page_response.text
    assert 'id="cutPreviewVideo"' in page_response.text
    assert 'id="cutFrameTimeline"' in page_response.text
    assert 'id="cutFrameTimelineTrack"' in page_response.text
    assert 'id="cutFrameTimelineThumbnails"' in page_response.text
    assert 'id="cutFrameTimelineRanges"' in page_response.text
    assert 'id="removeTimelineRangeButton"' in page_response.text
    assert 'id="textEditorPreviewPane"' in page_response.text
    assert 'id="transcriptSegmentList"' in page_response.text
    assert 'id="transcriptEditStatus"' in page_response.text
    assert "saveTranscriptText" in script_response.text
    assert 'method: "PUT"' in script_response.text
    assert "/transcript`" in script_response.text
    assert 'class="text-editor-tabbar"' in page_response.text
    assert 'data-text-editor-tab="cuts"' in page_response.text
    assert 'data-text-editor-panel="cuts"' in page_response.text
    assert 'data-text-editor-tab="silence"' in page_response.text
    assert 'data-text-editor-panel="silence"' in page_response.text
    assert 'aria-controls="textSilencePanel"' in page_response.text
    output_panel_start = page_response.text.index('id="textOutputPanel"')
    output_panel_end = page_response.text.index('id="textTranscriptPanel"')
    output_panel_markup = page_response.text[output_panel_start:output_panel_end]
    assert page_response.text.count('id="generateCutButton"') == 1
    assert 'id="generateCutButton"' in output_panel_markup
    assert 'id="outputCutSummary"' in output_panel_markup
    assert 'id="outputCutSelectionDetail"' in output_panel_markup
    assert 'id="generateNoSpeechCutButton"' not in page_response.text
    assert "generateNoSpeechCutButton" not in script_response.text
    assert 'generateCutButton.addEventListener("click", generateCut)' in script_response.text
    assert "updateOriginalSourceActionsVisibility" in script_response.text
    assert "source=original" in script_response.text
    assert "picture-in-picture?job=" in script_response.text
    assert "/original-video`" in script_response.text
    assert "buildCutTimelineThumbnails" in script_response.text
    assert "beginCutTimelineSelection" in script_response.text
    assert "beginTimelineRangeAdjustment" in script_response.text
    assert "timelineDeleteRanges" in script_response.text
    assert "...timelineDeleteRanges" in script_response.text
    assert "CUT_TIMELINE_MIN_RANGE" in script_response.text
    assert "activateTextEditorPanel" in script_response.text
    assert "splitTextIntoCharacterTokens" in script_response.text
    assert "formatPreciseTime" in script_response.text
    assert "文字列表仅支持整段选择" in page_response.text
    assert "请选择整段，或在时间轴上拖出删除区间" in page_response.text
    assert 'segmentText.className = "segment-text"' in script_response.text
    assert (
        'segmentText.className = "segment-text transcript-segment-text"'
        in script_response.text
    )
    assert 'words.className = "word-list transcript-word-list"' not in script_response.text
    assert 'characters.className = "word-list"' not in script_response.text
    assert 'event.target.closest(".word-chip")' not in script_response.text
    assert "`${selectedSegmentCount} 段文字`" in script_response.text
    assert "previous.end + 0.12" in script_response.text
    assert r"/\p{P}|\s/u" in script_response.text
    assert 'toDataURL("image/jpeg"' in script_response.text
    assert page_response.headers["cache-control"] == "no-store, max-age=0"
    assert script_response.headers["cache-control"] == "no-store, max-age=0"
    assert "--editor-timeline-track-height: 112px" in styles_response.text
    assert "--editor-timeline-ruler-height: 28px" in styles_response.text
    assert "transform: rotate(0.55deg)" not in styles_response.text
    assert "margin-left: 13px" not in styles_response.text
    assert "margin-left: 9px" not in styles_response.text
    assert "grid-template-columns: 38px minmax(0, 1fr)" in styles_response.text
    assert ".suggestion-card-footer {" in styles_response.text
    assert ".no-speech-panel {" in styles_response.text
    assert ".no-speech-selection-footer {" in styles_response.text
    assert ".output-cut-builder {" in styles_response.text
    assert ".cut-timeline-no-speech-range {" in styles_response.text
    assert "grid-template-columns: minmax(0, 1fr) auto" in styles_response.text
    assert styles_response.text.count("height: var(--editor-timeline-track-height)") == 3
    assert "#cutPreviewPlayer:fullscreen .cut-frame-timeline" in styles_response.text
    assert "display: none !important" in styles_response.text
    assert "height: min(72dvh, 840px, calc(100dvh - 112px))" in styles_response.text
    assert art_page_response.status_code == 200
    assert "/art-text.js?v=20260730-09" in art_page_response.text
    assert 'class="cut-progress art-generation-progress full-row"' in art_page_response.text
    assert "art-particle art-particle-1" in art_page_response.text
    assert "解析时间轴" in art_page_response.text
    assert ".art-generation-progress" in styles_response.text
    assert "@keyframes art-particle-float" in styles_response.text
    assert "@keyframes art-panel-scan" in styles_response.text
    assert "/styles.css?v=20260730-08" in art_page_response.text
    assert "/ui-feedback.js?v=20260729-03" in art_page_response.text
    assert "AI 分句生成艺术字字幕" in art_page_response.text
    assert "每行最多 10 字生成统一字号字幕" in art_script_response.text
    assert "TRANSCRIPT_TRACK_MAX_CHARS_PER_CUE = 10" in art_script_response.text
    assert "正在按每行最多 10 字重新整理全文轨道" in art_script_response.text
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
    assert 'data-workbench-panel="output"' in art_page_response.text
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
    assert 'id="artHistoryName"' in art_page_response.text
    assert 'historyName: artHistoryName.value.trim() || null' in art_script_response.text
    assert 'id="cutHistoryName"' in page_response.text
    assert 'historyName: cutHistoryName.value.trim() || null' in script_response.text
    assert 'id="artTimeFitMessage"' in art_page_response.text
    assert 'id="frameTimeline"' in art_page_response.text
    assert 'id="frameTimelineSeek"' in art_page_response.text
    assert 'id="frameTimelineRuler"' in art_page_response.text
    assert 'id="frameTimelineJumpInput"' in art_page_response.text
    assert 'id="frameTimelineJumpButton"' in art_page_response.text
    assert 'id="frameTimelineThumbnails"' in art_page_response.text
    assert 'id="frameTimelineSegments"' in art_page_response.text
    assert 'aria-label="艺术字时间轴"' in art_page_response.text
    assert 'id="continuePictureInPicture"' in art_page_response.text
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
    assert "element.hidden = !isVisible;" in art_script_response.text
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
    assert "setupExternalVideoControls" in art_script_response.text
    assert "requestFullscreen" in art_script_response.text
    assert "buildFrameTimelineThumbnails" in art_script_response.text
    assert "renderFrameTimelineRuler" in art_script_response.text
    assert "parseFrameTimelineTimeInput" in art_script_response.text
    assert "jumpToFrameTimelineTime" in art_script_response.text
    assert "refreshFrameTimeline" in art_script_response.text
    assert "renderFrameTimelineOverlaySegments" in art_script_response.text
    assert "beginFrameTimelineScrub" in art_script_response.text
    assert "toDataURL(\"image/jpeg\"" in art_script_response.text
    assert "const edgeOffset = Math.min(0.04, total / 2)" in art_script_response.text
    assert 'videoSource === "original" && payload.edit?.status' in art_script_response.text
    assert art_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert art_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert pip_page_response.status_code == 200
    assert "/picture-in-picture.js?v=20260730-01" in pip_page_response.text
    assert "/ui-feedback.js?v=20260729-03" in pip_page_response.text
    assert 'name="assetType" value="video"' in pip_page_response.text
    assert "Seedance 动态镜头" in pip_page_response.text
    assert 'class="pip-editor-body"' in pip_page_response.text
    assert 'id="segmentList"' in pip_page_response.text
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
    assert 'id="imageProgress" class="pip-inline-progress pip-tech-progress"' in pip_page_response.text
    assert "pip-tech-particle pip-tech-particle-5" in pip_page_response.text
    assert 'id="generatedList"' in pip_page_response.text
    assert 'id="pipOverlayLayer"' in pip_page_response.text
    assert 'id="pipTimelineThumbnails"' in pip_page_response.text
    assert 'id="generatePipVideo"' in pip_page_response.text
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
    assert "/picture-in-picture`" in pip_script_response.text
    assert "AI 根据文字智能生成" in pip_script_response.text
    assert "aspectRatio: currentImageAspectRatio()" in pip_script_response.text
    assert '"original", "edited", "art"' in pip_script_response.text
    assert "source: requestedSource" in pip_script_response.text
    assert "renderPreview" in pip_script_response.text
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
    assert pip_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert pip_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert template_page_response.status_code == 200
    assert "/art-template-library.js?v=" in template_page_response.text
    assert 'id="templateCardGrid"' in template_page_response.text
    assert 'id="useTemplateButton"' in template_page_response.text
    assert 'id="openTemplateUpload"' in template_page_response.text
    assert 'id="templateUploadDialog"' in template_page_response.text
    assert 'id="renameTemplateButton"' in template_page_response.text
    assert 'id="deleteTemplateButton"' in template_page_response.text
    assert "艺术字效果模板库" in template_page_response.text
    assert "/api/art-templates" in template_script_response.text
    assert "preferredArtTemplateSettings" in template_script_response.text
    assert 'method: "PATCH"' in template_script_response.text
    assert 'method: "DELETE"' in template_script_response.text
    assert "loadArtTemplateLibrary" in art_script_response.text
    assert "ART_STYLE_BASES" in art_script_response.text
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
    assert "/font-manager.js?v=" in font_page_response.text
    assert 'id="fontUploadForm"' in font_page_response.text
    assert 'id="fontCardGrid"' in font_page_response.text
    assert "/api/fonts" in font_script_response.text
    assert "registerUploadedFont" in font_script_response.text
    assert font_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert font_script_response.headers["cache-control"] == "no-store, max-age=0"


def test_art_template_library_upload_rename_render_and_delete(tmp_path: Path):
    template_payload = {
        "name": "我的蓝色立体字",
        "sample": "蓝色",
        "description": "蓝色主色与深蓝描边的立体艺术字。",
        "baseStyle": "impact",
        "color": "#59C7FF",
        "strokeColor": "#102A43",
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
                    artStyle=uploaded["id"],
                )
            ],
            1,
        )
        assert normalized[0]["artStyle"] == uploaded["id"]
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


def test_media_cut_boundaries_do_not_cross_retained_word_edges():
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
        1.5,
        timeline_delete_ranges=media_ranges,
    )

    assert boundary_limits == [{"start": 0.5, "end": 1.0}]
    assert media_ranges == requested_ranges
    assert retained["text"] == "保留保留"
    assert all(
        word["end"] > word["start"]
        for word in retained["segments"][0]["words"]
    )


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
        lambda media_path, ranges, duration, boundary_limits: [
            {"start": 0.225, "end": 0.61}
        ],
    )

    with TestClient(app_module.app) as client, sample_video.open("rb") as handle:
        upload_response = client.post(
            "/api/transcriptions",
            files={"file": (sample_video.name, handle, "video/mp4")},
        )
        job_id = upload_response.json()["id"]

        cut_response = client.post(
            f"/api/transcriptions/{job_id}/cuts",
            json={
                "ranges": [{"start": 0.25, "end": 0.55}],
                "historyName": "第一版剪辑",
            },
        )
        job_response = client.get(f"/api/transcriptions/{job_id}")
        video_response = client.get(
            f"/api/transcriptions/{job_id}/edited-video"
        )
        art_response = client.post(
            f"/api/transcriptions/{job_id}/art-text",
            json={
                "historyName": "客户艺术字版",
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
        history_response = client.get("/api/history")

    assert cut_response.status_code == 202
    edit = job_response.json()["edit"]
    assert edit["status"] == "completed"
    assert edit["ranges"] == [{"start": 0.225, "end": 0.61}]
    assert edit["requestedRanges"] == [{"start": 0.25, "end": 0.55}]
    assert edit["outputDuration"] == 0.615
    assert edit["transcript"]["text"] == "保留保留"
    assert edit["transcript"]["segments"][0]["words"][1] == {
        "text": "保留",
        "start": 0.225,
        "end": 0.615,
    }
    assert video_response.status_code == 200
    assert video_response.headers["content-type"] == "video/mp4"
    output_path = app_module.DATA_DIR / "jobs" / job_id / "edited.mp4"
    assert output_path.is_file()
    assert 0.45 < app_module.probe_video(output_path) < 0.8
    assert art_response.status_code == 202
    art = final_job_response.json()["art"]
    assert art["status"] == "completed"
    assert art["source"] == "edited"
    assert art["overlays"][0]["text"] == "重点"
    assert art["overlays"][0]["direction"] == "vertical"
    assert art["overlays"][0]["textAlign"] == "right"
    assert art["overlays"][0]["artStyle"] == "metal"
    assert art_video_response.status_code == 200
    assert art_video_response.headers["content-type"] == "video/mp4"
    assert history_response.status_code == 200
    assert history_response.json()["count"] == 2
    assert history_response.json()["editedCount"] == 1
    assert history_response.json()["artCount"] == 1
    assert edit["historyId"] != art["historyId"]
    assert edit["historyName"] == "第一版剪辑"
    assert art["historyName"] == "客户艺术字版"
    assert {item["name"] for item in history_response.json()["versions"]} == {
        "第一版剪辑",
        "客户艺术字版",
    }
    art_output_path = app_module.DATA_DIR / "jobs" / job_id / "art-text.mp4"
    art_layer_path = app_module.DATA_DIR / "jobs" / job_id / "art-text-0.png"
    assert art_output_path.is_file()
    assert art_layer_path.is_file()
    assert 0.5 < app_module.probe_video(art_output_path) < 0.9


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
        {"text": "从来", "start": 0.86, "end": 1.12},
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
        "如果你圈子里",
        "从来没有人拿到过结果",
        "那你第一次碰到机会",
        "第一反应肯定",
        "不是冲上去",
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
    assert result["cues"][-1]["end"] == words[-1]["end"]

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
    assert "10 个汉字是硬性上限" in system_prompt
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
            ["人这辈子最难突破的", "从来不是自己的能力"],
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
            ["人这辈子最难突破的", "从来不是自己的能力"],
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
            ["你身边人人都觉得", "一个月赚一万就顶天了"],
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

    assert result["cues"] == [
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

    with pytest.raises(ValueError, match="最多只能显示 10 个字"):
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

    monkeypatch.setattr(app_module.subprocess, "run", fake_run)
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
