# Technical Design

## Scope

Repair the two synchronization boundaries that can corrupt an already valid transcript art track:

- backend text-save projection in `server/app.py`;
- frontend cut reconciliation in `web/editor-art-model.js` and its Store integration tests.

Initial AI/local art-text generation remains authoritative and unchanged. No external model is called during synchronization.

## Invariants

1. Current transcript characters define semantic identity and order.
2. Existing transcript cue texts define the last accepted semantic partition.
3. Source and edited times define retention, order and display timing only.
4. Every current character belongs to exactly one active cue.
5. A cue boundary may move only through an explicit text-diff projection or to a legal fallback boundary.
6. Empty cues are suppressed; protected words are never split merely to keep the old cue count.

## Save-Time Semantic Projection

Replace duration-ratio redistribution with a deterministic cue-aware text projection.

### Inputs

- ordered transcript cues overlapping the edited source segment;
- their current content-character sequences and cue ownership;
- the authoritative updated segment text and natural timed words already produced by `sync_source_segments_from_editable()`.

### Projection

Flatten the old overlapping cue texts into one character sequence while retaining each character's cue owner. Compute a monotonic old/new text diff:

- equal runs retain the old cue owner exactly;
- deletions remove only their old owners' characters;
- insertions inherit the adjacent affected cue, preferring the side that keeps the surrounding equal runs in one cue;
- replacements are limited to the old owners touched by that diff hunk;
- a hunk spanning multiple owners selects boundaries only from legal word/segment candidates in the updated segment;
- when a hunk has no legal internal boundary, assign it to one owner and suppress emptied cues rather than hard-splitting a word.

The output updates cue `text` and matching `characterTimings` only. Existing cue `start/end/sourceStart/sourceEnd`, ID, track ID and style remain stable, preserving the established text-save timing contract.

If the helper cannot prove character conservation, it must leave the prior cue texts intact and surface a deterministic failure to the route instead of silently persisting a partially redistributed track. The existing broad best-effort `except Exception: return` must not hide an invariant violation introduced by the new projection.

## Cut-Time Boundary Projection

`reconcileTranscriptTrack()` continues to operate once per `trackId`, but `partitionTranscriptTrack()` no longer accepts a raw character index as final authority.

### Candidate data

Extend transcript units with their natural word/segment identity while building `transcriptCharacterUnits()`. Derive:

- hard legal candidates at the start/end of natural word or segment units;
- protected spans represented by each old cue's unchanged text around its boundary;
- current source/edited distance for tie-breaking only.

### Boundary selection order

For each old cue boundary, in monotonic order:

1. Project the old semantic boundary through the flattened base-cue/current-transcript diff.
2. If the exact projection is unavailable, choose the nearest candidate preserving matched left/right semantic anchors.
3. If those anchors were edited away, choose the nearest legal word/segment boundary to the source or capacity preference.
4. Reject candidates that strand a one-character cue or reproduce existing incomplete-ending/weak-start shapes when another legal candidate exists.
5. If no legal candidate exists, reuse the previous cursor so the empty cue becomes suppressed; never cut inside a protected word to preserve cue count.

The existing full-track conservation check remains mandatory. Add a semantic-boundary check so a partition can be complete yet still be rejected. Capacity fallback uses the same legal candidate set; it may choose a different legal boundary but cannot return an arbitrary character index.

## Reconciliation Baseline

Visible cue text and `_cutReconciliation.overlay.text` must always represent the same semantic partition version after a text save. Suppressed cues keep their stable base and order. Cut undo/restore therefore reprojects from the accepted semantic partition instead of from a previously corrupted temporary output.

Equivalent service projections with different source anchors must not repartition text when the semantic transcript and accepted cue partition are unchanged.

## Data Flow

```text
initial backend semantic cues
  -> text save: cue-aware diff projection, stable cue times
  -> Store visible/base text sync
  -> transcript split/delete changes retained characters
  -> ArtModel diff-projects old semantic boundaries
  -> legal-boundary validation + character conservation
  -> one Store frame for timeline/preview/compose
```

## Compatibility

- No public API schema change is required.
- Existing jobs without `_cutReconciliation` use visible cue text as their semantic base.
- Missing/invalid transcript words fall back to segment boundaries and existing stable cue text anchors; they do not permit arbitrary internal cuts.
- Manual art overlays retain the current anchored-overlay path.
- Existing initial AI segmentation cache, font sizing and cue count limits remain unchanged.

## Risks And Rollback

- Repeated text can make diff anchors ambiguous. Resolve ties monotonically, then by source distance and original cue order; tests must include repeated phrases.
- A fully rewritten multi-cue segment may legitimately reduce active cue count because no safe old boundary remains. Character conservation and semantic integrity take priority over preserving every cue.
- If implementation cannot maintain stable cue timing and semantic legality together, roll back the new projection helpers as one unit; do not restore duration-ratio or raw midpoint cutting as a silent fallback.

