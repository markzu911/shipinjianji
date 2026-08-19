(function exposeEditorMedia(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorMedia = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function editorMediaFactory(root) {
    "use strict";

    function finiteNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function clamp(value, minimum, maximum) {
      return Math.min(maximum, Math.max(minimum, value));
    }

    function normalizeRanges(ranges) {
      const sorted = (Array.isArray(ranges) ? ranges : [])
        .map((range) => {
          const start = Math.max(0, finiteNumber(range?.start));
          const end = Math.max(start, finiteNumber(range?.end, start));
          return end > start ? { start, end } : null;
        })
        .filter(Boolean)
        .sort((left, right) => left.start - right.start || left.end - right.end);
      const merged = [];
      for (const range of sorted) {
        const previous = merged.at(-1);
        if (previous && range.start <= previous.end + 0.0001) {
          previous.end = Math.max(previous.end, range.end);
        } else {
          merged.push({ ...range });
        }
      }
      return merged;
    }

    function createPlaybackFrameClock(video, onFrame, options = {}) {
      const requestFrame = options.requestAnimationFrame ||
        root.requestAnimationFrame?.bind(root);
      const cancelFrame = options.cancelAnimationFrame ||
        root.cancelAnimationFrame?.bind(root);
      const hasVideoFrameCallback =
        typeof video.requestVideoFrameCallback === "function";
      const mode = hasVideoFrameCallback
        ? "video-frame"
        : typeof requestFrame === "function"
          ? "animation-frame"
          : "timeupdate";
      let callbackId = null;
      let callbackGeneration = 0;
      let destroyed = false;

      function emitFrame(metadata = {}) {
        const mediaTime = Number(metadata.mediaTime);
        onFrame(
          Number.isFinite(mediaTime) ? mediaTime : Number(video.currentTime) || 0,
          metadata,
        );
      }

      function schedule() {
        if (
          destroyed ||
          callbackId !== null ||
          video.paused ||
          video.ended
        ) {
          return false;
        }
        const scheduledGeneration = callbackGeneration;
        const handleFrame = (timestamp, metadata) => {
          handleScheduledFrame(scheduledGeneration, timestamp, metadata);
        };
        if (mode === "video-frame") {
          callbackId = video.requestVideoFrameCallback(handleFrame);
        } else if (mode === "animation-frame") {
          callbackId = requestFrame(handleFrame);
        }
        return callbackId !== null;
      }

      function handleScheduledFrame(generation, _timestamp, metadata = {}) {
        if (generation !== callbackGeneration) return;
        callbackId = null;
        if (destroyed || video.paused || video.ended) return;
        emitFrame(metadata);
        if (generation !== callbackGeneration) return;
        schedule();
      }

      function stop({ reset = false } = {}) {
        callbackGeneration += 1;
        const pendingCallbackId = callbackId;
        callbackId = null;
        if (pendingCallbackId !== null) {
          if (mode === "video-frame") {
            video.cancelVideoFrameCallback?.(pendingCallbackId);
          } else if (mode === "animation-frame") {
            cancelFrame?.(pendingCallbackId);
          }
        }
        if (reset) options.onReset?.();
      }

      function sync({ reset = false, reason = "sync" } = {}) {
        if (destroyed) return;
        if (reset) options.onReset?.();
        emitFrame({ mediaTime: Number(video.currentTime) || 0, reason });
      }

      function handlePlay() {
        schedule();
      }

      function handlePause() {
        stop();
      }

      function handleEnded() {
        stop({ reset: true });
      }

      function handleEmptied() {
        stop({ reset: true });
      }

      function handleSeeking() {
        stop({ reset: true });
      }

      function handleSeeked() {
        sync({ reset: true, reason: "seeked" });
        schedule();
      }

      function handleTimeupdateFallback() {
        if (mode === "timeupdate" && !video.paused && !video.ended) emitFrame();
      }

      video.addEventListener("play", handlePlay);
      video.addEventListener("pause", handlePause);
      video.addEventListener("ended", handleEnded);
      video.addEventListener("emptied", handleEmptied);
      video.addEventListener("seeking", handleSeeking);
      video.addEventListener("seeked", handleSeeked);
      if (mode === "timeupdate") {
        video.addEventListener("timeupdate", handleTimeupdateFallback);
      }

      function destroy() {
        if (destroyed) return;
        stop({ reset: true });
        destroyed = true;
        video.removeEventListener("play", handlePlay);
        video.removeEventListener("pause", handlePause);
        video.removeEventListener("ended", handleEnded);
        video.removeEventListener("emptied", handleEmptied);
        video.removeEventListener("seeking", handleSeeking);
        video.removeEventListener("seeked", handleSeeked);
        video.removeEventListener("timeupdate", handleTimeupdateFallback);
      }

      return { destroy, mode, schedule, stop, sync };
    }

    function createController(video, options = {}) {
      if (!video) throw new Error("EditorMedia requires a video element.");
      let sourceKey = "";
      let cutRanges = [];
      let cutRangeSignature = "";
      let configuredSourceDuration = 0;
      let sourceLoadPending = false;
      let sourceLoadStarted = false;
      let sourceLoadFailed = false;
      let destroyed = false;
      const frameListeners = new Set();
      const stateListeners = new Set();

      function sourceDuration() {
        const mediaDuration = Number(video.duration);
        return Number.isFinite(mediaDuration) && mediaDuration > 0
          ? mediaDuration
          : configuredSourceDuration;
      }

      function editedDuration() {
        const removed = cutRanges.reduce(
          (total, range) => total + range.end - range.start,
          0,
        );
        return Math.max(0, sourceDuration() - removed);
      }

      function sourceToEdited(seconds) {
        const sourceTime = clamp(
          finiteNumber(seconds),
          0,
          sourceDuration() || Number.POSITIVE_INFINITY,
        );
        let removedBefore = 0;
        for (const range of cutRanges) {
          if (sourceTime >= range.end) {
            removedBefore += range.end - range.start;
            continue;
          }
          if (sourceTime > range.start) return Math.max(0, range.start - removedBefore);
          break;
        }
        return Math.max(0, sourceTime - removedBefore);
      }

      function editedToSource(seconds, edge = "start") {
        const editedTime = clamp(
          finiteNumber(seconds),
          0,
          editedDuration() || Number.POSITIVE_INFINITY,
        );
        let sourceTime = editedTime;
        let removedBefore = 0;
        for (const range of cutRanges) {
          const editedRangeStart = Math.max(0, range.start - removedBefore);
          const crossesRange = edge === "end"
            ? editedTime > editedRangeStart + 0.0001
            : editedTime >= editedRangeStart - 0.0001;
          if (!crossesRange) break;
          sourceTime += range.end - range.start;
          removedBefore += range.end - range.start;
        }
        return clamp(
          sourceTime,
          0,
          sourceDuration() || Number.POSITIVE_INFINITY,
        );
      }

      function frameState(sourceTime = Number(video.currentTime) || 0, metadata = {}) {
        return Object.freeze({
          sourceTime,
          editedTime: sourceToEdited(sourceTime),
          sourceDuration: sourceDuration(),
          editedDuration: editedDuration(),
          playing: !video.paused && !video.ended,
          sourceKey,
          metadata,
        });
      }

      function emitFrame(sourceTime, metadata = {}) {
        if (destroyed) return;
        const value = frameState(sourceTime, metadata);
        for (const listener of frameListeners) listener(value);
      }

      function emitState(reason) {
        if (destroyed) return;
        const value = Object.freeze({ ...frameState(), reason });
        for (const listener of stateListeners) listener(value);
      }

      const clock = createPlaybackFrameClock(video, emitFrame, {
        ...options,
        onReset: options.onReset,
      });

      const stateEvents = [
        "loadstart", "loadedmetadata", "durationchange", "play", "pause", "ended",
        "seeking", "seeked", "emptied", "error", "volumechange",
      ];
      const stateHandlers = new Map(
        stateEvents.map((eventName) => {
          const handler = () => {
            if (eventName === "loadstart") {
              sourceLoadStarted = true;
            } else if (eventName === "loadedmetadata") {
              sourceLoadPending = false;
              sourceLoadStarted = false;
              sourceLoadFailed = false;
            } else if (eventName === "error") {
              sourceLoadPending = false;
              sourceLoadStarted = false;
              sourceLoadFailed = true;
            }
            emitState(eventName);
          };
          video.addEventListener(eventName, handler);
          return [eventName, handler];
        }),
      );

      function normalizedSource(value) {
        const source = String(value || "").trim();
        if (!source) return "";
        try {
          return new URL(source, root.location?.href || "http://editor.local/").href;
        } catch {
          return source;
        }
      }

      function currentSourceNeedsRecovery() {
        const networkNoSource = Number(video.NETWORK_NO_SOURCE ?? 3);
        if (
          sourceLoadFailed ||
          Boolean(video.error)
        ) {
          return true;
        }
        if (
          Number(video.networkState) === networkNoSource &&
          (!sourceLoadPending || sourceLoadStarted)
        ) {
          return true;
        }
        if (sourceLoadPending) return false;
        const hasAttachedSource = Boolean(
          String(video.currentSrc || "").trim() ||
          String(video.getAttribute?.("src") || "").trim(),
        );
        return Number(video.readyState) === 0 && !hasAttachedSource;
      }

      function setSource(url, settings = {}) {
        if (destroyed) return false;
        const nextKey = String(settings.key || normalizedSource(url));
        if (
          !settings.force &&
          nextKey &&
          nextKey === sourceKey &&
          !currentSourceNeedsRecovery()
        ) {
          return false;
        }
        if (!url) return clearSource(settings);
        sourceKey = nextKey;
        sourceLoadPending = true;
        sourceLoadStarted = false;
        sourceLoadFailed = false;
        configuredSourceDuration = Math.max(
          0,
          finiteNumber(settings.sourceDuration, configuredSourceDuration),
        );
        video.src = String(url);
        video.load?.();
        emitState(settings.reason || "source");
        return true;
      }

      function clearSource(settings = {}) {
        if (destroyed) return false;
        const hasSource = Boolean(
          sourceKey || video.currentSrc || video.getAttribute?.("src"),
        );
        if (!hasSource && !settings.force) return false;
        video.pause?.();
        sourceKey = "";
        sourceLoadPending = false;
        sourceLoadStarted = false;
        sourceLoadFailed = false;
        configuredSourceDuration = 0;
        video.removeAttribute?.("src");
        video.load?.();
        emitState(settings.reason || "clear-source");
        return true;
      }

      function setCutRanges(ranges, settings = {}) {
        const nextRanges = normalizeRanges(ranges);
        const nextSignature = JSON.stringify(nextRanges);
        const previousDuration = configuredSourceDuration;
        if (Number.isFinite(Number(settings.sourceDuration))) {
          configuredSourceDuration = Math.max(0, Number(settings.sourceDuration));
        }
        if (
          nextSignature === cutRangeSignature &&
          previousDuration === configuredSourceDuration
        ) {
          return cutRanges.map((range) => ({ ...range }));
        }
        cutRanges = nextRanges;
        cutRangeSignature = nextSignature;
        emitState(settings.reason || "cut-ranges");
        return cutRanges.map((range) => ({ ...range }));
      }

      function seekSource(seconds, settings = {}) {
        if (destroyed) return 0;
        const nextTime = clamp(
          finiteNumber(seconds),
          0,
          sourceDuration() || Number.POSITIVE_INFINITY,
        );
        video.currentTime = nextTime;
        if (settings.sync !== false) clock.sync({ reset: true, reason: "seek" });
        return nextTime;
      }

      function seekEdited(seconds, settings = {}) {
        return seekSource(editedToSource(seconds), settings);
      }

      function play() {
        return video.play?.();
      }

      function pause() {
        video.pause?.();
      }

      function toggle() {
        return video.paused || video.ended ? play() : pause();
      }

      function setVolume(value) {
        const nextVolume = clamp(finiteNumber(value, 1), 0, 1);
        video.volume = nextVolume;
        emitState("volume");
        return nextVolume;
      }

      function setMuted(value) {
        video.muted = Boolean(value);
        emitState("muted");
        return video.muted;
      }

      function subscribeFrame(listener) {
        if (destroyed || typeof listener !== "function") return () => {};
        frameListeners.add(listener);
        return () => frameListeners.delete(listener);
      }

      function subscribeState(listener) {
        if (destroyed || typeof listener !== "function") return () => {};
        stateListeners.add(listener);
        return () => stateListeners.delete(listener);
      }

      function applyFrame(frame) {
        if (!frame?.media) return false;
        video.dataset.projectRevision = String(frame.revision ?? "");
        video.dataset.timingRevision = String(frame.timingRevision ?? "");
        setCutRanges(frame.media.cutRanges, {
          sourceDuration: frame.media.sourceDuration,
          reason: "project-frame",
        });
        if (frame.media.sourceUrl) {
          return setSource(frame.media.sourceUrl, {
            key: `${frame.media.jobId || ""}:${frame.media.sourceUrl}`,
            sourceDuration: frame.media.sourceDuration,
            reason: "project-frame",
          });
        }
        return false;
      }

      function destroy() {
        if (destroyed) return;
        clock.destroy();
        for (const [eventName, handler] of stateHandlers) {
          video.removeEventListener(eventName, handler);
        }
        frameListeners.clear();
        stateListeners.clear();
        destroyed = true;
      }

      return Object.freeze({
        applyFrame,
        clearSource,
        currentEditedTime: () => sourceToEdited(Number(video.currentTime) || 0),
        currentSourceTime: () => Number(video.currentTime) || 0,
        destroy,
        editedDuration,
        editedToSource,
        frameMode: clock.mode,
        pause,
        play,
        seekEdited,
        seekSource,
        setCutRanges,
        setMuted,
        setSource,
        setVolume,
        sourceDuration,
        sourceToEdited,
        subscribeFrame,
        subscribeState,
        toggle,
        video: () => video,
      });
    }

    return { createController, createPlaybackFrameClock, normalizeRanges };
  },
);
