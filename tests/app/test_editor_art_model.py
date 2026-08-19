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
const updated = model.updateOverlay(cues, cues[0].id, {
  text: '第一段改', artStyle: 'neon', color: '#A9E7CF', fontSize: 66, start: 3,
}, { duration: 5 });
const timeline = model.buildTimeline({ overlays: updated }, 5, {
  clipId: `art:${updated[0].id}`,
});
console.log(JSON.stringify({
  before: cues.map(({ id, text, start, end, sourceStart, sourceEnd }) => ({ id, text, start, end, sourceStart, sourceEnd })),
  after: updated.map(({ id, text, start, end, sourceStart, sourceEnd, artStyle, fontSize }) => ({ id, text, start, end, sourceStart, sourceEnd, artStyle, fontSize })),
  tracks: timeline.tracks,
  selection: timeline.selection,
  error: model.validateOverlays(updated, 5),
}));
"""
    )

    assert [item["id"] for item in payload["before"]] == [
        item["id"] for item in payload["after"]
    ]
    assert payload["after"][0]["text"] == "第一段改"
    assert payload["after"][1]["text"] == payload["before"][1]["text"]
    for before, after in zip(payload["before"], payload["after"], strict=True):
        assert after["start"] == before["start"]
        assert after["end"] == before["end"]
        assert after["sourceStart"] == before["sourceStart"]
        assert after["sourceEnd"] == before["sourceEnd"]
        assert after["artStyle"] == "neon"
        assert after["fontSize"] == 66
    assert len(payload["tracks"]) == 1
    assert len(payload["tracks"][0]["clips"]) == 2
    assert payload["selection"]["clipId"].startswith("art:art-full-")
    assert payload["error"] == ""


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
