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
  const generationLabels = {
    cut: "生成剪辑视频",
    art: "生成艺术字视频",
    pip: "生成画中画视频",
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
        <button
          class="editor-suite-generate-button"
          type="button"
          data-editor-suite-generate
          aria-label="生成视频"
          disabled
        >
          <iconify-icon icon="ph:film-strip-bold" aria-hidden="true"></iconify-icon>
          <span>生成视频</span>
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
  const cutGenerateSource = document.querySelector("#generateCutButton");
  const artGenerateSource = document.querySelector("#generateArtVideo");
  const pipGenerateSource = document.querySelector("#generatePipVideo");
  const cutProgress = document.querySelector("#cutProgress");
  const artProgress = document.querySelector("#artProgress");
  const pipProgress = document.querySelector("#outputProgress");
  const cutGenerationError = document.querySelector("#cutError");
  const artGenerationError = document.querySelector("#artFormError");
  const pipGenerationError = document.querySelector("#outputError");
  const directGenerationSources = new Map([
    ["cut", cutGenerateSource],
    ["art", artGenerateSource],
    ["pip", pipGenerateSource],
  ]);
  const directGenerationProgress = new Map([
    ["cut", cutProgress],
    ["art", artProgress],
    ["pip", pipProgress],
  ]);
  const directGenerationErrors = new Map([
    ["cut", cutGenerationError],
    ["art", artGenerationError],
    ["pip", pipGenerationError],
  ]);
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

  function generationState(name) {
    if (cutDraftActive && name !== "cut") {
      return {
        disabled: true,
        label: generationLabels[name],
        busy: false,
      };
    }
    const directSource = directGenerationSources.get(name);
    if (directSource) {
      const directProgress = directGenerationProgress.get(name);
      const directError = directGenerationErrors.get(name);
      return {
        disabled: directSource.disabled,
        label: directSource.textContent.trim() || generationLabels[name],
        busy: Boolean(directProgress && !directProgress.hidden),
        error: directError && !directError.hidden
          ? directError.textContent.trim()
          : "",
      };
    }
    const state = toolStates.get(name);
    return {
      disabled: state?.generationDisabled ?? true,
      label: state?.generationLabel || generationLabels[name],
      busy: Boolean(state?.generationBusy),
      error: String(state?.generationError || ""),
    };
  }

  function syncGenerationButton() {
    if (!generateButton) return;
    const state = generationState(activeTool);
    const label = generateButton.querySelector("span");
    generateButton.disabled = state.disabled;
    generateButton.classList.toggle("is-busy", state.busy);
    generateButton.setAttribute("aria-busy", String(state.busy));
    generateButton.dataset.generationKind = activeTool;
    if (label) {
      label.textContent = state.busy ? "生成中…" : "生成视频";
    }
    const disabledHints = {
      cut: "请先在剪辑工具中选择要删除的内容",
      art: "请先在艺术字工具中添加文字",
      pip: "请先在画中画工具中生成并启用素材",
    };
    generateButton.title = state.disabled && !state.busy
      ? cutDraftActive && activeTool !== "cut"
        ? "剪辑方案尚未生成，请先生成剪辑视频再输出效果"
        : disabledHints[activeTool]
      : state.busy
        ? `${toolLabels[activeTool]}视频正在生成`
        : state.label;
    generateButton.setAttribute(
      "aria-label",
      state.busy ? `${toolLabels[activeTool]}视频生成中` : state.label,
    );
    if (state.error) {
      status.textContent = state.error;
      root.dataset.state = "error";
    } else if (state.busy) {
      status.textContent = `${toolLabels[activeTool]}视频正在生成，请稍候…`;
      root.dataset.state = "working";
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
    panel.hidden = true;

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
      if (activeTool === "cut") return;
      syncFrameTime();
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
    inspectorHost.hidden = isCut;
    inspector.dataset.activeTool = activeTool;
    document.body.dataset.activeEditorTool = activeTool;
    for (const [name, entry] of frameEntries) {
      entry.panel.hidden = isCut || name !== activeTool;
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

    currentJob = job;

    const ready = job.status === "completed";
    const editReady = job.edit?.status === "completed";
    const downstreamReady = ready && (!job.edit || editReady || cutDraftActive);
    const artReady = job.art?.status === "completed";
    const pipReady = job.pictureInPicture?.status === "completed";
    const artSource = editReady ? "edited" : "original";
    const pipSource = artReady ? "art" : artSource;
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

    if (cutDraftActive) {
      status.textContent =
        "删除方案已更新；可继续添加艺术字和画中画，最终输出前需先生成剪辑视频。";
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

  generateButton?.addEventListener("click", () => {
    if (generateButton.disabled) return;
    const directSource = directGenerationSources.get(activeTool);
    if (directSource) {
      directSource.click();
      return;
    }
    const entry = frameEntries.get(activeTool);
    if (!entry?.frame.contentWindow) return;
    entry.frame.contentWindow.postMessage(
      { type: "editor-suite:generate-video", kind: activeTool },
      window.location.origin,
    );
  });

  for (const [name, source] of directGenerationSources) {
    if (!source) continue;
    const generationObserver = new MutationObserver(syncGenerationButton);
    generationObserver.observe(source, {
      attributes: true,
      childList: true,
      subtree: true,
      attributeFilter: ["disabled"],
    });
    const progress = directGenerationProgress.get(name);
    if (progress) {
      generationObserver.observe(progress, {
        attributes: true,
        attributeFilter: ["hidden"],
      });
    }
    const error = directGenerationErrors.get(name);
    if (error) {
      generationObserver.observe(error, {
        attributes: true,
        childList: true,
        subtree: true,
        attributeFilter: ["hidden"],
      });
    }
  }

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
  };
  document.addEventListener("editor-suite:refresh", () => refresh());
  updateActiveTool();
  syncGenerationButton();
  refresh();
})();
