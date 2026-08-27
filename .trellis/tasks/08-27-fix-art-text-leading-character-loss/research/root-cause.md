# Root Cause: transcript art cue leading characters disappear after split/delete

## Evidence

- Screenshot: `C:/Users/jiadi/AppData/Local/Temp/codex-clipboard-64d1890e-e833-46c8-a585-2584a81569a7.png`.
- Reproduction source was read-only from local job snapshots and `GET /cut-draft`; no job, history, media or browser state was modified.
- The screenshot's first-screen mismatch is systematic:
  - retained `但后来我才发现` -> art `后来我才发现`
  - retained `你能看到的选项` -> art `能看到的选项`
  - retained `该有的想法` -> art `有的想法`
  - retained `人这辈子最难突破...` -> art `这辈子最难突破...`

## Confirmed Cause

`web/editor-art-model.js:435` reconciles every transcript cue independently. At `web/editor-art-model.js:467`, a next-transcript character is retained only when its source midpoint falls inside the old cue's `sourceStart/sourceEnd`.

That predicate incorrectly treats physical source anchors as character identity. User-created splits expose a legitimate projection change:

| Cue | Canonical old cue source start | Temporary local transcript source start | Current output |
| --- | ---: | ---: | --- |
| 但后来我才发现 | 14.13 | 13.90 | 后来我才发现 |
| 你能看到的选项 | 15.81 | 15.55 | 能看到的选项 |
| 该有的想法 | 17.39 | 17.19 | 有的想法 |
| 人这辈子最难突破... | 22.19 | 21.90 | 这辈子最难突破... |

Running the current ArtModel against those values produces the screenshot's missing prefixes. The characters still exist in `nextCut.transcript`; their midpoints merely precede the old acoustically aligned cue start.

## Trigger Sequence

1. Text save refreshes the canonical server retained projection.
2. User clicks transcript split. `web/app.js:1420` invalidates `serverRetainedProjection`, so the cut UI temporarily derives a semantic/local projection from the new editable segments.
3. User deletes the split segment. The cut timing action reconciles existing art cues against that local projection.
4. Per-cue midpoint filtering drops characters that moved across old physical cue boundaries.
5. The normalized server projection arrives with the same ranges/duration. `web/editor-project-store.js:422` excludes transcript anchors from `cutTimingSignature()`, so there is no second reconciliation to recover the missing characters.

## Why Existing Guards Miss It

- `server/app.py:8488` verifies initial generated cue text against collected transcript text, so initial generation is complete.
- `server/app.py:6418` builds the retained transcript without losing semantic characters.
- Existing ArtModel tests use identical source anchors in old and next projections; they cover deletion through a cue but not legal anchor drift for the same retained characters.
- Existing Store tests verify transcript-only updates do not retime art, but do not execute text edit + split + delete while an existing transcript track is active.

## Required Prevention

- Reconcile transcript overlays per track with one monotonic character assignment.
- Treat source anchors as boundary preferences only. First/last and inter-cue drift must never leave an unassigned next-transcript character.
- Assert track-wide content conservation after every cut reconciliation.
- Keep visible cue text and `_cutReconciliation` baseline on the same text version after a transcript edit.

## Secondary Workflow Blocker

The real browser sequence exposed a separate persistence defect after the first text-save PUT. `update_transcript_track_text_for_segment()` sets `job.art.status = None` when the rendered art video becomes stale. `ProjectRepository._validate_job_shape()` requires every non-null art state to use `_SUBJOB_STATUSES`, so the resulting snapshot is invalid and the next split PUT refuses to overwrite it. The stale render state must use the existing retryable non-running `interrupted` representation while preserving editable overlays.

The same workflow exposed a second frontend state defect: the text-save handler refreshed `currentEditableSegments` but left `currentSegments` on the pre-edit transcript. The next split/delete passed its new selection through `canonicalizeTextSelectionRange()` backed by stale character timings, expanding a middle-paragraph deletion through the remainder. Every authoritative post-save job read must refresh both layers and invalidate the character-unit cache before deriving cut state.
