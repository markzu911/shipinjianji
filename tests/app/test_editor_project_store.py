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


def test_editor_project_store_only_selects_media_after_transcription_completes() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
function hydrate(status, result = null) {
  store.dispatch({ type: 'projectHydrated', payload: { job: {
    id: 'job-transition', status, duration: result ? 10 : 0, result,
  } } });
  return projectStore.selectEditorFrame(store.getState(), timeline).media.sourceUrl;
}
const queued = hydrate('queued');
const transcribing = hydrate('transcribing');
const completed = hydrate('completed', {
  mediaDuration: 10, text: 'ready', segments: [], editableSegments: [],
});
console.log(JSON.stringify({ queued, transcribing, completed }));
"""
    )

    assert result == {
        "queued": "",
        "transcribing": "",
        "completed": "/api/transcriptions/job-transition/original-video",
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
global.EditorPipModel = require('./web/editor-pip-model.js');
const store = projectStore.createStore({}, { timeline });
const baseJob = {
  id: 'job-one', status: 'completed', duration: 10, updatedAt: 'v1',
  result: { text: '原文', segments: [] },
  art: { source: 'original', overlays: [{ text: '服务端', start: 1, end: 2 }] },
  pictureInPicture: { source: 'art', overlays: [{ assetId: 'asset-1', start: 2, end: 3 }] },
  pictureInPictureImages: [{
    id: 'asset-1', type: 'image', source: 'art', status: 'completed',
    assetUrl: '/asset-1.png', start: 2, end: 3,
  }],
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
  pictureInPictureImages: [
    ...baseJob.pictureInPictureImages,
    {
      id: 'asset-after-cancel', type: 'image', source: 'art', status: 'completed',
      assetUrl: '/asset-after-cancel.png', start: 4, end: 6,
    },
  ],
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
  pipAssetIds: snapshot.project.pip.assets.map(asset => asset.id),
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
    assert result["pipAssetIds"] == ["asset-1", "asset-after-cancel"]
    assert result["timelineKinds"] == ["cut", "art", "pip"]


def test_editor_project_store_selects_atomic_semantic_frame_and_explicit_compose_dto() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-frame', status: 'completed', duration: 12,
  result: { mediaDuration: 12, text: '文案', segments: [] },
  art: { source: 'original', overlays: [{
    text: '标题', font: 'bold', fontSize: 54, color: '#FFFFFF',
    strokeColor: '#000000', strokeWidth: 3, shadow: true,
    x: 0.5, y: 0.2, start: 1, end: 3, localOnly: 'drop-me'
  }] },
  pictureInPictureImages: [{
    id: 'asset-one', text: '图片', imageUrl: '/asset-one.png', status: 'completed'
  }],
  pictureInPicture: { source: 'art', overlays: [{
    assetId: 'asset-one', start: 2, end: 4, x: 0.8, y: 0.2, width: 0.4,
    assetUrl: '/must-not-compose.png', status: 'completed'
  }] },
} } });
const hydratedArt = store.getState().project.art;
store.dispatch({ type: 'artStateChanged', payload: {
  ...hydratedArt,
  timeline: { duration: 12, tracks: [{
    id: 'art:track', kind: 'art', clips: [{
      id: 'art:semantic', sourceId: hydratedArt.overlays[0].id,
      name: '标题', start: 1, end: 3, editable: true,
    }]
  }] },
} });
store.dispatch({ type: 'activeToolChanged', payload: { tool: 'pip' } });
store.dispatch({ type: 'pipStateChanged', payload: {
  source: 'art',
  overlays: [{ assetId: 'asset-one', start: 2, end: 4, x: 0.8, y: 0.2, width: 0.4 }],
  assets: [{ id: 'asset-two', type: 'video', assetUrl: '/asset-two.mp4' }],
  timeline: { duration: 12, tracks: [{
    id: 'pip:track', kind: 'pip', clips: [{
      id: 'pip:asset-one', sourceId: 'asset-one', name: '图片',
      start: 2, end: 4, editable: true,
    }]
  }], selection: { clipId: 'pip:asset-one' } },
} });
store.dispatch({ type: 'timelineKindChanged', payload: {
  kind: 'cut',
  timeline: { duration: 12, tracks: [{
    id: 'cut:manual', kind: 'cut', clips: [{
      id: 'cut:range:1', sourceId: '1', name: '删除区间',
      start: 6, end: 7, editable: true,
    }]
  }] },
} });
const snapshot = store.getState();
const frame = projectStore.selectEditorFrame(snapshot, timeline);
console.log(JSON.stringify({
  snapshotRevision: snapshot.revision,
  frameRevision: frame.revision,
  previewRevision: frame.preview.revision,
  timelineKinds: frame.timeline.tracks.map(track => track.kind),
  selection: frame.timeline.selection,
  sourceUrl: frame.media.sourceUrl,
  artId: frame.preview.art.overlays[0].id,
  pipId: frame.preview.pip.overlays[0].id,
  assets: frame.preview.pip.assets.map(asset => ({
    id: asset.id, type: asset.type, assetUrl: asset.assetUrl,
  })),
  composeArt: frame.composition.artOverlays[0],
  composePip: frame.composition.pictureInPictureOverlays[0],
}));
"""
    )

    assert result["snapshotRevision"] == result["frameRevision"]
    assert result["previewRevision"] == result["frameRevision"]
    assert result["sourceUrl"].endswith("/job-frame/original-video")
    assert result["timelineKinds"] == ["cut", "art", "pip"]
    assert result["selection"]["clipId"] == "pip:asset-one"
    assert result["artId"] == "art:overlay:0"
    assert result["pipId"] == "asset-one"
    assert result["assets"] == [
        {"id": "asset-one", "type": "image", "assetUrl": "/asset-one.png"},
        {"id": "asset-two", "type": "video", "assetUrl": "/asset-two.mp4"},
    ]
    assert "id" not in result["composeArt"]
    assert "localOnly" not in result["composeArt"]
    assert "id" not in result["composePip"]
    assert "assetUrl" not in result["composePip"]
    assert "status" not in result["composePip"]


def test_editor_project_store_atomically_reconciles_cut_art_and_restores_undo() -> None:
    result = run_store_script(
        r"""
global.EditorArtModel = require('./web/editor-art-model.js');
const model = global.EditorArtModel;
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-cut-art', status: 'completed', duration: 6,
  result: { mediaDuration: 6, text: '甲乙丙丁', segments: [] },
} } });
const overlay = (value) => model.normalizeOverlay(value, { duration: 6 });
const art = { source: 'original', overlays: [
  overlay({
    id: 'cue-one', text: '甲乙', start: 0, end: 2,
    sourceStart: 0, sourceEnd: 2, trackType: 'transcript', trackId: 'full',
    characterTimings: [{ start: 0, end: 1 }, { start: 1, end: 2 }],
  }),
  overlay({
    id: 'cue-two', text: '丙丁', start: 2, end: 4,
    sourceStart: 2, sourceEnd: 4, trackType: 'transcript', trackId: 'full',
    characterTimings: [{ start: 2, end: 3 }, { start: 3, end: 4 }],
  }),
  overlay({ id: 'manual', text: '乙', start: 1, end: 2, sourceStart: 1, sourceEnd: 2 }),
  overlay({ id: 'custom', text: '标题', start: 0.2, end: 0.8 }),
] };
store.dispatch({ type: 'activeToolChanged', payload: { tool: 'art' } });
store.dispatch({ type: 'artStateChanged', payload: {
  art,
  timeline: model.buildTimeline(art, 6, { clipId: 'art:cue-two' }),
} });
const before = store.getState();
const transcript = (parts) => ({ segments: parts.map(([text, start, end, sourceStart, sourceEnd]) => ({
  text, start, end, sourceStart, sourceEnd,
  words: [{ text, start, end, sourceStart, sourceEnd }],
})) });
const observed = [];
store.subscribe((state, previous, action) => {
  if (action.type !== 'cutTimingChanged') return;
  const frame = projectStore.selectEditorFrame(state, timeline);
  observed.push({
    revisionDelta: state.revision - previous.revision,
    overlayIds: state.project.art.overlays.map(item => item.id),
    timelineIds: frame.timeline.tracks.filter(track => track.kind === 'art')
      .flatMap(track => track.clips.map(clip => clip.sourceId)),
    composeIds: frame.composition.artOverlays.map(item => item.text),
  });
});
const cross = store.dispatch({ type: 'cutTimingChanged', payload: {
  active: true, ranges: [{ start: 1, end: 3 }], sourceDuration: 6, duration: 4,
  transcript: transcript([['甲', 0, 1, 0, 1], ['丁', 1, 2, 3, 4]]),
} });
const afterCross = store.getState();
const fullCue = store.dispatch({ type: 'cutTimingChanged', payload: {
  active: true, ranges: [{ start: 2, end: 4 }], sourceDuration: 6, duration: 4,
  transcript: transcript([['甲乙', 0, 2, 0, 2]]),
} });
const afterFullCue = store.getState();
const undo = store.dispatch({ type: 'cutTimingChanged', payload: {
  active: false, ranges: [], sourceDuration: 6, duration: 6,
  transcript: transcript([['甲乙丙丁', 0, 4, 0, 4]]),
} });
const afterUndo = store.getState();
console.log(JSON.stringify({
  beforeRevision: before.revision,
  cross,
  fullCue,
  undo,
  observed,
  crossText: afterCross.project.art.overlays.map(item => [item.id, item.text]),
  crossSuppressed: afterCross.project.art.suppressedOverlays.map(item => item.id),
  fullCueIds: afterFullCue.project.art.overlays.map(item => item.id),
  fullCueSuppressed: afterFullCue.project.art.suppressedOverlays.map(item => item.id),
  fullCueSelection: afterFullCue.project.timeline.selection,
  undoText: afterUndo.project.art.overlays.map(item => [item.id, item.text]),
  undoSuppressed: afterUndo.project.art.suppressedOverlays,
  composeKeys: Object.keys(projectStore.selectCompositionRequest(afterCross).artOverlays[0]),
}));
"""
    )

    assert result["cross"]["revision"] == result["beforeRevision"] + 1
    assert result["fullCue"]["revision"] == result["beforeRevision"] + 2
    assert result["undo"]["revision"] == result["beforeRevision"] + 3
    assert result["crossText"] == [
        ["cue-one", "甲"],
        ["custom", "标题"],
        ["cue-two", "丁"],
    ]
    assert result["crossSuppressed"] == ["manual"]
    assert result["fullCueIds"] == ["cue-one", "custom", "manual"]
    assert result["fullCueSuppressed"] == ["cue-two"]
    assert result["fullCueSelection"]["clipId"] == "art:cue-one"
    assert result["undoText"] == [
        ["cue-one", "甲乙"],
        ["custom", "标题"],
        ["manual", "乙"],
        ["cue-two", "丙丁"],
    ]
    assert result["undoSuppressed"] == []
    assert all(item["revisionDelta"] == 1 for item in result["observed"])
    for item in result["observed"]:
        assert sorted(item["overlayIds"]) == sorted(item["timelineIds"])
        assert len(item["overlayIds"]) == len(item["composeIds"])
    assert "_cutReconciliation" not in result["composeKeys"]


def test_editor_project_store_does_not_retime_art_for_transcript_only_cut_update() -> None:
    result = run_store_script(
        r"""
global.EditorArtModel = require('./web/editor-art-model.js');
const model = global.EditorArtModel;
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-transcript-only', status: 'completed', duration: 1,
  result: { mediaDuration: 1, text: '旧文案', segments: [] },
} } });
const art = { source: 'original', overlays: [model.normalizeOverlay({
  id: 'cue', text: '旧文案', start: 0.4, end: 0.85,
  sourceStart: 0.4, sourceEnd: 0.85,
  trackType: 'transcript', trackId: 'full',
}, { duration: 1 })] };
store.dispatch({ type: 'artStateChanged', payload: {
  art,
  timeline: model.buildTimeline(art, 1, { clipId: 'art:cue' }),
} });
store.dispatch({ type: 'cutTimingChanged', payload: {
  active: false, ranges: [], sourceDuration: 1, duration: 1,
  transcript: { text: '旧文案', segments: [{
    text: '旧文案', start: 0.35, end: 0.95,
    sourceStart: 0.35, sourceEnd: 0.95,
    words: [{ text: '旧文案', start: 0.35, end: 0.95,
      sourceStart: 0.35, sourceEnd: 0.95 }],
  }] },
} });
const before = store.getState();
const dispatchResult = store.dispatch({ type: 'cutTimingChanged', payload: {
  active: false, ranges: [], sourceDuration: 1, duration: 1,
  transcript: { text: '全新文案', segments: [{
    text: '全新文案', start: 0.35, end: 0.95,
    sourceStart: 0.35, sourceEnd: 0.95,
    words: [{ text: '全新文案', start: 0.35, end: 0.95,
      sourceStart: 0.35, sourceEnd: 0.95 }],
  }] },
} });
const after = store.getState();
console.log(JSON.stringify({
  dispatchResult,
  beforeTimingRevision: before.timingRevision,
  afterTimingRevision: after.timingRevision,
  beforeArt: before.project.art,
  afterArt: after.project.art,
}));
"""
    )

    assert result["dispatchResult"]["accepted"] is True
    assert result["afterTimingRevision"] == result["beforeTimingRevision"]
    assert result["afterArt"] == result["beforeArt"]


def test_editor_project_store_reconciles_stale_art_draft_with_current_cut() -> None:
    result = run_store_script(
        r"""
global.EditorArtModel = require('./web/editor-art-model.js');
const model = global.EditorArtModel;
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-stale-draft', status: 'completed', duration: 4, updatedAt: 'server-v1',
  result: { mediaDuration: 4, text: '甲乙丙丁', segments: [] },
} } });
const transcript = { text: '丙丁', segments: [{
  text: '丙丁', start: 0, end: 2, sourceStart: 2, sourceEnd: 4,
  words: [{ text: '丙丁', start: 0, end: 2, sourceStart: 2, sourceEnd: 4 }],
}] };
store.dispatch({ type: 'cutTimingChanged', payload: {
  active: true, ranges: [{ start: 0, end: 2 }],
  sourceDuration: 4, duration: 2, transcript,
} });
const overlay = (value) => model.normalizeOverlay(value, { duration: 4 });
const staleArt = { source: 'original', suppressedOverlays: [], overlays: [
  overlay({
    id: 'cue-one', text: '甲乙', start: 0, end: 2,
    sourceStart: 0, sourceEnd: 2, trackType: 'transcript', trackId: 'full',
  }),
  overlay({
    id: 'cue-two', text: '丙丁', start: 2, end: 4,
    sourceStart: 2, sourceEnd: 4, trackType: 'transcript', trackId: 'full',
  }),
] };
const restored = store.dispatch({ type: 'projectDraftRestored', payload: {
  jobId: 'job-stale-draft', serverVersion: 'server-v1', art: staleArt,
  timeline: model.buildTimeline(staleArt, 4, { clipId: 'art:cue-one' }),
} });
const snapshot = store.getState();
const frame = projectStore.selectEditorFrame(snapshot, timeline);
console.log(JSON.stringify({
  restored,
  active: snapshot.project.art.overlays.map(({ id, text, start, end }) => ({
    id, text, start, end,
  })),
  suppressed: snapshot.project.art.suppressedOverlays.map(item => item.id),
  selection: snapshot.project.timeline.selection,
  timelineIds: frame.timeline.tracks.filter(track => track.kind === 'art')
    .flatMap(track => track.clips.map(clip => clip.sourceId)),
  timelineDuration: frame.timeline.duration,
  composition: frame.composition.artOverlays.map(item => item.text),
}));
"""
    )

    assert result["restored"]["accepted"] is True
    assert result["active"] == [
        {"id": "cue-two", "text": "丙丁", "start": 0, "end": 2}
    ]
    assert result["suppressed"] == ["cue-one"]
    assert result["selection"]["clipId"] == "art:cue-two"
    assert result["timelineIds"] == ["cue-two"]
    assert result["timelineDuration"] == 2
    assert result["composition"] == ["丙丁"]


def test_editor_project_store_timeline_range_action_is_atomic_and_echo_is_noop() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-timeline', duration: 10, result: { text: '', segments: [] }
} } });
store.dispatch({ type: 'artStateChanged', payload: {
  source: 'original',
  overlays: [{
    id: 'overlay-one', text: '标题', start: 1, end: 3,
    sourceStart: 1, sourceEnd: 3,
    characterTimings: [
      { start: 1, end: 2 },
      { start: 2, end: 3 },
    ],
  }],
  timeline: { duration: 10, tracks: [{
    id: 'art:track', kind: 'art', clips: [{
      id: 'art:overlay-one', sourceId: 'overlay-one', name: '标题',
      start: 1, end: 3, minDuration: 0.1, editable: true,
    }]
  }] },
} });
const before = store.getState();
const changed = store.dispatch({ type: 'timelineClipRangeChanged', payload: {
  kind: 'art', clipId: 'art:overlay-one', start: 2, end: 5,
  sourceStart: 2.5, sourceEnd: 5.5,
} });
const after = store.getState();
const echo = store.dispatch({ type: 'artStateChanged', payload: {
  ...after.project.art,
  timeline: after.project.timeline,
} });
const frame = projectStore.selectEditorFrame(after, timeline);
const clip = frame.timeline.tracks
  .flatMap(track => track.clips)
  .find(item => item.id === 'art:overlay-one');
console.log(JSON.stringify({
  beforeRevision: before.revision,
  beforeTimingRevision: before.timingRevision,
  changed,
  echo,
  afterRevision: after.revision,
  afterTimingRevision: after.timingRevision,
  overlay: after.project.art.overlays[0],
  clip,
  selection: frame.timeline.selection,
}));
"""
    )

    assert result["changed"]["accepted"] is True
    assert result["afterRevision"] == result["beforeRevision"] + 1
    assert result["afterTimingRevision"] == result["beforeTimingRevision"] + 1
    assert result["echo"]["accepted"] is False
    assert result["overlay"]["start"] == 2
    assert result["overlay"]["end"] == 5
    assert result["overlay"]["sourceStart"] == 2.5
    assert result["overlay"]["sourceEnd"] == 5.5
    assert result["overlay"]["characterTimings"] == [
        {"start": 2, "end": 3.5},
        {"start": 3.5, "end": 5},
    ]
    assert result["clip"]["start"] == 2
    assert result["clip"]["end"] == 5
    assert result["selection"]["clipId"] == "art:overlay-one"


def test_editor_project_store_restores_art_and_pip_draft_atomically() -> None:
    result = run_store_script(
        r"""
global.EditorPipModel = require('./web/editor-pip-model.js');
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-draft-v2', duration: 8, createdAt: 'base-v1',
  status: 'completed', result: { text: '', segments: [] },
  pictureInPictureImages: [{
    id: 'wide-asset', type: 'image', source: 'art', status: 'completed',
    assetUrl: '/wide.png', start: 1, end: 4,
  }],
  art: { status: 'completed', source: 'original', overlays: [] },
} } });
const before = store.getState();
const restored = store.dispatch({ type: 'projectDraftRestored', payload: {
  jobId: before.jobId,
  serverVersion: before.serverVersion,
  art: { source: 'original', overlays: [{
    id: 'headline', text: '标题', start: 1, end: 3, x: 0.5, y: 0.8,
  }] },
  pip: { source: 'art', assets: before.project.pip.assets, overlays: [{
    assetId: 'wide-asset', start: 1, end: 4, x: 0.5, y: 0.5, width: 1.75,
  }] },
  timeline: { duration: 8, tracks: [
    { id: 'art:overlay:headline', kind: 'art', clips: [{
      id: 'art:headline', sourceId: 'headline', kind: 'art', start: 1, end: 3,
    }] },
    { id: 'pip:overlay:wide-asset', kind: 'pip', clips: [{
      id: 'pip:wide-asset', sourceId: 'wide-asset', kind: 'pip', start: 1, end: 4,
    }] },
  ], selection: { clipId: 'pip:wide-asset' } },
} });
const after = store.getState();
const frame = projectStore.selectEditorFrame(after, timeline);
console.log(JSON.stringify({
  restored,
  revisionDelta: after.revision - before.revision,
  timingDelta: after.timingRevision - before.timingRevision,
  artIds: after.project.art.overlays.map(item => item.id),
  pipWidth: after.project.pip.overlays[0].width,
  selection: after.project.timeline.selection,
  composeWidth: frame.composition.pictureInPictureOverlays[0].width,
  timelineKinds: frame.timeline.tracks.map(track => track.kind),
}));
"""
    )

    assert result["restored"]["accepted"] is True
    assert result["revisionDelta"] == 1
    assert result["timingDelta"] == 1
    assert result["artIds"] == ["headline"]
    assert result["pipWidth"] == 1.75
    assert result["composeWidth"] == 1.75
    assert result["selection"] == {
        "clipId": "pip:wide-asset",
        "trackId": "pip:overlay:wide-asset",
    }
    assert result["timelineKinds"] == ["art", "pip"]


def test_editor_project_store_tool_echo_preserves_cross_kind_track_order() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-cross-kind-order', duration: 10,
  result: { text: '文案', segments: [{ id: 'one', text: '文案', start: 0, end: 1 }] },
} } });
store.dispatch({ type: 'pipStateChanged', payload: {
  source: 'original',
  overlays: [{ id: 'pip-one', assetId: 'asset-one', start: 2, end: 4 }],
  timeline: { duration: 10, tracks: [{
    id: 'pip:track', kind: 'pip', order: 0, clips: [{
      id: 'pip:pip-one', sourceId: 'pip-one', start: 2, end: 4,
    }],
  }] },
} });
store.dispatch({ type: 'artStateChanged', payload: {
  source: 'original',
  overlays: [{ id: 'art-one', text: '标题', start: 1, end: 3 }],
  timeline: { duration: 10, tracks: [{
    id: 'art:track', kind: 'art', order: 0, clips: [{
      id: 'art:art-one', sourceId: 'art-one', start: 1, end: 3,
    }],
  }] },
} });
const before = store.getState();
const echo = store.dispatch({ type: 'artStateChanged', payload: {
  ...before.project.art,
  timeline: before.project.timeline,
} });
const after = store.getState();
console.log(JSON.stringify({
  echo,
  beforeRevision: before.revision,
  afterRevision: after.revision,
  beforeTrackKinds: before.project.timeline.tracks.map(track => track.kind),
  afterTrackKinds: after.project.timeline.tracks.map(track => track.kind),
}));
"""
    )

    assert result["echo"]["accepted"] is False
    assert result["afterRevision"] == result["beforeRevision"]
    assert result["beforeTrackKinds"] == ["cut", "art", "pip"]
    assert result["afterTrackKinds"] == result["beforeTrackKinds"]


def test_editor_project_store_track_order_only_change_keeps_timing_revision() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-track-order', duration: 10, result: { text: '', segments: [] }
} } });
const art = {
  source: 'original',
  overlays: [
    { id: 'art-one', text: '标题一', start: 1, end: 3 },
    { id: 'art-two', text: '标题二', start: 4, end: 6 },
  ],
  timeline: { duration: 10, tracks: [
    { id: 'art:track-one', kind: 'art', clips: [{
      id: 'art:art-one', sourceId: 'art-one', start: 1, end: 3,
    }] },
    { id: 'art:track-two', kind: 'art', clips: [{
      id: 'art:art-two', sourceId: 'art-two', start: 4, end: 6,
    }] },
  ] },
};
store.dispatch({ type: 'artStateChanged', payload: art });
const before = store.getState();
const reordered = store.dispatch({
  type: 'artStateChanged',
  payload: { ...art, timeline: {
    ...art.timeline,
    tracks: [...art.timeline.tracks].reverse(),
  } },
});
const after = store.getState();
console.log(JSON.stringify({
  reordered,
  beforeRevision: before.revision,
  afterRevision: after.revision,
  beforeTimingRevision: before.timingRevision,
  afterTimingRevision: after.timingRevision,
  beforeTrackIds: before.project.timeline.tracks.map(track => track.id),
  afterTrackIds: after.project.timeline.tracks.map(track => track.id),
}));
"""
    )

    assert result["reordered"]["accepted"] is True
    assert result["afterRevision"] == result["beforeRevision"] + 1
    assert result["beforeTrackIds"] == ["art:track-one", "art:track-two"]
    assert result["afterTrackIds"] == ["art:track-two", "art:track-one"]
    assert result["afterTimingRevision"] == result["beforeTimingRevision"]


def test_editor_project_store_inactive_tool_projection_cannot_steal_selection() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-selection', duration: 10, result: { text: '', segments: [] }
} } });
const artState = {
  source: 'original',
  overlays: [{ id: 'art-one', text: '标题', start: 1, end: 3 }],
  timeline: { duration: 10, tracks: [{
    id: 'art:track', kind: 'art', clips: [{
      id: 'art:art-one', sourceId: 'art-one', start: 1, end: 3,
    }],
  }], selection: { clipId: 'art:art-one' } },
};
store.dispatch({ type: 'artStateChanged', payload: artState });
store.dispatch({ type: 'pipStateChanged', payload: {
  source: 'original',
  overlays: [{ id: 'pip-one', assetId: 'asset-one', start: 4, end: 6 }],
  timeline: { duration: 10, tracks: [{
    id: 'pip:track', kind: 'pip', clips: [{
      id: 'pip:pip-one', sourceId: 'pip-one', start: 4, end: 6,
    }],
  }] },
} });
store.dispatch({ type: 'activeToolChanged', payload: { tool: 'pip' } });
store.dispatch({
  type: 'selectionChanged',
  payload: { selection: { clipId: 'pip:pip-one' } },
});
const beforeInactive = store.getState();
store.dispatch({ type: 'artStateChanged', payload: artState });
const afterInactive = store.getState();
store.dispatch({ type: 'activeToolChanged', payload: { tool: 'art' } });
store.dispatch({
  type: 'selectionChanged',
  payload: { selection: { clipId: 'art:art-one' } },
});
store.dispatch({ type: 'artStateChanged', payload: {
  source: 'original', overlays: [],
  timeline: { duration: 10, tracks: [], selection: null },
} });
const afterActiveDelete = store.getState();
console.log(JSON.stringify({
  beforeInactiveSelection: beforeInactive.project.timeline.selection,
  afterInactiveSelection: afterInactive.project.timeline.selection,
  inactiveAcceptedRevision: afterInactive.revision,
  beforeInactiveRevision: beforeInactive.revision,
  afterActiveDeleteSelection: afterActiveDelete.project.timeline.selection,
}));
"""
    )

    assert result["beforeInactiveSelection"]["clipId"] == "pip:pip-one"
    assert result["afterInactiveSelection"]["clipId"] == "pip:pip-one"
    assert result["inactiveAcceptedRevision"] == result["beforeInactiveRevision"]
    assert result["afterActiveDeleteSelection"] is None


def test_editor_project_store_restores_versioned_art_draft_atomically() -> None:
    result = run_store_script(
        r"""
const store = projectStore.createStore({}, { timeline });
store.dispatch({ type: 'projectHydrated', payload: { job: {
  id: 'job-draft', status: 'completed', duration: 10, updatedAt: 'server-v1',
  result: { text: '文案', segments: [] },
  edit: { status: 'completed', outputDuration: 8, transcript: { text: '文案', segments: [] } },
} } });
const before = store.getState();
const art = { source: 'edited', overlays: [{
  id: 'stable-one', text: '重点', start: 1, end: 3,
  sourceStart: 1.5, sourceEnd: 3.5, color: '#FFD84D',
}] };
const artTimeline = { duration: 8, tracks: [{
  id: 'art:overlay:stable-one', kind: 'art', clips: [{
    id: 'art:stable-one', sourceId: 'stable-one', start: 1, end: 3,
  }],
}], selection: { clipId: 'art:stable-one' } };
const wrongVersion = store.dispatch({
  type: 'projectDraftRestored', payload: {
    jobId: 'job-draft', serverVersion: 'server-v0', art, timeline: artTimeline,
  },
});
const restored = store.dispatch({
  type: 'projectDraftRestored', payload: {
    jobId: 'job-draft', serverVersion: 'server-v1', art, timeline: artTimeline,
  },
});
const after = store.getState();
const echo = store.dispatch({
  type: 'projectDraftRestored', payload: {
    jobId: 'job-draft', serverVersion: 'server-v1', art, timeline: artTimeline,
  },
});
console.log(JSON.stringify({
  wrongVersion, restored, echo,
  beforeRevision: before.revision,
  beforeTimingRevision: before.timingRevision,
  revision: after.revision,
  timingRevision: after.timingRevision,
  source: after.project.art.source,
  overlay: after.project.art.overlays[0],
  selection: after.project.timeline.selection,
}));
"""
    )

    assert result["wrongVersion"]["accepted"] is False
    assert result["restored"]["accepted"] is True
    assert result["revision"] == result["beforeRevision"] + 1
    assert result["timingRevision"] == result["beforeTimingRevision"] + 1
    assert result["source"] == "edited"
    assert result["overlay"]["id"] == "stable-one"
    assert result["selection"]["clipId"] == "art:stable-one"
    assert result["selection"]["trackId"] == "art:overlay:stable-one"
    assert result["echo"]["accepted"] is False
