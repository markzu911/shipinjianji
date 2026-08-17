const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f-]{27}$/i;
const FONT_FAMILIES = {
  modern: '"Microsoft YaHei", sans-serif',
  bold: '"Microsoft YaHei", sans-serif',
  classic: '"SimHei", sans-serif',
  song: '"SimSun", serif',
  kai: '"KaiTi", serif',
  fang: '"FangSong", serif',
};

const backToVideoEditor = document.querySelector("#backToVideoEditor");
const templateCount = document.querySelector("#templateCount");
const uploadedTemplateCount = document.querySelector("#uploadedTemplateCount");
const preferredTemplateName = document.querySelector("#preferredTemplateName");
const openTemplateUpload = document.querySelector("#openTemplateUpload");
const templatePreviewText = document.querySelector("#templatePreviewText");
const templateFont = document.querySelector("#templateFont");
const templatePreviewSize = document.querySelector("#templatePreviewSize");
const templatePreviewSizeValue = document.querySelector(
  "#templatePreviewSizeValue",
);
const templatePreviewColor = document.querySelector("#templatePreviewColor");
const templateSearch = document.querySelector("#templateSearch");
const templateFilterButtons = [
  ...document.querySelectorAll("[data-template-filter]"),
];
const templateLibraryLoading = document.querySelector(
  "#templateLibraryLoading",
);
const templateLibraryEmpty = document.querySelector("#templateLibraryEmpty");
const templateCardGrid = document.querySelector("#templateCardGrid");
const hiddenTemplatesSection = document.querySelector(
  "#hiddenTemplatesSection",
);
const hiddenTemplatesGrid = document.querySelector("#hiddenTemplatesGrid");
const templateDetailCategory = document.querySelector(
  "#templateDetailCategory",
);
const templateDetailPreview = document.querySelector(
  "#templateDetailPreview",
);
const templateDetailName = document.querySelector("#templateDetailName");
const templateDetailDescription = document.querySelector(
  "#templateDetailDescription",
);
const templateDetailType = document.querySelector("#templateDetailType");
const templateDetailFont = document.querySelector("#templateDetailFont");
const templateDetailSize = document.querySelector("#templateDetailSize");
const templatePrimarySwatch = document.querySelector(
  "#templatePrimarySwatch",
);
const templateStrokeSwatch = document.querySelector("#templateStrokeSwatch");
const useTemplateButton = document.querySelector("#useTemplateButton");
const restoreTemplateColor = document.querySelector(
  "#restoreTemplateColor",
);
const uploadedTemplateActions = document.querySelector(
  "#uploadedTemplateActions",
);
const renameTemplateButton = document.querySelector("#renameTemplateButton");
const deleteTemplateButton = document.querySelector("#deleteTemplateButton");
const templateUploadDialog = document.querySelector("#templateUploadDialog");
const templateUploadForm = document.querySelector("#templateUploadForm");
const templateUploadFile = document.querySelector("#templateUploadFile");
const templateUploadFilename = document.querySelector(
  "#templateUploadFilename",
);
const templateUploadError = document.querySelector("#templateUploadError");
const submitTemplateUpload = document.querySelector("#submitTemplateUpload");
const downloadTemplateExample = document.querySelector(
  "#downloadTemplateExample",
);
const templateRenameDialog = document.querySelector("#templateRenameDialog");
const templateRenameForm = document.querySelector("#templateRenameForm");
const templateRenameInput = document.querySelector("#templateRenameInput");
const templateRenameError = document.querySelector("#templateRenameError");
const submitTemplateRename = document.querySelector("#submitTemplateRename");
const templateLibraryStatus = document.querySelector(
  "#templateLibraryStatus",
);

const query = new URLSearchParams(window.location.search);
const jobId = query.get("job") || "";
const videoSource = query.get("source") === "original" ? "original" : "edited";
const loadedFontFamilies = new Map();
const templateColors = new Map();
let previewFitFrame = 0;
const fontNames = new Map();
let templates = [];
let hiddenBuiltins = [];
let activeTemplateId = "impact";
let preferredTemplateId = "impact";
let activeFilter = "all";

try {
  preferredTemplateId =
    window.localStorage.getItem("preferredArtTemplateId") || "impact";
} catch {
  preferredTemplateId = "impact";
}

if (JOB_ID_PATTERN.test(jobId)) {
  backToVideoEditor.href =
    `/art-text?job=${encodeURIComponent(jobId)}` +
    `&source=${encodeURIComponent(videoSource)}`;
}

function currentTemplate() {
  return (
    templates.find((template) => template.id === activeTemplateId) ||
    templates[0] ||
    null
  );
}

function currentPreviewText() {
  return templatePreviewText.value.trim() || "新征程新赶考";
}

function templateColorFor(template) {
  return templateColors.get(template.id) || template.color;
}

function syncActiveTemplateColorControl() {
  const template = currentTemplate();
  if (!template) return;
  templatePreviewColor.value = templateColorFor(template);
}

function normalizedTemplateEffects(template = {}, primaryColor = template.color) {
  const animation =
    template.animation && typeof template.animation === "object"
      ? template.animation
      : {};
  const characterLayout =
    template.characterLayout && typeof template.characterLayout === "object"
      ? template.characterLayout
      : {};
  const staggered = characterLayout.type === "staggered";
  const rotations = Array.isArray(characterLayout.rotationPattern)
    ? characterLayout.rotationPattern
        .slice(0, 12)
        .map((value) => Math.min(12, Math.max(-12, Number(value) || 0)))
    : [];
  const verticalOffsets = Array.isArray(characterLayout.verticalOffsetPattern)
    ? characterLayout.verticalOffsetPattern
        .slice(0, 12)
        .map((value) => Math.min(0.25, Math.max(-0.25, Number(value) || 0)))
    : [];
  return {
    color: primaryColor || "#FFFFFF",
    letterSpacing: Math.min(
      40,
      Math.max(-20, Math.round(Number(template.letterSpacing) || 0)),
    ),
    textColorMode:
      template.textColorMode === "center-highlight"
        ? "center-highlight"
        : "solid",
    secondaryColor: template.secondaryColor || primaryColor || "#FFFFFF",
    animation: {
      type:
        animation.type === "character-bounce"
          ? "character-bounce"
          : "none",
      duration: Math.min(2, Math.max(0.2, Number(animation.duration) || 0.56)),
      stagger: Math.min(0.3, Math.max(0, Number(animation.stagger) || 0.07)),
      amplitude: Math.min(0.5, Math.max(0.05, Number(animation.amplitude) || 0.18)),
    },
    characterLayout: {
      type: staggered ? "staggered" : "none",
      rotationPattern: staggered
        ? rotations.length
          ? rotations
          : [-7, 5, -4, 3, -6, 4]
        : [],
      verticalOffsetPattern: staggered
        ? verticalOffsets.length
          ? verticalOffsets
          : [0.06, -0.04, 0.03, -0.05]
        : [],
    },
  };
}

function renderTemplateCharacters(element, text, template, primaryColor) {
  const effects = normalizedTemplateEffects(template, primaryColor);
  const needsCharacters =
    effects.textColorMode === "center-highlight" ||
    effects.animation.type === "character-bounce" ||
    effects.characterLayout.type === "staggered";
  element.classList.toggle("has-character-effect", needsCharacters);
  element.setAttribute("aria-label", text);
  if (!needsCharacters) {
    element.textContent = text;
    return;
  }
  const characters = Array.from(text);
  const visibleIndexes = characters
    .map((character, index) => (/\s/u.test(character) ? -1 : index))
    .filter((index) => index >= 0);
  const highlightedStart = Math.floor(visibleIndexes.length * 0.25);
  const highlightedEnd = Math.ceil(visibleIndexes.length * 0.75);
  const highlightedIndexes = new Set(
    visibleIndexes.slice(highlightedStart, highlightedEnd),
  );

  element.replaceChildren();
  characters.forEach((character, index) => {
    if (/\s/u.test(character)) {
      element.append(document.createTextNode(character));
      return;
    }
    const span = document.createElement("span");
    span.className = "art-character";
    span.textContent = character;
    span.setAttribute("aria-hidden", "true");
    const isPrimary =
      effects.textColorMode !== "center-highlight" ||
      highlightedIndexes.has(index);
    span.style.color = isPrimary ? effects.color : effects.secondaryColor;
    if (effects.characterLayout.type === "staggered") {
      const visibleIndex = visibleIndexes.indexOf(index);
      const rotations = effects.characterLayout.rotationPattern;
      const offsets = effects.characterLayout.verticalOffsetPattern;
      span.classList.add("is-character-staggered");
      span.style.setProperty(
        "--art-character-rotation",
        `${rotations[visibleIndex % rotations.length]}deg`,
      );
      span.style.setProperty(
        "--art-character-offset",
        `${offsets[visibleIndex % offsets.length]}em`,
      );
    }
    if (effects.animation.type === "character-bounce") {
      const visibleIndex = visibleIndexes.indexOf(index);
      span.classList.add("is-character-bounce");
      span.style.animationDuration = `${effects.animation.duration}s`;
      span.style.animationDelay = `${visibleIndex * effects.animation.stagger}s`;
      span.style.setProperty(
        "--art-character-lift",
        `${effects.animation.amplitude}em`,
      );
    }
    element.append(span);
  });
}

function fitEffectPreviewText(element) {
  const visibleCharacterCount = Number(element.dataset.characterCount) || 1;
  const requestedFontSize = Number(element.dataset.requestedFontSize) || 24;
  const letterSpacing = Number(element.dataset.templateLetterSpacing) || 0;
  const fallbackWidth = element.classList.contains("template-card-preview")
    ? 232
    : 190;
  const styles = window.getComputedStyle(element);
  const contentWidth =
    element.clientWidth -
    (Number.parseFloat(styles.paddingLeft) || 0) -
    (Number.parseFloat(styles.paddingRight) || 0);
  const availableTextWidth = Math.max(
    48,
    (contentWidth > 0 ? contentWidth : fallbackWidth) - 12,
  );
  const spacingWidth = letterSpacing * Math.max(0, visibleCharacterCount - 1);
  const fittedFontSize = Math.max(
    10,
    (availableTextWidth - spacingWidth) / visibleCharacterCount,
  );
  element.style.fontSize = `${Math.min(requestedFontSize, fittedFontSize)}px`;
}

function scheduleEffectPreviewFit() {
  window.cancelAnimationFrame(previewFitFrame);
  previewFitFrame = window.requestAnimationFrame(() => {
    previewFitFrame = 0;
    document
      .querySelectorAll(".template-card-preview, .template-detail-preview")
      .forEach(fitEffectPreviewText);
  });
}

function announce(message) {
  templateLibraryStatus.textContent = "";
  window.requestAnimationFrame(() => {
    templateLibraryStatus.textContent = message;
  });
}

function fontFamilyFor(font) {
  if (font.source === "uploaded") {
    return loadedFontFamilies.get(font.id) || "sans-serif";
  }
  return font.cssFamily || FONT_FAMILIES[font.id] || "sans-serif";
}

async function registerUploadedFont(font) {
  if (font.source !== "uploaded" || loadedFontFamilies.has(font.id)) return;
  const family = `UserFont_${font.id.replace(/[^a-z0-9_]/gi, "_")}`;
  const format = /\.otf$/i.test(font.originalFilename || "")
    ? "opentype"
    : "truetype";
  const face = new FontFace(
    family,
    `url("${font.fileUrl}") format("${format}")`,
    { display: "swap" },
  );
  await face.load();
  document.fonts.add(face);
  loadedFontFamilies.set(font.id, `"${family}", sans-serif`);
}

function applyEffectPreview(element, template, options = {}) {
  if (!template) return;
  const fontId = templateFont.value || "bold";
  const size = Number(templatePreviewSize.value) || 46;
  const color = templateColorFor(template);
  const effects = normalizedTemplateEffects(template, color);
  const previewText = currentPreviewText();
  const visibleCharacterCount = Math.max(
    1,
    Array.from(previewText).filter((character) => !/\s/u.test(character)).length,
  );
  const requestedFontSize = options.card
    ? Math.min(44, size)
    : Math.min(72, size + 8);
  element.className =
    `${options.card ? "template-card-preview" : "template-detail-preview"} ` +
    `style-${template.baseStyle || template.id}`;
  element.style.fontFamily = FONT_FAMILIES[fontId] || "sans-serif";
  element.dataset.characterCount = String(visibleCharacterCount);
  element.dataset.requestedFontSize = String(requestedFontSize);
  element.dataset.templateLetterSpacing = String(effects.letterSpacing);
  element.style.letterSpacing = "0px";
  element.style.setProperty(
    "--template-letter-spacing",
    `${effects.letterSpacing}px`,
  );
  element.style.setProperty("--template-color", color);
  element.style.setProperty("--template-stroke", template.strokeColor);
  renderTemplateCharacters(element, previewText, template, color);
  if (!element.classList.contains("has-character-effect")) {
    element.style.letterSpacing = `${effects.letterSpacing}px`;
  }
  fitEffectPreviewText(element);
  scheduleEffectPreviewFit();
}

function filteredTemplates() {
  const search = templateSearch.value.trim().toLocaleLowerCase("zh-CN");
  return templates.filter((template) => {
    const matchesFilter =
      activeFilter === "all" ||
      (activeFilter === "uploaded"
        ? template.source === "uploaded"
        : template.category === activeFilter);
    const matchesSearch =
      !search ||
      [template.name, template.sample, template.description, template.category]
        .some((value) =>
          String(value).toLocaleLowerCase("zh-CN").includes(search),
        );
    return matchesFilter && matchesSearch;
  });
}

function createTemplateCard(template) {
  const card = document.createElement("article");
  card.className = "template-card";
  card.classList.toggle("is-selected", template.id === activeTemplateId);
  card.classList.toggle("is-preferred", template.id === preferredTemplateId);
  card.dataset.templateId = template.id;

  const badge = document.createElement("span");
  badge.className = "font-source-badge";
  badge.textContent =
    template.id === preferredTemplateId
      ? "默认"
      : template.source === "uploaded"
        ? "我的"
        : template.category;

  const preview = document.createElement("div");
  applyEffectPreview(preview, template, { card: true });

  const copy = document.createElement("div");
  copy.className = "template-card-copy";
  const name = document.createElement("strong");
  name.textContent = template.name;
  const description = document.createElement("small");
  description.textContent = template.description;
  copy.append(name, description);

  const actions = document.createElement("div");
  actions.className = "template-card-actions";
  const viewButton = document.createElement("button");
  viewButton.type = "button";
  viewButton.className = "secondary-button";
  viewButton.textContent = "查看";
  viewButton.addEventListener("click", () => selectTemplate(template.id));
  const useButton = document.createElement("button");
  useButton.type = "button";
  useButton.className = "primary-button";
  useButton.textContent =
    template.id === preferredTemplateId ? "已使用" : "使用";
  useButton.addEventListener("click", () => useTemplate(template.id));
  actions.append(viewButton, useButton);

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "template-card-delete";
  deleteButton.setAttribute("aria-label", `删除模板 ${template.name}`);
  deleteButton.title = template.source === "uploaded" ? "删除模板" : "从模板库隐藏";
  deleteButton.innerHTML =
    '<iconify-icon icon="ph:x-bold" aria-hidden="true"></iconify-icon>';
  deleteButton.addEventListener("click", (event) => {
    event.stopPropagation();
    deleteTemplateById(template.id);
  });

  card.append(badge, preview, copy, actions, deleteButton);
  return card;
}

function renderTemplateCards() {
  const visibleTemplates = filteredTemplates();
  templateCardGrid.replaceChildren(
    ...visibleTemplates.map(createTemplateCard),
  );
  templateLibraryEmpty.hidden = visibleTemplates.length > 0;
}

function renderTemplateDetail() {
  const template = currentTemplate();
  if (!template) return;
  applyEffectPreview(templateDetailPreview, template);
  templateDetailCategory.textContent = template.category;
  templateDetailName.textContent = template.name;
  templateDetailDescription.textContent = template.description;
  templateDetailType.textContent =
    template.source === "uploaded" ? "我的可编辑效果" : "内置效果";
  templateDetailFont.textContent =
    fontNames.get(templateFont.value) || "醒目粗体";
  templateDetailSize.textContent = templatePreviewSize.value;
  templatePrimarySwatch.style.background = templateColorFor(template);
  templateStrokeSwatch.style.background = template.strokeColor;
  preferredTemplateName.textContent =
    `默认模板 ${
      templates.find((item) => item.id === preferredTemplateId)?.name ||
      template.name
    }`;
  useTemplateButton.textContent =
    template.id === preferredTemplateId ? "当前默认模板" : "使用此模板";
  const isUploaded = template.source === "uploaded";
  uploadedTemplateActions.hidden = !isUploaded;
  deleteTemplateButton.textContent = isUploaded ? "删除模板" : "从模板库隐藏";
}

function render() {
  templatePreviewSizeValue.value = templatePreviewSize.value;
  renderTemplateCards();
  renderTemplateDetail();
}

function selectTemplate(templateId) {
  if (!templates.some((template) => template.id === templateId)) return;
  activeTemplateId = templateId;
  syncActiveTemplateColorControl();
  render();
}

function storeTemplateChoice(template) {
  const color = templateColorFor(template);
  const effects = normalizedTemplateEffects(template, color);
  const selection = {
    id: template.id,
    color,
    strokeColor: template.strokeColor,
    font: templateFont.value,
    fontSize: Number(templatePreviewSize.value) || 46,
    letterSpacing: effects.letterSpacing,
    textColorMode: effects.textColorMode,
    secondaryColor: effects.secondaryColor,
    animation: effects.animation,
    characterLayout: effects.characterLayout,
  };
  preferredTemplateId = template.id;
  try {
    window.localStorage.setItem("preferredArtTemplateId", selection.id);
    window.localStorage.setItem(
      "preferredArtTemplateSettings",
      JSON.stringify(selection),
    );
  } catch {
    // The query parameters still carry the selection back to the editor.
  }
  return selection;
}

function useTemplate(templateId) {
  const template = templates.find((item) => item.id === templateId);
  if (!template) return;
  activeTemplateId = template.id;
  syncActiveTemplateColorControl();
  const selection = storeTemplateChoice(template);
  render();
  announce(`已选择 ${template.name}。`);

  if (!JOB_ID_PATTERN.test(jobId)) return;
  const destination = new URL("/art-text", window.location.origin);
  destination.searchParams.set("job", jobId);
  destination.searchParams.set("source", videoSource);
  destination.searchParams.set("template", selection.id);
  destination.searchParams.set("templateColor", selection.color);
  destination.searchParams.set("templateStroke", selection.strokeColor);
  destination.searchParams.set("templateFont", selection.font);
  destination.searchParams.set("templateSize", String(selection.fontSize));
  window.location.assign(destination);
}

async function loadTemplates(options = {}) {
  const response = await fetch("/api/art-templates");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "无法读取艺术字模板库。");
  }
  templates = payload.templates || [];
  const currentTemplateIds = new Set(templates.map((template) => template.id));
  for (const templateId of templateColors.keys()) {
    if (!currentTemplateIds.has(templateId)) templateColors.delete(templateId);
  }
  hiddenBuiltins = Array.isArray(payload.hiddenBuiltins)
    ? payload.hiddenBuiltins
    : [];
  templateCount.textContent = `内置模板 ${payload.builtinCount || 0}`;
  uploadedTemplateCount.textContent =
    `我的模板 ${payload.uploadedCount || 0}`;
  renderHiddenTemplates();

  if (!templates.some((template) => template.id === preferredTemplateId)) {
    preferredTemplateId = "impact";
    try {
      window.localStorage.setItem("preferredArtTemplateId", "impact");
      window.localStorage.removeItem("preferredArtTemplateSettings");
    } catch {
      // The built-in fallback remains active for this session.
    }
  }
  const requestedActiveId = options.activeId || activeTemplateId;
  activeTemplateId = templates.some(
    (template) => template.id === requestedActiveId,
  )
    ? requestedActiveId
    : preferredTemplateId;
  const active = currentTemplate();
  if (active && options.restoreColor !== false) syncActiveTemplateColorControl();
  render();
  return payload;
}

function closeDialog(dialog) {
  if (dialog.open) dialog.close();
}

function showDialogError(element, message = "") {
  element.textContent = message;
  element.hidden = !message;
}

async function uploadTemplate(event) {
  event.preventDefault();
  const file = templateUploadFile.files?.[0];
  if (!file) {
    showDialogError(templateUploadError, "请选择艺术字效果模板文件。");
    templateUploadFile.focus();
    return;
  }
  showDialogError(templateUploadError);
  submitTemplateUpload.disabled = true;
  submitTemplateUpload.textContent = "正在上传…";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch("/api/art-templates", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "艺术字模板上传失败。");
    }
    templateUploadForm.reset();
    templateUploadFilename.textContent =
      "支持 .json 或 .arttext，最大 256KB，不支持 TTF/OTF 字体";
    closeDialog(templateUploadDialog);
    await loadTemplates({ activeId: payload.id });
    activeTemplateId = payload.id;
    syncActiveTemplateColorControl();
    render();
    announce(`已上传艺术字模板 ${payload.name}。`);
  } catch (error) {
    showDialogError(templateUploadError, error.message);
  } finally {
    submitTemplateUpload.disabled = false;
    submitTemplateUpload.textContent = "上传到模板库";
  }
}

function openRenameDialog() {
  const template = currentTemplate();
  if (!template || template.source !== "uploaded") return;
  templateRenameInput.value = template.name;
  showDialogError(templateRenameError);
  templateRenameDialog.showModal();
  window.requestAnimationFrame(() => {
    templateRenameInput.focus();
    templateRenameInput.select();
  });
}

async function renameTemplate(event) {
  event.preventDefault();
  const template = currentTemplate();
  if (!template || template.source !== "uploaded") return;
  const name = templateRenameInput.value.trim();
  if (!name) {
    showDialogError(templateRenameError, "请输入艺术字模板名称。");
    templateRenameInput.focus();
    return;
  }
  showDialogError(templateRenameError);
  submitTemplateRename.disabled = true;
  submitTemplateRename.textContent = "正在保存…";
  try {
    const response = await fetch(
      `/api/art-templates/${encodeURIComponent(template.id)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      },
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "艺术字模板名称修改失败。");
    }
    closeDialog(templateRenameDialog);
    await loadTemplates({
      activeId: payload.id,
      restoreColor: false,
    });
    announce(`已将艺术字模板修改为 ${payload.name}。`);
  } catch (error) {
    showDialogError(templateRenameError, error.message);
  } finally {
    submitTemplateRename.disabled = false;
    submitTemplateRename.textContent = "保存名称";
  }
}

async function deleteTemplateById(templateId) {
  const template = templates.find((item) => item.id === templateId);
  if (!template) return;
  const isUploaded = template.source === "uploaded";
  const confirmed = await window.appConfirm({
    eyebrow: isUploaded ? "删除艺术字模板" : "隐藏内置模板",
    title: isUploaded
      ? `删除“${template.name}”？`
      : `从模板库隐藏“${template.name}”？`,
    message: isUploaded
      ? "删除后将无法再使用该艺术字效果，此操作不能撤销。"
      : "隐藏后不再显示在模板库中，可在底部「已隐藏的内置模板」里恢复。",
    confirmText: isUploaded ? "确认删除" : "隐藏",
    tone: "danger",
  });
  if (!confirmed) return;
  deleteTemplateButton.disabled = true;
  try {
    const response = await fetch(
      `/api/art-templates/${encodeURIComponent(template.id)}`,
      { method: "DELETE" },
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "艺术字模板删除失败。");
    }
    if (preferredTemplateId === template.id) {
      preferredTemplateId = "impact";
      try {
        window.localStorage.setItem("preferredArtTemplateId", "impact");
        window.localStorage.removeItem("preferredArtTemplateSettings");
      } catch {
        // The built-in fallback remains active for this session.
      }
    }
    await loadTemplates({ activeId: preferredTemplateId });
    announce(
      isUploaded
        ? `已删除艺术字模板 ${template.name}。`
        : `已隐藏内置模板 ${template.name}。`,
    );
  } catch (error) {
    announce(error.message);
    await window.appAlert({
      title: "艺术字模板删除失败",
      message: error.message,
    });
  } finally {
    deleteTemplateButton.disabled = false;
  }
}

function deleteTemplate() {
  const template = currentTemplate();
  if (template) deleteTemplateById(template.id);
}

function renderHiddenTemplates() {
  if (!hiddenTemplatesSection || !hiddenTemplatesGrid) return;
  hiddenTemplatesSection.hidden = hiddenBuiltins.length === 0;
  hiddenTemplatesGrid.replaceChildren();
  for (const template of hiddenBuiltins) {
    const chip = document.createElement("div");
    chip.className = "hidden-template-chip";
    chip.title = `内置模板 · ${template.category}`;
    const name = document.createElement("span");
    name.textContent = template.name;
    const restoreButton = document.createElement("button");
    restoreButton.type = "button";
    restoreButton.className = "hidden-template-restore";
    restoreButton.textContent = "恢复";
    restoreButton.addEventListener("click", () => {
      restoreTemplate(template.id);
    });
    chip.append(name, restoreButton);
    hiddenTemplatesGrid.append(chip);
  }
}

async function restoreTemplate(templateId) {
  try {
    const response = await fetch(
      `/api/art-templates/${encodeURIComponent(templateId)}/restore`,
      { method: "POST" },
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "艺术字模板恢复失败。");
    }
    const restored = hiddenBuiltins.find((item) => item.id === templateId);
    await loadTemplates({ activeId: preferredTemplateId });
    if (restored) announce(`已恢复内置模板 ${restored.name}。`);
  } catch (error) {
    announce(error.message);
    await window.appAlert({
      title: "艺术字模板恢复失败",
      message: error.message,
    });
  }
}

function downloadTemplateExampleFile() {
  const example = {
    name: "逐字跃动",
    sample: "别再乱买衣服啦!",
    description: "黄白分字的漫画描边字，入场时逐字跃动。",
    baseStyle: "comic",
    color: "#FFF36A",
    strokeColor: "#0A0A0A",
    textColorMode: "center-highlight",
    secondaryColor: "#FFFFFF",
    animation: {
      type: "character-bounce",
      duration: 0.56,
      stagger: 0.07,
      amplitude: 0.18,
    },
  };
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(example, null, 2)], {
      type: "application/json;charset=utf-8",
    }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "艺术字模板示例.arttext";
  link.click();
  URL.revokeObjectURL(url);
}

async function loadFonts() {
  const response = await fetch("/api/fonts");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "无法读取字体库。");
  }
  const fonts = payload.fonts || [];
  await Promise.allSettled(
    fonts
      .filter((font) => font.source === "uploaded")
      .map(registerUploadedFont),
  );
  templateFont.replaceChildren();
  for (const font of fonts) {
    const option = document.createElement("option");
    option.value = font.id;
    option.textContent = font.name;
    templateFont.append(option);
    fontNames.set(font.id, font.name);
    FONT_FAMILIES[font.id] = fontFamilyFor(font);
  }
  let preferredFont = "bold";
  try {
    preferredFont =
      window.localStorage.getItem("preferredArtFontId") || "bold";
  } catch {
    preferredFont = "bold";
  }
  if (fonts.some((font) => font.id === preferredFont)) {
    templateFont.value = preferredFont;
  }
}

async function initialize() {
  templateLibraryLoading.hidden = false;
  try {
    await loadFonts();
    await loadTemplates({ activeId: preferredTemplateId });
  } catch (error) {
    templateCardGrid.replaceChildren();
    templateLibraryEmpty.hidden = false;
    templateLibraryEmpty.querySelector("strong").textContent =
      "艺术字模板读取失败";
    templateLibraryEmpty.querySelector("span").textContent = error.message;
  } finally {
    templateLibraryLoading.hidden = true;
  }
}

templatePreviewText.addEventListener("input", render);
templateFont.addEventListener("change", render);
templatePreviewSize.addEventListener("input", render);
templatePreviewColor.addEventListener("input", () => {
  const template = currentTemplate();
  if (!template) return;
  templateColors.set(template.id, templatePreviewColor.value);
  render();
});
templateSearch.addEventListener("input", renderTemplateCards);
window.addEventListener("resize", scheduleEffectPreviewFit);
openTemplateUpload.addEventListener("click", () => {
  showDialogError(templateUploadError);
  templateUploadDialog.showModal();
});
templateUploadForm.addEventListener("submit", uploadTemplate);
templateUploadFile.addEventListener("change", () => {
  const file = templateUploadFile.files?.[0];
  templateUploadFilename.textContent = file
    ? file.name
    : "支持 .json 或 .arttext，最大 256KB，不支持 TTF/OTF 字体";
  showDialogError(templateUploadError);
});
downloadTemplateExample.addEventListener(
  "click",
  downloadTemplateExampleFile,
);
renameTemplateButton.addEventListener("click", openRenameDialog);
templateRenameForm.addEventListener("submit", renameTemplate);
deleteTemplateButton.addEventListener("click", deleteTemplate);
for (const button of document.querySelectorAll("[data-close-template-upload]")) {
  button.addEventListener("click", () => closeDialog(templateUploadDialog));
}
for (const button of document.querySelectorAll("[data-close-template-rename]")) {
  button.addEventListener("click", () => closeDialog(templateRenameDialog));
}
for (const dialog of [templateUploadDialog, templateRenameDialog]) {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeDialog(dialog);
  });
}
useTemplateButton.addEventListener("click", () => {
  if (activeTemplateId) useTemplate(activeTemplateId);
});
restoreTemplateColor.addEventListener("click", () => {
  const template = currentTemplate();
  if (!template) return;
  templateColors.delete(template.id);
  syncActiveTemplateColorControl();
  render();
  announce(`已恢复 ${template.name} 的默认配色。`);
});

for (const button of templateFilterButtons) {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.templateFilter;
    for (const item of templateFilterButtons) {
      item.setAttribute("aria-pressed", String(item === button));
    }
    renderTemplateCards();
  });
}

initialize();
