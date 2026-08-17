const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;
const POSITION_PRESETS = {
  "left-top": { label: "左上", x: 0.2, y: 0.2 },
  "right-top": { label: "右上", x: 0.8, y: 0.2 },
  "left-bottom": { label: "左下", x: 0.2, y: 0.8 },
  "right-bottom": { label: "右下", x: 0.8, y: 0.8 },
  center: { label: "居中", x: 0.5, y: 0.5 },
};

const pageLoading = document.querySelector("#pageLoading");
const pageError = document.querySelector("#pageError");
const pageErrorText = document.querySelector("#pageErrorText");
const pageErrorBack = document.querySelector("#pageErrorBack");
const pipWorkspace = document.querySelector("#pipWorkspace");
const brandLink = document.querySelector("#brandLink");
const backToArtText = document.querySelector("#backToArtText");
const restartProjectButton = document.querySelector("#restartProjectButton");
const pipCount = document.querySelector("#pipCount");
const pipSourceLabel = document.querySelector("#pipSourceLabel");
const pipEditWorkflowStep = document.querySelector("#pipEditWorkflowStep");
const pipArtWorkflowStep = document.querySelector("#pipArtWorkflowStep");
const pipVideo = document.querySelector("#pipVideo");
const pipVideoPlayer = document.querySelector("#pipVideoPlayer");
const pipVideoStage = document.querySelector("#pipVideoStage");
const pipOverlayLayer = document.querySelector("#pipOverlayLayer");
const videoTime = document.querySelector("#videoTime");
const timelineTime = document.querySelector("#timelineTime");
const pipTimelineScroll = document.querySelector("#pipTimelineScroll");
const pipTimelineTrack = document.querySelector("#pipTimelineTrack");
const pipTimelineRuler = document.querySelector("#pipTimelineRuler");
const pipTimelineThumbnails = document.querySelector("#pipTimelineThumbnails");
const pipTimelineSegments = document.querySelector("#pipTimelineSegments");
const pipTimelinePlayhead = document.querySelector("#pipTimelinePlayhead");
const pipTimelineSeek = document.querySelector("#pipTimelineSeek");
const segmentList = document.querySelector("#segmentList");
const selectedSegmentTime = document.querySelector("#selectedSegmentTime");
const assetTypeInputs = [
  ...document.querySelectorAll('input[name="assetType"]'),
];
const generationModeInputs = [
  ...document.querySelectorAll('input[name="generationMode"]'),
];
const aspectRatioInputs = [
  ...document.querySelectorAll('input[name="imageAspectRatio"]'),
];
const aspectRatioLegend = document.querySelector("#aspectRatioLegend");
const pipStartTime = document.querySelector("#pipStartTime");
const pipEndTime = document.querySelector("#pipEndTime");
const fitPipToTranscript = document.querySelector("#fitPipToTranscript");
const pipTimeMessage = document.querySelector("#pipTimeMessage");
const promptField = document.querySelector("#promptField");
const pipPromptLabel = document.querySelector("#pipPromptLabel");
const pipPromptHelp = document.querySelector("#pipPromptHelp");
const pipPrompt = document.querySelector("#pipPrompt");
const writePipPrompt = document.querySelector("#writePipPrompt");
const promptWriterStatus = document.querySelector("#promptWriterStatus");
const generatePipImage = document.querySelector("#generatePipImage");
const imageProgress = document.querySelector("#imageProgress");
const assetProgressText = document.querySelector("#assetProgressText");
const imageError = document.querySelector("#imageError");
const generatedCount = document.querySelector("#generatedCount");
const generatedEmpty = document.querySelector("#generatedEmpty");
const generatedList = document.querySelector("#generatedList");
const generatePipVideo = document.querySelector("#generatePipVideo");
const outputProgress = document.querySelector("#outputProgress");
const outputStatus = document.querySelector("#outputStatus");
const outputPercent = document.querySelector("#outputPercent");
const outputProgressTrack = document.querySelector("#outputProgressTrack");
const outputProgressBar = document.querySelector("#outputProgressBar");
const outputError = document.querySelector("#outputError");
const outputResult = document.querySelector("#outputResult");
const outputStatusChip = document.querySelector("#outputStatusChip");
const previewFinalVideo = document.querySelector("#previewFinalVideo");
const downloadFinalVideo = document.querySelector("#downloadFinalVideo");
const mediaControlGroups = [
  ...document.querySelectorAll("[data-media-controls]"),
];

const PIP_TIMELINE_THUMB_MIN = 8;
const PIP_TIMELINE_THUMB_MAX = 180;
const PIP_TIMELINE_MAJOR_TICK_WIDTH = 72;
const PIP_TIMELINE_MIN_PIXELS_PER_SECOND = 22;
const PIP_TIMELINE_TEXT_CHAR_WIDTH = 10;
const PIP_TIMELINE_TEXT_LINES = 2;
const PIP_TIMELINE_TRACK_HEIGHT = 30;
const PIP_TIMELINE_BASE_HEIGHT = 44;
const PIP_MIN_WIDTH = 0.2;
const PIP_MAX_WIDTH = 0.55;

const query = new URLSearchParams(window.location.search);
const embeddedEditor = query.get("embedded") === "1";
document.documentElement.classList.toggle("editor-tool-embedded", embeddedEditor);
const jobId = query.get("job") || "";
const requestedSource = ["original", "edited", "art"].includes(
  query.get("source"),
)
  ? query.get("source")
  : "art";
let job = null;
let duration = 0;
let transcriptSegments = [];
let selectedSegmentIndex = -1;
let pictureItems = [];
let pollTimer = null;
let assetPollTimer = null;
let baseVideoUrl = "";
let finalVideoUrl = "";
let showingFinalVideo = false;
let generationModalActive = false;
let selectedPictureItemId = "";
let activePictureDrag = null;
let activePictureResize = null;
let pipTimelineBuildId = 0;
let pipTimelineSignature = "";
let pipTimelineRulerSignature = "";
let pipTimelineResizeTimer = null;
let editorHostCurrentTime = null;
let editorHostStateSignature = "";
let previewVisibilitySignature = "";
let cutDraftActive = false;
let pendingCutDraft = null;
let pipEditorReady = false;
const pipTimelineStore = window.EditorTimeline.createStore(
  { duration: 0, tracks: [] },
  { onCommit: () => persistEmbeddedPipDraft() },
);

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function formatTime(value, includeTenths = false) {
  const seconds = Math.max(0, Number(value) || 0);
  const minutes = Math.floor(seconds / 60);
  const wholeSeconds = Math.floor(seconds % 60);
  const base = `${String(minutes).padStart(2, "0")}:${String(wholeSeconds).padStart(2, "0")}`;
  return includeTenths ? `${base}.${Math.floor((seconds % 1) * 10)}` : base;
}

function formatRange(start, end) {
  return `${formatTime(start, true)}–${formatTime(end, true)}`;
}

function showPageError(message) {
  pageLoading.hidden = true;
  pipWorkspace.hidden = true;
  pageErrorText.textContent = message;
  pageError.hidden = false;
}

function showMessage(element, message) {
  element.textContent = message || "";
  element.hidden = !message;
  if (element === outputError) window.queueMicrotask(notifyEditorHost);
}

async function parseResponse(response, fallback) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // The fallback below keeps non-JSON gateway errors understandable.
  }
  if (!response.ok) {
    throw new Error(payload?.detail || fallback);
  }
  return payload;
}

function currentGenerationMode() {
  return generationModeInputs.find((input) => input.checked)?.value || "custom";
}

function currentAssetType() {
  return assetTypeInputs.find((input) => input.checked)?.value || "image";
}

function isReadyAsset(item) {
  return item.type !== "video" || item.status === "completed";
}

function assetKindLabel(item) {
  return item.type === "video" ? "动态视频" : "静态图片";
}

function currentImageAspectRatio() {
  return aspectRatioInputs.find((input) => input.checked)?.value || "16:9";
}

function numericAspectRatio(value) {
  const [width, height] = String(value || "16:9").split(":").map(Number);
  return width > 0 && height > 0 ? width / height : 16 / 9;
}

function updateAspectRatioSelection() {
  for (const input of aspectRatioInputs) {
    input.closest(".pip-aspect-ratio-option")?.classList.toggle(
      "is-selected",
      input.checked,
    );
  }
}

function selectedSegment() {
  return transcriptSegments[selectedSegmentIndex] || null;
}

function showPipTimeMessage(message, state = "") {
  pipTimeMessage.textContent = message || "";
  pipTimeMessage.dataset.state = state;
  pipTimeMessage.hidden = !message;
}

function setPipTimeRange(start, end, message = "") {
  const safeStart = clamp(Number(start) || 0, 0, Math.max(0, duration - 0.1));
  const safeEnd = clamp(Number(end) || safeStart + 0.1, safeStart + 0.1, duration);
  pipStartTime.max = Math.max(0, duration - 0.1).toFixed(1);
  pipEndTime.max = duration.toFixed(1);
  pipStartTime.value = safeStart.toFixed(1);
  pipEndTime.value = safeEnd.toFixed(1);
  showPipTimeMessage(message, message ? "success" : "");
  return { start: safeStart, end: safeEnd };
}

function currentPipTimeRange(showError = true) {
  const start = Number(pipStartTime.value);
  const end = Number(pipEndTime.value);
  let error = "";
  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    error = "请输入有效的开始和结束时间。";
  } else if (start < 0 || end > duration + 0.01) {
    error = `画中画时间必须在 0–${duration.toFixed(1)} 秒之间。`;
  } else if (end - start < 0.05) {
    error = "结束时间必须晚于开始时间。";
  }
  if (error) {
    if (showError) showPipTimeMessage(error, "error");
    return null;
  }
  if (showError) showPipTimeMessage("画中画显示时间已确认。", "success");
  return { start, end };
}

function fitPipTimeToTranscript() {
  const segment = selectedSegment();
  if (!segment) {
    showPipTimeMessage("请先选择要插入画中画的文字片段。", "error");
    return;
  }
  const range = setPipTimeRange(
    segment.start,
    segment.end,
    `已贴合当前文案时间：${formatRange(segment.start, segment.end)}。`,
  );
  seekEditorPreview(range.start);
  renderPreview();
}

function presetKeyForCoordinates(x, y) {
  let bestKey = "right-top";
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const [key, preset] of Object.entries(POSITION_PRESETS)) {
    const distance = Math.hypot(Number(x) - preset.x, Number(y) - preset.y);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestKey = key;
    }
  }
  return bestDistance <= 0.04 ? bestKey : "custom";
}

function constrainPictureItemToStage(
  item,
  imageAspectRatio = numericAspectRatio(item.aspectRatio),
  bounds = null,
) {
  const layerBounds = bounds || pipOverlayLayer.getBoundingClientRect();
  if (layerBounds.width <= 0 || layerBounds.height <= 0) return;
  const halfWidth = Math.min(0.49, item.width / 2);
  const normalizedHeight =
    (item.width * layerBounds.width) /
    Math.max(0.1, imageAspectRatio) /
    layerBounds.height;
  const halfHeight = Math.min(0.49, normalizedHeight / 2);
  item.x = clamp(item.x, halfWidth, 1 - halfWidth);
  item.y = clamp(item.y, halfHeight, 1 - halfHeight);
}

function pictureItemAspectRatio(item, element) {
  const media = element.querySelector("img, video");
  if (media?.naturalWidth && media?.naturalHeight) {
    return media.naturalWidth / media.naturalHeight;
  }
  if (media?.videoWidth && media?.videoHeight) {
    return media.videoWidth / media.videoHeight;
  }
  return numericAspectRatio(item.aspectRatio);
}

function maximumPictureWidthAtPosition(item, imageAspectRatio, bounds) {
  const horizontalRoom = 2 * Math.min(item.x, 1 - item.x);
  const verticalRoom =
    (2 * Math.min(item.y, 1 - item.y) * imageAspectRatio * bounds.height) /
    bounds.width;
  return Math.max(
    0.05,
    Math.min(PIP_MAX_WIDTH, horizontalRoom, verticalRoom),
  );
}

function pictureResizeWidth(resize, event) {
  const deltaX = event.clientX - resize.startClientX;
  const deltaY = event.clientY - resize.startClientY;
  const horizontalDirection = resize.direction.includes("e")
    ? 1
    : resize.direction.includes("w")
      ? -1
      : 0;
  const verticalDirection = resize.direction.includes("s")
    ? 1
    : resize.direction.includes("n")
      ? -1
      : 0;
  const horizontalChange =
    (horizontalDirection * deltaX * 2) / resize.bounds.width;
  const verticalChange =
    (verticalDirection * deltaY * 2 * resize.imageAspectRatio) /
    resize.bounds.width;
  const widthChange =
    horizontalDirection && verticalDirection
      ? Math.abs(horizontalChange) >= Math.abs(verticalChange)
        ? horizontalChange
        : verticalChange
      : horizontalChange || verticalChange;
  return clamp(
    resize.startWidth + widthChange,
    Math.min(PIP_MIN_WIDTH, resize.maximumWidth),
    resize.maximumWidth,
  );
}

function updatePictureDrag(event) {
  const drag = activePictureDrag;
  if (!drag || drag.pointerId !== event.pointerId) return;
  const deltaX = event.clientX - drag.startClientX;
  const deltaY = event.clientY - drag.startClientY;
  if (!drag.moved && Math.hypot(deltaX, deltaY) < 3) return;
  drag.moved = true;
  drag.element.classList.add("is-dragging");
  drag.targetX = drag.startX + deltaX / drag.bounds.width;
  drag.targetY = drag.startY + deltaY / drag.bounds.height;
  if (drag.framePending) return;
  drag.framePending = true;
  // Coalesce to one style write per animation frame and reuse the bounds
  // captured at drag start (no per-move layout read) for smooth dragging.
  window.requestAnimationFrame(() => {
    drag.framePending = false;
    if (activePictureDrag !== drag) return;
    drag.item.x = drag.targetX;
    drag.item.y = drag.targetY;
    constrainPictureItemToStage(
      drag.item,
      drag.imageAspectRatio,
      drag.bounds,
    );
    drag.element.style.left = `${drag.item.x * 100}%`;
    drag.element.style.top = `${drag.item.y * 100}%`;
  });
}

function finishPictureDrag(event) {
  const drag = activePictureDrag;
  if (!drag || drag.pointerId !== event.pointerId) return;
  if (drag.element.hasPointerCapture(event.pointerId)) {
    drag.element.releasePointerCapture(event.pointerId);
  }
  drag.element.classList.remove("is-dragging");
  drag.element.removeEventListener("pointermove", updatePictureDrag);
  drag.element.removeEventListener("pointerup", finishPictureDrag);
  drag.element.removeEventListener("pointercancel", finishPictureDrag);
  activePictureDrag = null;
  syncPipTimelineModel();
  pipTimelineStore.patchClipPayload(
    pipTimelineClipId(drag.item.id),
    { x: drag.item.x, y: drag.item.y, width: drag.item.width },
    { silent: true },
  );
  pipTimelineStore.commit("preview-move");
  renderGeneratedList();
  renderTimelineSegments();
  renderPreview();
}

function beginPictureDrag(event, item, element) {
  if (event.button !== 0 || showingFinalVideo) return;
  event.preventDefault();
  pipVideo.pause();
  selectedPictureItemId = item.id;
  const bounds = pipOverlayLayer.getBoundingClientRect();
  const imageAspectRatio = pictureItemAspectRatio(item, element);
  activePictureDrag = {
    pointerId: event.pointerId,
    item,
    element,
    bounds,
    imageAspectRatio,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX: item.x,
    startY: item.y,
    moved: false,
  };
  element.classList.add("is-selected");
  element.setPointerCapture(event.pointerId);
  element.addEventListener("pointermove", updatePictureDrag);
  element.addEventListener("pointerup", finishPictureDrag);
  element.addEventListener("pointercancel", finishPictureDrag);
}

function updatePictureResize(event) {
  const resize = activePictureResize;
  if (!resize || resize.pointerId !== event.pointerId) return;
  const deltaX = event.clientX - resize.startClientX;
  const deltaY = event.clientY - resize.startClientY;
  if (!resize.moved && Math.hypot(deltaX, deltaY) < 3) return;
  resize.moved = true;
  resize.element.classList.add("is-resizing");
  resize.targetWidth = pictureResizeWidth(resize, event);
  if (resize.framePending) return;
  resize.framePending = true;
  window.requestAnimationFrame(() => {
    resize.framePending = false;
    if (activePictureResize !== resize) return;
    resize.item.width = resize.targetWidth;
    resize.element.style.width = `${resize.item.width * 100}%`;
  });
}

function finishPictureResize(event) {
  const resize = activePictureResize;
  if (!resize || resize.pointerId !== event.pointerId) return;
  resize.item.width = resize.targetWidth;
  resize.element.style.width = `${resize.item.width * 100}%`;
  if (resize.element.hasPointerCapture(event.pointerId)) {
    resize.element.releasePointerCapture(event.pointerId);
  }
  resize.element.classList.remove("is-resizing");
  resize.element.removeEventListener("pointermove", updatePictureResize);
  window.removeEventListener("pointerup", finishPictureResize);
  window.removeEventListener("pointercancel", finishPictureResize);
  activePictureResize = null;
  syncPipTimelineModel();
  pipTimelineStore.patchClipPayload(
    pipTimelineClipId(resize.item.id),
    { x: resize.item.x, y: resize.item.y, width: resize.item.width },
    { silent: true },
  );
  pipTimelineStore.commit("preview-resize");
  renderGeneratedList();
  renderTimelineSegments();
  renderPreview();
}

function beginPictureResize(event, item, element, direction) {
  if (event.button !== 0 || showingFinalVideo) return;
  event.preventDefault();
  event.stopPropagation();
  pipVideo.pause();
  selectedPictureItemId = item.id;
  const bounds = pipOverlayLayer.getBoundingClientRect();
  const imageAspectRatio = pictureItemAspectRatio(item, element);
  activePictureResize = {
    pointerId: event.pointerId,
    item,
    element,
    direction,
    bounds,
    imageAspectRatio,
    maximumWidth: maximumPictureWidthAtPosition(item, imageAspectRatio, bounds),
    startClientX: event.clientX,
    startClientY: event.clientY,
    startWidth: item.width,
    targetWidth: item.width,
    moved: false,
    framePending: false,
  };
  element.classList.add("is-selected");
  element.setPointerCapture(event.pointerId);
  element.addEventListener("pointermove", updatePictureResize);
  window.addEventListener("pointerup", finishPictureResize);
  window.addEventListener("pointercancel", finishPictureResize);
}

function setVideoSource(url, isFinal = false) {
  if (!url) return;
  const currentTime = clamp(pipVideo.currentTime || 0, 0, duration);
  const wasPaused = pipVideo.paused;
  showingFinalVideo = isFinal;
  pipVideo.src = `${url}${url.includes("?") ? "&" : "?"}v=${Date.now()}`;
  pipOverlayLayer.hidden = isFinal;
  previewFinalVideo.textContent = isFinal ? "返回编辑预览" : "预览成片";
  pipVideo.addEventListener(
    "loadedmetadata",
    () => {
      pipVideo.currentTime = clamp(currentTime, 0, pipVideo.duration || duration);
      if (!wasPaused) pipVideo.play().catch(() => {});
      syncVideoStageLayout();
      renderPreview();
    },
    { once: true },
  );
}

function syncVideoStageLayout() {
  const sourceWidth = Number(pipVideo.videoWidth) || 9;
  const sourceHeight = Number(pipVideo.videoHeight) || 16;
  pipVideoStage.style.aspectRatio = `${sourceWidth} / ${sourceHeight}`;
}

function setupExternalVideoControls(container) {
  const video = document.getElementById(container.dataset.videoId);
  const fullscreenTarget = document.getElementById(container.dataset.fullscreenId);
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

  const renderPlayback = () => {
    const total = Number(video.duration) || duration;
    seek.max = String(total);
    seek.value = String(clamp(video.currentTime || 0, 0, total));
    time.textContent = `${formatTime(video.currentTime)} / ${formatTime(total)}`;
    playIcon.hidden = !video.paused;
    pauseIcon.hidden = video.paused;
    playButton.setAttribute("aria-label", video.paused ? "播放" : "暂停");
  };
  const renderVolume = () => {
    const muted = video.muted || video.volume === 0;
    volume.value = String(video.volume);
    volumeIcon.hidden = muted;
    mutedIcon.hidden = !muted;
    muteButton.setAttribute("aria-label", muted ? "取消静音" : "静音");
  };

  playButton.addEventListener("click", () => {
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  });
  seek.addEventListener("input", () => {
    video.currentTime = Number(seek.value);
  });
  muteButton.addEventListener("click", () => {
    video.muted = !video.muted;
    renderVolume();
  });
  volume.addEventListener("input", () => {
    video.volume = Number(volume.value);
    video.muted = video.volume === 0;
    renderVolume();
  });
  fullscreenButton.addEventListener("click", () => {
    if (document.fullscreenElement) document.exitFullscreen?.();
    else fullscreenTarget.requestFullscreen?.();
  });
  video.addEventListener("loadedmetadata", renderPlayback);
  video.addEventListener("durationchange", renderPlayback);
  video.addEventListener("timeupdate", renderPlayback);
  video.addEventListener("play", renderPlayback);
  video.addEventListener("pause", renderPlayback);
  video.addEventListener("volumechange", renderVolume);
  renderPlayback();
  renderVolume();
}

function pipTimelinePixelsPerSecond() {
  let pixelsPerSecond = PIP_TIMELINE_MIN_PIXELS_PER_SECOND;
  for (const item of pictureItems.filter(({ enabled }) => enabled)) {
    const itemDuration = Math.max(0.05, item.end - item.start);
    const characterCount = Array.from(
      String(item.text || "").replace(/\s+/g, ""),
    ).length;
    const requiredWidth =
      Math.ceil(characterCount / PIP_TIMELINE_TEXT_LINES) *
        PIP_TIMELINE_TEXT_CHAR_WIDTH +
      16;
    pixelsPerSecond = Math.max(pixelsPerSecond, requiredWidth / itemDuration);
  }
  return Math.ceil(pixelsPerSecond);
}

function updatePipTimelineScale() {
  const viewportWidth = pipTimelineScroll.clientWidth;
  if (duration <= 0 || viewportWidth <= 0) {
    pipTimelineTrack.style.removeProperty("width");
    return;
  }
  pipTimelineTrack.style.width = `${Math.max(
    viewportWidth,
    Math.round(duration * pipTimelinePixelsPerSecond()),
  )}px`;
}

function pipTimelineMajorStep(total, width) {
  const targetStep =
    total / Math.max(1, Math.floor(width / PIP_TIMELINE_MAJOR_TICK_WIDTH));
  const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600];
  return steps.find((step) => step >= targetStep) || steps.at(-1);
}

function renderTimelineRuler() {
  updatePipTimelineScale();
  const width = pipTimelineTrack.clientWidth;
  if (duration <= 0 || width <= 0) {
    pipTimelineRuler.replaceChildren();
    return;
  }
  const majorStep = pipTimelineMajorStep(duration, width);
  const minorStep = majorStep / 5;
  const signature = `${duration.toFixed(3)}|${Math.round(width)}|${majorStep}`;
  if (signature === pipTimelineRulerSignature) return;
  pipTimelineRulerSignature = signature;
  pipTimelineRuler.replaceChildren();

  const tickCount = Math.floor(duration / minorStep + 0.000001);
  for (let index = 0; index <= tickCount; index += 1) {
    const seconds = index * minorStep;
    const isMajor = index % 5 === 0;
    const tick = document.createElement("span");
    tick.className = "frame-timeline-tick";
    tick.classList.toggle("is-major", isMajor);
    tick.style.left = `${(seconds / duration) * 100}%`;
    if (isMajor) {
      const label = document.createElement("span");
      label.className = "frame-timeline-tick-label";
      label.textContent = formatTime(seconds);
      if (index === 0) label.classList.add("is-start");
      if (Math.abs(duration - seconds) < 0.001) label.classList.add("is-end");
      tick.append(label);
    }
    pipTimelineRuler.append(tick);
  }
}

function renderPipTimelinePlaceholders(count, fallback = false) {
  pipTimelineThumbnails.replaceChildren();
  for (let index = 0; index < count; index += 1) {
    const item = document.createElement("span");
    item.className = `frame-timeline-thumb ${fallback ? "is-fallback" : "is-loading"}`;
    pipTimelineThumbnails.append(item);
  }
}

function desiredPipTimelineThumbnailCount() {
  const width = pipTimelineTrack.clientWidth || 640;
  if (duration <= 0) return PIP_TIMELINE_THUMB_MIN;
  const majorStep = pipTimelineMajorStep(duration, width);
  return clamp(
    Math.ceil(duration / majorStep) + 1,
    PIP_TIMELINE_THUMB_MIN,
    PIP_TIMELINE_THUMB_MAX,
  );
}

function waitForPipTimelineMetadata(video) {
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
      reject(new Error("timeline metadata unavailable"));
    };
    video.addEventListener("loadedmetadata", handleLoaded, { once: true });
    video.addEventListener("error", handleError, { once: true });
  });
}

function seekPipTimelineExtractor(video, seconds) {
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
      reject(new Error("timeline frame unavailable"));
    };
    const timer = window.setTimeout(done, 900);
    video.addEventListener("seeked", handleSeeked, { once: true });
    video.addEventListener("error", handleError, { once: true });
    video.currentTime = target;
  });
}

async function buildPipTimelineThumbnails(options = {}) {
  const source = pipVideo.currentSrc || pipVideo.src;
  if (!source || duration <= 0) return;
  const count = desiredPipTimelineThumbnailCount();
  const signature = `${source}|${duration.toFixed(2)}|${count}`;
  if (!options.force && signature === pipTimelineSignature) return;
  pipTimelineSignature = signature;
  const buildId = (pipTimelineBuildId += 1);
  renderPipTimelinePlaceholders(count);

  const extractor = document.createElement("video");
  extractor.muted = true;
  extractor.playsInline = true;
  extractor.preload = "auto";
  extractor.src = source;
  try {
    await waitForPipTimelineMetadata(extractor);
    if (buildId !== pipTimelineBuildId) return;
    const ratio =
      extractor.videoWidth > 0 && extractor.videoHeight > 0
        ? extractor.videoWidth / extractor.videoHeight
        : 16 / 9;
    const canvas = document.createElement("canvas");
    canvas.width = 116;
    canvas.height = Math.max(48, Math.round(canvas.width / ratio));
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) throw new Error("timeline canvas unavailable");

    for (let index = 0; index < count; index += 1) {
      const edgeOffset = Math.min(0.04, duration / 2);
      const rawSeconds =
        count === 1 ? edgeOffset : (duration * index) / Math.max(1, count - 1);
      const seconds = clamp(
        rawSeconds,
        edgeOffset,
        Math.max(edgeOffset, duration - edgeOffset),
      );
      await seekPipTimelineExtractor(extractor, seconds);
      if (buildId !== pipTimelineBuildId) return;
      context.drawImage(extractor, 0, 0, canvas.width, canvas.height);
      const image = document.createElement("img");
      image.src = canvas.toDataURL("image/jpeg", 0.72);
      image.alt = "";
      image.draggable = false;
      const item = document.createElement("span");
      item.className = "frame-timeline-thumb";
      item.append(image);
      pipTimelineThumbnails.children[index]?.replaceWith(item);
    }
  } catch {
    if (buildId === pipTimelineBuildId) {
      renderPipTimelinePlaceholders(count, true);
    }
  } finally {
    extractor.removeAttribute("src");
    extractor.load();
  }
}

function schedulePipTimelineRebuild() {
  window.clearTimeout(pipTimelineResizeTimer);
  pipTimelineResizeTimer = window.setTimeout(() => {
    updatePipTimelineScale();
    pipTimelineRulerSignature = "";
    renderTimelineRuler();
    buildPipTimelineThumbnails();
  }, 180);
}

function pipTimelineClipId(pictureId) {
  return `pip:${pictureId}`;
}

function buildPipTimelineTracks() {
  return pictureItems
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => item.enabled)
    .map(({ item, index }, trackIndex) => ({
      id: `pip:track:${item.id}`,
      kind: "pip",
      name: `画中画${index + 1}`,
      order: trackIndex,
      clips: [
        {
          id: pipTimelineClipId(item.id),
          sourceId: item.id,
          name: `画中画${index + 1}`,
          start: item.start,
          end: item.end,
          minDuration: 0.1,
          editable: true,
          payload: {
            x: Number(item.x),
            y: Number(item.y),
            width: Number(item.width),
            enabled: Boolean(item.enabled),
          },
        },
      ],
    }));
}

function syncPipTimelineModel() {
  pipTimelineStore.setDuration(duration, { silent: true });
  return pipTimelineStore.replaceKind("pip", buildPipTimelineTracks(), {
    selection: selectedPictureItemId
      ? pipTimelineClipId(selectedPictureItemId)
      : null,
    silent: true,
  });
}

function updatePictureTimelineRange(item, start, end) {
  if (!item || !item.enabled) return false;
  syncPipTimelineModel();
  const clip = pipTimelineStore.setClipRange(
    pipTimelineClipId(item.id),
    start,
    end,
    { silent: true },
  );
  if (!clip) return false;
  item.start = clip.start;
  item.end = clip.end;
  selectedPictureItemId = item.id;
  pipTimelineStore.selectClip(clip.id, { silent: true });
  return true;
}

function beginPipTimelineSegmentAdjustment(event) {
  const segment = event.target.closest(
    ".pip-timeline-segment[data-picture-id]",
  );
  if (!segment || event.button !== 0) return;
  const item = pictureItems.find(
    (candidate) => String(candidate.id) === segment.dataset.pictureId,
  );
  if (!item) return;
  event.preventDefault();
  event.stopPropagation();
  selectedPictureItemId = item.id;
  seekEditorPreview(item.start);
  syncPipTimelineModel();
  pipTimelineStore.selectClip(pipTimelineClipId(item.id), { silent: true });
  const mode =
    event.target.closest("[data-timeline-resize]")?.dataset.timelineResize ||
    "move";
  const pointerSession = window.EditorTimeline.createPointerSession(
    pipTimelineStore,
    {
      clipId: pipTimelineClipId(item.id),
      mode,
      startClientX: event.clientX,
      trackWidth: pipTimelineTrack.getBoundingClientRect().width,
      duration,
      onUpdate: (clip) => {
        item.start = clip.start;
        item.end = clip.end;
      },
    },
  );
  if (!pointerSession) return;
  let moved = false;

  const move = (moveEvent) => {
    if (!moved && Math.abs(moveEvent.clientX - event.clientX) < 3) return;
    moved = true;
    const clip = pointerSession.update(moveEvent.clientX);
    segment.classList.add("is-selected", "is-dragging");
    segment.style.left = `${(clip.start / duration) * 100}%`;
    segment.style.width = `${Math.max(
      0.8,
      ((clip.end - clip.start) / duration) * 100,
    )}%`;
    seekEditorPreview(mode === "end" ? clip.end : clip.start);
    renderPreview();
  };

  const finish = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    window.removeEventListener("pointercancel", finish);
    pointerSession.finish();
    renderGeneratedList();
    renderTimelineSegments();
    renderPreview();
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish, { once: true });
  window.addEventListener("pointercancel", finish, { once: true });
}

function renderTimelineSegments() {
  syncPipTimelineModel();
  updatePipTimelineScale();
  pipTimelineSegments.replaceChildren();
  const enabledItems = pictureItems
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => item.enabled);
  const trackCount = Math.max(1, enabledItems.length);
  const trackAreaHeight = trackCount * PIP_TIMELINE_TRACK_HEIGHT;
  pipTimelineSegments.style.height = `${trackAreaHeight}px`;
  pipTimelineTrack.style.setProperty(
    "--editor-layer-timeline-height",
    `${trackAreaHeight}px`,
  );
  pipTimelineTrack.style.setProperty(
    "--editor-timeline-track-height",
    `${PIP_TIMELINE_BASE_HEIGHT + trackAreaHeight}px`,
  );
  if (duration <= 0) {
    notifyEditorHost();
    return;
  }
  for (const [trackIndex, { item, index }] of enabledItems.entries()) {
    const trackLabel = `画中画${index + 1}`;
    const segment = document.createElement("button");
    segment.type = "button";
    segment.className = "pip-timeline-segment";
    segment.dataset.pictureId = String(item.id);
    segment.dataset.timelineClipId = pipTimelineClipId(item.id);
    const timelineClip = pipTimelineStore.findClip(pipTimelineClipId(item.id));
    if (timelineClip) segment.dataset.timelineTrackId = timelineClip.trackId;
    segment.dataset.timelineEditable = "true";
    segment.dataset.timelineClipEditable = "true";
    segment.dataset.effectStart = String(item.start);
    segment.dataset.effectEnd = String(item.end);
    segment.dataset.timelineTrackIndex = String(trackIndex);
    segment.style.top = `${trackIndex * PIP_TIMELINE_TRACK_HEIGHT + 2}px`;
    segment.style.left = `${(item.start / duration) * 100}%`;
    segment.style.width = `${Math.max(1, ((item.end - item.start) / duration) * 100)}%`;
    const isSelected = item.id === selectedPictureItemId;
    segment.classList.toggle("is-selected", isSelected);
    segment.setAttribute("aria-pressed", String(isSelected));
    segment.title = `${trackLabel} ${formatRange(item.start, item.end)}`;
    segment.setAttribute(
      "aria-label",
      `${trackLabel}，${formatRange(item.start, item.end)}`,
    );
    const label = document.createElement("span");
    label.className = "editor-layer-timeline-segment-label";
    label.textContent = trackLabel;
    segment.append(label);
    for (const mode of ["start", "end"]) {
      const handle = document.createElement("span");
      handle.className = `art-timeline-handle timeline-clip-handle is-${mode}`;
      handle.dataset.timelineResize = mode;
      handle.setAttribute("aria-hidden", "true");
      segment.append(handle);
    }
    segment.addEventListener("click", (event) => {
      event.stopPropagation();
      selectedPictureItemId = item.id;
      pipTimelineStore.selectClip(pipTimelineClipId(item.id), { commit: true });
      seekToPictureItem(item);
      generatedList.children[index]?.scrollIntoView({ block: "nearest" });
      renderGeneratedList();
      renderTimelineSegments();
      renderPreview();
    });
    pipTimelineSegments.append(segment);
  }
  notifyEditorHost();
}

function renderTimelinePlayhead(currentTime = pipVideo.currentTime || 0) {
  updatePipTimelineScale();
  const current = clamp(Number(currentTime) || 0, 0, duration);
  const progress = duration > 0 ? (current / duration) * 100 : 0;
  pipTimelinePlayhead.style.left = `${progress}%`;
  pipTimelineSeek.value = String(current);
  timelineTime.textContent = `${formatTime(current)} / ${formatTime(duration)}`;
  videoTime.textContent = `${formatTime(current)} / ${formatTime(duration)}`;
  if (!pipVideo.paused && pipTimelineScroll.clientWidth > 0) {
    const playheadX = (progress / 100) * pipTimelineTrack.clientWidth;
    const viewportStart = pipTimelineScroll.scrollLeft;
    const viewportEnd = viewportStart + pipTimelineScroll.clientWidth;
    if (playheadX < viewportStart || playheadX > viewportEnd) {
      pipTimelineScroll.scrollLeft = Math.max(
        0,
        playheadX - pipTimelineScroll.clientWidth * 0.5,
      );
    }
  }
}

function createPicturePreviewElement(item) {
  const overlay = document.createElement("button");
  overlay.type = "button";
  overlay.className = "pip-preview-item";
  overlay.dataset.pictureId = item.id;
  overlay.dataset.effectStart = String(item.start || 0);
  const media = document.createElement(item.type === "video" ? "video" : "img");
  media.src = item.assetUrl || item.imageUrl;
  if (item.type === "video") {
    media.muted = true;
    media.loop = true;
    media.playsInline = true;
    media.preload = "auto";
    media.setAttribute("aria-hidden", "true");
    media.addEventListener("loadedmetadata", renderPreview, { once: true });
  } else {
    media.alt = `画中画：${item.text}`;
    media.draggable = false;
  }
  const dragHint = document.createElement("span");
  dragHint.className = "pip-drag-hint";
  dragHint.textContent = "拖动摆放 · 边角缩放";
  const resizeHandles = ["nw", "n", "ne", "e", "se", "s", "sw", "w"].map(
    (direction) => {
      const handle = document.createElement("span");
      handle.className = "pip-resize-handle";
      handle.dataset.pipResize = direction;
      handle.setAttribute("aria-hidden", "true");
      return handle;
    },
  );
  overlay.append(media, dragHint, ...resizeHandles);
  overlay.addEventListener("pointerdown", (event) => {
    const activeItem = pictureItems.find(
      (candidate) => candidate.id === overlay.dataset.pictureId,
    );
    if (!activeItem) return;
    const resizeHandle = event.target.closest("[data-pip-resize]");
    if (resizeHandle) {
      beginPictureResize(
        event,
        activeItem,
        overlay,
        resizeHandle.dataset.pipResize,
      );
      return;
    }
    beginPictureDrag(event, activeItem, overlay);
  });
  return overlay;
}

function syncPreviewVideo(media, item, current) {
  if (!media || media.readyState < 1 || !Number.isFinite(media.duration)) return;
  const localTime = Math.max(0, current - item.start) % Math.max(0.1, media.duration);
  if (Math.abs(media.currentTime - localTime) > 0.35) {
    media.currentTime = localTime;
  }
  if (pipVideo.paused) media.pause();
  else media.play().catch(() => {});
}

function previewPlaybackTime() {
  const current =
    embeddedEditor && Number.isFinite(editorHostCurrentTime)
      ? editorHostCurrentTime
      : Number(pipVideo.currentTime) || 0;
  return clamp(current, 0, duration || Infinity);
}

function seekEditorPreview(seconds) {
  const nextTime = clamp(Number(seconds) || 0, 0, duration || Infinity);
  if (embeddedEditor && window.parent !== window) {
    editorHostCurrentTime = nextTime;
    window.parent.postMessage(
      {
        type: "editor-suite:seek",
        kind: "pip",
        currentTime: nextTime,
      },
      window.location.origin,
    );
  } else {
    pipVideo.currentTime = nextTime;
  }
  return nextTime;
}

function renderPreview(options = {}) {
  const current = previewPlaybackTime();
  if (!embeddedEditor) renderTimelinePlayhead(current);
  if (activePictureDrag || activePictureResize) return;
  if (showingFinalVideo) {
    if (options.timeOnly && previewVisibilitySignature === "final") return;
    previewVisibilitySignature = "final";
    pipOverlayLayer.replaceChildren();
    notifyEditorHost();
    return;
  }
  const visibleItems = pictureItems.filter(
    (item) =>
      item.enabled &&
      item.status !== "failed" &&
      current >= item.start &&
      current <= item.end,
  );
  const nextVisibilitySignature = visibleItems.map(({ id }) => id).join("|");
  if (options.timeOnly && nextVisibilitySignature === previewVisibilitySignature) {
    return;
  }
  previewVisibilitySignature = nextVisibilitySignature;
  const visibleIds = new Set(visibleItems.map((item) => item.id));
  for (const child of [...pipOverlayLayer.children]) {
    if (!visibleIds.has(child.dataset.pictureId)) child.remove();
  }
  for (const item of visibleItems) {
    let overlay = [...pipOverlayLayer.children].find(
      (child) => child.dataset.pictureId === item.id,
    );
    if (!overlay) {
      overlay = createPicturePreviewElement(item);
      pipOverlayLayer.append(overlay);
    }
    overlay.classList.toggle("is-selected", item.id === selectedPictureItemId);
    overlay.setAttribute(
      "aria-label",
      `拖动“${item.text}”画中画调整位置，拖动边框控制点缩放，当前横向 ${Math.round(item.x * 100)}%，纵向 ${Math.round(item.y * 100)}%，大小 ${Math.round(item.width * 100)}%`,
    );
    overlay.title = "拖动画面调整位置，拖动边框控制点缩放";
    overlay.style.left = `${item.x * 100}%`;
    overlay.style.top = `${item.y * 100}%`;
    overlay.style.width = `${item.width * 100}%`;
    if (item.type === "video") {
      syncPreviewVideo(overlay.querySelector("video"), item, current);
    }
  }
  notifyEditorHost();
}

function notifyEditorHost(options = {}) {
  const timeline = syncPipTimelineModel();
  const state = {
    overlayHtml: pipOverlayLayer.innerHTML,
    overlayWidth: pipOverlayLayer.clientWidth,
    overlayHeight: pipOverlayLayer.clientHeight,
    timelineHtml: pipTimelineSegments?.innerHTML || "",
    timelineTrackCount: Math.max(
      1,
      ...Array.from(
        pipTimelineSegments?.querySelectorAll("[data-timeline-track-index]") || [],
        (segment) => Number(segment.dataset.timelineTrackIndex) + 1,
      ),
    ),
    timeline,
    generationDisabled: generatePipVideo.disabled,
    generationLabel: generatePipVideo.textContent.trim(),
    generationBusy: !outputProgress.hidden,
    generationError: outputError.hidden ? "" : outputError.textContent.trim(),
    generationPayload: {
      source: requestedSource,
      overlays: pictureItems
        .filter((item) => item.enabled && isReadyAsset(item))
        .map((item) => ({
          assetId: item.id,
          start: item.start,
          end: item.end,
          sourceStart: item.sourceStart ?? null,
          sourceEnd: item.sourceEnd ?? null,
          x: item.x,
          y: item.y,
          width: item.width,
        })),
    },
  };
  const signature = JSON.stringify(state);
  if (!options.force && signature === editorHostStateSignature) return;
  editorHostStateSignature = signature;
  if (!embeddedEditor || window.parent === window) {
    document.dispatchEvent(
      new CustomEvent("editor-suite:tool-state", {
        detail: { kind: "pip", ...state },
      }),
    );
    return;
  }
  window.parent.postMessage(
    {
      type: "editor-suite:tool-state",
      kind: "pip",
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

function embeddedPipDraftKey() {
  return `editor-suite:pip-draft:${jobId}`;
}

function persistEmbeddedPipDraft() {
  if (!jobId || !pipEditorReady) return;
  const segment = selectedSegment();
  const timeline = syncPipTimelineModel();
  window.EditorTimeline.saveDraft(
    window.sessionStorage,
    embeddedPipDraftKey(),
    timeline,
    {
      text: segment?.text || "",
      sourceStart: segment?.sourceStart ?? null,
      sourceEnd: segment?.sourceEnd ?? null,
      prompt: pipPrompt.value,
      assetType: currentAssetType(),
      mode: currentGenerationMode(),
      aspectRatio: currentImageAspectRatio(),
      selectedPictureItemId,
      items: pictureItems.map((item) => ({
        id: item.id,
        start: item.start,
        end: item.end,
        sourceStart: item.sourceStart ?? null,
        sourceEnd: item.sourceEnd ?? null,
        x: item.x,
        y: item.y,
        width: item.width,
        enabled: item.enabled,
      })),
    },
  );
}

function restoreEmbeddedPipDraft() {
  if (!jobId) return false;
  const envelope = window.EditorTimeline.loadDraft(
    window.sessionStorage,
    embeddedPipDraftKey(),
  );
  const saved = envelope?.metadata;
  if (!saved) return false;
  pipPrompt.value = String(saved.prompt || "");
  for (const input of assetTypeInputs) input.checked = input.value === saved.assetType;
  for (const input of generationModeInputs) input.checked = input.value === saved.mode;
  for (const input of aspectRatioInputs) input.checked = input.value === saved.aspectRatio;
  updateAssetType();
  updateGenerationMode();
  updateAspectRatioSelection();
  const savedItems = new Map(
    (saved.items || []).map((item) => [String(item.id), item]),
  );
  for (const item of pictureItems) {
    const savedItem = savedItems.get(String(item.id));
    if (savedItem) Object.assign(item, savedItem);
  }
  if (saved.selectedPictureItemId) {
    selectedPictureItemId = String(saved.selectedPictureItemId);
  }
  syncPipTimelineModel();
  renderGeneratedList();
  const index = transcriptSegments.findIndex((segment) =>
    saved.sourceStart !== null && saved.sourceEnd !== null
      ? Math.abs(Number(segment.sourceStart) - Number(saved.sourceStart)) < 0.01 &&
        Math.abs(Number(segment.sourceEnd) - Number(saved.sourceEnd)) < 0.01
      : segment.text === saved.text,
  );
  if (index >= 0) selectTranscriptSegment(index, { preservePreviewTime: true });
  return true;
}

function matchingDraftSegment(item, segments) {
  const sourceStart = Number(item.sourceStart);
  const sourceEnd = Number(item.sourceEnd);
  if (
    item.sourceStart !== null &&
    item.sourceEnd !== null &&
    Number.isFinite(sourceStart) &&
    Number.isFinite(sourceEnd)
  ) {
    const anchored = segments.find(
      (segment) =>
        Math.min(sourceEnd, Number(segment.sourceEnd)) -
          Math.max(sourceStart, Number(segment.sourceStart)) > 0.01,
    );
    if (anchored) return anchored;
  }
  const matchingText = segments.filter(
    (segment) => String(segment.text).trim() === String(item.text).trim(),
  );
  return matchingText.sort(
    (left, right) =>
      Math.abs(Number(left.start) - Number(item.start)) -
      Math.abs(Number(right.start) - Number(item.start)),
  )[0] || null;
}

function applyEditorCutDraft(data) {
  pendingCutDraft = data;
  cutDraftActive = Boolean(data.active);
  if (!pipEditorReady || !data.transcript) return;
  const previousSegment = selectedSegment();
  duration = Math.max(0, Number(data.duration) || 0);
  transcriptSegments = (data.transcript.segments || [])
    .map((segment) => ({
      text: String(segment.text || "").trim(),
      start: clamp(Number(segment.start) || 0, 0, duration),
      end: clamp(Number(segment.end) || 0, 0, duration),
      sourceStart: Number(segment.sourceStart),
      sourceEnd: Number(segment.sourceEnd),
    }))
    .filter((segment) => segment.text && segment.end > segment.start);
  for (const item of pictureItems) {
    const segment = matchingDraftSegment(item, transcriptSegments);
    if (!segment) continue;
    item.start = segment.start;
    item.end = segment.end;
    item.sourceStart = segment.sourceStart;
    item.sourceEnd = segment.sourceEnd;
  }
  selectedSegmentIndex = Math.max(
    0,
    transcriptSegments.findIndex((segment) =>
      previousSegment?.sourceStart !== undefined
        ? Math.abs(Number(segment.sourceStart) - Number(previousSegment.sourceStart)) < 0.01
        : segment.text === previousSegment?.text,
    ),
  );
  pipTimelineSeek.max = String(duration);
  pipTimelineRulerSignature = "";
  renderSegmentList();
  renderGeneratedList();
  renderTimelineRuler();
  renderTimelineSegments();
  if (transcriptSegments.length > 0) {
    selectTranscriptSegment(selectedSegmentIndex, { preservePreviewTime: true });
  }
  showPromptWriterStatus(
    cutDraftActive
      ? "当前文案和时间已按剪辑方案实时更新；点击生成视频会按当前预览一次合成。"
      : "",
    cutDraftActive ? "warning" : "",
  );
  persistEmbeddedPipDraft();
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
  if (data.type === "editor-suite:generate-video" && data.kind === "pip") {
    if (generatePipVideo.disabled) return;
    generateVideo(data.composition || null);
    return;
  }
  if (data.type === "editor-suite:sync-time") {
    const nextTime = clamp(Number(data.currentTime) || 0, 0, duration || Infinity);
    editorHostCurrentTime = nextTime;
    renderPreview({ timeOnly: true });
    return;
  }
  if (data.type === "editor-suite:timeline-action" && data.kind === "pip") {
    const item = pictureItems.find(
      (candidate) => String(candidate.id) === String(data.sourceId),
    );
    if (!item) return;
    selectedPictureItemId = item.id;
    syncPipTimelineModel();
    pipTimelineStore.selectClip(pipTimelineClipId(item.id), { silent: true });
    if (data.action === "set-range") {
      if (!updatePictureTimelineRange(item, data.start, data.end)) return;
      seekEditorPreview(Number(data.currentTime) || item.start);
      renderTimelineSegments();
      renderPreview();
      return;
    }
    if (data.action === "commit") {
      pipTimelineStore.commit("host-timeline");
      renderGeneratedList();
      renderTimelineSegments();
      renderPreview();
      return;
    }
    seekEditorPreview(Number(data.currentTime) || item.start);
    renderGeneratedList();
    renderTimelineSegments();
    renderPreview();
    return;
  }
  if (data.type === "editor-suite:select-pip-timeline" && data.kind === "pip") {
    const item = pictureItems.find(
      (candidate) => String(candidate.id) === String(data.id),
    );
    if (!item) return;
    selectedPictureItemId = item.id;
    seekEditorPreview(Number(data.currentTime) || item.start);
    renderGeneratedList();
    renderTimelineSegments();
    renderPreview();
    return;
  }
  if (data.type === "editor-suite:move-finish" && data.kind === "pip") {
    // The host drove a drag directly on its mirrored element; sync the list
    // readout and preview once here instead of on every pointermove.
    pipTimelineStore.commit("host-preview");
    renderGeneratedList();
    renderPreview();
    return;
  }
  if (data.type === "editor-suite:resize-effect" && data.kind === "pip") {
    const item = pictureItems.find(
      (candidate) => String(candidate.id) === String(data.id),
    );
    if (!item) return;
    item.width = clamp(Number(data.width) || item.width, PIP_MIN_WIDTH, PIP_MAX_WIDTH);
    selectedPictureItemId = item.id;
    syncPipTimelineModel();
    pipTimelineStore.patchClipPayload(
      pipTimelineClipId(item.id),
      { width: item.width },
      { silent: true },
    );
    return;
  }
  if (data.type !== "editor-suite:move-effect" || data.kind !== "pip") return;
  const item = pictureItems.find((candidate) => String(candidate.id) === String(data.id));
  if (!item) return;
  item.x = clamp(Number(data.x) || 0.5, 0.05, 0.95);
  item.y = clamp(Number(data.y) || 0.5, 0.05, 0.95);
  selectedPictureItemId = item.id;
  syncPipTimelineModel();
  pipTimelineStore.patchClipPayload(
    pipTimelineClipId(item.id),
    { x: item.x, y: item.y, width: item.width },
    { silent: true },
  );
}

window.addEventListener("message", handleEditorHostMessage);

const pipGenerationObserver = new MutationObserver(notifyEditorHost);
pipGenerationObserver.observe(generatePipVideo, {
  attributes: true,
  childList: true,
  subtree: true,
  attributeFilter: ["disabled"],
});
pipGenerationObserver.observe(outputProgress, {
  attributes: true,
  attributeFilter: ["hidden"],
});
pipGenerationObserver.observe(outputError, {
  attributes: true,
  childList: true,
  subtree: true,
  attributeFilter: ["hidden"],
});

function selectTranscriptSegment(index, options = {}) {
  if (!transcriptSegments[index]) return;
  selectedSegmentIndex = index;
  const segment = transcriptSegments[index];
  fitPipToTranscript.disabled = false;
  pipStartTime.disabled = false;
  pipEndTime.disabled = false;
  showPromptWriterStatus("");
  setPipTimeRange(segment.start, segment.end);
  selectedSegmentTime.textContent = formatRange(segment.start, segment.end);
  if (!options.preservePreviewTime) {
    seekEditorPreview(segment.start);
  }
  renderSegmentList();
  renderPreview();
  persistEmbeddedPipDraft();
}

function renderSegmentList() {
  segmentList.replaceChildren();
  if (transcriptSegments.length === 0) {
    fitPipToTranscript.disabled = true;
    pipStartTime.disabled = true;
    pipEndTime.disabled = true;
    const empty = document.createElement("div");
    empty.className = "pip-empty-state";
    empty.textContent = "当前视频没有可选择的文字片段。";
    segmentList.append(empty);
    return;
  }

  transcriptSegments.forEach((segment, index) => {
    const label = document.createElement("label");
    label.className = "pip-segment-option";
    label.classList.toggle("is-selected", index === selectedSegmentIndex);
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "transcriptSegment";
    radio.value = String(index);
    radio.checked = index === selectedSegmentIndex;
    radio.addEventListener("change", () => selectTranscriptSegment(index));
    const copy = document.createElement("span");
    const time = document.createElement("time");
    const text = document.createElement("strong");
    time.textContent = formatTime(segment.start);
    text.textContent = segment.text;
    copy.append(time, text);
    label.append(radio, copy);
    segmentList.append(label);
  });
}

function placementSelect(item) {
  const select = document.createElement("select");
  select.setAttribute("aria-label", `设置“${item.text}”的位置`);
  const activeKey = presetKeyForCoordinates(item.x, item.y);
  if (activeKey === "custom") {
    const customOption = document.createElement("option");
    customOption.value = "custom";
    customOption.textContent = "自定义（已拖动）";
    customOption.selected = true;
    customOption.disabled = true;
    select.append(customOption);
  }
  for (const [key, preset] of Object.entries(POSITION_PRESETS)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = preset.label;
    option.selected = key === activeKey;
    select.append(option);
  }
  select.addEventListener("change", () => {
    const preset = POSITION_PRESETS[select.value];
    if (!preset) return;
    item.x = preset.x;
    item.y = preset.y;
    constrainPictureItemToStage(item);
    selectedPictureItemId = item.id;
    seekToPictureItem(item);
    renderGeneratedList();
    renderPreview();
  });
  return select;
}

function seekToPictureItem(item) {
  if (showingFinalVideo) setVideoSource(baseVideoUrl, false);
  seekEditorPreview(item.start + 0.02);
}

function renderGeneratedList() {
  generatedList.replaceChildren();
  generatedEmpty.hidden = pictureItems.length > 0;
  generatedCount.textContent = `${pictureItems.length} 个`;
  pipCount.textContent = `${pictureItems.length} / 20`;
  generatePipVideo.disabled = !pictureItems.some(
    (item) => item.enabled && isReadyAsset(item),
  );

  pictureItems.forEach((item, index) => {
    const ready = isReadyAsset(item);
    const card = document.createElement("article");
    card.className = "pip-generated-card";
    card.dataset.pictureId = item.id;
    card.classList.toggle("is-disabled", ready && !item.enabled);
    card.classList.toggle("is-selected", item.id === selectedPictureItemId);
    card.classList.toggle("is-processing", item.type === "video" && !ready && item.status !== "failed");
    card.classList.toggle("is-failed", item.status === "failed");
    if (item.type === "video" && !ready && item.status !== "failed") {
      card.style.setProperty("--pip-progress", `${clamp(item.progress || 10, 0, 100)}%`);
    }
    const previewButton = document.createElement("button");
    previewButton.type = "button";
    previewButton.className = "pip-image-preview-button";
    previewButton.setAttribute("aria-label", `在视频中预览：${item.text}`);
    previewButton.disabled = !ready;
    if (ready) {
      const media = document.createElement(item.type === "video" ? "video" : "img");
      media.src = item.assetUrl || item.imageUrl;
      if (item.type === "video") {
        media.muted = true;
        media.playsInline = true;
        media.preload = "metadata";
        media.setAttribute("aria-hidden", "true");
      } else {
        media.alt = "";
      }
      previewButton.append(media);
      if (item.type === "video") {
        const badge = document.createElement("span");
        badge.className = "pip-video-badge";
        badge.textContent = "视频";
        previewButton.append(badge);
      }
    } else {
      const placeholder = document.createElement("span");
      placeholder.className = "pip-asset-placeholder";
      placeholder.textContent = item.status === "failed" ? "生成失败" : `${item.progress || 10}%`;
      previewButton.append(placeholder);
    }
    previewButton.addEventListener("click", () => {
      if (!ready) return;
      selectedPictureItemId = item.id;
      seekToPictureItem(item);
      renderGeneratedList();
      renderTimelineSegments();
      renderPreview();
    });

    const content = document.createElement("div");
    content.className = "pip-generated-content";
    const top = document.createElement("div");
    top.className = "pip-generated-top";
    const enabledLabel = document.createElement("label");
    enabledLabel.className = "pip-enabled-toggle";
    const enabled = document.createElement("input");
    enabled.type = "checkbox";
    enabled.checked = item.enabled && ready;
    enabled.disabled = !ready;
    enabled.setAttribute("aria-label", `使用画中画：${item.text}`);
    enabled.addEventListener("change", () => {
      item.enabled = enabled.checked;
      renderGeneratedList();
      renderTimelineSegments();
      renderPreview();
    });
    enabledLabel.append(enabled, document.createTextNode("使用"));
    const time = document.createElement("time");
    time.textContent = `${formatRange(item.start, item.end)} · ${assetKindLabel(item)} · ${item.aspectRatio || "16:9"}`;
    top.append(enabledLabel, time);

    const text = document.createElement("p");
    text.textContent = item.text;
    const assetStatus = document.createElement("p");
    assetStatus.className = "pip-asset-status";
    if (item.type === "video" && !ready) {
      assetStatus.textContent =
        item.status === "failed"
          ? item.error || "Seedance 视频生成失败，请重新生成。"
          : item.stage || "Seedance 正在生成动态画面…";
    }
    const controls = document.createElement("div");
    controls.className = "pip-item-controls";
    controls.hidden = !ready;
    const positionLabel = document.createElement("label");
    positionLabel.append(document.createTextNode("位置"), placementSelect(item));
    const sizeLabel = document.createElement("label");
    const sizeText = document.createElement("span");
    sizeText.textContent = `大小 ${Math.round(item.width * 100)}%`;
    const size = document.createElement("input");
    size.type = "range";
    size.min = "20";
    size.max = "55";
    size.step = "1";
    size.value = String(Math.round(item.width * 100));
    size.setAttribute("aria-label", `调整“${item.text}”的大小`);
    size.addEventListener("input", () => {
      item.width = Number(size.value) / 100;
      constrainPictureItemToStage(item);
      selectedPictureItemId = item.id;
      sizeText.textContent = `大小 ${size.value}%`;
      seekToPictureItem(item);
      renderPreview();
      persistEmbeddedPipDraft();
    });
    sizeLabel.append(sizeText, size);
    controls.append(positionLabel, sizeLabel);
    content.append(top, text);
    if (assetStatus.textContent) content.append(assetStatus);
    content.append(controls);
    card.append(previewButton, content);
    generatedList.append(card);
  });
  persistEmbeddedPipDraft();
}

function updateAssetType() {
  const assetType = currentAssetType();
  for (const input of assetTypeInputs) {
    input.closest(".pip-mode-option")?.classList.toggle("is-selected", input.checked);
  }
  aspectRatioLegend.textContent = assetType === "video" ? "生成视频尺寸" : "生成图片尺寸";
  pipPromptLabel.textContent = assetType === "video" ? "视频提示词" : "图片提示词";
  pipPrompt.placeholder =
    assetType === "video"
      ? "例如：清晨城市天际线，云层缓慢流动，镜头轻微推进，电影感，蓝金色调"
      : "例如：清晨城市天际线，阳光穿过云层，电影感，蓝金色调";
  pipPromptHelp.textContent =
    assetType === "video"
      ? "Seedance 会生成 720P 动态镜头并匹配当前视频风格，通常需要数分钟；画面不会包含文字。"
      : "AI 会参考当前视频画面的色调、光线和质感；画面中不会生成文字。";
  updateGenerationMode();
}

function updateGenerationMode() {
  const mode = currentGenerationMode();
  const assetType = currentAssetType();
  for (const input of generationModeInputs) {
    input.closest(".pip-mode-option")?.classList.toggle("is-selected", input.checked);
  }
  promptField.hidden = mode === "auto";
  if (assetType === "video") {
    generatePipImage.textContent =
      mode === "auto" ? "AI 根据文字生成视频" : "使用 Seedance 生成视频";
  } else {
    generatePipImage.textContent =
      mode === "auto" ? "AI 根据文字智能生成" : "使用 AI 生成图片";
  }
  showMessage(imageError, "");
}

function showPromptWriterStatus(message, state = "") {
  promptWriterStatus.textContent = message || "";
  promptWriterStatus.dataset.state = state;
  promptWriterStatus.hidden = !message;
}

async function writePromptDraft() {
  const segment = selectedSegment();
  if (!segment) {
    showPromptWriterStatus("请先选择要插入画中画的文字片段。", "error");
    segmentList.focus?.();
    return;
  }
  const timeRange = currentPipTimeRange();
  if (!timeRange) {
    showPromptWriterStatus("请先修正画中画显示时间。", "error");
    return;
  }

  const assetType = currentAssetType();
  const buttonLabel = writePipPrompt.querySelector("span");
  showMessage(imageError, "");
  showPromptWriterStatus("AI 正在结合文案和视频风格编写提示词…");
  writePipPrompt.disabled = true;
  writePipPrompt.setAttribute("aria-busy", "true");
  pipPrompt.readOnly = true;
  if (buttonLabel) buttonLabel.textContent = "AI 正在编写…";
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/picture-in-picture/prompt`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: segment.text,
          start: timeRange.start,
          end: timeRange.end,
          assetType,
          source: requestedSource,
          aspectRatio: currentImageAspectRatio(),
          sourceStart: segment.sourceStart ?? null,
          sourceEnd: segment.sourceEnd ?? null,
        }),
      },
    );
    const payload = await parseResponse(response, "AI 提示词编写失败，请稍后重试。");
    const prompt = String(payload.prompt || "").trim();
    if (!prompt) throw new Error("AI 没有返回可用的提示词，请重新尝试。");
    pipPrompt.value = prompt;
    pipPrompt.focus();
    pipPrompt.setSelectionRange(prompt.length, prompt.length);
    showPromptWriterStatus(
      `已生成${assetType === "video" ? "视频" : "图片"}提示词草稿，可以继续修改。`,
      "success",
    );
  } catch (error) {
    showPromptWriterStatus(error.message, "error");
  } finally {
    writePipPrompt.disabled = false;
    writePipPrompt.removeAttribute("aria-busy");
    pipPrompt.readOnly = false;
    if (buttonLabel) buttonLabel.textContent = "AI 一键编写提示词";
  }
}

async function generateAsset() {
  const segment = selectedSegment();
  if (!segment) {
    showMessage(imageError, "请先选择要插入画中画的文字片段。");
    segmentList.focus?.();
    return;
  }
  const mode = currentGenerationMode();
  const assetType = currentAssetType();
  const prompt = pipPrompt.value.trim();
  if (mode === "custom" && !prompt) {
    showMessage(imageError, "请输入想要生成的画中画内容。");
    pipPrompt.focus();
    return;
  }
  const timeRange = currentPipTimeRange();
  if (!timeRange) {
    pipStartTime.focus();
    return;
  }
  if (pictureItems.length >= 20) {
    showMessage(imageError, "一个视频最多生成 20 个画中画素材。");
    return;
  }

  showMessage(imageError, "");
  imageProgress.dataset.assetType = assetType;
  imageProgress.classList.toggle("is-video-generation", assetType === "video");
  imageProgress.classList.toggle("is-image-generation", assetType !== "video");
  imageProgress.hidden = false;
  assetProgressText.textContent =
    assetType === "video"
      ? "正在创建 Seedance 视频任务，提交后可在下方查看生成进度…"
      : "Seedream 正在参考视频风格并生成图片，通常需要几十秒…";
  generatePipImage.disabled = true;
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/picture-in-picture/${assetType === "video" ? "videos" : "images"}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: segment.text,
          start: timeRange.start,
          end: timeRange.end,
          mode,
          prompt,
          source: requestedSource,
          aspectRatio: currentImageAspectRatio(),
          sourceStart: segment.sourceStart ?? null,
          sourceEnd: segment.sourceEnd ?? null,
        }),
      },
    );
    const record = await parseResponse(
      response,
      assetType === "video"
        ? "动态画中画任务创建失败，请稍后重试。"
        : "画中画图片生成失败，请稍后重试。",
    );
    pictureItems.push({
      ...record,
      type: record.type || assetType,
      sourceStart: segment.sourceStart ?? null,
      sourceEnd: segment.sourceEnd ?? null,
      x: 0.8,
      y: 0.2,
      width: 0.32,
      enabled: assetType !== "video" || record.status === "completed",
    });
    selectedPictureItemId = record.id;
    if (mode === "custom") pipPrompt.value = "";
    if (isReadyAsset(pictureItems.at(-1))) seekToPictureItem(pictureItems.at(-1));
    renderGeneratedList();
    renderTimelineSegments();
    renderPreview();
    generatedList.lastElementChild?.scrollIntoView({ block: "nearest" });
    if (assetType === "video" && record.status !== "completed") {
      pollGeneratedAssets();
    }
  } catch (error) {
    showMessage(imageError, error.message);
  } finally {
    imageProgress.hidden = true;
    generatePipImage.disabled = false;
  }
}

function mergeVideoAssetRecords(payload) {
  const records = (payload.pictureInPictureVideos || []).filter(
    (record) => (record.source || "art") === requestedSource,
  );
  for (const record of records) {
    const item = pictureItems.find((candidate) => candidate.id === record.id);
    if (!item) continue;
    const wasReady = isReadyAsset(item);
    Object.assign(item, record, { type: "video" });
    if (!wasReady && isReadyAsset(item)) {
      item.enabled = true;
      selectedPictureItemId = item.id;
      seekToPictureItem(item);
    }
    if (item.status === "failed") item.enabled = false;
  }
}

async function pollGeneratedAssets() {
  if (assetPollTimer) window.clearTimeout(assetPollTimer);
  assetPollTimer = null;
  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await parseResponse(response, "无法读取动态画中画生成进度。");
    job = payload;
    mergeVideoAssetRecords(payload);
    renderGeneratedList();
    renderTimelineSegments();
    renderPreview();
    const hasPending = pictureItems.some(
      (item) => item.type === "video" && ["queued", "processing"].includes(item.status),
    );
    if (hasPending) {
      assetPollTimer = window.setTimeout(pollGeneratedAssets, 2000);
    }
  } catch (error) {
    showMessage(imageError, error.message);
    assetPollTimer = window.setTimeout(pollGeneratedAssets, 3500);
  }
}

function setOutputProgress(progress, stage) {
  const value = clamp(Math.round(Number(progress) || 0), 0, 100);
  outputProgress.hidden = false;
  outputProgress.dataset.progress = String(value);
  outputProgress.classList.toggle("is-completing", value >= 82);
  outputStatus.textContent = stage || "正在生成画中画视频…";
  outputPercent.textContent = `${value}%`;
  outputProgressTrack.setAttribute("aria-valuenow", String(value));
  outputProgressBar.style.width = `${value}%`;
  outputStatusChip.hidden = false;
  outputStatusChip.textContent = value < 100 ? "生成中" : "已完成";
}

function renderPictureInPictureJob(pictureInPicture) {
  if (!pictureInPicture) return;
  if (["queued", "processing"].includes(pictureInPicture.status)) {
    outputResult.hidden = true;
    generatePipVideo.disabled = true;
    setOutputProgress(pictureInPicture.progress, pictureInPicture.stage);
    if (!generationModalActive) {
      generationModalActive = true;
      window.appGeneration?.show({
        title: "生成画中画视频",
        progress: pictureInPicture.progress,
        status: pictureInPicture.stage || "正在生成画中画视频…",
        onClose: () => {
          generationModalActive = false;
        },
        onCancel: () => void cancelPipGeneration(),
      });
    } else {
      window.appGeneration?.setProgress(
        pictureInPicture.progress,
        pictureInPicture.stage,
      );
    }
    return;
  }
  if (pictureInPicture.status === "completed") {
    setOutputProgress(100, pictureInPicture.stage || "画中画视频生成完成");
    outputProgress.hidden = true;
    outputStatusChip.hidden = false;
    outputStatusChip.textContent = "已完成";
    finalVideoUrl = pictureInPicture.outputUrl;
    downloadFinalVideo.href = `${finalVideoUrl}?download=true`;
    outputResult.hidden = false;
    generatePipVideo.disabled = !pictureItems.some(
      (item) => item.enabled && isReadyAsset(item),
    );
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.complete({
        videoUrl: pictureInPicture.outputUrl,
        downloadUrl: `${pictureInPicture.outputUrl}?download=true`,
        redirectOnClose: embeddedEditor ? null : "/",
      });
    }
    return;
  }
  if (pictureInPicture.status === "failed") {
    outputProgress.hidden = true;
    outputStatusChip.hidden = true;
    generatePipVideo.disabled = !pictureItems.some(
      (item) => item.enabled && isReadyAsset(item),
    );
    showMessage(outputError, pictureInPicture.error || "画中画视频生成失败，请重试。");
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.fail(
        pictureInPicture.error || "画中画视频生成失败，请重试。",
      );
    }
  }
  if (pictureInPicture.status === "cancelled") {
    outputProgress.hidden = true;
    outputStatusChip.hidden = true;
    generatePipVideo.disabled = !pictureItems.some(
      (item) => item.enabled && isReadyAsset(item),
    );
    showMessage(outputError, "已取消生成。");
  }
}

async function cancelPipGeneration() {
  if (!jobId) return;
  if (pollTimer) window.clearTimeout(pollTimer);
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/cancel`,
      { method: "POST" },
    );
    const payload = await parseResponse(response, "无法取消生成。");
    job = payload;
    updateEditorSuiteJobState(payload);
    renderPictureInPictureJob(pictureInPictureForSource(payload));
    window.appGeneration?.fail("已取消生成。");
  } catch (error) {
    window.appGeneration?.fail(error.message || "取消失败，请重试。");
  }
}

async function pollPictureInPictureJob() {
  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await parseResponse(response, "无法读取视频生成进度。");
    job = payload;
    updateEditorSuiteJobState(payload);
    const activePictureInPicture = pictureInPictureForSource(payload);
    renderPictureInPictureJob(activePictureInPicture);
    if (["queued", "processing"].includes(activePictureInPicture?.status)) {
      pollTimer = window.setTimeout(pollPictureInPictureJob, 1200);
    }
  } catch (error) {
    outputProgress.hidden = true;
    generatePipVideo.disabled = !pictureItems.some(
      (item) => item.enabled && isReadyAsset(item),
    );
    showMessage(outputError, error.message);
  }
}

async function generateVideo(composition = null) {
  const enabledItems = pictureItems.filter(
    (item) => item.enabled && isReadyAsset(item),
  );
  if (enabledItems.length === 0) {
    showMessage(outputError, "请至少生成并启用一个画中画素材。");
    return;
  }
  showMessage(outputError, "");
  outputResult.hidden = true;
  generatePipVideo.disabled = true;
  setOutputProgress(5, "正在创建画中画合成任务…");
  const overlays = enabledItems.map((item) => ({
    assetId: item.id,
    start: item.start,
    end: item.end,
    sourceStart: item.sourceStart ?? null,
    sourceEnd: item.sourceEnd ?? null,
    x: item.x,
    y: item.y,
    width: item.width,
  }));
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
  const artPayload =
    composition?.art ||
    (job?.art?.composition
      ? {
          source: job.art.source || "original",
          overlays: job.art.overlays || [],
        }
      : null);
  const endpoint = useComposition ? "compose" : "picture-in-picture";
  const requestPayload = useComposition
    ? {
        target: "pip",
        ranges: compositionRanges,
        artOverlays: Array.isArray(artPayload?.overlays)
          ? artPayload.overlays
          : [],
        artSource: artPayload?.source || "original",
        pictureInPictureOverlays: overlays,
        pictureInPictureSource: requestedSource,
        historyName: null,
      }
    : {
        source: requestedSource,
        overlays,
      };
  try {
    const response = await fetch(
      `/api/transcriptions/${encodeURIComponent(jobId)}/${endpoint}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload),
      },
    );
    const result = await parseResponse(response, "无法创建画中画视频。");
    renderPictureInPictureJob(result);
    pollPictureInPictureJob();
  } catch (error) {
    outputProgress.hidden = true;
    generatePipVideo.disabled = false;
    showMessage(outputError, error.message);
    if (generationModalActive) {
      generationModalActive = false;
      window.appGeneration?.fail(error.message);
    }
  }
}

function restorePictureItems(payload) {
  const activePictureInPicture = pictureInPictureForSource(payload);
  const renderedOverlays = new Map(
    (activePictureInPicture?.overlays || []).map((overlay) => [
      overlay.assetId || overlay.imageId,
      overlay,
    ]),
  );
  const hasRenderedSelection = renderedOverlays.size > 0;
  const imageRecords = (payload.pictureInPictureImages || []).map((record) => ({
    ...record,
    type: "image",
    status: "completed",
    assetUrl: record.assetUrl || record.imageUrl,
  }));
  const videoRecords = (payload.pictureInPictureVideos || []).map((record) => ({
    ...record,
    type: "video",
  }));
  pictureItems = [...imageRecords, ...videoRecords]
    .filter((record) => (record.source || "art") === requestedSource)
    .sort((left, right) => String(left.createdAt || "").localeCompare(String(right.createdAt || "")))
    .map((record) => {
    const rendered = renderedOverlays.get(record.id);
    const ready = isReadyAsset(record);
    return {
      ...record,
      x: Number(rendered?.x ?? 0.8),
      y: Number(rendered?.y ?? 0.2),
      width: Number(rendered?.width ?? 0.32),
      enabled: ready && (hasRenderedSelection ? Boolean(rendered) : true),
    };
    });
}

function pictureInPictureForSource(payload) {
  const pictureInPicture = payload.pictureInPicture;
  if (!pictureInPicture) return null;
  return (pictureInPicture.source || "art") === requestedSource
    ? pictureInPicture
    : null;
}

async function initialize() {
  if (!JOB_ID_PATTERN.test(jobId)) {
    showPageError("链接中缺少有效的视频任务，请先上传并完成文字识别。");
    return;
  }
  const editUrl = `/?job=${encodeURIComponent(jobId)}`;
  const artUrl = `/art-text?job=${encodeURIComponent(jobId)}`;
  brandLink.href = editUrl;
  backToArtText.href = requestedSource === "art" ? artUrl : editUrl;
  pageErrorBack.href = backToArtText.href;
  if (requestedSource !== "art") {
    backToArtText.textContent =
      requestedSource === "edited" ? "返回视频剪辑" : "返回文字编辑";
    pageErrorBack.textContent = backToArtText.textContent;
  }

  try {
    const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
    const payload = await parseResponse(response, "无法读取视频信息。");
    if (payload.status !== "completed") {
      throw new Error("请等待文字识别完成后再插入画中画。");
    }
    job = payload;
    updateEditorSuiteJobState(payload);
    let transcript = null;
    if (requestedSource === "original") {
      if (payload.edit?.status) {
        throw new Error("该视频已经进入剪辑流程，请使用剪辑后的视频插入画中画。");
      }
      duration = Number(payload.duration) || 0;
      transcript = payload.result;
      baseVideoUrl =
        `/api/transcriptions/${encodeURIComponent(jobId)}/original-video`;
      pipSourceLabel.textContent = "原视频";
      pipEditWorkflowStep?.classList.remove("is-complete");
      pipArtWorkflowStep?.classList.remove("is-complete");
    } else if (requestedSource === "edited") {
      if (payload.edit?.status !== "completed" || !payload.edit.outputUrl) {
        throw new Error("请先完成视频剪辑，或选择直接处理原视频。");
      }
      duration = Number(payload.edit.outputDuration) || 0;
      transcript = payload.edit.transcript;
      baseVideoUrl = payload.edit.outputUrl;
      pipSourceLabel.textContent = "剪辑视频";
      pipArtWorkflowStep?.classList.remove("is-complete");
    } else {
      if (payload.art?.status !== "completed" || !payload.art.outputUrl) {
        throw new Error("请先生成艺术字视频，或选择直接处理原视频。");
      }
      const artSource = payload.art.source === "original" ? "original" : "edited";
      const sourceArtUrl =
        `/art-text?job=${encodeURIComponent(jobId)}` +
        `&source=${encodeURIComponent(artSource)}`;
      backToArtText.href = sourceArtUrl;
      pageErrorBack.href = sourceArtUrl;
      duration = Number(payload.art.outputDuration) || 0;
      transcript =
        artSource === "original" ? payload.result : payload.edit?.transcript;
      baseVideoUrl = payload.art.outputUrl;
      pipSourceLabel.textContent = "艺术字视频";
      if (artSource === "original") {
        pipEditWorkflowStep?.classList.remove("is-complete");
      }
    }
    transcriptSegments = (transcript?.segments || [])
      .filter((segment) => String(segment.text || "").trim())
      .map((segment) => ({
        text: String(segment.text).trim(),
        start: clamp(Number(segment.start) || 0, 0, duration),
        end: clamp(Number(segment.end) || 0, 0, duration),
      }))
      .filter((segment) => segment.end > segment.start);
    restorePictureItems(payload);
    pipTimelineSeek.max = String(duration);
    pipVideo.src = `${baseVideoUrl}?v=${Date.now()}`;
    renderSegmentList();
    renderGeneratedList();
    const activePictureInPicture = pictureInPictureForSource(payload);
    renderPictureInPictureJob(activePictureInPicture);
    pageLoading.hidden = true;
    pageError.hidden = true;
    pipWorkspace.hidden = false;
    pipEditorReady = true;
    if (pendingCutDraft?.transcript) applyEditorCutDraft(pendingCutDraft);
    restoreEmbeddedPipDraft();
    pipTimelineRulerSignature = "";
    renderTimelineRuler();
    renderTimelineSegments();
    if (transcriptSegments.length > 0 && selectedSegmentIndex < 0) {
      selectTranscriptSegment(0, { preservePreviewTime: embeddedEditor });
    }
    if (["queued", "processing"].includes(activePictureInPicture?.status)) {
      pollPictureInPictureJob();
    }
    if (
      pictureItems.some(
        (item) => item.type === "video" && ["queued", "processing"].includes(item.status),
      )
    ) {
      pollGeneratedAssets();
    }
  } catch (error) {
    showPageError(error.message);
  }
}

async function restartProject() {
  const confirmed = await window.appConfirm({
    eyebrow: "画中画设置检查",
    title: "确定重新开始？",
    message: "当前尚未生成的画中画设置不会保留，已经生成的素材仍会保留。",
    confirmText: "重新开始",
    icon: "ph:arrow-counter-clockwise-bold",
  });
  if (!confirmed) return;
  if (pollTimer) window.clearTimeout(pollTimer);
  if (assetPollTimer) window.clearTimeout(assetPollTimer);
  try {
    window.sessionStorage.removeItem("currentTranscriptionJobId");
  } catch {
    // Returning to upload still works without browser storage.
  }
  window.location.href = "/";
}

for (const input of assetTypeInputs) {
  input.addEventListener("change", () => {
    updateAssetType();
    showPromptWriterStatus("");
    persistEmbeddedPipDraft();
  });
}
for (const input of generationModeInputs) {
  input.addEventListener("change", () => {
    updateGenerationMode();
    persistEmbeddedPipDraft();
  });
}
for (const input of aspectRatioInputs) {
  input.addEventListener("change", () => {
    updateAspectRatioSelection();
    persistEmbeddedPipDraft();
  });
}
generatePipImage.addEventListener("click", generateAsset);
writePipPrompt.addEventListener("click", writePromptDraft);
fitPipToTranscript.addEventListener("click", fitPipTimeToTranscript);
for (const input of [pipStartTime, pipEndTime]) {
  input.addEventListener("change", () => {
    const range = currentPipTimeRange();
    if (!range) return;
    seekEditorPreview(range.start);
    renderPreview();
  });
}
pipPrompt.addEventListener("input", () => {
  if (promptWriterStatus.dataset.state === "success") showPromptWriterStatus("");
  persistEmbeddedPipDraft();
});
generatePipVideo.addEventListener("click", generateVideo);
restartProjectButton.addEventListener("click", restartProject);
previewFinalVideo.addEventListener("click", () => {
  if (!finalVideoUrl) return;
  setVideoSource(showingFinalVideo ? baseVideoUrl : finalVideoUrl, !showingFinalVideo);
});
pipVideo.addEventListener("loadedmetadata", () => {
  syncVideoStageLayout();
  renderTimelinePlayhead();
  pipTimelineRulerSignature = "";
  renderTimelineRuler();
  renderPreview();
  buildPipTimelineThumbnails({ force: true });
});
pipVideo.addEventListener("timeupdate", renderPreview);
pipVideo.addEventListener("seeking", () => {
  if (embeddedEditor) {
    editorHostCurrentTime = clamp(
      Number(pipVideo.currentTime) || 0,
      0,
      duration || Infinity,
    );
    window.parent.postMessage(
      {
        type: "editor-suite:seek",
        kind: "pip",
        currentTime: pipVideo.currentTime || 0,
      },
      window.location.origin,
    );
  }
  renderPreview();
});
pipVideo.addEventListener("play", renderPreview);
pipVideo.addEventListener("pause", renderPreview);
pipTimelineSeek.addEventListener("input", () => {
  seekEditorPreview(pipTimelineSeek.value);
});
pipTimelineSegments.addEventListener(
  "pointerdown",
  beginPipTimelineSegmentAdjustment,
);
pipTimelineTrack.addEventListener("pointerdown", (event) => {
  if (event.target.closest(".pip-timeline-segment")) return;
  const bounds = pipTimelineTrack.getBoundingClientRect();
  const ratio = clamp((event.clientX - bounds.left) / bounds.width, 0, 1);
  seekEditorPreview(ratio * duration);
});
window.addEventListener("resize", () => {
  syncVideoStageLayout();
  schedulePipTimelineRebuild();
});

for (const container of mediaControlGroups) {
  setupExternalVideoControls(container);
}
updateAssetType();
updateAspectRatioSelection();
initialize();
