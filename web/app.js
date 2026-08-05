const MAX_FILE_SIZE = 1024 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ["mp4", "mov", "mkv", "webm"];
const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;

const uploadForm = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#videoFile");
const dropZone = document.querySelector("#dropZone");
const uploadPicker = document.querySelector("#uploadPicker");
const uploadPreview = document.querySelector("#uploadPreview");
const selectedVideoPreview = document.querySelector("#selectedVideoPreview");
const changeFileButton = document.querySelector("#changeFileButton");
const fileSummary = document.querySelector("#fileSummary");
const fileName = document.querySelector("#fileName");
const fileMeta = document.querySelector("#fileMeta");
const removeFileButton = document.querySelector("#removeFile");
const startButton = document.querySelector("#startButton");
const formError = document.querySelector("#formError");
const uploadCard = document.querySelector("#uploadCard");
const progressCard = document.querySelector("#progressCard");
const resultCard = document.querySelector("#resultCard");
const progressBar = document.querySelector("#progressBar");
const progressTrack = document.querySelector("#progressTrack");
const progressPercent = document.querySelector("#progressPercent");
const liveStatus = document.querySelector("#liveStatus");
const uploadStatus = document.querySelector("#uploadStatus");
const stepUpload = document.querySelector("#stepUpload");
const stepExtract = document.querySelector("#stepExtract");
const stepTranscribe = document.querySelector("#stepTranscribe");
const jobError = document.querySelector("#jobError");
const jobErrorText = document.querySelector("#jobErrorText");
const retryButton = document.querySelector("#retryButton");
const suggestionState = document.querySelector("#suggestionState");
const suggestionList = document.querySelector("#suggestionList");
const selectAllSuggestionsButton = document.querySelector(
  "#selectAllSuggestionsButton",
);
const noSpeechState = document.querySelector("#noSpeechState");
const noSpeechList = document.querySelector("#noSpeechList");
const selectAllNoSpeechButton = document.querySelector(
  "#selectAllNoSpeechButton",
);
const noSpeechCutSummary = document.querySelector("#noSpeechCutSummary");
const noSpeechCutSelectionDetail = document.querySelector(
  "#noSpeechCutSelectionDetail",
);
const segmentList = document.querySelector("#segmentList");
const segmentStructureStatus = document.querySelector("#segmentStructureStatus");
const cutDraftSaveStatus = document.querySelector("#cutDraftSaveStatus");
const segmentEditDialog = document.querySelector("#segmentEditDialog");
const segmentEditEyebrow = document.querySelector("#segmentEditEyebrow");
const segmentEditTime = document.querySelector("#segmentEditTime");
const segmentEditText = document.querySelector("#segmentEditText");
const segmentEditSelectionStatus = document.querySelector(
  "#segmentEditSelectionStatus",
);
const segmentEditClose = document.querySelector("#segmentEditClose");
const splitSegmentButton = document.querySelector("#splitSegmentButton");
const mergeSegmentUpButton = document.querySelector("#mergeSegmentUpButton");
const mergeSegmentDownButton = document.querySelector(
  "#mergeSegmentDownButton",
);
const clearSelectionButton = document.querySelector("#clearSelectionButton");
const generateCutButton = document.querySelector("#generateCutButton");
const cutHistoryName = document.querySelector("#cutHistoryName");
const outputCutSummary = document.querySelector("#outputCutSummary");
const outputCutSelectionDetail = document.querySelector(
  "#outputCutSelectionDetail",
);
const cutSummary = document.querySelector("#cutSummary");
const cutSelectionDetail = document.querySelector("#cutSelectionDetail");
const cutError = document.querySelector("#cutError");
const cutProgress = document.querySelector("#cutProgress");
const cutStatus = document.querySelector("#cutStatus");
const cutProgressTrack = document.querySelector("#cutProgressTrack");
const cutProgressBar = document.querySelector("#cutProgressBar");
const cutProgressPercent = document.querySelector("#cutProgressPercent");
const cutResult = document.querySelector("#cutResult");
const cutResultTitle = document.querySelector("#cut-result-title");
const cutDuration = document.querySelector("#cutDuration");
const editedVideo = document.querySelector("#editedVideo");
const downloadVideoButton = document.querySelector("#downloadVideoButton");
const continueArtButton = document.querySelector("#continueArtButton");
const skipToArtButton = document.querySelector("#skipToArtButton");
const directPipButton = document.querySelector("#directPipButton");
const continuePipButton = document.querySelector("#continuePipButton");
const directToolsPrompt = document.querySelector("#directToolsPrompt");
const restartProjectButton = document.querySelector("#restartProjectButton");
const cutOperationLock = document.querySelector("#cutOperationLock");
const cutOperationLockMessage = document.querySelector(
  "#cutOperationLockMessage",
);
const cutOperationLockTrack = document.querySelector(
  "#cutOperationLockTrack",
);
const cutOperationLockBar = document.querySelector("#cutOperationLockBar");
const cutOperationLockPercent = document.querySelector(
  "#cutOperationLockPercent",
);
const cutOperationLockTargets = [
  document.querySelector(".skip-link"),
  document.querySelector(".site-header"),
  document.querySelector("#main"),
  document.querySelector(".site-footer"),
].filter(Boolean);
const ambientCanvas = document.querySelector("#ambientCanvas");
const localSourceTab = document.querySelector("#localSourceTab");
const historySourceTab = document.querySelector("#historySourceTab");
const localSourcePanel = document.querySelector("#localSourcePanel");
const historySourcePanel = document.querySelector("#historySourcePanel");
const historyCountBadge = document.querySelector("#historyCountBadge");
const historyStatus = document.querySelector("#historyStatus");
const historyEmpty = document.querySelector("#historyEmpty");
const historyList = document.querySelector("#historyList");
const refreshHistoryButton = document.querySelector("#refreshHistoryButton");
const cutPreviewPlayer = document.querySelector("#cutPreviewPlayer");
const cutVideoStage = document.querySelector("#cutVideoStage");
const cutPreviewVideo = document.querySelector("#cutPreviewVideo");
const cutPreviewPlay = document.querySelector("#cutPreviewPlay");
const cutPreviewPlayIcon = document.querySelector("#cutPreviewPlayIcon");
const cutPreviewPauseIcon = document.querySelector("#cutPreviewPauseIcon");
const cutPreviewSeek = document.querySelector("#cutPreviewSeek");
const cutPreviewTime = document.querySelector("#cutPreviewTime");
const cutPreviewMute = document.querySelector("#cutPreviewMute");
const cutPreviewVolumeIcon = document.querySelector("#cutPreviewVolumeIcon");
const cutPreviewMutedIcon = document.querySelector("#cutPreviewMutedIcon");
const cutPreviewVolume = document.querySelector("#cutPreviewVolume");
const cutPreviewFullscreen = document.querySelector("#cutPreviewFullscreen");
const cutFrameTimeline = document.querySelector("#cutFrameTimeline");
const cutFrameTimelineScroll = document.querySelector("#cutFrameTimelineScroll");
const cutFrameTimelineTrack = document.querySelector("#cutFrameTimelineTrack");
const cutFrameTimelineRuler = document.querySelector("#cutFrameTimelineRuler");
const cutFrameTimelineText = document.querySelector("#cutFrameTimelineText");
const cutFrameTimelineThumbnails = document.querySelector(
  "#cutFrameTimelineThumbnails",
);
const cutFrameTimelineRanges = document.querySelector(
  "#cutFrameTimelineRanges",
);
const cutFrameTimelinePlayhead = document.querySelector(
  "#cutFrameTimelinePlayhead",
);
const cutFrameTimelineSeek = document.querySelector("#cutFrameTimelineSeek");
const cutFrameTimelineTime = document.querySelector("#cutFrameTimelineTime");
const cutFrameTimelineStatus = document.querySelector(
  "#cutFrameTimelineStatus",
);
const textEditorPreviewPane = document.querySelector("#textEditorPreviewPane");
const cutPreviewPanel = document.querySelector(".cut-preview-panel");
const textEditorOutputPanel = document.querySelector("#textOutputPanel");
const textEditorPanelStack = document.querySelector(".text-editor-panel-stack");
const textEditorTabs = [...document.querySelectorAll("[data-text-editor-tab]")];
const textEditorPanels = [
  ...document.querySelectorAll("[data-text-editor-panel]"),
];

if (textEditorPreviewPane && cutPreviewPanel) {
  textEditorPreviewPane.append(cutPreviewPanel);
}
if (textEditorOutputPanel) {
  textEditorOutputPanel.append(cutProgress, cutResult);
}

const CUT_TIMELINE_STEP = 1 / 30;
const CUT_TIMELINE_MIN_RANGE = 0.1;
const CUT_TIMELINE_DRAG_THRESHOLD = 5;
const CUT_SPEECH_BOUNDARY_EPSILON = 0.002;
const CUT_TIMELINE_TEXT_GAP_COVERAGE_MAX = 1.5;
const CUT_TIMELINE_THUMB_MIN = 8;
const CUT_TIMELINE_THUMB_MAX = 180;
const CUT_TIMELINE_MAJOR_TICK_WIDTH = 72;
const CUT_TIMELINE_MIN_PIXELS_PER_SECOND = 22;
const CUT_TIMELINE_TEXT_CHAR_WIDTH = 10;
const CUT_TIMELINE_TEXT_LINES = 2;

let selectedFile = null;
let selectedPreviewUrl = "";
let pollTimer = null;
let editPollTimer = null;
let currentJobId = null;
let currentSegments = [];
let currentEditableSegments = [];
let activeSegmentEditIndex = null;
let segmentOperationInFlight = false;
let currentSuggestions = [];
let currentNoSpeechSuggestions = [];
let cutControlsLocked = false;
let currentVideoDuration = 0;
let timelineDeleteRanges = [];
let generatedCutSelectionSignature = "";
let pendingCutSelectionSignature = "";
let selectedTimelineRangeId = null;
let timelineRangeInProgress = false;
let timelineRangeConfirmationOpen = false;
let nextTimelineRangeId = 1;
let cutTimelineBuildId = 0;
let cutTimelineSignature = "";
let cutTimelineRulerSignature = "";
let cutTimelineResizeTimer = null;
let noSpeechPreviewEnd = null;
let cutSelectionPreviewEnd = null;
let activeTranscriptSegmentIndex = -1;
let transcriptFollowScrollFrame = 0;
let cutDraftReady = false;
let cutDraftRevision = 0;
let cutDraftLastSignature = "";
let cutDraftSaveQueue = Promise.resolve();
let cutDraftNeedsServerSync = false;
let originalSourceActionsAllowed = true;
let historyVersions = [];
let editingHistoryId = null;
let historyBusyId = null;
const selectedRanges = new Map();
const selectedNoSpeechRanges = new Map();
const ignoredSuggestions = new Set();
const ignoredNoSpeechSuggestions = new Set();

function updateOriginalSourceActionsVisibility() {
  const visible = originalSourceActionsAllowed && !hasCutSelection();
  directToolsPrompt.hidden = !visible;
  directToolsPrompt.setAttribute("aria-hidden", String(!visible));
  for (const link of [skipToArtButton, directPipButton]) {
    link.tabIndex = visible ? 0 : -1;
    link.setAttribute("aria-disabled", String(!visible));
  }
}

function setOriginalSourceActionsAllowed(allowed) {
  originalSourceActionsAllowed = allowed;
  updateOriginalSourceActionsVisibility();
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 MB";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index > 1 ? 1 : 0)} ${units[index]}`;
}

function activateTextEditorPanel(panelName, { focus = false } = {}) {
  const activeTab = textEditorTabs.find(
    (tab) => tab.dataset.textEditorTab === panelName,
  );
  if (!activeTab) return;

  for (const tab of textEditorTabs) {
    const isActive = tab === activeTab;
    tab.setAttribute("aria-selected", String(isActive));
    tab.tabIndex = isActive ? 0 : -1;
  }
  for (const panel of textEditorPanels) {
    panel.hidden = panel.dataset.textEditorPanel !== panelName;
  }
  if (textEditorPanelStack) textEditorPanelStack.scrollTop = 0;
  if (focus) activeTab.focus();
}

function handleTextEditorTabKeydown(event) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const currentIndex = textEditorTabs.indexOf(event.currentTarget);
  if (currentIndex < 0) return;
  event.preventDefault();
  let nextIndex = currentIndex;
  if (event.key === "Home") nextIndex = 0;
  if (event.key === "End") nextIndex = textEditorTabs.length - 1;
  if (event.key === "ArrowLeft") {
    nextIndex = (currentIndex - 1 + textEditorTabs.length) % textEditorTabs.length;
  }
  if (event.key === "ArrowRight") {
    nextIndex = (currentIndex + 1) % textEditorTabs.length;
  }
  activateTextEditorPanel(textEditorTabs[nextIndex].dataset.textEditorTab, {
    focus: true,
  });
}

function formatTime(seconds) {
  const safeSeconds = Math.max(0, Math.round(Number(seconds) || 0));
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function formatPreciseTime(seconds) {
  const totalMilliseconds = Math.max(
    0,
    Math.round((Number(seconds) || 0) * 1000),
  );
  const minutes = Math.floor(totalMilliseconds / 60000);
  const secondsWithinMinute = (totalMilliseconds % 60000) / 1000;
  return `${String(minutes).padStart(2, "0")}:${secondsWithinMinute
    .toFixed(3)
    .padStart(6, "0")}`;
}

function formatDuration(seconds) {
  const value = Math.max(0, Number(seconds) || 0);
  if (value < 60) return `${value.toFixed(1)} 秒`;
  return `${Math.floor(value / 60)} 分 ${Math.round(value % 60)} 秒`;
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function formatCutRange(start, end) {
  return `${formatPreciseTime(start)}–${formatPreciseTime(end)}`;
}

function syncCorrectedWords() {
  const textByRange = new Map();
  for (const segment of [...currentSegments, ...currentEditableSegments]) {
    textByRange.set(
      rangeKey(segment.start, segment.end),
      String(segment.text || ""),
    );
    for (const token of getSegmentTokens(segment)) {
      textByRange.set(rangeKey(token.start, token.end), token.text);
    }
  }

  for (const [key, range] of [...selectedRanges.entries()]) {
    if (textByRange.has(key)) {
      selectedRanges.set(key, { ...range, text: textByRange.get(key) });
    } else {
      selectedRanges.delete(key);
    }
  }
  renderCutSegments();
}

function rangeKey(start, end) {
  return `${Number(start).toFixed(3)}-${Number(end).toFixed(3)}`;
}

function rememberJob(jobId) {
  if (!JOB_ID_PATTERN.test(jobId)) return;
  currentJobId = jobId;
  restartProjectButton.hidden = false;
  try {
    window.sessionStorage.setItem("currentTranscriptionJobId", jobId);
  } catch {
    // Query parameter recovery still works when browser storage is unavailable.
  }
  const url = new URL(window.location.href);
  if (url.searchParams.get("job") !== jobId) {
    url.searchParams.set("job", jobId);
    window.history.replaceState(null, "", url);
  }
  document.dispatchEvent(new CustomEvent("editor-suite:refresh"));
}

function forgetJob() {
  try {
    window.sessionStorage.removeItem("currentTranscriptionJobId");
  } catch {
    // Nothing else is required when browser storage is unavailable.
  }
  const url = new URL(window.location.href);
  if (url.searchParams.has("job")) {
    url.searchParams.delete("job");
    window.history.replaceState(null, "", url);
  }
  restartProjectButton.hidden = true;
  document.dispatchEvent(new CustomEvent("editor-suite:refresh"));
}

function getRememberedJobId() {
  const queryJobId = new URLSearchParams(window.location.search).get("job");
  if (queryJobId && JOB_ID_PATTERN.test(queryJobId)) return queryJobId;
  try {
    const storedJobId = window.sessionStorage.getItem(
      "currentTranscriptionJobId",
    );
    return storedJobId && JOB_ID_PATTERN.test(storedJobId)
      ? storedJobId
      : null;
  } catch {
    return null;
  }
}

function splitTextIntoCharacterTokens(text, start, end) {
  const characters = [...String(text || "")].filter(
    (character) => !/\p{P}|\s/u.test(character),
  );
  if (!characters.length) return [];

  const numericStart = Number(start);
  const numericEnd = Number(end);
  const safeStart = Number.isFinite(numericStart) ? numericStart : 0;
  const safeEnd = Number.isFinite(numericEnd)
    ? Math.max(safeStart, numericEnd)
    : safeStart;
  const duration = safeEnd - safeStart;

  return characters.map((character, index) => ({
    text: character,
    start: Number(
      (safeStart + (duration * index) / characters.length).toFixed(3),
    ),
    end: Number(
      (index === characters.length - 1
        ? safeEnd
        : safeStart + (duration * (index + 1)) / characters.length
      ).toFixed(3),
    ),
  }));
}

function getSegmentTokens(segment) {
  const words = Array.isArray(segment.words) ? segment.words : [];
  if (words.length) {
    return words.flatMap((word) =>
      splitTextIntoCharacterTokens(word.text, word.start, word.end),
    );
  }
  return splitTextIntoCharacterTokens(
    segment.text,
    segment.start,
    segment.end,
  );
}

const EDITABLE_CLAUSE_ENDINGS = /[\u3002\uff01\uff1f\u2026\uff0c\u3001\uff1b\uff1a.!?,;:]$/u;
const EDITABLE_BREAK_BEFORE = [
  "\u4f46\u662f",
  "\u800c\u662f",
  "\u4e0d\u8fc7",
  "\u7136\u800c",
  "\u6240\u4ee5",
  "\u56e0\u4e3a",
  "\u7531\u4e8e",
  "\u4e8e\u662f",
  "\u5982\u679c",
  "\u5373\u4f7f",
  "\u53ea\u8981",
  "\u54ea\u6015",
  "\u5176\u5b9e",
  "\u5c24\u5176",
  "\u540c\u65f6",
  "\u7136\u540e",
];

function buildFallbackEditableSegments(segments) {
  const editable = [];
  const append = (sourceIndex, words) => {
    if (!words.length) return;
    const text = words.map((word) => String(word.text || "")).join("");
    if (!text.trim()) return;
    editable.push({
      id: editable.length,
      sourceSegmentIndex: sourceIndex,
      start: Number(words[0].start),
      end: Number(words.at(-1).end),
      text,
      words: words.map((word) => ({ ...word })),
    });
  };

  segments.forEach((segment, sourceIndex) => {
    const words = Array.isArray(segment.words) && segment.words.length
      ? segment.words
      : [{ text: segment.text, start: segment.start, end: segment.end }];
    let group = [];
    words.forEach((word) => {
      const previous = group.at(-1);
      const groupText = group.map((item) => String(item.text || "")).join("");
      const gap = previous
        ? Number(word.start) - Number(previous.end)
        : 0;
      const breakBefore = previous && (
        gap >= 0.32 || (
          Array.from(groupText.replace(/\s/g, "")).length >= 4 &&
          EDITABLE_BREAK_BEFORE.some((prefix) =>
            String(word.text || "").trimStart().startsWith(prefix),
          )
        )
      );
      if (breakBefore) {
        append(sourceIndex, group);
        group = [];
      }
      group.push(word);
      if (EDITABLE_CLAUSE_ENDINGS.test(String(word.text || "").trim())) {
        append(sourceIndex, group);
        group = [];
      }
    });
    append(sourceIndex, group);
  });
  return editable;
}

function resolveEditableSegments(segments, editableSegments) {
  return Array.isArray(editableSegments) && editableSegments.length
    ? editableSegments
    : buildFallbackEditableSegments(segments);
}

function renderCutSegments() {
  activeTranscriptSegmentIndex = -1;
  segmentList.replaceChildren();
  currentEditableSegments.forEach((segment, segmentIndex) => {
    const segmentStart = Number(segment.start);
    const segmentEnd = Number(segment.end);
    const hasValidRange =
      Number.isFinite(segmentStart) &&
      Number.isFinite(segmentEnd) &&
      segmentEnd > segmentStart;
    const item = document.createElement("li");
    item.className = "segment-item is-editable";
    item.dataset.segmentIndex = String(segmentIndex);

    const selectSegmentButton = document.createElement("button");
    selectSegmentButton.type = "button";
    selectSegmentButton.className = "segment-toggle";
    selectSegmentButton.dataset.segmentIndex = String(segmentIndex);
    selectSegmentButton.setAttribute("aria-pressed", "false");
    selectSegmentButton.setAttribute(
      "aria-label",
      `删除第 ${segmentIndex + 1} 段`,
    );
    selectSegmentButton.disabled = !hasValidRange;

    const time = document.createElement("time");
    time.className = "segment-time";
    time.textContent = formatTime(segment.start);
    time.setAttribute(
      "aria-label",
      `从 ${formatPreciseTime(segment.start)} 到 ${formatPreciseTime(segment.end)}`,
    );

    const timeColumn = document.createElement("span");
    timeColumn.className = "segment-time-column";
    const currentBadge = document.createElement("span");
    currentBadge.className = "segment-current-badge";
    currentBadge.textContent = "播放中";
    currentBadge.setAttribute("aria-hidden", "true");
    currentBadge.hidden = true;
    timeColumn.append(time, currentBadge);

    const segmentText = document.createElement("button");
    segmentText.type = "button";
    segmentText.className = "segment-text";
    segmentText.textContent = String(segment.text || "暂无识别文字");
    segmentText.setAttribute(
      "aria-label",
      `编辑第 ${segmentIndex + 1} 段分段：${String(segment.text || "暂无识别文字")}`,
    );

    item.append(selectSegmentButton, timeColumn, segmentText);
    segmentList.append(item);
  });
  updateCutSegmentTimestamps();
}

function getLiveEditedSegmentTiming(
  segment,
  spans = getEditedTimelineSpans(),
) {
  const segmentStart = Number(segment.start) || 0;
  const segmentEnd = Number(segment.end) || segmentStart;
  const parts = spans
    .map((span) => {
      const sourceStart = Math.max(segmentStart, span.sourceStart);
      const sourceEnd = Math.min(segmentEnd, span.sourceEnd);
      if (sourceEnd <= sourceStart) return null;
      return {
        editedStart: span.editedStart + sourceStart - span.sourceStart,
        editedEnd: span.editedStart + sourceEnd - span.sourceStart,
      };
    })
    .filter(Boolean);
  if (parts.length === 0) return null;
  return {
    start: parts[0].editedStart,
    end: parts.at(-1).editedEnd,
  };
}

function updateCutInspectorTimestamps() {
  const spans = getEditedTimelineSpans();
  for (const card of suggestionList.querySelectorAll(".suggestion-card")) {
    const suggestion = currentSuggestions.find(
      (item) => item.id === card.dataset.suggestionId,
    );
    const time = card.querySelector(".suggestion-time");
    if (!suggestion || !time) continue;
    if (isSuggestionSelected(suggestion)) {
      time.textContent = "已删除";
      continue;
    }
    time.textContent =
      `${formatPreciseTime(sourceTimeToEditedTime(suggestion.start, spans))} — ` +
      `${formatPreciseTime(sourceTimeToEditedTime(suggestion.end, spans))}`;
  }
  for (const card of noSpeechList?.querySelectorAll(".no-speech-card") || []) {
    const suggestion = currentNoSpeechSuggestions.find(
      (item) => item.id === card.dataset.noSpeechId,
    );
    const time = card.querySelector(".no-speech-time");
    if (!suggestion || !time) continue;
    if (isNoSpeechSelected(suggestion)) {
      time.textContent = "已删除";
      continue;
    }
    time.textContent =
      `${formatPreciseTime(sourceTimeToEditedTime(suggestion.start, spans))} — ` +
      `${formatPreciseTime(sourceTimeToEditedTime(suggestion.end, spans))}`;
  }
}

function updateCutSegmentTimestamps() {
  const spans = getEditedTimelineSpans();
  segmentList
    .querySelectorAll(".segment-item[data-segment-index]")
    .forEach((item) => {
      const segmentIndex = Number(item.dataset.segmentIndex);
      const segment = currentEditableSegments[segmentIndex];
      const time = item.querySelector(".segment-time");
      if (!segment || !time) return;
      const timing = getLiveEditedSegmentTiming(segment, spans);
      item.classList.toggle("is-removed-from-timeline", !timing);
      if (!timing) {
        time.textContent = "已删除";
        time.setAttribute("aria-label", "此段已从剪辑时间轴删除");
        return;
      }
      time.textContent = formatTime(timing.start);
      time.setAttribute(
        "aria-label",
        `剪辑后从 ${formatPreciseTime(timing.start)} 到 ${formatPreciseTime(timing.end)}`,
      );
    });
  updateActiveTranscriptSegment(undefined, { follow: false });
}

function setSegmentStructureStatus(message, tone = "neutral") {
  segmentStructureStatus.textContent = message;
  segmentStructureStatus.dataset.tone = tone;
}

function getSegmentSelectionOffsets() {
  const start = Number(segmentEditText.selectionStart) || 0;
  const end = Number(segmentEditText.selectionEnd) || 0;
  return {
    start: Array.from(segmentEditText.value.slice(0, start)).length,
    end: Array.from(segmentEditText.value.slice(0, end)).length,
    text: segmentEditText.value.slice(start, end),
  };
}

function updateSegmentEditSelection() {
  const selection = getSegmentSelectionOffsets();
  const selectedCharacters = Array.from(selection.text.trim()).length;
  const hasPartialSelection =
    selectedCharacters > 0 &&
    (selection.start > 0 || selection.end < Array.from(segmentEditText.value).length);
  splitSegmentButton.disabled = segmentOperationInFlight || !hasPartialSelection;
  segmentEditSelectionStatus.textContent = hasPartialSelection
    ? `已选择 ${selectedCharacters} 个字，将拆分为单独一行`
    : "尚未选择部分文字";
  segmentEditSelectionStatus.dataset.ready = String(hasPartialSelection);
}

function closeSegmentEditDialog() {
  if (!segmentEditDialog.open || segmentOperationInFlight) return;
  segmentEditDialog.classList.remove("is-visible");
  segmentEditDialog.close();
  activeSegmentEditIndex = null;
}

function openSegmentEditDialog(segmentIndex) {
  if (cutControlsLocked || segmentOperationInFlight) return;
  const segment = currentEditableSegments[segmentIndex];
  if (!segment) return;
  const timing = getLiveEditedSegmentTiming(segment);
  if (!timing) {
    setSegmentStructureStatus("该段已从当前剪辑时间轴删除。", "error");
    return;
  }
  if (selectedRanges.has(rangeKey(segment.start, segment.end))) {
    setSegmentStructureStatus("该段已删除，当前剪辑方案内不可恢复或调整。", "error");
    return;
  }
  activeSegmentEditIndex = segmentIndex;
  segmentEditEyebrow.textContent = `段落 ${String(segmentIndex + 1).padStart(2, "0")}`;
  segmentEditTime.textContent =
    `${formatPreciseTime(timing.start)} — ${formatPreciseTime(timing.end)}`;
  segmentEditText.value = String(segment.text || "");
  segmentEditText.setSelectionRange(0, 0);
  mergeSegmentUpButton.disabled = segmentIndex === 0;
  mergeSegmentDownButton.disabled =
    segmentIndex === currentEditableSegments.length - 1;
  splitSegmentButton.disabled = true;
  segmentEditSelectionStatus.textContent = "尚未选择部分文字";
  segmentEditSelectionStatus.dataset.ready = "false";
  segmentEditDialog.showModal();
  window.requestAnimationFrame(() => {
    segmentEditDialog.classList.add("is-visible");
    segmentEditText.focus();
  });
}

function setSegmentOperationBusy(busy) {
  segmentOperationInFlight = busy;
  segmentEditDialog.classList.toggle("is-busy", busy);
  segmentEditClose.disabled = busy;
  mergeSegmentUpButton.disabled =
    busy || activeSegmentEditIndex === 0;
  mergeSegmentDownButton.disabled =
    busy || activeSegmentEditIndex === currentEditableSegments.length - 1;
  updateSegmentEditSelection();
}

async function applyEditableSegmentOperation(action) {
  if (segmentOperationInFlight || activeSegmentEditIndex === null) return;
  const payload = {
    segmentIndex: activeSegmentEditIndex,
    action,
  };
  if (action === "split") {
    const selection = getSegmentSelectionOffsets();
    payload.selectionStart = selection.start;
    payload.selectionEnd = selection.end;
  }

  setSegmentOperationBusy(true);
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(currentJobId)}/editable-segments`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "分段调整失败，请重试。");
    }
    currentEditableSegments = result.editableSegments || currentEditableSegments;
    syncCorrectedWords();
    renderCutTimelineTextSegments();
    updateSelectionSummary();
    setSegmentOperationBusy(false);
    closeSegmentEditDialog();
    setSegmentStructureStatus(
      action === "split" ? "已按所选文字完成拆分" : "已完成段落合并",
      "success",
    );
  } catch (error) {
    setSegmentOperationBusy(false);
    segmentEditSelectionStatus.textContent = error.message;
    segmentEditSelectionStatus.dataset.ready = "error";
  }
}

function getSuggestionRanges(suggestion) {
  return Array.isArray(suggestion.ranges)
    ? suggestion.ranges.filter(
        (range) =>
          Number.isFinite(Number(range.start)) &&
          Number.isFinite(Number(range.end)) &&
          Number(range.end) > Number(range.start),
      )
    : [];
}

function isSuggestionSelected(suggestion) {
  const ranges = getSuggestionRanges(suggestion);
  return (
    ranges.length > 0 &&
    ranges.every((range) =>
      selectedRanges.has(rangeKey(range.start, range.end)),
    )
  );
}

function updateSuggestionStates() {
  let deletedCount = 0;
  for (const card of suggestionList.querySelectorAll(".suggestion-card")) {
    const suggestion = currentSuggestions.find(
      (item) => item.id === card.dataset.suggestionId,
    );
    if (!suggestion) continue;

    const ignored = ignoredSuggestions.has(suggestion.id);
    const marked = isSuggestionSelected(suggestion);
    if (marked) deletedCount += 1;
    card.classList.toggle("is-marked", marked);
    card.classList.toggle("is-ignored", ignored);

    const applyButton = card.querySelector('[data-action="apply"]');
    const ignoreButton = card.querySelector('[data-action="ignore"]');
    const status = card.querySelector(".suggestion-card-status");
    applyButton.disabled = cutControlsLocked || ignored || marked;
    applyButton.classList.toggle("is-active", marked);
    applyButton.setAttribute("aria-pressed", String(marked));
    applyButton.textContent = marked ? "已删除" : "删除";
    ignoreButton.disabled = cutControlsLocked || marked;
    ignoreButton.setAttribute("aria-pressed", String(ignored));
    ignoreButton.textContent = ignored ? "恢复建议" : "忽略";
    status.textContent = ignored
      ? "已忽略"
      : marked
        ? "已从剪辑时间轴删除"
        : "等待确认";
  }

  if (currentSuggestions.length > 0) {
    suggestionState.textContent =
      deletedCount > 0
        ? `共 ${currentSuggestions.length} 条建议，已删除 ${deletedCount} 条。`
        : `发现 ${currentSuggestions.length} 条疑似问题，请逐条确认。`;
  }

  const remainingSuggestions = currentSuggestions.filter(
    (suggestion) =>
      !isSuggestionSelected(suggestion) &&
      !ignoredSuggestions.has(suggestion.id),
  );
  selectAllSuggestionsButton.hidden = currentSuggestions.length === 0;
  selectAllSuggestionsButton.disabled =
    cutControlsLocked || remainingSuggestions.length === 0;
  selectAllSuggestionsButton.classList.toggle(
    "is-active",
    remainingSuggestions.length === 0,
  );
  selectAllSuggestionsButton.setAttribute("aria-pressed", "false");
  selectAllSuggestionsButton.querySelector("span").textContent =
    remainingSuggestions.length > 0
      ? "一键删除"
      : deletedCount === currentSuggestions.length
        ? "已全部删除"
        : "无待删建议";
}

function renderSuggestions(suggestions, status) {
  suggestionList.replaceChildren();
  ignoredSuggestions.clear();
  currentSuggestions = Array.isArray(suggestions)
    ? suggestions.filter(
        (suggestion) =>
          suggestion &&
          typeof suggestion.id === "string" &&
          getSuggestionRanges(suggestion).length > 0,
      )
    : [];

  suggestionState.classList.remove("is-empty", "is-warning");
  selectAllSuggestionsButton.hidden =
    status !== "completed" || currentSuggestions.length === 0;
  if (status !== "completed") {
    suggestionState.classList.add("is-warning");
    suggestionState.textContent =
      "本次 AI 初筛暂不可用，不影响下方手动选择和剪辑。";
    return;
  }
  if (currentSuggestions.length === 0) {
    suggestionState.classList.add("is-empty");
    suggestionState.textContent =
      "没有发现明显口误，建议仍由你快速复核全文。";
    return;
  }

  for (const suggestion of currentSuggestions) {
    const item = document.createElement("li");
    item.className = "suggestion-card";
    item.dataset.suggestionId = suggestion.id;

    const heading = document.createElement("div");
    heading.className = "suggestion-card-heading";
    const labels = document.createElement("div");
    labels.className = "suggestion-labels";
    const type = document.createElement("span");
    type.className = "suggestion-type";
    type.textContent = suggestion.type;
    const confidence = document.createElement("span");
    confidence.className = "suggestion-confidence";
    confidence.textContent =
      `置信度 ${Math.round(Number(suggestion.confidence) * 100)}%`;
    labels.append(type, confidence);
    const time = document.createElement("span");
    time.className = "suggestion-time";
    time.textContent =
      `${formatPreciseTime(suggestion.start)} — ${formatPreciseTime(suggestion.end)}`;
    heading.append(labels, time);

    const quote = document.createElement("p");
    quote.className = "suggestion-quote";
    quote.textContent = `“${suggestion.text}”`;
    const reason = document.createElement("p");
    reason.className = "suggestion-reason";
    reason.textContent = suggestion.reason;

    const footer = document.createElement("div");
    footer.className = "suggestion-card-footer";
    const cardStatus = document.createElement("span");
    cardStatus.className = "suggestion-card-status";
    cardStatus.setAttribute("aria-live", "polite");
    const actions = document.createElement("div");
    actions.className = "suggestion-actions";
    const applyButton = document.createElement("button");
    applyButton.type = "button";
    applyButton.className = "suggestion-action suggestion-mark-button";
    applyButton.dataset.action = "apply";
    const ignoreButton = document.createElement("button");
    ignoreButton.type = "button";
    ignoreButton.className = "suggestion-action suggestion-ignore-button";
    ignoreButton.dataset.action = "ignore";
    actions.append(applyButton, ignoreButton);
    footer.append(cardStatus, actions);

    item.append(heading, quote, reason, footer);
    suggestionList.append(item);
  }
  updateSuggestionStates();
}

function getNoSpeechRange(suggestion) {
  if (!suggestion) return null;
  const start = Number(suggestion.start);
  const end = Number(suggestion.end);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return null;
  }
  return {
    id: String(suggestion.id || rangeKey(start, end)),
    start,
    end,
    source: "no-speech",
  };
}

function isNoSpeechSelected(suggestion) {
  const range = getNoSpeechRange(suggestion);
  return Boolean(range && selectedNoSpeechRanges.has(range.id));
}

function setActionLabel(button, label) {
  const labelElement = button?.querySelector(".button-label");
  if (labelElement) labelElement.textContent = label;
}

function updateNoSpeechStates() {
  if (!noSpeechList || !selectAllNoSpeechButton || !noSpeechState) return;
  let deletedCount = 0;
  for (const card of noSpeechList.querySelectorAll(".no-speech-card")) {
    const suggestion = currentNoSpeechSuggestions.find(
      (item) => item.id === card.dataset.noSpeechId,
    );
    if (!suggestion) continue;

    const marked = isNoSpeechSelected(suggestion);
    const ignored = ignoredNoSpeechSuggestions.has(suggestion.id);
    const protectedRange = Boolean(suggestion.protected);
    if (marked) deletedCount += 1;
    card.classList.toggle("is-marked", marked);
    card.classList.toggle("is-ignored", ignored);
    card.classList.toggle("is-protected", protectedRange);

    const applyButton = card.querySelector('[data-action="apply"]');
    const ignoreButton = card.querySelector('[data-action="ignore"]');
    const previewButton = card.querySelector('[data-action="preview"]');
    const status = card.querySelector(".no-speech-card-status");
    const canDelete = suggestion.deletable !== false;
    applyButton.disabled = cutControlsLocked || ignored || marked || !canDelete;
    applyButton.classList.toggle("is-active", marked);
    applyButton.setAttribute("aria-pressed", String(marked));
    setActionLabel(
      applyButton,
      marked ? "已删除" : protectedRange ? "确认删除" : "删除",
    );
    ignoreButton.disabled = cutControlsLocked || marked;
    ignoreButton.setAttribute("aria-pressed", String(ignored));
    setActionLabel(ignoreButton, ignored ? "恢复建议" : "忽略");
    previewButton.disabled = cutControlsLocked || marked;
    status.textContent = !canDelete
      ? "整段无文字，不能删除全部视频"
      : ignored
        ? "已忽略"
        : marked
          ? "已从剪辑时间轴删除"
          : protectedRange
            ? "已保护，需要手动确认"
            : "等待试听确认";
  }

  const protectedCount = currentNoSpeechSuggestions.filter(
    (suggestion) => suggestion.protected,
  ).length;
  noSpeechState.classList.toggle("is-marked", deletedCount > 0);
  noSpeechState.textContent =
    deletedCount > 0
      ? `发现 ${currentNoSpeechSuggestions.length} 处长时间无文字片段，已删除 ${deletedCount} 处。`
      : `发现 ${currentNoSpeechSuggestions.length} 处长时间无文字片段${protectedCount ? `，其中 ${protectedCount} 处片头或片尾已默认保护` : ""}。`;

  const bulkEligible = currentNoSpeechSuggestions.filter(
    (suggestion) =>
      !suggestion.protected &&
      suggestion.deletable !== false,
  );
  const bulkCandidates = bulkEligible.filter(
    (suggestion) =>
      !ignoredNoSpeechSuggestions.has(suggestion.id) &&
      !isNoSpeechSelected(suggestion),
  );
  const bulkDeletedCount = bulkEligible.filter((suggestion) =>
    isNoSpeechSelected(suggestion),
  ).length;
  selectAllNoSpeechButton.hidden = bulkEligible.length === 0;
  selectAllNoSpeechButton.disabled =
    cutControlsLocked || bulkCandidates.length === 0;
  selectAllNoSpeechButton.classList.toggle(
    "is-active",
    bulkCandidates.length === 0,
  );
  selectAllNoSpeechButton.setAttribute("aria-pressed", "false");
  setActionLabel(
    selectAllNoSpeechButton,
    bulkCandidates.length > 0
      ? "一键删除可删片段"
      : bulkDeletedCount === bulkEligible.length
        ? "可删片段已删除"
        : "无待删片段",
  );
}

function noSpeechKindLabel(suggestion) {
  if (suggestion.kind === "leading") return "片头保护";
  if (suggestion.kind === "trailing") return "片尾保护";
  if (suggestion.kind === "full") return "整段保护";
  return "中段空白";
}

function noSpeechAudioLabel(suggestion) {
  if (suggestion.audioState === "quiet") return "音频安静";
  if (suggestion.audioState === "ambient") return "检测到背景声";
  return "音频待复核";
}

function createNoSpeechAction(action, icon, label, className = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `no-speech-action ${className}`.trim();
  button.dataset.action = action;
  const iconElement = document.createElement("iconify-icon");
  iconElement.setAttribute("icon", icon);
  iconElement.setAttribute("aria-hidden", "true");
  const labelElement = document.createElement("span");
  labelElement.className = "button-label";
  labelElement.textContent = label;
  button.append(iconElement, labelElement);
  return button;
}

function renderNoSpeechSuggestions(suggestions, status) {
  if (!noSpeechList || !selectAllNoSpeechButton || !noSpeechState) return;
  noSpeechList.replaceChildren();
  selectedNoSpeechRanges.clear();
  ignoredNoSpeechSuggestions.clear();
  currentNoSpeechSuggestions = Array.isArray(suggestions)
    ? suggestions
        .filter((suggestion) => getNoSpeechRange(suggestion))
        .map((suggestion) => ({
          ...suggestion,
          id: getNoSpeechRange(suggestion).id,
        }))
    : [];

  noSpeechState.classList.remove("is-empty", "is-warning", "is-marked");
  selectAllNoSpeechButton.hidden = true;
  if (status !== "completed") {
    noSpeechState.classList.add("is-warning");
    noSpeechState.textContent =
      "本次无文字片段检测暂不可用，你仍可在时间轴上手动选择删除区间。";
    return;
  }
  if (currentNoSpeechSuggestions.length === 0) {
    noSpeechState.classList.add("is-empty");
    noSpeechState.textContent =
      "没有发现超过 1.5 秒的无文字片段，短暂停顿已自动保留。";
    return;
  }

  for (const suggestion of currentNoSpeechSuggestions) {
    const item = document.createElement("li");
    item.className = "no-speech-card";
    item.dataset.noSpeechId = suggestion.id;

    const heading = document.createElement("div");
    heading.className = "no-speech-card-heading";
    const labels = document.createElement("div");
    labels.className = "no-speech-labels";
    const kind = document.createElement("span");
    kind.className = "no-speech-kind";
    kind.textContent = noSpeechKindLabel(suggestion);
    const audio = document.createElement("span");
    audio.className = `no-speech-audio is-${suggestion.audioState || "unknown"}`;
    audio.textContent = noSpeechAudioLabel(suggestion);
    labels.append(kind, audio);
    const time = document.createElement("span");
    time.className = "no-speech-time";
    time.textContent =
      `${formatPreciseTime(suggestion.start)} — ${formatPreciseTime(suggestion.end)}`;
    heading.append(labels, time);

    const description = document.createElement("p");
    description.className = "no-speech-description";
    const seconds = Math.max(
      0,
      Number(suggestion.end) - Number(suggestion.start),
    );
    description.textContent =
      `${seconds.toFixed(1)} 秒无识别文字。${suggestion.reason || "请先试听，再决定是否删除。"}`;

    const footer = document.createElement("div");
    footer.className = "no-speech-card-footer";
    const cardStatus = document.createElement("span");
    cardStatus.className = "no-speech-card-status";
    cardStatus.setAttribute("aria-live", "polite");
    const actions = document.createElement("div");
    actions.className = "no-speech-actions";
    actions.append(
      createNoSpeechAction(
        "preview",
        "ph:play-circle-bold",
        "试听",
        "no-speech-preview-button",
      ),
      createNoSpeechAction(
        "apply",
        "ph:scissors-bold",
        "删除",
        "no-speech-mark-button",
      ),
      createNoSpeechAction(
        "ignore",
        "ph:eye-slash-bold",
        "忽略",
        "no-speech-ignore-button",
      ),
    );
    footer.append(cardStatus, actions);
    item.append(heading, description, footer);
    noSpeechList.append(item);
  }
  updateNoSpeechStates();
}

function mergeCutRanges(ranges) {
  const normalized = ranges
    .map(({ start, end }) => ({ start: Number(start), end: Number(end) }))
    .filter(
      ({ start, end }) =>
        Number.isFinite(start) && Number.isFinite(end) && end > start,
    )
    .sort((a, b) => a.start - b.start);
  const merged = [];
  for (const range of normalized) {
    const previous = merged.at(-1);
    if (previous && range.start <= previous.end + 0.12) {
      previous.end = Math.max(previous.end, range.end);
    } else {
      merged.push({ ...range });
    }
  }
  return merged;
}

function getRecognizedWordRanges() {
  const sourceSegments = currentSegments.length
    ? currentSegments
    : currentEditableSegments;
  const ranges = [];

  for (const segment of sourceSegments) {
    const words = Array.isArray(segment.words)
      ? segment.words.filter((word) => String(word.text || "").trim())
      : [];
    const speechParts = words.length ? words : [segment];
    for (const part of speechParts) {
      const start = Number(part.start);
      const end = Number(part.end);
      if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
        ranges.push({
          start,
          end,
          text: String(part.text || segment.text || ""),
        });
      }
    }
  }

  ranges.sort((a, b) => a.start - b.start || a.end - b.end);
  return ranges;
}

function getRecognizedSpeechRanges() {
  const normalized = [];
  for (const range of getRecognizedWordRanges()) {
    const previous = normalized.at(-1);
    if (
      previous &&
      range.start <= previous.end + CUT_SPEECH_BOUNDARY_EPSILON
    ) {
      previous.end = Math.max(previous.end, range.end);
    } else {
      normalized.push({ ...range });
    }
  }
  return normalized;
}

function expandRangeToAdjacentSilence(range) {
  const total = cutTimelineDuration();
  const originalStart = clamp(Number(range?.start) || 0, 0, total);
  const originalEnd = clamp(
    Number(range?.end) || originalStart,
    originalStart,
    total,
  );
  const expanded = {
    ...range,
    start: originalStart,
    end: originalEnd,
    originalStart,
    originalEnd,
    adjacentSilenceBefore: 0,
    adjacentSilenceAfter: 0,
  };
  const speechRanges = getRecognizedSpeechRanges();
  if (originalEnd <= originalStart || speechRanges.length === 0) {
    return expanded;
  }

  const startsInsideSpeech = speechRanges.some(
    (speech) =>
      originalStart > speech.start + CUT_SPEECH_BOUNDARY_EPSILON &&
      originalStart < speech.end - CUT_SPEECH_BOUNDARY_EPSILON,
  );
  const endsInsideSpeech = speechRanges.some(
    (speech) =>
      originalEnd > speech.start + CUT_SPEECH_BOUNDARY_EPSILON &&
      originalEnd < speech.end - CUT_SPEECH_BOUNDARY_EPSILON,
  );

  if (!startsInsideSpeech) {
    const previousSpeech = speechRanges.findLast(
      (speech) =>
        speech.end <= originalStart + CUT_SPEECH_BOUNDARY_EPSILON,
    );
    expanded.start = previousSpeech ? previousSpeech.end : 0;
  }
  if (!endsInsideSpeech) {
    const nextSpeech = speechRanges.find(
      (speech) =>
        speech.start >= originalEnd - CUT_SPEECH_BOUNDARY_EPSILON,
    );
    expanded.end = nextSpeech ? nextSpeech.start : total;
  }

  expanded.start = Math.min(expanded.start, originalStart);
  expanded.end = Math.max(expanded.end, originalEnd);
  expanded.adjacentSilenceBefore = originalStart - expanded.start;
  expanded.adjacentSilenceAfter = expanded.end - originalEnd;
  return expanded;
}

function alignManualRangeToTranscript(range) {
  const total = cutTimelineDuration();
  const originalStart = clamp(Number(range?.start) || 0, 0, total);
  const originalEnd = clamp(
    Number(range?.end) || originalStart,
    originalStart,
    total,
  );
  if (originalEnd <= originalStart) return null;

  const words = getRecognizedWordRanges();
  if (words.length === 0) {
    return {
      ...range,
      start: originalStart,
      end: originalEnd,
      originalStart,
      originalEnd,
      adjacentSilenceBefore: 0,
      adjacentSilenceAfter: 0,
    };
  }

  const selectedWords = new Set(
    words.filter((word) => {
      const midpoint = word.start + (word.end - word.start) / 2;
      return (
        midpoint >= originalStart - CUT_SPEECH_BOUNDARY_EPSILON &&
        midpoint <= originalEnd + CUT_SPEECH_BOUNDARY_EPSILON
      );
    }),
  );
  let start = selectedWords.size
    ? Math.min(originalStart, ...[...selectedWords].map((word) => word.start))
    : originalStart;
  let end = selectedWords.size
    ? Math.max(originalEnd, ...[...selectedWords].map((word) => word.end))
    : originalEnd;

  for (const word of words) {
    if (selectedWords.has(word)) continue;
    if (
      word.start < start - CUT_SPEECH_BOUNDARY_EPSILON &&
      word.end > start + CUT_SPEECH_BOUNDARY_EPSILON
    ) {
      start = Math.max(start, word.end);
    }
    if (
      word.start < end - CUT_SPEECH_BOUNDARY_EPSILON &&
      word.end > end + CUT_SPEECH_BOUNDARY_EPSILON
    ) {
      end = Math.min(end, word.start);
    }
  }

  if (end <= start) return null;
  return {
    ...range,
    start,
    end,
    originalStart,
    originalEnd,
    adjacentSilenceBefore: 0,
    adjacentSilenceAfter: 0,
  };
}

function getMergedTextSelection() {
  return mergeCutRanges([...selectedRanges.values()]);
}

function getCommittedTimelineDeleteRanges() {
  return timelineDeleteRanges.filter(
    ({ id }) =>
      !timelineRangeInProgress || id !== selectedTimelineRangeId,
  );
}

function getMergedSelection() {
  return mergeCutRanges([
    ...getMergedTextSelection(),
    ...selectedNoSpeechRanges.values(),
    ...getCommittedTimelineDeleteRanges(),
  ]);
}

function getEditedTimelineSpans() {
  const sourceTotal = cutTimelineDuration();
  if (sourceTotal <= 0) return [];
  const displayedDeletedRanges = getMergedSelection();
  const deletedRanges = displayedDeletedRanges
    .map(({ start, end }) => ({
      start: clamp(Number(start) || 0, 0, sourceTotal),
      end: clamp(Number(end) || 0, 0, sourceTotal),
    }))
    .filter(({ start, end }) => end > start);
  const spans = [];
  let sourceCursor = 0;
  let editedCursor = 0;
  for (const range of deletedRanges) {
    if (range.start > sourceCursor) {
      const duration = range.start - sourceCursor;
      spans.push({
        sourceStart: sourceCursor,
        sourceEnd: range.start,
        editedStart: editedCursor,
        editedEnd: editedCursor + duration,
      });
      editedCursor += duration;
    }
    sourceCursor = Math.max(sourceCursor, range.end);
  }
  if (sourceCursor < sourceTotal) {
    spans.push({
      sourceStart: sourceCursor,
      sourceEnd: sourceTotal,
      editedStart: editedCursor,
      editedEnd: editedCursor + sourceTotal - sourceCursor,
    });
  }
  return spans;
}

function editedCutTimelineDuration(spans = getEditedTimelineSpans()) {
  return spans.at(-1)?.editedEnd || 0;
}

function sourceTimeToEditedTime(seconds, spans = getEditedTimelineSpans()) {
  const sourceTime = clamp(Number(seconds) || 0, 0, cutTimelineDuration());
  for (const span of spans) {
    if (sourceTime < span.sourceStart) return span.editedStart;
    if (sourceTime <= span.sourceEnd) {
      return span.editedStart + sourceTime - span.sourceStart;
    }
  }
  return editedCutTimelineDuration(spans);
}

function editedTimeToSourceTime(seconds, spans = getEditedTimelineSpans()) {
  const editedTotal = editedCutTimelineDuration(spans);
  const editedTime = clamp(Number(seconds) || 0, 0, editedTotal);
  for (const span of spans) {
    if (editedTime < span.editedEnd - 0.0001) {
      return span.sourceStart + editedTime - span.editedStart;
    }
  }
  return spans.at(-1)?.sourceEnd || 0;
}

function getEditableSegmentCoverageEnd(segmentIndex) {
  const segment = currentEditableSegments[segmentIndex];
  const segmentEnd = Number(segment?.end) || Number(segment?.start) || 0;
  const nextStart = Number(currentEditableSegments[segmentIndex + 1]?.start);
  if (
    !Number.isFinite(nextStart) ||
    nextStart <= segmentEnd ||
    nextStart - segmentEnd > CUT_TIMELINE_TEXT_GAP_COVERAGE_MAX
  ) {
    return segmentEnd;
  }
  return nextStart;
}

function getRetainedSegmentParts(
  segment,
  spans = getEditedTimelineSpans(),
  coverageEnd = Number(segment.end) || Number(segment.start) || 0,
) {
  const segmentStart = Number(segment.start) || 0;
  const segmentEnd = Number(segment.end) || segmentStart;
  const displayEnd = Math.max(segmentEnd, Number(coverageEnd) || segmentEnd);
  const words = Array.isArray(segment.words) ? segment.words : [];
  const parts = [];
  for (const span of spans) {
    const sourceStart = Math.max(segmentStart, span.sourceStart);
    const sourceEnd = Math.min(displayEnd, span.sourceEnd);
    if (sourceEnd <= sourceStart) continue;
    const retainedWords = words.filter((word) => {
      const start = Number(word.start) || 0;
      const end = Number(word.end) || start;
      const midpoint = start + (end - start) / 2;
      return midpoint >= sourceStart && midpoint < sourceEnd;
    });
    const text = retainedWords.length
      ? retainedWords.map((word) => String(word.text || "")).join("")
      : sourceStart <= segmentStart + 0.001 && sourceEnd >= segmentEnd - 0.001
        ? String(segment.text || "")
        : "";
    if (!text.trim()) continue;
    const editedStart = span.editedStart + sourceStart - span.sourceStart;
    const editedWords = retainedWords
      .map((word) => {
        const wordSourceStart = Math.max(Number(word.start) || 0, sourceStart);
        const wordSourceEnd = Math.min(
          Number(word.end) || wordSourceStart,
          sourceEnd,
        );
        if (wordSourceEnd <= wordSourceStart) return null;
        return {
          text: String(word.text || ""),
          start: editedStart + wordSourceStart - sourceStart,
          end: editedStart + wordSourceEnd - sourceStart,
          sourceStart: wordSourceStart,
          sourceEnd: wordSourceEnd,
        };
      })
      .filter(Boolean);
    parts.push({
      sourceStart,
      sourceEnd,
      editedStart,
      editedEnd: span.editedStart + sourceEnd - span.sourceStart,
      text,
      words: editedWords,
    });
  }
  return parts;
}

function getActiveTranscriptSegmentIndex(
  currentTime = cutPreviewVideo.currentTime || 0,
  spans = getEditedTimelineSpans(),
) {
  const sourceTime = Number(currentTime);
  if (!Number.isFinite(sourceTime)) return -1;
  for (const [segmentIndex, segment] of currentEditableSegments.entries()) {
    const parts = getRetainedSegmentParts(
      segment,
      spans,
      getEditableSegmentCoverageEnd(segmentIndex),
    );
    if (
      parts.some(
        ({ sourceStart, sourceEnd }) =>
          sourceTime >= sourceStart && sourceTime < sourceEnd,
      )
    ) {
      return segmentIndex;
    }
  }
  return -1;
}

function scrollActiveTranscriptSegmentIntoView(item) {
  const panel = item.closest(".text-editor-panel");
  if (!panel || panel.hidden || panel.clientHeight <= 0) return;
  const panelRect = panel.getBoundingClientRect();
  const itemRect = item.getBoundingClientRect();
  const outsideViewport =
    itemRect.top < panelRect.top + 8 || itemRect.bottom > panelRect.bottom - 8;
  if (!outsideViewport) return;
  window.cancelAnimationFrame(transcriptFollowScrollFrame);
  transcriptFollowScrollFrame = window.requestAnimationFrame(() => {
    if (!item.isConnected || !item.classList.contains("is-playback-active")) return;
    const reduceMotion = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    item.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "nearest",
      inline: "nearest",
    });
  });
}

function updateActiveTranscriptSegment(
  currentTime = cutPreviewVideo.currentTime || 0,
  { follow = false } = {},
) {
  const nextIndex = getActiveTranscriptSegmentIndex(currentTime);
  const currentItem = segmentList.querySelector(
    ".segment-item.is-playback-active[data-segment-index]",
  );
  if (
    nextIndex === activeTranscriptSegmentIndex &&
    Number(currentItem?.dataset.segmentIndex) === nextIndex
  ) {
    return;
  }

  for (const item of segmentList.querySelectorAll(".segment-item.is-playback-active")) {
    item.classList.remove("is-playback-active");
    item.removeAttribute("aria-current");
    const badge = item.querySelector(".segment-current-badge");
    if (badge) badge.hidden = true;
  }

  activeTranscriptSegmentIndex = nextIndex;
  if (nextIndex < 0) return;
  const nextItem = segmentList.querySelector(
    `.segment-item[data-segment-index="${nextIndex}"]`,
  );
  if (!nextItem || nextItem.classList.contains("is-removed-from-timeline")) return;
  nextItem.classList.add("is-playback-active");
  nextItem.setAttribute("aria-current", "true");
  const badge = nextItem.querySelector(".segment-current-badge");
  if (badge) badge.hidden = false;
  if (follow) scrollActiveTranscriptSegmentIntoView(nextItem);
}

function hasCutSelection() {
  return (
    selectedRanges.size > 0 ||
    selectedNoSpeechRanges.size > 0 ||
    getCommittedTimelineDeleteRanges().length > 0
  );
}

function cutSelectionSignature(ranges = getMergedSelection()) {
  return ranges
    .map(({ start, end }) =>
      `${Number(start).toFixed(3)}-${Number(end).toFixed(3)}`,
    )
    .join("|");
}

function hasUncommittedCutSelection() {
  return (
    hasCutSelection() &&
    cutSelectionSignature() !== generatedCutSelectionSignature
  );
}

function buildLiveCutDraftState() {
  const spans = getEditedTimelineSpans();
  const segments = currentEditableSegments.flatMap((segment, segmentIndex) =>
    getRetainedSegmentParts(
      segment,
      spans,
      getEditableSegmentCoverageEnd(segmentIndex),
    ).map((part, partIndex) => ({
      id: `cut-draft-${segmentIndex}-${partIndex}`,
      text: String(part.text || ""),
      start: part.editedStart,
      end: part.editedEnd,
      sourceStart: part.sourceStart,
      sourceEnd: part.sourceEnd,
      words: part.words,
    })),
  );
  return {
    active: hasUncommittedCutSelection(),
    ranges: getMergedSelection().map(({ start, end }) => ({ start, end })),
    sourceDuration: cutTimelineDuration(),
    duration: editedCutTimelineDuration(spans),
    transcript: {
      text: segments.map((segment) => segment.text).join("\n"),
      segments,
    },
  };
}

function syncEditorSuiteCutDraftState(state = buildLiveCutDraftState()) {
  window.EditorSuite?.setCutDraft(state);
}

function updateTimelineRangeConfirmation() {
  const hasPendingRange = Boolean(
    timelineRangeInProgress &&
    selectedTimelineRangeId !== null &&
    timelineDeleteRanges.some(({ id }) => id === selectedTimelineRangeId),
  );
  generateCutButton.disabled =
    cutControlsLocked || hasPendingRange || !hasCutSelection();
}

function setCutControlsDisabled(disabled) {
  cutControlsLocked = disabled;
  segmentList.querySelectorAll(".segment-toggle").forEach((button) => {
    button.disabled = disabled;
  });
  suggestionList.querySelectorAll(".suggestion-action").forEach((button) => {
    button.disabled = disabled;
  });
  selectAllSuggestionsButton.disabled =
    disabled || currentSuggestions.length === 0;
  noSpeechList
    ?.querySelectorAll(".no-speech-action")
    .forEach((button) => {
      button.disabled = disabled;
    });
  if (selectAllNoSpeechButton) {
    selectAllNoSpeechButton.disabled =
      disabled || currentNoSpeechSuggestions.length === 0;
  }
  cutFrameTimeline?.classList.toggle("is-locked", disabled);
  clearSelectionButton.disabled = disabled || !hasCutSelection();
  generateCutButton.disabled = disabled || !hasCutSelection();
  updateTimelineRangeConfirmation();
  updateSuggestionStates();
  updateNoSpeechStates();
}

function setCutDraftSaveStatus(message, tone = "neutral") {
  if (!cutDraftSaveStatus) return;
  cutDraftSaveStatus.textContent = message;
  cutDraftSaveStatus.dataset.tone = tone;
}

function cutDraftStorageKey(jobId = currentJobId) {
  return jobId ? `video-editor:cut-draft:${jobId}` : "";
}

function loadLocalCutDraft(jobId = currentJobId) {
  const key = cutDraftStorageKey(jobId);
  if (!key) return null;
  try {
    const payload = JSON.parse(window.localStorage.getItem(key) || "null");
    return payload && typeof payload === "object" ? payload : null;
  } catch {
    return null;
  }
}

function saveLocalCutDraft(draft, jobId = currentJobId) {
  const key = cutDraftStorageKey(jobId);
  if (!key) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(draft));
  } catch {
    // Server persistence remains available when browser storage is restricted.
  }
}

function removeLocalCutDraft(jobId = currentJobId) {
  const key = cutDraftStorageKey(jobId);
  if (!key) return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Nothing else is required when browser storage is restricted.
  }
}

function resolvePersistedCutDraft(serverDraft, jobId = currentJobId) {
  const localDraft = loadLocalCutDraft(jobId);
  const serverUpdatedAt = Date.parse(serverDraft?.updatedAt || "") || 0;
  const localUpdatedAt = Date.parse(localDraft?.updatedAt || "") || 0;
  cutDraftNeedsServerSync = Boolean(
    localDraft && (!serverDraft || localUpdatedAt > serverUpdatedAt),
  );
  return cutDraftNeedsServerSync ? localDraft : serverDraft;
}

function serializableCutDraftRange(range) {
  const start = Number(range?.start);
  const end = Number(range?.end);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return null;
  }
  return { start, end };
}

function buildPersistedCutDraftPayload() {
  const textRanges = [...selectedRanges.entries()].flatMap(([key, range]) => {
    const normalized = serializableCutDraftRange(range);
    if (!normalized) return [];
    const payload = {
      key,
      ...normalized,
      text: String(range.text || ""),
      adjacentSilenceBefore: Math.max(
        0,
        Number(range.adjacentSilenceBefore) || 0,
      ),
      adjacentSilenceAfter: Math.max(
        0,
        Number(range.adjacentSilenceAfter) || 0,
      ),
    };
    for (const field of ["originalStart", "originalEnd"]) {
      const value = Number(range[field]);
      if (Number.isFinite(value) && value >= 0) payload[field] = value;
    }
    return [payload];
  });
  const noSpeechRanges = [...selectedNoSpeechRanges.entries()].flatMap(
    ([key, range]) => {
      const normalized = serializableCutDraftRange(range);
      return normalized ? [{ key, ...normalized }] : [];
    },
  );
  const timelineRanges = getCommittedTimelineDeleteRanges().flatMap((range) => {
    const normalized = serializableCutDraftRange(range);
    return normalized ? [normalized] : [];
  });
  return {
    revision: cutDraftRevision,
    textRanges,
    noSpeechRanges,
    timelineRanges,
  };
}

function cutDraftSelectionSignature(payload) {
  return JSON.stringify({
    textRanges: payload.textRanges,
    noSpeechRanges: payload.noSpeechRanges,
    timelineRanges: payload.timelineRanges,
  });
}

function restorePersistedCutDraft(draft) {
  cutDraftRevision = Math.max(0, Number(draft?.revision) || 0);
  for (const item of Array.isArray(draft?.textRanges) ? draft.textRanges : []) {
    const normalized = serializableCutDraftRange(item);
    const key = String(item?.key || "");
    if (!normalized || !key) continue;
    selectedRanges.set(key, {
      ...normalized,
      text: String(item.text || ""),
      originalStart: Number.isFinite(Number(item.originalStart))
        ? Number(item.originalStart)
        : normalized.start,
      originalEnd: Number.isFinite(Number(item.originalEnd))
        ? Number(item.originalEnd)
        : normalized.end,
      adjacentSilenceBefore: Math.max(
        0,
        Number(item.adjacentSilenceBefore) || 0,
      ),
      adjacentSilenceAfter: Math.max(
        0,
        Number(item.adjacentSilenceAfter) || 0,
      ),
    });
  }
  for (
    const item of Array.isArray(draft?.noSpeechRanges)
      ? draft.noSpeechRanges
      : []
  ) {
    const normalized = serializableCutDraftRange(item);
    const key = String(item?.key || "");
    if (!normalized || !key) continue;
    selectedNoSpeechRanges.set(key, { id: key, ...normalized });
  }
  timelineDeleteRanges = (
    Array.isArray(draft?.timelineRanges) ? draft.timelineRanges : []
  ).flatMap((item) => {
    const normalized = serializableCutDraftRange(item);
    if (!normalized) return [];
    return [{ id: nextTimelineRangeId++, ...normalized }];
  });
  const payload = buildPersistedCutDraftPayload();
  cutDraftLastSignature = cutDraftSelectionSignature(payload);
  const restoredCount =
    payload.textRanges.length +
    payload.noSpeechRanges.length +
    payload.timelineRanges.length;
  setCutDraftSaveStatus(
    restoredCount > 0 ? "已恢复并保存剪辑草稿" : "剪辑草稿自动保存",
    restoredCount > 0 ? "success" : "neutral",
  );
}

async function persistCutDraft() {
  if (!cutDraftReady || !currentJobId) return;
  const jobId = currentJobId;
  const payload = buildPersistedCutDraftPayload();
  const signature = cutDraftSelectionSignature(payload);
  if (signature === cutDraftLastSignature) return;
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/cut-draft`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      },
    );
    const result = await response.json();
    if (!response.ok) {
      if ([404, 405].includes(response.status)) {
        cutDraftLastSignature = signature;
        cutDraftNeedsServerSync = true;
        setCutDraftSaveStatus("剪辑草稿已保存在本机", "success");
        return;
      }
      throw new Error(result.detail || "剪辑草稿保存失败。请稍后重试。");
    }
    if (currentJobId !== jobId) return;
    cutDraftRevision = Math.max(
      cutDraftRevision,
      Number(result.cutDraft?.revision) || 0,
    );
    cutDraftLastSignature = signature;
    cutDraftNeedsServerSync = false;
    saveLocalCutDraft(result.cutDraft, jobId);
    setCutDraftSaveStatus("剪辑草稿已保存", "success");
  } catch (error) {
    if (currentJobId !== jobId) return;
    setCutDraftSaveStatus(
      `已保存在本机；${error.message || "服务器同步失败"} 下一次修改时会重试。`,
      "error",
    );
  }
}

function scheduleCutDraftSave() {
  if (!cutDraftReady || !currentJobId) return;
  const signature = cutDraftSelectionSignature(
    buildPersistedCutDraftPayload(),
  );
  if (signature === cutDraftLastSignature) return;
  saveLocalCutDraft({
    schemaVersion: 1,
    ...buildPersistedCutDraftPayload(),
    updatedAt: new Date().toISOString(),
  });
  cutDraftNeedsServerSync = true;
  setCutDraftSaveStatus("正在保存剪辑草稿…", "saving");
  cutDraftSaveQueue = cutDraftSaveQueue.then(
    persistCutDraft,
    persistCutDraft,
  );
}

async function clearPersistedCutDraft(jobId) {
  if (!jobId) return;
  const response = await fetch(
    `/api/transcriptions/${encodeURIComponent(jobId)}/cut-draft`,
    { method: "DELETE" },
  );
  const result = await response.json();
  if ([404, 405].includes(response.status)) return;
  if (!response.ok) {
    throw new Error(result.detail || "剪辑草稿清除失败。请稍后重试。");
  }
}

function updateSelectionSummary() {
  const merged = getMergedSelection();
  const deletedDuration = merged.reduce(
    (total, range) => total + range.end - range.start,
    0,
  );
  const mergedNoSpeechRanges = mergeCutRanges([
    ...selectedNoSpeechRanges.values(),
  ]);
  const noSpeechDeletedDuration = mergedNoSpeechRanges.reduce(
    (total, range) => total + range.end - range.start,
    0,
  );
  const selectionParts = [];
  const selectedSegmentCount = currentEditableSegments.filter((segment) =>
    selectedRanges.has(rangeKey(segment.start, segment.end)),
  ).length;
  const otherTextRangeCount = Math.max(
    0,
    selectedRanges.size - selectedSegmentCount,
  );
  if (selectedSegmentCount > 0) {
    selectionParts.push(`${selectedSegmentCount} 段文字`);
  }
  if (otherTextRangeCount > 0) {
    selectionParts.push(`${otherTextRangeCount} 个 AI 口误范围`);
  }
  if (selectedNoSpeechRanges.size > 0) {
    selectionParts.push(`${selectedNoSpeechRanges.size} 个空白片段`);
  }
  const committedTimelineRanges = getCommittedTimelineDeleteRanges();
  if (committedTimelineRanges.length > 0) {
    selectionParts.push(`${committedTimelineRanges.length} 个时间轴区间`);
  }

  if (!hasCutSelection()) {
    cutSummary.textContent = "尚未删除任何内容";
    cutSelectionDetail.textContent =
      "点击文字删除会一并收紧前后无声区；时间轴拖动按自定义区间处理";
    outputCutSummary.textContent = "尚未删除任何内容";
    outputCutSelectionDetail.textContent =
      "请先在文字剪辑、空白剪辑或时间轴中删除内容";
  } else {
    const editedDuration = Math.max(0, cutTimelineDuration() - deletedDuration);
    cutSummary.textContent = `已删除 ${selectionParts.join("、")}`;
    cutSelectionDetail.textContent =
      `共删除 ${formatDuration(deletedDuration)} · 剪辑后约 ${formatDuration(editedDuration)} · 原视频保留`;
    outputCutSummary.textContent = `已删除 ${selectionParts.join("、")}`;
    outputCutSelectionDetail.textContent =
      `共删除 ${formatDuration(deletedDuration)} · 剪辑后约 ${formatDuration(editedDuration)} · 原视频保留`;
  }

  clearSelectionButton.disabled =
    cutControlsLocked || !hasCutSelection();
  generateCutButton.disabled =
    cutControlsLocked || !hasCutSelection();
  if (noSpeechCutSummary && noSpeechCutSelectionDetail) {
    if (selectedNoSpeechRanges.size === 0) {
      noSpeechCutSummary.textContent = "尚未删除空白片段";
      noSpeechCutSelectionDetail.textContent =
        "请先试听，再直接删除不需要的区间";
    } else {
      noSpeechCutSummary.textContent =
        `已删除 ${selectedNoSpeechRanges.size} 个空白片段`;
      const hasOtherSelections =
        selectedRanges.size > 0 || committedTimelineRanges.length > 0;
      noSpeechCutSelectionDetail.textContent =
        `已删除空白 ${formatDuration(noSpeechDeletedDuration)}` +
        (hasOtherSelections ? " · 已与其他删除区间合并" : " · 原视频保留");
    }
  }
  updateTimelineRangeConfirmation();
  updateOriginalSourceActionsVisibility();

  segmentList.querySelectorAll(".segment-toggle").forEach((button) => {
    const segment = currentEditableSegments[Number(button.dataset.segmentIndex)];
    const allSelected = Boolean(
      segment && selectedRanges.has(rangeKey(segment.start, segment.end)),
    );
    button.closest(".segment-item")?.classList.toggle(
      "has-selection",
      allSelected,
    );
    button.classList.toggle("is-selected", allSelected);
    button.setAttribute("aria-pressed", String(allSelected));
    button.disabled = cutControlsLocked;
    button.setAttribute(
      "aria-label",
      `${allSelected ? "撤销删除" : "删除"}第 ${Number(button.dataset.segmentIndex) + 1} 段`,
    );
  });
  document.body.classList.toggle(
    "has-cut-selection",
    hasCutSelection(),
  );
  updateCutSegmentTimestamps();
  updateCutInspectorTimestamps();
  syncEditorSuiteCutDraftState();
  refreshCutTimeline();
  updateSuggestionStates();
  updateNoSpeechStates();
  scheduleCutDraftSave();
}

function cutTimelineDuration() {
  if (currentVideoDuration > 0) return currentVideoDuration;
  return Number.isFinite(cutPreviewVideo.duration)
    ? Math.max(0, cutPreviewVideo.duration)
    : 0;
}

function cutTimelinePixelsPerSecond() {
  let pixelsPerSecond = CUT_TIMELINE_MIN_PIXELS_PER_SECOND;
  const spans = getEditedTimelineSpans();
  for (const [segmentIndex, segment] of currentEditableSegments.entries()) {
    for (const part of getRetainedSegmentParts(
      segment,
      spans,
      getEditableSegmentCoverageEnd(segmentIndex),
    )) {
      const duration = Math.max(0.05, part.editedEnd - part.editedStart);
      const characterCount = Array.from(
        String(part.text || "").replace(/\s+/g, ""),
      ).length;
      const requiredWidth =
        Math.ceil(characterCount / CUT_TIMELINE_TEXT_LINES) *
          CUT_TIMELINE_TEXT_CHAR_WIDTH +
        16;
      pixelsPerSecond = Math.max(pixelsPerSecond, requiredWidth / duration);
    }
  }
  return Math.ceil(pixelsPerSecond);
}

function updateCutTimelineScale() {
  const total = editedCutTimelineDuration();
  const viewportWidth = cutFrameTimelineScroll.clientWidth;
  if (total <= 0 || viewportWidth <= 0) {
    cutFrameTimelineTrack.style.removeProperty("width");
    return;
  }
  const width = Math.max(
    viewportWidth,
    Math.round(total * cutTimelinePixelsPerSecond()),
  );
  cutFrameTimelineTrack.style.width = `${width}px`;
}

function updateCutTimelineStatus(
  message,
  tone = "neutral",
  source = "system",
) {
  cutFrameTimelineStatus.textContent = message;
  cutFrameTimelineStatus.dataset.tone = tone;
  cutFrameTimelineStatus.dataset.source = source;
}

function syncCutVideoStageLayout() {
  if (!cutPreviewVideo.videoWidth || !cutPreviewVideo.videoHeight) return;
  const ratio = cutPreviewVideo.videoWidth / cutPreviewVideo.videoHeight;
  cutVideoStage.style.aspectRatio = `${cutPreviewVideo.videoWidth} / ${cutPreviewVideo.videoHeight}`;
  cutVideoStage.style.width =
    ratio < 1
      ? `min(100%, ${Math.round(Math.min(600, window.innerHeight * 0.68) * ratio)}px)`
      : "min(100%, 860px)";
}

function updateCutTimelineTextStates(currentTime = cutPreviewVideo.currentTime || 0) {
  cutFrameTimelineText.querySelectorAll(".cut-timeline-text-segment").forEach((item) => {
    const start = Number(item.dataset.sourceStart) || 0;
    const end = Number(item.dataset.sourceEnd) || start;
    item.classList.toggle(
      "is-active",
      currentTime >= start && currentTime < end,
    );
  });
}

function updateCutTimelinePlayhead({ followTranscript = !cutPreviewVideo.paused } = {}) {
  const spans = getEditedTimelineSpans();
  const total = editedCutTimelineDuration(spans);
  const sourceCurrent = clamp(
    cutPreviewVideo.currentTime || 0,
    0,
    cutTimelineDuration() || 0,
  );
  const current = sourceTimeToEditedTime(sourceCurrent, spans);
  const progress = total > 0 ? current / total : 0;
  cutFrameTimeline.hidden = total <= 0;
  updateCutTimelineScale();
  cutFrameTimelineSeek.max = String(total);
  cutFrameTimelineSeek.step = String(CUT_TIMELINE_STEP);
  cutFrameTimelineSeek.value = String(current);
  cutFrameTimelineSeek.setAttribute("aria-valuemax", String(total));
  cutFrameTimelineSeek.setAttribute("aria-valuenow", current.toFixed(2));
  cutFrameTimelineSeek.setAttribute(
    "aria-valuetext",
    `${formatTime(current)} / ${formatTime(total)}`,
  );
  cutFrameTimelinePlayhead.style.left = `${progress * 100}%`;
  cutFrameTimelineTime.value = `${formatTime(current)} / ${formatTime(total)}`;
  updateCutTimelineTextStates(sourceCurrent);
  updateActiveTranscriptSegment(sourceCurrent, { follow: followTranscript });
  if (!cutPreviewVideo.paused && cutFrameTimelineScroll.clientWidth > 0) {
    const playheadX = progress * cutFrameTimelineTrack.clientWidth;
    const viewportStart = cutFrameTimelineScroll.scrollLeft;
    const viewportEnd = viewportStart + cutFrameTimelineScroll.clientWidth;
    if (playheadX < viewportStart || playheadX > viewportEnd) {
      cutFrameTimelineScroll.scrollLeft = Math.max(
        0,
        playheadX - cutFrameTimelineScroll.clientWidth * 0.5,
      );
    }
  }
}

function seekCutPreview(seconds) {
  const total = cutTimelineDuration();
  noSpeechPreviewEnd = null;
  cutSelectionPreviewEnd = null;
  cutPreviewVideo.currentTime = clamp(Number(seconds) || 0, 0, total);
  updateCutTimelinePlayhead({ followTranscript: true });
}

function previewSelectedCutRange(range) {
  const total = cutTimelineDuration();
  const start = clamp(Number(range?.start) || 0, 0, total);
  const end = clamp(Number(range?.end) || start, start, total);
  if (total <= 0 || end <= start) return;
  cutPreviewVideo.pause();
  seekCutPreview(Math.max(0, start - 0.6));
  cutSelectionPreviewEnd = Math.min(total, end + 0.8);
  const adjacentSilence =
    (Number(range?.adjacentSilenceBefore) || 0) +
    (Number(range?.adjacentSilenceAfter) || 0);
  updateCutTimelineStatus(
    `正在左侧预览裁剪衔接 ${formatCutRange(start, end)}` +
      (adjacentSilence > CUT_SPEECH_BOUNDARY_EPSILON
        ? `，已同时收紧 ${formatDuration(adjacentSilence)} 无声区。`
        : "。"),
    "neutral",
    "preview",
  );
  cutPreviewVideo.play().catch(() => {});
}

function previewNoSpeechSuggestion(suggestion) {
  const range = getNoSpeechRange(suggestion);
  if (!range) return;
  const total = cutTimelineDuration();
  const previewStart = Math.max(0, range.start - 0.25);
  const previewEnd = Math.min(total, range.end + 0.25);
  seekCutPreview(previewStart);
  noSpeechPreviewEnd = previewEnd;
  updateCutTimelineStatus(
    `正在试听无文字区间 ${formatCutRange(range.start, range.end)}。`,
    "neutral",
    "no-speech",
  );
  cutPreviewVideo.play().catch(() => {});
}

function cutTimelineSecondsFromClientX(clientX) {
  const spans = getEditedTimelineSpans();
  const total = editedCutTimelineDuration(spans);
  const rect = cutFrameTimelineTrack.getBoundingClientRect();
  if (rect.width <= 0 || total <= 0) return 0;
  const editedSeconds =
    clamp((clientX - rect.left) / rect.width, 0, 1) * total;
  return editedTimeToSourceTime(editedSeconds, spans);
}

function cutTimelineMajorStep(total, width) {
  const targetStep =
    total / Math.max(1, Math.floor(width / CUT_TIMELINE_MAJOR_TICK_WIDTH));
  const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600];
  return steps.find((step) => step >= targetStep) || steps.at(-1);
}

function renderCutTimelineRuler() {
  const total = editedCutTimelineDuration();
  const width = cutFrameTimelineTrack.clientWidth;
  if (total <= 0 || width <= 0) {
    cutFrameTimelineRuler.replaceChildren();
    return;
  }
  const majorStep = cutTimelineMajorStep(total, width);
  const minorStep = majorStep / 5;
  const signature = `${total.toFixed(3)}|${Math.round(width)}|${majorStep}`;
  if (signature === cutTimelineRulerSignature) return;
  cutTimelineRulerSignature = signature;
  cutFrameTimelineRuler.replaceChildren();

  const tickCount = Math.floor(total / minorStep + 0.000001);
  for (let index = 0; index <= tickCount; index += 1) {
    const seconds = index * minorStep;
    const isMajor = index % 5 === 0;
    const tick = document.createElement("span");
    tick.className = "frame-timeline-tick";
    tick.classList.toggle("is-major", isMajor);
    tick.style.left = `${(seconds / total) * 100}%`;
    if (isMajor) {
      const label = document.createElement("span");
      label.className = "frame-timeline-tick-label";
      label.textContent = formatTime(seconds);
      if (index === 0) label.classList.add("is-start");
      if (Math.abs(total - seconds) < 0.001) label.classList.add("is-end");
      tick.append(label);
    }
    cutFrameTimelineRuler.append(tick);
  }
}

function renderCutTimelineRanges() {
  cutFrameTimelineRanges.replaceChildren();
  const spans = getEditedTimelineSpans();
  const total = editedCutTimelineDuration(spans);
  if (total <= 0) return;
  if (
    selectedTimelineRangeId !== null &&
    !timelineDeleteRanges.some(({ id }) => id === selectedTimelineRangeId)
  ) {
    selectedTimelineRangeId = null;
  }

  for (const range of timelineDeleteRanges.filter(
    ({ id }) => id === selectedTimelineRangeId,
  )) {
    const editedStart = sourceTimeToEditedTime(range.start, spans);
    const editedEnd = sourceTimeToEditedTime(range.end, spans);
    const rangeElement = document.createElement("div");
    rangeElement.className = "cut-timeline-delete-range";
    rangeElement.classList.toggle(
      "is-selected",
      range.id === selectedTimelineRangeId,
    );
    rangeElement.classList.toggle(
      "is-pending",
      timelineRangeInProgress && range.id === selectedTimelineRangeId,
    );
    rangeElement.dataset.rangeId = String(range.id);
    rangeElement.style.left = `${(editedStart / total) * 100}%`;
    rangeElement.style.width = `${Math.max(0.25, ((editedEnd - editedStart) / total) * 100)}%`;

    const startHandle = document.createElement("button");
    startHandle.type = "button";
    startHandle.className = "cut-timeline-range-handle";
    startHandle.dataset.dragMode = "start";
    startHandle.dataset.edge = "start";
    startHandle.setAttribute(
      "aria-label",
      `调整删除区间开始时间，当前 ${formatTime(range.start)}`,
    );

    const body = document.createElement("button");
    body.type = "button";
    body.className = "cut-timeline-range-body";
    body.dataset.dragMode = "move";
    body.textContent = formatCutRange(range.start, range.end);
    body.title = "拖动调整区间，确认后才会删除";
    body.setAttribute(
      "aria-label",
      `待确认删除区间 ${formatCutRange(range.start, range.end)}，可拖动调整`,
    );

    const endHandle = document.createElement("button");
    endHandle.type = "button";
    endHandle.className = "cut-timeline-range-handle";
    endHandle.dataset.dragMode = "end";
    endHandle.dataset.edge = "end";
    endHandle.setAttribute(
      "aria-label",
      `调整删除区间结束时间，当前 ${formatTime(range.end)}`,
    );
    rangeElement.append(startHandle, body, endHandle);
    cutFrameTimelineRanges.append(rangeElement);
  }
  updateTimelineRangeConfirmation();
  updateCutTimelineTextStates();
}

function renderCutTimelineTextSegments() {
  cutFrameTimelineText.replaceChildren();
  const spans = getEditedTimelineSpans();
  const total = editedCutTimelineDuration(spans);
  if (total <= 0) return;
  updateCutTimelineScale();

  currentEditableSegments.forEach((segment, segmentIndex) => {
    for (const part of getRetainedSegmentParts(
      segment,
      spans,
      getEditableSegmentCoverageEnd(segmentIndex),
    )) {
      const item = document.createElement("span");
      item.className = "cut-timeline-text-segment";
      item.dataset.segmentIndex = String(segmentIndex);
      item.dataset.sourceStart = String(part.sourceStart);
      item.dataset.sourceEnd = String(part.sourceEnd);
      item.style.left = `${(part.editedStart / total) * 100}%`;
      item.style.width = `${Math.max(0.2, ((part.editedEnd - part.editedStart) / total) * 100)}%`;
      const label = document.createElement("span");
      label.className = "cut-timeline-text-segment-label";
      label.textContent = String(part.text || "暂无文字").replace(/\s+/g, " ");
      const editedRange = formatCutRange(part.editedStart, part.editedEnd);
      item.title = `${editedRange} ${label.textContent}`;
      item.setAttribute(
        "aria-label",
        `剪辑后 ${editedRange} ${label.textContent}`,
      );
      item.append(label);
      cutFrameTimelineText.append(item);
    }
  });
  updateCutTimelineTextStates();
}

function renderCutTimelinePlaceholders(count, fallback = false) {
  cutFrameTimelineThumbnails.replaceChildren();
  for (let index = 0; index < count; index += 1) {
    const item = document.createElement("span");
    item.className = `frame-timeline-thumb ${fallback ? "is-fallback" : "is-loading"}`;
    cutFrameTimelineThumbnails.append(item);
  }
}

function desiredCutTimelineThumbnailCount() {
  const total = editedCutTimelineDuration();
  const width = cutFrameTimelineTrack.clientWidth || 640;
  if (total <= 0) return CUT_TIMELINE_THUMB_MIN;
  const majorStep = cutTimelineMajorStep(total, width);
  return clamp(
    Math.ceil(total / majorStep) + 1,
    CUT_TIMELINE_THUMB_MIN,
    CUT_TIMELINE_THUMB_MAX,
  );
}

function waitForCutVideoMetadata(video) {
  if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      video.removeEventListener("loadedmetadata", handleLoaded);
      video.removeEventListener("error", handleError);
    };
    const handleLoaded = () => {
      cleanup();
      resolve();
    };
    const handleError = () => {
      cleanup();
      reject(new Error("video metadata unavailable"));
    };
    video.addEventListener("loadedmetadata", handleLoaded, { once: true });
    video.addEventListener("error", handleError, { once: true });
  });
}

function seekCutTimelineExtractor(video, seconds) {
  const target = clamp(seconds, 0, Math.max(0, video.duration - 0.04));
  if (Math.abs((video.currentTime || 0) - target) < 0.01) {
    return new Promise((resolve) => window.requestAnimationFrame(resolve));
  }
  return new Promise((resolve, reject) => {
    let settled = false;
    const cleanup = () => {
      window.clearTimeout(timer);
      video.removeEventListener("seeked", handleSeeked);
      video.removeEventListener("error", handleError);
    };
    const done = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };
    const handleSeeked = done;
    const handleError = () => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(new Error("video frame unavailable"));
    };
    const timer = window.setTimeout(done, 900);
    video.addEventListener("seeked", handleSeeked, { once: true });
    video.addEventListener("error", handleError, { once: true });
    video.currentTime = target;
  });
}

async function buildCutTimelineThumbnails(options = {}) {
  const spans = getEditedTimelineSpans();
  const total = editedCutTimelineDuration(spans);
  const source = cutPreviewVideo.currentSrc || cutPreviewVideo.src;
  if (!source || total <= 0) return;
  const count = desiredCutTimelineThumbnailCount();
  const deletionSignature = getMergedSelection()
    .map(({ start, end }) => `${start.toFixed(3)}-${end.toFixed(3)}`)
    .join("|");
  const signature = `${source}|${total.toFixed(2)}|${count}|${deletionSignature}`;
  if (!options.force && signature === cutTimelineSignature) return;
  cutTimelineSignature = signature;
  const buildId = (cutTimelineBuildId += 1);
  renderCutTimelinePlaceholders(count);
  updateCutTimelineStatus("正在生成帧预览…", "neutral", "thumbnails");

  const extractor = document.createElement("video");
  extractor.muted = true;
  extractor.playsInline = true;
  extractor.preload = "auto";
  extractor.src = source;
  try {
    await waitForCutVideoMetadata(extractor);
    if (buildId !== cutTimelineBuildId) return;
    const ratio =
      extractor.videoWidth > 0 && extractor.videoHeight > 0
        ? extractor.videoWidth / extractor.videoHeight
        : 16 / 9;
    const canvas = document.createElement("canvas");
    canvas.width = 116;
    canvas.height = Math.max(48, Math.round(canvas.width / ratio));
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) throw new Error("frame canvas unavailable");

    for (let index = 0; index < count; index += 1) {
      const editedSeconds =
        count === 1 ? 0.04 : (total * index) / Math.max(1, count - 1);
      const seconds = editedTimeToSourceTime(editedSeconds, spans);
      await seekCutTimelineExtractor(extractor, seconds);
      if (buildId !== cutTimelineBuildId) return;
      context.drawImage(extractor, 0, 0, canvas.width, canvas.height);
      const frameUrl = canvas.toDataURL("image/jpeg", 0.72);
      const image = document.createElement("img");
      image.src = frameUrl;
      image.alt = "";
      image.draggable = false;
      const item = document.createElement("span");
      item.className = "frame-timeline-thumb";
      item.style.backgroundImage = `url("${frameUrl}")`;
      item.append(image);
      cutFrameTimelineThumbnails.children[index]?.replaceWith(item);
    }
    if (cutFrameTimelineStatus.dataset.source === "thumbnails") {
      updateCutTimelineStatus("");
    }
  } catch {
    if (buildId === cutTimelineBuildId) {
      renderCutTimelinePlaceholders(count, true);
      updateCutTimelineStatus(
        "帧预览生成失败，仍可拖动时间轴完成剪辑。",
        "error",
        "thumbnails",
      );
    }
  } finally {
    extractor.removeAttribute("src");
    extractor.load();
  }
}

function refreshCutTimeline(options = {}) {
  updateCutTimelinePlayhead();
  renderCutTimelineRuler();
  renderCutTimelineTextSegments();
  renderCutTimelineRanges();
  buildCutTimelineThumbnails(options);
}

function beginCutTimelineSelection(event) {
  if (
    cutControlsLocked ||
    timelineRangeInProgress ||
    event.button !== 0 ||
    event.target.closest(".cut-timeline-delete-range")
  ) {
    return;
  }
  event.preventDefault();
  cutPreviewVideo.pause();
  const anchorSeconds = cutTimelineSecondsFromClientX(event.clientX);
  const startClientX = event.clientX;
  let draftRange = null;
  let rawDraftStart = anchorSeconds;
  let rawDraftEnd = anchorSeconds;
  seekCutPreview(anchorSeconds);

  const move = (moveEvent) => {
    if (
      !draftRange &&
      Math.abs(moveEvent.clientX - startClientX) < CUT_TIMELINE_DRAG_THRESHOLD
    ) {
      return;
    }
    const current = cutTimelineSecondsFromClientX(moveEvent.clientX);
    if (!draftRange) {
      draftRange = {
        id: nextTimelineRangeId++,
        start: anchorSeconds,
        end: anchorSeconds,
      };
      timelineDeleteRanges.push(draftRange);
      selectedTimelineRangeId = draftRange.id;
      timelineRangeInProgress = true;
    }
    rawDraftStart = Math.min(anchorSeconds, current);
    rawDraftEnd = Math.max(anchorSeconds, current);
    const safeRange = alignManualRangeToTranscript({
      ...draftRange,
      start: rawDraftStart,
      end: rawDraftEnd,
    });
    draftRange.start = safeRange?.start ?? rawDraftStart;
    draftRange.end = safeRange?.end ?? rawDraftEnd;
    seekCutPreview(current);
    renderCutTimelineRanges();
    updateCutTimelineStatus(
      safeRange
        ? `将按自定义区间删除 ${formatCutRange(draftRange.start, draftRange.end)}；如触碰文字，仅吸附完整文字边界`
        : "当前拖动范围落在文字内部，松开后不会删除。",
      safeRange ? "neutral" : "error",
      "selection",
    );
  };

  const finish = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    window.removeEventListener("pointercancel", finish);
    if (!draftRange) return;
    const safeRange = alignManualRangeToTranscript({
      ...draftRange,
      start: rawDraftStart,
      end: rawDraftEnd,
    });
    if (
      !safeRange ||
      safeRange.end - safeRange.start < CUT_TIMELINE_MIN_RANGE
    ) {
      timelineDeleteRanges = timelineDeleteRanges.filter(
        ({ id }) => id !== draftRange.id,
      );
      timelineRangeInProgress = false;
      selectedTimelineRangeId = null;
      updateCutTimelineStatus(
        "未删除：区间过短，或边界落在无法安全裁剪的文字内部。",
        "error",
        "selection",
      );
      updateSelectionSummary();
      return;
    }
    Object.assign(draftRange, safeRange);
    renderCutTimelineRanges();
    updateTimelineRangeConfirmation();
    updateCutTimelineStatus(
      `已选择 ${formatCutRange(draftRange.start, draftRange.end)}，确认后才会删除。`,
      "neutral",
      "selection",
    );
    void requestTimelineRangeConfirmation(draftRange);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish, { once: true });
  window.addEventListener("pointercancel", finish, { once: true });
}

function beginTimelineRangeAdjustment(event) {
  const control = event.target.closest("[data-drag-mode]");
  const rangeElement = event.target.closest(".cut-timeline-delete-range");
  if (!control || !rangeElement || cutControlsLocked || event.button !== 0) {
    return;
  }
  const rangeId = Number(rangeElement.dataset.rangeId);
  const range = timelineDeleteRanges.find(({ id }) => id === rangeId);
  if (!range) return;
  event.preventDefault();
  event.stopPropagation();
  cutPreviewVideo.pause();
  selectedTimelineRangeId = rangeId;
  const mode = control.dataset.dragMode;
  const original = { start: range.start, end: range.end };
  const startClientX = event.clientX;
  const total = cutTimelineDuration();
  renderCutTimelineRanges();

  const move = (moveEvent) => {
    const rect = cutFrameTimelineTrack.getBoundingClientRect();
    const delta = ((moveEvent.clientX - startClientX) / rect.width) * total;
    if (mode === "start") {
      range.start = clamp(
        original.start + delta,
        0,
        original.end - CUT_TIMELINE_MIN_RANGE,
      );
      seekCutPreview(range.start);
    } else if (mode === "end") {
      range.end = clamp(
        original.end + delta,
        original.start + CUT_TIMELINE_MIN_RANGE,
        total,
      );
      seekCutPreview(range.end);
    } else {
      const length = original.end - original.start;
      range.start = clamp(original.start + delta, 0, total - length);
      range.end = range.start + length;
      seekCutPreview(range.start);
    }
    renderCutTimelineRanges();
    updateCutTimelineStatus(
      `正在调整删除区间 ${formatCutRange(range.start, range.end)}`,
      "neutral",
      "selection",
    );
  };

  const finish = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    window.removeEventListener("pointercancel", finish);
    const safeRange = alignManualRangeToTranscript(range);
    if (safeRange) Object.assign(range, safeRange);
    updateCutTimelineStatus(
      `已调整待确认区间 ${formatCutRange(range.start, range.end)}，确认后才会删除。`,
      "neutral",
      "selection",
    );
    updateSelectionSummary();
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish, { once: true });
  window.addEventListener("pointercancel", finish, { once: true });
}

function cancelPendingTimelineRange() {
  if (selectedTimelineRangeId === null || cutControlsLocked) return;
  timelineDeleteRanges = timelineDeleteRanges.filter(
    ({ id }) => id !== selectedTimelineRangeId,
  );
  selectedTimelineRangeId = null;
  timelineRangeInProgress = false;
  updateCutTimelineStatus("");
  updateSelectionSummary();
}

function confirmPendingTimelineRange() {
  if (selectedTimelineRangeId === null || cutControlsLocked) return;
  const range = timelineDeleteRanges.find(
    ({ id }) => id === selectedTimelineRangeId,
  );
  if (!range || !timelineRangeInProgress) return;
  timelineRangeInProgress = false;
  selectedTimelineRangeId = null;
  updateSelectionSummary();
  previewSelectedCutRange(range);
}

async function requestTimelineRangeConfirmation(range) {
  if (
    !range ||
    cutControlsLocked ||
    timelineRangeConfirmationOpen ||
    !timelineRangeInProgress ||
    selectedTimelineRangeId !== range.id
  ) {
    return;
  }
  timelineRangeConfirmationOpen = true;
  let confirmed = false;
  try {
    confirmed = await window.appConfirm({
      eyebrow: "时间轴滑动删除",
      title: "删除这个时间轴区间？",
      message:
        `将删除 ${formatCutRange(range.start, range.end)}，并自动拼接前后画面。` +
        "删除后当前方案内不可撤销，原视频仍会保留。",
      confirmText: "确认删除",
      cancelText: "取消",
      tone: "danger",
      icon: "ph:scissors-bold",
    });
  } finally {
    timelineRangeConfirmationOpen = false;
  }
  if (
    !timelineRangeInProgress ||
    selectedTimelineRangeId !== range.id
  ) {
    return;
  }
  if (confirmed) {
    confirmPendingTimelineRange();
  } else {
    cancelPendingTimelineRange();
  }
}

function adjustTimelineRangeWithKeyboard(event) {
  const control = event.target.closest("[data-drag-mode]");
  const rangeElement = event.target.closest(".cut-timeline-delete-range");
  if (!control || !rangeElement || cutControlsLocked) return;
  const rangeId = Number(rangeElement.dataset.rangeId);
  const range = timelineDeleteRanges.find(({ id }) => id === rangeId);
  if (!range) return;
  selectedTimelineRangeId = rangeId;
  if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    cancelPendingTimelineRange();
    return;
  }
  if (event.key === "Enter" && timelineRangeInProgress) {
    event.preventDefault();
    void requestTimelineRangeConfirmation(range);
    return;
  }
  if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
  event.preventDefault();
  const direction = event.key === "ArrowLeft" ? -1 : 1;
  const delta = direction * (event.shiftKey ? 1 : 0.1);
  const total = cutTimelineDuration();
  const mode = control.dataset.dragMode;
  if (mode === "start") {
    range.start = clamp(
      range.start + delta,
      0,
      range.end - CUT_TIMELINE_MIN_RANGE,
    );
    seekCutPreview(range.start);
  } else if (mode === "end") {
    range.end = clamp(
      range.end + delta,
      range.start + CUT_TIMELINE_MIN_RANGE,
      total,
    );
    seekCutPreview(range.end);
  } else {
    const length = range.end - range.start;
    range.start = clamp(range.start + delta, 0, total - length);
    range.end = range.start + length;
    seekCutPreview(range.start);
  }
  renderCutTimelineRanges();
  updateTimelineRangeConfirmation();
  window.requestAnimationFrame(() => {
    cutFrameTimelineRanges
      .querySelector(
        `[data-range-id="${rangeId}"] [data-drag-mode="${mode}"]`,
      )
      ?.focus({ preventScroll: true });
  });
  updateCutTimelineStatus(
    `已调整待确认区间 ${formatCutRange(range.start, range.end)}，确认后才会删除。`,
    "neutral",
    "selection",
  );
  updateSelectionSummary();
}

function setupCutPreviewControls() {
  let lastAudibleVolume = 1;
  const safeDuration = () => cutTimelineDuration();
  const skipSelectedRangeDuringPlayback = () => {
    if (cutPreviewVideo.paused) return null;
    const current = cutPreviewVideo.currentTime || 0;
    const range = getMergedSelection().find(
      ({ start, end }) => current >= start && current < end - 0.001,
    );
    if (!range) return null;
    const nextTime = clamp(range.end, 0, safeDuration());
    if (nextTime <= current) return null;
    cutPreviewVideo.currentTime = nextTime;
    updateCutTimelineStatus(
      `剪辑预览已跳过 ${formatCutRange(range.start, range.end)}。`,
      "success",
      "preview",
    );
    return nextTime;
  };
  const updateTime = () => {
    const sourceTotal = safeDuration();
    let current = clamp(
      cutPreviewVideo.currentTime || 0,
      0,
      sourceTotal || 0,
    );
    if (
      noSpeechPreviewEnd !== null &&
      current >= noSpeechPreviewEnd - CUT_TIMELINE_STEP
    ) {
      cutPreviewVideo.pause();
      noSpeechPreviewEnd = null;
      updateCutTimelineStatus(
        "试听结束，请确认是否删除。",
        "success",
        "no-speech",
      );
    } else {
      current = skipSelectedRangeDuringPlayback() ?? current;
      if (
        cutSelectionPreviewEnd !== null &&
        current >= cutSelectionPreviewEnd - CUT_TIMELINE_STEP
      ) {
        cutPreviewVideo.pause();
        cutSelectionPreviewEnd = null;
        updateCutTimelineStatus(
          "左侧裁剪衔接预览结束，时间轴已自动拼接。",
          "success",
          "preview",
        );
      }
    }
    const spans = getEditedTimelineSpans();
    const total = editedCutTimelineDuration(spans);
    const editedCurrent = sourceTimeToEditedTime(current, spans);
    cutPreviewSeek.max = String(total);
    cutPreviewSeek.value = String(editedCurrent);
    cutPreviewSeek.setAttribute(
      "aria-valuetext",
      `${formatTime(editedCurrent)} / ${formatTime(total)}`,
    );
    cutPreviewTime.value = `${formatTime(editedCurrent)} / ${formatTime(total)}`;
    updateCutTimelinePlayhead();
  };
  const updatePlay = () => {
    const playing = !cutPreviewVideo.paused && !cutPreviewVideo.ended;
    if (playing) skipSelectedRangeDuringPlayback();
    cutPreviewPlay.setAttribute("aria-label", playing ? "暂停" : "播放");
    cutPreviewPlayIcon.hidden = playing;
    cutPreviewPauseIcon.hidden = !playing;
  };
  const updateVolume = () => {
    const muted = cutPreviewVideo.muted || cutPreviewVideo.volume === 0;
    cutPreviewMute.setAttribute("aria-label", muted ? "取消静音" : "静音");
    cutPreviewMute.setAttribute("aria-pressed", String(muted));
    cutPreviewVolumeIcon.hidden = muted;
    cutPreviewMutedIcon.hidden = !muted;
    cutPreviewVolume.value = String(muted ? 0 : cutPreviewVideo.volume);
  };
  const updateFullscreen = () => {
    const fullscreen = document.fullscreenElement === cutPreviewPlayer;
    cutPreviewFullscreen.setAttribute(
      "aria-label",
      fullscreen ? "退出全屏" : "进入全屏",
    );
    cutPreviewFullscreen.setAttribute("aria-pressed", String(fullscreen));
  };
  const togglePlayback = () => {
    if (cutPreviewVideo.paused || cutPreviewVideo.ended) {
      cutPreviewVideo.play().catch(() => {});
    } else {
      cutPreviewVideo.pause();
    }
  };
  const toggleFullscreen = async () => {
    try {
      if (document.fullscreenElement === cutPreviewPlayer) {
        await document.exitFullscreen();
      } else if (!document.fullscreenElement) {
        await cutPreviewPlayer.requestFullscreen();
      }
    } catch {
      // Playback and timeline remain usable when fullscreen is unavailable.
    }
  };

  cutPreviewPlay.addEventListener("click", togglePlayback);
  cutPreviewVideo.addEventListener("click", togglePlayback);
  cutPreviewVideo.addEventListener("dblclick", toggleFullscreen);
  cutPreviewSeek.addEventListener("input", () =>
    seekCutPreview(editedTimeToSourceTime(cutPreviewSeek.value)),
  );
  cutFrameTimelineSeek.addEventListener("input", () =>
    seekCutPreview(editedTimeToSourceTime(cutFrameTimelineSeek.value)),
  );
  cutPreviewMute.addEventListener("click", () => {
    if (cutPreviewVideo.muted || cutPreviewVideo.volume === 0) {
      cutPreviewVideo.muted = false;
      cutPreviewVideo.volume = lastAudibleVolume || 1;
    } else {
      lastAudibleVolume = cutPreviewVideo.volume || 1;
      cutPreviewVideo.muted = true;
    }
    updateVolume();
  });
  cutPreviewVolume.addEventListener("input", () => {
    const nextVolume = clamp(Number(cutPreviewVolume.value) || 0, 0, 1);
    cutPreviewVideo.volume = nextVolume;
    cutPreviewVideo.muted = nextVolume === 0;
    if (nextVolume > 0) lastAudibleVolume = nextVolume;
    updateVolume();
  });
  cutPreviewFullscreen.addEventListener("click", toggleFullscreen);
  document.addEventListener("fullscreenchange", updateFullscreen);
  cutPreviewVideo.addEventListener("loadedmetadata", () => {
    currentVideoDuration = Math.max(
      currentVideoDuration,
      Number.isFinite(cutPreviewVideo.duration) ? cutPreviewVideo.duration : 0,
    );
    syncCutVideoStageLayout();
    updateTime();
    refreshCutTimeline({ force: true });
  });
  for (const eventName of ["durationchange", "timeupdate", "emptied"]) {
    cutPreviewVideo.addEventListener(eventName, updateTime);
  }
  for (const eventName of ["play", "pause", "ended"]) {
    cutPreviewVideo.addEventListener(eventName, updatePlay);
  }
  cutPreviewVideo.addEventListener("volumechange", updateVolume);
  updateTime();
  updatePlay();
  updateVolume();
  updateFullscreen();
}

function scheduleCutTimelineResize() {
  window.clearTimeout(cutTimelineResizeTimer);
  cutTimelineResizeTimer = window.setTimeout(() => {
    syncCutVideoStageLayout();
    updateCutTimelineScale();
    cutTimelineRulerSignature = "";
    renderCutTimelineRuler();
    buildCutTimelineThumbnails();
  }, 180);
}

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function clearFormError() {
  formError.textContent = "";
  formError.hidden = true;
}

function clearUploadPreview() {
  selectedVideoPreview.pause();
  selectedVideoPreview.removeAttribute("src");
  selectedVideoPreview.load();
  if (selectedPreviewUrl) URL.revokeObjectURL(selectedPreviewUrl);
  selectedPreviewUrl = "";
  uploadPreview.hidden = true;
  uploadPicker.hidden = false;
  dropZone.classList.remove("has-preview");
}

function clearSelectedFile() {
  selectedFile = null;
  fileInput.value = "";
  fileSummary.hidden = true;
  startButton.disabled = true;
  clearUploadPreview();
}

function validateFile(file) {
  if (!file) return "请先选择一个视频文件。";
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return "仅支持 MP4、MOV、MKV 和 WebM 视频。";
  }
  if (file.size > MAX_FILE_SIZE) return "视频不能超过 1GB。";
  if (file.size === 0) return "所选文件为空，请重新选择。";
  return "";
}

function setSelectedFile(file) {
  clearFormError();
  const error = validateFile(file);
  if (error) {
    clearSelectedFile();
    showFormError(error);
    return;
  }

  clearUploadPreview();
  selectedFile = file;
  fileName.textContent = file.name;
  fileMeta.textContent = `${formatBytes(file.size)} · 等待上传`;
  fileSummary.hidden = false;
  startButton.disabled = false;
  selectedPreviewUrl = URL.createObjectURL(file);
  selectedVideoPreview.src = selectedPreviewUrl;
  uploadPicker.hidden = true;
  uploadPreview.hidden = false;
  dropZone.classList.add("has-preview");
}

function activateVideoSource(source) {
  const historyActive = source === "history";
  localSourcePanel.hidden = historyActive;
  historySourcePanel.hidden = !historyActive;
  localSourceTab.classList.toggle("is-active", !historyActive);
  historySourceTab.classList.toggle("is-active", historyActive);
  localSourceTab.setAttribute("aria-selected", String(!historyActive));
  historySourceTab.setAttribute("aria-selected", String(historyActive));
  localSourceTab.tabIndex = historyActive ? -1 : 0;
  historySourceTab.tabIndex = historyActive ? 0 : -1;
  if (historyActive) loadHistoryVersions();
}

function setHistoryStatus(message, state = "") {
  historyStatus.textContent = message;
  historyStatus.dataset.state = state;
}

function formatHistoryDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "保存时间未知";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function createHistoryAction(label, action, icon, className = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `history-action ${className}`.trim();
  button.dataset.action = action;
  button.innerHTML = `<iconify-icon icon="${icon}" aria-hidden="true"></iconify-icon><span></span>`;
  button.querySelector("span").textContent = label;
  return button;
}

function renderHistoryVersions() {
  historyList.replaceChildren();
  historyCountBadge.textContent = String(historyVersions.length);
  historyEmpty.hidden = historyVersions.length !== 0;

  for (const version of historyVersions) {
    const item = document.createElement("li");
    const card = document.createElement("article");
    card.className = "history-card";
    card.dataset.historyId = version.id;
    card.dataset.kind = version.kind;

    const media = document.createElement("div");
    media.className = "history-card-media";
    const video = document.createElement("video");
    video.controls = true;
    video.playsInline = true;
    video.preload = "none";
    video.src = version.videoUrl;
    if (version.thumbnailUrl) video.poster = version.thumbnailUrl;
    video.setAttribute("aria-label", `预览${version.name}`);
    const kind = document.createElement("span");
    kind.className = "history-kind-badge";
    kind.textContent = version.kindLabel;
    media.append(video, kind);

    const content = document.createElement("div");
    content.className = "history-card-content";
    const heading = document.createElement("div");
    heading.className = "history-card-heading";
    const titleBlock = document.createElement("div");
    titleBlock.className = "history-card-title";

    if (editingHistoryId === version.id) {
      const label = document.createElement("label");
      label.className = "history-rename-label";
      label.textContent = "版本名称";
      const input = document.createElement("input");
      input.className = "history-rename-input";
      input.dataset.historyRenameInput = version.id;
      input.value = version.name;
      input.maxLength = 80;
      input.autocomplete = "off";
      label.append(input);
      titleBlock.append(label);
    } else {
      const name = document.createElement("h4");
      name.textContent = version.name;
      titleBlock.append(name);
    }

    const savedAt = document.createElement("time");
    savedAt.dateTime = version.createdAt || "";
    savedAt.textContent = formatHistoryDate(version.createdAt);
    titleBlock.append(savedAt);
    heading.append(titleBlock);

    const meta = document.createElement("div");
    meta.className = "history-card-meta";
    const duration = document.createElement("span");
    duration.innerHTML = '<iconify-icon icon="ph:timer-bold" aria-hidden="true"></iconify-icon>';
    duration.append(formatDuration(version.duration));
    const size = document.createElement("span");
    size.innerHTML = '<iconify-icon icon="ph:hard-drives-bold" aria-hidden="true"></iconify-icon>';
    size.append(formatBytes(version.fileSize));
    meta.append(duration, size);

    const actions = document.createElement("div");
    actions.className = "history-card-actions";
    if (editingHistoryId === version.id) {
      actions.append(
        createHistoryAction("保存名称", "save-name", "ph:check-bold", "is-primary"),
        createHistoryAction("取消", "cancel-name", "ph:x-bold"),
      );
    } else {
      actions.append(
        createHistoryAction("使用此版本", "use", "ph:arrow-right-bold", "is-primary"),
        createHistoryAction("重命名", "rename", "ph:pencil-simple-bold"),
        createHistoryAction("删除", "delete", "ph:trash-bold", "is-danger"),
      );
    }
    for (const button of actions.querySelectorAll("button")) {
      button.disabled = historyBusyId !== null;
    }

    content.append(heading, meta, actions);
    card.append(media, content);
    item.append(card);
    historyList.append(item);
  }

  if (editingHistoryId) {
    window.requestAnimationFrame(() => {
      const input = historyList.querySelector(
        `[data-history-rename-input="${editingHistoryId}"]`,
      );
      input?.focus();
      input?.select();
    });
  }
}

async function loadHistoryVersions() {
  refreshHistoryButton.disabled = true;
  historyList.setAttribute("aria-busy", "true");
  setHistoryStatus("正在读取剪辑历史…");
  try {
    const response = await fetch("/api/history");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法读取剪辑历史。");
    historyVersions = payload.versions || [];
    editingHistoryId = null;
    renderHistoryVersions();
    setHistoryStatus(
      historyVersions.length
        ? `共 ${historyVersions.length} 个版本，剪辑版与艺术字版分别保存。`
        : "完成剪辑或生成艺术字后，系统会自动保存一个版本。",
      historyVersions.length ? "success" : "",
    );
  } catch (error) {
    setHistoryStatus(`${error.message} 请稍后重试。`, "error");
  } finally {
    refreshHistoryButton.disabled = false;
    historyList.removeAttribute("aria-busy");
  }
}

async function useHistoryVersion(version) {
  historyBusyId = version.id;
  renderHistoryVersions();
  setHistoryStatus(`正在恢复“${version.name}”…`);
  uploadCard.hidden = true;
  progressCard.hidden = false;
  resultCard.hidden = true;
  jobError.hidden = true;
  setProgress(72);
  liveStatus.textContent = "正在恢复历史视频和文字时间轴…";
  try {
    const response = await fetch(
      `/api/history/${encodeURIComponent(version.id)}/use`,
      { method: "POST" },
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法使用该历史版本。");
    rememberJob(payload.id);
    renderJob(payload);
  } catch (error) {
    uploadCard.hidden = false;
    progressCard.hidden = true;
    setHistoryStatus(`${error.message} 请重新选择一个版本。`, "error");
  } finally {
    historyBusyId = null;
    renderHistoryVersions();
  }
}

async function renameHistoryVersion(version) {
  const input = historyList.querySelector(
    `[data-history-rename-input="${version.id}"]`,
  );
  const name = input?.value.trim() || "";
  if (!name) {
    setHistoryStatus("版本名称不能为空。", "error");
    input?.focus();
    return;
  }
  historyBusyId = version.id;
  renderHistoryVersions();
  try {
    const response = await fetch(`/api/history/${encodeURIComponent(version.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法修改版本名称。");
    historyVersions = historyVersions.map((item) =>
      item.id === payload.id ? payload : item,
    );
    editingHistoryId = null;
    setHistoryStatus("版本名称已保存。", "success");
  } catch (error) {
    setHistoryStatus(error.message, "error");
  } finally {
    historyBusyId = null;
    renderHistoryVersions();
  }
}

async function deleteHistoryVersion(version) {
  const confirmed = await window.appConfirm({
    eyebrow: version.kindLabel,
    title: "删除这个历史版本？",
    message: `“${version.name}”的视频文件和文字时间轴将被永久删除，其他版本不会受影响。`,
    confirmText: "删除版本",
    tone: "danger",
    icon: "ph:trash-bold",
  });
  if (!confirmed) return;
  historyBusyId = version.id;
  renderHistoryVersions();
  try {
    const response = await fetch(`/api/history/${encodeURIComponent(version.id)}`, {
      method: "DELETE",
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法删除历史版本。");
    historyVersions = historyVersions.filter((item) => item.id !== version.id);
    if (editingHistoryId === version.id) editingHistoryId = null;
    setHistoryStatus("历史版本已删除。", "success");
  } catch (error) {
    setHistoryStatus(error.message, "error");
  } finally {
    historyBusyId = null;
    renderHistoryVersions();
  }
}

function resetToUpload() {
  cutDraftReady = false;
  cutDraftRevision = 0;
  cutDraftLastSignature = "";
  cutDraftSaveQueue = Promise.resolve();
  cutDraftNeedsServerSync = false;
  setCutDraftSaveStatus("剪辑草稿自动保存");
  setCutOperationLock(false);
  if (pollTimer) window.clearTimeout(pollTimer);
  if (editPollTimer) window.clearTimeout(editPollTimer);
  pollTimer = null;
  editPollTimer = null;
  currentJobId = null;
  forgetJob();
  currentSegments = [];
  currentEditableSegments = [];
  currentSuggestions = [];
  currentNoSpeechSuggestions = [];
  cutControlsLocked = false;
  currentVideoDuration = 0;
  timelineDeleteRanges = [];
  generatedCutSelectionSignature = "";
  pendingCutSelectionSignature = "";
  selectedTimelineRangeId = null;
  timelineRangeInProgress = false;
  timelineRangeConfirmationOpen = false;
  nextTimelineRangeId = 1;
  cutTimelineBuildId += 1;
  cutTimelineSignature = "";
  cutTimelineRulerSignature = "";
  selectedRanges.clear();
  selectedNoSpeechRanges.clear();
  ignoredSuggestions.clear();
  ignoredNoSpeechSuggestions.clear();
  noSpeechPreviewEnd = null;
  cutSelectionPreviewEnd = null;
  suggestionList.replaceChildren();
  suggestionState.classList.remove("is-empty", "is-warning");
  suggestionState.textContent = "正在读取 AI 分析结果…";
  noSpeechList?.replaceChildren();
  noSpeechState?.classList.remove("is-empty", "is-warning", "is-marked");
  if (noSpeechState) {
    noSpeechState.textContent = "正在读取无文字片段检测结果…";
  }
  if (selectAllNoSpeechButton) selectAllNoSpeechButton.hidden = true;
  document.body.classList.remove("has-result", "has-cut-selection");
  clearSelectedFile();
  startButton.querySelector("span").textContent = "开始提取文字";
  clearFormError();
  jobError.hidden = true;
  resultCard.hidden = true;
  progressCard.hidden = true;
  uploadCard.hidden = false;
  cutProgress.hidden = true;
  cutResult.hidden = true;
  setOriginalSourceActionsAllowed(true);
  cutError.hidden = true;
  editedVideo.removeAttribute("src");
  editedVideo.load();
  cutPreviewVideo.pause();
  cutPreviewVideo.removeAttribute("src");
  cutPreviewVideo.load();
  cutFrameTimeline.hidden = true;
  cutFrameTimelineScroll.scrollLeft = 0;
  cutFrameTimelineTrack.style.removeProperty("width");
  cutFrameTimelineRuler.replaceChildren();
  cutFrameTimelineText.replaceChildren();
  cutFrameTimelineThumbnails.replaceChildren();
  cutFrameTimelineRanges.replaceChildren();
  updateTimelineRangeConfirmation();
  updateCutTimelineStatus("");
  activateVideoSource("local");
  loadHistoryVersions();
  uploadCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function confirmAndResetProject() {
  const confirmed = await window.appConfirm({
    eyebrow: "项目状态检查",
    title: "确定重新开始？",
    message:
      "当前选择和未生成的设置不会保留；原视频和已经生成的文件仍会安全保留。",
    confirmText: "重新开始",
    icon: "ph:arrow-counter-clockwise-bold",
  });
  if (!confirmed) return;
  const jobId = currentJobId;
  cutDraftReady = false;
  try {
    await cutDraftSaveQueue;
    await clearPersistedCutDraft(jobId);
    removeLocalCutDraft(jobId);
    resetToUpload();
  } catch (error) {
    cutDraftReady = true;
    setCutDraftSaveStatus(error.message, "error");
    await window.appAlert({
      eyebrow: "剪辑草稿未清除",
      title: "暂时无法重新开始",
      message: error.message,
      confirmText: "知道了",
      tone: "danger",
      icon: "ph:warning-circle-bold",
    });
  }
}

function setProgress(value) {
  const normalized = Math.min(100, Math.max(0, Math.round(value)));
  progressBar.style.width = `${normalized}%`;
  progressTrack.setAttribute("aria-valuenow", String(normalized));
  progressPercent.textContent = `${normalized}%`;
}

function setStepState(element, state) {
  element.classList.toggle("is-active", state === "active");
  element.classList.toggle("is-complete", state === "complete");
}

function renderJob(job) {
  window.EditorSuite?.update(job);
  setProgress(job.progress || 0);
  liveStatus.textContent = job.stage || "正在处理…";
  jobError.hidden = true;

  if (job.status === "queued" || job.status === "extracting") {
    setStepState(stepUpload, "complete");
    setStepState(stepExtract, "active");
    setStepState(stepTranscribe, "pending");
  } else if (job.status === "transcribing") {
    setStepState(stepUpload, "complete");
    setStepState(stepExtract, "complete");
    setStepState(stepTranscribe, "active");
  } else if (job.status === "completed") {
    setStepState(stepUpload, "complete");
    setStepState(stepExtract, "complete");
    setStepState(stepTranscribe, "complete");
    renderResult(job);
  } else if (job.status === "failed") {
    jobErrorText.textContent = job.error || "未知错误，请重新尝试。";
    jobError.hidden = false;
    liveStatus.textContent = "处理失败";
  }
}

function renderResult(job) {
  cutDraftReady = false;
  cutDraftSaveQueue = Promise.resolve();
  const result = job.result || {};
  const segments = result.segments || [];
  currentJobId = job.id;
  currentSegments = segments;
  currentEditableSegments = resolveEditableSegments(
    segments,
    result.editableSegments,
  );
  cutControlsLocked = false;
  setCutOperationLock(false);
  currentVideoDuration = Math.max(
    0,
    Number(result.mediaDuration || result.duration || job.duration) || 0,
  );
  timelineDeleteRanges = [];
  generatedCutSelectionSignature = cutSelectionSignature(
    job.edit?.requestedRanges || [],
  );
  pendingCutSelectionSignature = "";
  selectedTimelineRangeId = null;
  timelineRangeInProgress = false;
  timelineRangeConfirmationOpen = false;
  nextTimelineRangeId = 1;
  cutTimelineBuildId += 1;
  cutTimelineSignature = "";
  cutTimelineRulerSignature = "";
  selectedRanges.clear();
  selectedNoSpeechRanges.clear();
  ignoredNoSpeechSuggestions.clear();
  noSpeechPreviewEnd = null;
  cutSelectionPreviewEnd = null;
  document.body.classList.add("has-result");
  renderSuggestions(
    result.suggestions || [],
    result.suggestionStatus || "unavailable",
  );
  renderNoSpeechSuggestions(
    result.noSpeechSuggestions || [],
    result.noSpeechStatus || "unavailable",
  );
  restorePersistedCutDraft(
    resolvePersistedCutDraft(job.cutDraft || null, currentJobId),
  );
  cutError.hidden = true;
  cutProgress.hidden = true;
  cutResult.hidden = true;
  setOriginalSourceActionsAllowed(!job.edit?.status);
  generateCutButton.querySelector("span").textContent = "生成剪辑视频";
  skipToArtButton.href =
    `/art-text?job=${encodeURIComponent(currentJobId)}&source=original`;
  directPipButton.href =
    `/picture-in-picture?job=${encodeURIComponent(currentJobId)}&source=original`;
  cutPreviewVideo.src =
    `/api/transcriptions/${encodeURIComponent(currentJobId)}/original-video`;
  cutPreviewVideo.load();

  renderCutSegments();
  updateSelectionSummary();
  cutDraftReady = true;
  if (cutDraftNeedsServerSync) {
    cutDraftLastSignature = "";
    scheduleCutDraftSave();
  }

  progressCard.hidden = true;
  resultCard.hidden = false;
  if (job.edit) renderEdit(job.edit);
  activateTextEditorPanel("cuts");
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  resultCard.focus({ preventScroll: true });
}

async function pollJob(jobId) {
  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法读取转写进度。请刷新后重试。");

    renderJob(payload);
    if (!['completed', 'failed'].includes(payload.status)) {
      pollTimer = window.setTimeout(() => pollJob(jobId), 1200);
    }
  } catch (error) {
    jobErrorText.textContent = error.message;
    jobError.hidden = false;
    liveStatus.textContent = "无法读取处理状态";
  }
}

function setCutProgress(value, message) {
  const normalized = Math.min(100, Math.max(0, Math.round(value)));
  cutProgressBar.style.width = `${normalized}%`;
  cutProgressTrack.setAttribute("aria-valuenow", String(normalized));
  cutProgressPercent.textContent = `${normalized}%`;
  cutStatus.textContent = message || "正在生成剪辑视频…";
  cutOperationLockTrack.setAttribute("aria-valuenow", String(normalized));
  cutOperationLockBar.style.width = `${normalized}%`;
  cutOperationLockPercent.textContent = `${normalized}%`;
  cutOperationLockMessage.textContent = message || "正在生成剪辑视频…";
}

function setCutOperationLock(locked, message = "") {
  cutOperationLock.hidden = !locked;
  document.body.classList.toggle("is-cut-operation-locked", locked);
  for (const target of cutOperationLockTargets) {
    if (locked) target.setAttribute("inert", "");
    else target.removeAttribute("inert");
  }
  if (!locked) return;
  if (message) cutOperationLockMessage.textContent = message;
  cutOperationLock.focus({ preventScroll: true });
}

function renderEdit(edit) {
  if (!edit) return;
  setOriginalSourceActionsAllowed(false);

  if (edit.status === "queued" || edit.status === "processing") {
    cutError.hidden = true;
    cutResult.hidden = true;
    cutProgress.hidden = false;
    setCutControlsDisabled(true);
    setCutOperationLock(true, edit.stage);
    setCutProgress(edit.progress || 0, edit.stage);
  } else if (edit.status === "completed") {
    generatedCutSelectionSignature =
      pendingCutSelectionSignature ||
      cutSelectionSignature(edit.requestedRanges || edit.ranges || []);
    pendingCutSelectionSignature = "";
    updateCutSegmentTimestamps();
    syncEditorSuiteCutDraftState({
      active: false,
      ranges: edit.ranges || edit.requestedRanges || [],
      sourceDuration: cutTimelineDuration(),
      duration: Number(edit.outputDuration) || 0,
      transcript: edit.transcript || null,
    });
    setCutOperationLock(false);
    cutProgress.hidden = true;
    cutError.hidden = true;
    cutResult.hidden = false;
    setCutControlsDisabled(false);
    generateCutButton.querySelector("span").textContent = "重新生成剪辑视频";
    const source = `${edit.outputUrl}?v=${Date.now()}`;
    editedVideo.src = source;
    downloadVideoButton.href = `${edit.outputUrl}?download=true`;
    continueArtButton.href =
      `/art-text?job=${encodeURIComponent(currentJobId)}&source=edited`;
    continuePipButton.href =
      `/picture-in-picture?job=${encodeURIComponent(currentJobId)}&source=edited`;
    cutDuration.textContent = `成片 ${formatTime(edit.outputDuration)}`;
    cutResult.scrollIntoView({ behavior: "smooth", block: "start" });
    cutResultTitle.focus({ preventScroll: true });
  } else if (edit.status === "failed") {
    setCutOperationLock(false);
    cutProgress.hidden = true;
    cutError.textContent = edit.error || "视频剪辑失败，请重新尝试。";
    cutError.hidden = false;
    setCutControlsDisabled(false);
  }
}

async function pollEdit(jobId) {
  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法读取剪辑进度。");

    window.EditorSuite?.update(payload);
    renderEdit(payload.edit);
    if (["queued", "processing"].includes(payload.edit?.status)) {
      editPollTimer = window.setTimeout(() => pollEdit(jobId), 1200);
    }
  } catch (error) {
    cutProgress.hidden = false;
    cutError.hidden = true;
    setCutOperationLock(true, "连接暂时中断，正在重新获取剪辑状态…");
    editPollTimer = window.setTimeout(() => pollEdit(jobId), 1800);
  }
}

async function generateCut() {
  const ranges = getMergedSelection();
  if (!currentJobId || ranges.length === 0) return;
  const deletedDuration = ranges.reduce(
    (total, range) => total + range.end - range.start,
    0,
  );
  const confirmed = await window.appConfirm({
    eyebrow: "剪辑范围确认",
    title: "生成这版剪辑视频？",
    message: `新视频将删除约 ${formatDuration(deletedDuration)} 的内容。原视频不会被覆盖，之后仍可重新剪辑。`,
    confirmText: "生成剪辑视频",
    icon: "ph:scissors-bold",
  });
  if (!confirmed) return;

  pendingCutSelectionSignature = cutSelectionSignature(ranges);

  cutError.hidden = true;
  cutResult.hidden = true;
  cutProgress.hidden = false;
  setOriginalSourceActionsAllowed(false);
  setCutControlsDisabled(true);
  setCutOperationLock(true, "正在创建剪辑任务…");
  setCutProgress(5, "正在创建剪辑任务…");

  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(currentJobId)}/cuts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ranges,
          historyName: cutHistoryName.value.trim() || null,
        }),
      },
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法创建剪辑任务。");
    renderEdit(payload);
    pollEdit(currentJobId);
  } catch (error) {
    pendingCutSelectionSignature = "";
    setCutOperationLock(false);
    cutProgress.hidden = true;
    cutError.textContent = error.message;
    cutError.hidden = false;
    setCutControlsDisabled(false);
  }
}

function startUpload(file) {
  const formData = new FormData();
  formData.append("file", file);
  const request = new XMLHttpRequest();
  request.open("POST", "/api/transcriptions");
  request.responseType = "json";

  uploadCard.hidden = true;
  progressCard.hidden = false;
  resultCard.hidden = true;
  jobError.hidden = true;
  setProgress(0);
  setStepState(stepUpload, "active");
  setStepState(stepExtract, "pending");
  setStepState(stepTranscribe, "pending");
  liveStatus.textContent = "正在上传视频…";

  request.upload.addEventListener("progress", (event) => {
    if (!event.lengthComputable) return;
    const uploadPercent = Math.round((event.loaded / event.total) * 100);
    uploadStatus.textContent = `已上传 ${uploadPercent}%`;
    setProgress(Math.min(9, Math.round(uploadPercent * 0.09)));
  });

  request.addEventListener("load", () => {
    const payload = request.response || {};
    if (request.status < 200 || request.status >= 300) {
      jobErrorText.textContent = payload.detail || "上传失败，请检查视频后重试。";
      jobError.hidden = false;
      liveStatus.textContent = "上传失败";
      return;
    }
    uploadStatus.textContent = "上传完成";
    rememberJob(payload.id);
    renderJob(payload);
    pollJob(payload.id);
  });

  request.addEventListener("error", () => {
    jobErrorText.textContent = "网络连接中断，请重新选择视频上传。";
    jobError.hidden = false;
    liveStatus.textContent = "上传失败";
  });

  request.send(formData);
}

function setupAmbientParticles() {
  const context = ambientCanvas?.getContext("2d");
  if (!ambientCanvas || !context) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let points = [];
  let streaks = [];
  let width = 0;
  let height = 0;
  let frameId = 0;
  let lastFrame = 0;
  let resizeFrame = 0;

  function seedPoints() {
    const count = Math.max(34, Math.min(76, Math.round(width / 31)));
    points = Array.from({ length: count }, (_, index) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.17,
      vy: (Math.random() - 0.5) * 0.13,
      radius: index % 10 === 0 ? 2.2 : 0.85 + Math.random() * 1.05,
      warm: index % 7 === 0,
      layer: index % 4,
      phase: Math.random() * Math.PI * 2,
    }));
    streaks = Array.from(
      { length: Math.max(4, Math.min(12, Math.round(width / 150))) },
      (_, index) => ({
        x: Math.random() * width,
        y: Math.random() * height,
        length: 78 + Math.random() * 160,
        speed: 0.24 + Math.random() * 0.42,
        warm: index % 3 === 0,
        phase: Math.random() * Math.PI * 2,
      }),
    );
  }

  function resizeCanvas() {
    const bounds = ambientCanvas.getBoundingClientRect();
    width = Math.max(1, bounds.width);
    height = Math.max(1, bounds.height);
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    ambientCanvas.width = Math.round(width * ratio);
    ambientCanvas.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    seedPoints();
    drawParticles(0, false);
  }

  function drawParticles(timestamp, advance = true) {
    context.clearRect(0, 0, width, height);
    const interfaceBusy =
      document.body.classList.contains("is-cut-operation-locked") ||
      (progressCard && !progressCard.hidden);
    const activity = interfaceBusy ? 1.42 : 1;
    const linkDistance = (width > 1100 ? 190 : 126) * activity;
    const delta = lastFrame ? Math.min(2.2, (timestamp - lastFrame) / 16.67) : 1;
    lastFrame = timestamp;

    if (advance) {
      for (const point of points) {
        const drift =
          0.68 + Math.sin(timestamp * 0.00032 + point.phase) * 0.24 + point.layer * 0.06;
        point.x += point.vx * delta * drift * activity;
        point.y += point.vy * delta * drift * activity;
        if (point.x < -8) point.x = width + 8;
        if (point.x > width + 8) point.x = -8;
        if (point.y < -8) point.y = height + 8;
        if (point.y > height + 8) point.y = -8;
      }
      for (const streak of streaks) {
        const glide = 0.62 + Math.sin(timestamp * 0.00028 + streak.phase) * 0.18;
        streak.x += streak.speed * delta * glide * activity;
        if (streak.x - streak.length > width + 60) {
          streak.x = -streak.length - Math.random() * 140;
          streak.y = Math.random() * height;
        }
      }
    }

    context.save();
    context.globalCompositeOperation = "lighter";
    for (const streak of streaks) {
      const alpha =
        (streak.warm ? 0.12 : 0.095) *
        activity *
        (0.7 + Math.sin(timestamp * 0.001 + streak.phase) * 0.3);
      context.beginPath();
      context.moveTo(streak.x, streak.y);
      context.lineTo(streak.x + streak.length, streak.y - streak.length * 0.04);
      context.strokeStyle = streak.warm
        ? `rgba(211, 117, 55, ${alpha})`
        : `rgba(203, 226, 101, ${alpha})`;
      context.lineWidth = streak.warm ? 0.9 : 0.7;
      context.stroke();
    }
    context.restore();

    for (let index = 0; index < points.length; index += 1) {
      const point = points[index];
      for (let neighborIndex = index + 1; neighborIndex < points.length; neighborIndex += 1) {
        const neighbor = points[neighborIndex];
        const distance = Math.hypot(point.x - neighbor.x, point.y - neighbor.y);
        if (distance >= linkDistance) continue;
        context.beginPath();
        context.moveTo(point.x, point.y);
        context.lineTo(neighbor.x, neighbor.y);
        const alpha = (1 - distance / linkDistance) * (point.warm || neighbor.warm ? 0.18 : 0.12);
        context.strokeStyle = point.warm || neighbor.warm
          ? `rgba(211, 117, 55, ${alpha})`
          : `rgba(196, 210, 111, ${alpha})`;
        context.lineWidth = point.layer === neighbor.layer ? 0.72 : 0.5;
        context.stroke();
      }
    }

    for (const point of points) {
      const pulse = 0.76 + Math.sin(timestamp * 0.0012 + point.phase) * 0.24;
      context.beginPath();
      context.arc(point.x, point.y, point.radius * pulse, 0, Math.PI * 2);
      context.fillStyle = point.warm
        ? "rgba(220, 126, 68, 0.64)"
        : "rgba(210, 225, 128, 0.62)";
      context.fill();
    }
  }

  function animate(timestamp) {
    drawParticles(timestamp, !reducedMotion.matches);
    if (!reducedMotion.matches && !document.hidden) {
      frameId = window.requestAnimationFrame(animate);
    }
  }

  function restartAnimation() {
    window.cancelAnimationFrame(frameId);
    lastFrame = 0;
    if (reducedMotion.matches || document.hidden) {
      drawParticles(0, false);
      return;
    }
    frameId = window.requestAnimationFrame(animate);
  }

  window.addEventListener("resize", () => {
    window.cancelAnimationFrame(resizeFrame);
    resizeFrame = window.requestAnimationFrame(() => {
      resizeCanvas();
      restartAnimation();
    });
  });
  document.addEventListener("visibilitychange", restartAnimation);
  reducedMotion.addEventListener?.("change", restartAnimation);
  resizeCanvas();
  restartAnimation();
}

fileInput.addEventListener("change", () => setSelectedFile(fileInput.files?.[0]));

localSourceTab.addEventListener("click", () => activateVideoSource("local"));
historySourceTab.addEventListener("click", () => activateVideoSource("history"));
for (const tab of [localSourceTab, historySourceTab]) {
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const nextSource = tab === localSourceTab ? "history" : "local";
    activateVideoSource(nextSource);
    (nextSource === "history" ? historySourceTab : localSourceTab).focus();
  });
}

refreshHistoryButton.addEventListener("click", loadHistoryVersions);

historyList.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) return;
  const actionButton = event.target.closest("[data-action]");
  const card = event.target.closest("[data-history-id]");
  if (!actionButton || !card || actionButton.disabled) return;
  const version = historyVersions.find(
    (item) => item.id === card.dataset.historyId,
  );
  if (!version) return;
  const action = actionButton.dataset.action;
  if (action === "use") useHistoryVersion(version);
  if (action === "rename") {
    editingHistoryId = version.id;
    renderHistoryVersions();
  }
  if (action === "save-name") renameHistoryVersion(version);
  if (action === "cancel-name") {
    editingHistoryId = null;
    setHistoryStatus("已取消重命名。");
    renderHistoryVersions();
  }
  if (action === "delete") deleteHistoryVersion(version);
});

historyList.addEventListener("keydown", (event) => {
  const input = event.target.closest?.("[data-history-rename-input]");
  if (!input) return;
  const version = historyVersions.find(
    (item) => item.id === input.dataset.historyRenameInput,
  );
  if (!version) return;
  if (event.key === "Enter") {
    event.preventDefault();
    renameHistoryVersion(version);
  } else if (event.key === "Escape") {
    event.preventDefault();
    editingHistoryId = null;
    renderHistoryVersions();
  }
});

uploadPicker.addEventListener("click", () => {
  fileInput.click();
});

changeFileButton.addEventListener("click", () => {
  fileInput.value = "";
  fileInput.click();
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}

dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (file) setSelectedFile(file);
});

segmentList.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) return;
  const segmentButton = event.target.closest(".segment-toggle");
  if (!segmentButton) {
    const segmentItem = event.target.closest(".segment-item[data-segment-index]");
    if (segmentItem) {
      openSegmentEditDialog(Number(segmentItem.dataset.segmentIndex));
    }
    return;
  }
  const segment = currentEditableSegments[Number(segmentButton.dataset.segmentIndex)];
  if (!segment) return;

  const range = {
    start: Number(segment.start),
    end: Number(segment.end),
    text: String(segment.text || ""),
  };
  if (!Number.isFinite(range.start) || !Number.isFinite(range.end)) return;
  if (range.end <= range.start) return;
  const key = rangeKey(range.start, range.end);
  if (selectedRanges.has(key)) {
    selectedRanges.delete(key);
    updateSelectionSummary();
    seekCutPreview(range.start);
    return;
  }
  seekCutPreview(range.start);
  for (const [selectedKey, selectedRange] of selectedRanges.entries()) {
    const selectedStart = Number(
      selectedRange.originalStart ?? selectedRange.start,
    );
    const selectedEnd = Number(
      selectedRange.originalEnd ?? selectedRange.end,
    );
    if (
      selectedStart >= range.start &&
      selectedEnd <= range.end
    ) {
      selectedRanges.delete(selectedKey);
    }
  }
  const expandedRange = expandRangeToAdjacentSilence(range);
  selectedRanges.set(key, expandedRange);
  updateSelectionSummary();
  previewSelectedCutRange(expandedRange);
});

for (const eventName of ["select", "mouseup", "keyup"]) {
  segmentEditText.addEventListener(eventName, updateSegmentEditSelection);
}
segmentEditClose.addEventListener("click", closeSegmentEditDialog);
segmentEditDialog.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeSegmentEditDialog();
});
segmentEditDialog.addEventListener("click", (event) => {
  if (event.target === segmentEditDialog) closeSegmentEditDialog();
});
splitSegmentButton.addEventListener("click", () => {
  applyEditableSegmentOperation("split");
});
mergeSegmentUpButton.addEventListener("click", () => {
  applyEditableSegmentOperation("merge_up");
});
mergeSegmentDownButton.addEventListener("click", () => {
  applyEditableSegmentOperation("merge_down");
});

suggestionList.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) return;
  const button = event.target.closest(".suggestion-action");
  const card = event.target.closest(".suggestion-card");
  if (!button || !card || button.disabled) return;
  const suggestion = currentSuggestions.find(
    (item) => item.id === card.dataset.suggestionId,
  );
  if (!suggestion) return;
  seekCutPreview(suggestion.start);

  const ranges = getSuggestionRanges(suggestion);
  let previewRange = null;
  if (button.dataset.action === "apply") {
    if (isSuggestionSelected(suggestion)) return;
    ignoredSuggestions.delete(suggestion.id);
    const expandedRanges = [];
    for (const range of ranges) {
      const key = rangeKey(range.start, range.end);
      const expandedRange = expandRangeToAdjacentSilence(range);
      selectedRanges.set(key, expandedRange);
      expandedRanges.push(expandedRange);
    }
    if (expandedRanges.length > 0) {
      previewRange = {
        start: Math.min(...expandedRanges.map(({ start }) => start)),
        end: Math.max(...expandedRanges.map(({ end }) => end)),
        adjacentSilenceBefore: expandedRanges.reduce(
          (total, range) => total + range.adjacentSilenceBefore,
          0,
        ),
        adjacentSilenceAfter: expandedRanges.reduce(
          (total, range) => total + range.adjacentSilenceAfter,
          0,
        ),
      };
    }
  } else if (button.dataset.action === "ignore") {
    if (ignoredSuggestions.has(suggestion.id)) {
      ignoredSuggestions.delete(suggestion.id);
    } else {
      ignoredSuggestions.add(suggestion.id);
    }
  }
  updateSelectionSummary();
  if (previewRange) previewSelectedCutRange(previewRange);
});

selectAllSuggestionsButton.addEventListener("click", () => {
  if (cutControlsLocked || currentSuggestions.length === 0) return;
  const candidates = currentSuggestions.filter(
    (suggestion) =>
      !isSuggestionSelected(suggestion) &&
      !ignoredSuggestions.has(suggestion.id),
  );
  if (candidates.length === 0) return;
  for (const suggestion of candidates) {
    for (const range of getSuggestionRanges(suggestion)) {
      const key = rangeKey(range.start, range.end);
      selectedRanges.set(key, expandRangeToAdjacentSilence(range));
    }
  }
  updateSelectionSummary();
  const firstRanges = getSuggestionRanges(candidates[0]);
  if (firstRanges.length > 0) {
    const firstExpandedRanges = firstRanges.map((range) =>
      expandRangeToAdjacentSilence(range),
    );
    previewSelectedCutRange({
      start: Math.min(...firstExpandedRanges.map(({ start }) => start)),
      end: Math.max(...firstExpandedRanges.map(({ end }) => end)),
      adjacentSilenceBefore: firstExpandedRanges.reduce(
        (total, range) => total + range.adjacentSilenceBefore,
        0,
      ),
      adjacentSilenceAfter: firstExpandedRanges.reduce(
        (total, range) => total + range.adjacentSilenceAfter,
        0,
      ),
    });
  }
});

noSpeechList?.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) return;
  const button = event.target.closest(".no-speech-action");
  const card = event.target.closest(".no-speech-card");
  if (!button || !card || button.disabled) return;
  const suggestion = currentNoSpeechSuggestions.find(
    (item) => item.id === card.dataset.noSpeechId,
  );
  const range = getNoSpeechRange(suggestion);
  if (!suggestion || !range) return;

  if (button.dataset.action === "preview") {
    previewNoSpeechSuggestion(suggestion);
    return;
  }
  seekCutPreview(range.start);
  let markedForPreview = false;
  if (button.dataset.action === "apply") {
    if (selectedNoSpeechRanges.has(range.id)) return;
    ignoredNoSpeechSuggestions.delete(suggestion.id);
    if (suggestion.deletable !== false) {
      selectedNoSpeechRanges.set(range.id, range);
      markedForPreview = true;
    }
  } else if (button.dataset.action === "ignore") {
    if (ignoredNoSpeechSuggestions.has(suggestion.id)) {
      ignoredNoSpeechSuggestions.delete(suggestion.id);
    } else {
      ignoredNoSpeechSuggestions.add(suggestion.id);
    }
  }
  updateSelectionSummary();
  if (markedForPreview) previewSelectedCutRange(range);
});

selectAllNoSpeechButton?.addEventListener("click", () => {
  if (cutControlsLocked) return;
  const candidates = currentNoSpeechSuggestions.filter(
    (suggestion) =>
      !suggestion.protected &&
      suggestion.deletable !== false &&
      !ignoredNoSpeechSuggestions.has(suggestion.id) &&
      !isNoSpeechSelected(suggestion),
  );
  if (candidates.length === 0) return;
  for (const suggestion of candidates) {
    const range = getNoSpeechRange(suggestion);
    if (!range) continue;
    selectedNoSpeechRanges.set(range.id, range);
  }
  updateSelectionSummary();
  const firstRange = getNoSpeechRange(candidates[0]);
  if (firstRange) previewSelectedCutRange(firstRange);
});

cutFrameTimelineTrack.addEventListener("pointerdown", beginCutTimelineSelection);
cutFrameTimelineRanges.addEventListener(
  "pointerdown",
  beginTimelineRangeAdjustment,
);
cutFrameTimelineRanges.addEventListener("keydown", adjustTimelineRangeWithKeyboard);
cutFrameTimelineRanges.addEventListener("click", (event) => {
  const rangeElement = event.target.closest(".cut-timeline-delete-range");
  if (!rangeElement) return;
  selectedTimelineRangeId = Number(rangeElement.dataset.rangeId);
  renderCutTimelineRanges();
});
generateCutButton.addEventListener("click", generateCut);

removeFileButton.addEventListener("click", () => {
  clearSelectedFile();
  clearFormError();
  uploadPicker.focus();
});

selectedVideoPreview.addEventListener("loadedmetadata", () => {
  if (!selectedFile) return;
  const duration = Number(selectedVideoPreview.duration);
  const durationLabel = Number.isFinite(duration)
    ? ` · ${formatDuration(duration)}`
    : "";
  fileMeta.textContent = `${formatBytes(selectedFile.size)}${durationLabel} · 等待上传`;
});

selectedVideoPreview.addEventListener("error", () => {
  if (!selectedFile) return;
  fileMeta.textContent = `${formatBytes(selectedFile.size)} · 当前浏览器无法预览此格式，仍可正常上传`;
});

window.addEventListener("beforeunload", () => {
  if (selectedPreviewUrl) URL.revokeObjectURL(selectedPreviewUrl);
});

uploadForm.addEventListener("submit", (event) => {
  event.preventDefault();
  clearFormError();
  const error = validateFile(selectedFile);
  if (error) {
    showFormError(error);
    return;
  }
  startUpload(selectedFile);
});

retryButton.addEventListener("click", resetToUpload);
restartProjectButton.addEventListener("click", confirmAndResetProject);

for (const tab of textEditorTabs) {
  tab.addEventListener("click", () => {
    activateTextEditorPanel(tab.dataset.textEditorTab);
  });
  tab.addEventListener("keydown", handleTextEditorTabKeydown);
}
setupCutPreviewControls();
window.addEventListener("resize", scheduleCutTimelineResize);
setupAmbientParticles();
loadHistoryVersions();

const rememberedJobId = getRememberedJobId();
if (rememberedJobId) {
  rememberJob(rememberedJobId);
  uploadCard.hidden = true;
  progressCard.hidden = false;
  resultCard.hidden = true;
  jobError.hidden = true;
  setProgress(0);
  liveStatus.textContent = "正在恢复转写结果…";
  pollJob(rememberedJobId);
}
