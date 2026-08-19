(function exposeEditorArtRenderer(root, factory) {
  const api = factory(root.EditorArtModel);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorArtRenderer = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function editorArtRendererFactory(artModel) {
    "use strict";

    function finiteNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function shiftHexColor(value, amount) {
      const source = /^#[0-9a-f]{6}$/i.test(String(value || "")) ? String(value) : "#FFFFFF";
      const channels = [1, 3, 5].map((offset) => parseInt(source.slice(offset, offset + 2), 16));
      return `#${channels.map((channel) =>
        Math.round(channel + (255 - channel) * amount).toString(16).padStart(2, "0"),
      ).join("")}`;
    }

    function sanitizeOverlay(value, index = 0, options = {}) {
      return artModel.normalizeOverlay(value, {
        duration: options.duration ?? Math.max(0.05, finiteNumber(value?.end, 0.05)),
        id: value?.id ?? value?.trackId ?? `art-overlay-${index}`,
        palettes: options.palettes,
        templateEffects: options.templateEffects,
      });
    }

    function formatText(overlay) {
      return artModel.formatText(overlay);
    }

    function renderCharacters(element, text, settings = {}, currentTime = null, playing = true) {
      const value = String(text || "");
      const effects = {
        ...artModel.normalizeTemplateEffects(settings),
        color: settings.color || "#FFFFFF",
      };
      const visibleCount = [...value].filter((character) => !/\s/u.test(character)).length;
      const timings = artModel.normalizeCharacterTimings(settings.characterTimings);
      const hasSpeechTimings = timings.length === visibleCount;
      const isTimelineOverlay = Number.isFinite(Number(settings.start)) && Number.isFinite(Number(settings.end));
      const animated = effects.animation.type === "character-bounce" && (hasSpeechTimings || !isTimelineOverlay);
      const staggered = effects.characterLayout.type === "staggered";
      const splitCharacters = effects.textColorMode === "center-highlight" || animated || staggered;
      element.classList.toggle("has-character-effect", splitCharacters);
      element.setAttribute("aria-label", value);
      if (!splitCharacters) {
        element.textContent = value;
        return;
      }
      const documentRef = element.ownerDocument || document;
      const highlightStart = Math.floor(visibleCount * 0.25);
      const highlightEnd = Math.ceil(visibleCount * 0.75);
      let visibleIndex = 0;
      const nodes = [];
      for (const character of value) {
        if (/\s/u.test(character)) {
          nodes.push(documentRef.createTextNode(character));
          continue;
        }
        const span = documentRef.createElement("span");
        span.className = "art-character";
        span.textContent = character;
        span.setAttribute("aria-hidden", "true");
        if (effects.textColorMode === "center-highlight") {
          span.style.color = highlightStart <= visibleIndex && visibleIndex < highlightEnd
            ? effects.color
            : effects.secondaryColor;
        }
        if (staggered) {
          const rotations = effects.characterLayout.rotationPattern;
          const offsets = effects.characterLayout.verticalOffsetPattern;
          span.classList.add("is-character-staggered");
          span.style.setProperty("--art-character-rotation", `${rotations[visibleIndex % rotations.length]}deg`);
          span.style.setProperty("--art-character-offset", `${offsets[visibleIndex % offsets.length]}em`);
        }
        if (animated) {
          span.classList.add("is-character-bounce");
          if (hasSpeechTimings) {
            const timing = timings[visibleIndex];
            span.style.animationDuration = `${Math.min(effects.animation.duration, Math.max(0.2, timing.end - timing.start + 0.18))}s`;
            span.style.animationDelay = `${timing.start - finiteNumber(currentTime)}s`;
            span.style.animationPlayState = playing ? "running" : "paused";
          } else {
            span.style.animationDuration = `${effects.animation.duration}s`;
            span.style.animationDelay = `${visibleIndex * effects.animation.stagger}s`;
          }
          span.style.setProperty("--art-character-lift", `${effects.animation.amplitude}em`);
        }
        nodes.push(span);
        visibleIndex += 1;
      }
      element.replaceChildren(...nodes);
    }

    function applyStyle(element, overlay, options = {}) {
      const scale = Math.max(0.01, finiteNumber(options.scale, 1));
      const fontFamilies = options.fontFamilies || {};
      const artStyle = String(options.baseStyle || overlay.artStyle || "impact");
      const stroke = Math.max(0, finiteNumber(overlay.strokeWidth) * scale);
      const style = element.style;
      style.fontFamily = fontFamilies[overlay.font] || fontFamilies.modern || '"Microsoft YaHei", sans-serif';
      style.fontWeight = overlay.font === "bold" ? "800" : "700";
      style.fontSize = `${Math.max(10, finiteNumber(overlay.fontSize, 54) * scale)}px`;
      style.lineHeight = `${Math.max(10, (finiteNumber(overlay.fontSize, 54) + (overlay.direction === "vertical" ? finiteNumber(overlay.letterSpacing) : finiteNumber(overlay.lineSpacing))) * scale)}px`;
      style.textAlign = overlay.textAlign || "center";
      style.color = overlay.color;
      style.background = "transparent";
      style.backgroundClip = "border-box";
      style.webkitBackgroundClip = "border-box";
      style.border = "0";
      style.borderRadius = "0";
      style.padding = "2px 6px";
      style.boxShadow = "none";
      style.clipPath = "none";
      style.webkitTextStroke = `${stroke}px ${overlay.strokeColor}`;
      style.paintOrder = "stroke fill";
      style.textShadow = "none";
      if (artStyle === "neon") {
        style.color = "#FFFFFF";
        style.webkitTextStroke = `${Math.max(1, stroke)}px ${overlay.color}`;
        style.textShadow = `0 0 ${Math.max(3, 5 * scale)}px ${overlay.color},0 0 ${Math.max(6, 12 * scale)}px ${overlay.color},0 0 ${Math.max(10, 22 * scale)}px ${overlay.color}`;
      } else if (["gradient", "ice", "metal"].includes(artStyle)) {
        const second = artStyle === "ice" ? shiftHexColor(overlay.color, 0.32) : shiftHexColor(overlay.color, 0.48);
        const final = artStyle === "gradient" ? "#ff4d8d" : overlay.color;
        style.color = "transparent";
        style.background = `linear-gradient(180deg, #ffffff 4%, ${second} 48%, ${final} 100%)`;
        style.backgroundClip = "text";
        style.webkitBackgroundClip = "text";
        style.webkitTextStroke = `${Math.max(1, stroke + 1)}px ${overlay.strokeColor}`;
      } else if (artStyle === "comic") {
        style.webkitTextStroke = `${Math.max(2, stroke + 2)}px ${overlay.strokeColor}`;
        style.textShadow = `0 ${Math.max(1, scale)}px ${Math.max(2, 4 * scale)}px rgba(21,19,17,.58)`;
      } else if (["ink", "ribbon", "luxury", "sticker"].includes(artStyle)) {
        style.color = artStyle === "ink" ? overlay.strokeColor : "#FFFFFF";
        style.background = artStyle === "luxury" ? "rgba(7, 9, 14, .9)" : overlay.color;
        style.border = `${Math.max(1, stroke)}px solid ${artStyle === "sticker" ? "rgba(255,255,255,.95)" : overlay.color}`;
        style.borderRadius = artStyle === "ribbon" ? "3px" : "6px";
        style.padding = `${Math.max(2, 4 * scale)}px ${Math.max(5, 10 * scale)}px`;
        style.webkitTextStroke = artStyle === "ink" ? "0" : `${Math.min(2, stroke)}px ${overlay.strokeColor}`;
      } else if (artStyle === "clean") {
        style.webkitTextStroke = `${Math.min(1.5, stroke)}px ${overlay.strokeColor}`;
        style.textShadow = overlay.shadow ? `0 ${Math.max(1, 2 * scale)}px ${Math.max(3, 8 * scale)}px rgba(0,0,0,.72)` : "none";
      } else if (overlay.shadow) {
        style.textShadow = `0 ${Math.max(1, 2 * scale)}px ${Math.max(2, 5 * scale)}px rgba(0,0,0,.62)`;
      }
    }

    return Object.freeze({ applyStyle, formatText, renderCharacters, sanitizeOverlay });
  },
);
