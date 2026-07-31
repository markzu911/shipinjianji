const fontUploadForm = document.querySelector("#fontUploadForm");
const fontFile = document.querySelector("#fontFile");
const fontDropZone = document.querySelector("#fontDropZone");
const fontFileSummary = document.querySelector("#fontFileSummary");
const fontFileName = document.querySelector("#fontFileName");
const fontFileSize = document.querySelector("#fontFileSize");
const fontUploadError = document.querySelector("#fontUploadError");
const uploadFontButton = document.querySelector("#uploadFontButton");
const fontPreviewText = document.querySelector("#fontPreviewText");
const fontPreviewSize = document.querySelector("#fontPreviewSize");
const fontPreviewSizeValue = document.querySelector("#fontPreviewSizeValue");
const fontPreviewColor = document.querySelector("#fontPreviewColor");
const fontSearch = document.querySelector("#fontSearch");
const builtinFontCount = document.querySelector("#builtinFontCount");
const uploadedFontCount = document.querySelector("#uploadedFontCount");
const fontLibraryLoading = document.querySelector("#fontLibraryLoading");
const fontLibraryEmpty = document.querySelector("#fontLibraryEmpty");
const fontCardGrid = document.querySelector("#fontCardGrid");
const fontFilterButtons = [
  ...document.querySelectorAll("[data-font-filter]"),
];
const fontDetailEmpty = document.querySelector("#fontDetailEmpty");
const fontDetailContent = document.querySelector("#fontDetailContent");
const fontDetailPreview = document.querySelector("#fontDetailPreview");
const fontDetailName = document.querySelector("#fontDetailName");
const fontDetailSource = document.querySelector("#fontDetailSource");
const fontDetailStyle = document.querySelector("#fontDetailStyle");
const fontDetailSize = document.querySelector("#fontDetailSize");
const fontDetailError = document.querySelector("#fontDetailError");
const useFontButton = document.querySelector("#useFontButton");
const saveFontNameButton = document.querySelector("#saveFontNameButton");
const downloadFontButton = document.querySelector("#downloadFontButton");
const deleteFontButton = document.querySelector("#deleteFontButton");
const fontLibraryStatus = document.querySelector("#fontLibraryStatus");

const FONT_FILE_PATTERN = /\.(ttf|otf)$/i;
const MAX_FONT_BYTES = 20 * 1024 * 1024;
const loadedFontFamilies = new Map();
let fonts = [];
let activeFilter = "all";
let selectedFontId = null;
let preferredFontId = "";
let uploadBusy = false;

try {
  preferredFontId = window.localStorage.getItem("preferredArtFontId") || "";
} catch {
  preferredFontId = "";
}

function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function showUploadError(message) {
  fontUploadError.textContent = message;
  fontUploadError.hidden = !message;
}

function showDetailError(message) {
  fontDetailError.textContent = message;
  fontDetailError.hidden = !message;
}

function announce(message) {
  fontLibraryStatus.textContent = "";
  window.requestAnimationFrame(() => {
    fontLibraryStatus.textContent = message;
  });
}

function fontFamilyFor(font) {
  if (font.source === "builtin") {
    return font.cssFamily || "sans-serif";
  }
  return loadedFontFamilies.get(font.id) || "sans-serif";
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

function currentPreviewText() {
  return fontPreviewText.value.trim() || "新征程新赶考";
}

function updatePreviewStyles() {
  const text = currentPreviewText();
  const size = Number(fontPreviewSize.value) || 42;
  const color = fontPreviewColor.value;
  fontPreviewSizeValue.value = String(size);

  for (const preview of document.querySelectorAll(".font-card-preview")) {
    preview.textContent = text;
    preview.style.fontSize = `${size}px`;
    preview.style.color = color;
  }
  const selected = fonts.find((font) => font.id === selectedFontId);
  if (selected) {
    fontDetailPreview.textContent = text;
    fontDetailPreview.style.fontFamily = fontFamilyFor(selected);
    fontDetailPreview.style.fontSize = `${Math.min(72, size + 10)}px`;
    fontDetailPreview.style.color = color;
  }
}

function filteredFonts() {
  const search = fontSearch.value.trim().toLocaleLowerCase("zh-CN");
  return fonts.filter((font) => {
    const matchesSource =
      activeFilter === "all" || font.source === activeFilter;
    const matchesSearch =
      !search ||
      [font.name, font.familyName, font.styleName, font.originalFilename]
        .filter(Boolean)
        .some((value) =>
          String(value).toLocaleLowerCase("zh-CN").includes(search),
        );
    return matchesSource && matchesSearch;
  });
}

function createFontCard(font) {
  const card = document.createElement("article");
  card.className = "font-card";
  card.classList.toggle("is-selected", font.id === selectedFontId);
  card.classList.toggle("is-preferred", font.id === preferredFontId);
  card.dataset.fontId = font.id;

  const sourceBadge = document.createElement("span");
  sourceBadge.className = "font-source-badge";
  sourceBadge.textContent = font.source === "builtin" ? "系统" : "我的";

  const preview = document.createElement("div");
  preview.className = "font-card-preview";
  preview.textContent = currentPreviewText();
  preview.style.fontFamily = fontFamilyFor(font);

  const meta = document.createElement("div");
  meta.className = "font-card-meta";
  const name = document.createElement("strong");
  name.textContent = font.name;
  const style = document.createElement("small");
  style.textContent =
    font.id === preferredFontId
      ? `${font.styleName || "Regular"} · 默认字体`
      : font.styleName || "Regular";
  meta.append(name, style);

  const actions = document.createElement("div");
  actions.className = "font-card-actions";
  const viewButton = document.createElement("button");
  viewButton.type = "button";
  viewButton.className = "secondary-button";
  viewButton.textContent = "查看";
  viewButton.addEventListener("click", () => selectFont(font.id));
  const useButton = document.createElement("button");
  useButton.type = "button";
  useButton.className = "primary-button";
  useButton.textContent = font.id === preferredFontId ? "已使用" : "使用";
  useButton.addEventListener("click", () => setPreferredFont(font.id));
  actions.append(viewButton, useButton);

  card.append(sourceBadge, preview, meta, actions);
  return card;
}

function renderFontCards() {
  const visibleFonts = filteredFonts();
  fontCardGrid.replaceChildren(...visibleFonts.map(createFontCard));
  fontLibraryEmpty.hidden = visibleFonts.length > 0;
  updatePreviewStyles();
}

function renderFontDetail() {
  const font = fonts.find((item) => item.id === selectedFontId);
  fontDetailEmpty.hidden = Boolean(font);
  fontDetailContent.hidden = !font;
  if (!font) return;

  fontDetailPreview.style.fontFamily = fontFamilyFor(font);
  fontDetailName.value = font.name;
  fontDetailName.readOnly = font.source === "builtin";
  fontDetailSource.textContent =
    font.source === "builtin" ? "系统自带字体" : "用户上传字体";
  fontDetailStyle.textContent = font.styleName || "Regular";
  fontDetailSize.textContent = formatBytes(font.fileSize);
  useFontButton.textContent =
    font.id === preferredFontId ? "当前默认字体" : "设为默认字体";
  saveFontNameButton.hidden = font.source === "builtin";
  downloadFontButton.hidden = font.source === "builtin";
  deleteFontButton.hidden = font.source === "builtin";
  downloadFontButton.href = font.downloadUrl || "#";
  showDetailError("");
  updatePreviewStyles();
}

function selectFont(fontId) {
  selectedFontId = fontId;
  renderFontCards();
  renderFontDetail();
}

function setPreferredFont(fontId) {
  const font = fonts.find((item) => item.id === fontId);
  if (!font) return;
  preferredFontId = fontId;
  try {
    window.localStorage.setItem("preferredArtFontId", fontId);
  } catch {
    // The current page still reflects the selection when storage is unavailable.
  }
  selectedFontId = fontId;
  renderFontCards();
  renderFontDetail();
  announce(`已将 ${font.name} 设为默认艺术字字体。`);
}

function updateFileSummary(file) {
  const isValid =
    file &&
    FONT_FILE_PATTERN.test(file.name) &&
    file.size > 0 &&
    file.size <= MAX_FONT_BYTES;
  fontFileSummary.hidden = !file;
  uploadFontButton.disabled = !isValid || uploadBusy;
  if (!file) {
    showUploadError("");
    return;
  }
  fontFileName.textContent = file.name;
  fontFileSize.textContent = formatBytes(file.size);
  if (!FONT_FILE_PATTERN.test(file.name)) {
    showUploadError("请选择 .ttf 或 .otf 字体文件。");
  } else if (file.size === 0) {
    showUploadError("字体文件不能为空。");
  } else if (file.size > MAX_FONT_BYTES) {
    showUploadError("字体文件不能超过 20MB。");
  } else {
    showUploadError("");
  }
}

async function loadFonts(options = {}) {
  fontLibraryLoading.hidden = false;
  try {
    const response = await fetch("/api/fonts");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "无法读取字体库。");
    }
    fonts = payload.fonts || [];
    await Promise.allSettled(
      fonts
        .filter((font) => font.source === "uploaded")
        .map(registerUploadedFont),
    );
    builtinFontCount.textContent = `系统字体 ${payload.builtinCount || 0}`;
    uploadedFontCount.textContent = `我的字体 ${payload.uploadedCount || 0}`;
    if (!fonts.some((font) => font.id === preferredFontId)) {
      preferredFontId = fonts.find((font) => font.id === "bold")?.id || "";
    }
    if (options.selectId && fonts.some((font) => font.id === options.selectId)) {
      selectedFontId = options.selectId;
    } else if (
      selectedFontId &&
      !fonts.some((font) => font.id === selectedFontId)
    ) {
      selectedFontId = null;
    }
    renderFontCards();
    renderFontDetail();
  } catch (error) {
    fontCardGrid.replaceChildren();
    fontLibraryEmpty.hidden = false;
    fontLibraryEmpty.querySelector("strong").textContent = "字体库读取失败";
    fontLibraryEmpty.querySelector("span").textContent = error.message;
  } finally {
    fontLibraryLoading.hidden = true;
  }
}

async function uploadFont(event) {
  event.preventDefault();
  const file = fontFile.files?.[0];
  if (!file || uploadFontButton.disabled) return;

  uploadBusy = true;
  uploadFontButton.disabled = true;
  uploadFontButton.textContent = "正在验证并上传…";
  showUploadError("");
  const data = new FormData();
  data.append("file", file);

  try {
    const response = await fetch("/api/fonts", {
      method: "POST",
      body: data,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "字体上传失败。");
    }
    fontUploadForm.reset();
    updateFileSummary(null);
    await loadFonts({ selectId: payload.id });
    announce(`${payload.name} 已加入字体库。`);
  } catch (error) {
    showUploadError(error.message);
  } finally {
    uploadBusy = false;
    uploadFontButton.textContent = "上传并加入字体库";
    updateFileSummary(fontFile.files?.[0] || null);
  }
}

async function saveFontName() {
  const font = fonts.find((item) => item.id === selectedFontId);
  if (!font || font.source !== "uploaded") return;
  const name = fontDetailName.value.trim();
  if (!name) {
    showDetailError("字体名称不能为空。");
    fontDetailName.focus();
    return;
  }

  saveFontNameButton.disabled = true;
  try {
    const response = await fetch(`/api/fonts/${encodeURIComponent(font.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "字体名称保存失败。");
    }
    Object.assign(font, payload);
    renderFontCards();
    renderFontDetail();
    announce(`字体已重命名为 ${payload.name}。`);
  } catch (error) {
    showDetailError(error.message);
  } finally {
    saveFontNameButton.disabled = false;
  }
}

async function deleteSelectedFont() {
  const font = fonts.find((item) => item.id === selectedFontId);
  if (!font || font.source !== "uploaded") return;
  const confirmed = await window.appConfirm({
    eyebrow: "删除字体",
    title: `删除“${font.name}”？`,
    message: "删除后将不能继续选择该字体，此操作不能撤销。",
    confirmText: "确认删除",
    tone: "danger",
  });
  if (!confirmed) return;

  deleteFontButton.disabled = true;
  try {
    const response = await fetch(`/api/fonts/${encodeURIComponent(font.id)}`, {
      method: "DELETE",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "字体删除失败。");
    }
    if (preferredFontId === font.id) {
      preferredFontId = "bold";
      try {
        window.localStorage.setItem("preferredArtFontId", preferredFontId);
      } catch {
        // The fallback still applies for the current page.
      }
    }
    selectedFontId = null;
    await loadFonts();
    announce(`${font.name} 已从字体库删除。`);
  } catch (error) {
    showDetailError(error.message);
  } finally {
    deleteFontButton.disabled = false;
  }
}

fontFile.addEventListener("change", () => {
  updateFileSummary(fontFile.files?.[0] || null);
});

fontDropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fontFile.click();
  }
});

for (const eventName of ["dragenter", "dragover"]) {
  fontDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    fontDropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  fontDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    fontDropZone.classList.remove("is-dragging");
  });
}

fontDropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fontFile.files = transfer.files;
  updateFileSummary(file);
});

fontUploadForm.addEventListener("submit", uploadFont);
fontPreviewText.addEventListener("input", updatePreviewStyles);
fontPreviewSize.addEventListener("input", updatePreviewStyles);
fontPreviewColor.addEventListener("input", updatePreviewStyles);
fontSearch.addEventListener("input", renderFontCards);
useFontButton.addEventListener("click", () => {
  if (selectedFontId) setPreferredFont(selectedFontId);
});
saveFontNameButton.addEventListener("click", saveFontName);
deleteFontButton.addEventListener("click", deleteSelectedFont);

for (const button of fontFilterButtons) {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.fontFilter;
    for (const item of fontFilterButtons) {
      item.setAttribute("aria-pressed", String(item === button));
    }
    renderFontCards();
  });
}

loadFonts();
