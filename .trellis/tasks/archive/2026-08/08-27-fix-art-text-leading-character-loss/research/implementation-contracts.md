# Implementation Contracts

This task-local summary narrows the applicable project specs so sub-agent context is not truncated. The source contracts remain authoritative.

## Media And Timeline

Source: `.trellis/spec/backend/media-and-timeline.md`.

- Semantic retained characters determine identity; physical delete ranges and source anchors only retime retained characters.
- `start/end` are edited time and `sourceStart/sourceEnd` are original-media anchors. They must remain distinct.
- Valid word/character timing is authoritative for transcript art. Quiet/VAD data must not delete, compress or reorder characters.
- Full transcript art preview and compose must consume the same normalized cues.
- Editable splits remain visible as separate transcript runs. Missing/invalid editable mapping falls back without deleting characters.
- A physical projection that collapses or shifts a character still has to emit that semantic character with finite positive timing.

## Frontend State

Source: `.trellis/spec/frontend/architecture-and-state.md`.

- `EditorProjectStore` is the cross-tool state authority. One `CUT_TIMING_CHANGED` must atomically update cut, art timeline, preview and compose.
- Text-only transcript changes increment semantic revision but not `timingRevision`; existing art/PiP timing and source anchors stay stable.
- Pure structure changes must not invoke art/PiP cut reconciliation. Real ranges/duration changes may reconcile once.
- Local draft persistence and server responses cannot overwrite a newer Store snapshot. A later equivalent action is a no-op.
- The base video source, playback position and tool roots must not reload for text/split/delete state projection.

## Cross-Layer Review

Source: `.trellis/spec/guides/cross-layer-thinking-guide.md`.

- Trace one semantic character through retained transcript -> ArtModel -> ProjectStore -> public timeline -> preview -> compose.
- Verify both local temporary projection and canonical server projection, including legal anchor drift in both directions.
- Assert one source of truth and one normalized output rather than independent UI fixes.

## Testing

Sources: `.trellis/spec/testing/index.md` and `.trellis/spec/testing/browser-workflows.md`.

- Art track or public timeline changes require ArtModel, ProjectStore, TimelineController and browser coverage.
- Browser verification must use the real edit/split/delete workflow and assert no base video `src/load()` churn.
- Do not use real `data/jobs`, history or user media as writable fixtures. Local real-job checks are read-only evidence only.
- Preview and compose cue text must be compared from the same Store revision.
- Run targeted tests first, then complete `tests/app`, JavaScript syntax checks and `git diff --check`.

## Persistence

Source: `.trellis/spec/backend/persistence-and-jobs.md`.

- Every non-null art subtask stored in `project-state.json` must have a legal terminal/running/interrupted status; `null` is not a valid status.
- Editing transcript text invalidates the old rendered art output without scheduling a worker, so it must use a legal non-running retryable state rather than `queued`.
- A successful text-save snapshot must remain valid and overwritable by the immediately following split/delete requests.
- Post-save `currentSegments` and `currentEditableSegments` must describe the same text revision before any character selection is canonicalized; refreshed source segments invalidate cached character units.
