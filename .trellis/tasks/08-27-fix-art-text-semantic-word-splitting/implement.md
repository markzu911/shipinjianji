# Implementation Plan

1. Add failing backend tests for `update_transcript_track_text_for_segment()` using duration ratios that currently split “其实” and “该有的”; assert unchanged semantic runs retain cue ownership, full text is conserved, and cue timing/IDs/styles do not move.
2. Implement a deterministic cue-aware diff projection in `server/app.py`, feed it the updated segment's natural word boundaries, and replace whole-segment duration-ratio character redistribution. Keep the persisted `interrupted + retryable` art invalidation behavior unchanged.
3. Add failing ArtModel/ProjectStore tests reproducing `前文其 / 实该 / 有的后文结束` through source-midpoint and no-source/capacity paths, plus deletion, suppression, restore, repeated phrases and a fully edited fallback case.
4. Extend transcript character units with word/segment ownership and implement semantic-boundary projection/validation in `web/editor-art-model.js`. Preserve whole-track character conservation, stable cue IDs/styles and `_cutReconciliation` baseline synchronization.
5. Verify `EditorProjectStore` keeps timeline, preview and compose texts identical through text save, user transcript split, deletion, server echo and undo/restore; manual overlays and timing revisions remain unchanged except for real cut timing changes.
6. Extend the real browser edit -> split -> delete workflow with multi-character protected phrases and assert cue arrays, not only concatenated text. Confirm no base video `src/load()` churn and no external segmentation request.
7. Update frontend state, backend persistence and cross-layer specs with the single semantic-boundary contract and the prohibition on duration/midpoint character cutting.
8. Run focused validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_art_text_track.py tests/app/test_editor_project_store.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "art and (text or split or delete)"
node --check web/editor-art-model.js
node --check web/editor-project-store.js
```

9. Run full quality gates:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
git diff --check
py -3 ./.trellis/scripts/task.py validate .trellis/tasks/08-27-fix-art-text-semantic-word-splitting
```

10. Review the final diff for character conservation, semantic-boundary legality, repeated-text determinism, no external AI calls, no user data writes and no unrelated production/deployment changes.

## Verification Evidence (2026-08-27)

- Focused backend, ArtModel, ProjectStore and browser workflow regression: `87 passed, 37 deselected`.
- Full application regression: `480 passed`.
- Standalone browser regression: `48 passed`; the previously observed animation-geometry race did not recur.
- `node --check web/editor-art-model.js` and `node --check web/editor-project-store.js`: passed.
- `python -m compileall -q server`: passed.
- `git diff --check`: passed with only existing LF/CRLF conversion warnings.
- Trellis task context validation: passed (`implement.jsonl` 6 entries, `check.jsonl` 7 entries).
- Product code contains no new vocabulary-specific exception for the reported examples; tests cover them as regression evidence only.
- No external AI request, user-media read/write, production merge, deployment, push or commit was performed.

## Risky Files And Rollback Points

- `server/app.py`: text-save cue projection and art invalidation share one function; do not regress legal persisted subjob state.
- `web/editor-art-model.js`: shared cut-to-art reconciliation affects preview, timeline, compose and undo/restore atomically.
- `web/editor-project-store.js`: only change if baseline synchronization cannot be maintained inside existing merge/reconciliation paths.
- Browser fixtures/tests must use temporary seeded jobs and local request stubs; never read or mutate `data/jobs`, `data/history` or user media.
