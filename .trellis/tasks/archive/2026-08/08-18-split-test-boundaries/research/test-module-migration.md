# Research: Test module migration

- Query: Provide the implementation-ready module map for splitting `tests/test_app.py` without changing behavior.
- Scope: internal
- Date: 2026-08-18

## Findings

### Baseline

- `tests/test_app.py` has 164 `test_*` functions and collects 167 nodes after parameterization.
- `tests/test_build_mac_package.py` adds one node; repository baseline is 168 collected tests.
- The only oversized function is `test_frontend_assets_are_versioned_and_not_cached` at `tests/test_app.py:658-1694` (1,037 lines, 830 `assert` nodes).

### Thirteen target modules

Each original test belongs to exactly one row. Multiple ranges mean a late test is moved back to its actual feature owner.

| Target | Original line range(s) | Functions | First test | Last test |
| --- | --- | ---: | --- | --- |
| `tests/app/test_settings.py` | 85-305 | 8 | `test_health_reports_media_tools` | `test_model_settings_page_is_available` |
| `tests/app/test_maintenance_history.py` | 308-655, 9568-9572 | 9 | `test_job_cleanup_removes_only_stale_inactive_job_directories` | `test_missing_job_returns_404` |
| `tests/app/test_frontend_contracts.py` | 658-2562 | 7 original functions | `test_frontend_assets_are_versioned_and_not_cached` | `test_douyin_preview_is_inline_only` |
| `tests/app/test_asset_libraries.py` | 2565-2885 | 8 | `test_art_template_library_upload_rename_render_and_delete` | `test_font_library_rejects_non_font_upload` |
| `tests/app/test_transcription_suggestions.py` | 2888-3855 | 16 | `test_transcript_is_normalized_to_simplified_chinese` | `test_no_speech_detection_ignores_short_conversational_pauses` |
| `tests/app/test_cut_draft.py` | 3858-5124 | 23 | `test_transcript_word_can_be_corrected_without_changing_timestamps` | `test_cut_draft_alignment_without_asr_words_falls_back_to_semantic_range` |
| `tests/app/test_cut_acoustic_boundaries.py` | 5127-6156, 9575-9618 | 24 | `test_shared_acoustic_boundary_removes_tail_inside_raw_ge_yi_token` | `test_retained_transcript_maps_audio_quiet_ranges_to_edited_timeline` |
| `tests/app/test_cut_rendering.py` | 6159-6606, 9564-9565, 9718-9739 | 8 | `test_retained_transcript_uses_edited_video_timeline` | `test_cut_render_normalizes_output_audio` |
| `tests/app/test_art_text_api.py` | 6609-6675, 7653-7880 | 6 | `test_art_text_can_use_original_video_without_cut` | `test_ai_art_suggestion_endpoint_uses_original_video_and_can_be_cleared` |
| `tests/app/test_composition.py` | 6678-6713, 7344-7650 | 4 | `test_original_art_and_picture_in_picture_are_blocked_after_cut_starts` | `test_failed_preview_composition_removes_job_working_directory` |
| `tests/app/test_picture_in_picture.py` | 6716-7341 | 12 | `test_picture_in_picture_writes_editable_prompt_from_selected_text` | `test_picture_in_picture_overlay_accepts_live_retimed_range` |
| `tests/app/test_art_text_track.py` | 7883-8961, 9621-9715 | 25 | `test_art_text_formats_horizontal_and_vertical_layouts` | `test_static_transcript_overlays_share_segment_audio_alignment` |
| `tests/app/test_art_text_rendering.py` | 8964-9561 | 14 | `test_balanced_multiline_art_text_renders_with_uniform_line_heights` | `test_art_text_layer_is_scaled_into_video_safe_area` |

Function-by-function names and exact imports are recorded in `research/test-split-migration-matrix.md`.

### Shared fixture and helper placement

- Move `isolated_jobs` unchanged from `tests/test_app.py:20-51` to `tests/app/conftest.py`.
- Move `sample_video` unchanged from `tests/test_app.py:54-82` to the same `conftest.py`.
- Required conftest imports: `subprocess`, `Path`, `pytest`, and `server.app as app_module`.
- `tests/app/conftest.py` applies only to tests under `tests/app/`. It is not discovered for sibling `tests/test_build_mac_package.py`, so the autouse `isolated_jobs` fixture does not import or mutate application state during the Mac packaging test.
- Move stateless `_build_track_words` (`tests/test_app.py:8310-8318`) into `test_art_text_track.py`; its only callers are at lines 8323, 8351, and 8393.
- No test directly assigns an `app_module` attribute. Production globals are either reset by `isolated_jobs` (`JOBS`, `JOB_FILES`, runtime model/URL settings, DashScope URLs) or patched with pytest `monkeypatch`. Keep the fixture body intact to preserve module-order independence.

### Frontend omnibus split

Replace the single function at lines 658-1694 with nine tests. Preserve every assertion expression verbatim and use a small function-scoped helper that fetches only requested paths with `TestClient`; do not cache responses at module scope because `/api/art-templates` depends on the function-scoped temporary `DATA_DIR`.

| Replacement test | Original assertion lines | Assertions |
| --- | --- | ---: |
| `test_shared_frontend_assets_are_versioned_and_not_cached` | 676-689, 833-841, 1191-1193, 1689-1694 | 30 |
| `test_editor_suite_frontend_contracts` | 690-832, 1031-1042, 1325-1328 | 114 |
| `test_upload_and_history_frontend_contracts` | 842-894 | 53 |
| `test_cut_timeline_and_draft_frontend_contracts` | 895-1030, 1043-1046 | 133 |
| `test_cut_range_and_segment_frontend_contracts` | 1047-1190, 1194-1215, 1469-1481 | 135 |
| `test_art_text_frontend_contracts` | 1216-1324, 1329-1468, 1482-1501 | 204 |
| `test_picture_in_picture_frontend_contracts` | 1502-1627 | 111 |
| `test_art_template_library_frontend_contracts` | 1628-1676 | 38 |
| `test_font_manager_frontend_contracts` | 1677-1688 | 12 |

The counts total 830. The old resource-fetch block at lines 659-674 is replaced by targeted helper calls and contains no assertions. Replacing one collected node with nine makes the expected post-split total 176 nodes: 175 application nodes plus one Mac packaging node.

### Machine completeness checks

Capture the original function inventory before removal:

```powershell
py -3 -c "import ast,pathlib; t=ast.parse(pathlib.Path('tests/test_app.py').read_text(encoding='utf-8')); print('\n'.join(n.name for n in t.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')))"
```

After migration, collect and run each boundary independently:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
Get-ChildItem tests/app/test_*.py | ForEach-Object { .\.venv\Scripts\python.exe -m pytest -q $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
.\.venv\Scripts\python.exe -m pytest -q tests/test_build_mac_package.py --setup-show
.\.venv\Scripts\python.exe -m pytest -q
```

Verify no test function exceeds 300 lines:

```powershell
@'
import ast
from pathlib import Path
oversized = []
for path in Path("tests/app").glob("test_*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            size = node.end_lineno - node.lineno + 1
            if size > 300:
                oversized.append((str(path), node.name, size))
assert not oversized, oversized
'@ | py -3 -
```

Preserve both parameterization decorators at `tests/test_app.py:5245` and `tests/test_app.py:8213`; otherwise collection silently drops three cases.

## Related Specs

- `.trellis/spec/testing/index.md`
- `.trellis/spec/guides/project-overview.md`
- `.trellis/spec/guides/code-reuse-thinking-guide.md`

## Caveats / Not Found

- There is no `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, root `conftest.py`, or `pytest_plugins` declaration; default pytest discovery and directory-scoped conftest lookup apply.
- Do not add `tests/app/__init__.py` unless an importable test-helper package is deliberately introduced; it is unnecessary for collection.
- `--setup-show` can confirm Mac fixture isolation only after `tests/app/conftest.py` exists.
