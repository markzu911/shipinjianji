(() => {
  const root = document.querySelector("[data-editor-suite-nav]");
  if (!root) return;

  const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;
  const stage = root.dataset.stage || "cut";
  const initialRequestedJobId = new URLSearchParams(
    window.location.search,
  ).get("job");
  const initialArtTemplateSelection = parseRequestedArtTemplate(
    window.location.search,
  );
  const PIP_MIN_WIDTH = window.EditorPipModel?.MIN_WIDTH || 0.15;

  function parseRequestedArtTemplate(search) {
    const query = new URLSearchParams(search || "");
    const id = String(query.get("template") || "").trim();
    if (!id) return null;
    const sizeValue = query.get("templateSize");
    const rawSize =
      sizeValue === null || sizeValue.trim() === ""
        ? null
        : Number(sizeValue);
    return Object.freeze({
      id,
      color: query.get("templateColor"),
      strokeColor: query.get("templateStroke"),
      font: query.get("templateFont"),
      fontSize: Number.isFinite(rawSize) ? rawSize : null,
    });
  }

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
    cutDraftRevision: 0,
    sourceDuration: 0,
    duration: 0,
    transcript: null,
  };
  const projectStore = window.EditorProjectStore.createStore(
    { ui: { activeTool } },
    { timeline: window.EditorTimeline },
  );
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
        visibleKinds: ["art", "pip"],
        mediaController,
        onSelect: selectSemanticClip,
        onCommit: commitTimelineRange,
        onSeek: (seconds) => mediaController?.seekEdited(seconds),
        onDelete: deleteSemanticClip,
      })
    : null;
  const editorDraftRestoredJobs = new Set();
  let suppressEditorDraftPersistence = false;
  const artTool = window.ArtTool.mount(artPanelRoot, createArtToolServices());
  const pipTool = window.PipTool.mount(pipPanelRoot, createPipToolServices());

  function projectSnapshot() {
    return projectStore.getState();
  }

  function syncProjectTimeline() {
    return projectStore.select(window.EditorProjectStore.selectTimelineDocument);
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
      actionType === window.EditorProjectStore.ACTIONS.TRANSCRIPT_TEXT_CHANGED ||
      actionType === window.EditorProjectStore.ACTIONS.CUT_TIMING_CHANGED;
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
            suppressedOverlays: state.project.art.suppressedOverlays || [],
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
    const rawSuppressedOverlays = Array.isArray(envelope.art.suppressedOverlays)
      ? envelope.art.suppressedOverlays
      : [];
    const allRawOverlays = [...rawOverlays, ...rawSuppressedOverlays];
    const validRecords = allRawOverlays.length <= 500 && allRawOverlays.every(
      (overlay) =>
        overlay &&
        typeof overlay === "object" &&
        String(overlay.id ?? "").trim() &&
        String(overlay.text ?? "").trim() &&
        [overlay.start, overlay.end, overlay.x, overlay.y].every((value) =>
          Number.isFinite(Number(value)),
        ),
    );
    const uniqueIds = new Set(allRawOverlays.map((overlay) => String(overlay?.id ?? "")));
    if (
      !["original", "edited"].includes(source) ||
      !validRecords ||
      uniqueIds.size !== allRawOverlays.length
    ) {
      editorDraftRestoredJobs.add(state.jobId);
      return false;
    }
    const overlays = rawOverlays.map((overlay) =>
      window.EditorArtModel.normalizeOverlay(overlay, { duration }),
    );
    const suppressedOverlays = rawSuppressedOverlays.map((overlay) =>
      window.EditorArtModel.normalizeOverlay(overlay, {
        duration: Math.max(duration, Number(state.project.cut.sourceDuration) || 0),
      }),
    );
    if (overlays.length && window.EditorArtModel.validateOverlays(overlays, duration)) {
      editorDraftRestoredJobs.add(state.jobId);
      return false;
    }
    const art = {
      source,
      overlays,
      suppressedOverlays,
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

  function createArtToolServices() {
    return {
      project: {
        snapshot: projectSnapshot,
        subscribe: (listener) => projectStore.subscribe(listener),
        dispatch: (action) => projectStore.dispatch(action),
        beginEffect: (scope) => projectStore.beginEffect(scope),
        isCurrentEffect: (token) => projectStore.isCurrentEffect(token),
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
        refreshJob: refresh,
        generateCurrentPreview,
      },
      api: { request: artApiRequest },
      feedback: {
        confirm: (options) => window.appConfirm(options),
        generation: window.appGeneration,
      },
      initialTemplateSelection: initialArtTemplateSelection,
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
        subscribe: (listener) => projectStore.subscribe(listener),
        beginEffect: (scope) => projectStore.beginEffect(scope),
        isCurrentEffect: (token) => projectStore.isCurrentEffect(token),
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

  const unsubscribeProjectStore = projectStore.subscribe((next, previous, action) => {
    renderEditorFrame(next);
    if (next.ui.activeTool !== previous.ui.activeTool) {
      activeTool = next.ui.activeTool;
    }
    persistEditorDraft(next, action);
  });

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
    if (currentEditorFrame) previewCompositor?.render(currentEditorFrame);
    syncDouyinBasePlayback();
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

  function selectCurrentProjectFrame(state = projectSnapshot()) {
    if (!state) return null;
    return window.EditorProjectStore.selectEditorFrame(
      state,
      window.EditorTimeline,
    );
  }

  function compositionRequest() {
    const frame = selectCurrentProjectFrame();
    return frame?.composition || null;
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
    const { target, historyName, cutDraftRevision, ...visual } = value;
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
    generateButton.disabled = true;
    generateButton.classList.add("is-busy");
    status.textContent = "正在创建当前预览合成任务…";
    root.dataset.state = "working";
    try {
      if (typeof cutTimelineAdapter?.flushDraft === "function") {
        await cutTimelineAdapter.flushDraft();
      }
      const frame = selectCurrentProjectFrame();
      const validationError = compositionValidationError(frame);
      if (validationError) throw new Error(validationError);
      const request = frame.composition;
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
          redirectOnClose: "/",
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
      if (url.pathname !== "/") return "";
      const tool = url.searchParams.get("tool");
      return ["art", "pip"].includes(tool) ? tool : "cut";
    } catch {
      return "";
    }
    return "";
  }

  function workspaceCurrentTime() {
    return mediaController?.currentEditedTime() || 0;
  }

  function updateBrowserTool(name, replace = false) {
    if (!supportsInlineWorkspace()) return;
    const url = new URL(window.location.href);
    if (name === "cut") url.searchParams.delete("tool");
    else url.searchParams.set("tool", name);
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({ ...(window.history.state || {}), editorTool: name }, "", url);
  }

  function renderEditorFrame(state = projectSnapshot()) {
    if (!mediaController) return null;
    const nextFrame = selectCurrentProjectFrame(state);
    if (!nextFrame) return null;
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
    const selectedClipId = String(
      projectSnapshot().project.timeline.selection?.clipId || "",
    );
    const result = selectedClipId === details.clipId
      ? { accepted: true }
      : projectStore.dispatch({
          type: window.EditorProjectStore.ACTIONS.SELECTION_CHANGED,
          payload: { selection: { clipId: details.clipId } },
        });
    if (["art", "pip"].includes(details.kind)) {
      openTool(details.kind);
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
    const result = projectStore.dispatch(
      transaction.kind === "cut" && cutProjection
        ? {
            type: window.EditorProjectStore.ACTIONS.CUT_TIMING_CHANGED,
            payload: cutProjection,
          }
        : {
            type: window.EditorProjectStore.ACTIONS.TIMELINE_CLIP_RANGE_CHANGED,
            payload: committedTransaction,
          },
    );
    return result;
  }

  function deleteSemanticClip(value = {}) {
    const details = semanticClipDetails(value);
    if (details.kind === "cut") {
      return cutTimelineAdapter?.deleteRange?.(details.sourceId) ?? false;
    }
    return false;
  }

  function commitPreviewPatch(value, patch) {
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
    return result;
  }

  function commitPreviewMove(value) {
    return commitPreviewPatch(
      value,
      { x: Number(value.x), y: Number(value.y) },
    );
  }

  function commitPreviewResize(value) {
    const width = Number(value.width);
    if (!Number.isFinite(width) || width < PIP_MIN_WIDTH) return false;
    return commitPreviewPatch(
      value,
      { width },
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
    cutPanelStack.toggleAttribute("inert", !isCut);
    inspectorHost.hidden = false;
    inspectorHost.classList.toggle("is-background", isCut);
    inspectorHost.setAttribute("aria-hidden", String(isCut));
    inspector.dataset.activeTool = activeTool;
    document.body.dataset.activeEditorTool = activeTool;
    if (artPanelRoot) {
      const selected = !isCut && activeTool === "art";
      artPanelRoot.classList.toggle("is-active", selected);
      artPanelRoot.setAttribute("aria-hidden", String(!selected));
      artPanelRoot.toggleAttribute("inert", !selected);
      if (selected) artTool?.activate();
      else artTool?.deactivate();
    }
    if (pipPanelRoot) {
      const selected = !isCut && activeTool === "pip";
      pipPanelRoot.classList.toggle("is-active", selected);
      pipPanelRoot.setAttribute("aria-hidden", String(!selected));
      pipPanelRoot.toggleAttribute("inert", !selected);
      if (selected) pipTool?.activate();
      else pipTool?.deactivate();
    }
    updateActiveTool();
    syncGenerationButton();
    syncSaveButton();
  }

  function openTool(name, href = "", options = {}) {
    if (!tools.has(name)) return false;
    const tool = tools.get(name);
    if (tool.getAttribute("aria-disabled") === "true") return false;
    if (!supportsInlineWorkspace()) {
      return false;
    }
    if (
      name === "art" &&
      !String(projectSnapshot()?.project.timeline.selection?.clipId || "").startsWith("art:")
    ) {
      const firstArt = projectSnapshot()?.project.art.overlays[0];
      if (firstArt) selectArt(firstArt.id);
    }
    if (
      name === "pip" &&
      !String(projectSnapshot()?.project.timeline.selection?.clipId || "").startsWith("pip:")
    ) {
      const firstPip = projectSnapshot()?.project.pip.overlays[0];
      if (firstPip) selectPip(firstPip.assetId || firstPip.id);
    }
    activeTool = name;
    projectStore.dispatch({
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
      projectStore.dispatch({
        type: window.EditorProjectStore.ACTIONS.PROJECT_HYDRATED,
        payload: { job, preserveLocalTools: true },
      });
      restoreEditorDraft(projectSnapshot());
      suppressEditorDraftPersistence = false;
    }
    const jobChanged = job.id !== previousJobId;
    previousJobId = job.id;
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
      `/?job=${encodedJobId}&source=${artSource}&tool=art`,
      downstreamReady,
    );
    setToolLink(
      "pip",
      `/?job=${encodedJobId}&source=${pipSource}&tool=pip`,
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
      const requestedTool = new URLSearchParams(window.location.search).get("tool");
      if (["art", "pip"].includes(requestedTool) && tools.get(requestedTool)?.getAttribute("aria-disabled") !== "true") {
        openTool(requestedTool, tools.get(requestedTool)?.href, {
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
      cutDraftRevision: Math.max(
        0,
        Number(payload.cutDraftRevision ?? cutDraftState.cutDraftRevision) || 0,
      ),
      sourceDuration: Math.max(0, Number(payload.sourceDuration) || 0),
      duration: Math.max(0, Number(payload.duration) || 0),
      transcript: payload.transcript || null,
    };
    const commit = projectStore.dispatch({
      type: window.EditorProjectStore.ACTIONS.CUT_TIMING_CHANGED,
      payload: {
        cut: nextCutDraftState,
        timeline: payload.timeline || null,
      },
    });
    cutDraftState = projectSnapshot().project.cut;
    cutDraftActive = cutDraftState.active;
    updateDouyinBaseVideo();
    if (currentJob && commit.accepted) {
      renderJobState(currentJob, { hydrateProject: false });
    } else syncGenerationButton();
    return commit;
  }

  function setTimelineTracks(kind, tracks, options = {}) {
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

  douyinPreviewToggle?.addEventListener("click", () => {
    setDouyinPreviewEnabled(!douyinPreviewEnabled);
  });

  for (const [name, tool] of tools) {
    tool.addEventListener("click", (event) => {
      event.preventDefault();
      if (tool.getAttribute("aria-disabled") === "true") return;
      openTool(name, tool.href);
    });
  }

  document.addEventListener(
    "click",
    (event) => {
      if (event.defaultPrevented) return;
      const anchor = event.target.closest("a[href]");
      if (!anchor || root.contains(anchor) || anchor.hasAttribute("download")) return;
      const name = toolFromHref(anchor.getAttribute("href"));
      if (!["art", "pip"].includes(name) || !supportsInlineWorkspace()) return;
      event.preventDefault();
      openTool(name, anchor.href);
    },
    true,
  );

  mediaController?.subscribeFrame(syncDouyinBasePlayback);
  mediaController?.subscribeState(syncDouyinBasePlayback);

  generateButton?.addEventListener("click", generateCurrentPreview);
  saveButton?.addEventListener("click", saveCurrentVersion);

  window.addEventListener("popstate", () => {
    if (!supportsInlineWorkspace()) return;
    const requested = new URLSearchParams(window.location.search).get("tool");
    const name = ["art", "pip"].includes(requested) ? requested : "cut";
    openTool(name, tools.get(name)?.href, {
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
    parseRequestedArtTemplate,
    projectSnapshot,
    subscribeProject: (listener) => projectStore.subscribe(listener),
    beginProjectEffect: (scope) => projectStore.beginEffect(scope),
    isCurrentProjectEffect: (token) =>
      projectStore.isCurrentEffect(token),
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
    projectStore.destroy();
  });
  document.addEventListener("editor-suite:refresh", () => refresh());
  updateActiveTool();
  syncGenerationButton();
  refresh();
})();
