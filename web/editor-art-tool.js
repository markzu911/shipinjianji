(function exposeArtTool(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.ArtTool = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function artToolFactory(root) {
    "use strict";

    const BUILTIN_FONTS = [
      ["modern", "现代黑体"], ["bold", "醒目粗体"], ["classic", "经典黑体"],
      ["song", "宋体"], ["kai", "楷体"], ["fang", "仿宋"],
    ];
    const TEMPLATE_NAMES = {
      impact: "热血立体", neon: "霓虹发光", metal: "金属渐变",
      sticker: "标签贴纸", clean: "清爽描边", gradient: "元气渐变",
      comic: "漫画标题", ice: "冰晶高光", ink: "国风水墨",
      ribbon: "彩带标题", luxury: "黑金质感",
    };
    const mountedTools = new WeakMap();

    function required(value, name) {
      if (typeof value !== "function") throw new Error(`ArtTool requires ${name}.`);
    }

    function mount(host, services) {
      if (!host?.querySelector || !host?.replaceChildren) {
        throw new Error("ArtTool requires a root element.");
      }
      const model = root.EditorArtModel;
      const renderer = root.EditorArtRenderer;
      if (!model || !renderer) throw new Error("ArtTool requires shared art modules.");
      required(services?.project?.snapshot, "project.snapshot");
      required(services?.project?.subscribe, "project.subscribe");
      required(services?.project?.beginEffect, "project.beginEffect");
      required(services?.project?.isCurrentEffect, "project.isCurrentEffect");
      required(services?.media?.currentEditedTime, "media.currentEditedTime");
      required(services?.media?.seekEdited, "media.seekEdited");
      required(services?.media?.subscribeFrame, "media.subscribeFrame");
      required(services?.commands?.replaceArt, "commands.replaceArt");
      required(services?.commands?.selectArt, "commands.selectArt");
      required(services?.commands?.setArtRange, "commands.setArtRange");
      required(services?.commands?.saveTranscript, "commands.saveTranscript");
      required(services?.commands?.generateCurrentPreview, "commands.generateCurrentPreview");
      required(services?.api?.request, "api.request");
      mountedTools.get(host)?.destroy();

      const ownedRoot = host.ownerDocument.createElement("div");
      ownedRoot.className = "editor-art-tool";
      ownedRoot.innerHTML = `
        <div class="workbench-tabbar editor-art-tool-tabs" role="tablist" aria-label="艺术字编辑功能">
          <button type="button" class="workbench-tab" role="tab" data-art-tab="settings" aria-selected="true">艺术字设置</button>
          <button type="button" class="workbench-tab" role="tab" data-art-tab="ai" aria-selected="false">AI 推荐</button>
          <button type="button" class="workbench-tab" role="tab" data-art-tab="transcript" aria-selected="false">视频文案</button>
        </div>
        <section class="editor-art-tool-panel" data-art-panel="settings" role="tabpanel">
          <div class="art-section-heading"><div><p class="step-label">艺术字设置</p><h2>选择并调整艺术字</h2></div><span class="result-chip" data-art-count>0 / 20</span></div>
          <ol class="overlay-list editor-art-overlay-list" data-art-list></ol>
          <label class="field full-field"><span>自定义文字</span><span class="inline-input-action"><input data-art-add-text maxlength="60" placeholder="例如：今天分享三个重点" /><button type="button" class="secondary-button" data-art-add>添加</button></span></label>
          <p class="form-error" data-art-error role="alert" hidden></p>
          <fieldset class="overlay-controls editor-art-controls" data-art-controls disabled>
            <legend class="sr-only">当前艺术字设置</legend>
            <div class="art-style-picker full-field"><span class="field-label">艺术字模板</span><div class="art-style-grid" data-art-templates role="radiogroup"></div></div>
            <label class="field full-field"><span>文字内容</span><textarea rows="2" maxlength="60" data-art-field="text"></textarea></label>
            <label class="field"><span>字体</span><select data-art-field="font"></select></label>
            <label class="field"><span>字号</span><input type="number" min="20" max="180" step="1" data-art-field="fontSize" /></label>
            <label class="field"><span>文字方向</span><select data-art-field="direction"><option value="horizontal">横向排版</option><option value="vertical">竖向排版</option></select></label>
            <label class="field"><span>对齐方式</span><select data-art-field="textAlign"><option value="left">左对齐</option><option value="center">居中对齐</option><option value="right">右对齐</option></select></label>
            <label class="field"><span>每行字数</span><input type="number" min="0" max="20" data-art-field="charsPerLine" /></label>
            <label class="field"><span>字间距</span><input type="number" min="0" max="20" step="1" data-art-field="letterSpacing" /></label>
            <label class="field"><span>行间距</span><input type="number" min="0" max="40" data-art-field="lineSpacing" /></label>
            <label class="field color-field"><span>文字颜色</span><input type="color" data-art-field="color" /></label>
            <label class="field color-field"><span>描边颜色</span><input type="color" data-art-field="strokeColor" /></label>
            <label class="field"><span>描边</span><input type="number" min="0" max="12" step="1" data-art-field="strokeWidth" /></label>
            <label class="toggle-field"><span><strong>文字阴影</strong></span><input type="checkbox" data-art-field="shadow" /></label>
            <label class="field"><span>开始时间（秒）</span><input type="number" min="0" step="0.01" data-art-range="start" /></label>
            <label class="field"><span>结束时间（秒）</span><input type="number" min="0.02" step="0.01" data-art-range="end" /></label>
            <label class="field"><span>横向 X（%）</span><input type="number" min="5" max="95" step="0.1" data-art-coordinate="x" /></label>
            <label class="field"><span>纵向 Y（%）</span><input type="number" min="5" max="95" step="0.1" data-art-coordinate="y" /></label>
            <div class="position-presets full-field"><div class="position-presets-heading"><span><strong>位置预设</strong><small>保存当前坐标并复用</small></span></div><div class="position-preset-grid" data-art-presets></div><div class="position-preset-save"><input data-art-preset-name maxlength="40" placeholder="输入预设名称" /><button type="button" class="secondary-button compact-button" data-art-preset-save>保存坐标</button></div></div>
            <button type="button" class="secondary-button full-field" data-art-fit>贴合匹配文案时间</button>
            <button type="button" class="secondary-button full-field" data-art-apply-all>应用当前设置到全部自定义艺术字</button>
            <button type="button" class="text-danger-button full-field" data-art-delete>删除当前艺术字</button>
          </fieldset>
        </section>
        <section class="editor-art-tool-panel" data-art-panel="ai" role="tabpanel" hidden>
          <div class="art-section-heading"><div><p class="step-label">AI 推荐</p><h2>推荐重点文案、时间与位置</h2></div><span class="result-chip">确认后添加</span></div>
          <label class="field"><span>本次新增数量</span><input type="number" min="1" max="20" value="3" data-art-ai-count /></label>
          <button type="button" class="primary-button" data-art-ai-request>AI 分析并推荐</button>
          <div class="cut-progress" data-art-ai-progress hidden><div class="cut-progress-heading"><strong data-art-ai-status>正在分析…</strong><span data-art-ai-percent>0%</span></div><div class="progress-track"><span class="progress-bar" data-art-ai-bar></span></div></div>
          <p class="form-error" data-art-ai-error role="alert" hidden></p>
          <ol class="ai-suggestion-list editor-art-ai-list" data-art-ai-list></ol>
          <div class="ai-review-actions" data-art-ai-actions hidden><button type="button" class="secondary-button" data-art-ai-cancel>取消草稿</button><button type="button" class="primary-button" data-art-ai-confirm>确认添加</button></div>
        </section>
        <section class="editor-art-tool-panel" data-art-panel="transcript" role="tabpanel" hidden>
          <div class="art-section-heading"><div><p class="step-label">视频文案</p><h2>修改文案并添加到视频</h2></div><span class="result-chip" data-art-transcript-meta></span></div>
          <label class="field full-field"><span>保留文案</span><textarea rows="7" data-art-transcript-text></textarea></label>
          <button type="button" class="secondary-button" data-art-transcript-save>保存文案</button>
          <button type="button" class="primary-button" data-art-full-track>一键添加全文艺术字</button>
          <p class="retained-bulk-message" data-art-transcript-status role="status" hidden></p>
          <ol class="retained-segments editor-art-transcript-list" data-art-transcript-list></ol>
          <button type="button" class="secondary-button" data-art-add-selected disabled>添加所选文案</button>
        </section>
      `;
      host.replaceChildren(ownedRoot);

      const query = (selector) => ownedRoot.querySelector(selector);
      const queryAll = (selector) => [...ownedRoot.querySelectorAll(selector)];
      const state = {
        active: false,
        destroyed: false,
        activeTab: "settings",
        frame: null,
        aiDraftSuggestions: [],
        previewDraftId: null,
        busyEffect: "",
        fieldErrors: {},
        templates: Object.entries(model.DEFAULT_PALETTES).map(([id, palette]) => ({ id, name: TEMPLATE_NAMES[id], ...palette })),
        templateEffects: {},
        fonts: BUILTIN_FONTS.map(([id, name]) => ({ id, name, source: "builtin" })),
        presets: [],
        selectedSegments: new Set(),
        requests: new Map(),
        pollTimer: null,
        catalogsLoaded: false,
        transcriptSignature: "",
      };

      function snapshot() {
        return services.project.snapshot();
      }

      function duration() {
        const project = snapshot()?.project;
        return Math.max(0, Number(state.frame?.timeline?.duration || project?.cut?.duration || project?.cut?.sourceDuration) || 0);
      }

      function art() {
        return snapshot()?.project?.art || { source: "original", overlays: [], assets: [] };
      }

      function selectedOverlay() {
        const clipId = String(snapshot()?.project?.timeline?.selection?.clipId || "");
        const sourceId = clipId.replace(/^art:/, "");
        return art().overlays.find((overlay) => String(overlay.id) === sourceId) || null;
      }

      function transcript() {
        const project = snapshot()?.project;
        return project?.cut?.transcript || project?.transcript || { text: "", segments: [] };
      }

      function setMessage(selector, message, tone = "warning") {
        const element = query(selector);
        if (!element) return;
        element.textContent = String(message || "");
        element.hidden = !message;
        element.dataset.tone = tone;
      }

      function abortEffect(scope) {
        const current = state.requests.get(scope);
        current?.controller.abort();
        state.requests.delete(scope);
        if (state.busyEffect === scope) state.busyEffect = "";
        if (scope === "ai") {
          root.clearTimeout(state.pollTimer);
          state.pollTimer = null;
        }
        if (scope === "catalogs") state.catalogsLoaded = false;
        if (!state.destroyed) renderBusyControls();
      }

      function beginRequest(scope, projectScope = scope) {
        abortEffect(scope);
        const token = services.project.beginEffect(projectScope);
        const controller = new AbortController();
        const request = { token, controller };
        state.requests.set(scope, request);
        return request;
      }

      function ownsRequest(scope, request) {
        return state.requests.get(scope) === request;
      }

      function discardRequest(scope, request) {
        if (ownsRequest(scope, request)) abortEffect(scope);
        else request.controller.abort();
      }

      function finishRequest(scope, request) {
        if (!ownsRequest(scope, request)) return false;
        state.requests.delete(scope);
        if (state.busyEffect === scope) state.busyEffect = "";
        if (scope === "ai") {
          root.clearTimeout(state.pollTimer);
          state.pollTimer = null;
        }
        if (!state.destroyed) renderBusyControls();
        return true;
      }

      function requestCurrent(scope, request) {
        return Boolean(
          !state.destroyed &&
          state.active &&
          state.requests.get(scope) === request &&
          request.token &&
          request.token.jobId === snapshot()?.jobId &&
          request.token.baseRevision === snapshot()?.revision &&
          services.project.isCurrentEffect(request.token),
        );
      }

      function replaceArt(overlays, options = {}) {
        const current = art();
        return services.commands.replaceArt(
          { ...current, overlays },
          { ...options, selection: options.selection },
        );
      }

      function renderTabs() {
        for (const tab of queryAll("[data-art-tab]")) {
          const selected = tab.dataset.artTab === state.activeTab;
          tab.setAttribute("aria-selected", String(selected));
          tab.tabIndex = selected ? 0 : -1;
        }
        for (const panel of queryAll("[data-art-panel]")) {
          panel.hidden = panel.dataset.artPanel !== state.activeTab;
        }
      }

      function renderTemplates(selected) {
        const container = query("[data-art-templates]");
        container.replaceChildren();
        for (const template of state.templates) {
          const button = host.ownerDocument.createElement("button");
          button.type = "button";
          button.className = "art-style-option";
          button.dataset.artTemplate = template.id;
          button.setAttribute("aria-pressed", String(selected?.artStyle === template.id));
          const sample = host.ownerDocument.createElement("span");
          sample.className = `art-style-sample style-${template.baseStyle || template.id}`;
          renderer.renderCharacters(sample, String(template.sample || template.name || "艺字").slice(0, 2), template);
          const copy = host.ownerDocument.createElement("span");
          const strong = host.ownerDocument.createElement("strong");
          strong.textContent = template.name || TEMPLATE_NAMES[template.id] || template.id;
          const small = host.ownerDocument.createElement("small");
          small.textContent = template.description || "点击应用到当前艺术字";
          copy.append(strong, small);
          button.append(sample, copy);
          container.append(button);
        }
      }

      function renderOverlayList(selected) {
        const list = query("[data-art-list]");
        list.replaceChildren();
        for (const overlay of art().overlays) {
          const item = host.ownerDocument.createElement("li");
          const button = host.ownerDocument.createElement("button");
          button.type = "button";
          button.dataset.artSelect = String(overlay.id);
          button.className = "overlay-list-item";
          button.classList.toggle("is-selected", String(selected?.id) === String(overlay.id));
          const title = host.ownerDocument.createElement("strong");
          title.textContent = overlay.text || "未命名艺术字";
          const time = host.ownerDocument.createElement("small");
          time.textContent = `${Number(overlay.start).toFixed(2)}s - ${Number(overlay.end).toFixed(2)}s`;
          button.append(title, time);
          item.append(button);
          list.append(item);
        }
        query("[data-art-count]").textContent = `${art().overlays.filter((item) => !model.isTranscriptOverlay(item)).length} / ${model.MANUAL_OVERLAY_LIMIT}`;
      }

      function setField(selector, value) {
        const element = query(selector);
        if (!element || element === ownedRoot.ownerDocument.activeElement) return;
        if (element.type === "checkbox") element.checked = Boolean(value);
        else element.value = value ?? "";
      }

      function renderControls(selected) {
        const controls = query("[data-art-controls]");
        controls.disabled = !selected;
        if (!selected) return;
        for (const field of queryAll("[data-art-field]")) setField(`[data-art-field="${field.dataset.artField}"]`, selected[field.dataset.artField]);
        setField('[data-art-range="start"]', Number(selected.start).toFixed(2));
        setField('[data-art-range="end"]', Number(selected.end).toFixed(2));
        setField('[data-art-coordinate="x"]', (Number(selected.x) * 100).toFixed(1));
        setField('[data-art-coordinate="y"]', (Number(selected.y) * 100).toFixed(1));
        query("[data-art-apply-all]").disabled = model.isTranscriptOverlay(selected) || art().overlays.filter((item) => !model.isTranscriptOverlay(item)).length < 2;
        renderTemplates(selected);
      }

      function renderPresets() {
        const grid = query("[data-art-presets]");
        grid.replaceChildren();
        for (const preset of state.presets) {
          const wrapper = host.ownerDocument.createElement("span");
          wrapper.className = "position-preset-chip";
          const apply = host.ownerDocument.createElement("button");
          apply.type = "button";
          apply.dataset.artPreset = preset.id;
          apply.textContent = preset.name;
          const remove = host.ownerDocument.createElement("button");
          remove.type = "button";
          remove.dataset.artPresetDelete = preset.id;
          remove.setAttribute("aria-label", `删除预设“${preset.name}”`);
          remove.textContent = "×";
          wrapper.append(apply, remove);
          grid.append(wrapper);
        }
      }

      function transcriptSegments() {
        return (Array.isArray(transcript()?.segments) ? transcript().segments : []).filter((segment) => String(segment.text || "").trim());
      }

      function segmentKey(segment, index) {
        return String(segment.id ?? `${Number(segment.start).toFixed(3)}:${Number(segment.end).toFixed(3)}:${index}`);
      }

      function renderTranscript() {
        const current = transcript();
        const jobId = snapshot()?.jobId || "";
        const textarea = query("[data-art-transcript-text]");
        const segments = transcriptSegments();
        const signature = JSON.stringify({
          jobId,
          text: String(current.text || ""),
          segments: segments.map((segment) => ({
            id: segment.id,
            text: segment.text,
            start: segment.start,
            end: segment.end,
          })),
        });
        if (
          state.transcriptSignature !== signature &&
          textarea !== ownedRoot.ownerDocument.activeElement
        ) {
          textarea.value = String(current.text || transcriptSegments().map((item) => item.text).join(""));
          state.transcriptSignature = signature;
        }
        const validKeys = new Set(
          segments.map((segment, index) => segmentKey(segment, index)),
        );
        for (const key of [...state.selectedSegments]) {
          if (!validKeys.has(key)) state.selectedSegments.delete(key);
        }
        query("[data-art-transcript-meta]").textContent = `${segments.length} 段`;
        const list = query("[data-art-transcript-list]");
        list.replaceChildren();
        segments.forEach((segment, index) => {
          const key = segmentKey(segment, index);
          const item = host.ownerDocument.createElement("li");
          item.className = "retained-segment";
          const label = host.ownerDocument.createElement("label");
          label.className = "retained-segment-check";
          const checkbox = host.ownerDocument.createElement("input");
          checkbox.type = "checkbox";
          checkbox.dataset.artSegment = key;
          checkbox.checked = state.selectedSegments.has(key);
          const text = host.ownerDocument.createElement("span");
          text.textContent = String(segment.text || "");
          label.append(checkbox, text);
          const play = host.ownerDocument.createElement("button");
          play.type = "button";
          play.dataset.artSegmentPlay = key;
          play.textContent = "试听";
          item.append(label, play);
          list.append(item);
        });
        query("[data-art-add-selected]").disabled =
          state.selectedSegments.size === 0 || Boolean(state.busyEffect);
      }

      function renderAi() {
        const list = query("[data-art-ai-list]");
        list.replaceChildren();
        state.aiDraftSuggestions.forEach((suggestion, index) => {
          const item = host.ownerDocument.createElement("li");
          item.className = "ai-suggestion-card";
          item.classList.toggle(
            "is-previewing",
            suggestion.draftId === state.previewDraftId,
          );
          const checkbox = host.ownerDocument.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = suggestion.accepted !== false;
          checkbox.dataset.artAiAccept = String(index);
          const text = host.ownerDocument.createElement("input");
          text.value = suggestion.text || "";
          text.maxLength = 60;
          text.dataset.artAiText = String(index);
          const time = host.ownerDocument.createElement("span");
          time.className = "result-chip";
          time.textContent = `${Number(suggestion.start).toFixed(1)} - ${Number(suggestion.end).toFixed(1)}s`;
          const preview = host.ownerDocument.createElement("button");
          preview.type = "button";
          preview.className = "secondary-button compact-button";
          preview.dataset.artAiPreview = String(index);
          preview.textContent = suggestion.draftId === state.previewDraftId
            ? "正在预览"
            : "在视频中预览";
          const sample = host.ownerDocument.createElement("span");
          sample.className = "art-style-sample editor-art-ai-sample";
          renderer.renderCharacters(sample, suggestion.text || "AI", suggestion);
          item.append(checkbox, text, time, sample, preview);
          list.append(item);
        });
        query("[data-art-ai-actions]").hidden = state.aiDraftSuggestions.length === 0;
      }

      function renderBusyControls() {
        const busy = Boolean(state.busyEffect);
        for (const selector of [
          "[data-art-full-track]",
          "[data-art-transcript-save]",
          "[data-art-ai-request]",
          "[data-art-ai-count]",
          "[data-art-ai-confirm]",
          "[data-art-ai-cancel]",
        ]) {
          const control = query(selector);
          if (control) control.disabled = busy;
        }
        const addSelected = query("[data-art-add-selected]");
        if (addSelected) {
          addSelected.disabled = busy || state.selectedSegments.size === 0;
        }
      }

      function renderAll() {
        if (state.destroyed) return;
        const selected = selectedOverlay();
        renderTabs();
        renderOverlayList(selected);
        renderControls(selected);
        renderPresets();
        renderTranscript();
        renderAi();
        renderBusyControls();
      }

      function syncAiPreview() {
        const suggestion = state.aiDraftSuggestions.find(
          (item) => item.draftId === state.previewDraftId,
        );
        services.preview?.setArtDraft?.(suggestion || null);
      }

      function commitSelectedPatch(patch) {
        const selected = selectedOverlay();
        if (!selected) return;
        const overlays = model.updateOverlay(art().overlays, selected.id, patch, {
          duration: duration(),
          palettes: Object.fromEntries(state.templates.map((item) => [item.id, item])),
          templateEffects: state.templateEffects,
        });
        replaceArt(overlays, { selection: `art:${selected.id}` });
      }

      function addManual(text, range = null, extra = {}) {
        const current = art().overlays;
        if (current.filter((item) => !model.isTranscriptOverlay(item)).length >= model.MANUAL_OVERLAY_LIMIT) {
          setMessage("[data-art-error]", `一个视频最多添加 ${model.MANUAL_OVERLAY_LIMIT} 条自定义艺术字。`);
          return null;
        }
        const value = String(text || "").trim();
        if (!value) {
          setMessage("[data-art-error]", "请输入要添加的艺术字文案。");
          return null;
        }
        const start = range?.start ?? services.media.currentEditedTime();
        const end = range?.end ?? Math.min(duration(), start + 3);
        const sourceStart = Number.isFinite(Number(extra.sourceStart)) ? Number(extra.sourceStart) : services.media.editedToSource?.(start, "start");
        const sourceEnd = Number.isFinite(Number(extra.sourceEnd)) ? Number(extra.sourceEnd) : services.media.editedToSource?.(end, "end");
        const overlay = model.createOverlay(current, {
          text: value, start, end, sourceStart, sourceEnd, ...extra,
        }, { duration: duration() });
        replaceArt([...current, overlay], { selection: `art:${overlay.id}` });
        services.media.seekEdited(overlay.start);
        setMessage("[data-art-error]", "");
        return overlay;
      }

      async function loadCatalogs() {
        if (state.catalogsLoaded || state.destroyed) return;
        const request = beginRequest("catalogs", "art-catalogs");
        state.catalogsLoaded = true;
        const options = { signal: request.controller.signal };
        const [fontResult, templateResult, presetResult] = await Promise.allSettled([
          services.api.request("/api/fonts", options),
          services.api.request("/api/art-templates", options),
          services.api.request("/api/art-position-presets", options),
        ]);
        if (state.destroyed || state.requests.get("catalogs") !== request) return;
        if (fontResult.status === "fulfilled") {
          state.fonts = [...state.fonts, ...(fontResult.value.fonts || []).filter((font) => font.source === "uploaded")];
          const select = query('[data-art-field="font"]');
          select.replaceChildren(...state.fonts.map((font) => {
            const option = host.ownerDocument.createElement("option");
            option.value = font.id;
            option.textContent = font.name;
            return option;
          }));
        }
        if (templateResult.status === "fulfilled" && templateResult.value.templates?.length) {
          state.templates = templateResult.value.templates;
          state.templateEffects = Object.fromEntries(state.templates.map((template) => [template.id, model.normalizeTemplateEffects(template)]));
        }
        if (presetResult.status === "fulfilled") state.presets = presetResult.value.presets || [];
        state.requests.delete("catalogs");
        renderAll();
      }

      async function savePreset() {
        const selected = selectedOverlay();
        const name = query("[data-art-preset-name]").value.trim();
        if (!selected || !name) return;
        const request = beginRequest("preset-save", "art-position-preset-save");
        try {
          const payload = await services.api.request("/api/art-position-presets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, x: selected.x, y: selected.y }),
            signal: request.controller.signal,
          });
          if (!requestCurrent("preset-save", request)) return;
          state.presets = [
            ...state.presets.filter((item) => item.id !== payload.id),
            payload,
          ];
          query("[data-art-preset-name]").value = "";
          renderPresets();
        } catch (error) {
          if (error.name !== "AbortError" && ownsRequest("preset-save", request)) {
            setMessage("[data-art-error]", error.message);
          }
        } finally {
          finishRequest("preset-save", request);
        }
      }

      async function deletePreset(id) {
        const preset = state.presets.find((item) => String(item.id) === String(id));
        const confirmed = await services.feedback.confirm({
          eyebrow: "删除位置预设", title: "确定删除该位置预设？",
          message: preset ? `将删除“${preset.name}”。` : "", confirmText: "删除", tone: "danger",
        });
        if (!confirmed) return;
        if (state.destroyed || !state.active) return;
        const request = beginRequest(
          "preset-delete",
          "art-position-preset-delete",
        );
        try {
          await services.api.request(
            `/api/art-position-presets/${encodeURIComponent(id)}`,
            { method: "DELETE", signal: request.controller.signal },
          );
          if (!requestCurrent("preset-delete", request)) return;
          state.presets = state.presets.filter(
            (item) => String(item.id) !== String(id),
          );
          renderPresets();
        } catch (error) {
          if (
            error.name !== "AbortError" &&
            ownsRequest("preset-delete", request)
          ) {
            setMessage("[data-art-error]", error.message);
          }
        } finally {
          finishRequest("preset-delete", request);
        }
      }

      async function createFullTrack() {
        const currentTranscript = transcript();
        if (!transcriptSegments().length || state.busyEffect) return;
        const selected = selectedOverlay();
        const styleSeed = selected || {};
        const palette = model.DEFAULT_PALETTES.impact;
        const style = {
          font: styleSeed.font || "bold", fontSize: styleSeed.fontSize || 54,
          color: palette.color, strokeColor: palette.strokeColor,
          strokeWidth: styleSeed.strokeWidth ?? 3, shadow: true, x: 0.5, y: 0.82,
          direction: "horizontal", textAlign: "center", charsPerLine: 0,
          letterSpacing: 0, lineSpacing: 0, artStyle: "impact",
          ...state.templateEffects.impact,
        };
        const request = beginRequest("track", "art-transcript-track");
        state.busyEffect = "track";
        renderBusyControls();
        setMessage("[data-art-transcript-status]", "正在生成全文艺术字…", "neutral");
        try {
          const result = await services.api.request(`/api/transcriptions/${encodeURIComponent(snapshot().jobId)}/art-text/transcript-track`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              source: art().source, font: style.font, fontSize: style.fontSize,
              letterSpacing: style.letterSpacing, strokeWidth: style.strokeWidth,
              draftTranscript: currentTranscript, draftDuration: duration(),
            }), signal: request.controller.signal,
          });
          if (!requestCurrent("track", request)) return;
          const track = model.buildTranscriptTrack(result, style, art().overlays, { duration: duration() });
          const retained = art().overlays.filter((overlay) => !model.isTranscriptOverlay(overlay));
          const replaced = replaceArt([...retained, ...track], {
            selection: track[0] ? `art:${track[0].id}` : null,
            token: request.token,
          });
          if (replaced?.accepted) setMessage("[data-art-transcript-status]", `已生成 ${track.length} 个全文艺术字片段。`, "success");
        } catch (error) {
          if (error.name !== "AbortError" && ownsRequest("track", request)) {
            setMessage("[data-art-transcript-status]", error.message);
          }
        } finally {
          if (finishRequest("track", request)) renderAll();
        }
      }

      async function saveTranscript() {
        const text = query("[data-art-transcript-text]").value.trim();
        if (!text || state.busyEffect) return;
        const request = beginRequest("transcript", "art-transcript-save");
        state.busyEffect = "transcript";
        renderBusyControls();
        setMessage("[data-art-transcript-status]", "正在保存文案并保持现有 cue 时间…", "neutral");
        try {
          const result = await services.commands.saveTranscript(text, {
            token: request.token,
            signal: request.controller.signal,
          });
          if (result?.accepted && ownsRequest("transcript", request)) {
            state.transcriptSignature = "";
            setMessage("[data-art-transcript-status]", "文案已保存，现有全文艺术字时间保持不变。", "success");
          }
        } catch (error) {
          if (error.name !== "AbortError" && ownsRequest("transcript", request)) {
            setMessage("[data-art-transcript-status]", error.message);
          }
        } finally {
          if (finishRequest("transcript", request)) renderAll();
        }
      }

      function showAiJob(job) {
        const progress = Math.max(0, Math.min(100, Number(job?.progress) || 0));
        query("[data-art-ai-progress]").hidden = !["queued", "processing"].includes(job?.status);
        query("[data-art-ai-status]").textContent = job?.stage || "正在分析视频内容…";
        query("[data-art-ai-percent]").textContent = `${progress}%`;
        query("[data-art-ai-bar]").style.width = `${progress}%`;
        if (job?.status === "completed") {
          state.aiDraftSuggestions = (job.suggestions || []).map((item, index) => ({
            ...item, draftId: `ai-draft-${index + 1}`, accepted: true,
          }));
          state.previewDraftId = state.aiDraftSuggestions[0]?.draftId || null;
          renderAi();
          syncAiPreview();
        } else if (job?.status === "failed") {
          setMessage("[data-art-ai-error]", job.error || "AI 艺术字分析失败。");
        }
      }

      async function pollAi(request) {
        try {
          const job = await services.api.request(`/api/transcriptions/${encodeURIComponent(snapshot().jobId)}`, { signal: request.controller.signal });
          if (!requestCurrent("ai", request)) {
            discardRequest("ai", request);
            return;
          }
          const suggestion = job.artSuggestion;
          if (!suggestion || (suggestion.source || "edited") !== art().source) throw new Error("AI 艺术字草稿已失效，请重新分析。");
          showAiJob(suggestion);
          if (["queued", "processing"].includes(suggestion.status)) {
            state.pollTimer = root.setTimeout(() => pollAi(request), 1200);
          } else {
            finishRequest("ai", request);
          }
        } catch (error) {
          if (error.name !== "AbortError" && ownsRequest("ai", request)) {
            setMessage("[data-art-ai-error]", error.message);
          }
          finishRequest("ai", request);
        }
      }

      async function requestAi() {
        if (state.busyEffect) return;
        const count = Number(query("[data-art-ai-count]").value);
        const manual = art().overlays.filter((item) => !model.isTranscriptOverlay(item));
        if (!Number.isInteger(count) || count < 1 || count + manual.length > model.MANUAL_OVERLAY_LIMIT) {
          setMessage("[data-art-ai-error]", "推荐数量超出当前艺术字容量。");
          return;
        }
        const request = beginRequest("ai", "art-ai-suggestions");
        state.busyEffect = "ai";
        renderBusyControls();
        setMessage("[data-art-ai-error]", "");
        try {
          const job = await services.api.request(`/api/transcriptions/${encodeURIComponent(snapshot().jobId)}/art-text/suggestions`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: art().source, count, existingOverlays: manual.map(({ id, ...overlay }) => overlay) }),
            signal: request.controller.signal,
          });
          if (!requestCurrent("ai", request)) {
            discardRequest("ai", request);
            return;
          }
          showAiJob(job);
          await pollAi(request);
        } catch (error) {
          if (error.name !== "AbortError" && ownsRequest("ai", request)) {
            setMessage("[data-art-ai-error]", error.message);
          }
          finishRequest("ai", request);
        }
      }

      async function clearAi() {
        abortEffect("ai");
        state.aiDraftSuggestions = [];
        state.previewDraftId = null;
        syncAiPreview();
        const request = beginRequest("ai-clear", "art-ai-suggestions-clear");
        state.busyEffect = "ai-clear";
        renderAi();
        renderBusyControls();
        try {
          await services.api.request(`/api/transcriptions/${encodeURIComponent(snapshot().jobId)}/art-text/suggestions`, {
            method: "DELETE",
            signal: request.controller.signal,
          });
        } catch {
          // Local drafts are already gone; stale server drafts cannot enter Store.
        } finally {
          finishRequest("ai-clear", request);
        }
      }

      function confirmAi() {
        const accepted = state.aiDraftSuggestions.filter((item) => item.accepted !== false);
        if (!accepted.length) return;
        let overlays = [...art().overlays];
        for (const suggestion of accepted) overlays.push(model.overlayFromSuggestion(suggestion, overlays, { duration: duration() }));
        const first = overlays[art().overlays.length];
        replaceArt(overlays, { selection: first ? `art:${first.id}` : null });
        void clearAi();
        state.activeTab = "settings";
        renderAll();
      }

      async function deleteSelected() {
        const selected = selectedOverlay();
        if (!selected) return;
        const track = model.isTranscriptOverlay(selected);
        const confirmed = await services.feedback.confirm({
          eyebrow: track ? "全文艺术字轨道" : "删除艺术字",
          title: track ? "删除整条全文轨道？" : "删除当前艺术字？",
          message: track ? "轨道内所有词级同步片段都会删除。" : `将删除“${selected.text}”。`,
          confirmText: "删除", tone: "danger",
        });
        if (!confirmed) return;
        if (
          state.destroyed ||
          !state.active ||
          String(selectedOverlay()?.id || "") !== String(selected.id)
        ) {
          return;
        }
        const overlays = model.removeOverlay(art().overlays, selected.id);
        replaceArt(overlays, { selection: overlays[0] ? `art:${overlays[0].id}` : null });
      }

      function addSelectedSegments() {
        const segments = transcriptSegments();
        let overlays = [...art().overlays];
        let first = null;
        segments.forEach((segment, index) => {
          if (!state.selectedSegments.has(segmentKey(segment, index))) return;
          if (overlays.filter((item) => !model.isTranscriptOverlay(item)).length >= model.MANUAL_OVERLAY_LIMIT) return;
          const overlay = model.createOverlay(overlays, segment, { duration: duration() });
          overlays.push(overlay);
          first ||= overlay;
        });
        state.selectedSegments.clear();
        replaceArt(overlays, { selection: first ? `art:${first.id}` : null });
      }

      function findSegment(key) {
        return transcriptSegments().find((segment, index) => segmentKey(segment, index) === key);
      }

      function handleClick(event) {
        const target = event.target.closest("button");
        if (!target || !ownedRoot.contains(target)) return;
        if (target.dataset.artTab) {
          state.activeTab = target.dataset.artTab;
          renderTabs();
        } else if (target.hasAttribute("data-art-add")) {
          const input = query("[data-art-add-text]");
          if (addManual(input.value)) input.value = "";
        } else if (target.dataset.artSelect) {
          services.commands.selectArt(target.dataset.artSelect);
          services.media.seekEdited(art().overlays.find((item) => String(item.id) === target.dataset.artSelect)?.start || 0);
        } else if (target.dataset.artTemplate) {
          const template = state.templates.find((item) => item.id === target.dataset.artTemplate);
          commitSelectedPatch({
            artStyle: template.id, color: template.color, strokeColor: template.strokeColor,
            ...model.normalizeTemplateEffects(template),
          });
        } else if (target.hasAttribute("data-art-delete")) deleteSelected();
        else if (target.hasAttribute("data-art-apply-all")) {
          const selected = selectedOverlay();
          if (selected) replaceArt(model.applyStyleToManualOverlays(art().overlays, selected.id, { duration: duration() }), { selection: `art:${selected.id}` });
        } else if (target.hasAttribute("data-art-fit")) {
          const selected = selectedOverlay();
          const segments = transcriptSegments();
          const normalized = String(selected?.text || "").replace(/[\s\p{P}]/gu, "");
          const match = segments.find((segment) => String(segment.text || "").replace(/[\s\p{P}]/gu, "").includes(normalized)) || segments.find((segment) => Number(segment.start) <= selected?.start && Number(segment.end) >= selected?.start);
          if (selected && match) services.commands.setArtRange(selected.id, Number(match.start), Number(match.end), { sourceStart: match.sourceStart, sourceEnd: match.sourceEnd });
        } else if (target.hasAttribute("data-art-preset-save")) savePreset();
        else if (target.dataset.artPreset) {
          const preset = state.presets.find((item) => String(item.id) === target.dataset.artPreset);
          if (preset) commitSelectedPatch({ x: Number(preset.x), y: Number(preset.y) });
        } else if (target.dataset.artPresetDelete) deletePreset(target.dataset.artPresetDelete);
        else if (target.hasAttribute("data-art-full-track")) createFullTrack();
        else if (target.hasAttribute("data-art-transcript-save")) saveTranscript();
        else if (target.hasAttribute("data-art-add-selected")) addSelectedSegments();
        else if (target.dataset.artSegmentPlay) services.media.seekEdited(Number(findSegment(target.dataset.artSegmentPlay)?.start) || 0);
        else if (target.hasAttribute("data-art-ai-request")) requestAi();
        else if (target.hasAttribute("data-art-ai-cancel")) clearAi();
        else if (target.hasAttribute("data-art-ai-confirm")) confirmAi();
        else if (target.dataset.artAiPreview !== undefined) {
          const item = state.aiDraftSuggestions[Number(target.dataset.artAiPreview)];
          state.previewDraftId = item?.draftId || null;
          if (item) services.media.seekEdited(item.start);
          syncAiPreview();
          renderAi();
        }
      }

      function handleChange(event) {
        const target = event.target;
        if (target.dataset.artField) {
          const field = target.dataset.artField;
          const value = target.type === "checkbox" ? target.checked : ["fontSize", "charsPerLine", "letterSpacing", "lineSpacing", "strokeWidth"].includes(field) ? Number(target.value) : target.value;
          commitSelectedPatch({ [field]: value });
        } else if (target.dataset.artRange) {
          const selected = selectedOverlay();
          if (!selected) return;
          const field = target.dataset.artRange;
          const start = field === "start" ? Number(target.value) : selected.start;
          const end = field === "end" ? Number(target.value) : selected.end;
          services.commands.setArtRange(selected.id, start, end);
          const updated = selectedOverlay();
          target.value = Number(updated?.[field] ?? selected[field]).toFixed(2);
        } else if (target.dataset.artCoordinate) {
          const percent = Math.min(95, Math.max(5, Number(target.value) || 5));
          target.value = percent.toFixed(1);
          commitSelectedPatch({ [target.dataset.artCoordinate]: percent / 100 });
        } else if (target.dataset.artSegment) {
          target.checked ? state.selectedSegments.add(target.dataset.artSegment) : state.selectedSegments.delete(target.dataset.artSegment);
          query("[data-art-add-selected]").disabled =
            state.selectedSegments.size === 0 || Boolean(state.busyEffect);
        } else if (target.dataset.artAiAccept !== undefined) {
          const item = state.aiDraftSuggestions[Number(target.dataset.artAiAccept)];
          if (item) item.accepted = target.checked;
        } else if (target.dataset.artAiText !== undefined) {
          const item = state.aiDraftSuggestions[Number(target.dataset.artAiText)];
          if (item) {
            item.text = target.value;
            if (item.draftId === state.previewDraftId) syncAiPreview();
          }
        }
      }

      function handleKeydown(event) {
        const tabs = queryAll("[data-art-tab]");
        const current = tabs.indexOf(event.target);
        if (current >= 0 && ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          const index = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
          state.activeTab = tabs[index].dataset.artTab;
          renderTabs();
          tabs[index].focus();
        } else if (event.key === "Enter" && event.target.matches("[data-art-add-text]")) {
          event.preventDefault();
          query("[data-art-add]").click();
        }
      }

      function handleInput(event) {
        const target = event.target;
        if (!target.dataset.artCoordinate) return;
        const percent = Number(target.value);
        if (
          target.value.trim() === "" ||
          !Number.isFinite(percent) ||
          !target.validity.valid
        ) {
          return;
        }
        commitSelectedPatch({ [target.dataset.artCoordinate]: percent / 100 });
      }

      ownedRoot.addEventListener("click", handleClick);
      ownedRoot.addEventListener("change", handleChange);
      ownedRoot.addEventListener("input", handleInput);
      ownedRoot.addEventListener("keydown", handleKeydown);
      const unsubscribeProject = services.project.subscribe((next, previous) => {
        if (next.jobId !== previous.jobId) {
          for (const scope of [...state.requests.keys()]) abortEffect(scope);
          state.aiDraftSuggestions = [];
          state.selectedSegments.clear();
          state.transcriptSignature = "";
          state.previewDraftId = null;
          syncAiPreview();
        }
        if (state.active) renderAll();
      });
      const unsubscribeFrame = services.media.subscribeFrame(() => {});

      function activate() {
        if (state.destroyed || state.active) return;
        state.active = true;
        host.hidden = false;
        host.removeAttribute("inert");
        renderAll();
        syncAiPreview();
        loadCatalogs().catch(() => {});
      }

      function deactivate() {
        if (state.destroyed || !state.active) return;
        state.active = false;
        services.preview?.setArtDraft?.(null);
        for (const scope of [...state.requests.keys()]) abortEffect(scope);
        state.busyEffect = "";
        const focused = host.ownerDocument.activeElement;
        if (focused && host.contains(focused)) focused.blur();
        host.setAttribute("inert", "");
      }

      function render(frame) {
        if (state.destroyed) return;
        state.frame = frame || null;
        if (state.active) renderAll();
      }

      function destroy() {
        if (state.destroyed) return;
        state.destroyed = true;
        state.active = false;
        services.preview?.setArtDraft?.(null);
        for (const scope of [...state.requests.keys()]) abortEffect(scope);
        root.clearTimeout(state.pollTimer);
        unsubscribeProject();
        unsubscribeFrame();
        ownedRoot.removeEventListener("click", handleClick);
        ownedRoot.removeEventListener("change", handleChange);
        ownedRoot.removeEventListener("input", handleInput);
        ownedRoot.removeEventListener("keydown", handleKeydown);
        if (ownedRoot.parentNode === host) ownedRoot.remove();
        if (mountedTools.get(host) === api) mountedTools.delete(host);
      }

      const fontSelect = query('[data-art-field="font"]');
      fontSelect.replaceChildren(...state.fonts.map((font) => {
        const option = host.ownerDocument.createElement("option");
        option.value = font.id;
        option.textContent = font.name;
        return option;
      }));
      renderAll();
      const api = Object.freeze({ activate, deactivate, destroy, render });
      mountedTools.set(host, api);
      return api;
    }

    return Object.freeze({ mount });
  },
);
