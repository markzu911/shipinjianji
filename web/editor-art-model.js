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
    const FULL_TRANSCRIPT_TRACK_ID = "transcript-full";
    const CUT_RECONCILIATION_FIELD = "_cutReconciliation";
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

    function contentCharacters(value) {
      return [...String(value || "")].filter(
        (character) => !/\s/u.test(character) && !/\p{P}/u.test(character),
      );
    }

    function validTimedRange(value, startKey = "start", endKey = "end") {
      const start = Number(value?.[startKey]);
      const end = Number(value?.[endKey]);
      return Number.isFinite(start) && Number.isFinite(end) && end > start
        ? { start, end }
        : null;
    }

    function roundTiming(value) {
      return Math.round(Number(value) * 1e6) / 1e6;
    }

    function sourceRangeForItem(item, segment) {
      const direct = validTimedRange(item, "sourceStart", "sourceEnd");
      if (direct) return direct;
      const source = validTimedRange(segment, "sourceStart", "sourceEnd");
      const edited = validTimedRange(segment);
      const itemRange = validTimedRange(item);
      if (!source || !edited || !itemRange) return null;
      const scale = (source.end - source.start) / (edited.end - edited.start);
      return {
        start: source.start + (itemRange.start - edited.start) * scale,
        end: source.start + (itemRange.end - edited.start) * scale,
      };
    }

    function transcriptCharacterUnits(transcript = {}, options = {}) {
      const units = [];
      const charactersFor = options.includePunctuation
        ? (value) => [...String(value || "")].filter((character) => !/\s/u.test(character))
        : contentCharacters;
      let pendingWhitespace = false;
      for (const [segmentIndex, segment] of (
        Array.isArray(transcript?.segments) ? transcript.segments : []
      ).entries()) {
        const segmentCharacters = charactersFor(segment?.text).join("");
        const usableItems = (value) => {
          const items = (Array.isArray(value) ? value : []).filter(
            (item) => charactersFor(item?.text).length,
          );
          return items.length &&
            items.every((item) => validTimedRange(item)) &&
            items.flatMap((item) => charactersFor(item?.text)).join("") === segmentCharacters
            ? items
            : null;
        };
        const items = usableItems(segment?.words) ||
          usableItems(segment?.asrWords) ||
          [segment];
        for (const [semanticUnitIndex, item] of items.entries()) {
          const characters = [];
          for (const character of [...String(item?.text || "")]) {
            if (/\s/u.test(character)) {
              pendingWhitespace = pendingWhitespace || units.length > 0 || characters.length > 0;
              continue;
            }
            if (!options.includePunctuation && /\p{P}/u.test(character)) continue;
            characters.push({
              character,
              separatorBefore: pendingWhitespace ? " " : "",
            });
            pendingWhitespace = false;
          }
          const range = validTimedRange(item);
          if (!characters.length || !range) continue;
          const supplied = Array.isArray(item.characterTimings)
            ? item.characterTimings.map((timing) => validTimedRange(timing))
            : [];
          const source = sourceRangeForItem(item, segment);
          for (let index = 0; index < characters.length; index += 1) {
            const characterRange = supplied.length === characters.length && supplied[index]
              ? supplied[index]
              : {
                  start: range.start + ((range.end - range.start) * index) / characters.length,
                  end: range.start + ((range.end - range.start) * (index + 1)) / characters.length,
                };
            const sourceScale = source
              ? (source.end - source.start) / (range.end - range.start)
              : null;
            const sourceStart = source
              ? source.start + (characterRange.start - range.start) * sourceScale
              : null;
            const sourceEnd = source
              ? source.start + (characterRange.end - range.start) * sourceScale
              : null;
            units.push({
              character: characters[index].character,
              separatorBefore: characters[index].separatorBefore,
              start: characterRange.start,
              end: characterRange.end,
              sourceStart,
              sourceEnd,
              segmentIndex,
              semanticUnitIndex,
            });
          }
        }
      }
      return units;
    }

    function exactTranscriptPhraseMatch(
      transcript,
      phrase,
      currentStart = 0,
      options = {},
    ) {
      const target = contentCharacters(phrase);
      const units = transcriptCharacterUnits(transcript);
      const candidates = [];
      if (target.length && units.length >= target.length) {
        for (let index = 0; index <= units.length - target.length; index += 1) {
          if (!target.every((character, offset) => units[index + offset].character === character)) {
            continue;
          }
          const first = units[index];
          const last = units[index + target.length - 1];
          candidates.push({
            index,
            first,
            last,
            units: units.slice(index, index + target.length),
          });
        }
      }
      if (!candidates.length) return null;
      const reference = finiteNumber(currentStart);
      const sourceReference = Number(options.sourceStart);
      candidates.sort((left, right) => {
        const leftSourceDistance = Number.isFinite(sourceReference) && Number.isFinite(left.first.sourceStart)
          ? Math.abs(left.first.sourceStart - sourceReference)
          : Number.POSITIVE_INFINITY;
        const rightSourceDistance = Number.isFinite(sourceReference) && Number.isFinite(right.first.sourceStart)
          ? Math.abs(right.first.sourceStart - sourceReference)
          : Number.POSITIVE_INFINITY;
        return leftSourceDistance - rightSourceDistance ||
          Math.abs(left.first.start - reference) - Math.abs(right.first.start - reference) ||
          left.index - right.index;
      });
      return candidates[0];
    }

    function matchTranscriptPhrase(transcript, phrase, currentStart = 0) {
      const exact = exactTranscriptPhraseMatch(transcript, phrase, currentStart);
      if (exact) {
        const { first, last } = exact;
        return {
          start: roundTiming(first.start),
          end: roundTiming(last.end),
          sourceStart: Number.isFinite(first.sourceStart) ? roundTiming(first.sourceStart) : null,
          sourceEnd: Number.isFinite(last.sourceEnd) ? roundTiming(last.sourceEnd) : null,
        };
      }

      const reference = finiteNumber(currentStart);
      const segment = (Array.isArray(transcript?.segments) ? transcript.segments : []).find(
        (item) => {
          const range = validTimedRange(item);
          return range && range.start <= reference && range.end >= reference;
        },
      );
      const range = validTimedRange(segment);
      if (!range) return null;
      const source = validTimedRange(segment, "sourceStart", "sourceEnd");
      return {
        start: roundTiming(range.start),
        end: roundTiming(range.end),
        sourceStart: source ? roundTiming(source.start) : null,
        sourceEnd: source ? roundTiming(source.end) : null,
      };
    }

    function normalizeCutRanges(cut = {}) {
      const sourceDuration = Math.max(0, finiteNumber(cut.sourceDuration));
      const ranges = (Array.isArray(cut.ranges) ? cut.ranges : [])
        .flatMap((range) => {
          const start = clamp(finiteNumber(range?.start), 0, sourceDuration);
          const end = clamp(finiteNumber(range?.end), start, sourceDuration);
          return end > start ? [{ start, end }] : [];
        })
        .sort((left, right) => left.start - right.start || left.end - right.end);
      return ranges.reduce((merged, range) => {
        const previous = merged.at(-1);
        if (!previous || range.start > previous.end + 0.000001) {
          merged.push({ ...range });
        } else {
          previous.end = Math.max(previous.end, range.end);
        }
        return merged;
      }, []);
    }

    function retainedTimelineSpans(cut = {}) {
      const sourceDuration = Math.max(0, finiteNumber(cut.sourceDuration));
      if (!sourceDuration) return [];
      const spans = [];
      let sourceCursor = 0;
      let editedCursor = 0;
      for (const range of normalizeCutRanges(cut)) {
        if (range.start > sourceCursor) {
          const spanDuration = range.start - sourceCursor;
          spans.push({
            sourceStart: sourceCursor,
            sourceEnd: range.start,
            editedStart: editedCursor,
            editedEnd: editedCursor + spanDuration,
          });
          editedCursor += spanDuration;
        }
        sourceCursor = Math.max(sourceCursor, range.end);
      }
      if (sourceCursor < sourceDuration) {
        spans.push({
          sourceStart: sourceCursor,
          sourceEnd: sourceDuration,
          editedStart: editedCursor,
          editedEnd: editedCursor + sourceDuration - sourceCursor,
        });
      }
      return spans;
    }

    function sourceRangeFromEditedRange(overlay, cut = {}) {
      const spans = retainedTimelineSpans(cut);
      if (!spans.length) return null;
      const map = (seconds, edge) => {
        const time = Math.max(0, finiteNumber(seconds));
        for (const span of spans) {
          const inside = edge === "end"
            ? time <= span.editedEnd + 0.000001
            : time < span.editedEnd - 0.000001;
          if (inside) {
            return clamp(
              span.sourceStart + time - span.editedStart,
              span.sourceStart,
              span.sourceEnd,
            );
          }
        }
        return spans.at(-1).sourceEnd;
      };
      const start = map(overlay?.start, "start");
      const end = map(overlay?.end, "end");
      return end > start ? { start, end } : null;
    }

    function editedRangeForSourceRange(sourceRange, cut = {}) {
      if (!sourceRange) return null;
      const intersections = retainedTimelineSpans(cut).flatMap((span) => {
        const sourceStart = Math.max(sourceRange.start, span.sourceStart);
        const sourceEnd = Math.min(sourceRange.end, span.sourceEnd);
        return sourceEnd > sourceStart
          ? [{
              sourceStart,
              sourceEnd,
              start: span.editedStart + sourceStart - span.sourceStart,
              end: span.editedStart + sourceEnd - span.sourceStart,
            }]
          : [];
      });
      if (!intersections.length) return null;
      return {
        start: intersections[0].start,
        end: intersections.at(-1).end,
        sourceStart: intersections[0].sourceStart,
        sourceEnd: intersections.at(-1).sourceEnd,
      };
    }

    function overlaySourceRange(overlay, previousCut = null) {
      return validTimedRange(overlay, "sourceStart", "sourceEnd") ||
        (previousCut ? sourceRangeFromEditedRange(overlay, previousCut) : null);
    }

    function cleanReconciliationBase(overlay) {
      const base = clone(overlay || {});
      delete base[CUT_RECONCILIATION_FIELD];
      return base;
    }

    function transcriptReconciliationBase(overlay, previousCut) {
      const stored = overlay?.[CUT_RECONCILIATION_FIELD]?.overlay;
      const base = cleanReconciliationBase(stored || overlay);
      const sourceRange = overlaySourceRange(base, previousCut);
      if (sourceRange) {
        base.sourceStart = sourceRange.start;
        base.sourceEnd = sourceRange.end;
      }
      return base;
    }

    function withTranscriptReconciliationBase(overlay, base) {
      return {
        ...overlay,
        [CUT_RECONCILIATION_FIELD]: {
          version: 1,
          overlay: cleanReconciliationBase(base),
        },
      };
    }

    function transcriptTrackEntry(overlay, previousCut, index) {
      const base = transcriptReconciliationBase(overlay, previousCut);
      const sourceRange = overlaySourceRange(base, previousCut);
      return { overlay, base, sourceRange, index };
    }

    function transcriptTrackEntryOrder(left, right) {
      const leftSource = left.sourceRange?.start;
      const rightSource = right.sourceRange?.start;
      if (Number.isFinite(leftSource) && Number.isFinite(rightSource)) {
        return leftSource - rightSource || left.index - right.index;
      }
      return finiteNumber(left.base?.start) - finiteNumber(right.base?.start) ||
        left.index - right.index;
    }

    function transcriptSemanticCharacters(transcript) {
      const segments = Array.isArray(transcript?.segments)
        ? transcript.segments
        : [];
      const semanticSegments = segments.length
        ? segments
        : [{ text: String(transcript?.text || "") }];
      const characters = [];
      let pendingWhitespace = false;
      for (const [segmentIndex, segment] of semanticSegments.entries()) {
        const segmentCharacters = contentCharacters(segment?.text).join("");
        const semanticItems = (value) => {
          const items = (Array.isArray(value) ? value : []).filter(
            (item) => contentCharacters(item?.text).length,
          );
          return items.length &&
            items.flatMap((item) => contentCharacters(item?.text)).join("") === segmentCharacters
            ? items
            : null;
        };
        const items = semanticItems(segment?.words) ||
          semanticItems(segment?.asrWords) ||
          [segment];
        for (const [semanticUnitIndex, item] of items.entries()) {
          for (const character of [...String(item?.text || "")]) {
            if (/\s/u.test(character)) {
              pendingWhitespace = pendingWhitespace || characters.length > 0;
              continue;
            }
            if (/\p{P}/u.test(character)) continue;
            characters.push({
              character,
              separatorBefore: pendingWhitespace ? " " : "",
              segmentIndex,
              semanticUnitIndex,
            });
            pendingWhitespace = false;
          }
        }
      }
      return characters;
    }

    function fallbackTranscriptTrackUnits(transcript, entries, nextCut, duration) {
      const characters = transcriptSemanticCharacters(transcript);
      if (!characters.length) return [];
      const mappedRanges = entries.flatMap((entry) => {
        const mapped = editedRangeForSourceRange(entry.sourceRange, nextCut);
        return mapped ? [mapped] : [];
      });
      const baseRanges = entries.flatMap((entry) => {
        const range = validTimedRange(entry.base);
        return range ? [range] : [];
      });
      const ranges = mappedRanges.length ? mappedRanges : baseRanges;
      let start = ranges.length
        ? Math.min(...ranges.map((range) => range.start))
        : 0;
      let end = ranges.length
        ? Math.max(...ranges.map((range) => range.end))
        : duration;
      start = clamp(start, 0, Math.max(0, duration - 0.02));
      end = clamp(end, start + 0.02, duration);
      return characters.map((item, index) => ({
        ...item,
        start: start + ((end - start) * index) / characters.length,
        end: start + ((end - start) * (index + 1)) / characters.length,
        sourceStart: null,
        sourceEnd: null,
      }));
    }

    function transcriptBoundaryPreference(left, right) {
      const leftEnd = left.sourceRange?.end;
      const rightStart = right.sourceRange?.start;
      if (Number.isFinite(leftEnd) && Number.isFinite(rightStart)) {
        return (leftEnd + rightStart) / 2;
      }
      if (Number.isFinite(leftEnd)) return leftEnd;
      if (Number.isFinite(rightStart)) return rightStart;
      return null;
    }

    function transcriptSourceSplitIndex(units, preference) {
      if (!Number.isFinite(preference)) return null;
      let splitIndex = 0;
      for (const unit of units) {
        if (!Number.isFinite(unit.sourceStart) || !Number.isFinite(unit.sourceEnd)) {
          return null;
        }
        const midpoint = unit.sourceStart + (unit.sourceEnd - unit.sourceStart) / 2;
        if (midpoint >= preference) break;
        splitIndex += 1;
      }
      return splitIndex;
    }

    function transcriptCapacitySplitIndex(entries, boundaryIndex, unitCount) {
      const capacities = entries.map((entry) => contentCharacters(entry.base?.text).length);
      const totalCapacity = capacities.reduce((total, count) => total + count, 0);
      const ratio = totalCapacity
        ? capacities.slice(0, boundaryIndex + 1)
            .reduce((total, count) => total + count, 0) / totalCapacity
        : (boundaryIndex + 1) / entries.length;
      return Math.round(unitCount * ratio);
    }

    function transcriptSemanticSplitIndexes(units) {
      const boundaries = new Set([0, units.length]);
      for (let index = 1; index < units.length; index += 1) {
        const previous = units[index - 1];
        const current = units[index];
        if (
          previous.segmentIndex !== current.segmentIndex ||
          previous.semanticUnitIndex !== current.semanticUnitIndex
        ) {
          boundaries.add(index);
        }
      }
      return [...boundaries].sort((left, right) => left - right);
    }

    const TRANSCRIPT_INCOMPLETE_ENDINGS = Object.freeze([
      "这辈子", "最难", "最重要", "最关键", "因为", "如果", "虽然",
      "但是", "而是", "需要", "应该", "可以", "不能", "不会", "没有",
      "不是", "想要", "为了", "通过", "正在", "已经", "从来不", "最",
      "才", "还", "又", "赚", "跟", "到", "被你", "把你", "给你",
      "让你", "由你", "对你", "过来跟", "这件", "这个", "这种", "那些",
      "一个", "所有", "第一",
    ]);
    const TRANSCRIPT_WEAK_STARTERS = new Set([
      "的", "地", "得", "了", "着", "过", "吗", "呢", "啊", "是", "赚",
      "做", "有", "能", "会", "想", "要", "说", "给", "让", "把", "被",
      "在", "跟", "就", "都", "觉得", "发现", "认为",
    ]);

    function transcriptSemanticUnitText(units, index) {
      const first = units[index];
      if (!first) return "";
      const characters = [];
      for (let cursor = index; cursor < units.length; cursor += 1) {
        const unit = units[cursor];
        if (
          unit.segmentIndex !== first.segmentIndex ||
          unit.semanticUnitIndex !== first.semanticUnitIndex
        ) {
          break;
        }
        characters.push(unit.character);
      }
      return characters.join("");
    }

    function transcriptSplitIsUnsafe(units, cursor, candidate) {
      if (candidate <= cursor || candidate - cursor === 1) return true;
      if (units.length - candidate === 1) return true;
      const leftText = units.slice(cursor, candidate)
        .map((unit) => unit.character).join("");
      if (TRANSCRIPT_INCOMPLETE_ENDINGS.some((ending) => leftText.endsWith(ending))) {
        return true;
      }
      return TRANSCRIPT_WEAK_STARTERS.has(
        transcriptSemanticUnitText(units, candidate),
      );
    }

    function transcriptCharacterMatches(oldCharacters, newCharacters) {
      const matches = [];
      let prefix = 0;
      while (
        prefix < oldCharacters.length &&
        prefix < newCharacters.length &&
        oldCharacters[prefix] === newCharacters[prefix]
      ) {
        matches.push([prefix, prefix]);
        prefix += 1;
      }
      let suffix = 0;
      while (
        suffix < oldCharacters.length - prefix &&
        suffix < newCharacters.length - prefix &&
        oldCharacters[oldCharacters.length - suffix - 1] ===
          newCharacters[newCharacters.length - suffix - 1]
      ) {
        suffix += 1;
      }

      const oldMiddle = oldCharacters.slice(prefix, oldCharacters.length - suffix);
      const newMiddle = newCharacters.slice(prefix, newCharacters.length - suffix);
      const maximumCells = 2_000_000;
      if (
        oldMiddle.length &&
        newMiddle.length &&
        oldMiddle.length * newMiddle.length <= maximumCells
      ) {
        const stride = newMiddle.length + 1;
        const lengths = new Uint32Array((oldMiddle.length + 1) * stride);
        for (let oldIndex = oldMiddle.length - 1; oldIndex >= 0; oldIndex -= 1) {
          for (let newIndex = newMiddle.length - 1; newIndex >= 0; newIndex -= 1) {
            const offset = oldIndex * stride + newIndex;
            lengths[offset] = oldMiddle[oldIndex] === newMiddle[newIndex]
              ? lengths[(oldIndex + 1) * stride + newIndex + 1] + 1
              : Math.max(
                  lengths[(oldIndex + 1) * stride + newIndex],
                  lengths[offset + 1],
                );
          }
        }
        let oldIndex = 0;
        let newIndex = 0;
        while (oldIndex < oldMiddle.length && newIndex < newMiddle.length) {
          if (
            oldMiddle[oldIndex] === newMiddle[newIndex] &&
            lengths[oldIndex * stride + newIndex] ===
              lengths[(oldIndex + 1) * stride + newIndex + 1] + 1
          ) {
            matches.push([prefix + oldIndex, prefix + newIndex]);
            oldIndex += 1;
            newIndex += 1;
          } else if (
            lengths[(oldIndex + 1) * stride + newIndex] >=
            lengths[oldIndex * stride + newIndex + 1]
          ) {
            oldIndex += 1;
          } else {
            newIndex += 1;
          }
        }
      }
      for (let index = suffix; index > 0; index -= 1) {
        matches.push([
          oldCharacters.length - index,
          newCharacters.length - index,
        ]);
      }
      return matches;
    }

    function transcriptTrackBoundaryProjections(entries, units) {
      const oldTexts = entries.map((entry) => contentCharacters(entry.base?.text));
      const oldCharacters = oldTexts.flat();
      const newCharacters = units.map((unit) => unit.character);
      const matches = transcriptCharacterMatches(oldCharacters, newCharacters);
      let oldCursor = 0;
      return oldTexts.slice(0, -1).map((text) => {
        oldCursor += text.length;
        let lower = 0;
        let upper = newCharacters.length;
        for (const [oldIndex, newIndex] of matches) {
          if (oldIndex < oldCursor) lower = newIndex + 1;
          else {
            upper = newIndex;
            break;
          }
        }
        return {
          lower: Math.min(lower, upper),
          upper: Math.max(lower, upper),
        };
      });
    }

    function nearestTranscriptSemanticSplit(candidates, preference, cursor) {
      const available = candidates.filter((candidate) => candidate >= cursor);
      if (!available.length) return cursor;
      return available.reduce((best, candidate) => (
        Math.abs(candidate - preference) < Math.abs(best - preference) ||
        (
          Math.abs(candidate - preference) === Math.abs(best - preference) &&
          candidate < best
        )
          ? candidate
          : best
      ));
    }

    function partitionTranscriptTrack(entries, units, preferSourceBoundaries = true) {
      const boundaries = [0];
      const semanticSplits = transcriptSemanticSplitIndexes(units);
      const projections = transcriptTrackBoundaryProjections(entries, units);
      let cursor = 0;
      for (let index = 0; index < entries.length - 1; index += 1) {
        const preference = transcriptBoundaryPreference(entries[index], entries[index + 1]);
        const sourceSplit = preferSourceBoundaries
          ? transcriptSourceSplitIndex(units, preference)
          : null;
        const splitIndex = sourceSplit === null
          ? transcriptCapacitySplitIndex(entries, index, units.length)
          : sourceSplit;
        const projection = projections[index];
        const lower = Math.max(cursor, projection?.lower ?? cursor);
        const upper = Math.max(lower, projection?.upper ?? units.length);
        const safeInternalAlternative = semanticSplits.some(
          (candidate) =>
            candidate > cursor &&
            candidate < units.length &&
            !transcriptSplitIsUnsafe(units, cursor, candidate),
        );
        const inheritedIsLegal =
          lower === upper &&
          semanticSplits.includes(lower) &&
          (
            lower === cursor ||
            !transcriptSplitIsUnsafe(units, cursor, lower) ||
            !safeInternalAlternative
          );
        if (inheritedIsLegal) {
          cursor = lower;
        } else {
          const projectionIsInsideWord =
            lower === upper && !semanticSplits.includes(lower);
          const candidateLower = projectionIsInsideWord ? lower : cursor;
          const candidateUpper = lower === upper ? units.length : upper;
          const candidates = semanticSplits.filter(
            (candidate) =>
              candidate >= candidateLower &&
              candidate <= candidateUpper &&
              !transcriptSplitIsUnsafe(units, cursor, candidate),
          );
          cursor = candidates.length
            ? nearestTranscriptSemanticSplit(
                candidates,
                projectionIsInsideWord
                  ? candidateLower
                  : clamp(splitIndex, candidateLower, candidateUpper),
                candidateLower,
              )
            : cursor;
        }
        boundaries.push(cursor);
      }
      boundaries.push(units.length);
      return entries.map((entry, index) => ({
        entry,
        units: units.slice(boundaries[index], boundaries[index + 1]),
      }));
    }

    function rebuildTranscriptTrack(partition, duration) {
      const active = [];
      const suppressed = [];
      for (const { entry, units } of partition) {
        if (!units.length) {
          suppressed.push(withTranscriptReconciliationBase(
            clone(entry.overlay),
            entry.base,
          ));
          continue;
        }
        const first = units[0];
        const last = units.at(-1);
        const hasSourceRange =
          Number.isFinite(first.sourceStart) &&
          Number.isFinite(last.sourceEnd) &&
          last.sourceEnd > first.sourceStart;
        const fallbackSourceRange = entry.sourceRange;
        const rebuilt = normalizeOverlay({
          ...clone(entry.overlay),
          text: units.map((unit, index) =>
            `${index ? unit.separatorBefore : ""}${unit.character}`).join(""),
          start: first.start,
          end: last.end,
          sourceStart: hasSourceRange
            ? first.sourceStart
            : fallbackSourceRange?.start,
          sourceEnd: hasSourceRange
            ? last.sourceEnd
            : fallbackSourceRange?.end,
          characterTimings: units.map((unit) => ({
            start: unit.start,
            end: unit.end,
          })),
        }, { duration });
        active.push(withTranscriptReconciliationBase(rebuilt, entry.base));
      }
      return { active, suppressed };
    }

    function transcriptTrackConserved(result, units) {
      const expected = units.map((unit) => unit.character).join("");
      const actual = result.active
        .flatMap((overlay) => contentCharacters(overlay.text))
        .join("");
      const timingCount = result.active.reduce(
        (total, overlay) => total + (
          Array.isArray(overlay.characterTimings) ? overlay.characterTimings.length : 0
        ),
        0,
      );
      return actual === expected && timingCount === units.length;
    }

    function reconcileTranscriptTrackWithoutProjection(entries, nextCut, duration) {
      const active = [];
      const suppressed = [];
      for (const entry of entries) {
        if (!entry.sourceRange) {
          active.push(withTranscriptReconciliationBase(
            clone(entry.overlay),
            entry.base,
          ));
          continue;
        }
        const retainedRange = editedRangeForSourceRange(entry.sourceRange, nextCut);
        if (!retainedRange) {
          suppressed.push(withTranscriptReconciliationBase(
            clone(entry.overlay),
            entry.base,
          ));
          continue;
        }
        const rebuilt = normalizeOverlay({
          ...clone(entry.overlay),
          start: retainedRange.start,
          end: retainedRange.end,
          characterTimings: [],
        }, { duration });
        active.push(withTranscriptReconciliationBase(rebuilt, entry.base));
      }
      return { active, suppressed };
    }

    function transcriptUnitsForTrack(entries, units, limitToTrackCoverage = false) {
      if (!units.length) return units;
      const fullTranscriptTrack = entries.some(
        (entry) => String(entry.base?.trackId || "") === FULL_TRANSCRIPT_TRACK_ID,
      );
      const target = entries.flatMap((entry) =>
        contentCharacters(entry.base?.text),
      );
      const semanticMatches = [];
      if (!fullTranscriptTrack && target.length && target.length <= units.length) {
        for (let index = 0; index <= units.length - target.length; index += 1) {
          if (
            target.every(
              (character, offset) => units[index + offset].character === character,
            )
          ) {
            const end = index + target.length;
            const startsAtSegmentBoundary =
              index === 0 ||
              units[index - 1].segmentIndex !== units[index].segmentIndex;
            const endsAtSegmentBoundary =
              end === units.length ||
              units[end - 1].segmentIndex !== units[end].segmentIndex;
            if (startsAtSegmentBoundary && endsAtSegmentBoundary) {
              semanticMatches.push(index);
            }
          }
        }
      }
      const ranges = entries.flatMap((entry) =>
        entry.sourceRange ? [entry.sourceRange] : [],
      );
      if (semanticMatches.length) {
        const trackCenter = ranges.length
          ? (
              Math.min(...ranges.map((range) => range.start)) +
              Math.max(...ranges.map((range) => range.end))
            ) / 2
          : null;
        const matchStart = semanticMatches.reduce((best, candidate) => {
          if (!Number.isFinite(trackCenter)) return Math.min(best, candidate);
          const first = units[candidate];
          const last = units[candidate + target.length - 1];
          const candidateCenter =
            Number.isFinite(first.sourceStart) && Number.isFinite(last.sourceEnd)
              ? (first.sourceStart + last.sourceEnd) / 2
              : null;
          const bestFirst = units[best];
          const bestLast = units[best + target.length - 1];
          const bestCenter =
            Number.isFinite(bestFirst.sourceStart) && Number.isFinite(bestLast.sourceEnd)
              ? (bestFirst.sourceStart + bestLast.sourceEnd) / 2
              : null;
          if (!Number.isFinite(candidateCenter)) return best;
          if (!Number.isFinite(bestCenter)) return candidate;
          return Math.abs(candidateCenter - trackCenter) < Math.abs(bestCenter - trackCenter)
            ? candidate
            : best;
        });
        return units.slice(matchStart, matchStart + target.length);
      }
      if (
        fullTranscriptTrack ||
        !limitToTrackCoverage ||
        !units.every((unit) =>
          Number.isFinite(unit.sourceStart) && Number.isFinite(unit.sourceEnd),
        )
      ) {
        return units;
      }
      if (!ranges.length) return units;
      const trackStart = Math.min(...ranges.map((range) => range.start));
      const trackEnd = Math.max(...ranges.map((range) => range.end));
      const semanticUnitKey = (unit) =>
        `${unit.segmentIndex}:${unit.semanticUnitIndex}`;
      const retainedSemanticUnits = new Set(
        units
          .filter(
            (unit) => unit.sourceEnd > trackStart && unit.sourceStart < trackEnd,
          )
          .map(semanticUnitKey),
      );
      return units.filter((unit) => retainedSemanticUnits.has(semanticUnitKey(unit)));
    }

    function reconcileTranscriptTrack(
      overlays,
      previousCut,
      nextCut,
      displayUnits,
      duration,
      limitToTrackCoverage = false,
    ) {
      const entries = overlays
        .map((overlay, index) => transcriptTrackEntry(overlay, previousCut, index))
        .sort(transcriptTrackEntryOrder);
      const transcript = nextCut?.transcript;
      const semanticCharacters = transcriptSemanticCharacters(transcript);
      const hasExplicitTranscriptProjection =
        transcript &&
        typeof transcript === "object" &&
        (
          semanticCharacters.length > 0 ||
          Object.prototype.hasOwnProperty.call(transcript, "text") ||
          (Array.isArray(transcript.segments) && transcript.segments.length > 0)
        );
      if (!hasExplicitTranscriptProjection) {
        return reconcileTranscriptTrackWithoutProjection(entries, nextCut, duration);
      }
      const trackUnits = transcriptUnitsForTrack(
        entries,
        displayUnits,
        limitToTrackCoverage,
      );
      const units = displayUnits.length
        ? trackUnits
        : fallbackTranscriptTrackUnits(
            transcript,
            entries,
            nextCut,
            duration,
          );
      let result = rebuildTranscriptTrack(
        partitionTranscriptTrack(entries, units),
        duration,
      );
      if (!transcriptTrackConserved(result, units)) {
        result = rebuildTranscriptTrack(
          partitionTranscriptTrack(entries, units, false),
          duration,
        );
      }
      return result;
    }

    function reconcileAnchoredOverlay(overlay, nextCut, duration) {
      const sourceRange = validTimedRange(overlay, "sourceStart", "sourceEnd");
      if (!sourceRange) return { active: clone(overlay) };
      const retainedRange = editedRangeForSourceRange(sourceRange, nextCut);
      if (!retainedRange) return { suppressed: clone(overlay) };

      const exact = exactTranscriptPhraseMatch(
        nextCut?.transcript,
        overlay.text,
        retainedRange.start,
        { sourceStart: sourceRange.start },
      );
      const exactInsideAnchor = exact &&
        (!Number.isFinite(exact.first.sourceStart) ||
          (exact.first.sourceStart < sourceRange.end + 0.000001 &&
            exact.last.sourceEnd > sourceRange.start - 0.000001));
      const next = exactInsideAnchor
        ? {
            ...clone(overlay),
            start: exact.first.start,
            end: exact.last.end,
            sourceStart: Number.isFinite(exact.first.sourceStart)
              ? exact.first.sourceStart
              : overlay.sourceStart,
            sourceEnd: Number.isFinite(exact.last.sourceEnd)
              ? exact.last.sourceEnd
              : overlay.sourceEnd,
            characterTimings: exact.units.map((unit) => ({ start: unit.start, end: unit.end })),
          }
        : {
            ...clone(overlay),
            start: retainedRange.start,
            end: retainedRange.end,
            characterTimings: [],
          };
      return { active: normalizeOverlay(next, { duration }) };
    }

    function reconcileArtWithCut(art = {}, previousCut = {}, nextCut = {}) {
      const duration = Math.max(0.02, finiteNumber(nextCut?.duration, 0.02));
      const displayUnits = transcriptCharacterUnits(nextCut?.transcript);
      const byId = new Map();
      for (const overlay of Array.isArray(art?.suppressedOverlays)
        ? art.suppressedOverlays
        : []) {
        byId.set(String(overlay?.id ?? ""), clone(overlay));
      }
      for (const overlay of Array.isArray(art?.overlays) ? art.overlays : []) {
        byId.set(String(overlay?.id ?? ""), clone(overlay));
      }

      const overlays = [];
      const suppressedOverlays = [];
      const transcriptTracks = new Map();
      for (const overlay of byId.values()) {
        if (isTranscriptOverlay(overlay)) {
          const trackId = String(overlay.trackId);
          if (!transcriptTracks.has(trackId)) transcriptTracks.set(trackId, []);
          transcriptTracks.get(trackId).push(overlay);
          continue;
        }
        const result = reconcileAnchoredOverlay(overlay, nextCut, duration);
        if (result.active) overlays.push(result.active);
        else if (result.suppressed) suppressedOverlays.push(result.suppressed);
      }
      for (const trackOverlays of transcriptTracks.values()) {
        const result = reconcileTranscriptTrack(
          trackOverlays,
          previousCut,
          nextCut,
          displayUnits,
          duration,
          transcriptTracks.size > 1,
        );
        overlays.push(...result.active);
        suppressedOverlays.push(...result.suppressed);
      }
      overlays.sort((left, right) => finiteNumber(left.start) - finiteNumber(right.start));
      suppressedOverlays.sort((left, right) => finiteNumber(left.start) - finiteNumber(right.start));
      return {
        art: {
          ...clone(art),
          overlays,
          suppressedOverlays,
        },
        activeIds: overlays.map((overlay) => String(overlay.id)),
      };
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
        const normalized = normalizeOverlay(next, {
          duration: options.duration,
          palettes: options.palettes,
          templateEffects: options.templateEffects,
          id: overlay.id,
        });
        if (!transcriptSelected) return normalized;
        const cueTextChanged =
          String(overlay.id) === String(id) &&
          Object.prototype.hasOwnProperty.call(cuePatch, "text") &&
          String(cuePatch.text || "").trim() !== String(overlay.text || "");
        for (const field of [
          "id", "start", "end", "sourceStart", "sourceEnd", "timingRevision",
        ]) {
          if (Object.prototype.hasOwnProperty.call(overlay, field)) {
            normalized[field] = clone(overlay[field]);
          } else {
            delete normalized[field];
          }
        }
        if (!cueTextChanged) {
          normalized.text = clone(overlay.text);
          if (Object.prototype.hasOwnProperty.call(overlay, "characterTimings")) {
            normalized.characterTimings = clone(overlay.characterTimings);
          } else {
            delete normalized.characterTimings;
          }
        }
        return normalized;
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
        const transcriptOverlay = isTranscriptOverlay(overlay);
        const groupId = transcriptOverlay
          ? `art:transcript:${overlay.trackId}`
          : "art:manual";
        if (!groups.has(groupId)) {
          groups.set(groupId, {
            id: groupId,
            kind: "art",
            name: transcriptOverlay ? "视频文案艺术字" : "手动艺术字",
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
          minDuration: transcriptOverlay ? 0.02 : 0.05,
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
      const trackId = String(result.trackId || options.trackId || FULL_TRANSCRIPT_TRACK_ID);
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
      CUT_RECONCILIATION_FIELD,
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
      matchTranscriptPhrase,
      nextStableId,
      normalizeCharacterTimings,
      normalizeColor,
      normalizeOverlay,
      normalizeRange,
      normalizeTemplateEffects,
      overlayFromSuggestion,
      reconcileArtWithCut,
      removeOverlay,
      updateOverlay,
      validateOverlays,
    });
  },
);
