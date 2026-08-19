(function exposePipTool(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.PipTool = api;
})(
  typeof globalThis === "object" ? globalThis : window,
  function pipToolFactory(root) {
    "use strict";

    const POSITION_PRESETS = Object.freeze({
      "left-top": { label: "左上", x: 0.2, y: 0.2 },
      "right-top": { label: "右上", x: 0.8, y: 0.2 },
      center: { label: "居中", x: 0.5, y: 0.5 },
      "left-bottom": { label: "左下", x: 0.2, y: 0.8 },
      "right-bottom": { label: "右下", x: 0.8, y: 0.8 },
    });
    const mountedTools = new WeakMap();

    function required(value, name) {
      if (typeof value !== "function") throw new Error(`PipTool requires ${name}.`);
    }

    function mount(host, services) {
      if (!host?.querySelector || !host?.replaceChildren) {
        throw new Error("PipTool requires a root element.");
      }
      const model = root.EditorPipModel;
      if (!model) throw new Error("PipTool requires EditorPipModel.");
      required(services?.project?.snapshot, "project.snapshot");
      required(services?.project?.subscribe, "project.subscribe");
      required(services?.project?.beginEffect, "project.beginEffect");
      required(services?.project?.isCurrentEffect, "project.isCurrentEffect");
      required(services?.media?.currentEditedTime, "media.currentEditedTime");
      required(services?.media?.seekEdited, "media.seekEdited");
      required(services?.media?.editedToSource, "media.editedToSource");
      required(services?.media?.subscribeFrame, "media.subscribeFrame");
      required(services?.commands?.replacePip, "commands.replacePip");
      required(services?.commands?.selectPip, "commands.selectPip");
      required(services?.commands?.setPipRange, "commands.setPipRange");
      required(services?.commands?.generateCurrentPreview, "commands.generateCurrentPreview");
      required(services?.api?.request, "api.request");
      mountedTools.get(host)?.destroy();

      const ownedRoot = host.ownerDocument.createElement("div");
      ownedRoot.className = "editor-pip-tool";
      ownedRoot.innerHTML = `
        <section class="editor-pip-tool-panel" aria-labelledby="editorPipTitle">
          <div class="art-section-heading">
            <div><p class="step-label">画中画设置</p><h2 id="editorPipTitle">选择文案并生成画面</h2></div>
            <span class="result-chip" data-pip-count>0 / 20</span>
          </div>
          <div class="pip-control-section">
            <div class="pip-section-title-row"><h3>文案片段</h3><span class="pip-time-chip" data-pip-segment-time>尚未选择</span></div>
            <div id="editorPipSegmentList" class="pip-segment-list editor-pip-segment-list" data-pip-segments role="radiogroup" aria-label="选择文字片段"></div>
          </div>
          <div class="pip-control-section editor-pip-generation-controls">
            <fieldset class="pip-asset-type-field">
              <legend>素材类型</legend>
              <div class="pip-generation-modes">
                <label class="pip-mode-option is-selected"><input type="radio" name="editorPipAssetType" value="image" data-pip-asset-type checked /><span><strong>图片</strong><small>Seedream 静态画面</small></span></label>
                <label class="pip-mode-option"><input type="radio" name="editorPipAssetType" value="video" data-pip-asset-type /><span><strong>视频</strong><small>Seedance 动态镜头</small></span></label>
              </div>
            </fieldset>
            <fieldset class="pip-asset-type-field">
              <legend>生成方式</legend>
              <div class="pip-generation-modes">
                <label class="pip-mode-option is-selected"><input type="radio" name="editorPipMode" value="custom" data-pip-mode checked /><span><strong>自定义</strong><small>输入具体画面</small></span></label>
                <label class="pip-mode-option"><input type="radio" name="editorPipMode" value="auto" data-pip-mode /><span><strong>AI 智能生成</strong><small>根据文案构思</small></span></label>
              </div>
            </fieldset>
            <label class="field"><span>画幅</span><select data-pip-aspect aria-label="画中画素材画幅"><option>1:1</option><option>3:4</option><option>4:3</option><option selected>16:9</option><option>9:16</option></select></label>
            <div class="pip-time-settings full-field">
              <div class="pip-time-settings-heading"><strong>显示时间</strong><button id="fitPipToTranscript" type="button" class="secondary-button compact-button" data-pip-fit>贴合文案</button></div>
              <div class="pip-time-inputs">
                <label><span>开始（秒）</span><input id="pipStartTime" type="number" min="0" step="0.01" data-pip-range="start" /></label>
                <label><span>结束（秒）</span><input id="pipEndTime" type="number" min="0.05" step="0.01" data-pip-range="end" /></label>
              </div>
            </div>
            <div class="pip-prompt-field full-field" data-pip-prompt-field>
              <div class="pip-prompt-heading"><label for="pipPrompt">画面提示词</label><button id="writePipPrompt" type="button" class="secondary-button compact-button" data-pip-write-prompt><iconify-icon icon="ph:sparkle-fill" aria-hidden="true"></iconify-icon><span>AI 编写</span></button></div>
              <textarea id="pipPrompt" rows="3" maxlength="800" data-pip-prompt placeholder="描述要插入的具体画面"></textarea>
              <small data-pip-prompt-status role="status" hidden></small>
            </div>
            <button id="generatePipImage" type="button" class="primary-button full-field" data-pip-generate>生成画中画素材</button>
            <p class="form-error full-field" data-pip-error role="alert" hidden></p>
          </div>
          <div class="pip-control-section pip-generated-section">
            <div class="pip-section-title-row"><h3>素材</h3><span data-pip-assets-status>0 个</span></div>
            <div class="pip-empty-state" data-pip-empty>生成素材后可在这里启用和调整。</div>
            <div id="editorPipGeneratedList" class="pip-generated-list editor-pip-generated-list" data-pip-list></div>
          </div>
        </section>
      `;
      host.replaceChildren(ownedRoot);

      const query = (selector) => ownedRoot.querySelector(selector);
      const queryAll = (selector) => [...ownedRoot.querySelectorAll(selector)];
      const state = {
        active: false,
        destroyed: false,
        lifecycle: 0,
        frame: null,
        jobId: "",
        source: "original",
        selectedSegmentId: "",
        selectedAssetId: "",
        requestedRange: null,
        assetType: "image",
        generationMode: "custom",
        aspectRatio: "16:9",
        requests: new Map(),
        pollTimer: null,
        pollFailures: 0,
      };

      function snapshot() {
        return services.project.snapshot();
      }

      function projectPip() {
        return snapshot()?.project?.pip || { source: "original", assets: [], overlays: [] };
      }

      function duration() {
        const project = snapshot()?.project;
        return Math.max(0, Number(state.frame?.timeline?.duration || project?.cut?.duration || project?.cut?.sourceDuration) || 0);
      }

      function segments() {
        const project = snapshot()?.project;
        const transcript = project?.cut?.transcript || project?.transcript || {};
        return (Array.isArray(transcript.segments) ? transcript.segments : [])
          .map((segment, index) => ({
            id: String(segment.id ?? index),
            text: String(segment.text || "").trim(),
            start: Math.max(0, Number(segment.start) || 0),
            end: Math.min(duration(), Math.max(0, Number(segment.end) || 0)),
            sourceStart: Number.isFinite(Number(segment.sourceStart))
              ? Number(segment.sourceStart)
              : services.media.editedToSource(Number(segment.start) || 0, "start"),
            sourceEnd: Number.isFinite(Number(segment.sourceEnd))
              ? Number(segment.sourceEnd)
              : services.media.editedToSource(Number(segment.end) || 0, "end"),
          }))
          .filter((segment) => segment.text && segment.end > segment.start);
      }

      function selectedSegment() {
        return segments().find((segment) => segment.id === state.selectedSegmentId) || null;
      }

      function selectedOverlay() {
        const clipId = String(snapshot()?.project?.timeline?.selection?.clipId || "");
        const id = clipId.startsWith("pip:") ? clipId.slice(4) : state.selectedAssetId;
        return projectPip().overlays.find((overlay) => String(overlay.assetId || overlay.id) === id) || null;
      }

      function setMessage(selector, message, tone = "warning") {
        const element = query(selector);
        if (!element) return;
        element.textContent = String(message || "");
        element.dataset.tone = tone;
        element.hidden = !message;
      }

      function abortRequest(scope) {
        const request = state.requests.get(scope);
        request?.controller.abort();
        state.requests.delete(scope);
      }

      function stopEffects() {
        state.lifecycle += 1;
        for (const scope of [...state.requests.keys()]) abortRequest(scope);
        root.clearTimeout(state.pollTimer);
        state.pollTimer = null;
      }

      function beginRequest(scope) {
        abortRequest(scope);
        const request = {
          token: services.project.beginEffect(`pip-${scope}`),
          controller: new AbortController(),
          lifecycle: state.lifecycle,
          jobId: snapshot()?.jobId || "",
          source: projectPip().source,
        };
        state.requests.set(scope, request);
        return request;
      }

      function requestCurrent(scope, request) {
        return Boolean(
          state.active &&
          !state.destroyed &&
          state.lifecycle === request.lifecycle &&
          state.requests.get(scope) === request &&
          request.jobId === snapshot()?.jobId &&
          request.source === projectPip().source &&
          services.project.isCurrentEffect(request.token),
        );
      }

      function finishRequest(scope, request) {
        if (state.requests.get(scope) !== request) return false;
        state.requests.delete(scope);
        renderBusy();
        return true;
      }

      function formatTime(seconds) {
        const total = Math.max(0, Number(seconds) || 0);
        const minutes = Math.floor(total / 60);
        return `${String(minutes).padStart(2, "0")}:${(total % 60).toFixed(1).padStart(4, "0")}`;
      }

      function currentRange(showError = true) {
        const start = Number(query('[data-pip-range="start"]')?.value);
        const end = Number(query('[data-pip-range="end"]')?.value);
        const range = model.normalizeRange(start, end, duration(), 0.05);
        if (!range && showError) setMessage("[data-pip-error]", "请设置有效的画中画开始和结束时间。", "error");
        return range;
      }

      function syncRangeInputs() {
        const overlay = selectedOverlay();
        const segment = selectedSegment();
        const range = state.requestedRange || overlay || segment;
        if (!range) return;
        for (const input of queryAll("[data-pip-range]")) {
          if (host.ownerDocument.activeElement === input) continue;
          input.value = Number(range[input.dataset.pipRange] || 0).toFixed(2);
        }
      }

      function selectSegment(id, options = {}) {
        const segment = segments().find((item) => item.id === String(id));
        if (!segment) return false;
        state.selectedSegmentId = segment.id;
        state.requestedRange = { start: segment.start, end: segment.end };
        if (!options.keepTime) services.media.seekEdited(segment.start);
        renderSegments();
        syncRangeInputs();
        return true;
      }

      function renderSegments() {
        const list = query("[data-pip-segments]");
        list.replaceChildren();
        const records = segments();
        if (!records.length) {
          list.scrollTop = 0;
          const empty = host.ownerDocument.createElement("p");
          empty.className = "pip-empty-state";
          empty.textContent = "当前视频没有可选择的文字片段。";
          list.append(empty);
          query("[data-pip-segment-time]").textContent = "尚未选择";
          return;
        }
        let selectionReset = false;
        if (!records.some((segment) => segment.id === state.selectedSegmentId)) {
          state.selectedSegmentId = records[0].id;
          state.requestedRange = { start: records[0].start, end: records[0].end };
          selectionReset = true;
        }
        let selectedLabel = null;
        for (const segment of records) {
          const label = host.ownerDocument.createElement("label");
          label.className = "pip-segment-option";
          label.classList.toggle("is-selected", segment.id === state.selectedSegmentId);
          const radio = host.ownerDocument.createElement("input");
          radio.type = "radio";
          radio.name = "editorPipTranscriptSegment";
          radio.value = segment.id;
          radio.checked = segment.id === state.selectedSegmentId;
          radio.addEventListener("change", () => selectSegment(segment.id));
          const copy = host.ownerDocument.createElement("span");
          const time = host.ownerDocument.createElement("time");
          time.textContent = formatTime(segment.start);
          const text = host.ownerDocument.createElement("strong");
          text.textContent = segment.text;
          copy.append(time, text);
          label.append(radio, copy);
          list.append(label);
          if (segment.id === state.selectedSegmentId) selectedLabel = label;
        }
        const segment = selectedSegment();
        query("[data-pip-segment-time]").textContent = segment
          ? `${formatTime(segment.start)} - ${formatTime(segment.end)}`
          : "尚未选择";
        if (selectionReset) {
          list.scrollTop = 0;
        } else if (selectedLabel && list.clientHeight > 0) {
          const listRect = list.getBoundingClientRect();
          const itemRect = selectedLabel.getBoundingClientRect();
          if (itemRect.top < listRect.top) {
            list.scrollTop -= listRect.top - itemRect.top;
          } else if (itemRect.bottom > listRect.bottom) {
            list.scrollTop += itemRect.bottom - listRect.bottom;
          }
        }
      }

      function placementKey(overlay) {
        for (const [key, preset] of Object.entries(POSITION_PRESETS)) {
          if (Math.hypot(overlay.x - preset.x, overlay.y - preset.y) <= 0.04) return key;
        }
        return "custom";
      }

      function commitOverlayPatch(id, patch) {
        const pip = projectPip();
        const overlays = pip.overlays.map((overlay) =>
          String(overlay.assetId || overlay.id) === String(id)
            ? { ...overlay, ...patch }
            : overlay,
        );
        return services.commands.replacePip(
          { ...pip, overlays },
          { selection: `pip:${id}` },
        );
      }

      function renderAssets() {
        const pip = projectPip();
        const list = query("[data-pip-list]");
        list.replaceChildren();
        query("[data-pip-empty]").hidden = pip.assets.length > 0;
        query("[data-pip-count]").textContent = `${pip.assets.length} / ${model.MAX_ASSETS}`;
        query("[data-pip-assets-status]").textContent = `${pip.assets.length} 个`;
        for (const asset of pip.assets) {
          const overlay = pip.overlays.find((item) => String(item.assetId) === asset.id);
          const ready = model.isReadyAsset(asset);
          const card = host.ownerDocument.createElement("article");
          card.className = "pip-generated-card editor-pip-asset-card";
          card.dataset.pictureId = asset.id;
          card.classList.toggle("is-selected", state.selectedAssetId === asset.id || Boolean(overlay && selectedOverlay()?.assetId === asset.id));
          card.classList.toggle("is-processing", ["queued", "processing"].includes(asset.status));
          card.classList.toggle("is-failed", asset.status === "failed");
          const preview = host.ownerDocument.createElement("button");
          preview.type = "button";
          preview.className = "pip-image-preview-button";
          preview.disabled = !ready;
          preview.setAttribute("aria-label", `选择画中画素材：${asset.text || asset.id}`);
          if (ready) {
            if (asset.type === "video") {
              const videoBadge = host.ownerDocument.createElement("span");
              videoBadge.className = "pip-asset-placeholder pip-video-badge";
              videoBadge.textContent = "视频素材";
              preview.append(videoBadge);
            } else {
              const media = host.ownerDocument.createElement("img");
              media.src = asset.assetUrl;
              media.alt = "";
              preview.append(media);
            }
          } else {
            const placeholder = host.ownerDocument.createElement("span");
            placeholder.className = "pip-asset-placeholder";
            placeholder.textContent = asset.status === "failed" ? "生成失败" : `${Math.round(Number(asset.progress) || 10)}%`;
            preview.append(placeholder);
          }
          preview.addEventListener("click", () => {
            state.selectedAssetId = asset.id;
            if (overlay) services.commands.selectPip(asset.id);
            services.media.seekEdited(Number(overlay?.start ?? asset.start) || 0);
            renderAssets();
            syncRangeInputs();
          });

          const content = host.ownerDocument.createElement("div");
          content.className = "pip-generated-content";
          const heading = host.ownerDocument.createElement("div");
          heading.className = "pip-generated-top";
          const enabledLabel = host.ownerDocument.createElement("label");
          enabledLabel.className = "pip-enabled-toggle";
          const enabled = host.ownerDocument.createElement("input");
          enabled.type = "checkbox";
          enabled.checked = Boolean(overlay);
          enabled.disabled = !ready;
          enabled.setAttribute("aria-label", `使用画中画：${asset.text || asset.id}`);
          enabled.addEventListener("change", () => {
            const latest = projectPip();
            const next = model.setAssetEnabled(latest, asset.id, enabled.checked, {
              source: latest.source,
              duration: duration(),
            });
            state.selectedAssetId = asset.id;
            services.commands.replacePip(next, {
              selection: enabled.checked ? `pip:${asset.id}` : null,
            });
          });
          enabledLabel.append(enabled, host.ownerDocument.createTextNode("使用"));
          const meta = host.ownerDocument.createElement("time");
          meta.textContent = asset.status === "failed"
            ? String(asset.error || "生成失败")
            : `${asset.type === "video" ? "视频" : "图片"} · ${asset.aspectRatio || "16:9"}`;
          heading.append(enabledLabel, meta);
          const text = host.ownerDocument.createElement("p");
          text.textContent = asset.text || asset.prompt || "画中画素材";
          content.append(heading, text);

          if (overlay) {
            const controls = host.ownerDocument.createElement("div");
            controls.className = "pip-item-controls editor-pip-item-controls";
            const positionLabel = host.ownerDocument.createElement("label");
            positionLabel.append(host.ownerDocument.createTextNode("位置"));
            const position = host.ownerDocument.createElement("select");
            position.setAttribute("aria-label", `设置“${asset.text || asset.id}”的位置`);
            const currentPosition = placementKey(overlay);
            if (currentPosition === "custom") {
              const custom = host.ownerDocument.createElement("option");
              custom.value = "custom";
              custom.textContent = "自定义";
              position.append(custom);
            }
            for (const [key, preset] of Object.entries(POSITION_PRESETS)) {
              const option = host.ownerDocument.createElement("option");
              option.value = key;
              option.textContent = preset.label;
              option.selected = key === currentPosition;
              position.append(option);
            }
            position.addEventListener("change", () => {
              const preset = POSITION_PRESETS[position.value];
              if (preset) commitOverlayPatch(asset.id, preset);
            });
            positionLabel.append(position);

            const sizeLabel = host.ownerDocument.createElement("label");
            sizeLabel.append(host.ownerDocument.createTextNode("宽度（%）"));
            const size = host.ownerDocument.createElement("input");
            size.type = "number";
            size.min = String(model.MIN_WIDTH * 100);
            size.step = "1";
            size.value = String(Math.round(overlay.width * 10000) / 100);
            size.dataset.pipWidth = asset.id;
            size.setAttribute("aria-label", `调整“${asset.text || asset.id}”的宽度`);
            size.addEventListener("change", () => {
              const width = Number(size.value) / 100;
              if (!Number.isFinite(width) || width < model.MIN_WIDTH) {
                size.value = String(Math.round(overlay.width * 10000) / 100);
                setMessage("[data-pip-error]", `画中画宽度不能小于 ${model.MIN_WIDTH * 100}%。`, "error");
                return;
              }
              setMessage("[data-pip-error]", "");
              commitOverlayPatch(asset.id, { width });
            });
            sizeLabel.append(size);
            controls.append(positionLabel, sizeLabel);
            content.append(controls);
          }
          card.append(preview, content);
          list.append(card);
        }
      }

      function renderBusy() {
        const busy = state.requests.has("prompt") || state.requests.has("create");
        const promptButton = query("[data-pip-write-prompt]");
        const generateButton = query("[data-pip-generate]");
        promptButton.disabled = busy;
        generateButton.disabled = busy || projectPip().assets.length >= model.MAX_ASSETS;
        promptButton.setAttribute("aria-busy", String(state.requests.has("prompt")));
        generateButton.setAttribute("aria-busy", String(state.requests.has("create")));
        generateButton.textContent = state.requests.has("create") ? "正在生成…" : "生成画中画素材";
      }

      function render(frame = state.frame) {
        if (state.destroyed) return false;
        if (frame) state.frame = frame;
        const nextJobId = String(snapshot()?.jobId || "");
        const nextSource = projectPip().source;
        if (nextJobId !== state.jobId || nextSource !== state.source) {
          stopEffects();
          state.jobId = nextJobId;
          state.source = nextSource;
          state.selectedAssetId = "";
          state.selectedSegmentId = "";
          state.requestedRange = null;
          state.pollFailures = 0;
        }
        renderSegments();
        renderAssets();
        syncRangeInputs();
        renderBusy();
        if (state.active) schedulePendingPoll(0);
        return true;
      }

      function requestPayload(includeMode = false) {
        const segment = selectedSegment();
        const range = currentRange();
        if (!segment || !range) return null;
        return {
          text: segment.text,
          start: range.start,
          end: range.end,
          ...(includeMode
            ? {
                mode: state.generationMode,
                prompt: String(query("[data-pip-prompt]")?.value || "").trim(),
              }
            : { assetType: state.assetType }),
          source: projectPip().source,
          aspectRatio: state.aspectRatio,
          sourceStart: Number.isFinite(Number(segment.sourceStart)) ? Number(segment.sourceStart) : null,
          sourceEnd: Number.isFinite(Number(segment.sourceEnd)) ? Number(segment.sourceEnd) : null,
        };
      }

      async function writePrompt() {
        const payload = requestPayload(false);
        if (!payload) {
          setMessage("[data-pip-prompt-status]", "请先选择文案并设置有效时间。", "error");
          return;
        }
        const request = beginRequest("prompt");
        renderBusy();
        setMessage("[data-pip-prompt-status]", "AI 正在编写提示词…");
        try {
          const result = await services.api.request(
            `/api/transcriptions/${encodeURIComponent(request.jobId)}/picture-in-picture/prompt`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
              signal: request.controller.signal,
            },
          );
          if (!requestCurrent("prompt", request)) return;
          const prompt = String(result.prompt || "").trim();
          if (!prompt) throw new Error("AI 没有返回可用的提示词。");
          query("[data-pip-prompt]").value = prompt;
          setMessage("[data-pip-prompt-status]", "提示词草稿已生成，可以继续修改。", "success");
        } catch (error) {
          if (error?.name !== "AbortError" && requestCurrent("prompt", request)) {
            setMessage("[data-pip-prompt-status]", error.message || "AI 提示词生成失败。", "error");
          }
        } finally {
          finishRequest("prompt", request);
        }
      }

      function nextProjectWithAsset(record, autoEnable, token = null) {
        const latest = projectPip();
        const asset = model.normalizeAsset(record, { source: latest.source });
        if (!asset || asset.source !== latest.source) return false;
        const assets = model.mergeAssets(latest.assets, [asset], { source: latest.source });
        let next = { ...latest, assets };
        if (autoEnable && model.isReadyAsset(asset)) {
          next = model.setAssetEnabled(next, asset.id, true, {
            source: latest.source,
            duration: duration(),
          });
        }
        state.selectedAssetId = asset.id;
        return services.commands.replacePip(next, {
          selection: autoEnable && model.isReadyAsset(asset) ? `pip:${asset.id}` : undefined,
          token,
        });
      }

      async function generateAsset() {
        const payload = requestPayload(true);
        if (!payload) return;
        if (state.generationMode === "custom" && !payload.prompt) {
          setMessage("[data-pip-error]", "请输入想要生成的画中画内容。", "error");
          query("[data-pip-prompt]")?.focus();
          return;
        }
        if (projectPip().assets.length >= model.MAX_ASSETS) {
          setMessage("[data-pip-error]", "一个视频最多生成 20 个画中画素材。", "error");
          return;
        }
        setMessage("[data-pip-error]", "");
        const request = beginRequest("create");
        renderBusy();
        try {
          const endpoint = state.assetType === "video" ? "videos" : "images";
          const result = await services.api.request(
            `/api/transcriptions/${encodeURIComponent(request.jobId)}/picture-in-picture/${endpoint}`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
              signal: request.controller.signal,
            },
          );
          if (!requestCurrent("create", request)) return;
          const record = {
            ...result,
            type: result.type || state.assetType,
            source: result.source || request.source,
            status: result.status || (state.assetType === "image" ? "completed" : "queued"),
            sourceStart: payload.sourceStart,
            sourceEnd: payload.sourceEnd,
          };
          nextProjectWithAsset(record, model.isReadyAsset(record), request.token);
          if (state.generationMode === "custom") query("[data-pip-prompt]").value = "";
          if (!model.isReadyAsset(record)) schedulePendingPoll(0);
        } catch (error) {
          if (error?.name !== "AbortError" && requestCurrent("create", request)) {
            setMessage("[data-pip-error]", error.message || "画中画素材生成失败。", "error");
          }
        } finally {
          finishRequest("create", request);
        }
      }

      function pendingAssets() {
        return projectPip().assets.filter((asset) => ["queued", "processing"].includes(asset.status));
      }

      function schedulePendingPoll(delay = 2000) {
        root.clearTimeout(state.pollTimer);
        state.pollTimer = null;
        if (!state.active || !pendingAssets().length || state.requests.has("poll")) return;
        state.pollTimer = root.setTimeout(() => {
          state.pollTimer = null;
          void pollAssets();
        }, Math.max(0, delay));
      }

      async function pollAssets() {
        if (!state.active || !pendingAssets().length) return;
        const request = beginRequest("poll");
        try {
          const job = await services.api.request(
            `/api/transcriptions/${encodeURIComponent(request.jobId)}`,
            { signal: request.controller.signal },
          );
          if (!requestCurrent("poll", request)) return;
          const latest = projectPip();
          const previousById = new Map(latest.assets.map((asset) => [asset.id, asset]));
          const incoming = [
            ...(job.pictureInPictureImages || []).map((asset) => ({ ...asset, type: "image" })),
            ...(job.pictureInPictureVideos || []).map((asset) => ({ ...asset, type: "video" })),
          ];
          const assets = model.mergeAssets(latest.assets, incoming, { source: latest.source });
          let next = { ...latest, assets };
          let selection;
          for (const asset of assets) {
            const previous = previousById.get(asset.id);
            if (previous && !model.isReadyAsset(previous) && model.isReadyAsset(asset)) {
              next = model.setAssetEnabled(next, asset.id, true, {
                source: latest.source,
                duration: duration(),
              });
              selection = `pip:${asset.id}`;
              state.selectedAssetId = asset.id;
            }
          }
          services.commands.replacePip(next, { selection, token: request.token });
          state.pollFailures = 0;
        } catch (error) {
          if (error?.name !== "AbortError" && requestCurrent("poll", request)) {
            state.pollFailures += 1;
            setMessage("[data-pip-error]", error.message || "无法读取动态素材进度。", "error");
          }
        } finally {
          finishRequest("poll", request);
          if (state.pollFailures < 3) schedulePendingPoll(state.pollFailures ? 3500 : 2000);
        }
      }

      function commitRange() {
        const range = currentRange();
        if (!range) return;
        state.requestedRange = range;
        const overlay = selectedOverlay();
        if (!overlay) return;
        services.commands.setPipRange(overlay.assetId, range.start, range.end, {
          sourceStart: services.media.editedToSource(range.start, "start"),
          sourceEnd: services.media.editedToSource(range.end, "end"),
        });
      }

      function fitRange() {
        const segment = selectedSegment();
        if (!segment) return;
        state.requestedRange = { start: segment.start, end: segment.end };
        syncRangeInputs();
        const overlay = selectedOverlay();
        if (overlay) {
          services.commands.setPipRange(overlay.assetId, segment.start, segment.end, {
            sourceStart: segment.sourceStart,
            sourceEnd: segment.sourceEnd,
          });
        }
        services.media.seekEdited(segment.start);
      }

      function handleOptionChange(event) {
        const input = event.target;
        if (input.matches?.("[data-pip-asset-type]")) state.assetType = input.value;
        if (input.matches?.("[data-pip-mode]")) state.generationMode = input.value;
        if (input.matches?.("[data-pip-aspect]")) state.aspectRatio = input.value;
        for (const option of queryAll(".pip-mode-option")) {
          option.classList.toggle("is-selected", Boolean(option.querySelector("input")?.checked));
        }
        query("[data-pip-prompt-field]").hidden = state.generationMode === "auto";
      }

      query("[data-pip-write-prompt]").addEventListener("click", writePrompt);
      query("[data-pip-generate]").addEventListener("click", generateAsset);
      query("[data-pip-fit]").addEventListener("click", fitRange);
      query("[data-pip-aspect]").addEventListener("change", handleOptionChange);
      for (const input of queryAll("[data-pip-asset-type], [data-pip-mode]")) {
        input.addEventListener("change", handleOptionChange);
      }
      for (const input of queryAll("[data-pip-range]")) {
        input.addEventListener("change", commitRange);
      }
      const unsubscribeProject = services.project.subscribe((next, previous) => {
        if (
          next?.jobId !== previous?.jobId ||
          next?.project?.pip?.source !== previous?.project?.pip?.source
        ) {
          stopEffects();
          state.selectedAssetId = "";
          state.selectedSegmentId = "";
          state.requestedRange = null;
          state.pollFailures = 0;
        }
        if (state.active) render(state.frame);
      });
      const unsubscribeFrame = services.media.subscribeFrame(() => {});

      function activate() {
        if (state.destroyed || state.active) return false;
        state.active = true;
        render(state.frame);
        schedulePendingPoll(0);
        return true;
      }

      function deactivate() {
        if (state.destroyed || !state.active) return false;
        state.active = false;
        stopEffects();
        query("[data-pip-prompt]").value = "";
        setMessage("[data-pip-prompt-status]", "");
        setMessage("[data-pip-error]", "");
        state.requestedRange = null;
        if (ownedRoot.contains(host.ownerDocument.activeElement)) {
          host.ownerDocument.activeElement.blur?.();
        }
        return true;
      }

      function destroy() {
        if (state.destroyed) return;
        deactivate();
        state.destroyed = true;
        stopEffects();
        unsubscribeProject();
        unsubscribeFrame();
        ownedRoot.remove();
        if (mountedTools.get(host)?.destroy === destroy) mountedTools.delete(host);
      }

      const tool = Object.freeze({ activate, deactivate, render, destroy });
      mountedTools.set(host, tool);
      return tool;
    }

    return Object.freeze({ mount });
  },
);
