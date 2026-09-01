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
        "/transcript-follow-scroll.js",
        "/timeline-thumbnail-cache.js",
        "/ui-feedback.js",
        "/timeline-model.js",
        "/editor-pip-model.js",
        "/editor-project-store.js",
        "/editor-media-controller.js",
        "/editor-art-model.js",
        "/editor-art-renderer.js",
        "/editor-preview-compositor.js",
        "/editor-timeline-controller.js",
        "/editor-art-tool.js",
        "/editor-pip-tool.js",
    )
    page_response = responses["/"]
    styles_response = responses["/styles.css"]
    script_response = responses["/app.js"]
    follow_scroll_response = responses["/transcript-follow-scroll.js"]
    thumbnail_cache_response = responses["/timeline-thumbnail-cache.js"]
    feedback_script_response = responses["/ui-feedback.js"]
    timeline_script_response = responses["/timeline-model.js"]
    pip_model_response = responses["/editor-pip-model.js"]
    project_store_script_response = responses["/editor-project-store.js"]
    media_controller_response = responses["/editor-media-controller.js"]
    art_model_response = responses["/editor-art-model.js"]
    art_renderer_response = responses["/editor-art-renderer.js"]
    preview_compositor_response = responses["/editor-preview-compositor.js"]
    timeline_controller_response = responses["/editor-timeline-controller.js"]
    art_tool_response = responses["/editor-art-tool.js"]
    pip_tool_response = responses["/editor-pip-tool.js"]

    assert page_response.status_code == 200
    assert styles_response.status_code == 200
    assert "/app.js?v=20260831-07" in page_response.text
    assert "/styles.css?v=20260901-05" in page_response.text
    assert "/transcript-follow-scroll.js?v=20260831-01" in page_response.text
    assert "/timeline-thumbnail-cache.js?v=20260828-01" in page_response.text
    assert "/ui-feedback.js?v=20260807-03" in page_response.text
    assert "/timeline-model.js?v=20260810-01" in page_response.text
    assert "/editor-pip-model.js?v=20260819-01" in page_response.text
    assert "/editor-project-store.js?v=20260831-01" in page_response.text
    assert "/editor-media-controller.js?v=20260831-01" in page_response.text
    assert "/editor-art-model.js?v=20260827-01" in page_response.text
    assert "/editor-art-renderer.js?v=20260819-01" in page_response.text
    assert "/editor-preview-compositor.js?v=20260820-01" in page_response.text
    assert "/editor-timeline-controller.js?v=20260831-01" in page_response.text
    assert "/editor-art-tool.js?v=20260901-01" in page_response.text
    assert "/editor-pip-tool.js?v=20260825-01" in page_response.text
    assert "/editor-suite.js?v=20260831-01" in page_response.text
    assert timeline_script_response.status_code == 200
    assert timeline_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert "function createStore" in timeline_script_response.text
    assert "function createPointerSession" in timeline_script_response.text
    assert project_store_script_response.status_code == 200
    assert project_store_script_response.headers["cache-control"] == "no-store, max-age=0"
    assert "function createStore" in project_store_script_response.text
    assert 'data-art-field="textAlign"' not in art_tool_response.text
    assert 'data-art-field="lineSpacing"' not in art_tool_response.text
    for response in (
        media_controller_response,
        art_model_response,
        art_renderer_response,
        preview_compositor_response,
        timeline_controller_response,
        art_tool_response,
        pip_model_response,
        pip_tool_response,
    ):
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store, max-age=0"
    assert "root.EditorMedia = api" in media_controller_response.text
    assert "root.EditorArtModel = api" in art_model_response.text
    assert "root.EditorArtRenderer = api" in art_renderer_response.text
    assert "root.EditorPreview = api" in preview_compositor_response.text
    assert "root.EditorTimelineController = api" in timeline_controller_response.text
    assert "root.ArtTool = api" in art_tool_response.text
    assert "root.EditorPipModel = api" in pip_model_response.text
    assert "root.PipTool = api" in pip_tool_response.text
    timeline_controller_source = timeline_controller_response.text.replace("\r\n", "\n")
    assert 'if (keyboardTarget) {\n      keyboardTarget.addEventListener?.("keydown", keyDown);' in (
        timeline_controller_source
    )
    assert '} else {\n      layer?.addEventListener("keydown", keyDown);' in (
        timeline_controller_source
    )
    assert page_response.text.index("/timeline-model.js") < page_response.text.index(
        "/editor-pip-model.js"
    )
    assert page_response.text.index("/editor-pip-model.js") < page_response.text.index(
        "/editor-project-store.js"
    )
    assert page_response.text.index("/editor-project-store.js") < page_response.text.index(
        "/editor-media-controller.js"
    )
    assert page_response.text.index("/editor-media-controller.js") < page_response.text.index(
        "/editor-art-model.js"
    )
    assert page_response.text.index("/editor-art-model.js") < page_response.text.index(
        "/editor-art-renderer.js"
    )
    assert page_response.text.index("/editor-art-renderer.js") < page_response.text.index(
        "/editor-preview-compositor.js"
    )
    assert page_response.text.index("/editor-preview-compositor.js") < page_response.text.index(
        "/editor-timeline-controller.js"
    )
    assert page_response.text.index("/editor-timeline-controller.js") < page_response.text.index(
        "/editor-art-tool.js"
    )
    assert page_response.text.index("/editor-art-tool.js") < page_response.text.index(
        "/editor-pip-tool.js"
    )
    assert page_response.text.index("/editor-pip-tool.js") < page_response.text.index(
        "/editor-suite.js"
    )
    assert page_response.text.index("/transcript-follow-scroll.js") < (
        page_response.text.index("/timeline-thumbnail-cache.js")
    )
    assert page_response.text.index("/timeline-thumbnail-cache.js") < (
        page_response.text.index("/app.js")
    )

    assert follow_scroll_response.status_code == 200
    assert follow_scroll_response.headers["cache-control"] == "no-store, max-age=0"
    assert "root.TranscriptFollowScroll = api" in follow_scroll_response.text
    assert "function createController" in follow_scroll_response.text
    assert "function getTranscriptFollowScrollTarget" in follow_scroll_response.text
    assert "function createPlaceholder" in follow_scroll_response.text
    assert "tailRemainder" in follow_scroll_response.text

    assert thumbnail_cache_response.status_code == 200
    assert thumbnail_cache_response.headers["cache-control"] == "no-store, max-age=0"
    assert "window.TimelineThumbnailCache = Object.freeze" in (
        thumbnail_cache_response.text
    )
    assert "function createStore(options = {})" in thumbnail_cache_response.text
    assert "function load(signature)" in thumbnail_cache_response.text
    assert "function save(record)" in thumbnail_cache_response.text
    assert "function prune({ preserveSignature" in thumbnail_cache_response.text
    assert "blob instanceof BlobType" in thumbnail_cache_response.text
    assert "DEFAULT_MAX_RECORDS = 24" in thumbnail_cache_response.text
    assert "64 * 1024 * 1024" in thumbnail_cache_response.text
    assert "30 * 24 * 60 * 60 * 1000" in thumbnail_cache_response.text

    assert feedback_script_response.status_code == 200
    assert 'className = "app-dialog-shell"' in feedback_script_response.text
    assert "window.appConfirm" in feedback_script_response.text
    assert "window.appGeneration" in feedback_script_response.text
    assert "generation-overlay" in styles_response.text
    assert "window.appGeneration?.show" in script_response.text
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
    assert "editor-suite:move-finish" not in editor_suite_script_response.text
    assert "editor-suite:timeline-action" not in editor_suite_script_response.text
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
    assert "embedded" not in editor_suite_script_response.text
    assert 'window.history[method]' in editor_suite_script_response.text
    assert "postMessage" not in editor_suite_script_response.text
    assert 'addEventListener("message"' not in editor_suite_script_response.text
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
    assert "return frame?.composition || null" in editor_suite_script_response.text
    assert '/compose`' in editor_suite_script_response.text
    assert "data-editor-suite-download" in editor_suite_script_response.text
    assert "syncGenerationButton" in editor_suite_script_response.text
    assert "workspaceSourceTime" not in editor_suite_script_response.text
    assert "window.EditorMedia.createController(previewVideo)" in editor_suite_script_response.text
    assert "window.EditorPreview.createCompositor" in editor_suite_script_response.text
    assert "window.EditorTimelineController.createController" in editor_suite_script_response.text
    assert "function selectCurrentProjectFrame" in editor_suite_script_response.text
    assert "window.EditorProjectStore.selectEditorFrame(" in editor_suite_script_response.text
    assert "select-art-timeline" not in editor_suite_script_response.text
    assert "adjust-art-timeline" not in editor_suite_script_response.text
    assert "ensureToolFrame" not in editor_suite_script_response.text
    assert "syncMirroredPlayback" not in editor_suite_script_response.text
    assert "frameEntries" not in editor_suite_script_response.text
    assert "mediaController?.subscribeFrame" in editor_suite_script_response.text
    assert "previewCompositor?.syncTime();" not in editor_suite_script_response.text
    assert "function scheduleFrameSync" not in editor_suite_script_response.text
    assert 'inspectorHost.classList.toggle("is-background", isCut)' in (
        editor_suite_script_response.text
    )
    assert "renderedPreviewState" not in editor_suite_script_response.text
    assert "function normalizedToolHref" not in editor_suite_script_response.text
    assert '["art", "pip"]' in editor_suite_script_response.text
    assert "overlayHtml" not in editor_suite_script_response.text
    assert "timelineHtml" not in editor_suite_script_response.text
    assert 'activeTool !== "cut" && Boolean(state)' not in (
        editor_suite_script_response.text
    )
    assert 'previewVideo?.addEventListener(eventName, scheduleFrameSync)' not in editor_suite_script_response.text
    assert "editor-tool-embedded" not in styles_response.text
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
    assert "generationPayload" not in editor_suite_script_response.text
    assert 'type: "editor-suite:cut-draft"' not in editor_suite_script_response.text
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
    assert 'id="cutFrameTimelineClips"' in page_response.text
    assert 'id="cutFrameTimelineRanges"' in page_response.text
    assert 'id="cutTimelineSplitButton"' in page_response.text
    assert 'icon="ph:scissors-bold"' in page_response.text
    assert 'aria-label="在当前播放头位置分割视频"' in page_response.text
    assert 'id="cutTimelineDeleteClipButton"' in page_response.text
    assert 'id="cutTimelineRestoreClipButton"' in page_response.text
    assert 'id="timelineRangeConfirmActions"' not in page_response.text
    assert 'id="cancelTimelineRangeButton"' not in page_response.text
    assert 'id="confirmTimelineRangeButton"' not in page_response.text
    assert "松开后弹窗确认" not in page_response.text
    assert "语音附近确认后会对齐安全边界，可微调并再次点击确认删除" in page_response.text
    assert "选区保持精确范围" not in page_response.text
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
    assert "source=original&tool=pip" in script_response.text
    assert "/original-video`" in script_response.text
    assert "buildCutTimelineThumbnails" in script_response.text
    assert "function splitCutTimelineAtPlayhead" in script_response.text
    assert "function deriveCutSplitClips" in script_response.text
    assert "function deleteSelectedCutSplitClip" in script_response.text
    assert "function restoreSelectedCutSplitClip" in script_response.text
    assert 'boundaryMode: "split_exact"' in script_response.text
    assert "splitClipKey: currentClip.key" in script_response.text
    assert 'stageCutHistoryOperation("分割视频片段")' in script_response.text
    assert script_response.text.count("splitPoints: cutSplitPoints.map") >= 4
    assert "structureOnly: true" in script_response.text
    assert "CUT_STRUCTURE_CHANGED" in editor_suite_script_response.text
    assert "renderCutTimelineTextSegments" in script_response.text
    assert "cutTimelinePixelsPerSecond" in script_response.text
    assert "CUT_TIMELINE_TEXT_LINES" in script_response.text
    assert "Math.ceil(total / majorStep) + 1" in script_response.text
    thumbnail_count_start = script_response.text.index(
        "function desiredCutTimelineThumbnailCount"
    )
    thumbnail_count_end = script_response.text.index(
        "function cutTimelineAbortError", thumbnail_count_start
    )
    thumbnail_count_source = script_response.text[
        thumbnail_count_start:thumbnail_count_end
    ]
    assert "currentVideoDuration" in thumbnail_count_source
    assert "editedCutTimelineDuration" not in thumbnail_count_source
    assert ".cut-timeline-text-segment {" in styles_response.text
    assert ".cut-frame-timeline .frame-timeline-thumb img {" in styles_response.text
    assert ".cut-frame-timeline-actions {" in styles_response.text
    assert ".cut-timeline-action-button {" in styles_response.text
    assert ".cut-frame-timeline-clips {" in styles_response.text
    assert ".cut-timeline-split-clip {" in styles_response.text
    assert "cut-timeline-deleted-marker" not in styles_response.text
    assert "cut-timeline-deleted-marker" not in script_response.text
    assert "min-width: 44px" in styles_response.text
    assert "min-height: 44px" in styles_response.text
    assert "background-repeat: repeat-x" in styles_response.text
    assert "beginCutTimelineSelection" in script_response.text
    assert "beginTimelineRangeAdjustment" in script_response.text
    assert "skipSelectedRangeDuringPlayback" in script_response.text
    frame_skip = "if (skipSelectedRangeDuringPlayback(sourceTime) !== null)"
    frame_render = "updateCutPlaybackVisualFrame(sourceTime, { followTranscript: true })"
    assert frame_skip in script_response.text
    assert script_response.text.index(frame_skip) < script_response.text.index(
        frame_render
    )
    assert "currentEditableSegmentBoundaries" in script_response.text
    assert "editableBoundaryBefore" in script_response.text
    assert "editableBoundaryAfter" in script_response.text
    assert "boundary?.deleteRight" in script_response.text
    assert "boundary?.deleteLeft" in script_response.text
    assert "segment?.mediaStart" in script_response.text
    assert "segment?.mediaEnd" in script_response.text
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
    assert "window.TranscriptFollowScroll.createController({" in script_response.text
    assert "layer: transcriptNowPlayingLayer" in script_response.text
    assert "function transcriptDisplayItems" in script_response.text
    assert 'id="transcriptNowPlayingLayer"' in page_response.text
    assert 'aria-label="播放中的文案"' in page_response.text
    assert "function getTranscriptFollowScrollTarget" not in script_response.text
    assert "function scrollActiveTranscriptSegmentToAnchor" not in script_response.text
    assert "function followActiveTranscriptSegment" not in script_response.text
    assert "updateActiveTranscriptSegment(sourceCurrent" in script_response.text
    assert ".segment-item.is-playback-active" in styles_response.text
    assert ".transcript-now-playing-layer" in styles_response.text
    assert ".segment-follow-placeholder" in styles_response.text
    assert ".segment-item.is-playback-active.is-follow-animating" not in (
        styles_response.text
    )
    assert "var(--surface)" in styles_response.text
    assert (
        'segmentList.addEventListener("click", handleTranscriptDisplayClick)'
        in script_response.text
    )
    assert "transcriptNowPlayingLayer.addEventListener(" in script_response.text
    assert 'id="cutDraftSaveStatus"' in page_response.text
    assert "function restorePersistedCutDraft" in script_response.text
    assert "function applyPersistedCutDraftAlignment" in script_response.text
    assert "function reconcileCurrentCutHistorySnapshot" in script_response.text
    assert "function scheduleCutDraftSave" in script_response.text
    assert "async function flushCutDraftSave" in script_response.text
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
    assert "window.EditorSuite?.setCutDraft({" in script_response.text
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

    generate_start = script_response.text.index("async function generateCut()")
    generate_end = script_response.text.index("function startUpload", generate_start)
    generate_source = script_response.text[generate_start:generate_end]
    assert generate_source.index("await flushCutDraftSave()") < generate_source.index(
        "const ranges = getMergedSelection()"
    ) < generate_source.index("/cuts`")

    compose_start = editor_suite_script_response.text.index(
        "async function generateCurrentPreview()"
    )
    compose_end = editor_suite_script_response.text.index(
        "async function cancelComposition()", compose_start
    )
    compose_source = editor_suite_script_response.text[compose_start:compose_end]
    assert compose_source.index("await cutTimelineAdapter.flushDraft()") < (
        compose_source.index("const frame = selectCurrentProjectFrame()")
    ) < compose_source.index("/compose`")


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
    assert "确认后语音附近会对齐安全剪辑点" in script_response.text
    keyboard_start = script_response.text.index(
        "function adjustTimelineRangeWithKeyboard"
    )
    keyboard_end = script_response.text.index(
        "function resetCutPlaybackCursors", keyboard_start
    )
    keyboard_source = script_response.text[keyboard_start:keyboard_end]
    assert "const semanticRange = alignManualRangeToTranscript(range);" in keyboard_source
    assert "Object.assign(range, semanticRange);" in keyboard_source
    assert "function applyCutTimelineTextLayoutRanges" in script_response.text
    assert "item.dataset.layoutStart" in script_response.text
    assert "item.dataset.layoutEnd" in script_response.text
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
    assert "const CUT_TIMELINE_CANCEL_HIT_WIDTH = 44;" in script_response.text
    assert "const CUT_TIMELINE_CANCEL_GAP = 4;" in script_response.text
    assert "rightCenter + cancelHitHalf <= trackWidth" in script_response.text
    assert ".cut-timeline-range-cancel {" in styles_response.text
    assert ".cut-timeline-range-cancel iconify-icon {" in styles_response.text
    assert ".cut-timeline-delete-range.is-narrow {" in styles_response.text
    assert (
        ".cut-timeline-delete-range.is-narrow .cut-timeline-range-cancel {"
        in styles_response.text
    )
    assert "top: 50%;" in styles_response.text
    assert "transform: translate(-50%, -50%);" in styles_response.text
    assert "inset: -12px;" in styles_response.text
    assert "--cut-timeline-range-cancel-left" in script_response.text
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
    assert "const historyBefore = cloneCutHistorySnapshot();" in adjustment_script
    assert "before: historyBefore" in adjustment_script
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
    assert "hasPendingRange || !hasMergedSelection" in script_response.text
    assert 'typeof options.hasMergedSelection === "boolean"' in script_response.text
    assert "已调整待确认区间" in script_response.text
    assert "const CUT_TIMELINE_MANUAL_MIN_RANGE = CUT_TIMELINE_STEP;" in (
        script_response.text
    )
    assert "const CUT_TIMELINE_SPLIT_MIN_RANGE = 0.1;" in script_response.text
    assert "CUT_TIMELINE_MIN_RANGE" not in script_response.text
    split_validation = script_response.text[
        script_response.text.index("function validateCutTimelineSplit"):
        script_response.text.index("function getEditedAudioQuietRanges")
    ]
    split_normalization = script_response.text[
        script_response.text.index("function normalizeCutSplitPoints"):
        script_response.text.index("function cutSplitClipKey")
    ]
    assert "CUT_TIMELINE_SPLIT_MIN_RANGE" in split_validation
    assert "CUT_TIMELINE_MANUAL_MIN_RANGE" not in split_validation
    assert "CUT_TIMELINE_SPLIT_MIN_RANGE" in split_normalization
    assert "CUT_TIMELINE_MANUAL_MIN_RANGE" not in split_normalization
    assert "CUT_TIMELINE_MANUAL_MIN_RANGE" in selection_script
    assert "CUT_TIMELINE_MANUAL_MIN_RANGE" in keyboard_source
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
    assert "grid-template-columns: 22px 26px minmax(0, 1fr) 22px" in (
        styles_response.text
    )
    assert "min-height: 32px" in styles_response.text
    assert ".segment-time {" in styles_response.text
    assert "font-size: 10.8px" in styles_response.text
    assert ".segment-text {" in styles_response.text
    assert "font-size: 12px" in styles_response.text
    assert "width: 22px" in styles_response.text
    assert "height: 22px" in styles_response.text
    assert "text-shadow: 0 0 6px" in styles_response.text
    assert "transform: translateY(0.5px)" in styles_response.text
    assert ".segment-play-button {" in styles_response.text
    assert ".segment-play-button:focus-visible" in styles_response.text
    assert "@media (max-width: 480px)" in styles_response.text
    assert "grid-template-columns: 22px minmax(0, 1fr) 22px" in (
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
    assert "canvas.toBlob(" in script_response.text
    assert '"image/jpeg"' in script_response.text
    assert "0.72" in script_response.text
    assert "URL.createObjectURL(frame.blob)" in script_response.text
    assert "URL.revokeObjectURL(frame.url)" in script_response.text
    assert "cutTimelineThumbnailStore?.close()" in script_response.text

    assert "--editor-timeline-track-height: 112px" in styles_response.text
    assert "--editor-timeline-ruler-height: 28px" in styles_response.text
    assert "--editor-timeline-track-height: var(--timeline-layer-track-height-compact)" in (
        styles_response.text
    )
    assert "--cut-timeline-text-height: var(--timeline-row-height-compact)" in (
        styles_response.text
    )
    assert ".cut-frame-timeline .frame-timeline-tick-label" in styles_response.text
    assert "top: -1px" in styles_response.text
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
    render_segments_start = script_response.text.index(
        "function buildCutSegmentDisplayItems()"
    )
    render_segments_end = script_response.text.index(
        "function noSpeechKindLabel", render_segments_start
    )
    assert "const deletedRanges = getCommittedTimelineSemanticDeleteRanges();" in (
        script_response.text[render_segments_start:render_segments_end]
    )


def test_cut_timeline_text_layout_uses_edited_gaps_without_mutating_source_ranges():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    helper_start = app_source.index("function applyCutTimelineTextLayoutRanges(")
    helper_end = app_source.index(
        "function renderCutTimelineTextSegments(", helper_start
    )
    helper_source = app_source[helper_start:helper_end]
    script = f"""
const CUT_SPEECH_BOUNDARY_EPSILON = 0.002;
const CUT_TIMELINE_TEXT_GAP_COVERAGE_MAX = 1.5;
{helper_source}
const parts = [
  {{ sourceStart: 10, sourceEnd: 10.3, editedStart: 0.2, editedEnd: 0.5 }},
  {{ sourceStart: 20, sourceEnd: 20.3, editedStart: 0.6, editedEnd: 0.9 }},
  {{ sourceStart: 30, sourceEnd: 30.3, editedStart: 3.625, editedEnd: 3.9 }},
];
const before = JSON.stringify(parts);
const layouts = applyCutTimelineTextLayoutRanges(parts);
const exactThreshold = applyCutTimelineTextLayoutRanges([
  {{ sourceStart: 100, sourceEnd: 100.1, editedStart: 1000, editedEnd: 1000.1 }},
  {{ sourceStart: 110, sourceEnd: 110.1, editedStart: 1001.6, editedEnd: 1001.7 }},
]);
const overThreshold = applyCutTimelineTextLayoutRanges([
  {{ sourceStart: 200, sourceEnd: 200.1, editedStart: 2000, editedEnd: 2000.1 }},
  {{ sourceStart: 210, sourceEnd: 210.1, editedStart: 2001.601, editedEnd: 2001.7 }},
]);
const tinyPositiveGap = applyCutTimelineTextLayoutRanges([
  {{ sourceStart: 300, sourceEnd: 300.1, editedStart: 3000, editedEnd: 3000.1 }},
  {{ sourceStart: 310, sourceEnd: 310.1, editedStart: 3000.101, editedEnd: 3000.2 }},
]);
process.stdout.write(JSON.stringify({{
  before,
  after: JSON.stringify(parts),
  layouts,
  exactThreshold,
  overThreshold,
  tinyPositiveGap,
}}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["after"] == payload["before"]
    assert [part["layoutStart"] for part in payload["layouts"]] == pytest.approx(
        [0.2, 0.6, 3.625]
    )
    assert [part["layoutEnd"] for part in payload["layouts"]] == pytest.approx(
        [0.6, 0.9, 3.9]
    )
    assert [
        (part["sourceStart"], part["sourceEnd"]) for part in payload["layouts"]
    ] == [(10, 10.3), (20, 20.3), (30, 30.3)]
    assert payload["exactThreshold"][0]["layoutEnd"] == pytest.approx(1001.6)
    assert payload["overThreshold"][0]["layoutEnd"] == pytest.approx(2000.1)
    assert payload["tinyPositiveGap"][0]["layoutEnd"] == pytest.approx(3000.101)


def test_cut_commit_render_plan_preserves_replace_across_mid_phase_cancel():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    plan_start = app_source.index("function createCutCommitRenderPlan()")
    plan_end = app_source.index(
        "function updateOriginalSourceActionsVisibility", plan_start
    )
    requeue_start = app_source.index("function requeueUnfinishedCutCommitRender")
    requeue_end = app_source.index(
        "function cancelPendingCutCommitEffects", requeue_start
    )
    helpers = app_source[plan_start:plan_end] + app_source[
        requeue_start:requeue_end
    ]
    script = f"""
{helpers}
let cutCommitRenderPlan = createCutCommitRenderPlan();
requestCutCommitRender({{ transcript: "replace", timelineText: "replace" }});
const active = {{
  phase: "store",
  renderPlan: consumeCutCommitRenderPlan(),
}};
requestCutCommitRender({{ transcript: "reconcile", timelineText: "reconcile" }});
requeueUnfinishedCutCommitRender(active);
const afterCancel = consumeCutCommitRenderPlan();
requestCutCommitRender({{ transcript: "reconcile", timelineText: "reconcile" }});
requestCutCommitRender({{ transcript: "replace", timelineText: "replace" }});
requestCutCommitRender({{ transcript: "reconcile", timelineText: "reconcile" }});
const sameFrame = consumeCutCommitRenderPlan();
requeueUnfinishedCutCommitRender({{
  phase: "timelineAux",
  renderPlan: {{ transcript: "replace", timelineText: "replace" }},
}});
const afterTimeline = consumeCutCommitRenderPlan();
process.stdout.write(JSON.stringify({{ afterCancel, afterTimeline, sameFrame }}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "afterCancel": {
            "transcript": "reconcile",
            "timelineText": "replace",
        },
        "afterTimeline": {
            "transcript": "skip",
            "timelineText": "skip",
        },
        "sameFrame": {
            "transcript": "replace",
            "timelineText": "replace",
        },
    }


def test_cut_segment_update_dispatches_reconcile_and_replace_modes():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    update_start = app_source.index("function updateCutSegmentText(")
    update_end = app_source.index(
        "function updateImmediateCutSelectionFeedback", update_start
    )
    update_source = app_source[update_start:update_end]
    script = f"""
const calls = [];
const reconcileCutSegments = () => calls.push("reconcile");
const renderCutSegments = () => calls.push("replace");
{update_source}
updateCutSegmentText("reconcile");
updateCutSegmentText("replace");
updateCutSegmentText();
process.stdout.write(JSON.stringify(calls));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == ["reconcile", "replace", "replace"]


def test_cut_commit_effect_second_frame_is_cancellable_and_flushes_synchronously():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    cancel_start = app_source.index("function cancelPendingCutCommitEffects()")
    schedule_start = app_source.index("function scheduleCutCommitEffects()")
    schedule_end = app_source.index("function resetCutCommitScheduler", schedule_start)
    flush_start = app_source.index("function flushPendingCutCommitEffects()")
    flush_end = app_source.index("function updateSelectionSummary", flush_start)
    source = (
        app_source[cancel_start:schedule_start]
        + app_source[schedule_start:schedule_end]
        + app_source[flush_start:flush_end]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
let cutCommitEffectsFrameId = null;
let cutCommitEffectsTimer = null;
let cutCommitActiveEffects = null;
let cutCommitPreviewEffect = null;
let runCount = 0;
let nextFrameId = 1;
const frames = new Map();
const timers = new Map();
const cancelledFrames = [];
const window = {{
  requestAnimationFrame(callback) {{
    const id = nextFrameId++;
    frames.set(id, callback);
    return id;
  }},
  cancelAnimationFrame(id) {{
    cancelledFrames.push(id);
    frames.delete(id);
  }},
  setTimeout(callback) {{ timers.set(1, callback); return 1; }},
  clearTimeout(id) {{ timers.delete(id); }},
}};
const requeueUnfinishedCutCommitRender = () => undefined;
const runCutCommitEffects = () => {{ runCount += 1; }};
const runCutCommitStoreEffects = () => {{ runCount += 10; }};
const runCutCommitTimelineEffects = () => {{ runCount += 100; }};
const runCutCommitTimelineAuxEffects = () => {{ runCount += 1000; }};
${{source}}
return {{
  scheduleCutCommitEffects,
  cancelPendingCutCommitEffects,
  flushPendingCutCommitEffects,
  runFirstFrame() {{
    const [id, callback] = frames.entries().next().value;
    frames.delete(id);
    callback();
  }},
  state() {{
    return {{
      cancelledFrames: [...cancelledFrames],
      frameCount: frames.size,
      frameId: cutCommitEffectsFrameId,
      runCount,
      timerCount: timers.size,
    }};
  }},
}};
`)();
functions.scheduleCutCommitEffects();
functions.runFirstFrame();
const afterFirstFrame = functions.state();
functions.cancelPendingCutCommitEffects();
const afterCancel = functions.state();
functions.scheduleCutCommitEffects();
const flushed = functions.flushPendingCutCommitEffects();
const afterFlush = functions.state();
process.stdout.write(JSON.stringify({{ afterFirstFrame, afterCancel, flushed, afterFlush }}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["afterFirstFrame"] == {
        "cancelledFrames": [],
        "frameCount": 1,
        "frameId": 2,
        "runCount": 0,
        "timerCount": 0,
    }
    assert payload["afterCancel"] == {
        "cancelledFrames": [2],
        "frameCount": 0,
        "frameId": None,
        "runCount": 0,
        "timerCount": 0,
    }
    assert payload["flushed"] is True
    assert payload["afterFlush"] == {
        "cancelledFrames": [2, 3],
        "frameCount": 0,
        "frameId": None,
        "runCount": 1,
        "timerCount": 0,
    }


def test_top_level_art_and_pip_tools_are_the_only_editor_runtime():
    root = Path(__file__).resolve().parents[2]
    web = root / "web"
    page = (web / "index.html").read_text(encoding="utf-8")
    suite = (web / "editor-suite.js").read_text(encoding="utf-8")
    project_store = (web / "editor-project-store.js").read_text(encoding="utf-8")
    tool = (web / "editor-art-tool.js").read_text(encoding="utf-8")
    pip_tool = (web / "editor-pip-tool.js").read_text(encoding="utf-8")
    styles = (web / "styles.css").read_text(encoding="utf-8")
    compositor = (root / "web" / "editor-preview-compositor.js").read_text(
        encoding="utf-8"
    )

    for legacy_resource in (
        "art-text.html",
        "art-text.js",
        "picture-in-picture.html",
        "picture-in-picture.js",
    ):
        assert not (web / legacy_resource).exists()

    assert 'id="editorArtPanelRoot"' in page
    assert 'title="艺术字设置"' not in page
    assert "window.ArtTool.mount(artPanelRoot, createArtToolServices())" in suite
    assert 'id="editorPipPanelRoot"' in page
    assert 'title="画中画设置"' not in page
    assert "window.PipTool.mount(pipPanelRoot, createPipToolServices())" in suite
    assert ".editor-pip-tool {\n  width: 100%;" in styles
    assert "overflow-x: hidden;\n  overflow-y: auto;\n  padding: 8px;" in styles
    assert (
        ".editor-pip-tool-panel {\n"
        "  --pip-readable-small-font: 15px;\n"
        "  --pip-readable-regular-font: 16px;\n"
        "  --pip-readable-strong-font: 17px;\n"
        "  width: 100%;\n"
        "  max-width: none;\n"
        "  box-sizing: border-box;\n"
        "  zoom: 0.6;\n"
        "  font-family:\n"
        '    "Microsoft YaHei UI",\n'
        '    "PingFang SC",\n'
        '    "Noto Sans CJK SC",\n'
        '    "Source Han Sans SC",\n'
        "    system-ui,\n"
        "    sans-serif;\n"
        "  font-weight: 500;\n"
        "  font-size: var(--pip-readable-regular-font);\n"
        "  text-rendering: optimizeLegibility;\n"
        "}"
    ) in styles
    assert (
        ".editor-pip-tool-panel :is(h1, h2, h3, h4, h5, h6, strong, legend),\n"
        ".editor-pip-tool-panel .step-label {\n"
        "  font-weight: 700;\n"
        "}"
    ) in styles
    assert (
        ".editor-pip-tool-panel :is(small, time) {\n"
        "  font-weight: 500;\n"
        "  font-size: var(--pip-readable-small-font);\n"
        "  line-height: 1.3;\n"
        "}"
    ) in styles
    assert (
        ".editor-pip-tool-panel .pip-segment-option > span {\n"
        "  grid-template-columns: 64px minmax(0, 1fr);\n"
        "  gap: 12px;\n"
        "}"
    ) in styles
    assert (
        '.editor-pip-tool input[type="radio"] {\n'
        "  width: 26px;\n"
        "  height: 26px;\n"
        "  min-width: 26px;\n"
        "  min-height: 26px;"
    ) in styles
    assert "@media (max-width: 720px)" in styles
    assert ".editor-pip-tool {\n    padding: 6px;\n  }" in styles
    assert "restoreEditorDraft(projectSnapshot())" in suite
    assert "PROJECT_DRAFT_RESTORED" in suite
    assert "editor-suite:project-draft:" in suite
    assert "schemaVersion: 2" in suite
    assert "pip: {" in suite
    assert "initialTemplateSelection: initialArtTemplateSelection" in suite
    assert "function parseRequestedArtTemplate(search)" in suite
    assert "const commit = projectStore.dispatch({" in suite
    assert "if (currentJob && commit.accepted)" in suite
    assert "renderJobState(currentJob, { hydrateProject: false })" in suite

    assert "root.ArtTool = api" in tool
    assert "function mount(host, services)" in tool
    assert "activate, deactivate, destroy, render" in tool
    assert "sessionStorage" not in tool
    assert "localStorage" not in tool
    assert "postMessage" not in tool
    assert 'addEventListener("message"' not in tool
    assert "createStore(" not in tool
    assert "createElement(\"video\")" not in tool
    assert "generateCurrentPreview" in tool
    assert "data-art-full-track" in tool
    assert "data-art-ai-request" in tool
    assert "一键添加视频文案" in tool
    assert "按剪后词级时间自动生成全文艺术字，默认使用“热血立体”。" in tool
    assert tool.count('role="tab" data-art-tab=') == 3
    assert 'data-art-tab="transcript"' not in tool
    assert 'data-art-panel="transcript"' not in tool
    for tab, panel in (
        ("selection", "selection"),
        ("settings", "settings"),
        ("ai", "ai"),
    ):
        assert (
            f'id="editor-art-{tab}-tab" role="tab" data-art-tab="{tab}" '
            f'aria-controls="editor-art-{panel}-panel"'
        ) in tool
        assert (
            f'id="editor-art-{panel}-panel" data-art-panel="{panel}" '
            f'role="tabpanel" aria-labelledby="editor-art-{tab}-tab"'
        ) in tool
    selection_panel = tool[
        tool.index('data-art-panel="selection"') :
        tool.index('data-art-panel="settings"')
    ]
    settings_panel = tool[
        tool.index('data-art-panel="settings"') :
        tool.index('data-art-panel="ai"')
    ]
    for selection_control in (
        "data-art-list",
        "data-art-add-text",
        "data-art-add",
        "data-art-full-track",
        "data-art-transcript-section",
        "data-art-selection-error",
    ):
        assert selection_control in selection_panel
        assert selection_control not in settings_panel
    assert "data-art-detail-title" in settings_panel
    assert "data-art-detail-help" in settings_panel
    assert "data-art-controls-legend" in settings_panel
    assert "data-art-settings-error" in settings_panel
    assert 'data-art-template-trigger aria-haspopup="listbox"' in settings_panel
    assert 'data-art-templates role="listbox"' in settings_panel
    assert 'role="radiogroup"' not in settings_panel
    assert "template.description" not in tool
    assert "点击应用到当前艺术字" not in tool
    assert "点击应用到整轨文案艺术字" not in tool
    assert settings_panel.count("data-art-manual-only") == 7
    for duplicate_transcript_control in (
        "data-art-transcript-text",
        "data-art-transcript-save",
        "data-art-transcript-list",
        "data-art-add-selected",
    ):
        assert duplicate_transcript_control not in settings_panel
    assert "function saveTranscript(" not in tool
    assert "function addSelectedSegments(" not in tool
    assert "consumeInitialTemplateSelection();" in tool
    assert "pendingTemplateSelection" in tool
    assert "preferredTemplateSettings" in tool

    assert "root.PipTool = api" in pip_tool
    assert "function mount(host, services)" in pip_tool
    assert "sessionStorage" not in pip_tool
    assert "localStorage" not in pip_tool
    assert "postMessage" not in pip_tool
    assert "EditorTimeline.createStore" not in pip_tool
    assert 'size.type = "number"' in pip_tool
    assert "size.max" not in pip_tool
    assert "root.EditorPipModel?.MIN_WIDTH || 0.15" in compositor
    assert "window.EditorPipModel?.MIN_WIDTH || 0.15" in suite

    assert "root.EditorArtRenderer?.sanitizeOverlay" in compositor
    assert "root.EditorArtRenderer?.renderCharacters" in compositor
    for marker in (
        "iframe",
        "postMessage",
        'addEventListener("message"',
        "embedded",
        "frameEntries",
        "toolBridgeRevisions",
        "desiredToolUrls",
        "legacyTimelineDocument",
        "toolStates",
        "timelineHtml",
        "overlayHtml",
        "generationPayload",
        "__EDITOR_PROJECT_STORE_ENABLED__",
        "__EDITOR_ART_PANEL_ENABLED__",
        "__EDITOR_PIP_PANEL_ENABLED__",
    ):
        assert marker not in suite

    for bridge_projection in (
        "selectCutDraftMessage",
        "selectToolState",
        "selectIframeProjection",
        'type: "editor-suite:cut-draft"',
        'changeKind: "tool-state"',
        'changeKind: "project-projection"',
    ):
        assert bridge_projection not in project_store


def test_legacy_editor_pages_redirect_to_top_level_tools():
    with TestClient(app_module.app, follow_redirects=False) as client:
        art = client.get(
            "/art-text?job=abc&source=edited&embedded=1&tool=pip"
            "&template=impact&templateColor=%23ffffff"
        )
        pip = client.get(
            "/picture-in-picture?job=abc&source=original&embedded=1&tool=art"
        )
        art_api = client.get(
            "/api/transcriptions/00000000-0000-0000-0000-000000000000/art-text-video"
        )
        pip_api = client.get(
            "/api/transcriptions/00000000-0000-0000-0000-000000000000/"
            "picture-in-picture-video"
        )

    assert art.status_code == 307
    assert art.headers["location"] == (
        "/?job=abc&source=edited&template=impact&templateColor=%23ffffff&tool=art"
    )
    assert pip.status_code == 307
    assert pip.headers["location"] == "/?job=abc&source=original&tool=pip"
    assert art_api.status_code == 404
    assert pip_api.status_code == 404
    assert "location" not in art_api.headers
    assert "location" not in pip_api.headers


def test_removed_legacy_editor_resources_are_not_served():
    with TestClient(app_module.app, follow_redirects=False) as client:
        art_script = client.get("/art-text.js")
        pip_script = client.get("/picture-in-picture.js")
        art_page = client.get("/art-text")
        pip_page = client.get("/picture-in-picture")

    assert art_script.status_code == 404
    assert pip_script.status_code == 404
    assert art_page.status_code == 307
    assert art_page.headers["location"] == "/?tool=art"
    assert pip_page.status_code == 307
    assert pip_page.headers["location"] == "/?tool=pip"


def test_single_page_tool_links_target_the_top_level_document():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    suite_source = (root / "web" / "editor-suite.js").read_text(encoding="utf-8")
    template_source = (root / "web" / "art-template-library.js").read_text(
        encoding="utf-8"
    )

    assert "/art-text?job=" not in app_source
    assert "/picture-in-picture?job=" not in app_source
    assert "source=original&tool=art" in app_source
    assert "source=original&tool=pip" in app_source
    assert "source=${artSource}&tool=art" in suite_source
    assert "source=${pipSource}&tool=pip" in suite_source
    assert 'new URL("/", window.location.origin)' in template_source
    assert 'destination.searchParams.set("tool", "art")' in template_source

def test_art_template_library_frontend_contracts():
    responses = _fetch_frontend_assets(
        "/fonts",
        "/art-template-library.js",
        "/api/art-templates",
        "/editor-art-tool.js",
    )
    template_page_response = responses["/fonts"]
    template_script_response = responses["/art-template-library.js"]
    template_api_response = responses["/api/art-templates"]
    art_tool_response = responses["/editor-art-tool.js"]

    assert template_page_response.status_code == 200
    assert "/styles.css?v=20260901-05" in template_page_response.text
    assert "/art-template-library.js?v=20260819-01" in template_page_response.text
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
    assert "characterLayout" in art_tool_response.text
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
    assert "consumeInitialTemplateSelection" in art_tool_response.text
    assert "normalizedTemplateSettings" in art_tool_response.text
    assert 'new URL("/", window.location.origin)' in template_script_response.text
    assert 'destination.searchParams.set("tool", "art")' in template_script_response.text
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
    assert "/styles.css?v=20260901-05" in font_page_response.text
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
const CUT_TIMELINE_MIN_RANGE = 0.1;
const selectedRanges = new Map();
const selectedNoSpeechRanges = new Map();
let timelineDeleteRanges = [];
let cutSplitPoints = [];
let selectedSplitClipKey = "";
let nextTimelineRangeId = 1;
let selectedTimelineRangeId = null;
let transcriptCharacterUnitsCache = null;
let timelineRangeInProgress = false;
let timelineRangeConfirmationOpen = false;
let cutHistoryLastState = null;
let cutHistoryReplaying = false;
const cloneCutHistorySnapshot = (snapshot) => snapshot;
const cutHistoryTimingSignature = (snapshot) => JSON.stringify(snapshot);
const refreshCutStructureState = () => {{}};
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
    render_start = app_source.index("function buildCutSegmentDisplayItems")
    render_end = app_source.index("function updateCutSegmentText", render_start)
    click_start = app_source.index("function handleTranscriptDisplayClick")
    click_end = app_source.index("\n}\n\nfor (const eventName", click_start) + 2
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
const selectedNoSpeechRanges = new Map();
const currentSuggestions = [];
const currentEditableSegments = [];
const currentNoSpeechSuggestions = [];
let activeTranscriptSegmentIndex = -1;
let activeTranscriptSegmentKey = "";
let activeTranscriptItem = null;
const transcriptFollowScrollController = {{ reset() {{}} }};
const renderedItems = [];
const historyActions = [];
const seekTimes = [];
let selectionUpdateCount = 0;
let cutControlsLocked = false;
const window = {{}};
const rangeKey = (start, end) =>
  Number(start).toFixed(3) + "-" + Number(end).toFixed(3);
const getSuggestionRanges = (suggestion) => suggestion.ranges || [];
const getCommittedTimelineDeleteRanges = () => [];
const getCommittedTimelineSemanticDeleteRanges = () => [];
const getNoSpeechRange = (suggestion) => suggestion;
const noSpeechKindLabel = () => "quiet";
const noSpeechAudioLabel = () => "silent";
const stageCutHistoryOperation = (label) => historyActions.push(label);
const updateSelectionSummary = () => {{ selectionUpdateCount += 1; }};
const seekCutPreview = (time) => seekTimes.push(time);
const scheduleCutPreviewEffect = (effect) => effect?.();
const renderTextSegmentItem = (run) => ({{
  dataset: {{}},
  type: "text",
  text: run.text,
}});
const renderNoSpeechSegmentItem = (suggestion) => ({{
  dataset: {{}},
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
    handleTranscriptDisplayClick({{ target: new HTMLButtonElement(rangeKeys) }});
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
    assert [
        (run["characterStart"], run["characterEnd"])
        for run in payload["split"]
    ] == [(0, 1), (1, 2), (2, 3)]
    assert payload["split"][1]["suggestionRangeKeys"] == ["1.000-2.000"]
    assert [run["text"] for run in payload["timelineDeleted"]] == ["甲", "乙"]
    assert all(run["kind"] == "deleted" for run in payload["timelineDeleted"])
    assert payload["remainingAfterRestore"] == []
    assert payload["historyActions"] == ["恢复已删除文字"]
    assert payload["seekTimes"] == [0]
    assert payload["selectionUpdateCount"] == 1
    rendered_items = [
        {key: value for key, value in item.items() if key != "dataset"}
        for item in payload["renderedItems"]
    ]
    assert rendered_items == [
        {"type": "text", "text": "文案"},
        {"type": "no-speech", "id": "quiet"},
    ]


def test_frontend_segment_dialog_targets_visible_fragment_and_scopes_operations():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    dialog_start = app_source.index("function getSegmentSelectionOffsets")
    dialog_end = app_source.index("function broadcastTranscriptUpdated", dialog_start)
    source = app_source[dialog_start:dialog_end]
    script = f"""
const source = {json.dumps(source)};
const requests = [];
const classList = () => ({{ add() {{}}, remove() {{}}, toggle() {{}} }});
const button = () => ({{ disabled: false }});
const status = () => ({{ textContent: "", dataset: {{}} }});
const functions = new Function(
  "source",
  "requests",
  "button",
  "status",
  "classList",
  `
let activeSegmentEditTarget = null;
let segmentOperationInFlight = false;
let cutControlsLocked = false;
let currentJobId = "fragment-job";
let currentEditableSegments = [
  {{ id: 0, text: "重复删除重复保留" }},
  {{ id: 1, text: "下段内容" }},
];
const getCommittedTimelineSemanticDeleteRanges = () => [];
const buildSegmentTextRuns = (_segment, _deletedRanges, segmentIndex) =>
  segmentIndex === 0
    ? [{{
        kind: "edit",
        text: "重复保留",
        characterStart: 4,
        characterEnd: 8,
        start: 0.35,
        end: 0.65,
        semanticStart: 0.35,
        semanticEnd: 0.65,
      }}]
    : [];
const segmentEditText = {{
  value: "",
  selectionStart: 0,
  selectionEnd: 0,
  setSelectionRange(start, end) {{
    this.selectionStart = start;
    this.selectionEnd = end;
  }},
  focus() {{}},
}};
const splitSegmentButton = button();
const mergeSegmentUpButton = button();
const mergeSegmentDownButton = button();
const saveSegmentTextButton = button();
const segmentEditClose = button();
const segmentEditSelectionStatus = status();
const segmentStructureStatus = status();
const segmentEditEyebrow = status();
const segmentEditTime = status();
const segmentEditDialog = {{
  open: false,
  classList: classList(),
  showModal() {{ this.open = true; }},
  close() {{ this.open = false; }},
}};
const window = {{
  requestAnimationFrame(callback) {{ callback(); }},
  EditorSuite: {{ beginProjectEffect() {{ return {{}}; }} }},
}};
const formatPreciseTime = value => Number(value).toFixed(3);
const getLiveEditedSegmentTiming = segment => ({{
  start: Number(segment.start) - 0.3,
  end: Number(segment.end) - 0.3,
}});
const setSegmentStructureStatus = (message, tone) => {{
  segmentStructureStatus.textContent = message;
  segmentStructureStatus.dataset.tone = tone;
}};
const fetch = async (_url, options) => {{
  requests.push(JSON.parse(options.body));
  return {{
    ok: false,
    async json() {{ return {{ detail: "模拟请求结束" }}; }},
  }};
}};
${{source}}
return {{
  openSegmentEditDialog,
  resolveSegmentEditTarget,
  applyEditableSegmentOperation,
  saveSegmentText,
  controls: {{
    segmentEditDialog,
    segmentEditEyebrow,
    segmentEditTime,
    segmentEditText,
    mergeSegmentUpButton,
    mergeSegmentDownButton,
  }},
}};
`)(source, requests, button, status, classList);

const item = {{ dataset: {{
  segmentIndex: "0",
  segmentCharacterStart: "4",
  segmentCharacterEnd: "8",
  displayStart: "0.35",
  displayEnd: "0.65",
  semanticStart: "0.35",
  semanticEnd: "0.65",
  displayText: "重复保留",
}} }};
functions.openSegmentEditDialog(item);
const opened = {{
  open: functions.controls.segmentEditDialog.open,
  eyebrow: functions.controls.segmentEditEyebrow.textContent,
  time: functions.controls.segmentEditTime.textContent,
  text: functions.controls.segmentEditText.value,
  mergeUpDisabled: functions.controls.mergeSegmentUpButton.disabled,
  mergeDownDisabled: functions.controls.mergeSegmentDownButton.disabled,
}};

functions.controls.segmentEditText.setSelectionRange(2, 4);
await functions.applyEditableSegmentOperation("split");
await functions.applyEditableSegmentOperation("merge_down");
functions.controls.segmentEditText.value = "重复改留";
await functions.saveSegmentText();

const staleTarget = functions.resolveSegmentEditTarget({{ dataset: {{
  ...item.dataset,
  displayText: "重复删除",
}} }});
const staleTimeTarget = functions.resolveSegmentEditTarget({{ dataset: {{
  ...item.dataset,
  displayStart: "0.36",
}} }});
console.log(JSON.stringify({{
  opened,
  requests,
  staleRejected: staleTarget === null,
  staleTimeRejected: staleTimeTarget === null,
  usesAmbiguousIndexOf: source.includes("indexOf(displayText)"),
}}));
"""

    try:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the segment dialog test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert payload["opened"] == {
        "open": True,
        "eyebrow": "段落 01",
        "time": "0.050 — 0.350",
        "text": "重复保留",
        "mergeUpDisabled": True,
        "mergeDownDisabled": False,
    }
    assert payload["requests"] == [
        {
            "segmentIndex": 0,
            "action": "split",
            "selectionStart": 6,
            "selectionEnd": 8,
        },
        {
            "segmentIndex": 0,
            "action": "merge_down",
            "selectionStart": 4,
            "selectionEnd": 8,
        },
        {
            "segmentIndex": 0,
            "action": "text",
            "text": "重复改留",
            "selectionStart": 4,
            "selectionEnd": 8,
        },
    ]
    assert payload["staleRejected"] is True
    assert payload["staleTimeRejected"] is True
    assert payload["usesAmbiguousIndexOf"] is False


def test_frontend_suggestion_presentation_uses_semantic_original_ranges():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    run_start = app_source.index("function selectedTextRangeKeysAtTime")
    run_end = app_source.index("function renderSegmentTextRun", run_start)
    source = app_source[run_start:run_end]
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const selectedRanges = new Map();
const currentSuggestions = [];
const rangeKey = (start, end) =>
  Number(start).toFixed(3) + "-" + Number(end).toFixed(3);
const getSuggestionRanges = (suggestion) => suggestion.ranges || [];
const getSegmentTokens = (segment) => segment.words || [];
${{source}}
return {{ selectedRanges, currentSuggestions, buildSegmentTextRuns }};
`)();

functions.selectedRanges.set("first", {{
  start: 1.7,
  end: 3,
  originalStart: 2,
  originalEnd: 3,
}});
functions.currentSuggestions.push({{ ranges: [{{
  start: 1.7,
  end: 3,
  originalStart: 2,
  originalEnd: 3,
}}] }});
const physicalStartCrossesPerson = functions.buildSegmentTextRuns({{
  words: [
    {{ text: "而是你身边所有", start: 0, end: 1.8 }},
    {{ text: "人", start: 1.8, end: 2 }},
    {{ text: "一起给", start: 2, end: 3 }},
  ],
}}, []);

functions.selectedRanges.clear();
functions.currentSuggestions.length = 0;
functions.selectedRanges.set("second", {{
  start: 0,
  end: 1.7,
  originalStart: 0,
  originalEnd: 1,
}});
functions.currentSuggestions.push({{ ranges: [{{
  start: 0,
  end: 1.7,
  originalStart: 0,
  originalEnd: 1,
}}] }});
const physicalEndCrossesNiShen = functions.buildSegmentTextRuns({{
  words: [
    {{ text: "删除内容", start: 0, end: 1 }},
    {{ text: "你", start: 1, end: 1.3 }},
    {{ text: "身", start: 1.3, end: 1.6 }},
    {{ text: "边", start: 1.6, end: 2 }},
  ],
}}, []);

functions.selectedRanges.clear();
functions.currentSuggestions.length = 0;
functions.currentSuggestions.push({{ ranges: [{{ start: 1, end: 1.6 }}] }});
const legacyPhysicalFallback = functions.buildSegmentTextRuns({{
  words: [
    {{ text: "前", start: 0, end: 1 }},
    {{ text: "你", start: 1, end: 1.3 }},
    {{ text: "身", start: 1.3, end: 1.6 }},
    {{ text: "边", start: 1.6, end: 2 }},
  ],
}}, []);

console.log(JSON.stringify({{
  physicalStartCrossesPerson,
  physicalEndCrossesNiShen,
  legacyPhysicalFallback,
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
        pytest.skip("Node.js is required for the semantic presentation test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert [item["text"] for item in payload["physicalStartCrossesPerson"]] == [
        "而是你身边所有人",
        "一起给",
    ]
    assert [item["kind"] for item in payload["physicalStartCrossesPerson"]] == [
        "edit",
        "restore",
    ]
    assert [item["text"] for item in payload["physicalEndCrossesNiShen"]] == [
        "删除内容",
        "你身边",
    ]
    assert [item["kind"] for item in payload["physicalEndCrossesNiShen"]] == [
        "restore",
        "edit",
    ]
    assert [item["text"] for item in payload["legacyPhysicalFallback"]] == [
        "前",
        "你身",
        "边",
    ]


def test_playback_frame_skips_deleted_audio_before_visual_update() -> None:
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    start = app_source.index("function resetCutPlaybackCursors")
    end = app_source.index("function setupCutPreviewControls", start)
    source = app_source[start:end]
    script = f"""
const source = {json.dumps(source)};
const events = [];
const functions = new Function("events", `
let transcriptPlaybackCursor = 0;
let transcriptPlaybackActiveCursor = 0;
let transcriptPlaybackLastTime = 0;
let cutTimelineTextPlaybackFloorCursor = 0;
let cutTimelineTextPlaybackCursor = 0;
let cutTimelineTextPlaybackLastTime = 0;
const cutPreviewVideo = {{ paused: false, currentTime: 0.5 }};
const transcriptPreviewRange = null;
const CUT_SPEECH_BOUNDARY_EPSILON = 0.001;
const getMergedSelection = () => [{{ start: 0.5, end: 0.8 }}];
const clamp = (value, minimum, maximum) =>
  Math.min(maximum, Math.max(minimum, value));
const cutTimelineDuration = () => 2;
const cutMediaController = () => ({{
  seekSource(value, settings) {{
    events.push("seek:" + value.toFixed(1) + ":" + settings.sync);
  }},
}});
const updateCutTimelineStatus = () => events.push("status");
const formatCutRange = () => "range";
const updateCutPlaybackVisualFrame = () => events.push("visual");
${{source}}
return {{ handleCutPlaybackMediaFrame }};
`)(events);
const result = functions.handleCutPlaybackMediaFrame(0.5);
console.log(JSON.stringify({{ result, events }}));
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
        pytest.skip("Node.js is required for the playback frame test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert payload["result"] == {"skipped": True}
    assert payload["events"] == ["seek:0.8:false", "status"]


def test_split_into_three_projects_neutral_and_directional_timeline_boundaries() -> None:
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    start = app_source.index("function editableBoundaryBefore")
    end = app_source.index("function selectedTextRangeKeysAtTime", start)
    source = app_source[start:end]
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const CUT_SPEECH_BOUNDARY_EPSILON = 0.001;
const selectedRanges = new Map();
const currentEditableSegmentBoundaries = [
  {{ leftEditableSegmentId: 0, rightEditableSegmentId: 1, neutral: 0.31 }},
  {{ leftEditableSegmentId: 1, rightEditableSegmentId: 2, neutral: 0.68 }},
];
const currentEditableSegments = [
  {{ id: 0, start: 0, end: 0.33, mediaStart: 0, mediaEnd: 0.31 }},
  {{ id: 1, start: 0.33, end: 0.67, mediaStart: 0.31, mediaEnd: 0.68 }},
  {{ id: 2, start: 0.67, end: 1, mediaStart: 0.68, mediaEnd: 1 }},
];
${{source}}
return {{
  neutralBounds: currentEditableSegments.map(editableSegmentDisplayBounds),
  deleteMiddleBounds: (() => {{
    selectedRanges.set("middle", {{
      start: 0.30,
      end: 0.69,
      originalStart: 0.33,
      originalEnd: 0.67,
    }});
    return currentEditableSegments.map(editableSegmentDisplayBounds);
  }})(),
}};
`)();
console.log(JSON.stringify(functions));
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
        pytest.skip("Node.js is required for the editable boundary test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert [(item["start"], item["end"]) for item in payload["neutralBounds"]] == [
        (0, 0.31),
        (0.31, 0.68),
        (0.68, 1),
    ]
    assert [
        (item["start"], item["end"])
        for item in payload["deleteMiddleBounds"]
    ] == [
        (0, 0.30),
        (0.30, 0.69),
        (0.69, 1),
    ]
    assert "editableSegmentDisplayBounds(\n        editableSegment" in app_source


def test_frontend_removed_rows_use_monotonic_edited_timestamps():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    timing_start = app_source.index("function getLiveEditedSegmentTiming")
    timing_end = app_source.index("function setSegmentStructureStatus", timing_start)
    mapping_start = app_source.index("function sourceTimeToEditedTime")
    mapping_end = app_source.index("function editedTimeToSourceTime", mapping_start)
    source = "\n".join(
        [
            app_source[timing_start:timing_end],
            app_source[mapping_start:mapping_end],
        ]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const spans = [
  {{ sourceStart: 0, sourceEnd: 18, editedStart: 0, editedEnd: 18 }},
  {{ sourceStart: 29, sourceEnd: 33, editedStart: 18, editedEnd: 22 }},
  {{ sourceStart: 35, sourceEnd: 40, editedStart: 22, editedEnd: 27 }},
];
const clamp = (value, minimum, maximum) =>
  Math.min(maximum, Math.max(minimum, value));
const cutTimelineDuration = () => 40;
const editedCutTimelineDuration = (items) => items.at(-1)?.editedEnd || 0;
const formatTime = (seconds) => Number(seconds).toFixed(3);
const formatPreciseTime = formatTime;
const makeItem = (start, end) => {{
  const time = {{
    textContent: "",
    attributes: {{}},
    setAttribute(name, value) {{ this.attributes[name] = value; }},
  }};
  const classes = {{}};
  return {{
    dataset: {{ displayStart: String(start), displayEnd: String(end) }},
    matches() {{ return true; }},
    querySelector(selector) {{ return selector === ".segment-time" ? time : null; }},
    classList: {{ toggle(name, value) {{ classes[name] = value; }} }},
    classes,
    time,
  }};
}};
const items = [
  makeItem(17, 18),
  makeItem(28, 29),
  makeItem(29, 33),
  makeItem(33, 35),
  makeItem(34, 35),
  makeItem(35, 40),
];
const getEditedTimelineSpans = () => spans;
const transcriptDisplayItems = () => items;
const rebuildTranscriptPlaybackEntries = () => {{}};
const updateActiveTranscriptSegment = () => {{}};
${{source}}
return {{
  run() {{
    updateCutSegmentTimestamps();
    return items.map((item) => ({{
      displayStart: Number(item.dataset.displayStart),
      displayEnd: Number(item.dataset.displayEnd),
      label: item.time.attributes["aria-label"],
      removed: item.classes["is-removed-from-timeline"],
      time: Number(item.time.textContent),
    }}));
  }},
}};
`)();
console.log(JSON.stringify(functions.run()));
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
        pytest.skip("Node.js is required for the edited timestamp test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert [
        (item["displayStart"], item["displayEnd"])
        for item in payload
    ] == [(17, 18), (28, 29), (29, 33), (33, 35), (34, 35), (35, 40)]
    assert [item["time"] for item in payload] == [17, 18, 18, 22, 22, 22]
    assert [item["removed"] for item in payload] == [
        False,
        True,
        False,
        True,
        True,
        False,
    ]
    assert all(
        left["time"] <= right["time"]
        for left, right in zip(payload, payload[1:])
    )
    assert "剪辑后位于 18.000 删除点" in payload[1]["label"]
    assert "原片从 28.000 到 29.000，已删除" in payload[1]["label"]


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
let transcriptCharacterUnitsCache = null;
let mergedCutSelectionCache = null;
let semanticCutDeleteRangesCache = null;
${{source}}
return {{
  selectedRanges,
  getMergedSelection,
  resetSelectionCaches() {{
    mergedCutSelectionCache = null;
    semanticCutDeleteRangesCache = null;
  }},
}};
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
functions.resetSelectionCaches();
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


def test_frontend_applies_text_and_timeline_alignment_atomically():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    timeline_start = app_source.index("function getCommittedTimelineDeleteRanges")
    timeline_end = app_source.index(
        "function protectRecognizedSpeechFromQuietRanges", timeline_start
    )
    serialization_start = app_source.index("function serializableCutDraftRange")
    serialization_end = app_source.index(
        "function normalizeRestoredTextDeleteRange", serialization_start
    )
    payload_start = app_source.index("function buildPersistedCutDraftPayload")
    payload_end = app_source.index("function restorePersistedCutDraft", payload_start)
    apply_start = app_source.index("function applyPersistedCutDraftAlignment")
    apply_end = app_source.index("async function persistCutDraft", apply_start)
    source = "\n".join(
        [
            app_source[timeline_start:timeline_end],
            app_source[serialization_start:serialization_end],
            app_source[payload_start:payload_end],
            app_source[apply_start:apply_end],
        ]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const selectedRanges = new Map([["text-a", {{
  start: 0.0, end: 0.35, originalStart: 0.0, originalEnd: 0.35,
  text: "得", adjacentSilenceBefore: 0, adjacentSilenceAfter: 0,
}}]]);
const selectedNoSpeechRanges = new Map([["quiet-a", {{
  id: "quiet-a", start: 0.6, end: 0.7,
}}]]);
let timelineDeleteRanges = [{{
  id: 1, key: "timeline-1", start: 0.35, end: 0.5,
  originalStart: 0.35, originalEnd: 0.42,
  boundaryMode: "split_exact", splitClipKey: "split-clip:source-start:split-a",
}}, {{
  id: 2, key: "timeline-pending", start: 0.75, end: 0.79,
  originalStart: 0.75, originalEnd: 0.79,
}}];
let cutSplitPoints = [{{ key: "split-a", sourceTime: 0.8 }}];
let cutSplitClipsCache = {{ stale: true }};
let timelineRangeInProgress = true;
let selectedTimelineRangeId = 2;
let cutDraftRevision = 3;
let automaticNoSpeechInitialized = true;
let cutDraftLastSignature = "";
let cutHistoryReplaying = false;
let selectionUpdates = 0;
let historyReconciles = 0;
const rangeKey = (start, end) =>
  Number(start).toFixed(3) + ":" + Number(end).toFixed(3);
const CUT_TIMELINE_SPLIT_MIN_RANGE = 0.001;
const cutTimelineDuration = () => 1;
const clamp = (value, minimum, maximum) =>
  Math.min(maximum, Math.max(minimum, value));
const updateSelectionSummary = () => {{ selectionUpdates += 1; }};
const reconcileCurrentCutHistorySnapshot = () => {{ historyReconciles += 1; }};
${{source}}
return {{
  expectedSignature: () => cutDraftSemanticSignature(buildPersistedCutDraftPayload()),
  applyPersistedCutDraftAlignment,
  snapshot: () => ({{
    text: [...selectedRanges.entries()],
    noSpeech: [...selectedNoSpeechRanges.entries()],
    timeline: timelineDeleteRanges,
    splitPoints: cutSplitPoints,
    splitCache: cutSplitClipsCache,
    selectionUpdates,
    historyReconciles,
  }}),
}};
`)();
const expected = functions.expectedSignature();
const before = functions.snapshot();
const rejected = functions.applyPersistedCutDraftAlignment({{
  textRanges: [{{
    key: "text-a", start: 0, end: 0.4,
    originalStart: 0, originalEnd: 0.36, text: "得",
    adjacentSilenceBefore: 0, adjacentSilenceAfter: 0.04,
  }}],
  noSpeechRanges: [{{ key: "quiet-a", start: 0.601, end: 0.699 }}],
  timelineRanges: [{{
    key: "wrong-key", start: 0.4, end: 0.5,
    originalStart: 0.351, originalEnd: 0.421,
    boundaryMode: "split_exact", splitClipKey: "split-clip:source-start:split-a",
  }}],
  splitPoints: [{{ key: "split-a", sourceTime: 0.801 }}],
  automaticNoSpeechInitialized: true,
}}, expected);
const afterRejected = functions.snapshot();
const normalizedDraft = {{
  textRanges: [{{
    key: "text-a", start: 0, end: 0.4,
    originalStart: 0, originalEnd: 0.36, text: "得",
    adjacentSilenceBefore: 0, adjacentSilenceAfter: 0.04,
  }}],
  noSpeechRanges: [{{ key: "quiet-a", start: 0.601, end: 0.699 }}],
  timelineRanges: [{{
    key: "timeline-1", start: 0.4, end: 0.5,
    originalStart: 0.351, originalEnd: 0.421,
    boundaryMode: "split_exact", splitClipKey: "split-clip:source-start:split-a",
  }}],
  splitPoints: [{{ key: "split-a", sourceTime: 0.801 }}],
  automaticNoSpeechInitialized: true,
}};
const applied = functions.applyPersistedCutDraftAlignment(normalizedDraft, expected);
const afterApplied = functions.snapshot();
const rejectedChangedText = functions.applyPersistedCutDraftAlignment({{
  textRanges: [{{
    key: "text-a", start: 0, end: 0.4,
    originalStart: 0, originalEnd: 0.36, text: "你",
  }}],
  noSpeechRanges: [{{ key: "quiet-a", start: 0.601, end: 0.699 }}],
  timelineRanges: [{{
    key: "timeline-1", start: 0.4, end: 0.5,
    originalStart: 0.351, originalEnd: 0.421,
    boundaryMode: "split_exact", splitClipKey: "split-clip:source-start:split-a",
  }}],
  splitPoints: [{{ key: "split-a", sourceTime: 0.801 }}],
  automaticNoSpeechInitialized: true,
}}, functions.expectedSignature());
const rejectedUnknownBoundaryMode = functions.applyPersistedCutDraftAlignment({{
  textRanges: [{{
    key: "text-a", start: 0, end: 0.4,
    originalStart: 0, originalEnd: 0.36, text: "得",
    adjacentSilenceBefore: 0, adjacentSilenceAfter: 0.04,
  }}],
  noSpeechRanges: [{{ key: "quiet-a", start: 0.601, end: 0.699 }}],
  timelineRanges: [{{
    key: "timeline-1", start: 0.4, end: 0.5,
    originalStart: 0.351, originalEnd: 0.421,
    boundaryMode: "unknown",
    splitClipKey: "split-clip:source-start:split-a",
  }}],
  splitPoints: [{{ key: "split-a", sourceTime: 0.801 }}],
  automaticNoSpeechInitialized: true,
}}, functions.expectedSignature());
const rejectedDuplicateKey = functions.applyPersistedCutDraftAlignment({{
  ...normalizedDraft,
  textRanges: [
    ...normalizedDraft.textRanges,
    {{ ...normalizedDraft.textRanges[0] }},
  ],
}}, functions.expectedSignature());
const rejectedExtraKey = functions.applyPersistedCutDraftAlignment({{
  ...normalizedDraft,
  noSpeechRanges: [
    ...normalizedDraft.noSpeechRanges,
    {{ key: "quiet-extra", start: 0.82, end: 0.84 }},
  ],
}}, functions.expectedSignature());
const rejectedMissingKey = functions.applyPersistedCutDraftAlignment({{
  ...normalizedDraft,
  splitPoints: [],
}}, functions.expectedSignature());
const rejectedSplitOwnership = functions.applyPersistedCutDraftAlignment({{
  ...normalizedDraft,
  timelineRanges: [{{
    ...normalizedDraft.timelineRanges[0],
    splitClipKey: "split-clip:split-a:source-end",
  }}],
}}, functions.expectedSignature());
console.log(JSON.stringify({{
  rejected,
  unchangedAfterRejected: JSON.stringify(before) === JSON.stringify(afterRejected),
  applied,
  afterApplied,
  rejectedChangedText,
  unchangedAfterChangedText:
    JSON.stringify(afterApplied) === JSON.stringify(functions.snapshot()),
  rejectedUnknownBoundaryMode,
  unchangedAfterUnknownBoundaryMode:
    JSON.stringify(afterApplied) === JSON.stringify(functions.snapshot()),
  rejectedDuplicateKey,
  rejectedExtraKey,
  rejectedMissingKey,
  rejectedSplitOwnership,
  unchangedAfterStructuralRejections:
    JSON.stringify(afterApplied) === JSON.stringify(functions.snapshot()),
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
        pytest.skip("Node.js is required for the frontend cut-draft unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert payload["rejected"] is False
    assert payload["unchangedAfterRejected"] is True
    assert payload["applied"] is True
    assert payload["afterApplied"]["text"][0][1]["end"] == 0.4
    assert payload["afterApplied"]["text"][0][1]["originalEnd"] == 0.36
    assert payload["afterApplied"]["text"][0][1]["adjacentSilenceAfter"] == 0.04
    assert payload["afterApplied"]["noSpeech"][0][1] == {
        "id": "quiet-a",
        "start": 0.601,
        "end": 0.699,
    }
    assert payload["afterApplied"]["timeline"][0] == {
        "id": 1,
        "key": "timeline-1",
        "start": 0.4,
        "end": 0.5,
        "originalStart": 0.351,
        "originalEnd": 0.421,
        "boundaryMode": "split_exact",
        "splitClipKey": "split-clip:source-start:split-a",
    }
    assert payload["afterApplied"]["timeline"][1] == {
        "id": 2,
        "key": "timeline-pending",
        "start": 0.75,
        "end": 0.79,
        "originalStart": 0.75,
        "originalEnd": 0.79,
    }
    assert payload["afterApplied"]["splitPoints"] == [
        {"key": "split-a", "sourceTime": 0.801}
    ]
    assert payload["afterApplied"]["splitCache"] is None
    assert payload["afterApplied"]["selectionUpdates"] == 1
    assert payload["afterApplied"]["historyReconciles"] == 1
    assert payload["rejectedChangedText"] is False
    assert payload["unchangedAfterChangedText"] is True
    assert payload["rejectedUnknownBoundaryMode"] is False
    assert payload["unchangedAfterUnknownBoundaryMode"] is True
    assert payload["rejectedDuplicateKey"] is False
    assert payload["rejectedExtraKey"] is False
    assert payload["rejectedMissingKey"] is False
    assert payload["rejectedSplitOwnership"] is False
    assert payload["unchangedAfterStructuralRejections"] is True


def test_frontend_normalized_cut_draft_ack_undo_redo_and_invalid_rebase():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    timeline_start = app_source.index("function getCommittedTimelineDeleteRanges")
    timeline_end = app_source.index(
        "function protectRecognizedSpeechFromQuietRanges", timeline_start
    )
    serialization_start = app_source.index("function serializableCutDraftRange")
    serialization_end = app_source.index(
        "function normalizeRestoredTextDeleteRange", serialization_start
    )
    payload_start = app_source.index("function buildPersistedCutDraftPayload")
    payload_end = app_source.index("function restorePersistedCutDraft", payload_start)
    apply_start = app_source.index("function applyPersistedCutDraftAlignment")
    apply_end = app_source.index("function scheduleCutDraftSave", apply_start)
    source = "\n".join(
        [
            app_source[timeline_start:timeline_end],
            app_source[serialization_start:serialization_end],
            app_source[payload_start:payload_end],
            app_source[apply_start:apply_end],
        ]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const selectedRanges = new Map();
const selectedNoSpeechRanges = new Map();
let timelineDeleteRanges = [{{
  id: 1,
  key: "timeline-1",
  start: 0.3504,
  end: 0.4204,
  originalStart: 0.3504,
  originalEnd: 0.4204,
}}];
let cutSplitPoints = [];
let cutSplitClipsCache = null;
let timelineRangeInProgress = false;
let selectedTimelineRangeId = null;
let currentJobId = "job-1";
let cutDraftRevision = 1;
let automaticNoSpeechInitialized = true;
let cutDraftReady = true;
let cutDraftSaveInFlight = null;
let cutDraftDesired = null;
let cutDraftAcknowledged = null;
let cutDraftFailedSignature = "";
let cutDraftLastSignature = "";
let cutDraftNeedsServerSync = true;
let cutDraftSaveGeneration = 1;
let cutDraftSaveQueue = Promise.resolve();
let cutDraftSaveTimer = null;
let cutCommitExternallySynced = false;
let cutHistoryReplaying = false;
let serverRevision = 1;
let responseRevisionOverride = null;
let returnInvalidStructure = false;
let historyReconciles = 0;
const requests = [];
const localRevisions = [];
const statuses = [];
const retainedProjectionChecks = [];
const CUT_TIMELINE_SPLIT_MIN_RANGE = 0.001;
const cutTimelineDuration = () => 1;
const clamp = (value, minimum, maximum) =>
  Math.min(maximum, Math.max(minimum, value));
const rangeKey = (start, end) =>
  Number(start).toFixed(3) + ":" + Number(end).toFixed(3);
const window = {{
  clearTimeout,
  queueMicrotask,
}};
const updateSelectionSummary = () => undefined;
const reconcileCurrentCutHistorySnapshot = () => {{ historyReconciles += 1; }};
const applyServerRetainedProjection = (transcript, options) => {{
  const currentSignature = cutDraftSemanticSignature(
    buildPersistedCutDraftPayload(),
  );
  const accepted = options.jobId === currentJobId
    && options.signature === currentSignature
    && options.revision === cutDraftRevision;
  retainedProjectionChecks.push({{
    accepted,
    text: transcript?.text || "",
  }});
  return accepted;
}};
const saveLocalCutDraft = draft => {{
  localRevisions.push(Number(draft?.revision) || 0);
}};
const syncEditorSuiteCutDraftState = () => undefined;
const renderCutTimelineTextSegments = () => undefined;
const setCutDraftSaveStatus = (message, tone) => {{
  statuses.push({{ message, tone }});
}};
const fetch = async (_url, options) => {{
  const request = JSON.parse(options.body);
  requests.push(request);
  const responseRevision = responseRevisionOverride ?? serverRevision + 1;
  responseRevisionOverride = null;
  if (Number.isInteger(responseRevision) && responseRevision > serverRevision) {{
    serverRevision = responseRevision;
  }}
  const timelineRanges = request.timelineRanges.map(range => ({{
    ...range,
    start: Number(Math.max(
      0,
      Math.round(range.originalStart * 1000) / 1000 - 0.03,
    ).toFixed(3)),
    end: Number(Math.min(
      1,
      Math.round(range.originalEnd * 1000) / 1000 + 0.03,
    ).toFixed(3)),
    originalStart: Math.round(range.originalStart * 1000) / 1000,
    originalEnd: Math.round(range.originalEnd * 1000) / 1000,
  }}));
  const responseTimelineRanges = returnInvalidStructure ? [] : timelineRanges;
  returnInvalidStructure = false;
  return {{
    ok: true,
    status: 200,
    json: async () => ({{
      retainedTranscript: {{ text: "normalized", segments: [] }},
      cutDraft: {{
        schemaVersion: 1,
        revision: responseRevision,
        automaticNoSpeechInitialized:
          request.automaticNoSpeechInitialized === true,
        textRanges: request.textRanges,
        noSpeechRanges: request.noSpeechRanges,
        timelineRanges: responseTimelineRanges,
        splitPoints: request.splitPoints,
      }},
    }}),
  }};
}};
${{source}}
return {{
  async run() {{
    const snapshots = [];
    captureDesiredCutDraft();
    responseRevisionOverride = 1.5;
    await persistCutDraft();
    snapshots.push({{
      phase: "invalid-revision",
      revision: cutDraftRevision,
      acknowledged: isCutDraftAcknowledged(
        cutDraftSemanticSignature(buildPersistedCutDraftPayload()),
      ),
    }});

    cutDraftFailedSignature = "";
    await persistCutDraft();
    snapshots.push({{
      phase: "normalized",
      revision: cutDraftRevision,
      range: {{ ...timelineDeleteRanges[0] }},
      acknowledged: isCutDraftAcknowledged(
        cutDraftSemanticSignature(buildPersistedCutDraftPayload()),
      ),
    }});

    timelineDeleteRanges = [];
    captureDesiredCutDraft();
    await persistCutDraft();
    snapshots.push({{
      phase: "undo",
      revision: cutDraftRevision,
      count: timelineDeleteRanges.length,
      acknowledged: isCutDraftAcknowledged(
        cutDraftSemanticSignature(buildPersistedCutDraftPayload()),
      ),
    }});

    timelineDeleteRanges = [{{
      id: 2,
      key: "timeline-1",
      start: 0.32,
      end: 0.45,
      originalStart: 0.35,
      originalEnd: 0.42,
    }}];
    captureDesiredCutDraft();
    await persistCutDraft();
    snapshots.push({{
      phase: "redo",
      revision: cutDraftRevision,
      range: {{ ...timelineDeleteRanges[0] }},
      acknowledged: isCutDraftAcknowledged(
        cutDraftSemanticSignature(buildPersistedCutDraftPayload()),
      ),
    }});

    timelineDeleteRanges[0].originalEnd = 0.4314;
    captureDesiredCutDraft();
    returnInvalidStructure = true;
    await persistCutDraft();
    snapshots.push({{
      phase: "invalid",
      revision: cutDraftRevision,
      acknowledged: isCutDraftAcknowledged(
        cutDraftSemanticSignature(buildPersistedCutDraftPayload()),
      ),
    }});

    timelineDeleteRanges = [];
    cutDraftFailedSignature = "";
    captureDesiredCutDraft();
    await persistCutDraft();
    snapshots.push({{
      phase: "recovered",
      revision: cutDraftRevision,
      count: timelineDeleteRanges.length,
      acknowledged: isCutDraftAcknowledged(
        cutDraftSemanticSignature(buildPersistedCutDraftPayload()),
      ),
    }});
    return {{
      historyReconciles,
      localRevisions,
      requestRevisions: requests.map(request => request.revision),
      requestTimelineCounts: requests.map(
        request => request.timelineRanges.length,
      ),
      snapshots,
      statuses,
      retainedProjectionChecks,
    }};
  }},
}};
`)();
functions.run().then(
  result => console.log(JSON.stringify(result)),
  error => {{
    console.error(error?.stack || error);
    process.exitCode = 1;
  }},
);
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
        pytest.skip("Node.js is required for the frontend cut-draft unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert payload["requestRevisions"] == [1, 1, 2, 3, 4, 5]
    assert payload["requestTimelineCounts"] == [1, 1, 0, 1, 1, 0]
    assert payload["localRevisions"] == [2, 3, 4, 6]
    assert payload["historyReconciles"] == 1
    assert payload["snapshots"] == [
        {
            "phase": "invalid-revision",
            "revision": 1,
            "acknowledged": False,
        },
        {
            "phase": "normalized",
            "revision": 2,
            "range": {
                "id": 1,
                "key": "timeline-1",
                "start": 0.32,
                "end": 0.45,
                "originalStart": 0.35,
                "originalEnd": 0.42,
            },
            "acknowledged": True,
        },
        {"phase": "undo", "revision": 3, "count": 0, "acknowledged": True},
        {
            "phase": "redo",
            "revision": 4,
            "range": {
                "id": 2,
                "key": "timeline-1",
                "start": 0.32,
                "end": 0.45,
                "originalStart": 0.35,
                "originalEnd": 0.42,
            },
            "acknowledged": True,
        },
        {"phase": "invalid", "revision": 5, "acknowledged": False},
        {"phase": "recovered", "revision": 6, "count": 0, "acknowledged": True},
    ]
    assert payload["statuses"][0]["tone"] == "error"
    assert payload["statuses"][-2]["tone"] == "error"
    assert payload["statuses"][-1] == {
        "message": "剪辑草稿已保存",
        "tone": "success",
    }
    assert payload["retainedProjectionChecks"] == [
        {"accepted": True, "text": "normalized"},
        {"accepted": True, "text": "normalized"},
        {"accepted": True, "text": "normalized"},
        {"accepted": True, "text": "normalized"},
    ]


def test_frontend_live_transcript_uses_semantic_range_and_physical_retiming():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    token_start = app_source.index("function splitTextIntoCharacterTokens")
    token_end = app_source.index("function getTranscriptCharacterUnits", token_start)
    retained_start = app_source.index("function getRetainedSegmentParts")
    retained_end = app_source.index(
        "function getActiveTranscriptSegmentIndex", retained_start
    )
    source = "\n".join(
        [app_source[token_start:token_end], app_source[retained_start:retained_end]]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const CUT_SPEECH_BOUNDARY_EPSILON = 0.001;
const selectedRanges = new Map();
const canonicalizeTextDeleteRange = (range) => range;
const getCommittedTimelineSemanticDeleteRanges = () => [];
${{source}}
return {{ getRetainedSegmentParts }};
`)();
const parts = functions.getRetainedSegmentParts(
  {{
    start: 0.2,
    end: 0.6,
    text: "得你",
    words: [
      {{ text: "得", start: 0.2, end: 0.4 }},
      {{ text: "你", start: 0.4, end: 0.6 }},
    ],
  }},
  [{{ sourceStart: 0.5, sourceEnd: 0.6, editedStart: 0 }}],
  [{{ start: 0.2, end: 0.4 }}],
);
console.log(JSON.stringify(parts));
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
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    assert json.loads(result.stdout) == [
        {
            "sourceStart": 0.5,
            "sourceEnd": 0.6,
            "editedStart": 0,
            "editedEnd": pytest.approx(0.1),
            "text": "你",
            "words": [
                {
                    "text": "你",
                    "start": 0,
                    "end": pytest.approx(0.1),
                    "sourceStart": 0.5,
                    "sourceEnd": 0.6,
                }
            ],
        }
    ]


def test_frontend_live_transcript_keeps_tokens_fully_inside_physical_cut():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    token_start = app_source.index("function splitTextIntoCharacterTokens")
    token_end = app_source.index("function getTranscriptCharacterUnits", token_start)
    retained_start = app_source.index("function getRetainedSegmentParts")
    retained_end = app_source.index(
        "function getActiveTranscriptSegmentIndex", retained_start
    )
    source = "\n".join(
        [app_source[token_start:token_end], app_source[retained_start:retained_end]]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const CUT_SPEECH_BOUNDARY_EPSILON = 0.001;
const selectedRanges = new Map();
const canonicalizeTextDeleteRange = (range) => range;
const getCommittedTimelineSemanticDeleteRanges = () => [];
${{source}}
return {{ getRetainedSegmentParts }};
`)();
const parts = functions.getRetainedSegmentParts(
  {{
    start: 27.0,
    end: 31.0,
    text: "所有人一起给一起给你画",
    words: [
      {{ text: "所有人", start: 27.0, end: 28.454 }},
      {{ text: "一起给", start: 28.454, end: 29.171 }},
      {{ text: "一起", start: 29.171, end: 29.649 }},
      {{ text: "给你画", start: 29.649, end: 31.0 }},
    ],
  }},
  [
    {{ sourceStart: 27.0, sourceEnd: 28.299, editedStart: 27.0 }},
    {{ sourceStart: 29.807, sourceEnd: 31.0, editedStart: 28.299 }},
  ],
  [{{ start: 28.454, end: 29.171 }}],
);
console.log(JSON.stringify(parts));
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
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    parts = json.loads(result.stdout)
    assert "".join(part["text"] for part in parts) == "所有人一起给你画"
    assert all(
        word["end"] > word["start"]
        for part in parts
        for word in part["words"]
    )


def test_frontend_server_projection_rejects_stale_job_signature_and_revision():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    guard_start = app_source.index("function applyServerRetainedProjection")
    guard_end = app_source.index("function syncEditorSuiteCutDraftState", guard_start)
    source = app_source[guard_start:guard_end]
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
let serverRetainedProjection = null;
let currentJobId = "job-current";
let cutDraftRevision = 4;
const buildPersistedCutDraftPayload = () => ({{ signature: "sig-current" }});
const cutDraftSemanticSignature = (payload) => payload.signature;
${{source}}
return {{
  applyServerRetainedProjection,
  current: () => serverRetainedProjection,
}};
`)();
const transcript = {{ text: "所有人一起给你画", segments: [] }};
const staleJob = functions.applyServerRetainedProjection(transcript, {{
  jobId: "job-old", signature: "sig-current", revision: 4,
}});
const staleSignature = functions.applyServerRetainedProjection(transcript, {{
  jobId: "job-current", signature: "sig-old", revision: 4,
}});
const staleRevision = functions.applyServerRetainedProjection(transcript, {{
  jobId: "job-current", signature: "sig-current", revision: 3,
}});
const accepted = functions.applyServerRetainedProjection(transcript, {{
  jobId: "job-current", signature: "sig-current", revision: 4,
}});
console.log(JSON.stringify({{
  staleJob, staleSignature, staleRevision, accepted,
  current: functions.current(),
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
        pytest.skip("Node.js is required for the frontend projection unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert payload["staleJob"] is False
    assert payload["staleSignature"] is False
    assert payload["staleRevision"] is False
    assert payload["accepted"] is True
    assert payload["current"]["transcript"]["text"] == "所有人一起给你画"


def test_frontend_local_projection_preserves_source_segment_identity():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    token_start = app_source.index("function splitTextIntoCharacterTokens")
    token_end = app_source.index("function getTranscriptCharacterUnits", token_start)
    retained_start = app_source.index("function getRetainedSegmentParts")
    retained_end = app_source.index("function applyServerRetainedProjection", retained_start)
    source = "\n".join(
        [app_source[token_start:token_end], app_source[retained_start:retained_end]]
    )
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
const CUT_SPEECH_BOUNDARY_EPSILON = 0.001;
const currentEditableSegments = [
  {{ start: 0, end: 1, text: "第一段", words: [{{ text: "第一段", start: 0, end: 1 }}] }},
  {{ start: 1, end: 2, text: "第二段", words: [{{ text: "第二段", start: 1, end: 2 }}] }},
];
const spans = [{{ sourceStart: 0, sourceEnd: 2, editedStart: 0, editedEnd: 2 }}];
const getEditedTimelineSpans = () => spans;
const getCurrentSemanticDeleteRanges = () => [];
const getEditableSegmentCoverageEnd = (index) => currentEditableSegments[index].end;
const editedCutTimelineDuration = () => 2;
const cutDraftSemanticSignature = () => "signature";
const buildPersistedCutDraftPayload = () => ({{}});
let serverRetainedProjection = null;
let currentJobId = "job-current";
let cutDraftRevision = 1;
const cutPreviewVideo = {{ currentTime: 1.2 }};
${{source}}
return {{
  buildLocalRetainedProjection,
  getActiveTranscriptSegmentIndex,
}};
`)();
const projection = functions.buildLocalRetainedProjection();
console.log(JSON.stringify({{
  sourceSegmentIndexes: projection.segments.map(item => item.sourceSegmentIndex),
  activeIndex: functions.getActiveTranscriptSegmentIndex(),
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
        pytest.skip("Node.js is required for the frontend projection unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    assert json.loads(result.stdout) == {
        "sourceSegmentIndexes": [0, 1],
        "activeIndex": 1,
    }


def test_frontend_cut_draft_flush_fails_once_when_server_sync_does_not_commit():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    flush_start = app_source.index("async function flushCutDraftSave")
    flush_end = app_source.index("async function clearPersistedCutDraft", flush_start)
    source = app_source[flush_start:flush_end]
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
let cutDraftReady = true;
let currentJobId = "job-1";
let cutDraftSaveQueue = Promise.resolve();
let cutDraftSaveInFlight = null;
let cutDraftSaveTimer = null;
let cutDraftLastSignature = "stale";
let cutDraftNeedsServerSync = true;
let cutDraftRevision = 3;
let scheduleCount = 0;
const buildPersistedCutDraftPayload = () => ({{
  textRanges: [{{ key: "text-a", start: 0, end: 0.4 }}],
}});
const cutDraftSemanticSignature = (payload) => JSON.stringify(payload);
const flushPendingCutSelectionCommit = () => false;
const flushPendingCutCommitEffects = () => false;
const flushLocalCutHistory = () => undefined;
const cancelCutDraftSaveTimer = () => undefined;
const scheduleCutDraftSave = () => {{ scheduleCount += 1; }};
const isCutDraftAcknowledged = () => false;
${{source}}
return {{
  flushCutDraftSave,
  scheduleCount: () => scheduleCount,
}};
`)();
functions.flushCutDraftSave().then(
  () => console.log(JSON.stringify({{ resolved: true }})),
  (error) => console.log(JSON.stringify({{
    resolved: false,
    message: error.message,
    scheduleCount: functions.scheduleCount(),
  }})),
);
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
        pytest.skip("Node.js is required for the frontend cut-draft unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    payload = json.loads(result.stdout)
    assert payload == {
        "resolved": False,
        "message": "剪辑草稿尚未同步到服务器。请稍后重试。",
        "scheduleCount": 1,
    }


def test_frontend_restart_abandons_in_flight_cut_draft_without_waiting():
    app_source = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    reset_start = app_source.index("async function confirmAndResetProject")
    reset_end = app_source.index("function setProgress", reset_start)
    source = app_source[reset_start:reset_end]
    script = f"""
const source = {json.dumps(source)};
const functions = new Function(`
let currentJobId = "job-1";
let cutDraftReady = true;
const calls = [];
const never = new Promise(() => {{}});
let cutDraftSaveInFlight = {{ promise: never }};
let cutDraftSaveQueue = never;
let shouldFailClear = false;
const window = {{
  appConfirm: async () => true,
  appAlert: async () => calls.push("alert"),
}};
const resetCutDraftSaveRuntime = () => calls.push("reset-runtime");
const cancelCutDraftSaveTimer = () => calls.push("cancel-timer");
const clearPersistedCutDraft = async (jobId) => {{
  calls.push("clear:" + jobId);
  if (shouldFailClear) throw new Error("clear failed");
}};
const removeLocalCutDraft = (jobId) => calls.push("remove-draft:" + jobId);
const removeLocalCutHistory = (jobId) => calls.push("remove-history:" + jobId);
const resetToUpload = () => calls.push("reset-upload");
const setCutDraftSaveStatus = () => calls.push("status-error");
${{source}}
return {{
  confirmAndResetProject,
  calls: () => calls,
  ready: () => cutDraftReady,
  prepareFailure: () => {{
    calls.length = 0;
    shouldFailClear = true;
    cutDraftReady = true;
  }},
}};
`)();
(async () => {{
  const outcome = await Promise.race([
    functions.confirmAndResetProject().then(() => "completed"),
    new Promise(resolve => setTimeout(() => resolve("timed-out"), 50)),
  ]);
  const success = {{
    outcome,
    calls: [...functions.calls()],
    ready: functions.ready(),
  }};
  functions.prepareFailure();
  await functions.confirmAndResetProject();
  console.log(JSON.stringify({{
    success,
    failure: {{
      calls: functions.calls(),
      ready: functions.ready(),
    }},
  }}));
}})();
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
        pytest.skip("Node.js is required for the frontend restart unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    assert json.loads(result.stdout) == {
        "success": {
            "outcome": "completed",
            "calls": [
                "reset-runtime",
                "clear:job-1",
                "remove-draft:job-1",
                "remove-history:job-1",
                "reset-upload",
            ],
            "ready": False,
        },
        "failure": {
            "calls": [
                "reset-runtime",
                "clear:job-1",
                "status-error",
                "alert",
            ],
            "ready": True,
        },
    }


def test_frontend_transcript_now_playing_layer_has_one_real_row_owner():
    root = Path(__file__).resolve().parents[2]
    page_source = (root / "web" / "index.html").read_text(encoding="utf-8")
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    follow_source = (root / "web" / "transcript-follow-scroll.js").read_text(
        encoding="utf-8"
    )

    placeholder_start = follow_source.index("function createPlaceholder")
    placeholder_end = follow_source.index("function placeLayer", placeholder_start)
    placeholder_source = follow_source[placeholder_start:placeholder_end]
    reset_start = app_source.index("function resetCutTranscriptRenderState()")
    reset_end = app_source.index("function recordCutRenderResult", reset_start)
    reset_source = app_source[reset_start:reset_end]
    render_start = app_source.index("function renderCutSegments(")
    render_end = app_source.index("function updateCutSegmentText", render_start)
    render_source = app_source[render_start:render_end]

    assert page_source.count('id="transcriptNowPlayingLayer"') == 1
    assert follow_source.count("layer.appendChild(item)") == 1
    assert 'placeholder.className = "segment-follow-placeholder"' in placeholder_source
    assert 'placeholder.setAttribute?.("aria-hidden", "true")' in placeholder_source
    assert 'placeholder.setAttribute?.("inert", "")' in placeholder_source
    assert ".dataset" not in placeholder_source
    assert "segment-play-button" not in placeholder_source
    assert ".tabIndex" not in placeholder_source
    assert "item.style.transform =" not in follow_source
    assert "transcriptFollowScrollController.reset()" in reset_source
    assert render_source.index("resetCutTranscriptRenderState()") < (
        render_source.index("segmentList.replaceChildren(fragment)")
    )
    assert app_source.count(
        'segmentList.addEventListener("click", handleTranscriptDisplayClick)'
    ) == 1
    assert app_source.count("transcriptNowPlayingLayer.addEventListener(") == 1


def test_frontend_transcript_follow_scroll_anchors_clamps_and_deduplicates():
    root = Path(__file__).resolve().parents[2]
    follow_source = (root / "web" / "transcript-follow-scroll.js").read_text(
        encoding="utf-8"
    )

    assert ".animate(" not in follow_source
    assert "previousVisualTop" not in follow_source
    assert "activeMotion" not in follow_source
    assert "startListPhase" not in follow_source
    assert "startTailPhase" not in follow_source
    assert "list.style.transform" not in follow_source
    assert follow_source.count("panel.scrollTop = metrics.targetScrollTop;") == 1
    assert follow_source.index("const metrics = getTranscriptFollowScrollMetrics") < (
        follow_source.index("const placeholder = createPlaceholder")
    )
    assert follow_source.index("const layerPlacement = getLayerPlacement") < (
        follow_source.index("const placeholder = createPlaceholder")
    )

    script = r"""
const assert = require('node:assert/strict');
global.getComputedStyle = (node) => node.computedStyle || ({
  paddingTop: '0px',
  position: 'static',
  top: 'auto',
});
const followScroll = require('./web/transcript-follow-scroll.js');

function createClassList(initial = []) {
  const values = new Set(initial);
  return {
    add: (...names) => names.forEach((name) => values.add(name)),
    contains: (name) => values.has(name),
    remove: (...names) => names.forEach((name) => values.delete(name)),
  };
}

function createFixture({ reducedMotion = false } = {}) {
  const scrollWrites = [];
  let animationCalls = 0;
  let scrollTop = 100;

  function createNode(classNames = []) {
    const node = {
      attributes: {},
      children: [],
      classList: createClassList(classNames),
      className: classNames.join(' '),
      isConnected: true,
      parentNode: null,
      style: {},
      appendChild(child) {
        child.parentNode?.removeChild?.(child);
        this.children.push(child);
        child.parentNode = this;
        child.isConnected = this.isConnected;
        return child;
      },
      insertBefore(child, reference) {
        child.parentNode?.removeChild?.(child);
        const index = reference ? this.children.indexOf(reference) : -1;
        this.children.splice(index < 0 ? this.children.length : index, 0, child);
        child.parentNode = this;
        child.isConnected = this.isConnected;
        return child;
      },
      remove() {
        this.parentNode?.removeChild?.(this);
      },
      removeChild(child) {
        const index = this.children.indexOf(child);
        if (index >= 0) this.children.splice(index, 1);
        child.parentNode = null;
        child.isConnected = false;
        return child;
      },
      setAttribute(name, value) {
        this.attributes[name] = String(value);
      },
      animate() {
        animationCalls += 1;
      },
    };
    Object.defineProperty(node, 'nextSibling', {
      get() {
        if (!this.parentNode) return null;
        const index = this.parentNode.children.indexOf(this);
        return this.parentNode.children[index + 1] || null;
      },
    });
    return node;
  }

  function addEventTarget(node) {
    const listeners = new Map();
    node.addEventListener = (type, callback) => {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(callback);
    };
    node.dispatch = (type, key = '') => {
      for (const callback of listeners.get(type) || []) callback({ key, type });
    };
    node.listenerCount = () => [...listeners.values()].reduce(
      (total, callbacks) => total + callbacks.size,
      0,
    );
    node.removeEventListener = (type, callback) => {
      listeners.get(type)?.delete(callback);
    };
    return node;
  }

  const toolbar = {
    computedStyle: { position: 'static', top: 'auto' },
    getBoundingClientRect: () => ({
      bottom: 178,
      height: 60,
      top: 118,
    }),
  };
  const panel = addEventTarget({
    clientHeight: 300,
    clientTop: 0,
    hidden: false,
    scrollHeight: 1000,
    get scrollTop() {
      return scrollTop;
    },
    set scrollTop(value) {
      scrollTop = Number(value);
      scrollWrites.push(scrollTop);
    },
    getBoundingClientRect: () => ({
      bottom: 400,
      height: 300,
      top: 100,
    }),
    querySelector: (selector) => selector === '.cut-toolbar' ? toolbar : null,
  });
  const positioningContext = {
    clientLeft: 0,
    clientTop: 0,
    getBoundingClientRect: () => ({ left: 20, top: 80 }),
  };
  const list = createNode(['segment-list']);
  const layer = addEventTarget(createNode(['transcript-now-playing-layer']));
  layer.hidden = true;
  layer.offsetParent = positioningContext;
  layer.parentElement = positioningContext;
  layer.getBoundingClientRect = () => {
    const transformMatch = String(layer.style.transform || '').match(
      /translate3d\(0, (-?[\d.]+)px, 0\)/,
    );
    const transformY = transformMatch ? Number(transformMatch[1]) : 0;
    const top = 80 + Number.parseFloat(layer.style.top || 0) + transformY;
    const left = 20 + Number.parseFloat(layer.style.left || 0);
    const height = Number.parseFloat(layer.style.height || 0);
    const width = Number.parseFloat(layer.style.width || 0);
    return { bottom: top + height, height, left, top, width };
  };

  function createItem(contentTop, height = 32) {
    const item = createNode(['segment-item', 'is-playback-active']);
    item.buttonCount = 1;
    item.closest = (selector) => selector === '.text-editor-panel' ? panel : null;
    item.getBoundingClientRect = () => {
      if (item.parentNode === layer) return layer.getBoundingClientRect();
      const top = 100 + contentTop - panel.scrollTop;
      return {
        bottom: top + height,
        height,
        left: 40,
        right: 280,
        top,
        width: 240,
      };
    };
    list.appendChild(item);
    return item;
  }

  const controller = followScroll.createController({
    createElement: () => createNode(),
    layer,
    matchMedia: () => ({ matches: reducedMotion }),
  });
  return {
    animationCalls: () => animationCalls,
    controller,
    createItem,
    layer,
    list,
    panel,
    scrollWrites,
    toolbar,
  };
}

const fixture = createFixture();
const first = fixture.createItem(420);
const second = fixture.createItem(620);
const firstMetrics = followScroll.getTranscriptFollowScrollMetrics(
  fixture.panel,
  first,
  fixture.toolbar,
);
assert.equal(firstMetrics.anchorTop, 282);
assert.equal(firstMetrics.tailRemainder, 0);

assert.equal(fixture.controller.follow(first, 'row-first'), true);
assert.deepEqual(fixture.scrollWrites, [firstMetrics.targetScrollTop]);
assert.equal(fixture.layer.children.length, 1);
assert.equal(fixture.layer.children[0], first);
assert.equal(fixture.layer.getBoundingClientRect().top, firstMetrics.anchorTop);
assert.equal(fixture.list.children.length, 2);
const firstPlaceholder = fixture.list.children[0];
assert.equal(firstPlaceholder.className, 'segment-follow-placeholder');
assert.equal(firstPlaceholder.attributes['aria-hidden'], 'true');
assert.equal(Object.hasOwn(firstPlaceholder.attributes, 'inert'), true);
assert.equal(firstPlaceholder.inert, true);
assert.equal(firstPlaceholder.children.length, 0);
assert.equal(first.buttonCount, 1);

assert.equal(fixture.controller.follow(first, 'row-first'), false);
assert.deepEqual(fixture.scrollWrites, [firstMetrics.targetScrollTop]);
assert.equal(fixture.layer.children[0], first);

assert.equal(fixture.controller.follow(second, 'row-second'), true);
assert.deepEqual(fixture.list.children, [first, fixture.list.children[1]]);
assert.equal(fixture.list.children[1].className, 'segment-follow-placeholder');
assert.equal(fixture.layer.children[0], second);
assert.equal(fixture.animationCalls(), 0);

fixture.panel.dispatch('keydown', 'Enter');
assert.equal(fixture.layer.children[0], second);
fixture.panel.dispatch('wheel');
assert.deepEqual(fixture.list.children, [first, second]);
assert.equal(fixture.layer.hidden, true);
assert.equal(fixture.layer.children.length, 0);
assert.equal(fixture.panel.listenerCount(), 0);
assert.equal(fixture.controller.follow(second, 'row-second'), false);
assert.equal(fixture.layer.children.length, 0);

fixture.controller.reset();
assert.equal(fixture.controller.follow(second, 'row-second'), true);
second.classList.remove('is-playback-active');
assert.equal(fixture.controller.follow(second, 'row-second'), false);
assert.deepEqual(fixture.list.children, [first, second]);
second.classList.add('is-playback-active');
assert.equal(fixture.controller.follow(second, 'row-second'), true);
fixture.controller.reset();

const hiddenFixture = createFixture({ reducedMotion: true });
const hiddenItem = hiddenFixture.createItem(420);
hiddenFixture.panel.hidden = true;
assert.equal(hiddenFixture.controller.follow(hiddenItem, 'retry-key'), false);
assert.equal(hiddenFixture.scrollWrites.length, 0);
hiddenFixture.panel.hidden = false;
assert.equal(hiddenFixture.controller.follow(hiddenItem, 'retry-key'), true);
assert.equal(hiddenFixture.scrollWrites.length, 1);
assert.equal(hiddenFixture.animationCalls(), 0);
hiddenFixture.controller.destroy();
hiddenFixture.controller.destroy();
assert.equal(hiddenFixture.controller.follow(hiddenItem, 'after-destroy'), false);
assert.deepEqual(hiddenFixture.list.children, [hiddenItem]);

const tailFixture = createFixture();
const tailItem = tailFixture.createItem(900);
const tailMetrics = followScroll.getTranscriptFollowScrollMetrics(
  tailFixture.panel,
  tailItem,
  tailFixture.toolbar,
);
assert.ok(tailMetrics.tailRemainder > 0);
assert.equal(tailFixture.controller.follow(tailItem, 'tail-row'), true);
assert.equal(
  tailFixture.layer.getBoundingClientRect().top,
  tailMetrics.anchorTop + tailMetrics.tailRemainder,
);
assert.ok(
  tailFixture.layer.getBoundingClientRect().bottom <=
    tailFixture.panel.getBoundingClientRect().bottom,
);
assert.equal(tailFixture.animationCalls(), 0);
tailFixture.panel.dispatch('touchstart');
assert.deepEqual(tailFixture.list.children, [tailItem]);
assert.equal(tailFixture.layer.hidden, true);

console.log('ok');
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the transcript follow-scroll unit test.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stderr)

    assert result.stdout.strip() == "ok"




def test_frontend_playback_frame_clock_uses_one_cancellable_callback():
    root = Path(__file__).resolve().parents[2]
    media_source = (root / "web" / "editor-media-controller.js").read_text(
        encoding="utf-8"
    )
    clock_start = media_source.index("function createPlaybackFrameClock")
    clock_end = media_source.index("function createController", clock_start)
    clock_source = media_source[clock_start:clock_end]
    script = f"""
const window = {{}};
const root = window;
{clock_source}

function createVideo(withVideoFrames = false) {{
  const listeners = new Map();
  const callbacks = new Map();
  const cancelled = [];
  let nextId = 1;
  const video = {{
    callbacks,
    cancelled,
    currentTime: 0,
    ended: false,
    paused: true,
    addEventListener(type, callback) {{
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(callback);
    }},
    dispatch(type) {{
      for (const callback of [...(listeners.get(type) || [])]) callback();
    }},
    listenerCount() {{
      return [...listeners.values()].reduce(
        (total, callbacksForType) => total + callbacksForType.size,
        0,
      );
    }},
    removeEventListener(type, callback) {{
      listeners.get(type)?.delete(callback);
    }},
  }};
  if (withVideoFrames) {{
    video.requestVideoFrameCallback = (callback) => {{
      const id = nextId++;
      callbacks.set(id, callback);
      return id;
    }};
    video.cancelVideoFrameCallback = (id) => {{
      cancelled.push(id);
      callbacks.delete(id);
    }};
  }}
  return video;
}}

const videoFrames = [];
let videoFrameResets = 0;
const video = createVideo(true);
const videoClock = createPlaybackFrameClock(
  video,
  (time) => videoFrames.push(time),
  {{ onReset: () => {{ videoFrameResets += 1; }} }},
);
video.paused = false;
video.dispatch('play');
video.dispatch('play');
const videoUniqueAfterDuplicatePlay = video.callbacks.size === 1;
const firstVideoEntry = video.callbacks.entries().next().value;
video.callbacks.delete(firstVideoEntry[0]);
firstVideoEntry[1](0, {{ mediaTime: 1.25 }});
const videoRescheduledOnce = video.callbacks.size === 1;
const staleVideoCallback = video.callbacks.values().next().value;
video.dispatch('seeking');
const videoCancelledOnSeeking = video.callbacks.size === 0;
video.currentTime = 4;
video.paused = false;
video.dispatch('seeked');
const currentVideoCallback = video.callbacks.values().next().value;
const framesBeforeStaleCallback = [...videoFrames];
staleVideoCallback?.(0, {{ mediaTime: 2.75 }});
const staleVideoCallbackIgnored =
  video.callbacks.size === 1 &&
  video.callbacks.values().next().value === currentVideoCallback &&
  JSON.stringify(videoFrames) === JSON.stringify(framesBeforeStaleCallback);
video.paused = true;
video.dispatch('pause');
const videoCancelledOnPause = video.callbacks.size === 0;
video.paused = false;
video.dispatch('play');
video.ended = true;
video.dispatch('ended');
video.ended = false;
video.dispatch('play');
video.dispatch('emptied');
video.dispatch('play');
const lateVideoCallback = video.callbacks.values().next().value;
videoClock.destroy();
lateVideoCallback?.(0, {{ mediaTime: 9 }});

const rafCallbacks = new Map();
const rafCancelled = [];
let nextRafId = 0;
const rafFrames = [];
const rafVideo = createVideo(false);
const rafClock = createPlaybackFrameClock(
  rafVideo,
  (time) => rafFrames.push(time),
  {{
    requestAnimationFrame(callback) {{
      const id = nextRafId++;
      rafCallbacks.set(id, callback);
      return id;
    }},
    cancelAnimationFrame(id) {{
      rafCancelled.push(id);
      rafCallbacks.delete(id);
    }},
  }},
);
rafVideo.currentTime = 2;
rafVideo.paused = false;
rafVideo.dispatch('play');
rafVideo.dispatch('play');
const rafAcceptsZeroIdAndDeduplicates =
  rafCallbacks.size === 1 && rafCallbacks.has(0);
const firstRaf = rafCallbacks.get(0);
rafCallbacks.delete(0);
firstRaf(16);
rafVideo.paused = true;
rafVideo.dispatch('pause');
const rafCancelledOnPause = rafCallbacks.size === 0;
rafClock.destroy();

const fallbackFrames = [];
const fallbackVideo = createVideo(false);
const fallbackClock = createPlaybackFrameClock(
  fallbackVideo,
  (time) => fallbackFrames.push(time),
);
fallbackVideo.currentTime = 3;
fallbackVideo.paused = false;
fallbackVideo.dispatch('timeupdate');
fallbackVideo.paused = true;
fallbackVideo.dispatch('timeupdate');
fallbackClock.destroy();

console.log(JSON.stringify({{
  fallbackFrames,
  fallbackMode: fallbackClock.mode,
  rafAcceptsZeroIdAndDeduplicates,
  rafCancelled,
  rafCancelledOnPause,
  rafFrames,
  rafMode: rafClock.mode,
  videoCancelledOnPause,
  videoCancelledOnSeeking,
  videoFrameResets,
  videoFrames,
  videoListenersAfterDestroy: video.listenerCount(),
  videoMode: videoClock.mode,
  videoRescheduledOnce,
  staleVideoCallbackIgnored,
  videoUniqueAfterDuplicatePlay,
}}));
"""

    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=root,
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the playback frame-clock test.")

    payload = json.loads(result.stdout)
    assert payload["videoMode"] == "video-frame"
    assert payload["videoUniqueAfterDuplicatePlay"] is True
    assert payload["videoRescheduledOnce"] is True
    assert payload["staleVideoCallbackIgnored"] is True
    assert payload["videoCancelledOnSeeking"] is True
    assert payload["videoCancelledOnPause"] is True
    assert payload["videoFrames"] == [1.25, 4]
    assert payload["videoFrameResets"] == 5
    assert payload["videoListenersAfterDestroy"] == 0
    assert payload["rafMode"] == "animation-frame"
    assert payload["rafAcceptsZeroIdAndDeduplicates"] is True
    assert payload["rafFrames"] == [2]
    assert payload["rafCancelledOnPause"] is True
    assert payload["rafCancelled"] == [1]
    assert payload["fallbackMode"] == "timeupdate"
    assert payload["fallbackFrames"] == [3]


def test_frontend_playback_frame_path_uses_cached_indexes_only():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    media_source = (root / "web" / "editor-media-controller.js").read_text(
        encoding="utf-8"
    )
    styles_source = (root / "web" / "styles.css").read_text(encoding="utf-8")
    frame_start = app_source.index("function updateCutPlaybackVisualFrame")
    frame_end = app_source.index("function updateCutTimelinePlayhead", frame_start)
    frame_source = app_source[frame_start:frame_end]
    state_start = app_source.index("function getCutPlaybackFrameState")
    state_end = app_source.index("function updateCutPlaybackVisualFrame", state_start)
    state_source = app_source[state_start:state_end]
    refresh_start = app_source.index("function refreshCutTimeline")
    refresh_end = app_source.index("function beginCutTimelineSelection", refresh_start)
    refresh_source = app_source[refresh_start:refresh_end]

    for forbidden in (
        "getMergedSelection",
        "querySelector",
        "querySelectorAll",
        "renderCutTimeline",
        "updateCutTimelineScale",
        "updateTime",
    ):
        assert forbidden not in frame_source
    assert "cutTimelineTrackWidthCache" in frame_source
    assert "translate3d(" in frame_source
    assert "editedTimelineSpansCache || []" in state_source
    assert "getEditedTimelineSpans" not in state_source
    assert "requestVideoFrameCallback" in media_source
    assert "function createPlaybackFrameClock" not in app_source
    assert "window.EditorSuite?.mediaController?.()" in app_source
    assert "cutPlaybackFrameClock?.destroy()" in app_source
    assert refresh_source.index("updateCutTimelineScale()") < refresh_source.index(
        "renderCutTimelineTextSegments()"
    )
    assert refresh_source.index("renderCutTimelineRanges()") < refresh_source.index(
        "updateCutTimelinePlayhead()"
    )
    assert ".cut-frame-timeline .frame-timeline-playhead" in styles_source
    assert "will-change: transform" in styles_source


def test_frontend_playback_cursors_handle_overlap_forward_and_seek():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    floor_start = app_source.index("function playbackCursorFloor")
    floor_end = app_source.index("function rebuildTranscriptPlaybackEntries", floor_start)
    transcript_start = app_source.index("function transcriptPlaybackEntryAtTime")
    transcript_end = app_source.index("function getLiveEditedSegmentTiming", transcript_start)
    timeline_start = app_source.index("function updateCutTimelineTextStates")
    timeline_end = app_source.index("function getCutPlaybackFrameState", timeline_start)
    source = "\n".join(
        [
            app_source[floor_start:floor_end],
            app_source[transcript_start:transcript_end],
            app_source[timeline_start:timeline_end],
        ]
    )
    script = f"""
{source}
const transcriptPlaybackEntries = [
  {{ key: 'long', start: 0, end: 10, maximumEnd: 10, eligible: true, priority: 1 }},
  {{ key: 'short', start: 2, end: 3, maximumEnd: 10, eligible: true, priority: 2 }},
];
const transcriptPlaybackEntryByKey = new Map(
  transcriptPlaybackEntries.map((entry) => [entry.key, entry]),
);
let transcriptPlaybackCursor = -1;
let transcriptPlaybackActiveCursor = -1;
let transcriptPlaybackLastTime = Number.NEGATIVE_INFINITY;
let transcriptPreviewRange = null;

const activeClasses = [new Set(), new Set()];
const cutTimelineTextPlaybackEntries = transcriptPlaybackEntries.map(
  (entry, index) => ({{
    ...entry,
    element: {{
      classList: {{
        add: (name) => activeClasses[index].add(name),
        remove: (name) => activeClasses[index].delete(name),
      }},
    }},
  }}),
);
let cutTimelineTextPlaybackCursor = -1;
let cutTimelineTextPlaybackFloorCursor = -1;
let cutTimelineTextPlaybackLastTime = Number.NEGATIVE_INFINITY;
const cutPreviewVideo = {{ currentTime: 0 }};

const transcriptAtOverlap = transcriptPlaybackEntryAtTime(2.5)?.key;
const transcriptAfterShortEnds = transcriptPlaybackEntryAtTime(4)?.key;
const transcriptFloorAfterShortEnds = transcriptPlaybackCursor;
const transcriptActiveAfterShortEnds = transcriptPlaybackActiveCursor;
const transcriptAfterRepeatedForward = transcriptPlaybackEntryAtTime(5)?.key;
const transcriptAfterBackwardSeek = transcriptPlaybackEntryAtTime(0.5)?.key;
updateCutTimelineTextStates(2.5);
const timelineAtOverlap = cutTimelineTextPlaybackCursor;
updateCutTimelineTextStates(4);
const timelineAfterShortEnds = cutTimelineTextPlaybackCursor;
const timelineFloorAfterShortEnds = cutTimelineTextPlaybackFloorCursor;
updateCutTimelineTextStates(5);
const timelineAfterRepeatedForward = cutTimelineTextPlaybackCursor;
const timelineFloorAfterRepeatedForward = cutTimelineTextPlaybackFloorCursor;
updateCutTimelineTextStates(0.5);
const timelineAfterBackwardSeek = cutTimelineTextPlaybackCursor;

console.log(JSON.stringify({{
  transcriptAfterBackwardSeek,
  transcriptAfterShortEnds,
  transcriptAfterRepeatedForward,
  transcriptActiveAfterShortEnds,
  transcriptFloorAfterShortEnds,
  transcriptAtOverlap,
  timelineAfterBackwardSeek,
  timelineAfterShortEnds,
  timelineAfterRepeatedForward,
  timelineFloorAfterRepeatedForward,
  timelineFloorAfterShortEnds,
  timelineAtOverlap,
}}));
"""

    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=root,
            check=True,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the playback cursor test.")

    payload = json.loads(result.stdout)
    assert payload == {
        "transcriptAfterBackwardSeek": "long",
        "transcriptAfterShortEnds": "long",
        "transcriptAfterRepeatedForward": "long",
        "transcriptActiveAfterShortEnds": 0,
        "transcriptFloorAfterShortEnds": 1,
        "transcriptAtOverlap": "short",
        "timelineAfterBackwardSeek": 0,
        "timelineAfterShortEnds": 0,
        "timelineAfterRepeatedForward": 0,
        "timelineFloorAfterRepeatedForward": 1,
        "timelineFloorAfterShortEnds": 1,
        "timelineAtOverlap": 1,
    }


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
    assert "previewCompositor?.render(nextFrame)" in editor_suite_script_response.text
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


def test_editor_project_store_integration_guards_text_and_compose_state():
    root = Path(__file__).resolve().parents[2]
    app_source = (root / "web" / "app.js").read_text(encoding="utf-8")
    suite_source = (root / "web" / "editor-suite.js").read_text(encoding="utf-8")
    art_tool = (root / "web" / "editor-art-tool.js").read_text(encoding="utf-8")
    pip_tool = (root / "web" / "editor-pip-tool.js").read_text(encoding="utf-8")

    save_start = app_source.index("async function saveSegmentText()")
    save_end = app_source.index("function broadcastTranscriptUpdated()", save_start)
    save_source = app_source[save_start:save_end]
    assert 'beginProjectEffect("transcript-save")' in save_source
    assert "applyTranscriptTextEffect" in save_source
    assert "await loadServerRetainedProjection(" in save_source
    assert "syncTextSaveSourceSegments(jobPayload);" in save_source
    assert "syncTextSaveSourceSegments(refreshedJob);" in save_source
    assert "currentSegments = source.segments;" in save_source
    assert "currentEditableSegments = resolveEditableSegments(" in save_source
    assert "source.editableSegmentBoundaries" in save_source
    assert save_source.count(
        "cutTranscript = buildLiveCutDraftState().transcript"
    ) == 2
    refresh_effect = save_source.index('beginProjectEffect(\n        "transcript-refresh"')
    refreshed_job = save_source.index("const refreshedJob = await readProject()")
    refreshed_segments = save_source.index(
        "syncTextSaveSourceSegments(refreshedJob);"
    )
    refreshed_projection = save_source.rindex(
        "cutTranscript = buildLiveCutDraftState().transcript"
    )
    refreshed_apply = save_source.rindex("applyTranscriptTextEffect(")
    assert (
        refresh_effect
        < refreshed_job
        < refreshed_segments
        < refreshed_projection
        < refreshed_apply
    )
    assert "broadcastTranscriptUpdated();" in save_source
    assert "if (textSaveEffect)" not in save_source
    assert "projectStoreEnabled" not in save_source
    assert "window.location.reload" not in save_source
    assert "正在刷新页面" not in save_source

    compose_start = suite_source.index("function compositionRequest()")
    compose_end = suite_source.index("function stableValue", compose_start)
    compose_source = suite_source[compose_start:compose_end]
    assert "selectCurrentProjectFrame()" in compose_source
    assert "frame?.composition" in compose_source
    assert "selectCompositionRequest" not in compose_source
    assert "toolStates.get" not in compose_source

    generate_start = suite_source.index("async function generateCurrentPreview()")
    generate_end = suite_source.index("async function cancelComposition", generate_start)
    generate_source = suite_source[generate_start:generate_end]
    assert "const frame = selectCurrentProjectFrame();" in generate_source
    assert "const request = frame.composition;" in generate_source

    for marker in (
        "projectStoreEnabled",
        "toolFrameOwnsSource",
        "postMessage",
        'addEventListener("message"',
        "editor-suite:transcript-text",
        "editor-suite:project-ack",
        "advanceToolBridgeRevision",
        "acknowledgeToolProjection",
    ):
        assert marker not in suite_source

    assert "services.project.snapshot()" in art_tool
    assert "services.project.snapshot()" in pip_tool
    assert "sessionStorage" not in art_tool
    assert "sessionStorage" not in pip_tool


def test_realtime_effect_timeline_and_inspector_contracts():
    root = Path(__file__).resolve().parents[2]
    suite = (root / "web" / "editor-suite.js").read_text(encoding="utf-8")
    project_store = (root / "web" / "editor-project-store.js").read_text(
        encoding="utf-8"
    )
    art_model = (root / "web" / "editor-art-model.js").read_text(encoding="utf-8")
    art_tool = (root / "web" / "editor-art-tool.js").read_text(encoding="utf-8")
    pip_tool = (root / "web" / "editor-pip-tool.js").read_text(encoding="utf-8")
    styles = (root / "web" / "styles.css").read_text(encoding="utf-8")

    assert 'visibleKinds: ["art", "pip"]' in suite
    assert "matchTranscriptPhrase" in art_model
    assert "reconcileArtWithCut" in art_model
    assert "root.EditorArtModel?.reconcileArtWithCut?.(" in project_store
    assert 'replaceTimelineKind(\n            project.timeline,\n            "art"' in project_store
    assert "suppressedOverlays: state.project.art.suppressedOverlays || []" in suite
    assert "model.matchTranscriptPhrase(transcript(), selected.text, selected.start)" in art_tool
    assert "draftTranscript: transcript()" in art_tool
    assert "draftDuration: duration()" in art_tool
    assert "services.media.editedToSource?.(suggestion.start" in art_tool
    assert "data-art-selection-empty" in art_tool
    assert "ownedRoot.scrollTop = 0" in art_tool
    assert "scrollIntoView" not in pip_tool
    assert "listRect.height / list.offsetHeight" in pip_tool
    assert "(itemRect.bottom - listRect.bottom) / scrollScale" in pip_tool
    assert ".editor-art-selection-empty" in styles
    art_tabs_start = styles.index(".editor-art-tool-tabs {")
    art_tabs_end = styles.index("}", art_tabs_start)
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in styles[
        art_tabs_start:art_tabs_end
    ]


def test_compact_ui_density_preserves_preview_and_uses_shared_timeline_geometry():
    root = Path(__file__).resolve().parents[2]
    styles = (root / "web" / "styles.css").read_text(encoding="utf-8")
    timeline = (root / "web" / "editor-timeline-controller.js").read_text(
        encoding="utf-8"
    )
    for page_name in (
        "index.html",
        "settings.html",
        "font-manager.html",
        "font-library.html",
    ):
        page = (root / "web" / page_name).read_text(encoding="utf-8")
        assert "/styles.css?v=20260901-05" in page
    index_page = (root / "web" / "index.html").read_text(encoding="utf-8")
    assert "/editor-timeline-controller.js?v=20260831-01" in index_page

    for token in (
        "--ui-compact-control-height: 36px;",
        "--ui-compact-control-height-small: 30px;",
        "--ui-compact-panel-padding: 12px;",
        "--ui-compact-gap: 8px;",
        "--ui-compact-font: 12px;",
        "--ui-compact-font-small: 10px;",
        "--timeline-ruler-height-compact: 12px;",
        "--timeline-row-height-compact: 22px;",
        "--timeline-base-track-height-compact: 60px;",
        "--timeline-layer-track-height-compact: 52px;",
    ):
        assert token in styles

    density_start = styles.index("/* Compact application density")
    density_end = styles.index("/* Compact timeline geometry", density_start)
    density_rules = styles[density_start:density_end]
    for preview_selector in (
        ".text-editor-preview-pane",
        ".cut-preview-panel",
        "#cutPreviewPlayer",
        ".cut-video-stage",
        "#cutPreviewVideo",
        ".editor-suite-preview-canvas",
    ):
        assert preview_selector not in density_rules
    assert "zoom:" not in density_rules
    assert "transform: scale(" not in density_rules
    assert ".media-time {\n  min-width: 96px;" in styles
    assert (
        ".text-editor-preview-pane #cutPreviewPlayer:not(:fullscreen) "
        ".external-video-controls {"
    ) in styles
    assert "min-height: 24px;" in styles
    assert (
        ".text-editor-preview-pane .cut-timeline-action-button {\n"
        "    width: 22px;\n"
        "    min-width: 22px;\n"
        "    height: 22px;\n"
        "    min-height: 22px;"
    ) in styles
    assert (
        "grid-template-columns: 24px minmax(84px, 1fr) 96px 24px "
        "minmax(52px, 76px) 24px;"
    ) in styles
    assert (
        ".text-editor-preview-pane #cutPreviewPlayer:not(:fullscreen) "
        ".media-time {\n  width: 96px;\n  min-width: 96px;"
    ) in styles
    assert (
        ".text-editor-preview-pane #cutPreviewPlayer:not(:fullscreen) "
        ".media-control-button {\n  width: 24px;\n  height: 24px;"
    ) in styles
    assert (
        ".text-editor-preview-pane #cutPreviewPlayer.media-player-shell.cut-preview-player "
        ".media-seek.media-seek {\n    min-height: 44px;"
    ) in styles
    assert (
        ".text-editor-preview-pane #cutPreviewPlayer.media-player-shell.cut-preview-player "
        "#cutPreviewPlay,"
    ) in styles
    assert (
        "#cutPreviewPlayer #cutPreviewPlay,\n"
        "  #cutPreviewPlayer #cutPreviewMute,"
    ) in styles
    assert (
        "#cutPreviewPlayer #cutPreviewSeek {\n    min-height: 44px;"
    ) in styles
    assert "/* Compact transcript controls keep half-scale geometry" in styles
    for transcript_type_contract in (
        ".segment-time {",
        "font-size: 10.8px;",
        ".segment-current-badge {",
        "font-size: 8.4px;",
        ".segment-text {",
        "font-size: 12px;",
        ".segment-no-speech-copy strong {",
        ".segment-no-speech-meta {",
        "font-size: 9.6px;",
    ):
        assert transcript_type_contract in styles
    assert ".editor-pip-tool-panel {\n  --pip-readable-small-font: 15px;" in styles
    assert "zoom: 0.6;" in styles
    assert '"Microsoft YaHei UI",' in styles
    assert '"Noto Sans CJK SC",' in styles
    assert (
        "font-weight: 500;\n"
        "  font-size: var(--pip-readable-regular-font);\n"
        "  text-rendering: optimizeLegibility;"
    ) in styles
    assert ".editor-pip-tool-panel .step-label {\n  font-weight: 700;" in styles
    for pip_type_contract in (
        "--pip-readable-small-font: 15px;",
        "--pip-readable-regular-font: 16px;",
        "--pip-readable-strong-font: 17px;",
        ".editor-pip-tool-panel .pip-asset-status,",
        ".editor-pip-tool-panel .pip-generated-content > p,",
        ".editor-pip-tool-panel .pip-video-badge {",
    ):
        assert pip_type_contract in styles

    for timeline_contract in (
        "--frame-timeline-ruler-height: var(--timeline-ruler-height-compact);",
        "--cut-timeline-text-height: var(--timeline-row-height-compact);",
        "--editor-timeline-track-height: var(--timeline-base-track-height-compact);",
        "--editor-timeline-track-height: calc(",
        "--editor-timeline-track-height: var(--timeline-layer-track-height-compact);",
    ):
        assert timeline_contract in styles
    assert "const TIMELINE_ROW_HEIGHT = 22;" in timeline
    assert "const TIMELINE_EFFECT_BASE_HEIGHT = 52;" in timeline
    assert "rowCount * TIMELINE_ROW_HEIGHT" in timeline
    assert "TIMELINE_EFFECT_BASE_HEIGHT + rowCount * TIMELINE_ROW_HEIGHT" in timeline
