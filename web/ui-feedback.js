(() => {
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  );
  let dialog = null;
  let activeResolve = null;
  let closingTimer = null;
  let previouslyFocused = null;
  let queue = Promise.resolve();

  function createDialog() {
    const element = document.createElement("dialog");
    element.className = "app-dialog-shell";
    element.setAttribute("aria-labelledby", "appDialogTitle");
    element.setAttribute("aria-describedby", "appDialogMessage");
    element.innerHTML = `
      <section class="app-dialog-card">
        <div class="app-dialog-signal" aria-hidden="true">
          <span class="app-dialog-signal-line"></span>
          <span class="app-dialog-signal-code">SYS / CHECK</span>
        </div>
        <div class="app-dialog-heading">
          <span class="app-dialog-icon" aria-hidden="true">
            <iconify-icon id="appDialogIcon" icon="ph:warning-circle-bold"></iconify-icon>
          </span>
          <div>
            <p id="appDialogEyebrow" class="app-dialog-eyebrow">请确认操作</p>
            <h2 id="appDialogTitle">继续当前操作？</h2>
          </div>
        </div>
        <p id="appDialogMessage" class="app-dialog-message"></p>
        <div class="app-dialog-actions">
          <button id="appDialogCancel" class="app-dialog-button is-secondary" type="button">取消</button>
          <button id="appDialogConfirm" class="app-dialog-button is-primary" type="button">确认</button>
        </div>
      </section>
    `;
    document.body.append(element);

    element.querySelector("#appDialogCancel").addEventListener("click", () => {
      closeDialog(false);
    });
    element.querySelector("#appDialogConfirm").addEventListener("click", () => {
      closeDialog(true);
    });
    element.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDialog(false);
    });
    element.addEventListener("click", (event) => {
      if (event.target === element) closeDialog(false);
    });
    return element;
  }

  function finishClose(value) {
    if (!dialog?.open) return;
    window.clearTimeout(closingTimer);
    dialog.close();
    dialog.classList.remove("is-visible", "is-closing");
    const resolve = activeResolve;
    activeResolve = null;
    resolve?.(value);
    if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    previouslyFocused = null;
  }

  function closeDialog(value) {
    if (!dialog?.open || dialog.classList.contains("is-closing")) return;
    if (prefersReducedMotion.matches) {
      finishClose(value);
      return;
    }
    dialog.classList.add("is-closing");
    closingTimer = window.setTimeout(() => finishClose(value), 135);
  }

  function presentDialog(options) {
    dialog ||= createDialog();
    const {
      title = "继续当前操作？",
      message = "请确认是否继续。",
      eyebrow = "请确认操作",
      confirmText = "确认",
      cancelText = "取消",
      tone = "default",
      icon = tone === "danger" ? "ph:trash-bold" : "ph:warning-circle-bold",
    } = options || {};

    dialog.dataset.tone = tone;
    dialog.querySelector("#appDialogEyebrow").textContent = eyebrow;
    dialog.querySelector("#appDialogTitle").textContent = title;
    dialog.querySelector("#appDialogMessage").textContent = message;
    dialog.querySelector("#appDialogIcon").setAttribute("icon", icon);
    const cancelButton = dialog.querySelector("#appDialogCancel");
    const confirmButton = dialog.querySelector("#appDialogConfirm");
    cancelButton.hidden = !cancelText;
    cancelButton.textContent = cancelText || "";
    confirmButton.textContent = confirmText;
    dialog.classList.remove("is-closing");
    previouslyFocused = document.activeElement;

    return new Promise((resolve) => {
      activeResolve = resolve;
      dialog.showModal();
      window.requestAnimationFrame(() => {
        dialog.classList.add("is-visible");
        confirmButton.focus();
      });
    });
  }

  function enqueue(options) {
    const result = queue.then(() => presentDialog(options));
    queue = result.catch(() => false).then(() => undefined);
    return result;
  }

  window.appConfirm = (options) =>
    enqueue(typeof options === "string" ? { message: options } : options);
  window.appAlert = (options) =>
    enqueue({
      eyebrow: "操作未完成",
      title: "需要处理一个问题",
      confirmText: "我知道了",
      cancelText: "",
      tone: "danger",
      icon: "ph:warning-octagon-bold",
      ...(typeof options === "string" ? { message: options } : options),
    });

  // --- Video generation modal ---------------------------------------------
  // A full-screen overlay that blocks other interactions while a video is being
  // generated, shows a live progress bar, then previews the finished video with
  // a download button.
  let generationOverlay = null;
  let generationOnClose = null;

  function clampPercent(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.max(0, Math.min(100, Math.round(number)));
  }

  function buildGenerationModal() {
    const overlay = document.createElement("div");
    overlay.className = "generation-overlay";
    overlay.setAttribute("hidden", "");
    overlay.innerHTML = `
      <div class="generation-card" role="dialog" aria-modal="true" aria-labelledby="generationTitle">
        <div class="generation-card-head">
          <h2 id="generationTitle">生成视频</h2>
          <span id="generationPercent" class="generation-percent">0%</span>
        </div>
        <p id="generationStatus" class="generation-status">正在准备…</p>
        <div id="generationTrack" class="generation-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
          <div id="generationBar" class="generation-bar"></div>
        </div>
        <div id="generationVideoWrap" class="generation-video-wrap" hidden>
          <video id="generationVideo" controls autoplay playsinline preload="auto"></video>
          <p id="generationVideoMeta" class="generation-video-meta"></p>
        </div>
        <div class="generation-actions">
          <a id="generationDownload" class="generation-button is-primary" href="#" download hidden>下载成片</a>
          <button id="generationClose" class="generation-button is-secondary" type="button" hidden>知道了</button>
        </div>
      </div>
    `;
    document.body.append(overlay);
    overlay.querySelector("#generationClose").addEventListener("click", () => {
      hideGenerationModal();
    });
    return overlay;
  }

  function generationEls() {
    if (!generationOverlay) generationOverlay = buildGenerationModal();
    return {
      overlay: generationOverlay,
      title: generationOverlay.querySelector("#generationTitle"),
      status: generationOverlay.querySelector("#generationStatus"),
      percent: generationOverlay.querySelector("#generationPercent"),
      bar: generationOverlay.querySelector("#generationBar"),
      track: generationOverlay.querySelector("#generationTrack"),
      videoWrap: generationOverlay.querySelector("#generationVideoWrap"),
      video: generationOverlay.querySelector("#generationVideo"),
      videoMeta: generationOverlay.querySelector("#generationVideoMeta"),
      download: generationOverlay.querySelector("#generationDownload"),
      close: generationOverlay.querySelector("#generationClose"),
    };
  }

  function showGenerationModal(options = {}) {
    const els = generationEls();
    els.title.textContent = options.title || "生成视频";
    els.status.textContent = options.status || "正在准备…";
    els.status.classList.remove("is-error");
    if (options.progress != null) {
      const value = clampPercent(options.progress);
      els.bar.classList.remove("is-indeterminate");
      els.bar.style.width = `${value}%`;
      els.percent.textContent = `${value}%`;
      els.track.setAttribute("aria-valuenow", String(value));
    } else {
      els.bar.classList.add("is-indeterminate");
      els.bar.style.width = "100%";
      els.percent.textContent = "";
    }
    els.videoWrap.hidden = true;
    els.download.hidden = true;
    els.close.hidden = true;
    generationOnClose = options.onClose || null;
    els.overlay.hidden = false;
    document.body.classList.add("has-generation-modal");
  }

  function updateGenerationProgress(progress, message) {
    const els = generationEls();
    const value = clampPercent(progress);
    els.bar.classList.remove("is-indeterminate");
    els.bar.style.width = `${value}%`;
    els.percent.textContent = `${value}%`;
    els.track.setAttribute("aria-valuenow", String(value));
    if (message) els.status.textContent = message;
  }

  function completeGeneration(options = {}) {
    const els = generationEls();
    els.bar.classList.remove("is-indeterminate");
    els.bar.style.width = "100%";
    els.percent.textContent = "100%";
    els.track.setAttribute("aria-valuenow", "100");
    els.status.textContent = options.status || "生成完成";
    if (options.videoUrl) {
      els.video.src = options.videoUrl;
      els.video.load();
      void els.video.play().catch(() => {});
      els.videoWrap.hidden = false;
      els.videoMeta.textContent = options.duration
        ? `成片时长 ${options.duration}`
        : "";
    }
    if (options.downloadUrl) {
      els.download.href = options.downloadUrl;
      els.download.hidden = false;
    }
    els.close.hidden = false;
  }

  function failGeneration(message) {
    const els = generationEls();
    els.bar.classList.remove("is-indeterminate");
    els.status.classList.add("is-error");
    els.status.textContent = message || "生成失败，请重试。";
    els.close.hidden = false;
  }

  function hideGenerationModal() {
    if (!generationOverlay) return;
    const els = generationEls();
    els.video.pause();
    els.video.removeAttribute("src");
    els.video.load();
    els.status.classList.remove("is-error");
    els.overlay.hidden = true;
    document.body.classList.remove("has-generation-modal");
    if (generationOnClose) {
      const callback = generationOnClose;
      generationOnClose = null;
      callback();
    }
  }

  window.appGeneration = {
    show: showGenerationModal,
    setProgress: updateGenerationProgress,
    complete: completeGeneration,
    fail: failGeneration,
    hide: hideGenerationModal,
  };
})();
