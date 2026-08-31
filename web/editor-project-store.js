(function exposeEditorProjectStore(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorProjectStore = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function editorProjectStoreFactory(root) {
    "use strict";

    const SCHEMA_VERSION = 1;
    const CUT_RECONCILIATION_FIELD = "_cutReconciliation";
    const ACTIONS = Object.freeze({
      PROJECT_HYDRATED: "projectHydrated",
      PROJECT_DRAFT_RESTORED: "projectDraftRestored",
      TRANSCRIPT_TEXT_CHANGED: "transcriptTextChanged",
      CUT_TIMING_CHANGED: "cutTimingChanged",
      CUT_STRUCTURE_CHANGED: "cutStructureChanged",
      ART_STATE_CHANGED: "artStateChanged",
      PIP_STATE_CHANGED: "pipStateChanged",
      TIMELINE_KIND_CHANGED: "timelineKindChanged",
      TIMELINE_CLIP_RANGE_CHANGED: "timelineClipRangeChanged",
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

    function normalizeSplitPoints(points) {
      const seenKeys = new Set();
      const normalized = [];
      for (const point of Array.isArray(points) ? points : []) {
        const key = String(point?.key || "").trim();
        const sourceTime = Number(point?.sourceTime);
        if (!key || !Number.isFinite(sourceTime) || seenKeys.has(key)) continue;
        seenKeys.add(key);
        normalized.push({ key, sourceTime: Math.max(0, sourceTime) });
      }
      return normalized.sort(
        (left, right) =>
          left.sourceTime - right.sourceTime || left.key.localeCompare(right.key),
      );
    }

    function normalizeCut(value = {}) {
      return {
        active: Boolean(value.active),
        ranges: normalizeRanges(value.ranges),
        splitPoints: normalizeSplitPoints(value.splitPoints),
        cutDraftRevision: Math.max(
          0,
          finiteNumber(value.cutDraftRevision),
        ),
        sourceDuration: Math.max(0, finiteNumber(value.sourceDuration)),
        duration: Math.max(0, finiteNumber(value.duration)),
        transcript: isObject(value.transcript) ? clone(value.transcript) : null,
      };
    }

    function semanticOverlayId(kind, overlay, index) {
      if (overlay?.id !== undefined && overlay?.id !== null && overlay.id !== "") {
        return overlay.id;
      }
      if (kind === "pip" && (overlay?.assetId || overlay?.imageId)) {
        return String(overlay.assetId || overlay.imageId);
      }
      if (overlay?.trackId) {
        return `${kind}:${overlay.trackId}:${timingValue(overlay.sourceStart) ?? index}`;
      }
      return `${kind}:overlay:${index}`;
    }

    function normalizeAssets(assets, options = {}) {
      if (root.EditorPipModel?.normalizeAssets) {
        return root.EditorPipModel.normalizeAssets(assets, options);
      }
      const records = Array.isArray(assets)
        ? assets
        : isObject(assets)
          ? Object.values(assets)
          : [];
      const byId = new Map();
      for (const record of records) {
        const id = String(record?.id || record?.assetId || record?.imageId || "");
        if (!id) continue;
        byId.set(id, {
          ...clone(record),
          id,
          type: record.type === "video" || record.assetType === "video"
            ? "video"
            : "image",
          assetUrl: String(record.assetUrl || record.imageUrl || ""),
        });
      }
      return [...byId.values()];
    }

    function normalizeTool(
      value = {},
      fallbackSource = "original",
      kind = "art",
      fallbackAssets = [],
    ) {
      if (kind === "pip" && root.EditorPipModel?.normalizeProject) {
        const source = root.EditorPipModel.normalizeSource(
          value.source,
          fallbackSource,
        );
        return root.EditorPipModel.normalizeProject(
          {
            ...clone(value),
            source,
            assets: [
              ...normalizeAssets(fallbackAssets, { source }),
              ...normalizeAssets(value.assets, { source }),
            ],
          },
          { fallbackSource: source },
        );
      }
      const overlays = (Array.isArray(value.overlays) ? value.overlays : []).map(
        (overlay, index) => ({
          ...clone(overlay),
          id: semanticOverlayId(kind, overlay, index),
        }),
      );
      const activeIds = new Set(overlays.map((overlay) => String(overlay.id)));
      const suppressedOverlays = kind === "art"
        ? (Array.isArray(value.suppressedOverlays) ? value.suppressedOverlays : [])
            .map((overlay, index) => ({
              ...clone(overlay),
              id: semanticOverlayId(kind, overlay, overlays.length + index),
            }))
            .filter((overlay) => !activeIds.has(String(overlay.id)))
        : [];
      return {
        source: String(value.source || fallbackSource),
        overlays,
        ...(kind === "art" ? { suppressedOverlays } : {}),
        assets: normalizeAssets(
          value.assets === undefined
            ? fallbackAssets
            : [...normalizeAssets(fallbackAssets), ...normalizeAssets(value.assets)],
        ),
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

    function toolTimelineTracks(kind, tool) {
      if (kind === "art" && root.EditorArtModel?.buildTimelineTracks) {
        return root.EditorArtModel.buildTimelineTracks(tool?.overlays || []);
      }
      return (tool?.overlays || []).map((overlay, index) => {
        const sourceId = String(
          overlay.id ?? overlay.assetId ?? overlay.imageId ?? index,
        );
        return {
          id: `${kind}:overlay:${sourceId}`,
          kind,
          name: kind === "pip" ? "画中画" : String(overlay.text || "艺术字"),
          order: index,
          clips: [{
            id: `${kind}:${sourceId}`,
            sourceId,
            kind,
            name: kind === "pip" ? "画中画" : String(overlay.text || "艺术字"),
            start: Math.max(0, finiteNumber(overlay.start)),
            end: Math.max(0, finiteNumber(overlay.end)),
            minDuration: kind === "art" && overlay.trackType === "transcript"
              ? 0.02
              : 0.05,
            payload: {
              trackId: overlay.trackId || null,
              trackType: overlay.trackType || null,
              sourceStart: timingValue(overlay.sourceStart),
              sourceEnd: timingValue(overlay.sourceEnd),
            },
          }],
        };
      });
    }

    function projectFromJob(job, timelineApi) {
      const normalizedJob = isObject(job) ? clone(job) : null;
      const cut = cutFromJob(normalizedJob);
      const art = normalizeTool(
        normalizedJob?.art || {},
        normalizedJob?.edit?.status === "completed" ? "edited" : "original",
        "art",
      );
      const pip = normalizeTool(
        {
          ...(normalizedJob?.pictureInPicture || {}),
          assets: [
            ...(normalizedJob?.pictureInPictureImages || []).map((asset) => ({
              ...asset,
              type: "image",
            })),
            ...(normalizedJob?.pictureInPictureVideos || []).map((asset) => ({
              ...asset,
              type: "video",
            })),
          ],
        },
        normalizedJob?.art?.status === "completed" ? "art" : "original",
        "pip",
      );
      return {
        job: normalizedJob,
        transcript: transcriptFromJob(normalizedJob),
        editableSegments: editableSegmentsFromJob(normalizedJob),
        cut,
        art,
        pip,
        timeline: normalizeTimeline(
          {
            duration: cut.duration || finiteNumber(normalizedJob?.duration),
            tracks: [
              ...cutTimelineTracks(cut),
              ...toolTimelineTracks("art", art),
              ...toolTimelineTracks("pip", pip),
            ],
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
            ? normalizeTool(inputProject.art, "original", "art")
            : baseProject.art,
          pip: inputProject.pip
            ? normalizeTool(inputProject.pip, "original", "pip")
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
        timeline: (project?.timeline?.tracks || [])
          .map((track) => ({
            id: String(track?.id || ""),
            kind: String(track?.kind || ""),
            clips: (track?.clips || [])
              .map((clip) => ({
                id: String(clip?.id || ""),
                start: timingValue(clip?.start),
                end: timingValue(clip?.end),
              }))
              .sort((left, right) => left.id.localeCompare(right.id)),
          }))
          .sort((left, right) =>
            `${left.kind}:${left.id}`.localeCompare(`${right.kind}:${right.id}`),
          ),
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

    function textCharacterTimings(overlay, text) {
      const count = [...String(text || "")].filter(
        (character) => !/\s/u.test(character),
      ).length;
      const supplied = Array.isArray(overlay?.characterTimings)
        ? overlay.characterTimings.flatMap((timing) => {
            const start = Number(timing?.start);
            const end = Number(timing?.end);
            return Number.isFinite(start) && Number.isFinite(end) && end > start
              ? [{ start, end }]
              : [];
          })
        : [];
      if (supplied.length === count || !count) return supplied;
      const start = Number(overlay?.start);
      const end = Number(overlay?.end);
      if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return [];
      return Array.from({ length: count }, (_, index) => ({
        start: start + ((end - start) * index) / count,
        end: start + ((end - start) * (index + 1)) / count,
      }));
    }

    function mergeTranscriptOverlayText(overlay, text) {
      const next = {
        ...clone(overlay),
        text,
        characterTimings: textCharacterTimings(overlay, text),
      };
      const reconciliation = overlay?.[CUT_RECONCILIATION_FIELD];
      if (isObject(reconciliation?.overlay)) {
        next[CUT_RECONCILIATION_FIELD] = {
          ...clone(reconciliation),
          overlay: {
            ...clone(reconciliation.overlay),
            text,
            characterTimings: textCharacterTimings(reconciliation.overlay, text),
          },
        };
      }
      return next;
    }

    function preserveOverlayTiming(overlay, baseline) {
      if (!baseline) return clone(overlay);
      const next = {
        ...clone(overlay),
        start: clone(baseline.start),
        end: clone(baseline.end),
        characterTimings: textCharacterTimings(baseline, overlay?.text),
      };
      for (const field of ["sourceStart", "sourceEnd"]) {
        if (Object.prototype.hasOwnProperty.call(baseline, field)) {
          next[field] = clone(baseline[field]);
        } else {
          delete next[field];
        }
      }
      return next;
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
      function mergeOverlays(items, options = {}) {
        return (items || []).map((overlay, index) => {
          const serverOverlay =
            serverByKey.get(overlayMatchKey(overlay, index)) ||
            (options.allowOverlap ? overlappingServerCue(overlay) : null) ||
            (options.allowOverlap &&
            overlay?.sourceStart === undefined &&
            overlay?.start === undefined
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
          return mergeTranscriptOverlayText(
            overlay,
            String(serverOverlay.text || ""),
          );
        });
      }
      return {
        ...clone(currentArt),
        overlays: mergeOverlays(currentArt?.overlays, { allowOverlap: true }),
        suppressedOverlays: mergeOverlays(currentArt?.suppressedOverlays),
      };
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
          suppressedOverlays: clone(mergedArt?.suppressedOverlays || []),
        };
      }
      return next;
    }

    function replaceTimelineKind(
      timeline,
      kind,
      incoming,
      timelineApi,
      options = {},
    ) {
      const existing = normalizeTimeline(timeline, timelineApi);
      const incomingDocument = normalizeTimeline(incoming || {}, timelineApi);
      const incomingTracks = incomingDocument.tracks.filter(
        (track) => track.kind === kind,
      );
      const firstExistingIndex = existing.tracks.findIndex(
        (track) => track.kind === kind,
      );
      const retainedTracks = existing.tracks.filter(
        (track) => track.kind !== kind,
      );
      const kindOrder = { cut: 0, art: 1, pip: 2 };
      let insertionIndex = firstExistingIndex;
      if (insertionIndex < 0) {
        const rank = kindOrder[kind] ?? Number.POSITIVE_INFINITY;
        insertionIndex = retainedTracks.findIndex(
          (track) => (kindOrder[track.kind] ?? Number.POSITIVE_INFINITY) > rank,
        );
        if (insertionIndex < 0) insertionIndex = retainedTracks.length;
      }
      retainedTracks.splice(insertionIndex, 0, ...incomingTracks);
      return normalizeTimeline(
        {
          duration: Math.max(existing.duration, incomingDocument.duration),
          tracks: retainedTracks,
          selection: options.acceptIncomingSelection
            ? incomingDocument.selection
            : existing.selection,
        },
        timelineApi,
      );
    }

    function updateTimelineClipRange(timeline, payload, timelineApi) {
      const store = timelineApi?.createStore?.(timeline || {});
      const clipId = String(payload.clipId || "");
      if (!store || !clipId) return null;
      const clip = store.setClipRange(clipId, payload.start, payload.end, {
        silent: true,
      });
      if (!clip) return null;
      if (payload.selection !== false) store.selectClip(clipId, { silent: true });
      return { clip, timeline: store.snapshot() };
    }

    function resolveArtSelection(selection, previousArt, nextArt, activeIds) {
      const selectedClipId = String(selection?.clipId || "");
      const selectedArtId = selectedClipId.startsWith("art:")
        ? selectedClipId.slice(4)
        : "";
      if (!selectedArtId || activeIds.includes(selectedArtId)) return selection;
      const hidden = [
        ...(previousArt?.overlays || []),
        ...(previousArt?.suppressedOverlays || []),
        ...(nextArt?.suppressedOverlays || []),
      ].find((overlay) => String(overlay.id) === selectedArtId);
      const sameTrack = hidden?.trackId
        ? (nextArt?.overlays || [])
            .filter((overlay) => overlay.trackId === hidden.trackId)
            .sort((left, right) =>
              Math.abs(finiteNumber(left.start) - finiteNumber(hidden.start)) -
              Math.abs(finiteNumber(right.start) - finiteNumber(hidden.start)),
            )[0]
        : null;
      return sameTrack ? { clipId: `art:${sameTrack.id}` } : null;
    }

    function updateToolOverlayRange(
      tool,
      clip,
      start,
      end,
      sourceStart,
      sourceEnd,
    ) {
      let matched = false;
      const hasSourceRange =
        Number.isFinite(Number(sourceStart)) &&
        Number.isFinite(Number(sourceEnd)) &&
        Number(sourceEnd) > Number(sourceStart);
      const overlays = tool.overlays.map((overlay) => {
        const overlayId = String(
          overlay.id ?? overlay.assetId ?? overlay.imageId ?? "",
        );
        if (
          overlayId !== String(clip.sourceId) &&
          overlayId !== String(clip.id).replace(/^(art|pip):/, "")
        ) {
          return overlay;
        }
        matched = true;
        const oldStart = Number(overlay.start);
        const oldEnd = Number(overlay.end);
        const oldDuration = oldEnd - oldStart;
        const newDuration = end - start;
        const characterTimings =
          Array.isArray(overlay.characterTimings) &&
          Number.isFinite(oldStart) &&
          Number.isFinite(oldEnd) &&
          oldDuration > 0 &&
          Number.isFinite(start) &&
          Number.isFinite(end) &&
          newDuration > 0
            ? overlay.characterTimings.map((timing) => ({
                ...timing,
                start:
                  start +
                  ((Number(timing.start) - oldStart) / oldDuration) * newDuration,
                end:
                  start +
                  ((Number(timing.end) - oldStart) / oldDuration) * newDuration,
              }))
            : overlay.characterTimings;
        return {
          ...overlay,
          start,
          end,
          ...(Array.isArray(characterTimings) ? { characterTimings } : {}),
          ...(hasSourceRange
            ? { sourceStart: Number(sourceStart), sourceEnd: Number(sourceEnd) }
            : {}),
        };
      });
      return matched ? { ...tool, overlays } : tool;
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
          hydrated.pip = normalizeTool(
            {
              ...clone(project.pip),
              assets: hydrated.pip.assets,
            },
            project.pip.source,
            "pip",
            project.pip.assets,
          );
          hydrated.timeline = clone(project.timeline);
          hydrated.cut = clone(project.cut);
        }
        project = hydrated;
        jobId = String(job.id);
        serverVersion = String(job.updatedAt || job.createdAt || "");
      } else if (action.type === ACTIONS.PROJECT_DRAFT_RESTORED) {
        if (
          String(payload.jobId || "") !== state.jobId ||
          String(payload.serverVersion || "") !== state.serverVersion ||
          (!isObject(payload.art) && !isObject(payload.pip))
        ) {
          return null;
        }
        let restoredArtBeforeReconciliation = null;
        let restoredArtReconciliation = null;
        if (isObject(payload.art)) {
          project.art = normalizeTool(
            payload.art,
            project.art.source,
            "art",
            project.art.assets,
          );
          restoredArtBeforeReconciliation = project.art;
          restoredArtReconciliation = root.EditorArtModel?.reconcileArtWithCut?.(
            project.art,
            project.cut,
            project.cut,
          ) || null;
          if (restoredArtReconciliation?.art) {
            project.art = normalizeTool(
              restoredArtReconciliation.art,
              project.art.source,
              "art",
              project.art.assets,
            );
          }
        }
        if (isObject(payload.pip)) {
          project.pip = normalizeTool(
            payload.pip,
            project.pip.source,
            "pip",
            project.pip.assets,
          );
        }
        if (payload.timeline) {
          if (isObject(payload.art)) {
            project.timeline = replaceTimelineKind(
              project.timeline,
              "art",
              payload.timeline,
              timelineApi,
            );
          }
          if (isObject(payload.pip)) {
            project.timeline = replaceTimelineKind(
              project.timeline,
              "pip",
              payload.timeline,
              timelineApi,
            );
          }
          project.timeline = normalizeTimeline(
            {
              ...project.timeline,
              selection: payload.timeline.selection || null,
            },
            timelineApi,
          );
        }
        if (restoredArtReconciliation?.art) {
          const incomingSelection = payload.timeline?.selection || project.timeline.selection;
          const artSelection = resolveArtSelection(
            incomingSelection,
            restoredArtBeforeReconciliation,
            project.art,
            restoredArtReconciliation.activeIds,
          );
          project.timeline = replaceTimelineKind(
            project.timeline,
            "art",
            {
              duration: project.cut.duration,
              tracks: toolTimelineTracks("art", project.art),
              selection: artSelection,
            },
            timelineApi,
            {
              acceptIncomingSelection: String(incomingSelection?.clipId || "")
                .startsWith("art:"),
            },
          );
        }
        project.timeline = normalizeTimeline(
          { ...project.timeline, duration: project.cut.duration },
          timelineApi,
        );
      } else if (action.type === ACTIONS.TRANSCRIPT_TEXT_CHANGED) {
        if (payload.job?.id && String(payload.job.id) !== state.jobId) return null;
        const transcript = payload.transcript || payload.job?.result;
        if (!isObject(transcript)) return null;
        const mergedArt = mergeArtText(project.art, payload.serverArt || payload.job?.art);
        const selectionBeforeTextChange = project.timeline.selection;
        let artBeforeReconciliation = null;
        let artReconciliation = null;
        project.transcript = clone(transcript);
        project.editableSegments = Array.isArray(payload.editableSegments)
          ? clone(payload.editableSegments)
          : clone(transcript.editableSegments || project.editableSegments);
        project.art = mergedArt;
        if (isObject(payload.cutTranscript)) {
          project.cut = normalizeCut({
            ...project.cut,
            transcript: payload.cutTranscript,
          });
          artBeforeReconciliation = project.art;
          artReconciliation = root.EditorArtModel?.reconcileArtWithCut?.(
            project.art,
            project.cut,
            project.cut,
          ) || null;
          if (artReconciliation?.art) {
            const baselineById = new Map(
              [
                ...(artBeforeReconciliation?.overlays || []),
                ...(artBeforeReconciliation?.suppressedOverlays || []),
              ].map((overlay) => [
                String(overlay?.id || ""),
                overlay,
              ]),
            );
            project.art = normalizeTool(
              {
                ...artReconciliation.art,
                overlays: artReconciliation.art.overlays.map((overlay) =>
                  preserveOverlayTiming(
                    overlay,
                    baselineById.get(String(overlay?.id || "")),
                  ),
                ),
              },
              project.art.source,
              "art",
              project.art.assets,
            );
          }
          project.timeline = replaceTimelineKind(
            project.timeline,
            "cut",
            {
              duration: project.cut.duration,
              tracks: [
                ...cutTimelineTracks(project.cut),
                ...project.timeline.tracks.filter(
                  (track) =>
                    track.kind === "cut" && track.id !== "cut:transcript",
                ),
              ],
            },
            timelineApi,
          );
        }
        project.job = mergeJobText(project.job, payload.job, project.art);
        const currentSelection = String(selectionBeforeTextChange?.clipId || "")
          .startsWith("art:")
          ? selectionBeforeTextChange
          : project.timeline.selection;
        const selectedArtId = String(currentSelection?.clipId || "").startsWith("art:")
          ? String(currentSelection.clipId).slice(4)
          : "";
        const artSelection = artReconciliation?.art
          ? resolveArtSelection(
              currentSelection,
              artBeforeReconciliation,
              project.art,
              artReconciliation.activeIds,
            )
          : currentSelection;
        project.timeline = replaceTimelineKind(
          project.timeline,
          "art",
          {
            duration: project.cut.duration,
            tracks: toolTimelineTracks("art", project.art),
            selection: artSelection,
          },
          timelineApi,
          { acceptIncomingSelection: Boolean(selectedArtId) },
        );
        serverVersion = String(
          payload.serverVersion || payload.job?.updatedAt || serverVersion,
        );
      } else if (action.type === ACTIONS.CUT_STRUCTURE_CHANGED) {
        const incomingStructure = normalizeCut(payload.cut || payload);
        project.cut = normalizeCut({
          ...project.cut,
          splitPoints: incomingStructure.splitPoints,
        });
        if (payload.timeline) {
          const incomingCutTimeline = normalizeTimeline(
            payload.timeline,
            timelineApi,
          );
          project.timeline = replaceTimelineKind(
            project.timeline,
            "cut",
            {
              duration: Math.max(
                project.cut.duration,
                Number(incomingCutTimeline.duration) || 0,
              ),
              tracks: [
                ...cutTimelineTracks(project.cut),
                ...incomingCutTimeline.tracks.filter(
                  (track) =>
                    track.kind === "cut" && track.id !== "cut:transcript",
                ),
              ],
              selection: incomingCutTimeline.selection,
            },
            timelineApi,
            { acceptIncomingSelection: ui.activeTool === "cut" },
          );
          project.timeline = normalizeTimeline(
            { ...project.timeline, duration: project.cut.duration },
            timelineApi,
          );
        }
      } else if (action.type === ACTIONS.CUT_TIMING_CHANGED) {
        const previousCut = project.cut;
        const previousArt = project.art;
        const selectionBeforeCut = project.timeline.selection;
        project.cut = normalizeCut(payload.cut || payload);
        const cutTimingChanged =
          cutTimingSignature(previousCut) !== cutTimingSignature(project.cut);
        const reconciliation = cutTimingChanged
          ? root.EditorArtModel?.reconcileArtWithCut?.(
              project.art,
              previousCut,
              project.cut,
            )
          : null;
        if (reconciliation?.art) {
          project.art = normalizeTool(
            reconciliation.art,
            project.art.source,
            "art",
            project.art.assets,
          );
        }
        const incomingCutTimeline = payload.timeline
          ? normalizeTimeline(payload.timeline, timelineApi)
          : { duration: project.cut.duration, tracks: [] };
        project.timeline = replaceTimelineKind(
          project.timeline,
          "cut",
          {
            duration: Math.max(
              project.cut.duration,
              Number(incomingCutTimeline.duration) || 0,
            ),
            tracks: [
              ...cutTimelineTracks(project.cut),
              ...incomingCutTimeline.tracks.filter(
                (track) => track.kind === "cut" && track.id !== "cut:transcript",
              ),
            ],
            selection: incomingCutTimeline.selection,
          },
          timelineApi,
          { acceptIncomingSelection: ui.activeTool === "cut" },
        );
        if (reconciliation?.art) {
          const currentSelection = String(selectionBeforeCut?.clipId || "").startsWith("art:")
            ? selectionBeforeCut
            : project.timeline.selection;
          const selectedClipId = String(currentSelection?.clipId || "");
          const selectedArtId = selectedClipId.startsWith("art:")
            ? selectedClipId.slice(4)
            : "";
          const artSelection = resolveArtSelection(
            currentSelection,
            previousArt,
            project.art,
            reconciliation.activeIds,
          );
          project.timeline = replaceTimelineKind(
            project.timeline,
            "art",
            {
              duration: project.cut.duration,
              tracks: toolTimelineTracks("art", project.art),
              selection: artSelection,
            },
            timelineApi,
            { acceptIncomingSelection: Boolean(selectedArtId) },
          );
        }
        project.timeline = normalizeTimeline(
          { ...project.timeline, duration: project.cut.duration },
          timelineApi,
        );
      } else if (
        action.type === ACTIONS.ART_STATE_CHANGED ||
        action.type === ACTIONS.PIP_STATE_CHANGED
      ) {
        const kind = action.type === ACTIONS.ART_STATE_CHANGED ? "art" : "pip";
        const nextTool = normalizeTool(
          payload[kind] || payload,
          project[kind].source,
          kind,
          project[kind].assets,
        );
        project[kind] = nextTool;
        if (payload.timeline) {
          project.timeline = replaceTimelineKind(
            project.timeline,
            kind,
            payload.timeline,
            timelineApi,
            { acceptIncomingSelection: ui.activeTool === kind },
          );
        }
      } else if (action.type === ACTIONS.TIMELINE_KIND_CHANGED) {
        const kind = String(payload.kind || "");
        if (!["cut", "art", "pip"].includes(kind) || !payload.timeline) return null;
        project.timeline = replaceTimelineKind(
          project.timeline,
          kind,
          payload.timeline,
          timelineApi,
          { acceptIncomingSelection: ui.activeTool === kind },
        );
      } else if (action.type === ACTIONS.TIMELINE_CLIP_RANGE_CHANGED) {
        const rangeUpdate = updateTimelineClipRange(
          project.timeline,
          payload,
          timelineApi,
        );
        if (!rangeUpdate) return null;
        project.timeline = rangeUpdate.timeline;
        const kind = String(rangeUpdate.clip.kind || payload.kind || "");
        if (["art", "pip"].includes(kind)) {
          project[kind] = updateToolOverlayRange(
            project[kind],
            rangeUpdate.clip,
            rangeUpdate.clip.start,
            rangeUpdate.clip.end,
            payload.sourceStart,
            payload.sourceEnd,
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
      const cutDraftMetadataOnly =
        action.type === ACTIONS.CUT_TIMING_CHANGED &&
        stableSignature({
          ...comparable,
          project: {
            ...project,
            cut: {
              ...project.cut,
              cutDraftRevision: state.project.cut.cutDraftRevision,
            },
          },
        }) === stableSignature(state);
      const timingChanged =
        action.type !== ACTIONS.CUT_STRUCTURE_CHANGED &&
        action.type !== ACTIONS.TRANSCRIPT_TEXT_CHANGED &&
        ((action.type === ACTIONS.PROJECT_HYDRATED && jobId !== state.jobId) ||
          projectTimingSignature(project) !== projectTimingSignature(state.project));
      return owned({
        ...comparable,
        revision: state.revision + (cutDraftMetadataOnly ? 0 : 1),
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
        const performanceProbe = root.__cutPerformanceProbe;
        const dispatchStarted = performanceProbe ? performance.now() : 0;
        const previous = state;
        const next = reduceState(previous, action, timelineApi);
        if (!next) return result(false);
        const reducedAt = performanceProbe ? performance.now() : 0;
        state = next;
        const listenerDurations = [];
        for (const listener of listeners) {
          const listenerStarted = performanceProbe ? performance.now() : 0;
          listener(state, previous, action);
          if (performanceProbe) {
            listenerDurations.push(performance.now() - listenerStarted);
          }
        }
        if (performanceProbe) {
          performanceProbe.storeDispatchBreakdowns = [
            ...(Array.isArray(performanceProbe.storeDispatchBreakdowns)
              ? performanceProbe.storeDispatchBreakdowns
              : []),
            {
              action: String(action?.type || ""),
              reduce: reducedAt - dispatchStarted,
              listeners: listenerDurations,
              total: performance.now() - dispatchStarted,
            },
          ];
        }
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

    function selectTimelineDocument(state, timelineApi = root.EditorTimeline) {
      return normalizeTimeline(state.project.timeline, timelineApi);
    }

    function selectPreviewLayers(state) {
      return clone({
        revision: state.revision,
        timingRevision: state.timingRevision,
        art: state.project.art,
        pip: state.project.pip,
        selection: state.project.timeline.selection,
      });
    }

    const ART_COMPOSITION_FIELDS = [
      "text", "font", "fontSize", "color", "strokeColor", "strokeWidth",
      "shadow", "x", "y", "start", "end", "direction", "textAlign",
      "charsPerLine", "letterSpacing", "lineSpacing", "artStyle",
      "textColorMode", "secondaryColor", "animation", "characterLayout",
      "characterTimings", "trackId", "trackType", "sourceStart", "sourceEnd",
    ];
    const PIP_COMPOSITION_FIELDS = [
      "assetId", "imageId", "start", "end", "sourceStart", "sourceEnd",
      "x", "y", "width",
    ];

    function projectFields(value, fields) {
      const projected = {};
      for (const field of fields) {
        if (value?.[field] !== undefined) projected[field] = clone(value[field]);
      }
      return projected;
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
        ...(state.project.cut.cutDraftRevision > 0
          ? { cutDraftRevision: state.project.cut.cutDraftRevision }
          : {}),
        artOverlays: state.project.art.overlays.map((overlay) =>
          projectFields(overlay, ART_COMPOSITION_FIELDS)),
        artSource: state.project.art.source || "original",
        pictureInPictureOverlays: state.project.pip.overlays.map((overlay) =>
          projectFields(overlay, PIP_COMPOSITION_FIELDS)),
        pictureInPictureSource: state.project.pip.source || "original",
        historyName: null,
      });
    }

    function selectEditorFrame(state, timelineApi = root.EditorTimeline) {
      const composition = selectCompositionRequest(state);
      return clone({
        revision: state.revision,
        timingRevision: state.timingRevision,
        media: {
          jobId: state.jobId,
          sourceUrl: state.jobId && state.project.job?.status === "completed"
            ? `/api/transcriptions/${encodeURIComponent(state.jobId)}/original-video`
            : "",
          sourceDuration: state.project.cut.sourceDuration,
          cutRanges: composition.ranges,
        },
        preview: selectPreviewLayers(state),
        timeline: selectTimelineDocument(state, timelineApi),
        composition,
      });
    }

    return {
      SCHEMA_VERSION,
      ACTIONS,
      createStore,
      cutTimingSignature,
      toolTimingSignature,
      selectTimelineDocument,
      selectPreviewLayers,
      selectCompositionRequest,
      selectEditorFrame,
    };
  },
);
