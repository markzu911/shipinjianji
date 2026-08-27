# Implementation Contracts

This task-local summary narrows the applicable project specs for Phase 2 context injection. Source specs remain authoritative.

## Frontend State

Source: `.trellis/spec/frontend/architecture-and-state.md`.

- `EditorProjectStore` owns cross-tool project state. One `CUT_TIMING_CHANGED` must atomically update cut, art timeline, public preview and compose.
- Current transcript characters are semantic identity. Physical source anchors only order, retime and project those characters.
- Text-only updates synchronize visible transcript cue text and `_cutReconciliation` baseline without changing `timingRevision` or unrelated tool state.
- Full transcript art synchronization operates once per `trackId`; manual art overlays remain on the independent anchored-overlay path.
- Public timeline, preview and compose consume the same normalized Store frame. Equivalent server echoes cannot reapply a destructive partition.

## Backend Persistence And Text Save

Sources: `.trellis/spec/backend/persistence-and-jobs.md` and `.trellis/spec/backend/media-and-timeline.md`.

- `segments[].words` is the preferred natural-word timing layer; fall back per segment only when it is absent or invalid.
- Text save may change transcript cue text but must not move existing cue `start/end/sourceStart/sourceEnd`.
- Persisted art invalidation remains `status="interrupted"`, `retryable=True`, `outputUrl=None`; do not restore illegal `null` or workerless `queued` states.
- Source and edited time remain distinct. Timing cannot decide whether a semantic character exists or authorize a cut inside a protected semantic unit.
- Initial art generation and final composition must conserve the current transcript characters and use normalized cue arrays.
- Consecutive text/split/delete writes must leave a repository-valid snapshot that can be loaded and overwritten again.

## Cross-Layer Boundary

Source: `.trellis/spec/guides/cross-layer-thinking-guide.md`.

- Trace one character through updated source segments -> persisted art cue -> Store reconciliation -> public timeline/preview -> compose.
- Treat semantic identity, semantic cue partition and physical timing as separate authorities.
- The current semantic projection must be refreshed atomically across source segments, editable segments, boundaries, caches and Store state.
- Do not fix one renderer or UI list independently; normalize at the shared model/Store boundary.

## Testing

Sources: `.trellis/spec/testing/index.md` and `.trellis/spec/testing/browser-workflows.md`.

- Art track reconciliation changes require ArtModel, ProjectStore, timeline/compose and real browser workflow coverage.
- Tests must assert both concatenated character conservation and individual cue arrays; a complete but semantically broken partition is a failure.
- Browser coverage uses temporary seeded jobs, mocks external services, checks edit -> split -> delete -> undo/restore, and asserts no base video `src/load()` churn.
- Run targeted tests first, then full `tests/app`, full browser tests, JavaScript syntax checks, Trellis validation and `git diff --check`.
- Never read or mutate real `data/jobs`, `data/history`, user media, `.env` credentials or external model endpoints in tests.

