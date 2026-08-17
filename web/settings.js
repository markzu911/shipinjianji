(() => {
  const providerSettings = document.querySelector("#providerSettings");
  const loading = document.querySelector("#settingsLoading");
  const pageError = document.querySelector("#settingsError");
  const pageErrorText = document.querySelector("#settingsErrorText");
  const configuredProviderCount = document.querySelector("#configuredProviderCount");
  const retryButton = document.querySelector("#retrySettingsButton");

  let providers = [];

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    if (!response.ok) {
      let message = "请求失败，请稍后重试。";
      try {
        const body = await response.json();
        if (body.detail) message = body.detail;
      } catch {
        // Keep the generic recovery message for non-JSON responses.
      }
      throw new Error(message);
    }
    return response.json();
  }

  function providerIcon(providerId) {
    return providerId === "dashscope" ? "ph:cloud-bold" : "ph:fire-bold";
  }

  function renderProviders() {
    const configuredCount = providers.filter((provider) => provider.configured).length;
    configuredProviderCount.textContent = `${configuredCount} / ${providers.length} 个服务已配置`;
    providerSettings.innerHTML = providers.map((provider) => `
      <article class="panel provider-card" data-provider-id="${escapeHtml(provider.id)}">
        <div class="provider-card-heading">
          <span class="provider-icon" aria-hidden="true">
            <iconify-icon icon="${providerIcon(provider.id)}"></iconify-icon>
          </span>
          <div>
            <p class="step-label">${escapeHtml(provider.environmentVariable)}</p>
            <h2>${escapeHtml(provider.name)}</h2>
          </div>
          <span class="provider-status ${provider.configured ? "is-configured" : ""}">
            <iconify-icon icon="${provider.configured ? "ph:check-circle-fill" : "ph:warning-circle-bold"}" aria-hidden="true"></iconify-icon>
            ${provider.configured ? "已配置" : "未配置"}
          </span>
        </div>

        <form class="credential-form" novalidate>
          <fieldset class="provider-models">
            <legend>模型名称</legend>
            <div class="provider-model-list">
            ${provider.models.map((item) => `
              <label class="provider-config-field">
                <span>${escapeHtml(item.role)}</span>
                <input
                  name="model-${escapeHtml(item.id)}"
                  data-model-id="${escapeHtml(item.id)}"
                  type="text"
                  maxlength="200"
                  value="${escapeHtml(item.model)}"
                  autocomplete="off"
                  spellcheck="false"
                  required
                />
              </label>
            `).join("")}
            </div>
          </fieldset>

          <fieldset class="provider-request-urls">
            <legend>请求地址</legend>
            <div class="provider-url-list">
              ${provider.requestUrls.map((item) => `
                <label class="provider-config-field">
                  <span>${escapeHtml(item.label)}</span>
                  <input
                    name="url-${escapeHtml(item.id)}"
                    data-url-id="${escapeHtml(item.id)}"
                    type="url"
                    maxlength="1000"
                    value="${escapeHtml(item.value)}"
                    placeholder="${escapeHtml(item.placeholder)}"
                    autocomplete="url"
                    spellcheck="false"
                    required
                  />
                </label>
              `).join("")}
            </div>
          </fieldset>

          <label class="credential-label" for="credential-${escapeHtml(provider.id)}">API Key</label>
          <div class="credential-input-row">
            <div class="credential-input-wrap">
              <input
                id="credential-${escapeHtml(provider.id)}"
                name="apiKey"
                type="password"
                maxlength="4096"
                autocomplete="new-password"
                spellcheck="false"
                placeholder="${provider.configured ? provider.maskedValue + "（输入新 Key 可替换）" : "输入 API Key"}"
              />
              <button
                class="credential-visibility-button"
                type="button"
                aria-label="显示 API Key"
                title="显示 API Key"
              >
                <iconify-icon icon="ph:eye-bold" aria-hidden="true"></iconify-icon>
              </button>
            </div>
            <button class="primary-button credential-save-button" type="submit" disabled>
              <iconify-icon icon="ph:floppy-disk-bold" aria-hidden="true"></iconify-icon>
              保存
            </button>
          </div>
          <p class="credential-help">Key 留空时只保存模型名称和请求地址，不覆盖当前 Key。</p>
          <p class="credential-feedback" role="status" aria-live="polite"></p>
          <button
            class="credential-clear-button"
            type="button"
            ${provider.configured ? "" : "disabled"}
          >
            清除当前 Key
          </button>
        </form>
      </article>
    `).join("");

    providerSettings.querySelectorAll(".provider-card").forEach(bindProviderCard);
  }

  function setFeedback(card, message, tone = "") {
    const feedback = card.querySelector(".credential-feedback");
    feedback.textContent = message;
    feedback.dataset.tone = tone;
  }

  function setCardBusy(card, busy) {
    card.setAttribute("aria-busy", String(busy));
    card.querySelectorAll("button, input").forEach((control) => {
      if (busy) {
        control.dataset.wasDisabled = String(control.disabled);
        control.disabled = true;
      } else {
        control.disabled = control.dataset.wasDisabled === "true";
        delete control.dataset.wasDisabled;
      }
    });
  }

  function replaceProvider(updatedProvider) {
    providers = providers.map((provider) =>
      provider.id === updatedProvider.id ? updatedProvider : provider,
    );
    renderProviders();
  }

  function bindProviderCard(card) {
    const providerId = card.dataset.providerId;
    const form = card.querySelector(".credential-form");
    const input = form.elements.apiKey;
    const saveButton = card.querySelector(".credential-save-button");
    const visibilityButton = card.querySelector(".credential-visibility-button");
    const clearButton = card.querySelector(".credential-clear-button");

    form.querySelectorAll("input").forEach((field) => {
      field.addEventListener("input", () => {
        saveButton.disabled = false;
        setFeedback(card, "");
      });
    });

    visibilityButton.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      visibilityButton.setAttribute("aria-label", show ? "隐藏 API Key" : "显示 API Key");
      visibilityButton.title = show ? "隐藏 API Key" : "显示 API Key";
      visibilityButton.querySelector("iconify-icon").setAttribute(
        "icon",
        show ? "ph:eye-slash-bold" : "ph:eye-bold",
      );
      input.focus();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const apiKey = input.value.trim();
      if (!form.reportValidity()) return;
      const models = Object.fromEntries(
        [...form.querySelectorAll("[data-model-id]")].map((field) => [
          field.dataset.modelId,
          field.value.trim(),
        ]),
      );
      const requestUrls = Object.fromEntries(
        [...form.querySelectorAll("[data-url-id]")].map((field) => [
          field.dataset.urlId,
          field.value.trim(),
        ]),
      );
      setCardBusy(card, true);
      setFeedback(card, "正在保存…");
      try {
        const result = await apiRequest(`/api/settings/models/${providerId}`, {
          method: "PUT",
          body: JSON.stringify({
            apiKey: apiKey || null,
            models,
            requestUrls,
          }),
        });
        replaceProvider(result.provider);
        const updatedCard = providerSettings.querySelector(`[data-provider-id="${providerId}"]`);
        setFeedback(updatedCard, "已保存并即时生效。", "success");
      } catch (error) {
        setCardBusy(card, false);
        setFeedback(card, error.message, "error");
      }
    });

    clearButton.addEventListener("click", async () => {
      const provider = providers.find((item) => item.id === providerId);
      const confirmed = await window.appConfirm({
        eyebrow: "清除模型凭证",
        title: `清除${provider.name} API Key？`,
        message: "清除后，该服务商对应的 AI 功能将不可用，直到重新填写 Key。",
        confirmText: "确认清除",
        tone: "danger",
        icon: "ph:key-bold",
      });
      if (!confirmed) return;
      setCardBusy(card, true);
      setFeedback(card, "正在清除…");
      try {
        const result = await apiRequest(`/api/settings/models/${providerId}`, {
          method: "DELETE",
        });
        replaceProvider(result.provider);
        const updatedCard = providerSettings.querySelector(`[data-provider-id="${providerId}"]`);
        setFeedback(updatedCard, "当前 Key 已清除。", "success");
      } catch (error) {
        setCardBusy(card, false);
        setFeedback(card, error.message, "error");
      }
    });
  }

  async function loadSettings() {
    loading.hidden = false;
    pageError.hidden = true;
    providerSettings.hidden = true;
    try {
      const result = await apiRequest("/api/settings/models");
      providers = result.providers || [];
      renderProviders();
      providerSettings.hidden = false;
    } catch (error) {
      pageErrorText.textContent = error.message;
      pageError.hidden = false;
      configuredProviderCount.textContent = "配置读取失败";
    } finally {
      loading.hidden = true;
    }
  }

  retryButton.addEventListener("click", loadSettings);
  loadSettings();
})();
