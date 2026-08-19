(function exposeEditorArtModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorArtModel = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function editorArtModelFactory() {
    "use strict";

    const MANUAL_OVERLAY_LIMIT = 20;
    const TRANSCRIPT_TRACK_TYPE = "transcript";
    const TRANSCRIPT_STYLE_FIELDS = Object.freeze([
      "font", "fontSize", "color", "strokeColor", "strokeWidth", "shadow",
      "x", "y", "direction", "textAlign", "charsPerLine",
      "letterSpacing", "lineSpacing", "artStyle", "textColorMode",
      "secondaryColor", "animation", "characterLayout",
    ]);
    const TRANSCRIPT_CUE_FIELDS = Object.freeze(["text"]);
    const DEFAULT_PALETTES = Object.freeze({
      impact: { color: "#FFD84D", strokeColor: "#15110A" },
      neon: { color: "#A9E7CF", strokeColor: "#173A31" },
      metal: { color: "#FFD166", strokeColor: "#5B2A00" },
      sticker: { color: "#FF4D8D", strokeColor: "#4A1028" },
      clean: { color: "#FFFFFF", strokeColor: "#071018" },
      gradient: { color: "#FF8A3D", strokeColor: "#5A1744" },
      comic: { color: "#FFE14D", strokeColor: "#E52B2B" },
      ice: { color: "#B7F4FF", strokeColor: "#1667A9" },
      ink: { color: "#F5E6C8", strokeColor: "#171512" },
      ribbon: { color: "#C66E3A", strokeColor: "#352218" },
      luxury: { color: "#F5D06F", strokeColor: "#17120A" },
    });
    const LINE_START_FORBIDDEN_PUNCTUATION = new Set(
      [..."，。！？；：、,.!?;:)]}）】》〉」』”’"],
    );
    const LINE_END_FORBIDDEN_PUNCTUATION = new Set(
      [..."([{（【《〈「『“‘"],
    );

    function clone(value) {
      if (value === undefined) return undefined;
      return JSON.parse(JSON.stringify(value));
    }

    function finiteNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function clamp(value, minimum, maximum) {
      return Math.min(maximum, Math.max(minimum, value));
    }

    function normalizeColor(value, fallback = "#FFFFFF") {
      return /^#[0-9a-f]{6}$/i.test(String(value || ""))
        ? String(value).toUpperCase()
        : fallback;
    }

    function normalizeTemplateEffects(template = {}) {
      const animation = template.animation || {};
      const characterLayout = template.characterLayout || {};
      const staggered = characterLayout.type === "staggered";
      const rotations = Array.isArray(characterLayout.rotationPattern)
        ? characterLayout.rotationPattern
            .slice(0, 12)
            .map((value) => clamp(finiteNumber(value), -12, 12))
        : [];
      const offsets = Array.isArray(characterLayout.verticalOffsetPattern)
        ? characterLayout.verticalOffsetPattern
            .slice(0, 12)
            .map((value) => clamp(finiteNumber(value), -0.25, 0.25))
        : [];
      return {
        letterSpacing: clamp(Math.round(finiteNumber(template.letterSpacing)), -20, 40),
        textColorMode:
          template.textColorMode === "center-highlight"
            ? "center-highlight"
            : "solid",
        secondaryColor: normalizeColor(
          template.secondaryColor,
          normalizeColor(template.color),
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
            ? rotations.length ? rotations : [-7, 5, -4, 3, -6, 4]
            : [],
          verticalOffsetPattern: staggered
            ? offsets.length ? offsets : [0.06, -0.04, 0.03, -0.05]
            : [],
        },
      };
    }

    function normalizeCharacterTimings(value, start = 0, end = 0, text = "") {
      const supplied = (Array.isArray(value) ? value : []).flatMap((timing) => {
        const itemStart = Number(timing?.start);
        const itemEnd = Number(timing?.end);
        return Number.isFinite(itemStart) && Number.isFinite(itemEnd) && itemEnd > itemStart
          ? [{ start: itemStart, end: itemEnd }]
          : [];
      });
      // The compose API validates timings against every visible character,
      // including punctuation. Keep this count aligned with the renderer and
      // backend so manual text such as "重点！" remains generatable.
      const count = [...String(text || "")].filter((character) => !/\s/u.test(character)).length;
      if (supplied.length === count || !count || end <= start) return supplied;
      const duration = end - start;
      return Array.from({ length: count }, (_, index) => ({
        start: start + (duration * index) / count,
        end: start + (duration * (index + 1)) / count,
      }));
    }

    function normalizeRange(start, end, duration, minimumDuration = 0.05) {
      const limit = Math.max(minimumDuration, finiteNumber(duration, minimumDuration));
      const safeStart = clamp(finiteNumber(start), 0, Math.max(0, limit - minimumDuration));
      const safeEnd = clamp(
        finiteNumber(end, safeStart + Math.min(3, limit - safeStart)),
        safeStart + minimumDuration,
        limit,
      );
      return { start: safeStart, end: safeEnd };
    }

    function nextStableId(overlays, prefix = "art-overlay") {
      const used = new Set((Array.isArray(overlays) ? overlays : []).map((item) => String(item?.id || "")));
      let index = 1;
      while (used.has(`${prefix}-${index}`)) index += 1;
      return `${prefix}-${index}`;
    }

    function normalizeOverlay(value = {}, options = {}) {
      const transcriptCue =
        value.trackType === TRANSCRIPT_TRACK_TYPE && Boolean(value.trackId);
      const minimumDuration = transcriptCue ? 0.02 : 0.05;
      const range = normalizeRange(
        value.start,
        value.end,
        options.duration ?? Math.max(finiteNumber(value.end), minimumDuration),
        minimumDuration,
      );
      const artStyle = String(value.artStyle || options.artStyle || "impact");
      const palette = options.palettes?.[artStyle] || DEFAULT_PALETTES[artStyle] || DEFAULT_PALETTES.impact;
      const effects = normalizeTemplateEffects({
        ...(options.templateEffects?.[artStyle] || {}),
        ...value,
      });
      const sourceStart = Number(value.sourceStart);
      const sourceEnd = Number(value.sourceEnd);
      const text = String(value.text || "").trim();
      return {
        ...clone(value),
        id: value.id ?? options.id ?? "art-overlay-1",
        text,
        font: String(value.font || options.font || "bold"),
        fontSize: clamp(Math.round(finiteNumber(value.fontSize, options.fontSize || 54)), 20, 180),
        color: normalizeColor(value.color, palette.color),
        strokeColor: normalizeColor(value.strokeColor, palette.strokeColor),
        strokeWidth: clamp(Math.round(finiteNumber(value.strokeWidth, 3)), 0, 12),
        shadow: value.shadow !== false,
        x: clamp(finiteNumber(value.x, 0.5), 0.05, 0.95),
        y: clamp(finiteNumber(value.y, 0.18), 0.05, 0.95),
        ...range,
        direction: value.direction === "vertical" ? "vertical" : "horizontal",
        textAlign: ["left", "center", "right"].includes(value.textAlign)
          ? value.textAlign
          : "center",
        charsPerLine: transcriptCue
          ? 0
          : clamp(Math.round(finiteNumber(value.charsPerLine, 10)), 0, 20),
        letterSpacing: clamp(effects.letterSpacing, 0, 20),
        lineSpacing: clamp(Math.round(finiteNumber(value.lineSpacing, 8)), 0, 40),
        artStyle,
        textColorMode: effects.textColorMode,
        secondaryColor: effects.secondaryColor,
        animation: effects.animation,
        characterLayout: effects.characterLayout,
        characterTimings: normalizeCharacterTimings(
          value.characterTimings,
          range.start,
          range.end,
          text,
        ),
        trackId: transcriptCue ? String(value.trackId) : null,
        trackType: transcriptCue ? TRANSCRIPT_TRACK_TYPE : null,
        sourceStart:
          Number.isFinite(sourceStart) && Number.isFinite(sourceEnd) && sourceEnd > sourceStart
            ? sourceStart
            : null,
        sourceEnd:
          Number.isFinite(sourceStart) && Number.isFinite(sourceEnd) && sourceEnd > sourceStart
            ? sourceEnd
            : null,
      };
    }

    function createOverlay(overlays, value = {}, options = {}) {
      const current = Array.isArray(overlays) ? overlays : [];
      const requestedId = value.id;
      const requestedIdAvailable =
        requestedId !== undefined &&
        requestedId !== null &&
        String(requestedId).trim() &&
        !current.some((overlay) => String(overlay?.id) === String(requestedId));
      const id = requestedIdAvailable
        ? requestedId
        : nextStableId(current, options.idPrefix);
      return normalizeOverlay({ ...value, id }, options);
    }

    function isTranscriptOverlay(overlay) {
      return overlay?.trackType === TRANSCRIPT_TRACK_TYPE && Boolean(overlay.trackId);
    }

    function updateOverlay(overlays, id, patch = {}, options = {}) {
      const current = Array.isArray(overlays) ? overlays : [];
      const selected = current.find((overlay) => String(overlay.id) === String(id));
      if (!selected) return current.map(clone);
      const transcriptSelected = isTranscriptOverlay(selected);
      const sharedPatch = transcriptSelected
        ? Object.fromEntries(
            Object.entries(patch).filter(([key]) => TRANSCRIPT_STYLE_FIELDS.includes(key)),
          )
        : patch;
      const cuePatch = transcriptSelected
        ? Object.fromEntries(
            Object.entries(patch).filter(([key]) => TRANSCRIPT_CUE_FIELDS.includes(key)),
          )
        : {};
      return current.map((overlay) => {
        const target = transcriptSelected
          ? overlay.trackId === selected.trackId
          : String(overlay.id) === String(id);
        if (!target) return clone(overlay);
        const next = {
          ...clone(overlay),
          ...clone(sharedPatch),
          ...(transcriptSelected && String(overlay.id) === String(id)
            ? clone(cuePatch)
            : {}),
        };
        if (transcriptSelected) {
          next.direction = "horizontal";
          next.charsPerLine = 0;
        }
        return normalizeOverlay(next, {
          duration: options.duration,
          palettes: options.palettes,
          templateEffects: options.templateEffects,
          id: overlay.id,
        });
      });
    }

    function applyStyleToManualOverlays(overlays, sourceId, options = {}) {
      const current = Array.isArray(overlays) ? overlays : [];
      const source = current.find((overlay) => String(overlay.id) === String(sourceId));
      if (!source || isTranscriptOverlay(source)) return current.map(clone);
      const patch = Object.fromEntries(
        TRANSCRIPT_STYLE_FIELDS.map((field) => [field, clone(source[field])]),
      );
      return current.map((overlay) =>
        isTranscriptOverlay(overlay) || String(overlay.id) === String(sourceId)
          ? clone(overlay)
          : normalizeOverlay({ ...clone(overlay), ...patch }, {
              duration: options.duration,
              palettes: options.palettes,
              templateEffects: options.templateEffects,
              id: overlay.id,
            }),
      );
    }

    function removeOverlay(overlays, id) {
      const current = Array.isArray(overlays) ? overlays : [];
      const selected = current.find((overlay) => String(overlay.id) === String(id));
      if (!selected) return current.map(clone);
      return current
        .filter((overlay) =>
          isTranscriptOverlay(selected)
            ? overlay.trackId !== selected.trackId
            : String(overlay.id) !== String(id),
        )
        .map(clone);
    }

    function buildTimelineTracks(overlays) {
      const groups = new Map();
      for (const overlay of Array.isArray(overlays) ? overlays : []) {
        const groupId = isTranscriptOverlay(overlay)
          ? `art:transcript:${overlay.trackId}`
          : `art:overlay:${overlay.id}`;
        if (!groups.has(groupId)) {
          groups.set(groupId, {
            id: groupId,
            kind: "art",
            name: isTranscriptOverlay(overlay) ? "全文艺术字" : String(overlay.text || "艺术字"),
            clips: [],
          });
        }
        groups.get(groupId).clips.push({
          id: `art:${overlay.id}`,
          sourceId: String(overlay.id),
          kind: "art",
          name: String(overlay.text || "艺术字"),
          start: finiteNumber(overlay.start),
          end: finiteNumber(overlay.end),
          minDuration: isTranscriptOverlay(overlay) ? 0.02 : 0.05,
          payload: {
            text: String(overlay.text || ""),
            trackId: overlay.trackId || null,
            trackType: overlay.trackType || null,
            sourceStart: Number.isFinite(Number(overlay.sourceStart)) ? Number(overlay.sourceStart) : null,
            sourceEnd: Number.isFinite(Number(overlay.sourceEnd)) ? Number(overlay.sourceEnd) : null,
          },
        });
      }
      return [...groups.values()].map((track, index) => ({
        ...track,
        order: index,
        clips: track.clips.sort((left, right) => left.start - right.start || left.end - right.end),
      }));
    }

    function buildTimeline(art, duration, selection = null) {
      return {
        schemaVersion: 1,
        duration: Math.max(0, finiteNumber(duration)),
        tracks: buildTimelineTracks(art?.overlays),
        selection: selection?.clipId ? { clipId: String(selection.clipId) } : null,
      };
    }

    function buildTranscriptTrack(result = {}, style = {}, current = [], options = {}) {
      const cues = Array.isArray(result.cues) ? result.cues : [];
      const trackId = String(result.trackId || options.trackId || "transcript-full");
      const existing = (Array.isArray(current) ? current : []).filter(
        (overlay) => isTranscriptOverlay(overlay) && overlay.trackId === trackId,
      );
      const used = new Set();
      return cues.map((cue, index) => {
        const sourceStart = Number(cue.sourceStart);
        const matched = existing.find((overlay) => {
          if (used.has(String(overlay.id))) return false;
          const overlaySourceStart = Number(overlay.sourceStart);
          return Number.isFinite(sourceStart) && Number.isFinite(overlaySourceStart)
            ? Math.abs(sourceStart - overlaySourceStart) < 0.001
            : index === existing.indexOf(overlay);
        });
        if (matched) used.add(String(matched.id));
        return normalizeOverlay(
          {
            ...clone(style),
            ...clone(cue),
            id: matched?.id || `art-${trackId}-${index + 1}`,
            fontSize: result.fontSize || style.fontSize,
            trackId,
            trackType: TRANSCRIPT_TRACK_TYPE,
            direction: "horizontal",
            charsPerLine: 0,
          },
          { duration: options.duration },
        );
      });
    }

    function overlayFromSuggestion(suggestion, overlays, options = {}) {
      const {
        accepted: _accepted,
        draftId: _draftId,
        position: _position,
        ...confirmed
      } = clone(suggestion || {});
      return createOverlay(overlays, {
        ...confirmed,
        id: undefined,
        trackId: null,
        trackType: null,
      }, options);
    }

    function balanceHorizontalLine(sourceLine, limit) {
      const characters = [...sourceLine];
      if (limit <= 0 || characters.length <= limit) return [sourceLine];
      const lines = [];
      let cursor = 0;
      while (cursor < characters.length) {
        let end = Math.min(characters.length, cursor + limit);
        if (end < characters.length) {
          while (
            end > cursor + 1 &&
            (LINE_END_FORBIDDEN_PUNCTUATION.has(characters[end - 1]) ||
              LINE_START_FORBIDDEN_PUNCTUATION.has(characters[end]))
          ) end -= 1;
        }
        if (end <= cursor) end = Math.min(characters.length, cursor + limit);
        lines.push(characters.slice(cursor, end).join(""));
        cursor = end;
      }
      return lines;
    }

    function formatText(overlay = {}) {
      const limit = Math.max(0, Math.round(finiteNumber(overlay.charsPerLine)));
      const wrapped = [];
      for (const sourceLine of String(overlay.text || "").split(/\r?\n/)) {
        const characters = [...sourceLine];
        if (!characters.length || !limit) wrapped.push(sourceLine);
        else if (overlay.direction === "horizontal") {
          wrapped.push(...balanceHorizontalLine(sourceLine, limit));
        } else {
          for (let index = 0; index < characters.length; index += limit) {
            wrapped.push(characters.slice(index, index + limit).join(""));
          }
        }
      }
      if (overlay.direction === "vertical") {
        const columns = [...wrapped].reverse();
        const gap = "\u200a".repeat(Math.max(1, Math.round(finiteNumber(overlay.lineSpacing) / 2)));
        const rows = Math.max(0, ...columns.map((column) => [...column].length));
        return Array.from({ length: rows }, (_, row) =>
          columns.map((column) => [...column][row] ?? "\u3000").join(gap),
        ).join("\n");
      }
      const gap = "\u200a".repeat(Math.max(0, Math.round(finiteNumber(overlay.letterSpacing) / 2)));
      return wrapped.map((line) => gap ? [...line].join(gap) : line).join("\n");
    }

    function validateOverlays(overlays, duration) {
      const items = Array.isArray(overlays) ? overlays : [];
      if (!items.length) return "请至少添加一条艺术字。";
      if (items.filter((overlay) => !isTranscriptOverlay(overlay)).length > MANUAL_OVERLAY_LIMIT) {
        return `一个视频最多添加 ${MANUAL_OVERLAY_LIMIT} 条自定义艺术字。`;
      }
      const ids = new Set();
      for (const [index, overlay] of items.entries()) {
        const id = String(overlay.id ?? "").trim();
        if (!id || ids.has(id)) return `第 ${index + 1} 条艺术字标识无效。`;
        ids.add(id);
        if (!String(overlay.text || "").trim()) return `第 ${index + 1} 条艺术字内容不能为空。`;
        if (String(overlay.text || "").length > 60) return `第 ${index + 1} 条艺术字不能超过 60 个字符。`;
        const numericValues = [
          overlay.start, overlay.end, overlay.x, overlay.y,
          overlay.fontSize, overlay.strokeWidth, overlay.letterSpacing,
          overlay.lineSpacing, overlay.charsPerLine,
        ].map(Number);
        if (!numericValues.every(Number.isFinite)) return `第 ${index + 1} 条艺术字包含无效数值。`;
        if (Number(overlay.x) < 0.05 || Number(overlay.x) > 0.95 || Number(overlay.y) < 0.05 || Number(overlay.y) > 0.95) {
          return `第 ${index + 1} 条艺术字位置超出画面。`;
        }
        if (!Number.isInteger(Number(overlay.strokeWidth)) || Number(overlay.strokeWidth) < 0 || Number(overlay.strokeWidth) > 12) {
          return `第 ${index + 1} 条艺术字描边应在 0–12 之间。`;
        }
        if (!Number.isInteger(Number(overlay.letterSpacing)) || Number(overlay.letterSpacing) < 0 || Number(overlay.letterSpacing) > 20) {
          return `第 ${index + 1} 条艺术字字间距应在 0–20 之间。`;
        }
        const minimum = isTranscriptOverlay(overlay) ? 0.02 : 0.05;
        if (finiteNumber(overlay.end) - finiteNumber(overlay.start) < minimum) {
          return `第 ${index + 1} 条艺术字的结束时间必须晚于开始时间。`;
        }
        if (finiteNumber(overlay.start) < 0 || finiteNumber(overlay.end) > finiteNumber(duration) + 0.01) {
          return `第 ${index + 1} 条艺术字的时间超出视频范围。`;
        }
        const timings = Array.isArray(overlay.characterTimings)
          ? overlay.characterTimings
          : [];
        const visibleCount = [...String(overlay.text || "")].filter(
          (character) => !/\s/u.test(character),
        ).length;
        if (timings.length && timings.length !== visibleCount) {
          return `第 ${index + 1} 条艺术字的逐字时间与文字数量不一致。`;
        }
        if (timings.some((timing) => {
          const start = Number(timing?.start);
          const end = Number(timing?.end);
          return !Number.isFinite(start) || !Number.isFinite(end) || end <= start ||
            start < Number(overlay.start) - 0.01 || end > Number(overlay.end) + 0.01;
        })) {
          return `第 ${index + 1} 条艺术字的逐字时间无效。`;
        }
      }
      const track = items.filter(isTranscriptOverlay).sort((a, b) => a.start - b.start);
      for (let index = 0; index < track.length; index += 1) {
        if (track[index].direction !== "horizontal" || track[index].charsPerLine !== 0 || /[\r\n]/.test(track[index].text)) {
          return "全文艺术字轨道必须保持横向单行排版，请重新生成。";
        }
        if (index && track[index].start < track[index - 1].end - 0.001) {
          return "全文艺术字轨道片段发生重叠，请重新生成。";
        }
      }
      return "";
    }

    return Object.freeze({
      MANUAL_OVERLAY_LIMIT,
      TRANSCRIPT_TRACK_TYPE,
      TRANSCRIPT_STYLE_FIELDS,
      TRANSCRIPT_CUE_FIELDS,
      DEFAULT_PALETTES,
      applyStyleToManualOverlays,
      balanceHorizontalLine,
      buildTimeline,
      buildTimelineTracks,
      buildTranscriptTrack,
      createOverlay,
      formatText,
      isTranscriptOverlay,
      nextStableId,
      normalizeCharacterTimings,
      normalizeColor,
      normalizeOverlay,
      normalizeRange,
      normalizeTemplateEffects,
      overlayFromSuggestion,
      removeOverlay,
      updateOverlay,
      validateOverlays,
    });
  },
);
