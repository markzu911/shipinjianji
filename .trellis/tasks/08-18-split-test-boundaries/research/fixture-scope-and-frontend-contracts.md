# Research: Fixture scope and frontend contract decomposition

- Query: Identify order/module-global assumptions, confirm `tests/app/conftest.py` scope relative to the Mac packaging test, and decompose the 1,037-line frontend omnibus test without weakening assertions.
- Scope: mixed
- Date: 2026-08-18

## Findings

### Fixture scope and Mac packaging isolation

- `isolated_jobs` is currently an autouse fixture at `tests/test_app.py:20-51`. Before every application test it captures 11 runtime model/URL settings, captures DashScope client URLs, monkeypatches `DATA_DIR` to that test's `tmp_path`, removes three API-key environment variables, and clears `JOBS` plus `JOB_FILES`. After the test it restores model/URL settings and DashScope client URLs. Pytest's `monkeypatch` fixture restores `DATA_DIR`, environment variables, and per-test object patches automatically.
- `sample_video` at `tests/test_app.py:54-82` builds an isolated one-second 320x180 H.264/AAC sample under `tmp_path`. It is reused across history, upload, cut, art, picture-in-picture, transcript-track, and media-probe tests; moving it once to `tests/app/conftest.py` avoids duplication.
- Pytest searches `conftest.py` fixtures upward from the collected test's directory, not sideways into sibling directories. Therefore `tests/app/conftest.py` applies to `tests/app/test_*.py` and descendants, but not to sibling `tests/test_build_mac_package.py` at `tests/test_build_mac_package.py:1`.
- The Mac packaging test imports only `Path` and `tools.build_mac_package` (`tests/test_build_mac_package.py:1-3`) and takes only builtin `tmp_path` and `monkeypatch` (`tests/test_build_mac_package.py:6-9`). With the fixture located under `tests/app/`, `isolated_jobs` is neither discovered nor imported for that test. This is the intended boundary; placing the fixture in `tests/conftest.py` would make the autouse fixture affect the Mac test and import `server.app` unnecessarily.
- Environment version checked locally: pytest 9.1.1. Reference: pytest documentation, "Fixture availability" and `conftest.py` directory scope, <https://docs.pytest.org/en/stable/reference/fixtures.html#fixture-availability>.

### Order and global-state assumptions

- No test assigns directly to an `app_module` attribute. Global substitutions use `monkeypatch.setattr` (examples: `ENV_FILE` at `tests/test_app.py:142`, `Recognition` at `tests/test_app.py:2970`, `Generation` at `tests/test_app.py:3205`, `httpx.post` at `tests/test_app.py:6830`, and `run_ffmpeg` at `tests/test_app.py:9349`) and therefore unwind after each test.
- Many tests intentionally populate `app_module.JOBS`/`JOB_FILES` (first examples at `tests/test_app.py:338-339`; later cut/art/pip/composition examples at `tests/test_app.py:6298-6345`, `tests/test_app.py:6612-6633`, `tests/test_app.py:6992-7005`, and `tests/test_app.py:7394-7448`). They do not consume records created by a prior test. The autouse fixture clears both dictionaries before each test under `JOBS_LOCK`, so moving it intact preserves order independence.
- Model settings tests mutate module-level model names through the API (`tests/test_app.py:136-185`). The fixture's explicit `runtime_setting_names` restoration is essential because these assignments are performed by production code and are not themselves monkeypatched. Do not replace the fixture with only `JOBS.clear()`.
- DashScope URL mutation has two layers: module constants and `app_module.dashscope.base_*` fields (`tests/test_app.py:175-181`). The fixture restores both; dropping the client-field restoration would introduce cross-module order dependence after the settings module runs.
- API key changes use `monkeypatch.setenv`/`delenv` (settings at `tests/test_app.py:111-112`, ASR at `tests/test_app.py:2923`, PIP at `tests/test_app.py:6829`), so they are per-test. External requests remain test-owned mocks and must not be generalized into an autouse network mock because negative credential tests intentionally validate early rejection.
- `_build_track_words` is the only module-level helper (`tests/test_app.py:8310-8318`) and is used only by three transcript-track tests (`tests/test_app.py:8323`, `tests/test_app.py:8351`, `tests/test_app.py:8393`). Move it into `test_art_text_track.py`; it has no state.
- The current repository has no root `conftest.py`, `pytest_plugins`, or pytest configuration file. There is no hidden fixture import path or configured collection ordering to preserve.

### Frontend omnibus test: current shape

`test_frontend_assets_are_versioned_and_not_cached` starts at `tests/test_app.py:658`. It opens one `TestClient` and fetches 15 resources at lines 659-674, then executes 830 `assert` statements across unrelated main editor, editor-suite, art, PIP, template-library, and font-manager contracts. The assertions naturally form nine independent blocks below.

Use a small private helper in `test_frontend_contracts.py`, such as `_fetch_frontend_assets(*paths)`, that opens one `TestClient` and returns responses keyed by path. Each test should request only the pages/scripts it asserts against. Keep every original assertion expression verbatim; repeated GETs are acceptable and safer than a module-scoped response cache because the autouse application isolation is function-scoped.

Do not use a module-scoped fixture for the omnibus responses: `/api/art-templates` reads `DATA_DIR`, while the function-scoped `isolated_jobs` fixture supplies the safe temporary `DATA_DIR`. A module-scoped asset fixture would be created outside that function-scoped isolation.

### Exact assertion partition

The following partition covers all 830 original `assert` nodes exactly once. The line blocks also keep every temporary slice variable with the assertions that consume it.

| Replacement test | Original assertion lines | Assert count | Required resources |
| --- | --- | ---: | --- |
| `test_shared_frontend_assets_are_versioned_and_not_cached` | 676-689, 833-841, 1191-1193, 1689-1694 | 30 | `/`, `/styles.css`, `/app.js`, `/ui-feedback.js`, `/timeline-model.js`, `/art-text.js`, `/picture-in-picture.js` |
| `test_editor_suite_frontend_contracts` | 690-832, 1031-1042, 1325-1328 | 114 | `/`, `/styles.css`, `/editor-suite.js` |
| `test_upload_and_history_frontend_contracts` | 842-894 | 53 | `/`, `/styles.css`, `/app.js` |
| `test_cut_timeline_and_draft_frontend_contracts` | 895-1030, 1043-1046 | 133 | `/`, `/styles.css`, `/app.js`, `/editor-suite.js` |
| `test_cut_range_and_segment_frontend_contracts` | 1047-1190, 1194-1215, 1469-1481 | 135 | `/`, `/styles.css`, `/app.js` |
| `test_art_text_frontend_contracts` | 1216-1324, 1329-1468, 1482-1501 | 204 | `/art-text`, `/art-text.js`, `/styles.css`, `/editor-suite.js` |
| `test_picture_in_picture_frontend_contracts` | 1502-1627 | 111 | `/picture-in-picture`, `/picture-in-picture.js`, `/styles.css`, `/editor-suite.js`, `/art-text.js` |
| `test_art_template_library_frontend_contracts` | 1628-1676 | 38 | `/fonts`, `/art-template-library.js`, `/api/art-templates`, `/art-text.js` |
| `test_font_manager_frontend_contracts` | 1677-1688 | 12 | `/font-manager`, `/font-manager.js` |

The old resource-fetch block at lines 659-674 is not an assertion and should be replaced by targeted helper calls. No response should be fetched from production `DATA_DIR`; all tests still run under `isolated_jobs`.

Important cross-block placements:

- Shared feedback assertions at lines 838-840 intentionally verify `window.appGeneration?.show` in all three feature scripts; keep them together in the shared-assets test rather than duplicating them in three modules.
- Cut/audio source-string assertions at lines 1469-1481 occur physically inside the art portion of the old function but concern `app.js` retained-range protection; move them to the cut range/segment test.
- Editor-suite save/history assertions at lines 1325-1328 remain editor-suite contracts, not art-page contracts.
- PIP/editor-suite cross-message assertions at lines 1556, 1563, and 1626 remain in the PIP contract test because that test observes both ends of the resize/selection contract.
- Final obsolete-style prohibitions at lines 1689-1694 are global stylesheet assertions and belong in the shared-assets test, not the font-manager test.

### Mechanical completeness checks

Before deleting `tests/test_app.py`, run a one-time AST inventory against the old file or the committed baseline and compare names with the destination tree:

```powershell
py -3 -c "import ast,pathlib; p=pathlib.Path('tests/test_app.py'); t=ast.parse(p.read_text(encoding='utf-8')); print('\n'.join(n.name for n in t.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')))"
```

After migration:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_settings.py
# Repeat the second command for every tests/app/test_*.py module.
.\.venv\Scripts\python.exe -m pytest -q tests/test_build_mac_package.py --setup-show
.\.venv\Scripts\python.exe -m pytest -q
```

Expected collection math: the original application suite has 167 nodes. Replacing one omnibus node with nine nodes yields 175 application nodes; adding the unchanged Mac packaging test yields 176 total collected nodes. A lower count indicates a lost test/decorator. Keep both parameterization decorators with their destination functions.

To enforce the no-oversized-test acceptance criterion mechanically, parse destination test functions with `ast` and fail if `end_lineno - lineno + 1 > 300`. To enforce exact migration, compare the set of 163 unchanged test function names plus the nine replacement names against collected node base names; parameterized node suffixes must be normalized before comparison.

## Files Found

- `tests/test_app.py`: 164 application test functions, both shared fixtures, and one track helper.
- `tests/test_build_mac_package.py`: one independent packaging-data isolation test using only builtin fixtures.
- `.trellis/spec/testing/index.md`: test isolation, external-request mocking, real-media, and order-independence rules.
- `.trellis/spec/guides/project-overview.md`: current monolith/test ownership map.

## Related Specs

- `.trellis/spec/testing/index.md` requires temporary data roots, mocked external AI/HTTP, real short media for rendering, and restoration of `JOBS`, caches, model settings, and thread-local/global state.
- `.trellis/spec/guides/cross-layer-thinking-guide.md` identifies message origin validation and timeline ownership as static frontend contract concerns; keeping the editor-suite, art, and PIP source assertions separate makes these failures diagnosable.

## Caveats / Not Found

- Static source/HTML assertions are legitimate here only for version/cache, DOM/ARIA, script-reference, and message-safety contracts. The existing Node-backed tests at `tests/test_app.py:1697-2428` already cover observable behavior and should remain intact.
- `isolated_jobs` clears `JOBS`/`JOB_FILES` before, not after, each test. This is sufficient for independence because every application test receives the fixture; retain the pre-test clear and lock. Adding post-test clear is optional cleanup but is a behavioral change to the fixture and unnecessary for this migration.
- `--setup-show` output is the practical post-migration confirmation that the Mac packaging test does not load `isolated_jobs`; this cannot be executed until `tests/app/conftest.py` exists.
