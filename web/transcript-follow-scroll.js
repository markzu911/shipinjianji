(function exposeTranscriptFollowScroll(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.TranscriptFollowScroll = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function transcriptFollowScrollFactory(root) {
    "use strict";

    const ANCHOR_GAP = 8;
    const MIN_DURATION = 180;
    const MAX_DURATION = 360;
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

    function getMotionDuration(distance) {
      return Math.round(clamp(
        MIN_DURATION + Math.abs(finiteNumber(distance)) * 0.45,
        MIN_DURATION,
        MAX_DURATION,
      ));
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

    function parseTransformY(transform) {
      const value = String(transform || "").trim();
      if (!value || value === "none") return 0;
      const matrix3d = value.match(/^matrix3d\(([^)]+)\)$/);
      if (matrix3d) return finiteNumber(matrix3d[1].split(",")[13]);
      const matrix = value.match(/^matrix\(([^)]+)\)$/);
      if (matrix) return finiteNumber(matrix[1].split(",")[5]);
      const translateY = value.match(/^translateY\((-?[\d.]+)px\)$/);
      if (translateY) return finiteNumber(translateY[1]);
      const translate3d = value.match(
        /^translate3d\([^,]+,\s*(-?[\d.]+)px,\s*[^)]+\)$/,
      );
      if (translate3d) return finiteNumber(translate3d[1]);
      const translate = value.match(
        /^translate\([^,]+,\s*(-?[\d.]+)px\)$/,
      );
      return translate ? finiteNumber(translate[1]) : 0;
    }

    function createController(options = {}) {
      const layer = options.layer || root.document?.querySelector?.(
        "#transcriptNowPlayingLayer",
      );
      const matchMedia = options.matchMedia || root.matchMedia?.bind(root);
      const createElement =
        options.createElement || root.document?.createElement?.bind(root.document);
      const readComputedStyle =
        options.getComputedStyle || root.getComputedStyle?.bind(root);
      const passiveListenerOptions = { passive: true };
      let activeMotion = null;
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

      function readTransformY(element) {
        if (!element) return 0;
        const computed = readComputedStyle?.(element)?.transform;
        return parseTransformY(computed || element.style?.transform);
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

        const { item, list, originalNextSibling, originalParent, placeholder } = pinned;
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
        if (list?.style) {
          list.style.transform = "";
          list.style.willChange = "";
        }
        clearLayerStyles();
      }

      function commitCurrentListPosition(motion) {
        if (!motion || motion.phase !== "list" || !motion.pinned?.panel) return;
        const visualOffset = readTransformY(motion.pinned.list);
        if (Math.abs(visualOffset) < 0.01) return;
        const { maxScrollTop } = motion.metrics;
        const committedScrollTop = clamp(
          finiteNumber(motion.pinned.panel.scrollTop) - visualOffset,
          0,
          maxScrollTop,
        );
        if (
          Math.abs(committedScrollTop - finiteNumber(motion.pinned.panel.scrollTop)) >=
          0.01
        ) {
          motion.pinned.panel.scrollTop = committedScrollTop;
        }
      }

      function cancelMotion({ commitVisual = false } = {}) {
        const motion = activeMotion;
        if (!motion) return;
        if (commitVisual) commitCurrentListPosition(motion);
        activeMotion = null;
        for (const animation of motion.animations) {
          animation.onfinish = null;
          animation.cancel?.();
        }
        motion.animations.clear();
        if (motion.pinned?.list?.style) {
          motion.pinned.list.style.transform = "";
          motion.pinned.list.style.willChange = "";
        }
        layer?.classList?.remove("is-follow-animating");
        if (layer?.style) layer.style.willChange = "";
      }

      function stopAndRestore({ clearKey = false, commitVisual = false } = {}) {
        cancelMotion({ commitVisual });
        restorePinnedItem();
        if (clearKey) followedDisplayKey = "";
      }

      function handleUserScrollIntent(event) {
        if (event.type === "keydown" && !SCROLL_KEYS.has(event.key)) return;
        stopAndRestore({ commitVisual: true });
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

      function placeLayer(itemRect, anchorTop) {
        const positioningContext = layer.offsetParent || layer.parentElement;
        const contextRect = positioningContext?.getBoundingClientRect?.() || {
          left: 0,
          top: 0,
        };
        const contextLeft = finiteNumber(contextRect.left) +
          finiteNumber(positioningContext?.clientLeft);
        const contextTop = finiteNumber(contextRect.top) +
          finiteNumber(positioningContext?.clientTop);
        layer.hidden = false;
        layer.style.height = `${itemRect.height}px`;
        layer.style.left = `${itemRect.left - contextLeft}px`;
        layer.style.top = `${anchorTop - contextTop}px`;
        layer.style.width = `${itemRect.width}px`;
      }

      function finishTransformAnimation(
        motion,
        animation,
        element,
        targetOffset,
        onFinish,
      ) {
        if (activeMotion !== motion) return;
        motion.animations.delete(animation);
        animation.onfinish = null;
        setTransformY(element, targetOffset);
        animation.cancel?.();
        onFinish();
      }

      function animateTransform(
        motion,
        element,
        startOffset,
        targetOffset,
        duration,
        onFinish,
      ) {
        setTransformY(element, startOffset);
        if (
          Math.abs(targetOffset - startOffset) < 0.5 ||
          typeof element?.animate !== "function"
        ) {
          setTransformY(element, targetOffset);
          onFinish();
          return;
        }
        const animation = element.animate(
          [
            { transform: `translate3d(0, ${startOffset}px, 0)` },
            { transform: `translate3d(0, ${targetOffset}px, 0)` },
          ],
          {
            duration,
            easing: "cubic-bezier(0.22, 1, 0.36, 1)",
            fill: "both",
          },
        );
        if (!animation) {
          setTransformY(element, targetOffset);
          onFinish();
          return;
        }
        motion.animations.add(animation);
        animation.onfinish = () => {
          finishTransformAnimation(
            motion,
            animation,
            element,
            targetOffset,
            onFinish,
          );
        };
      }

      function finishMotion(motion) {
        if (activeMotion !== motion) return;
        activeMotion = null;
        motion.pinned.list.style.transform = "";
        motion.pinned.list.style.willChange = "";
        layer.classList?.remove("is-follow-animating");
        layer.style.willChange = "";
      }

      function startTailPhase(motion) {
        if (activeMotion !== motion) return;
        if (!isPinnedTargetValid(motion.pinned)) {
          stopAndRestore({ clearKey: true, commitVisual: true });
          return;
        }
        motion.phase = "tail";
        const tailRemainder = motion.metrics.tailRemainder;
        if (Math.abs(tailRemainder) < 0.5) {
          setTransformY(layer, 0);
          finishMotion(motion);
          return;
        }
        layer.style.willChange = "transform";
        animateTransform(
          motion,
          layer,
          motion.tailStartOffset,
          tailRemainder,
          getMotionDuration(tailRemainder - motion.tailStartOffset),
          () => finishMotion(motion),
        );
      }

      function completeListPhasePart(motion) {
        if (activeMotion !== motion) return;
        motion.pendingListAnimations -= 1;
        if (motion.pendingListAnimations <= 0) startTailPhase(motion);
      }

      function startListPhase(motion) {
        const { list } = motion.pinned;
        const { scrollDelta, tailRemainder } = motion.metrics;
        const entryDistance = motion.startLayerOffset;
        const hasListMotion = Math.abs(scrollDelta) >= 0.5;
        const hasTailMotion = Math.abs(tailRemainder) >= 0.5;
        const hasEntryMotion = !hasTailMotion && Math.abs(entryDistance) >= 0.5;
        motion.tailStartOffset = hasTailMotion ? entryDistance : 0;
        motion.phase = "list";
        motion.pendingListAnimations = Number(hasListMotion) + Number(hasEntryMotion);

        motion.pinned.panel.scrollTop = motion.metrics.targetScrollTop;
        if (!hasListMotion && !hasEntryMotion) {
          startTailPhase(motion);
          return;
        }
        if (!hasEntryMotion) setTransformY(layer, motion.tailStartOffset);
        if (hasListMotion) {
          list.style.willChange = "transform";
          animateTransform(
            motion,
            list,
            scrollDelta,
            0,
            getMotionDuration(scrollDelta),
            () => completeListPhasePart(motion),
          );
        } else {
          setTransformY(list, 0);
        }
        if (hasEntryMotion) {
          layer.style.willChange = "transform";
          animateTransform(
            motion,
            layer,
            entryDistance,
            0,
            getMotionDuration(entryDistance),
            () => completeListPhasePart(motion),
          );
        }
      }

      function follow(item, displayKey) {
        const normalizedKey = String(displayKey || "");
        if (destroyed || !normalizedKey || !layer) return false;
        if (normalizedKey === followedDisplayKey) {
          if (pinnedItem && !isPinnedTargetValid()) {
            stopAndRestore({ clearKey: true, commitVisual: true });
          }
          return false;
        }

        const previousVisualTop = pinnedItem && !layer.hidden
          ? layer.getBoundingClientRect?.().top
          : null;
        stopAndRestore({ commitVisual: true });
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
        const originalParent = item.parentNode;
        const originalNextSibling = item.nextSibling;
        const placeholder = createPlaceholder(item, itemRect);
        if (!placeholder) return false;

        placeLayer(itemRect, metrics.anchorTop);
        layer.appendChild(item);
        pinnedItem = {
          item,
          list: originalParent,
          originalNextSibling,
          originalParent,
          panel,
          placeholder,
        };
        followedDisplayKey = normalizedKey;
        addIntentListeners(panel);

        const startLayerOffset = Number.isFinite(previousVisualTop)
          ? previousVisualTop - metrics.anchorTop
          : metrics.itemOffset;
        setTransformY(layer, startLayerOffset);
        const reduceMotion = Boolean(
          matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
        );
        if (reduceMotion) {
          panel.scrollTop = metrics.targetScrollTop;
          setTransformY(originalParent, 0);
          setTransformY(layer, metrics.tailRemainder);
          return true;
        }

        layer.classList?.add("is-follow-animating");
        const motion = {
          animations: new Set(),
          metrics,
          pendingListAnimations: 0,
          phase: "list",
          pinned: pinnedItem,
          startLayerOffset,
          tailStartOffset: 0,
        };
        activeMotion = motion;
        startListPhase(motion);
        return true;
      }

      function reset() {
        stopAndRestore({ clearKey: true, commitVisual: true });
      }

      function destroy() {
        reset();
        destroyed = true;
      }

      return { destroy, follow, reset };
    }

    return {
      createController,
      getMotionDuration,
      getTranscriptFollowScrollMetrics,
      getTranscriptFollowScrollTarget,
      parseTransformY,
    };
  },
);
