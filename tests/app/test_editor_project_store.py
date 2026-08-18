from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def run_store_script(body: str) -> dict[str, object]:
    script = f"""
const timeline = require('./web/timeline-model.js');
const projectStore = require('./web/editor-project-store.js');
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
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for the editor project store tests.")
    return json.loads(completed.stdout)


def test_editor_project_store_owns_and_freezes_snapshots() -> None:
    result = run_store_script(
        r"""
const job = {
  id: 'job-one', status: 'completed', duration: 10, updatedAt: 'v1',
  result: { text: '原文', segments: [{ text: '原文', start: 0, end: 1 }], editableSegments: [] },
  art: { source: 'original', overlays: [{ text: '原文', start: 0, end: 1, color: 'red' }] },
  pictureInPicture: { source: 'art', overlays: [{ assetId: 'asset-1', start: 1, end: 2 }] },
};
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job } });
const first = store.getState();
job.result.text = '被外部修改';
job.art.overlays[0].start = 9;
try { first.project.art.overlays[0].start = 8; } catch {}
console.log(JSON.stringify({
  frozen: Object.isFrozen(first) && Object.isFrozen(first.project.art.overlays[0]),
  text: first.project.transcript.text,
  artStart: first.project.art.overlays[0].start,
}));
"""
    )

    assert result == {
        "frozen": True,
        "text": "原文",
        "artStart": 0,
    }


def test_editor_project_store_new_job_always_advances_timing_revision() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
const first = store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-one', duration: 0, result: { text: '', segments: [] }
} } });
const same = store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-one', duration: 0, result: { text: '', segments: [] }
} } });
const second = store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-two', duration: 0, result: { text: '', segments: [] }
} } });
console.log(JSON.stringify({ first, same, second }));
"""
    )

    assert result["first"] == {
        "accepted": True,
        "revision": 1,
        "timingRevision": 1,
    }
    assert result["same"]["accepted"] is False
    assert result["second"] == {
        "accepted": True,
        "revision": 2,
        "timingRevision": 2,
    }


def test_editor_project_store_revision_matrix_and_text_only_merge() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
const job = {
  id: 'job-one', status: 'completed', duration: 10, updatedAt: 'v1',
  result: { text: '原文', segments: [], editableSegments: [] },
  art: { source: 'original', overlays: [{ text: '原文', start: 1, end: 3, sourceStart: 1, sourceEnd: 3, color: 'red', trackType: 'transcript', trackId: 'full' }] },
  pictureInPicture: { source: 'art', overlays: [{ assetId: 'asset-1', start: 2, end: 4, sourceStart: 2, sourceEnd: 4 }] },
};
const revisions = [];
revisions.push(store.dispatch({ type: 'projectHydrated', payload: { job } }));
revisions.push(store.dispatch({ type: 'activeToolChanged', payload: { tool: 'art' } }));
revisions.push(store.dispatch({ type: 'artStateChanged', payload: {
  source: 'original', overlays: [{ text: '原文', start: 1, end: 3, sourceStart: 1, sourceEnd: 3, color: 'blue', trackType: 'transcript', trackId: 'full' }]
} }));
revisions.push(store.dispatch({ type: 'transcriptTextChanged', payload: {
  transcript: { text: '新文案', segments: [], editableSegments: [] },
  editableSegments: [],
  serverArt: { overlays: [{ text: '新文案', start: 1, end: 3, sourceStart: 1, sourceEnd: 3, trackType: 'transcript', trackId: 'full' }] },
} }));
const afterText = store.getState();
revisions.push(store.dispatch({ type: 'artStateChanged', payload: {
  source: 'original', overlays: [{ text: '新文案', start: 1.25, end: 3, sourceStart: 1, sourceEnd: 3, color: 'blue', trackType: 'transcript', trackId: 'full' }]
} }));
revisions.push(store.dispatch({ type: 'cutTimingChanged', payload: {
  active: true, ranges: [{ start: 4, end: 5 }], sourceDuration: 10, duration: 9,
  transcript: { text: '新文案', segments: [] },
} }));
console.log(JSON.stringify({
  revisions,
  textTimingRevision: afterText.timingRevision,
  text: afterText.project.art.overlays[0].text,
  color: afterText.project.art.overlays[0].color,
  times: [
    afterText.project.art.overlays[0].start,
    afterText.project.art.overlays[0].end,
    afterText.project.art.overlays[0].sourceStart,
    afterText.project.art.overlays[0].sourceEnd,
  ],
}));
"""
    )

    assert [item["revision"] for item in result["revisions"]] == [1, 2, 3, 4, 5, 6]
    assert [item["timingRevision"] for item in result["revisions"]] == [
        1,
        1,
        1,
        1,
        2,
        3,
    ]
    assert result["textTimingRevision"] == 1
    assert result["text"] == "新文案"
    assert result["color"] == "blue"
    assert result["times"] == [1, 3, 1, 3]


def test_editor_project_store_rejects_stale_and_timing_conflicted_effects() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-one', duration: 10, result: { text: '原文', segments: [] }
} } });
let notifications = 0;
store.subscribe(() => { notifications += 1; });
const stale = store.beginEffect('transcript-save');
const latest = store.beginEffect('transcript-save');
const staleResult = store.applyEffect(stale, { type: 'transcriptTextChanged', payload: {
  transcript: { text: '旧响应', segments: [] }
} });
store.dispatch({ type: 'activeToolChanged', payload: { tool: 'art' } });
const latestResult = store.applyEffect(latest, { type: 'transcriptTextChanged', payload: {
  transcript: { text: '新响应', segments: [] }
} });
const timingToken = store.beginEffect('transcript-refresh');
store.dispatch({ type: 'cutTimingChanged', payload: {
  active: true, ranges: [{ start: 1, end: 2 }], sourceDuration: 10, duration: 9,
  transcript: { text: '新响应', segments: [] },
} });
const timingResult = store.applyEffect(timingToken, { type: 'transcriptTextChanged', payload: {
  transcript: { text: '冲突响应', segments: [] }
} });
const oldJobToken = store.beginEffect('job-change');
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-two', duration: 5, result: { text: '另一个任务', segments: [] }
} } });
const oldJobResult = store.applyEffect(oldJobToken, { type: 'transcriptTextChanged', payload: {
  transcript: { text: '错误任务', segments: [] }
} });
console.log(JSON.stringify({
  staleResult, latestResult, timingResult, oldJobResult, notifications,
  text: store.getState().project.transcript.text,
}));
"""
    )

    assert result["staleResult"]["accepted"] is False
    assert result["latestResult"]["accepted"] is True
    assert result["timingResult"]["accepted"] is False
    assert result["oldJobResult"]["accepted"] is False
    assert result["notifications"] == 4
    assert result["text"] == "另一个任务"


def test_editor_project_store_preserves_local_tools_and_selects_compose_atomically() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
const baseJob = {
  id: 'job-one', status: 'completed', duration: 10, updatedAt: 'v1',
  result: { text: '原文', segments: [] },
  art: { source: 'original', overlays: [{ text: '服务端', start: 1, end: 2 }] },
  pictureInPicture: { source: 'art', overlays: [{ assetId: 'asset-1', start: 2, end: 3 }] },
};
store.dispatch({ type: 'projectHydrated', payload: { job: baseJob } });
store.dispatch({ type: 'artStateChanged', payload: {
  source: 'original', overlays: [{ text: '本地艺术字', start: 1, end: 2, x: 0.8 }]
} });
store.dispatch({ type: 'pipStateChanged', payload: {
  source: 'art', overlays: [{ assetId: 'asset-1', start: 2, end: 3, width: 0.5 }]
} });
store.dispatch({ type: 'cutTimingChanged', payload: {
  active: true, ranges: [{ start: 4, end: 5 }], sourceDuration: 10, duration: 9,
  transcript: { text: '原文', segments: [{ id: 'one', text: '原文', start: 0, end: 1 }] },
} });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  ...baseJob,
  updatedAt: 'v2',
  art: { source: 'original', overlays: [{ text: '迟到服务端', start: 7, end: 8 }] },
  pictureInPicture: { source: 'art', overlays: [{ assetId: 'asset-1', start: 7, end: 8 }] },
} } });
const snapshot = store.getState();
const request = projectStore.selectCompositionRequest(snapshot);
const timelineDocument = projectStore.selectTimelineDocument(snapshot, timeline);
store.dispatch({ type: 'activeToolChanged', payload: { tool: 'pip' } });
console.log(JSON.stringify({
  snapshotRevision: snapshot.revision,
  currentRevision: store.getState().revision,
  request,
  localArt: snapshot.project.art.overlays[0],
  localPip: snapshot.project.pip.overlays[0],
  timelineKinds: timelineDocument.tracks.map(track => track.kind),
}));
"""
    )

    assert result["currentRevision"] == result["snapshotRevision"] + 1
    assert result["request"]["ranges"] == [{"start": 4, "end": 5}]
    assert result["request"]["artOverlays"][0]["text"] == "本地艺术字"
    assert result["request"]["pictureInPictureOverlays"][0]["width"] == 0.5
    assert result["localArt"]["start"] == 1
    assert result["localPip"]["start"] == 2
    assert result["timelineKinds"] == ["cut"]
