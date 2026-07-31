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
const templateDetailNote = document.querySelector("#templateDetailNote");
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
const fontNames = new Map();
let templates = [];
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
  const color = templatePreviewColor.value || template.color;
  const fontSize = options.card ? Math.min(44, size) : Math.min(72, size + 8);
  element.className =
    `${options.card ? "template-card-preview" : "template-detail-preview"} ` +
    `style-${template.baseStyle || template.id}`;
  element.textContent = currentPreviewText();
  element.style.fontFamily = FONT_FAMILIES[fontId] || "sans-serif";
  element.style.fontSize = `${fontSize}px`;
  element.style.setProperty("--template-color", color);
  element.style.setProperty("--template-stroke", template.strokeColor);
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

  card.append(badge, preview, copy, actions);
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
  templatePrimarySwatch.style.background = templatePreviewColor.value;
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
  templateDetailNote.textContent = isUploaded
    ? "这是你上传的艺术字效果模板，可以修改名称或删除；文字、字号和颜色仍可在编辑器中调整。"
    : "内置模板不会被修改或删除；这里的调整只会作为本次艺术字参数带入编辑器。";
}

function render() {
  templatePreviewSizeValue.value = templatePreviewSize.value;
  renderTemplateCards();
  renderTemplateDetail();
}

function selectTemplate(templateId) {
  if (!templates.some((template) => template.id === templateId)) return;
  activeTemplateId = templateId;
  render();
}

function storeTemplateChoice(template) {
  const selection = {
    id: template.id,
    color: templatePreviewColor.value,
    strokeColor: template.strokeColor,
    font: templateFont.value,
    fontSize: Number(templatePreviewSize.value) || 46,
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
  templateCount.textContent = `内置模板 ${payload.builtinCount || 0}`;
  uploadedTemplateCount.textContent =
    `我的模板 ${payload.uploadedCount || 0}`;

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
  if (active && options.restoreColor !== false) {
    templatePreviewColor.value = active.color;
  }
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
    templatePreviewColor.value = payload.color;
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

async function deleteTemplate() {
  const template = currentTemplate();
  if (!template || template.source !== "uploaded") return;
  const confirmed = await window.appConfirm({
    eyebrow: "删除艺术字模板",
    title: `删除“${template.name}”？`,
    message: "删除后将无法再使用该艺术字效果，此操作不能撤销。",
    confirmText: "确认删除",
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
    announce(`已删除艺术字模板 ${template.name}。`);
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

function downloadTemplateExampleFile() {
  const example = {
    name: "我的蓝色立体字",
    sample: "蓝色",
    description: "蓝色主色与深蓝描边的立体艺术字。",
    baseStyle: "impact",
    color: "#59C7FF",
    strokeColor: "#102A43",
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
templatePreviewColor.addEventListener("input", render);
templateSearch.addEventListener("input", renderTemplateCards);
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
  templatePreviewColor.value = template.color;
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
