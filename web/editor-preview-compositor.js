(function exposeEditorPreview(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorPreview = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function editorPreviewFactory(root) {
    "use strict";

    const PIP_MIN_WIDTH = 0.2;
    const ART_POSITION_MIN = 0.05;
    const ART_POSITION_MAX = 0.95;
    const RESIZE_DIRECTIONS = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
    const FONT_FAMILIES = {
      modern: '"Microsoft YaHei", sans-serif',
      bold: '"Microsoft YaHei", sans-serif',
      classic: '"SimHei", sans-serif',
      song: '"SimSun", serif',
      kai: '"KaiTi", serif',
      fang: '"FangSong", serif',
    };
    const LINE_END_FORBIDDEN_PUNCTUATION = new Set(
      [..."（([【《〈「『“‘"],
    );
    const LINE_START_FORBIDDEN_PUNCTUATION = new Set(
      [..."，。！？；：、,.!?;:）)]】》〉」』”’％%…—"],
    );

    function finiteNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function clamp(value, minimum, maximum) {
      return Math.min(maximum, Math.max(minimum, value));
    }

    function stableValue(value) {
      if (Array.isArray(value)) return value.map(stableValue);
      if (!value || typeof value !== "object") return value;
      return Object.fromEntries(
        Object.keys(value)
          .sort()
          .map((key) => [key, stableValue(value[key])]),
      );
    }

    function stableSignature(value) {
      return JSON.stringify(stableValue(value));
    }

    function normalizedColor(value, fallback) {
      const color = String(value || "").trim();
      return /^#[0-9a-f]{6}$/i.test(color) ? color : fallback;
    }

    function shiftHexColor(value, amount) {
      const hex = normalizedColor(value, "#FFFFFF");
      const number = Number.parseInt(hex.slice(1), 16);
      const channels = [number >> 16, (number >> 8) & 255, number & 255];
      const shifted = channels.map((channel) =>
        clamp(
          Math.round(
            amount >= 0
              ? channel + (255 - channel) * amount
              : channel * (1 + amount),
          ),
          0,
          255,
        ),
      );
      return `#${shifted
        .map((channel) => channel.toString(16).padStart(2, "0"))
        .join("")}`;
    }

    function hexWithAlpha(value, alpha) {
      const hex = normalizedColor(value, "#000000").slice(1);
      const red = Number.parseInt(hex.slice(0, 2), 16);
      const green = Number.parseInt(hex.slice(2, 4), 16);
      const blue = Number.parseInt(hex.slice(4, 6), 16);
      return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
    }

    function normalizeEffects(overlay) {
      const animation = overlay.animation || {};
      const layout = overlay.characterLayout || {};
      const staggered = layout.type === "staggered";
      const rotations = Array.isArray(layout.rotationPattern)
        ? layout.rotationPattern
            .slice(0, 12)
            .map((value) => clamp(finiteNumber(value), -12, 12))
        : [];
      const offsets = Array.isArray(layout.verticalOffsetPattern)
        ? layout.verticalOffsetPattern
            .slice(0, 12)
            .map((value) => clamp(finiteNumber(value), -0.25, 0.25))
        : [];
      return {
        textColorMode:
          overlay.textColorMode === "center-highlight"
            ? "center-highlight"
            : "solid",
        secondaryColor: normalizedColor(
          overlay.secondaryColor,
          normalizedColor(overlay.color, "#FFFFFF"),
        ),
        animation: {
          type:
            animation.type === "character-bounce"
              ? "character-bounce"
              : "none",
          duration: clamp(finiteNumber(animation.duration, 0.56), 0.2, 2),
          stagger: clamp(finiteNumber(animation.stagger, 0.07), 0, 0.3),
          amplitude: clamp(finiteNumber(animation.amplitude, 0.18), 0.05, 0.5),
        },
        characterLayout: {
          type: staggered ? "staggered" : "none",
          rotationPattern: staggered
            ? rotations.length
              ? rotations
              : [-7, 5, -4, 3, -6, 4]
            : [],
          verticalOffsetPattern: staggered
            ? offsets.length
              ? offsets
              : [0.06, -0.04, 0.03, -0.05]
            : [],
        },
      };
    }

    function normalizeCharacterTimings(value) {
      return (Array.isArray(value) ? value : [])
        .map((timing) => ({
          start: finiteNumber(timing?.start, Number.NaN),
          end: finiteNumber(timing?.end, Number.NaN),
        }))
        .filter(
          (timing) =>
            Number.isFinite(timing.start) &&
            Number.isFinite(timing.end) &&
            timing.end > timing.start,
        );
    }

    function sanitizeArtOverlay(value, index) {
      const id = String(value?.id ?? value?.trackId ?? `art-overlay-${index}`);
      return {
        id,
        text: String(value?.text || ""),
        font: String(value?.font || "modern"),
        fontSize: Math.max(1, finiteNumber(value?.fontSize, 42)),
        color: normalizedColor(value?.color, "#FFFFFF"),
        strokeColor: normalizedColor(value?.strokeColor, "#111111"),
        strokeWidth: Math.max(0, finiteNumber(value?.strokeWidth, 2)),
        shadow: value?.shadow !== false,
        x: finiteNumber(value?.x, 0.5),
        y: finiteNumber(value?.y, 0.5),
        start: finiteNumber(value?.start),
        end: finiteNumber(value?.end),
        direction: value?.direction === "vertical" ? "vertical" : "horizontal",
        textAlign: ["left", "right", "center"].includes(value?.textAlign)
          ? value.textAlign
          : "center",
        charsPerLine: Math.max(0, Math.round(finiteNumber(value?.charsPerLine))),
        letterSpacing: clamp(Math.round(finiteNumber(value?.letterSpacing)), -20, 40),
        lineSpacing: finiteNumber(value?.lineSpacing, 8),
        artStyle: String(value?.artStyle || "impact"),
        characterTimings: normalizeCharacterTimings(value?.characterTimings),
        trackId: value?.trackId == null ? null : String(value.trackId),
        trackType: value?.trackType == null ? null : String(value.trackType),
        ...normalizeEffects(value || {}),
      };
    }

    function sanitizePipOverlay(value, index) {
      const assetId = String(value?.assetId || value?.imageId || "");
      return {
        id: String(value?.id ?? assetId ?? `pip-overlay-${index}`),
        assetId,
        start: finiteNumber(value?.start),
        end: finiteNumber(value?.end),
        x: finiteNumber(value?.x, 0.8),
        y: finiteNumber(value?.y, 0.2),
        width: Math.max(PIP_MIN_WIDTH, finiteNumber(value?.width, 0.32)),
        enabled: value?.enabled !== false,
      };
    }

    function sanitizeAsset(value) {
      const id = String(value?.id || value?.assetId || value?.imageId || "");
      return {
        id,
        type:
          value?.type === "video" || value?.assetType === "video"
            ? "video"
            : "image",
        url: String(value?.assetUrl || value?.imageUrl || value?.url || ""),
        status: String(value?.status || "completed"),
        text: String(value?.text || ""),
        aspectRatio: Math.max(0, finiteNumber(value?.aspectRatio)),
      };
    }

    function assetsFrom(value) {
      const records = Array.isArray(value)
        ? value
        : value && typeof value === "object"
          ? Object.values(value)
          : [];
      const assets = new Map();
      for (const record of records) {
        const asset = sanitizeAsset(record);
        if (asset.id) assets.set(asset.id, asset);
      }
      return assets;
    }

    function balanceHorizontalLine(sourceLine, limit) {
      const characters = [...sourceLine];
      if (limit <= 0 || characters.length <= limit) return [sourceLine];
      const lineCount = Math.ceil(characters.length / limit);
      const averageLength = characters.length / lineCount;
      const baseLength = Math.floor(characters.length / lineCount);
      const longerLineCount = characters.length % lineCount;
      const preferredLengths = Array.from(
        { length: lineCount },
        (_, index) => baseLength + (index < longerLineCount ? 1 : 0),
      );
      const costs = Array.from(
        { length: lineCount + 1 },
        () => Array(characters.length + 1).fill(Number.POSITIVE_INFINITY),
      );
      const previousBreaks = Array.from(
        { length: lineCount + 1 },
        () => Array(characters.length + 1).fill(-1),
      );
      costs[0][0] = 0;
      for (let lineIndex = 1; lineIndex <= lineCount; lineIndex += 1) {
        const remainingLines = lineCount - lineIndex;
        for (let end = lineIndex; end <= characters.length; end += 1) {
          const remaining = characters.length - end;
          if (remaining < remainingLines || remaining > remainingLines * limit) {
            continue;
          }
          const firstStart = Math.max(lineIndex - 1, end - limit);
          for (let start = firstStart; start < end; start += 1) {
            if (!Number.isFinite(costs[lineIndex - 1][start])) continue;
            if (
              end < characters.length &&
              (
                LINE_END_FORBIDDEN_PUNCTUATION.has(characters[end - 1]) ||
                LINE_START_FORBIDDEN_PUNCTUATION.has(characters[end])
              )
            ) {
              continue;
            }
            const length = end - start;
            const cost =
              costs[lineIndex - 1][start] +
              (length - averageLength) ** 2 * 100 +
              (length - preferredLengths[lineIndex - 1]) ** 2;
            if (cost < costs[lineIndex][end]) {
              costs[lineIndex][end] = cost;
              previousBreaks[lineIndex][end] = start;
            }
          }
        }
      }
      if (previousBreaks[lineCount][characters.length] < 0) {
        const lines = [];
        let start = 0;
        for (const length of preferredLengths) {
          lines.push(characters.slice(start, start + length).join(""));
          start += length;
        }
        return lines;
      }
      const lines = [];
      let end = characters.length;
      for (let lineIndex = lineCount; lineIndex > 0; lineIndex -= 1) {
        const start = previousBreaks[lineIndex][end];
        lines.push(characters.slice(start, end).join(""));
        end = start;
      }
      return lines.reverse();
    }

    function formatArtText(overlay) {
      const wrappedLines = [];
      for (const sourceLine of overlay.text.split(/\r?\n/)) {
        const characters = [...sourceLine];
        if (!characters.length || !overlay.charsPerLine) {
          wrappedLines.push(sourceLine);
        } else if (overlay.direction === "horizontal") {
          wrappedLines.push(
            ...balanceHorizontalLine(sourceLine, overlay.charsPerLine),
          );
        } else {
          for (let index = 0; index < characters.length; index += overlay.charsPerLine) {
            wrappedLines.push(
              characters.slice(index, index + overlay.charsPerLine).join(""),
            );
          }
        }
      }
      if (overlay.direction === "vertical") {
        const columns = [...wrappedLines].reverse();
        const gap = "\u200a".repeat(Math.max(1, Math.round(overlay.lineSpacing / 2)));
        const rows = Math.max(0, ...columns.map((column) => [...column].length));
        return Array.from({ length: rows }, (_, row) =>
          columns.map((column) => [...column][row] ?? "\u3000").join(gap),
        ).join("\n");
      }
      const gap = "\u200a".repeat(Math.max(0, Math.round(overlay.letterSpacing / 2)));
      return wrappedLines
        .map((line) => (gap ? [...line].join(gap) : line))
        .join("\n");
    }

    function createCompositor(options = {}) {
      const host = options.root;
      const mediaController = options.mediaController;
      if (!host) throw new Error("EditorPreview requires a root element.");
      if (typeof mediaController?.currentEditedTime !== "function") {
        throw new Error("EditorPreview requires an EditorMedia controller.");
      }
      const document = host.ownerDocument || root.document;
      if (!document?.createElement || !document?.createTextNode) {
        throw new Error("EditorPreview requires DOM creation APIs.");
      }

      const artLayer = document.createElement("div");
      artLayer.className = "editor-preview-art-layer overlay-layer is-art";
      artLayer.dataset.effectKind = "art";
      const pipLayer = document.createElement("div");
      pipLayer.className = "editor-preview-pip-layer pip-overlay-layer is-pip";
      pipLayer.dataset.effectKind = "pip";
      host.append(artLayer, pipLayer);

      const artRecords = new Map();
      const pipRecords = new Map();
      let currentTimeline = null;
      let modelSignature = "";
      let activePointer = null;
      let destroyed = false;

      function isPlaying() {
        const video = mediaController.video?.();
        return video ? !video.paused && !video.ended : false;
      }

      function previewScale() {
        const videoWidth = finiteNumber(mediaController.video?.()?.videoWidth);
        const layerWidth = finiteNumber(artLayer.clientWidth || host.clientWidth);
        return videoWidth > 0 && layerWidth > 0 ? layerWidth / videoWidth : 1;
      }

      function renderArtCharacters(record, currentTime, playing) {
        const { node, overlay } = record;
        const text = formatArtText(overlay) || "请输入文字";
        const visibleCount = [...text].filter((character) => !/\s/u.test(character)).length;
        const hasSpeechTimings = overlay.characterTimings.length === visibleCount;
        const animate =
          overlay.animation.type === "character-bounce" && hasSpeechTimings;
        const staggered = overlay.characterLayout.type === "staggered";
        const needsCharacters =
          overlay.textColorMode === "center-highlight" || animate || staggered;
        node.classList.toggle("has-character-effect", needsCharacters);
        node.setAttribute("aria-label", text);
        if (!needsCharacters) {
          node.textContent = text;
          return;
        }
        const highlightStart = Math.floor(visibleCount * 0.25);
        const highlightEnd = Math.ceil(visibleCount * 0.75);
        const nodes = [];
        let visibleIndex = 0;
        for (const character of text) {
          if (/\s/u.test(character)) {
            nodes.push(document.createTextNode(character));
            continue;
          }
          const span = document.createElement("span");
          span.className = "art-character";
          span.textContent = character;
          span.setAttribute("aria-hidden", "true");
          if (overlay.textColorMode === "center-highlight") {
            span.style.color =
              highlightStart <= visibleIndex && visibleIndex < highlightEnd
                ? overlay.color
                : overlay.secondaryColor;
          }
          if (staggered) {
            const rotations = overlay.characterLayout.rotationPattern;
            const offsets = overlay.characterLayout.verticalOffsetPattern;
            span.classList.add("is-character-staggered");
            span.style.setProperty(
              "--art-character-rotation",
              `${rotations[visibleIndex % rotations.length]}deg`,
            );
            span.style.setProperty(
              "--art-character-offset",
              `${offsets[visibleIndex % offsets.length]}em`,
            );
          }
          if (animate) {
            const timing = overlay.characterTimings[visibleIndex];
            const spokenDuration = timing.end - timing.start;
            span.classList.add("is-character-bounce");
            span.style.animationDuration = `${Math.min(
              overlay.animation.duration,
              Math.max(0.2, spokenDuration + 0.18),
            )}s`;
            span.style.animationDelay = `${timing.start - currentTime}s`;
            span.style.animationPlayState = playing ? "running" : "paused";
            span.style.setProperty(
              "--art-character-lift",
              `${overlay.animation.amplitude}em`,
            );
          }
          nodes.push(span);
          visibleIndex += 1;
        }
        node.replaceChildren(...nodes);
      }

      function applyArtStyle(record) {
        const { node, overlay } = record;
        const scale = previewScale();
        const stroke = Math.max(0, overlay.strokeWidth * scale);
        const style = node.style;
        style.fontFamily = FONT_FAMILIES[overlay.font] || overlay.font || FONT_FAMILIES.modern;
        style.fontWeight = overlay.font === "bold" ? "800" : "700";
        style.fontSize = `${Math.max(10, overlay.fontSize * scale)}px`;
        style.lineHeight = `${Math.max(
          10,
          (overlay.fontSize +
            (overlay.direction === "vertical"
              ? overlay.letterSpacing
              : overlay.lineSpacing)) *
            scale,
        )}px`;
        style.textAlign = overlay.textAlign;
        style.color = overlay.color;
        style.background = "transparent";
        style.backgroundClip = "border-box";
        style.webkitBackgroundClip = "border-box";
        style.border = "0";
        style.borderLeft = "0";
        style.borderRadius = "0";
        style.padding = "2px 6px";
        style.boxShadow = "none";
        style.clipPath = "none";
        style.webkitTextStroke = `${stroke}px ${overlay.strokeColor}`;
        style.paintOrder = "stroke fill";
        style.textShadow = "none";
        const artStyle = overlay.artStyle;
        if (artStyle === "neon") {
          style.color = "#FFFFFF";
          style.webkitTextStroke = `${Math.max(1, stroke)}px ${overlay.color}`;
          style.textShadow = [
            `0 0 ${Math.max(3, 5 * scale)}px ${overlay.color}`,
            `0 0 ${Math.max(6, 12 * scale)}px ${overlay.color}`,
            `0 0 ${Math.max(10, 22 * scale)}px ${overlay.color}`,
          ].join(",");
        } else if (["gradient", "ice", "metal"].includes(artStyle)) {
          const gradient =
            artStyle === "ice"
              ? `linear-gradient(180deg, #ffffff 4%, ${shiftHexColor(overlay.color, 0.32)} 42%, ${overlay.color} 100%)`
              : artStyle === "metal"
                ? `linear-gradient(180deg, ${shiftHexColor(overlay.color, 0.72)} 5%, ${overlay.color} 48%, ${shiftHexColor(overlay.color, -0.38)} 94%)`
                : `linear-gradient(180deg, ${shiftHexColor(overlay.color, 0.48)} 4%, ${overlay.color} 52%, #ff4d8d 100%)`;
          style.color = "transparent";
          style.background = gradient;
          style.backgroundClip = "text";
          style.webkitBackgroundClip = "text";
          style.webkitTextStroke = `${Math.max(1, stroke + 1)}px ${overlay.strokeColor}`;
          style.textShadow =
            artStyle === "ice"
              ? `0 0 ${Math.max(4, 7 * scale)}px ${overlay.color}`
              : `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px rgba(0,0,0,.58)`;
        } else if (artStyle === "comic") {
          style.webkitTextStroke = `${Math.max(2, stroke + 2)}px ${overlay.strokeColor}`;
          style.textShadow = `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px rgba(21,19,17,.58)`;
        } else if (["ink", "ribbon", "luxury", "sticker"].includes(artStyle)) {
          style.color = artStyle === "ink" ? overlay.strokeColor : "#FFFFFF";
          style.background = artStyle === "luxury" ? "rgba(7, 9, 14, .9)" : overlay.color;
          style.border = `${Math.max(1, stroke)}px solid ${artStyle === "sticker" ? "rgba(255,255,255,.95)" : overlay.color}`;
          style.borderRadius = `${Math.max(4, 8 * scale)}px`;
          style.padding = `${Math.max(5, 9 * scale)}px ${Math.max(10, 18 * scale)}px`;
          style.webkitTextStroke = artStyle === "ink" ? "0" : `${Math.min(2, stroke)}px ${overlay.strokeColor}`;
          if (artStyle === "ink") {
            style.borderLeft = `${Math.max(4, 7 * scale)}px solid #c7302b`;
          } else if (artStyle === "ribbon") {
            style.border = "0";
            style.clipPath = "polygon(9% 0, 91% 0, 100% 50%, 91% 100%, 9% 100%, 0 50%)";
          } else if (artStyle === "luxury") {
            style.color = overlay.color;
          }
          style.boxShadow = overlay.shadow
            ? `0 ${Math.max(3, 5 * scale)}px ${Math.max(5, 10 * scale)}px rgba(0,0,0,.38)`
            : "none";
        } else if (artStyle === "clean") {
          style.textShadow = overlay.shadow
            ? `0 ${Math.max(1, scale)}px ${Math.max(2, 5 * scale)}px rgba(0,0,0,.62)`
            : "none";
        } else {
          style.webkitTextStroke = `${Math.max(1, stroke)}px ${overlay.strokeColor}`;
          style.textShadow = [
            "-1px -1px 0 #fff",
            "1px -1px 0 #fff",
            "-1px 1px 0 #fff",
            "1px 1px 0 #fff",
            `0 0 ${Math.max(2, 5 * scale)}px ${hexWithAlpha(overlay.strokeColor, 0.49)}`,
          ].join(",");
        }
      }

      function positionArt(record) {
        const { node, overlay } = record;
        const width = finiteNumber(artLayer.clientWidth || host.clientWidth);
        const height = finiteNumber(artLayer.clientHeight || host.clientHeight);
        if (!width || !height || node.hidden) {
          node.style.left = `${overlay.x * 100}%`;
          node.style.top = `${overlay.y * 100}%`;
          node.style.transform = "translate(-50%, -50%)";
          return;
        }
        const marginX = width * 0.04;
        const marginY = height * 0.04;
        const elementWidth = Math.max(1, finiteNumber(node.offsetWidth, 1));
        const elementHeight = Math.max(1, finiteNumber(node.offsetHeight, 1));
        const fitScale = Math.min(
          1,
          (width - marginX * 2) / elementWidth,
          (height - marginY * 2) / elementHeight,
        );
        const scaledWidth = elementWidth * fitScale;
        const scaledHeight = elementHeight * fitScale;
        const centerX = clamp(
          overlay.x * width,
          marginX + scaledWidth / 2,
          width - marginX - scaledWidth / 2,
        );
        const centerY = clamp(
          overlay.y * height,
          marginY + scaledHeight / 2,
          height - marginY - scaledHeight / 2,
        );
        node.style.left = `${centerX}px`;
        node.style.top = `${centerY}px`;
        node.style.transform = `translate(-50%, -50%) scale(${fitScale})`;
      }

      function createArtRecord(overlay) {
        const node = document.createElement("div");
        node.className = "preview-overlay";
        node.dataset.overlayId = overlay.id;
        node.dataset.effectKind = "art";
        node.setAttribute("role", "button");
        node.setAttribute("tabindex", "0");
        node.addEventListener("pointerdown", beginPointer);
        return { node, overlay, signature: "", animationSignature: "" };
      }

      function updateArtRecord(record, overlay, currentTime, playing) {
        record.overlay = overlay;
        record.node.dataset.overlayId = overlay.id;
        record.node.dataset.artStyle = overlay.artStyle;
        const signature = stableSignature(overlay);
        if (record.signature !== signature) {
          record.signature = signature;
          record.animationSignature = "";
          renderArtCharacters(record, currentTime, playing);
          applyArtStyle(record);
        }
      }

      function safeAssetUrl(value) {
        const url = String(value || "").trim();
        return /^javascript:/i.test(url) ? "" : url;
      }

      function createPipMedia(asset) {
        const media = document.createElement(asset.type === "video" ? "video" : "img");
        media.src = safeAssetUrl(asset.url);
        if (asset.type === "video") {
          media.muted = true;
          media.loop = true;
          media.playsInline = true;
          media.preload = "auto";
          media.setAttribute("aria-hidden", "true");
          media.addEventListener("loadedmetadata", syncTime, { once: true });
        } else {
          media.alt = asset.text ? `画中画：${asset.text}` : "画中画";
          media.draggable = false;
        }
        return media;
      }

      function createPipRecord(overlay, asset) {
        const node = document.createElement("button");
        node.type = "button";
        node.className = "pip-preview-item";
        node.dataset.pictureId = overlay.id;
        node.dataset.effectKind = "pip";
        const hint = document.createElement("span");
        hint.className = "pip-drag-hint";
        hint.textContent = "拖动摆放 · 边角缩放";
        const handles = RESIZE_DIRECTIONS.map((direction) => {
          const handle = document.createElement("span");
          handle.className = "pip-resize-handle";
          handle.dataset.pipResize = direction;
          handle.setAttribute("aria-hidden", "true");
          return handle;
        });
        const record = {
          node,
          overlay,
          asset,
          media: createPipMedia(asset),
          hint,
          handles,
          signature: "",
        };
        node.append(record.media, hint, ...handles);
        node.addEventListener("pointerdown", beginPointer);
        return record;
      }

      function updatePipRecord(record, overlay, asset) {
        const mediaChanged =
          record.asset.type !== asset.type || record.asset.url !== asset.url;
        record.overlay = overlay;
        record.asset = asset;
        record.node.dataset.pictureId = overlay.id;
        if (mediaChanged) {
          record.media.pause?.();
          record.media = createPipMedia(asset);
          record.node.replaceChildren(record.media, record.hint, ...record.handles);
        }
        const signature = stableSignature({ overlay, asset });
        if (record.signature === signature) return;
        record.signature = signature;
        record.node.style.left = `${overlay.x * 100}%`;
        record.node.style.top = `${overlay.y * 100}%`;
        record.node.style.width = `${Math.max(PIP_MIN_WIDTH, overlay.width) * 100}%`;
        record.node.setAttribute(
          "aria-label",
          `拖动“${asset.text || "画中画"}”调整位置，拖动边框控制点缩放`,
        );
        record.node.title = "拖动画面调整位置，拖动边框控制点缩放";
      }

      function timelineClipFor(kind, id) {
        const tracks = Array.isArray(currentTimeline?.tracks)
          ? currentTimeline.tracks
          : [];
        for (const track of tracks) {
          if (track?.kind && track.kind !== kind) continue;
          for (const clip of Array.isArray(track?.clips) ? track.clips : []) {
            const clipId = String(clip?.id || "");
            const sourceId = String(
              clip?.sourceId ??
                clip?.payload?.overlayId ??
                clip?.payload?.assetId ??
                "",
            );
            if (
              sourceId === id ||
              clipId === id ||
              clipId === `${kind}:${id}` ||
              clipId.replace(/^(art|pip):/, "") === id
            ) {
              return clip;
            }
          }
        }
        return null;
      }

      function updateSelection() {
        const selectedClipId = String(currentTimeline?.selection?.clipId || "");
        for (const [id, record] of artRecords) {
          const clip = timelineClipFor("art", id);
          record.node.classList.toggle(
            "is-selected",
            Boolean(selectedClipId) &&
              [id, `art:${id}`, String(clip?.id || "")].includes(selectedClipId),
          );
          if (clip?.id) record.node.dataset.timelineClipId = String(clip.id);
          else delete record.node.dataset.timelineClipId;
        }
        for (const [id, record] of pipRecords) {
          const clip = timelineClipFor("pip", id);
          record.node.classList.toggle(
            "is-selected",
            Boolean(selectedClipId) &&
              [id, `pip:${id}`, String(clip?.id || "")].includes(selectedClipId),
          );
          if (clip?.id) record.node.dataset.timelineClipId = String(clip.id);
          else delete record.node.dataset.timelineClipId;
        }
      }

      function reconcileArt(overlays, currentTime, playing) {
        const ids = new Set(overlays.map((overlay) => overlay.id));
        for (const [id, record] of artRecords) {
          if (ids.has(id)) continue;
          if (activePointer?.record === record) endPointer(null, true);
          record.node.removeEventListener("pointerdown", beginPointer);
          record.node.remove();
          artRecords.delete(id);
        }
        for (const overlay of overlays) {
          let record = artRecords.get(overlay.id);
          if (!record) {
            record = createArtRecord(overlay);
            artRecords.set(overlay.id, record);
          }
          updateArtRecord(record, overlay, currentTime, playing);
          artLayer.append(record.node);
        }
      }

      function reconcilePip(overlays, assets) {
        const renderable = overlays
          .map((overlay) => ({ overlay, asset: assets.get(overlay.assetId) }))
          .filter(
            ({ overlay, asset }) =>
              overlay.enabled &&
              asset &&
              asset.url &&
              asset.status !== "failed",
          );
        const ids = new Set(renderable.map(({ overlay }) => overlay.id));
        for (const [id, record] of pipRecords) {
          if (ids.has(id)) continue;
          if (activePointer?.record === record) endPointer(null, true);
          record.media.pause?.();
          record.node.removeEventListener("pointerdown", beginPointer);
          record.node.remove();
          pipRecords.delete(id);
        }
        for (const { overlay, asset } of renderable) {
          let record = pipRecords.get(overlay.id);
          if (!record) {
            record = createPipRecord(overlay, asset);
            pipRecords.set(overlay.id, record);
          }
          updatePipRecord(record, overlay, asset);
          pipLayer.append(record.node);
        }
      }

      function activeAtTime(overlay, currentTime) {
        return currentTime >= overlay.start && currentTime < overlay.end;
      }

      function artAnimationSignature(overlay, currentTime, playing) {
        if (
          overlay.animation.type !== "character-bounce" ||
          !overlay.characterTimings.length
        ) {
          return "";
        }
        let activeIndex = -1;
        for (let index = 0; index < overlay.characterTimings.length; index += 1) {
          if (currentTime + 0.0001 < overlay.characterTimings[index].start) break;
          activeIndex = index;
        }
        return playing
          ? `spoken:${activeIndex}:playing`
          : `spoken:${activeIndex}:paused:${Math.round(currentTime * 24)}`;
      }

      function syncPipVideo(record, currentTime, playing) {
        if (record.asset.type !== "video") return;
        const media = record.media;
        const duration = finiteNumber(media.duration);
        if (finiteNumber(media.readyState) < 1 || duration <= 0) return;
        const localTime = Math.max(0, currentTime - record.overlay.start) % Math.max(0.1, duration);
        if (Math.abs(finiteNumber(media.currentTime) - localTime) > 0.35) {
          media.currentTime = localTime;
        }
        if (playing) {
          if (media.paused) {
            const promise = media.play?.();
            promise?.catch?.(() => {});
          }
        } else if (!media.paused) {
          media.pause?.();
        }
      }

      function syncTime() {
        if (destroyed || activePointer) return false;
        const currentTime = Math.max(0, finiteNumber(mediaController.currentEditedTime()));
        const playing = isPlaying();
        for (const record of artRecords.values()) {
          const visible = activeAtTime(record.overlay, currentTime);
          record.node.hidden = !visible;
          if (!visible) continue;
          const animationSignature = artAnimationSignature(
            record.overlay,
            currentTime,
            playing,
          );
          if (record.animationSignature !== animationSignature) {
            record.animationSignature = animationSignature;
            renderArtCharacters(record, currentTime, playing);
          }
          positionArt(record);
        }
        for (const record of pipRecords.values()) {
          const visible = activeAtTime(record.overlay, currentTime);
          record.node.hidden = !visible;
          if (visible) syncPipVideo(record, currentTime, playing);
          else if (record.asset.type === "video" && !record.media.paused) {
            record.media.pause?.();
          }
        }
        return true;
      }

      function render(frame = {}) {
        if (destroyed) return false;
        host.dataset.projectRevision = String(frame.revision ?? "");
        host.dataset.timingRevision = String(frame.timingRevision ?? "");
        artLayer.dataset.projectRevision = host.dataset.projectRevision;
        pipLayer.dataset.projectRevision = host.dataset.projectRevision;
        const art = (Array.isArray(frame.preview?.art?.overlays)
          ? frame.preview.art.overlays
          : []).map(sanitizeArtOverlay);
        const pip = (Array.isArray(frame.preview?.pip?.overlays)
          ? frame.preview.pip.overlays
          : []).map(sanitizePipOverlay);
        const assets = assetsFrom(frame.preview?.pip?.assets);
        currentTimeline = frame.timeline || null;
        const nextSignature = stableSignature({
          artSource: String(frame.preview?.art?.source || "original"),
          art,
          pipSource: String(frame.preview?.pip?.source || "original"),
          pip,
          assets: [...assets.values()],
        });
        const currentTime = Math.max(0, finiteNumber(mediaController.currentEditedTime()));
        const playing = isPlaying();
        if (modelSignature !== nextSignature) {
          modelSignature = nextSignature;
          reconcileArt(art, currentTime, playing);
          reconcilePip(pip, assets);
        }
        updateSelection();
        syncTime();
        return true;
      }

      function pointerResizeDirection(target, boundary) {
        let node = target;
        while (node && node !== boundary) {
          if (node.dataset?.pipResize) return node.dataset.pipResize;
          node = node.parentNode;
        }
        return "";
      }

      function addPointerListeners() {
        root.addEventListener?.("pointermove", movePointer);
        root.addEventListener?.("pointerup", finishPointer);
        root.addEventListener?.("pointercancel", cancelPointer);
      }

      function removePointerListeners() {
        root.removeEventListener?.("pointermove", movePointer);
        root.removeEventListener?.("pointerup", finishPointer);
        root.removeEventListener?.("pointercancel", cancelPointer);
      }

      function beginPointer(event) {
        if (destroyed || (event.button !== undefined && event.button !== 0)) return;
        const node = event.currentTarget;
        const kind = node.dataset.effectKind;
        const id = String(node.dataset.overlayId || node.dataset.pictureId || "");
        const record = kind === "art" ? artRecords.get(id) : pipRecords.get(id);
        if (!record) return;
        const bounds = host.getBoundingClientRect();
        if (!bounds?.width || !bounds?.height) return;
        const nodeRect = node.getBoundingClientRect();
        const direction = kind === "pip" ? pointerResizeDirection(event.target, node) : "";
        const media = kind === "pip" ? record.media : null;
        const mediaAspectRatio =
          finiteNumber(media?.naturalWidth) > 0 && finiteNumber(media?.naturalHeight) > 0
            ? media.naturalWidth / media.naturalHeight
            : finiteNumber(media?.videoWidth) > 0 && finiteNumber(media?.videoHeight) > 0
              ? media.videoWidth / media.videoHeight
              : record.asset?.aspectRatio || Math.max(0.1, nodeRect.width / Math.max(1, nodeRect.height));
        event.preventDefault?.();
        if (direction) event.stopPropagation?.();
        const clip = timelineClipFor(kind, id);
        options.onSelect?.({ kind, id, clipId: String(clip?.id || `${kind}:${id}`) });
        activePointer = {
          pointerId: event.pointerId,
          kind,
          id,
          node,
          record,
          direction,
          bounds,
          startClientX: finiteNumber(event.clientX),
          startClientY: finiteNumber(event.clientY),
          startX: record.overlay.x,
          startY: record.overlay.y,
          startWidth: kind === "pip" ? record.overlay.width : 0,
          mediaAspectRatio,
          grabOffsetX: finiteNumber(event.clientX) - (nodeRect.left + nodeRect.width / 2),
          grabOffsetY: finiteNumber(event.clientY) - (nodeRect.top + nodeRect.height / 2),
          x: record.overlay.x,
          y: record.overlay.y,
          width: kind === "pip" ? record.overlay.width : 0,
          moved: false,
        };
        node.classList.add("is-selected");
        node.setPointerCapture?.(event.pointerId);
        addPointerListeners();
      }

      function pointerResizeWidth(pointer, event) {
        const deltaX = finiteNumber(event.clientX) - pointer.startClientX;
        const deltaY = finiteNumber(event.clientY) - pointer.startClientY;
        const horizontalDirection = pointer.direction.includes("e")
          ? 1
          : pointer.direction.includes("w")
            ? -1
            : 0;
        const verticalDirection = pointer.direction.includes("s")
          ? 1
          : pointer.direction.includes("n")
            ? -1
            : 0;
        const horizontalChange =
          (horizontalDirection * deltaX * 2) / pointer.bounds.width;
        const verticalChange =
          (verticalDirection * deltaY * 2 * pointer.mediaAspectRatio) /
          pointer.bounds.width;
        const change =
          horizontalDirection && verticalDirection
            ? Math.abs(horizontalChange) >= Math.abs(verticalChange)
              ? horizontalChange
              : verticalChange
            : horizontalChange || verticalChange;
        return Math.max(PIP_MIN_WIDTH, pointer.startWidth + change);
      }

      function movePointer(event) {
        const pointer = activePointer;
        if (!pointer || pointer.pointerId !== event.pointerId) return;
        const deltaX = finiteNumber(event.clientX) - pointer.startClientX;
        const deltaY = finiteNumber(event.clientY) - pointer.startClientY;
        if (!pointer.moved && Math.hypot(deltaX, deltaY) < 3) return;
        pointer.moved = true;
        if (pointer.direction) {
          pointer.width = pointerResizeWidth(pointer, event);
          pointer.node.classList.add("is-resizing");
          pointer.node.style.width = `${pointer.width * 100}%`;
          return;
        }
        pointer.node.classList.add("is-dragging");
        pointer.x = clamp(
          (finiteNumber(event.clientX) - pointer.grabOffsetX - pointer.bounds.left) /
            pointer.bounds.width,
          ART_POSITION_MIN,
          ART_POSITION_MAX,
        );
        pointer.y = clamp(
          (finiteNumber(event.clientY) - pointer.grabOffsetY - pointer.bounds.top) /
            pointer.bounds.height,
          ART_POSITION_MIN,
          ART_POSITION_MAX,
        );
        pointer.node.style.left = `${pointer.x * 100}%`;
        pointer.node.style.top = `${pointer.y * 100}%`;
        pointer.node.style.transform = "translate(-50%, -50%)";
      }

      function endPointer(event, cancelled) {
        const pointer = activePointer;
        if (!pointer || (event && pointer.pointerId !== event.pointerId)) return;
        activePointer = null;
        removePointerListeners();
        pointer.node.releasePointerCapture?.(pointer.pointerId);
        pointer.node.classList.remove("is-dragging", "is-resizing");
        if (cancelled || !pointer.moved) {
          if (pointer.kind === "art") {
            applyArtStyle(pointer.record);
            positionArt(pointer.record);
          } else {
            pointer.node.style.left = `${pointer.record.overlay.x * 100}%`;
            pointer.node.style.top = `${pointer.record.overlay.y * 100}%`;
            pointer.node.style.width = `${pointer.record.overlay.width * 100}%`;
          }
          return;
        }
        const clip = timelineClipFor(pointer.kind, pointer.id);
        const payload = {
          kind: pointer.kind,
          id: pointer.id,
          clipId: String(clip?.id || `${pointer.kind}:${pointer.id}`),
        };
        if (pointer.direction) {
          options.onResize?.({ ...payload, width: pointer.width });
        } else {
          options.onMove?.({ ...payload, x: pointer.x, y: pointer.y });
        }
      }

      function finishPointer(event) {
        endPointer(event, false);
      }

      function cancelPointer(event) {
        endPointer(event, true);
      }

      function handleResize() {
        if (destroyed) return;
        for (const record of artRecords.values()) {
          applyArtStyle(record);
          positionArt(record);
        }
      }

      const unsubscribeFrame = mediaController.subscribeFrame?.(syncTime) || (() => {});
      const unsubscribeState = mediaController.subscribeState?.(syncTime) || (() => {});
      const resizeObserver =
        typeof root.ResizeObserver === "function"
          ? new root.ResizeObserver(handleResize)
          : null;
      resizeObserver?.observe(host);

      function destroy() {
        if (destroyed) return;
        destroyed = true;
        endPointer(null, true);
        unsubscribeFrame();
        unsubscribeState();
        resizeObserver?.disconnect();
        for (const record of artRecords.values()) {
          record.node.removeEventListener("pointerdown", beginPointer);
        }
        for (const record of pipRecords.values()) {
          record.media.pause?.();
          record.node.removeEventListener("pointerdown", beginPointer);
        }
        artRecords.clear();
        pipRecords.clear();
        artLayer.remove();
        pipLayer.remove();
        delete host.dataset.projectRevision;
        delete host.dataset.timingRevision;
      }

      return Object.freeze({ destroy, render, syncTime });
    }

    return { createCompositor };
  },
);
