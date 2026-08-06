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
  const cutTabbar = inspector?.querySelector(".text-editor-tabbar");
  const cutPanelStack = inspector?.querySelector(".text-editor-panel-stack");
  const inspectorHost = document.querySelector("#editorSuiteInspectorHost");
  const previewOverlay = document.querySelector("#editorSuitePreviewOverlay");
  const timelineLayer = document.querySelector("#editorSuiteTimelineLayer");
  const timelineTrack = document.querySelector("#cutFrameTimelineTrack");
  const previewVideo = document.querySelector("#cutPreviewVideo");
  const previewStage = document.querySelector("#cutVideoStage");
  const generateButton = root.querySelector("[data-editor-suite-generate]");
  const downloadButton = root.querySelector("[data-editor-suite-download]");
  const frameEntries = new Map();
  const toolStates = new Map();
  const desiredToolUrls = new Map();
  let activeTool = stage;
  let refreshToken = 0;
  let overlayResizeObserver = null;
  let renderedPreviewState = null;
  let renderedTimelineState = null;
  let frameSyncRequest = 0;
  let currentJob = null;
  let previousJobId = null;
  let cutDraftActive = false;
  let cutDraftState = {
    active: false,
    ranges: [],
    sourceDuration: 0,
    duration: 0,
    transcript: null,
  };

  function supportsInlineWorkspace() {
    return Boolean(
      stage === "cut" &&
        inspector &&
        cutTabbar &&
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

  function previewCompositionState() {
    const ranges = cutDraftActive
      ? cutDraftState.ranges
      : currentJob?.edit?.status === "completed"
        ? currentJob.edit.requestedRanges || currentJob.edit.ranges || []
        : [];
    const art = toolStates.get("art")?.generationPayload || (
      currentJob?.art?.overlays
        ? {
            source: currentJob.art.source || "original",
            historyName: currentJob.art.historyName || null,
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
      historyName: compositionHistoryName(),
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

  let compositionPollTimer = null;

  function compositionHistoryName() {
    for (const selector of ["#cutHistoryName", "#artHistoryName"]) {
      const value = document.querySelector(selector)?.value?.trim();
      if (value) return value;
    }
    return null;
  }

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
        });
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
    const entry = frameEntries.get(name);
    if (!entry?.frame?.contentWindow) return;
    entry.frame.contentWindow.postMessage(
      {
        type: "editor-suite:cut-draft",
        ...cutDraftState,
      },
      window.location.origin,
    );
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

    const nextState = { signature: JSON.stringify(layers) };
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
        const scale = Math.min(
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
    const timelineStates = [toolStates.get("art"), toolStates.get("pip")]
      .filter(Boolean);
    const timelineHtml = timelineStates
      .map((state) => state.timelineHtml)
      .filter(Boolean)
      .join("");
    const showEffectTrack = Boolean(timelineHtml);
    const nextState = {
      kind: "shared",
      html: showEffectTrack ? timelineHtml : "",
      visible: showEffectTrack,
    };
    if (
      renderedTimelineState?.kind === nextState.kind &&
      renderedTimelineState.html === nextState.html &&
      renderedTimelineState.visible === nextState.visible
    ) {
      return;
    }
    timelineLayer.replaceChildren();
    if (nextState.visible && nextState.html) {
      timelineLayer.innerHTML = nextState.html;
    }
    timelineLayer.hidden = !nextState.visible;
    timelineTrack?.classList.toggle("has-effect-track", nextState.visible);
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
    cutTabbar.hidden = !isCut;
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
    renderActiveTool();
    if (!options.skipHistory) updateBrowserTool(name, options.replaceHistory);
    return true;
  }

  function renderEmptyState() {
    setToolLink("cut", "/", true);
    setToolLink("art", "#", false);
    setToolLink("pip", "#", false);
    setToolState("cut", "上传或选择视频");
    setToolState("art", "等待视频准备完成");
    setToolState("pip", "等待视频准备完成");
    status.textContent = "上传视频后，三个工具会在同一任务中启用。";
    root.dataset.state = "empty";
    activeTool = stage;
    renderActiveTool();
  }

  function renderJobState(job) {
    if (!job?.id || !JOB_ID_PATTERN.test(job.id)) {
      renderEmptyState();
      return;
    }

    const jobChanged = job.id !== previousJobId;
    previousJobId = job.id;
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
    cutDraftState = {
      active: Boolean(payload.active),
      ranges,
      sourceDuration: Math.max(0, Number(payload.sourceDuration) || 0),
      duration: Math.max(0, Number(payload.duration) || 0),
      transcript: payload.transcript || null,
    };
    cutDraftActive = cutDraftState.active;
    for (const name of ["art", "pip"]) syncFrameCutDraft(name);
    if (currentJob) renderJobState(currentJob);
    else syncGenerationButton();
  }

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

  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || !supportsInlineWorkspace()) return;
    const data = event.data || {};
    if (data.type === "editor-suite:open-tool" && tools.has(data.kind)) {
      openTool(data.kind, data.href || desiredToolUrls.get(data.kind));
      return;
    }
    if (data.type === "editor-suite:job-state" && data.job?.id) {
      renderJobState(data.job);
      window.dispatchEvent(
        new CustomEvent("editor-suite:job-state", { detail: data.job }),
      );
      return;
    }
    if (data.type === "editor-suite:seek" && data.kind === activeTool) {
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
    toolStates.set(data.kind, {
      overlayHtml: String(data.overlayHtml || ""),
      overlayWidth: Number(data.overlayWidth) || 1,
      overlayHeight: Number(data.overlayHeight) || 1,
      timelineHtml: String(data.timelineHtml || ""),
      generationDisabled: data.generationDisabled !== false,
      generationLabel: String(data.generationLabel || ""),
      generationBusy: Boolean(data.generationBusy),
      generationError: String(data.generationError || ""),
      generationPayload:
        data.generationPayload && typeof data.generationPayload === "object"
          ? data.generationPayload
          : null,
    });
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
    syncGenerationButton();
    renderMirroredPreview();
    renderMirroredTimeline();
  });

  for (const eventName of ["timeupdate", "seeking", "loadedmetadata", "play", "pause"]) {
    previewVideo?.addEventListener(eventName, scheduleFrameSync);
  }

  previewOverlay?.addEventListener("pointerdown", (event) => {
    if (activeTool === "cut") return;
    const target = event.target.closest("[data-overlay-id], [data-picture-id]");
    if (!target) return;
    const effectKind = target.closest("[data-effect-kind]")?.dataset.effectKind;
    if (effectKind !== activeTool) return;
    event.preventDefault();
    const bounds = previewStage.getBoundingClientRect();
    const id = target.dataset.overlayId || target.dataset.pictureId;
    const move = (moveEvent) => {
      const x = Math.min(0.95, Math.max(0.05, (moveEvent.clientX - bounds.left) / bounds.width));
      const y = Math.min(0.95, Math.max(0.05, (moveEvent.clientY - bounds.top) / bounds.height));
      frameEntries.get(effectKind)?.frame.contentWindow?.postMessage(
        { type: "editor-suite:move-effect", kind: effectKind, id, x, y },
        window.location.origin,
      );
    };
    const finish = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
    };
    move(event);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish, { once: true });
  });

  timelineTrack?.addEventListener(
    "pointerdown",
    (event) => {
      if (activeTool === "cut") return;
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
    setCutDraft,
    generateCurrentPreview,
  };
  document.addEventListener("editor-suite:refresh", () => refresh());
  document.addEventListener("editor-suite:transcript-updated", (event) => {
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
