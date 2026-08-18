from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


def _fetch_frontend_assets(*paths: str):
    with TestClient(app_module.app) as client:
        return {path: client.get(path) for path in paths}


def test_shared_frontend_assets_are_versioned_and_not_cached():
    responses = _fetch_frontend_assets(
        "/",
        "/styles.css",
        "/app.js",
        "/ui-feedback.js",
        "/timeline-model.js",
        "/art-text.js",
        "/picture-in-picture.js",
    )
    page_response = responses["/"]
    styles_response = responses["/styles.css"]
    script_response = responses["/app.js"]
    feedback_script_response = responses["/ui-feedback.js"]
    timeline_script_response = responses["/timeline-model.js"]
    art_script_response = responses["/art-text.js"]
    pip_script_response = responses["/picture-in-picture.js"]

    assert page_response.status_code == 200
    assert styles_response.status_code == 200
    assert "/app.js?v=20260817-06" in page_response.text
    assert "/styles.css?v=20260814-13" in page_response.text
    assert "/ui-feedback.js?v=20260807-03" in page_response.text
    assert "/timeline-model.js?v=20260810-01" in page_response.text
    assert "/editor-suite.js?v=20260814-02" in page_response.text
    assert timeline_script_response.status_code == 200
    assert timeline_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert "function createStore" in timeline_script_response.text
    assert "function createPointerSession" in timeline_script_response.text
    assert page_response.text.index("/timeline-model.js") < page_response.text.index(
        "/editor-suite.js"
    )

    assert feedback_script_response.status_code == 200
    assert 'className = "app-dialog-shell"' in feedback_script_response.text
    assert "window.appConfirm" in feedback_script_response.text
    assert "window.appGeneration" in feedback_script_response.text
    assert "generation-overlay" in styles_response.text
    assert "window.appGeneration?.show" in art_script_response.text
    assert "window.appGeneration?.show" in script_response.text
    assert "window.appGeneration?.show" in pip_script_response.text
    assert "window.confirm" not in script_response.text

    assert page_response.headers["cache-control"] == "no-store, max-age=0"
    assert script_response.headers["cache-control"] == "no-store, max-age=0"
    assert feedback_script_response.headers["cache-control"] == "no-store, max-age=0"

    assert ".hero" not in styles_response.text
    assert "studio-wave-breathe" not in styles_response.text
    assert ".section-helper" not in styles_response.text
    assert ".next-step-copy" not in styles_response.text
    assert ".output-note" not in styles_response.text
    assert ".template-library-note" not in styles_response.text


def test_editor_suite_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/",
        "/styles.css",
        "/editor-suite.js",
    )
    page_response = responses["/"]
    styles_response = responses["/styles.css"]
    editor_suite_script_response = responses["/editor-suite.js"]

    assert 'class="preview-grid"' in page_response.text
    assert 'data-preview-grid-toggle' in page_response.text
    assert 'data-douyin-preview-toggle' in page_response.text
    assert 'class="cut-preview-mode-controls"' in page_response.text
    assert 'id="editorSuiteDouyinChrome"' in page_response.text
    assert 'class="douyin-status-bar"' not in page_response.text
    assert 'class="douyin-location"' not in page_response.text
    assert 'id="page-title" class="sr-only"' in page_response.text
    assert 'class="hero"' not in page_response.text
    assert "30 FPS" not in page_response.text
    assert "剪辑版与艺术字版分别保存，选择任一版本即可继续处理" not in page_response.text
    assert "汇总文字剪辑、AI 建议、空白剪辑和时间轴" not in page_response.text
    assert "剪辑是可选步骤，你可以直接为原视频添加艺术字或画中画" not in page_response.text
    assert "记录当前视频的剪辑操作" not in page_response.text
    assert "剪辑已完成。你可以基于剪辑视频" not in page_response.text
    assert "原视频仍保留，可重新选择文字生成新版本" not in page_response.text
    assert 'class="progress-live-status"' in page_response.text
    assert 'id="extractStatus">等待处理' in page_response.text
    assert 'id="transcribeStatus">等待处理' in page_response.text
    assert "Paraformer 返回句子和词级时间戳" not in page_response.text
    assert ".progress-live-status {" in styles_response.text
    assert "counter-reset: process-stage;" in styles_response.text
    progress_card_rule = styles_response.text.rsplit(
        "body:not(.has-result) .page-shell:has(#progressCard:not([hidden])) #progressCard {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "min-height: 0;" in progress_card_rule
    assert 'data-editor-suite-nav data-stage="cut"' in page_response.text
    header_start = page_response.text.index('<header class="site-header">')
    editor_suite_start = page_response.text.index('data-editor-suite-nav data-stage="cut"')
    header_actions_start = page_response.text.index('<div class="header-actions">')
    assert header_start < editor_suite_start < header_actions_start
    assert editor_suite_script_response.status_code == 200
    assert "editor-suite:move-finish" in editor_suite_script_response.text
    assert "editor-suite:timeline-action" in editor_suite_script_response.text
    assert "setTimelineTracks" in editor_suite_script_response.text
    assert "job.pictureInPicture?.composition" in editor_suite_script_response.text
    assert "job.art?.composition" in editor_suite_script_response.text
    assert "最终导出会同时保留两种效果" in editor_suite_script_response.text
    assert 'id="editorSuitePreviewOverlay"' in page_response.text
    assert 'id="editorSuiteTimelineLayer"' in page_response.text
    assert 'aria-label="艺术字和画中画叠加片段"' in page_response.text
    assert 'id="editorSuiteInspectorHost"' in page_response.text
    assert 'id="editorSuiteGenerateDock"' not in page_response.text
    assert "data-editor-generate=" not in page_response.text
    assert editor_suite_script_response.text.count("data-editor-suite-generate") == 2
    assert 'data-generation-kind' not in page_response.text
    assert editor_suite_script_response.text.count(
        'class="editor-suite-generate-button"'
    ) == 1
    assert "const generateButtons" not in editor_suite_script_response.text
    assert "const directGenerationSources" not in editor_suite_script_response.text
    assert 'generateButton?.addEventListener("click", generateCurrentPreview)' in (
        editor_suite_script_response.text
    )
    assert 'id="cut-preview-title"' not in page_response.text
    assert 'id="editorSuiteTimelineTitle"' not in page_response.text
    assert 'url.searchParams.set("embedded", "1")' in editor_suite_script_response.text
    assert 'window.history[method]' in editor_suite_script_response.text
    assert 'type: "editor-suite:sync-time"' in editor_suite_script_response.text
    assert 'type: "editor-suite:open-tool"' in editor_suite_script_response.text
    assert 'data.type === "editor-suite:job-state"' in editor_suite_script_response.text
    assert "const cutTabbar" not in editor_suite_script_response.text
    assert "cutTabbar.hidden" not in editor_suite_script_response.text
    assert "cutPanelStack.hidden = !isCut" in editor_suite_script_response.text
    inline_support_start = editor_suite_script_response.text.index(
        "function supportsInlineWorkspace()"
    )
    inline_support_end = editor_suite_script_response.text.index(
        "function currentJobId()", inline_support_start
    )
    inline_support_contract = editor_suite_script_response.text[
        inline_support_start:inline_support_end
    ]
    assert 'stage === "cut"' in inline_support_contract
    assert "cutPanelStack" in inline_support_contract
    assert "cutTabbar" not in inline_support_contract
    assert 'type: "editor-suite:generate-video"' not in editor_suite_script_response.text
    assert 'target: "all"' in editor_suite_script_response.text
    assert '/compose`' in editor_suite_script_response.text
    assert "data-editor-suite-download" in editor_suite_script_response.text
    assert "syncGenerationButton" in editor_suite_script_response.text
    assert "workspaceSourceTime" in editor_suite_script_response.text
    assert 'classList.toggle("has-effect-track", nextState.visible)' in editor_suite_script_response.text
    assert "timelineTrackOffset" in editor_suite_script_response.text
    assert "timelineTrackCount" in editor_suite_script_response.text
    assert 'segment.dataset.timelineTrackIndex' in editor_suite_script_response.text
    assert "select-art-timeline" in editor_suite_script_response.text
    assert "adjust-art-timeline" in editor_suite_script_response.text
    assert 'ensureToolFrame("art", artHref);' in editor_suite_script_response.text
    assert "Math.abs(nextTime - workspaceCurrentTime()) > 0.05" in editor_suite_script_response.text
    assert "Math.abs(childTime - workspaceCurrentTime()) > 0.05" in editor_suite_script_response.text
    assert "function syncMirroredPlayback" in editor_suite_script_response.text
    assert "function scheduleFrameSync" in editor_suite_script_response.text
    assert 'for (const name of frameEntries.keys()) syncFrameTime(name);' in (
        editor_suite_script_response.text
    )
    frame_sync_start = editor_suite_script_response.text.index(
        "function scheduleFrameSync()"
    )
    frame_sync_end = editor_suite_script_response.text.index(
        "function renderActiveTool()", frame_sync_start
    )
    assert 'if (activeTool === "cut") return;' not in (
        editor_suite_script_response.text[frame_sync_start:frame_sync_end]
    )
    assert 'inspectorHost.classList.toggle("is-background", isCut)' in (
        editor_suite_script_response.text
    )
    assert "renderedPreviewState" in editor_suite_script_response.text
    assert "function normalizedToolHref" in editor_suite_script_response.text
    assert 'url.searchParams.delete("embedded")' in editor_suite_script_response.text
    assert "current.frame.dataset.toolHref !== toolHref" in (
        editor_suite_script_response.text
    )
    assert '["art", "pip"]' in editor_suite_script_response.text
    assert 'canvas.dataset.effectKind = layer.kind' in (
        editor_suite_script_response.text
    )
    assert 'kind: "shared"' in editor_suite_script_response.text
    assert "if (effectKind !== activeTool) return;" in (
        editor_suite_script_response.text
    )
    assert 'activeTool !== "cut" && Boolean(state)' not in (
        editor_suite_script_response.text
    )
    assert 'previewVideo?.addEventListener(eventName, scheduleFrameSync)' in editor_suite_script_response.text
    assert "height: auto !important;" in styles_response.text
    assert ".editor-suite-inspector-host" in styles_response.text
    timeline_layer_start = styles_response.text.index(".editor-suite-timeline-layer {")
    timeline_layer_end = styles_response.text.index("}", timeline_layer_start)
    timeline_layer_styles = styles_response.text[timeline_layer_start:timeline_layer_end]
    assert "background: transparent;" in timeline_layer_styles
    assert "border-bottom: 0;" in timeline_layer_styles
    assert 'body[data-active-editor-tool="art"] #cutFrameTimelineText' not in styles_response.text
    assert 'body[data-active-editor-tool="pip"] #cutFrameTimelineText' not in styles_response.text
    assert ".editor-suite-generate-dock" not in styles_response.text
    assert ".editor-suite-generate-button" in styles_response.text
    assert ".editor-suite-generation-runtime" in styles_response.text
    assert ".editor-suite-nav" in styles_response.text
    assert "body.has-result .site-header .editor-suite-nav" in styles_response.text
    assert "body.has-result .site-header .editor-suite-copy" in styles_response.text
    assert "height: calc(100dvh - 65px);" in styles_response.text

    assert "const downstreamReady" in editor_suite_script_response.text
    assert "按当前剪后时间添加" in editor_suite_script_response.text
    assert "点击生成视频会一次完成剪辑、艺术字和画中画合成" in (
        editor_suite_script_response.text
    )
    assert "function generationTarget()" not in editor_suite_script_response.text
    assert "function generateCurrentPreview()" in editor_suite_script_response.text
    assert 'target: "all"' in editor_suite_script_response.text
    assert "generationPayload" in editor_suite_script_response.text
    assert 'type: "editor-suite:cut-draft"' in editor_suite_script_response.text
    assert "workspaceCurrentTime" in editor_suite_script_response.text
    assert "setCutDraft," in editor_suite_script_response.text

    assert 'id="cutHistoryName"' not in page_response.text
    assert "data-editor-suite-save" in editor_suite_script_response.text
    assert "saveCurrentVersion" in editor_suite_script_response.text
    assert '/history`' in editor_suite_script_response.text


def test_upload_and_history_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/",
        "/styles.css",
        "/app.js",
    )
    page_response = responses["/"]
    styles_response = responses["/styles.css"]
    script_response = responses["/app.js"]

    assert 'id="cutOperationLock"' in page_response.text
    assert "setCutOperationLock" in script_response.text
    assert ".cut-operation-lock" in styles_response.text
    assert 'setAttribute("inert", "")' in script_response.text
    assert 'class="ambient-scan"' in page_response.text
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
    assert 'id="textSuggestionsTab"' not in page_response.text
    assert 'id="suggestionsBlock"' not in page_response.text
    assert 'id="selectAllSuggestionsButton"' not in page_response.text
    assert 'id="suggestionList"' not in page_response.text
    assert 'id="textSilenceTab"' not in page_response.text
    assert 'id="textSilencePanel"' not in page_response.text
    assert 'id="selectAllNoSpeechButton"' not in page_response.text
    assert 'id="noSpeechState"' not in page_response.text
    assert 'id="noSpeechList"' not in page_response.text
    assert 'id="directToolsPrompt"' in page_response.text
    assert 'id="continuePipButton"' in page_response.text
    assert 'selectAllSuggestionsButton.addEventListener("click"' not in script_response.text
    assert "AI 删减建议" not in page_response.text
    assert "已全部删除" not in script_response.text
    assert "const ignoredSuggestions" not in script_response.text
    assert "setCurrentNoSpeechSuggestions" in script_response.text
    assert "seedAutomaticNoSpeechRanges" in script_response.text
    assert "selectedNoSpeechRanges" in script_response.text
    assert "renderNoSpeechSegmentItem" in script_response.text
    assert "一键删除可删片段" not in page_response.text
    assert "可删片段已删除" not in script_response.text
    assert "previewNoSpeechSuggestion" in script_response.text
    assert "setOriginalSourceActionsAllowed(!job.edit?.status);" in script_response.text
    assert "setOriginalSourceActionsAllowed(false);" in script_response.text
    assert "continuePipButton.href" in script_response.text
    assert "source=edited" in script_response.text
    assert 'id="restartProjectButton"' in page_response.text
    assert 'id="result-title"' not in page_response.text
    assert 'class="result-stats"' not in page_response.text
    assert 'id="newUploadButton"' not in page_response.text
    assert "const newUploadButton" not in script_response.text


def test_cut_timeline_and_draft_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/",
        "/styles.css",
        "/app.js",
        "/editor-suite.js",
    )
    page_response = responses["/"]
    styles_response = responses["/styles.css"]
    script_response = responses["/app.js"]
    editor_suite_script_response = responses["/editor-suite.js"]

    assert 'id="cutPreviewVideo"' in page_response.text
    assert 'id="cutFrameTimeline"' in page_response.text
    assert 'id="cutFrameTimelineScroll"' in page_response.text
    assert 'id="cutFrameTimelineTrack"' in page_response.text
    assert 'id="cutFrameTimelineText"' in page_response.text
    assert 'id="cutFrameTimelineThumbnails"' in page_response.text
    assert 'id="cutFrameTimelineRanges"' in page_response.text
    assert 'id="timelineRangeConfirmActions"' not in page_response.text
    assert 'id="cancelTimelineRangeButton"' not in page_response.text
    assert 'id="confirmTimelineRangeButton"' not in page_response.text
    assert "松开后弹窗确认" not in page_response.text
    assert "选区保持精确范围，可微调，再次点击确认删除" in page_response.text
    assert "选区保持精确范围" in page_response.text
    assert "触碰文字时仅吸附完整文字边界" not in page_response.text
    assert 'id="clearSelectionButton" class="secondary-button" type="button" disabled hidden' in page_response.text
    assert 'clearSelectionButton.addEventListener("click"' not in script_response.text
    assert 'id="textEditorPreviewPane"' in page_response.text
    assert 'id="textTranscriptTab"' not in page_response.text
    assert 'id="textTranscriptPanel"' not in page_response.text
    assert 'id="transcriptText"' not in page_response.text
    assert 'id="transcriptSegmentList"' not in page_response.text
    assert "识别全文" not in page_response.text
    assert "saveTranscriptText" not in script_response.text
    assert 'class="text-editor-tabbar"' not in page_response.text
    assert 'id="textCutsTab"' not in page_response.text
    assert 'data-text-editor-tab=' not in page_response.text
    assert 'data-text-editor-panel=' not in page_response.text
    assert 'id="textCutsPanel"' in page_response.text
    assert 'aria-labelledby="text-cuts-title"' in page_response.text
    assert 'data-text-editor-tab="silence"' not in page_response.text
    assert 'data-text-editor-panel="silence"' not in page_response.text
    assert 'id="cutUndoButton"' not in page_response.text
    assert 'id="cutRedoButton"' not in page_response.text
    assert 'id="cutHistoryStatus"' not in page_response.text
    assert 'id="cutHistoryList"' not in page_response.text
    assert 'id="textHistoryTab"' not in page_response.text
    assert 'id="textHistoryPanel"' not in page_response.text
    assert "操作记录" not in page_response.text
    assert "function undoCutHistory()" in script_response.text
    assert "function redoCutHistory()" in script_response.text
    assert "handleGlobalCutHistoryShortcut" in script_response.text
    assert "isNativeUndoTarget" in script_response.text
    assert "video-editor:cut-history:${jobId}" in script_response.text
    assert 'stageCutHistoryOperation("删除时间轴区间")' in script_response.text
    assert 'aria-controls="textSilencePanel"' not in page_response.text
    assert 'data-text-editor-tab="output"' not in page_response.text
    assert '>生成结果</button>' not in page_response.text
    output_panel_start = page_response.text.index('id="textOutputPanel"')
    output_panel_end = page_response.text.index('id="textCutsPanel"')
    output_panel_markup = page_response.text[output_panel_start:output_panel_end]
    assert page_response.text.count('id="generateCutButton"') == 1
    assert 'id="generateCutButton"' in output_panel_markup
    assert 'id="outputCutSummary"' in output_panel_markup
    assert 'id="outputCutSelectionDetail"' in output_panel_markup
    assert 'class="editor-suite-generation-runtime"' in output_panel_markup
    assert 'aria-hidden="true"' in output_panel_markup
    assert 'id="generateNoSpeechCutButton"' not in page_response.text
    assert "generateNoSpeechCutButton" not in script_response.text
    assert 'generateCutButton.addEventListener("click", generateCut)' in script_response.text
    assert 'activateTextEditorPanel("output")' not in script_response.text
    assert "updateOriginalSourceActionsVisibility" in script_response.text
    assert "source=original" in script_response.text
    assert "picture-in-picture?job=" in script_response.text
    assert "/original-video`" in script_response.text
    assert "buildCutTimelineThumbnails" in script_response.text
    assert "renderCutTimelineTextSegments" in script_response.text
    assert "cutTimelinePixelsPerSecond" in script_response.text
    assert "CUT_TIMELINE_TEXT_LINES" in script_response.text
    assert "Math.ceil(total / majorStep) + 1" in script_response.text
    assert ".cut-timeline-text-segment {" in styles_response.text
    assert ".cut-frame-timeline .frame-timeline-thumb img {" in styles_response.text
    assert "background-repeat: repeat-x" in styles_response.text
    assert "beginCutTimelineSelection" in script_response.text
    assert "beginTimelineRangeAdjustment" in script_response.text
    assert "skipSelectedRangeDuringPlayback" in script_response.text
    assert "时间轴已自动拼接" in script_response.text
    assert "function getEditedTimelineSpans" in script_response.text
    assert "function editedTimeToSourceTime" in script_response.text
    assert "function sourceTimeToEditedTime" in script_response.text
    assert "getRetainedSegmentParts" in script_response.text
    assert "function updateCutSegmentTimestamps" in script_response.text
    assert 'currentBadge.textContent = "播放中"' in script_response.text
    assert 'playButton.className = "segment-play-button"' in script_response.text
    assert 'playButton.dataset.segmentPreview = "true"' in script_response.text
    assert 'playButton.title = "播放当前段落"' in script_response.text
    assert 'playButton.setAttribute("aria-label", `播放当前段落：${run.text}`)' in (
        script_response.text
    )
    assert "function previewTextSegment(item)" in script_response.text
    assert "transcriptPreviewRange" in script_response.text
    assert 'event.target.closest(".segment-play-button")' in script_response.text
    assert "function getActiveTranscriptSegmentIndex" in script_response.text
    assert 'nextItem.setAttribute("aria-current", "true")' in script_response.text
    assert "function getTranscriptFollowScrollTarget" in script_response.text
    assert "function scrollActiveTranscriptSegmentToAnchor" in script_response.text
    assert "function followActiveTranscriptSegment" in script_response.text
    assert "updateActiveTranscriptSegment(sourceCurrent" in script_response.text
    assert ".segment-item.is-playback-active" in styles_response.text
    assert 'id="cutDraftSaveStatus"' in page_response.text
    assert "function restorePersistedCutDraft" in script_response.text
    assert "function applyPersistedCutDraftAlignment" in script_response.text
    assert "function reconcileCurrentCutHistorySnapshot" in script_response.text
    assert "function scheduleCutDraftSave" in script_response.text
    assert "function clearPersistedCutDraft" in script_response.text
    assert "function resolvePersistedCutDraft" in script_response.text
    assert "window.localStorage.setItem(key" in script_response.text
    assert "/cut-draft`" in script_response.text
    assert "keepalive: true" in script_response.text
    assert "function setCurrentSuggestions" in script_response.text
    assert "function seedAutomaticSuggestionRanges" in script_response.text
    assert "function seedAutomaticNoSpeechRanges" in script_response.text
    assert "if (suggestion.deletable === false) continue" in script_response.text
    assert "const persistedDraft = resolvePersistedCutDraft(" in script_response.text
    assert "job.cutDraft ?? null" in script_response.text
    assert "if (persistedDraft === null)" in script_response.text
    assert "restorePersistedCutDraft(persistedDraft)" in script_response.text
    assert "automaticNoSpeechInitialized" in script_response.text
    assert 'noSpeechStatus === "completed" && !automaticNoSpeechInitialized' in (
        script_response.text
    )
    assert ".cut-draft-save-status" in styles_response.text
    assert 'item.dataset.noSpeechId = range.id' in script_response.text
    assert '"no-speech-restore"' in script_response.text
    assert 'item.classList.toggle("is-removed-from-timeline", !timing)' in script_response.text
    assert "function protectRestoredNoSpeechFromTextRanges" in script_response.text
    assert "...protectRestoredNoSpeechFromTextRanges(textRanges)" in script_response.text
    assert 'stageCutHistoryOperation("恢复空白片段")' in script_response.text
    assert 'stageCutHistoryOperation("删除空白片段")' in script_response.text
    assert "window.EditorSuite?.setCutDraft(state)" in script_response.text
    assert "function buildLiveCutDraftState" in script_response.text
    assert "sourceDuration: cutTimelineDuration()" in script_response.text
    assert "ranges: edit.ranges || edit.requestedRanges || []" in script_response.text
    assert "transcript: edit.transcript || null" in script_response.text
    assert "sourceStart: part.sourceStart" in script_response.text
    assert "sourceStart: wordSourceStart" in script_response.text
    assert "words: part.words" in script_response.text

    assert "const total = editedCutTimelineDuration(spans);" in script_response.text
    assert "function previewSelectedCutRange" in script_response.text
    assert "正在左侧预览裁剪衔接" in script_response.text
    assert script_response.text.count("previewSelectedCutRange(") >= 4


def test_cut_range_and_segment_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/",
        "/styles.css",
        "/app.js",
    )
    page_response = responses["/"]
    styles_response = responses["/styles.css"]
    script_response = responses["/app.js"]

    assert "function getRecognizedSpeechRanges" in script_response.text
    assert "function getRecognizedCharacterRanges" in script_response.text
    assert "function expandRangeToAdjacentSilence" in script_response.text
    assert "function alignManualRangeToTranscript" in script_response.text
    assert "当前拖动范围落在文字内部" not in script_response.text
    assert "边界落在无法安全裁剪的文字内部" not in script_response.text
    assert "覆盖文字时不会自动扩大" in script_response.text
    assert "getEditableSegmentCoverageEnd" in script_response.text
    assert "adjacentSilenceBefore" in script_response.text
    manual_align_start = script_response.text.index(
        "function alignManualRangeToTranscript"
    )
    manual_align_end = script_response.text.index(
        "function getCommittedTimelineDeleteRanges", manual_align_start
    )
    manual_align_script = script_response.text[manual_align_start:manual_align_end]
    assert "expandRangeToAdjacentSilence" not in manual_align_script
    assert "getRecognizedCharacterRanges" not in manual_align_script
    assert "adjacentSilenceBefore: 0" in manual_align_script
    assert "拖动自定义区间" in page_response.text
    assert "时间轴拖动按自定义区间处理" in page_response.text
    assert "前后紧邻的无声区" not in page_response.text
    assert "timelineDeleteRanges" in script_response.text
    assert "getCommittedTimelineDeleteRanges" in script_response.text
    assert "confirmPendingTimelineRange" in script_response.text
    assert "cancelPendingTimelineRange" in script_response.text
    assert "requestTimelineRangeConfirmation" in script_response.text
    assert "timelineRangeConfirmationOpen" in script_response.text
    assert 'cancelButton.className = "cut-timeline-range-cancel"' in script_response.text
    assert 'cancelButton.dataset.timelineRangeAction = "cancel"' in script_response.text
    assert 'cancelIcon.setAttribute("icon", "ph:x-bold")' in script_response.text
    assert 'cancelPendingTimelineRange("已取消时间轴选区。")' in script_response.text
    assert ".cut-timeline-range-cancel {" in styles_response.text
    assert ".cut-timeline-range-cancel iconify-icon {" in styles_response.text
    assert 'rangeElement.dataset.cancelSide' not in script_response.text
    selection_start = script_response.text.index(
        "function beginCutTimelineSelection"
    )
    selection_end = script_response.text.index(
        "function beginTimelineRangeAdjustment", selection_start
    )
    selection_script = script_response.text[selection_start:selection_end]
    assert "requestTimelineRangeConfirmation" not in selection_script
    adjustment_start = selection_end
    adjustment_end = script_response.text.index(
        "function cancelPendingTimelineRange", adjustment_start
    )
    adjustment_script = script_response.text[adjustment_start:adjustment_end]
    assert 'finishEvent.type === "pointerup"' in adjustment_script
    assert 'mode === "move"' in adjustment_script
    assert "if (!hasDragged)" in adjustment_script
    confirmation_start = script_response.text.index(
        "async function requestTimelineRangeConfirmation"
    )
    confirmation_end = script_response.text.index(
        "function adjustTimelineRangeWithKeyboard", confirmation_start
    )
    confirmation_script = script_response.text[
        confirmation_start:confirmation_end
    ]
    assert "cancelPendingTimelineRange();" not in confirmation_script
    assert "已保留待确认区间" in confirmation_script
    assert 'eyebrow: "时间轴滑动删除"' in script_response.text
    assert 'title: "删除这个时间轴区间？"' in script_response.text
    assert 'confirmText: "确认删除"' in script_response.text
    assert "已取消时间轴选区。" in script_response.text
    assert "hasPendingRange || getMergedSelection().length === 0" in script_response.text
    assert "已调整待确认区间" in script_response.text
    assert "CUT_TIMELINE_MIN_RANGE" in script_response.text
    assert "activateTextEditorPanel" not in script_response.text
    assert "splitTextIntoCharacterTokens" in script_response.text
    assert "function getTranscriptCharacterUnits" in script_response.text
    assert "parentWordStart: item.start" in script_response.text
    assert "parentWordEnd: item.end" in script_response.text
    assert "function canonicalizeTextSelectionRange" in script_response.text
    assert "function normalizeRestoredTextDeleteRange" in script_response.text
    assert "const restoredRange = normalizeRestoredTextDeleteRange(item);" in (
        script_response.text
    )
    assert "canonicalizeTextSelectionRange(semanticRange)" not in script_response.text
    assert "expandRangeToAdjacentSilence(semanticRange)" in script_response.text
    assert "const semanticRange = canonicalizeTextSelectionRange(range);" in (
        script_response.text
    )
    assert "formatPreciseTime" in script_response.text
    assert "点击左侧圆圈删除整段，再次点击可撤销" not in page_response.text
    assert "仅提示疑似口误、重复、语气词和无效片段" not in page_response.text
    assert "仅检测超过 1.5 秒的无文字区间" not in page_response.text
    assert "圆圈切换删除，点击文案调整分段" in page_response.text
    assert "点击文字删除会一并收紧前后无声区" in page_response.text
    assert "再次点击可撤销" in page_response.text
    assert 'time.textContent = formatTime(segmentStart)' in script_response.text
    assert 'segmentText.className = "segment-text"' in script_response.text
    assert "function suggestionTextRangeKeysAtTime" in script_response.text
    assert "function buildSegmentTextRuns" in script_response.text
    assert 'kind === "restore" || previous.presentationKey === presentationKey' in (
        script_response.text
    )
    assert "item.dataset.displayStart" in script_response.text
    assert "item.dataset.displayEnd" in script_response.text
    assert "item.dataset.displayKey" in script_response.text
    assert '"is-restored-fragment"' in script_response.text
    assert "fragment.append(item)" in script_response.text
    assert 'className = "segment-text-run segment-restore-button"' in script_response.text
    assert "restoreButton.dataset.rangeKeys" in script_response.text
    assert "所有 AI 建议都需由用户确认" not in page_response.text
    assert 'stageCutHistoryOperation("恢复已删除文字")' in script_response.text
    assert "segment-edit-hint" not in script_response.text
    assert "grid-template-columns: 44px 52px minmax(0, 1fr) 44px" in (
        styles_response.text
    )
    assert ".segment-play-button {" in styles_response.text
    assert ".segment-play-button:focus-visible" in styles_response.text
    assert "@media (max-width: 480px)" in styles_response.text
    assert "grid-template-columns: 44px minmax(0, 1fr) 44px" in (
        styles_response.text
    )
    assert "selectSegmentButton.disabled =" in script_response.text
    assert '`${allSelected ? "恢复删除文字" : "删除文字"}：${run.text}`' in script_response.text
    assert 'id="segmentEditDialog"' in page_response.text
    assert 'id="splitSegmentButton"' in page_response.text
    assert 'id="mergeSegmentUpButton"' in page_response.text
    assert 'id="mergeSegmentDownButton"' in page_response.text
    assert "applyEditableSegmentOperation" in script_response.text
    assert "/editable-segments`" in script_response.text
    assert ".segment-edit-dialog {" in styles_response.text
    assert ".cut-timeline-text-segment-label {" in styles_response.text
    assert "text-align-last: justify" in styles_response.text
    assert ".timeline-range-confirm-actions {" not in styles_response.text
    assert ".cut-timeline-delete-range.is-pending {" in styles_response.text
    assert "transcript-segment-text" not in script_response.text
    assert ".text-editor-tabbar {" not in styles_response.text
    assert ".text-editor-tab {" not in styles_response.text
    assert ".cut-history-toolbar {" not in styles_response.text
    assert ".cut-history-panel {" not in styles_response.text
    assert "min-height: 44px" in styles_response.text
    assert 'activateTextEditorPanel("cuts");' not in script_response.text
    assert 'job.edit ? "output" : "cuts"' not in script_response.text
    assert 'words.className = "word-list transcript-word-list"' not in script_response.text
    assert 'characters.className = "word-list"' not in script_response.text
    assert 'event.target.closest(".word-chip")' not in script_response.text
    assert "`${selectedSegmentCount} 段文字`" in script_response.text
    assert r"/\p{P}|\s/u" in script_response.text
    assert 'toDataURL("image/jpeg"' in script_response.text

    assert "--editor-timeline-track-height: 112px" in styles_response.text
    assert "--editor-timeline-ruler-height: 28px" in styles_response.text
    assert "--editor-timeline-track-height: 74px" in styles_response.text
    assert "--cut-timeline-text-height: 30px" in styles_response.text
    assert ".cut-frame-timeline .frame-timeline-tick-label" in styles_response.text
    assert "top: -7px" in styles_response.text
    assert "width: 100% !important" in styles_response.text
    assert "transform: rotate(0.55deg)" not in styles_response.text
    assert "margin-left: 13px" not in styles_response.text
    assert "margin-left: 9px" not in styles_response.text
    assert "grid-template-columns: 38px minmax(0, 1fr)" in styles_response.text
    assert ".segment-restore-button {" in styles_response.text
    assert ".segment-restore-button:focus-visible" in styles_response.text
    assert ".segment-item.is-no-speech-fragment {" in styles_response.text
    assert ".segment-no-speech-button {" in styles_response.text
    assert ".output-cut-builder {" in styles_response.text
    assert ".cut-timeline-no-speech-range {" in styles_response.text
    assert "grid-template-columns: minmax(0, 1fr) auto" in styles_response.text
    assert styles_response.text.count("height: var(--editor-timeline-track-height)") == 4
    assert "#cutPreviewPlayer:fullscreen .cut-frame-timeline" in styles_response.text
    assert "display: none !important" in styles_response.text
    assert "height: min(72dvh, 840px, calc(100dvh - 112px))" in styles_response.text

    assert "getEditedAudioQuietRanges" in script_response.text
    assert "audioQuietRanges: getEditedAudioQuietRanges(spans)" in script_response.text
    assert "resolveOverlappingRepeatAndQuietRanges" in script_response.text
    assert "protectRecognizedSpeechFromQuietRanges" in script_response.text
    assert "getRetainedTranscriptRanges" in script_response.text
    assert "subtractProtectedRanges" in script_response.text
    render_segments_start = script_response.text.index("function renderCutSegments()")
    render_segments_end = script_response.text.index(
        "function noSpeechKindLabel", render_segments_start
    )
    assert "const deletedRanges = getCommittedTimelineDeleteRanges();" in (
        script_response.text[render_segments_start:render_segments_end]
    )


def test_art_text_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/art-text",
        "/art-text.js",
        "/styles.css",
        "/editor-suite.js",
    )
    art_page_response = responses["/art-text"]
    art_script_response = responses["/art-text.js"]
    styles_response = responses["/styles.css"]
    editor_suite_script_response = responses["/editor-suite.js"]

    assert art_page_response.status_code == 200
    assert "/art-text.js?v=20260814-02" in art_page_response.text
    assert 'class="cut-progress art-generation-progress full-row"' in art_page_response.text
    assert "art-particle art-particle-1" in art_page_response.text
    assert "解析时间轴" in art_page_response.text
    assert ".art-generation-progress" in styles_response.text
    assert "@keyframes art-particle-float" in styles_response.text
    assert "@keyframes art-panel-scan" in styles_response.text
    assert "/styles.css?v=20260814-10" in art_page_response.text
    assert "/ui-feedback.js?v=20260807-03" in art_page_response.text
    assert 'id="overlayCoordinateReadout"' in art_page_response.text
    assert 'id="positionPresetGrid"' in art_page_response.text
    assert 'id="positionXPercent"' in art_page_response.text
    assert 'id="positionYPercent"' in art_page_response.text
    assert 'aria-label="手动输入艺术字坐标"' in art_page_response.text
    assert "commitPositionCoordinate" in art_script_response.text
    assert ".position-coordinate-fields {" in styles_response.text
    assert "/timeline-model.js?v=20260810-01" in art_page_response.text
    assert "/editor-suite.js?v=20260814-02" in art_page_response.text
    assert 'class="preview-grid"' in art_page_response.text
    assert 'data-preview-grid-toggle' in art_page_response.text
    assert "从保留文案中选择一句" not in art_page_response.text
    assert "播放或拖动视频进度" not in art_page_response.text
    assert "AI 会结合口播文案和低清关键帧拼图" not in art_page_response.text
    assert "关键帧仅临时上传到阿里云百炼，用于本次分析" in art_page_response.text
    assert "可修改文案、时间、位置和模板" not in art_page_response.text
    assert "生成后仍可返回修改参数" not in art_page_response.text
    assert 'data-editor-suite-nav data-stage="art"' in art_page_response.text
    assert 'data-workbench-tab="transcript"' not in art_page_response.text
    assert 'id="transcriptTab"' not in art_page_response.text
    assert 'class="transcript-quick-action"' in art_page_response.text
    assert "一键添加视频文案" in art_page_response.text
    assert "默认使用“热血立体”" in art_page_response.text
    assert "生成统一字号字幕" in art_script_response.text
    assert "TRANSCRIPT_TRACK_MAX_CHARS_PER_CUE = 12" in art_script_response.text
    assert "正在自动整理全文艺术字的内容和时间" in art_script_response.text
    assert "normalizeTranscriptTrackTiming" not in art_script_response.text
    assert "segments: retainedTranscriptSegments" in art_script_response.text
    assert "payload.draftTranscript = cutTranscript;" in art_script_response.text
    assert "Number(pendingCutDraft.duration) || duration" in art_script_response.text
    assert (
        art_script_response.text.count(
            "requestDraftVersion !== transcriptTrackDraftVersion"
        )
        == 2
    )
    assert "window.setTimeout(addFullTranscriptTrack, 0);" in art_script_response.text
    assert "comparableCaptionText(pendingTranscript.text)" not in art_script_response.text
    assert "cutDraftTranscriptTrackCues" in art_script_response.text
    assert "cutDraftTimedTranscriptWords" in art_script_response.text
    assert "segmentLower.indexOf(wordLower, textOffset)" in art_script_response.text
    assert "timedWords.at(-1).text += segmentContent.slice(textOffset)" in (
        art_script_response.text
    )
    assert "replaceTranscriptTrackFromCutDraft" in art_script_response.text
    assert "不会使用剪辑前的旧文案" in art_script_response.text
    assert 'type: "editor-suite:request-cut-draft"' in art_script_response.text
    assert 'data.type === "editor-suite:request-cut-draft"' in (
        editor_suite_script_response.text
    )
    assert "scheduleTranscriptTrackRefresh();" in art_script_response.text
    assert "trackRefreshPending ||" in art_script_response.text
    assert (
        'validationError === "全文艺术字轨道与当前视频文案不一致。"'
        in art_script_response.text
    )
    assert "请删除后重新生成" not in art_script_response.text
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
    assert 'data-workbench-tab="output"' not in art_page_response.text
    assert 'data-workbench-panel="output"' not in art_page_response.text
    assert "生成下载" not in art_page_response.text
    assert 'activateWorkbenchPanel("output")' not in art_script_response.text
    art_output_runtime = art_page_response.text[
        art_page_response.text.index('id="outputPanel"') :
        art_page_response.text.index('id="generateArtVideo"')
    ]
    assert 'class="editor-suite-generation-runtime"' in art_output_runtime
    assert 'aria-hidden="true"' in art_output_runtime
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
    assert 'id="artHistoryName"' not in art_page_response.text

    assert 'id="artTimeFitMessage"' in art_page_response.text
    assert 'id="frameTimeline"' in art_page_response.text
    assert 'id="frameTimelineSeek"' in art_page_response.text
    assert 'id="frameTimelineRuler"' in art_page_response.text
    assert 'id="frameTimelineJumpInput"' in art_page_response.text
    assert 'id="frameTimelineJumpButton"' in art_page_response.text
    assert 'id="frameTimelineThumbnails"' in art_page_response.text
    assert 'id="frameTimelineSegments"' in art_page_response.text
    assert 'aria-label="艺术字时间轴"' in art_page_response.text
    assert 'id="frameTimelineScroll"' in art_page_response.text
    assert 'class="frame-timeline editor-layer-timeline"' in art_page_response.text
    overlay_selection_start = art_page_response.text.index(
        'class="overlay-selection-block"'
    )
    custom_text_start = art_page_response.text.index('class="custom-text-row"')
    detail_settings_start = art_page_response.text.index('class="art-detail-heading"')
    overlay_controls_start = art_page_response.text.index('id="overlayControls"')
    assert (
        overlay_selection_start
        < custom_text_start
        < detail_settings_start
        < overlay_controls_start
    )
    assert "点击选择后，在下方修改" in art_page_response.text
    assert 'id="continuePictureInPicture"' in art_page_response.text
    assert 'id="transcriptStyleGrid"' in art_page_response.text
    assert "先选择字幕艺术字类型" in art_page_response.text
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
    assert ".filter(({ overlay }) => isOverlayVisibleAtTime(overlay, currentTime))" in art_script_response.text
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
    assert "setTranscriptTrackTemplate" in art_script_response.text
    assert 'const TRANSCRIPT_TRACK_DEFAULT_STYLE = "impact";' in art_script_response.text
    assert "selectedStyle = TRANSCRIPT_TRACK_DEFAULT_STYLE" in art_script_response.text
    assert "一键添加视频文案" in art_script_response.text
    assert "setupExternalVideoControls" in art_script_response.text
    assert "requestFullscreen" in art_script_response.text
    assert "buildFrameTimelineThumbnails" in art_script_response.text
    assert "updateFrameTimelineScale" in art_script_response.text
    assert "editor-layer-timeline-segment-label" in art_script_response.text
    assert "renderFrameTimelineRuler" in art_script_response.text
    assert "parseFrameTimelineTimeInput" in art_script_response.text
    assert "jumpToFrameTimelineTime" in art_script_response.text
    assert "refreshFrameTimeline" in art_script_response.text
    assert "renderFrameTimelineOverlaySegments" in art_script_response.text
    assert "FRAME_TIMELINE_TRACK_HEIGHT = 30" in art_script_response.text
    assert "trackIndexes.set(trackKey, trackIndexes.size)" in art_script_response.text
    assert "segment.dataset.timelineTrackIndex" in art_script_response.text
    assert "timelineTrackCount" in art_script_response.text
    assert "beginFrameTimelineSegmentAdjustment" in art_script_response.text
    assert "updateManualOverlayTimelineRange" in art_script_response.text
    assert "function syncFrameTimelineSegmentRange(overlay)" in art_script_response.text
    manual_range_start = art_script_response.text.index(
        "function updateManualOverlayTimelineRange(overlay, start, end)"
    )
    manual_range_end = art_script_response.text.index(
        "function beginFrameTimelineSegmentAdjustment", manual_range_start
    )
    assert "syncFrameTimelineSegmentRange(overlay);" in (
        art_script_response.text[manual_range_start:manual_range_end]
    )
    assert "data-art-time-drag" in art_script_response.text
    assert "segment.dataset.effectStart" in art_script_response.text
    assert "segment.dataset.effectEnd" in art_script_response.text
    assert 'kind: "art"' in art_script_response.text
    assert 'type: "editor-suite:tool-state"' in art_script_response.text
    assert "updateEditorSuiteJobState" in art_script_response.text
    assert "artGenerationObserver" in art_script_response.text
    assert "applyEditorCutDraft" in art_script_response.text
    assert "function retainedTimelineSpans" in art_script_response.text
    assert "function editedRangeForSourceOverlay" in art_script_response.text
    assert "anchorOverlayToSourceTimeline" in art_script_response.text
    assert "buildTranscriptWordMatchIndex" in art_script_response.text
    assert "matchOverlayToTranscriptWords" in art_script_response.text
    assert "previous.end = current.start;" in art_script_response.text
    assert "已按剪后文案的词级时间匹配" in art_script_response.text
    assert "persistEmbeddedArtDraft" in art_script_response.text
    assert "sourceStart: segment.sourceStart" in art_script_response.text
    assert "payload.draftTranscript =" in art_script_response.text
    assert "scheduleTranscriptTrackRefresh" in art_script_response.text
    cut_sync_start = art_script_response.text.index(
        "function applyEditorCutDraft(data)"
    )
    cut_sync_end = art_script_response.text.index(
        "function handleEditorHostMessage", cut_sync_start
    )
    cut_sync_script = art_script_response.text[cut_sync_start:cut_sync_end]
    assert "scheduleTranscriptTrackRefresh();" not in cut_sync_script
    assert "replaceTranscriptTrackFromCutDraft(" in cut_sync_script
    assert "editorHostCurrentTime" in art_script_response.text
    assert "previewVisibilitySignature" in art_script_response.text
    assert "renderPreview({ timeOnly: true })" in art_script_response.text
    assert "renderArtTextCharacters" in art_script_response.text
    assert "alignCharacterTimingsToAudioActivity" in art_script_response.text
    assert "audioQuietRanges: retainedAudioQuietRanges" in art_script_response.text
    assert "compactArtStyleSample" in art_script_response.text
    assert "speechAnimationPreviewSignature" in art_script_response.text
    assert "characterTimings" in art_script_response.text
    assert "spokenDuration + 0.18" in art_script_response.text
    assert '"center-highlight"' in art_script_response.text
    assert '"character-bounce"' in art_script_response.text

    art_sync_start = art_script_response.text.index(
        'if (data.type === "editor-suite:sync-time")'
    )
    art_sync_end = art_script_response.text.index(
        'if (data.type !== "editor-suite:move-effect"', art_sync_start
    )
    art_sync_script = art_script_response.text[art_sync_start:art_sync_end]
    assert "artVideo.currentTime = nextTime" not in art_sync_script
    assert "artVideo.pause()" not in art_sync_script
    assert "已按当前剪后文案实时同步" in art_script_response.text
    assert "剪辑视频生成后即可使用 AI 全文分句" not in art_script_response.text
    assert "beginFrameTimelineScrub" in art_script_response.text
    assert "artTimelineStore" in art_script_response.text
    assert "createPointerSession" in art_script_response.text
    assert 'data.type === "editor-suite:timeline-action"' in art_script_response.text
    assert "toDataURL(\"image/jpeg\"" in art_script_response.text
    assert "const edgeOffset = Math.min(0.04, total / 2)" in art_script_response.text
    assert 'videoSource === "original" && payload.edit?.status' in art_script_response.text
    assert art_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert art_script_response.headers["cache-control"] == "no-store, max-age=0"


def test_picture_in_picture_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/picture-in-picture",
        "/picture-in-picture.js",
        "/styles.css",
        "/editor-suite.js",
        "/art-text.js",
    )
    pip_page_response = responses["/picture-in-picture"]
    pip_script_response = responses["/picture-in-picture.js"]
    styles_response = responses["/styles.css"]
    editor_suite_script_response = responses["/editor-suite.js"]
    art_script_response = responses["/art-text.js"]

    assert pip_page_response.status_code == 200
    assert "/picture-in-picture.js?v=20260812-01" in pip_page_response.text
    assert "/ui-feedback.js?v=20260807-03" in pip_page_response.text
    assert "/styles.css?v=20260812-02" in pip_page_response.text
    assert "/timeline-model.js?v=20260810-01" in pip_page_response.text
    assert "/editor-suite.js?v=20260814-02" in pip_page_response.text
    assert 'class="preview-grid"' in pip_page_response.text
    assert 'data-preview-grid-toggle' in pip_page_response.text
    assert 'data-editor-suite-nav data-stage="pip"' in pip_page_response.text
    assert 'name="assetType" value="video"' in pip_page_response.text
    assert "Seedance 动态镜头" in pip_page_response.text
    assert 'class="pip-editor-body"' in pip_page_response.text
    assert 'id="pipTimelineScroll"' in pip_page_response.text
    assert 'class="frame-timeline editor-layer-timeline pip-timeline"' in pip_page_response.text
    assert 'id="segmentList"' in pip_page_response.text
    assert "time.textContent = formatTime(segment.start)" in pip_script_response.text
    assert "beginPipTimelineSegmentAdjustment" in pip_script_response.text
    assert "pipTimelineStore" in pip_script_response.text
    assert "handle.dataset.timelineResize = mode" in pip_script_response.text
    assert "grid-template-columns: 28px minmax(0, 1fr)" in styles_response.text
    assert "grid-template-columns: 46px minmax(0, 1fr)" in styles_response.text
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
    assert "applyEditorCutDraft" in pip_script_response.text
    assert "persistEmbeddedPipDraft" in pip_script_response.text
    assert "start: item.start" in pip_script_response.text
    assert "sourceStart: segment.sourceStart ?? null" in pip_script_response.text
    assert 'id="imageProgress" class="pip-inline-progress pip-tech-progress"' in pip_page_response.text
    assert "pip-tech-particle pip-tech-particle-5" in pip_page_response.text
    assert 'id="generatedList"' in pip_page_response.text
    assert 'id="pipOverlayLayer"' in pip_page_response.text
    assert "选择一段口播文字，生成对应画面" not in pip_page_response.text
    assert "每个画中画独立一条轨道" not in pip_page_response.text
    assert "时间轴显示当前视频" not in pip_page_response.text
    assert "画中画出现后可直接按住拖动摆放" not in pip_page_response.text
    assert "previewHint" not in pip_script_response.text
    assert "PIP_TIMELINE_TRACK_HEIGHT = 30" in pip_script_response.text
    assert "segment.dataset.timelineTrackIndex" in pip_script_response.text
    assert 'const trackLabel = `画中画${index + 1}`;' in pip_script_response.text
    assert "label.textContent = trackLabel" in pip_script_response.text
    assert (
        'segment.title = `${trackLabel} ${formatRange(item.start, item.end)}`'
        in pip_script_response.text
    )
    assert "timelineTrackCount" in pip_script_response.text
    assert 'type: "editor-suite:select-pip-timeline"' in editor_suite_script_response.text
    assert 'data.type === "editor-suite:select-pip-timeline"' in pip_script_response.text
    assert "拖动边框缩放" in pip_page_response.text
    assert "beginPictureResize" in pip_script_response.text
    assert "pictureResizeWidth" in pip_script_response.text
    assert 'handle.className = "pip-resize-handle"' in pip_script_response.text
    assert 'data.type === "editor-suite:resize-effect"' in pip_script_response.text
    assert 'type: "editor-suite:resize-effect"' in editor_suite_script_response.text
    assert ".pip-resize-handle" in styles_response.text
    assert '[data-pip-resize="se"]' in styles_response.text
    assert 'kind: "pip"' in pip_script_response.text
    assert 'type: "editor-suite:tool-state"' in pip_script_response.text
    assert "updateEditorSuiteJobState" in pip_script_response.text
    assert "pipGenerationObserver" in pip_script_response.text
    assert 'id="pipTimelineThumbnails"' in pip_page_response.text
    assert 'id="generatePipVideo"' in pip_page_response.text
    assert 'class="pip-output-section editor-suite-generation-runtime"' in pip_page_response.text
    assert 'document.querySelector(".pip-output-section")?.scrollIntoView' not in pip_script_response.text
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
    assert 'const endpoint = useComposition ? "compose" : "picture-in-picture"' in (
        pip_script_response.text
    )
    assert "pictureInPictureOverlays: overlays" in pip_script_response.text
    assert 'const endpoint = useComposition ? "compose" : "art-text"' in (
        art_script_response.text
    )
    assert "AI 根据文字智能生成" in pip_script_response.text
    assert "aspectRatio: currentImageAspectRatio()" in pip_script_response.text
    assert '"original", "edited", "art"' in pip_script_response.text
    assert "source: requestedSource" in pip_script_response.text
    assert "renderPreview" in pip_script_response.text
    assert "editorHostCurrentTime" in pip_script_response.text
    assert "previewVisibilitySignature" in pip_script_response.text
    assert "renderPreview({ timeOnly: true })" in pip_script_response.text
    pip_sync_start = pip_script_response.text.index(
        'if (data.type === "editor-suite:sync-time")'
    )
    pip_sync_end = pip_script_response.text.index(
        'if (data.type !== "editor-suite:move-effect"', pip_sync_start
    )
    pip_sync_script = pip_script_response.text[pip_sync_start:pip_sync_end]
    assert "pipVideo.currentTime = nextTime" not in pip_sync_script
    assert "pipVideo.pause()" not in pip_sync_script
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
    assert "updatePipTimelineScale" in pip_script_response.text
    assert "pipTimelineMajorStep" in pip_script_response.text
    assert pip_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert editor_suite_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert pip_script_response.headers["cache-control"] == "no-store, max-age=0"


def test_art_template_library_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/fonts",
        "/art-template-library.js",
        "/api/art-templates",
        "/art-text.js",
    )
    template_page_response = responses["/fonts"]
    template_script_response = responses["/art-template-library.js"]
    template_api_response = responses["/api/art-templates"]
    art_script_response = responses["/art-text.js"]

    assert template_page_response.status_code == 200
    assert "/styles.css?v=20260812-02" in template_page_response.text
    assert "/art-template-library.js?v=20260812-02" in template_page_response.text
    assert "当前模板主色" in template_page_response.text
    assert 'id="templateCardGrid"' in template_page_response.text
    assert 'id="useTemplateButton"' in template_page_response.text
    assert 'id="openTemplateUpload"' in template_page_response.text
    assert 'id="templateUploadDialog"' in template_page_response.text
    assert 'id="renameTemplateButton"' in template_page_response.text
    assert 'id="deleteTemplateButton"' in template_page_response.text
    assert "艺术字效果模板库" in template_page_response.text
    assert "上传和管理可编辑效果模板" not in template_page_response.text
    assert "templateDetailNote" not in template_page_response.text
    assert "templateDetailNote" not in template_script_response.text
    assert "点击恢复后重新出现在模板库" in template_page_response.text
    assert "/api/art-templates" in template_script_response.text
    assert "preferredArtTemplateSettings" in template_script_response.text
    assert "characterLayout" in art_script_response.text
    assert "is-character-staggered" in template_script_response.text
    assert "const effects = normalizedTemplateEffects(template, color);" in (
        template_script_response.text
    )
    assert "function fitEffectPreviewText(element)" in (
        template_script_response.text
    )
    assert "const templateColors = new Map();" in template_script_response.text
    assert "function templateColorFor(template)" in template_script_response.text
    assert "templateColors.set(template.id, templatePreviewColor.value);" in (
        template_script_response.text
    )
    assert 'window.addEventListener("resize", scheduleEffectPreviewFit);' in (
        template_script_response.text
    )
    assert 'method: "PATCH"' in template_script_response.text
    assert 'method: "DELETE"' in template_script_response.text
    assert "loadArtTemplateLibrary" in art_script_response.text
    assert "ART_STYLE_BASES" in art_script_response.text
    assert "renderTemplateCharacters" in template_script_response.text
    assert 'type: "character-bounce"' in template_script_response.text
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


def test_font_manager_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/font-manager",
        "/font-manager.js",
    )
    font_page_response = responses["/font-manager"]
    font_script_response = responses["/font-manager.js"]

    assert font_page_response.status_code == 200
    assert "/styles.css?v=20260812-02" in font_page_response.text
    assert "/font-manager.js?v=" in font_page_response.text
    assert 'id="fontUploadForm"' in font_page_response.text
    assert 'id="fontCardGrid"' in font_page_response.text
    assert "上传 TTF 或 OTF 字体" not in font_page_response.text
    assert "可以查看完整预览、设置默认字体" not in font_page_response.text
    assert "请确认拥有字体使用权" in font_page_response.text
    assert "/api/fonts" in font_script_response.text
    assert "registerUploadedFont" in font_script_response.text
    assert font_page_response.headers["cache-control"] == "no-store, max-age=0"
    assert font_script_response.headers["cache-control"] == "no-store, max-age=0"


def test_frontend_text_ranges_use_character_units_with_per_segment_fallback():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    helper_start = app_source.index("function splitTextIntoCharacterTokens")
    helper_end = app_source.index("const EDITABLE_CLAUSE_ENDINGS", helper_start)
    recognized_start = app_source.index("function getRecognizedCharacterRanges")
    recognized_end = app_source.index(
        "function getRecognizedSpeechRanges", recognized_start
    )
    canonical_start = app_source.index("function canonicalizeTextSelectionRange")
    canonical_end = app_source.index("function alignManualRangeToTranscript")
    manual_end = app_source.index(
        "function getCommittedTimelineDeleteRanges", canonical_end
    )
    restored_start = app_source.index("function serializableCutDraftRange")
    restored_end = app_source.index("function buildPersistedCutDraftPayload")
    history_start = app_source.index("function applyCutHistorySnapshot")
    history_end = app_source.index("function undoCutHistory", history_start)
    transcript_function_source = "\n".join(
        [
            app_source[helper_start:helper_end],
            app_source[recognized_start:recognized_end],
            app_source[canonical_start:canonical_end],
            app_source[canonical_end:manual_end],
            app_source[restored_start:restored_end],
            app_source[history_start:history_end],
        ]
    )
    mixed_segments = [
        {
            "start": 0.0,
            "end": 0.6,
            "text": "一起给",
            "words": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给", "start": 0.4, "end": 0.6},
            ],
            "asrWords": [
                {"text": "一起", "start": 0.0, "end": 0.4},
                {"text": "给一", "start": 0.4, "end": 0.8},
            ],
        },
        {
            "start": 1.0,
            "end": 1.4,
            "text": "旧段",
            "words": [],
            "asrWords": [{"text": "旧段", "start": 1.0, "end": 1.4}],
        },
        {
            "start": 2.0,
            "end": 2.4,
            "text": "整段",
            "words": [],
            "asrWords": [],
        },
        {
            "start": 2.4,
            "end": 3.0,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 2.4, "end": 2.8},
                {"text": "你", "start": 2.8, "end": 3.0},
            ],
            "asrWords": [
                {"text": "觉", "start": 2.4, "end": 2.6},
                {"text": "得你", "start": 2.6, "end": 3.0},
            ],
        },
    ]
    script = f"""
const source = {json.dumps(transcript_function_source)};
const rangeKey = (start, end) =>
  Number(start).toFixed(3) + ":" + Number(end).toFixed(3);
const segments = {json.dumps(mixed_segments, ensure_ascii=False)};
const transcriptFunctions = new Function(
  "rangeKey",
  "currentSegments",
  "currentEditableSegments",
  "cutTimelineDuration",
  "clamp",
  `
const CUT_SPEECH_BOUNDARY_EPSILON = 0.001;
const selectedRanges = new Map();
const selectedNoSpeechRanges = new Map();
let timelineDeleteRanges = [];
let nextTimelineRangeId = 1;
let selectedTimelineRangeId = null;
let timelineRangeInProgress = false;
let timelineRangeConfirmationOpen = false;
let cutHistoryLastState = null;
let cutHistoryReplaying = false;
const cloneCutHistorySnapshot = (snapshot) => snapshot;
const updateCutTimelineStatus = () => {{}};
const updateSelectionSummary = () => {{}};
${{source}}
return {{
  getSegmentTokens,
  getTranscriptCharacterUnits,
  normalizeRestoredTextDeleteRange,
  alignManualRangeToTranscript,
  applyCutHistorySnapshot,
  selectedRanges,
}};`,
)(rangeKey, segments, [], () => 3, (value, minimum, maximum) => (
  Math.min(maximum, Math.max(minimum, value))
));
const units = transcriptFunctions.getTranscriptCharacterUnits(segments);
const restored = transcriptFunctions.normalizeRestoredTextDeleteRange({{
  key: "legacy-partial",
  start: 0.01,
  end: 0.59,
  originalStart: 0.01,
  originalEnd: 0.59,
}});
const manual = transcriptFunctions.alignManualRangeToTranscript({{
  start: 0.41,
  end: 0.59,
}});
const deNiRestored = transcriptFunctions.normalizeRestoredTextDeleteRange({{
  key: "legacy-de-ni-partial",
  start: 2.41,
  end: 2.79,
  originalStart: 2.41,
  originalEnd: 2.79,
}});
const alignedSharedBoundary = transcriptFunctions.normalizeRestoredTextDeleteRange({{
  key: "shared-de-ni",
  start: 2.4,
  end: 2.84,
  originalStart: 2.4,
  originalEnd: 2.8,
}});
transcriptFunctions.applyCutHistorySnapshot({{
  textRanges: [{{
    key: "history-de-ni-partial",
    start: 2.41,
    end: 2.79,
    originalStart: 2.41,
    originalEnd: 2.79,
  }}],
  noSpeechRanges: [],
  timelineRanges: [],
}});
const historyRestored = [...transcriptFunctions.selectedRanges.values()][0];
console.log(JSON.stringify({{
  units,
  restored,
  manual,
  deNiRestored,
  alignedSharedBoundary,
  historyRestored,
}}));
"""

    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the frontend transcript unit test.")

    payload = json.loads(result.stdout)
    assert [item["text"] for item in payload["units"]] == [
        "一",
        "起",
        "给",
        "旧",
        "段",
        "整",
        "段",
        "觉",
        "得",
        "你",
    ]
    assert payload["restored"] == {
        "start": 0,
        "end": 0.6,
        "text": "",
        "originalStart": 0,
        "originalEnd": 0.6,
        "adjacentSilenceBefore": 0,
        "adjacentSilenceAfter": 0,
    }
    assert payload["manual"] == {
        "start": 0.41,
        "end": 0.59,
        "originalStart": 0.41,
        "originalEnd": 0.59,
        "adjacentSilenceBefore": 0,
        "adjacentSilenceAfter": 0,
    }
    expected_de_ni = {
        "start": 2.4,
        "end": 2.8,
        "text": "",
        "originalStart": 2.4,
        "originalEnd": 2.8,
        "adjacentSilenceBefore": 0,
        "adjacentSilenceAfter": 0,
    }
    assert payload["deNiRestored"] == expected_de_ni
    assert payload["historyRestored"] == expected_de_ni
    assert payload["alignedSharedBoundary"] == {
        "start": 2.4,
        "end": 2.84,
        "text": "",
        "originalStart": 2.4,
        "originalEnd": 2.8,
        "adjacentSilenceBefore": 0,
        "adjacentSilenceAfter": pytest.approx(0.04),
    }


def test_frontend_merges_adjacent_deleted_text_across_range_keys():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    token_start = app_source.index("function splitTextIntoCharacterTokens")
    token_end = app_source.index("const EDITABLE_CLAUSE_ENDINGS", token_start)
    run_start = app_source.index("function selectedTextRangeKeysAtTime")
    run_end = app_source.index("function renderSegmentTextRun", run_start)
    render_start = app_source.index("function renderCutSegments")
    render_end = app_source.index("function updateCutSegmentText", render_start)
    click_start = app_source.index('segmentList.addEventListener("click"')
    click_end = app_source.index("\n\nfor (const eventName", click_start)
    source = "\n".join(
        [
            app_source[token_start:token_end],
            app_source[run_start:run_end],
            app_source[render_start:render_end],
            app_source[click_start:click_end],
        ]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const selectedRanges = new Map();
const currentSuggestions = [];
const currentEditableSegments = [];
const currentNoSpeechSuggestions = [];
let activeTranscriptSegmentIndex = -1;
let activeTranscriptSegmentKey = "";
let followedTranscriptSegmentKey = "";
const renderedItems = [];
const historyActions = [];
const seekTimes = [];
let selectionUpdateCount = 0;
let segmentClickHandler = null;
let cutControlsLocked = false;
const rangeKey = (start, end) =>
  Number(start).toFixed(3) + "-" + Number(end).toFixed(3);
const getSuggestionRanges = (suggestion) => suggestion.ranges || [];
const getCommittedTimelineDeleteRanges = () => [];
const getNoSpeechRange = (suggestion) => suggestion;
const stageCutHistoryOperation = (label) => historyActions.push(label);
const updateSelectionSummary = () => {{ selectionUpdateCount += 1; }};
const seekCutPreview = (time) => seekTimes.push(time);
const renderTextSegmentItem = (run) => ({{ type: "text", text: run.text }});
const renderNoSpeechSegmentItem = (suggestion) => ({{
  type: "no-speech",
  id: suggestion.id,
}});
class Element {{
  closest() {{ return null; }}
}}
class HTMLButtonElement extends Element {{
  constructor(rangeKeys) {{
    super();
    this.disabled = false;
    this.dataset = {{ rangeKeys: JSON.stringify(rangeKeys) }};
  }}
  closest(selector) {{
    return selector === ".segment-restore-button" ? this : null;
  }}
}}
const document = {{
  createDocumentFragment: () => ({{
    children: [],
    append(item) {{ this.children.push(item); }},
  }}),
}};
const segmentList = {{
  replaceChildren(fragment) {{ renderedItems.push(...fragment.children); }},
  addEventListener(type, handler) {{
    if (type === "click") segmentClickHandler = handler;
  }},
}};
const updateCutSegmentTimestamps = () => {{}};
${{source}}
return {{
  selectedRanges,
  currentSuggestions,
  currentEditableSegments,
  currentNoSpeechSuggestions,
  renderedItems,
  buildSegmentTextRuns,
  renderCutSegments,
  clickMergedRestoreRangeKeys(rangeKeys) {{
    segmentClickHandler({{ target: new HTMLButtonElement(rangeKeys) }});
  }},
  historyActions,
  seekTimes,
  getSelectionUpdateCount: () => selectionUpdateCount,
}};
`)();
const segment = {{
  start: 0,
  end: 5,
  text: "你身边人人都觉得",
  words: [
    {{ text: "你", start: 0, end: 1 }},
    {{ text: "身边", start: 1, end: 2 }},
    {{ text: "人", start: 2, end: 3 }},
    {{ text: "人", start: 3, end: 4 }},
    {{ text: "都觉得", start: 4, end: 5 }},
  ],
}};
for (const [key, start, end] of [
  ["a", 0, 1],
  ["b", 1, 2],
  ["c", 2, 3],
  ["d", 3, 4],
  ["e", 4, 5],
]) {{
  functions.selectedRanges.set(key, {{
    start,
    end,
    originalStart: start,
    originalEnd: end,
  }});
}}
const adjacent = functions.buildSegmentTextRuns(segment, []);
functions.clickMergedRestoreRangeKeys(adjacent[0].rangeKeys);
const remainingAfterRestore = [...functions.selectedRanges.keys()];

functions.selectedRanges.set("left", {{
  start: 0,
  end: 1,
  originalStart: 0,
  originalEnd: 1,
}});
functions.selectedRanges.set("right", {{
  start: 2,
  end: 3,
  originalStart: 2,
  originalEnd: 3,
}});
functions.currentSuggestions.push({{
  ranges: [{{ start: 1, end: 2 }}],
}});
const split = functions.buildSegmentTextRuns({{
  start: 0,
  end: 3,
  text: "删留删",
  words: [
    {{ text: "删", start: 0, end: 1 }},
    {{ text: "留", start: 1, end: 2 }},
    {{ text: "删", start: 2, end: 3 }},
  ],
}}, []);
functions.selectedRanges.clear();
functions.currentSuggestions.length = 0;
const timelineDeleted = functions.buildSegmentTextRuns({{
  start: 0,
  end: 2,
  text: "甲乙",
  words: [
    {{ text: "甲", start: 0, end: 1 }},
    {{ text: "乙", start: 1, end: 2 }},
  ],
}}, [
  {{ start: 0, end: 1 }},
  {{ start: 1, end: 2 }},
]);

functions.currentEditableSegments.push({{
  start: 0,
  end: 1,
  text: "文案",
  words: [{{ text: "文案", start: 0, end: 1 }}],
}});
functions.currentNoSpeechSuggestions.push({{ id: "quiet", start: 1, end: 2 }});
functions.renderCutSegments();
console.log(JSON.stringify({{
  adjacent,
  split,
  timelineDeleted,
  remainingAfterRestore,
  historyActions: functions.historyActions,
  seekTimes: functions.seekTimes,
  selectionUpdateCount: functions.getSelectionUpdateCount(),
  renderedItems: functions.renderedItems,
}}));
"""

    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the deleted-text grouping test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert len(payload["adjacent"]) == 1
    assert payload["adjacent"][0]["kind"] == "restore"
    assert payload["adjacent"][0]["text"] == "你身边人人都觉得"
    assert payload["adjacent"][0]["rangeKeys"] == ["a", "b", "c", "d", "e"]
    assert [run["kind"] for run in payload["split"]] == [
        "restore",
        "edit",
        "restore",
    ]
    assert [run["text"] for run in payload["split"]] == ["删", "留", "删"]
    assert payload["split"][1]["suggestionRangeKeys"] == ["1.000-2.000"]
    assert [run["text"] for run in payload["timelineDeleted"]] == ["甲", "乙"]
    assert all(run["kind"] == "deleted" for run in payload["timelineDeleted"])
    assert payload["remainingAfterRestore"] == []
    assert payload["historyActions"] == ["恢复已删除文字"]
    assert payload["seekTimes"] == [0]
    assert payload["selectionUpdateCount"] == 1
    assert payload["renderedItems"] == [
        {"type": "text", "text": "文案"},
        {"type": "no-speech", "id": "quiet"},
    ]


def test_frontend_merged_selection_preserves_shared_physical_boundaries():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    helper_start = app_source.index("function splitTextIntoCharacterTokens")
    helper_end = app_source.index("const EDITABLE_CLAUSE_ENDINGS", helper_start)
    range_start = app_source.index("function mergeCutRanges")
    range_end = app_source.index("function expandRangeToAdjacentSilence", range_start)
    canonical_start = app_source.index("function canonicalizeTextSelectionRange")
    selection_start = app_source.index("function getCommittedTimelineDeleteRanges")
    selection_end = app_source.index("function getEditedTimelineSpans", selection_start)
    source = "\n".join(
        [
            app_source[helper_start:helper_end],
            app_source[range_start:range_end],
            app_source[canonical_start:selection_start],
            app_source[selection_start:selection_end],
        ]
    )
    segments = [
        {
            "start": 0.0,
            "end": 0.6,
            "text": "觉得你",
            "words": [
                {"text": "觉得", "start": 0.0, "end": 0.4},
                {"text": "你", "start": 0.4, "end": 0.6},
            ],
        }
    ]
    script = f"""
const source = {json.dumps(source)};
const segments = {json.dumps(segments, ensure_ascii=False)};
const functions = new Function(
  "currentSegments",
  "currentEditableSegments",
  "cutTimelineDuration",
  "clamp",
  `
const CUT_SPEECH_BOUNDARY_EPSILON = 0.001;
const CUT_SAFE_NO_SPEECH_MIN_DURATION = 0.45;
const rangeKey = (start, end) =>
  Number(start).toFixed(3) + ":" + Number(end).toFixed(3);
const selectedRanges = new Map();
const selectedNoSpeechRanges = new Map();
const currentNoSpeechSuggestions = [];
const getNoSpeechRange = () => null;
let timelineDeleteRanges = [];
let timelineRangeInProgress = false;
let selectedTimelineRangeId = null;
${{source}}
return {{ selectedRanges, getMergedSelection }};
`,
)(segments, [], () => 1, (value, minimum, maximum) => (
  Math.min(maximum, Math.max(minimum, value))
));
functions.selectedRanges.set("tail", {{
  start: 0.0,
  end: 0.44,
  originalStart: 0.0,
  originalEnd: 0.4,
}});
const tail = functions.getMergedSelection();
functions.selectedRanges.clear();
functions.selectedRanges.set("head", {{
  start: 0.04,
  end: 0.4,
  originalStart: 0.0,
  originalEnd: 0.4,
}});
const head = functions.getMergedSelection();
console.log(JSON.stringify({{ tail, head }}));
"""

    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the frontend cut-range unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert payload["tail"] == [{"start": 0.0, "end": 0.44}]
    assert payload["head"] == [{"start": 0.04, "end": 0.4}]


def test_frontend_transcript_follow_scroll_anchors_clamps_and_deduplicates():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    helper_start = app_source.index("function getTranscriptFollowScrollTarget")
    helper_end = app_source.index("function updateActiveTranscriptSegment", helper_start)
    helper_source = app_source[helper_start:helper_end]
    script = f"""
const frames = [];
const scrollCalls = [];
let reduceMotion = false;
let toolbarHeight = 60;
const toolbarOffset = 18;
const window = {{
  cancelAnimationFrame: () => {{}},
  requestAnimationFrame: (callback) => {{
    frames.push(callback);
    return frames.length;
  }},
  getComputedStyle: () => ({{ top: "0px" }}),
  matchMedia: () => ({{ matches: reduceMotion }}),
}};
const clamp = (value, minimum, maximum) => (
  Math.min(maximum, Math.max(minimum, value))
);
let transcriptFollowScrollFrame = 0;
let followedTranscriptSegmentKey = "";
{helper_source}
const toolbar = {{
  getBoundingClientRect: () => ({{
    top: 100 + toolbarOffset,
    bottom: 100 + toolbarOffset + toolbarHeight,
    height: toolbarHeight,
  }}),
}};
const panel = {{
  hidden: false,
  clientHeight: 300,
  scrollHeight: 1000,
  scrollTop: 100,
  getBoundingClientRect: () => ({{ top: 100, bottom: 400, height: 300 }}),
  querySelector: (selector) => selector === ".cut-toolbar" ? toolbar : null,
  scrollTo: (options) => {{
    scrollCalls.push(options);
    panel.scrollTop = options.top;
  }},
}};
let itemContentTop = 300;
const item = {{
  isConnected: true,
  classList: {{ contains: (name) => name === "is-playback-active" }},
  closest: (selector) => selector === ".text-editor-panel" ? panel : null,
  getBoundingClientRect: () => {{
    const top = 100 + itemContentTop - panel.scrollTop;
    return {{ top, bottom: top + 64, height: 64 }};
  }},
}};

const shortToolbarTarget = getTranscriptFollowScrollTarget(panel, item, toolbar);
toolbarHeight = 92;
const tallToolbarTarget = getTranscriptFollowScrollTarget(panel, item, toolbar);
toolbarHeight = 60;
followActiveTranscriptSegment(item, "row-a");
followActiveTranscriptSegment(item, "row-a");
const queuedAfterDuplicate = frames.length;
frames.shift()();
const anchorTop = 100 + toolbarOffset + toolbarHeight + 8;
const middleAnchorOffset = item.getBoundingClientRect().top - anchorTop;
itemContentTop = 1000;
reduceMotion = true;
followActiveTranscriptSegment(item, "row-b");
frames.shift()();
const tailAnchorOffset = item.getBoundingClientRect().top - anchorTop;
console.log(JSON.stringify({{
  queuedAfterDuplicate,
  shortToolbarTarget,
  tallToolbarTarget,
  middleAnchorOffset,
  tailAnchorOffset,
  scrollCalls,
}}));
"""

    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the transcript follow-scroll test.")

    payload = json.loads(result.stdout)
    assert payload["queuedAfterDuplicate"] == 1
    assert payload["shortToolbarTarget"] == 214
    assert payload["tallToolbarTarget"] == 182
    assert payload["middleAnchorOffset"] == 0
    assert payload["tailAnchorOffset"] == 214
    assert payload["scrollCalls"] == [
        {"top": 214, "behavior": "smooth"},
        {"top": 700, "behavior": "auto"},
    ]


def test_timeline_model_shares_selection_drag_resize_and_persistence():
    script = r"""
const timeline = require('./web/timeline-model.js');
const commits = [];
const store = timeline.createStore({
  duration: 12,
  tracks: [
    { id: 'cut:deletions', kind: 'cut', clips: [
      { id: 'cut:1', start: 1, end: 2, minDuration: 0.1 }
    ] },
    { id: 'art:overlay:1', kind: 'art', clips: [
      { id: 'art:1', start: 2, end: 4, minDuration: 0.1 }
    ] },
    { id: 'pip:track:1', kind: 'pip', clips: [
      { id: 'pip:1', start: 5, end: 8, minDuration: 0.1, payload: { width: 0.3 } }
    ] }
  ]
}, { onCommit: (state, reason) => commits.push({ state, reason }) });

store.selectClip('art:1');
const move = timeline.createPointerSession(store, {
  clipId: 'art:1', mode: 'move', startClientX: 100,
  trackWidth: 1200, duration: 12
});
move.update(300);
move.finish();
const moved = store.findClip('art:1');
if (moved.start !== 4 || moved.end !== 6) throw new Error('move failed');

const resize = timeline.createPointerSession(store, {
  clipId: 'pip:1', mode: 'start', startClientX: 0,
  trackWidth: 1200, duration: 12
});
resize.update(200);
resize.finish();
const resized = store.findClip('pip:1');
if (resized.start !== 7 || resized.end !== 8) throw new Error('resize failed');

const boundaryMove = timeline.createPointerSession(store, {
  clipId: 'art:1', mode: 'move', startClientX: 0,
  trackWidth: 1200, duration: 12
});
boundaryMove.update(2400);
boundaryMove.finish({ commit: false });
const bounded = store.findClip('art:1');
if (bounded.start !== 10 || bounded.end !== 12) {
  throw new Error('boundary move changed clip duration');
}

const boundaryResize = timeline.createPointerSession(store, {
  clipId: 'pip:1', mode: 'start', startClientX: 0,
  trackWidth: 1200, duration: 12
});
boundaryResize.update(1200);
boundaryResize.finish({ commit: false });
const minSized = store.findClip('pip:1');
if (minSized.start !== 7.9 || minSized.end !== 8) {
  throw new Error('boundary resize moved the fixed edge');
}

store.patchClipPayload('pip:1', { width: 0.42 }, { commit: true });
if (store.findClip('pip:1').payload.width !== 0.42) throw new Error('payload failed');

const values = new Map();
const storage = {
  setItem: (key, value) => values.set(key, value),
  getItem: (key) => values.get(key) || null
};
if (!timeline.saveDraft(storage, 'project', store.snapshot(), { name: 'draft' })) {
  throw new Error('save failed');
}
const restored = timeline.loadDraft(storage, 'project');
if (restored.metadata.name !== 'draft') throw new Error('metadata failed');
if (restored.timeline.tracks.length !== 3) throw new Error('tracks failed');
if (commits.length !== 3) throw new Error('commit mechanism failed');
console.log(JSON.stringify({ commits: commits.length, selection: store.snapshot().selection }));
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the timeline model unit test.")

    payload = json.loads(result.stdout)
    assert payload["commits"] == 3
    assert payload["selection"]["clipId"] == "pip:1"


def test_douyin_preview_is_inline_only():
    with TestClient(app_module.app) as client:
        page_response = client.get("/")
        removed_page_response = client.get("/douyin-preview")
        removed_script_response = client.get("/douyin-preview.js")
        styles_response = client.get("/styles.css")
        editor_suite_script_response = client.get("/editor-suite.js")
        feedback_script_response = client.get("/ui-feedback.js")

    assert page_response.status_code == 200
    assert removed_page_response.status_code == 404
    assert removed_script_response.status_code == 404
    assert styles_response.status_code == 200
    assert editor_suite_script_response.status_code == 200
    assert feedback_script_response.status_code == 200

    assert 'data-douyin-preview-toggle' in page_response.text
    assert 'id="editorSuiteDouyinChrome"' in page_response.text
    assert 'class="douyin-action-bar"' in page_response.text
    assert 'class="douyin-bottom-nav"' in page_response.text
    assert ".douyin-caption-block {" in styles_response.text
    assert ".douyin-action-bar {" in styles_response.text
    assert ".douyin-top-bar {" in styles_response.text
    assert ".douyin-feed-tabs {" in styles_response.text
    assert ".douyin-status-bar {" not in styles_response.text
    assert 'class="douyin-status-bar"' not in page_response.text
    assert 'class="douyin-content-type"' not in page_response.text
    assert "font-size: clamp(8px, 3.8cqw, 13px)" in styles_response.text
    assert "font-size: clamp(7px, 3.2cqw, 11px)" in styles_response.text
    assert 'class="douyin-action-button is-liked"' in page_response.text
    assert page_response.text.count('class="douyin-action-button') == 4
    assert page_response.text.count('tabindex="-1"') >= 4
    assert 'class="douyin-music-disc"' in page_response.text
    assert "douyin-shoot-same" not in page_response.text
    assert ".douyin-location {" not in styles_response.text
    assert ".douyin-content-type {" not in styles_response.text
    assert "--iphone-screen-width: 440" in styles_response.text
    assert "--iphone-screen-height: 956" in styles_response.text
    assert "--iphone-safe-top: 6.4854%" in styles_response.text
    assert "--iphone-safe-bottom: 3.5565%" in styles_response.text
    assert "--iphone-safe-top-space: 14.0909cqw" in styles_response.text
    assert "--iphone-safe-bottom-space: 7.7273cqw" in styles_response.text
    assert "var(--iphone-safe-top) + var(--douyin-header-content-height)" in (
        styles_response.text
    )
    assert "var(--iphone-safe-bottom) + var(--douyin-tabbar-content-height)" in (
        styles_response.text
    )
    assert "--douyin-video-bottom: var(--douyin-tabbar-height)" in (
        styles_response.text
    )
    assert "aspect-ratio: 440 / 956 !important" in styles_response.text
    assert "padding: var(--iphone-safe-top-space) var(--douyin-side-inset) 0" in (
        styles_response.text
    )
    assert "padding: 0 var(--douyin-side-inset) var(--iphone-safe-bottom-space)" in (
        styles_response.text
    )
    assert "bottom: var(--douyin-content-bottom)" in styles_response.text
    assert "object-fit: contain" in styles_response.text
    douyin_video_rule = styles_response.text.split(
        ".cut-video-stage.is-douyin-preview #cutPreviewVideo {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "top: 0;" in douyin_video_rule
    assert "height: calc(100% - var(--douyin-video-bottom));" in douyin_video_rule
    assert "object-fit: cover;" in douyin_video_rule
    douyin_base_video_rule = styles_response.text.split(
        ".editor-suite-douyin-base-video {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "top: 0;" in douyin_base_video_rule
    assert (
        "height: calc(100% - var(--douyin-video-bottom, 0%));"
        in douyin_base_video_rule
    )
    assert "object-fit: cover;" in douyin_base_video_rule
    assert "const fitScale = douyinPreviewEnabled ? Math.max : Math.min;" in (
        editor_suite_script_response.text
    )
    assert "const scale = fitScale(" in editor_suite_script_response.text
    douyin_overlay_rule = styles_response.text.split(
        ".cut-video-stage.is-douyin-preview .editor-suite-preview-overlay {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "inset: 0 0 var(--douyin-video-bottom);" in douyin_overlay_rule
    douyin_top_bar_rule = styles_response.text.rsplit(
        ".douyin-top-bar {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "background: transparent;" in douyin_top_bar_rule
    assert "backdrop-filter: none;" in douyin_top_bar_rule
    douyin_bottom_nav_rule = styles_response.text.rsplit(
        ".douyin-bottom-nav {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "background: transparent;" in douyin_bottom_nav_rule
    assert ".cut-video-stage.is-douyin-preview .editor-suite-preview-overlay" in (
        styles_response.text
    )
    assert "width: min(100%, 360px) !important" in styles_response.text
    assert ".editor-suite-douyin-base-video" in styles_response.text
    assert "grid-template-rows: minmax(0, 1fr)" in styles_response.text
    assert "container-type: inline-size" in styles_response.text
    assert "--douyin-action-gap: 5.6818cqw" in styles_response.text
    assert "--douyin-action-right: 1.3636%" in styles_response.text
    assert "--douyin-action-top: 48.954%" in styles_response.text
    assert "clamp(20px, 7.7273cqw, 34px)" in styles_response.text
    assert "bottom: 9.728%" in styles_response.text
    assert "clamp(20px, 10cqw, 34px)" in styles_response.text
    assert ".douyin-music-disc {" in styles_response.text
    assert ".douyin-safety-zone" not in styles_response.text
    assert "@keyframes art-character-bounce" in styles_response.text
    assert "prefers-reduced-motion: reduce" in styles_response.text
    assert ".art-style-sample.has-character-effect" in styles_response.text
    assert "animation-fill-mode: forwards" in styles_response.text
    assert ".art-character.is-character-staggered" in styles_response.text
    assert ".template-card-preview.has-character-effect" in styles_response.text
    assert "flex: 0 0 178px" in styles_response.text

    assert 'data-douyin-preview href' not in editor_suite_script_response.text
    assert "setDouyinPreviewLink" not in editor_suite_script_response.text
    assert "setDouyinPreviewAvailable" in editor_suite_script_response.text
    assert "setDouyinPreviewEnabled" in editor_suite_script_response.text
    assert "function updateDouyinBaseVideo" in editor_suite_script_response.text
    assert "has-douyin-edited-base" in editor_suite_script_response.text
    assert "douyinVideoZoom" not in editor_suite_script_response.text
    assert "is-douyin-preview" in editor_suite_script_response.text
    assert "/douyin-preview?job=" not in editor_suite_script_response.text
    assert "repeat(3, minmax(0, 1fr))" in styles_response.text
    assert "is-douyin-preview" in feedback_script_response.text
    assert "stage.parentElement?.querySelector" in feedback_script_response.text
