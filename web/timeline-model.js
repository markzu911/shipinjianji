(function exposeTimelineModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorTimeline = api;
})(typeof globalThis === "object" ? globalThis : window, function timelineModelFactory() {
  "use strict";

  const SCHEMA_VERSION = 1;
  const DEFAULT_MIN_DURATION = 0.1;
  const KIND_ORDER = { cut: 0, art: 1, pip: 2 };

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function finiteNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function normalizeClip(rawClip, track, duration) {
    const id = String(rawClip?.id || "").trim();
    if (!id) return null;
    const minDuration = Math.max(
      0.001,
      finiteNumber(rawClip.minDuration, DEFAULT_MIN_DURATION),
    );
    const maximum = duration > 0 ? duration : Number.POSITIVE_INFINITY;
    let start = clamp(finiteNumber(rawClip.start), 0, maximum);
    let end = clamp(
      finiteNumber(rawClip.end, start + minDuration),
      0,
      maximum,
    );
    if (end - start < minDuration) {
      end = Math.min(maximum, start + minDuration);
      if (end - start < minDuration) start = Math.max(0, end - minDuration);
    }
    return {
      id,
      trackId: track.id,
      kind: track.kind,
      sourceId: String(rawClip.sourceId ?? id),
      name: String(rawClip.name || "片段"),
      start,
      end,
      minDuration,
      editable: rawClip.editable !== false && !rawClip.locked,
      locked: Boolean(rawClip.locked),
      payload:
        rawClip.payload && typeof rawClip.payload === "object"
          ? clone(rawClip.payload)
          : {},
    };
  }

  function normalizeTrack(rawTrack, index, duration) {
    const kind = String(rawTrack?.kind || "custom");
    const id = String(rawTrack?.id || `${kind}:${index + 1}`);
    const track = {
      id,
      kind,
      name: String(rawTrack?.name || `轨道 ${index + 1}`),
      order: finiteNumber(rawTrack?.order, KIND_ORDER[kind] ?? index),
      locked: Boolean(rawTrack?.locked),
      clips: [],
    };
    track.clips = (Array.isArray(rawTrack?.clips) ? rawTrack.clips : [])
      .map((clip) => normalizeClip(clip, track, duration))
      .filter(Boolean)
      .sort((left, right) => left.start - right.start || left.end - right.end);
    return track;
  }

  function normalizeDocument(input = {}) {
    const duration = Math.max(0, finiteNumber(input.duration));
    const tracks = (Array.isArray(input.tracks) ? input.tracks : [])
      .map((track, index) => normalizeTrack(track, index, duration))
      .sort((left, right) => left.order - right.order);
    const selectedClipId = String(input.selection?.clipId || "");
    const selectedTrack = tracks.find((track) =>
      track.clips.some((clip) => clip.id === selectedClipId),
    );
    return {
      schemaVersion: SCHEMA_VERSION,
      duration,
      tracks,
      selection: selectedTrack
        ? { trackId: selectedTrack.id, clipId: selectedClipId }
        : null,
    };
  }

  function createStore(initial = {}, options = {}) {
    let documentState = normalizeDocument(initial);
    const listeners = new Set();

    function snapshot() {
      return clone(documentState);
    }

    function notify(reason) {
      const value = snapshot();
      for (const listener of listeners) listener(value, reason);
      options.onChange?.(value, reason);
      return value;
    }

    function findClip(clipId) {
      for (const track of documentState.tracks) {
        const clip = track.clips.find((item) => item.id === String(clipId));
        if (clip) return { track, clip };
      }
      return null;
    }

    function replace(nextDocument, settings = {}) {
      documentState = normalizeDocument(nextDocument);
      return settings.silent ? snapshot() : notify("replace");
    }

    function replaceKind(kind, tracks, settings = {}) {
      const preserved = documentState.tracks.filter(
        (track) => track.kind !== String(kind),
      );
      const selection = settings.selection === undefined
        ? documentState.selection
        : settings.selection
          ? { clipId: String(settings.selection) }
          : null;
      return replace(
        {
          ...documentState,
          tracks: [
            ...preserved,
            ...(Array.isArray(tracks) ? tracks : []).map((track) => ({
              ...track,
              kind: String(kind),
            })),
          ],
          selection,
        },
        settings,
      );
    }

    function setDuration(duration, settings = {}) {
      return replace(
        { ...documentState, duration: Math.max(0, finiteNumber(duration)) },
        settings,
      );
    }

    function selectClip(clipId, settings = {}) {
      const found = findClip(clipId);
      documentState.selection = found
        ? { trackId: found.track.id, clipId: found.clip.id }
        : null;
      const value = settings.silent ? snapshot() : notify("select");
      if (settings.commit) commit("select");
      return found ? clone(found.clip) : null;
    }

    function setClipRange(clipId, start, end, settings = {}) {
      const found = findClip(clipId);
      if (!found || !found.clip.editable) return null;
      const normalized = normalizeClip(
        { ...found.clip, start, end },
        found.track,
        documentState.duration,
      );
      Object.assign(found.clip, normalized);
      documentState.selection = {
        trackId: found.track.id,
        clipId: found.clip.id,
      };
      if (!settings.silent) notify(settings.reason || "set-range");
      if (settings.commit) commit(settings.reason || "set-range");
      return clone(found.clip);
    }

    function adjustClip(clipId, mode, delta, settings = {}) {
      const found = findClip(clipId);
      if (!found || !found.clip.editable) return null;
      const original = found.clip;
      let start = original.start;
      let end = original.end;
      const change = finiteNumber(delta);
      if (mode === "start") {
        start = clamp(
          original.start + change,
          0,
          original.end - original.minDuration,
        );
      } else if (mode === "end") {
        end = clamp(
          original.end + change,
          original.start + original.minDuration,
          documentState.duration || Number.POSITIVE_INFINITY,
        );
      } else {
        const clipDuration = original.end - original.start;
        const maximumStart = Math.max(0, documentState.duration - clipDuration);
        start = clamp(original.start + change, 0, maximumStart);
        end = start + clipDuration;
      }
      return setClipRange(clipId, start, end, settings);
    }

    function patchClipPayload(clipId, patch, settings = {}) {
      const found = findClip(clipId);
      if (!found || !patch || typeof patch !== "object") return null;
      found.clip.payload = { ...found.clip.payload, ...clone(patch) };
      documentState.selection = {
        trackId: found.track.id,
        clipId: found.clip.id,
      };
      if (!settings.silent) notify(settings.reason || "patch-payload");
      if (settings.commit) commit(settings.reason || "patch-payload");
      return clone(found.clip);
    }

    function commit(reason = "save") {
      const value = snapshot();
      options.onCommit?.(value, reason);
      return value;
    }

    function subscribe(listener) {
      if (typeof listener !== "function") return () => {};
      listeners.add(listener);
      return () => listeners.delete(listener);
    }

    return {
      snapshot,
      replace,
      replaceKind,
      setDuration,
      findClip: (clipId) => {
        const found = findClip(clipId);
        return found ? clone(found.clip) : null;
      },
      selectClip,
      setClipRange,
      adjustClip,
      patchClipPayload,
      commit,
      subscribe,
    };
  }

  function createPointerSession(store, options) {
    const clip = store?.findClip(options?.clipId);
    if (!clip || !clip.editable) return null;
    const mode = ["start", "end", "move"].includes(options.mode)
      ? options.mode
      : "move";
    const startClientX = finiteNumber(options.startClientX);
    const trackWidth = Math.max(1, finiteNumber(options.trackWidth, 1));
    const duration = Math.max(
      0,
      finiteNumber(options.duration, store.snapshot().duration),
    );
    const original = { start: clip.start, end: clip.end };
    let latest = clone(clip);

    function update(clientX) {
      const delta = ((finiteNumber(clientX) - startClientX) / trackWidth) * duration;
      let start = original.start;
      let end = original.end;
      if (mode === "start") {
        start = clamp(
          original.start + delta,
          0,
          original.end - clip.minDuration,
        );
      } else if (mode === "end") {
        end = clamp(
          original.end + delta,
          original.start + clip.minDuration,
          duration || Number.POSITIVE_INFINITY,
        );
      } else {
        const clipDuration = original.end - original.start;
        const maximumStart = Math.max(0, duration - clipDuration);
        start = clamp(original.start + delta, 0, maximumStart);
        end = start + clipDuration;
      }
      latest = store.setClipRange(clip.id, start, end, {
        reason: `pointer-${mode}`,
      }) || latest;
      options.onUpdate?.(clone(latest));
      return clone(latest);
    }

    function finish(settings = {}) {
      if (settings.commit !== false) store.commit(`pointer-${mode}`);
      options.onFinish?.(clone(latest));
      return clone(latest);
    }

    return { original: clone(clip), update, finish };
  }

  function saveDraft(storage, key, timeline, metadata = {}) {
    if (!storage || !key) return false;
    try {
      storage.setItem(
        key,
        JSON.stringify({
          schemaVersion: SCHEMA_VERSION,
          savedAt: new Date().toISOString(),
          timeline: normalizeDocument(timeline),
          metadata: clone(metadata),
        }),
      );
      return true;
    } catch {
      return false;
    }
  }

  function loadDraft(storage, key) {
    if (!storage || !key) return null;
    try {
      const saved = JSON.parse(storage.getItem(key) || "null");
      if (!saved || typeof saved !== "object") return null;
      if (saved.timeline) {
        return {
          schemaVersion: finiteNumber(saved.schemaVersion, SCHEMA_VERSION),
          savedAt: String(saved.savedAt || ""),
          timeline: normalizeDocument(saved.timeline),
          metadata:
            saved.metadata && typeof saved.metadata === "object"
              ? saved.metadata
              : {},
          legacy: false,
        };
      }
      return {
        schemaVersion: 0,
        savedAt: "",
        timeline: null,
        metadata: saved,
        legacy: true,
      };
    } catch {
      return null;
    }
  }

  return {
    SCHEMA_VERSION,
    normalizeDocument,
    createStore,
    createPointerSession,
    saveDraft,
    loadDraft,
  };
});
