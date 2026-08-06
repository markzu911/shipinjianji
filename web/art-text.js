const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;
const FONT_FAMILIES = {
  modern: '"Microsoft YaHei", sans-serif',
  bold: '"Microsoft YaHei", sans-serif',
  classic: '"SimHei", sans-serif',
  song: '"SimSun", serif',
  kai: '"KaiTi", serif',
  fang: '"FangSong", serif',
};
const BUILTIN_FONT_IDS = new Set(Object.keys(FONT_FAMILIES));
const customFontFaces = new Map();

const pageLoading = document.querySelector("#pageLoading");
const pageError = document.querySelector("#pageError");
const pageErrorText = document.querySelector("#pageErrorText");
const artWorkspace = document.querySelector("#artWorkspace");
const brandLink = document.querySelector("#brandLink");
const backToEdit = document.querySelector("#backToEdit");
const templateLibraryLink = document.querySelector("#templateLibraryLink");
const directDownload = document.querySelector("#directDownload");
const artVideo = document.querySelector("#artVideo");
const videoStage = document.querySelector("#videoStage");
const videoTime = document.querySelector("#videoTime");
const overlayLayer = document.querySelector("#overlayLayer");
const overlayCount = document.querySelector("#overlayCount");
const customText = document.querySelector("#customText");
const addCustomText = document.querySelector("#addCustomText");
const emptyControlState = document.querySelector("#emptyControlState");
const overlayControls = document.querySelector("#overlayControls");
const overlayText = document.querySelector("#overlayText");
const transcriptTrackHint = document.querySelector("#transcriptTrackHint");
const fontSelect = document.querySelector("#fontSelect");
const fontSize = document.querySelector("#fontSize");
const fontSizeValue = document.querySelector("#fontSizeValue");
const directionSelect = document.querySelector("#directionSelect");
const textAlignSelect = document.querySelector("#textAlignSelect");
const charsPerLine = document.querySelector("#charsPerLine");
const charsPerLineLabel = document.querySelector("#charsPerLineLabel");
const letterSpacing = document.querySelector("#letterSpacing");
const letterSpacingValue = document.querySelector("#letterSpacingValue");
const lineSpacing = document.querySelector("#lineSpacing");
const lineSpacingValue = document.querySelector("#lineSpacingValue");
const textColor = document.querySelector("#textColor");
const strokeColor = document.querySelector("#strokeColor");
const strokeWidth = document.querySelector("#strokeWidth");
const strokeWidthValue = document.querySelector("#strokeWidthValue");
const shadowToggle = document.querySelector("#shadowToggle");
const startTime = document.querySelector("#startTime");
const endTime = document.querySelector("#endTime");
const fitArtToTranscript = document.querySelector("#fitArtToTranscript");
const artTimeFitMessage = document.querySelector("#artTimeFitMessage");
const applyCurrentSettingsToAll = document.querySelector(
  "#applyCurrentSettingsToAll",
);
const applyAllSettingsMessage = document.querySelector(
  "#applyAllSettingsMessage",
);
const deleteOverlay = document.querySelector("#deleteOverlay");
const artStyleGrid = document.querySelector("#artStyleGrid");
let artStyleButtons = [...document.querySelectorAll(".art-style-option")];
const transcriptStyleGrid = document.querySelector("#transcriptStyleGrid");
let transcriptStyleButtons = [];
const overlayList = document.querySelector("#overlayList");
const retainedText = document.querySelector("#retainedText");
const saveRetainedText = document.querySelector("#saveRetainedText");
const retainedEditStatus = document.querySelector("#retainedEditStatus");
const retainedSegments = document.querySelector("#retainedSegments");
const retainedMeta = document.querySelector("#retainedMeta");
const selectAllRetainedSegments = document.querySelector(
  "#selectAllRetainedSegments",
);
const retainedSelectionStatus = document.querySelector(
  "#retainedSelectionStatus",
);
const addSelectedRetainedSegments = document.querySelector(
  "#addSelectedRetainedSegments",
);
const addAllRetainedSegments = document.querySelector(
  "#addAllRetainedSegments",
);
const retainedBulkMessage = document.querySelector("#retainedBulkMessage");
const generateArtVideo = document.querySelector("#generateArtVideo");
const artHistoryName = document.querySelector("#artHistoryName");
const artFormError = document.querySelector("#artFormError");
const artProgress = document.querySelector("#artProgress");
const artStatus = document.querySelector("#artStatus");
const artProgressPercent = document.querySelector("#artProgressPercent");
const artProgressTrack = document.querySelector("#artProgressTrack");
const artProgressBar = document.querySelector("#artProgressBar");
const artResult = document.querySelector("#artResult");
const artResultDuration = document.querySelector("#artResultDuration");
const finalVideo = document.querySelector("#finalVideo");
const downloadFinalVideo = document.querySelector("#downloadFinalVideo");
const continuePictureInPicture = document.querySelector(
  "#continuePictureInPicture",
);
const restartProjectButton = document.querySelector("#restartProjectButton");
const aiSuggestionCount = document.querySelector("#aiSuggestionCount");
const generateAiSuggestions = document.querySelector("#generateAiSuggestions");
const aiSuggestionLimit = document.querySelector("#aiSuggestionLimit");
const aiSuggestionError = document.querySelector("#aiSuggestionError");
const aiSuggestionProgress = document.querySelector("#aiSuggestionProgress");
const aiSuggestionStatus = document.querySelector("#aiSuggestionStatus");
const aiSuggestionProgressPercent = document.querySelector(
  "#aiSuggestionProgressPercent",
);
const aiSuggestionProgressTrack = document.querySelector(
  "#aiSuggestionProgressTrack",
);
const aiSuggestionProgressBar = document.querySelector(
  "#aiSuggestionProgressBar",
);
const aiSuggestionReview = document.querySelector("#aiSuggestionReview");
const aiSuggestionReviewCount = document.querySelector(
  "#aiSuggestionReviewCount",
);
const aiSuggestionList = document.querySelector("#aiSuggestionList");
const cancelAiSuggestions = document.querySelector("#cancelAiSuggestions");
const confirmAiSuggestions = document.querySelector("#confirmAiSuggestions");
const workbenchTabs = [...document.querySelectorAll("[data-workbench-tab]")];
const workbenchPanels = [...document.querySelectorAll("[data-workbench-panel]")];
const mediaControlGroups = [
  ...document.querySelectorAll("[data-media-controls]"),
];
const frameTimeline = document.querySelector("#frameTimeline");
const frameTimelineSeek = document.querySelector("#frameTimelineSeek");
const frameTimelineTime = document.querySelector("#frameTimelineTime");
const frameTimelineJumpInput = document.querySelector("#frameTimelineJumpInput");
const frameTimelineJumpButton = document.querySelector("#frameTimelineJumpButton");
const frameTimelineScroll = document.querySelector("#frameTimelineScroll");
const frameTimelineTrack = document.querySelector(".frame-timeline-track");
const frameTimelineRuler = document.querySelector("#frameTimelineRuler");
const frameTimelineThumbnails = document.querySelector(
  "#frameTimelineThumbnails",
);
const frameTimelineSegments = document.querySelector("#frameTimelineSegments");
const frameTimelinePlayhead = document.querySelector("#frameTimelinePlayhead");
const frameTimelineStatus = document.querySelector("#frameTimelineStatus");

const query = new URLSearchParams(window.location.search);
const embeddedEditor = query.get("embedded") === "1";
document.documentElement.classList.toggle("editor-tool-embedded", embeddedEditor);
const jobId = query.get("job") || "";
const videoSource = query.get("source") === "original" ? "original" : "edited";
const TRANSCRIPT_TRACK_MAX_CHARS_PER_CUE = 12;
const TRANSCRIPT_TRACK_DEFAULT_STYLE = "impact";
let job = null;
let duration = 0;
let overlays = [];
let cutSuppressedOverlays = [];
let selectedOverlayId = null;
let generationModalActive = false;
let nextOverlayId = 1;
let pollTimer = null;
let aiPollTimer = null;
let aiDraftSuggestions = [];
let previewDraftId = null;
let aiSuggestionBusy = false;
let availableFontIds = new Set(BUILTIN_FONT_IDS);
let availableArtTemplateIds = new Set();
const ART_STYLE_BASES = {};
let preferredArtFontId = "bold";
let retainedTranscriptSegments = [];
let selectedRetainedSegmentKeys = new Set();
let transcriptTrackBusy = false;
let transcriptTrackRefreshTimer = null;
let transcriptTrackDraftVersion = 0;
let transcriptTrackTemplateId = TRANSCRIPT_TRACK_DEFAULT_STYLE;
let transcriptSaveBusy = false;
let retainedSavedText = "";
let frameTimelineBuildId = 0;
let frameTimelineSignature = "";
let frameTimelineRulerSignature = "";
let frameTimelineResizeTimer = null;
let editorHostCurrentTime = null;
let editorHostStateSignature = "";
let previewVisibilitySignature = "";
let cutDraftActive = false;
let pendingCutDraft = null;
let appliedCutDraftState = null;
let artEditorReady = false;
let preferredArtTemplateSettings = {
  id: "impact",
  color: "#FFD84D",
  strokeColor: "#15110A",
  font: "bold",
  fontSize: 54,
};

try {
  preferredArtFontId =
    window.localStorage.getItem("preferredArtFontId") || "bold";
  const savedTemplateSettings = JSON.parse(
    window.localStorage.getItem("preferredArtTemplateSettings") || "null",
  );
  if (savedTemplateSettings && typeof savedTemplateSettings === "object") {
    preferredArtTemplateSettings = {
      ...preferredArtTemplateSettings,
      ...savedTemplateSettings,
    };
  }
} catch {
  preferredArtFontId = "bold";
}

async function loadFontLibrary() {
  const response = await fetch("/api/fonts");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "无法读取艺术字字体库。");
  }

  const previousValue = fontSelect.value;
  const uploadedGroup = fontSelect.querySelector(
    'optgroup[data-font-source="uploaded"]',
  );
  uploadedGroup?.remove();
  const customFonts = (payload.fonts || []).filter(
    (font) => font.source === "uploaded",
  );
  const nextAvailableIds = new Set(BUILTIN_FONT_IDS);
  const group = document.createElement("optgroup");
  group.label = "我的字体";
  group.dataset.fontSource = "uploaded";

  for (const font of customFonts) {
    try {
      let family = customFontFaces.get(font.id)?.family;
      if (!family) {
        family = `UserFont_${font.id.replace(/[^a-z0-9_]/gi, "_")}`;
        const format = /\.otf$/i.test(font.originalFilename || "")
          ? "opentype"
          : "truetype";
        const face = new FontFace(
          family,
          `url("${font.fileUrl}") format("${format}")`,
          { display: "swap" },
        );
        await face.load();
        document.fonts.add(face);
        customFontFaces.set(font.id, { family, face });
      }
      FONT_FAMILIES[font.id] = `"${family}", sans-serif`;
      nextAvailableIds.add(font.id);
      const option = document.createElement("option");
      option.value = font.id;
      option.textContent = font.name;
      group.append(option);
    } catch {
      // Invalid browser font data is omitted from the editor.
    }
  }

  for (const fontId of Object.keys(FONT_FAMILIES)) {
    if (!BUILTIN_FONT_IDS.has(fontId) && !nextAvailableIds.has(fontId)) {
      delete FONT_FAMILIES[fontId];
    }
  }
  availableFontIds = nextAvailableIds;
  if (group.children.length > 0) fontSelect.append(group);
  if (!availableFontIds.has(preferredArtFontId)) preferredArtFontId = "bold";
  if (availableFontIds.has(previousValue)) fontSelect.value = previousValue;
}

async function loadArtTemplateLibrary() {
  const response = await fetch("/api/art-templates");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "无法读取艺术字效果模板库。");
  }

  const templates = payload.templates || [];
  const nextTemplateIds = new Set();
  const buttons = [];
  for (const template of templates) {
    nextTemplateIds.add(template.id);
    ART_STYLE_PALETTES[template.id] = {
      color: template.color,
      strokeColor: template.strokeColor,
    };
    ART_STYLE_BASES[template.id] = template.baseStyle || template.id;

    buttons.push(createArtStyleButton(template));
  }
  artStyleGrid.replaceChildren(...buttons);
  artStyleButtons = buttons;
  availableArtTemplateIds = nextTemplateIds;
  if (!availableArtTemplateIds.has(preferredArtTemplateSettings.id)) {
    preferredArtTemplateSettings = {
      ...preferredArtTemplateSettings,
      id: "impact",
      ...ART_STYLE_PALETTES.impact,
    };
  }
  renderTranscriptStyleGrid(templates);
}

function replaceUnavailableOverlayTemplates() {
  for (const overlay of overlays) {
    if (!availableArtTemplateIds.has(overlay.artStyle)) {
      overlay.artStyle = "impact";
      Object.assign(overlay, ART_STYLE_PALETTES.impact);
    }
  }
}

function replaceUnavailableOverlayFonts() {
  for (const overlay of overlays) {
    if (!availableFontIds.has(overlay.font)) overlay.font = "bold";
  }
}

function normalizedTemplateColor(value, fallback) {
  return /^#[0-9a-f]{6}$/i.test(String(value || ""))
    ? String(value).toUpperCase()
    : fallback;
}

function createArtStyleButton(template, extraClass = "") {
  const button = document.createElement("button");
  button.className = ["art-style-option", extraClass].filter(Boolean).join(" ");
  button.type = "button";
  button.dataset.artStyle = template.id;
  button.setAttribute("aria-pressed", "false");
  const descriptionText =
    template.source === "uploaded"
      ? `我的模板 · ${template.description}`
      : template.description;
  button.title = `${template.name}：${descriptionText}`;
  button.setAttribute("aria-label", `选择${template.name}，${descriptionText}`);
  const sample = document.createElement("span");
  sample.className =
    `art-style-sample style-${template.baseStyle || template.id}`;
  sample.textContent = template.sample;
  sample.style.setProperty("--template-color", template.color);
  sample.style.setProperty("--template-stroke", template.strokeColor);
  const copy = document.createElement("span");
  const name = document.createElement("strong");
  name.textContent = template.name;
  const description = document.createElement("small");
  description.textContent = descriptionText;
  copy.append(name, description);
  button.append(sample, copy);
  return button;
}

function updateTranscriptStyleButtons() {
  const hasTrack = currentTranscriptTrack().length > 0;
  for (const button of transcriptStyleButtons) {
    const isSelected = button.dataset.artStyle === transcriptTrackTemplateId;
    button.setAttribute("aria-pressed", String(isSelected));
    button.disabled = transcriptTrackBusy || hasTrack;
  }
}

function selectedTranscriptTemplateName() {
  const button = transcriptStyleButtons.find(
    (item) => item.dataset.artStyle === transcriptTrackTemplateId,
  );
  return button?.querySelector("strong")?.textContent || "所选类型";
}

function setTranscriptTrackTemplate(artStyle, options = {}) {
  if (!ART_STYLE_PALETTES[artStyle] || !availableArtTemplateIds.has(artStyle)) {
    return false;
  }
  transcriptTrackTemplateId = artStyle;
  preferredArtTemplateSettings = {
    ...preferredArtTemplateSettings,
    id: artStyle,
    ...ART_STYLE_PALETTES[artStyle],
  };
  try {
    window.localStorage.setItem(
      "preferredArtTemplateSettings",
      JSON.stringify(preferredArtTemplateSettings),
    );
    window.localStorage.setItem("preferredArtTemplateId", artStyle);
  } catch {
    // The current session can still use the selected subtitle template.
  }
  updateTranscriptStyleButtons();
  updateRetainedBulkControls();
  if (options.announce) {
    showRetainedBulkMessage(
      `已选择“${selectedTranscriptTemplateName()}”，现在可以生成整条字幕。`,
    );
  }
  return true;
}

function renderTranscriptStyleGrid(templates) {
  if (!transcriptStyleGrid) return;
  const buttons = templates.map((template) =>
    createArtStyleButton(template, "transcript-style-option"),
  );
  transcriptStyleGrid.replaceChildren(...buttons);
  transcriptStyleButtons = buttons;
  if (
    transcriptTrackTemplateId &&
    !availableArtTemplateIds.has(transcriptTrackTemplateId)
  ) {
    transcriptTrackTemplateId = "";
  }
  updateTranscriptStyleButtons();
}

function fallbackTemplatesFromStyleButtons() {
  return artStyleButtons
    .map((button) => {
      const id = button.dataset.artStyle;
      if (!id || !ART_STYLE_PALETTES[id]) return null;
      return {
        id,
        baseStyle: id,
        sample: button.querySelector(".art-style-sample")?.textContent || id,
        name: button.querySelector("strong")?.textContent || id,
        description: button.querySelector("small")?.textContent || "",
        source: "builtin",
        ...ART_STYLE_PALETTES[id],
      };
    })
    .filter(Boolean);
}

function syncTranscriptTemplateFromExistingTrack() {
  const trackSeed = currentTranscriptTrack()[0];
  if (trackSeed?.artStyle && ART_STYLE_PALETTES[trackSeed.artStyle]) {
    transcriptTrackTemplateId = trackSeed.artStyle;
  }
  updateTranscriptStyleButtons();
}

function applyRequestedTemplateSelection() {
  const requestedStyle = query.get("template");
  if (!requestedStyle || !ART_STYLE_PALETTES[requestedStyle]) return;
  const palette = ART_STYLE_PALETTES[requestedStyle];
  const requestedFont = query.get("templateFont") || "";
  const requestedSize = clamp(
    Number(query.get("templateSize")) || preferredArtTemplateSettings.fontSize,
    20,
    180,
  );
  preferredArtTemplateSettings = {
    id: requestedStyle,
    color: normalizedTemplateColor(
      query.get("templateColor"),
      palette.color,
    ),
    strokeColor: normalizedTemplateColor(
      query.get("templateStroke"),
      palette.strokeColor,
    ),
    font: availableFontIds.has(requestedFont)
      ? requestedFont
      : preferredArtFontId,
    fontSize: requestedSize,
  };

  const overlay = selectedOverlay();
  if (overlay) {
    const templateChanges = {
      artStyle: preferredArtTemplateSettings.id,
      color: preferredArtTemplateSettings.color,
      strokeColor: preferredArtTemplateSettings.strokeColor,
      font: preferredArtTemplateSettings.font,
      fontSize: preferredArtTemplateSettings.fontSize,
    };
    const targets = isTranscriptTrackOverlay(overlay)
      ? transcriptTrackOverlays(overlay.trackId)
      : [overlay];
    for (const target of targets) Object.assign(target, templateChanges);
  }
  try {
    window.localStorage.setItem(
      "preferredArtTemplateSettings",
      JSON.stringify(preferredArtTemplateSettings),
    );
    window.localStorage.setItem(
      "preferredArtTemplateId",
      preferredArtTemplateSettings.id,
    );
  } catch {
    // The selected template still applies for the current editor session.
  }
  setTranscriptTrackTemplate(preferredArtTemplateSettings.id);
}

function activateWorkbenchPanel(name, options = {}) {
  const activeTab = workbenchTabs.find(
    (tab) => tab.dataset.workbenchTab === name,
  );
  if (!activeTab) return;

  for (const tab of workbenchTabs) {
    const isActive = tab === activeTab;
    tab.setAttribute("aria-selected", String(isActive));
    tab.tabIndex = isActive ? 0 : -1;
  }
  for (const panel of workbenchPanels) {
    panel.hidden = panel.dataset.workbenchPanel !== name;
  }
  if (options.focusTab) activeTab.focus();

  window.requestAnimationFrame(() => {
    syncVideoStageLayout();
    renderPreview();
  });
}

function revealSettingsPanel() {
  activateWorkbenchPanel("settings");
  window.requestAnimationFrame(() => {
    const panel = document.querySelector(".art-control-panel");
    if (window.innerWidth > 1000) {
      panel.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
}

const AI_POSITION_LABELS = {
  "top-left": "左上",
  "top-center": "上方",
  "top-right": "右上",
  "middle-left": "左侧",
  center: "中央",
  "middle-right": "右侧",
  "bottom-left": "左下",
  "bottom-center": "下方",
  "bottom-right": "右下",
};

const AI_POSITION_VALUES = {
  "top-left": { x: 0.2, y: 0.18 },
  "top-center": { x: 0.5, y: 0.18 },
  "top-right": { x: 0.8, y: 0.18 },
  "middle-left": { x: 0.2, y: 0.5 },
  center: { x: 0.5, y: 0.5 },
  "middle-right": { x: 0.8, y: 0.5 },
  "bottom-left": { x: 0.2, y: 0.82 },
  "bottom-center": { x: 0.5, y: 0.82 },
  "bottom-right": { x: 0.8, y: 0.82 },
};

const AI_STYLE_LABELS = {
  impact: "热血立体",
  neon: "霓虹发光",
  metal: "金属渐变",
  sticker: "标签贴纸",
  clean: "清爽描边",
  gradient: "元气渐变",
  comic: "漫画标题",
  ice: "冰晶高光",
  ink: "国风水墨",
  ribbon: "彩带标题",
  luxury: "黑金质感",
};

const FRAME_TIMELINE_STEP = 1 / 30;
const FRAME_THUMBNAIL_MIN = 8;
const FRAME_THUMBNAIL_MAX = 180;
const FRAME_TIMELINE_MAJOR_TICK_WIDTH = 72;
const FRAME_TIMELINE_MIN_PIXELS_PER_SECOND = 22;
const FRAME_TIMELINE_TEXT_CHAR_WIDTH = 10;
const FRAME_TIMELINE_TEXT_LINES = 2;

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function formatTime(seconds) {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = Math.floor(safeSeconds % 60);
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function formatRange(start, end) {
  return `${formatTime(start)}–${formatTime(end)}`;
}

function setupExternalVideoControls(container) {
  const video = document.querySelector(`#${container.dataset.videoId}`);
  const fullscreenTarget = document.querySelector(
    `#${container.dataset.fullscreenId}`,
  );
  const playButton = container.querySelector("[data-media-play]");
  const playIcon = container.querySelector("[data-media-play-icon]");
  const pauseIcon = container.querySelector("[data-media-pause-icon]");
  const seek = container.querySelector("[data-media-seek]");
  const time = container.querySelector("[data-media-time]");
  const muteButton = container.querySelector("[data-media-mute]");
  const volumeIcon = container.querySelector("[data-media-volume-icon]");
  const mutedIcon = container.querySelector("[data-media-muted-icon]");
  const volume = container.querySelector("[data-media-volume]");
  const fullscreenButton = container.querySelector("[data-media-fullscreen]");
  let lastAudibleVolume = 1;

  function safeDuration() {
    return Number.isFinite(video.duration) ? Math.max(0, video.duration) : 0;
  }

  function updateTimeControl() {
    const mediaDuration = safeDuration();
    seek.max = String(mediaDuration);
    seek.value = String(Math.min(video.currentTime || 0, mediaDuration));
    seek.setAttribute(
      "aria-valuetext",
      `${formatTime(video.currentTime)} / ${formatTime(mediaDuration)}`,
    );
    time.value = `${formatTime(video.currentTime)} / ${formatTime(mediaDuration)}`;
  }

  function updatePlayControl() {
    const isPlaying = !video.paused && !video.ended;
    playButton.setAttribute("aria-label", isPlaying ? "暂停" : "播放");
    playIcon.hidden = isPlaying;
    pauseIcon.hidden = !isPlaying;
  }

  function updateVolumeControl() {
    const isMuted = video.muted || video.volume === 0;
    muteButton.setAttribute("aria-label", isMuted ? "取消静音" : "静音");
    muteButton.setAttribute("aria-pressed", String(isMuted));
    volumeIcon.hidden = isMuted;
    mutedIcon.hidden = !isMuted;
    volume.value = String(isMuted ? 0 : video.volume);
  }

  function updateFullscreenControl() {
    const isFullscreen = document.fullscreenElement === fullscreenTarget;
    fullscreenButton.setAttribute(
      "aria-label",
      isFullscreen ? "退出全屏" : "进入全屏",
    );
    fullscreenButton.setAttribute("aria-pressed", String(isFullscreen));
  }

  function togglePlayback() {
    if (video.paused || video.ended) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement === fullscreenTarget) {
        await document.exitFullscreen();
      } else if (!document.fullscreenElement) {
        await fullscreenTarget.requestFullscreen();
      }
    } catch {
      // Keep playback controls usable when fullscreen is unavailable.
    }
  }

  playButton.addEventListener("click", togglePlayback);
  video.addEventListener("click", togglePlayback);
  video.addEventListener("dblclick", toggleFullscreen);
  seek.addEventListener("input", () => {
    const mediaDuration = safeDuration();
    video.currentTime = clamp(Number(seek.value) || 0, 0, mediaDuration);
    updateTimeControl();
    if (video === artVideo) {
      updateFrameTimelinePlayhead();
      renderPreview();
    }
  });
  muteButton.addEventListener("click", () => {
    if (video.muted || video.volume === 0) {
      video.muted = false;
      video.volume = lastAudibleVolume || 1;
    } else {
      lastAudibleVolume = video.volume || 1;
      video.muted = true;
    }
    updateVolumeControl();
  });
  volume.addEventListener("input", () => {
    const nextVolume = clamp(Number(volume.value) || 0, 0, 1);
    video.volume = nextVolume;
    video.muted = nextVolume === 0;
    if (nextVolume > 0) lastAudibleVolume = nextVolume;
    updateVolumeControl();
  });
  fullscreenButton.addEventListener("click", toggleFullscreen);
  document.addEventListener("fullscreenchange", () => {
    updateFullscreenControl();
    if (video === artVideo) syncVideoStageLayout();
  });
  for (const eventName of ["loadedmetadata", "durationchange", "timeupdate"]) {
    video.addEventListener(eventName, updateTimeControl);
  }
  for (const eventName of ["play", "pause", "ended"]) {
    video.addEventListener(eventName, updatePlayControl);
  }
  video.addEventListener("volumechange", updateVolumeControl);
  video.addEventListener("emptied", updateTimeControl);

  updateTimeControl();
  updatePlayControl();
  updateVolumeControl();
  updateFullscreenControl();
}

function frameTimelineDuration() {
  if (duration > 0) return duration;
  return Number.isFinite(artVideo.duration) ? Math.max(0, artVideo.duration) : 0;
}

function frameTimelinePixelsPerSecond() {
  let pixelsPerSecond = FRAME_TIMELINE_MIN_PIXELS_PER_SECOND;
  const previewDraft = aiDraftSuggestions.find(
    (item) => item.draftId === previewDraftId,
  );
  const items = [...overlays, ...(previewDraft ? [previewDraft] : [])];
  for (const overlay of items) {
    const itemDuration = Math.max(
      0.05,
      (Number(overlay.end) || 0) - (Number(overlay.start) || 0),
    );
    const characterCount = Array.from(
      String(overlay.text || "").replace(/\s+/g, ""),
    ).length;
    const requiredWidth =
      Math.ceil(characterCount / FRAME_TIMELINE_TEXT_LINES) *
        FRAME_TIMELINE_TEXT_CHAR_WIDTH +
      16;
    pixelsPerSecond = Math.max(pixelsPerSecond, requiredWidth / itemDuration);
  }
  return Math.ceil(pixelsPerSecond);
}

function updateFrameTimelineScale() {
  const total = frameTimelineDuration();
  const viewportWidth = frameTimelineScroll?.clientWidth || 0;
  if (total <= 0 || viewportWidth <= 0) {
    frameTimelineTrack.style.removeProperty("width");
    return;
  }
  frameTimelineTrack.style.width = `${Math.max(
    viewportWidth,
    Math.round(total * frameTimelinePixelsPerSecond()),
  )}px`;
}

function updateFrameTimelineStatus(message, tone = "neutral", source = "system") {
  if (!frameTimelineStatus) return;
  frameTimelineStatus.textContent = message;
  frameTimelineStatus.hidden = !message;
  frameTimelineStatus.dataset.tone = tone;
  frameTimelineStatus.dataset.source = source;
}

function parseFrameTimelineTimeInput(value) {
  const input = String(value || "").trim();
  if (!input) return null;
  if (/^\d+(?:\.\d+)?$/.test(input)) return Number(input);

  const parts = input.split(":");
  if (parts.length < 2 || parts.length > 3) return null;
  const secondsText = parts.at(-1);
  const wholeParts = parts.slice(0, -1);
  if (
    !/^\d+(?:\.\d+)?$/.test(secondsText) ||
    !wholeParts.every((part) => /^\d+$/.test(part))
  ) {
    return null;
  }

  const seconds = Number(secondsText);
  if (seconds >= 60) return null;
  if (parts.length === 2) return Number(parts[0]) * 60 + seconds;

  const minutes = Number(parts[1]);
  if (minutes >= 60) return null;
  return Number(parts[0]) * 3600 + minutes * 60 + seconds;
}

function showFrameTimelineJumpFeedback(message, tone = "error") {
  frameTimelineJumpInput.setAttribute(
    "aria-invalid",
    String(tone === "error"),
  );
  updateFrameTimelineStatus(message, tone, "jump");
}

function formatFrameTimelineSeconds(seconds) {
  return Number(Number(seconds).toFixed(2)).toString();
}

function jumpToFrameTimelineTime() {
  const target = parseFrameTimelineTimeInput(frameTimelineJumpInput.value);
  const total = frameTimelineDuration();
  if (target === null) {
    showFrameTimelineJumpFeedback(
      "请输入有效时间，例如 14.5 或 00:14。",
    );
    frameTimelineJumpInput.focus();
    frameTimelineJumpInput.select();
    return;
  }
  if (total <= 0) {
    showFrameTimelineJumpFeedback("视频尚未加载完成，请稍后再试。");
    return;
  }
  if (target > total) {
    showFrameTimelineJumpFeedback(
      `输入时间不能超过视频总时长 ${formatFrameTimelineSeconds(total)} 秒。`,
    );
    frameTimelineJumpInput.focus();
    frameTimelineJumpInput.select();
    return;
  }

  seekArtVideoPreview(target);
  showFrameTimelineJumpFeedback(
    `已定位到 ${formatFrameTimelineSeconds(target)} 秒。`,
    "success",
  );
}

function frameTimelineMajorStep(total, width) {
  const targetStep = total / Math.max(1, Math.floor(width / FRAME_TIMELINE_MAJOR_TICK_WIDTH));
  const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600];
  return steps.find((step) => step >= targetStep) || steps.at(-1);
}

function renderFrameTimelineRuler() {
  if (!frameTimelineRuler || !frameTimelineTrack) return;
  const total = frameTimelineDuration();
  updateFrameTimelineScale();
  const width = frameTimelineTrack.clientWidth;
  if (total <= 0 || width <= 0) {
    frameTimelineRuler.replaceChildren();
    return;
  }

  const majorStep = frameTimelineMajorStep(total, width);
  const minorStep = majorStep / 5;
  const signature = `${total.toFixed(3)}|${Math.round(width)}|${majorStep}`;
  if (signature === frameTimelineRulerSignature) return;
  frameTimelineRulerSignature = signature;
  frameTimelineRuler.replaceChildren();

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
    frameTimelineRuler.append(tick);
  }
}

function updateFrameTimelinePlayhead() {
  if (!frameTimeline || !frameTimelineSeek || !frameTimelinePlayhead) return;
  const total = frameTimelineDuration();
  const current = clamp(artVideo.currentTime || 0, 0, total || 0);
  const progress = total > 0 ? current / total : 0;
  frameTimeline.hidden = total <= 0;
  updateFrameTimelineScale();
  frameTimelineSeek.max = String(total);
  frameTimelineSeek.step = String(FRAME_TIMELINE_STEP);
  frameTimelineSeek.value = String(current);
  frameTimelineSeek.setAttribute("aria-valuemax", String(total));
  frameTimelineSeek.setAttribute("aria-valuenow", current.toFixed(2));
  frameTimelineSeek.setAttribute(
    "aria-valuetext",
    `${formatTime(current)} / ${formatTime(total)}`,
  );
  frameTimelinePlayhead.style.left = `${progress * 100}%`;
  if (frameTimelineTime) {
    frameTimelineTime.value = `${formatTime(current)} / ${formatTime(total)}`;
  }
  if (!artVideo.paused && frameTimelineScroll?.clientWidth > 0) {
    const playheadX = progress * frameTimelineTrack.clientWidth;
    const viewportStart = frameTimelineScroll.scrollLeft;
    const viewportEnd = viewportStart + frameTimelineScroll.clientWidth;
    if (playheadX < viewportStart || playheadX > viewportEnd) {
      frameTimelineScroll.scrollLeft = Math.max(
        0,
        playheadX - frameTimelineScroll.clientWidth * 0.5,
      );
    }
  }
}

function seekArtVideoPreview(seconds) {
  const total = frameTimelineDuration();
  seekEditorPreview(clamp(Number(seconds) || 0, 0, total));
  updateFrameTimelinePlayhead();
  renderPreview();
}

function timelineSecondsFromClientX(clientX) {
  const total = frameTimelineDuration();
  const rect = frameTimelineTrack?.getBoundingClientRect();
  if (!rect || rect.width <= 0 || total <= 0) return 0;
  const progress = clamp((clientX - rect.left) / rect.width, 0, 1);
  return progress * total;
}

function beginFrameTimelineScrub(event) {
  if (event.button !== 0) return;
  event.preventDefault();
  frameTimelineSeek?.focus({ preventScroll: true });
  seekArtVideoPreview(timelineSecondsFromClientX(event.clientX));

  const move = (moveEvent) => {
    seekArtVideoPreview(timelineSecondsFromClientX(moveEvent.clientX));
  };
  const finish = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    window.removeEventListener("pointercancel", finish);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish, { once: true });
  window.addEventListener("pointercancel", finish, { once: true });
}

function renderFrameTimelinePlaceholders(count) {
  if (!frameTimelineThumbnails) return;
  frameTimelineThumbnails.replaceChildren();
  for (let index = 0; index < count; index += 1) {
    const item = document.createElement("span");
    item.className = "frame-timeline-thumb is-loading";
    frameTimelineThumbnails.append(item);
  }
}

function desiredFrameThumbnailCount() {
  const total = frameTimelineDuration();
  const width = frameTimelineTrack?.clientWidth || 640;
  if (total <= 0) return FRAME_THUMBNAIL_MIN;
  const majorStep = frameTimelineMajorStep(total, width);
  return clamp(
    Math.ceil(total / majorStep) + 1,
    FRAME_THUMBNAIL_MIN,
    FRAME_THUMBNAIL_MAX,
  );
}

function waitForVideoMetadata(video) {
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
      reject(new Error("frame metadata unavailable"));
    };
    video.addEventListener("loadedmetadata", handleLoaded, { once: true });
    video.addEventListener("error", handleError, { once: true });
  });
}

function seekTimelineExtractor(video, seconds) {
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
      reject(new Error("frame seek unavailable"));
    };
    const timer = window.setTimeout(done, 900);
    video.addEventListener("seeked", handleSeeked, { once: true });
    video.addEventListener("error", handleError, { once: true });
    video.currentTime = target;
  });
}

function renderFrameTimelineFallback(count) {
  if (!frameTimelineThumbnails) return;
  frameTimelineThumbnails.replaceChildren();
  for (let index = 0; index < count; index += 1) {
    const item = document.createElement("span");
    item.className = "frame-timeline-thumb is-fallback";
    frameTimelineThumbnails.append(item);
  }
}

async function buildFrameTimelineThumbnails(options = {}) {
  if (!frameTimeline || !frameTimelineThumbnails) return;
  const total = frameTimelineDuration();
  const source = artVideo.currentSrc || artVideo.src;
  if (!source || total <= 0) {
    frameTimeline.hidden = true;
    return;
  }

  const count = desiredFrameThumbnailCount();
  const signature = `${source}|${total.toFixed(2)}|${count}`;
  if (!options.force && signature === frameTimelineSignature) return;
  frameTimelineSignature = signature;

  const buildId = (frameTimelineBuildId += 1);
  frameTimeline.hidden = false;
  renderFrameTimelinePlaceholders(count);
  updateFrameTimelineStatus("正在生成帧缩略图...");

  const extractor = document.createElement("video");
  extractor.muted = true;
  extractor.playsInline = true;
  extractor.preload = "auto";
  extractor.src = source;

  try {
    await waitForVideoMetadata(extractor);
    if (buildId !== frameTimelineBuildId) return;

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
      const edgeOffset = Math.min(0.04, total / 2);
      const rawSeconds =
        count === 1 ? edgeOffset : (total * index) / Math.max(1, count - 1);
      const seconds = clamp(
        rawSeconds,
        edgeOffset,
        Math.max(edgeOffset, total - edgeOffset),
      );
      await seekTimelineExtractor(extractor, seconds);
      if (buildId !== frameTimelineBuildId) return;
      context.drawImage(extractor, 0, 0, canvas.width, canvas.height);
      const image = document.createElement("img");
      image.src = canvas.toDataURL("image/jpeg", 0.72);
      image.alt = "";
      image.draggable = false;
      const item = document.createElement("span");
      item.className = "frame-timeline-thumb";
      item.append(image);
      frameTimelineThumbnails.children[index]?.replaceWith(item);
    }
    updateFrameTimelineStatus("");
  } catch {
    if (buildId === frameTimelineBuildId) {
      renderFrameTimelineFallback(count);
      updateFrameTimelineStatus("缩略图生成失败，可继续拖动时间轴预览。");
    }
  } finally {
    extractor.removeAttribute("src");
    extractor.load();
  }
}

function renderFrameTimelineOverlaySegments() {
  if (!frameTimelineSegments) return;
  frameTimelineSegments.replaceChildren();
  const total = frameTimelineDuration();
  if (total <= 0) {
    notifyEditorHost();
    return;
  }

  const previewDraft = aiDraftSuggestions.find(
    (item) => item.draftId === previewDraftId,
  );
  const items = [
    ...overlays.map((overlay) => ({ overlay, isDraft: false })),
    ...(previewDraft ? [{ overlay: previewDraft, isDraft: true }] : []),
  ];
  const selected = selectedOverlay();

  for (const { overlay, isDraft } of items) {
    const start = clamp(Number(overlay.start) || 0, 0, total);
    const end = clamp(Number(overlay.end) || start, start, total);
    const segment = document.createElement("span");
    segment.className = "frame-timeline-segment";
    segment.classList.toggle(
      "is-selected",
      overlay.id === selectedOverlayId ||
        (
          isTranscriptTrackOverlay(overlay) &&
          isTranscriptTrackOverlay(selected) &&
          overlay.trackId === selected.trackId
        ),
    );
    segment.classList.toggle("is-draft", isDraft);
    segment.style.left = `${(start / total) * 100}%`;
    segment.style.width = `${Math.max(0.8, ((end - start) / total) * 100)}%`;
    segment.title = `${overlay.text || ""} ${formatRange(start, end)}`.trim();
    const label = document.createElement("span");
    label.className = "editor-layer-timeline-segment-label";
    label.textContent = overlay.text || "艺术字";
    segment.append(label);
    frameTimelineSegments.append(segment);
  }
  notifyEditorHost();
}

function refreshFrameTimeline(options = {}) {
  updateFrameTimelineScale();
  updateFrameTimelinePlayhead();
  renderFrameTimelineRuler();
  renderFrameTimelineOverlaySegments();
  buildFrameTimelineThumbnails(options);
}

function scheduleFrameTimelineRebuild() {
  window.clearTimeout(frameTimelineResizeTimer);
  frameTimelineResizeTimer = window.setTimeout(() => {
    updateFrameTimelineScale();
    frameTimelineRulerSignature = "";
    renderFrameTimelineRuler();
    buildFrameTimelineThumbnails();
  }, 180);
}

function shiftHexColor(hex, amount) {
  const value = Number.parseInt(hex.slice(1), 16);
  const channels = [value >> 16, (value >> 8) & 255, value & 255];
  const shifted = channels.map((channel) =>
    clamp(
      Math.round(
        amount >= 0
          ? channel + (255 - channel) * amount
          : channel * (1 + amount),
      ),
      0,
      255,
    ),
  );
  return `#${shifted
    .map((channel) => channel.toString(16).padStart(2, "0"))
    .join("")}`;
}

function hexWithAlpha(hex, alpha) {
  const normalized = String(hex || "").trim().replace(/^#/, "");
  if (!/^[0-9a-f]{6}$/i.test(normalized)) return hex;
  const red = Number.parseInt(normalized.slice(0, 2), 16);
  const green = Number.parseInt(normalized.slice(2, 4), 16);
  const blue = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function selectedOverlay() {
  return overlays.find((overlay) => overlay.id === selectedOverlayId) || null;
}

const MANUAL_OVERLAY_LIMIT = 20;
const TRANSCRIPT_TRACK_TYPE = "transcript";
const TRANSCRIPT_TRACK_DEFAULT_POSITION = { x: 0.5, y: 0.9 };
const TRANSCRIPT_TRACK_STYLE_KEYS = new Set([
  "font",
  "fontSize",
  "color",
  "strokeColor",
  "strokeWidth",
  "shadow",
  "x",
  "y",
  "textAlign",
  "letterSpacing",
  "artStyle",
]);

function isTranscriptTrackOverlay(overlay) {
  return overlay?.trackType === TRANSCRIPT_TRACK_TYPE && Boolean(overlay.trackId);
}

function transcriptTrackOverlays(trackId = null) {
  return overlays.filter(
    (overlay) =>
      isTranscriptTrackOverlay(overlay) &&
      (!trackId || overlay.trackId === trackId),
  );
}

function currentTranscriptTrack() {
  return transcriptTrackOverlays();
}

function manualOverlayCount() {
  return [...overlays, ...cutSuppressedOverlays].filter(
    (overlay) => !isTranscriptTrackOverlay(overlay),
  ).length;
}

function selectedTrackOverlays() {
  const overlay = selectedOverlay();
  return isTranscriptTrackOverlay(overlay)
    ? transcriptTrackOverlays(overlay.trackId)
    : [];
}

function activeTrackCue(trackItems, currentTime = previewPlaybackTime()) {
  return (
    trackItems.find((overlay) => isOverlayVisibleAtTime(overlay, currentTime)) ||
    trackItems[0] ||
    null
  );
}

const LINE_END_FORBIDDEN_PUNCTUATION = new Set(
  [..."（([【《〈「『“‘"],
);
const LINE_START_FORBIDDEN_PUNCTUATION = new Set(
  [..."，。！？；：、,.!?;:）)]】》〉」』”’％%…—"],
);

function balanceHorizontalLine(sourceLine, limit) {
  const characters = [...sourceLine];
  if (limit <= 0 || characters.length <= limit) return [sourceLine];

  const lineCount = Math.ceil(characters.length / limit);
  const averageLength = characters.length / lineCount;
  const baseLength = Math.floor(characters.length / lineCount);
  const longerLineCount = characters.length % lineCount;
  const preferredLengths = Array.from(
    { length: lineCount },
    (_, index) => baseLength + (index < longerLineCount ? 1 : 0),
  );
  const costs = Array.from(
    { length: lineCount + 1 },
    () => Array(characters.length + 1).fill(Number.POSITIVE_INFINITY),
  );
  const previousBreaks = Array.from(
    { length: lineCount + 1 },
    () => Array(characters.length + 1).fill(-1),
  );
  costs[0][0] = 0;

  for (let lineIndex = 1; lineIndex <= lineCount; lineIndex += 1) {
    const remainingLines = lineCount - lineIndex;
    for (let end = lineIndex; end <= characters.length; end += 1) {
      const remainingCharacters = characters.length - end;
      if (
        remainingCharacters < remainingLines ||
        remainingCharacters > remainingLines * limit
      ) {
        continue;
      }
      const firstStart = Math.max(lineIndex - 1, end - limit);
      for (let start = firstStart; start < end; start += 1) {
        if (!Number.isFinite(costs[lineIndex - 1][start])) continue;
        if (
          end < characters.length &&
          (
            LINE_END_FORBIDDEN_PUNCTUATION.has(characters[end - 1]) ||
            LINE_START_FORBIDDEN_PUNCTUATION.has(characters[end])
          )
        ) {
          continue;
        }
        const length = end - start;
        const cost =
          costs[lineIndex - 1][start] +
          (length - averageLength) ** 2 * 100 +
          (length - preferredLengths[lineIndex - 1]) ** 2;
        if (cost < costs[lineIndex][end]) {
          costs[lineIndex][end] = cost;
          previousBreaks[lineIndex][end] = start;
        }
      }
    }
  }

  if (previousBreaks[lineCount][characters.length] < 0) {
    const lines = [];
    let start = 0;
    for (const length of preferredLengths) {
      lines.push(characters.slice(start, start + length).join(""));
      start += length;
    }
    return lines;
  }

  const lines = [];
  let end = characters.length;
  for (let lineIndex = lineCount; lineIndex > 0; lineIndex -= 1) {
    const start = previousBreaks[lineIndex][end];
    lines.push(characters.slice(start, end).join(""));
    end = start;
  }
  return lines.reverse();
}

function formatOverlayText(overlay) {
  const limit = Number(overlay.charsPerLine) || 0;
  const wrappedLines = [];
  for (const sourceLine of String(overlay.text || "").split(/\r?\n/)) {
    const characters = [...sourceLine];
    if (characters.length === 0 || limit === 0) {
      wrappedLines.push(sourceLine);
      continue;
    }
    if (overlay.direction === "horizontal") {
      wrappedLines.push(...balanceHorizontalLine(sourceLine, limit));
    } else {
      for (let index = 0; index < characters.length; index += limit) {
        wrappedLines.push(characters.slice(index, index + limit).join(""));
      }
    }
  }

  if (overlay.direction === "vertical") {
    const columns = [...wrappedLines].reverse();
    const columnGap = "\u200a".repeat(
      Math.max(1, Math.round(overlay.lineSpacing / 2)),
    );
    const rowCount = Math.max(0, ...columns.map((column) => [...column].length));
    return Array.from({ length: rowCount }, (_, rowIndex) =>
      columns
        .map((column) => [...column][rowIndex] ?? "\u3000")
        .join(columnGap),
    ).join("\n");
  }

  const characterGap = "\u200a".repeat(
    Math.round(overlay.letterSpacing / 2),
  );
  return wrappedLines
    .map((line) => characterGap ? [...line].join(characterGap) : line)
    .join("\n");
}

function showPageError(message) {
  pageLoading.hidden = true;
  artWorkspace.hidden = true;
  pageErrorText.textContent = message;
  pageError.hidden = false;
}

function normalizeOverlayRange(start, end) {
  const safeStart = clamp(
    Number(start) || 0,
    0,
    Math.max(0, duration - 0.1),
  );
  const safeEnd = clamp(
    Number(end) || safeStart + 3,
    safeStart + 0.1,
    duration,
  );
  return { start: safeStart, end: safeEnd };
}

function overlayCutContext(state = null) {
  const edit = job?.edit || {};
  const useEditedJob = !state && videoSource === "edited";
  const rawRanges = Array.isArray(state?.ranges)
    ? state.ranges
    : useEditedJob
      ? edit.ranges || edit.requestedRanges || []
      : [];
  const sourceDuration = Math.max(
    0,
    Number(state?.sourceDuration) || Number(job?.duration) || duration,
  );
  const ranges = rawRanges
    .map((range) => ({
      start: clamp(Number(range.start) || 0, 0, sourceDuration),
      end: clamp(Number(range.end) || 0, 0, sourceDuration),
    }))
    .filter((range) => range.end > range.start)
    .sort((left, right) => left.start - right.start)
    .reduce((merged, range) => {
      const previous = merged.at(-1);
      if (!previous || range.start > previous.end) {
        merged.push({ ...range });
      } else {
        previous.end = Math.max(previous.end, range.end);
      }
      return merged;
    }, []);
  return { ranges, sourceDuration };
}

function retainedTimelineSpans(context) {
  const spans = [];
  let sourceCursor = 0;
  let editedCursor = 0;
  for (const range of context.ranges) {
    if (range.start > sourceCursor) {
      const spanDuration = range.start - sourceCursor;
      spans.push({
        sourceStart: sourceCursor,
        sourceEnd: range.start,
        editedStart: editedCursor,
        editedEnd: editedCursor + spanDuration,
      });
      editedCursor += spanDuration;
    }
    sourceCursor = Math.max(sourceCursor, range.end);
  }
  if (sourceCursor < context.sourceDuration) {
    spans.push({
      sourceStart: sourceCursor,
      sourceEnd: context.sourceDuration,
      editedStart: editedCursor,
      editedEnd: editedCursor + context.sourceDuration - sourceCursor,
    });
  }
  return spans;
}

function editedTimeToSourceTime(seconds, spans, edge = "start") {
  const editedDuration = spans.at(-1)?.editedEnd || 0;
  const time = clamp(Number(seconds) || 0, 0, editedDuration);
  for (const span of spans) {
    const insideSpan =
      edge === "end"
        ? time <= span.editedEnd + 0.0001
        : time < span.editedEnd - 0.0001;
    if (insideSpan) {
      return span.sourceStart + time - span.editedStart;
    }
  }
  return spans.at(-1)?.sourceEnd ?? null;
}

function sourceRangeForEditedOverlay(overlay, state = null) {
  const spans = retainedTimelineSpans(overlayCutContext(state));
  if (!spans.length) return null;
  const sourceStart = editedTimeToSourceTime(overlay.start, spans, "start");
  const sourceEnd = editedTimeToSourceTime(overlay.end, spans, "end");
  if (
    !Number.isFinite(sourceStart) ||
    !Number.isFinite(sourceEnd) ||
    sourceEnd <= sourceStart
  ) {
    return null;
  }
  return { sourceStart, sourceEnd };
}

function anchorOverlayToSourceTimeline(overlay, state = null, force = false) {
  const hasAnchor =
    Number.isFinite(Number(overlay.sourceStart)) &&
    Number.isFinite(Number(overlay.sourceEnd)) &&
    Number(overlay.sourceEnd) > Number(overlay.sourceStart);
  if (hasAnchor && !force) return true;
  const sourceRange = sourceRangeForEditedOverlay(overlay, state);
  if (!sourceRange) return false;
  Object.assign(overlay, sourceRange);
  return true;
}

function editedRangeForSourceOverlay(overlay, state) {
  const sourceStart = Number(overlay.sourceStart);
  const sourceEnd = Number(overlay.sourceEnd);
  if (!Number.isFinite(sourceStart) || !Number.isFinite(sourceEnd)) return null;
  const intersections = retainedTimelineSpans(overlayCutContext(state))
    .map((span) => {
      const start = Math.max(sourceStart, span.sourceStart);
      const end = Math.min(sourceEnd, span.sourceEnd);
      if (end <= start) return null;
      return {
        start: span.editedStart + start - span.sourceStart,
        end: span.editedStart + end - span.sourceStart,
      };
    })
    .filter(Boolean);
  if (!intersections.length) return null;
  return {
    start: intersections[0].start,
    end: intersections.at(-1).end,
  };
}

function createOverlay(text, start, end, values = {}, options = {}) {
  const isTranscriptCue =
    values.trackType === TRANSCRIPT_TRACK_TYPE && Boolean(values.trackId);
  if (!isTranscriptCue && manualOverlayCount() >= MANUAL_OVERLAY_LIMIT) {
    showFormError(`一个视频最多添加 ${MANUAL_OVERLAY_LIMIT} 条自定义艺术字。`);
    return null;
  }

  const { start: safeStart, end: safeEnd } = isTranscriptCue
    ? {
        start: clamp(Number(start) || 0, 0, Math.max(0, duration - 0.02)),
        end: clamp(Number(end) || 0.02, 0.02, duration),
      }
    : normalizeOverlayRange(start, end);
  if (isTranscriptCue && safeEnd <= safeStart) {
    showFormError("全文艺术字包含无效词级时间，请重新生成。");
    return null;
  }
  const preferredStyle = ART_STYLE_PALETTES[preferredArtTemplateSettings.id]
    ? preferredArtTemplateSettings.id
    : "impact";
  const preferredPalette = ART_STYLE_PALETTES[preferredStyle];
  const preferredFont = availableFontIds.has(
    preferredArtTemplateSettings.font,
  )
    ? preferredArtTemplateSettings.font
    : preferredArtFontId;
  const overlay = {
    id: nextOverlayId++,
    text: String(text || "").trim(),
    font: values.font || preferredFont || "bold",
    fontSize:
      Number(values.fontSize) ||
      Number(preferredArtTemplateSettings.fontSize) ||
      54,
    color:
      values.color ||
      preferredArtTemplateSettings.color ||
      preferredPalette.color,
    strokeColor:
      values.strokeColor ||
      preferredArtTemplateSettings.strokeColor ||
      preferredPalette.strokeColor,
    strokeWidth: Number.isFinite(Number(values.strokeWidth))
      ? Number(values.strokeWidth)
      : 3,
    shadow: values.shadow ?? true,
    x: Number(values.x) || 0.5,
    y: Number(values.y) || 0.18,
    start: safeStart,
    end: safeEnd,
    direction: values.direction || "horizontal",
    textAlign: values.textAlign || "center",
    charsPerLine: Number.isFinite(Number(values.charsPerLine))
      ? Number(values.charsPerLine)
      : 10,
    letterSpacing: Number(values.letterSpacing) || 0,
    lineSpacing: Number.isFinite(Number(values.lineSpacing))
      ? Number(values.lineSpacing)
      : 8,
    artStyle: values.artStyle || preferredStyle,
    trackId: isTranscriptCue ? String(values.trackId) : null,
    trackType: isTranscriptCue ? TRANSCRIPT_TRACK_TYPE : null,
    sourceStart: Number.isFinite(Number(values.sourceStart))
      ? Number(values.sourceStart)
      : null,
    sourceEnd: Number.isFinite(Number(values.sourceEnd))
      ? Number(values.sourceEnd)
      : null,
  };
  anchorOverlayToSourceTimeline(
    overlay,
    appliedCutDraftState || (artEditorReady ? pendingCutDraft : null),
  );
  overlays.push(overlay);
  selectedOverlayId = overlay.id;
  showApplyAllSettingsMessage("");
  if (!options.deferRender) {
    seekEditorPreview(safeStart);
    showFormError("");
    renderEditor();
  }
  return overlay;
}

function addExistingOverlays(items) {
  cutSuppressedOverlays = [];
  overlays = (items || []).map((item) => ({
    direction: "horizontal",
    textAlign: "center",
    charsPerLine: 10,
    letterSpacing: 0,
    lineSpacing: 8,
    artStyle: "impact",
    trackId: null,
    trackType: null,
    ...item,
    id: nextOverlayId++,
  }));
  for (const overlay of overlays) anchorOverlayToSourceTimeline(overlay);
  selectedOverlayId = overlays[0]?.id || null;
}

function embeddedArtDraftKey() {
  return `editor-suite:art-draft:${jobId}`;
}

function persistEmbeddedArtDraft() {
  if (!embeddedEditor || !jobId) return;
  try {
    window.sessionStorage.setItem(
      embeddedArtDraftKey(),
      JSON.stringify({
        overlays: [...overlays, ...cutSuppressedOverlays],
        selectedOverlayId,
      }),
    );
  } catch {
    // The editor remains usable when private browsing blocks session storage.
  }
}

function restoreEmbeddedArtDraft() {
  if (!embeddedEditor || !jobId) return false;
  try {
    const saved = JSON.parse(
      window.sessionStorage.getItem(embeddedArtDraftKey()) || "null",
    );
    if (!saved || !Array.isArray(saved.overlays)) return false;
    addExistingOverlays(saved.overlays);
    return true;
  } catch {
    return false;
  }
}

function overlayScale() {
  if (!artVideo.videoWidth) return 1;
  return videoStage.clientWidth / artVideo.videoWidth;
}

function syncVideoStageLayout() {
  if (!artVideo.videoWidth || !artVideo.videoHeight) return;
  const ratio = artVideo.videoWidth / artVideo.videoHeight;
  const playerShell = videoStage.closest(".media-player-shell");
  videoStage.style.aspectRatio = `${artVideo.videoWidth} / ${artVideo.videoHeight}`;
  videoStage.classList.toggle("is-portrait", ratio < 1);

  if (document.fullscreenElement === playerShell) {
    playerShell.style.removeProperty("--media-player-width");
    return;
  }

  const shouldFitViewport = window.innerWidth > 1000;
  if (shouldFitViewport) {
    const previewPanel = videoStage.closest(".preview-panel");
    const timelineReserve = frameTimeline && !frameTimeline.hidden ? 180 : 0;
    const availableHeight = Math.max(
      180,
      (previewPanel?.clientHeight || window.innerHeight - 190) -
        206 -
        timelineReserve,
    );
    const availableWidth = Math.max(
      260,
      (previewPanel?.clientWidth || window.innerWidth * 0.55) - 36,
    );
    const fittedWidth = Math.min(availableWidth, availableHeight * ratio);
    videoStage.style.width = `${Math.round(fittedWidth)}px`;
    videoStage.style.maxWidth = "100%";
    playerShell.style.setProperty(
      "--media-player-width",
      `${Math.round(fittedWidth)}px`,
    );
  } else {
    videoStage.style.width = "100%";
    videoStage.style.maxWidth = "";
    playerShell.style.removeProperty("--media-player-width");
  }
}

function applyPreviewStyle(element, overlay) {
  const scale = overlayScale();
  const artStyle = ART_STYLE_BASES[overlay.artStyle] || overlay.artStyle;
  const scaledStroke = Math.max(0, overlay.strokeWidth * scale);
  element.style.left = `${overlay.x * 100}%`;
  element.style.top = `${overlay.y * 100}%`;
  element.style.transform = "translate(-50%, -50%)";
  element.style.fontFamily = FONT_FAMILIES[overlay.font] || FONT_FAMILIES.modern;
  element.style.fontWeight = overlay.font === "bold" ? "800" : "700";
  element.style.fontSize = `${Math.max(10, overlay.fontSize * scale)}px`;
  element.style.lineHeight = `${Math.max(
    10,
    (overlay.fontSize + (
      overlay.direction === "vertical"
        ? overlay.letterSpacing
        : overlay.lineSpacing
    )) * scale,
  )}px`;
  element.style.textAlign = overlay.textAlign;
  element.style.color = overlay.color;
  element.style.background = "transparent";
  element.style.backgroundClip = "border-box";
  element.style.webkitBackgroundClip = "border-box";
  element.style.border = "0";
  element.style.borderRadius = "0";
  element.style.padding = "2px 6px";
  element.style.boxShadow = "none";
  element.style.clipPath = "none";
  element.style.webkitTextStroke = `${scaledStroke}px ${overlay.strokeColor}`;
  element.style.paintOrder = "stroke fill";
  element.style.textShadow = "none";

  if (artStyle === "neon") {
    element.style.color = "#FFFFFF";
    element.style.webkitTextStroke =
      `${Math.max(1, scaledStroke)}px ${overlay.color}`;
    element.style.textShadow = [
      `0 0 ${Math.max(3, 5 * scale)}px ${overlay.color}`,
      `0 0 ${Math.max(6, 12 * scale)}px ${overlay.color}`,
      `0 0 ${Math.max(10, 22 * scale)}px ${overlay.color}`,
    ].join(",");
  } else if (artStyle === "gradient") {
    element.style.color = "transparent";
    element.style.background =
      `linear-gradient(180deg, ${shiftHexColor(overlay.color, 0.48)} 4%, ` +
      `${overlay.color} 52%, #ff4d8d 100%)`;
    element.style.backgroundClip = "text";
    element.style.webkitBackgroundClip = "text";
    element.style.webkitTextStroke =
      `${Math.max(1, scaledStroke + 1)}px ${overlay.strokeColor}`;
    element.style.textShadow =
      `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px rgba(0,0,0,.58)`;
  } else if (artStyle === "comic") {
    element.style.webkitTextStroke =
      `${Math.max(2, scaledStroke + 2)}px ${overlay.strokeColor}`;
    element.style.textShadow =
      `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px rgba(21,19,17,.58)`;
  } else if (artStyle === "ice") {
    element.style.color = "transparent";
    element.style.background =
      `linear-gradient(180deg, #ffffff 4%, ` +
      `${shiftHexColor(overlay.color, 0.32)} 42%, ${overlay.color} 100%)`;
    element.style.backgroundClip = "text";
    element.style.webkitBackgroundClip = "text";
    element.style.webkitTextStroke =
      `${Math.max(1, scaledStroke + 1)}px ${overlay.strokeColor}`;
    element.style.textShadow = [
      `0 0 ${Math.max(4, 7 * scale)}px ${overlay.color}`,
      `0 ${Math.max(2, 4 * scale)}px ${Math.max(5, 10 * scale)}px rgba(31, 149, 211, .75)`,
    ].join(",");
  } else if (artStyle === "ink") {
    element.style.color = overlay.strokeColor;
    element.style.background = overlay.color;
    element.style.border =
      `${Math.max(1, scaledStroke)}px solid ${shiftHexColor(overlay.strokeColor, 0.35)}`;
    element.style.borderLeft =
      `${Math.max(4, 7 * scale)}px solid #c7302b`;
    element.style.borderRadius = `${Math.max(4, 7 * scale)}px`;
    element.style.padding =
      `${Math.max(5, 9 * scale)}px ${Math.max(10, 18 * scale)}px`;
    element.style.webkitTextStroke = "0";
    element.style.boxShadow = overlay.shadow
      ? `${Math.max(3, 5 * scale)}px ${Math.max(3, 6 * scale)}px 0 rgba(0,0,0,.38)`
      : "none";
  } else if (artStyle === "ribbon") {
    element.style.color = "#ffffff";
    element.style.background = overlay.color;
    element.style.border = "0";
    element.style.padding =
      `${Math.max(6, 10 * scale)}px ${Math.max(15, 26 * scale)}px`;
    element.style.clipPath =
      "polygon(9% 0, 91% 0, 100% 50%, 91% 100%, 9% 100%, 0 50%)";
    element.style.webkitTextStroke =
      `${Math.min(2, scaledStroke)}px ${overlay.strokeColor}`;
    element.style.textShadow =
      `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px rgba(0,0,0,.45)`;
    element.style.boxShadow =
      `0 0 0 ${Math.max(1, scaledStroke)}px rgba(255,255,255,.85)`;
  } else if (artStyle === "luxury") {
    element.style.color = overlay.color;
    element.style.background = "rgba(7, 9, 14, .9)";
    element.style.border =
      `${Math.max(1, scaledStroke)}px solid ${overlay.color}`;
    element.style.borderRadius = `${Math.max(5, 8 * scale)}px`;
    element.style.padding =
      `${Math.max(6, 10 * scale)}px ${Math.max(11, 20 * scale)}px`;
    element.style.webkitTextStroke =
      `${Math.min(1.5, scaledStroke)}px ${overlay.strokeColor}`;
    element.style.textShadow =
      `0 0 ${Math.max(4, 8 * scale)}px ${shiftHexColor(overlay.color, -0.2)}`;
    element.style.boxShadow =
      `inset 0 0 0 1px rgba(255,255,255,.14), ` +
      `0 0 ${Math.max(5, 10 * scale)}px rgba(245,208,111,.24)`;
  } else if (artStyle === "metal") {
    element.style.color = "transparent";
    element.style.background =
      `linear-gradient(180deg, ${shiftHexColor(overlay.color, 0.72)} 5%, ` +
      `${overlay.color} 48%, ${shiftHexColor(overlay.color, -0.38)} 94%)`;
    element.style.backgroundClip = "text";
    element.style.webkitBackgroundClip = "text";
    element.style.webkitTextStroke =
      `${Math.max(1, scaledStroke + 1)}px ${overlay.strokeColor}`;
    element.style.textShadow =
      `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px ` +
      `${shiftHexColor(overlay.strokeColor, -0.2)}`;
  } else if (artStyle === "sticker") {
    element.style.color = "#FFFFFF";
    element.style.background = overlay.color;
    element.style.border =
      `${Math.max(2, scaledStroke)}px solid rgba(255, 255, 255, 0.95)`;
    element.style.borderRadius = `${Math.max(8, 14 * scale)}px`;
    element.style.padding =
      `${Math.max(5, 10 * scale)}px ${Math.max(8, 16 * scale)}px`;
    element.style.webkitTextStroke =
      `${Math.min(2, scaledStroke)}px ${overlay.strokeColor}`;
    element.style.textShadow =
      `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px rgba(0,0,0,.5)`;
  } else if (artStyle === "clean") {
    element.style.textShadow = overlay.shadow
      ? `0 ${Math.max(1, scale)}px ${Math.max(2, 5 * scale)}px rgba(0, 0, 0, 0.62)`
      : "none";
  } else {
    element.style.webkitTextStroke =
      `${Math.max(1, scaledStroke)}px ${overlay.strokeColor}`;
    element.style.textShadow = [
      `-1px -1px 0 #fff`,
      `1px -1px 0 #fff`,
      `-1px 1px 0 #fff`,
      `1px 1px 0 #fff`,
      `0 0 ${Math.max(2, 5 * scale)}px ` +
        `${hexWithAlpha(overlay.strokeColor, 0.49)}`,
    ].join(",");
  }
}

function positionPreviewOverlay(element, overlay) {
  const layerWidth = overlayLayer.clientWidth;
  const layerHeight = overlayLayer.clientHeight;
  if (!layerWidth || !layerHeight || element.hidden) return;

  const safeMarginX = layerWidth * 0.04;
  const safeMarginY = layerHeight * 0.04;
  const safeWidth = layerWidth - safeMarginX * 2;
  const safeHeight = layerHeight - safeMarginY * 2;
  const elementWidth = Math.max(1, element.offsetWidth);
  const elementHeight = Math.max(1, element.offsetHeight);
  const fitScale = Math.min(
    1,
    safeWidth / elementWidth,
    safeHeight / elementHeight,
  );
  const scaledWidth = elementWidth * fitScale;
  const scaledHeight = elementHeight * fitScale;
  const centerX = clamp(
    overlay.x * layerWidth,
    safeMarginX + scaledWidth / 2,
    layerWidth - safeMarginX - scaledWidth / 2,
  );
  const centerY = clamp(
    overlay.y * layerHeight,
    safeMarginY + scaledHeight / 2,
    layerHeight - safeMarginY - scaledHeight / 2,
  );

  element.style.left = `${centerX}px`;
  element.style.top = `${centerY}px`;
  element.style.transform = `translate(-50%, -50%) scale(${fitScale})`;
}

let lastOverlayTap = null;

function beginOverlayDrag(event, overlayId) {
  event.preventDefault();
  // A quick second tap on the same art text is a double-click to edit. The
  // native dblclick event is suppressed by preventDefault() above, so detect
  // the double-click from pointerdown timing instead.
  const now = Date.now();
  if (
    lastOverlayTap &&
    lastOverlayTap.id === overlayId &&
    now - lastOverlayTap.time < 400
  ) {
    lastOverlayTap = null;
    beginInlineOverlayEdit(overlayId);
    return;
  }
  lastOverlayTap = { id: overlayId, time: now };
  selectedOverlayId = overlayId;
  renderControls();
  renderOverlayList();
  renderPreview();

  const move = (moveEvent) => {
    // Moving the pointer means this was a drag, not a double-click.
    if (
      Math.abs(moveEvent.clientX - event.clientX) > 6 ||
      Math.abs(moveEvent.clientY - event.clientY) > 6
    ) {
      lastOverlayTap = null;
    }
    const overlay = overlays.find((item) => item.id === overlayId);
    if (!overlay) return;
    const bounds = videoStage.getBoundingClientRect();
    const x = clamp((moveEvent.clientX - bounds.left) / bounds.width, 0.05, 0.95);
    const y = clamp((moveEvent.clientY - bounds.top) / bounds.height, 0.05, 0.95);
    const targets = isTranscriptTrackOverlay(overlay)
      ? transcriptTrackOverlays(overlay.trackId)
      : [overlay];
    for (const target of targets) Object.assign(target, { x, y });
    const element = overlayLayer.querySelector(`[data-overlay-id="${overlayId}"]`);
    if (element) positionPreviewOverlay(element, overlay);
  };

  const finish = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    renderControls();
    renderOverlayList();
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish, { once: true });
}

let inlineOverlayEditor = null;

function closeInlineOverlayEditor(options = {}) {
  const editor = inlineOverlayEditor;
  inlineOverlayEditor = null;
  if (!editor || !editor.isConnected) return;
  const overlayId = Number(editor.dataset.overlayId);
  const overlay = Number.isFinite(overlayId)
    ? overlays.find((item) => item.id === overlayId)
    : null;
  const value = editor.value.trim();
  if (options.commit && overlay && value) {
    selectedOverlayId = overlay.id;
    renderControls();
    updateSelectedOverlay({ text: value });
    editor.remove();
    return;
  }
  if (options.warnEmpty && overlay && !value) {
    inlineOverlayEditor = editor;
    showRetainedBulkMessage("文案不能为空。", "warning");
    editor.focus();
    return;
  }
  editor.remove();
  if (!options.commit) renderPreview();
}

function beginInlineOverlayEdit(overlayId) {
  if (inlineOverlayEditor) closeInlineOverlayEditor();
  const overlay = overlays.find((item) => item.id === overlayId);
  if (!overlay) return;
  if (isTranscriptTrackOverlay(overlay)) {
    window.appAlert?.({
      title: "全文艺术字轨道不能单独修改文案",
      message:
        "整条 AI 分句字幕的文案来自转写内容并保持整轨同步，不能单独改其中一条。" +
        "如需自定义文案，请删除轨道后手动添加艺术字。",
    });
    return;
  }
  artVideo.pause();
  selectedOverlayId = overlay.id;
  renderControls();
  renderOverlayList();
  renderPreview();
  const overlayElement = overlayLayer.querySelector(
    `[data-overlay-id="${overlayId}"]`,
  );
  if (!overlayElement) return;

  const editor = document.createElement("textarea");
  editor.className = "art-inline-editor";
  editor.dataset.overlayId = String(overlayId);
  editor.value = String(overlay.text || "");
  editor.maxLength = 60;
  editor.rows = 1;
  const layerRect = overlayLayer.getBoundingClientRect();
  const elementRect = overlayElement.getBoundingClientRect();
  const editorWidth = Math.min(
    Math.max(160, Math.ceil(elementRect.width) + 12),
    Math.max(160, layerRect.width * 0.9),
  );
  const editorHeight = Math.min(
    Math.max(42, Math.ceil(elementRect.height) + 8),
    160,
  );
  editor.style.left = `${
    elementRect.left - layerRect.left + elementRect.width / 2 - editorWidth / 2
  }px`;
  editor.style.top = `${
    elementRect.top - layerRect.top + elementRect.height / 2 - editorHeight / 2
  }px`;
  editor.style.width = `${editorWidth}px`;
  editor.style.minHeight = `${editorHeight}px`;
  const displayFontSize = Number(getComputedStyle(overlayElement).fontSize) || 20;
  editor.style.fontSize = `${Math.max(14, Math.round(displayFontSize * 0.92))}px`;
  editor.addEventListener("pointerdown", (event) => event.stopPropagation());
  editor.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      closeInlineOverlayEditor(
        editor.value.trim() ? { commit: true } : { warnEmpty: true },
      );
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeInlineOverlayEditor();
    }
  });
  editor.addEventListener("blur", () => {
    if (inlineOverlayEditor === editor) {
      closeInlineOverlayEditor({ commit: true });
    }
  });
  inlineOverlayEditor = editor;
  overlayLayer.append(editor);
  editor.focus();
  editor.select();
}

function isOverlayVisibleAtTime(overlay, currentTime) {
  const start = Number(overlay.start) || 0;
  const end = Number(overlay.end) || start;
  return currentTime >= start && currentTime < end;
}

function previewPlaybackTime() {
  const current =
    embeddedEditor && Number.isFinite(editorHostCurrentTime)
      ? editorHostCurrentTime
      : Number(artVideo.currentTime) || 0;
  return clamp(current, 0, duration || Infinity);
}

function seekEditorPreview(seconds) {
  const nextTime = clamp(Number(seconds) || 0, 0, duration || Infinity);
  if (embeddedEditor && window.parent !== window) {
    editorHostCurrentTime = nextTime;
    window.parent.postMessage(
      {
        type: "editor-suite:seek",
        kind: "art",
        currentTime: nextTime,
      },
      window.location.origin,
    );
  } else {
    artVideo.currentTime = nextTime;
  }
  return nextTime;
}

function renderPreview(options = {}) {
  const currentTime = previewPlaybackTime();
  const previewDraft = aiDraftSuggestions.find(
    (item) => item.draftId === previewDraftId,
  );
  const visibleItems = [
    ...overlays.map((overlay) => ({ overlay, isDraft: false })),
    ...(previewDraft ? [{ overlay: previewDraft, isDraft: true }] : []),
  ].filter(({ overlay }) => isOverlayVisibleAtTime(overlay, currentTime));
  const nextVisibilitySignature = visibleItems
    .map(({ overlay, isDraft }) => `${isDraft ? "draft" : "overlay"}:${overlay.id ?? overlay.draftId}`)
    .join("|");
  if (options.timeOnly && nextVisibilitySignature === previewVisibilitySignature) {
    return;
  }
  previewVisibilitySignature = nextVisibilitySignature;
  overlayLayer.replaceChildren();
  const selected = selectedOverlay();
  for (const { overlay, isDraft } of visibleItems) {
    const element = document.createElement("div");
    const isSelected =
      isDraft ||
      overlay.id === selectedOverlayId ||
      (
        isTranscriptTrackOverlay(overlay) &&
        isTranscriptTrackOverlay(selected) &&
        overlay.trackId === selected.trackId
      );
    element.className = "preview-overlay";
    if (!isDraft) element.dataset.overlayId = String(overlay.id);
    element.textContent = formatOverlayText(overlay) || "请输入文字";
    element.classList.toggle("is-draft", isDraft);
    element.classList.toggle("is-selected", isSelected);
    applyPreviewStyle(element, overlay);
    if (!isDraft) {
      element.addEventListener("pointerdown", (event) => {
        beginOverlayDrag(event, overlay.id);
      });
    }
    overlayLayer.append(element);
    positionPreviewOverlay(element, overlay);
  }
  notifyEditorHost();
}

function notifyEditorHost(options = {}) {
  const state = {
    overlayHtml: overlayLayer.innerHTML,
    overlayWidth: overlayLayer.clientWidth,
    overlayHeight: overlayLayer.clientHeight,
    timelineHtml: frameTimelineSegments?.innerHTML || "",
    generationDisabled: generateArtVideo.disabled,
    generationLabel: generateArtVideo.textContent.trim(),
    generationBusy: !artProgress.hidden,
    generationError: artFormError.hidden ? "" : artFormError.textContent.trim(),
    generationPayload: {
      source: videoSource,
      historyName: artHistoryName.value.trim() || null,
      overlays: overlays.map(({ id, ...overlay }) => overlay),
    },
  };
  const signature = JSON.stringify(state);
  if (!options.force && signature === editorHostStateSignature) return;
  editorHostStateSignature = signature;
  if (!embeddedEditor || window.parent === window) {
    document.dispatchEvent(
      new CustomEvent("editor-suite:tool-state", {
        detail: { kind: "art", ...state },
      }),
    );
    return;
  }
  window.parent.postMessage(
    {
      type: "editor-suite:tool-state",
      kind: "art",
      currentTime: previewPlaybackTime(),
      ...state,
    },
    window.location.origin,
  );
}

function updateEditorSuiteJobState(payload) {
  window.EditorSuite?.update(payload);
  if (!embeddedEditor || window.parent === window) return;
  window.parent.postMessage(
    { type: "editor-suite:job-state", job: payload },
    window.location.origin,
  );
}

async function refreshArtAfterTranscriptUpdate() {
  if (!jobId) return;
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}`,
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法刷新艺术字。");
    job = payload;
    updateEditorSuiteJobState(payload);
    const transcript = payload.result || {};
    const nextDuration = Math.max(0, Number(payload.duration) || duration);
    duration = nextDuration;
    if (Array.isArray(transcript.segments) && transcript.segments.length) {
      renderRetainedTranscript({
        text: transcript.text || "",
        segments: transcript.segments.map((segment) => ({
          ...segment,
          start: clamp(Number(segment.start) || 0, 0, nextDuration),
          end: clamp(Number(segment.end) || 0, 0, nextDuration),
        })),
      });
    }
    const art = payload.art || {};
    if (Array.isArray(art.overlays) && art.overlays.length) {
      cutSuppressedOverlays = [];
      overlays = art.overlays.map((item) => ({
        ...item,
        id: nextOverlayId++,
      }));
      selectedOverlayId = overlays[0]?.id || null;
    }
    renderEditor();
    renderPreview({ force: true });
    showRetainedBulkMessage("已同步剪后文案，全文艺术字字幕已更新。", "success");
  } catch (error) {
    showRetainedBulkMessage("刷新艺术字失败，请手动重新生成轨道。", "warning");
  }
}

function buildTranscriptWordMatchIndex(transcript) {
  const wordByStartOffset = new Map();
  const wordByEndOffset = new Map();
  let text = "";
  for (const segment of transcript?.segments || []) {
    const segmentWords = Array.isArray(segment.words) && segment.words.length
      ? segment.words
      : [segment];
    for (const word of segmentWords) {
      const comparableText = comparableCaptionText(word.text);
      const start = Number(word.start);
      const end = Number(word.end);
      if (
        !comparableText ||
        !Number.isFinite(start) ||
        !Number.isFinite(end) ||
        end <= start
      ) {
        continue;
      }
      const item = {
        start,
        end,
        textStart: text.length,
        textEnd: text.length + comparableText.length,
        sourceStart: Number.isFinite(Number(word.sourceStart))
          ? Number(word.sourceStart)
          : null,
        sourceEnd: Number.isFinite(Number(word.sourceEnd))
          ? Number(word.sourceEnd)
          : null,
      };
      text += comparableText;
      wordByStartOffset.set(item.textStart, item);
      wordByEndOffset.set(item.textEnd, item);
    }
  }
  return { text, wordByStartOffset, wordByEndOffset };
}

function matchOverlayToTranscriptWords(overlay, index, state) {
  const target = comparableCaptionText(overlay.text);
  if (!target || !index.text) return null;
  const expectedRange = editedRangeForSourceOverlay(overlay, state);
  const expectedStart = expectedRange?.start ?? (Number(overlay.start) || 0);
  const expectedEnd =
    expectedRange?.end ?? (Number(overlay.end) || expectedStart);
  const overlaySourceStart = Number(overlay.sourceStart);
  const overlaySourceEnd = Number(overlay.sourceEnd);
  let bestMatch = null;
  let bestSourceDistance = Number.POSITIVE_INFINITY;
  let bestTimelineDistance = Number.POSITIVE_INFINITY;
  let offset = index.text.indexOf(target);

  while (offset >= 0) {
    const firstWord = index.wordByStartOffset.get(offset);
    const lastWord = index.wordByEndOffset.get(offset + target.length);
    if (firstWord && lastWord) {
      const hasSourceMatch =
        Number.isFinite(overlaySourceStart) &&
        Number.isFinite(overlaySourceEnd) &&
        Number.isFinite(firstWord.sourceStart) &&
        Number.isFinite(lastWord.sourceEnd);
      const sourceDistance = hasSourceMatch
        ? Math.abs(firstWord.sourceStart - overlaySourceStart) +
          Math.abs(lastWord.sourceEnd - overlaySourceEnd)
        : Number.POSITIVE_INFINITY;
      const timelineDistance =
        Math.abs(firstWord.start - expectedStart) +
        Math.abs(lastWord.end - expectedEnd);
      if (
        sourceDistance < bestSourceDistance - 0.0001 ||
        (
          Math.abs(sourceDistance - bestSourceDistance) <= 0.0001 &&
          timelineDistance < bestTimelineDistance
        ) ||
        (
          !Number.isFinite(sourceDistance) &&
          !Number.isFinite(bestSourceDistance) &&
          timelineDistance < bestTimelineDistance
        )
      ) {
        bestSourceDistance = sourceDistance;
        bestTimelineDistance = timelineDistance;
        bestMatch = {
          start: firstWord.start,
          end: lastWord.end,
          sourceStart: firstWord.sourceStart,
          sourceEnd: lastWord.sourceEnd,
        };
      }
    }
    offset = index.text.indexOf(target, offset + 1);
  }
  return bestMatch;
}

function retimeDraftAnchoredOverlays(data) {
  const previousState = appliedCutDraftState;
  const transcriptIndex = buildTranscriptWordMatchIndex(data.transcript);
  const retained = [];
  const suppressed = [];
  const previouslySuppressedIds = new Set(
    cutSuppressedOverlays.map((overlay) => overlay.id),
  );
  let removedCount = 0;
  let matchedCount = 0;
  for (const overlay of [...overlays, ...cutSuppressedOverlays]) {
    const hasSourceAnchor = anchorOverlayToSourceTimeline(
      overlay,
      previousState,
    );
    const wordMatch = matchOverlayToTranscriptWords(
      overlay,
      transcriptIndex,
      data,
    );
    if (wordMatch) {
      overlay.start = clamp(wordMatch.start, 0, Math.max(0, duration - 0.02));
      overlay.end = clamp(wordMatch.end, overlay.start + 0.02, duration);
      if (
        Number.isFinite(wordMatch.sourceStart) &&
        Number.isFinite(wordMatch.sourceEnd)
      ) {
        overlay.sourceStart = wordMatch.sourceStart;
        overlay.sourceEnd = wordMatch.sourceEnd;
      }
      retained.push(overlay);
      matchedCount += 1;
      continue;
    }
    if (!hasSourceAnchor) {
      retained.push(overlay);
      continue;
    }
    if (isTranscriptTrackOverlay(overlay)) {
      retained.push(overlay);
      continue;
    }
    const range = editedRangeForSourceOverlay(overlay, data);
    const minimumDuration = isTranscriptTrackOverlay(overlay) ? 0.02 : 0.05;
    if (
      isTranscriptTrackOverlay(overlay) ||
      !range ||
      range.end - range.start < minimumDuration
    ) {
      suppressed.push(overlay);
      if (!previouslySuppressedIds.has(overlay.id)) removedCount += 1;
      continue;
    }
    overlay.start = clamp(range.start, 0, Math.max(0, duration - minimumDuration));
    overlay.end = clamp(range.end, overlay.start + minimumDuration, duration);
    retained.push(overlay);
  }
  const transcriptItems = retained
    .filter(isTranscriptTrackOverlay)
    .sort((left, right) => left.start - right.start);
  for (let index = 1; index < transcriptItems.length; index += 1) {
    const previous = transcriptItems[index - 1];
    const current = transcriptItems[index];
    if (
      current.start < previous.end - 0.001 &&
      current.start - previous.start >= 0.019
    ) {
      previous.end = current.start;
    }
  }
  overlays = retained;
  cutSuppressedOverlays = suppressed;
  if (!overlays.some((overlay) => overlay.id === selectedOverlayId)) {
    selectedOverlayId = overlays[0]?.id || null;
  }
  return { matchedCount, removedCount };
}

function applyEditorCutDraft(data) {
  pendingCutDraft = data;
  transcriptTrackDraftVersion += 1;
  cutDraftActive = Boolean(data.active);
  if (!artEditorReady || !data.transcript) return;
  duration = Math.max(0, Number(data.duration) || 0);
  const segments = (data.transcript.segments || []).map((segment) => ({
    ...segment,
    start: clamp(Number(segment.start) || 0, 0, duration),
    end: clamp(Number(segment.end) || 0, 0, duration),
  }));
  const trackSeed = currentTranscriptTrack()[0];
  const locallyRebuiltTrack = trackSeed
    ? replaceTranscriptTrackFromCutDraft(
        trackSeed,
        transcriptTrackSharedStyle(trackSeed),
        data,
      )
    : [];
  const { matchedCount, removedCount } = retimeDraftAnchoredOverlays(data);
  appliedCutDraftState = data;
  renderRetainedTranscript({
    ...data.transcript,
    segments,
  });
  if (embeddedEditor) {
    editorHostCurrentTime = clamp(previewPlaybackTime(), 0, duration);
  } else {
    artVideo.currentTime = clamp(artVideo.currentTime || 0, 0, duration);
  }
  frameTimelineSeek.max = String(duration);
  frameTimelineSignature = "";
  frameTimelineRulerSignature = "";
  showRetainedBulkMessage(
    cutDraftActive
      ? `已按剪后文案的词级时间匹配 ${matchedCount} 条艺术字；点击生成视频会按当前预览一次合成。${
          removedCount ? ` 已隐藏 ${removedCount} 条文字已被删除的艺术字。` : ""
        }`
      : removedCount
        ? `已按剪后文案的词级时间同步，并隐藏 ${removedCount} 条文字已被删除的艺术字。`
        : `已按剪后文案的词级时间匹配 ${matchedCount} 条艺术字。`,
    cutDraftActive ? "warning" : "success",
  );
  renderEditor();
  if (!locallyRebuiltTrack.length && trackSeed) {
    showRetainedBulkMessage(
      "当前剪后文案缺少可用的词级时间，全文艺术字未被旧数据覆盖。",
      "warning",
    );
  }
  window.requestAnimationFrame(() => refreshFrameTimeline({ force: true }));
}

function handleEditorHostMessage(event) {
  if (
    !embeddedEditor ||
    event.origin !== window.location.origin ||
    event.source !== window.parent
  ) {
    return;
  }
  const data = event.data || {};
  if (data.type === "editor-suite:cut-draft") {
    applyEditorCutDraft(data);
    return;
  }
  if (data.type === "editor-suite:generate-video" && data.kind === "art") {
    if (generateArtVideo.disabled) return;
    generateVideo(data.composition || null);
    return;
  }
  if (data.type === "editor-suite:sync-time") {
    const nextTime = clamp(Number(data.currentTime) || 0, 0, duration || Infinity);
    editorHostCurrentTime = nextTime;
    renderPreview({ timeOnly: true });
    return;
  }
  if (data.type === "editor-suite:transcript-updated") {
    void refreshArtAfterTranscriptUpdate();
    return;
  }
  if (data.type !== "editor-suite:move-effect" || data.kind !== "art") return;
  const overlay = overlays.find((item) => String(item.id) === String(data.id));
  if (!overlay) return;
  const targets = isTranscriptTrackOverlay(overlay)
    ? transcriptTrackOverlays(overlay.trackId)
    : [overlay];
  for (const target of targets) {
    target.x = clamp(Number(data.x) || 0.5, 0.05, 0.95);
    target.y = clamp(Number(data.y) || 0.5, 0.05, 0.95);
  }
  selectedOverlayId = overlay.id;
  renderEditor();
}

window.addEventListener("message", handleEditorHostMessage);

const artGenerationObserver = new MutationObserver(notifyEditorHost);
artGenerationObserver.observe(generateArtVideo, {
  attributes: true,
  childList: true,
  subtree: true,
  attributeFilter: ["disabled"],
});
artGenerationObserver.observe(artProgress, {
  attributes: true,
  attributeFilter: ["hidden"],
});
artGenerationObserver.observe(artFormError, {
  attributes: true,
  childList: true,
  subtree: true,
  attributeFilter: ["hidden"],
});

function renderControls() {
  const overlay = selectedOverlay();
  const hasSelection = Boolean(overlay);
  const trackItems = selectedTrackOverlays();
  const isTrack = trackItems.length > 0;
  overlayControls.disabled = !hasSelection;
  fitArtToTranscript.disabled =
    !hasSelection || isTrack || retainedTranscriptSegments.length === 0;
  applyCurrentSettingsToAll.disabled =
    !hasSelection || isTrack || manualOverlayCount() < 2;
  emptyControlState.hidden = hasSelection;
  transcriptTrackHint.hidden = !isTrack;
  overlayText.readOnly = isTrack;
  directionSelect.disabled = isTrack;
  charsPerLine.disabled = isTrack;
  lineSpacing.disabled = isTrack;
  startTime.readOnly = isTrack;
  endTime.readOnly = isTrack;
  deleteOverlay.textContent = isTrack
    ? "删除全文艺术字轨道"
    : "删除当前艺术字";
  if (!overlay) return;

  overlayText.value = isTrack
    ? `全文艺术字轨道（${trackItems.length} 个单行片段）`
    : overlay.text;
  fontSelect.value = overlay.font;
  fontSize.value = String(overlay.fontSize);
  fontSizeValue.value = String(overlay.fontSize);
  directionSelect.value = overlay.direction;
  textAlignSelect.value = overlay.textAlign;
  charsPerLine.value = String(overlay.charsPerLine);
  charsPerLineLabel.textContent =
    overlay.direction === "vertical" ? "每列字数" : "每行字数";
  letterSpacing.value = String(overlay.letterSpacing);
  letterSpacingValue.value = String(overlay.letterSpacing);
  lineSpacing.value = String(overlay.lineSpacing);
  lineSpacingValue.value = String(overlay.lineSpacing);
  for (const button of artStyleButtons) {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.artStyle === overlay.artStyle),
    );
  }
  textColor.value = overlay.color;
  strokeColor.value = overlay.strokeColor;
  strokeWidth.value = String(overlay.strokeWidth);
  strokeWidthValue.value = String(overlay.strokeWidth);
  shadowToggle.checked = overlay.shadow;
  startTime.value = (
    isTrack ? trackItems[0].start : overlay.start
  ).toFixed(1);
  endTime.value = (
    isTrack ? trackItems.at(-1).end : overlay.end
  ).toFixed(1);
  startTime.max = Math.max(0, duration - 0.1).toFixed(1);
  endTime.max = duration.toFixed(1);
}

function renderOverlayList() {
  const trackItems = currentTranscriptTrack();
  const manualItems = overlays.filter(
    (overlay) => !isTranscriptTrackOverlay(overlay),
  );
  overlayCount.textContent = trackItems.length
    ? `全文轨道 · ${manualItems.length} / ${MANUAL_OVERLAY_LIMIT}`
    : `${manualItems.length} / ${MANUAL_OVERLAY_LIMIT}`;
  overlayList.replaceChildren();
  const listItems = [
    ...(trackItems.length
      ? [{
          type: "track",
          overlay: activeTrackCue(trackItems),
          overlays: trackItems,
        }]
      : []),
    ...manualItems.map((overlay) => ({
      type: "overlay",
      overlay,
      overlays: [overlay],
    })),
  ];
  const selected = selectedOverlay();
  for (const entry of listItems) {
    const { overlay } = entry;
    const item = document.createElement("li");
    const button = document.createElement("button");
    const text = document.createElement("span");
    const time = document.createElement("small");
    const isSelected =
      entry.type === "track"
        ? isTranscriptTrackOverlay(selected) &&
          selected.trackId === overlay.trackId
        : overlay.id === selectedOverlayId;
    button.type = "button";
    button.classList.toggle("is-selected", isSelected);
    button.classList.toggle("is-transcript-track", entry.type === "track");
    button.setAttribute("aria-pressed", String(isSelected));
    text.textContent =
      entry.type === "track"
        ? "全文艺术字轨道"
        : overlay.text || "未命名艺术字";
    time.textContent =
      entry.type === "track"
        ? `${entry.overlays.length} 段 · ${formatRange(
            entry.overlays[0].start,
            entry.overlays.at(-1).end,
          )}`
        : formatRange(overlay.start, overlay.end);
    button.append(text, time);
    button.addEventListener("click", () => {
      const active =
        entry.type === "track"
          ? activeTrackCue(entry.overlays)
          : overlay;
      selectedOverlayId = active.id;
      if (
        entry.type !== "track" ||
        !entry.overlays.some((cue) =>
          isOverlayVisibleAtTime(cue, previewPlaybackTime()),
        )
      ) {
        seekEditorPreview(active.start);
      }
      showArtTimeFitMessage("");
      showApplyAllSettingsMessage("");
      renderEditor();
    });
    item.append(button);
    overlayList.append(item);
  }
  generateArtVideo.disabled = overlays.length === 0;
  updateAiSuggestionLimit();
  renderFrameTimelineOverlaySegments();
}

function renderEditor() {
  renderControls();
  renderOverlayList();
  renderPreview();
  persistEmbeddedArtDraft();
}

function showApplyAllSettingsMessage(message) {
  applyAllSettingsMessage.textContent = message;
  applyAllSettingsMessage.hidden = !message;
}

function showArtTimeFitMessage(message, state = "") {
  artTimeFitMessage.textContent = message || "";
  artTimeFitMessage.dataset.state = state;
  artTimeFitMessage.hidden = !message;
}

function comparableCaptionText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[\s\p{P}\p{S}]/gu, "");
}

function transcriptCueTextLength(value) {
  return comparableCaptionText(value).length;
}

function currentCutDraftTranscript() {
  const transcript = pendingCutDraft?.transcript;
  return Array.isArray(transcript?.segments) && transcript.segments.length
    ? transcript
    : null;
}

function transcriptTrackSharedStyle(trackSeed) {
  return {
    font: trackSeed.font,
    fontSize: Number(trackSeed.fontSize) || 54,
    color: trackSeed.color,
    strokeColor: trackSeed.strokeColor,
    strokeWidth: Number(trackSeed.strokeWidth) || 0,
    shadow: trackSeed.shadow,
    x: Number(trackSeed.x),
    y: Number(trackSeed.y),
    direction: "horizontal",
    textAlign: trackSeed.textAlign || "center",
    charsPerLine: 0,
    letterSpacing: Number(trackSeed.letterSpacing) || 0,
    lineSpacing: 0,
    artStyle: trackSeed.artStyle,
  };
}

function transcriptTrackDisplayText(words) {
  return words
    .map((word) => String(word.text || ""))
    .join("")
    .replace(/\p{P}/gu, "")
    .replace(/\s+/g, " ")
    .trim();
}

function cutDraftTimedTranscriptWords(segment) {
  const rawWords = Array.isArray(segment.words) && segment.words.length
    ? segment.words
    : [segment];
  // Preserve the original letter case while matching case-insensitively, so
  // latin words like "AI" or "OK" stay capitalized in the generated subtitles.
  const segmentContent = String(segment.text || "")
    .replace(/[\s\p{P}\p{S}]/gu, "");
  const segmentLower = segmentContent.toLowerCase();
  if (!segmentContent) return [];

  const timedWords = [];
  let textOffset = 0;
  for (const [index, word] of rawWords.entries()) {
    const wordLower = String(word.text || "")
      .replace(/[\s\p{P}\p{S}]/gu, "")
      .toLowerCase();
    const start = Number(word.start);
    const end = Number(word.end);
    if (!wordLower || !Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
      continue;
    }
    const matchOffset = segmentLower.indexOf(wordLower, textOffset);
    let nextOffset = matchOffset >= textOffset
      ? matchOffset + wordLower.length
      : Math.min(segmentLower.length, textOffset + wordLower.length);
    if (index === rawWords.length - 1) nextOffset = segmentLower.length;
    const text = segmentContent.slice(textOffset, nextOffset);
    if (text) timedWords.push({ ...word, text });
    textOffset = nextOffset;
  }
  if (textOffset < segmentContent.length && timedWords.length) {
    timedWords.at(-1).text += segmentContent.slice(textOffset);
  }
  return timedWords;
}

function transcriptTrackMaxCharsPerCue(style = {}) {
  const videoWidth = Number(artVideo?.videoWidth) || 1920;
  const fontSize = Math.max(1, Number(style.fontSize) || 54);
  const strokeWidth = Math.max(0, Number(style.strokeWidth) || 0);
  const padding = Math.max(48, Math.floor(fontSize / 2), (strokeWidth + 7) * 3);
  const safeWidth = Math.max(1, videoWidth * 0.88);
  const fitted = Math.floor((safeWidth - padding * 2) / fontSize);
  return Math.max(6, Math.min(TRANSCRIPT_TRACK_MAX_CHARS_PER_CUE, fitted));
}

function cutDraftTranscriptTrackCues(data, maxChars = TRANSCRIPT_TRACK_MAX_CHARS_PER_CUE) {
  const cues = [];
  const closingMarks = /[”’》〉】」』）)\]]+$/;
  const strongBoundary = (word) =>
    /[。！？!?；;]$/.test(String(word.text || "").replace(closingMarks, ""));
  const softBoundary = (word) =>
    /[，、,:：]$/.test(String(word.text || "").replace(closingMarks, ""));
  const groupLength = (group) =>
    group.reduce((total, word) => total + transcriptCueTextLength(word.text), 0);

  const flush = (group) => {
    if (!group.length) return;
    const text = transcriptTrackDisplayText(group);
    const start = Number(group[0].start);
    const end = Number(group.at(-1).end);
    if (text && Number.isFinite(start) && Number.isFinite(end) && end > start) {
      const cue = { text, start, end };
      const sourceStart = Number(group[0].sourceStart);
      const sourceEnd = Number(group.at(-1).sourceEnd);
      if (
        Number.isFinite(sourceStart) &&
        Number.isFinite(sourceEnd) &&
        sourceEnd > sourceStart
      ) {
        Object.assign(cue, { sourceStart, sourceEnd });
      }
      cues.push(cue);
    }
  };

  // A cue may only come from one spoken sentence, so split the words into
  // sentences first and never pack across a strong sentence boundary.
  const sentences = [];
  for (const segment of data?.transcript?.segments || []) {
    let sentence = [];
    for (const word of cutDraftTimedTranscriptWords(segment)) {
      sentence.push(word);
      if (strongBoundary(word)) {
        if (sentence.length) sentences.push(sentence);
        sentence = [];
      }
    }
    if (sentence.length) sentences.push(sentence);
  }

  const splitClauses = (words) => {
    const clauses = [];
    let current = [];
    for (const word of words) {
      current.push(word);
      if (softBoundary(word)) {
        clauses.push(current);
        current = [];
      }
    }
    if (current.length) clauses.push(current);
    return clauses;
  };

  const splitLongClauseBalanced = (clause) => {
    const chunks = [];
    let remaining = [...clause];
    while (remaining.length) {
      if (groupLength(remaining) <= maxChars) {
        chunks.push(remaining);
        break;
      }
      let maxTake = 0;
      let length = 0;
      for (let index = 0; index < remaining.length; index += 1) {
        const wordLength = transcriptCueTextLength(remaining[index].text);
        if (length + wordLength > maxChars) break;
        maxTake += 1;
        length += wordLength;
      }
      if (maxTake === 0) maxTake = 1;
      const totalLength = groupLength(remaining);
      let bestTake = 1;
      let bestScore = Infinity;
      for (let take = 1; take <= maxTake; take += 1) {
        const leftLength = groupLength(remaining.slice(0, take));
        const rightLength = totalLength - leftLength;
        if (leftLength < 2 || (rightLength > 0 && rightLength < 2)) continue;
        // Audio pauses are the general signal for a natural phrase boundary.
        const pause = Math.max(
          0,
          Number(remaining[take]?.start || 0) -
            Number(remaining[take - 1]?.end || 0),
        );
        let score;
        if (pause >= 0.5) score = -90;
        else if (pause >= 0.3) score = -70;
        else if (pause >= 0.18) score = -50;
        else if (pause >= 0.1) score = -35;
        else if (pause >= 0.05) score = -18;
        else score = 0;
        if (softBoundary(remaining[take - 1])) score -= 25;
        // Balance only breaks ties between otherwise-equal boundaries.
        score += Math.abs(leftLength - rightLength);
        if (score < bestScore) {
          bestScore = score;
          bestTake = take;
        }
      }
      chunks.push(remaining.slice(0, bestTake));
      remaining = remaining.slice(bestTake);
    }
    return chunks;
  };

  const leadingPhrases = new Set([
    "说实话",
    "坦白说",
    "老实说",
    "换句话说",
    "也就是说",
    "所以说",
    "所以说啊",
    "简单来说",
    "总的来说",
    "事实上",
    "实际上",
    "比如说",
    "记住一句话",
  ]);

  const packedAll = [];
  for (const sentence of sentences) {
    const words = sentence.filter((word) => transcriptCueTextLength(word.text) > 0);
    const clauses = splitClauses(words);
    // A discourse-marker clause (e.g. "说实话，") leads the following clause.
    const mergedClauses = [];
    for (let index = 0; index < clauses.length; index += 1) {
      const clause = clauses[index];
      if (
        leadingPhrases.has(transcriptTrackDisplayText(clause)) &&
        index + 1 < clauses.length
      ) {
        mergedClauses.push([...clause, ...clauses[index + 1]]);
        index += 1;
      } else {
        mergedClauses.push(clause);
      }
    }
    // Pack whole clauses onto one line up to the budget so a sentence is not
    // fragmented at every comma.
    let current = [];
    for (const clause of mergedClauses) {
      if (
        current.length &&
        groupLength(current) + groupLength(clause) > maxChars
      ) {
        packedAll.push(current);
        current = [];
      }
      current.push(...clause);
    }
    if (current.length) packedAll.push(current);
  }

  // A single clause that alone exceeds the budget is split balanced.
  const packedLines = [];
  for (const line of packedAll) {
    if (groupLength(line) <= maxChars) {
      packedLines.push(line);
    } else {
      packedLines.push(...splitLongClauseBalanced(line));
    }
  }

  // A single-character piece leads into the following cue instead of standing
  // on its own line, across the whole track so a one-character sentence is
  // folded forward even when it is the only content of its own sentence.
  const finalGroups = [];
  let pendingFold = null;
  for (const current of packedLines) {
    if (groupLength(current) === 1 && pendingFold === null) {
      pendingFold = current;
      continue;
    }
    if (pendingFold !== null) {
      const combined = [...pendingFold, ...current];
      if (groupLength(combined) <= maxChars) {
        finalGroups.push(combined);
      } else if (current.length > 1) {
        finalGroups.push([...pendingFold, current[0]]);
        finalGroups.push(current.slice(1));
      } else {
        finalGroups.push(combined);
      }
      pendingFold = null;
      continue;
    }
    finalGroups.push(current);
  }
  if (pendingFold !== null) {
    if (finalGroups.length) {
      finalGroups[finalGroups.length - 1] = [
        ...finalGroups.at(-1),
        ...pendingFold,
      ];
    } else {
      finalGroups.push(pendingFold);
    }
  }
  finalGroups.forEach(flush);

  for (let index = 1; index < cues.length; index += 1) {
    const previous = cues[index - 1];
    const current = cues[index];
    if (current.start >= previous.end - 0.001) continue;
    if (current.start - previous.start < 0.019) return [];
    previous.end = current.start;
  }
  return cues;
}

function replaceTranscriptTrackFromCutDraft(trackSeed, sharedStyle, data) {
  const maxChars = transcriptTrackMaxCharsPerCue(sharedStyle);
  const cues = cutDraftTranscriptTrackCues(data, maxChars);
  if (!cues.length) return [];
  const existingIds = new Set(currentTranscriptTrack().map((overlay) => overlay.id));
  const trackId = trackSeed?.trackId || "transcript-full";
  const created = [];
  for (const cue of cues) {
    const overlay = createOverlay(
      cue.text,
      cue.start,
      cue.end,
      {
        ...sharedStyle,
        trackId,
        trackType: TRANSCRIPT_TRACK_TYPE,
        sourceStart: cue.sourceStart,
        sourceEnd: cue.sourceEnd,
      },
      { deferRender: true },
    );
    if (overlay) created.push(overlay);
  }
  if (created.length !== cues.length) {
    const createdIds = new Set(created.map((overlay) => overlay.id));
    overlays = overlays.filter((overlay) => !createdIds.has(overlay.id));
    return [];
  }
  overlays = overlays.filter((overlay) => !existingIds.has(overlay.id));
  cutSuppressedOverlays = cutSuppressedOverlays.filter(
    (overlay) => !isTranscriptTrackOverlay(overlay),
  );
  selectedOverlayId = activeTrackCue(created)?.id || created[0].id;
  return created;
}

function requestLatestEditorCutDraft() {
  if (!embeddedEditor || window.parent === window) return;
  window.parent.postMessage(
    { type: "editor-suite:request-cut-draft", kind: "art" },
    window.location.origin,
  );
}

function matchingTranscriptSegment(overlay) {
  if (!retainedTranscriptSegments.length) return null;
  const overlayText = comparableCaptionText(overlay.text);
  const overlayCenter = (Number(overlay.start) + Number(overlay.end)) / 2;
  let bestSegment = retainedTranscriptSegments[0];
  let bestScore = Number.NEGATIVE_INFINITY;

  for (const segment of retainedTranscriptSegments) {
    const segmentText = comparableCaptionText(segment.text);
    let textScore = 0;
    if (overlayText && segmentText) {
      if (overlayText === segmentText) {
        textScore = 4;
      } else if (
        overlayText.includes(segmentText) ||
        segmentText.includes(overlayText)
      ) {
        textScore =
          3 +
          Math.min(overlayText.length, segmentText.length) /
            Math.max(overlayText.length, segmentText.length);
      } else {
        const overlayCharacters = new Set(overlayText);
        const commonCharacters = [...overlayCharacters].filter((character) =>
          segmentText.includes(character),
        ).length;
        textScore =
          commonCharacters /
          Math.max(overlayCharacters.size, segmentText.length);
      }
    }
    const segmentCenter = (Number(segment.start) + Number(segment.end)) / 2;
    const proximityScore =
      1 -
      Math.min(
        1,
        Math.abs(segmentCenter - overlayCenter) / Math.max(duration, 0.1),
      );
    const score = textScore * 10 + proximityScore;
    if (score > bestScore) {
      bestScore = score;
      bestSegment = segment;
    }
  }
  return bestSegment;
}

function fitSelectedArtTimeToTranscript() {
  const overlay = selectedOverlay();
  if (!overlay) {
    showArtTimeFitMessage("请先选择一条艺术字。", "error");
    return;
  }
  const segment = matchingTranscriptSegment(overlay);
  if (!segment) {
    showArtTimeFitMessage("当前视频没有可匹配的文案片段。", "error");
    return;
  }
  const range = normalizeOverlayRange(segment.start, segment.end);
  Object.assign(overlay, range, {
    sourceStart: Number.isFinite(Number(segment.sourceStart))
      ? Number(segment.sourceStart)
      : overlay.sourceStart,
    sourceEnd: Number.isFinite(Number(segment.sourceEnd))
      ? Number(segment.sourceEnd)
      : overlay.sourceEnd,
  });
  if (
    !Number.isFinite(Number(segment.sourceStart)) ||
    !Number.isFinite(Number(segment.sourceEnd))
  ) {
    anchorOverlayToSourceTimeline(
      overlay,
      appliedCutDraftState || pendingCutDraft,
      true,
    );
  }
  seekEditorPreview(range.start);
  renderEditor();
  showArtTimeFitMessage(
    `已贴合文案“${String(segment.text).trim()}”：${formatRange(range.start, range.end)}。`,
    "success",
  );
}

function updateSelectedOverlay(changes, options = {}) {
  const overlay = selectedOverlay();
  if (!overlay) return;
  showArtTimeFitMessage("");
  showApplyAllSettingsMessage("");
  if (isTranscriptTrackOverlay(overlay)) {
    const sharedChanges = Object.fromEntries(
      Object.entries(changes).filter(([key]) =>
        TRANSCRIPT_TRACK_STYLE_KEYS.has(key),
      ),
    );
    for (const target of transcriptTrackOverlays(overlay.trackId)) {
      Object.assign(target, sharedChanges, {
        direction: "horizontal",
        charsPerLine: 0,
      });
    }
  } else {
    Object.assign(overlay, changes);
    if (Object.hasOwn(changes, "start") || Object.hasOwn(changes, "end")) {
      anchorOverlayToSourceTimeline(
        overlay,
        appliedCutDraftState || pendingCutDraft,
        true,
      );
    }
  }
  if (options.seek) seekEditorPreview(overlay.start);
  renderOverlayList();
  renderPreview();
}

function applySelectedSettingsToAllOverlays() {
  const source = selectedOverlay();
  const manualItems = overlays.filter(
    (overlay) => !isTranscriptTrackOverlay(overlay),
  );
  if (
    !source ||
    isTranscriptTrackOverlay(source) ||
    manualItems.length < 2
  ) {
    return;
  }
  const sharedSettings = {
    font: source.font,
    fontSize: source.fontSize,
    color: source.color,
    strokeColor: source.strokeColor,
    strokeWidth: source.strokeWidth,
    shadow: source.shadow,
    x: source.x,
    y: source.y,
    direction: source.direction,
    textAlign: source.textAlign,
    charsPerLine: source.charsPerLine,
    letterSpacing: source.letterSpacing,
    lineSpacing: source.lineSpacing,
    artStyle: source.artStyle,
  };

  for (const overlay of manualItems) {
    if (overlay.id !== source.id) Object.assign(overlay, sharedSettings);
  }
  renderEditor();
  showApplyAllSettingsMessage(
    `已将当前设置应用到其余 ${manualItems.length - 1} 条自定义艺术字，文案和时间保持不变。`,
  );
}

function retainedSegmentKey(segment) {
  return [
    Number(segment.start || 0).toFixed(3),
    Number(segment.end || 0).toFixed(3),
    String(segment.text || "").trim(),
  ].join("|");
}

function isRetainedSegmentAdded(segment) {
  if (currentTranscriptTrack().length > 0) return true;
  const text = String(segment.text || "").trim();
  const { start, end } = normalizeOverlayRange(segment.start, segment.end);
  return overlays.some(
    (overlay) =>
      String(overlay.text || "").trim() === text &&
      Math.abs(Number(overlay.start) - start) < 0.05 &&
      Math.abs(Number(overlay.end) - end) < 0.05,
  );
}

function selectableRetainedSegments() {
  if (
    currentTranscriptTrack().length > 0 ||
    manualOverlayCount() >= MANUAL_OVERLAY_LIMIT
  ) {
    return [];
  }
  return retainedTranscriptSegments.filter(
    (segment) => !isRetainedSegmentAdded(segment),
  );
}

function showRetainedBulkMessage(message, tone = "success") {
  retainedBulkMessage.textContent = message;
  retainedBulkMessage.dataset.tone = tone;
  retainedBulkMessage.hidden = !message;
}

function updateRetainedBulkControls() {
  const trackItems = currentTranscriptTrack();
  const selectable = selectableRetainedSegments();
  const selectableKeys = new Set(selectable.map(retainedSegmentKey));
  selectedRetainedSegmentKeys = new Set(
    [...selectedRetainedSegmentKeys].filter((key) => selectableKeys.has(key)),
  );
  const selectedCount = selectedRetainedSegmentKeys.size;
  const allSelected =
    selectable.length > 0 && selectedCount === selectable.length;
  selectAllRetainedSegments.disabled =
    transcriptTrackBusy || selectable.length === 0;
  selectAllRetainedSegments.checked = allSelected;
  selectAllRetainedSegments.indeterminate =
    selectedCount > 0 && !allSelected;
  retainedSelectionStatus.textContent = trackItems.length
    ? `全文轨道已覆盖全部文案 · ${trackItems.length} 个语义片段`
    : `已选 ${selectedCount} / ${selectable.length} · 还可加 ${Math.max(
        0,
        MANUAL_OVERLAY_LIMIT - manualOverlayCount(),
      )}`;
  addSelectedRetainedSegments.disabled =
    transcriptTrackBusy || selectedCount === 0;
  addSelectedRetainedSegments.textContent = `添加所选（${selectedCount}）`;
  addAllRetainedSegments.disabled =
    transcriptTrackBusy ||
    trackItems.length > 0 ||
    retainedTranscriptSegments.length === 0 ||
    (embeddedEditor && !currentCutDraftTranscript()) ||
    !availableArtTemplateIds.has(TRANSCRIPT_TRACK_DEFAULT_STYLE);
  addAllRetainedSegments.textContent = transcriptTrackBusy
    ? "正在生成视频文案…"
    : trackItems.length > 0
      ? "视频文案已添加"
      : "一键添加视频文案";
  generateArtVideo.disabled = transcriptTrackBusy || overlays.length === 0;
  updateTranscriptStyleButtons();
  window.queueMicrotask(notifyEditorHost);
}

function comparableTranscriptEditorText(value) {
  return String(value || "").replace(/\s+/g, "");
}

function showRetainedEditStatus(message, tone = "") {
  retainedEditStatus.textContent = message;
  retainedEditStatus.dataset.tone = tone;
  retainedEditStatus.hidden = !message;
}

function updateRetainedEditControls() {
  const current = comparableTranscriptEditorText(retainedText.value);
  const saved = comparableTranscriptEditorText(retainedSavedText);
  saveRetainedText.disabled = transcriptSaveBusy || !current || current === saved;
  saveRetainedText.textContent = transcriptSaveBusy ? "正在保存…" : "保存修改";
}

function renderRetainedSegmentList() {
  retainedSegments.replaceChildren();
  const remainingCapacity = Math.max(
    0,
    MANUAL_OVERLAY_LIMIT - manualOverlayCount(),
  );

  for (const segment of retainedTranscriptSegments) {
    const key = retainedSegmentKey(segment);
    const alreadyAdded = isRetainedSegmentAdded(segment);
    const item = document.createElement("li");
    item.className = "retained-segment";
    item.classList.toggle("is-selected", selectedRetainedSegmentKeys.has(key));
    item.classList.toggle("is-added", alreadyAdded);

    const selectionLabel = document.createElement("label");
    selectionLabel.className = "retained-segment-check";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selectedRetainedSegmentKeys.has(key);
    checkbox.disabled = alreadyAdded || remainingCapacity === 0;
    checkbox.setAttribute(
      "aria-label",
      `选择文案：${String(segment.text || "").trim()}`,
    );
    checkbox.addEventListener("change", () => {
      showRetainedBulkMessage("");
      if (checkbox.checked) {
        selectedRetainedSegmentKeys.add(key);
      } else {
        selectedRetainedSegmentKeys.delete(key);
      }
      item.classList.toggle("is-selected", checkbox.checked);
      updateRetainedBulkControls();
    });
    selectionLabel.append(checkbox);

    const time = document.createElement("time");
    const text = document.createElement("p");
    const button = document.createElement("button");
    time.textContent = formatRange(segment.start, segment.end);
    text.textContent = segment.text;
    button.type = "button";
    button.disabled = alreadyAdded || remainingCapacity === 0;
    button.textContent = alreadyAdded
      ? currentTranscriptTrack().length
        ? "已由全文轨道覆盖"
        : "已添加"
      : "添加为艺术字";
    button.addEventListener("click", () => {
      showRetainedBulkMessage("");
      const overlay = createOverlay(
        segment.text,
        segment.start,
        segment.end,
        {
          sourceStart: segment.sourceStart,
          sourceEnd: segment.sourceEnd,
        },
      );
      if (!overlay) return;
      selectedRetainedSegmentKeys.delete(key);
      renderRetainedSegmentList();
      revealSettingsPanel();
    });
    item.append(selectionLabel, time, text, button);
    retainedSegments.append(item);
  }
  updateRetainedBulkControls();
}

function renderRetainedTranscript(transcript) {
  retainedTranscriptSegments = (transcript?.segments || [])
    .filter((segment) => String(segment.text || "").trim())
    .map((segment) => ({ ...segment }));
  selectedRetainedSegmentKeys = new Set();
  retainedSavedText = transcript?.text || "";
  retainedText.value = retainedSavedText;
  retainedText.placeholder = "剪后暂无可显示的识别文字。";
  retainedMeta.textContent =
    `${retainedTranscriptSegments.length} 段 · ${formatTime(duration)}`;
  showRetainedEditStatus("");
  updateRetainedEditControls();
  renderRetainedSegmentList();
}

function addRetainedSegmentsAsOverlays(segments) {
  const candidates = segments.filter(
    (segment) => !isRetainedSegmentAdded(segment),
  );
  const capacity = Math.max(
    0,
    MANUAL_OVERLAY_LIMIT - manualOverlayCount(),
  );
  const additions = candidates.slice(0, capacity);
  let addedCount = 0;

  for (const segment of additions) {
    if (
      createOverlay(
        segment.text,
        segment.start,
        segment.end,
        {
          sourceStart: segment.sourceStart,
          sourceEnd: segment.sourceEnd,
        },
        { deferRender: true },
      )
    ) {
      addedCount += 1;
    }
  }
  selectedRetainedSegmentKeys.clear();
  if (addedCount === 0) {
    showRetainedBulkMessage(
      capacity === 0
        ? `一个视频最多添加 ${MANUAL_OVERLAY_LIMIT} 条自定义艺术字。`
        : "所选文案均已添加为艺术字。",
      "warning",
    );
    renderRetainedSegmentList();
    return;
  }

  const selected = selectedOverlay();
  if (selected) seekEditorPreview(selected.start);
  if (additions.length < candidates.length) {
    showRetainedBulkMessage(
      `已添加 ${addedCount} 条，达到 ${MANUAL_OVERLAY_LIMIT} 条自定义艺术字上限，其余文案未添加。`,
      "warning",
    );
  } else {
    showRetainedBulkMessage(
      `已将 ${addedCount} 条文案添加为艺术字，可在“艺术字设置”中统一检查和调整。`,
    );
  }
  renderEditor();
  renderRetainedSegmentList();
}

async function addFullTranscriptTrack() {
  if (transcriptTrackBusy || currentTranscriptTrack().length > 0) return;
  if (embeddedEditor && !currentCutDraftTranscript()) {
    requestLatestEditorCutDraft();
    showRetainedBulkMessage(
      "正在读取当前剪后文案，请稍候再试。不会使用剪辑前的旧文案。",
      "warning",
    );
    updateRetainedBulkControls();
    return;
  }
  if (!availableArtTemplateIds.has(TRANSCRIPT_TRACK_DEFAULT_STYLE)) {
    showRetainedBulkMessage(
      "默认的“热血立体”艺术字暂不可用，请刷新后重试。",
      "warning",
    );
    updateRetainedBulkControls();
    return;
  }
  const selected = selectedOverlay();
  const selectedStyle = TRANSCRIPT_TRACK_DEFAULT_STYLE;
  transcriptTrackTemplateId = selectedStyle;
  const palette = ART_STYLE_PALETTES[selectedStyle];
  const chosenTemplateSettings =
    preferredArtTemplateSettings.id === selectedStyle
      ? preferredArtTemplateSettings
      : {};
  const sharedStyle = {
    font:
      chosenTemplateSettings.font ||
      selected?.font ||
      preferredArtFontId ||
      "bold",
    fontSize:
      Number(chosenTemplateSettings.fontSize) ||
      Number(selected?.fontSize) ||
      54,
    color:
      chosenTemplateSettings.color ||
      palette.color,
    strokeColor:
      chosenTemplateSettings.strokeColor ||
      palette.strokeColor,
    strokeWidth: Number.isFinite(Number(selected?.strokeWidth))
      ? Number(selected.strokeWidth)
      : 3,
    shadow: selected?.shadow ?? true,
    x: TRANSCRIPT_TRACK_DEFAULT_POSITION.x,
    y: TRANSCRIPT_TRACK_DEFAULT_POSITION.y,
    direction: "horizontal",
    textAlign: "center",
    charsPerLine: 0,
    letterSpacing: Number(selected?.letterSpacing) || 0,
    lineSpacing: 0,
    artStyle: selectedStyle,
  };

  const cutTranscript = currentCutDraftTranscript();
  if (cutTranscript) {
    transcriptTrackBusy = true;
    updateRetainedBulkControls();
    const created = replaceTranscriptTrackFromCutDraft(
      null,
      sharedStyle,
      pendingCutDraft,
    );
    transcriptTrackBusy = false;
    if (!created.length) {
      showRetainedBulkMessage(
        "当前剪后文案缺少可用的词级时间，无法生成全文艺术字。",
        "warning",
      );
      updateRetainedBulkControls();
      return;
    }
    seekEditorPreview(created[0].start);
    selectedRetainedSegmentKeys.clear();
    showRetainedBulkMessage(
      `已直接使用当前剪后文案和词级时间生成 ${created.length} 个艺术字片段。`,
    );
    renderEditor();
    renderRetainedSegmentList();
    revealSettingsPanel();
    return;
  }

  transcriptTrackBusy = true;
  const requestDraftVersion = transcriptTrackDraftVersion;
  const requestPayload = transcriptTrackRequestPayload(sharedStyle);
  showRetainedBulkMessage(
    `AI 正在使用“${selectedTranscriptTemplateName()}”生成统一字号字幕…`,
  );
  updateRetainedBulkControls();
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/art-text/transcript-track`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload),
      },
    );
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "无法生成全文单行艺术字轨道。");
    }
    if (requestDraftVersion !== transcriptTrackDraftVersion) {
      window.setTimeout(addFullTranscriptTrack, 0);
      return;
    }

    const created = [];
    for (const cue of result.cues || []) {
      const overlay = createOverlay(
        cue.text,
        cue.start,
        cue.end,
        {
          ...sharedStyle,
          fontSize: result.fontSize,
          trackId: result.trackId,
          trackType: result.trackType,
          sourceStart: cue.sourceStart,
          sourceEnd: cue.sourceEnd,
        },
        { deferRender: true },
      );
      if (overlay) created.push(overlay);
    }
    if (created.length !== Number(result.cueCount)) {
      overlays = overlays.filter(
        (overlay) => overlay.trackId !== result.trackId,
      );
      throw new Error("全文轨道片段未完整写入，请重新生成。");
    }

    selectedOverlayId = created[0].id;
    seekEditorPreview(created[0].start);
    selectedRetainedSegmentKeys.clear();
    const segmentationLabel =
      result.segmentationMethod === "ai"
        ? `AI 已使用 ${result.segmentationModel || "语义模型"} 完成分句`
        : "AI 暂时不可用，已使用自然停顿规则安全分句";
    showRetainedBulkMessage(
      `${segmentationLabel}，共生成 ${created.length} 个单行片段。` +
        `每行最多 10 字，全部保持 ${result.fontSize} 号字。`,
    );
    renderEditor();
    renderRetainedSegmentList();
    revealSettingsPanel();
  } catch (error) {
    showRetainedBulkMessage(error.message, "warning");
  } finally {
    transcriptTrackBusy = false;
    updateRetainedBulkControls();
  }
}

function transcriptTrackRequestPayload(sharedStyle) {
  const payload = {
    source: videoSource,
    font: sharedStyle.font,
    fontSize: sharedStyle.fontSize,
    letterSpacing: sharedStyle.letterSpacing,
    strokeWidth: sharedStyle.strokeWidth,
  };
  const cutTranscript = pendingCutDraft?.transcript;
  if (Array.isArray(cutTranscript?.segments) && cutTranscript.segments.length) {
    payload.draftTranscript = cutTranscript;
    payload.draftDuration = Math.max(
      0.001,
      Number(pendingCutDraft.duration) || duration,
    );
  } else if (retainedTranscriptSegments.length) {
    payload.draftTranscript = {
      text: retainedSavedText,
      segments: retainedTranscriptSegments,
    };
    payload.draftDuration = duration;
  }
  return payload;
}

function scheduleTranscriptTrackRefresh() {
  window.clearTimeout(transcriptTrackRefreshTimer);
  if (!currentTranscriptTrack().length) return;
  transcriptTrackRefreshTimer = window.setTimeout(async () => {
    transcriptTrackRefreshTimer = null;
    if (transcriptTrackBusy) {
      scheduleTranscriptTrackRefresh();
      return;
    }
    await rebuildTranscriptTrackLayout({ liveSync: true });
  }, 240);
}

async function rebuildTranscriptTrackLayout(options = {}) {
  const selected = selectedOverlay();
  const trackSeed = isTranscriptTrackOverlay(selected)
    ? selected
    : currentTranscriptTrack()[0];
  if (!isTranscriptTrackOverlay(trackSeed) || transcriptTrackBusy) return false;
  const previousSelectedId = selected?.id || selectedOverlayId;
  const existingTrack = transcriptTrackOverlays(trackSeed.trackId);
  if (!existingTrack.length) return false;

  const sharedStyle = transcriptTrackSharedStyle(trackSeed);
  if (currentCutDraftTranscript()) {
    const created = replaceTranscriptTrackFromCutDraft(
      trackSeed,
      sharedStyle,
      pendingCutDraft,
    );
    if (!created.length) {
      showRetainedBulkMessage(
        "当前剪后文案缺少可用的词级时间，全文艺术字保持原状。",
        "warning",
      );
      return false;
    }
    showRetainedBulkMessage(
      `已按当前剪后文案即时重排，共 ${created.length} 个艺术字片段。`,
    );
    renderEditor();
    renderRetainedSegmentList();
    return true;
  }
  const previousIds = new Set(existingTrack.map((overlay) => overlay.id));
  const created = [];
  transcriptTrackBusy = true;
  const requestDraftVersion = transcriptTrackDraftVersion;
  const requestPayload = transcriptTrackRequestPayload(sharedStyle);
  showRetainedBulkMessage(
    options.liveSync
      ? "剪辑方案已更新，正在同步全文艺术字内容和时间…"
      : `正在保持语义边界，并按每行最多 10 字、${sharedStyle.fontSize} 号字重排…`,
  );
  updateRetainedBulkControls();
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/art-text/transcript-track`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload),
      },
    );
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "无法根据字号重新整理全文轨道。");
    }
    if (requestDraftVersion !== transcriptTrackDraftVersion) {
      scheduleTranscriptTrackRefresh();
      return false;
    }

    for (const cue of result.cues || []) {
      const overlay = createOverlay(
        cue.text,
        cue.start,
        cue.end,
        {
          ...sharedStyle,
          fontSize: result.fontSize,
          trackId: result.trackId,
          trackType: result.trackType,
          sourceStart: cue.sourceStart,
          sourceEnd: cue.sourceEnd,
        },
        { deferRender: true },
      );
      if (overlay) created.push(overlay);
    }
    if (!created.length || created.length !== Number(result.cueCount)) {
      throw new Error("字号重排后的全文轨道未完整写入，请重试。");
    }

    overlays = overlays.filter((overlay) => !previousIds.has(overlay.id));
    const activeCue = activeTrackCue(created, previewPlaybackTime());
    selectedOverlayId = activeCue?.id || created[0].id;
    const segmentationLabel =
      result.segmentationMethod === "ai" ? "AI 语义分句" : "自然分句";
    showRetainedBulkMessage(
      options.liveSync
        ? `已按当前剪后文案实时同步，共 ${created.length} 个艺术字片段。`
        : `已保持 ${result.fontSize} 号字、每行最多 10 字和${segmentationLabel}，` +
            `共 ${created.length} 个单行片段。`,
    );
    renderEditor();
    renderRetainedSegmentList();
    return true;
  } catch (error) {
    const createdIds = new Set(created.map((overlay) => overlay.id));
    overlays = overlays.filter((overlay) => !createdIds.has(overlay.id));
    selectedOverlayId = previousSelectedId;
    showRetainedBulkMessage(error.message, "warning");
    renderEditor();
    return false;
  } finally {
    transcriptTrackBusy = false;
    updateRetainedBulkControls();
  }
}

async function saveRetainedTranscript() {
  if (transcriptSaveBusy) return;
  const nextText = retainedText.value.trim();
  if (!nextText) {
    showRetainedEditStatus("视频文案不能为空。", "warning");
    retainedText.focus();
    return;
  }
  if (
    comparableTranscriptEditorText(nextText) ===
    comparableTranscriptEditorText(retainedSavedText)
  ) {
    showRetainedEditStatus("当前文案没有未保存的修改。");
    updateRetainedEditControls();
    return;
  }

  const existingTrack = currentTranscriptTrack();
  transcriptSaveBusy = true;
  showRetainedEditStatus("正在保存文案并对齐原时间轴…");
  updateRetainedEditControls();
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/transcript`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: nextText }),
      },
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "无法保存修改后的视频文案。");
    }

    job.result = payload.result;
    if (videoSource === "edited" && job.edit) {
      job.edit.transcript = payload.editTranscript;
    }
    job.art = null;
    job.artSuggestion = null;
    artResult.hidden = true;
    const transcript =
      videoSource === "edited" ? payload.editTranscript : payload.result;
    if (!transcript) {
      throw new Error("修改后的文案无法对齐当前剪辑视频。");
    }
    renderRetainedTranscript(transcript);

    if (existingTrack.length > 0) {
      selectedOverlayId = existingTrack[0].id;
      const rebuilt = await rebuildTranscriptTrackLayout();
      showRetainedEditStatus(
        rebuilt
          ? `已保存 ${payload.changedWords} 个词块的修改，并同步更新全文艺术字。`
          : "文案已保存，但全文艺术字同步失败，请重新生成全文轨道。",
        rebuilt ? "" : "warning",
      );
    } else {
      showRetainedEditStatus(
        `已保存 ${payload.changedWords} 个词块的修改，一键生成将使用新文案。`,
      );
    }
  } catch (error) {
    showRetainedEditStatus(error.message, "warning");
  } finally {
    transcriptSaveBusy = false;
    updateRetainedEditControls();
  }
}

function showAiSuggestionError(message) {
  aiSuggestionError.textContent = message;
  aiSuggestionError.hidden = !message;
}

function updateAiSuggestionLimit() {
  const remaining = Math.max(
    0,
    MANUAL_OVERLAY_LIMIT - manualOverlayCount(),
  );
  aiSuggestionLimit.textContent =
    remaining > 0
      ? `最多还可新增 ${remaining} 条`
      : "已达到 20 条艺术字上限";
  aiSuggestionCount.max = String(Math.max(1, remaining));
  const requested = Number(aiSuggestionCount.value);
  if (remaining > 0 && Number.isFinite(requested) && requested > remaining) {
    aiSuggestionCount.value = String(remaining);
  }
  const hasPendingDraft = aiDraftSuggestions.length > 0;
  aiSuggestionCount.disabled = aiSuggestionBusy || remaining === 0 || hasPendingDraft;
  generateAiSuggestions.disabled =
    aiSuggestionBusy || remaining === 0 || hasPendingDraft;
}

function setAiSuggestionProgress(value, message) {
  const progress = clamp(Math.round(Number(value) || 0), 0, 100);
  aiSuggestionProgressBar.style.width = `${progress}%`;
  aiSuggestionProgressTrack.setAttribute("aria-valuenow", String(progress));
  aiSuggestionProgressPercent.textContent = `${progress}%`;
  aiSuggestionStatus.textContent = message || "正在分析视频内容…";
}

function getSourceSuggestion(suggestion) {
  if (!suggestion) return null;
  return (suggestion.source || "edited") === videoSource ? suggestion : null;
}

function updateAiReviewSummary() {
  const acceptedCount = aiDraftSuggestions.filter((item) => item.accepted).length;
  aiSuggestionReviewCount.textContent =
    `${acceptedCount} / ${aiDraftSuggestions.length} 条待添加`;
  confirmAiSuggestions.disabled =
    aiSuggestionBusy ||
    acceptedCount === 0 ||
    acceptedCount + manualOverlayCount() > MANUAL_OVERLAY_LIMIT;
  updateAiSuggestionLimit();
}

function createAiField(labelText, control, className = "") {
  const label = document.createElement("label");
  label.className = `field ai-suggestion-field ${className}`.trim();
  const labelTextElement = document.createElement("span");
  labelTextElement.textContent = labelText;
  label.append(labelTextElement, control);
  return label;
}

function renderAiSuggestionReview() {
  aiSuggestionList.replaceChildren();
  aiSuggestionReview.hidden = aiDraftSuggestions.length === 0;
  if (aiDraftSuggestions.length === 0) {
    previewDraftId = null;
    renderPreview();
    renderFrameTimelineOverlaySegments();
    updateAiSuggestionLimit();
    return;
  }

  for (const [index, suggestion] of aiDraftSuggestions.entries()) {
    const item = document.createElement("li");
    item.className = "ai-suggestion-card";
    item.classList.toggle("is-previewing", suggestion.draftId === previewDraftId);

    const heading = document.createElement("div");
    heading.className = "ai-suggestion-card-heading";
    const adoptionLabel = document.createElement("label");
    adoptionLabel.className = "ai-adoption-toggle";
    const adoptionCheckbox = document.createElement("input");
    adoptionCheckbox.type = "checkbox";
    adoptionCheckbox.checked = suggestion.accepted;
    const adoptionText = document.createElement("span");
    adoptionText.textContent = `采用第 ${index + 1} 条`;
    adoptionLabel.append(adoptionCheckbox, adoptionText);
    const timeBadge = document.createElement("span");
    timeBadge.className = "result-chip";
    timeBadge.textContent = formatRange(suggestion.start, suggestion.end);
    heading.append(adoptionLabel, timeBadge);

    const fields = document.createElement("div");
    fields.className = "ai-suggestion-fields";

    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.maxLength = 60;
    textInput.value = suggestion.text;
    fields.append(createAiField("艺术字文案", textInput, "ai-text-field"));

    const startInput = document.createElement("input");
    startInput.type = "number";
    startInput.min = "0";
    startInput.max = Math.max(0, duration - 0.1).toFixed(1);
    startInput.step = "0.1";
    startInput.value = suggestion.start.toFixed(1);
    fields.append(createAiField("开始（秒）", startInput));

    const endInput = document.createElement("input");
    endInput.type = "number";
    endInput.min = "0.1";
    endInput.max = duration.toFixed(1);
    endInput.step = "0.1";
    endInput.value = suggestion.end.toFixed(1);
    fields.append(createAiField("结束（秒）", endInput));

    const positionSelect = document.createElement("select");
    for (const [value, label] of Object.entries(AI_POSITION_LABELS)) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      positionSelect.append(option);
    }
    positionSelect.value = suggestion.position;
    fields.append(createAiField("画面位置", positionSelect));

    const styleSelect = document.createElement("select");
    for (const [value, label] of Object.entries(AI_STYLE_LABELS)) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      styleSelect.append(option);
    }
    styleSelect.value = suggestion.artStyle;
    fields.append(createAiField("艺术字模板", styleSelect));

    const reason = document.createElement("p");
    reason.className = "ai-suggestion-reason";
    reason.textContent = suggestion.reason || "AI 已结合内容重点和画面留白推荐。";

    const previewButton = document.createElement("button");
    previewButton.type = "button";
    previewButton.className = "secondary-button compact-button ai-preview-button";
    previewButton.textContent =
      suggestion.draftId === previewDraftId ? "正在预览" : "在视频中预览";

    adoptionCheckbox.addEventListener("change", () => {
      suggestion.accepted = adoptionCheckbox.checked;
      item.classList.toggle("is-rejected", !suggestion.accepted);
      updateAiReviewSummary();
    });
    textInput.addEventListener("input", () => {
      suggestion.text = textInput.value;
      renderPreview();
    });
    startInput.addEventListener("change", () => {
      suggestion.start = clamp(
        Number(startInput.value) || 0,
        0,
        Math.max(0, suggestion.end - 0.1),
      );
      startInput.value = suggestion.start.toFixed(1);
      timeBadge.textContent = formatRange(suggestion.start, suggestion.end);
      seekEditorPreview(suggestion.start);
      renderPreview();
    });
    endInput.addEventListener("change", () => {
      suggestion.end = clamp(
        Number(endInput.value) || suggestion.start + 0.1,
        suggestion.start + 0.1,
        duration,
      );
      endInput.value = suggestion.end.toFixed(1);
      timeBadge.textContent = formatRange(suggestion.start, suggestion.end);
      renderPreview();
    });
    positionSelect.addEventListener("change", () => {
      suggestion.position = positionSelect.value;
      Object.assign(suggestion, AI_POSITION_VALUES[positionSelect.value]);
      renderPreview();
    });
    styleSelect.addEventListener("change", () => {
      suggestion.artStyle = styleSelect.value;
      Object.assign(suggestion, ART_STYLE_PALETTES[styleSelect.value]);
      renderPreview();
    });
    previewButton.addEventListener("click", () => {
      previewDraftId = suggestion.draftId;
      seekEditorPreview(suggestion.start);
      renderAiSuggestionReview();
      renderPreview();
    });

    item.classList.toggle("is-rejected", !suggestion.accepted);
    item.append(heading, fields, reason, previewButton);
    aiSuggestionList.append(item);
  }
  renderFrameTimelineOverlaySegments();
  updateAiReviewSummary();
}

function loadAiDraftSuggestions(items) {
  aiDraftSuggestions = (items || []).map((item, index) => ({
    ...item,
    draftId: `ai-draft-${Date.now()}-${index}`,
    accepted: true,
  }));
  previewDraftId = aiDraftSuggestions[0]?.draftId || null;
  if (aiDraftSuggestions[0]) {
    seekEditorPreview(aiDraftSuggestions[0].start);
  }
  renderAiSuggestionReview();
  renderPreview();
}

function renderAiSuggestionJob(suggestion) {
  if (!suggestion) return;
  if (["queued", "processing"].includes(suggestion.status)) {
    aiSuggestionBusy = true;
    aiSuggestionProgress.hidden = false;
    aiSuggestionReview.hidden = true;
    showAiSuggestionError("");
    setAiSuggestionProgress(suggestion.progress, suggestion.stage);
    updateAiSuggestionLimit();
    return;
  }

  aiSuggestionBusy = false;
  aiSuggestionProgress.hidden = true;
  if (suggestion.status === "completed") {
    showAiSuggestionError("");
    loadAiDraftSuggestions(suggestion.suggestions);
    aiSuggestionReview.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } else if (suggestion.status === "failed") {
    showAiSuggestionError(
      suggestion.error || "AI 艺术字分析失败，请重新尝试。",
    );
    updateAiSuggestionLimit();
  }
}

async function pollAiSuggestionJob() {
  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法读取 AI 分析进度。");
    job = payload;
    const suggestion = getSourceSuggestion(payload.artSuggestion);
    if (!suggestion) throw new Error("AI 艺术字草稿已失效，请重新分析。");
    renderAiSuggestionJob(suggestion);
    if (["queued", "processing"].includes(suggestion.status)) {
      aiPollTimer = window.setTimeout(pollAiSuggestionJob, 1200);
    }
  } catch (error) {
    aiSuggestionBusy = false;
    aiSuggestionProgress.hidden = true;
    showAiSuggestionError(error.message);
    updateAiSuggestionLimit();
  }
}

async function requestAiSuggestions() {
  if (cutDraftActive) {
    showAiSuggestionError(
      "请先生成剪辑视频再获取 AI 推荐；当前可从剪后文案直接添加艺术字。",
    );
    return;
  }
  const remaining = MANUAL_OVERLAY_LIMIT - manualOverlayCount();
  const count = Number(aiSuggestionCount.value);
  if (!Number.isInteger(count) || count < 1 || count > remaining) {
    showAiSuggestionError(`请输入 1–${Math.max(1, remaining)} 之间的整数。`);
    aiSuggestionCount.focus();
    return;
  }

  aiSuggestionBusy = true;
  showAiSuggestionError("");
  aiSuggestionReview.hidden = true;
  aiSuggestionProgress.hidden = false;
  setAiSuggestionProgress(5, "正在创建 AI 艺术字分析任务…");
  updateAiSuggestionLimit();

  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/art-text/suggestions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: videoSource,
          count,
          existingOverlays: overlays
            .filter((overlay) => !isTranscriptTrackOverlay(overlay))
            .map(({ id, ...overlay }) => overlay),
        }),
      },
    );
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "无法创建 AI 艺术字分析任务。");
    }
    renderAiSuggestionJob(result);
    pollAiSuggestionJob();
  } catch (error) {
    aiSuggestionBusy = false;
    aiSuggestionProgress.hidden = true;
    showAiSuggestionError(error.message);
    updateAiSuggestionLimit();
  }
}

async function clearAiSuggestionState() {
  try {
    await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/art-text/suggestions`,
      { method: "DELETE" },
    );
  } catch {
    // The local draft is already cleared; a stale server draft is harmless.
  }
}

function cancelAiSuggestionDrafts() {
  aiDraftSuggestions = [];
  previewDraftId = null;
  aiSuggestionList.replaceChildren();
  aiSuggestionReview.hidden = true;
  showAiSuggestionError("");
  renderPreview();
  renderFrameTimelineOverlaySegments();
  updateAiSuggestionLimit();
  clearAiSuggestionState();
}

function confirmAiSuggestionDrafts() {
  const accepted = aiDraftSuggestions.filter((item) => item.accepted);
  if (accepted.length === 0) {
    showAiSuggestionError("请至少勾选一条要添加的艺术字。");
    return;
  }
  if (
    accepted.length + manualOverlayCount() >
    MANUAL_OVERLAY_LIMIT
  ) {
    showAiSuggestionError("确认后的艺术字总数不能超过 20 条。");
    return;
  }
  for (const [index, item] of accepted.entries()) {
    if (!String(item.text || "").trim()) {
      showAiSuggestionError(`第 ${index + 1} 条草稿的文案不能为空。`);
      return;
    }
    if (item.end - item.start < 0.05) {
      showAiSuggestionError(`第 ${index + 1} 条草稿的结束时间必须晚于开始时间。`);
      return;
    }
  }

  aiDraftSuggestions = [];
  previewDraftId = null;
  aiSuggestionList.replaceChildren();
  for (const item of accepted) {
    createOverlay(item.text, item.start, item.end, item);
  }
  aiSuggestionReview.hidden = true;
  showAiSuggestionError("");
  renderEditor();
  clearAiSuggestionState();
  revealSettingsPanel();
}

function showFormError(message) {
  artFormError.textContent = message;
  artFormError.hidden = !message;
  window.queueMicrotask(notifyEditorHost);
}

function validateOverlays() {
  if (
    comparableTranscriptEditorText(retainedText.value) !==
    comparableTranscriptEditorText(retainedSavedText)
  ) {
    return "视频文案还有未保存的修改，请先保存文案。";
  }
  if (overlays.length === 0) return "请至少添加一条艺术字。";
  for (const [index, overlay] of overlays.entries()) {
    if (!overlay.text.trim()) return `第 ${index + 1} 条艺术字内容不能为空。`;
    const minimumDuration = isTranscriptTrackOverlay(overlay) ? 0.02 : 0.05;
    if (overlay.end - overlay.start < minimumDuration) {
      return `第 ${index + 1} 条艺术字的结束时间必须晚于开始时间。`;
    }
    if (overlay.start < 0 || overlay.end > duration + 0.01) {
      return `第 ${index + 1} 条艺术字的时间超出视频范围。`;
    }
  }
  const trackItems = currentTranscriptTrack().sort(
    (left, right) => left.start - right.start,
  );
  if (trackItems.length > 0) {
    if (
      trackItems.some(
        (overlay) =>
          overlay.direction !== "horizontal" ||
          overlay.charsPerLine !== 0 ||
          /[\r\n]/.test(overlay.text),
      )
    ) {
      return "全文艺术字轨道必须保持横向单行排版，请重新生成。";
    }
    if (
      trackItems.some(
        (overlay) =>
          transcriptCueTextLength(overlay.text) >
          TRANSCRIPT_TRACK_MAX_CHARS_PER_CUE,
      )
    ) {
      return "全文艺术字轨道每段最多 10 个字，请重新生成全文轨道。";
    }
    for (let index = 1; index < trackItems.length; index += 1) {
      if (trackItems[index].start < trackItems[index - 1].end - 0.001) {
        return "全文艺术字轨道存在重叠时间，请重新生成。";
      }
    }
    const trackText = comparableCaptionText(
      trackItems.map((overlay) => overlay.text).join(""),
    );
    const transcriptText = comparableCaptionText(
      retainedTranscriptSegments.map((segment) => segment.text).join(""),
    );
    if (!trackText || trackText !== transcriptText) {
      return "全文艺术字轨道与当前视频文案不一致。";
    }
  }
  return "";
}

function setArtProgress(value, message) {
  const progress = clamp(Math.round(Number(value) || 0), 0, 100);
  artProgressBar.style.width = `${progress}%`;
  artProgressTrack.setAttribute("aria-valuenow", String(progress));
  artProgressPercent.textContent = `${progress}%`;
  artStatus.textContent = message || "正在生成艺术字视频…";
}

function renderArtJob(art) {
  if (!art) return;
  if (["queued", "processing"].includes(art.status)) {
    artProgress.hidden = false;
    artResult.hidden = true;
    generateArtVideo.disabled = true;
    setArtProgress(art.progress, art.stage);
    if (!generationModalActive) {
      generationModalActive = true;
      window.appGeneration?.show({
        title: "生成艺术字视频",
        progress: art.progress,
        status: art.stage || "正在生成艺术字视频…",
        onClose: () => {
          generationModalActive = false;
        },
      });
    } else {
      window.appGeneration?.setProgress(art.progress, art.stage);
    }
    return;
  }

  generateArtVideo.disabled = overlays.length === 0;
  if (art.status === "completed") {
    artProgress.hidden = true;
    showFormError("");
    artResult.hidden = false;
    finalVideo.src = `${art.outputUrl}?v=${Date.now()}`;
    downloadFinalVideo.href = `${art.outputUrl}?download=true`;
    continuePictureInPicture.href =
      `/picture-in-picture?job=${encodeURIComponent(jobId)}&source=art`;
    artResultDuration.textContent = `成片 ${formatTime(art.outputDuration)}`;
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.complete({
        videoUrl: art.outputUrl,
        downloadUrl: `${art.outputUrl}?download=true`,
        duration: formatTime(art.outputDuration),
      });
    }
  } else if (art.status === "failed") {
    artProgress.hidden = true;
    showFormError(art.error || "艺术字视频生成失败，请重新尝试。");
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.fail(
        art.error || "艺术字视频生成失败，请重新尝试。",
      );
    }
  }
}

function getSourceArt(art) {
  if (!art) return null;
  return (art.source || "edited") === videoSource ? art : null;
}

async function pollArtJob() {
  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法读取生成进度。");
    job = payload;
    updateEditorSuiteJobState(payload);
    const art = getSourceArt(payload.art);
    renderArtJob(art);
    if (["queued", "processing"].includes(art?.status)) {
      pollTimer = window.setTimeout(pollArtJob, 1200);
    }
  } catch (error) {
    artProgress.hidden = true;
    generateArtVideo.disabled = overlays.length === 0;
    showFormError(error.message);
  }
}

async function generateVideo(composition = null) {
  const trackRefreshPending =
    transcriptTrackRefreshTimer !== null && currentTranscriptTrack().length > 0;
  if (trackRefreshPending) {
    window.clearTimeout(transcriptTrackRefreshTimer);
    transcriptTrackRefreshTimer = null;
  }
  let validationError = validateOverlays();
  if (
    trackRefreshPending ||
    validationError === "全文艺术字轨道每段最多 10 个字，请重新生成全文轨道。" ||
    validationError === "全文艺术字轨道存在重叠时间，请重新生成。" ||
    validationError === "全文艺术字轨道与当前视频文案不一致。"
  ) {
    showFormError("正在自动整理全文艺术字的内容和时间…");
    const rebuilt = await rebuildTranscriptTrackLayout();
    if (!rebuilt) {
      showFormError(validationError);
      return;
    }
    validationError = validateOverlays();
  }
  if (validationError) {
    showFormError(validationError);
    return;
  }

  showFormError("");
  artResult.hidden = true;
  artProgress.hidden = false;
  generateArtVideo.disabled = true;
  setArtProgress(5, "正在创建艺术字合成任务…");

  const payload = {
    source: videoSource,
    historyName: artHistoryName.value.trim() || null,
    overlays: overlays.map(({ id, ...overlay }) => overlay),
  };
  const compositionRanges = Array.isArray(composition?.ranges)
    ? composition.ranges
    : Array.isArray(pendingCutDraft?.ranges)
      ? pendingCutDraft.ranges
      : Array.isArray(job?.edit?.requestedRanges)
        ? job.edit.requestedRanges
      : [];
  const useComposition =
    compositionRanges.length > 0 &&
    (cutDraftActive || Boolean(composition) || Boolean(job?.edit?.composition));
  const endpoint = useComposition ? "compose" : "art-text";
  const requestPayload = useComposition
    ? {
        target: "art",
        ranges: compositionRanges,
        artOverlays: payload.overlays,
        artSource: videoSource,
        historyName: payload.historyName,
      }
    : payload;
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/${endpoint}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload),
      },
    );
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "无法创建艺术字视频。");
    renderArtJob(result);
    pollArtJob();
  } catch (error) {
    artProgress.hidden = true;
    generateArtVideo.disabled = false;
    showFormError(error.message);
  }
}

async function initialize() {
  if (!JOB_ID_PATTERN.test(jobId)) {
    showPageError("链接中缺少有效的视频任务，请先上传视频。");
    return;
  }
  const editUrl = `/?job=${encodeURIComponent(jobId)}`;
  brandLink.href = editUrl;
  backToEdit.href = editUrl;
  templateLibraryLink.href =
    `/fonts?job=${encodeURIComponent(jobId)}` +
    `&source=${encodeURIComponent(videoSource)}`;

  try {
    await loadFontLibrary();
  } catch {
    availableFontIds = new Set(BUILTIN_FONT_IDS);
    preferredArtFontId = "bold";
  }
  try {
    await loadArtTemplateLibrary();
  } catch {
    availableArtTemplateIds = new Set(Object.keys(ART_STYLE_PALETTES));
    renderTranscriptStyleGrid(fallbackTemplatesFromStyleButtons());
  }

  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "无法读取视频信息。");
    if (payload.status !== "completed") {
      throw new Error("请等待文字识别完成后再添加艺术字。");
    }
    if (videoSource === "original" && payload.edit?.status) {
      throw new Error("该视频已经进入剪辑流程，请使用剪辑后的视频添加艺术字。");
    }
    if (videoSource === "edited" && payload.edit?.status !== "completed") {
      throw new Error("请先完成视频剪辑，再添加艺术字。");
    }

    job = payload;
    updateEditorSuiteJobState(payload);
    const originalVideoUrl =
      `/api/transcriptions/${encodeURIComponent(jobId)}/original-video`;
    const videoUrl =
      videoSource === "original" ? originalVideoUrl : payload.edit.outputUrl;
    const transcript =
      videoSource === "original" ? payload.result : payload.edit.transcript;
    duration =
      Number(
        videoSource === "original"
          ? payload.duration
          : payload.edit.outputDuration,
      ) || 0;
    directDownload.textContent =
      videoSource === "original" ? "直接下载原视频" : "直接下载剪辑视频";
    directDownload.href = `${videoUrl}?download=true`;
    artVideo.src = `${videoUrl}?v=${Date.now()}`;
    renderRetainedTranscript(transcript);
    const art = getSourceArt(payload.art);
    if (art?.overlays?.length) addExistingOverlays(art.overlays);
    else restoreEmbeddedArtDraft();
    replaceUnavailableOverlayFonts();
    replaceUnavailableOverlayTemplates();
    applyRequestedTemplateSelection();
    syncTranscriptTemplateFromExistingTrack();
    renderRetainedSegmentList();
    renderEditor();
    renderArtJob(art);
    const suggestion = getSourceSuggestion(payload.artSuggestion);
    renderAiSuggestionJob(suggestion);

    pageLoading.hidden = true;
    pageError.hidden = true;
    artWorkspace.hidden = false;
    artEditorReady = true;
    if (pendingCutDraft?.transcript) applyEditorCutDraft(pendingCutDraft);
    window.requestAnimationFrame(() => {
      syncVideoStageLayout();
      refreshFrameTimeline({ force: true });
    });
    if (["queued", "processing"].includes(suggestion?.status)) {
      activateWorkbenchPanel("ai");
    } else {
      activateWorkbenchPanel("settings");
    }
    if (["queued", "processing"].includes(art?.status)) pollArtJob();
    if (["queued", "processing"].includes(suggestion?.status)) {
      pollAiSuggestionJob();
    }
  } catch (error) {
    showPageError(error.message);
  }
}

async function restartProject() {
  const confirmed = await window.appConfirm({
    eyebrow: "艺术字设置检查",
    title: "确定重新开始？",
    message:
      "当前未生成的艺术字设置不会保留；原视频和已经生成的文件仍会安全保留。",
    confirmText: "重新开始",
    icon: "ph:arrow-counter-clockwise-bold",
  });
  if (!confirmed) return;
  if (pollTimer) window.clearTimeout(pollTimer);
  if (aiPollTimer) window.clearTimeout(aiPollTimer);
  try {
    window.sessionStorage.removeItem("currentTranscriptionJobId");
  } catch {
    // Returning to the upload page still works when browser storage is unavailable.
  }
  window.location.href = "/";
}

addCustomText.addEventListener("click", () => {
  const text = customText.value.trim();
  if (!text) {
    customText.focus();
    return;
  }
  const start = clamp(
    previewPlaybackTime(),
    0,
    Math.max(0, duration - 0.1),
  );
  createOverlay(text, start, Math.min(duration, start + 3));
  customText.value = "";
});

customText.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    addCustomText.click();
  }
});

overlayText.addEventListener("input", () => {
  updateSelectedOverlay({ text: overlayText.value });
});
fontSelect.addEventListener("change", () => {
  updateSelectedOverlay({ font: fontSelect.value });
});
fontSize.addEventListener("input", () => {
  fontSizeValue.value = fontSize.value;
  updateSelectedOverlay({ fontSize: Number(fontSize.value) });
});
fontSize.addEventListener("change", rebuildTranscriptTrackLayout);
directionSelect.addEventListener("change", () => {
  charsPerLineLabel.textContent =
    directionSelect.value === "vertical" ? "每列字数" : "每行字数";
  updateSelectedOverlay({ direction: directionSelect.value });
});
textAlignSelect.addEventListener("change", () => {
  updateSelectedOverlay({ textAlign: textAlignSelect.value });
});
charsPerLine.addEventListener("input", () => {
  const value = clamp(Number(charsPerLine.value) || 0, 0, 20);
  charsPerLine.value = String(value);
  updateSelectedOverlay({ charsPerLine: value });
});
letterSpacing.addEventListener("input", () => {
  letterSpacingValue.value = letterSpacing.value;
  updateSelectedOverlay({ letterSpacing: Number(letterSpacing.value) });
});
lineSpacing.addEventListener("input", () => {
  lineSpacingValue.value = lineSpacing.value;
  updateSelectedOverlay({ lineSpacing: Number(lineSpacing.value) });
});
textColor.addEventListener("input", () => {
  updateSelectedOverlay({ color: textColor.value.toUpperCase() });
});
strokeColor.addEventListener("input", () => {
  updateSelectedOverlay({ strokeColor: strokeColor.value.toUpperCase() });
});
strokeWidth.addEventListener("input", () => {
  strokeWidthValue.value = strokeWidth.value;
  updateSelectedOverlay({ strokeWidth: Number(strokeWidth.value) });
});
shadowToggle.addEventListener("change", () => {
  updateSelectedOverlay({ shadow: shadowToggle.checked });
});
startTime.addEventListener("change", () => {
  const overlay = selectedOverlay();
  if (!overlay) return;
  const start = clamp(Number(startTime.value), 0, Math.max(0, overlay.end - 0.1));
  startTime.value = start.toFixed(1);
  updateSelectedOverlay({ start }, { seek: true });
});
endTime.addEventListener("change", () => {
  const overlay = selectedOverlay();
  if (!overlay) return;
  const end = clamp(Number(endTime.value), overlay.start + 0.1, duration);
  endTime.value = end.toFixed(1);
  updateSelectedOverlay({ end });
});
fitArtToTranscript.addEventListener("click", fitSelectedArtTimeToTranscript);

const ART_STYLE_PALETTES = {
  impact: { color: "#FFD84D", strokeColor: "#15110A" },
  neon: { color: "#A9E7CF", strokeColor: "#173A31" },
  metal: { color: "#FFD166", strokeColor: "#5B2A00" },
  sticker: { color: "#FF4D8D", strokeColor: "#4A1028" },
  clean: { color: "#FFFFFF", strokeColor: "#071018" },
  gradient: { color: "#FF8A3D", strokeColor: "#5A1744" },
  comic: { color: "#FFE14D", strokeColor: "#E52B2B" },
  ice: { color: "#B7F4FF", strokeColor: "#1667A9" },
  ink: { color: "#F5E6C8", strokeColor: "#171512" },
  ribbon: { color: "#C66E3A", strokeColor: "#352218" },
  luxury: { color: "#F5D06F", strokeColor: "#17120A" },
};

artStyleGrid.addEventListener("click", (event) => {
  const button = event.target.closest(".art-style-option");
  if (!button || !artStyleGrid.contains(button)) return;
  const artStyle = button.dataset.artStyle;
  if (!ART_STYLE_PALETTES[artStyle]) return;
  updateSelectedOverlay({
    artStyle,
    ...ART_STYLE_PALETTES[artStyle],
  });
  renderControls();
});

transcriptStyleGrid?.addEventListener("click", (event) => {
  const button = event.target.closest(".art-style-option");
  if (!button || !transcriptStyleGrid.contains(button) || button.disabled) {
    return;
  }
  setTranscriptTrackTemplate(button.dataset.artStyle, { announce: true });
});

for (const [index, tab] of workbenchTabs.entries()) {
  tab.addEventListener("click", () => {
    activateWorkbenchPanel(tab.dataset.workbenchTab);
  });
  tab.addEventListener("keydown", (event) => {
    let nextIndex = index;
    if (event.key === "ArrowRight") {
      nextIndex = (index + 1) % workbenchTabs.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + workbenchTabs.length) % workbenchTabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = workbenchTabs.length - 1;
    } else {
      return;
    }
    event.preventDefault();
    activateWorkbenchPanel(
      workbenchTabs[nextIndex].dataset.workbenchTab,
      { focusTab: true },
    );
  });
}

deleteOverlay.addEventListener("click", async () => {
  const selected = selectedOverlay();
  if (!selected) return;
  if (isTranscriptTrackOverlay(selected)) {
    const confirmed = await window.appConfirm({
      eyebrow: "全文艺术字轨道",
      title: "删除整条全文轨道？",
      message:
        "轨道内所有词级同步片段都会删除，自定义艺术字不会受到影响。",
      confirmText: "删除全文轨道",
      icon: "ph:trash-bold",
      tone: "danger",
    });
    if (!confirmed) return;
    overlays = overlays.filter(
      (overlay) => overlay.trackId !== selected.trackId,
    );
  } else {
    overlays = overlays.filter((overlay) => overlay.id !== selectedOverlayId);
  }
  selectedOverlayId = overlays[0]?.id || null;
  showApplyAllSettingsMessage("");
  showRetainedBulkMessage("");
  renderEditor();
  renderRetainedSegmentList();
});

applyCurrentSettingsToAll.addEventListener(
  "click",
  applySelectedSettingsToAllOverlays,
);

retainedText.addEventListener("input", () => {
  const changed =
    comparableTranscriptEditorText(retainedText.value) !==
    comparableTranscriptEditorText(retainedSavedText);
  showRetainedEditStatus(changed ? "文案已修改，保存后才会用于艺术字。" : "");
  updateRetainedEditControls();
});

saveRetainedText.addEventListener("click", saveRetainedTranscript);

selectAllRetainedSegments.addEventListener("change", () => {
  showRetainedBulkMessage("");
  selectedRetainedSegmentKeys.clear();
  if (selectAllRetainedSegments.checked) {
    for (const segment of selectableRetainedSegments()) {
      selectedRetainedSegmentKeys.add(retainedSegmentKey(segment));
    }
  }
  renderRetainedSegmentList();
});

addSelectedRetainedSegments.addEventListener("click", () => {
  const selectedSegments = retainedTranscriptSegments.filter((segment) =>
    selectedRetainedSegmentKeys.has(retainedSegmentKey(segment)),
  );
  addRetainedSegmentsAsOverlays(selectedSegments);
});

addAllRetainedSegments.addEventListener("click", () => {
  addFullTranscriptTrack();
});

artVideo.addEventListener("loadedmetadata", () => {
  syncVideoStageLayout();
  videoTime.textContent = `${formatTime(artVideo.currentTime)} / ${formatTime(duration)}`;
  refreshFrameTimeline({ force: true });
  renderPreview();
});
artVideo.addEventListener("seeking", () => {
  if (embeddedEditor) {
    editorHostCurrentTime = clamp(
      Number(artVideo.currentTime) || 0,
      0,
      duration || Infinity,
    );
    window.parent.postMessage(
      {
        type: "editor-suite:seek",
        kind: "art",
        currentTime: artVideo.currentTime || 0,
      },
      window.location.origin,
    );
  }
  videoTime.textContent = `${formatTime(artVideo.currentTime)} / ${formatTime(duration)}`;
  updateFrameTimelinePlayhead();
  renderPreview();
});
artVideo.addEventListener("timeupdate", () => {
  videoTime.textContent = `${formatTime(artVideo.currentTime)} / ${formatTime(duration)}`;
  updateFrameTimelinePlayhead();
  renderPreview();
});
window.addEventListener("resize", () => {
  syncVideoStageLayout();
  scheduleFrameTimelineRebuild();
  refreshFrameTimeline();
  renderPreview();
});
frameTimelineSeek.addEventListener("input", () => {
  seekArtVideoPreview(frameTimelineSeek.value);
});
frameTimelineJumpButton.addEventListener("click", jumpToFrameTimelineTime);
frameTimelineJumpInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  jumpToFrameTimelineTime();
});
frameTimelineJumpInput.addEventListener("input", () => {
  frameTimelineJumpInput.setAttribute("aria-invalid", "false");
  if (frameTimelineStatus.dataset.source === "jump") {
    updateFrameTimelineStatus("");
  }
});
frameTimelineTrack?.addEventListener("pointerdown", beginFrameTimelineScrub);
generateArtVideo.addEventListener("click", generateVideo);
generateAiSuggestions.addEventListener("click", requestAiSuggestions);
aiSuggestionCount.addEventListener("change", () => {
  const remaining = Math.max(
    1,
    MANUAL_OVERLAY_LIMIT - manualOverlayCount(),
  );
  const count = Number(aiSuggestionCount.value);
  if (Number.isFinite(count)) {
    aiSuggestionCount.value = String(clamp(Math.round(count), 1, remaining));
  }
});
cancelAiSuggestions.addEventListener("click", cancelAiSuggestionDrafts);
confirmAiSuggestions.addEventListener("click", confirmAiSuggestionDrafts);
restartProjectButton.addEventListener("click", restartProject);
document.addEventListener("visibilitychange", async () => {
  if (document.hidden) return;
  try {
    await Promise.all([
      loadFontLibrary(),
      loadArtTemplateLibrary(),
    ]);
    replaceUnavailableOverlayFonts();
    replaceUnavailableOverlayTemplates();
    renderEditor();
  } catch {
    // Keep the current editor state when the font library cannot be refreshed.
  }
});

for (const container of mediaControlGroups) {
  setupExternalVideoControls(container);
}

requestLatestEditorCutDraft();
initialize();
