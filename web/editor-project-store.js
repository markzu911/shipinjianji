(function exposeEditorProjectStore(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorProjectStore = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function editorProjectStoreFactory(root) {
    "use strict";

    const SCHEMA_VERSION = 1;
    const ACTIONS = Object.freeze({
      PROJECT_HYDRATED: "projectHydrated",
      TRANSCRIPT_TEXT_CHANGED: "transcriptTextChanged",
      CUT_TIMING_CHANGED: "cutTimingChanged",
      ART_STATE_CHANGED: "artStateChanged",
      PIP_STATE_CHANGED: "pipStateChanged",
      ACTIVE_TOOL_CHANGED: "activeToolChanged",
      SELECTION_CHANGED: "selectionChanged",
    });

    function isObject(value) {
      return Boolean(value) && typeof value === "object";
    }

    function clone(value) {
      if (value === undefined) return undefined;
      return JSON.parse(JSON.stringify(value));
    }

    function deepFreeze(value) {
      if (!isObject(value) || Object.isFrozen(value)) return value;
      Object.freeze(value);
      for (const nested of Object.values(value)) deepFreeze(nested);
      return value;
    }

    function owned(value) {
      return deepFreeze(clone(value));
    }

    function finiteNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function normalizedRange(range) {
      const start = Math.max(0, finiteNumber(range?.start));
      const end = Math.max(start, finiteNumber(range?.end, start));
      return end > start ? { start, end } : null;
    }

    function normalizeRanges(ranges) {
      return (Array.isArray(ranges) ? ranges : [])
        .map(normalizedRange)
        .filter(Boolean)
        .sort((left, right) => left.start - right.start || left.end - right.end);
    }

    function normalizeCut(value = {}) {
      return {
        active: Boolean(value.active),
        ranges: normalizeRanges(value.ranges),
        sourceDuration: Math.max(0, finiteNumber(value.sourceDuration)),
        duration: Math.max(0, finiteNumber(value.duration)),
        transcript: isObject(value.transcript) ? clone(value.transcript) : null,
      };
    }

    function normalizeTool(value = {}, fallbackSource = "original") {
      return {
        source: String(value.source || fallbackSource),
        overlays: Array.isArray(value.overlays) ? clone(value.overlays) : [],
      };
    }

    function fallbackNormalizeTimeline(value = {}) {
      return {
        schemaVersion: 1,
        duration: Math.max(0, finiteNumber(value.duration)),
        tracks: Array.isArray(value.tracks) ? clone(value.tracks) : [],
        selection: isObject(value.selection) ? clone(value.selection) : null,
      };
    }

    function normalizeTimeline(value, timelineApi) {
      return timelineApi?.normalizeDocument
        ? timelineApi.normalizeDocument(value || {})
        : fallbackNormalizeTimeline(value || {});
    }

    function transcriptFromJob(job) {
      return isObject(job?.result) ? clone(job.result) : null;
    }

    function editableSegmentsFromJob(job) {
      return Array.isArray(job?.result?.editableSegments)
        ? clone(job.result.editableSegments)
        : [];
    }

    function cutFromJob(job) {
      const result = job?.result || {};
      const edit = job?.edit || {};
      const editReady = edit.status === "completed";
      const sourceDuration = Math.max(
        0,
        finiteNumber(result.mediaDuration || result.duration || job?.duration),
      );
      return normalizeCut({
        active: false,
        ranges: editReady ? edit.requestedRanges || edit.ranges || [] : [],
        sourceDuration,
        duration: editReady
          ? finiteNumber(edit.outputDuration)
          : sourceDuration,
        transcript: editReady && edit.transcript ? edit.transcript : result,
      });
    }

    function cutTimelineTracks(cut) {
      const segments = Array.isArray(cut?.transcript?.segments)
        ? cut.transcript.segments
        : [];
      if (!segments.length) return [];
      return [
        {
          id: "cut:transcript",
          kind: "cut",
          name: "剪后文案",
          order: 0,
          locked: true,
          clips: segments.map((segment, index) => ({
            id: `cut:segment:${segment.id ?? index}`,
            sourceId: String(segment.id ?? index),
            name: String(segment.text || `文案 ${index + 1}`),
            start: Math.max(0, finiteNumber(segment.start)),
            end: Math.max(0, finiteNumber(segment.end)),
            editable: false,
            locked: true,
            minDuration: 0.001,
            payload: {
              text: String(segment.text || ""),
              sourceStart: timingValue(segment.sourceStart),
              sourceEnd: timingValue(segment.sourceEnd),
            },
          })),
        },
      ];
    }

    function projectFromJob(job, timelineApi) {
      const normalizedJob = isObject(job) ? clone(job) : null;
      const cut = cutFromJob(normalizedJob);
      return {
        job: normalizedJob,
        transcript: transcriptFromJob(normalizedJob),
        editableSegments: editableSegmentsFromJob(normalizedJob),
        cut,
        art: normalizeTool(normalizedJob?.art || {}, "original"),
        pip: normalizeTool(
          normalizedJob?.pictureInPicture || {},
          normalizedJob?.art?.status === "completed" ? "art" : "original",
        ),
        timeline: normalizeTimeline(
          {
            duration: cut.duration || finiteNumber(normalizedJob?.duration),
            tracks: cutTimelineTracks(cut),
          },
          timelineApi,
        ),
      };
    }

    function initialState(value = {}, timelineApi) {
      const job = value?.project?.job || value?.job || null;
      const baseProject = job
        ? projectFromJob(job, timelineApi)
        : projectFromJob(null, timelineApi);
      const inputProject = isObject(value.project) ? value.project : {};
      const state = {
        schemaVersion: SCHEMA_VERSION,
        jobId: String(value.jobId || job?.id || ""),
        revision: Math.max(0, finiteNumber(value.revision)),
        timingRevision: Math.max(0, finiteNumber(value.timingRevision)),
        serverVersion: String(
          value.serverVersion || job?.updatedAt || job?.createdAt || "",
        ),
        project: {
          ...baseProject,
          transcript: inputProject.transcript
            ? clone(inputProject.transcript)
            : baseProject.transcript,
          editableSegments: Array.isArray(inputProject.editableSegments)
            ? clone(inputProject.editableSegments)
            : baseProject.editableSegments,
          cut: inputProject.cut
            ? normalizeCut(inputProject.cut)
            : baseProject.cut,
          art: inputProject.art
            ? normalizeTool(inputProject.art, "original")
            : baseProject.art,
          pip: inputProject.pip
            ? normalizeTool(inputProject.pip, "original")
            : baseProject.pip,
          timeline: normalizeTimeline(
            inputProject.timeline || baseProject.timeline,
            timelineApi,
          ),
        },
        ui: {
          activeTool: ["cut", "art", "pip"].includes(value?.ui?.activeTool)
            ? value.ui.activeTool
            : "cut",
        },
      };
      return owned(state);
    }

    function stableValue(value) {
      if (Array.isArray(value)) return value.map(stableValue);
      if (!isObject(value)) return value;
      return Object.fromEntries(
        Object.keys(value)
          .sort()
          .map((key) => [key, stableValue(value[key])]),
      );
    }

    function stableSignature(value) {
      return JSON.stringify(stableValue(value));
    }

    function timingValue(value) {
      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    }

    function toolTimingSignature(tool) {
      return stableSignature({
        source: String(tool?.source || "original"),
        overlays: (Array.isArray(tool?.overlays) ? tool.overlays : []).map(
          (overlay, index) => ({
            key: String(
              overlay?.id ??
                overlay?.assetId ??
                overlay?.imageId ??
                overlay?.trackId ??
                index,
            ),
            start: timingValue(overlay?.start),
            end: timingValue(overlay?.end),
            sourceStart: timingValue(overlay?.sourceStart),
            sourceEnd: timingValue(overlay?.sourceEnd),
          }),
        ),
      });
    }

    function cutTimingSignature(cut) {
      return stableSignature({
        active: Boolean(cut?.active),
        ranges: normalizeRanges(cut?.ranges),
        sourceDuration: timingValue(cut?.sourceDuration),
        duration: timingValue(cut?.duration),
      });
    }

    function projectTimingSignature(project) {
      return stableSignature({
        cut: cutTimingSignature(project?.cut),
        art: toolTimingSignature(project?.art),
        pip: toolTimingSignature(project?.pip),
      });
    }

    function overlayMatchKey(overlay, index) {
      if (overlay?.id !== undefined && overlay?.id !== null) {
        return `id:${overlay.id}`;
      }
      if (overlay?.assetId || overlay?.imageId) {
        return `asset:${overlay.assetId || overlay.imageId}`;
      }
      if (overlay?.trackId) {
        const sourceStart = timingValue(overlay.sourceStart);
        return `track:${overlay.trackId}:${sourceStart ?? index}`;
      }
      const sourceStart = timingValue(overlay?.sourceStart);
      const sourceEnd = timingValue(overlay?.sourceEnd);
      if (sourceStart !== null || sourceEnd !== null) {
        return `source:${sourceStart}:${sourceEnd}`;
      }
      return `index:${index}`;
    }

    function mergeArtText(currentArt, serverArt) {
      if (!Array.isArray(serverArt?.overlays) || !serverArt.overlays.length) {
        return clone(currentArt);
      }
      const serverByKey = new Map(
        serverArt.overlays.map((overlay, index) => [
          overlayMatchKey(overlay, index),
          overlay,
        ]),
      );
      function overlappingServerCue(overlay) {
        const start = timingValue(overlay?.sourceStart ?? overlay?.start);
        const end = timingValue(overlay?.sourceEnd ?? overlay?.end);
        if (start === null || end === null || end <= start) return null;
        let best = null;
        let bestOverlap = 0;
        for (const candidate of serverArt.overlays) {
          if (candidate?.trackType !== "transcript") continue;
          if (
            overlay?.trackId &&
            candidate.trackId &&
            String(overlay.trackId) !== String(candidate.trackId)
          ) {
            continue;
          }
          const candidateStart = timingValue(
            candidate.sourceStart ?? candidate.start,
          );
          const candidateEnd = timingValue(candidate.sourceEnd ?? candidate.end);
          if (candidateStart === null || candidateEnd === null) continue;
          const overlap = Math.min(end, candidateEnd) - Math.max(start, candidateStart);
          if (overlap > bestOverlap) {
            best = candidate;
            bestOverlap = overlap;
          }
        }
        return bestOverlap > 0.001 ? best : null;
      }
      const overlays = (currentArt?.overlays || []).map((overlay, index) => {
        const serverOverlay =
          serverByKey.get(overlayMatchKey(overlay, index)) ||
          overlappingServerCue(overlay) ||
          (overlay?.sourceStart === undefined && overlay?.start === undefined
            ? serverArt.overlays[index]
            : null);
        const transcriptCue =
          overlay?.trackType === "transcript" ||
          serverOverlay?.trackType === "transcript";
        if (
          !transcriptCue ||
          !serverOverlay ||
          serverOverlay.text === undefined
        ) {
          return clone(overlay);
        }
        return { ...clone(overlay), text: String(serverOverlay.text || "") };
      });
      return { ...clone(currentArt), overlays };
    }

    function mergeJobText(currentJob, incomingJob, mergedArt) {
      if (!isObject(incomingJob)) return clone(currentJob);
      const next = clone(currentJob || incomingJob);
      next.updatedAt = incomingJob.updatedAt || next.updatedAt;
      next.result = {
        ...(next.result || {}),
        text: incomingJob.result?.text ?? next.result?.text ?? "",
        segments: clone(incomingJob.result?.segments || next.result?.segments || []),
        editableSegments: clone(
          incomingJob.result?.editableSegments ||
            next.result?.editableSegments ||
            [],
        ),
      };
      if (next.art || incomingJob.art) {
        next.art = {
          ...(next.art || incomingJob.art || {}),
          overlays: clone(mergedArt?.overlays || []),
        };
      }
      return next;
    }

    function replaceTimelineKind(timeline, kind, incoming, timelineApi) {
      const existing = normalizeTimeline(timeline, timelineApi);
      const incomingDocument = normalizeTimeline(incoming || {}, timelineApi);
      return normalizeTimeline(
        {
          duration: Math.max(existing.duration, incomingDocument.duration),
          tracks: [
            ...existing.tracks.filter((track) => track.kind !== kind),
            ...incomingDocument.tracks.filter((track) => track.kind === kind),
          ],
          selection: incomingDocument.selection || existing.selection,
        },
        timelineApi,
      );
    }

    function reduceState(state, action, timelineApi) {
      if (!isObject(action) || !Object.values(ACTIONS).includes(action.type)) {
        return null;
      }
      const payload = isObject(action.payload) ? action.payload : action;
      let project = clone(state.project);
      let ui = clone(state.ui);
      let jobId = state.jobId;
      let serverVersion = state.serverVersion;

      if (action.type === ACTIONS.PROJECT_HYDRATED) {
        const job = payload.job;
        if (!isObject(job) || !job.id) return null;
        const hydrated = projectFromJob(job, timelineApi);
        const sameJob = String(job.id) === state.jobId;
        const preserveLocalTools = sameJob && payload.preserveLocalTools !== false;
        if (preserveLocalTools) {
          hydrated.art = clone(project.art);
          hydrated.pip = clone(project.pip);
          hydrated.timeline = clone(project.timeline);
          hydrated.cut = clone(project.cut);
        }
        project = hydrated;
        jobId = String(job.id);
        serverVersion = String(job.updatedAt || job.createdAt || "");
      } else if (action.type === ACTIONS.TRANSCRIPT_TEXT_CHANGED) {
        if (payload.job?.id && String(payload.job.id) !== state.jobId) return null;
        const transcript = payload.transcript || payload.job?.result;
        if (!isObject(transcript)) return null;
        const mergedArt = mergeArtText(project.art, payload.serverArt || payload.job?.art);
        project.transcript = clone(transcript);
        project.editableSegments = Array.isArray(payload.editableSegments)
          ? clone(payload.editableSegments)
          : clone(transcript.editableSegments || project.editableSegments);
        project.art = mergedArt;
        project.job = mergeJobText(project.job, payload.job, mergedArt);
        serverVersion = String(
          payload.serverVersion || payload.job?.updatedAt || serverVersion,
        );
      } else if (action.type === ACTIONS.CUT_TIMING_CHANGED) {
        project.cut = normalizeCut(payload.cut || payload);
        project.timeline = replaceTimelineKind(
          project.timeline,
          "cut",
          {
            duration: project.cut.duration,
            tracks: cutTimelineTracks(project.cut),
          },
          timelineApi,
        );
      } else if (
        action.type === ACTIONS.ART_STATE_CHANGED ||
        action.type === ACTIONS.PIP_STATE_CHANGED
      ) {
        const kind = action.type === ACTIONS.ART_STATE_CHANGED ? "art" : "pip";
        const nextTool = normalizeTool(payload[kind] || payload, project[kind].source);
        project[kind] = nextTool;
        if (payload.timeline) {
          project.timeline = replaceTimelineKind(
            project.timeline,
            kind,
            payload.timeline,
            timelineApi,
          );
        }
      } else if (action.type === ACTIONS.ACTIVE_TOOL_CHANGED) {
        const tool = String(payload.tool || payload.activeTool || "");
        if (!["cut", "art", "pip"].includes(tool)) return null;
        ui.activeTool = tool;
      } else if (action.type === ACTIONS.SELECTION_CHANGED) {
        project.timeline = normalizeTimeline(
          { ...project.timeline, selection: payload.selection || null },
          timelineApi,
        );
      }

      const comparable = { ...state, project, ui, jobId, serverVersion };
      if (stableSignature(comparable) === stableSignature(state)) return null;
      const timingChanged =
        (action.type === ACTIONS.PROJECT_HYDRATED && jobId !== state.jobId) ||
        projectTimingSignature(project) !== projectTimingSignature(state.project);
      return owned({
        ...comparable,
        revision: state.revision + 1,
        timingRevision: state.timingRevision + (timingChanged ? 1 : 0),
      });
    }

    function createStore(initial = {}, options = {}) {
      const timelineApi = options.timeline || root.EditorTimeline || null;
      let state = initialState(initial, timelineApi);
      let destroyed = false;
      const listeners = new Set();
      const effectRequests = new Map();
      const consumedEffects = new Set();

      function result(accepted) {
        return {
          accepted,
          revision: state.revision,
          timingRevision: state.timingRevision,
        };
      }

      function dispatch(action) {
        if (destroyed) return result(false);
        const previous = state;
        const next = reduceState(previous, action, timelineApi);
        if (!next) return result(false);
        state = next;
        for (const listener of listeners) listener(state, previous, action);
        return result(true);
      }

      function subscribe(listener) {
        if (destroyed || typeof listener !== "function") return () => {};
        listeners.add(listener);
        return () => listeners.delete(listener);
      }

      function beginEffect(scope) {
        const normalizedScope = String(scope || "").trim();
        if (destroyed || !normalizedScope) return null;
        const requestId = (effectRequests.get(normalizedScope) || 0) + 1;
        effectRequests.set(normalizedScope, requestId);
        return owned({
          scope: normalizedScope,
          requestId,
          baseRevision: state.revision,
          baseTimingRevision: state.timingRevision,
          jobId: state.jobId,
        });
      }

      function effectKey(token) {
        return `${token?.scope || ""}:${token?.requestId || 0}`;
      }

      function isCurrentEffect(token) {
        return Boolean(
          !destroyed &&
            token &&
            String(token.jobId || "") === state.jobId &&
            effectRequests.get(String(token.scope || "")) === token.requestId &&
            Number(token.baseTimingRevision) === state.timingRevision &&
            !consumedEffects.has(effectKey(token)),
        );
      }

      function applyEffect(token, action) {
        if (!isCurrentEffect(token)) return result(false);
        consumedEffects.add(effectKey(token));
        return dispatch(action);
      }

      function select(selector) {
        return typeof selector === "function" ? selector(state, timelineApi) : undefined;
      }

      function destroy() {
        destroyed = true;
        listeners.clear();
        effectRequests.clear();
        consumedEffects.clear();
      }

      return {
        getState: () => state,
        dispatch,
        subscribe,
        beginEffect,
        isCurrentEffect,
        applyEffect,
        select,
        destroy,
      };
    }

    function selectCutDraftMessage(state) {
      return clone({
        type: "editor-suite:cut-draft",
        ...state.project.cut,
        revision: state.revision,
        timingRevision: state.timingRevision,
        changeKind: "cut-timing",
      });
    }

    function selectToolState(state, kind) {
      if (!["art", "pip"].includes(kind)) return null;
      return clone({
        kind,
        ...state.project[kind],
        revision: state.revision,
        timingRevision: state.timingRevision,
        changeKind: "tool-state",
      });
    }

    function selectTimelineDocument(state, timelineApi = root.EditorTimeline) {
      return normalizeTimeline(state.project.timeline, timelineApi);
    }

    function selectPreviewLayers(state) {
      return clone({
        revision: state.revision,
        timingRevision: state.timingRevision,
        art: state.project.art,
        pip: state.project.pip,
      });
    }

    function selectCompositionRequest(state) {
      const job = state.project.job;
      const ranges = state.project.cut.active
        ? state.project.cut.ranges
        : job?.edit?.status === "completed"
          ? job.edit.requestedRanges || job.edit.ranges || []
          : [];
      return clone({
        target: "all",
        ranges,
        artOverlays: state.project.art.overlays,
        artSource: state.project.art.source || "original",
        pictureInPictureOverlays: state.project.pip.overlays,
        pictureInPictureSource: state.project.pip.source || "original",
        historyName: null,
      });
    }

    function selectIframeProjection(state, kind) {
      if (!["art", "pip"].includes(kind)) return null;
      return clone({
        kind,
        revision: state.revision,
        timingRevision: state.timingRevision,
        changeKind: "project-projection",
        cutDraft: state.project.cut,
        transcript: state.project.transcript,
        editableSegments: state.project.editableSegments,
        tool: state.project[kind],
      });
    }

    return {
      SCHEMA_VERSION,
      ACTIONS,
      createStore,
      cutTimingSignature,
      toolTimingSignature,
      selectCutDraftMessage,
      selectToolState,
      selectTimelineDocument,
      selectPreviewLayers,
      selectCompositionRequest,
      selectIframeProjection,
    };
  },
);
