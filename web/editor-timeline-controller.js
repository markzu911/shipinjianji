(function exposeTimelineController(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorTimelineController = api;
})(typeof globalThis === "object" ? globalThis : window, function timelineControllerFactory(root) {
  "use strict";

  const DEFAULT_STEP = 0.1;
  const DEFAULT_HISTORY_LIMIT = 100;
  const DRAG_THRESHOLD = 3;
  const TIMELINE_ROW_HEIGHT = 26;
  const TIMELINE_EFFECT_BASE_HEIGHT = 63;

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function finiteNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function editableTarget(target) {
    if (!target || typeof target.closest !== "function") return false;
    return Boolean(target.closest("input, textarea, select, [contenteditable]"));
  }

  function accepted(result) {
    return result !== false && result?.accepted !== false;
  }

  function createController(options = {}) {
    const timelineApi = options.timeline || root.EditorTimeline;
    if (!timelineApi?.normalizeDocument || !timelineApi?.createStore) {
      throw new Error("EditorTimeline is required.");
    }

    const layer = options.root || null;
    const track = options.track || layer?.parentElement || null;
    const keyboardTarget = options.keyboardTarget || root.document || null;
    const visibleKinds = Array.isArray(options.visibleKinds)
      ? new Set(options.visibleKinds.map((kind) => String(kind)))
      : null;
    const historyLimit = Math.max(
      1,
      Math.floor(finiteNumber(options.historyLimit, DEFAULT_HISTORY_LIMIT)),
    );
    let frame = {
      jobId: "",
      revision: 0,
      timingRevision: 0,
      timeline: timelineApi.normalizeDocument(),
    };
    let previewDocument = null;
    let history = [];
    let historyIndex = 0;
    let destroyed = false;
    let pointerCleanup = null;

    function currentDocument() {
      return clone(previewDocument || frame.timeline);
    }

    function findClip(clipId, documentState = currentDocument()) {
      for (const timelineTrack of documentState.tracks) {
        const clip = timelineTrack.clips.find((item) => item.id === String(clipId));
        if (clip) return { track: timelineTrack, clip };
      }
      return null;
    }

    function trackClass(kind) {
      if (kind === "pip") return "pip-timeline-segment";
      if (kind === "cut") return "cut-timeline-delete-range";
      return "frame-timeline-segment";
    }

    function renderDocument(documentState = currentDocument()) {
      if (!layer || destroyed) return documentState;
      const selectedClipId = String(documentState.selection?.clipId || "");
      const duration = Math.max(0, finiteNumber(documentState.duration));
      const fragments = [];
      let trackIndex = 0;
      let rowCount = 0;

      for (const timelineTrack of documentState.tracks) {
        if (visibleKinds && !visibleKinds.has(String(timelineTrack.kind))) continue;
        const laneEnds = [];
        for (const clip of timelineTrack.clips) {
          let laneIndex = 0;
          if (timelineTrack.kind === "art") {
            laneEnds[0] = Math.max(finiteNumber(laneEnds[0]), clip.end);
          } else {
            laneIndex = laneEnds.findIndex((laneEnd) => laneEnd <= clip.start);
            if (laneIndex < 0) {
              laneIndex = laneEnds.length;
              laneEnds.push(clip.end);
            } else {
              laneEnds[laneIndex] = clip.end;
            }
          }
          const segment = root.document.createElement("button");
          segment.type = "button";
          segment.className = trackClass(clip.kind);
          segment.dataset.timelineClipId = clip.id;
          segment.dataset.effectKind = clip.kind;
          segment.dataset.sourceId = clip.sourceId;
          if (clip.kind === "art") segment.dataset.overlayId = clip.sourceId;
          if (clip.kind === "pip") segment.dataset.pictureId = clip.sourceId;
          segment.dataset.effectStart = String(clip.start);
          segment.dataset.effectEnd = String(clip.end);
          segment.dataset.timelineTrackIndex = String(trackIndex);
          segment.dataset.timelineLaneIndex = String(laneIndex);
          segment.dataset.timelineEditable = String(Boolean(clip.editable));
          segment.style.top = `${(rowCount + laneIndex) * TIMELINE_ROW_HEIGHT + 2}px`;
          segment.style.left = `${duration > 0 ? (clip.start / duration) * 100 : 0}%`;
          segment.style.width = `${
            duration > 0 ? Math.max(0.25, ((clip.end - clip.start) / duration) * 100) : 0
          }%`;
          segment.style.zIndex = clip.id === selectedClipId ? "3" : "1";
          segment.classList.toggle("is-selected", clip.id === selectedClipId);
          segment.setAttribute("aria-pressed", String(clip.id === selectedClipId));
          segment.setAttribute(
            "aria-label",
            `${clip.name}, ${clip.start.toFixed(1)} - ${clip.end.toFixed(1)}`,
          );

          const label = root.document.createElement("span");
          label.className = "editor-layer-timeline-segment-label";
          label.textContent = clip.name;
          segment.append(label);
          if (clip.editable) {
            for (const mode of ["start", "end"]) {
              const handle = root.document.createElement("span");
              handle.dataset.timelineResize = mode;
              if (clip.kind === "art") {
                handle.dataset.artTimeDrag = mode;
                handle.className = `art-timeline-handle is-${mode}`;
              } else {
                handle.className = `timeline-resize-handle is-${mode}`;
              }
              handle.setAttribute("aria-hidden", "true");
              segment.append(handle);
            }
          }
          fragments.push(segment);
        }
        rowCount += laneEnds.length;
        trackIndex += 1;
      }

      layer.replaceChildren(...fragments);
      layer.hidden = fragments.length === 0;
      const layerHeight = rowCount * TIMELINE_ROW_HEIGHT;
      layer.style.height = fragments.length ? `${layerHeight}px` : "";
      layer.dataset.projectRevision = String(frame.revision);
      layer.dataset.timingRevision = String(frame.timingRevision);
      track?.classList?.toggle("has-effect-track", fragments.length > 0);
      if (track?.style) {
        if (fragments.length) {
          track.style.setProperty("--editor-layer-timeline-height", `${layerHeight}px`);
          track.style.setProperty(
            "--editor-timeline-track-height",
            `${TIMELINE_EFFECT_BASE_HEIGHT + rowCount * TIMELINE_ROW_HEIGHT}px`,
          );
        } else {
          track.style.removeProperty("--editor-layer-timeline-height");
          track.style.removeProperty("--editor-timeline-track-height");
        }
      }
      return documentState;
    }

    function render(nextFrame = {}) {
      if (destroyed) return currentDocument();
      const nextJobId = String(nextFrame.media?.jobId || nextFrame.jobId || "");
      const jobChanged = nextJobId !== frame.jobId;
      if (jobChanged) {
        pointerCleanup?.();
        previewDocument = null;
        history = [];
        historyIndex = 0;
      }
      const nextTimeline = timelineApi.normalizeDocument(
        nextFrame.timeline || nextFrame.project?.timeline || {},
      );
      frame = {
        jobId: nextJobId,
        revision: Math.max(0, finiteNumber(nextFrame.revision)),
        timingRevision: Math.max(0, finiteNumber(nextFrame.timingRevision)),
        timeline: nextTimeline,
      };
      if (!pointerCleanup) previewDocument = null;
      return renderDocument();
    }

    function selectionDocument(clipId, documentState = frame.timeline) {
      const found = findClip(clipId, documentState);
      return timelineApi.normalizeDocument({
        ...documentState,
        selection: found ? { clipId: found.clip.id } : null,
      });
    }

    function timelineSecondsFromClientX(clientX) {
      const duration = frame.timeline.duration;
      const rect = track?.getBoundingClientRect?.();
      const width = rect?.width;
      const left = rect?.left;
      if (
        !Number.isFinite(duration) ||
        duration <= 0 ||
        !Number.isFinite(width) ||
        width <= 0 ||
        !Number.isFinite(left) ||
        !Number.isFinite(clientX)
      ) {
        return null;
      }
      const progress = Math.min(
        1,
        Math.max(0, (clientX - left) / width),
      );
      return progress * duration;
    }

    function selectClip(clipId, settings = {}) {
      if (destroyed) return null;
      const found = findClip(clipId, frame.timeline);
      if (!found) return null;
      const result = options.onSelect?.({
        clip: clone(found.clip),
        track: clone(found.track),
        revision: frame.revision,
        source: settings.source || "timeline",
      });
      if (!accepted(result)) return null;
      previewDocument = selectionDocument(found.clip.id);
      renderDocument(previewDocument);
      const hasSeekTime = Object.prototype.hasOwnProperty.call(settings, "seekTime");
      const duration = Math.max(0, finiteNumber(frame.timeline.duration));
      const requestedSeekTime = hasSeekTime
        ? Math.max(0, finiteNumber(settings.seekTime, found.clip.start))
        : found.clip.start;
      const seekTime = duration > 0
        ? Math.min(duration, requestedSeekTime)
        : found.clip.start;
      options.onSeek?.(seekTime, clone(found.clip));
      return clone(found.clip);
    }

    function normalizedRange(clipId, start, end, baseDocument = frame.timeline) {
      const transientStore = timelineApi.createStore(baseDocument);
      const clip = transientStore.setClipRange(clipId, start, end, { silent: true });
      return clip
        ? { clip, document: transientStore.snapshot() }
        : null;
    }

    function recordHistory(before, after, reason) {
      if (historyIndex < history.length) history = history.slice(0, historyIndex);
      history.push({ before: clone(before), after: clone(after), reason });
      while (history.length > historyLimit) history.shift();
      historyIndex = history.length;
    }

    function submitRange(clipId, start, end, settings = {}) {
      if (destroyed) return null;
      const baseDocument = frame.timeline;
      const frameBeforeCommit = frame;
      const beforeFound = findClip(clipId, baseDocument);
      const normalized = normalizedRange(clipId, start, end, baseDocument);
      if (!beforeFound || !normalized) return null;
      const after = normalized.clip;
      const before = beforeFound.clip;
      if (before.start === after.start && before.end === after.end) {
        previewDocument = null;
        renderDocument(frame.timeline);
        return clone(after);
      }
      const reason = settings.reason || "timeline-range";
      const result = options.onCommit?.({
        clipId: after.id,
        sourceId: after.sourceId,
        kind: after.kind,
        start: after.start,
        end: after.end,
        before: clone(before),
        after: clone(after),
        reason,
        direction: settings.direction || "forward",
        revision: frame.revision,
      });
      if (!accepted(result)) {
        previewDocument = null;
        renderDocument(frame.timeline);
        return null;
      }
      if (settings.recordHistory !== false) recordHistory(before, after, reason);
      if (frame === frameBeforeCommit) {
        frame = { ...frame, timeline: normalized.document };
      }
      previewDocument = normalized.document;
      renderDocument(previewDocument);
      return clone(after);
    }

    function applyHistoryEntry(entry, direction) {
      const target = direction === "undo" ? entry.before : entry.after;
      return submitRange(target.id, target.start, target.end, {
        reason: entry.reason,
        direction,
        recordHistory: false,
      });
    }

    function undo() {
      if (historyIndex <= 0 || destroyed) return false;
      const entry = history[historyIndex - 1];
      if (!applyHistoryEntry(entry, "undo")) return false;
      historyIndex -= 1;
      return true;
    }

    function redo() {
      if (historyIndex >= history.length || destroyed) return false;
      const entry = history[historyIndex];
      if (!applyHistoryEntry(entry, "redo")) return false;
      historyIndex += 1;
      return true;
    }

    function pointerDown(event) {
      const segment = event.target.closest?.("[data-timeline-clip-id]");
      if (!segment || event.button !== 0) return;
      const clipId = segment.dataset.timelineClipId;
      const found = findClip(clipId, frame.timeline);
      if (!found) return;
      event.preventDefault();
      event.stopPropagation();
      const clickSeekTime = timelineSecondsFromClientX(event.clientX) ?? found.clip.start;
      if (!found.clip.editable) {
        selectClip(clipId, { source: "pointer", seekTime: clickSeekTime });
        return;
      }

      const documentBeforePointer = currentDocument();
      const mode = event.target.closest?.("[data-timeline-resize]")?.dataset
        .timelineResize || "move";
      const width = Math.max(1, finiteNumber(track?.getBoundingClientRect?.().width, 1));
      const transientStore = timelineApi.createStore(selectionDocument(clipId));
      const session = timelineApi.createPointerSession(transientStore, {
        clipId,
        mode,
        startClientX: event.clientX,
        trackWidth: width,
        duration: frame.timeline.duration,
      });
      if (!session) return;
      previewDocument = selectionDocument(clipId);
      renderDocument(previewDocument);

      let moved = false;
      const move = (moveEvent) => {
        if (!moved && Math.abs(moveEvent.clientX - event.clientX) < DRAG_THRESHOLD) {
          return;
        }
        moved = true;
        const clip = session.update(moveEvent.clientX);
        previewDocument = transientStore.snapshot();
        renderDocument(previewDocument);
        options.onPreview?.({ clip: clone(clip), mode });
        options.onSeek?.(mode === "end" ? clip.end : clip.start, clone(clip));
      };
      const finish = (finishEvent) => {
        cleanup();
        const clip = session.finish({ commit: false });
        if (finishEvent.type === "pointercancel") {
          previewDocument = null;
          renderDocument(frame.timeline);
          return;
        }
        if (!moved) {
          previewDocument = null;
          const selected = selectClip(clipId, {
            source: "pointer",
            seekTime: mode === "move" ? clickSeekTime : found.clip.start,
          });
          if (!selected) {
            previewDocument = documentBeforePointer;
            renderDocument(previewDocument);
          }
          return;
        }
        submitRange(clip.id, clip.start, clip.end, {
          reason: `pointer-${mode}`,
        });
      };
      const cleanup = () => {
        root.removeEventListener?.("pointermove", move);
        root.removeEventListener?.("pointerup", finish);
        root.removeEventListener?.("pointercancel", finish);
        pointerCleanup = null;
      };
      pointerCleanup?.();
      pointerCleanup = cleanup;
      root.addEventListener?.("pointermove", move);
      root.addEventListener?.("pointerup", finish, { once: true });
      root.addEventListener?.("pointercancel", finish, { once: true });
    }

    function keyDown(event) {
      if (editableTarget(event.target)) return;
      const commandKey = event.ctrlKey || event.metaKey;
      const key = String(event.key || "").toLowerCase();
      if (commandKey && key === "z") {
        const canApply = event.shiftKey ? historyIndex < history.length : historyIndex > 0;
        if (!canApply) return;
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
        return;
      }
      if (commandKey && key === "y") {
        if (historyIndex >= history.length) return;
        event.preventDefault();
        redo();
        return;
      }
      const segment = event.target.closest?.("[data-timeline-clip-id]");
      if (!segment) return;
      const clipId = segment.dataset.timelineClipId;
      const found = findClip(clipId, frame.timeline);
      if (!found) return;
      if (["Delete", "Backspace"].includes(event.key)) {
        event.preventDefault();
        options.onDelete?.({ clip: clone(found.clip), revision: frame.revision });
        return;
      }
      if (!["ArrowLeft", "ArrowRight"].includes(event.key) || !found.clip.editable) {
        return;
      }
      event.preventDefault();
      const direction = event.key === "ArrowLeft" ? -1 : 1;
      const delta = direction * (event.shiftKey ? 1 : DEFAULT_STEP);
      const mode = event.target.closest?.("[data-timeline-resize]")?.dataset
        .timelineResize || "move";
      const transientStore = timelineApi.createStore(frame.timeline);
      const next = transientStore.adjustClip(clipId, mode, delta, { silent: true });
      if (next) {
        submitRange(clipId, next.start, next.end, {
          reason: `keyboard-${mode}`,
        });
        options.onSeek?.(mode === "end" ? next.end : next.start, clone(next));
      }
    }

    layer?.addEventListener("pointerdown", pointerDown);
    if (keyboardTarget) {
      keyboardTarget.addEventListener?.("keydown", keyDown);
    } else {
      layer?.addEventListener("keydown", keyDown);
    }

    function destroy() {
      if (destroyed) return;
      destroyed = true;
      pointerCleanup?.();
      layer?.removeEventListener("pointerdown", pointerDown);
      if (keyboardTarget) {
        keyboardTarget.removeEventListener?.("keydown", keyDown);
      } else {
        layer?.removeEventListener("keydown", keyDown);
      }
      layer?.replaceChildren();
      history = [];
      historyIndex = 0;
      previewDocument = null;
    }

    return {
      render,
      currentDocument,
      selectClip,
      submitRange,
      undo,
      redo,
      canUndo: () => historyIndex > 0,
      canRedo: () => historyIndex < history.length,
      historySnapshot: () => ({
        index: historyIndex,
        entries: clone(history),
      }),
      destroy,
    };
  }

  return { createController };
});
