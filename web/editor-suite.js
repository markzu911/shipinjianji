(() => {
  const root = document.querySelector("[data-editor-suite-nav]");
  if (!root) return;

  const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;
  const stage = root.dataset.stage || "cut";
  const embeddedEditor = new URLSearchParams(window.location.search).get("embedded") === "1";
  const toolLabels = {
    cut: "视频剪辑",
    art: "艺术字",
    pip: "画中画",
  };

  root.innerHTML = `
    <nav class="editor-suite-nav" aria-label="统一视频编辑工作台">
      <div class="editor-suite-copy">
        <span class="editor-suite-kicker">同一视频工程</span>
        <strong>创作工作台</strong>
        <small>剪辑、艺术字和画中画共享预览与时间轴</small>
      </div>
      <ol class="editor-suite-tools">
        <li>
          <a class="editor-suite-tool" data-editor-tool="cut" href="/">
            <span class="editor-suite-index">1</span>
            <span><strong>视频剪辑</strong><small data-editor-tool-state="cut">上传或选择视频</small></span>
          </a>
        </li>
        <li>
          <a class="editor-suite-tool" data-editor-tool="art" href="#" aria-disabled="true">
            <span class="editor-suite-index">2</span>
            <span><strong>艺术字</strong><small data-editor-tool-state="art">等待视频准备完成</small></span>
          </a>
        </li>
        <li>
          <a class="editor-suite-tool" data-editor-tool="pip" href="#" aria-disabled="true">
            <span class="editor-suite-index">3</span>
            <span><strong>画中画</strong><small data-editor-tool-state="pip">等待视频准备完成</small></span>
          </a>
        </li>
      </ol>
      <div class="editor-suite-project-state" aria-live="polite">
        <span class="editor-suite-state-dot" aria-hidden="true"></span>
        <span data-editor-suite-status>上传视频后，三个工具会在同一任务中启用。</span>
        <a
          class="editor-suite-download-button"
          data-editor-suite-download
          href="#"
          aria-label="下载当前预览成片"
          title="下载当前预览成片"
          hidden
        >
          <iconify-icon icon="ph:download-simple-bold" aria-hidden="true"></iconify-icon>
        </a>
        <button
          class="editor-suite-download-button editor-suite-save-button"
          type="button"
          data-editor-suite-save
          aria-label="保存当前版本"
          title="保存当前版本"
          hidden
        >
          <iconify-icon icon="ph:bookmark-simple-bold" aria-hidden="true"></iconify-icon>
        </button>
        <button
          class="editor-suite-generate-button"
          type="button"
          data-editor-suite-generate
          aria-label="生成视频"
          disabled
        >
          <iconify-icon icon="ph:scissors-bold" aria-hidden="true"></iconify-icon>
          <span>剪辑视频</span>
        </button>
      </div>
    </nav>
  `;

  const tools = new Map(
    [...root.querySelectorAll("[data-editor-tool]")].map((element) => [
      element.dataset.editorTool,
      element,
    ]),
  );
  const states = new Map(
    [...root.querySelectorAll("[data-editor-tool-state]")].map((element) => [
      element.dataset.editorToolState,
      element,
    ]),
  );
  const status = root.querySelector("[data-editor-suite-status]");
  const inspector = document.querySelector(".text-editor-inspector");
  const cutPanelStack = inspector?.querySelector(".text-editor-panel-stack");
  const inspectorHost = document.querySelector("#editorSuiteInspectorHost");
  const previewOverlay = document.querySelector("#editorSuitePreviewOverlay");
  const timelineLayer = document.querySelector("#editorSuiteTimelineLayer");
  const timelineTrack = document.querySelector("#cutFrameTimelineTrack");
  const previewVideo = document.querySelector("#cutPreviewVideo");
  const previewStage = document.querySelector("#cutVideoStage");
  const previewGrid = previewStage?.querySelector(".preview-grid");
  const previewGridToggle = document.querySelector(
    "[data-preview-grid-toggle]",
  );
  const douyinPreviewToggle = document.querySelector(
    "[data-douyin-preview-toggle]",
  );
  const douyinChrome = document.querySelector("#editorSuiteDouyinChrome");
  const generateButton = root.querySelector("[data-editor-suite-generate]");
  const downloadButton = root.querySelector("[data-editor-suite-download]");
  const saveButton = root.querySelector("[data-editor-suite-save]");
  const frameEntries = new Map();
  const toolStates = new Map();
  const toolBridgeRevisions = new Map();
  const desiredToolUrls = new Map();
  let activeTool = stage;
  let refreshToken = 0;
  let overlayResizeObserver = null;
  let renderedPreviewState = null;
  let renderedTimelineState = null;
  let frameSyncRequest = 0;
  let currentJob = null;
  let previousJobId = null;
  let douyinPreviewEnabled = false;
  let douyinBaseVideo = null;
  let previewGridStateBeforeDouyin = null;
  let cutDraftActive = false;
  let cutDraftState = {
    active: false,
    ranges: [],
    sourceDuration: 0,
    duration: 0,
    transcript: null,
  };
  const timelineStore = window.EditorTimeline.createStore({
    duration: 0,
    tracks: [],
  });
  const projectStoreEnabled = Boolean(
    stage === "cut" &&
      window.EditorProjectStore &&
      window.__EDITOR_PROJECT_STORE_ENABLED__ !== false,
  );
  const projectStore = projectStoreEnabled
    ? window.EditorProjectStore.createStore(
        { ui: { activeTool } },
        { timeline: window.EditorTimeline },
      )
    : null;

  function projectSnapshot() {
    return projectStore?.getState() || null;
  }

  function syncProjectTimeline() {
    if (!projectStoreEnabled) return timelineStore.snapshot();
    const documentState = projectStore.select(
      window.EditorProjectStore.selectTimelineDocument,
    );
    return timelineStore.replace(documentState, { silent: true });
  }

  function bridgeRevision(value) {
    if (value === undefined || value === null || value === "") return null;
    const revision = Number(value);
    return Number.isFinite(revision) ? revision : null;
  }

  function advanceToolBridgeRevision(name, revision) {
    const normalized = bridgeRevision(revision);
    if (!projectStoreEnabled || normalized === null) return;
    toolBridgeRevisions.set(
      name,
      Math.max(toolBridgeRevisions.get(name) ?? -1, normalized),
    );
  }

  function postProjectProjection(name, message) {
    const entry = frameEntries.get(name);
    if (!entry?.frame?.contentWindow) return;
    advanceToolBridgeRevision(name, message?.revision);
    entry.frame.contentWindow.postMessage(message, window.location.origin);
  }

  function acknowledgeToolProjection(name, state = projectSnapshot()) {
    const entry = frameEntries.get(name);
    if (!state || !entry?.frame?.contentWindow) return;
    entry.frame.contentWindow.postMessage({
      type: "editor-suite:project-ack",
      kind: name,
      revision: state.revision,
      timingRevision: state.timingRevision,
      changeKind: "tool-state-ack",
    }, window.location.origin);
  }

  function postTranscriptTextProjection(name, state = projectSnapshot()) {
    if (!state) return;
    postProjectProjection(
      name,
      {
        type: "editor-suite:transcript-text",
        kind: name,
        transcript:
          state.project.cut.transcript || state.project.transcript,
        editableSegments: state.project.editableSegments,
        art: state.project.art,
        revision: state.revision,
        timingRevision: state.timingRevision,
        changeKind: "transcript-text",
      },
    );
  }

  projectStore?.subscribe((next, previous, action) => {
    syncProjectTimeline();
    if (action.type === window.EditorProjectStore.ACTIONS.TRANSCRIPT_TEXT_CHANGED) {
      for (const name of ["art", "pip"]) postTranscriptTextProjection(name, next);
    }
    if (next.ui.activeTool !== previous.ui.activeTool) {
      activeTool = next.ui.activeTool;
    }
  });

  function syncToolTimeline(kind, timeline, options = {}) {
    if (!timeline || !Array.isArray(timeline.tracks)) return;
    const duration = Math.max(
      timelineStore.snapshot().duration,
      Number(timeline.duration) || 0,
    );
    timelineStore.setDuration(duration, { silent: true });
    const selection =
      options.selection !== undefined
        ? options.selection
        : kind === activeTool
          ? timeline.selection?.clipId || null
          : undefined;
    timelineStore.replaceKind(
      kind,
      timeline.tracks.filter((track) => track.kind === kind),
      { selection, silent: true },
    );
  }

  function supportsInlineWorkspace() {
    return Boolean(
      stage === "cut" &&
        inspector &&
        cutPanelStack &&
        inspectorHost &&
        previewOverlay &&
        timelineLayer &&
        previewVideo,
    );
  }

  function currentJobId() {
    const queryJobId = new URLSearchParams(window.location.search).get("job");
    if (queryJobId && JOB_ID_PATTERN.test(queryJobId)) return queryJobId;
    try {
      const storedJobId = window.sessionStorage.getItem(
        "currentTranscriptionJobId",
      );
      return storedJobId && JOB_ID_PATTERN.test(storedJobId)
        ? storedJobId
        : "";
    } catch {
      return "";
    }
  }

  function setToolLink(name, href, enabled = true) {
    const tool = tools.get(name);
    if (!tool) return;
    tool.href = enabled ? href : "#";
    tool.setAttribute("aria-disabled", String(!enabled));
    tool.tabIndex = enabled ? 0 : -1;
    if (name !== "cut" && enabled) desiredToolUrls.set(name, href);
  }

  function setToolState(name, label, complete = false) {
    const stateLabel = states.get(name);
    const tool = tools.get(name);
    if (stateLabel) stateLabel.textContent = label;
    if (tool) tool.classList.toggle("is-complete", complete);
  }

  function setDouyinPreviewAvailable(enabled) {
    if (douyinPreviewToggle) {
      douyinPreviewToggle.disabled = !enabled;
      douyinPreviewToggle.setAttribute("aria-disabled", String(!enabled));
      douyinPreviewToggle.tabIndex = enabled ? 0 : -1;
    }
    if (!enabled) setDouyinPreviewEnabled(false);
  }

  function setDouyinPreviewEnabled(enabled) {
    const nextEnabled = Boolean(enabled && currentJob?.id);
    if (nextEnabled && !douyinPreviewEnabled) {
      previewGridStateBeforeDouyin = previewGrid
        ? !previewGrid.hidden
        : null;
      if (previewGrid) previewGrid.hidden = true;
      if (previewGridToggle) {
        previewGridToggle.disabled = true;
        previewGridToggle.setAttribute("aria-pressed", "false");
        previewGridToggle.title = "抖音发布预览中不显示构图辅助线";
      }
    } else if (!nextEnabled && douyinPreviewEnabled) {
      if (previewGrid && previewGridStateBeforeDouyin !== null) {
        previewGrid.hidden = !previewGridStateBeforeDouyin;
      }
      if (previewGridToggle) {
        previewGridToggle.disabled = false;
        previewGridToggle.setAttribute(
          "aria-pressed",
          String(Boolean(previewGridStateBeforeDouyin)),
        );
        previewGridToggle.title = "九宫格构图辅助线";
      }
      previewGridStateBeforeDouyin = null;
    }
    douyinPreviewEnabled = nextEnabled;
    previewStage?.classList.toggle(
      "is-douyin-preview",
      douyinPreviewEnabled,
    );
    if (douyinChrome) {
      douyinChrome.hidden = !douyinPreviewEnabled;
      douyinChrome.setAttribute(
        "aria-hidden",
        String(!douyinPreviewEnabled),
      );
    }
    if (douyinPreviewToggle) {
      douyinPreviewToggle.setAttribute(
        "aria-pressed",
        String(douyinPreviewEnabled),
      );
      douyinPreviewToggle.title = douyinPreviewEnabled
        ? "关闭抖音发布预览"
        : "抖音发布预览";
    }
    if (douyinPreviewEnabled) {
      previewStage?.setAttribute("data-preview-mode", "douyin");
    } else {
      previewStage?.removeAttribute("data-preview-mode");
    }
    updateDouyinBaseVideo();
    window.dispatchEvent(new Event("resize"));
    renderMirroredPreview();
    syncMirroredPlayback();
  }

  function editedDouyinVideoUrl() {
    if (
      !douyinPreviewEnabled ||
      currentJob?.edit?.status !== "completed" ||
      !currentJob.edit.outputUrl
    ) {
      return "";
    }
    return String(currentJob.edit.outputUrl);
  }

  function ensureDouyinBaseVideo() {
    if (douyinBaseVideo || !previewVideo) return douyinBaseVideo;
    douyinBaseVideo = document.createElement("video");
    douyinBaseVideo.className = "editor-suite-douyin-base-video";
    douyinBaseVideo.muted = true;
    douyinBaseVideo.playsInline = true;
    douyinBaseVideo.preload = "metadata";
    douyinBaseVideo.setAttribute("aria-hidden", "true");
    douyinBaseVideo.tabIndex = -1;
    douyinBaseVideo.addEventListener("loadedmetadata", () => {
      syncDouyinBasePlayback(true);
    });
    previewVideo.insertAdjacentElement("afterend", douyinBaseVideo);
    return douyinBaseVideo;
  }

  function updateDouyinBaseVideo() {
    if (!previewStage) return;
    const editedUrl = editedDouyinVideoUrl();
    const useEditedBase = Boolean(editedUrl);
    previewStage.classList.toggle("has-douyin-edited-base", useEditedBase);
    previewStage.dataset.douyinVideoSource = useEditedBase
      ? "edited"
      : cutDraftActive
        ? "cut-draft"
        : "original";
    if (!useEditedBase) {
      douyinBaseVideo?.pause();
      return;
    }
    const video = ensureDouyinBaseVideo();
    if (!video) return;
    if (video.dataset.sourceUrl !== editedUrl) {
      video.dataset.sourceUrl = editedUrl;
      const version = encodeURIComponent(
        currentJob?.edit?.updatedAt || currentJob?.updatedAt || "",
      );
      video.src = `${editedUrl}${editedUrl.includes("?") ? "&" : "?"}v=${version}`;
      video.load();
      return;
    }
    syncDouyinBasePlayback();
  }

  function syncDouyinBasePlayback(force = false) {
    if (
      !douyinPreviewEnabled ||
      !previewStage?.classList.contains("has-douyin-edited-base") ||
      !douyinBaseVideo ||
      !previewVideo
    ) {
      return;
    }
    const editedTime = workspaceCurrentTime();
    if (
      douyinBaseVideo.readyState >= 1 &&
      (force || Math.abs((Number(douyinBaseVideo.currentTime) || 0) - editedTime) > 0.24)
    ) {
      douyinBaseVideo.currentTime = Math.min(
        editedTime,
        Math.max(0, (Number(douyinBaseVideo.duration) || editedTime) - 0.01),
      );
    }
    if (!previewVideo.paused && !previewVideo.ended) {
      douyinBaseVideo.play().catch(() => {});
    } else {
      douyinBaseVideo.pause();
    }
  }

  function previewCompositionState() {
    if (projectStoreEnabled) {
      const request = projectStore.select(
        window.EditorProjectStore.selectCompositionRequest,
      );
      return {
        ranges: request.ranges,
        art: {
          source: request.artSource,
          overlays: request.artOverlays,
        },
        pictureInPicture: {
          source: request.pictureInPictureSource,
          overlays: request.pictureInPictureOverlays,
        },
      };
    }
    const ranges = cutDraftActive
      ? cutDraftState.ranges
      : currentJob?.edit?.status === "completed"
        ? currentJob.edit.requestedRanges || currentJob.edit.ranges || []
        : [];
    const art = toolStates.get("art")?.generationPayload || (
      currentJob?.art?.overlays
        ? {
            source: currentJob.art.source || "original",
            overlays: currentJob.art.overlays,
          }
        : { overlays: [] }
    );
    const pictureInPicture = toolStates.get("pip")?.generationPayload || (
      currentJob?.pictureInPicture?.overlays
        ? {
            source: currentJob.pictureInPicture.source || "original",
            overlays: currentJob.pictureInPicture.overlays,
          }
        : { overlays: [] }
    );
    return {
      ranges: Array.isArray(ranges) ? ranges : [],
      art,
      pictureInPicture,
    };
  }

  function compositionRequest() {
    if (projectStoreEnabled) {
      return projectStore.select(
        window.EditorProjectStore.selectCompositionRequest,
      );
    }
    const composition = previewCompositionState();
    return {
      target: "all",
      ranges: composition.ranges,
      artOverlays: composition.art?.overlays || [],
      artSource: composition.art?.source || "original",
      pictureInPictureOverlays:
        composition.pictureInPicture?.overlays || [],
      pictureInPictureSource:
        composition.pictureInPicture?.source || "original",
      historyName: null,
    };
  }

  function stableValue(value) {
    if (Array.isArray(value)) return value.map(stableValue);
    if (!value || typeof value !== "object") return value;
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stableValue(value[key])]),
    );
  }

  function compositionVisualSignature(value) {
    if (!value) return "";
    const { target, historyName, ...visual } = value;
    return JSON.stringify(stableValue(visual));
  }

  function currentPreviewMatchesComposition() {
    return (
      currentJob?.composition?.status === "completed" &&
      compositionVisualSignature(compositionRequest()) ===
        compositionVisualSignature(currentJob.composition.request)
    );
  }

  function compositionBusy() {
    return ["queued", "processing"].includes(
      currentJob?.composition?.status,
    );
  }

  function compositionReady() {
    return currentJob?.status === "completed" && !compositionBusy();
  }

  function currentManualHistoryKind() {
    if (compositionBusy() || currentJob?.composition?.status === "completed") return "";
    if (
      activeTool === "cut" &&
      !cutDraftActive &&
      currentJob?.edit?.status === "completed" &&
      !currentJob.edit.historyId
    ) {
      return "edited";
    }
    if (
      activeTool === "art" &&
      currentJob?.art?.status === "completed" &&
      !currentJob.art.composition &&
      !currentJob.art.historyId
    ) {
      return "art";
    }
    return "";
  }

  function syncSaveButton() {
    if (!saveButton) return;
    const kind = currentManualHistoryKind();
    saveButton.hidden = !kind;
    saveButton.disabled = !kind || saveButton.getAttribute("aria-busy") === "true";
    saveButton.dataset.historyKind = kind;
    const label = kind === "art" ? "保存艺术字版本" : "保存剪辑版本";
    saveButton.title = label;
    saveButton.setAttribute("aria-label", label);
  }

  function syncGenerationButton() {
    if (!generateButton) return;
    const state = {
      disabled: !compositionReady(),
      busy: compositionBusy(),
      error: String(currentJob?.composition?.error || ""),
    };
    const label = generateButton.querySelector("span");
    generateButton.disabled = state.disabled;
    generateButton.classList.toggle("is-busy", state.busy);
    generateButton.setAttribute("aria-busy", String(state.busy));
    generateButton.dataset.generationKind = "all";
    if (label) {
      label.textContent = state.busy ? "生成中…" : "剪辑视频";
    }
    generateButton.title = state.disabled && !state.busy
      ? "视频准备完成后即可把当前预览导出为成片"
      : state.busy
        ? "当前预览正在生成"
      : "按当前预览合成剪辑、艺术字和画中画";
    generateButton.setAttribute(
      "aria-label",
      state.busy ? "当前预览视频生成中" : "剪辑当前预览视频",
    );
    const outputUrl = currentJob?.composition?.outputUrl;
    const outputMatchesPreview = currentPreviewMatchesComposition();
    if (downloadButton) {
      downloadButton.hidden = !outputUrl || !outputMatchesPreview;
      downloadButton.href = outputUrl ? `${outputUrl}?download=true` : "#";
    }
    syncSaveButton();
    if (state.error) {
      status.textContent = state.error;
      root.dataset.state = "error";
    } else if (state.busy) {
      status.textContent = "正在按当前预览合成视频，请稍候…";
      root.dataset.state = "working";
    } else if (currentJob?.composition?.status === "completed" && !outputMatchesPreview) {
      status.textContent = "当前预览有未生成的更改，点击剪辑视频更新成片。";
      root.dataset.state = "ready";
    }
  }

  async function saveCurrentVersion() {
    const kind = currentManualHistoryKind();
    const jobId = currentJobId();
    if (!kind || !jobId || !saveButton) return;
    saveButton.disabled = true;
    saveButton.setAttribute("aria-busy", "true");
    status.textContent = "正在保存当前版本…";
    try {
      const response = await fetch(
        `/api/transcriptions/${encodeURIComponent(jobId)}/history`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind, name: null }),
        },
      );
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "无法保存当前版本。");
      const resultKey = kind === "edited" ? "edit" : "art";
      currentJob[resultKey] = {
        ...currentJob[resultKey],
        historyId: payload.id,
        historyName: payload.name,
      };
      status.textContent = `已保存“${payload.name}”`;
      root.dataset.state = "complete";
    } catch (error) {
      status.textContent = error.message;
      root.dataset.state = "error";
    } finally {
      saveButton.setAttribute("aria-busy", "false");
      syncSaveButton();
    }
  }

  let compositionPollTimer = null;

  async function generateCurrentPreview() {
    if (!compositionReady()) return;
    const jobId = currentJobId();
    if (!jobId) return;
    const request = compositionRequest();
    generateButton.disabled = true;
    generateButton.classList.add("is-busy");
    status.textContent = "正在创建当前预览合成任务…";
    root.dataset.state = "working";
    try {
      const response = await fetch(
        `/api/transcriptions/${encodeURIComponent(jobId)}/compose`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        },
      );
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "无法创建当前预览合成任务。");
      await refresh();
      window.appGeneration?.show({
        title: "合成成片",
        progress: Number(payload.progress) || 5,
        status: payload.stage || "正在生成当前预览…",
        onCancel: () => void cancelComposition(),
      });
      pollComposition(jobId);
    } catch (error) {
      status.textContent = error.message;
      root.dataset.state = "error";
      syncGenerationButton();
      window.appGeneration?.fail(error.message);
      if (
        window.handleExpiredTask &&
        /任务不存在|服务已重启|转写任务不存在/.test(error.message)
      ) {
        window.handleExpiredTask();
      }
    }
  }

  async function cancelComposition() {
    const jobId = currentJobId();
    if (!jobId) return;
    if (compositionPollTimer) window.clearTimeout(compositionPollTimer);
    try {
      const response = await fetch(
        `/api/transcriptions/${encodeURIComponent(jobId)}/cancel`,
        { method: "POST" },
      );
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "无法取消生成。");
      renderJobState(payload);
      syncGenerationButton();
      window.appGeneration?.fail("已取消生成。");
    } catch (error) {
      window.appGeneration?.fail(error.message || "取消失败，请重试。");
    }
  }

  function formatGenerationDuration(seconds) {
    const total = Math.max(0, Math.round(Number(seconds) || 0));
    const minutes = Math.floor(total / 60);
    const rest = total % 60;
    return `${minutes}:${String(rest).padStart(2, "0")}`;
  }

  async function pollComposition(jobId) {
    if (compositionPollTimer) window.clearTimeout(compositionPollTimer);
    try {
      const response = await fetch(`/api/transcriptions/${encodeURIComponent(jobId)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "无法读取合成进度。");
      renderJobState(payload);
      window.dispatchEvent(new CustomEvent("editor-suite:job-state", { detail: payload }));
      const composition = payload.composition;
      if (["queued", "processing"].includes(composition?.status)) {
        window.appGeneration?.setProgress(
          composition.progress,
          composition.stage,
        );
        compositionPollTimer = window.setTimeout(() => pollComposition(jobId), 900);
        return;
      }
      if (composition?.status === "completed") {
        const outputUrl = composition.outputUrl;
        window.appGeneration?.complete({
          videoUrl: outputUrl,
          downloadUrl: outputUrl ? `${outputUrl}?download=true` : null,
          duration: formatGenerationDuration(composition.outputDuration),
          redirectOnClose: embeddedEditor ? null : "/",
        });
        return;
      }
      if (composition?.status === "cancelled") {
        syncGenerationButton();
        return;
      }
      if (composition?.status === "failed") {
        window.appGeneration?.fail(
          composition.error || "合成失败，请重新尝试。",
        );
        return;
      }
    } catch (error) {
      status.textContent = error.message;
      root.dataset.state = "error";
      syncGenerationButton();
      window.appGeneration?.fail(error.message);
    }
  }

  function updateActiveTool() {
    for (const [name, tool] of tools) {
      const active = name === activeTool;
      tool.classList.toggle("is-active", active);
      if (active) tool.setAttribute("aria-current", "page");
      else tool.removeAttribute("aria-current");
    }
  }

  function toolFromHref(href) {
    if (!href || href === "#") return "";
    try {
      const url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return "";
      if (url.pathname === "/art-text") return "art";
      if (url.pathname === "/picture-in-picture") return "pip";
      if (url.pathname === "/") return "cut";
    } catch {
      return "";
    }
    return "";
  }

  function embeddedUrl(href) {
    const url = new URL(href, window.location.href);
    url.searchParams.set("embedded", "1");
    return `${url.pathname}${url.search}`;
  }

  function normalizedToolHref(href) {
    const url = new URL(href, window.location.href);
    url.searchParams.delete("embedded");
    url.searchParams.sort();
    return `${url.pathname}${url.search}`;
  }

  function workspaceCurrentTime() {
    const sourceTime = Number(previewVideo?.currentTime) || 0;
    const ranges = cutDraftState.ranges.length
      ? cutDraftState.ranges
      : currentJob?.edit?.status === "completed"
        ? currentJob.edit.requestedRanges || currentJob.edit.ranges || []
        : [];
    let removedBefore = 0;
    for (const range of ranges) {
      const start = Number(range.start) || 0;
      const end = Math.max(start, Number(range.end) || start);
      if (sourceTime >= end) {
        removedBefore += end - start;
        continue;
      }
      if (sourceTime > start) return Math.max(0, start - removedBefore);
      break;
    }
    return Math.max(0, sourceTime - removedBefore);
  }

  function workspaceSourceTime(editedTime) {
    let sourceTime = Math.max(0, Number(editedTime) || 0);
    let removedBefore = 0;
    const ranges = cutDraftState.ranges.length
      ? cutDraftState.ranges
      : currentJob?.edit?.status === "completed"
        ? currentJob.edit.requestedRanges || currentJob.edit.ranges || []
        : [];
    for (const range of ranges) {
      const start = Number(range.start) || 0;
      const end = Math.max(start, Number(range.end) || start);
      const editedRangeStart = Math.max(0, start - removedBefore);
      if (sourceTime < editedRangeStart) break;
      sourceTime += end - start;
      removedBefore += end - start;
    }
    return sourceTime;
  }

  function syncFrameCutDraft(name) {
    const message = projectStoreEnabled
      ? projectStore.select(window.EditorProjectStore.selectCutDraftMessage)
      : {
          type: "editor-suite:cut-draft",
          ...cutDraftState,
        };
    postProjectProjection(name, message);
  }

  function syncFrameTime(name = activeTool) {
    const entry = frameEntries.get(name);
    if (!entry?.frame?.contentWindow || !previewVideo) return;
    entry.frame.contentWindow.postMessage(
      {
        type: "editor-suite:sync-time",
        currentTime: workspaceCurrentTime(),
        playing: !previewVideo.paused,
      },
      window.location.origin,
    );
  }

  function createToolFrame(name, href) {
    const toolHref = normalizedToolHref(href);
    const panel = document.createElement("section");
    panel.className = "editor-suite-tool-panel is-loading";
    panel.dataset.editorSuitePanel = name;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-label", `${toolLabels[name]}设置`);
    panel.setAttribute("aria-hidden", "true");
    panel.setAttribute("inert", "");

    const frame = document.createElement("iframe");
    frame.className = "editor-suite-tool-frame";
    frame.title = `${toolLabels[name]}设置`;
    frame.loading = "eager";
    frame.dataset.toolHref = toolHref;
    frame.src = embeddedUrl(toolHref);
    frame.addEventListener("load", () => {
      panel.classList.remove("is-loading");
      syncFrameCutDraft(name);
      if (projectStoreEnabled) postTranscriptTextProjection(name);
      syncFrameTime(name);
    });
    panel.append(frame);
    inspectorHost.append(panel);
    const entry = { frame, panel };
    frameEntries.set(name, entry);
    return entry;
  }

  function ensureToolFrame(name, href) {
    const toolHref = normalizedToolHref(href);
    const current = frameEntries.get(name);
    if (!current) return createToolFrame(name, toolHref);
    if (current.frame.dataset.toolHref !== toolHref) {
      current.panel.classList.add("is-loading");
      current.frame.dataset.toolHref = toolHref;
      current.frame.src = embeddedUrl(toolHref);
      toolStates.delete(name);
      syncGenerationButton();
    }
    return current;
  }

  function updateBrowserTool(name, replace = false) {
    if (!supportsInlineWorkspace()) return;
    const url = new URL(window.location.href);
    if (name === "cut") url.searchParams.delete("tool");
    else url.searchParams.set("tool", name);
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({ ...(window.history.state || {}), editorTool: name }, "", url);
  }

  function syncMirroredPlayback() {
    syncDouyinBasePlayback();
    const canvas = previewOverlay?.querySelector(".editor-suite-preview-canvas");
    if (!canvas || !previewVideo) return;
    const current = Number(previewVideo.currentTime) || 0;
    const playing = !previewVideo.paused && !previewVideo.ended;
    for (const media of canvas.querySelectorAll("video")) {
      media.muted = true;
      media.loop = true;
      media.playsInline = true;
      const start = Number(media.closest("[data-effect-start]")?.dataset.effectStart) || 0;
      const syncMedia = () => {
        if (!Number.isFinite(media.duration) || media.duration <= 0) return;
        const localTime = Math.max(0, current - start) % media.duration;
        if (Math.abs((Number(media.currentTime) || 0) - localTime) > 0.35) {
          media.currentTime = localTime;
        }
        if (playing) media.play().catch(() => {});
        else media.pause();
      };
      if (media.readyState >= 1) syncMedia();
      else media.addEventListener("loadedmetadata", syncMedia, { once: true });
    }
  }

  function renderMirroredPreview() {
    if (!previewOverlay) return;
    const layers = ["art", "pip"]
      .map((kind) => ({ kind, state: toolStates.get(kind) }))
      .filter((layer) => layer.state?.overlayHtml)
      .map(({ kind, state }) => ({
        kind,
        html: state.overlayHtml,
        width: Math.max(1, Number(state.overlayWidth) || 1),
        height: Math.max(1, Number(state.overlayHeight) || 1),
      }));
    if (!layers.length) {
      if (renderedPreviewState?.signature || previewOverlay.children.length) {
        previewOverlay.replaceChildren();
      }
      renderedPreviewState = { signature: "" };
      overlayResizeObserver?.disconnect();
      previewOverlay.hidden = true;
      return;
    }

    const nextState = {
      signature: JSON.stringify({ layers, douyinPreviewEnabled }),
    };
    if (renderedPreviewState?.signature === nextState.signature) {
      previewOverlay.hidden = false;
      syncMirroredPlayback();
      return;
    }

    previewOverlay.replaceChildren();

    const canvases = layers.map((layer) => {
      const canvas = document.createElement("div");
      canvas.className = `editor-suite-preview-canvas is-${layer.kind}`;
      canvas.dataset.effectKind = layer.kind;
      canvas.style.width = `${layer.width}px`;
      canvas.style.height = `${layer.height}px`;
      canvas.innerHTML = layer.html;
      previewOverlay.append(canvas);
      return { canvas, layer };
    });
    previewOverlay.hidden = false;
    renderedPreviewState = nextState;

    const resize = () => {
      for (const { canvas, layer } of canvases) {
        const fitScale = douyinPreviewEnabled ? Math.max : Math.min;
        const scale = fitScale(
          previewOverlay.clientWidth / layer.width,
          previewOverlay.clientHeight / layer.height,
        );
        const left = (previewOverlay.clientWidth - layer.width * scale) / 2;
        const top = (previewOverlay.clientHeight - layer.height * scale) / 2;
        canvas.style.transform =
          `translate(${left}px, ${top}px) scale(${scale})`;
      }
    };
    resize();
    overlayResizeObserver?.disconnect();
    overlayResizeObserver = new ResizeObserver(resize);
    overlayResizeObserver.observe(previewOverlay);
    syncMirroredPlayback();
  }

  function renderMirroredTimeline() {
    if (!timelineLayer) return;
    const timelineStates = [
      ["art", toolStates.get("art")],
      ["pip", toolStates.get("pip")],
    ].filter(([, state]) => state?.timelineHtml);
    let timelineTrackOffset = 0;
    const timelineHtml = timelineStates.map(([kind, state]) => {
      const container = document.createElement("div");
      container.innerHTML = state.timelineHtml;
      for (const segment of container.children) {
        segment.dataset.effectKind = kind;
        const localTrackIndex = Number(segment.dataset.timelineTrackIndex) || 0;
        segment.dataset.timelineTrackIndex = String(
          timelineTrackOffset + localTrackIndex,
        );
        segment.style.top = `${(
          timelineTrackOffset + localTrackIndex
        ) * 30 + 2}px`;
      }
      timelineTrackOffset += Math.max(1, Number(state.timelineTrackCount) || 1);
      return container.innerHTML;
    }).join("");
    const showEffectTrack = Boolean(timelineHtml);
    const nextState = {
      kind: "shared",
      html: showEffectTrack ? timelineHtml : "",
      visible: showEffectTrack,
      trackCount: showEffectTrack ? timelineTrackOffset : 0,
    };
    if (
      renderedTimelineState?.kind === nextState.kind &&
      renderedTimelineState.html === nextState.html &&
      renderedTimelineState.visible === nextState.visible &&
      renderedTimelineState.trackCount === nextState.trackCount
    ) {
      return;
    }
    timelineLayer.replaceChildren();
    if (nextState.visible && nextState.html) {
      timelineLayer.innerHTML = nextState.html;
    }
    timelineLayer.hidden = !nextState.visible;
    timelineTrack?.classList.toggle("has-effect-track", nextState.visible);
    if (timelineTrack) {
      if (nextState.visible) {
        const trackAreaHeight = nextState.trackCount * 30;
        timelineTrack.style.setProperty(
          "--editor-layer-timeline-height",
          `${trackAreaHeight}px`,
        );
        timelineTrack.style.setProperty(
          "--editor-timeline-track-height",
          `${74 + trackAreaHeight}px`,
        );
        timelineLayer.style.height = `${trackAreaHeight}px`;
      } else {
        timelineTrack.style.removeProperty("--editor-layer-timeline-height");
        timelineTrack.style.removeProperty("--editor-timeline-track-height");
        timelineLayer.style.removeProperty("height");
      }
    }
    renderedTimelineState = nextState;
  }

  function scheduleFrameSync() {
    if (frameSyncRequest) return;
    frameSyncRequest = window.requestAnimationFrame(() => {
      frameSyncRequest = 0;
      for (const name of frameEntries.keys()) syncFrameTime(name);
      syncMirroredPlayback();
    });
  }

  function renderActiveTool() {
    if (!supportsInlineWorkspace()) {
      updateActiveTool();
      syncGenerationButton();
      return;
    }
    const isCut = activeTool === "cut";
    cutPanelStack.hidden = !isCut;
    inspectorHost.hidden = false;
    inspectorHost.classList.toggle("is-background", isCut);
    inspectorHost.setAttribute("aria-hidden", String(isCut));
    inspector.dataset.activeTool = activeTool;
    document.body.dataset.activeEditorTool = activeTool;
    for (const [name, entry] of frameEntries) {
      const selected = !isCut && name === activeTool;
      entry.panel.classList.toggle("is-active", selected);
      entry.panel.setAttribute("aria-hidden", String(!selected));
      entry.panel.toggleAttribute("inert", !selected);
    }
    renderMirroredPreview();
    renderMirroredTimeline();
    updateActiveTool();
    syncGenerationButton();
    syncSaveButton();
    if (!isCut) window.requestAnimationFrame(() => syncFrameTime(activeTool));
  }

  function openTool(name, href = "", options = {}) {
    if (!tools.has(name)) return false;
    const tool = tools.get(name);
    if (tool.getAttribute("aria-disabled") === "true") return false;
    if (!supportsInlineWorkspace()) {
      if (href && !options.fromNavigation) window.location.href = href;
      return false;
    }
    if (name !== "cut") {
      const targetHref = href || desiredToolUrls.get(name) || tool.href;
      if (!targetHref || targetHref === "#") return false;
      ensureToolFrame(name, targetHref);
    }
    activeTool = name;
    projectStore?.dispatch({
      type: window.EditorProjectStore.ACTIONS.ACTIVE_TOOL_CHANGED,
      payload: { tool: name },
    });
    renderActiveTool();
    if (!options.skipHistory) updateBrowserTool(name, options.replaceHistory);
    return true;
  }

  function renderEmptyState() {
    setToolLink("cut", "/", true);
    setToolLink("art", "#", false);
    setToolLink("pip", "#", false);
    setDouyinPreviewAvailable(false);
    setToolState("cut", "上传或选择视频");
    setToolState("art", "等待视频准备完成");
    setToolState("pip", "等待视频准备完成");
    status.textContent = "上传视频后，三个工具会在同一任务中启用。";
    root.dataset.state = "empty";
    activeTool = stage;
    renderActiveTool();
  }

  function renderJobState(job, options = {}) {
    if (!job?.id || !JOB_ID_PATTERN.test(job.id)) {
      renderEmptyState();
      return;
    }

    if (options.hydrateProject !== false) {
      projectStore?.dispatch({
        type: window.EditorProjectStore.ACTIONS.PROJECT_HYDRATED,
        payload: { job, preserveLocalTools: true },
      });
    }
    const jobChanged = job.id !== previousJobId;
    previousJobId = job.id;
    if (jobChanged) {
      timelineStore.replace(
        { duration: Number(job.duration) || 0, tracks: [] },
        { silent: true },
      );
    }
    if (jobChanged && stage === "cut") {
      // A fresh video task lands on the cut tool. Clear a stale ?tool=art
      // parameter left by a previous task so the workspace does not jump to
      // the art-text tool right after transcription.
      activeTool = "cut";
      const url = new URL(window.location.href);
      if (url.searchParams.has("tool")) {
        url.searchParams.delete("tool");
        window.history.replaceState(
          { ...(window.history.state || {}), editorTool: "cut" },
          "",
          url,
        );
      }
    }

    currentJob = job;
    updateDouyinBaseVideo();
    if (!job.composition) {
      job.composition = null;
    }

    const ready = job.status === "completed";
    const editReady = job.edit?.status === "completed";
    const downstreamReady = ready && (!job.edit || editReady || cutDraftActive);
    const artReady = job.art?.status === "completed";
    const pipReady = job.pictureInPicture?.status === "completed";
    const artSource = job.art?.composition
      ? job.art.source || "original"
      : editReady
        ? "edited"
        : "original";
    const pipSource = job.pictureInPicture?.composition
      ? job.pictureInPicture.source || artSource
      : artReady
        ? "art"
        : artSource;
    const encodedJobId = encodeURIComponent(job.id);

    setToolLink("cut", `/?job=${encodedJobId}`, true);
    setToolLink(
      "art",
      `/art-text?job=${encodedJobId}&source=${artSource}`,
      downstreamReady,
    );
    setToolLink(
      "pip",
      `/picture-in-picture?job=${encodedJobId}&source=${pipSource}`,
      downstreamReady,
    );
    setDouyinPreviewAvailable(ready);

    setToolState(
      "cut",
      editReady ? "剪辑版已生成" : ready ? "可剪辑，也可跳过" : "正在准备视频",
      editReady,
    );
    setToolState(
      "art",
      artReady && !cutDraftActive
        ? "艺术字已合成"
        : cutDraftActive
          ? "按当前剪后时间添加"
          : ready
            ? "可添加艺术字"
            : "等待视频准备完成",
      artReady && !cutDraftActive,
    );
    setToolState(
      "pip",
      pipReady && !cutDraftActive
        ? "组合成片已生成"
        : cutDraftActive
          ? "按当前剪后时间添加"
        : artReady
          ? "将基于艺术字版合成"
          : ready
            ? "可直接添加画中画"
            : "等待视频准备完成",
      pipReady && !cutDraftActive,
    );

    if (compositionBusy()) {
      status.textContent = "正在按当前预览合成剪辑视频，请稍候…";
      root.dataset.state = "working";
    } else if (job.composition?.status === "completed") {
      status.textContent = "当前预览已生成最终成片，剪辑、艺术字和画中画均已保留。";
      root.dataset.state = "complete";
    } else if (cutDraftActive) {
      status.textContent =
        "当前预览包含剪辑调整；点击生成视频会一次完成剪辑、艺术字和画中画合成。";
      root.dataset.state = "working";
    } else if (pipReady) {
      status.textContent = "剪辑、艺术字和画中画已汇入最终成片。";
      root.dataset.state = "complete";
    } else if (artReady) {
      status.textContent = "艺术字已合成；现在添加画中画，最终导出会同时保留两种效果。";
      root.dataset.state = "ready";
    } else if (editReady) {
      status.textContent = "剪辑版已生成；可继续添加艺术字或画中画。";
      root.dataset.state = "ready";
    } else if (ready) {
      status.textContent = "视频已就绪；切换工具只更新右侧，预览和时间轴保持不变。";
      root.dataset.state = "ready";
    } else {
      status.textContent = job.stage || "正在准备视频…";
      root.dataset.state = "working";
    }
    syncGenerationButton();

    if (supportsInlineWorkspace()) {
      const artHref = desiredToolUrls.get("art");
      if (
        artHref &&
        tools.get("art")?.getAttribute("aria-disabled") !== "true"
      ) {
        ensureToolFrame("art", artHref);
      }
      for (const name of ["art", "pip"]) {
        const entry = frameEntries.get(name);
        const href = desiredToolUrls.get(name);
        if (entry && href && entry.frame.dataset.toolHref !== href) {
          ensureToolFrame(name, href);
        }
      }
      const requestedTool = new URLSearchParams(window.location.search).get("tool");
      if (["art", "pip"].includes(requestedTool) && tools.get(requestedTool)?.getAttribute("aria-disabled") !== "true") {
        openTool(requestedTool, desiredToolUrls.get(requestedTool), {
          skipHistory: true,
        });
      } else {
        renderActiveTool();
      }
    } else {
      updateActiveTool();
    }
  }

  async function refresh(job = null) {
    if (job?.id) {
      renderJobState(job);
      return;
    }
    const jobId = currentJobId();
    if (!jobId) {
      renderEmptyState();
      return;
    }
    const token = ++refreshToken;
    try {
      const response = await fetch(
        `/api/transcriptions/${encodeURIComponent(jobId)}`,
      );
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "无法读取当前视频任务。");
      if (token === refreshToken) renderJobState(payload);
    } catch {
      if (token !== refreshToken) return;
      renderEmptyState();
      status.textContent = "当前任务暂时无法读取，请返回剪辑工具重新选择视频。";
      root.dataset.state = "error";
    }
  }

  function setCutDraft(value) {
    const payload = value && typeof value === "object"
      ? value
      : { active: Boolean(value) };
    const ranges = Array.isArray(payload.ranges)
      ? payload.ranges
          .map((range) => ({
            start: Math.max(0, Number(range.start) || 0),
            end: Math.max(0, Number(range.end) || 0),
          }))
          .filter((range) => range.end > range.start)
          .sort((left, right) => left.start - right.start)
      : [];
    const nextCutDraftState = {
      active: Boolean(payload.active),
      ranges,
      sourceDuration: Math.max(0, Number(payload.sourceDuration) || 0),
      duration: Math.max(0, Number(payload.duration) || 0),
      transcript: payload.transcript || null,
    };
    const previousTimingRevision = projectSnapshot()?.timingRevision ?? -1;
    const dispatchResult = projectStore?.dispatch({
      type: window.EditorProjectStore.ACTIONS.CUT_TIMING_CHANGED,
      payload: nextCutDraftState,
    });
    cutDraftState = projectStoreEnabled
      ? projectSnapshot().project.cut
      : nextCutDraftState;
    cutDraftActive = cutDraftState.active;
    updateDouyinBaseVideo();
    const timingChanged = projectStoreEnabled
      ? dispatchResult?.accepted &&
        projectSnapshot().timingRevision !== previousTimingRevision
      : true;
    if (timingChanged) {
      for (const name of ["art", "pip"]) syncFrameCutDraft(name);
    }
    if (currentJob) renderJobState(currentJob);
    else syncGenerationButton();
  }

  function setTimelineTracks(kind, tracks, options = {}) {
    if (projectStoreEnabled) {
      if (["art", "pip"].includes(kind)) {
        const currentTool = projectSnapshot().project[kind];
        projectStore.dispatch({
          type:
            kind === "art"
              ? window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED
              : window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
          payload: {
            ...currentTool,
            timeline: {
              duration: Math.max(0, Number(options.duration) || 0),
              tracks: Array.isArray(tracks) ? tracks : [],
              selection: options.selection
                ? { clipId: String(options.selection) }
                : null,
            },
          },
        });
      }
      if (options.selection !== undefined) {
        projectStore.dispatch({
          type: window.EditorProjectStore.ACTIONS.SELECTION_CHANGED,
          payload: {
            selection: options.selection
              ? { clipId: String(options.selection) }
              : null,
          },
        });
      }
      return syncProjectTimeline();
    }
    syncToolTimeline(
      kind,
      {
        duration: Math.max(0, Number(options.duration) || 0),
        tracks: Array.isArray(tracks) ? tracks : [],
        selection: options.selection
          ? { clipId: String(options.selection) }
          : null,
      },
      { selection: options.selection || null },
    );
    return timelineStore.snapshot();
  }

  douyinPreviewToggle?.addEventListener("click", () => {
    setDouyinPreviewEnabled(!douyinPreviewEnabled);
  });

  for (const [name, tool] of tools) {
    tool.addEventListener("click", (event) => {
      if (tool.getAttribute("aria-disabled") === "true") {
        event.preventDefault();
        return;
      }
      if (embeddedEditor && window.parent !== window) {
        event.preventDefault();
        window.parent.postMessage(
          { type: "editor-suite:open-tool", kind: name, href: tool.href },
          window.location.origin,
        );
        return;
      }
      if (supportsInlineWorkspace()) {
        event.preventDefault();
        openTool(name, tool.href);
      }
    });
  }

  document.addEventListener(
    "click",
    (event) => {
      if (event.defaultPrevented) return;
      const anchor = event.target.closest("a[href]");
      if (!anchor || root.contains(anchor) || anchor.hasAttribute("download")) return;
      const name = toolFromHref(anchor.getAttribute("href"));
      if (!name) return;
      if (embeddedEditor && window.parent !== window) {
        event.preventDefault();
        window.parent.postMessage(
          { type: "editor-suite:open-tool", kind: name, href: anchor.href },
          window.location.origin,
        );
        return;
      }
      if (!supportsInlineWorkspace() || name === "cut") return;
      event.preventDefault();
      openTool(name, anchor.href);
    },
    true,
  );

  function toolFrameOwnsSource(source, kind = "") {
    if (kind) return frameEntries.get(kind)?.frame.contentWindow === source;
    return [...frameEntries.values()].some(
      (entry) => entry.frame.contentWindow === source,
    );
  }

  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || !supportsInlineWorkspace()) return;
    const data = event.data || {};
    if (data.type === "editor-suite:open-tool" && tools.has(data.kind)) {
      if (!toolFrameOwnsSource(event.source)) return;
      openTool(data.kind, data.href || desiredToolUrls.get(data.kind));
      return;
    }
    if (data.type === "editor-suite:job-state" && data.job?.id) {
      if (
        !["art", "pip"].includes(data.kind) ||
        !toolFrameOwnsSource(event.source, data.kind)
      ) {
        return;
      }
      if (projectStoreEnabled) {
        const messageRevision = bridgeRevision(data.revision);
        const acceptanceFloor = toolBridgeRevisions.get(data.kind) ?? -1;
        if (
          messageRevision === null ||
          messageRevision < acceptanceFloor
        ) {
          return;
        }
      }
      renderJobState(data.job, { hydrateProject: !projectStoreEnabled });
      if (!projectStoreEnabled) {
        window.dispatchEvent(
          new CustomEvent("editor-suite:job-state", { detail: data.job }),
        );
      }
      return;
    }
    if (data.type === "editor-suite:seek" && data.kind === activeTool) {
      if (!toolFrameOwnsSource(event.source, data.kind)) return;
      const nextTime = Number(data.currentTime);
      if (
        Number.isFinite(nextTime) &&
        Math.abs(nextTime - workspaceCurrentTime()) > 0.05
      ) {
        previewVideo.currentTime = workspaceSourceTime(nextTime);
      }
      return;
    }
    if (
      data.type === "editor-suite:request-cut-draft" &&
      ["art", "pip"].includes(data.kind) &&
      frameEntries.get(data.kind)?.frame.contentWindow === event.source
    ) {
      syncFrameCutDraft(data.kind);
      return;
    }
    if (data.type !== "editor-suite:tool-state" || !["art", "pip"].includes(data.kind)) {
      return;
    }
    if (!toolFrameOwnsSource(event.source, data.kind)) return;
    const messageRevision = bridgeRevision(data.revision);
    const previousBridgeRevision = toolBridgeRevisions.get(data.kind) ?? -1;
    if (projectStoreEnabled) {
      if (
        messageRevision === null ||
        messageRevision < previousBridgeRevision
      ) {
        return;
      }
    }
    advanceToolBridgeRevision(data.kind, messageRevision);
    const bridgeState = {
      overlayHtml: String(data.overlayHtml || ""),
      overlayWidth: Number(data.overlayWidth) || 1,
      overlayHeight: Number(data.overlayHeight) || 1,
      timelineHtml: String(data.timelineHtml || ""),
      timelineTrackCount: Math.max(1, Number(data.timelineTrackCount) || 1),
      timeline: data.timeline || null,
      generationDisabled: data.generationDisabled !== false,
      generationLabel: String(data.generationLabel || ""),
      generationBusy: Boolean(data.generationBusy),
      generationError: String(data.generationError || ""),
      generationPayload:
        data.generationPayload && typeof data.generationPayload === "object"
          ? data.generationPayload
          : null,
      revision: messageRevision,
      timingRevision: bridgeRevision(data.timingRevision),
      changeKind: String(data.changeKind || "tool-state"),
    };
    toolStates.set(data.kind, bridgeState);
    if (projectStoreEnabled) {
      const semantic = bridgeState.generationPayload || {};
      projectStore.dispatch({
        type:
          data.kind === "art"
            ? window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED
            : window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
        payload: {
          source: semantic.source || projectSnapshot().project[data.kind].source,
          overlays: Array.isArray(semantic.overlays) ? semantic.overlays : [],
          timeline: data.timeline || null,
        },
      });
      acknowledgeToolProjection(data.kind);
      syncProjectTimeline();
    } else {
      syncToolTimeline(data.kind, data.timeline);
    }
    syncGenerationButton();
    renderMirroredPreview();
    renderMirroredTimeline();
    if (data.kind === activeTool) {
      const childTime = Number(data.currentTime);
      if (
        Number.isFinite(childTime) &&
        Math.abs(childTime - workspaceCurrentTime()) > 0.05
      ) {
        syncFrameTime(data.kind);
      }
    }
  });

  document.addEventListener("editor-suite:tool-state", (event) => {
    const data = event.detail || {};
    if (!['art', 'pip'].includes(data.kind)) return;
    toolStates.set(data.kind, data);
    if (projectStoreEnabled) {
      const semantic = data.generationPayload || {};
      projectStore.dispatch({
        type:
          data.kind === "art"
            ? window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED
            : window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
        payload: {
          source: semantic.source || projectSnapshot().project[data.kind].source,
          overlays: Array.isArray(semantic.overlays) ? semantic.overlays : [],
          timeline: data.timeline || null,
        },
      });
      syncProjectTimeline();
    } else {
      syncToolTimeline(data.kind, data.timeline);
    }
    syncGenerationButton();
    renderMirroredPreview();
    renderMirroredTimeline();
  });

  for (const eventName of ["timeupdate", "seeking", "loadedmetadata", "play", "pause"]) {
    previewVideo?.addEventListener(eventName, scheduleFrameSync);
  }

  function beginMirroredPipResize(event, target, canvas, id, direction) {
    const canvasRect = canvas?.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    if (!canvasRect || canvasRect.width <= 0 || canvasRect.height <= 0) return;
    event.preventDefault();
    event.stopPropagation();
    const startClientX = event.clientX;
    const startClientY = event.clientY;
    const startWidth =
      Number.parseFloat(target.style.width) / 100 ||
      targetRect.width / canvasRect.width;
    const centerX = Number.parseFloat(target.style.left) / 100 || 0.5;
    const centerY = Number.parseFloat(target.style.top) / 100 || 0.5;
    const media = target.querySelector("img, video");
    const imageAspectRatio = Math.max(
      0.1,
      media?.naturalWidth && media?.naturalHeight
        ? media.naturalWidth / media.naturalHeight
        : media?.videoWidth && media?.videoHeight
          ? media.videoWidth / media.videoHeight
          : targetRect.width / targetRect.height,
    );
    const maximumWidth = Math.max(
      0.05,
      Math.min(
        0.55,
        2 * Math.min(centerX, 1 - centerX),
        (2 * Math.min(centerY, 1 - centerY) * imageAspectRatio * canvasRect.height) /
          canvasRect.width,
      ),
    );
    let moved = false;
    let framePending = false;
    let latestWidth = startWidth;
    let finished = false;

    const move = (moveEvent) => {
      const deltaX = moveEvent.clientX - startClientX;
      const deltaY = moveEvent.clientY - startClientY;
      if (!moved && Math.hypot(deltaX, deltaY) < 3) return;
      moved = true;
      if (framePending) return;
      framePending = true;
      const horizontalDirection = direction.includes("e")
        ? 1
        : direction.includes("w")
          ? -1
          : 0;
      const verticalDirection = direction.includes("s")
        ? 1
        : direction.includes("n")
          ? -1
          : 0;
      const horizontalChange =
        (horizontalDirection * deltaX * 2) / canvasRect.width;
      const verticalChange =
        (verticalDirection * deltaY * 2 * imageAspectRatio) /
        canvasRect.width;
      const widthChange =
        horizontalDirection && verticalDirection
          ? Math.abs(horizontalChange) >= Math.abs(verticalChange)
            ? horizontalChange
            : verticalChange
          : horizontalChange || verticalChange;
      const width = Math.min(
        maximumWidth,
        Math.max(Math.min(0.2, maximumWidth), startWidth + widthChange),
      );
      latestWidth = width;
      window.requestAnimationFrame(() => {
        framePending = false;
        if (finished) return;
        if (!previewOverlay?.contains(target)) return;
        target.classList.add("is-selected", "is-resizing");
        target.style.width = `${width * 100}%`;
        frameEntries.get("pip")?.frame.contentWindow?.postMessage(
          { type: "editor-suite:resize-effect", kind: "pip", id, width },
          window.location.origin,
        );
      });
    };

    const finish = () => {
      finished = true;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
      target.classList.remove("is-resizing");
      frameEntries.get("pip")?.frame.contentWindow?.postMessage(
        {
          type: "editor-suite:resize-effect",
          kind: "pip",
          id,
          width: latestWidth,
        },
        window.location.origin,
      );
      frameEntries.get("pip")?.frame.contentWindow?.postMessage(
        { type: "editor-suite:move-finish", kind: "pip", id },
        window.location.origin,
      );
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish, { once: true });
    window.addEventListener("pointercancel", finish, { once: true });
  }

  previewOverlay?.addEventListener("pointerdown", (event) => {
    if (activeTool === "cut" || event.button !== 0) return;
    const target = event.target.closest("[data-overlay-id], [data-picture-id]");
    if (!target) return;
    const effectKind = target.closest("[data-effect-kind]")?.dataset.effectKind;
    if (effectKind !== activeTool) return;
    event.preventDefault();
    const canvas = target.closest(".editor-suite-preview-canvas");
    const id = target.dataset.overlayId || target.dataset.pictureId;
    const resizeHandle = event.target.closest("[data-pip-resize]");
    if (effectKind === "pip" && resizeHandle) {
      beginMirroredPipResize(
        event,
        target,
        canvas,
        id,
        resizeHandle.dataset.pipResize,
      );
      return;
    }
    const startClientX = event.clientX;
    const startClientY = event.clientY;
    let moved = false;
    let framePending = false;
    let currentTarget = target;

    // Capture the grab offset — the pointer's distance from the element's
    // visual center — plus the canvas bounds once at drag start, so the grabbed
    // point stays under the pointer (1:1) instead of the element center snapping
    // onto it. The canvas may be rebuilt while dragging, so its rect is frozen
    // here rather than re-read from a possibly-detached node.
    const canvasRect = canvas?.getBoundingClientRect();
    const grabRect = target.getBoundingClientRect();
    const grabOffsetX = event.clientX - (grabRect.left + grabRect.width / 2);
    const grabOffsetY = event.clientY - (grabRect.top + grabRect.height / 2);

    // The mirror canvas may be rebuilt by a snapshot while dragging, so
    // re-resolve the element by id instead of keeping a stale reference.
    const resolveTarget = () => {
      if (previewOverlay?.contains(currentTarget)) return currentTarget;
      const found = canvas?.querySelector(
        `[data-picture-id="${id}"], [data-overlay-id="${id}"]`,
      );
      if (found) currentTarget = found;
      return currentTarget;
    };

    const move = (moveEvent) => {
      const deltaX = moveEvent.clientX - startClientX;
      const deltaY = moveEvent.clientY - startClientY;
      if (!moved && Math.hypot(deltaX, deltaY) < 3) return;
      moved = true;
      if (framePending) return;
      framePending = true;
      const clientX = moveEvent.clientX;
      const clientY = moveEvent.clientY;
      // Coalesce to one write per frame and move the mirrored element directly
      // (no snapshot round-trip), so dragging stays smooth on the compositor.
      window.requestAnimationFrame(() => {
        framePending = false;
        const element = resolveTarget();
        if (!previewOverlay?.contains(element)) return;
        element.classList.add("is-dragging");
        if (!canvasRect || canvasRect.width <= 0 || canvasRect.height <= 0) return;
        const x = Math.min(
          0.95,
          Math.max(
            0.05,
            (clientX - grabOffsetX - canvasRect.left) / canvasRect.width,
          ),
        );
        const y = Math.min(
          0.95,
          Math.max(
            0.05,
            (clientY - grabOffsetY - canvasRect.top) / canvasRect.height,
          ),
        );
        element.style.left = `${x * 100}%`;
        element.style.top = `${y * 100}%`;
        frameEntries.get(effectKind)?.frame.contentWindow?.postMessage(
          { type: "editor-suite:move-effect", kind: effectKind, id, x, y },
          window.location.origin,
        );
      });
    };

    const finish = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
      resolveTarget()?.classList.remove("is-dragging");
      frameEntries.get(effectKind)?.frame.contentWindow?.postMessage(
        { type: "editor-suite:move-finish", kind: effectKind, id },
        window.location.origin,
      );
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish, { once: true });
    window.addEventListener("pointercancel", finish, { once: true });
  });

  timelineLayer?.addEventListener(
    "pointerdown",
    (event) => {
      const unifiedSegment = event.target.closest(
        "[data-timeline-clip-id][data-effect-kind]",
      );
      if (unifiedSegment && event.button === 0) {
        event.preventDefault();
        event.stopPropagation();
        const kind = unifiedSegment.dataset.effectKind;
        const clipId = unifiedSegment.dataset.timelineClipId;
        const clip = timelineStore.findClip(clipId);
        const frame = frameEntries.get(kind)?.frame;
        if (!clip || !frame?.contentWindow) return;
        openTool(kind, desiredToolUrls.get(kind));
        timelineStore.selectClip(clipId, { silent: true });
        projectStore?.dispatch({
          type: window.EditorProjectStore.ACTIONS.SELECTION_CHANGED,
          payload: { selection: { clipId } },
        });
        for (const candidate of timelineLayer.querySelectorAll(
          "[data-timeline-clip-id]",
        )) {
          const selected = candidate.dataset.timelineClipId === clipId;
          candidate.classList.toggle("is-selected", selected);
          candidate.setAttribute("aria-pressed", String(selected));
        }
        previewVideo.currentTime = workspaceSourceTime(clip.start);
        frame.contentWindow.postMessage(
          {
            type: "editor-suite:timeline-action",
            action: "select",
            kind,
            clipId,
            sourceId: clip.sourceId,
            currentTime: clip.start,
          },
          window.location.origin,
        );
        if (!clip.editable) return;

        const mode =
          event.target.closest("[data-timeline-resize]")?.dataset
            .timelineResize ||
          event.target.closest("[data-art-time-drag]")?.dataset.artTimeDrag ||
          "move";
        const total = Math.max(
          timelineStore.snapshot().duration,
          Number(previewVideo.duration) || 0,
          Number(document.querySelector("#cutFrameTimelineSeek")?.max) || 0,
        );
        const pointerSession = window.EditorTimeline.createPointerSession(
          timelineStore,
          {
            clipId,
            mode,
            startClientX: event.clientX,
            trackWidth: timelineTrack.getBoundingClientRect().width,
            duration: total,
          },
        );
        if (!pointerSession) return;
        let moved = false;
        let currentSegment = unifiedSegment;

        const resolveSegment = () => {
          if (timelineLayer.contains(currentSegment)) return currentSegment;
          const found = timelineLayer.querySelector(
            `[data-timeline-clip-id="${clipId}"]`,
          );
          if (found) currentSegment = found;
          return currentSegment;
        };

        const move = (moveEvent) => {
          if (!moved && Math.abs(moveEvent.clientX - event.clientX) < 3) return;
          moved = true;
          const nextClip = pointerSession.update(moveEvent.clientX);
          const liveSegment = resolveSegment();
          liveSegment.classList.add("is-selected", "is-dragging");
          liveSegment.dataset.effectStart = String(nextClip.start);
          liveSegment.dataset.effectEnd = String(nextClip.end);
          liveSegment.style.left = `${(nextClip.start / total) * 100}%`;
          liveSegment.style.width = `${Math.max(
            0.8,
            ((nextClip.end - nextClip.start) / total) * 100,
          )}%`;
          const currentTime = mode === "end" ? nextClip.end : nextClip.start;
          previewVideo.currentTime = workspaceSourceTime(currentTime);
          frame.contentWindow.postMessage(
            {
              type: "editor-suite:timeline-action",
              action: "set-range",
              kind,
              clipId,
              sourceId: clip.sourceId,
              start: nextClip.start,
              end: nextClip.end,
              currentTime,
            },
            window.location.origin,
          );
        };

        const finish = () => {
          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", finish);
          window.removeEventListener("pointercancel", finish);
          resolveSegment()?.classList.remove("is-dragging");
          const finalClip = pointerSession.finish({ commit: false });
          frame.contentWindow.postMessage(
            {
              type: "editor-suite:timeline-action",
              action: "commit",
              kind,
              clipId,
              sourceId: clip.sourceId,
              start: finalClip.start,
              end: finalClip.end,
            },
            window.location.origin,
          );
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", finish, { once: true });
        window.addEventListener("pointercancel", finish, { once: true });
        return;
      }
      const pipSegment = event.target.closest(
        '.pip-timeline-segment[data-effect-kind="pip"][data-picture-id]',
      );
      if (pipSegment && event.button === 0) {
        event.preventDefault();
        event.stopPropagation();
        const id = pipSegment.dataset.pictureId;
        const start = Math.max(0, Number(pipSegment.dataset.effectStart) || 0);
        const pipFrame = frameEntries.get("pip")?.frame;
        if (!pipFrame?.contentWindow) return;
        openTool("pip", desiredToolUrls.get("pip"));
        previewVideo.currentTime = workspaceSourceTime(start);
        pipFrame.contentWindow.postMessage(
          {
            type: "editor-suite:select-pip-timeline",
            kind: "pip",
            id,
            currentTime: start,
          },
          window.location.origin,
        );
        return;
      }
      const segment = event.target.closest(
        '.frame-timeline-segment[data-effect-kind="art"][data-overlay-id]',
      );
      if (!segment || event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation();
      const id = segment.dataset.overlayId;
      const artFrame = frameEntries.get("art")?.frame;
      if (!artFrame?.contentWindow) return;
      openTool("art", desiredToolUrls.get("art"));
      artFrame.contentWindow.postMessage(
        {
          type: "editor-suite:select-art-timeline",
          kind: "art",
          id,
          currentTime: workspaceCurrentTime(),
        },
        window.location.origin,
      );
      if (segment.dataset.timelineEditable !== "true") return;

      const mode =
        event.target.closest("[data-art-time-drag]")?.dataset.artTimeDrag ||
        "move";
      const original = {
        start: Number(segment.dataset.effectStart) || 0,
        end: Number(segment.dataset.effectEnd) || 0,
      };
      const startClientX = event.clientX;
      const total =
        Number(previewVideo.duration) ||
        Number(document.querySelector("#cutFrameTimelineSeek")?.max) ||
        0;
      let moved = false;
      let currentSegment = segment;

      const resolveSegment = () => {
        if (timelineLayer.contains(currentSegment)) return currentSegment;
        const found = timelineLayer.querySelector(
          `.frame-timeline-segment[data-effect-kind="art"][data-overlay-id="${id}"]`,
        );
        if (found) currentSegment = found;
        return currentSegment;
      };

      const move = (moveEvent) => {
        if (!moved && Math.abs(moveEvent.clientX - startClientX) < 3) return;
        moved = true;
        if (total <= 0) return;
        const delta =
          ((moveEvent.clientX - startClientX) /
            timelineTrack.getBoundingClientRect().width) * total;
        let start = original.start;
        let end = original.end;
        if (mode === "start") {
          start = Math.min(
            original.end - 0.1,
            Math.max(0, original.start + delta),
          );
        } else if (mode === "end") {
          end = Math.min(
            total,
            Math.max(original.start + 0.1, original.end + delta),
          );
        } else {
          const length = original.end - original.start;
          start = Math.min(total - length, Math.max(0, original.start + delta));
          end = start + length;
        }
        const liveSegment = resolveSegment();
        liveSegment.classList.add("is-selected", "is-dragging");
        liveSegment.style.left = `${(start / total) * 100}%`;
        liveSegment.style.width = `${Math.max(
          0.8,
          ((end - start) / total) * 100,
        )}%`;
        const currentTime = mode === "end" ? end : start;
        previewVideo.currentTime = workspaceSourceTime(currentTime);
        artFrame.contentWindow.postMessage(
          {
            type: "editor-suite:adjust-art-timeline",
            kind: "art",
            id,
            start,
            end,
            currentTime,
          },
          window.location.origin,
        );
      };

      const finish = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", finish);
        window.removeEventListener("pointercancel", finish);
        resolveSegment()?.classList.remove("is-dragging");
        artFrame.contentWindow.postMessage(
          { type: "editor-suite:move-finish", kind: "art", id },
          window.location.origin,
        );
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", finish, { once: true });
      window.addEventListener("pointercancel", finish, { once: true });
    },
    true,
  );

  timelineTrack?.addEventListener(
    "pointerdown",
    (event) => {
      if (activeTool === "cut") return;
      if (
        event.target.closest(
          '.frame-timeline-segment[data-effect-kind="art"], ' +
            '.pip-timeline-segment[data-effect-kind="pip"]',
        )
      ) {
        return;
      }
      event.preventDefault();
      event.stopImmediatePropagation();
      const seek = (moveEvent) => {
        const bounds = timelineTrack.getBoundingClientRect();
        const ratio = Math.min(1, Math.max(0, (moveEvent.clientX - bounds.left) / bounds.width));
        const total = Number(previewVideo.duration) || Number(document.querySelector("#cutFrameTimelineSeek")?.max) || 0;
        if (total > 0) previewVideo.currentTime = ratio * total;
      };
      const finish = () => {
        window.removeEventListener("pointermove", seek, true);
        window.removeEventListener("pointerup", finish, true);
      };
      seek(event);
      window.addEventListener("pointermove", seek, true);
      window.addEventListener("pointerup", finish, { capture: true, once: true });
    },
    true,
  );

  generateButton?.addEventListener("click", generateCurrentPreview);
  saveButton?.addEventListener("click", saveCurrentVersion);

  window.addEventListener("popstate", () => {
    if (!supportsInlineWorkspace()) return;
    const requested = new URLSearchParams(window.location.search).get("tool");
    const name = ["art", "pip"].includes(requested) ? requested : "cut";
    openTool(name, desiredToolUrls.get(name) || tools.get(name)?.href, {
      skipHistory: true,
      fromNavigation: true,
    });
  });

  window.EditorSuite = {
    refresh,
    update: renderJobState,
    openTool,
    activeTool: () => activeTool,
    isDouyinPreview: () => douyinPreviewEnabled,
    setCutDraft,
    setTimelineTracks,
    timelineSnapshot: () => timelineStore.snapshot(),
    projectStoreEnabled: () => projectStoreEnabled,
    projectSnapshot,
    beginProjectEffect: (scope) => projectStore?.beginEffect(scope) || null,
    isCurrentProjectEffect: (token) =>
      projectStore?.isCurrentEffect(token) || false,
    applyTranscriptTextEffect: (token, job) => {
      if (
        !projectStore ||
        !job?.result ||
        String(job.id || "") !== projectSnapshot().jobId
      ) {
        return { accepted: false, revision: 0, timingRevision: 0 };
      }
      const result = projectStore.applyEffect(token, {
        type: window.EditorProjectStore.ACTIONS.TRANSCRIPT_TEXT_CHANGED,
        payload: {
          job,
          transcript: job.result,
          editableSegments: job.result.editableSegments || [],
          serverArt: job.art || null,
          serverVersion: job.updatedAt || "",
        },
      });
      if (result.accepted) {
        currentJob = projectSnapshot().project.job;
        syncGenerationButton();
      }
      return result;
    },
    compositionRequest: () => compositionRequest(),
    generateCurrentPreview,
  };
  document.addEventListener("editor-suite:refresh", () => refresh());
  document.addEventListener("editor-suite:transcript-updated", (event) => {
    if (projectStoreEnabled) return;
    // The cut page edited transcript text; ask an embedded art page to
    // re-read the re-segmented subtitle track from the server.
    const artEntry = frameEntries.get("art");
    if (artEntry?.frame?.contentWindow) {
      artEntry.frame.contentWindow.postMessage(
        { type: "editor-suite:transcript-updated" },
        window.location.origin,
      );
    }
  });
  updateActiveTool();
  syncGenerationButton();
  refresh();
})();
