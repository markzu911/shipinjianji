from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def run_media_script(body: str) -> dict[str, object]:
    script = f"""
const media = require('./web/editor-media-controller.js');
{body}
"""
    try:
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the editor media controller tests.")
    return json.loads(completed.stdout)


def test_media_controller_keeps_source_stable_and_maps_cut_time() -> None:
    result = run_media_script(
        r"""
function createVideo() {
  const listeners = new Map();
  let source = '';
  return {
    duration: 10,
    currentTime: 0,
    paused: true,
    ended: false,
    volume: 1,
    muted: false,
    dataset: {},
    loadCount: 0,
    srcWriteCount: 0,
    get src() { return source; },
    set src(value) { source = String(value); this.srcWriteCount += 1; },
    get currentSrc() { return source; },
    getAttribute(name) { return name === 'src' ? source || null : null; },
    removeAttribute(name) { if (name === 'src') source = ''; },
    load() { this.loadCount += 1; },
    play() { this.paused = false; this.dispatch('play'); return Promise.resolve(); },
    pause() { this.paused = true; this.dispatch('pause'); },
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(callback);
    },
    removeEventListener(type, callback) { listeners.get(type)?.delete(callback); },
    dispatch(type) { for (const callback of [...(listeners.get(type) || [])]) callback(); },
    listenerCount() {
      return [...listeners.values()].reduce((total, values) => total + values.size, 0);
    },
  };
}
const video = createVideo();
const controller = media.createController(video);
let stateEvents = 0;
controller.subscribeState(() => { stateEvents += 1; });
const frame = {
  revision: 4,
  timingRevision: 2,
  media: {
    jobId: 'job-one', sourceUrl: '/video-one', sourceDuration: 10,
    cutRanges: [{ start: 2, end: 3 }, { start: 5, end: 6 }],
  },
};
const firstLoad = controller.applyFrame(frame);
const repeatedLoad = controller.applyFrame({ ...frame, revision: 5 });
const mappings = {
  sourceOne: controller.sourceToEdited(1),
  sourceInsideCut: controller.sourceToEdited(2.5),
  sourceFour: controller.sourceToEdited(4),
  sourceSeven: controller.sourceToEdited(7),
  editedBoundary: controller.editedToSource(2),
  editedBoundaryEnd: controller.editedToSource(2, 'end'),
  editedThree: controller.editedToSource(3),
};
controller.seekEdited(3, { sync: false });
controller.setVolume(0.35);
controller.setMuted(true);
const beforeClear = {
  currentTime: video.currentTime,
  loadCount: video.loadCount,
  srcWriteCount: video.srcWriteCount,
  source: video.src,
  volume: video.volume,
  muted: video.muted,
  projectRevision: video.dataset.projectRevision,
};
controller.clearSource();
controller.destroy();
console.log(JSON.stringify({
  firstLoad, repeatedLoad, mappings, beforeClear,
  finalLoadCount: video.loadCount,
  finalSource: video.src,
  listenersAfterDestroy: video.listenerCount(),
  stateEvents,
}));
"""
    )

    assert result["firstLoad"] is True
    assert result["repeatedLoad"] is False
    assert result["beforeClear"]["loadCount"] == 1
    assert result["beforeClear"]["srcWriteCount"] == 1
    assert result["beforeClear"]["source"] == "/video-one"
    assert result["beforeClear"]["currentTime"] == 4
    assert result["beforeClear"]["volume"] == 0.35
    assert result["beforeClear"]["muted"] is True
    assert result["beforeClear"]["projectRevision"] == "5"
    assert result["mappings"] == {
        "sourceOne": 1,
        "sourceInsideCut": 2,
        "sourceFour": 3,
        "sourceSeven": 5,
        "editedBoundary": 3,
        "editedBoundaryEnd": 2,
        "editedThree": 4,
    }
    assert result["finalLoadCount"] == 2
    assert result["finalSource"] == ""
    assert result["listenersAfterDestroy"] == 0
    assert result["stateEvents"] >= 4


def test_media_controller_retries_failed_same_key_without_reloading_healthy_media() -> None:
    result = run_media_script(
        r"""
function createVideo() {
  const listeners = new Map();
  let source = '';
  return {
    NETWORK_NO_SOURCE: 3,
    duration: 10,
    currentTime: 0,
    paused: true,
    ended: false,
    readyState: 0,
    networkState: 2,
    error: null,
    dataset: {},
    loadCount: 0,
    srcWriteCount: 0,
    get src() { return source; },
    set src(value) { source = String(value); this.srcWriteCount += 1; },
    get currentSrc() { return source; },
    getAttribute(name) { return name === 'src' ? source || null : null; },
    removeAttribute(name) { if (name === 'src') source = ''; },
    load() { this.loadCount += 1; },
    play() { this.paused = false; return Promise.resolve(); },
    pause() { this.paused = true; },
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(callback);
    },
    removeEventListener(type, callback) { listeners.get(type)?.delete(callback); },
    dispatch(type) { for (const callback of [...(listeners.get(type) || [])]) callback(); },
  };
}
const video = createVideo();
const controller = media.createController(video);
const settings = { key: 'job-one:/video-one', sourceDuration: 10 };
const firstLoad = controller.setSource('/video-one', settings);
const loadingRepeat = controller.setSource('/video-one', settings);
video.dispatch('loadstart');
video.networkState = video.NETWORK_NO_SOURCE;
const failedBeforeErrorEventRetry = controller.setSource('/video-one', settings);
video.error = { code: 4 };
video.networkState = video.NETWORK_NO_SOURCE;
video.dispatch('error');
video.error = null;
video.networkState = 1;
const failedAfterErrorEventRetry = controller.setSource('/video-one', settings);
video.error = null;
video.networkState = 1;
video.readyState = 4;
video.dispatch('loadedmetadata');
video.currentTime = 4;
video.paused = false;
const healthyRepeat = controller.setSource('/video-one', settings);
console.log(JSON.stringify({
  firstLoad,
  loadingRepeat,
  failedBeforeErrorEventRetry,
  failedAfterErrorEventRetry,
  healthyRepeat,
  loadCount: video.loadCount,
  srcWriteCount: video.srcWriteCount,
  currentTime: video.currentTime,
  paused: video.paused,
}));
"""
    )

    assert result == {
        "firstLoad": True,
        "loadingRepeat": False,
        "failedBeforeErrorEventRetry": True,
        "failedAfterErrorEventRetry": True,
        "healthyRepeat": False,
        "loadCount": 3,
        "srcWriteCount": 3,
        "currentTime": 4,
        "paused": False,
    }


def test_media_frame_clock_has_one_cancellable_generation_guarded_callback() -> None:
    result = run_media_script(
        r"""
function createVideo(withVideoFrames = false) {
  const listeners = new Map();
  const callbacks = new Map();
  const cancelled = [];
  let nextId = 1;
  const video = {
    callbacks, cancelled, currentTime: 0, ended: false, paused: true,
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(callback);
    },
    removeEventListener(type, callback) { listeners.get(type)?.delete(callback); },
    dispatch(type) { for (const callback of [...(listeners.get(type) || [])]) callback(); },
    listenerCount() {
      return [...listeners.values()].reduce((total, values) => total + values.size, 0);
    },
  };
  if (withVideoFrames) {
    video.requestVideoFrameCallback = callback => {
      const id = nextId++;
      callbacks.set(id, callback);
      return id;
    };
    video.cancelVideoFrameCallback = id => {
      cancelled.push(id);
      callbacks.delete(id);
    };
  }
  return video;
}

const video = createVideo(true);
const frames = [];
let resets = 0;
const clock = media.createPlaybackFrameClock(
  video,
  time => frames.push(time),
  { onReset: () => { resets += 1; } },
);
video.paused = false;
video.dispatch('play');
video.dispatch('play');
const uniqueAfterDuplicatePlay = video.callbacks.size === 1;
const first = video.callbacks.entries().next().value;
video.callbacks.delete(first[0]);
first[1](0, { mediaTime: 1.25 });
const stale = video.callbacks.values().next().value;
video.dispatch('seeking');
video.currentTime = 4;
video.dispatch('seeked');
const current = video.callbacks.values().next().value;
stale(0, { mediaTime: 2.5 });
const staleIgnored =
  frames.length === 2 && frames[0] === 1.25 && frames[1] === 4 &&
  video.callbacks.size === 1 && video.callbacks.values().next().value === current;
clock.destroy();

const fallback = createVideo(false);
const fallbackFrames = [];
const fallbackClock = media.createPlaybackFrameClock(
  fallback,
  time => fallbackFrames.push(time),
);
fallback.currentTime = 3;
fallback.paused = false;
fallback.dispatch('timeupdate');
fallback.paused = true;
fallback.dispatch('timeupdate');
fallbackClock.destroy();

const rafCallbacks = new Map();
const rafCancelled = [];
let rafId = 0;
const rafVideo = createVideo(false);
const rafFrames = [];
const rafClock = media.createPlaybackFrameClock(
  rafVideo,
  time => rafFrames.push(time),
  {
    requestAnimationFrame(callback) {
      const id = rafId++;
      rafCallbacks.set(id, callback);
      return id;
    },
    cancelAnimationFrame(id) {
      rafCancelled.push(id);
      rafCallbacks.delete(id);
    },
  },
);
rafVideo.currentTime = 2;
rafVideo.paused = false;
rafVideo.dispatch('play');
rafVideo.dispatch('play');
const rafAcceptsZeroId = rafCallbacks.size === 1 && rafCallbacks.has(0);
const firstRaf = rafCallbacks.get(0);
rafCallbacks.delete(0);
firstRaf(16);
rafVideo.paused = true;
rafVideo.dispatch('pause');
rafClock.destroy();

console.log(JSON.stringify({
  mode: clock.mode,
  uniqueAfterDuplicatePlay,
  staleIgnored,
  frames,
  resets,
  listenersAfterDestroy: video.listenerCount(),
  fallbackMode: fallbackClock.mode,
  fallbackFrames,
  rafMode: rafClock.mode,
  rafAcceptsZeroId,
  rafFrames,
  rafCancelled,
}));
"""
    )

    assert result["mode"] == "video-frame"
    assert result["uniqueAfterDuplicatePlay"] is True
    assert result["staleIgnored"] is True
    assert result["frames"] == [1.25, 4]
    assert result["resets"] == 3
    assert result["listenersAfterDestroy"] == 0
    assert result["fallbackMode"] == "timeupdate"
    assert result["fallbackFrames"] == [3]
    assert result["rafMode"] == "animation-frame"
    assert result["rafAcceptsZeroId"] is True
    assert result["rafFrames"] == [2]
    assert result["rafCancelled"] == [1]
