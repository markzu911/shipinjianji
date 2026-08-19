from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def run_pip_model_script(body: str) -> dict[str, object]:
    script = f"""
const pip = require('./web/editor-pip-model.js');
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
        pytest.skip("Node.js is required for the shared PiP model tests.")
    return json.loads(completed.stdout)


def test_pip_model_separates_assets_from_enabled_overlays_and_has_stable_ids() -> None:
    result = run_pip_model_script(
        r"""
const assets = pip.normalizeAssets([
  { id: 'image-1', type: 'image', source: 'art', imageUrl: '/one.png', start: 1, end: 3 },
  { id: 'video-1', type: 'video', source: 'art', status: 'processing' },
  { id: 'other-source', type: 'image', source: 'edited', imageUrl: '/other.png' },
], { source: 'art' });
let project = pip.normalizeProject({ source: 'art', assets, overlays: [] }, { duration: 8 });
project = pip.setAssetEnabled(project, 'image-1', true, { source: 'art', duration: 8 });
const pendingAttempt = pip.setAssetEnabled(project, 'video-1', true, { source: 'art', duration: 8 });
const timeline = pip.buildTimeline(project, 8, { clipId: 'pip:image-1' });
console.log(JSON.stringify({
  assetIds: project.assets.map(item => item.id),
  overlayIds: project.overlays.map(item => item.assetId),
  pendingOverlayIds: pendingAttempt.overlays.map(item => item.assetId),
  clipId: timeline.tracks[0].clips[0].id,
  selection: timeline.selection,
}));
"""
    )

    assert result == {
        "assetIds": ["image-1", "video-1"],
        "overlayIds": ["image-1"],
        "pendingOverlayIds": ["image-1"],
        "clipId": "pip:image-1",
        "selection": {"clipId": "pip:image-1"},
    }


def test_pip_model_preserves_unlimited_finite_width_and_rejects_invalid_draft() -> None:
    result = run_pip_model_script(
        r"""
const assets = [{
  id: 'wide', type: 'image', source: 'art', status: 'completed', assetUrl: '/wide.png',
  start: 1, end: 4,
}];
const valid = pip.validateDraftOverlays([{
  assetId: 'wide', start: 1, end: 4, x: 0.5, y: 0.5, width: 1.75,
}], { source: 'art', duration: 8, assets });
const infinite = pip.validateDraftOverlays([{
  assetId: 'wide', start: 1, end: 4, x: 0.5, y: 0.5, width: Infinity,
}], { source: 'art', duration: 8, assets });
const unknown = pip.validateDraftOverlays([{
  assetId: 'missing', start: 1, end: 4, x: 0.5, y: 0.5, width: 1.75,
}], { source: 'art', duration: 8, assets });
const disabled = pip.validateDraftOverlays([{
  assetId: 'wide', start: 1, end: 4, x: 0.5, y: 0.5, width: 1.75,
  enabled: false,
}], { source: 'art', duration: 8, assets });
const duplicate = pip.validateDraftOverlays([
  { assetId: 'wide', start: 1, end: 4, x: 0.5, y: 0.5, width: 1.75 },
  { assetId: 'wide', start: 4, end: 6, x: 0.5, y: 0.5, width: 2 },
], { source: 'art', duration: 8, assets });
const coerced = pip.validateDraftOverlays([{
  assetId: 'wide', start: '1', end: 4, x: 0.5, y: 0.5, width: 1.75,
}], { source: 'art', duration: 8, assets });
const incompleteAnchors = pip.validateDraftOverlays([{
  assetId: 'wide', start: 1, end: 4, sourceStart: 1,
  x: 0.5, y: 0.5, width: 1.75,
}], { source: 'art', duration: 8, assets });
console.log(JSON.stringify({
  valid, infinite, unknown, disabled, duplicate, coerced, incompleteAnchors,
}));
"""
    )

    assert result["valid"][0]["width"] == 1.75
    assert result["valid"][0]["id"] == "wide"
    assert result["infinite"] is None
    assert result["unknown"] is None
    assert result["disabled"] is None
    assert result["duplicate"] is None
    assert result["coerced"] is None
    assert result["incompleteAnchors"] is None


def test_pip_tool_owns_only_inspector_and_effect_orchestration() -> None:
    source = (ROOT / "web" / "editor-pip-tool.js").read_text(encoding="utf-8")

    assert "PipTool.mount" not in source
    assert "sessionStorage" not in source
    assert "localStorage" not in source
    assert "postMessage" not in source
    assert 'addEventListener("message"' not in source
    assert "EditorTimeline.createStore" not in source
    assert "toDataURL" not in source
    assert "initialize()" not in source
    assert 'size.type = "number"' in source
    assert "size.max" not in source
    assert "commands.generateCurrentPreview" in source
    assert "const unsubscribeProject = services.project.subscribe" in source
    assert "const unsubscribeFrame = services.media.subscribeFrame" in source
    assert "unsubscribeProject();" in source
    assert "unsubscribeFrame();" in source
