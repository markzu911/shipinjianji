# Schema 提取清单

## Current Baseline

- Source: `server/app.py:381-610`
- Pydantic: 2.13.4
- Models: 29
- OpenAPI paths: 48
- OpenAPI component schemas: 34
- Stable OpenAPI JSON SHA-256: `e593b2b69a3a4fe98530d7bc8dc140a0f8841e5c153dd4bd5447b9dd23eaeea9`
- Pytest baseline: 176 nodes

## Exact Model Inventory

| Domain | Models |
| --- | --- |
| Cut and draft | `DeleteRange`, `CutRequest`, `CutDraftTextRange`, `CutDraftNoSpeechRange`, `CutDraftRequest` |
| Operations, settings and transcript | `JobCleanupRequest`, `ModelProviderUpdate`, `TranscriptWordUpdate`, `TranscriptTextUpdate`, `TranscriptSegmentOperation` |
| Art text | `ArtTextAnimation`, `ArtTextCharacterTiming`, `ArtTextCharacterLayout`, `TextOverlay`, `ArtTextRequest`, `TranscriptArtTextTrackRequest`, `ArtTextSuggestionRequest` |
| Picture in picture | `PictureInPictureImageRequest`, `PictureInPictureVideoRequest`, `PictureInPicturePromptRequest`, `PictureInPictureOverlay`, `PictureInPictureRequest` |
| Composition | `PreviewCompositionRequest` |
| Asset libraries and history | `FontUpdate`, `ArtTemplateUpdate`, `ArtPositionPresetCreate`, `ArtPositionPresetUpdate`, `HistoryVersionUpdate`, `HistoryVersionCreate` |

Each name must appear exactly once as a class definition in `server/schemas.py` and remain available as an explicit imported name in `server.app`.

## Dependency Evidence

- The model block only needs `Any`, `Literal`, `BaseModel` and `Field`.
- `BaseModel` and `Field` are not used below the current model block. `Any` remains required throughout `server/app.py`, and `Literal` remains required by runtime function annotations below the block.
- Nested dependencies are internal to the block: cut draft models inherit `DeleteRange`; art/composition models refer to `TextOverlay`, animation/layout/timing models and picture-in-picture overlays.
- No model reads runtime globals, paths, locks, jobs, environment variables, FastAPI objects or media libraries.
- Tests currently instantiate `DeleteRange`, `TextOverlay`, `ArtTextAnimation`, `ArtTextCharacterLayout`, `ArtTextCharacterTiming` and `PictureInPictureOverlay` through the `server.app` module object, so re-export compatibility is observable and required.

## Validation Evidence

- Exact OpenAPI hashing detects changes to field names, required/optional status, defaults, constraints, enums, nesting and request-body references across all routes.
- Existing feature API tests retain behavioral coverage for invalid and valid payloads.
- A dedicated identity test is required because full API tests can pass even if `server.app.<Model>` compatibility is accidentally removed.

## Chosen Boundary

The first runtime split extracts schemas only. It does not combine schema migration with repositories, route movement or media logic. This establishes a one-way module dependency and explicit re-export pattern that later backend extractions can reuse without making the first structural commit difficult to diagnose or roll back.
