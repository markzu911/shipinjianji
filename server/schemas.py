from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeleteRange(BaseModel):
    start: float
    end: float


class CutRequest(BaseModel):
    ranges: list[DeleteRange]
    historyName: str | None = Field(default=None, max_length=80)


class CutDraftTextRange(DeleteRange):
    key: str = Field(min_length=1, max_length=120)
    text: str = Field(default="", max_length=5000)
    originalStart: float | None = Field(default=None, ge=0, le=86400)
    originalEnd: float | None = Field(default=None, ge=0, le=86400)
    adjacentSilenceBefore: float = Field(default=0, ge=0, le=86400)
    adjacentSilenceAfter: float = Field(default=0, ge=0, le=86400)


class CutDraftNoSpeechRange(DeleteRange):
    key: str = Field(min_length=1, max_length=120)


class CutDraftRequest(BaseModel):
    revision: int = Field(default=0, ge=0)
    automaticNoSpeechInitialized: bool = False
    textRanges: list[CutDraftTextRange] = Field(default_factory=list, max_length=500)
    noSpeechRanges: list[CutDraftNoSpeechRange] = Field(
        default_factory=list,
        max_length=500,
    )
    timelineRanges: list[DeleteRange] = Field(default_factory=list, max_length=500)


class JobCleanupRequest(BaseModel):
    maxAgeDays: int | None = Field(default=None, ge=0, le=3650)
    maxDirectories: int | None = Field(default=None, ge=0, le=10000)
    dryRun: bool = False


class ModelProviderUpdate(BaseModel):
    apiKey: str | None = Field(default=None, max_length=4096)
    models: dict[str, str] = Field(default_factory=dict)
    requestUrls: dict[str, str] = Field(default_factory=dict)


class TranscriptWordUpdate(BaseModel):
    segmentIndex: int = Field(ge=0)
    wordIndex: int | None = Field(default=None, ge=0)
    text: str = Field(min_length=1, max_length=200)


class TranscriptTextUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


class TranscriptSegmentOperation(BaseModel):
    segmentIndex: int = Field(ge=0)
    action: Literal["split", "merge_up", "merge_down", "text"]
    selectionStart: int | None = Field(default=None, ge=0)
    selectionEnd: int | None = Field(default=None, ge=0)
    text: str | None = Field(default=None, max_length=500)


class ArtTextAnimation(BaseModel):
    type: Literal["none", "character-bounce"] = "none"
    duration: float = Field(default=0.56, ge=0.2, le=2.0)
    stagger: float = Field(default=0.07, ge=0.0, le=0.3)
    amplitude: float = Field(default=0.18, ge=0.05, le=0.5)


class ArtTextCharacterTiming(BaseModel):
    start: float = Field(ge=0, le=86400)
    end: float = Field(gt=0, le=86400)


class ArtTextCharacterLayout(BaseModel):
    type: Literal["none", "staggered"] = "none"
    rotationPattern: list[float] = Field(default_factory=list, max_length=12)
    verticalOffsetPattern: list[float] = Field(default_factory=list, max_length=12)


class TextOverlay(BaseModel):
    text: str
    font: str
    fontSize: int
    color: str
    strokeColor: str
    strokeWidth: int
    shadow: bool
    x: float
    y: float
    start: float
    end: float
    direction: str = "horizontal"
    textAlign: str = "center"
    charsPerLine: int = 10
    letterSpacing: int = 0
    lineSpacing: int = 8
    artStyle: str = "impact"
    textColorMode: Literal["solid", "center-highlight"] = "solid"
    secondaryColor: str = "#FFFFFF"
    animation: ArtTextAnimation = Field(default_factory=ArtTextAnimation)
    characterLayout: ArtTextCharacterLayout = Field(
        default_factory=ArtTextCharacterLayout
    )
    characterTimings: list[ArtTextCharacterTiming] = Field(
        default_factory=list,
        max_length=500,
    )
    trackId: str | None = Field(default=None, max_length=80)
    trackType: Literal["transcript"] | None = None
    sourceStart: float | None = Field(default=None, ge=0, le=86400)
    sourceEnd: float | None = Field(default=None, gt=0, le=86400)


class ArtTextRequest(BaseModel):
    overlays: list[TextOverlay]
    source: Literal["original", "edited"] = "edited"
    historyName: str | None = Field(default=None, max_length=80)


class TranscriptArtTextTrackRequest(BaseModel):
    source: Literal["original", "edited"] = "edited"
    font: str = Field(min_length=1, max_length=120)
    fontSize: int = Field(ge=20, le=180)
    letterSpacing: int = Field(default=0, ge=0, le=20)
    strokeWidth: int = Field(default=3, ge=0, le=12)
    draftTranscript: dict[str, Any] | None = None
    draftDuration: float | None = Field(default=None, gt=0, le=86400)


class ArtTextSuggestionRequest(BaseModel):
    count: int
    source: Literal["original", "edited"] = "edited"
    existingOverlays: list[TextOverlay] = Field(default_factory=list)
    draftTranscript: dict[str, Any] | None = None
    draftDuration: float | None = Field(default=None, gt=0, le=86400)


class PictureInPictureImageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    start: float
    end: float
    mode: Literal["custom", "auto"] = "custom"
    prompt: str = Field(default="", max_length=800)
    source: Literal["original", "edited", "art"] = "art"
    aspectRatio: Literal["1:1", "3:4", "4:3", "16:9", "9:16"] = "16:9"
    sourceStart: float | None = Field(default=None, ge=0, le=86400)
    sourceEnd: float | None = Field(default=None, gt=0, le=86400)


class PictureInPictureVideoRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    start: float
    end: float
    mode: Literal["custom", "auto"] = "custom"
    prompt: str = Field(default="", max_length=800)
    source: Literal["original", "edited", "art"] = "art"
    aspectRatio: Literal["1:1", "3:4", "4:3", "16:9", "9:16"] = "16:9"
    sourceStart: float | None = Field(default=None, ge=0, le=86400)
    sourceEnd: float | None = Field(default=None, gt=0, le=86400)


class PictureInPicturePromptRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    start: float
    end: float
    assetType: Literal["image", "video"] = "image"
    source: Literal["original", "edited", "art"] = "art"
    aspectRatio: Literal["1:1", "3:4", "4:3", "16:9", "9:16"] = "16:9"
    sourceStart: float | None = Field(default=None, ge=0, le=86400)
    sourceEnd: float | None = Field(default=None, gt=0, le=86400)


class PictureInPictureOverlay(BaseModel):
    assetId: str = ""
    imageId: str = ""
    start: float | None = None
    end: float | None = None
    sourceStart: float | None = Field(default=None, ge=0, le=86400)
    sourceEnd: float | None = Field(default=None, gt=0, le=86400)
    x: float = 0.78
    y: float = 0.22
    width: float = 0.32


class PictureInPictureRequest(BaseModel):
    overlays: list[PictureInPictureOverlay]
    source: Literal["original", "edited", "art"] = "art"


class PreviewCompositionRequest(BaseModel):
    # `all` is the shared editor action. The legacy targets remain accepted
    # for older embedded pages, but composition always renders every supplied
    # layer in one request.
    target: Literal["all", "art", "pip"] = "all"
    ranges: list[DeleteRange]
    artOverlays: list[TextOverlay] = Field(default_factory=list)
    artSource: Literal["original", "edited"] = "original"
    pictureInPictureOverlays: list[PictureInPictureOverlay] = Field(
        default_factory=list
    )
    pictureInPictureSource: Literal["original", "edited", "art"] = "original"
    historyName: str | None = Field(default=None, max_length=80)


class FontUpdate(BaseModel):
    name: str


class ArtTemplateUpdate(BaseModel):
    name: str


class ArtPositionPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    x: float
    y: float


class ArtPositionPresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    x: float | None = None
    y: float | None = None


class HistoryVersionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class HistoryVersionCreate(BaseModel):
    kind: Literal["edited", "art"]
    name: str | None = Field(default=None, max_length=80)


__all__ = (
    "DeleteRange",
    "CutRequest",
    "CutDraftTextRange",
    "CutDraftNoSpeechRange",
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
