from __future__ import annotations

import server.app as app_module
from server import schemas


SCHEMA_NAMES = (
    "DeleteRange",
    "CutRequest",
    "CutDraftTextRange",
    "CutDraftNoSpeechRange",
    "CutDraftTimelineRange",
    "CutDraftSplitPoint",
    "CutDraftRequest",
    "JobCleanupRequest",
    "ModelProviderUpdate",
    "TranscriptWordUpdate",
    "TranscriptTextUpdate",
    "TranscriptSegmentOperation",
    "ArtTextAnimation",
    "ArtTextCharacterTiming",
    "ArtTextCharacterLayout",
    "TextOverlay",
    "ArtTextRequest",
    "TranscriptArtTextTrackRequest",
    "ArtTextSuggestionRequest",
    "PictureInPictureImageRequest",
    "PictureInPictureVideoRequest",
    "PictureInPicturePromptRequest",
    "PictureInPictureOverlay",
    "PictureInPictureRequest",
    "PreviewCompositionRequest",
    "FontUpdate",
    "ArtTemplateUpdate",
    "ArtPositionPresetCreate",
    "ArtPositionPresetUpdate",
    "HistoryVersionUpdate",
    "HistoryVersionCreate",
)


def test_app_reexports_schema_classes():
    assert schemas.__all__ == SCHEMA_NAMES
    for name in SCHEMA_NAMES:
        assert getattr(app_module, name) is getattr(schemas, name)


def test_generation_requests_accept_optional_cut_draft_revision():
    cut_request = schemas.CutRequest(
        ranges=[],
        cutDraftRevision=4,
    )
    composition_request = schemas.PreviewCompositionRequest(
        ranges=[],
        cutDraftRevision=4,
    )

    assert cut_request.cutDraftRevision == 4
    assert composition_request.cutDraftRevision == 4
    assert schemas.CutRequest(ranges=[]).cutDraftRevision is None
    assert schemas.PreviewCompositionRequest(ranges=[]).cutDraftRevision is None
