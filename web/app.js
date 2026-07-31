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
const newUploadButton = document.querySelector("#newUploadButton");
const transcriptText = document.querySelector("#transcriptText");
const transcriptMeta = document.querySelector("#transcriptMeta");
const transcriptSegmentList = document.querySelector("#transcriptSegmentList");
const transcriptEditStatus = document.querySelector("#transcriptEditStatus");
const durationStat = document.querySelector("#durationStat");
const languageStat = document.querySelector("#languageStat");
const segmentStat = document.querySelector("#segmentStat");
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
const copyButton = document.querySelector("#copyButton");
const downloadButton = document.querySelector("#downloadButton");
const copyFeedback = document.querySelector("#copyFeedback");
const resultTitle = document.querySelector("#result-title");
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
const cutFrameTimelineTrack = document.querySelector("#cutFrameTimelineTrack");
const cutFrameTimelineRuler = document.querySelector("#cutFrameTimelineRuler");
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
const removeTimelineRangeButton = document.querySelector(
  "#removeTimelineRangeButton",
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
const CUT_TIMELINE_THUMB_MIN = 8;
const CUT_TIMELINE_THUMB_MAX = 18;
const CUT_TIMELINE_THUMB_WIDTH = 68;
const CUT_TIMELINE_MAJOR_TICK_WIDTH = 72;

let selectedFile = null;
let selectedPreviewUrl = "";
let pollTimer = null;
let editPollTimer = null;
let currentJobId = null;
let currentSegments = [];
let currentSuggestions = [];
let currentNoSpeechSuggestions = [];
let cutControlsLocked = false;
let currentVideoDuration = 0;
let timelineDeleteRanges = [];
let selectedTimelineRangeId = null;
let nextTimelineRangeId = 1;
let cutTimelineBuildId = 0;
let cutTimelineSignature = "";
let cutTimelineRulerSignature = "";
let cutTimelineResizeTimer = null;
let transcriptSaveTimer = null;
let transcriptSaveRevision = 0;
let transcriptSaveInFlight = false;
let noSpeechPreviewEnd = null;
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
  if (panelName === "transcript") {
    window.requestAnimationFrame(updateTranscriptPresentation);
  }
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

function updateTranscriptPresentation() {
  const characterCount = [...transcriptText.value.replace(/\s/g, "")].length;
  transcriptMeta.textContent =
    `AI 断句 · ${currentSegments.length} 段 · ${characterCount} 字`;
  transcriptText.style.height = "auto";
  const contentHeight = transcriptText.scrollHeight + 2;
  const nextHeight = Math.min(
    420,
    Math.max(176, contentHeight),
  );
  transcriptText.style.height = `${nextHeight}px`;
  transcriptText.style.overflowY = contentHeight > 420 ? "auto" : "hidden";
}

function renderTranscriptSegments() {
  transcriptSegmentList.replaceChildren();
  currentSegments.forEach((segment, segmentIndex) => {
    const item = document.createElement("li");
    item.className = "segment-item transcript-segment-item";

    const meta = document.createElement("div");
    meta.className = "segment-meta";
    const metaMain = document.createElement("div");
    metaMain.className = "segment-meta-main";
    const indexLabel = document.createElement("span");
    indexLabel.className = "segment-index";
    indexLabel.textContent = `段落 ${String(segmentIndex + 1).padStart(2, "0")}`;
    const time = document.createElement("span");
    time.className = "segment-time";
    time.textContent =
      `${formatPreciseTime(segment.start)} — ${formatPreciseTime(segment.end)}`;
    metaMain.append(indexLabel, time);
    meta.append(metaMain);

    const segmentText = document.createElement("p");
    segmentText.className = "segment-text transcript-segment-text";
    segmentText.textContent = String(segment.text || "暂无识别文字");
    segmentText.setAttribute(
      "aria-label",
      `第 ${segmentIndex + 1} 段：${segmentText.textContent}`,
    );

    item.append(meta, segmentText);
    transcriptSegmentList.append(item);
  });
}

function showTranscriptEditStatus(message, tone = "neutral") {
  transcriptEditStatus.textContent = message;
  transcriptEditStatus.dataset.tone = tone;
}

function syncCorrectedWords() {
  const textByRange = new Map();
  for (const segment of currentSegments) {
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

function queueTranscriptSave(revision, delay = 650) {
  if (transcriptSaveTimer) window.clearTimeout(transcriptSaveTimer);
  transcriptSaveTimer = window.setTimeout(() => {
    transcriptSaveTimer = null;
    saveTranscriptText(revision);
  }, delay);
}

async function saveTranscriptText(revision) {
  if (revision !== transcriptSaveRevision) return;
  if (transcriptSaveInFlight) {
    queueTranscriptSave(revision, 200);
    return;
  }
  if (!transcriptText.value.replace(/\s/g, "")) {
    showTranscriptEditStatus("识别全文不能为空，请恢复文字后再保存。", "error");
    return;
  }

  const submittedText = transcriptText.value;
  const jobId = currentJobId;
  transcriptSaveInFlight = true;
  showTranscriptEditStatus("正在识别修改位置并保存…");
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/transcript`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: submittedText }),
      },
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "文字保存失败，请重试。");
    }
    if (currentJobId !== jobId) return;

    currentSegments = payload.result?.segments || currentSegments;
    syncCorrectedWords();
    renderTranscriptSegments();
    updateSelectionSummary();
    if (
      revision === transcriptSaveRevision &&
      transcriptText.value === submittedText
    ) {
      transcriptText.value = payload.result?.text || submittedText;
      updateTranscriptPresentation();
      const changedWords = Number(payload.changedWords) || 0;
      showTranscriptEditStatus(
        changedWords > 0
          ? `已自动保存并同步 ${changedWords} 个词块，时间戳保持不变。`
          : "文字内容没有变化，无需更新词块。",
        "success",
      );
    } else {
      queueTranscriptSave(transcriptSaveRevision, 250);
    }
  } catch (error) {
    showTranscriptEditStatus(error.message, "error");
  } finally {
    transcriptSaveInFlight = false;
  }
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

function renderCutSegments() {
  segmentList.replaceChildren();
  currentSegments.forEach((segment, segmentIndex) => {
    const segmentStart = Number(segment.start);
    const segmentEnd = Number(segment.end);
    const hasValidRange =
      Number.isFinite(segmentStart) &&
      Number.isFinite(segmentEnd) &&
      segmentEnd > segmentStart;
    const item = document.createElement("li");
    item.className = "segment-item";

    const meta = document.createElement("div");
    meta.className = "segment-meta";
    const metaMain = document.createElement("div");
    metaMain.className = "segment-meta-main";
    const segmentIndexLabel = document.createElement("span");
    segmentIndexLabel.className = "segment-index";
    segmentIndexLabel.textContent = `段落 ${String(segmentIndex + 1).padStart(2, "0")}`;
    const time = document.createElement("span");
    time.className = "segment-time";
    time.textContent =
      `${formatPreciseTime(segment.start)} — ${formatPreciseTime(segment.end)}`;
    const selectSegmentButton = document.createElement("button");
    selectSegmentButton.type = "button";
    selectSegmentButton.className = "segment-toggle";
    selectSegmentButton.dataset.segmentIndex = String(segmentIndex);
    selectSegmentButton.setAttribute("aria-pressed", "false");
    selectSegmentButton.setAttribute(
      "aria-label",
      `选择第 ${segmentIndex + 1} 段`,
    );
    selectSegmentButton.textContent = "选择整段";
    selectSegmentButton.disabled = !hasValidRange;
    metaMain.append(segmentIndexLabel, time);
    meta.append(metaMain, selectSegmentButton);

    const segmentText = document.createElement("p");
    segmentText.className = "segment-text";
    segmentText.textContent = String(segment.text || "暂无识别文字");

    item.append(meta, segmentText);
    segmentList.append(item);
  });
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
  let markedCount = 0;
  for (const card of suggestionList.querySelectorAll(".suggestion-card")) {
    const suggestion = currentSuggestions.find(
      (item) => item.id === card.dataset.suggestionId,
    );
    if (!suggestion) continue;

    const ignored = ignoredSuggestions.has(suggestion.id);
    const marked = isSuggestionSelected(suggestion);
    if (marked) markedCount += 1;
    card.classList.toggle("is-marked", marked);
    card.classList.toggle("is-ignored", ignored);

    const applyButton = card.querySelector('[data-action="apply"]');
    const ignoreButton = card.querySelector('[data-action="ignore"]');
    const status = card.querySelector(".suggestion-card-status");
    applyButton.disabled = cutControlsLocked || ignored;
    applyButton.classList.toggle("is-active", marked);
    applyButton.setAttribute("aria-pressed", String(marked));
    applyButton.textContent = marked ? "撤销标记" : "标记删除";
    ignoreButton.disabled = cutControlsLocked;
    ignoreButton.setAttribute("aria-pressed", String(ignored));
    ignoreButton.textContent = ignored ? "恢复建议" : "忽略";
    status.textContent = ignored
      ? "已忽略"
      : marked
        ? "已加入待删除文字"
        : "等待确认";
  }

  if (currentSuggestions.length > 0) {
    suggestionState.textContent =
      markedCount > 0
        ? `共 ${currentSuggestions.length} 条建议，已标记 ${markedCount} 条。`
        : `发现 ${currentSuggestions.length} 条疑似问题，请逐条确认。`;
  }

  const allSelected =
    currentSuggestions.length > 0 &&
    currentSuggestions.every((suggestion) => isSuggestionSelected(suggestion));
  selectAllSuggestionsButton.hidden = currentSuggestions.length === 0;
  selectAllSuggestionsButton.disabled =
    cutControlsLocked || currentSuggestions.length === 0;
  selectAllSuggestionsButton.classList.toggle("is-active", allSelected);
  selectAllSuggestionsButton.setAttribute("aria-pressed", String(allSelected));
  selectAllSuggestionsButton.querySelector("span").textContent = allSelected
    ? "取消全部标记"
    : "一键标记删除";
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
  let markedCount = 0;
  for (const card of noSpeechList.querySelectorAll(".no-speech-card")) {
    const suggestion = currentNoSpeechSuggestions.find(
      (item) => item.id === card.dataset.noSpeechId,
    );
    if (!suggestion) continue;

    const marked = isNoSpeechSelected(suggestion);
    const ignored = ignoredNoSpeechSuggestions.has(suggestion.id);
    const protectedRange = Boolean(suggestion.protected);
    if (marked) markedCount += 1;
    card.classList.toggle("is-marked", marked);
    card.classList.toggle("is-ignored", ignored);
    card.classList.toggle("is-protected", protectedRange);

    const applyButton = card.querySelector('[data-action="apply"]');
    const ignoreButton = card.querySelector('[data-action="ignore"]');
    const previewButton = card.querySelector('[data-action="preview"]');
    const status = card.querySelector(".no-speech-card-status");
    const canDelete = suggestion.deletable !== false;
    applyButton.disabled = cutControlsLocked || ignored || !canDelete;
    applyButton.classList.toggle("is-active", marked);
    applyButton.setAttribute("aria-pressed", String(marked));
    setActionLabel(
      applyButton,
      marked ? "撤销标记" : protectedRange ? "仍要删除" : "标记删除",
    );
    ignoreButton.disabled = cutControlsLocked;
    ignoreButton.setAttribute("aria-pressed", String(ignored));
    setActionLabel(ignoreButton, ignored ? "恢复建议" : "忽略");
    previewButton.disabled = cutControlsLocked;
    status.textContent = !canDelete
      ? "整段无文字，不能删除全部视频"
      : ignored
        ? "已忽略"
        : marked
          ? "已加入待删除区间"
          : protectedRange
            ? "已保护，需要手动确认"
            : "等待试听确认";
  }

  const protectedCount = currentNoSpeechSuggestions.filter(
    (suggestion) => suggestion.protected,
  ).length;
  noSpeechState.classList.toggle("is-marked", markedCount > 0);
  noSpeechState.textContent =
    markedCount > 0
      ? `发现 ${currentNoSpeechSuggestions.length} 处长时间无文字片段，已标记 ${markedCount} 处。`
      : `发现 ${currentNoSpeechSuggestions.length} 处长时间无文字片段${protectedCount ? `，其中 ${protectedCount} 处片头或片尾已默认保护` : ""}。`;

  const bulkCandidates = currentNoSpeechSuggestions.filter(
    (suggestion) =>
      !suggestion.protected &&
      suggestion.deletable !== false &&
      !ignoredNoSpeechSuggestions.has(suggestion.id),
  );
  const allSelected =
    bulkCandidates.length > 0 &&
    bulkCandidates.every((suggestion) => isNoSpeechSelected(suggestion));
  selectAllNoSpeechButton.hidden = bulkCandidates.length === 0;
  selectAllNoSpeechButton.disabled =
    cutControlsLocked || bulkCandidates.length === 0;
  selectAllNoSpeechButton.classList.toggle("is-active", allSelected);
  selectAllNoSpeechButton.setAttribute("aria-pressed", String(allSelected));
  setActionLabel(
    selectAllNoSpeechButton,
    allSelected ? "取消可删标记" : "一键标记可删片段",
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
        "标记删除",
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

function getMergedTextSelection() {
  return mergeCutRanges([...selectedRanges.values()]);
}

function getMergedSelection() {
  return mergeCutRanges([
    ...getMergedTextSelection(),
    ...selectedNoSpeechRanges.values(),
    ...timelineDeleteRanges,
  ]);
}

function hasCutSelection() {
  return (
    selectedRanges.size > 0 ||
    selectedNoSpeechRanges.size > 0 ||
    timelineDeleteRanges.length > 0
  );
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
  removeTimelineRangeButton.disabled =
    disabled || selectedTimelineRangeId === null;
  updateSuggestionStates();
  updateNoSpeechStates();
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
  const selectedSegmentCount = currentSegments.filter((segment) =>
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
  if (timelineDeleteRanges.length > 0) {
    selectionParts.push(`${timelineDeleteRanges.length} 个时间轴区间`);
  }

  if (!hasCutSelection()) {
    cutSummary.textContent = "尚未选择要删除的段落";
    cutSelectionDetail.textContent = "请选择整段，或在时间轴上拖出删除区间";
    outputCutSummary.textContent = "尚未选择要删除的内容";
    outputCutSelectionDetail.textContent =
      "请先在文字剪辑、空白剪辑或时间轴中完成选择";
  } else {
    cutSummary.textContent = `已选择 ${selectionParts.join("、")}`;
    cutSelectionDetail.textContent = `预计删除 ${formatDuration(deletedDuration)} · 原视频保留`;
    outputCutSummary.textContent = `已汇总 ${selectionParts.join("、")}`;
    outputCutSelectionDetail.textContent =
      `预计删除 ${formatDuration(deletedDuration)} · 原视频保留`;
  }

  clearSelectionButton.disabled =
    cutControlsLocked || !hasCutSelection();
  generateCutButton.disabled =
    cutControlsLocked || !hasCutSelection();
  if (noSpeechCutSummary && noSpeechCutSelectionDetail) {
    if (selectedNoSpeechRanges.size === 0) {
      noSpeechCutSummary.textContent = "尚未标记要删除的空白片段";
      noSpeechCutSelectionDetail.textContent =
        "请先试听，再选择要从视频中删除的区间";
    } else {
      noSpeechCutSummary.textContent =
        `已标记 ${selectedNoSpeechRanges.size} 个空白片段`;
      const hasOtherSelections =
        selectedRanges.size > 0 || timelineDeleteRanges.length > 0;
      noSpeechCutSelectionDetail.textContent =
        `预计删除空白 ${formatDuration(noSpeechDeletedDuration)}` +
        (hasOtherSelections ? " · 生成时会合并其他已选剪辑区间" : " · 原视频保留");
    }
  }
  removeTimelineRangeButton.disabled =
    cutControlsLocked || selectedTimelineRangeId === null;
  updateOriginalSourceActionsVisibility();

  segmentList.querySelectorAll(".segment-toggle").forEach((button) => {
    const segment = currentSegments[Number(button.dataset.segmentIndex)];
    const allSelected = Boolean(
      segment && selectedRanges.has(rangeKey(segment.start, segment.end)),
    );
    button.closest(".segment-item")?.classList.toggle(
      "has-selection",
      allSelected,
    );
    button.classList.toggle("is-selected", allSelected);
    button.setAttribute("aria-pressed", String(allSelected));
    button.textContent = allSelected ? "取消整段" : "选择整段";
    button.setAttribute(
      "aria-label",
      `${allSelected ? "取消选择" : "选择"}第 ${Number(button.dataset.segmentIndex) + 1} 段`,
    );
  });
  document.body.classList.toggle(
    "has-cut-selection",
    hasCutSelection(),
  );
  renderCutTimelineRanges();
  updateSuggestionStates();
  updateNoSpeechStates();
}

function cutTimelineDuration() {
  if (currentVideoDuration > 0) return currentVideoDuration;
  return Number.isFinite(cutPreviewVideo.duration)
    ? Math.max(0, cutPreviewVideo.duration)
    : 0;
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
      ? `min(100%, ${Math.round(Math.min(440, window.innerHeight * 0.54) * ratio)}px)`
      : "min(100%, 720px)";
}

function updateCutTimelinePlayhead() {
  const total = cutTimelineDuration();
  const current = clamp(cutPreviewVideo.currentTime || 0, 0, total || 0);
  const progress = total > 0 ? current / total : 0;
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
  cutFrameTimelinePlayhead.style.left = `${progress * 100}%`;
  cutFrameTimelineTime.value = `${formatTime(current)} / ${formatTime(total)}`;
}

function seekCutPreview(seconds) {
  const total = cutTimelineDuration();
  noSpeechPreviewEnd = null;
  cutPreviewVideo.currentTime = clamp(Number(seconds) || 0, 0, total);
  updateCutTimelinePlayhead();
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
  const total = cutTimelineDuration();
  const rect = cutFrameTimelineTrack.getBoundingClientRect();
  if (rect.width <= 0 || total <= 0) return 0;
  return clamp((clientX - rect.left) / rect.width, 0, 1) * total;
}

function cutTimelineMajorStep(total, width) {
  const targetStep =
    total / Math.max(1, Math.floor(width / CUT_TIMELINE_MAJOR_TICK_WIDTH));
  const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600];
  return steps.find((step) => step >= targetStep) || steps.at(-1);
}

function renderCutTimelineRuler() {
  const total = cutTimelineDuration();
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
  const total = cutTimelineDuration();
  if (total <= 0) return;
  if (
    selectedTimelineRangeId !== null &&
    !timelineDeleteRanges.some(({ id }) => id === selectedTimelineRangeId)
  ) {
    selectedTimelineRangeId = null;
  }

  for (const range of getMergedTextSelection()) {
    const indicator = document.createElement("span");
    indicator.className = "cut-timeline-word-range";
    indicator.style.left = `${(clamp(range.start, 0, total) / total) * 100}%`;
    indicator.style.width = `${Math.max(0.25, ((range.end - range.start) / total) * 100)}%`;
    indicator.title = `文字删除区间 ${formatCutRange(range.start, range.end)}`;
    cutFrameTimelineRanges.append(indicator);
  }

  for (const range of mergeCutRanges([...selectedNoSpeechRanges.values()])) {
    const indicator = document.createElement("span");
    indicator.className = "cut-timeline-no-speech-range";
    indicator.style.left = `${(clamp(range.start, 0, total) / total) * 100}%`;
    indicator.style.width = `${Math.max(0.25, ((range.end - range.start) / total) * 100)}%`;
    indicator.title = `无文字删除区间 ${formatCutRange(range.start, range.end)}`;
    cutFrameTimelineRanges.append(indicator);
  }

  for (const range of timelineDeleteRanges) {
    const rangeElement = document.createElement("div");
    rangeElement.className = "cut-timeline-delete-range";
    rangeElement.classList.toggle(
      "is-selected",
      range.id === selectedTimelineRangeId,
    );
    rangeElement.dataset.rangeId = String(range.id);
    rangeElement.style.left = `${(clamp(range.start, 0, total) / total) * 100}%`;
    rangeElement.style.width = `${Math.max(0.25, ((range.end - range.start) / total) * 100)}%`;

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
    body.title = "拖动移动区间，按 Delete 可移除";
    body.setAttribute(
      "aria-label",
      `删除区间 ${formatCutRange(range.start, range.end)}，可拖动移动`,
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
  removeTimelineRangeButton.disabled =
    cutControlsLocked || selectedTimelineRangeId === null;
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
  const width = cutFrameTimelineTrack.clientWidth || 640;
  return clamp(
    Math.round(width / CUT_TIMELINE_THUMB_WIDTH),
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
  const total = cutTimelineDuration();
  const source = cutPreviewVideo.currentSrc || cutPreviewVideo.src;
  if (!source || total <= 0) return;
  const count = desiredCutTimelineThumbnailCount();
  const signature = `${source}|${total.toFixed(2)}|${count}`;
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
      const rawSeconds =
        count === 1 ? 0.04 : (total * index) / Math.max(1, count - 1);
      const seconds = clamp(rawSeconds, Math.min(0.04, total), Math.max(0, total - 0.04));
      await seekCutTimelineExtractor(extractor, seconds);
      if (buildId !== cutTimelineBuildId) return;
      context.drawImage(extractor, 0, 0, canvas.width, canvas.height);
      const image = document.createElement("img");
      image.src = canvas.toDataURL("image/jpeg", 0.72);
      image.alt = "";
      image.draggable = false;
      const item = document.createElement("span");
      item.className = "frame-timeline-thumb";
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
  renderCutTimelineRanges();
  buildCutTimelineThumbnails(options);
}

function beginCutTimelineSelection(event) {
  if (
    cutControlsLocked ||
    event.button !== 0 ||
    event.target.closest(".cut-timeline-delete-range")
  ) {
    return;
  }
  event.preventDefault();
  const anchorSeconds = cutTimelineSecondsFromClientX(event.clientX);
  const startClientX = event.clientX;
  let draftRange = null;
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
    }
    draftRange.start = Math.min(anchorSeconds, current);
    draftRange.end = Math.max(anchorSeconds, current);
    seekCutPreview(current);
    renderCutTimelineRanges();
    updateCutTimelineStatus(
      `正在选择删除区间 ${formatCutRange(draftRange.start, draftRange.end)}`,
      "neutral",
      "selection",
    );
  };

  const finish = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    window.removeEventListener("pointercancel", finish);
    if (!draftRange) return;
    if (draftRange.end - draftRange.start < CUT_TIMELINE_MIN_RANGE) {
      const total = cutTimelineDuration();
      draftRange.end = Math.min(total, draftRange.start + CUT_TIMELINE_MIN_RANGE);
      draftRange.start = Math.max(0, draftRange.end - CUT_TIMELINE_MIN_RANGE);
    }
    updateCutTimelineStatus(
      `已添加删除区间 ${formatCutRange(draftRange.start, draftRange.end)}。`,
      "success",
      "selection",
    );
    updateSelectionSummary();
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
    updateCutTimelineStatus(
      `已调整删除区间 ${formatCutRange(range.start, range.end)}。`,
      "success",
      "selection",
    );
    updateSelectionSummary();
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish, { once: true });
  window.addEventListener("pointercancel", finish, { once: true });
}

function removeSelectedTimelineRange() {
  if (selectedTimelineRangeId === null || cutControlsLocked) return;
  timelineDeleteRanges = timelineDeleteRanges.filter(
    ({ id }) => id !== selectedTimelineRangeId,
  );
  selectedTimelineRangeId = null;
  updateCutTimelineStatus("已移除当前时间轴删除区间。", "success");
  updateSelectionSummary();
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
    removeSelectedTimelineRange();
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
  updateSelectionSummary();
  window.requestAnimationFrame(() => {
    cutFrameTimelineRanges
      .querySelector(
        `[data-range-id="${rangeId}"] [data-drag-mode="${mode}"]`,
      )
      ?.focus({ preventScroll: true });
  });
  updateCutTimelineStatus(
    `已调整删除区间 ${formatCutRange(range.start, range.end)}。`,
    "success",
  );
}

function setupCutPreviewControls() {
  let lastAudibleVolume = 1;
  const safeDuration = () => cutTimelineDuration();
  const updateTime = () => {
    const total = safeDuration();
    const current = clamp(cutPreviewVideo.currentTime || 0, 0, total || 0);
    if (
      noSpeechPreviewEnd !== null &&
      current >= noSpeechPreviewEnd - CUT_TIMELINE_STEP
    ) {
      cutPreviewVideo.pause();
      noSpeechPreviewEnd = null;
      updateCutTimelineStatus(
        "试听结束，请确认是否标记删除。",
        "success",
        "no-speech",
      );
    }
    cutPreviewSeek.max = String(total);
    cutPreviewSeek.value = String(current);
    cutPreviewSeek.setAttribute(
      "aria-valuetext",
      `${formatTime(current)} / ${formatTime(total)}`,
    );
    cutPreviewTime.value = `${formatTime(current)} / ${formatTime(total)}`;
    updateCutTimelinePlayhead();
  };
  const updatePlay = () => {
    const playing = !cutPreviewVideo.paused && !cutPreviewVideo.ended;
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
  cutPreviewSeek.addEventListener("input", () => seekCutPreview(cutPreviewSeek.value));
  cutFrameTimelineSeek.addEventListener("input", () =>
    seekCutPreview(cutFrameTimelineSeek.value),
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
  setCutOperationLock(false);
  if (pollTimer) window.clearTimeout(pollTimer);
  if (editPollTimer) window.clearTimeout(editPollTimer);
  if (transcriptSaveTimer) window.clearTimeout(transcriptSaveTimer);
  pollTimer = null;
  editPollTimer = null;
  transcriptSaveTimer = null;
  transcriptSaveRevision = 0;
  transcriptSaveInFlight = false;
  currentJobId = null;
  forgetJob();
  currentSegments = [];
  currentSuggestions = [];
  currentNoSpeechSuggestions = [];
  cutControlsLocked = false;
  currentVideoDuration = 0;
  timelineDeleteRanges = [];
  selectedTimelineRangeId = null;
  nextTimelineRangeId = 1;
  cutTimelineBuildId += 1;
  cutTimelineSignature = "";
  cutTimelineRulerSignature = "";
  selectedRanges.clear();
  selectedNoSpeechRanges.clear();
  ignoredSuggestions.clear();
  ignoredNoSpeechSuggestions.clear();
  noSpeechPreviewEnd = null;
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
  cutFrameTimelineRuler.replaceChildren();
  cutFrameTimelineThumbnails.replaceChildren();
  cutFrameTimelineRanges.replaceChildren();
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
  if (confirmed) resetToUpload();
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
  const result = job.result || {};
  const segments = result.segments || [];
  currentJobId = job.id;
  currentSegments = segments;
  cutControlsLocked = false;
  setCutOperationLock(false);
  currentVideoDuration = Math.max(
    0,
    Number(result.mediaDuration || result.duration || job.duration) || 0,
  );
  timelineDeleteRanges = [];
  selectedTimelineRangeId = null;
  nextTimelineRangeId = 1;
  cutTimelineBuildId += 1;
  cutTimelineSignature = "";
  cutTimelineRulerSignature = "";
  selectedRanges.clear();
  selectedNoSpeechRanges.clear();
  ignoredNoSpeechSuggestions.clear();
  noSpeechPreviewEnd = null;
  document.body.classList.add("has-result");
  if (transcriptSaveTimer) window.clearTimeout(transcriptSaveTimer);
  transcriptSaveTimer = null;
  transcriptSaveRevision = 0;
  transcriptText.value = result.text || "";
  transcriptEditStatus.textContent = "";
  durationStat.textContent = formatTime(result.duration || job.duration);
  languageStat.textContent = result.language === "zh" ? "中文" : result.language || "中文";
  segmentStat.textContent = `${segments.length} 段`;
  renderSuggestions(
    result.suggestions || [],
    result.suggestionStatus || "unavailable",
  );
  renderNoSpeechSuggestions(
    result.noSpeechSuggestions || [],
    result.noSpeechStatus || "unavailable",
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
  renderTranscriptSegments();
  updateSelectionSummary();

  progressCard.hidden = true;
  resultCard.hidden = false;
  activateTextEditorPanel(job.edit ? "output" : "cuts");
  if (job.edit) renderEdit(job.edit);
  window.requestAnimationFrame(updateTranscriptPresentation);
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  resultTitle.focus({ preventScroll: true });
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
    activateTextEditorPanel("output");
  }
}

async function pollEdit(jobId) {
  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法读取剪辑进度。");

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

  cutError.hidden = true;
  cutResult.hidden = true;
  cutProgress.hidden = false;
  setOriginalSourceActionsAllowed(false);
  activateTextEditorPanel("output");
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
    setCutOperationLock(false);
    cutProgress.hidden = true;
    cutError.textContent = error.message;
    cutError.hidden = false;
    setCutControlsDisabled(false);
    activateTextEditorPanel("output");
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
  if (!segmentButton) return;
  const segment = currentSegments[Number(segmentButton.dataset.segmentIndex)];
  if (!segment) return;
  seekCutPreview(segment.start);

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
  } else {
    for (const [selectedKey, selectedRange] of selectedRanges.entries()) {
      if (
        Number(selectedRange.start) >= range.start &&
        Number(selectedRange.end) <= range.end
      ) {
        selectedRanges.delete(selectedKey);
      }
    }
    selectedRanges.set(key, range);
  }
  updateSelectionSummary();
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
  if (button.dataset.action === "apply") {
    const marked = isSuggestionSelected(suggestion);
    ignoredSuggestions.delete(suggestion.id);
    for (const range of ranges) {
      const key = rangeKey(range.start, range.end);
      if (marked) {
        selectedRanges.delete(key);
      } else {
        selectedRanges.set(key, range);
      }
    }
  } else if (button.dataset.action === "ignore") {
    if (ignoredSuggestions.has(suggestion.id)) {
      ignoredSuggestions.delete(suggestion.id);
    } else {
      ignoredSuggestions.add(suggestion.id);
      for (const range of ranges) {
        selectedRanges.delete(rangeKey(range.start, range.end));
      }
    }
  }
  updateSelectionSummary();
});

selectAllSuggestionsButton.addEventListener("click", () => {
  if (cutControlsLocked || currentSuggestions.length === 0) return;
  const allSelected = currentSuggestions.every((suggestion) =>
    isSuggestionSelected(suggestion),
  );
  ignoredSuggestions.clear();
  for (const suggestion of currentSuggestions) {
    for (const range of getSuggestionRanges(suggestion)) {
      const key = rangeKey(range.start, range.end);
      if (allSelected) {
        selectedRanges.delete(key);
      } else {
        selectedRanges.set(key, range);
      }
    }
  }
  updateSelectionSummary();
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
  if (button.dataset.action === "apply") {
    ignoredNoSpeechSuggestions.delete(suggestion.id);
    if (selectedNoSpeechRanges.has(range.id)) {
      selectedNoSpeechRanges.delete(range.id);
    } else if (suggestion.deletable !== false) {
      selectedNoSpeechRanges.set(range.id, range);
    }
  } else if (button.dataset.action === "ignore") {
    if (ignoredNoSpeechSuggestions.has(suggestion.id)) {
      ignoredNoSpeechSuggestions.delete(suggestion.id);
    } else {
      ignoredNoSpeechSuggestions.add(suggestion.id);
      selectedNoSpeechRanges.delete(range.id);
    }
  }
  updateSelectionSummary();
});

selectAllNoSpeechButton?.addEventListener("click", () => {
  if (cutControlsLocked) return;
  const candidates = currentNoSpeechSuggestions.filter(
    (suggestion) =>
      !suggestion.protected &&
      suggestion.deletable !== false &&
      !ignoredNoSpeechSuggestions.has(suggestion.id),
  );
  if (candidates.length === 0) return;
  const allSelected = candidates.every((suggestion) =>
    isNoSpeechSelected(suggestion),
  );
  for (const suggestion of candidates) {
    const range = getNoSpeechRange(suggestion);
    if (!range) continue;
    if (allSelected) {
      selectedNoSpeechRanges.delete(range.id);
    } else {
      selectedNoSpeechRanges.set(range.id, range);
    }
  }
  updateSelectionSummary();
});

clearSelectionButton.addEventListener("click", () => {
  selectedRanges.clear();
  selectedNoSpeechRanges.clear();
  timelineDeleteRanges = [];
  selectedTimelineRangeId = null;
  noSpeechPreviewEnd = null;
  updateCutTimelineStatus(
    "已清空文字、无文字片段和时间轴删除选择。",
    "success",
  );
  updateSelectionSummary();
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
removeTimelineRangeButton.addEventListener(
  "click",
  removeSelectedTimelineRange,
);

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
newUploadButton.addEventListener("click", resetToUpload);
restartProjectButton.addEventListener("click", confirmAndResetProject);

copyButton.addEventListener("click", async () => {
  const text = transcriptText.value;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    transcriptText.select();
    document.execCommand("copy");
  }
  copyFeedback.textContent = "已复制";
  window.setTimeout(() => {
    copyFeedback.textContent = "";
  }, 2200);
});

downloadButton.addEventListener("click", () => {
  const blob = new Blob([transcriptText.value], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "视频转写.txt";
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});

transcriptText.addEventListener("input", () => {
  updateTranscriptPresentation();
  transcriptSaveRevision += 1;
  showTranscriptEditStatus("已识别到文字修改，等待自动保存…");
  queueTranscriptSave(transcriptSaveRevision);
});
transcriptText.addEventListener("blur", () => {
  if (!transcriptSaveTimer) return;
  window.clearTimeout(transcriptSaveTimer);
  transcriptSaveTimer = null;
  saveTranscriptText(transcriptSaveRevision);
});
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
