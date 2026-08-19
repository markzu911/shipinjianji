# 当前艺术字轨道契约调研

## 结论

用户看到多条“文案艺术字”不是底层缺少轨道模型，而是 ArtTool 列表仍逐 overlay 渲染。现有 model 和公共时间轴已经按 `trackId` 具备整轨样式更新、整轨删除和一轨多 cue 的能力，所以最小且一致的修复是增加 ArtTool 轨道级 view model 与控件模式，不改数据 schema。

## Source Evidence

- `web/editor-art-tool.js:154-158`：选择从公共 timeline 的 `art:<cueId>` 解析为具体 overlay。
- `web/editor-art-tool.js:283-300`：列表逐个遍历 `art().overlays`，直接造成全文 cues 分别显示。
- `web/editor-art-tool.js:311-324`：同一套详细设置无条件展示文字、时间等 cue 级字段。
- `web/editor-art-tool.js:609-657`：生成全文轨道时移除全部旧 transcript overlays、保留 manual overlays，并选中新轨首 cue。
- `web/editor-art-tool.js:788-807`：删除入口已经依据 transcript 身份提示并调用 model 删除。
- `web/editor-art-model.js:673-710`：transcript selection 的共享样式按 `trackId` 更新，cue 字段只作用于所选 cue。
- `web/editor-art-model.js:732-742`：删除 transcript overlay 时按 `trackId` 移除全轨。
- `web/editor-art-model.js:745-780`：公共时间轴已经按 `art:transcript:<trackId>` 分组，并保留各 cue clips。
- `tests/app/test_editor_art_model.py:88-129`：已有共享样式不改变 ID/时间/source anchors 和单轨多 clip 的基础回归。
- `tests/app/browser/test_editor_workflows.py:2108-2160`：已有真实浏览器模板 handoff 覆盖同轨两 cue、单 revision 和 timingRevision 不变，可扩展为面板交互回归。

## Existing Specifications

- `.trellis/spec/frontend/architecture-and-state.md`：ArtTool 只能作为同一顶层 Store/frame 的 inspector；选中 transcript cue 时按 `trackId` 更新全轨。
- `.trellis/spec/frontend/ui-and-interactions.md`：保持控件可访问性、响应式和最小操作目标。
- `.trellis/spec/testing/browser-workflows.md`：真实浏览器需验证单 document/video、同 revision、manual/track 模板行为和 375px 无溢出。
- `.trellis/spec/guides/code-reuse-thinking-guide.md`：复用现有 ArtTool、时间轴和 Store owner，不新增重复时间映射或项目状态。

## Recommended Change Surface

- 必改：`web/editor-art-tool.js`、`web/index.html`、`tests/app/test_frontend_contracts.py`、`tests/app/browser/test_editor_workflows.py`。
- 按需：`web/styles.css`、`tests/app/test_editor_art_model.py`。
- 不应改：后端 API、持久化 schema、EditorProjectStore、PreviewCompositor、TimelineController 和 compose DTO，除非测试证明现有契约缺口。
