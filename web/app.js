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
const progressTitle = document.querySelector("#progress-title");
const liveStatus = document.querySelector("#liveStatus");
const uploadStatus = document.querySelector("#uploadStatus");
const extractStatus = document.querySelector("#extractStatus");
const transcribeStatus = document.querySelector("#transcribeStatus");
const stepUpload = document.querySelector("#stepUpload");
const stepExtract = document.querySelector("#stepExtract");
const stepTranscribe = document.querySelector("#stepTranscribe");
const jobError = document.querySelector("#jobError");
const jobErrorText = document.querySelector("#jobErrorText");
const retryButton = document.querySelector("#retryButton");
const segmentList = document.querySelector("#segmentList");
const transcriptNowPlayingLayer = document.querySelector(
  "#transcriptNowPlayingLayer",
);
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
const saveSegmentTextButton = document.querySelector("#saveSegmentTextButton");
const splitSegmentButton = document.querySelector("#splitSegmentButton");
const mergeSegmentUpButton = document.querySelector("#mergeSegmentUpButton");
const mergeSegmentDownButton = document.querySelector(
  "#mergeSegmentDownButton",
);
const clearSelectionButton = document.querySelector("#clearSelectionButton");
const generateCutButton = document.querySelector("#generateCutButton");
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
const CUT_SAFE_NO_SPEECH_MIN_DURATION = 0.45;
const CUT_TIMELINE_TEXT_GAP_COVERAGE_MAX = 1.5;
const CUT_TIMELINE_THUMB_MIN = 8;
const CUT_TIMELINE_THUMB_MAX = 180;
const CUT_TIMELINE_MAJOR_TICK_WIDTH = 72;
const CUT_TIMELINE_MIN_PIXELS_PER_SECOND = 22;
const CUT_TIMELINE_TEXT_CHAR_WIDTH = 10;
const CUT_TIMELINE_TEXT_LINES = 2;
const CUT_HISTORY_LIMIT = 40;
const CUT_HISTORY_COALESCE_MS = 800;
const transcriptFollowScrollController =
  window.TranscriptFollowScroll.createController({
    layer: transcriptNowPlayingLayer,
  });

let selectedFile = null;
let selectedPreviewUrl = "";
let pollTimer = null;
let editPollTimer = null;
let generationModalActive = false;
let currentJobId = null;
let currentSegments = [];
let currentEditableSegments = [];
let activeSegmentEditIndex = null;
let segmentOperationInFlight = false;
let currentSuggestions = [];
let currentNoSpeechSuggestions = [];
let currentAudioQuietRanges = [];
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
let transcriptPreviewRange = null;
let activeTranscriptSegmentIndex = -1;
let activeTranscriptSegmentKey = "";
let activeTranscriptItem = null;
let transcriptPlaybackEntries = [];
let transcriptPlaybackEntryByKey = new Map();
let transcriptPlaybackCursor = -1;
let transcriptPlaybackActiveCursor = -1;
let transcriptPlaybackLastTime = Number.NEGATIVE_INFINITY;
let cutPlaybackFrameClock = null;
let editedTimelineSpansCache = null;
let cutTimelinePixelsPerSecondCache = null;
let cutTimelineScaleSignature = "";
let cutTimelineTrackWidthCache = 0;
let cutTimelineTextPlaybackEntries = [];
let cutTimelineTextPlaybackFloorCursor = -1;
let cutTimelineTextPlaybackCursor = -1;
let cutTimelineTextPlaybackLastTime = Number.NEGATIVE_INFINITY;
let cutDraftReady = false;
let cutDraftRevision = 0;
let cutDraftLastSignature = "";
let cutDraftSaveQueue = Promise.resolve();
let cutDraftNeedsServerSync = false;
let automaticNoSpeechInitialized = false;
let originalSourceActionsAllowed = true;
let historyVersions = [];
let editingHistoryId = null;
let historyBusyId = null;
const selectedRanges = new Map();
const selectedNoSpeechRanges = new Map();
let cutHistoryBaseline = null;
let cutHistoryEntries = [];
let cutHistoryIndex = 0;
let cutTimelineDocument = window.EditorTimeline.normalizeDocument({
  duration: 0,
  tracks: [],
});
let suppressEditorSuiteCutSync = false;
let cutHistoryLastState = null;
let cutHistoryPendingMeta = null;
let cutHistoryReplaying = false;

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
  const sourceSegments = currentEditableSegments.length
    ? currentEditableSegments
    : currentSegments;
  const tokens = sourceSegments.flatMap((segment) => getSegmentTokens(segment));

  for (const [key, range] of [...selectedRanges.entries()]) {
    const start = Number(range.originalStart ?? range.start);
    const end = Number(range.originalEnd ?? range.end);
    const selectedTokens = tokens.filter(
      (token) => Number(token.start) < end && Number(token.end) > start,
    );
    if (!selectedTokens.length) {
      selectedRanges.delete(key);
      continue;
    }
    selectedRanges.set(key, {
      ...range,
      text: selectedTokens.map((token) => token.text).join(""),
    });
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
  const value = String(text || "");
  const characters = [...value].filter(
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

  const tokens = [];
  let pendingPrefix = "";
  let spokenIndex = 0;
  for (const character of value) {
    if (/\p{P}|\s/u.test(character)) {
      if (tokens.length) {
        tokens.at(-1).text += character;
      } else {
        pendingPrefix += character;
      }
      continue;
    }
    const tokenStart = safeStart + (duration * spokenIndex) / characters.length;
    spokenIndex += 1;
    const tokenEnd = spokenIndex === characters.length
      ? safeEnd
      : safeStart + (duration * spokenIndex) / characters.length;
    tokens.push({
      text: `${pendingPrefix}${character}`,
      start: Number(tokenStart.toFixed(3)),
      end: Number(tokenEnd.toFixed(3)),
    });
    pendingPrefix = "";
  }
  if (pendingPrefix && tokens.length) tokens.at(-1).text += pendingPrefix;
  return tokens;
}

function getValidTimedTranscriptItems(items) {
  if (!Array.isArray(items)) return [];
  return items.flatMap((item) => {
    const start = Number(item?.start);
    const end = Number(item?.end);
    return String(item?.text || "").trim() &&
      Number.isFinite(start) &&
      Number.isFinite(end) &&
      end > start
      ? [{ ...item, start, end }]
      : [];
  });
}

function getSegmentTokens(segment) {
  const timedItems = [segment.words, segment.asrWords, [segment]]
    .map(getValidTimedTranscriptItems)
    .find((items) => items.length) || [];
  return timedItems.flatMap((item) =>
    splitTextIntoCharacterTokens(item.text, item.start, item.end).map(
      (token) => ({
        ...token,
        parentWordStart: item.start,
        parentWordEnd: item.end,
      }),
    ),
  );
}

function getTranscriptCharacterUnits(segments = null) {
  const sourceSegments = Array.isArray(segments)
    ? segments
    : currentSegments.length
      ? currentSegments
      : currentEditableSegments;
  const seen = new Set();
  const units = [];
  for (const segment of sourceSegments) {
    for (const token of getSegmentTokens(segment)) {
      const key = `${rangeKey(token.start, token.end)}:${token.text}`;
      if (seen.has(key)) continue;
      seen.add(key);
      units.push(token);
    }
  }
  return units.sort(
    (left, right) => left.start - right.start || left.end - right.end,
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

function selectedTextRangeKeysAtTime(sourceTime) {
  return [...selectedRanges.entries()].flatMap(([key, range]) => {
    const start = Number(range.originalStart ?? range.start);
    const end = Number(range.originalEnd ?? range.end);
    return Number.isFinite(start) &&
      Number.isFinite(end) &&
      sourceTime >= start &&
      sourceTime < end
      ? [key]
      : [];
  });
}

function suggestionTextRangeKeysAtTime(sourceTime) {
  return currentSuggestions.flatMap((suggestion) =>
    getSuggestionRanges(suggestion).flatMap((range) => {
      const start = Number(range.start);
      const end = Number(range.end);
      return sourceTime >= start && sourceTime < end
        ? [rangeKey(start, end)]
        : [];
    }),
  );
}

function buildSegmentTextRuns(segment, deletedRanges) {
  const tokens = getSegmentTokens(segment);
  const words = tokens.length
    ? tokens
    : [
        {
          text: String(segment.text || "暂无识别文字"),
          start: Number(segment.start),
          end: Number(segment.end),
        },
      ];
  const runs = [];
  for (const word of words) {
    const start = Number(word.start);
    const end = Number(word.end);
    const midpoint = start + (end - start) / 2;
    const rangeKeys = Number.isFinite(midpoint)
      ? selectedTextRangeKeysAtTime(midpoint)
      : [];
    const suggestionRangeKeys = Number.isFinite(midpoint)
      ? suggestionTextRangeKeysAtTime(midpoint)
      : [];
    const deletedRange = Number.isFinite(midpoint) && deletedRanges.find(
      (range) =>
        midpoint >= Number(range.start) && midpoint < Number(range.end),
    );
    const kind = rangeKeys.length > 0
      ? "restore"
      : deletedRange
        ? "deleted"
        : "edit";
    const presentationKey = rangeKeys.length > 0
      ? `selected:${rangeKeys.join("|")}`
      : deletedRange
        ? `deleted:${rangeKey(deletedRange.start, deletedRange.end)}`
        : suggestionRangeKeys.length > 0
          ? `suggestion:${suggestionRangeKeys.join("|")}`
          : "retained";
    const previous = runs.at(-1);
    const canMerge = Boolean(
      previous &&
        previous.kind === kind &&
        (kind === "restore" || previous.presentationKey === presentationKey),
    );
    if (canMerge) {
      previous.text += String(word.text || "");
      previous.end = Number.isFinite(end) ? end : previous.end;
      previous.rangeKeys = [...new Set([...previous.rangeKeys, ...rangeKeys])];
      previous.suggestionRangeKeys = [
        ...new Set([
          ...previous.suggestionRangeKeys,
          ...suggestionRangeKeys,
        ]),
      ];
    } else {
      runs.push({
        kind,
        text: String(word.text || ""),
        start,
        end,
        rangeKeys,
        suggestionRangeKeys,
        presentationKey,
      });
    }
  }
  return runs.filter((run) => String(run.text || "").trim());
}

function renderSegmentTextRun(container, run, segmentIndex) {
  if (run.kind === "restore") {
    const restoreButton = document.createElement("button");
    restoreButton.type = "button";
    restoreButton.className = "segment-text-run segment-restore-button";
    restoreButton.dataset.rangeKeys = JSON.stringify(run.rangeKeys);
    restoreButton.dataset.start = String(run.start);
    restoreButton.disabled = cutControlsLocked;
    restoreButton.title = "恢复这处文字";
    restoreButton.setAttribute("aria-label", `恢复已删除文字：${run.text}`);
    const icon = document.createElement("iconify-icon");
    icon.setAttribute("icon", "ph:arrow-counter-clockwise-bold");
    icon.setAttribute("aria-hidden", "true");
    const label = document.createElement("span");
    label.className = "segment-text-run-label";
    label.textContent = run.text;
    restoreButton.append(icon, label);
    container.append(restoreButton);
    return;
  }
  if (run.kind === "deleted") {
    const deletedText = document.createElement("span");
    deletedText.className = "segment-text-run segment-deleted-text";
    deletedText.textContent = run.text;
    deletedText.setAttribute("aria-label", `已由时间轴删除：${run.text}`);
    container.append(deletedText);
    return;
  }
  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.className = "segment-text-run segment-edit-button";
  editButton.dataset.segmentIndex = String(segmentIndex);
  editButton.disabled = cutControlsLocked;
  editButton.textContent = run.text;
  editButton.setAttribute("aria-label", `编辑文字段：${run.text}`);
  container.append(editButton);
}

function renderTextSegmentItem(run, segmentIndex, displayIndex) {
  const segmentStart = Number(run.start);
  const segmentEnd = Number(run.end);
  const hasValidRange =
    Number.isFinite(segmentStart) &&
    Number.isFinite(segmentEnd) &&
    segmentEnd > segmentStart;
  const allSelected =
    run.rangeKeys.length > 0 &&
    run.rangeKeys.every((key) => selectedRanges.has(key));
  const item = document.createElement("li");
  item.className = "segment-item is-editable";
  item.classList.toggle("has-selection", allSelected);
  item.classList.toggle("is-delete-fragment", run.kind === "restore");
  item.classList.toggle(
    "is-restored-fragment",
    run.kind === "edit" && run.suggestionRangeKeys.length > 0,
  );
  item.dataset.segmentIndex = String(segmentIndex);
  item.dataset.displayIndex = String(displayIndex);
  item.dataset.displayKind = run.kind;
  item.dataset.displayStart = String(segmentStart);
  item.dataset.displayEnd = String(segmentEnd);
  item.dataset.displayText = run.text;
  item.dataset.rangeKeys = JSON.stringify(run.rangeKeys);
  item.dataset.displayKey =
    `${segmentIndex}:${run.presentationKey}:${rangeKey(segmentStart, segmentEnd)}`;

  const selectSegmentButton = document.createElement("button");
  selectSegmentButton.type = "button";
  selectSegmentButton.className = "segment-toggle";
  selectSegmentButton.dataset.segmentIndex = String(segmentIndex);
  selectSegmentButton.classList.toggle("is-selected", allSelected);
  selectSegmentButton.setAttribute("aria-pressed", String(allSelected));
  selectSegmentButton.setAttribute(
    "aria-label",
    `${allSelected ? "恢复删除文字" : "删除文字"}：${run.text}`,
  );
  selectSegmentButton.dataset.selectionDisabled = String(
    !hasValidRange || run.kind === "deleted",
  );
  selectSegmentButton.disabled =
    cutControlsLocked || !hasValidRange || run.kind === "deleted";

  const time = document.createElement("time");
  time.className = "segment-time";
  time.textContent = formatTime(segmentStart);
  time.setAttribute(
    "aria-label",
    `原片从 ${formatPreciseTime(segmentStart)} 到 ${formatPreciseTime(segmentEnd)}`,
  );

  const timeColumn = document.createElement("span");
  timeColumn.className = "segment-time-column";
  const currentBadge = document.createElement("span");
  currentBadge.className = "segment-current-badge";
  currentBadge.textContent = "播放中";
  currentBadge.setAttribute("aria-hidden", "true");
  currentBadge.hidden = true;
  timeColumn.append(time, currentBadge);

  const segmentText = document.createElement("div");
  segmentText.className = "segment-text";
  renderSegmentTextRun(segmentText, run, segmentIndex);

  const playButton = document.createElement("button");
  playButton.type = "button";
  playButton.className = "segment-play-button";
  playButton.dataset.segmentPreview = "true";
  playButton.disabled = cutControlsLocked || !hasValidRange;
  playButton.title = "播放当前段落";
  playButton.setAttribute("aria-label", `播放当前段落：${run.text}`);
  const playIcon = document.createElement("iconify-icon");
  playIcon.setAttribute("icon", "ph:play-fill");
  playIcon.setAttribute("aria-hidden", "true");
  playButton.append(playIcon);

  item.append(selectSegmentButton, timeColumn, segmentText, playButton);
  return item;
}

function renderNoSpeechSegmentItem(suggestion, displayIndex) {
  const range = getNoSpeechRange(suggestion);
  if (!range) return null;
  const selected = selectedNoSpeechRanges.has(range.id);
  const deletable = suggestion.deletable !== false;
  const duration = Math.max(0, range.end - range.start);
  const label = `空白 ${duration.toFixed(1)} 秒`;
  const item = document.createElement("li");
  item.className = "segment-item is-no-speech-fragment";
  item.classList.toggle("has-selection", selected);
  item.classList.toggle("is-delete-fragment", selected);
  item.classList.toggle("is-restored-no-speech", !selected && deletable);
  item.classList.toggle("is-protected-no-speech", !deletable);
  item.dataset.noSpeechId = range.id;
  item.dataset.displayIndex = String(displayIndex);
  item.dataset.displayKind = selected
    ? "no-speech-restore"
    : "no-speech";
  item.dataset.displayStart = String(range.start);
  item.dataset.displayEnd = String(range.end);
  item.dataset.displayText = label;
  item.dataset.displayKey =
    `no-speech:${range.id}:${rangeKey(range.start, range.end)}`;

  const toggleButton = document.createElement("button");
  toggleButton.type = "button";
  toggleButton.className = "segment-toggle";
  toggleButton.dataset.noSpeechId = range.id;
  toggleButton.classList.toggle("is-selected", selected);
  toggleButton.setAttribute("aria-pressed", String(selected));
  toggleButton.setAttribute(
    "aria-label",
    !deletable
      ? `不能删除整段空白：${label}`
      : `${selected ? "恢复删除空白" : "删除空白"}：${label}`,
  );
  toggleButton.dataset.selectionDisabled = String(!deletable);
  toggleButton.disabled = cutControlsLocked || !deletable;

  const time = document.createElement("time");
  time.className = "segment-time";
  time.textContent = formatTime(range.start);
  time.setAttribute(
    "aria-label",
    `原片从 ${formatPreciseTime(range.start)} 到 ${formatPreciseTime(range.end)}`,
  );
  const timeColumn = document.createElement("span");
  timeColumn.className = "segment-time-column";
  const currentBadge = document.createElement("span");
  currentBadge.className = "segment-current-badge";
  currentBadge.textContent = "播放中";
  currentBadge.setAttribute("aria-hidden", "true");
  currentBadge.hidden = true;
  timeColumn.append(time, currentBadge);

  const segmentText = document.createElement("div");
  segmentText.className = "segment-text segment-no-speech-content";
  const actionButton = document.createElement("button");
  actionButton.type = "button";
  actionButton.className =
    `segment-text-run segment-no-speech-button${selected ? " segment-restore-button" : ""}`;
  actionButton.dataset.noSpeechId = range.id;
  actionButton.disabled = cutControlsLocked;
  actionButton.setAttribute(
    "aria-label",
    selected ? `恢复已删除空白：${label}` : `试听空白：${label}`,
  );
  const icon = document.createElement("iconify-icon");
  icon.setAttribute(
    "icon",
    selected ? "ph:arrow-counter-clockwise-bold" : "ph:play-circle-bold",
  );
  icon.setAttribute("aria-hidden", "true");
  const copy = document.createElement("span");
  copy.className = "segment-no-speech-copy";
  const mainLabel = document.createElement("strong");
  mainLabel.className = selected ? "segment-text-run-label" : "";
  mainLabel.textContent = label;
  const meta = document.createElement("span");
  meta.className = "segment-no-speech-meta";
  meta.textContent = [
    noSpeechKindLabel(suggestion),
    noSpeechAudioLabel(suggestion),
    !deletable ? "保留整段视频" : selected ? "已自动删除" : "已恢复",
  ].join(" · ");
  copy.append(mainLabel, meta);
  actionButton.append(icon, copy);
  segmentText.append(actionButton);

  item.append(toggleButton, timeColumn, segmentText);
  return item;
}

function renderCutSegments() {
  transcriptFollowScrollController.reset();
  activeTranscriptSegmentIndex = -1;
  activeTranscriptSegmentKey = "";
  activeTranscriptItem = null;
  const deletedRanges = getCommittedTimelineSemanticDeleteRanges();
  const displayItems = [];
  currentEditableSegments.forEach((segment, segmentIndex) => {
    for (const run of buildSegmentTextRuns(segment, deletedRanges)) {
      displayItems.push({
        type: "text",
        start: Number(run.start),
        end: Number(run.end),
        segmentIndex,
        run,
      });
    }
  });
  for (const suggestion of currentNoSpeechSuggestions) {
    const range = getNoSpeechRange(suggestion);
    if (!range) continue;
    displayItems.push({
      type: "no-speech",
      start: range.start,
      end: range.end,
      suggestion,
    });
  }
  displayItems.sort((left, right) =>
    left.start - right.start ||
    left.end - right.end ||
    left.type.localeCompare(right.type),
  );

  const fragment = document.createDocumentFragment();
  displayItems.forEach((displayItem, displayIndex) => {
    const item = displayItem.type === "no-speech"
      ? renderNoSpeechSegmentItem(displayItem.suggestion, displayIndex)
      : renderTextSegmentItem(
          displayItem.run,
          displayItem.segmentIndex,
          displayIndex,
        );
    if (item) fragment.append(item);
  });
  segmentList.replaceChildren(fragment);
  updateCutSegmentTimestamps();
}

function updateCutSegmentText() {
  renderCutSegments();
}

function transcriptDisplayItems() {
  return [segmentList, transcriptNowPlayingLayer].flatMap((container) =>
    container
      ? [...container.querySelectorAll(".segment-item")]
      : [],
  );
}

function playbackCursorFloor(entries, currentIndex, lastTime, currentTime) {
  if (
    currentIndex >= 0 &&
    currentIndex < entries.length &&
    currentTime >= lastTime
  ) {
    let nextIndex = currentIndex;
    while (
      nextIndex + 1 < entries.length &&
      entries[nextIndex + 1].start <= currentTime
    ) {
      nextIndex += 1;
    }
    return nextIndex;
  }
  let low = 0;
  let high = entries.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (entries[middle].start <= currentTime) low = middle + 1;
    else high = middle;
  }
  return low - 1;
}

function rebuildTranscriptPlaybackEntries() {
  transcriptPlaybackEntries = transcriptDisplayItems()
    .flatMap((item) => {
      const start = Number(item.dataset.displayStart);
      const end = Number(item.dataset.displayEnd);
      if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
        return [];
      }
      const type = item.dataset.noSpeechId ? "no-speech" : "text";
      return [{
        displayIndex: Number(item.dataset.displayIndex) || 0,
        eligible: !item.classList.contains("is-removed-from-timeline"),
        end,
        item,
        key: String(item.dataset.displayKey || ""),
        priority: type === "no-speech" ? 2 : 1,
        segmentIndex: item.dataset.segmentIndex === undefined
          ? -1
          : Number(item.dataset.segmentIndex),
        start,
        type,
      }];
    })
    .sort((left, right) =>
      left.start - right.start ||
      left.end - right.end ||
      left.displayIndex - right.displayIndex,
    );
  let maximumEnd = Number.NEGATIVE_INFINITY;
  for (const entry of transcriptPlaybackEntries) {
    maximumEnd = Math.max(maximumEnd, entry.end);
    entry.maximumEnd = maximumEnd;
  }
  transcriptPlaybackEntryByKey = new Map(
    transcriptPlaybackEntries.map((entry) => [entry.key, entry]),
  );
  transcriptPlaybackCursor = -1;
  transcriptPlaybackActiveCursor = -1;
  transcriptPlaybackLastTime = Number.NEGATIVE_INFINITY;
}

function transcriptPlaybackEntryAtTime(currentTime) {
  const sourceTime = Number(currentTime);
  if (!Number.isFinite(sourceTime)) return null;
  if (transcriptPreviewRange) {
    const previewEntry = transcriptPlaybackEntryByKey.get(
      String(transcriptPreviewRange.displayKey || ""),
    );
    if (
      previewEntry &&
      sourceTime >= previewEntry.start &&
      sourceTime < previewEntry.end
    ) {
      return previewEntry;
    }
  }

  const previousFloorCursor = transcriptPlaybackCursor;
  const movingForward = sourceTime >= transcriptPlaybackLastTime;
  transcriptPlaybackCursor = playbackCursorFloor(
    transcriptPlaybackEntries,
    transcriptPlaybackCursor,
    transcriptPlaybackLastTime,
    sourceTime,
  );
  transcriptPlaybackLastTime = sourceTime;
  if (movingForward && transcriptPlaybackCursor === previousFloorCursor) {
    const activeEntry = transcriptPlaybackEntries[transcriptPlaybackActiveCursor];
    if (
      activeEntry?.eligible &&
      sourceTime >= activeEntry.start &&
      sourceTime < activeEntry.end
    ) {
      return activeEntry;
    }
    if (transcriptPlaybackActiveCursor < 0) return null;
  }
  let selectedEntry = null;
  let selectedIndex = -1;
  for (let index = transcriptPlaybackCursor; index >= 0; index -= 1) {
    const entry = transcriptPlaybackEntries[index];
    if (
      entry.eligible &&
      sourceTime >= entry.start &&
      sourceTime < entry.end &&
      (!selectedEntry || entry.priority > selectedEntry.priority)
    ) {
      selectedEntry = entry;
      selectedIndex = index;
    }
    if (
      index === 0 ||
      transcriptPlaybackEntries[index - 1].maximumEnd <= sourceTime
    ) {
      break;
    }
  }
  transcriptPlaybackActiveCursor = selectedIndex;
  return selectedEntry;
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

function updateCutSegmentTimestamps() {
  const spans = getEditedTimelineSpans();
  transcriptDisplayItems()
    .filter((item) =>
      item.matches(".segment-item[data-display-start][data-display-end]"),
    )
    .forEach((item) => {
      const segment = {
        start: Number(item.dataset.displayStart),
        end: Number(item.dataset.displayEnd),
      };
      const time = item.querySelector(".segment-time");
      if (!time || !Number.isFinite(segment.start) || !Number.isFinite(segment.end)) {
        return;
      }
      const timing = getLiveEditedSegmentTiming(segment, spans);
      item.classList.toggle("is-removed-from-timeline", !timing);
      if (!timing) {
        time.textContent = formatTime(segment.start);
        time.setAttribute(
          "aria-label",
          `原片从 ${formatPreciseTime(segment.start)} 到 ${formatPreciseTime(segment.end)}，已删除`,
        );
        return;
      }
      time.textContent = formatTime(timing.start);
      time.setAttribute(
        "aria-label",
        `剪辑后从 ${formatPreciseTime(timing.start)} 到 ${formatPreciseTime(timing.end)}`,
      );
    });
  rebuildTranscriptPlaybackEntries();
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
    renderCutSegments();
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

async function saveSegmentText() {
  if (segmentOperationInFlight || activeSegmentEditIndex === null) return;
  const newText = segmentEditText.value;
  const original = currentEditableSegments[activeSegmentEditIndex];
  if (!newText.trim()) {
    segmentEditSelectionStatus.textContent = "修改后的文字不能为空。";
    segmentEditSelectionStatus.dataset.ready = "error";
    return;
  }
  if (original && original.text === newText) {
    closeSegmentEditDialog();
    return;
  }
  const textSaveJobId = currentJobId;
  const textSaveEffect = window.EditorSuite.beginProjectEffect("transcript-save");
  setSegmentOperationBusy(true);
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(textSaveJobId)}/editable-segments`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segmentIndex: activeSegmentEditIndex,
          action: "text",
          text: newText,
        }),
      },
    );
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "文字保存失败，请重试。");
    }
    if (currentJobId !== textSaveJobId) {
      throw new Error("文字已保存，但当前项目已切换，未覆盖新项目状态。");
    }
    currentEditableSegments = result.editableSegments || currentEditableSegments;
    syncCorrectedWords();
    renderCutSegments();
    renderCutTimelineTextSegments();
    updateSelectionSummary();
    const readProject = async () => {
      const jobResponse = await fetch(
        `/api/transcriptions/${encodeURIComponent(textSaveJobId)}`,
      );
      const jobPayload = await jobResponse.json();
      if (!jobResponse.ok) {
        throw new Error(jobPayload.detail || "文字已保存，但同步项目状态失败。");
      }
      return jobPayload;
    };
    const jobPayload = await readProject();
    let applied = window.EditorSuite.applyTranscriptTextEffect(
      textSaveEffect,
      jobPayload,
    );
    if (!applied.accepted) {
      const refreshEffect = window.EditorSuite.beginProjectEffect(
        "transcript-refresh",
      );
      const refreshedJob = await readProject();
      applied = window.EditorSuite.applyTranscriptTextEffect(
        refreshEffect,
        refreshedJob,
      );
    }
    if (!applied.accepted) {
      throw new Error("文字已保存，但当前时间轴已变化，请稍后重试同步。");
    }
    broadcastTranscriptUpdated();
    setSegmentOperationBusy(false);
    closeSegmentEditDialog();
    setSegmentStructureStatus("已保存这段文字，项目预览已同步。", "success");
  } catch (error) {
    setSegmentOperationBusy(false);
    segmentEditSelectionStatus.textContent = error.message;
    segmentEditSelectionStatus.dataset.ready = "error";
  }
}

function broadcastTranscriptUpdated() {
  document.dispatchEvent(
    new CustomEvent("editor-suite:transcript-updated", {
      detail: { jobId: currentJobId },
    }),
  );
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

function setCurrentSuggestions(suggestions, status) {
  currentSuggestions = status === "completed" && Array.isArray(suggestions)
    ? suggestions.filter(
        (suggestion) =>
          suggestion &&
          typeof suggestion.id === "string" &&
          getSuggestionRanges(suggestion).length > 0,
      )
    : [];
}

function seedAutomaticSuggestionRanges() {
  let seededCount = 0;
  for (const suggestion of currentSuggestions) {
    for (const range of getSuggestionRanges(suggestion)) {
      const hasSemanticBounds =
        Number.isFinite(Number(range.originalStart)) &&
        Number.isFinite(Number(range.originalEnd));
      const semanticRange = canonicalizeTextSelectionRange({
        ...range,
        start: hasSemanticBounds ? Number(range.originalStart) : range.start,
        end: hasSemanticBounds ? Number(range.originalEnd) : range.end,
        text: String(suggestion.text || ""),
      });
      const key = rangeKey(semanticRange.start, semanticRange.end);
      if (selectedRanges.has(key)) continue;
      selectedRanges.set(
        key,
        hasSemanticBounds
          ? canonicalizeTextDeleteRange({
              ...semanticRange,
              start: Number(range.start),
              end: Number(range.end),
              originalStart: semanticRange.start,
              originalEnd: semanticRange.end,
            })
          : expandRangeToAdjacentSilence(semanticRange),
      );
      seededCount += 1;
    }
  }
  return seededCount;
}

function seedAutomaticNoSpeechRanges() {
  let seededCount = 0;
  for (const suggestion of currentNoSpeechSuggestions) {
    if (suggestion.deletable === false) continue;
    const range = getNoSpeechRange(suggestion);
    if (!range || selectedNoSpeechRanges.has(range.id)) continue;
    selectedNoSpeechRanges.set(range.id, range);
    seededCount += 1;
  }
  return seededCount;
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

function noSpeechKindLabel(suggestion) {
  if (suggestion.kind === "leading") return "片头空白";
  if (suggestion.kind === "trailing") return "片尾空白";
  if (suggestion.kind === "full") return "整段空白";
  return "中段空白";
}

function noSpeechAudioLabel(suggestion) {
  if (suggestion.audioState === "quiet") return "音频安静";
  if (suggestion.audioState === "ambient") return "检测到背景声";
  return "音频待复核";
}

function setCurrentNoSpeechSuggestions(suggestions, status) {
  currentNoSpeechSuggestions = status === "completed" && Array.isArray(suggestions)
    ? suggestions
        .filter((suggestion) => getNoSpeechRange(suggestion))
        .map((suggestion) => ({
          ...suggestion,
          id: getNoSpeechRange(suggestion).id,
        }))
    : [];
}

function mergeCutRanges(ranges, protectedRanges = []) {
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
    const crossesProtectedRange = Boolean(
      previous &&
        range.start > previous.end &&
        protectedRanges.some(
          (protectedRange) =>
            Number(protectedRange.start) < range.start &&
            Number(protectedRange.end) > previous.end,
        ),
    );
    if (
      previous &&
      range.start <= previous.end + 0.12 &&
      !crossesProtectedRange
    ) {
      previous.end = Math.max(previous.end, range.end);
    } else {
      merged.push({ ...range });
    }
  }
  return merged;
}

function getRecognizedCharacterRanges() {
  return getTranscriptCharacterUnits().map((token) => ({
    start: token.start,
    end: token.end,
    text: String(token.text || ""),
  }));
}

function getRecognizedSpeechRanges() {
  const normalized = [];
  for (const range of getRecognizedCharacterRanges()) {
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

function subtractProtectedRanges(ranges, protectedRanges, minimumDuration = 0) {
  const normalizedProtectedRanges = protectedRanges
    .map(({ start, end }) => ({ start: Number(start), end: Number(end) }))
    .filter(
      ({ start, end }) =>
        Number.isFinite(start) && Number.isFinite(end) && end > start,
    )
    .sort((a, b) => a.start - b.start || a.end - b.end);
  const safeRanges = [];
  for (const range of ranges) {
    let fragments = [{ start: Number(range.start), end: Number(range.end) }];
    for (const protectedRange of normalizedProtectedRanges) {
      if (!fragments.length || protectedRange.start >= fragments.at(-1).end) break;
      const nextFragments = [];
      for (const fragment of fragments) {
        if (
          protectedRange.end <= fragment.start ||
          protectedRange.start >= fragment.end
        ) {
          nextFragments.push(fragment);
          continue;
        }
        if (protectedRange.start > fragment.start) {
          nextFragments.push({
            start: fragment.start,
            end: protectedRange.start,
          });
        }
        if (protectedRange.end < fragment.end) {
          nextFragments.push({
            start: protectedRange.end,
            end: fragment.end,
          });
        }
      }
      fragments = nextFragments;
    }
    safeRanges.push(
      ...fragments.filter(
        ({ start, end }) =>
          end - start >= minimumDuration &&
          end - start > CUT_SPEECH_BOUNDARY_EPSILON,
      ),
    );
  }
  return safeRanges;
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

function canonicalizeTextSelectionRange(range) {
  const total = cutTimelineDuration();
  let start = clamp(Number(range?.start) || 0, 0, total);
  let end = clamp(Number(range?.end) || start, start, total);
  const words = getRecognizedCharacterRanges();
  while (true) {
    const intersectingWords = words.filter(
      (word) => word.start < end && word.end > start,
    );
    if (!intersectingWords.length) break;
    const expandedStart = Math.min(
      start,
      ...intersectingWords.map((word) => word.start),
    );
    const expandedEnd = Math.max(
      end,
      ...intersectingWords.map((word) => word.end),
    );
    if (expandedStart === start && expandedEnd === end) break;
    start = expandedStart;
    end = expandedEnd;
  }
  return { ...range, start, end };
}

function canonicalizeTextDeleteRange(range) {
  const suppliedOriginalStart = Number(range.originalStart);
  const suppliedOriginalEnd = Number(range.originalEnd);
  const semanticRange = canonicalizeTextSelectionRange({
    start: Number(range.originalStart ?? range.start),
    end: Number(range.originalEnd ?? range.end),
  });
  const total = cutTimelineDuration();
  const requestedStart = Number(range.start);
  const requestedEnd = Number(range.end);
  const physicalStart = Number.isFinite(requestedStart)
    ? clamp(requestedStart, 0, total)
    : semanticRange.start;
  const physicalEnd = Number.isFinite(requestedEnd)
    ? clamp(requestedEnd, physicalStart, total)
    : semanticRange.end;
  const hasAlignedPhysicalRange =
    Number.isFinite(suppliedOriginalStart) &&
    Number.isFinite(suppliedOriginalEnd) &&
    (Math.abs(physicalStart - suppliedOriginalStart) >
      CUT_SPEECH_BOUNDARY_EPSILON ||
      Math.abs(physicalEnd - suppliedOriginalEnd) >
        CUT_SPEECH_BOUNDARY_EPSILON);
  return {
    ...range,
    start:
      hasAlignedPhysicalRange && physicalEnd > physicalStart
        ? physicalStart
        : semanticRange.start,
    end:
      hasAlignedPhysicalRange && physicalEnd > physicalStart
        ? physicalEnd
        : semanticRange.end,
    originalStart: semanticRange.start,
    originalEnd: semanticRange.end,
  };
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

function getCommittedTimelineDeleteRanges() {
  return timelineDeleteRanges.filter(
    ({ id }) =>
      !timelineRangeInProgress || id !== selectedTimelineRangeId,
  );
}

function timelineSemanticDeleteRange(range) {
  const start = Number(range?.start);
  const end = Number(range?.end);
  const originalStart = Number(range?.originalStart);
  const originalEnd = Number(range?.originalEnd);
  return {
    start: Number.isFinite(originalStart) ? originalStart : start,
    end: Number.isFinite(originalEnd) ? originalEnd : end,
  };
}

function getCommittedTimelineSemanticDeleteRanges() {
  return getCommittedTimelineDeleteRanges().map(timelineSemanticDeleteRange);
}

function protectRecognizedSpeechFromQuietRanges(quietRanges) {
  return subtractProtectedRanges(
    quietRanges,
    getRecognizedSpeechRanges(),
    CUT_SAFE_NO_SPEECH_MIN_DURATION,
  );
}

function protectRestoredNoSpeechFromTextRanges(textRanges) {
  const restoredNoSpeechRanges = currentNoSpeechSuggestions.flatMap(
    (suggestion) => {
      const range = getNoSpeechRange(suggestion);
      return range && !selectedNoSpeechRanges.has(range.id) ? [range] : [];
    },
  );
  if (restoredNoSpeechRanges.length === 0) return textRanges;

  const safeRanges = [];
  for (const textRange of textRanges) {
    const start = Number(textRange.start);
    const end = Number(textRange.end);
    const originalStart = Number(textRange.originalStart ?? start);
    const originalEnd = Number(textRange.originalEnd ?? end);
    if (
      start > originalStart + CUT_SPEECH_BOUNDARY_EPSILON ||
      end < originalEnd - CUT_SPEECH_BOUNDARY_EPSILON
    ) {
      safeRanges.push({ start, end });
      continue;
    }
    let fragments = [
      { start, end: originalStart },
      { start: originalEnd, end },
    ].filter((range) => range.end - range.start > CUT_SPEECH_BOUNDARY_EPSILON);
    for (const protectedRange of restoredNoSpeechRanges) {
      const nextFragments = [];
      for (const fragment of fragments) {
        if (
          protectedRange.end <= fragment.start ||
          protectedRange.start >= fragment.end
        ) {
          nextFragments.push(fragment);
          continue;
        }
        if (protectedRange.start > fragment.start) {
          nextFragments.push({
            start: fragment.start,
            end: protectedRange.start,
          });
        }
        if (protectedRange.end < fragment.end) {
          nextFragments.push({
            start: protectedRange.end,
            end: fragment.end,
          });
        }
      }
      fragments = nextFragments;
    }
    safeRanges.push(
      ...fragments.filter(
        (range) => range.end - range.start > CUT_SPEECH_BOUNDARY_EPSILON,
      ),
    );
    if (originalEnd - originalStart > CUT_SPEECH_BOUNDARY_EPSILON) {
      safeRanges.push({ start: originalStart, end: originalEnd });
    }
  }
  return safeRanges;
}

function resolveOverlappingRepeatAndQuietRanges(textRanges, quietRanges) {
  return [
    ...protectRestoredNoSpeechFromTextRanges(textRanges),
    ...protectRecognizedSpeechFromQuietRanges(quietRanges),
  ];
}

function getRetainedTranscriptRanges(textRanges, timelineRanges) {
  const explicitTextDeleteRanges = [
    ...textRanges.map(canonicalizeTextDeleteRange).map((range) => ({
      start: range.originalStart,
      end: range.originalEnd,
    })),
    ...timelineRanges.map(timelineSemanticDeleteRange),
  ];
  return subtractProtectedRanges(
    getRecognizedCharacterRanges(),
    explicitTextDeleteRanges,
  );
}

function getMergedSelection() {
  const textRanges = [...selectedRanges.values()].map(
    canonicalizeTextDeleteRange,
  );
  const timelineRanges = getCommittedTimelineDeleteRanges();
  const retainedTranscriptRanges = getRetainedTranscriptRanges(
    textRanges,
    timelineRanges,
  );
  const retainedMediaRanges = subtractProtectedRanges(
    retainedTranscriptRanges,
    textRanges,
  );
  const resolvedAutomaticRanges = resolveOverlappingRepeatAndQuietRanges(
    textRanges,
    [...selectedNoSpeechRanges.values()],
  );
  const safeAutomaticRanges = subtractProtectedRanges(
    resolvedAutomaticRanges,
    retainedMediaRanges,
  );
  return mergeCutRanges(
    [...safeAutomaticRanges, ...timelineRanges],
    retainedMediaRanges,
  );
}

function invalidateCutTimelineScale() {
  cutTimelinePixelsPerSecondCache = null;
  cutTimelineScaleSignature = "";
  cutTimelineTrackWidthCache = 0;
}

function invalidateCutPlaybackStructure() {
  editedTimelineSpansCache = null;
  invalidateCutTimelineScale();
  cutTimelineTextPlaybackEntries = [];
  cutTimelineTextPlaybackFloorCursor = -1;
  cutTimelineTextPlaybackCursor = -1;
  cutTimelineTextPlaybackLastTime = Number.NEGATIVE_INFINITY;
  transcriptPlaybackCursor = -1;
  transcriptPlaybackLastTime = Number.NEGATIVE_INFINITY;
}

function buildEditedTimelineSpans() {
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

function getEditedTimelineSpans() {
  if (editedTimelineSpansCache === null) {
    editedTimelineSpansCache = buildEditedTimelineSpans();
  }
  return editedTimelineSpansCache;
}

function editedCutTimelineDuration(spans = getEditedTimelineSpans()) {
  return spans.at(-1)?.editedEnd || 0;
}

function sourceTimeToEditedTime(seconds, spans = getEditedTimelineSpans()) {
  const sourceTime = clamp(Number(seconds) || 0, 0, cutTimelineDuration());
  let low = 0;
  let high = spans.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (spans[middle].sourceEnd < sourceTime) low = middle + 1;
    else high = middle;
  }
  const span = spans[low];
  if (span) {
    if (sourceTime < span.sourceStart) return span.editedStart;
    return span.editedStart + sourceTime - span.sourceStart;
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

function getEditedAudioQuietRanges(spans = getEditedTimelineSpans()) {
  const mapped = [];
  for (const quietRange of currentAudioQuietRanges) {
    const quietStart = Number(quietRange?.start);
    const quietEnd = Number(quietRange?.end);
    if (!Number.isFinite(quietStart) || !Number.isFinite(quietEnd)) continue;
    for (const span of spans) {
      const sourceStart = Math.max(quietStart, span.sourceStart);
      const sourceEnd = Math.min(quietEnd, span.sourceEnd);
      if (sourceEnd <= sourceStart) continue;
      const start = span.editedStart + sourceStart - span.sourceStart;
      const end = span.editedStart + sourceEnd - span.sourceStart;
      const previous = mapped.at(-1);
      if (previous && start <= previous.end + 0.001) {
        previous.end = Math.max(previous.end, end);
      } else {
        mapped.push({ start, end });
      }
    }
  }
  return mapped;
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
  semanticDeleteRanges = [
    ...[...selectedRanges.values()].map(canonicalizeTextDeleteRange).map(
      (range) => ({
        start: range.originalStart,
        end: range.originalEnd,
      }),
    ),
    ...getCommittedTimelineSemanticDeleteRanges(),
  ],
) {
  const segmentStart = Number(segment.start) || 0;
  const segmentEnd = Number(segment.end) || segmentStart;
  const displayEnd = Math.max(segmentEnd, Number(coverageEnd) || segmentEnd);
  const tokens = getSegmentTokens(segment);
  const parts = [];
  for (const span of spans) {
    const sourceStart = Math.max(segmentStart, span.sourceStart);
    const sourceEnd = Math.min(displayEnd, span.sourceEnd);
    if (sourceEnd <= sourceStart) continue;
    const retainedWords = [];
    for (const token of tokens) {
      const start = Number(token.start) || 0;
      const end = Number(token.end) || start;
      const midpoint = start + (end - start) / 2;
      const semanticallyDeleted = semanticDeleteRanges.some(
        (range) =>
          midpoint >= Number(range.start) && midpoint < Number(range.end),
      );
      if (
        semanticallyDeleted ||
        end <= sourceStart + CUT_SPEECH_BOUNDARY_EPSILON ||
        start >= sourceEnd - CUT_SPEECH_BOUNDARY_EPSILON
      ) {
        continue;
      }
      const wordStart = Math.max(start, sourceStart);
      const wordEnd = Math.min(end, sourceEnd);
      const parentStart = Number(token.parentWordStart);
      const parentEnd = Number(token.parentWordEnd);
      const previous = retainedWords.at(-1);
      if (
        previous &&
        Number.isFinite(parentStart) &&
        Number.isFinite(parentEnd) &&
        previous.parentWordStart === parentStart &&
        previous.parentWordEnd === parentEnd &&
        wordStart <= previous.end + CUT_SPEECH_BOUNDARY_EPSILON
      ) {
        previous.text += String(token.text || "");
        previous.end = wordEnd;
      } else {
        retainedWords.push({
          text: String(token.text || ""),
          start: wordStart,
          end: wordEnd,
          parentWordStart: Number.isFinite(parentStart) ? parentStart : start,
          parentWordEnd: Number.isFinite(parentEnd) ? parentEnd : end,
        });
      }
    }
    const text = retainedWords.length
      ? retainedWords.map((word) => String(word.text || "")).join("")
      : tokens.length === 0 &&
          sourceStart <= segmentStart + 0.001 &&
          sourceEnd >= segmentEnd - 0.001
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

function updateActiveTranscriptSegment(
  currentTime = cutPreviewVideo.currentTime || 0,
  { follow = false } = {},
) {
  if (!follow) transcriptFollowScrollController.reset();
  const nextEntry = transcriptPlaybackEntryAtTime(currentTime);
  const nextItem = nextEntry?.item || null;
  const nextIndex = nextEntry?.segmentIndex ?? -1;
  const nextKey = nextEntry?.key || "";
  if (
    nextIndex === activeTranscriptSegmentIndex &&
    nextKey === activeTranscriptSegmentKey &&
    activeTranscriptItem === nextItem
  ) {
    if (follow && nextItem) {
      transcriptFollowScrollController.follow(nextItem, nextKey);
    }
    return;
  }

  if (activeTranscriptItem) {
    activeTranscriptItem.classList.remove("is-playback-active");
    activeTranscriptItem.removeAttribute("aria-current");
    const badge = activeTranscriptItem.querySelector(".segment-current-badge");
    if (badge) badge.hidden = true;
  }

  activeTranscriptSegmentIndex = nextIndex;
  activeTranscriptSegmentKey = nextKey;
  activeTranscriptItem = nextItem;
  if (!nextItem) {
    transcriptFollowScrollController.reset();
    return;
  }
  nextItem.classList.add("is-playback-active");
  nextItem.setAttribute("aria-current", "true");
  const badge = nextItem.querySelector(".segment-current-badge");
  if (badge) badge.hidden = false;
  if (follow) {
    transcriptFollowScrollController.follow(nextItem, nextKey);
  }
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
  return cutSelectionSignature() !== generatedCutSelectionSignature;
}

function buildLiveCutDraftState() {
  const spans = getEditedTimelineSpans();
  const semanticDeleteRanges = [
    ...[...selectedRanges.values()].map(canonicalizeTextDeleteRange).map(
      (range) => ({
        start: range.originalStart,
        end: range.originalEnd,
      }),
    ),
    ...getCommittedTimelineSemanticDeleteRanges(),
  ];
  const segments = currentEditableSegments.flatMap((segment, segmentIndex) =>
    getRetainedSegmentParts(
      segment,
      spans,
      getEditableSegmentCoverageEnd(segmentIndex),
      semanticDeleteRanges,
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
    cutDraftRevision,
    ranges: getMergedSelection().map(({ start, end }) => ({ start, end })),
    sourceDuration: cutTimelineDuration(),
    duration: editedCutTimelineDuration(spans),
    transcript: {
      text: segments.map((segment) => segment.text).join("\n"),
      segments,
      audioQuietRanges: getEditedAudioQuietRanges(spans),
    },
  };
}

function syncEditorSuiteCutDraftState(state = buildLiveCutDraftState()) {
  if (suppressEditorSuiteCutSync) return;
  window.EditorSuite?.setCutDraft({
    ...state,
    timeline: syncCutTimelineModel(),
  });
}

function acceptEditorSuiteJobState(event) {
  const job = event.detail;
  const edit = job?.edit;
  if (
    !job?.id ||
    job.id !== currentJobId ||
    edit?.status !== "completed" ||
    !edit.composition
  ) {
    return;
  }
  generatedCutSelectionSignature = cutSelectionSignature(
    edit.requestedRanges || edit.ranges || [],
  );
  pendingCutSelectionSignature = "";
  updateCutSegmentTimestamps();
  syncEditorSuiteCutDraftState({
    active: false,
    ranges: edit.ranges || edit.requestedRanges || [],
    sourceDuration: cutTimelineDuration(),
    duration: Number(edit.outputDuration) || 0,
    transcript: edit.transcript || null,
  });
}

function updateTimelineRangeConfirmation() {
  const hasPendingRange = Boolean(
    timelineRangeInProgress &&
    selectedTimelineRangeId !== null &&
    timelineDeleteRanges.some(({ id }) => id === selectedTimelineRangeId),
  );
  generateCutButton.disabled =
    cutControlsLocked || hasPendingRange || getMergedSelection().length === 0;
}

function setCutControlsDisabled(disabled) {
  cutControlsLocked = disabled;
  transcriptDisplayItems().forEach((item) => {
    item.querySelectorAll(".segment-toggle").forEach((button) => {
      if (button instanceof HTMLButtonElement) {
        button.disabled =
          disabled || button.dataset.selectionDisabled === "true";
      }
    });
    item.querySelectorAll(".segment-text-run").forEach((button) => {
      if (button instanceof HTMLButtonElement) button.disabled = disabled;
    });
  });
  cutFrameTimeline?.classList.toggle("is-locked", disabled);
  clearSelectionButton.disabled = disabled || !hasCutSelection();
  generateCutButton.disabled = disabled || getMergedSelection().length === 0;
  updateTimelineRangeConfirmation();
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

function serializableTimelineCutDraftRange(range, fallbackKey = "") {
  const normalized = serializableCutDraftRange(range);
  if (!normalized) return null;
  const semantic = timelineSemanticDeleteRange(range);
  if (
    !Number.isFinite(semantic.start) ||
    !Number.isFinite(semantic.end) ||
    semantic.end <= semantic.start
  ) {
    return null;
  }
  const defaultKey = `timeline-${rangeKey(semantic.start, semantic.end)}`;
  return {
    key: String(range?.key || fallbackKey || range?.id || defaultKey),
    ...normalized,
    originalStart: semantic.start,
    originalEnd: semantic.end,
  };
}

function normalizeRestoredTextDeleteRange(item) {
  const normalized = serializableCutDraftRange(item);
  if (!normalized) return null;
  const restored = canonicalizeTextDeleteRange({
    ...normalized,
    text: String(item?.text || ""),
    originalStart: Number.isFinite(Number(item?.originalStart))
      ? Number(item.originalStart)
      : normalized.start,
    originalEnd: Number.isFinite(Number(item?.originalEnd))
      ? Number(item.originalEnd)
      : normalized.end,
  });
  return {
    ...restored,
    adjacentSilenceBefore: Math.max(
      0,
      restored.originalStart - restored.start,
    ),
    adjacentSilenceAfter: Math.max(
      0,
      restored.end - restored.originalEnd,
    ),
  };
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
    const normalized = serializableTimelineCutDraftRange(range);
    return normalized ? [normalized] : [];
  });
  return {
    revision: cutDraftRevision,
    automaticNoSpeechInitialized,
    textRanges,
    noSpeechRanges,
    timelineRanges,
  };
}

function cutDraftSelectionSignature(payload) {
  return JSON.stringify({
    automaticNoSpeechInitialized:
      payload.automaticNoSpeechInitialized === true,
    textRanges: payload.textRanges,
    noSpeechRanges: payload.noSpeechRanges,
    timelineRanges: payload.timelineRanges,
  });
}

function restorePersistedCutDraft(draft) {
  cutDraftRevision = Math.max(0, Number(draft?.revision) || 0);
  automaticNoSpeechInitialized =
    draft?.automaticNoSpeechInitialized === true;
  for (const item of Array.isArray(draft?.textRanges) ? draft.textRanges : []) {
    const restoredRange = normalizeRestoredTextDeleteRange(item);
    if (!restoredRange) continue;
    const key = rangeKey(
      restoredRange.originalStart,
      restoredRange.originalEnd,
    );
    selectedRanges.set(key, restoredRange);
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
    const id = nextTimelineRangeId++;
    const normalized = serializableTimelineCutDraftRange(
      item,
      `timeline-${id}`,
    );
    if (!normalized) return [];
    return [{ id, ...normalized }];
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

function reconcileCurrentCutHistorySnapshot() {
  const aligned = cloneCutHistorySnapshot();
  cutHistoryLastState = aligned;
  if (!cutHistoryBaseline || cutHistoryIndex === 0) {
    cutHistoryBaseline = aligned;
  } else if (cutHistoryEntries[cutHistoryIndex - 1]) {
    cutHistoryEntries[cutHistoryIndex - 1].after = aligned;
  }
  if (cutHistoryEntries[cutHistoryIndex]) {
    cutHistoryEntries[cutHistoryIndex].before = aligned;
  }
  saveLocalCutHistory();
}

function applyPersistedCutDraftAlignment(draft, expectedSignature) {
  if (
    !draft ||
    cutDraftSelectionSignature(buildPersistedCutDraftPayload()) !==
      expectedSignature
  ) {
    return false;
  }

  const serverTextRanges = new Map(
    (Array.isArray(draft.textRanges) ? draft.textRanges : []).flatMap((item) => {
      const key = String(item?.key || "");
      const normalized = serializableCutDraftRange(item);
      return key && normalized ? [[key, { item, normalized }]] : [];
    }),
  );
  if (
    serverTextRanges.size !== selectedRanges.size ||
    [...selectedRanges.keys()].some((key) => !serverTextRanges.has(key))
  ) {
    return false;
  }

  const currentTimelineRanges = getCommittedTimelineDeleteRanges();
  const serverTimelineRanges = new Map(
    (Array.isArray(draft.timelineRanges) ? draft.timelineRanges : []).flatMap(
      (item) => {
        const key = String(item?.key || "");
        const normalized = serializableTimelineCutDraftRange(item);
        return key && normalized ? [[key, normalized]] : [];
      },
    ),
  );
  if (
    serverTimelineRanges.size !== currentTimelineRanges.length ||
    currentTimelineRanges.some(
      (range) => !serverTimelineRanges.has(String(range.key || "")),
    )
  ) {
    return false;
  }

  const alignedTextRanges = new Map();
  for (const [key, currentRange] of selectedRanges.entries()) {
    const { item, normalized } = serverTextRanges.get(key);
    const aligned = {
      ...currentRange,
      ...normalized,
      text: String(item.text ?? currentRange.text ?? ""),
      originalStart: Number.isFinite(Number(item.originalStart))
        ? Number(item.originalStart)
        : Number(currentRange.originalStart ?? normalized.start),
      originalEnd: Number.isFinite(Number(item.originalEnd))
        ? Number(item.originalEnd)
        : Number(currentRange.originalEnd ?? normalized.end),
      adjacentSilenceBefore: Math.max(
        0,
        Number(item.adjacentSilenceBefore) || 0,
      ),
      adjacentSilenceAfter: Math.max(
        0,
        Number(item.adjacentSilenceAfter) || 0,
      ),
    };
    alignedTextRanges.set(key, aligned);
  }

  const alignedTimelineRanges = currentTimelineRanges.map((currentRange) => ({
    ...currentRange,
    ...serverTimelineRanges.get(String(currentRange.key)),
  }));
  const rangeChanged = (left, right, fields) =>
    fields.some((field) => left?.[field] !== right?.[field]);
  const changed =
    [...selectedRanges.entries()].some(([key, currentRange]) =>
      rangeChanged(currentRange, alignedTextRanges.get(key), [
        "start",
        "end",
        "originalStart",
        "originalEnd",
        "adjacentSilenceBefore",
        "adjacentSilenceAfter",
        "text",
      ]),
    ) ||
    currentTimelineRanges.some((currentRange, index) =>
      rangeChanged(currentRange, alignedTimelineRanges[index], [
        "start",
        "end",
        "originalStart",
        "originalEnd",
      ]),
    );

  selectedRanges.clear();
  for (const [key, range] of alignedTextRanges) {
    selectedRanges.set(key, range);
  }
  timelineDeleteRanges = alignedTimelineRanges;

  cutDraftLastSignature = cutDraftSelectionSignature(
    buildPersistedCutDraftPayload(),
  );
  if (changed) {
    cutHistoryReplaying = true;
    try {
      updateSelectionSummary();
    } finally {
      cutHistoryReplaying = false;
    }
    reconcileCurrentCutHistorySnapshot();
  }
  return true;
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
    const alignmentApplied = applyPersistedCutDraftAlignment(
      result.cutDraft,
      signature,
    );
    if (!alignmentApplied) {
      cutDraftLastSignature = cutDraftSelectionSignature(
        result.cutDraft || payload,
      );
      cutDraftNeedsServerSync = true;
      saveLocalCutDraft(
        {
          schemaVersion: 1,
          ...buildPersistedCutDraftPayload(),
          updatedAt: new Date().toISOString(),
        },
        jobId,
      );
      return;
    }
    cutDraftNeedsServerSync = false;
    saveLocalCutDraft(result.cutDraft, jobId);
    syncEditorSuiteCutDraftState();
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

async function flushCutDraftSave() {
  if (!cutDraftReady || !currentJobId) {
    throw new Error("剪辑草稿尚未准备完成。请稍后重试。");
  }
  const jobId = currentJobId;
  while (currentJobId === jobId) {
    const requestedSignature = cutDraftSelectionSignature(
      buildPersistedCutDraftPayload(),
    );
    scheduleCutDraftSave();
    const pendingQueue = cutDraftSaveQueue;
    await pendingQueue;
    if (currentJobId !== jobId) {
      throw new Error("当前视频任务已变化，请重新确认剪辑范围。");
    }
    if (pendingQueue !== cutDraftSaveQueue) continue;
    const currentSignature = cutDraftSelectionSignature(
      buildPersistedCutDraftPayload(),
    );
    if (currentSignature !== requestedSignature) continue;
    if (
      currentSignature !== cutDraftLastSignature ||
      cutDraftNeedsServerSync ||
      cutDraftRevision <= 0
    ) {
      throw new Error("剪辑草稿尚未同步到服务器。请稍后重试。");
    }
    return cutDraftRevision;
  }
  throw new Error("当前视频任务已变化，请重新确认剪辑范围。");
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

function cutHistoryStorageKey(jobId = currentJobId) {
  return jobId ? `video-editor:cut-history:${jobId}` : "";
}

function cloneCutHistorySnapshot(source = buildPersistedCutDraftPayload()) {
  const textRanges = (Array.isArray(source?.textRanges) ? source.textRanges : [])
    .flatMap((item) => {
      const normalized = serializableCutDraftRange(item);
      if (!normalized) return [];
      const key = String(item?.key || rangeKey(normalized.start, normalized.end));
      const range = {
        key,
        ...normalized,
        text: String(item?.text || ""),
        adjacentSilenceBefore: Math.max(
          0,
          Number(item?.adjacentSilenceBefore) || 0,
        ),
        adjacentSilenceAfter: Math.max(
          0,
          Number(item?.adjacentSilenceAfter) || 0,
        ),
      };
      for (const field of ["originalStart", "originalEnd"]) {
        const value = Number(item?.[field]);
        if (Number.isFinite(value) && value >= 0) range[field] = value;
      }
      return [range];
    });
  const noSpeechRanges = (
    Array.isArray(source?.noSpeechRanges) ? source.noSpeechRanges : []
  ).flatMap((item) => {
    const normalized = serializableCutDraftRange(item);
    if (!normalized) return [];
    return [
      {
        key: String(item?.key || rangeKey(normalized.start, normalized.end)),
        ...normalized,
      },
    ];
  });
  const timelineRanges = (
    Array.isArray(source?.timelineRanges) ? source.timelineRanges : []
  ).flatMap((item, index) => {
    const normalized = serializableTimelineCutDraftRange(
      item,
      `timeline-history-${index + 1}`,
    );
    return normalized ? [normalized] : [];
  });
  return { textRanges, noSpeechRanges, timelineRanges };
}

function cutHistorySnapshotSignature(snapshot) {
  return cutDraftSelectionSignature(cloneCutHistorySnapshot(snapshot));
}

function saveLocalCutHistory(jobId = currentJobId) {
  const key = cutHistoryStorageKey(jobId);
  if (!key || !cutHistoryBaseline) return;
  try {
    window.localStorage.setItem(
      key,
      JSON.stringify({
        schemaVersion: 1,
        baseline: cutHistoryBaseline,
        entries: cutHistoryEntries,
        index: cutHistoryIndex,
        updatedAt: new Date().toISOString(),
      }),
    );
  } catch {
    // The editing draft still works when browser history storage is restricted.
  }
}

function removeLocalCutHistory(jobId = currentJobId) {
  const key = cutHistoryStorageKey(jobId);
  if (!key) return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Nothing else is required when browser storage is restricted.
  }
}

function loadLocalCutHistory(jobId = currentJobId) {
  const key = cutHistoryStorageKey(jobId);
  if (!key) return null;
  try {
    const stored = JSON.parse(window.localStorage.getItem(key) || "null");
    if (!stored || stored.schemaVersion !== 1) return null;
    const baseline = cloneCutHistorySnapshot(stored.baseline);
    const entries = (Array.isArray(stored.entries) ? stored.entries : [])
      .slice(0, CUT_HISTORY_LIMIT)
      .flatMap((entry, index) => {
        if (!entry || typeof entry !== "object") return [];
        return [
          {
            id: String(entry.id || `restored-${index}`),
            label: String(entry.label || "更新剪辑方案"),
            at: String(entry.at || new Date().toISOString()),
            coalesceKey: String(entry.coalesceKey || ""),
            before: cloneCutHistorySnapshot(entry.before),
            after: cloneCutHistorySnapshot(entry.after),
          },
        ];
      });
    const index = clamp(Number(stored.index) || 0, 0, entries.length);
    return { baseline, entries, index };
  } catch {
    return null;
  }
}

function canUndoCutHistory() {
  return Boolean(
    currentJobId &&
      cutHistoryIndex > 0 &&
      !cutControlsLocked &&
      !timelineRangeInProgress &&
      !timelineRangeConfirmationOpen,
  );
}

function canRedoCutHistory() {
  return Boolean(
    currentJobId &&
      cutHistoryIndex < cutHistoryEntries.length &&
      !cutControlsLocked &&
      !timelineRangeInProgress &&
      !timelineRangeConfirmationOpen,
  );
}

function resetCutHistoryRuntime() {
  cutHistoryBaseline = null;
  cutHistoryEntries = [];
  cutHistoryIndex = 0;
  cutHistoryLastState = null;
  cutHistoryPendingMeta = null;
  cutHistoryReplaying = false;
}

function restoreLocalCutHistory() {
  const current = cloneCutHistorySnapshot();
  const stored = loadLocalCutHistory();
  const storedExpected = stored
    ? stored.index > 0
      ? stored.entries[stored.index - 1]?.after
      : stored.baseline
    : null;
  if (
    stored &&
    storedExpected &&
    cutHistorySnapshotSignature(storedExpected) ===
      cutHistorySnapshotSignature(current)
  ) {
    cutHistoryBaseline = stored.baseline;
    cutHistoryEntries = stored.entries;
    cutHistoryIndex = stored.index;
  } else {
    cutHistoryBaseline = current;
    cutHistoryEntries = [];
    cutHistoryIndex = 0;
    saveLocalCutHistory();
  }
  cutHistoryLastState = current;
  cutHistoryPendingMeta = null;
}

function stageCutHistoryOperation(label, { coalesceKey = "" } = {}) {
  cutHistoryPendingMeta = {
    label: String(label || "更新剪辑方案"),
    coalesceKey: String(coalesceKey || ""),
  };
}

function recordCutHistoryIfChanged() {
  const current = cloneCutHistorySnapshot();
  const previous = cutHistoryLastState || current;
  const meta = cutHistoryPendingMeta;
  cutHistoryPendingMeta = null;
  if (!cutHistoryBaseline) cutHistoryBaseline = previous;

  if (
    cutHistoryReplaying ||
    !cutDraftReady ||
    cutHistorySnapshotSignature(previous) === cutHistorySnapshotSignature(current)
  ) {
    cutHistoryLastState = current;
    return;
  }

  if (cutHistoryIndex < cutHistoryEntries.length) {
    cutHistoryEntries = cutHistoryEntries.slice(0, cutHistoryIndex);
  }
  const now = new Date();
  const lastEntry = cutHistoryEntries[cutHistoryEntries.length - 1];
  const coalesce = Boolean(
    meta?.coalesceKey &&
      lastEntry?.coalesceKey === meta.coalesceKey &&
      now.getTime() - new Date(lastEntry.at).getTime() <= CUT_HISTORY_COALESCE_MS,
  );
  if (coalesce) {
    lastEntry.after = current;
    lastEntry.at = now.toISOString();
    lastEntry.label = meta.label;
  } else {
    cutHistoryEntries.push({
      id: `${now.getTime()}-${Math.random().toString(36).slice(2, 8)}`,
      label: meta?.label || "更新剪辑方案",
      at: now.toISOString(),
      coalesceKey: meta?.coalesceKey || "",
      before: previous,
      after: current,
    });
  }
  while (cutHistoryEntries.length > CUT_HISTORY_LIMIT) {
    const removed = cutHistoryEntries.shift();
    cutHistoryBaseline = removed.after;
  }
  cutHistoryIndex = cutHistoryEntries.length;
  cutHistoryLastState = current;
  saveLocalCutHistory();
}

function applyCutHistorySnapshot(snapshot) {
  const normalized = cloneCutHistorySnapshot(snapshot);
  selectedRanges.clear();
  selectedNoSpeechRanges.clear();
  for (const item of normalized.textRanges) {
    const restoredRange = normalizeRestoredTextDeleteRange(item);
    if (!restoredRange) continue;
    const key = rangeKey(
      restoredRange.originalStart,
      restoredRange.originalEnd,
    );
    selectedRanges.set(key, restoredRange);
  }
  for (const item of normalized.noSpeechRanges) {
    selectedNoSpeechRanges.set(item.key, {
      id: item.key,
      start: item.start,
      end: item.end,
    });
  }
  timelineDeleteRanges = normalized.timelineRanges.map((range) => ({
    id: nextTimelineRangeId++,
    ...range,
  }));
  selectedTimelineRangeId = null;
  timelineRangeInProgress = false;
  timelineRangeConfirmationOpen = false;
  cutHistoryLastState = cloneCutHistorySnapshot();
  cutHistoryReplaying = true;
  try {
    updateCutTimelineStatus("");
    updateSelectionSummary();
  } finally {
    cutHistoryReplaying = false;
  }
}

function undoCutHistory() {
  if (!canUndoCutHistory()) return;
  const entry = cutHistoryEntries[cutHistoryIndex - 1];
  cutHistoryIndex -= 1;
  applyCutHistorySnapshot(entry.before);
  saveLocalCutHistory();
}

function redoCutHistory() {
  if (!canRedoCutHistory()) return;
  const entry = cutHistoryEntries[cutHistoryIndex];
  cutHistoryIndex += 1;
  applyCutHistorySnapshot(entry.after);
  saveLocalCutHistory();
}

function isNativeUndoTarget(target) {
  if (!(target instanceof Element)) return false;
  return Boolean(
    target.closest("input, textarea, select, [contenteditable='true']"),
  );
}

function handleGlobalCutHistoryShortcut(event) {
  if (
    event.defaultPrevented ||
    (!event.ctrlKey && !event.metaKey) ||
    event.altKey ||
    isNativeUndoTarget(event.target)
  ) {
    return;
  }
  const key = event.key.toLowerCase();
  const wantsUndo = key === "z" && !event.shiftKey;
  const wantsRedo = key === "y" || (key === "z" && event.shiftKey);
  if (wantsUndo && canUndoCutHistory()) {
    event.preventDefault();
    undoCutHistory();
  } else if (wantsRedo && canRedoCutHistory()) {
    event.preventDefault();
    redoCutHistory();
  }
}

function updateSelectionSummary() {
  invalidateCutPlaybackStructure();
  recordCutHistoryIfChanged();
  const merged = getMergedSelection();
  const deletedDuration = merged.reduce(
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
      "请先在文字剪辑或时间轴中删除内容";
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
    cutControlsLocked || merged.length === 0;
  updateTimelineRangeConfirmation();
  updateOriginalSourceActionsVisibility();
  document.body.classList.toggle(
    "has-cut-selection",
    hasCutSelection(),
  );
  updateCutSegmentText();
  syncEditorSuiteCutDraftState();
  refreshCutTimeline();
  scheduleCutDraftSave();
}

function cutTimelineDuration() {
  if (currentVideoDuration > 0) return currentVideoDuration;
  return Number.isFinite(cutPreviewVideo.duration)
    ? Math.max(0, cutPreviewVideo.duration)
    : 0;
}

function cutTimelinePixelsPerSecond() {
  if (cutTimelinePixelsPerSecondCache !== null) {
    return cutTimelinePixelsPerSecondCache;
  }
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
  cutTimelinePixelsPerSecondCache = Math.ceil(pixelsPerSecond);
  return cutTimelinePixelsPerSecondCache;
}

function updateCutTimelineScale() {
  const total = editedCutTimelineDuration();
  const viewportWidth = cutFrameTimelineScroll.clientWidth;
  const pixelsPerSecond = cutTimelinePixelsPerSecond();
  const signature = `${total.toFixed(3)}|${viewportWidth}|${pixelsPerSecond}`;
  if (signature === cutTimelineScaleSignature) return;
  cutTimelineScaleSignature = signature;
  if (total <= 0 || viewportWidth <= 0) {
    cutFrameTimelineTrack.style.removeProperty("width");
    cutTimelineTrackWidthCache = 0;
    return;
  }
  const width = Math.max(
    viewportWidth,
    Math.round(total * pixelsPerSecond),
  );
  cutFrameTimelineTrack.style.width = `${width}px`;
  cutTimelineTrackWidthCache = width;
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
  if (cutVideoStage.classList.contains("is-douyin-preview")) return;
  const ratio = cutPreviewVideo.videoWidth / cutPreviewVideo.videoHeight;
  cutVideoStage.style.aspectRatio = `${cutPreviewVideo.videoWidth} / ${cutPreviewVideo.videoHeight}`;
  cutVideoStage.style.width =
    ratio < 1
      ? `min(100%, ${Math.round(Math.min(600, window.innerHeight * 0.68) * ratio)}px)`
      : "min(100%, 860px)";
}

function updateCutTimelineTextStates(currentTime = cutPreviewVideo.currentTime || 0) {
  const sourceTime = Number(currentTime) || 0;
  const previousFloorCursor = cutTimelineTextPlaybackFloorCursor;
  const movingForward = sourceTime >= cutTimelineTextPlaybackLastTime;
  const floorIndex = playbackCursorFloor(
    cutTimelineTextPlaybackEntries,
    cutTimelineTextPlaybackFloorCursor,
    cutTimelineTextPlaybackLastTime,
    sourceTime,
  );
  cutTimelineTextPlaybackFloorCursor = floorIndex;
  cutTimelineTextPlaybackLastTime = sourceTime;
  if (movingForward && floorIndex === previousFloorCursor) {
    const activeEntry = cutTimelineTextPlaybackEntries[cutTimelineTextPlaybackCursor];
    if (
      activeEntry &&
      sourceTime >= activeEntry.start &&
      sourceTime < activeEntry.end
    ) {
      return;
    }
    if (cutTimelineTextPlaybackCursor < 0) return;
  }
  let nextIndex = -1;
  for (let index = floorIndex; index >= 0; index -= 1) {
    const entry = cutTimelineTextPlaybackEntries[index];
    if (sourceTime >= entry.start && sourceTime < entry.end) {
      nextIndex = index;
      break;
    }
    if (
      index === 0 ||
      cutTimelineTextPlaybackEntries[index - 1].maximumEnd <= sourceTime
    ) {
      break;
    }
  }
  if (nextIndex === cutTimelineTextPlaybackCursor) return;
  cutTimelineTextPlaybackEntries[
    cutTimelineTextPlaybackCursor
  ]?.element.classList.remove("is-active");
  cutTimelineTextPlaybackEntries[nextIndex]?.element.classList.add("is-active");
  cutTimelineTextPlaybackCursor = nextIndex;
}

function getCutPlaybackFrameState(currentTime = cutPreviewVideo.currentTime || 0) {
  const spans = editedTimelineSpansCache || [];
  const total = editedCutTimelineDuration(spans);
  const sourceCurrent = clamp(
    Number(currentTime) || 0,
    0,
    cutTimelineDuration() || 0,
  );
  const current = sourceTimeToEditedTime(sourceCurrent, spans);
  const progress = total > 0 ? current / total : 0;
  return { current, progress, sourceCurrent, total };
}

function updateCutPlaybackVisualFrame(
  currentTime = cutPreviewVideo.currentTime || 0,
  { followTranscript = true } = {},
) {
  const frame = getCutPlaybackFrameState(currentTime);
  const { progress, sourceCurrent } = frame;
  const trackWidth = cutTimelineTrackWidthCache;
  cutFrameTimelinePlayhead.style.transform =
    `translate3d(${progress * trackWidth - 1}px, 0, 0)`;
  updateCutTimelineTextStates(sourceCurrent);
  updateActiveTranscriptSegment(sourceCurrent, { follow: followTranscript });
  return frame;
}

function updateCutTimelinePlayhead(
  { followTranscript = false, renderVisual = true } = {},
) {
  const frame = renderVisual
    ? updateCutPlaybackVisualFrame(
        cutPreviewVideo.currentTime || 0,
        { followTranscript },
      )
    : getCutPlaybackFrameState(cutPreviewVideo.currentTime || 0);
  const { current, progress, sourceCurrent, total } = frame;
  cutFrameTimeline.hidden = total <= 0;
  cutFrameTimelineSeek.max = String(total);
  cutFrameTimelineSeek.step = String(CUT_TIMELINE_STEP);
  cutFrameTimelineSeek.value = String(current);
  cutFrameTimelineSeek.setAttribute("aria-valuemax", String(total));
  cutFrameTimelineSeek.setAttribute("aria-valuenow", current.toFixed(2));
  cutFrameTimelineSeek.setAttribute(
    "aria-valuetext",
    `${formatTime(current)} / ${formatTime(total)}`,
  );
  cutFrameTimelineTime.value = `${formatTime(current)} / ${formatTime(total)}`;
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

function cutMediaController() {
  return window.EditorSuite?.mediaController?.() || null;
}

function pauseCutPreview() {
  const controller = cutMediaController();
  if (controller) controller.pause();
  else cutPreviewVideo.pause();
}

function playCutPreview() {
  const controller = cutMediaController();
  return controller ? controller.play() : cutPreviewVideo.play();
}

function seekCutPreview(seconds) {
  const total = cutTimelineDuration();
  noSpeechPreviewEnd = null;
  cutSelectionPreviewEnd = null;
  transcriptPreviewRange = null;
  resetCutPlaybackCursors();
  const nextTime = clamp(Number(seconds) || 0, 0, total);
  const controller = cutMediaController();
  if (controller) controller.seekSource(nextTime);
  else cutPreviewVideo.currentTime = nextTime;
  updateCutTimelinePlayhead({ followTranscript: true });
}

function previewSelectedCutRange(range) {
  const total = cutTimelineDuration();
  const start = clamp(Number(range?.start) || 0, 0, total);
  const end = clamp(Number(range?.end) || start, start, total);
  if (total <= 0 || end <= start) return;
  pauseCutPreview();
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
  playCutPreview()?.catch?.(() => {});
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
  playCutPreview()?.catch?.(() => {});
}

function previewTextSegment(item) {
  const total = cutTimelineDuration();
  const start = clamp(Number(item?.dataset.displayStart) || 0, 0, total);
  const end = clamp(Number(item?.dataset.displayEnd) || start, start, total);
  if (total <= 0 || end <= start) return;
  pauseCutPreview();
  seekCutPreview(start);
  transcriptPreviewRange = {
    start,
    end,
    displayKey: String(item.dataset.displayKey || ""),
  };
  updateActiveTranscriptSegment(start, { follow: true });
  updateCutTimelineStatus(
    `正在播放文案 ${formatCutRange(start, end)}。`,
    "neutral",
    "transcript",
  );
  playCutPreview()?.catch?.(() => {});
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

function cutTimelineClipId(rangeId) {
  return `cut:${rangeId}`;
}

function syncCutTimelineModel() {
  const total = Math.max(currentVideoDuration, cutTimelineDuration());
  cutTimelineDocument = window.EditorTimeline.normalizeDocument({
    duration: total,
    tracks: [
      {
        id: "cut:deletions",
        kind: "cut",
        name: "删除区间",
        order: 0,
        clips: timelineDeleteRanges.map((range) => ({
          id: cutTimelineClipId(range.id),
          sourceId: range.id,
          name: "删除区间",
          start: range.start,
          end: range.end,
          minDuration: CUT_TIMELINE_MIN_RANGE,
          editable: true,
          payload: {
            pending:
              timelineRangeInProgress && range.id === selectedTimelineRangeId,
          },
        })),
      },
    ],
    selection:
      selectedTimelineRangeId === null
        ? null
        : { clipId: cutTimelineClipId(selectedTimelineRangeId) },
  });
  return cutTimelineDocument;
}

function applySharedTimelineRange(transaction) {
  const range = timelineDeleteRanges.find(
    (item) => String(item.id) === String(transaction?.sourceId),
  );
  if (!range) return false;
  const start = Math.max(0, Number(transaction.start) || 0);
  const end = Math.max(start, Number(transaction.end) || start);
  if (end <= start) return false;
  const previousReplaying = cutHistoryReplaying;
  suppressEditorSuiteCutSync = true;
  cutHistoryReplaying = true;
  try {
    range.start = start;
    range.end = end;
    range.originalStart = start;
    range.originalEnd = end;
    selectedTimelineRangeId = range.id;
    updateSelectionSummary();
  } finally {
    cutHistoryReplaying = previousReplaying;
    suppressEditorSuiteCutSync = false;
  }
  return {
    cut: buildLiveCutDraftState(),
    timeline: syncCutTimelineModel(),
  };
}

function deleteSharedTimelineRange(sourceId) {
  const previousLength = timelineDeleteRanges.length;
  const previousReplaying = cutHistoryReplaying;
  suppressEditorSuiteCutSync = true;
  cutHistoryReplaying = true;
  try {
    timelineDeleteRanges = timelineDeleteRanges.filter(
      (item) => String(item.id) !== String(sourceId),
    );
    if (timelineDeleteRanges.length === previousLength) return false;
    selectedTimelineRangeId = null;
    timelineRangeInProgress = false;
    updateSelectionSummary();
  } finally {
    cutHistoryReplaying = previousReplaying;
    suppressEditorSuiteCutSync = false;
  }
  syncEditorSuiteCutDraftState();
  return true;
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
  syncCutTimelineModel();

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
    body.title = "拖动调整区间，再次点击确认删除";
    body.setAttribute(
      "aria-label",
      `待确认删除区间 ${formatCutRange(range.start, range.end)}，可拖动调整，再次点击或按 Enter 确认删除`,
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

    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "cut-timeline-range-cancel";
    cancelButton.dataset.timelineRangeAction = "cancel";
    cancelButton.title = "取消选区";
    cancelButton.setAttribute(
      "aria-label",
      `取消待确认删除区间 ${formatCutRange(range.start, range.end)}`,
    );

    const cancelIcon = document.createElement("iconify-icon");
    cancelIcon.setAttribute("icon", "ph:x-bold");
    cancelIcon.setAttribute("aria-hidden", "true");
    cancelButton.append(cancelIcon);

    rangeElement.append(startHandle, body, endHandle, cancelButton);
    cutFrameTimelineRanges.append(rangeElement);
  }
  updateTimelineRangeConfirmation();
  updateCutTimelineTextStates();
}

function renderCutTimelineTextSegments() {
  cutFrameTimelineText.replaceChildren();
  cutTimelineTextPlaybackEntries = [];
  cutTimelineTextPlaybackFloorCursor = -1;
  cutTimelineTextPlaybackCursor = -1;
  cutTimelineTextPlaybackLastTime = Number.NEGATIVE_INFINITY;
  const spans = getEditedTimelineSpans();
  const total = editedCutTimelineDuration(spans);
  if (total <= 0) return;

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
      cutTimelineTextPlaybackEntries.push({
        element: item,
        end: part.sourceEnd,
        start: part.sourceStart,
      });
    }
  });
  cutTimelineTextPlaybackEntries.sort((left, right) =>
    left.start - right.start || left.end - right.end,
  );
  let maximumEnd = Number.NEGATIVE_INFINITY;
  for (const entry of cutTimelineTextPlaybackEntries) {
    maximumEnd = Math.max(maximumEnd, entry.end);
    entry.maximumEnd = maximumEnd;
  }
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
  updateCutTimelineScale();
  renderCutTimelineRuler();
  renderCutTimelineTextSegments();
  renderCutTimelineRanges();
  updateCutTimelinePlayhead();
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
  pauseCutPreview();
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
      const id = nextTimelineRangeId++;
      draftRange = {
        id,
        key: `timeline-${id}`,
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
        ? `将删除 ${formatCutRange(draftRange.start, draftRange.end)}；确认后语音附近会对齐安全剪辑点`
        : "当前拖动范围无效，松开后不会删除。",
      safeRange ? "neutral" : "error",
      "selection",
    );
  };

  const finish = (finishEvent) => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    window.removeEventListener("pointercancel", finish);
    if (finishEvent.type === "pointercancel") {
      if (draftRange) {
        timelineDeleteRanges = timelineDeleteRanges.filter(
          ({ id }) => id !== draftRange.id,
        );
        timelineRangeInProgress = false;
        selectedTimelineRangeId = null;
        renderCutTimelineRanges();
        updateCutTimelineStatus("");
      }
      return;
    }
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
        "未删除：区间过短或无效。",
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
      `已选择 ${formatCutRange(draftRange.start, draftRange.end)}，可拖动微调，再次点击选区确认删除。`,
      "neutral",
      "selection",
    );
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
  const originalRange = { start: range.start, end: range.end };
  const previousSelectedRangeId = selectedTimelineRangeId;
  event.preventDefault();
  event.stopPropagation();
  pauseCutPreview();
  selectedTimelineRangeId = rangeId;
  const mode = control.dataset.dragMode;
  const startClientX = event.clientX;
  let hasDragged = false;
  const total = cutTimelineDuration();
  const transientTimelineStore = window.EditorTimeline.createStore(
    syncCutTimelineModel(),
  );
  transientTimelineStore.selectClip(cutTimelineClipId(range.id), { silent: true });
  const pointerSession = window.EditorTimeline.createPointerSession(
    transientTimelineStore,
    {
      clipId: cutTimelineClipId(range.id),
      mode,
      startClientX,
      trackWidth: cutFrameTimelineTrack.getBoundingClientRect().width,
      duration: total,
      onUpdate: (clip) => {
        range.start = clip.start;
        range.end = clip.end;
      },
    },
  );
  if (!pointerSession) return;
  renderCutTimelineRanges();

  const move = (moveEvent) => {
    if (
      !hasDragged &&
      Math.abs(moveEvent.clientX - startClientX) < CUT_TIMELINE_DRAG_THRESHOLD
    ) {
      return;
    }
    hasDragged = true;
    const clip = pointerSession.update(moveEvent.clientX);
    seekCutPreview(mode === "end" ? clip.end : clip.start);
    renderCutTimelineRanges();
    updateCutTimelineStatus(
      `正在调整删除区间 ${formatCutRange(range.start, range.end)}`,
      "neutral",
      "selection",
    );
  };

  const finish = (finishEvent) => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    window.removeEventListener("pointercancel", finish);
    if (finishEvent.type === "pointercancel") {
      pointerSession.finish({ commit: false });
      Object.assign(range, originalRange);
      selectedTimelineRangeId = previousSelectedRangeId;
      renderCutTimelineRanges();
      updateCutTimelineStatus("");
      return;
    }
    if (!hasDragged) {
      pointerSession.finish({ commit: false });
      if (
        finishEvent.type === "pointerup" &&
        mode === "move" &&
        timelineRangeInProgress
      ) {
        void requestTimelineRangeConfirmation(range);
      }
      return;
    }
    const safeRange = alignManualRangeToTranscript(range);
    if (safeRange) Object.assign(range, safeRange);
    pointerSession.finish({ commit: false });
    syncCutTimelineModel();
    stageCutHistoryOperation("调整时间轴删除区间");
    updateCutTimelineStatus(
      `已调整待确认区间 ${formatCutRange(range.start, range.end)}，再次点击选区确认删除。`,
      "neutral",
      "selection",
    );
    updateSelectionSummary();
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish, { once: true });
  window.addEventListener("pointercancel", finish, { once: true });
}

function cancelPendingTimelineRange(message = "") {
  if (selectedTimelineRangeId === null || cutControlsLocked) return;
  timelineDeleteRanges = timelineDeleteRanges.filter(
    ({ id }) => id !== selectedTimelineRangeId,
  );
  selectedTimelineRangeId = null;
  timelineRangeInProgress = false;
  updateSelectionSummary();
  updateCutTimelineStatus(message);
}

function confirmPendingTimelineRange() {
  if (selectedTimelineRangeId === null || cutControlsLocked) return;
  const range = timelineDeleteRanges.find(
    ({ id }) => id === selectedTimelineRangeId,
  );
  if (!range || !timelineRangeInProgress) return;
  stageCutHistoryOperation("删除时间轴区间");
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
        "语音附近会对齐安全剪辑点；删除后可通过全局撤销恢复，原视频仍会保留。",
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
    updateCutTimelineStatus(
      `已保留待确认区间 ${formatCutRange(range.start, range.end)}，可继续调整或再次点击确认。`,
      "neutral",
      "selection",
    );
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
    if (!timelineRangeInProgress) {
      stageCutHistoryOperation("恢复时间轴区间");
    }
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
  stageCutHistoryOperation("调整时间轴删除区间", {
    coalesceKey: `timeline-adjust:${rangeId}:${mode}`,
  });
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
  const semanticRange = alignManualRangeToTranscript(range);
  if (semanticRange) Object.assign(range, semanticRange);
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
    `已调整待确认区间 ${formatCutRange(range.start, range.end)}，再次点击选区确认删除。`,
    "neutral",
    "selection",
  );
  updateSelectionSummary();
}

function resetCutPlaybackCursors() {
  transcriptPlaybackCursor = -1;
  transcriptPlaybackActiveCursor = -1;
  transcriptPlaybackLastTime = Number.NEGATIVE_INFINITY;
  cutTimelineTextPlaybackFloorCursor = -1;
  cutTimelineTextPlaybackCursor = -1;
  cutTimelineTextPlaybackLastTime = Number.NEGATIVE_INFINITY;
}

function setupCutPreviewControls() {
  let lastAudibleVolume = 1;
  const safeDuration = () => cutTimelineDuration();
  cutPlaybackFrameClock?.destroy();
  const sharedMedia = cutMediaController();
  if (sharedMedia) {
    const unsubscribeFrame = sharedMedia.subscribeFrame(({ sourceTime }) => {
      updateCutPlaybackVisualFrame(sourceTime, { followTranscript: true });
    });
    const unsubscribeState = sharedMedia.subscribeState(({ reason }) => {
      if (["seeking", "seeked", "ended", "emptied"].includes(reason)) {
        resetCutPlaybackCursors();
      }
    });
    cutPlaybackFrameClock = {
      destroy() {
        unsubscribeFrame();
        unsubscribeState();
      },
      stop({ reset = false } = {}) {
        if (reset) resetCutPlaybackCursors();
      },
    };
  } else {
    cutPlaybackFrameClock = {
      destroy() {},
      stop({ reset = false } = {}) {
        if (reset) resetCutPlaybackCursors();
      },
    };
  }
  const skipSelectedRangeDuringPlayback = () => {
    if (cutPreviewVideo.paused) return null;
    const current = cutPreviewVideo.currentTime || 0;
    if (
      transcriptPreviewRange &&
      current >= transcriptPreviewRange.start - CUT_SPEECH_BOUNDARY_EPSILON &&
      current < transcriptPreviewRange.end - CUT_SPEECH_BOUNDARY_EPSILON
    ) {
      return null;
    }
    const range = getMergedSelection().find(
      ({ start, end }) => current >= start && current < end - 0.001,
    );
    if (!range) return null;
    const nextTime = clamp(range.end, 0, safeDuration());
    if (nextTime <= current) return null;
    cutMediaController()?.seekSource(nextTime) ?? (cutPreviewVideo.currentTime = nextTime);
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
      transcriptPreviewRange &&
      current >=
        transcriptPreviewRange.end - CUT_SPEECH_BOUNDARY_EPSILON
    ) {
      const previewEnd = transcriptPreviewRange.end;
      pauseCutPreview();
      transcriptPreviewRange = null;
      cutMediaController()?.seekSource(previewEnd) ?? (cutPreviewVideo.currentTime = previewEnd);
      current = previewEnd;
      updateCutTimelineStatus(
        "当前段落播放结束。",
        "success",
        "transcript",
      );
    }
    if (
      noSpeechPreviewEnd !== null &&
      current >= noSpeechPreviewEnd - CUT_TIMELINE_STEP
    ) {
      pauseCutPreview();
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
        pauseCutPreview();
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
    updateCutTimelinePlayhead({ renderVisual: cutPreviewVideo.paused });
  };
  const updatePlay = () => {
    const playing = !cutPreviewVideo.paused && !cutPreviewVideo.ended;
    if (playing) skipSelectedRangeDuringPlayback();
    cutPreviewPlay.setAttribute("aria-label", playing ? "暂停" : "播放");
    cutPreviewPlayIcon.hidden = playing;
    cutPreviewPauseIcon.hidden = !playing;
    if (!playing) {
      updateActiveTranscriptSegment(cutPreviewVideo.currentTime || 0, {
        follow: false,
      });
    }
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
      playCutPreview()?.catch?.(() => {});
    } else {
      pauseCutPreview();
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
    invalidateCutPlaybackStructure();
    syncCutVideoStageLayout();
    refreshCutTimeline({ force: true });
    updateTime();
  });
  cutPreviewVideo.addEventListener("durationchange", () => {
    invalidateCutPlaybackStructure();
    refreshCutTimeline();
    updateTime();
  });
  cutPreviewVideo.addEventListener("timeupdate", updateTime);
  cutPreviewVideo.addEventListener("emptied", () => {
    invalidateCutPlaybackStructure();
    updateTime();
  });
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
    invalidateCutTimelineScale();
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
        ? `共 ${historyVersions.length} 个已保存版本，最终成片会自动保留。`
        : "最终成片会自动保留；剪辑版和艺术字版可用顶部书签按钮保存。",
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
  progressTitle.textContent = "正在恢复项目";
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
  cutPlaybackFrameClock?.stop({ reset: true });
  transcriptFollowScrollController.reset();
  if (activeTranscriptItem) {
    activeTranscriptItem.classList.remove("is-playback-active");
    activeTranscriptItem.removeAttribute("aria-current");
    const badge = activeTranscriptItem.querySelector(".segment-current-badge");
    if (badge) badge.hidden = true;
  }
  activeTranscriptSegmentIndex = -1;
  activeTranscriptSegmentKey = "";
  activeTranscriptItem = null;
  transcriptPlaybackEntries = [];
  transcriptPlaybackEntryByKey = new Map();
  transcriptPlaybackCursor = -1;
  transcriptPlaybackLastTime = Number.NEGATIVE_INFINITY;
  cutDraftReady = false;
  cutDraftRevision = 0;
  cutDraftLastSignature = "";
  cutDraftSaveQueue = Promise.resolve();
  cutDraftNeedsServerSync = false;
  automaticNoSpeechInitialized = false;
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
  currentAudioQuietRanges = [];
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
  invalidateCutPlaybackStructure();
  resetCutHistoryRuntime();
  noSpeechPreviewEnd = null;
  cutSelectionPreviewEnd = null;
  transcriptPreviewRange = null;
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
  if (!window.EditorSuite?.clearMediaSource?.({ reason: "project-reset" })) {
    cutPreviewVideo.pause();
    cutPreviewVideo.removeAttribute("src");
    cutPreviewVideo.load();
  }
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

function isExpiredJobError(error) {
  return /任务不存在|不存在或服务已重启|转写任务不存在/.test(
    String(error?.message || error?.detail || ""),
  );
}

async function handleExpiredTask() {
  window.appGeneration?.hide();
  await window.appAlert?.({
    eyebrow: "需要重新上传",
    title: "当前任务已失效",
    message:
      "服务重启后，已上传视频的处理记录会清空。请重新上传视频，开始新的剪辑。",
    confirmText: "重新上传",
  });
  resetToUpload();
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
    removeLocalCutHistory(jobId);
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
    progressTitle.textContent = "正在提取音频";
    uploadStatus.textContent = "已完成";
    extractStatus.textContent = "处理中";
    transcribeStatus.textContent = "等待处理";
    setStepState(stepUpload, "complete");
    setStepState(stepExtract, "active");
    setStepState(stepTranscribe, "pending");
  } else if (job.status === "transcribing") {
    progressTitle.textContent = "正在识别文字";
    uploadStatus.textContent = "已完成";
    extractStatus.textContent = "已完成";
    transcribeStatus.textContent = "处理中";
    setStepState(stepUpload, "complete");
    setStepState(stepExtract, "complete");
    setStepState(stepTranscribe, "active");
  } else if (job.status === "completed") {
    uploadStatus.textContent = "已完成";
    extractStatus.textContent = "已完成";
    transcribeStatus.textContent = "已完成";
    setStepState(stepUpload, "complete");
    setStepState(stepExtract, "complete");
    setStepState(stepTranscribe, "complete");
    renderResult(job);
  } else if (job.status === "failed") {
    progressTitle.textContent = "处理遇到问题";
    jobErrorText.textContent = job.error || "未知错误，请重新尝试。";
    jobError.hidden = false;
    liveStatus.textContent = "处理失败";
  }
}

function renderResult(job) {
  cutPlaybackFrameClock?.stop({ reset: true });
  cutDraftReady = false;
  cutDraftRevision = 0;
  cutDraftLastSignature = "";
  cutDraftSaveQueue = Promise.resolve();
  cutDraftNeedsServerSync = false;
  automaticNoSpeechInitialized = false;
  resetCutHistoryRuntime();
  const result = job.result || {};
  const segments = result.segments || [];
  currentJobId = job.id;
  currentSegments = segments;
  currentEditableSegments = resolveEditableSegments(
    segments,
    result.editableSegments,
  );
  currentAudioQuietRanges = (result.audioQuietRanges || []).flatMap((range) => {
    const start = Number(range?.start);
    const end = Number(range?.end);
    return Number.isFinite(start) && Number.isFinite(end) && end > start
      ? [{ start, end }]
      : [];
  });
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
  invalidateCutPlaybackStructure();
  noSpeechPreviewEnd = null;
  cutSelectionPreviewEnd = null;
  transcriptPreviewRange = null;
  document.body.classList.add("has-result");
  setCurrentSuggestions(
    result.suggestions || [],
    result.suggestionStatus || "unavailable",
  );
  const noSpeechStatus = result.noSpeechStatus || "unavailable";
  setCurrentNoSpeechSuggestions(result.noSpeechSuggestions || [], noSpeechStatus);
  const persistedDraft = resolvePersistedCutDraft(
    job.cutDraft ?? null,
    currentJobId,
  );
  let shouldPersistAutomaticDefaults = false;
  if (persistedDraft === null) {
    shouldPersistAutomaticDefaults = seedAutomaticSuggestionRanges() > 0;
  } else {
    restorePersistedCutDraft(persistedDraft);
  }
  if (noSpeechStatus === "completed" && !automaticNoSpeechInitialized) {
    seedAutomaticNoSpeechRanges();
    automaticNoSpeechInitialized = true;
    shouldPersistAutomaticDefaults = true;
  }
  restoreLocalCutHistory();
  cutError.hidden = true;
  cutProgress.hidden = true;
  cutResult.hidden = true;
  setOriginalSourceActionsAllowed(!job.edit?.status);
  generateCutButton.querySelector("span").textContent = "生成剪辑视频";
  skipToArtButton.href =
    `/?job=${encodeURIComponent(currentJobId)}&source=original&tool=art`;
  directPipButton.href =
    `/?job=${encodeURIComponent(currentJobId)}&source=original&tool=pip`;
  if (!cutMediaController()) {
    cutPreviewVideo.src =
      `/api/transcriptions/${encodeURIComponent(currentJobId)}/original-video`;
    cutPreviewVideo.load();
  }

  renderCutSegments();
  updateSelectionSummary();
  cutDraftReady = true;
  if (shouldPersistAutomaticDefaults || cutDraftNeedsServerSync) {
    cutDraftLastSignature = "";
    scheduleCutDraftSave();
  }

  progressCard.hidden = true;
  resultCard.hidden = false;
  if (job.edit) renderEdit(job.edit);
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
    if (isExpiredJobError(error)) {
      handleExpiredTask();
      return;
    }
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
    if (!generationModalActive) {
      generationModalActive = true;
      window.appGeneration?.show({
        title: "生成剪辑视频",
        progress: edit.progress,
        status: edit.stage || "正在生成剪辑视频…",
        onClose: () => {
          generationModalActive = false;
        },
        onCancel: () => void cancelEditGeneration(),
      });
    } else {
      window.appGeneration?.setProgress(edit.progress, edit.stage);
    }
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
      `/?job=${encodeURIComponent(currentJobId)}&source=edited&tool=art`;
    continuePipButton.href =
      `/?job=${encodeURIComponent(currentJobId)}&source=edited&tool=pip`;
    cutDuration.textContent = `成片 ${formatTime(edit.outputDuration)}`;
    cutResult.scrollIntoView({ behavior: "smooth", block: "start" });
    cutResultTitle.focus({ preventScroll: true });
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.complete({
        videoUrl: edit.outputUrl,
        downloadUrl: `${edit.outputUrl}?download=true`,
        duration: formatTime(edit.outputDuration),
        redirectOnClose: "/",
      });
    }
  } else if (edit.status === "failed") {
    setCutOperationLock(false);
    cutProgress.hidden = true;
    cutError.textContent = edit.error || "视频剪辑失败，请重新尝试。";
    cutError.hidden = false;
    setCutControlsDisabled(false);
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.fail(
        edit.error || "视频剪辑失败，请重新尝试。",
      );
    }
  } else if (edit.status === "cancelled") {
    setCutOperationLock(false);
    cutProgress.hidden = true;
    cutError.textContent = "已取消生成。";
    cutError.hidden = false;
    setCutControlsDisabled(false);
    generateCutButton.querySelector("span").textContent = "生成剪辑视频";
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
    if (isExpiredJobError(error)) {
      handleExpiredTask();
      return;
    }
    cutProgress.hidden = false;
    cutError.hidden = true;
    setCutOperationLock(true, "连接暂时中断，正在重新获取剪辑状态…");
    editPollTimer = window.setTimeout(() => pollEdit(jobId), 1800);
  }
}

async function cancelEditGeneration() {
  if (!currentJobId) return;
  if (editPollTimer) window.clearTimeout(editPollTimer);
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(currentJobId)}/cancel`,
      { method: "POST" },
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法取消生成。");
    renderEdit(payload.edit);
    window.appGeneration?.fail("已取消生成。");
  } catch (error) {
    window.appGeneration?.fail(error.message || "取消失败，请重试。");
  }
}

async function generateCut() {
  const previewRanges = getMergedSelection();
  if (!currentJobId || previewRanges.length === 0) return;
  const deletedDuration = previewRanges.reduce(
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

  cutError.hidden = true;
  cutResult.hidden = true;
  cutProgress.hidden = false;
  setOriginalSourceActionsAllowed(false);
  setCutControlsDisabled(true);
  setCutOperationLock(true, "正在创建剪辑任务…");
  setCutProgress(5, "正在创建剪辑任务…");

  try {
    const revision = await flushCutDraftSave();
    const ranges = getMergedSelection();
    if (ranges.length === 0) {
      throw new Error("当前没有可生成的剪辑范围。");
    }
    pendingCutSelectionSignature = cutSelectionSignature(ranges);
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(currentJobId)}/cuts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ranges,
          cutDraftRevision: revision,
        }),
      },
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法创建剪辑任务。");
    renderEdit(payload);
    pollEdit(currentJobId);
  } catch (error) {
    if (isExpiredJobError(error)) {
      handleExpiredTask();
      return;
    }
    pendingCutSelectionSignature = "";
    setCutOperationLock(false);
    cutProgress.hidden = true;
    cutError.textContent = error.message;
    cutError.hidden = false;
    setCutControlsDisabled(false);
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.fail(error.message);
    }
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
  progressTitle.textContent = "正在上传视频";
  uploadStatus.textContent = "已上传 0%";
  extractStatus.textContent = "等待处理";
  transcribeStatus.textContent = "等待处理";
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
      progressTitle.textContent = "上传遇到问题";
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
    progressTitle.textContent = "上传遇到问题";
    jobErrorText.textContent = "网络连接中断，请重新选择视频上传。";
    jobError.hidden = false;
    liveStatus.textContent = "上传失败";
  });

  request.send(formData);
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

function handleTranscriptDisplayClick(event) {
  if (!(event.target instanceof Element)) return;
  const playButton = event.target.closest(".segment-play-button");
  if (playButton instanceof HTMLButtonElement) {
    if (playButton.disabled || cutControlsLocked) return;
    const segmentItem = playButton.closest(
      ".segment-item[data-display-start][data-display-end]",
    );
    if (segmentItem) previewTextSegment(segmentItem);
    return;
  }
  const noSpeechButton = event.target.closest(".segment-no-speech-button");
  if (noSpeechButton instanceof HTMLButtonElement) {
    if (noSpeechButton.disabled || cutControlsLocked) return;
    const suggestion = currentNoSpeechSuggestions.find(
      (item) => item.id === noSpeechButton.dataset.noSpeechId,
    );
    const range = getNoSpeechRange(suggestion);
    if (!suggestion || !range) return;
    if (selectedNoSpeechRanges.has(range.id)) {
      stageCutHistoryOperation("恢复空白片段");
      selectedNoSpeechRanges.delete(range.id);
      updateSelectionSummary();
    }
    previewNoSpeechSuggestion(suggestion);
    return;
  }
  const restoreButton = event.target.closest(".segment-restore-button");
  if (restoreButton instanceof HTMLButtonElement) {
    if (restoreButton.disabled || cutControlsLocked) return;
    let rangeKeys = [];
    try {
      rangeKeys = JSON.parse(restoreButton.dataset.rangeKeys || "[]");
    } catch {
      return;
    }
    const restoredRanges = rangeKeys
      .map((key) => selectedRanges.get(String(key)))
      .filter(Boolean);
    if (restoredRanges.length === 0) return;
    stageCutHistoryOperation("恢复已删除文字");
    for (const key of rangeKeys) selectedRanges.delete(String(key));
    updateSelectionSummary();
    const previewStart = Math.min(
      ...restoredRanges.map((range) =>
        Number(range.originalStart ?? range.start),
      ),
    );
    if (Number.isFinite(previewStart)) seekCutPreview(previewStart);
    return;
  }
  const editButton = event.target.closest(".segment-edit-button");
  if (editButton instanceof HTMLButtonElement) {
    if (!editButton.disabled) {
      openSegmentEditDialog(Number(editButton.dataset.segmentIndex));
    }
    return;
  }
  const segmentButton = event.target.closest(".segment-toggle");
  if (!segmentButton) {
    const segmentItem = event.target.closest(".segment-item[data-segment-index]");
    if (
      segmentItem &&
      !["restore", "deleted"].includes(segmentItem.dataset.displayKind)
    ) {
      openSegmentEditDialog(Number(segmentItem.dataset.segmentIndex));
    }
    return;
  }
  const segmentItem = segmentButton.closest(".segment-item");
  if (!segmentItem) return;

  if (segmentItem.dataset.noSpeechId) {
    const suggestion = currentNoSpeechSuggestions.find(
      (item) => item.id === segmentItem.dataset.noSpeechId,
    );
    const noSpeechRange = getNoSpeechRange(suggestion);
    if (!suggestion || !noSpeechRange || suggestion.deletable === false) return;
    if (selectedNoSpeechRanges.has(noSpeechRange.id)) {
      stageCutHistoryOperation("恢复空白片段");
      selectedNoSpeechRanges.delete(noSpeechRange.id);
      updateSelectionSummary();
      previewNoSpeechSuggestion(suggestion);
    } else {
      stageCutHistoryOperation("删除空白片段");
      selectedNoSpeechRanges.set(noSpeechRange.id, noSpeechRange);
      updateSelectionSummary();
      previewSelectedCutRange(noSpeechRange);
    }
    return;
  }

  const range = {
    start: Number(segmentItem.dataset.displayStart),
    end: Number(segmentItem.dataset.displayEnd),
    text: String(segmentItem.dataset.displayText || ""),
  };
  if (!Number.isFinite(range.start) || !Number.isFinite(range.end)) return;
  if (range.end <= range.start) return;
  let itemRangeKeys = [];
  try {
    itemRangeKeys = JSON.parse(segmentItem.dataset.rangeKeys || "[]")
      .map(String)
      .filter((key) => selectedRanges.has(key));
  } catch {
    itemRangeKeys = [];
  }
  const semanticRange = canonicalizeTextSelectionRange(range);
  const key = rangeKey(semanticRange.start, semanticRange.end);
  if (itemRangeKeys.length > 0 || selectedRanges.has(key)) {
    stageCutHistoryOperation("恢复这段文字");
    for (const selectedKey of itemRangeKeys) {
      selectedRanges.delete(selectedKey);
    }
    selectedRanges.delete(key);
    updateSelectionSummary();
    seekCutPreview(range.start);
    return;
  }
  stageCutHistoryOperation("删除这段文字");
  seekCutPreview(range.start);
  for (const [selectedKey, selectedRange] of selectedRanges.entries()) {
    const selectedStart = Number(
      selectedRange.originalStart ?? selectedRange.start,
    );
    const selectedEnd = Number(
      selectedRange.originalEnd ?? selectedRange.end,
    );
    if (
      selectedStart >= semanticRange.start &&
      selectedEnd <= semanticRange.end
    ) {
      selectedRanges.delete(selectedKey);
    }
  }
  const expandedRange = expandRangeToAdjacentSilence(semanticRange);
  selectedRanges.set(key, expandedRange);
  updateSelectionSummary();
  previewSelectedCutRange(expandedRange);
}

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
saveSegmentTextButton.addEventListener("click", saveSegmentText);
mergeSegmentUpButton.addEventListener("click", () => {
  applyEditableSegmentOperation("merge_up");
});
mergeSegmentDownButton.addEventListener("click", () => {
  applyEditableSegmentOperation("merge_down");
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
  const rangeId = Number(rangeElement.dataset.rangeId);
  const action = event.target.closest("[data-timeline-range-action]")?.dataset
    .timelineRangeAction;
  if (action === "cancel") {
    event.preventDefault();
    event.stopPropagation();
    if (timelineRangeInProgress && selectedTimelineRangeId === rangeId) {
      cancelPendingTimelineRange("已取消时间轴选区。");
    }
    return;
  }
  selectedTimelineRangeId = rangeId;
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
  cutPlaybackFrameClock?.destroy();
  transcriptFollowScrollController.destroy();
  if (selectedPreviewUrl) URL.revokeObjectURL(selectedPreviewUrl);
});

segmentList.addEventListener("click", handleTranscriptDisplayClick);
transcriptNowPlayingLayer.addEventListener(
  "click",
  handleTranscriptDisplayClick,
);

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
document.addEventListener("keydown", handleGlobalCutHistoryShortcut);
window.addEventListener("editor-suite:job-state", acceptEditorSuiteJobState);
window.EditorSuite?.registerCutTimelineAdapter?.({
  applyRange: applySharedTimelineRange,
  deleteRange: deleteSharedTimelineRange,
  flushDraft: flushCutDraftSave,
});
setupCutPreviewControls();
window.addEventListener("resize", scheduleCutTimelineResize);
loadHistoryVersions();

const rememberedJobId = getRememberedJobId();
if (rememberedJobId) {
  rememberJob(rememberedJobId);
  uploadCard.hidden = true;
  progressCard.hidden = false;
  resultCard.hidden = true;
  jobError.hidden = true;
  setProgress(0);
  progressTitle.textContent = "正在恢复项目";
  liveStatus.textContent = "正在恢复转写结果…";
  pollJob(rememberedJobId);
}
