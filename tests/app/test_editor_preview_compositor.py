from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def run_preview_script(body: str) -> dict[str, object]:
    script = rf"""
const globalListeners = new Map();
global.addEventListener = (type, listener) => {{
  if (!globalListeners.has(type)) globalListeners.set(type, new Set());
  globalListeners.get(type).add(listener);
}};
global.removeEventListener = (type, listener) => globalListeners.get(type)?.delete(listener);
function emitGlobal(type, event) {{
  for (const listener of [...(globalListeners.get(type) || [])]) listener(event);
}}

class ClassList {{
  constructor(node) {{ this.node = node; }}
  values() {{ return new Set(String(this.node.className || '').split(/\s+/).filter(Boolean)); }}
  write(values) {{ this.node.className = [...values].join(' '); }}
  add(...names) {{ const values = this.values(); names.forEach((name) => values.add(name)); this.write(values); }}
  remove(...names) {{ const values = this.values(); names.forEach((name) => values.delete(name)); this.write(values); }}
  contains(name) {{ return this.values().has(name); }}
  toggle(name, force) {{
    const values = this.values();
    const enabled = force === undefined ? !values.has(name) : Boolean(force);
    if (enabled) values.add(name); else values.delete(name);
    this.write(values);
    return enabled;
  }}
}}

class Style {{
  setProperty(name, value) {{ this[name] = String(value); }}
  removeProperty(name) {{ delete this[name]; }}
}}

let createCount = 0;
class NodeStub {{
  constructor(tagName = '') {{
    this.tagName = String(tagName).toUpperCase();
    this.nodeType = this.tagName ? 1 : 3;
    this.children = [];
    this.parentNode = null;
    this.dataset = {{}};
    this.style = new Style();
    this.className = '';
    this.classList = new ClassList(this);
    this.attributes = {{}};
    this.listeners = new Map();
    this.hidden = false;
    this.clientWidth = 0;
    this.clientHeight = 0;
    this.offsetWidth = 120;
    this.offsetHeight = 40;
    this.paused = true;
    this.ended = false;
    this.readyState = this.tagName === 'VIDEO' ? 1 : 0;
    this.duration = this.tagName === 'VIDEO' ? 2 : Number.NaN;
    this.currentTime = 0;
    this.playCalls = 0;
    this.pauseCalls = 0;
    this._text = '';
  }}
  set textContent(value) {{
    this._text = String(value ?? '');
    for (const child of this.children) child.parentNode = null;
    this.children = [];
  }}
  get textContent() {{
    if (this.nodeType === 3) return this._text;
    return this.children.length ? this.children.map((child) => child.textContent).join('') : this._text;
  }}
  append(...nodes) {{
    for (const node of nodes) {{
      if (!node) continue;
      node.remove?.();
      node.parentNode = this;
      this.children.push(node);
    }}
  }}
  replaceChildren(...nodes) {{
    for (const child of this.children) child.parentNode = null;
    this.children = [];
    this._text = '';
    this.append(...nodes);
  }}
  remove() {{
    if (!this.parentNode) return;
    const index = this.parentNode.children.indexOf(this);
    if (index >= 0) this.parentNode.children.splice(index, 1);
    this.parentNode = null;
  }}
  setAttribute(name, value) {{ this.attributes[name] = String(value); }}
  removeAttribute(name) {{ delete this.attributes[name]; }}
  addEventListener(type, listener) {{
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type).add(listener);
  }}
  removeEventListener(type, listener) {{ this.listeners.get(type)?.delete(listener); }}
  emit(type, event = {{}}) {{
    event.currentTarget = this;
    event.target ||= this;
    for (const listener of [...(this.listeners.get(type) || [])]) listener(event);
  }}
  querySelector(selector) {{ return this.querySelectorAll(selector)[0] || null; }}
  querySelectorAll(selector) {{
    const matches = [];
    const match = (node) => {{
      if (selector.startsWith('.')) return node.classList.contains(selector.slice(1));
      if (selector === '[data-pip-resize]') return Boolean(node.dataset.pipResize);
      if (selector === '[data-overlay-id]') return node.dataset.overlayId !== undefined;
      if (selector === '[data-picture-id]') return node.dataset.pictureId !== undefined;
      return node.tagName === selector.toUpperCase();
    }};
    const visit = (node) => {{
      for (const child of node.children || []) {{
        if (match(child)) matches.push(child);
        visit(child);
      }}
    }};
    visit(this);
    return matches;
  }}
  getBoundingClientRect() {{
    const parentWidth = this.parentNode?.clientWidth || this.parentNode?.parentNode?.clientWidth || 1000;
    const parentHeight = this.parentNode?.clientHeight || this.parentNode?.parentNode?.clientHeight || 500;
    const percent = (value, size, fallback) => String(value || '').endsWith('%')
      ? Number.parseFloat(value) * size / 100
      : Number.parseFloat(value) || fallback;
    const width = percent(this.style.width, parentWidth, this.clientWidth || this.offsetWidth);
    const height = this.clientHeight || this.offsetHeight;
    const centerX = percent(this.style.left, parentWidth, parentWidth / 2);
    const centerY = percent(this.style.top, parentHeight, parentHeight / 2);
    return {{ left: centerX - width / 2, top: centerY - height / 2, width, height }};
  }}
  setPointerCapture() {{}}
  releasePointerCapture() {{}}
  play() {{ this.paused = false; this.playCalls += 1; return Promise.resolve(); }}
  pause() {{ this.paused = true; this.pauseCalls += 1; }}
}}

const documentStub = {{
  createElement(tagName) {{ createCount += 1; const node = new NodeStub(tagName); node.ownerDocument = documentStub; return node; }},
  createTextNode(value) {{ const node = new NodeStub(); node._text = String(value); return node; }},
}};
global.document = documentStub;

const resizeObservers = [];
global.ResizeObserver = class {{
  constructor(callback) {{ this.callback = callback; this.disconnected = false; resizeObservers.push(this); }}
  observe(target) {{ this.target = target; }}
  disconnect() {{ this.disconnected = true; }}
  trigger() {{ this.callback([{{ target: this.target }}]); }}
}};

const preview = require('./web/editor-preview-compositor.js');
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
        pytest.skip("Node.js is required for the preview compositor tests.")
    return json.loads(completed.stdout)


def test_preview_compositor_renders_semantic_layers_and_reuses_nodes() -> None:
    result = run_preview_script(
        r"""
const host = new NodeStub('div');
host.ownerDocument = documentStub;
host.clientWidth = 1000;
host.clientHeight = 500;
const baseVideo = { paused: false, ended: false, videoWidth: 1000 };
let currentTime = 0.5;
const frameListeners = new Set();
const stateListeners = new Set();
const mediaController = {
  currentEditedTime: () => currentTime,
  video: () => baseVideo,
  subscribeFrame(listener) { frameListeners.add(listener); return () => frameListeners.delete(listener); },
  subscribeState(listener) { stateListeners.add(listener); return () => stateListeners.delete(listener); },
};
const calls = { select: [], move: [], resize: [] };
const compositor = preview.createCompositor({
  root: host,
  mediaController,
  onSelect: (payload) => calls.select.push(payload),
  onMove: (payload) => calls.move.push(payload),
  onResize: (payload) => calls.resize.push(payload),
});
function makeFrame(revision, selected = 'art:headline') {
  const artState = {
    source: 'original',
    overlays: [
      {
        id: 'headline', text: '甲乙丙丁', start: 0, end: 1,
        x: 0.5, y: 0.5, font: 'bold', fontSize: 40,
        color: '#FFFFFF', secondaryColor: '#FF0000',
        strokeColor: '#111111', strokeWidth: 2, artStyle: 'neon',
        textColorMode: 'center-highlight',
        animation: { type: 'character-bounce', duration: 0.5, amplitude: 0.2 },
        characterLayout: { type: 'staggered', rotationPattern: [-2, 2], verticalOffsetPattern: [0.1, -0.1] },
        characterTimings: [
          { start: 0, end: 0.2 }, { start: 0.2, end: 0.4 },
          { start: 0.4, end: 0.6 }, { start: 0.6, end: 0.8 },
        ],
      },
      { id: 'later', text: '稍后', start: 1, end: 2, x: 0.4, y: 0.8 },
    ],
  };
  Object.defineProperty(artState, 'overlayHtml', { get() { throw new Error('HTML must not be read'); } });
  return {
    revision,
    timingRevision: 7,
    preview: {
      art: artState,
      pip: {
        source: 'art',
        overlays: [
          { id: 'still', assetId: 'image-1', start: 0, end: 1, x: 0.2, y: 0.2, width: 0.3 },
          { id: 'motion', assetId: 'video-1', start: 1, end: 3, x: 0.8, y: 0.3, width: 0.3 },
          { id: 'missing', assetId: 'missing-1', start: 0, end: 4, x: 0.5, y: 0.5, width: 0.3 },
        ],
        assets: [
          { id: 'image-1', type: 'image', assetUrl: '/image.png', text: '静态素材' },
          { id: 'video-1', type: 'video', assetUrl: '/motion.mp4', text: '动态素材', status: 'completed' },
        ],
      },
    },
    timeline: {
      selection: { clipId: selected },
      tracks: [
        { kind: 'art', clips: [
          { id: 'art:headline', sourceId: 'headline' },
          { id: 'art:later', sourceId: 'later' },
        ] },
        { kind: 'pip', clips: [
          { id: 'pip:still', sourceId: 'still' },
          { id: 'pip:motion', sourceId: 'motion' },
        ] },
      ],
    },
  };
}

compositor.render(makeFrame(1));
const artLayer = host.children[0];
const pipLayer = host.children[1];
const headline = artLayer.children.find((node) => node.dataset.overlayId === 'headline');
const later = artLayer.children.find((node) => node.dataset.overlayId === 'later');
const still = pipLayer.children.find((node) => node.dataset.pictureId === 'still');
const motion = pipLayer.children.find((node) => node.dataset.pictureId === 'motion');
const initialCreateCount = createCount;
const initial = {
  revision: host.dataset.projectRevision,
  timingRevision: host.dataset.timingRevision,
  artCount: artLayer.children.length,
  pipCount: pipLayer.children.length,
  headlineVisible: !headline.hidden,
  laterHidden: later.hidden,
  stillVisible: !still.hidden,
  motionHidden: motion.hidden,
  selected: headline.classList.contains('is-selected'),
  characterCount: headline.children.length,
  bounceCount: headline.children.filter((node) => node.classList.contains('is-character-bounce')).length,
  colors: headline.children.map((node) => node.style.color),
  fontSize: headline.style.fontSize,
  stroke: headline.style.webkitTextStroke,
  stillTag: still.children[0].tagName,
  motionTag: motion.children[0].tagName,
  missingSkipped: !pipLayer.children.some((node) => node.dataset.pictureId === 'missing'),
};

compositor.render(makeFrame(2));
const reused = {
  sameArtNode: headline === artLayer.children.find((node) => node.dataset.overlayId === 'headline'),
  samePipNode: motion === pipLayer.children.find((node) => node.dataset.pictureId === 'motion'),
  noNewNodes: createCount === initialCreateCount,
  revision: host.dataset.projectRevision,
};

currentTime = 1.5;
for (const listener of frameListeners) listener({ editedTime: currentTime, playing: true });
const atMotion = {
  headlineHidden: headline.hidden,
  laterVisible: !later.hidden,
  stillHidden: still.hidden,
  motionVisible: !motion.hidden,
  localTime: motion.children[0].currentTime,
  playing: !motion.children[0].paused,
};
currentTime = 3;
for (const listener of frameListeners) listener({ editedTime: currentTime, playing: true });
const endExclusive = { hidden: motion.hidden, paused: motion.children[0].paused };

compositor.render(makeFrame(3, 'pip:motion'));
const selectionChanged = {
  artSelected: headline.classList.contains('is-selected'),
  pipSelected: motion.classList.contains('is-selected'),
};

console.log(JSON.stringify({ initial, reused, atMotion, endExclusive, selectionChanged }));
"""
    )

    assert result["initial"] == {
        "revision": "1",
        "timingRevision": "7",
        "artCount": 2,
        "pipCount": 2,
        "headlineVisible": True,
        "laterHidden": True,
        "stillVisible": True,
        "motionHidden": True,
        "selected": True,
        "characterCount": 4,
        "bounceCount": 4,
        "colors": ["#FF0000", "#FFFFFF", "#FFFFFF", "#FF0000"],
        "fontSize": "40px",
        "stroke": "2px #FFFFFF",
        "stillTag": "IMG",
        "motionTag": "VIDEO",
        "missingSkipped": True,
    }
    assert result["reused"] == {
        "sameArtNode": True,
        "samePipNode": True,
        "noNewNodes": True,
        "revision": "2",
    }
    assert result["atMotion"] == {
        "headlineHidden": True,
        "laterVisible": True,
        "stillHidden": True,
        "motionVisible": True,
        "localTime": 0.5,
        "playing": True,
    }
    assert result["endExclusive"] == {"hidden": True, "paused": True}
    assert result["selectionChanged"] == {
        "artSelected": False,
        "pipSelected": True,
    }


def test_preview_compositor_pointer_callbacks_resize_and_cleanup() -> None:
    result = run_preview_script(
        r"""
const host = new NodeStub('div');
host.ownerDocument = documentStub;
host.clientWidth = 1000;
host.clientHeight = 500;
const baseVideo = { paused: true, ended: false, videoWidth: 1000 };
let currentTime = 0.5;
const frameListeners = new Set();
const stateListeners = new Set();
const mediaController = {
  currentEditedTime: () => currentTime,
  video: () => baseVideo,
  subscribeFrame(listener) { frameListeners.add(listener); return () => frameListeners.delete(listener); },
  subscribeState(listener) { stateListeners.add(listener); return () => stateListeners.delete(listener); },
};
const calls = { select: [], move: [], resize: [] };
const compositor = preview.createCompositor({
  root: host,
  mediaController,
  onSelect: (payload) => calls.select.push(payload),
  onMove: (payload) => calls.move.push(payload),
  onResize: (payload) => calls.resize.push(payload),
});
const frame = {
  revision: 4,
  timingRevision: 2,
  preview: {
    art: { overlays: [{ id: 'art-1', text: '移动', start: 0, end: 2, x: 0.5, y: 0.5, fontSize: 40 }] },
    pip: {
      overlays: [{ id: 'pip-1', assetId: 'asset-1', start: 0, end: 2, x: 0.5, y: 0.5, width: 0.3 }],
      assets: [{ id: 'asset-1', type: 'image', assetUrl: '/asset.png' }],
    },
  },
  timeline: {
    selection: null,
    tracks: [
      { kind: 'art', clips: [{ id: 'art:art-1', sourceId: 'art-1' }] },
      { kind: 'pip', clips: [{ id: 'pip:pip-1', sourceId: 'pip-1' }] },
    ],
  },
};
compositor.render(frame);
const art = host.children[0].children[0];
const pip = host.children[1].children[0];
const pointer = (pointerId, clientX, clientY, target) => ({
  pointerId, clientX, clientY, button: 0, target,
  preventDefault() {}, stopPropagation() {},
});

art.emit('pointerdown', pointer(1, 500, 250, art));
emitGlobal('pointermove', pointer(1, 700, 350, art));
emitGlobal('pointerup', pointer(1, 700, 350, art));

const handle = pip.children.find((node) => node.dataset.pipResize === 'e');
pip.emit('pointerdown', pointer(2, 500, 250, handle));
emitGlobal('pointermove', pointer(2, 1500, 250, handle));
const liveWidth = Number.parseFloat(pip.style.width) / 100;
emitGlobal('pointerup', pointer(2, 1500, 250, handle));

host.clientWidth = 500;
resizeObservers[0].trigger();
const resizedFont = art.style.fontSize;

art.emit('pointerdown', pointer(3, 500, 250, art));
const listenersBeforeDestroy = [...globalListeners.values()].reduce((sum, listeners) => sum + listeners.size, 0);
compositor.destroy();
const listenersAfterDestroy = [...globalListeners.values()].reduce((sum, listeners) => sum + listeners.size, 0);

console.log(JSON.stringify({
  calls,
  liveWidth,
  resizedFont,
  listenersBeforeDestroy,
  listenersAfterDestroy,
  observerDisconnected: resizeObservers[0].disconnected,
  frameSubscribers: frameListeners.size,
  stateSubscribers: stateListeners.size,
  layersAfterDestroy: host.children.length,
  revisionRemoved: host.dataset.projectRevision === undefined,
  renderAfterDestroy: compositor.render(frame),
}));
"""
    )

    assert result["calls"]["select"] == [
        {"kind": "art", "id": "art-1", "clipId": "art:art-1"},
        {"kind": "pip", "id": "pip-1", "clipId": "pip:pip-1"},
        {"kind": "art", "id": "art-1", "clipId": "art:art-1"},
    ]
    assert result["calls"]["move"] == [
        {
            "kind": "art",
            "id": "art-1",
            "clipId": "art:art-1",
            "x": 0.7,
            "y": 0.7,
        }
    ]
    assert result["calls"]["resize"][0]["kind"] == "pip"
    assert result["calls"]["resize"][0]["width"] > 1
    assert result["liveWidth"] > 1
    assert result["resizedFont"] == "20px"
    assert result["listenersBeforeDestroy"] == 3
    assert result["listenersAfterDestroy"] == 0
    assert result["observerDisconnected"] is True
    assert result["frameSubscribers"] == 0
    assert result["stateSubscribers"] == 0
    assert result["layersAfterDestroy"] == 0
    assert result["revisionRemoved"] is True
    assert result["renderAfterDestroy"] is False


def test_preview_compositor_does_not_consume_html_snapshots_or_mutate_store() -> None:
    source = (ROOT / "web" / "editor-preview-compositor.js").read_text(
        encoding="utf-8"
    )

    assert "innerHTML" not in source
    assert "overlayHtml" not in source
    assert ".dispatch(" not in source
    assert ".getState(" not in source
    assert "Math.min(PIP_MIN_WIDTH" not in source
