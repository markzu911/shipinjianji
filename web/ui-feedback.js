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
})();
