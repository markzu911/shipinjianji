# Root Cause: art-text cue boundaries regress from semantic groups to arbitrary characters

## User Evidence

- Screenshot: `C:/Users/jiadi/AppData/Local/Temp/codex-clipboard-b4d5763d-ff7a-4edd-97d4-1dad6b06099c.png`.
- Reported trigger: edit transcript text, click transcript split, delete the split transcript.
- Visible failures: `其实` becomes `其 / 实`; `该有的` becomes `该 / 有的`.

The screenshot is evidence only. It does not provide implementation instructions.

## Confirmed Root Causes

### 1. Save-time backend redistribution ignores semantic boundaries

`server/app.py:update_transcript_track_text_for_segment()` collects every transcript cue overlapping the edited source segment and allocates `content_characters(new_text)` by each cue's source-duration ratio. The algorithm never compares old and new text and never consults `segments[].words` or the art-text segmentation rules.

Read-only minimal reproductions against the current function produced:

```text
durations [1, 2]   -> 前文其 / 实该有的后文
durations [1.1,.9] -> 前文其实该 / 有的后文
```

The input text was unchanged in both reproductions. Only cue duration ratios changed. Therefore text editing can corrupt a previously valid semantic partition before split/delete begins.

### 2. Cut-time frontend reconciliation selects arbitrary character indexes

`web/editor-art-model.js:partitionTranscriptTrack()` obtains each boundary from:

1. `transcriptSourceSplitIndex()`: count character midpoints before the old source boundary preference; or
2. `transcriptCapacitySplitIndex()`: round a cumulative cue-character ratio.

Neither result is restricted to a legal semantic boundary. A read-only Node reproduction used valid multi-character transcript words and old cue boundaries inside their source spans. Current output was:

```text
前文其 / 实该 / 有的后文结束
```

This reproduces both reported failure shapes without any specific video, job state or vocabulary exception.

## Broken Cross-Layer Contract

Initial track generation in `server/app.py` operates on complete `segments[].words` items:

- AI returns only `break_after` word indexes;
- `split_long_clause_to_fit()` considers pause, sentence/clause boundaries, incomplete endings and weak starters;
- normalization repairs lone-character and incomplete groups;
- the final conservation check verifies every character once.

After the track exists, save-time and cut-time synchronization discard that semantic partition and reconstruct boundaries from duration ratios or individual character midpoints. The system therefore has two incompatible contracts:

```text
initial generation: semantic word/group boundaries
later synchronization: arbitrary character indexes
```

The previous leading-character repair made the second path track-wide and conservative, which fixed missing characters but did not make its boundaries semantic.

## Why This Is Broad

Any multi-character word or phrase can be split when a cue duration ratio or old source preference falls between its characters. The exact word, ASR model and video are irrelevant. Anchor drift, edits that change segment length, user-created transcript splits, deletions and restore operations only change where the arbitrary index lands.

The defect is not fixed by adding “其实” or “该有的” to a dictionary. It requires one boundary contract across text save and cut reconciliation.

## Required Prevention

1. Preserve the existing semantic cue partition through a monotonic old-text -> new-text diff.
2. Keep unchanged character runs owned by their original cue.
3. Restrict fallback cuts to legal current transcript boundaries; merge/suppress rather than hard-split a protected unit.
4. Use source/edited timing only to retime retained units and break ties between equally legal boundaries.
5. Assert both track-wide character conservation and semantic-boundary legality in backend, ArtModel, Store and browser workflow tests.

## Break-Loop Analysis

### 1. Root Cause Category

- **Primary: B - Cross-Layer Contract.** Initial generation treated natural word groups as semantic ownership, while backend text save and frontend cut reconciliation later rebuilt the same boundaries from physical duration or character midpoints.
- **Secondary: C - Change Propagation Failure.** The previous character-conservation repair fixed the frontend track-wide allocation but did not update both save-time and cut-time boundary contracts together.
- **Secondary: D/E - Test Coverage Gap and Implicit Assumption.** Earlier tests asserted concatenated text but not individual cue arrays, allowing a complete yet semantically corrupted partition to pass. Timing was implicitly assumed to be a semantic existence signal.

### 2. Why Earlier Fixes Failed

1. The leading-character repair correctly stopped character loss, but its invariant was only “every character appears once.” It did not require boundaries to remain legal.
2. Fixing only the Store projection would still leave backend text saves able to persist an arbitrary split; fixing only the backend would let later cut reconciliation recreate it.
3. Source coverage filtering looked safe for legacy isolated tracks, but applying it to the single full transcript track removed current characters whose anchors drifted outside stale cue coverage.

### 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | Separate character identity, accepted semantic partition and physical timing as three authorities | DONE |
| P0 | Test coverage | Assert cue arrays, character conservation and legal boundaries through edit -> split -> delete -> restore | DONE |
| P0 | Cross-layer review | Review backend save and frontend reconciliation as one contract | DONE |
| P1 | Documentation | Record executable backend/frontend contracts and the source-anchor checklist | DONE |

### 4. Systematic Expansion

- Similar risk exists anywhere an old source range filters current semantic objects. Full-track reconciliation now consumes the complete current transcript; legacy multi-track isolation retains only whole natural units.
- Repeated text makes diff alignment ambiguous, so selection must remain monotonic and deterministic, with timing used only to rank equally legal candidates.
- A future boundary change must test both existence and partition legality; concatenated output alone is insufficient.

### 5. Knowledge Capture

- [x] Backend persistence contract updated with the cue-aware diff signature, validation matrix and tests.
- [x] Frontend state contract updated with legal semantic-boundary projection, full-track coverage and suppression/restore rules.
- [x] Cross-layer guide updated to prohibit physical anchors from deciding semantic existence.
- [x] No spec template sync was required because this repository has no `src/templates/markdown/spec/` directory.
