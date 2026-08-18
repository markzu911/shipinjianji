(function exposeTranscriptFollowScroll(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.TranscriptFollowScroll = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function transcriptFollowScrollFactory(root) {
    "use strict";

    const ANCHOR_GAP = 8;
    const DEFAULT_DURATION = 240;
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
      const anchorTop = (toolbarRect?.bottom ?? panelRect.top) + ANCHOR_GAP;
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
      return {
        anchorTop,
        itemOffset,
        maxScrollTop,
        scrollDelta: targetScrollTop - startScrollTop,
        startScrollTop,
        targetScrollTop,
      };
    }

    function getTranscriptFollowScrollTarget(panel, item, toolbar) {
      return getTranscriptFollowScrollMetrics(panel, item, toolbar).targetScrollTop;
    }

    function createController(options = {}) {
      const requestFrame =
        options.requestAnimationFrame || root.requestAnimationFrame?.bind(root);
      const cancelFrame =
        options.cancelAnimationFrame || root.cancelAnimationFrame?.bind(root);
      const matchMedia = options.matchMedia || root.matchMedia?.bind(root);
      const duration = Math.max(
        1,
        finiteNumber(options.duration, DEFAULT_DURATION),
      );
      const passiveListenerOptions = { passive: true };
      let activeMotion = null;
      let followedDisplayKey = "";
      let listenerPanel = null;
      let destroyed = false;

      function clearItemStyles(item) {
        if (!item) return;
        item.classList?.remove("is-follow-animating");
        if (!item.style) return;
        item.style.transform = "";
        item.style.willChange = "";
      }

      function removeIntentListeners() {
        if (!listenerPanel?.removeEventListener) {
          listenerPanel = null;
          return;
        }
        listenerPanel.removeEventListener(
          "wheel",
          handleUserScrollIntent,
          passiveListenerOptions,
        );
        listenerPanel.removeEventListener(
          "touchstart",
          handleUserScrollIntent,
          passiveListenerOptions,
        );
        listenerPanel.removeEventListener(
          "pointerdown",
          handleUserScrollIntent,
          passiveListenerOptions,
        );
        listenerPanel.removeEventListener("keydown", handleUserScrollIntent);
        listenerPanel = null;
      }

      function cancelMotion({ clearKey = false } = {}) {
        const motion = activeMotion;
        activeMotion = null;
        if (motion?.frameId && cancelFrame) cancelFrame(motion.frameId);
        removeIntentListeners();
        clearItemStyles(motion?.item);
        if (clearKey) followedDisplayKey = "";
      }

      function handleUserScrollIntent(event) {
        if (event.type === "keydown" && !SCROLL_KEYS.has(event.key)) return;
        cancelMotion();
      }

      function addIntentListeners(panel) {
        if (!panel?.addEventListener) return;
        listenerPanel = panel;
        panel.addEventListener(
          "wheel",
          handleUserScrollIntent,
          passiveListenerOptions,
        );
        panel.addEventListener(
          "touchstart",
          handleUserScrollIntent,
          passiveListenerOptions,
        );
        panel.addEventListener(
          "pointerdown",
          handleUserScrollIntent,
          passiveListenerOptions,
        );
        panel.addEventListener("keydown", handleUserScrollIntent);
      }

      function isMotionTargetValid(motion) {
        return Boolean(
          motion.item.isConnected &&
            motion.item.classList?.contains("is-playback-active") &&
            !motion.panel.hidden &&
            motion.panel.clientHeight > 0 &&
            motion.item.closest?.(".text-editor-panel") === motion.panel,
        );
      }

      function finishMotion(motion) {
        if (activeMotion !== motion) return;
        motion.panel.scrollTop = motion.metrics.targetScrollTop;
        activeMotion = null;
        removeIntentListeners();
        clearItemStyles(motion.item);
      }

      function advanceMotion(motion, timestamp) {
        if (activeMotion !== motion) return;
        motion.frameId = 0;
        if (!isMotionTargetValid(motion)) {
          cancelMotion({ clearKey: true });
          return;
        }
        if (motion.startTime === null) motion.startTime = timestamp;
        const elapsed = Math.max(0, timestamp - motion.startTime);
        const linearProgress = clamp(elapsed / duration, 0, 1);
        const progress = 1 - Math.pow(1 - linearProgress, 3);
        const { itemOffset, scrollDelta, startScrollTop } = motion.metrics;
        motion.panel.scrollTop = startScrollTop + scrollDelta * progress;
        motion.item.style.transform =
          `translateY(${-itemOffset * (1 - progress)}px)`;
        if (linearProgress >= 1) {
          finishMotion(motion);
          return;
        }
        motion.frameId = requestFrame?.((nextTimestamp) => {
          advanceMotion(motion, nextTimestamp);
        }) || 0;
      }

      function follow(item, displayKey) {
        const normalizedKey = String(displayKey || "");
        if (destroyed || !normalizedKey || normalizedKey === followedDisplayKey) {
          return false;
        }
        cancelMotion();
        const panel = item?.closest?.(".text-editor-panel");
        if (
          !panel ||
          panel.hidden ||
          panel.clientHeight <= 0 ||
          !item.isConnected ||
          !item.classList?.contains("is-playback-active")
        ) {
          return false;
        }
        followedDisplayKey = normalizedKey;
        const toolbar = panel.querySelector?.(".cut-toolbar") || null;
        const metrics = getTranscriptFollowScrollMetrics(panel, item, toolbar);
        const reduceMotion = Boolean(
          matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
        );
        if (reduceMotion) {
          panel.scrollTop = metrics.targetScrollTop;
          return true;
        }
        if (
          Math.abs(metrics.scrollDelta) < 0.5 &&
          Math.abs(metrics.itemOffset) < 0.5
        ) {
          panel.scrollTop = metrics.targetScrollTop;
          return true;
        }

        item.classList.add("is-follow-animating");
        item.style.willChange = "transform";
        item.style.transform = `translateY(${-metrics.itemOffset}px)`;
        const motion = {
          frameId: 0,
          item,
          metrics,
          panel,
          startTime: null,
        };
        activeMotion = motion;
        addIntentListeners(panel);
        motion.frameId = requestFrame?.((timestamp) => {
          advanceMotion(motion, timestamp);
        }) || 0;
        if (!motion.frameId) finishMotion(motion);
        return true;
      }

      function reset() {
        cancelMotion({ clearKey: true });
      }

      function destroy() {
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
