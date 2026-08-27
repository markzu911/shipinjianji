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
            timeout=20,
        )
    except FileNotFoundError:
        pytest.skip("Node.js is required for editor art model tests.")
    return json.loads(result.stdout)


def test_editor_art_model_normalizes_all_templates_and_stable_ids():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
let overlays = [];
for (const name of Object.keys(model.DEFAULT_PALETTES)) {
  overlays.push(model.createOverlay(overlays, {
    text: name,
    start: 1,
    end: 2,
    artStyle: name,
  }, { duration: 8 }));
}
const restored = model.normalizeOverlay({
  ...overlays[0], id: 'server-stable', x: 2, y: -1,
}, { duration: 8 });
console.log(JSON.stringify({
  count: overlays.length,
  ids: overlays.map((item) => item.id),
  restored: { id: restored.id, x: restored.x, y: restored.y },
  palettes: Object.keys(model.DEFAULT_PALETTES),
}));
"""
    )

    assert payload["count"] == 11
    assert len(set(payload["ids"])) == 11
    assert payload["ids"][0] == "art-overlay-1"
    assert payload["ids"][-1] == "art-overlay-11"
    assert payload["restored"] == {"id": "server-stable", "x": 0.95, "y": 0.05}
    assert payload["palettes"] == [
        "impact",
        "neon",
        "metal",
        "sticker",
        "clean",
        "gradient",
        "comic",
        "ice",
        "ink",
        "ribbon",
        "luxury",
    ]


def test_editor_art_model_replaces_duplicate_requested_ids_with_stable_ids():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const first = model.createOverlay([], {
  id: 'segment-one', text: 'first', start: 0, end: 1,
}, { duration: 3 });
const second = model.createOverlay([first], {
  id: 'segment-one', text: 'second', start: 1, end: 2,
}, { duration: 3 });
console.log(JSON.stringify({ first: first.id, second: second.id }));
"""
    )

    assert payload == {"first": "segment-one", "second": "art-overlay-1"}


def test_editor_art_model_keeps_track_timing_when_shared_style_changes():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const cues = model.buildTranscriptTrack({
  trackId: 'full', fontSize: 54, cues: [
    { text: '第一段', start: 0.2, end: 1.2, sourceStart: 1.2, sourceEnd: 2.2 },
    { text: '第二段', start: 1.2, end: 2.4, sourceStart: 2.2, sourceEnd: 3.4 },
  ],
}, { artStyle: 'impact', color: '#FFD84D' }, [], { duration: 5 });
const cueEdited = model.updateOverlay(cues, cues[0].id, {
  text: '第一段改',
}, { duration: 5 });
const updated = model.updateOverlay(cues, cues[0].id, {
  artStyle: 'neon', color: '#A9E7CF', fontSize: 66, start: 3,
}, { duration: 5 });
const legacyCues = cues.map(({ characterTimings, ...cue }) => cue);
const legacyUpdated = model.updateOverlay(legacyCues, legacyCues[0].id, {
  fontSize: 62,
}, { duration: 5 });
const invariant = ({
  id, text, start, end, sourceStart, sourceEnd, characterTimings, timingRevision,
}) => ({
  id, text, start, end, sourceStart, sourceEnd, characterTimings,
  timingRevision: timingRevision ?? null,
});
const timeline = model.buildTimeline({ overlays: updated }, 5, {
  clipId: `art:${updated[0].id}`,
});
console.log(JSON.stringify({
  before: cues.map(invariant),
  after: updated.map((cue) => ({ ...invariant(cue), artStyle: cue.artStyle, fontSize: cue.fontSize })),
  cueEditedTexts: cueEdited.map((cue) => cue.text),
  legacyTimingPresence: legacyUpdated.map((cue) =>
    Object.prototype.hasOwnProperty.call(cue, 'characterTimings')
  ),
  tracks: timeline.tracks,
  selection: timeline.selection,
  removed: model.removeOverlay(updated, updated[0].id),
  error: model.validateOverlays(updated, 5),
}));
"""
    )

    assert [item["id"] for item in payload["before"]] == [
        item["id"] for item in payload["after"]
    ]
    assert payload["cueEditedTexts"] == ["第一段改", "第二段"]
    assert payload["legacyTimingPresence"] == [False, False]
    for before, after in zip(payload["before"], payload["after"], strict=True):
        assert after["start"] == before["start"]
        assert after["end"] == before["end"]
        assert after["sourceStart"] == before["sourceStart"]
        assert after["sourceEnd"] == before["sourceEnd"]
        assert after["characterTimings"] == before["characterTimings"]
        assert after["timingRevision"] == before["timingRevision"]
        assert after["artStyle"] == "neon"
        assert after["fontSize"] == 66
    assert len(payload["tracks"]) == 1
    assert len(payload["tracks"][0]["clips"]) == 2
    assert payload["selection"]["clipId"].startswith("art:art-full-")
    assert payload["removed"] == []
    assert payload["error"] == ""


def test_editor_art_model_groups_manual_and_ai_overlays_separately_from_transcript():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const manualOne = model.normalizeOverlay({
  id: 'manual-one', text: '手动一', start: 2, end: 4,
  sourceStart: 12, sourceEnd: 14, x: 0.2, y: 0.3,
}, { duration: 8 });
const confirmed = model.overlayFromSuggestion({
  draftId: 'ai-draft', accepted: true, position: 'top',
  text: 'AI 普通', start: 1, end: 3,
  sourceStart: 11, sourceEnd: 13, x: 0.4, y: 0.2,
}, [manualOne], { duration: 8 });
const manualTwo = model.normalizeOverlay({
  id: 'manual-two', text: '手动二', start: 4, end: 5,
  sourceStart: 14, sourceEnd: 15, x: 0.7, y: 0.8,
}, { duration: 8 });
const transcript = model.buildTranscriptTrack({
  trackId: 'full', cues: [
    { text: '文案一', start: 0, end: 1, sourceStart: 10, sourceEnd: 11 },
    { text: '文案二', start: 5, end: 6, sourceStart: 15, sourceEnd: 16 },
  ],
}, {}, [], { duration: 8 });
const overlays = [manualOne, transcript[0], confirmed, transcript[1], manualTwo];
const before = JSON.stringify(overlays);
const tracks = model.buildTimelineTracks(overlays);
console.log(JSON.stringify({
  before,
  after: JSON.stringify(overlays),
  confirmedId: confirmed.id,
  tracks,
}));
"""
    )

    assert payload["after"] == payload["before"]
    assert [(track["id"], track["name"]) for track in payload["tracks"]] == [
        ("art:manual", "手动艺术字"),
        ("art:transcript:full", "视频文案艺术字"),
    ]
    manual_track, transcript_track = payload["tracks"]
    assert [clip["sourceId"] for clip in manual_track["clips"]] == [
        payload["confirmedId"],
        "manual-one",
        "manual-two",
    ]
    assert [clip["id"] for clip in manual_track["clips"]] == [
        f"art:{payload['confirmedId']}",
        "art:manual-one",
        "art:manual-two",
    ]
    assert [clip["sourceId"] for clip in transcript_track["clips"]] == [
        "art-full-1",
        "art-full-2",
    ]
    assert all(
        clip["payload"]["trackType"] == "transcript"
        and clip["payload"]["trackId"] == "full"
        for clip in transcript_track["clips"]
    )
    assert [
        (clip["payload"]["sourceStart"], clip["payload"]["sourceEnd"])
        for clip in manual_track["clips"]
    ] == [(11, 13), (12, 14), (14, 15)]


def test_editor_art_model_matches_compose_constraints_and_strips_ai_draft_state():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const manual = model.normalizeOverlay({
  id: 'manual-one', text: '重点！', start: 0.2, end: 1.2,
  x: 0, y: 1, strokeWidth: 15.5, letterSpacing: -4,
  animation: { type: 'character-bounce' },
}, { duration: 2 });
const confirmed = model.overlayFromSuggestion({
  draftId: 'ai-draft-1', accepted: true, position: 'top',
  text: '推荐', start: 0.3, end: 1, x: 0.5, y: 0.2,
}, [manual], { duration: 2 });
console.log(JSON.stringify({
  manual,
  error: model.validateOverlays([manual, confirmed], 2),
  confirmedKeys: Object.keys(confirmed).sort(),
}));
"""
    )

    assert payload["manual"]["x"] == 0.05
    assert payload["manual"]["y"] == 0.95
    assert payload["manual"]["strokeWidth"] == 12
    assert payload["manual"]["letterSpacing"] == 0
    assert len(payload["manual"]["characterTimings"]) == 3
    assert payload["error"] == ""
    assert "draftId" not in payload["confirmedKeys"]
    assert "accepted" not in payload["confirmedKeys"]
    assert "position" not in payload["confirmedKeys"]


def test_editor_art_model_matches_phrase_characters_and_nearest_occurrence():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const transcript = { segments: [
  {
    text: '先说保留重点，再说保留重点。', start: 1, end: 5,
    sourceStart: 5, sourceEnd: 9,
    words: [
      { text: '先说', start: 1, end: 1.4, sourceStart: 5, sourceEnd: 5.4 },
      { text: '保留重点', start: 1.4, end: 2.2, sourceStart: 5.4, sourceEnd: 6.2 },
      { text: '，再说', start: 2.2, end: 3.2, sourceStart: 6.2, sourceEnd: 7.2 },
      { text: '保留重点。', start: 3.2, end: 4.2, sourceStart: 7.2, sourceEnd: 8.2 },
    ],
  },
] };
console.log(JSON.stringify({
  first: model.matchTranscriptPhrase(transcript, '保留重点', 1.5),
  nearest: model.matchTranscriptPhrase(transcript, '保留重点', 3.6),
  insideWord: model.matchTranscriptPhrase(transcript, '留重', 1.7),
  legacyAsr: model.matchTranscriptPhrase({ segments: [{
    text: '旧数据', start: 0, end: 1,
    asrWords: [{ text: '旧数据', start: 0.2, end: 0.8 }],
  }] }, '数据', 0.5),
  irregular: model.matchTranscriptPhrase({ segments: [{
    text: '甲乙丙', start: 1, end: 3, sourceStart: 10, sourceEnd: 14,
    words: [{
      text: '甲乙丙', start: 1, end: 3, sourceStart: 10, sourceEnd: 14,
      characterTimings: [
        { start: 1, end: 1.2 },
        { start: 1.2, end: 2.7 },
        { start: 2.7, end: 3 },
      ],
    }],
  }] }, '乙', 1.5),
}));
"""
    )

    assert payload["first"] == {
        "start": 1.4,
        "end": 2.2,
        "sourceStart": 5.4,
        "sourceEnd": 6.2,
    }
    assert payload["nearest"] == {
        "start": 3.2,
        "end": 4.2,
        "sourceStart": 7.2,
        "sourceEnd": 8.2,
    }
    assert payload["insideWord"] == {
        "start": 1.6,
        "end": 2.0,
        "sourceStart": 5.6,
        "sourceEnd": 6.0,
    }
    assert payload["legacyAsr"] == {
        "start": 0.4,
        "end": 0.8,
        "sourceStart": None,
        "sourceEnd": None,
    }
    assert payload["irregular"] == {
        "start": 1.2,
        "end": 2.7,
        "sourceStart": 10.4,
        "sourceEnd": 13.4,
    }


def test_editor_art_model_reconciles_cut_characters_cues_and_anchored_overlays():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const overlay = (value) => model.normalizeOverlay(value, { duration: 6 });
const base = { source: 'original', overlays: [
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
  overlay({
    id: 'manual', text: '乙', start: 1, end: 2,
    sourceStart: 1, sourceEnd: 2,
  }),
  overlay({
    id: 'partial', text: '范围', start: 0.5, end: 1.5,
    sourceStart: 0.5, sourceEnd: 1.5,
  }),
  overlay({ id: 'custom', text: '标题', start: 0.2, end: 0.8 }),
] };
const originalCut = { ranges: [], sourceDuration: 6, duration: 6 };
const transcript = (parts) => ({ segments: parts.map(([text, start, end, sourceStart, sourceEnd]) => ({
  text, start, end, sourceStart, sourceEnd,
  words: [{ text, start, end, sourceStart, sourceEnd }],
})) });
const crossCut = {
  ranges: [{ start: 1, end: 3 }], sourceDuration: 6, duration: 4,
  transcript: transcript([
    ['甲', 0, 1, 0, 1],
    ['丁', 1, 2, 3, 4],
  ]),
};
const cross = model.reconcileArtWithCut(base, originalCut, crossCut).art;
const singleCharacterCut = {
  ranges: [{ start: 1, end: 2 }], sourceDuration: 6, duration: 5,
  transcript: transcript([
    ['甲', 0, 1, 0, 1],
    ['丙丁', 1, 3, 2, 4],
  ]),
};
const singleCharacter = model.reconcileArtWithCut(
  base,
  originalCut,
  singleCharacterCut,
).art;
const fullCueCut = {
  ranges: [{ start: 2, end: 4 }], sourceDuration: 6, duration: 4,
  transcript: transcript([['甲乙', 0, 2, 0, 2]]),
};
const fullCue = model.reconcileArtWithCut(base, originalCut, fullCueCut).art;
const restored = model.reconcileArtWithCut(cross, crossCut, {
  ranges: [], sourceDuration: 6, duration: 6,
  transcript: transcript([['甲乙丙丁', 0, 4, 0, 4]]),
}).art;
console.log(JSON.stringify({
  cross: cross.overlays.map(({ id, text, start, end, characterTimings }) => ({
    id, text, start, end, characterTimings,
  })),
  crossSuppressed: cross.suppressedOverlays.map(({ id }) => id),
  singleCharacter: singleCharacter.overlays
    .filter(item => item.trackType === 'transcript')
    .map(({ id, text, start, end }) => ({ id, text, start, end })),
  fullCueActive: fullCue.overlays.map(({ id }) => id),
  fullCueSuppressed: fullCue.suppressedOverlays.map(({ id }) => id),
  restored: restored.overlays.map(({ id, text, start, end }) => ({ id, text, start, end })),
}));
"""
    )

    assert payload["cross"] == [
        {
            "id": "cue-one",
            "text": "甲",
            "start": 0,
            "end": 1,
            "characterTimings": [{"start": 0, "end": 1}],
        },
        {
            "id": "custom",
            "text": "标题",
            "start": 0.2,
            "end": 0.8,
            "characterTimings": [
                {"start": 0.2, "end": 0.5},
                {"start": 0.5, "end": 0.8},
            ],
        },
        {
            "id": "partial",
            "text": "范围",
            "start": 0.5,
            "end": 1,
            "characterTimings": [
                {"start": 0.5, "end": 0.75},
                {"start": 0.75, "end": 1},
            ],
        },
        {
            "id": "cue-two",
            "text": "丁",
            "start": 1,
            "end": 2,
            "characterTimings": [{"start": 1, "end": 2}],
        },
    ]
    assert payload["crossSuppressed"] == ["manual"]
    assert payload["singleCharacter"] == [
        {"id": "cue-one", "text": "甲", "start": 0, "end": 1},
        {"id": "cue-two", "text": "丙丁", "start": 1, "end": 3},
    ]
    assert payload["fullCueActive"] == [
        "cue-one",
        "custom",
        "partial",
        "manual",
    ]
    assert payload["fullCueSuppressed"] == ["cue-two"]
    assert payload["restored"] == [
        {"id": "cue-one", "text": "甲乙", "start": 0, "end": 2},
        {"id": "custom", "text": "标题", "start": 0.2, "end": 0.8},
        {"id": "partial", "text": "范围", "start": 0.5, "end": 1.5},
        {"id": "manual", "text": "乙", "start": 1, "end": 2},
        {"id": "cue-two", "text": "丙丁", "start": 2, "end": 4},
    ]


def test_editor_art_model_conserves_track_characters_across_source_anchor_drift():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const cue = (id, text, start, end) => model.normalizeOverlay({
  id, text, start, end, sourceStart: start, sourceEnd: end,
  trackType: 'transcript', trackId: 'full',
}, { duration: 30 });
const base = { source: 'original', overlays: [
  cue('cue-dan', '但后来我才发现', 14.13, 15.45),
  cue('cue-ni', '你能看到的选项', 15.81, 17.0),
  cue('cue-gai', '该有的想法', 17.39, 18.4),
  cue('cue-ren', '人这辈子最难突破', 22.19, 24.3),
] };
const segment = (text, start, end, sourceStart = start, sourceEnd = end) => ({
  text, start, end, sourceStart, sourceEnd,
  words: [{ text, start, end, sourceStart, sourceEnd }],
});
const previousCut = { ranges: [], sourceDuration: 30, duration: 30 };
const nextCut = {
  ranges: [{ start: 18.4, end: 21.9 }], sourceDuration: 30, duration: 26.5,
  transcript: { segments: [
    segment('但后来我才发现', 13.90, 15.40),
    segment('你能看到的选项', 15.55, 17.00),
    segment('该有的想法', 17.19, 18.39),
    segment('人这辈子最难突破', 18.40, 20.80, 21.90, 24.30),
  ] },
};
const result = model.reconcileArtWithCut(base, previousCut, nextCut).art;
const transcriptCues = result.overlays.filter(item => item.trackId === 'full');
console.log(JSON.stringify({
  texts: transcriptCues.map(item => item.text),
  timingCounts: transcriptCues.map(item => item.characterTimings.length),
  concatenated: transcriptCues.map(item => item.text).join(''),
  expected: nextCut.transcript.segments.map(item => item.text).join(''),
  suppressed: result.suppressedOverlays.map(item => item.id),
}));
"""
    )

    assert payload["texts"] == [
        "但后来我才发现",
        "你能看到的选项",
        "该有的想法",
        "人这辈子最难突破",
    ]
    assert payload["timingCounts"] == [7, 7, 5, 8]
    assert payload["concatenated"] == payload["expected"]
    assert payload["suppressed"] == []


def test_editor_art_model_keeps_mixed_anchor_track_order_for_capacity_fallback():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const base = { source: 'original', overlays: [
  model.normalizeOverlay({
    id: 'legacy-no-source', text: '甲乙', start: 0, end: 2,
    trackType: 'transcript', trackId: 'full',
  }, { duration: 4 }),
  model.normalizeOverlay({
    id: 'source-anchored', text: '丙丁', start: 2, end: 4,
    sourceStart: 8, sourceEnd: 10,
    trackType: 'transcript', trackId: 'full',
  }, { duration: 4 }),
] };
const cut = {
  ranges: [], sourceDuration: 10, duration: 4,
  transcript: { segments: [{
    text: '甲乙丙丁', start: 0, end: 4,
    words: [{ text: '甲乙丙丁', start: 0, end: 4 }],
  }] },
};
const result = model.reconcileArtWithCut(base, cut, cut).art;
console.log(JSON.stringify(result.overlays.map(item => ({
  id: item.id,
  text: item.text,
  timingCount: item.characterTimings.length,
}))));
"""
    )

    assert payload == [
        {"id": "legacy-no-source", "text": "甲乙", "timingCount": 2},
        {"id": "source-anchored", "text": "丙丁", "timingCount": 2},
    ]


def test_editor_art_model_missing_transcript_projection_preserves_retained_cues():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const cue = (id, text, start, end) => model.normalizeOverlay({
  id, text, start, end, sourceStart: start, sourceEnd: end,
  trackType: 'transcript', trackId: 'full',
}, { duration: 4 });
const base = { source: 'original', overlays: [
  cue('retained', '保留文案', 0, 2),
  cue('deleted', '删除文案', 2, 4),
] };
const previous = { ranges: [], sourceDuration: 4, duration: 4 };
const next = { ranges: [{ start: 2, end: 4 }], sourceDuration: 4, duration: 2 };
const reconcile = transcript => model.reconcileArtWithCut(
  base, previous, { ...next, ...(transcript === undefined ? {} : { transcript }) },
).art;
const result = reconcile(undefined);
const emptyObject = reconcile({});
const emptySegments = reconcile({ segments: [] });
const explicitEmpty = reconcile({ text: '', segments: [] });
console.log(JSON.stringify({
  active: result.overlays.map(item => ({
    id: item.id, text: item.text, start: item.start, end: item.end,
    timingCount: item.characterTimings.length,
  })),
  suppressed: result.suppressedOverlays.map(item => item.id),
  emptyObjectActive: emptyObject.overlays.map(item => item.id),
  emptySegmentsActive: emptySegments.overlays.map(item => item.id),
  explicitEmptyActive: explicitEmpty.overlays.map(item => item.id),
  explicitEmptySuppressed: explicitEmpty.suppressedOverlays.map(item => item.id),
}));
"""
    )

    assert payload == {
        "active": [
            {
                "id": "retained",
                "text": "保留文案",
                "start": 0,
                "end": 2,
                "timingCount": 4,
            }
        ],
        "suppressed": ["deleted"],
        "emptyObjectActive": ["retained"],
        "emptySegmentsActive": ["retained"],
        "explicitEmptyActive": [],
        "explicitEmptySuppressed": ["retained", "deleted"],
    }


def test_editor_art_model_invalid_transcript_timing_still_conserves_current_text():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const cue = (id, text, start, end) => model.normalizeOverlay({
  id, text, start, end, sourceStart: start, sourceEnd: end,
  trackType: 'transcript', trackId: 'full',
}, { duration: 4 });
const base = { source: 'original', overlays: [
  cue('first', '旧文', 0, 2),
  cue('second', '案字', 2, 4),
] };
const currentText = '当前文案仍保留';
const result = model.reconcileArtWithCut(
  base,
  { ranges: [], sourceDuration: 4, duration: 4 },
  {
    ranges: [], sourceDuration: 4, duration: 4,
    transcript: { text: currentText, segments: [{ text: currentText }] },
  },
).art;
const cues = result.overlays.filter(item => item.trackId === 'full');
const timings = cues.flatMap(item => item.characterTimings);
console.log(JSON.stringify({
  text: cues.map(item => item.text).join(''),
  timingCount: timings.length,
  timingsValid: timings.every((timing, index) =>
    Number.isFinite(timing.start) && Number.isFinite(timing.end) &&
    timing.end > timing.start &&
    (!index || timing.start >= timings[index - 1].end - 0.000001)),
  sourceRanges: cues.map(item => [item.sourceStart, item.sourceEnd]),
  suppressed: result.suppressedOverlays.map(item => item.id),
}));
"""
    )

    assert payload == {
        "text": "当前文案仍保留",
        "timingCount": 7,
        "timingsValid": True,
        "sourceRanges": [[0, 2], [2, 4]],
        "suppressed": [],
    }


def test_editor_art_model_reconciliation_preserves_word_spaces_without_punctuation():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const base = { source: 'original', overlays: [model.normalizeOverlay({
  id: 'cue-english', text: 'hello world', start: 0, end: 2,
  sourceStart: 0, sourceEnd: 2, trackType: 'transcript', trackId: 'full',
}, { duration: 2 })] };
const cut = {
  ranges: [], sourceDuration: 2, duration: 2,
  transcript: { segments: [{
    text: 'hello world!', start: 0, end: 2, sourceStart: 0, sourceEnd: 2,
    words: [
      { text: 'hello ', start: 0, end: 1, sourceStart: 0, sourceEnd: 1 },
      { text: 'world!', start: 1, end: 2, sourceStart: 1, sourceEnd: 2 },
    ],
  }] },
};
const reconciled = model.reconcileArtWithCut(base, cut, cut).art.overlays[0];
console.log(JSON.stringify({
  text: reconciled.text,
  timingCount: reconciled.characterTimings.length,
  timingStart: reconciled.characterTimings[0].start,
  timingEnd: reconciled.characterTimings.at(-1).end,
}));
"""
    )

    assert payload == {
        "text": "hello world",
        "timingCount": 10,
        "timingStart": 0,
        "timingEnd": 2,
    }


def test_editor_art_renderer_formats_layout_and_character_effects():
    payload = run_node(
        r"""
const model = require('./web/editor-art-model.js');
const renderer = require('./web/editor-art-renderer.js');
class ClassList {
  constructor() { this.values = new Set(); }
  toggle(name, enabled) { enabled ? this.values.add(name) : this.values.delete(name); }
  add(name) { this.values.add(name); }
}
function element(tag = 'div') {
  return {
    tag, classList: new ClassList(), attributes: {}, children: [], textContent: '',
    style: { values: {}, setProperty(name, value) { this.values[name] = value; } },
    setAttribute(name, value) { this.attributes[name] = value; },
    replaceChildren(...children) { this.children = children; },
    ownerDocument: documentStub,
  };
}
const documentStub = {
  createTextNode: (text) => ({ type: 'text', text }),
  createElement: (tag) => element(tag),
};
const horizontal = model.formatText({ text: '测试文字换行', direction: 'horizontal', charsPerLine: 3, letterSpacing: 0 });
const vertical = model.formatText({ text: '甲乙丙丁', direction: 'vertical', charsPerLine: 2, lineSpacing: 2 });
const node = element();
renderer.renderCharacters(node, '重点', {
  color: '#FFD84D', secondaryColor: '#FFFFFF', textColorMode: 'center-highlight',
  animation: { type: 'character-bounce', duration: .56, stagger: .07, amplitude: .18 },
  characterLayout: { type: 'staggered', rotationPattern: [-2, 3], verticalOffsetPattern: [.02, -.02] },
  characterTimings: [{ start: 1, end: 1.4 }, { start: 1.4, end: 1.8 }],
  start: 1, end: 2,
}, 1.2, true);
console.log(JSON.stringify({
  horizontal, vertical,
  hasEffect: node.classList.values.has('has-character-effect'),
  childCount: node.children.length,
  classes: node.children.map((child) => [...child.classList.values]),
  labels: node.attributes,
}));
"""
    )

    assert payload["horizontal"] == "测试文\n字换行"
    assert payload["vertical"] == "丙\u200a甲\n丁\u200a乙"
    assert payload["hasEffect"] is True
    assert payload["childCount"] == 2
    assert all("is-character-bounce" in item for item in payload["classes"])
    assert all("is-character-staggered" in item for item in payload["classes"])
    assert payload["labels"]["aria-label"] == "重点"
