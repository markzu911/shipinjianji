import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def run_node(script: str) -> dict:
    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="strict",
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for timeline controller tests.")
    return json.loads(result.stdout)


def test_timeline_controller_commits_once_and_undoes_across_tracks():
    payload = run_node(
        r"""
const timeline = require('./web/timeline-model.js');
global.EditorTimeline = timeline;
const timelineController = require('./web/editor-timeline-controller.js');
const commits = [];
const controller = timelineController.createController({
  timeline,
  keyboardTarget: null,
  onCommit: transaction => {
    commits.push(transaction);
    return { accepted: true };
  }
});
controller.render({
  revision: 4,
  timingRevision: 2,
  timeline: {
    duration: 12,
    tracks: [
      { id: 'cut', kind: 'cut', clips: [
        { id: 'cut:1', sourceId: '1', start: 1, end: 2, minDuration: 0.1 }
      ] },
      { id: 'art', kind: 'art', clips: [
        { id: 'art:1', sourceId: 'a', start: 2, end: 4, minDuration: 0.1 }
      ] },
      { id: 'pip', kind: 'pip', clips: [
        { id: 'pip:1', sourceId: 'p', start: 6, end: 8, minDuration: 0.1 }
      ] }
    ]
  }
});

controller.submitRange('art:1', 3, 5, { reason: 'move-art' });
controller.render({
  revision: 5,
  timingRevision: 3,
  timeline: {
    duration: 12,
    tracks: [
      { id: 'cut', kind: 'cut', clips: [{ id: 'cut:1', sourceId: '1', start: 1, end: 2 }] },
      { id: 'art', kind: 'art', clips: [{ id: 'art:1', sourceId: 'a', start: 3, end: 5 }] },
      { id: 'pip', kind: 'pip', clips: [{ id: 'pip:1', sourceId: 'p', start: 6, end: 8 }] }
    ]
  }
});
controller.submitRange('pip:1', 7, 8, { reason: 'resize-pip' });
controller.render({
  revision: 6,
  timingRevision: 4,
  timeline: {
    duration: 12,
    tracks: [
      { id: 'cut', kind: 'cut', clips: [{ id: 'cut:1', sourceId: '1', start: 1, end: 2 }] },
      { id: 'art', kind: 'art', clips: [{ id: 'art:1', sourceId: 'a', start: 3, end: 5 }] },
      { id: 'pip', kind: 'pip', clips: [{ id: 'pip:1', sourceId: 'p', start: 7, end: 8 }] }
    ]
  }
});
const undoPip = controller.undo();
controller.render({
  revision: 7,
  timingRevision: 5,
  timeline: {
    duration: 12,
    tracks: [
      { id: 'cut', kind: 'cut', clips: [{ id: 'cut:1', sourceId: '1', start: 1, end: 2 }] },
      { id: 'art', kind: 'art', clips: [{ id: 'art:1', sourceId: 'a', start: 3, end: 5 }] },
      { id: 'pip', kind: 'pip', clips: [{ id: 'pip:1', sourceId: 'p', start: 6, end: 8 }] }
    ]
  }
});
const undoArt = controller.undo();
const redoArt = controller.redo();
console.log(JSON.stringify({
  commits: commits.map(item => ({
    kind: item.kind,
    start: item.start,
    end: item.end,
    direction: item.direction
  })),
  history: controller.historySnapshot(),
  undoPip,
  undoArt,
  redoArt
}));
"""
    )

    assert payload["undoPip"] is True
    assert payload["undoArt"] is True
    assert payload["redoArt"] is True
    assert payload["commits"] == [
        {"kind": "art", "start": 3, "end": 5, "direction": "forward"},
        {"kind": "pip", "start": 7, "end": 8, "direction": "forward"},
        {"kind": "pip", "start": 6, "end": 8, "direction": "undo"},
        {"kind": "art", "start": 2, "end": 4, "direction": "undo"},
        {"kind": "art", "start": 3, "end": 5, "direction": "redo"},
    ]
    assert payload["history"]["index"] == 1
    assert len(payload["history"]["entries"]) == 2


def test_timeline_controller_clamps_ranges_and_truncates_redo_branch():
    payload = run_node(
        r"""
const timeline = require('./web/timeline-model.js');
global.EditorTimeline = timeline;
const timelineController = require('./web/editor-timeline-controller.js');
const commits = [];
const controller = timelineController.createController({
  timeline,
  keyboardTarget: null,
  onCommit: transaction => {
    commits.push(transaction);
    return true;
  }
});
const frame = (start, end, revision) => ({
  revision,
  timingRevision: revision,
  timeline: { duration: 10, tracks: [
    { id: 'art', kind: 'art', clips: [
      { id: 'art:1', sourceId: 'a', start, end, minDuration: 0.5 }
    ] }
  ] }
});
controller.render(frame(2, 4, 1));
const bounded = controller.submitRange('art:1', 9.9, 20, { reason: 'bounded' });
controller.render(frame(bounded.start, bounded.end, 2));
controller.undo();
controller.render(frame(2, 4, 3));
const canRedoBefore = controller.canRedo();
controller.submitRange('art:1', 4, 6, { reason: 'branch' });
const canRedoAfter = controller.canRedo();
const unchanged = controller.submitRange('art:1', 4, 6, { reason: 'same' });
console.log(JSON.stringify({
  bounded,
  canRedoBefore,
  canRedoAfter,
  history: controller.historySnapshot(),
  commitCount: commits.length,
  unchanged
}));
"""
    )

    assert payload["bounded"]["end"] == 10
    assert payload["bounded"]["end"] - payload["bounded"]["start"] >= 0.5
    assert payload["canRedoBefore"] is True
    assert payload["canRedoAfter"] is False
    assert len(payload["history"]["entries"]) == 1
    assert payload["commitCount"] == 3
    assert payload["unchanged"]["start"] == 4
    assert payload["unchanged"]["end"] == 6


def test_timeline_controller_clears_history_when_the_media_job_changes():
    payload = run_node(
        r"""
const timeline = require('./web/timeline-model.js');
global.EditorTimeline = timeline;
const timelineController = require('./web/editor-timeline-controller.js');
const commits = [];
const controller = timelineController.createController({
  timeline,
  keyboardTarget: null,
  onCommit: transaction => {
    commits.push(transaction);
    return true;
  }
});
const frame = (jobId, start, end, revision) => ({
  revision,
  timingRevision: revision,
  media: { jobId },
  timeline: { duration: 10, tracks: [
    { id: 'art', kind: 'art', clips: [
      { id: 'art:1', sourceId: 'a', start, end, minDuration: 0.5 }
    ] }
  ] }
});
controller.render(frame('job-one', 2, 4, 1));
controller.submitRange('art:1', 3, 5, { reason: 'job-one-move' });
const canUndoBefore = controller.canUndo();
controller.render(frame('job-two', 1, 2, 1));
console.log(JSON.stringify({
  canUndoBefore,
  canUndoAfter: controller.canUndo(),
  undoAfter: controller.undo(),
  commitCount: commits.length,
  history: controller.historySnapshot(),
}));
"""
    )

    assert payload == {
        "canUndoBefore": True,
        "canUndoAfter": False,
        "undoAfter": False,
        "commitCount": 1,
        "history": {"index": 0, "entries": []},
    }


def test_timeline_controller_projects_only_configured_visible_kinds():
    payload = run_node(
        r"""
const timeline = require('./web/timeline-model.js');
global.EditorTimeline = timeline;
function element() {
  return {
    dataset: {}, children: [], hidden: false,
    style: { values: {}, setProperty(k, v) { this.values[k] = v; }, removeProperty(k) { delete this.values[k]; } },
    classList: { toggle() {} },
    setAttribute() {}, addEventListener() {}, removeEventListener() {},
    append(...items) { this.children.push(...items); },
    replaceChildren(...items) { this.children = items; },
  };
}
global.document = { createElement: () => element() };
const timelineController = require('./web/editor-timeline-controller.js');
const layer = element();
const track = element();
const selected = [];
const commits = [];
const controller = timelineController.createController({
  timeline, root: layer, track, keyboardTarget: null, visibleKinds: ['art', 'pip'],
  onSelect: transaction => { selected.push(transaction.clip.id); return true; },
  onCommit: transaction => { commits.push(transaction); return true; },
});
const documentState = controller.render({
  revision: 3, timingRevision: 2,
  timeline: { duration: 10, tracks: [
    { id: 'cut', kind: 'cut', clips: [{ id: 'cut:1', sourceId: 'c', start: 0, end: 1 }] },
    { id: 'art:manual', kind: 'art', clips: [
      { id: 'art:1', sourceId: 'a1', start: 1, end: 4 },
      { id: 'art:2', sourceId: 'a2', start: 2, end: 3 },
      { id: 'art:3', sourceId: 'a3', start: 4, end: 5 },
    ] },
    { id: 'art:transcript:full', kind: 'art', clips: [
      { id: 'art:cue', sourceId: 'cue', start: 1, end: 2 },
    ] },
    { id: 'pip', kind: 'pip', clips: [{ id: 'pip:1', sourceId: 'p', start: 2, end: 3 }] },
  ] },
});
const layout = {
  kinds: layer.children.map(item => item.dataset.effectKind),
  tracks: layer.children.map(item => item.dataset.timelineTrackIndex),
  lanes: layer.children.map(item => item.dataset.timelineLaneIndex),
  tops: layer.children.map(item => item.style.top),
  height: layer.style.height,
  trackHeight: track.style.values['--editor-timeline-track-height'],
};
controller.selectClip('art:2');
controller.submitRange('art:2', 2.5, 3.5, { reason: 'move-overlap' });
console.log(JSON.stringify({
  layout,
  selected,
  commits: commits.map(item => ({ clipId: item.clipId, sourceId: item.sourceId })),
  ranges: controller.currentDocument().tracks
    .find(item => item.id === 'art:manual').clips
    .map(item => ({ id: item.id, start: item.start, end: item.end })),
  authoritativeKinds: documentState.tracks.map(track => track.kind),
}));
"""
    )

    assert payload == {
        "layout": {
            "kinds": ["art", "art", "art", "art", "pip"],
            "tracks": ["0", "0", "0", "1", "2"],
            "lanes": ["0", "1", "0", "0", "0"],
            "tops": ["2px", "32px", "2px", "62px", "92px"],
            "height": "120px",
            "trackHeight": "194px",
        },
        "selected": ["art:2"],
        "commits": [{"clipId": "art:2", "sourceId": "a2"}],
        "ranges": [
            {"id": "art:1", "start": 1, "end": 4},
            {"id": "art:2", "start": 2.5, "end": 3.5},
            {"id": "art:3", "start": 4, "end": 5},
        ],
        "authoritativeKinds": ["cut", "art", "art", "pip"],
    }


def test_timeline_clip_click_seek_semantics_cover_scroll_fallback_and_drag():
    payload = run_node(
        r"""
const timeline = require('./web/timeline-model.js');
global.EditorTimeline = timeline;

const rootListeners = new Map();
global.addEventListener = (type, callback) => {
  if (!rootListeners.has(type)) rootListeners.set(type, new Set());
  rootListeners.get(type).add(callback);
};
global.removeEventListener = (type, callback) => {
  rootListeners.get(type)?.delete(callback);
};
function emitRoot(type, event = {}) {
  for (const callback of [...(rootListeners.get(type) || [])]) {
    callback({ type, ...event });
  }
}

function element() {
  const listeners = new Map();
  const classes = new Set();
  return {
    dataset: {}, attributes: {}, children: [], hidden: false, parentElement: null,
    style: {
      values: {},
      setProperty(key, value) { this.values[key] = value; },
      removeProperty(key) { delete this.values[key]; },
    },
    classList: {
      toggle(name, force) {
        if (force === false) classes.delete(name);
        else if (force === true || !classes.has(name)) classes.add(name);
        else classes.delete(name);
      },
      contains(name) { return classes.has(name); },
    },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(callback);
    },
    removeEventListener(type, callback) { listeners.get(type)?.delete(callback); },
    emit(type, event) {
      for (const callback of [...(listeners.get(type) || [])]) callback(event);
    },
    append(...items) {
      for (const item of items) item.parentElement = this;
      this.children.push(...items);
    },
    replaceChildren(...items) {
      for (const item of items) item.parentElement = this;
      this.children = items;
    },
    closest(selector) {
      let current = this;
      while (current) {
        if (selector === '[data-timeline-clip-id]' && current.dataset.timelineClipId) {
          return current;
        }
        if (selector === '[data-timeline-resize]' && current.dataset.timelineResize) {
          return current;
        }
        current = current.parentElement;
      }
      return null;
    },
  };
}

global.document = { createElement: () => element() };
const timelineController = require('./web/editor-timeline-controller.js');
const layer = element();
const track = element();
track.getBoundingClientRect = () => ({ left: -200, width: 1000 });
const selections = [];
const seeks = [];
const previews = [];
const commits = [];
const controller = timelineController.createController({
  timeline,
  root: layer,
  track,
  keyboardTarget: null,
  visibleKinds: ['art', 'pip'],
  onSelect: transaction => {
    selections.push({ id: transaction.clip.id, source: transaction.source });
    return transaction.clip.id !== 'art:reject';
  },
  onSeek: (seconds, clip) => seeks.push({ id: clip.id, seconds }),
  onPreview: transaction => previews.push({
    id: transaction.clip.id,
    mode: transaction.mode,
    start: transaction.clip.start,
    end: transaction.clip.end,
  }),
  onCommit: transaction => {
    commits.push({
      id: transaction.clipId,
      reason: transaction.reason,
      start: transaction.start,
      end: transaction.end,
    });
    return true;
  },
});
controller.render({
  revision: 1,
  timingRevision: 1,
  timeline: { duration: 20, tracks: [
    { id: 'art:manual', kind: 'art', clips: [
      { id: 'art:manual-1', sourceId: 'manual-1', start: 4, end: 8 },
      { id: 'art:reject', sourceId: 'reject', start: 8, end: 10 },
    ] },
    { id: 'art:transcript:full', kind: 'art', clips: [
      { id: 'art:cue-1', sourceId: 'cue-1', start: 12, end: 16 },
    ] },
    { id: 'pip', kind: 'pip', clips: [
      { id: 'pip:1', sourceId: 'pip-1', start: 2, end: 6, editable: false },
    ] },
  ] },
});

function pointerTarget(segment, mode) {
  if (mode === 'move') return segment;
  return segment.children.find(item => item.dataset.timelineResize === mode);
}

function pointerDownClip(clipId, clientX, mode = 'move') {
  const segment = layer.children.find(item => item.dataset.timelineClipId === clipId);
  const target = pointerTarget(segment, mode);
  const effects = { prevented: false, stopped: false };
  layer.emit('pointerdown', {
    target,
    button: 0,
    clientX,
    preventDefault() { effects.prevented = true; },
    stopPropagation() { effects.stopped = true; },
  });
  return { effects, target };
}

function clickClip(clipId, clientX, mode = 'move') {
  const { effects, target } = pointerDownClip(clipId, clientX, mode);
  emitRoot('pointerup', { target, button: 0, clientX });
  return effects;
}

function dragClip(clipId, startClientX, endClientX, mode = 'move') {
  const { effects, target } = pointerDownClip(clipId, startClientX, mode);
  emitRoot('pointermove', { target, button: 0, clientX: endClientX });
  emitRoot('pointerup', { target, button: 0, clientX: endClientX });
  return effects;
}

const effects = [
  clickClip('art:manual-1', 100),
  clickClip('art:cue-1', 500),
  clickClip('pip:1', 0),
];
controller.selectClip('art:manual-1');

track.getBoundingClientRect = () => ({ left: Number.NaN, width: 1000 });
effects.push(clickClip('art:cue-1', 500));
track.getBoundingClientRect = () => ({ left: -200, width: 1000 });

const seekCountBeforeReject = seeks.length;
effects.push(clickClip('art:reject', 250));
const rejection = {
  seekCount: seeks.length - seekCountBeforeReject,
  selectedIds: layer.children
    .filter(item => item.attributes['aria-pressed'] === 'true')
    .map(item => item.dataset.timelineClipId),
};

effects.push(clickClip('art:manual-1', 200, 'end'));
effects.push(dragClip('art:manual-1', 100, 150));
effects.push(dragClip('art:manual-1', 300, 350, 'end'));

controller.render({
  revision: 2,
  timingRevision: 2,
  timeline: { duration: 0, tracks: [
    { id: 'art:manual', kind: 'art', clips: [
      { id: 'art:manual-1', sourceId: 'manual-1', start: 4, end: 8 },
    ] },
  ] },
});
effects.push(clickClip('art:manual-1', 100));

console.log(JSON.stringify({
  effects,
  selections,
  seeks,
  rejection,
  previews,
  commits,
}));
"""
    )

    assert payload == {
        "effects": [
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
            {"prevented": True, "stopped": True},
        ],
        "selections": [
            {"id": "art:manual-1", "source": "pointer"},
            {"id": "art:cue-1", "source": "pointer"},
            {"id": "pip:1", "source": "pointer"},
            {"id": "art:manual-1", "source": "timeline"},
            {"id": "art:cue-1", "source": "pointer"},
            {"id": "art:reject", "source": "pointer"},
            {"id": "art:manual-1", "source": "pointer"},
            {"id": "art:manual-1", "source": "pointer"},
        ],
        "seeks": [
            {"id": "art:manual-1", "seconds": 6},
            {"id": "art:cue-1", "seconds": 14},
            {"id": "pip:1", "seconds": 4},
            {"id": "art:manual-1", "seconds": 4},
            {"id": "art:cue-1", "seconds": 12},
            {"id": "art:manual-1", "seconds": 4},
            {"id": "art:manual-1", "seconds": 5},
            {"id": "art:manual-1", "seconds": 10},
            {"id": "art:manual-1", "seconds": 4},
        ],
        "rejection": {"seekCount": 0, "selectedIds": ["art:cue-1"]},
        "previews": [
            {"id": "art:manual-1", "mode": "move", "start": 5, "end": 9},
            {"id": "art:manual-1", "mode": "end", "start": 5, "end": 10},
        ],
        "commits": [
            {
                "id": "art:manual-1",
                "reason": "pointer-move",
                "start": 5,
                "end": 9,
            },
            {
                "id": "art:manual-1",
                "reason": "pointer-end",
                "start": 5,
                "end": 10,
            },
        ],
    }
