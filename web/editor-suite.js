(() => {
  const root = document.querySelector("[data-editor-suite-nav]");
  if (!root) return;

  const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;
  const stage = root.dataset.stage || "cut";
  const initialRequestedJobId = new URLSearchParams(
    window.location.search,
  ).get("job");
  const embeddedEditor = new URLSearchParams(window.location.search).get("embedded") === "1";
  const toolLabels = {
    cut: "视频剪辑",
    art: "艺术字",
    pip: "画中画",
  };
  const PIP_MIN_WIDTH = window.EditorPipModel?.MIN_WIDTH || 0.15;

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
  const artPanelRoot = document.querySelector("#editorArtPanelRoot");
  const pipPanelRoot = document.querySelector("#editorPipPanelRoot");
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
  let legacyTimelineDocument = window.EditorTimeline.normalizeDocument({
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
  const topLevelArtEnabled = Boolean(
    projectStoreEnabled &&
      window.__EDITOR_ART_PANEL_ENABLED__ !== false &&
      window.ArtTool &&
      artPanelRoot,
  );
  const topLevelPipEnabled = Boolean(
    projectStoreEnabled &&
      window.__EDITOR_PIP_PANEL_ENABLED__ !== false &&
      window.PipTool &&
      window.EditorPipModel &&
      pipPanelRoot,
  );
  function topLevelToolEnabled(kind) {
    return kind === "art" ? topLevelArtEnabled : kind === "pip" ? topLevelPipEnabled : false;
  }
  function legacyToolNames() {
    return ["art", "pip"].filter((kind) => !topLevelToolEnabled(kind));
  }
  const mediaController = previewVideo && window.EditorMedia
    ? window.EditorMedia.createController(previewVideo)
    : null;
  let currentEditorFrame = null;
  let cutTimelineAdapter = null;
  const previewCompositor = previewOverlay && mediaController && window.EditorPreview
    ? window.EditorPreview.createCompositor({
        root: previewOverlay,
        mediaController,
        onSelect: selectSemanticClip,
        onMove: commitPreviewMove,
        onResize: commitPreviewResize,
      })
    : null;
  const timelineController = timelineLayer && window.EditorTimelineController
    ? window.EditorTimelineController.createController({
        root: timelineLayer,
        track: timelineTrack,
        timeline: window.EditorTimeline,
        mediaController,
        onSelect: selectSemanticClip,
        onCommit: commitTimelineRange,
        onSeek: (seconds) => mediaController?.seekEdited(seconds),
        onDelete: deleteSemanticClip,
      })
    : null;
  const editorDraftRestoredJobs = new Set();
  let suppressEditorDraftPersistence = false;
  const artTool = topLevelArtEnabled
    ? window.ArtTool.mount(artPanelRoot, createArtToolServices())
    : null;
  const pipTool = topLevelPipEnabled
    ? window.PipTool.mount(pipPanelRoot, createPipToolServices())
    : null;

  function projectSnapshot() {
    return projectStore?.getState() || null;
  }

  function syncProjectTimeline() {
    if (!projectStoreEnabled) return legacyTimelineDocument;
    return projectStore.select(window.EditorProjectStore.selectTimelineDocument);
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

  function editorDraftKey(jobId) {
    return `editor-suite:project-draft:${jobId}`;
  }

  function editorDraftServerVersion(job) {
    if (!job?.id) return "";
    const transcript = job.result || {};
    const edit = job.edit || null;
    const art = job.art || null;
    const signature = JSON.stringify({
      jobId: job.id,
      transcript: {
        text: transcript.text || "",
        segments: (transcript.segments || []).map((segment) => ({
          id: segment.id,
          text: segment.text,
          start: segment.start,
          end: segment.end,
        })),
      },
      edit: edit
        ? {
            status: edit.status,
            updatedAt: edit.updatedAt,
            outputDuration: edit.outputDuration,
            transcript: edit.transcript,
          }
        : null,
      art: art
        ? {
            status: art.status,
            updatedAt: art.updatedAt,
            source: art.source,
            overlays: art.overlays,
          }
        : null,
    });
    let hash = 2166136261;
    for (let index = 0; index < signature.length; index += 1) {
      hash ^= signature.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return `editor-art-base-v1:${(hash >>> 0).toString(16)}`;
  }

  function draftStorage() {
    try {
      return window.sessionStorage;
    } catch {
      return null;
    }
  }

  function isValidV2DraftSelection(value) {
    if (value === null) return true;
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value);
    return (
      keys.length === 1 &&
      keys[0] === "clipId" &&
      typeof value.clipId === "string" &&
      value.clipId.trim() === value.clipId &&
      value.clipId.length > 0
    );
  }

  function persistEditorDraft(state, action) {
    if (suppressEditorDraftPersistence || !state?.jobId) return;
    const actionType = String(action?.type || "");
    const rangeKind = String(action?.payload?.kind || "");
    const selectionId = String(
      state.project.timeline.selection?.clipId || "",
    );
    const relevant =
      [
        window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED,
        window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
      ].includes(actionType) ||
      (actionType === window.EditorProjectStore.ACTIONS.TIMELINE_CLIP_RANGE_CHANGED &&
        ["art", "pip"].includes(rangeKind)) ||
      (actionType === window.EditorProjectStore.ACTIONS.SELECTION_CHANGED &&
        (!selectionId || /^(art|pip):/.test(selectionId))) ||
      actionType === window.EditorProjectStore.ACTIONS.TRANSCRIPT_TEXT_CHANGED;
    if (!relevant) return;
    const storage = draftStorage();
    if (!storage) return;
    try {
      storage.setItem(
        editorDraftKey(state.jobId),
        JSON.stringify({
          schemaVersion: 2,
          jobId: state.jobId,
          serverVersion: editorDraftServerVersion(state.project.job),
          revision: state.revision,
          art: {
            source: state.project.art.source,
            overlays: state.project.art.overlays,
          },
          pip: {
            source: state.project.pip.source,
            overlays: state.project.pip.overlays,
          },
          selection: /^(art|pip):/.test(selectionId)
            ? { clipId: selectionId }
            : null,
          savedAt: new Date().toISOString(),
        }),
      );
    } catch {
      // Draft recovery is best-effort and never replaces Store authority.
    }
  }

  function restoreEditorDraft(state) {
    if (
      (!topLevelArtEnabled && !topLevelPipEnabled) ||
      !state?.jobId ||
      editorDraftRestoredJobs.has(state.jobId)
    ) {
      return false;
    }
    if (state.project.job?.status !== "completed" || !state.project.job?.result) {
      return false;
    }
    const storage = draftStorage();
    if (!storage) return false;
    let envelope;
    try {
      envelope = JSON.parse(storage.getItem(editorDraftKey(state.jobId)) || "null");
    } catch {
      editorDraftRestoredJobs.add(state.jobId);
      return false;
    }
    if (
      ![1, 2].includes(envelope?.schemaVersion) ||
      envelope.jobId !== state.jobId ||
      String(envelope.serverVersion || "") !==
        editorDraftServerVersion(state.project.job) ||
      !envelope.art ||
      !Array.isArray(envelope.art.overlays) ||
      (envelope.schemaVersion === 2 &&
        (!envelope.pip ||
          !Array.isArray(envelope.pip.overlays) ||
          !isValidV2DraftSelection(envelope.selection)))
    ) {
      editorDraftRestoredJobs.add(state.jobId);
      return false;
    }
    const source = String(envelope.art.source || state.project.art.source);
    const duration = Math.max(
      Number(state.project.timeline.duration) || 0,
      Number(state.project.cut.duration) || 0,
    );
    const rawOverlays = envelope.art.overlays;
    const validRecords = rawOverlays.length <= 500 && rawOverlays.every(
      (overlay) =>
        overlay &&
        typeof overlay === "object" &&
        String(overlay.id ?? "").trim() &&
        String(overlay.text ?? "").trim() &&
        [overlay.start, overlay.end, overlay.x, overlay.y].every((value) =>
          Number.isFinite(Number(value)),
        ),
    );
    const uniqueIds = new Set(rawOverlays.map((overlay) => String(overlay?.id ?? "")));
    if (
      !["original", "edited"].includes(source) ||
      !validRecords ||
      uniqueIds.size !== rawOverlays.length
    ) {
      editorDraftRestoredJobs.add(state.jobId);
      return false;
    }
    const overlays = rawOverlays.map((overlay) =>
      window.EditorArtModel.normalizeOverlay(overlay, { duration }),
    );
    if (overlays.length && window.EditorArtModel.validateOverlays(overlays, duration)) {
      editorDraftRestoredJobs.add(state.jobId);
      return false;
    }
    const art = {
      source,
      overlays,
      assets: [],
    };
    let pip = null;
    if (envelope.schemaVersion === 2) {
      const pipSource = String(envelope.pip.source || state.project.pip.source);
      const pipOverlays = window.EditorPipModel?.validateDraftOverlays(
        envelope.pip.overlays,
        {
          source: pipSource,
          duration,
          assets: state.project.pip.assets,
        },
      );
      if (
        !window.EditorPipModel?.SOURCES.includes(pipSource) ||
        pipSource !== state.project.pip.source ||
        !pipOverlays
      ) {
        editorDraftRestoredJobs.add(state.jobId);
        return false;
      }
      pip = {
        source: pipSource,
        overlays: pipOverlays,
        assets: state.project.pip.assets,
      };
    }
    const requestedSelection = envelope.schemaVersion === 2
      ? envelope.selection?.clipId || ""
      : String(envelope.selection?.clipId || "");
    const artSelectionValid = art.overlays.some(
      (overlay) => `art:${overlay.id}` === requestedSelection,
    );
    const pipSelectionValid = pip?.overlays.some(
      (overlay) => `pip:${overlay.assetId}` === requestedSelection,
    );
    if (
      envelope.schemaVersion === 2 &&
      requestedSelection &&
      !artSelectionValid &&
      !pipSelectionValid
    ) {
      editorDraftRestoredJobs.add(state.jobId);
      return false;
    }
    const selection = artSelectionValid || pipSelectionValid
      ? { clipId: requestedSelection }
      : null;
    const artTimeline = window.EditorArtModel.buildTimeline(
      art,
      duration,
      selection,
    );
    const pipTimeline = pip
      ? window.EditorPipModel.buildTimeline(pip, duration, selection)
      : { tracks: [] };
    const timeline = window.EditorTimeline.normalizeDocument({
      duration,
      tracks: [...artTimeline.tracks, ...pipTimeline.tracks],
      selection,
    });
    const restored = projectStore.dispatch({
      type: window.EditorProjectStore.ACTIONS.PROJECT_DRAFT_RESTORED,
      payload: {
        jobId: state.jobId,
        serverVersion: state.serverVersion,
        art,
        ...(pip ? { pip } : {}),
        timeline,
      },
    }).accepted;
    editorDraftRestoredJobs.add(state.jobId);
    return restored;
  }

  async function artApiRequest(path, options = {}) {
    const response = await fetch(path, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `请求失败（${response.status}）`);
    }
    return payload;
  }

  function replaceArtState(art, options = {}) {
    if (!projectStore || !window.EditorArtModel) {
      return { accepted: false, revision: 0, timingRevision: 0 };
    }
    const state = projectSnapshot();
    const nextArt = {
      ...state.project.art,
      ...art,
      overlays: Array.isArray(art?.overlays) ? art.overlays : [],
    };
    const requestedSelection = options.selection === undefined
      ? state.project.timeline.selection
      : options.selection
        ? { clipId: String(options.selection) }
        : null;
    const timeline = window.EditorArtModel.buildTimeline(
      nextArt,
      Math.max(
        Number(state.project.timeline.duration) || 0,
        Number(state.project.cut.duration) || 0,
      ),
      requestedSelection,
    );
    const action = {
      type: window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED,
      payload: { art: nextArt, timeline },
    };
    return options.token
      ? projectStore.applyEffect(options.token, action)
      : projectStore.dispatch(action);
  }

  function selectArt(id) {
    if (!projectStore || id === undefined || id === null) return false;
    return projectStore.dispatch({
      type: window.EditorProjectStore.ACTIONS.SELECTION_CHANGED,
      payload: { selection: { clipId: `art:${id}` } },
    });
  }

  function setArtRange(id, start, end, anchors = {}) {
    const state = projectSnapshot();
    const overlay = state?.project.art.overlays.find(
      (item) => String(item.id) === String(id),
    );
    if (!overlay) return false;
    const range = window.EditorArtModel.normalizeRange(
      start,
      end,
      state.project.timeline.duration || state.project.cut.duration,
      window.EditorArtModel.isTranscriptOverlay(overlay) ? 0.02 : 0.05,
    );
    const sourceStart = Number.isFinite(Number(anchors.sourceStart))
      ? Number(anchors.sourceStart)
      : mediaController?.editedToSource(range.start, "start");
    const sourceEnd = Number.isFinite(Number(anchors.sourceEnd))
      ? Number(anchors.sourceEnd)
      : mediaController?.editedToSource(range.end, "end");
    return projectStore.dispatch({
      type: window.EditorProjectStore.ACTIONS.TIMELINE_CLIP_RANGE_CHANGED,
      payload: {
        kind: "art",
        clipId: `art:${id}`,
        sourceId: String(id),
        ...range,
        sourceStart,
        sourceEnd,
      },
    });
  }

  async function saveArtTranscript(text, options = {}) {
    const state = projectSnapshot();
    if (!state?.jobId) throw new Error("当前视频任务不可用。");
    const token = options.token || projectStore.beginEffect("art-transcript-save");
    await artApiRequest(
      `/api/transcriptions/${encodeURIComponent(state.jobId)}/transcript`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
        signal: options.signal,
      },
    );
    if (
      !projectStore.isCurrentEffect(token) ||
      token.baseRevision !== projectSnapshot().revision
    ) {
      return { accepted: false, revision: projectSnapshot().revision };
    }
    const job = await artApiRequest(
      `/api/transcriptions/${encodeURIComponent(state.jobId)}`,
      { signal: options.signal },
    );
    if (
      !projectStore.isCurrentEffect(token) ||
      token.baseRevision !== projectSnapshot().revision
    ) {
      return { accepted: false, revision: projectSnapshot().revision };
    }
    const result = projectStore.applyEffect(token, {
      type: window.EditorProjectStore.ACTIONS.TRANSCRIPT_TEXT_CHANGED,
      payload: {
        job,
        transcript: job.result,
        editableSegments: job.result?.editableSegments || [],
        serverArt: job.art || null,
        serverVersion: job.updatedAt || "",
      },
    });
    if (result.accepted) {
      currentJob = projectSnapshot().project.job;
      syncGenerationButton();
    }
    return result;
  }

  function createArtToolServices() {
    return {
      project: {
        snapshot: projectSnapshot,
        subscribe: (listener) => projectStore?.subscribe(listener) || (() => {}),
        dispatch: (action) => projectStore?.dispatch(action),
        beginEffect: (scope) => projectStore?.beginEffect(scope) || null,
        isCurrentEffect: (token) => projectStore?.isCurrentEffect(token) || false,
      },
      media: {
        currentEditedTime: workspaceCurrentTime,
        seekEdited: (seconds) => mediaController?.seekEdited(seconds),
        editedToSource: (seconds, edge) =>
          mediaController?.editedToSource(seconds, edge),
        subscribeFrame: (listener) =>
          mediaController?.subscribeFrame(listener) || (() => {}),
      },
      preview: {
        setArtDraft: (overlay) => previewCompositor?.setArtDraft(overlay),
      },
      commands: {
        replaceArt: replaceArtState,
        selectArt,
        setArtRange,
        saveTranscript: saveArtTranscript,
        refreshJob: refresh,
        generateCurrentPreview,
      },
      api: { request: artApiRequest },
      feedback: {
        confirm: (options) => window.appConfirm(options),
        generation: window.appGeneration,
      },
    };
  }

  function replacePipState(pip, options = {}) {
    if (!projectStore || !window.EditorPipModel) {
      return { accepted: false, revision: 0, timingRevision: 0 };
    }
    const state = projectSnapshot();
    const duration = Math.max(
      Number(state.project.timeline.duration) || 0,
      Number(state.project.cut.duration) || 0,
    );
    const current = state.project.pip;
    const nextPip = window.EditorPipModel.normalizeProject(
      {
        ...current,
        ...pip,
        assets: window.EditorPipModel.mergeAssets(
          current.assets,
          pip?.assets,
          { source: pip?.source || current.source },
        ),
        overlays: Array.isArray(pip?.overlays) ? pip.overlays : current.overlays,
      },
      {
        fallbackSource: current.source,
        duration,
      },
    );
    const requestedSelection = options.selection === undefined
      ? state.project.timeline.selection
      : options.selection
        ? { clipId: String(options.selection) }
        : null;
    const timeline = window.EditorPipModel.buildTimeline(
      nextPip,
      duration,
      requestedSelection,
    );
    const action = {
      type: window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
      payload: { pip: nextPip, timeline },
    };
    return options.token
      ? projectStore.applyEffect(options.token, action)
      : projectStore.dispatch(action);
  }

  function selectPip(id) {
    const state = projectSnapshot();
    const normalizedId = String(id || "");
    if (
      !projectStore ||
      !state?.project.pip.overlays.some(
        (overlay) => String(overlay.assetId || overlay.id) === normalizedId,
      )
    ) {
      return false;
    }
    return projectStore.dispatch({
      type: window.EditorProjectStore.ACTIONS.SELECTION_CHANGED,
      payload: { selection: { clipId: `pip:${normalizedId}` } },
    });
  }

  function setPipRange(id, start, end, anchors = {}) {
    const state = projectSnapshot();
    const overlay = state?.project.pip.overlays.find(
      (item) => String(item.assetId || item.id) === String(id),
    );
    if (!overlay) return false;
    const range = window.EditorPipModel.normalizeRange(
      start,
      end,
      state.project.timeline.duration || state.project.cut.duration,
      0.05,
    );
    if (!range) return false;
    const sourceStart = Number.isFinite(Number(anchors.sourceStart))
      ? Number(anchors.sourceStart)
      : mediaController?.editedToSource(range.start, "start");
    const sourceEnd = Number.isFinite(Number(anchors.sourceEnd))
      ? Number(anchors.sourceEnd)
      : mediaController?.editedToSource(range.end, "end");
    return projectStore.dispatch({
      type: window.EditorProjectStore.ACTIONS.TIMELINE_CLIP_RANGE_CHANGED,
      payload: {
        kind: "pip",
        clipId: `pip:${id}`,
        sourceId: String(id),
        ...range,
        sourceStart,
        sourceEnd,
      },
    });
  }

  function createPipToolServices() {
    return {
      project: {
        snapshot: projectSnapshot,
        subscribe: (listener) => projectStore?.subscribe(listener) || (() => {}),
        beginEffect: (scope) => projectStore?.beginEffect(scope) || null,
        isCurrentEffect: (token) => projectStore?.isCurrentEffect(token) || false,
      },
      media: {
        currentEditedTime: workspaceCurrentTime,
        seekEdited: (seconds) => mediaController?.seekEdited(seconds),
        editedToSource: (seconds, edge) =>
          mediaController?.editedToSource(seconds, edge),
        subscribeFrame: (listener) =>
          mediaController?.subscribeFrame(listener) || (() => {}),
      },
      commands: {
        replacePip: replacePipState,
        selectPip,
        setPipRange,
        generateCurrentPreview,
      },
      api: { request: artApiRequest },
      feedback: {
        confirm: (options) => window.appConfirm(options),
        generation: window.appGeneration,
      },
    };
  }

  const unsubscribeProjectStore = projectStore?.subscribe((next, previous, action) => {
    renderEditorFrame(next);
    if (action.type === window.EditorProjectStore.ACTIONS.TRANSCRIPT_TEXT_CHANGED) {
      for (const name of legacyToolNames()) {
        postTranscriptTextProjection(name, next);
      }
    }
    if (next.ui.activeTool !== previous.ui.activeTool) {
      activeTool = next.ui.activeTool;
    }
    if (topLevelArtEnabled || topLevelPipEnabled) persistEditorDraft(next, action);
  }) || (() => {});

  function syncToolTimeline(kind, timeline, options = {}) {
    if (!timeline || !Array.isArray(timeline.tracks)) return;
    const duration = Math.max(
      legacyTimelineDocument.duration,
      Number(timeline.duration) || 0,
    );
    const selection =
      options.selection !== undefined
        ? options.selection
        : kind === activeTool
          ? timeline.selection?.clipId || null
          : undefined;
    legacyTimelineDocument = window.EditorTimeline.normalizeDocument({
      ...legacyTimelineDocument,
      duration,
      tracks: [
        ...legacyTimelineDocument.tracks.filter((track) => track.kind !== kind),
        ...timeline.tracks.filter((track) => track.kind === kind),
      ],
      selection: selection === undefined
        ? legacyTimelineDocument.selection
        : selection
          ? { clipId: String(selection) }
          : null,
    });
    renderEditorFrame();
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
    if (projectStoreEnabled) {
      if (currentEditorFrame) previewCompositor?.render(currentEditorFrame);
    } else {
      renderMirroredPreview();
    }
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
    const art = toolStates.get("art") || (
      currentJob?.art?.overlays
        ? {
            source: currentJob.art.source || "original",
            overlays: currentJob.art.overlays,
          }
        : { overlays: [] }
    );
    const pictureInPicture = toolStates.get("pip") || (
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

  function selectCurrentProjectFrame(state = projectSnapshot()) {
    if (!projectStoreEnabled || !state) return null;
    return window.EditorProjectStore.selectEditorFrame(
      state,
      window.EditorTimeline,
    );
  }

  function compositionRequest() {
    const frame = selectCurrentProjectFrame();
    if (frame) return frame.composition;
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

  function compositionValidationError(frame = selectCurrentProjectFrame()) {
    const overlays = frame?.preview?.art?.overlays || [];
    if (!overlays.length || !window.EditorArtModel?.validateOverlays) return "";
    return window.EditorArtModel.validateOverlays(
      overlays,
      Number(frame.timeline?.duration) || Number(currentJob?.duration) || 0,
    );
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
      disabled: !compositionReady() || Boolean(compositionValidationError()),
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
    const frame = selectCurrentProjectFrame();
    const validationError = compositionValidationError(frame);
    if (validationError) {
      status.textContent = validationError;
      root.dataset.state = "error";
      syncGenerationButton();
      return;
    }
    const request = frame?.composition || compositionRequest();
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
    return mediaController?.currentEditedTime() || 0;
  }

  function workspaceSourceTime(editedTime) {
    return mediaController?.editedToSource(editedTime) || 0;
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
    if (!entry?.frame?.contentWindow || !mediaController) return;
    entry.frame.contentWindow.postMessage(
      {
        type: "editor-suite:sync-time",
        currentTime: workspaceCurrentTime(),
        playing: !mediaController.video().paused,
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
  }

  function fallbackEditorFrame() {
    const composition = compositionRequest();
    return {
      revision: 0,
      timingRevision: 0,
      media: {
        jobId: String(currentJob?.id || ""),
        sourceUrl: currentJob?.id
          ? `/api/transcriptions/${encodeURIComponent(currentJob.id)}/original-video`
          : "",
        sourceDuration: Math.max(
          0,
          Number(cutDraftState.sourceDuration || currentJob?.duration) || 0,
        ),
        cutRanges: composition.ranges,
      },
      preview: {
        art: toolStates.get("art") || { source: "original", overlays: [], assets: [] },
        pip: toolStates.get("pip") || { source: "original", overlays: [], assets: [] },
        selection: legacyTimelineDocument.selection,
      },
      timeline: legacyTimelineDocument,
      composition,
    };
  }

  function renderEditorFrame(state = projectSnapshot()) {
    if (!mediaController) return null;
    const nextFrame = selectCurrentProjectFrame(state) || fallbackEditorFrame();
    currentEditorFrame = nextFrame;
    mediaController.applyFrame(nextFrame);
    previewCompositor?.render(nextFrame);
    timelineController?.render(nextFrame);
    artTool?.render(nextFrame);
    pipTool?.render(nextFrame);
    if (previewOverlay) {
      previewOverlay.hidden = !(
        nextFrame.preview.art.overlays.length ||
        nextFrame.preview.pip.overlays.length
      );
    }
    syncDouyinBasePlayback();
    return nextFrame;
  }

  function renderMirroredPreview() {
    return renderEditorFrame();
  }

  function renderMirroredTimeline() {
    return renderEditorFrame();
  }

  function semanticClipDetails(value = {}) {
    const clip = value.clip || null;
    const kind = String(value.kind || clip?.kind || value.track?.kind || "");
    const clipId = String(value.clipId || clip?.id || "");
    const sourceId = String(value.id || clip?.sourceId || "");
    return { kind, clipId, sourceId, clip };
  }

  function selectSemanticClip(value = {}) {
    const details = semanticClipDetails(value);
    if (!details.clipId || !["cut", "art", "pip"].includes(details.kind)) {
      return false;
    }
    const result = projectStore?.dispatch({
      type: window.EditorProjectStore.ACTIONS.SELECTION_CHANGED,
      payload: { selection: { clipId: details.clipId } },
    }) || { accepted: true };
    if (["art", "pip"].includes(details.kind)) {
      openTool(details.kind, desiredToolUrls.get(details.kind));
      if (!topLevelToolEnabled(details.kind)) {
        acknowledgeToolProjection(details.kind);
        postProjectProjection(details.kind, {
          type: "editor-suite:timeline-action",
          action: "select",
          kind: details.kind,
          clipId: details.clipId,
          sourceId: details.sourceId,
          currentTime: details.clip?.start ?? workspaceCurrentTime(),
          revision: projectSnapshot()?.revision,
        });
      }
    }
    return result;
  }

  function commitTimelineRange(transaction) {
    let cutProjection = null;
    if (transaction.kind === "cut" && cutTimelineAdapter?.applyRange) {
      cutProjection = cutTimelineAdapter.applyRange(transaction);
      if (!cutProjection) return false;
    }
    const committedTransaction = ["art", "pip"].includes(transaction.kind) && mediaController
      ? {
          ...transaction,
          sourceStart: mediaController.editedToSource(transaction.start, "start"),
          sourceEnd: mediaController.editedToSource(transaction.end, "end"),
        }
      : transaction;
    const result = projectStore?.dispatch(
      transaction.kind === "cut" && cutProjection
        ? {
            type: window.EditorProjectStore.ACTIONS.CUT_TIMING_CHANGED,
            payload: cutProjection,
          }
        : {
            type: window.EditorProjectStore.ACTIONS.TIMELINE_CLIP_RANGE_CHANGED,
            payload: committedTransaction,
          },
    ) || { accepted: true };
    if (
      result.accepted &&
      ["art", "pip"].includes(transaction.kind) &&
      !topLevelToolEnabled(transaction.kind)
    ) {
      acknowledgeToolProjection(transaction.kind);
      postProjectProjection(transaction.kind, {
        type: "editor-suite:timeline-action",
        action: "set-range",
        kind: transaction.kind,
        clipId: transaction.clipId,
        sourceId: transaction.sourceId,
        start: transaction.start,
        end: transaction.end,
        currentTime: transaction.start,
        revision: result.revision,
      });
      postProjectProjection(transaction.kind, {
        type: "editor-suite:timeline-action",
        action: "commit",
        kind: transaction.kind,
        clipId: transaction.clipId,
        sourceId: transaction.sourceId,
        start: transaction.start,
        end: transaction.end,
        currentTime: transaction.start,
        revision: result.revision,
      });
    }
    return result;
  }

  function deleteSemanticClip(value = {}) {
    const details = semanticClipDetails(value);
    if (details.kind === "cut") {
      return cutTimelineAdapter?.deleteRange?.(details.sourceId) ?? false;
    }
    return false;
  }

  function commitPreviewPatch(value, patch, messageType) {
    const kind = String(value?.kind || "");
    const id = String(value?.id || "");
    if (!projectStore || !["art", "pip"].includes(kind) || !id) return false;
    const state = projectSnapshot();
    const tool = state.project[kind];
    const selected = tool.overlays.find(
      (overlay) => String(overlay.id) === id,
    );
    if (!selected) return false;
    const overlays = tool.overlays.map((overlay) => {
      if (
        kind === "art" &&
        selected.trackType === "transcript" &&
        selected.trackId &&
        overlay.trackId === selected.trackId
      ) {
        return { ...overlay, ...patch };
      }
      return String(overlay.id) === id ? { ...overlay, ...patch } : overlay;
    });
    const result = projectStore.dispatch({
      type: kind === "art"
        ? window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED
        : window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
      payload: { ...tool, overlays },
    });
    if (!result.accepted) return result;
    if (!topLevelToolEnabled(kind)) {
      acknowledgeToolProjection(kind);
      postProjectProjection(kind, {
        type: messageType,
        kind,
        id,
        ...patch,
        revision: result.revision,
      });
      postProjectProjection(kind, {
        type: "editor-suite:move-finish",
        kind,
        id,
        revision: result.revision,
      });
    }
    return result;
  }

  function commitPreviewMove(value) {
    return commitPreviewPatch(
      value,
      { x: Number(value.x), y: Number(value.y) },
      "editor-suite:move-effect",
    );
  }

  function commitPreviewResize(value) {
    const width = Number(value.width);
    if (!Number.isFinite(width) || width < PIP_MIN_WIDTH) return false;
    return commitPreviewPatch(
      value,
      { width },
      "editor-suite:resize-effect",
    );
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
    if (artPanelRoot) {
      const selected = !isCut && activeTool === "art" && topLevelArtEnabled;
      artPanelRoot.classList.toggle("is-active", selected);
      artPanelRoot.setAttribute("aria-hidden", String(!selected));
      artPanelRoot.toggleAttribute("inert", !selected);
      if (selected) artTool?.activate();
      else artTool?.deactivate();
    }
    if (pipPanelRoot) {
      const selected = !isCut && activeTool === "pip" && topLevelPipEnabled;
      pipPanelRoot.classList.toggle("is-active", selected);
      pipPanelRoot.setAttribute("aria-hidden", String(!selected));
      pipPanelRoot.toggleAttribute("inert", !selected);
      if (selected) pipTool?.activate();
      else pipTool?.deactivate();
    }
    if (!projectStoreEnabled) {
      renderMirroredPreview();
      renderMirroredTimeline();
    }
    updateActiveTool();
    syncGenerationButton();
    syncSaveButton();
    if (!isCut && !topLevelToolEnabled(activeTool)) {
      window.requestAnimationFrame(() => syncFrameTime(activeTool));
    }
  }

  function openTool(name, href = "", options = {}) {
    if (!tools.has(name)) return false;
    const tool = tools.get(name);
    if (tool.getAttribute("aria-disabled") === "true") return false;
    if (!supportsInlineWorkspace()) {
      if (href && !options.fromNavigation) window.location.href = href;
      return false;
    }
    if (name !== "cut" && !topLevelToolEnabled(name)) {
      const targetHref = href || desiredToolUrls.get(name) || tool.href;
      if (!targetHref || targetHref === "#") return false;
      ensureToolFrame(name, targetHref);
    }
    if (
      name === "art" &&
      topLevelArtEnabled &&
      !String(projectSnapshot()?.project.timeline.selection?.clipId || "").startsWith("art:")
    ) {
      const firstArt = projectSnapshot()?.project.art.overlays[0];
      if (firstArt) selectArt(firstArt.id);
    }
    if (
      name === "pip" &&
      topLevelPipEnabled &&
      !String(projectSnapshot()?.project.timeline.selection?.clipId || "").startsWith("pip:")
    ) {
      const firstPip = projectSnapshot()?.project.pip.overlays[0];
      if (firstPip) selectPip(firstPip.assetId || firstPip.id);
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
      suppressEditorDraftPersistence = true;
      projectStore?.dispatch({
        type: window.EditorProjectStore.ACTIONS.PROJECT_HYDRATED,
        payload: { job, preserveLocalTools: true },
      });
      if (projectStoreEnabled) restoreEditorDraft(projectSnapshot());
      suppressEditorDraftPersistence = false;
    }
    const jobChanged = job.id !== previousJobId;
    previousJobId = job.id;
    if (jobChanged && !projectStoreEnabled) {
      legacyTimelineDocument = window.EditorTimeline.normalizeDocument({
        duration: Number(job.duration) || 0,
        tracks: [],
      });
    }
    if (
      jobChanged &&
      stage === "cut" &&
      initialRequestedJobId !== job.id
    ) {
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
        !topLevelArtEnabled &&
        artHref &&
        tools.get("art")?.getAttribute("aria-disabled") !== "true"
      ) {
        ensureToolFrame("art", artHref);
      }
      for (const name of legacyToolNames()) {
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
      payload: {
        cut: nextCutDraftState,
        timeline: payload.timeline || null,
      },
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
      for (const name of legacyToolNames()) {
        syncFrameCutDraft(name);
      }
    }
    if (currentJob) renderJobState(currentJob);
    else syncGenerationButton();
  }

  function setTimelineTracks(kind, tracks, options = {}) {
    if (projectStoreEnabled) {
      const timeline = {
        duration: Math.max(0, Number(options.duration) || 0),
        tracks: Array.isArray(tracks) ? tracks : [],
        selection: options.selection
          ? { clipId: String(options.selection) }
          : null,
      };
      if (kind === "cut") {
        projectStore.dispatch({
          type: window.EditorProjectStore.ACTIONS.CUT_TIMING_CHANGED,
          payload: {
            cut: projectSnapshot().project.cut,
            timeline,
          },
        });
      } else if (["art", "pip"].includes(kind)) {
        const currentTool = projectSnapshot().project[kind];
        projectStore.dispatch({
          type:
            kind === "art"
              ? window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED
              : window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
          payload: {
            ...currentTool,
            timeline,
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
    return legacyTimelineDocument;
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
        mediaController?.seekEdited(nextTime);
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
      source: String(data.source || projectSnapshot()?.project[data.kind]?.source || "original"),
      overlays: Array.isArray(data.overlays) ? data.overlays : [],
      assets: Array.isArray(data.assets) ? data.assets : [],
      timeline: data.timeline || null,
      generationDisabled: data.generationDisabled !== false,
      generationLabel: String(data.generationLabel || ""),
      generationBusy: Boolean(data.generationBusy),
      generationError: String(data.generationError || ""),
      revision: messageRevision,
      timingRevision: bridgeRevision(data.timingRevision),
      changeKind: String(data.changeKind || "tool-state"),
    };
    toolStates.set(data.kind, bridgeState);
    if (projectStoreEnabled) {
      projectStore.dispatch({
        type:
          data.kind === "art"
            ? window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED
            : window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
        payload: {
          source: bridgeState.source,
          overlays: bridgeState.overlays,
          assets: bridgeState.assets,
          timeline: bridgeState.timeline,
        },
      });
      acknowledgeToolProjection(data.kind);
    } else {
      syncToolTimeline(data.kind, data.timeline);
    }
    syncGenerationButton();
    if (!projectStoreEnabled) {
      renderMirroredPreview();
      renderMirroredTimeline();
    }
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
    if (topLevelToolEnabled(data.kind)) return;
    toolStates.set(data.kind, data);
    if (projectStoreEnabled) {
      projectStore.dispatch({
        type:
          data.kind === "art"
            ? window.EditorProjectStore.ACTIONS.ART_STATE_CHANGED
            : window.EditorProjectStore.ACTIONS.PIP_STATE_CHANGED,
        payload: {
          source: data.source || projectSnapshot().project[data.kind].source,
          overlays: Array.isArray(data.overlays) ? data.overlays : [],
          assets: Array.isArray(data.assets) ? data.assets : [],
          timeline: data.timeline || null,
        },
      });
    } else {
      syncToolTimeline(data.kind, data.timeline);
    }
    syncGenerationButton();
    if (!projectStoreEnabled) {
      renderMirroredPreview();
      renderMirroredTimeline();
    }
  });

  mediaController?.subscribeFrame(() => {
    for (const name of frameEntries.keys()) syncFrameTime(name);
    syncMirroredPlayback();
  });
  mediaController?.subscribeState(() => {
    for (const name of frameEntries.keys()) syncFrameTime(name);
    syncMirroredPlayback();
  });

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
    const media = target.querySelector("img, video");
    const imageAspectRatio = Math.max(
      0.1,
      media?.naturalWidth && media?.naturalHeight
        ? media.naturalWidth / media.naturalHeight
        : media?.videoWidth && media?.videoHeight
          ? media.videoWidth / media.videoHeight
          : targetRect.width / targetRect.height,
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
      const width = Math.max(PIP_MIN_WIDTH, startWidth + widthChange);
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

  if (!previewCompositor) previewOverlay?.addEventListener("pointerdown", (event) => {
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

  if (!timelineController) timelineLayer?.addEventListener(
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
        const transientTimelineStore = window.EditorTimeline.createStore(
          syncProjectTimeline(),
        );
        const clip = transientTimelineStore.findClip(clipId);
        const frame = frameEntries.get(kind)?.frame;
        if (!clip || !frame?.contentWindow) return;
        openTool(kind, desiredToolUrls.get(kind));
        transientTimelineStore.selectClip(clipId, { silent: true });
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
        mediaController?.seekEdited(clip.start);
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
          transientTimelineStore.snapshot().duration,
          Number(previewVideo.duration) || 0,
          Number(document.querySelector("#cutFrameTimelineSeek")?.max) || 0,
        );
        const pointerSession = window.EditorTimeline.createPointerSession(
          transientTimelineStore,
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
          mediaController?.seekEdited(currentTime);
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
        mediaController?.seekEdited(start);
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
        mediaController?.seekEdited(currentTime);
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
        if (total > 0) mediaController?.seekEdited(ratio * total);
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
    timelineSnapshot: () => syncProjectTimeline(),
    mediaController: () => mediaController,
    clearMediaSource: (options = {}) => mediaController?.clearSource(options) || false,
    setMediaSource: (url, options = {}) => mediaController?.setSource(url, options) || false,
    seekSource: (seconds) => mediaController?.seekSource(seconds),
    seekEdited: (seconds) => mediaController?.seekEdited(seconds),
    registerCutTimelineAdapter: (adapter) => {
      cutTimelineAdapter = adapter && typeof adapter === "object" ? adapter : null;
      return () => {
        if (cutTimelineAdapter === adapter) cutTimelineAdapter = null;
      };
    },
    projectStoreEnabled: () => projectStoreEnabled,
    topLevelArtEnabled: () => topLevelArtEnabled,
    topLevelPipEnabled: () => topLevelPipEnabled,
    projectSnapshot,
    subscribeProject: (listener) => projectStore?.subscribe(listener) || (() => {}),
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
  renderEditorFrame(projectSnapshot());
  window.addEventListener("beforeunload", () => {
    unsubscribeProjectStore();
    artTool?.destroy();
    pipTool?.destroy();
    previewCompositor?.destroy();
    timelineController?.destroy();
    mediaController?.destroy();
    projectStore?.destroy();
  });
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
