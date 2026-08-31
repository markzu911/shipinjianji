# Research: normalized cut-draft response acknowledgement and history consistency

- Query: Why does a VAD-normalized cut-draft PUT leave undo apparently saved locally while the server keeps the deletion, and what is the minimum safe class-wide fix?
- Scope: internal
- Date: 2026-08-28

## Findings

### Root cause

The server successfully commits a normalized draft, but the browser rejects the successful response before accepting its new revision.

1. Manual timeline selection keeps raw browser floating-point source times (`web/app.js:1903-1920`, `web/app.js:4272-4279`, `web/app.js:5367-5389`). A visually displayed `3.153-3.191` selection can therefore contain more precision in the request.
2. The server canonicalizes every ordinary range to millisecond precision (`server/app.py:886-898`), rounds timeline semantic `originalStart/originalEnd` (`server/app.py:15183-15213`), and then lets VAD/forced alignment widen the physical `start/end` while retaining rounded semantic boundaries (`server/app.py:6000-6324`). Text semantic ranges can additionally be canonicalized to natural character boundaries (`server/app.py:5901-5925`). Split points are also rounded to milliseconds (`server/app.py:901-920`). These are intended authoritative transformations.
3. The browser's semantic signature uses exact JavaScript numbers for text semantic boundaries, no-speech physical boundaries, timeline semantic boundaries, and split times (`web/app.js:2895-2946`). It does not canonicalize those numbers to the server representation.
4. On PUT success, the browser compares the normalized response signature with the pre-normalization request signature before reading/accepting the returned revision (`web/app.js:3256-3265`). A legitimate rounding or semantic canonicalization difference throws `服务器返回的剪辑草稿与当前请求不一致。` even though `cut-draft.json` and the in-memory job have already advanced (`server/app.py:15267-15308`).
5. Because `cutDraftRevision`, `cutDraftLastSignature`, and `cutDraftAcknowledged` remain stale, undo restores the local history snapshot but its save can be short-circuited or sent against the old revision (`web/app.js:3176-3196`, `web/app.js:3209-3215`, `web/app.js:3320-3367`, `web/app.js:3694-3752`). The UI can then say saved while GET/refresh still returns the committed deletion; redo subsequently receives `409`.

This is a class-wide contract defect, not a VAD edge case. Any server-side normalization that changes an exact signed number can trigger it: a short speech-safe timeline range, a text range canonicalized to character boundaries, a no-speech range with sub-millisecond precision, or an unrounded split point. `split_exact` often passes only because its inputs already happen to be stable millisecond values.

The interaction audit reproduced the defect on two independent jobs. A semantic selection near `3.153-3.191s` was committed as physical `3.09-3.32s`; local undo showed no deletion while the server retained the normalized range, refresh restored it, and redo entered `409` (`.trellis/tasks/08-28-editor-interaction-regression-audit/audit-results.md`).

### Why existing safeguards do not prevent it

- `applyPersistedCutDraftAlignment()` already supports atomically installing different physical text/timeline boundaries and validates matching keyed structures (`web/app.js:3008-3115`), but the exact response-signature check prevents it from running in the failing case.
- The helper only aligns text and timeline ranges. It does not install server-normalized no-speech ranges or split points, so merely deleting the signature check would leave other normalization classes divergent.
- `reconcileCurrentCutHistorySnapshot()` is designed to rewrite the current history endpoint after authoritative alignment (`web/app.js:3000-3006`, `web/app.js:3100-3111`). It cannot help when response processing exits before alignment.
- `applyServerRetainedProjection()` requires job, signature, and revision to match the current state (`web/app.js:2592-2610`). If normalization changes the semantic signature, it must receive the post-normalization signature, not the original request signature.
- Browser save tests normally echo the request back verbatim (`tests/app/browser/test_editor_workflows.py:188-218`). The recording route widens only text physical `start/end` while preserving signed semantic fields (`tests/app/browser/test_editor_workflows.py:221-275`). Neither route simulates server rounding/canonicalization of a signed field.
- The direct frontend alignment test covers physical text/timeline changes with unchanged semantic fields and invokes the helper without the PUT acknowledgement state machine (`tests/app/test_frontend_contracts.py:2201-2321`).
- API tests correctly prove that the backend normalizes, persists, restores, and rejects stale revisions (`tests/app/test_cut_draft.py:344-423`, `tests/app/test_cut_draft.py:1340-1425`, `tests/app/test_cut_draft.py:1479-1518`), but they cannot detect the browser's stale revision after a successful PUT.

### Minimum safe fix shape

Treat a successful PUT response as an authoritative normalization acknowledgement, while preserving stale-response and structural-integrity guards.

1. Validate that `result.cutDraft` exists and that its numeric revision is strictly greater than the request revision. Once that valid revision is present on an HTTP 2xx response, accept it before any normalization-sensitive comparison. The server has already durably committed `cut-draft.json`; keeping the old revision guarantees the next write will conflict.
2. Replace exact request-signature equality with structural command identity validation. Require the same job/request generation and the same keyed membership for text, no-speech, timeline, and split collections; preserve `automaticNoSpeechInitialized`, text/key identity, timeline `boundaryMode`/`splitClipKey`, and reject missing, duplicate, or unexpected entries. Numeric range fields are authoritative server output and must be allowed to normalize.
3. When the response still corresponds to the latest desired state, install the complete normalized server draft atomically: text ranges, no-speech ranges, timeline ranges, and split points. Do all validation and construction before mutating live state.
4. After installation, rebuild the payload and compute the post-normalization semantic signature. Use that signature for `cutDraftAcknowledged`, the rebuilt `cutDraftDesired`, retained-projection guards, local cache, and the reconciled current history endpoint. Do not acknowledge the pre-normalization signature as the current live state.
5. When a response is valid but a newer local edit already exists, accept only its revision and queue/rebase the latest desired payload exactly once. Do not overwrite the newer state with the older normalized snapshot. The existing single-in-flight/generation guard remains applicable (`web/app.js:3199-3232`, `web/app.js:3302-3313`).
6. If post-response normalization cannot be safely installed, retain the accepted revision and keep the draft marked as needing server synchronization (or reconcile with a no-cache GET). Never regress to the pre-response revision after the server has committed.
7. Undo and redo remain ordinary compensating PUTs: undo sends the `before` snapshot using the acknowledged revision; redo sends the server-normalized `after` snapshot using the undo acknowledgement revision. Show `剪辑草稿已保存` only when `isCutDraftAcknowledged(currentPostNormalizationSignature, jobId)` is true.

Rounding only the frontend signature to three decimals would close the observed single-frame case but is insufficient as the complete fix: text semantic canonicalization can legitimately move to natural character boundaries, and a signature-only change would not synchronize normalized no-speech/split state or the retained projection/history signature.

### Edge cases

- A second edit occurs while the first VAD/forced-alignment PUT is in flight: accept response revision, do not install stale normalized ranges, then send the latest state with the new base revision once.
- Undo is pressed immediately after confirmation but before the first PUT returns: the first response must advance revision without restoring the superseded deletion; the queued undo PUT must clear it using that revision.
- Server normalization changes both physical and semantic boundaries: install the response and rewrite only the current history endpoint, preserving the `before` snapshot so undo still means the user's original command reversal.
- Server returns the same or lower revision, malformed collections, duplicate/missing keys, a changed text identity, or changed `split_exact` ownership: reject it as an invalid acknowledgement; do not show saved.
- Old response omits `retainedTranscript`: normalized draft acknowledgement must still succeed, using the existing local projection fallback.
- Retained transcript is present: install it only against the post-normalization job/signature/revision triple.
- Normalized empty state, empty arrays, and automatic no-speech initialization must remain distinguishable from missing state.
- Reload after undo must select the server's empty draft, not a newer-timestamp local draft that was never acknowledged. The separate `updatedAt` local/server reconciliation risk remains outside this narrow task but the regression should ensure this fix does not create a false local winner.

### Exact tests required

1. Frontend state-machine unit test in `tests/app/test_frontend_contracts.py`: request a timeline range with sub-millisecond semantic values; return the same key with rounded semantic values, VAD-expanded physical values, and revision `N+1`. Assert no error status, revision `N+1`, full normalized live state, post-normalization acknowledgement, retained projection acceptance, and one history reconciliation.
2. Frontend normalization coverage: include no-speech millisecond rounding and split-point rounding, plus a text response whose semantic boundary is canonicalized. Assert live payload/signature equals the server-normalized snapshot and a redundant PUT is not scheduled.
3. Frontend stale/in-flight test: while request A is pending, create desired state B; return normalized A at revision `N+1`. Assert A does not overwrite B, B is sent once with revision `N+1`, and its response becomes revision `N+2`.
4. Frontend invalid-response test: missing/duplicate/wrong keys or changed split ownership must not be installed or shown as saved. If the response has a valid committed revision, assert the client does not reuse the old revision.
5. Browser workflow in `tests/app/browser/test_editor_workflows.py`: use a stateful cut-draft route (or deterministic backend normalization) that turns raw `3.1525...-3.1914...` into semantic `3.153-3.191` and physical `3.09-3.32`. Perform confirm -> wait for saved -> Ctrl+Z -> wait for an empty-range PUT based on the normalized revision -> Ctrl+Y -> wait for a normalized-range PUT based on the undo revision. Assert no `409` and no local-only/error status.
6. Browser refresh extension: after undo acknowledgement, reload and assert the range remains absent; after redo acknowledgement, reload and assert the normalized range returns. Verify the Store cut state and GET response agree at each step.
7. API regression in `tests/app/test_cut_draft.py`: retain current rounding/VAD persistence assertions and add an explicit sub-millisecond timeline request proving response semantic rounding plus physical widening and monotonic revision. No backend behavior change should be needed unless an acknowledgement token is introduced.
8. Run the focused suites: `py -3 -m pytest tests/app/test_frontend_contracts.py tests/app/test_cut_draft.py tests/app/browser/test_editor_workflows.py -q`, then the full project suite.

## Files Found

- `web/app.js` - cut draft serialization/signatures, save queue, authoritative alignment, retained projection, local recovery, and cut undo/redo.
- `server/app.py` - range/split normalization, VAD/forced-alignment boundary resolution, and cut-draft GET/PUT persistence/revision contract.
- `server/schemas.py` - cut-draft request fields and range identity metadata.
- `tests/app/test_frontend_contracts.py` - extracted JavaScript contract tests for alignment, retained projection guards, and flush failure.
- `tests/app/browser/test_editor_workflows.py` - real editor workflows and current request-echo save routes.
- `tests/app/test_cut_draft.py` - backend normalization, persistence, retained transcript, and revision-conflict coverage.
- `.trellis/tasks/08-28-editor-interaction-regression-audit/audit-results.md` - two-job browser reproduction and observed server/local divergence.

## Related Specs

- `.trellis/spec/frontend/architecture-and-state.md` - one authoritative editor Store and monotonic state transition expectations.
- `.trellis/spec/frontend/api-and-media.md` - API failure/stale-response handling and shared media state.
- `.trellis/spec/backend/media-and-timeline.md` - semantic versus physical cut ranges and the job/signature/revision retained-projection guard.
- `.trellis/spec/backend/persistence-and-jobs.md` - durable manifest and revision ownership.
- `.trellis/spec/testing/browser-workflows.md` - real interaction, refresh recovery, undo/redo, and request-state assertions.
- `.trellis/spec/guides/cross-layer-thinking-guide.md` - trace request, normalization, Store, persistence, and restore as one contract.

## Caveats / Not Found

- This research did not modify product code or execute the proposed regression tests.
- The exact raw floating values from the manual audit were not persisted in the audit artifact; the code path proves that pointer-to-time conversion can retain greater-than-millisecond precision, while the server always rounds to milliseconds. The observed UI values and server normalized values are consistent with that mismatch.
- A client mutation token echoed by the server would give stronger response identity than key-based structural validation, but it expands the API schema and persistence compatibility surface. It is not required for the minimum repair because each browser currently permits one in-flight PUT per job and already has generation/job guards.
- Transcript/job-version races during slow VAD processing and local-vs-server `updatedAt` selection are separate P0 consistency risks recorded by the optimization audit; do not silently broaden this task into those changes.
