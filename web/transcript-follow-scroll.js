(function exposeTranscriptFollowScroll(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.TranscriptFollowScroll = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function transcriptFollowScrollFactory(root) {
    "use strict";

    const ANCHOR_GAP = 8;
    const SCROLL_KEYS = new Set([
      "ArrowDown",
      "ArrowUp",
      "End",
      "Home",
      "PageDown",
      "PageUp",
      " ",
      "Spacebar",
    ]);

    function clamp(value, minimum, maximum) {
      return Math.min(maximum, Math.max(minimum, value));
    }

    function finiteNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function getTranscriptFollowScrollMetrics(panel, item, toolbar) {
      const panelRect = panel.getBoundingClientRect();
      const itemRect = item.getBoundingClientRect();
      const toolbarRect = toolbar?.getBoundingClientRect();
      let toolbarBottom = toolbarRect?.bottom ?? panelRect.top;
      const toolbarStyle = toolbar && root.getComputedStyle?.(toolbar);
      if (toolbarRect && toolbarStyle?.position === "sticky") {
        const stickyTop = Number.parseFloat(toolbarStyle.top);
        const panelStyle = root.getComputedStyle?.(panel);
        const paddingTop = Number.parseFloat(panelStyle?.paddingTop) || 0;
        if (Number.isFinite(stickyTop)) {
          const restingBottom = panelRect.top +
            finiteNumber(panel.clientTop) +
            paddingTop +
            stickyTop +
            finiteNumber(toolbarRect.height);
          toolbarBottom = Math.min(toolbarBottom, restingBottom);
        }
      }
      const baseAnchorTop = toolbarBottom + ANCHOR_GAP;
      const desiredAnchorTop = baseAnchorTop + itemRect.height * 3;
      const maximumAnchorTop = Math.max(
        baseAnchorTop,
        panelRect.bottom - itemRect.height,
      );
      const anchorTop = Math.min(desiredAnchorTop, maximumAnchorTop);
      const startScrollTop = finiteNumber(panel.scrollTop);
      const maxScrollTop = Math.max(
        0,
        finiteNumber(panel.scrollHeight) - finiteNumber(panel.clientHeight),
      );
      const itemOffset = itemRect.top - anchorTop;
      const targetScrollTop = clamp(
        startScrollTop + itemOffset,
        0,
        maxScrollTop,
      );
      const scrollDelta = targetScrollTop - startScrollTop;
      return {
        anchorTop,
        itemOffset,
        maxScrollTop,
        scrollDelta,
        startScrollTop,
        tailRemainder: itemOffset - scrollDelta,
        targetScrollTop,
      };
    }

    function getTranscriptFollowScrollTarget(panel, item, toolbar) {
      return getTranscriptFollowScrollMetrics(panel, item, toolbar).targetScrollTop;
    }

    function createController(options = {}) {
      const layer = options.layer || root.document?.querySelector?.(
        "#transcriptNowPlayingLayer",
      );
      const createElement =
        options.createElement || root.document?.createElement?.bind(root.document);
      const passiveListenerOptions = { passive: true };
      let pinnedItem = null;
      let followedDisplayKey = "";
      let listenerTargets = [];
      let destroyed = false;

      function setTransformY(element, offset) {
        if (!element?.style) return;
        const normalizedOffset = Math.abs(finiteNumber(offset)) < 0.01
          ? 0
          : finiteNumber(offset);
        element.style.transform = normalizedOffset
          ? `translate3d(0, ${normalizedOffset}px, 0)`
          : "";
      }

      function clearLayerStyles() {
        if (!layer) return;
        layer.classList?.remove("is-follow-animating");
        if (layer.style) {
          layer.style.height = "";
          layer.style.left = "";
          layer.style.top = "";
          layer.style.transform = "";
          layer.style.width = "";
          layer.style.willChange = "";
        }
        layer.hidden = true;
      }

      function removeIntentListeners() {
        for (const target of listenerTargets) {
          if (!target?.removeEventListener) continue;
          target.removeEventListener(
            "wheel",
            handleUserScrollIntent,
            passiveListenerOptions,
          );
          target.removeEventListener(
            "touchstart",
            handleUserScrollIntent,
            passiveListenerOptions,
          );
          target.removeEventListener(
            "pointerdown",
            handleUserScrollIntent,
            passiveListenerOptions,
          );
          target.removeEventListener("keydown", handleUserScrollIntent);
        }
        listenerTargets = [];
      }

      function removePlaceholder(placeholder) {
        if (!placeholder) return;
        if (typeof placeholder.remove === "function") {
          placeholder.remove();
        } else if (placeholder.parentNode?.removeChild) {
          placeholder.parentNode.removeChild(placeholder);
        }
      }

      function restorePinnedItem() {
        const pinned = pinnedItem;
        pinnedItem = null;
        removeIntentListeners();
        if (!pinned) {
          clearLayerStyles();
          return;
        }

        const { item, originalNextSibling, originalParent, placeholder } = pinned;
        if (placeholder?.parentNode?.insertBefore) {
          placeholder.parentNode.insertBefore(item, placeholder);
        } else if (originalParent?.insertBefore) {
          const reference = originalNextSibling?.parentNode === originalParent
            ? originalNextSibling
            : null;
          originalParent.insertBefore(item, reference);
        } else if (originalParent?.appendChild) {
          originalParent.appendChild(item);
        }
        removePlaceholder(placeholder);
        clearLayerStyles();
      }

      function stopAndRestore({ clearKey = false } = {}) {
        restorePinnedItem();
        if (clearKey) followedDisplayKey = "";
      }

      function handleUserScrollIntent(event) {
        if (event.type === "keydown" && !SCROLL_KEYS.has(event.key)) return;
        stopAndRestore();
      }

      function addIntentListeners(panel) {
        removeIntentListeners();
        listenerTargets = [panel, layer].filter(
          (target, index, targets) =>
            target?.addEventListener && targets.indexOf(target) === index,
        );
        for (const target of listenerTargets) {
          target.addEventListener(
            "wheel",
            handleUserScrollIntent,
            passiveListenerOptions,
          );
          target.addEventListener(
            "touchstart",
            handleUserScrollIntent,
            passiveListenerOptions,
          );
          target.addEventListener(
            "pointerdown",
            handleUserScrollIntent,
            passiveListenerOptions,
          );
          target.addEventListener("keydown", handleUserScrollIntent);
        }
      }

      function isPinnedTargetValid(pinned = pinnedItem) {
        return Boolean(
          pinned &&
            pinned.item.isConnected &&
            pinned.item.classList?.contains("is-playback-active") &&
            pinned.item.parentNode === layer &&
            pinned.placeholder?.isConnected &&
            pinned.placeholder.parentNode &&
            !pinned.panel.hidden &&
            pinned.panel.clientHeight > 0,
        );
      }

      function createPlaceholder(item, itemRect) {
        const placeholder = createElement?.("li");
        if (!placeholder) return null;
        placeholder.className = "segment-follow-placeholder";
        placeholder.setAttribute?.("aria-hidden", "true");
        placeholder.setAttribute?.("inert", "");
        placeholder.inert = true;
        if (placeholder.style) {
          placeholder.style.height = `${itemRect.height}px`;
          placeholder.style.minHeight = `${itemRect.height}px`;
        }
        item.parentNode.insertBefore(placeholder, item);
        return placeholder;
      }

      function getLayerPlacement(itemRect, anchorTop) {
        const positioningContext = layer.offsetParent || layer.parentElement;
        const contextRect = positioningContext?.getBoundingClientRect?.() || {
          left: 0,
          top: 0,
        };
        const contextLeft = finiteNumber(contextRect.left) +
          finiteNumber(positioningContext?.clientLeft);
        const contextTop = finiteNumber(contextRect.top) +
          finiteNumber(positioningContext?.clientTop);
        return {
          height: `${itemRect.height}px`,
          left: `${itemRect.left - contextLeft}px`,
          top: `${anchorTop - contextTop}px`,
          width: `${itemRect.width}px`,
        };
      }

      function placeLayer(placement) {
        layer.hidden = false;
        layer.style.height = placement.height;
        layer.style.left = placement.left;
        layer.style.top = placement.top;
        layer.style.width = placement.width;
      }

      function follow(item, displayKey) {
        const normalizedKey = String(displayKey || "");
        if (destroyed || !normalizedKey || !layer) return false;
        if (normalizedKey === followedDisplayKey) {
          if (pinnedItem && !isPinnedTargetValid()) {
            stopAndRestore({ clearKey: true });
          }
          return false;
        }

        stopAndRestore();
        const panel = item?.closest?.(".text-editor-panel");
        if (
          !panel ||
          panel.hidden ||
          panel.clientHeight <= 0 ||
          !item.isConnected ||
          !item.classList?.contains("is-playback-active") ||
          !item.parentNode?.insertBefore ||
          !layer.appendChild
        ) {
          return false;
        }

        const toolbar = panel.querySelector?.(".cut-toolbar") || null;
        const itemRect = item.getBoundingClientRect();
        const metrics = getTranscriptFollowScrollMetrics(panel, item, toolbar);
        const layerPlacement = getLayerPlacement(itemRect, metrics.anchorTop);
        const originalParent = item.parentNode;
        const originalNextSibling = item.nextSibling;
        const placeholder = createPlaceholder(item, itemRect);
        if (!placeholder) return false;

        placeLayer(layerPlacement);
        layer.appendChild(item);
        pinnedItem = {
          item,
          originalNextSibling,
          originalParent,
          panel,
          placeholder,
        };
        followedDisplayKey = normalizedKey;
        addIntentListeners(panel);
        panel.scrollTop = metrics.targetScrollTop;
        setTransformY(layer, metrics.tailRemainder);
        return true;
      }

      function reset() {
        stopAndRestore({ clearKey: true });
      }

      function destroy() {
        if (destroyed) return;
        reset();
        destroyed = true;
      }

      return { destroy, follow, reset };
    }

    return {
      createController,
      getTranscriptFollowScrollMetrics,
      getTranscriptFollowScrollTarget,
    };
  },
);
