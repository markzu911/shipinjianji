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
