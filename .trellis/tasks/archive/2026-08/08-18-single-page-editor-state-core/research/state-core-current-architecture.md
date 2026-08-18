# Research: Single-page editor state core current architecture

- Query: Map current project/timeline state ownership and determine the minimum safe B0 `EditorProjectStore`, revision guard, iframe adapter, tests, and rollback points.
- Scope: internal
- Date: 2026-08-18

## Findings

### Executive conclusion

The smallest safe B0 is a top-level semantic store plus a compatibility bridge. It must not migrate the art or picture-in-picture UI out of iframes yet, and it must not replace `EditorTimeline`. The store becomes the only top-level owner of the latest project projection, action/revision ordering, compose input, and projections sent to the existing children. The child tools may temporarily retain their local editing arrays and `EditorTimeline` stores, but their `tool-state` messages become adapter inputs rather than an independent compose authority.

The immediate text-edit bug is an explicit two-path race:

1. `saveSegmentText()` updates the server and local cut text, broadcasts `editor-suite:transcript-updated`, then schedules an unconditional top-level `window.location.reload()` after 500 ms (`web/app.js:1210`, `web/app.js:1241`, `web/app.js:1248`, `web/app.js:1252`).
2. The broadcast is forwarded to the art iframe (`web/editor-suite.js:1897`), which concurrently fetches the full job, replaces its transcript/art overlays, renders, and publishes state (`web/art-text.js:2966`, `web/art-text.js:2975`, `web/art-text.js:2990`, `web/art-text.js:3004`).
3. The fixed-delay reload destroys that iframe whether its fetch has completed or not. Reload then re-runs `renderResult()`, resets cut runtime/history fields, replaces the base video `src`, calls `load()`, and reconstructs both iframes (`web/app.js:4638`, `web/app.js:4640`, `web/app.js:4718`; `web/editor-suite.js:752`). Playback therefore restarts and any in-flight child response becomes irrelevant.

The reload originally compensated for an API response gap: `PUT /editable-segments` returns only `editableSegments` (`server/app.py:10643`), while the server also changes `result.segments`, `result.text`, and overlapping art subtitle cue text (`server/app.py:10617`, `server/app.py:10629`). The backend deliberately preserves each cue's `start/end` and invalidates the rendered art output (`server/app.py:8027`, `server/app.py:8033`, `server/app.py:8089`). The browser needs a later full-job read to see those changes. The existing art iframe already performs that read, so the additional whole-page reload is redundant and destructive.

### Files found

- `web/app.js` - cut/editor page state, transcript mutation, cut draft persistence, cut timeline, base video lifecycle, and the unconditional text-save reload.
- `web/editor-suite.js` - top-level iframe lifecycle, mirrored preview/timeline, compose payload, child message bridge, and a fourth timeline store.
- `web/art-text.js` - art overlays, transcript track, art timeline store, session draft, child message handling, and server refresh after transcript edits.
- `web/picture-in-picture.js` - PiP items/assets, transcript projection, PiP timeline store, session draft, and child message handling.
- `web/timeline-model.js` - reusable normalized timeline document/store, mutation/commit API, pointer session, and draft envelope.
- `server/app.py` - text mutation response shape and stable-time art cue update behavior.
- `server/schemas.py` - `TranscriptSegmentOperation` action contract.
- `web/index.html`, `web/art-text.html`, `web/picture-in-picture.html` - non-module `defer` loading order for shared globals.
- `tests/app/browser/test_editor_workflows.py` - real-browser refresh, tool switch/playback, and compose baselines.
- `tests/app/test_cut_draft.py` - backend text-edit and stable art cue timing coverage.
- `tests/app/test_frontend_contracts.py` - static frontend loading/message contracts.

### Current state owners

| Domain | Current owner(s) | Persistence/projection | Drift risk |
| --- | --- | --- | --- |
| Authoritative server job | `JOBS[job_id]` | `GET /api/transcriptions/{id}` | Child and parent fetch/apply independently. |
| Transcript source/editable text | `app.js` `currentSegments` and `currentEditableSegments` (`web/app.js:173`) | `PUT /editable-segments`; local arrays; job result | PUT response omits the updated full transcript/art snapshot. |
| Cut selection | `selectedRanges`, `selectedNoSpeechRanges`, `timelineDeleteRanges` (`web/app.js:183`, `web/app.js:224`) | local/server cut draft, local undo history | Separate from both cut and suite timeline stores. |
| Cut revision | `cutDraftRevision` (`web/app.js:215`) | server cut-draft revision | Applies only to cut draft, not transcript/art/PiP/project state. |
| Cut timeline | `cutTimelineStore` (`web/app.js:229`) | `onCommit -> scheduleCutDraftSave()` | Not the same store as the suite timeline. |
| Top-level project/job | `editor-suite.js` `currentJob` (`web/editor-suite.js:119`) | repeated GET/job-state messages | Whole mutable job object can arrive from parent or either child. |
| Top-level cut projection | `cutDraftState` (`web/editor-suite.js:124`) | direct `EditorSuite.setCutDraft()` then postMessage | No semantic distinction between text and timing updates. |
| Top-level tool projection | `toolStates` (`web/editor-suite.js:111`) | child `tool-state` messages | Contains HTML snapshots and private generation payloads. |
| Unified visual timeline copy | suite `timelineStore` (`web/editor-suite.js:132`) | `syncToolTimeline()` copies child tracks | Fourth store; selection/timing can lag child stores. |
| Art domain | `overlays`, `cutSuppressedOverlays`, selection and transcript fields (`web/art-text.js:158`) | sessionStorage + job art + child messages | Server refresh can replace locally newer iframe overlays. |
| Art timeline | `artTimelineStore` (`web/art-text.js:196`) | rebuilt from overlays; session draft | Timeline is derived but separately mutable during bridge actions. |
| PiP domain | `pictureItems`, transcript and selection fields (`web/picture-in-picture.js:99`) | sessionStorage + job PiP + child messages | Text/timing projection is reapplied independently. |
| PiP timeline | `pipTimelineStore` (`web/picture-in-picture.js:123`) | rebuilt from items; session draft | Duplicates the suite timeline projection. |
| Preview | parent `toolStates.*.overlayHtml` | child DOM HTML copied into parent (`web/editor-suite.js:828`) | Visual state is a DOM snapshot, not a selector over project state. |
| Compose request | `previewCompositionState()`/`compositionRequest()` | cut draft + child `generationPayload` or server fallback (`web/editor-suite.js:348`) | Fields can come from different logical revisions. |
| Playback | parent `#cutPreviewVideo`, child tool videos | `sync-time` postMessage (`web/editor-suite.js:739`) | Text reload tears down all clocks and reloads media. |

### Existing save, refresh, and message flows

#### Cut draft

- Cut UI mutations call `updateSelectionSummary()`, which rebuilds the live cut transcript, pushes it to `EditorSuite.setCutDraft()`, refreshes the cut timeline, and schedules persistence (`web/app.js:2762`, `web/app.js:2819`).
- Cut persistence uses a serialized promise queue and a cut-only server revision (`web/app.js:2363`, `web/app.js:2390`, `web/app.js:2425`). This queue and signature pattern are reusable for effects but do not provide a project-wide stale-response guard.
- `EditorSuite.setCutDraft()` normalizes ranges and then posts the complete cut projection to both children (`web/editor-suite.js:1205`, `web/editor-suite.js:1227`, `web/editor-suite.js:727`).

#### Tool state

- Art publishes HTML, a normalized timeline snapshot, generation UI state, and compose overlays (`web/art-text.js:2911`). PiP publishes the equivalent shape (`web/picture-in-picture.js:1149`).
- The suite stores those payloads in `toolStates`, copies tracks into its own timeline store, mirrors HTML into parent preview/timeline DOM, and uses the private `generationPayload` for compose (`web/editor-suite.js:1295`, `web/editor-suite.js:1330`, `web/editor-suite.js:1346`).
- Parent-to-child timing/select/move messages mutate the child first or in parallel with the suite timeline copy (`web/editor-suite.js:1586`). No revision accompanies these messages.

#### Text-only edit

- The backend contract already encodes the intended rule: update text and word mapping, redistribute text over overlapping transcript-track cues, keep cue times unchanged, and invalidate the stale rendered art video (`server/app.py:10617`; `server/app.py:8027`). Backend coverage locks this at `tests/app/test_cut_draft.py:781`.
- The art child has a partial text/timing distinction. `cutDraftTimingSignature()` excludes transcript text; `applyEditorCutDraft()` recognizes timing-unchanged/text-changed updates and avoids rebuilding the subtitle track (`web/art-text.js:3237`, `web/art-text.js:3246`). It then relies on a separate full-job refresh for updated server cue text (`web/art-text.js:2966`).
- PiP has no explicit text-only action; every cut-draft message rematches every item to transcript segments and rewrites item times (`web/picture-in-picture.js:1314`). Source anchors reduce risk, but a text-only action should not enter this timing path.

### Minimum `EditorProjectStore` API

Create `web/editor-project-store.js` as one non-module global loaded after `timeline-model.js` and before `editor-suite.js`/`app.js`. Keep `EditorTimeline` unchanged and inject it into the store factory.

Minimal state:

```javascript
{
  schemaVersion: 1,
  jobId: "",
  revision: 0,          // every accepted semantic state change
  timingRevision: 0,    // only accepted timing-structure changes
  serverVersion: "",    // job.updatedAt compatibility marker, not sole guard
  project: {
    job: null,           // normalized latest server projection
    transcript: null,
    cut: { active: false, ranges: [], sourceDuration: 0, duration: 0, transcript: null },
    art: { source: "original", overlays: [] },
    pip: { source: "original", overlays: [] },
    timeline: { duration: 0, tracks: [], selection: null }
  },
  ui: { activeTool: "cut" }
}
```

Minimal public surface:

```javascript
const store = EditorProjectStore.createStore(initial, { timeline: EditorTimeline });
store.getState();
store.dispatch(action);                 // returns { accepted, revision, timingRevision }
store.subscribe(listener);              // listener(next, previous, action)
store.beginEffect(scope);               // { scope, requestId, baseRevision, baseTimingRevision, jobId }
store.isCurrentEffect(token);            // same job + latest scope request
store.applyEffect(token, action);        // rejects stale token/action atomically
store.select(selector);                  // convenience only; selectors are exported pure functions
store.destroy();
```

Required actions:

- `projectHydrated({ job, preserveLocalTools })`: initial/explicit refresh. Job change resets all domains; same-job refresh must not overwrite locally newer art/PiP projections unless requested.
- `transcriptTextChanged({ transcript, editableSegments, serverArt })`: increments `revision` only. It must preserve existing art/PiP `start/end/sourceStart/sourceEnd`; server art may contribute updated transcript cue text/character mapping only. It must not replace video `src`, call `load()`, change playback, or rebuild timing tracks.
- `cutTimingChanged(cut)`: increments both revisions and derives the cut track/time map.
- `artStateChanged({ source, overlays, timeline })`: semantic child adapter input; timing revision increments only when normalized timing/source anchors differ, not for text/style/position alone.
- `pipStateChanged({ source, overlays, timeline })`: same rule as art.
- `activeToolChanged(tool)`: UI-only revision or no project revision; it must never recreate a frame solely because state changed.
- `selectionChanged(selection)`: UI/timeline selection only.

Revision guard rules:

1. `beginEffect("transcript-save")` cancels logically older transcript saves through a monotonically increasing request id.
2. A response is accepted only for the same `jobId`, latest request id in that scope, and compatible `baseTimingRevision`.
3. Text results may rebase over newer non-timing UI/style changes, but must be rejected/retried if timing changed while the request was in flight. Never apply a late full-job object wholesale.
4. `serverVersion`/`updatedAt` is diagnostic/compatibility metadata; local request id plus revisions are the actual guard because the current API has no project revision.
5. Each accepted action publishes one immutable snapshot. Preview and compose selectors must read one snapshot/revision, not call `getState()` separately per domain.

Required selectors:

- `selectCutDraftMessage(state)` - current legacy `editor-suite:cut-draft` shape plus `revision`, `timingRevision`, and semantic `changeKind`.
- `selectToolState(state, kind)` - adapter projection for current art/PiP state.
- `selectTimelineDocument(state)` - `EditorTimeline.normalizeDocument()` over cut/art/PiP tracks.
- `selectPreviewLayers(state)` - semantic art/PiP models; B0 may still feed the HTML mirror adapter, but the selector must not contain HTML.
- `selectCompositionRequest(state)` - replacement for `compositionRequest()`, derived atomically from the same snapshot.
- `selectIframeProjection(state, kind)` - compatibility messages only: cut draft, time/selection commands, and transcript text action.

### Compatibility adapter boundary

For B0, keep `createToolFrame()`, existing iframe pages, their internal arrays/stores, and all user-visible UI. Change only authority and message translation:

1. `app.js` dispatches semantic actions to the top store. `saveSegmentText()` performs PUT, obtains the updated full job via one guarded GET (until the API returns a full snapshot), dispatches `transcriptTextChanged`, and removes the unconditional reload.
2. `editor-suite.js` subscribes once. It translates store projections into the existing child messages and renders current mirror HTML during the compatibility period.
3. Child `tool-state` messages dispatch `artStateChanged`/`pipStateChanged`; `toolStates` becomes either an adapter cache derived from the store or is removed. Compose must use `selectCompositionRequest()`.
4. Add `revision`, `timingRevision`, and `changeKind` to messages, with backward-compatible defaults. Children record the last applied revision and ignore older messages.
5. For `changeKind: "transcript-text"`, art refreshes cue text without invoking `replaceTranscriptTrackFromCutDraft()` or `retimeDraftAnchoredOverlays()`; PiP updates transcript labels only and does not rematch/rewrite item times. Existing timing messages retain current behavior.
6. Do not put `overlayHtml`, `timelineHtml`, or private generation payloads into `EditorProjectStore`. They remain bridge-only compatibility caches until B1/B2/B3.

This boundary avoids a false migration: merely moving the existing `toolStates` payload into a new object would preserve four competing stores and would not solve revision drift.

### Reusable existing functions

- `EditorTimeline.normalizeDocument`, `createStore`, and `createPointerSession` (`web/timeline-model.js:79`, `web/timeline-model.js:98`, `web/timeline-model.js:257`). Reuse normalization; do not add another clip model.
- `syncToolTimeline()` track replacement behavior (`web/editor-suite.js:137`) can move behind `selectTimelineDocument()`.
- `previewCompositionState()` and `compositionRequest()` (`web/editor-suite.js:348`, `web/editor-suite.js:377`) define the existing public compose shape and should become pure selectors without changing API fields.
- `cutDraftTimingSignature()` (`web/art-text.js:3237`) is the current proven distinction between text and timing, but should be replaced by `timingRevision` rather than copied.
- Cut draft save queue/request snapshot pattern (`web/app.js:2363`, `web/app.js:2425`) is useful for serialized effects; project state still needs per-scope request ids.
- `update_transcript_track_text_for_segment()` (`server/app.py:8027`) is the authoritative stable-time merge rule. Frontend actions must preserve its timing invariant.
- Existing `event.origin` and `event.source` validation in parent/children must remain (`web/editor-suite.js:1295`, `web/art-text.js:3310`, `web/picture-in-picture.js:1363`).

### Exact affected files for minimum B0

Product code:

- Add `web/editor-project-store.js`.
- Update `web/index.html`, `web/art-text.html`, and `web/picture-in-picture.html` load order/version references only if children use shared action constants/guards.
- Update `web/app.js` to dispatch hydrate/cut/text actions, guard transcript-save effects, and remove the reload.
- Update `web/editor-suite.js` to own/create the store, adapt old messages, subscribe once, and derive compose/timeline from selectors.
- Update `web/art-text.js` to accept revision/change kind and apply text-only updates without timing work.
- Update `web/picture-in-picture.js` to accept revision/change kind and avoid timing rematch for text-only updates.
- Prefer no `server/app.py` or schema change in the minimum patch: use a guarded GET after the existing PUT. A later API improvement may return `{editableSegments, projectSnapshot, revision}` and remove that GET.

Tests:

- Add pure Node behavior coverage for store immutability, action revision increments, timing revision invariants, stale effect rejection, same-job hydrate preservation, and compose selector atomicity. Follow the existing Node subprocess pattern in `tests/app/test_frontend_contracts.py` or add a focused frontend state test file.
- Extend `tests/app/test_frontend_contracts.py` for script load order/version, absence of `window.location.reload()` in text save, message source/origin validation, and backward-compatible action/message constants.
- Extend `tests/app/browser/test_editor_workflows.py` with a real text-save workflow: start playback/seek to a nonzero time, edit a segment, wait for saved text and mirrored art text, assert the top document did not navigate, `#cutPreviewVideo.src` did not change, playback time did not reset, iframe elements were not replaced, art cue times stayed exact, PiP times stayed exact, and compose contains the new text/state from one store revision.
- Keep `tests/app/test_cut_draft.py:781` as the backend timing invariant. Add API coverage only if the response contract is expanded.
- Run all browser workflows plus full `tests/app/` and `node --check` on every `web/*.js`.

### Rollout and rollback points

1. Commit the new store and pure tests first with no consumers. Rollback: remove the script/reference.
2. Put store ownership behind one top-level flag, for example `window.__EDITOR_PROJECT_STORE_ENABLED__ !== false`; select either legacy authority or store authority once at startup, never both. Rollback: set the flag false, keeping old messages unchanged.
3. Migrate transcript save/hydration and remove reload. Rollback: restore the old reload only as an emergency behavior flag, not concurrently with the guarded action path.
4. Migrate compose to `selectCompositionRequest()`. Rollback: use the existing `compositionRequest()` adapter fed from the same store snapshot; do not restore child state as a second authority.
5. Migrate art and PiP message ingestion separately. Rollback each kind independently to legacy bridge input while leaving the other kind on the store.

The acceptance checkpoint for each step is a stable nonzero playback position and unchanged iframe identity after a text save. If either changes, stop before B1; do not proceed to media/timeline consolidation.

### Related specs

- `.trellis/spec/frontend/index.md`
- `.trellis/spec/frontend/architecture-and-state.md`
- `.trellis/spec/frontend/api-and-media.md`
- `.trellis/spec/testing/index.md`
- `.trellis/spec/testing/browser-workflows.md`
- `.trellis/spec/guides/project-overview.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`
- `.trellis/spec/guides/code-reuse-thinking-guide.md`
- `.trellis/tasks/08-13-project-optimization-audit/research/single-page-editor-architecture.md`
- `.trellis/tasks/08-13-project-optimization-audit/design.md`
- `.trellis/tasks/08-13-project-optimization-audit/implement.md`

### External references

None. The minimum design follows repository-local constraints: native scripts, no bundler/framework, same-origin iframes during migration, and existing Playwright/Python/Node test infrastructure.

## Caveats / Not Found

- There is no project-wide server revision today. `cutDraft.revision` covers only the cut draft; `job.updatedAt` is not a sufficient concurrency token. The first B0 implementation therefore provides a client revision/effect guard, not cross-tab or multi-client conflict resolution.
- The existing `PUT /editable-segments` response cannot atomically provide every updated domain. A guarded follow-up GET is the minimum compatible workaround, but the long-term API should return a normalized project snapshot with a server revision.
- Art/PiP child pages remain temporary local state owners during B0. The top store can establish ordered authority for projections and compose, but duplicate internal stores are removed only in B1-B3.
- The current art server refresh replaces overlay arrays from `job.art`; locally newer unsaved child changes can be lost. The Store action must merge text-only server data into current local art state rather than wholesale-replacing it.
- No current real-browser test covers transcript text save without navigation or playback reset. That test is mandatory before deleting the reload.
