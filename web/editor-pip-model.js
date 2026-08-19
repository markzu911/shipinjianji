(function exposeEditorPipModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorPipModel = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function editorPipModelFactory() {
    "use strict";

    const SOURCES = Object.freeze(["original", "edited", "art"]);
    const MIN_WIDTH = 0.15;
    const DEFAULT_WIDTH = 0.32;
    const MAX_ASSETS = 20;

    function clone(value) {
      return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
    }

    function finite(value, fallback = null) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function clamp(value, minimum, maximum) {
      return Math.min(maximum, Math.max(minimum, value));
    }

    function normalizeSource(value, fallback = "original") {
      const source = String(value || "");
      return SOURCES.includes(source) ? source : normalizeSource(fallback, "original");
    }

    function assetId(value) {
      return String(value?.id || value?.assetId || value?.imageId || "").trim();
    }

    function assetType(value) {
      return value?.type === "video" || value?.assetType === "video"
        ? "video"
        : "image";
    }

    function assetStatus(value) {
      if (assetType(value) === "image") return String(value?.status || "completed");
      return String(value?.status || "queued");
    }

    function isReadyAsset(value) {
      return assetStatus(value) === "completed" && Boolean(
        value?.assetUrl || value?.imageUrl || value?.url,
      );
    }

    function normalizeAsset(value, options = {}) {
      const id = assetId(value);
      if (!id) return null;
      const source = normalizeSource(value?.source, options.source || "original");
      return {
        ...clone(value),
        id,
        type: assetType(value),
        source,
        status: assetStatus(value),
        assetUrl: String(value?.assetUrl || value?.imageUrl || value?.url || ""),
        text: String(value?.text || ""),
      };
    }

    function normalizeAssets(values, options = {}) {
      const records = Array.isArray(values)
        ? values
        : values && typeof values === "object"
          ? Object.values(values)
          : [];
      const byId = new Map();
      for (const value of records) {
        const record = normalizeAsset(value, options);
        if (!record) continue;
        if (options.source && record.source !== normalizeSource(options.source)) continue;
        const previous = byId.get(record.id);
        byId.set(record.id, previous ? { ...previous, ...record } : record);
      }
      return [...byId.values()];
    }

    function mergeAssets(current, incoming, options = {}) {
      return normalizeAssets(
        [...normalizeAssets(current, options), ...normalizeAssets(incoming, options)],
        options,
      );
    }

    function normalizeRange(startValue, endValue, durationValue, minimum = 0.05) {
      const duration = Math.max(0, finite(durationValue, 0));
      const start = clamp(finite(startValue, 0), 0, duration);
      const end = clamp(finite(endValue, start), 0, duration);
      if (end - start < minimum) return null;
      return { start, end };
    }

    function normalizeOverlay(value, options = {}) {
      const id = assetId(value);
      if (!id) return null;
      if (
        options.strict &&
        ![value?.start, value?.end, value?.x, value?.y, value?.width].every(
          (item) => typeof item === "number" && Number.isFinite(item),
        )
      ) {
        return null;
      }
      const hasSourceStart = value?.sourceStart !== undefined && value?.sourceStart !== null;
      const hasSourceEnd = value?.sourceEnd !== undefined && value?.sourceEnd !== null;
      if (
        options.strict &&
        (
          hasSourceStart !== hasSourceEnd ||
          (hasSourceStart &&
            (typeof value.sourceStart !== "number" ||
              typeof value.sourceEnd !== "number" ||
              !Number.isFinite(value.sourceStart) ||
              !Number.isFinite(value.sourceEnd) ||
              value.sourceEnd <= value.sourceStart)) ||
          (value?.enabled !== undefined && value.enabled !== true)
        )
      ) {
        return null;
      }
      const duration = Math.max(0, finite(options.duration, 0));
      const range = normalizeRange(
        value?.start,
        value?.end,
        duration || Number.MAX_SAFE_INTEGER,
        options.minimumDuration || 0.05,
      );
      const width = finite(value?.width, DEFAULT_WIDTH);
      const x = finite(value?.x, 0.8);
      const y = finite(value?.y, 0.2);
      if (!range || width < MIN_WIDTH || x < 0.05 || x > 0.95 || y < 0.05 || y > 0.95) {
        return null;
      }
      const sourceStart = finite(value?.sourceStart);
      const sourceEnd = finite(value?.sourceEnd);
      return {
        ...clone(value),
        id,
        assetId: id,
        ...(value?.imageId ? { imageId: String(value.imageId) } : {}),
        start: range.start,
        end: range.end,
        ...(sourceStart !== null && sourceEnd !== null && sourceEnd > sourceStart
          ? { sourceStart, sourceEnd }
          : {}),
        x,
        y,
        width,
        enabled: value?.enabled !== false,
      };
    }

    function normalizeOverlays(values, options = {}) {
      const assets = normalizeAssets(options.assets, { source: options.source });
      const assetsById = new Map(assets.map((asset) => [asset.id, asset]));
      const seen = new Set();
      const overlays = [];
      for (const value of Array.isArray(values) ? values : []) {
        if (value?.enabled === false) {
          if (options.strict) return null;
          continue;
        }
        const overlay = normalizeOverlay(value, options);
        if (!overlay || seen.has(overlay.id)) {
          if (options.strict) return null;
          continue;
        }
        const asset = assetsById.get(overlay.assetId);
        if (options.requireAsset && (!asset || asset.source !== normalizeSource(options.source))) {
          if (options.strict) return null;
          continue;
        }
        if (asset && !isReadyAsset(asset)) {
          if (options.strict) return null;
          continue;
        }
        seen.add(overlay.id);
        overlays.push(overlay);
      }
      if (overlays.length > MAX_ASSETS) return options.strict ? null : overlays.slice(0, MAX_ASSETS);
      return overlays;
    }

    function normalizeProject(value = {}, options = {}) {
      const source = normalizeSource(value?.source, options.fallbackSource || "original");
      const assets = mergeAssets(options.assets, value?.assets, { source });
      const overlays = normalizeOverlays(value?.overlays, {
        duration: options.duration,
        assets,
        source,
        requireAsset: Boolean(options.requireAsset),
      }) || [];
      return { source, assets, overlays };
    }

    function createOverlay(assetValue, durationValue, options = {}) {
      const asset = normalizeAsset(assetValue, { source: options.source });
      if (!asset || !isReadyAsset(asset)) return null;
      const duration = Math.max(0, finite(durationValue, 0));
      const range = normalizeRange(asset.start, asset.end, duration, 0.05);
      if (!range) return null;
      const sourceStart = finite(asset.sourceStart);
      const sourceEnd = finite(asset.sourceEnd);
      return normalizeOverlay(
        {
          id: asset.id,
          assetId: asset.id,
          ...(asset.type === "image" ? { imageId: asset.id } : {}),
          ...range,
          ...(sourceStart !== null && sourceEnd !== null && sourceEnd > sourceStart
            ? { sourceStart, sourceEnd }
            : {}),
          x: finite(options.x, 0.8),
          y: finite(options.y, 0.2),
          width: Math.max(MIN_WIDTH, finite(options.width, DEFAULT_WIDTH)),
          enabled: true,
        },
        { duration },
      );
    }

    function setAssetEnabled(projectValue, idValue, enabled, options = {}) {
      const project = normalizeProject(projectValue, options);
      const id = String(idValue || "");
      const retained = project.overlays.filter((overlay) => overlay.assetId !== id);
      if (!enabled) return { ...project, overlays: retained };
      const existing = project.overlays.find((overlay) => overlay.assetId === id);
      if (existing) return project;
      const asset = project.assets.find((record) => record.id === id);
      const overlay = createOverlay(asset, options.duration, options);
      return overlay ? { ...project, overlays: [...project.overlays, overlay] } : project;
    }

    function buildTimeline(projectValue, durationValue, selection = null) {
      const duration = Math.max(0, finite(durationValue, 0));
      const project = normalizeProject(projectValue, { duration });
      const tracks = project.overlays.map((overlay, index) => ({
        id: `pip:overlay:${overlay.assetId}`,
        kind: "pip",
        name: "画中画",
        order: index,
        clips: [{
          id: `pip:${overlay.assetId}`,
          sourceId: overlay.assetId,
          kind: "pip",
          name: "画中画",
          start: overlay.start,
          end: overlay.end,
          minDuration: 0.05,
          editable: true,
          payload: {
            assetId: overlay.assetId,
            sourceStart: finite(overlay.sourceStart),
            sourceEnd: finite(overlay.sourceEnd),
          },
        }],
      }));
      const clipIds = new Set(tracks.flatMap((track) => track.clips.map((clip) => clip.id)));
      const clipId = String(selection?.clipId || selection || "");
      return {
        schemaVersion: 1,
        duration,
        tracks,
        selection: clipIds.has(clipId) ? { clipId } : null,
      };
    }

    function validateDraftOverlays(values, options = {}) {
      if (!Array.isArray(values) || values.length > MAX_ASSETS) return null;
      return normalizeOverlays(values, {
        ...options,
        strict: true,
        requireAsset: true,
      });
    }

    return Object.freeze({
      SOURCES,
      MIN_WIDTH,
      DEFAULT_WIDTH,
      MAX_ASSETS,
      assetId,
      isReadyAsset,
      normalizeSource,
      normalizeAsset,
      normalizeAssets,
      mergeAssets,
      normalizeRange,
      normalizeOverlay,
      normalizeOverlays,
      normalizeProject,
      createOverlay,
      setAssetEnabled,
      buildTimeline,
      validateDraftOverlays,
    });
  },
);
