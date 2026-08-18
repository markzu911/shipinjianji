# 单页编辑器状态核心实施计划

## Step 1. Store Core And Pure Tests

- [ ] 新增 `web/editor-project-store.js`，实现 state 规范化、不可变快照、subscribe/destroy、语义 action、revision/timingRevision 与 effect scope token。
- [ ] 实现 timing signature，只比较 cut/art/pip 的结构时间与 source anchor。
- [ ] 实现六个纯 selector，并让 timeline selector 复用 `EditorTimeline.normalizeDocument()`。
- [ ] 增加 Node 行为测试：不可变、revision 矩阵、迟到 effect、同 job hydrate 保留本地工具状态、原子 compose selector。
- [ ] 检查点：新脚本尚未接入业务时，现有浏览器基线行为完全不变。

## Step 2. Script Loading And Top-level Authority

- [ ] 在 `web/index.html` 中按 `timeline-model -> editor-project-store -> editor-suite -> app` 加载，并同步静态资源版本/缓存契约。
- [ ] 仅在确有共享常量消费时更新 art/pip 页面脚本顺序；不要为了对称性无条件加载 store。
- [ ] `editor-suite.js` 创建唯一 store，增加启动时固定的 feature flag 与只读/语义适配 API。
- [ ] 将首次 job hydrate、cut draft 更新和 active tool 更新接入 store；legacy authority 在 enabled 路径停止写 compose。
- [ ] 检查点：切换 cut/art/pip 不导航、不重建 iframe，现有 HTML mirror 仍工作。

## Step 3. Tool Compatibility Bridge

- [ ] 将 art/pip `tool-state` 的语义字段 dispatch 到 store；HTML/timeline 快照只留在 bridge cache。
- [ ] store projection 消息附带 `revision`、`timingRevision` 与 `changeKind`，保持旧消息字段兼容。
- [ ] art/pip 记录已应用 revision 并拒绝旧消息；保留 parent/source/origin 校验。
- [ ] 为 `transcript-text` 增加独立处理：art 仅改 cue 文本，pip 仅改 transcript 标签，两者均不进入 retime/rematch。
- [ ] 用语义签名/revision 阻止 parent subscriber 与 child `tool-state` 回声循环。
- [ ] 检查点：更新 art/pip 非时间字段不增加 `timingRevision`；拖动/缩放时间范围会增加。

## Step 4. Guarded Text Save

- [ ] `saveSegmentText()` 在请求前创建 `transcript-save` effect token，保留现有 PUT。
- [ ] PUT 成功后执行一次完整 job GET，但只规范化 transcript/editable/art cue text 投影。
- [ ] 用 `applyEffect` 提交 `transcriptTextChanged`；迟到或 timing 冲突时拒绝完整响应，并按当前 timing revision 重取只读文字投影。
- [ ] 删除 500ms reload 和“正在刷新页面”提示；不得重新设置 video src、调用 `load()` 或走 `ensureToolFrame()` 换源。
- [ ] 检查点：非零时间播放/暂停两种状态分别编辑文案，视频、document 和 iframe identity 保持。

## Step 5. Atomic Compose And Timeline Projection

- [ ] 将 `previewCompositionState()`/`compositionRequest()` 的 project 数据来源改为一个 store snapshot 的 selector 输出。
- [ ] suite timeline projection 改为消费 `selectTimelineDocument(snapshot)`；B0 可继续用旧 DOM renderer，但不能保留第二个 compose authority。
- [ ] 保持 `/compose` 公开 payload 字段和生成流程不变。
- [ ] 检查点：同一测试快照内 ranges、art、pip 和 revision 对齐，迟到 tool-state 不改变 compose。

## Step 6. Contract And Browser Coverage

- [ ] 扩展 `tests/app/test_frontend_contracts.py`：脚本顺序/版本、无 text-save reload、消息版本字段、origin/source 校验、compose selector authority。
- [ ] 扩展 `tests/app/browser/test_editor_workflows.py`：非零播放位置编辑文案，断言 document/video/src/time/play state/iframe identity 不变。
- [ ] 浏览器用例保存 art/pip 更新前后的所有时间字段，断言 art 文本更新而时间精确相等，pip 时间精确相等。
- [ ] 拦截或检查 compose 请求，确认新文字与 cut/art/pip 来自同一 store revision。
- [ ] 保留并运行 `tests/app/test_cut_draft.py` 的服务端稳定 cue 时间测试。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests/app/test_frontend_contracts.py -q
.\.venv\Scripts\python.exe -m pytest tests/app/test_cut_draft.py -q
.\.venv\Scripts\python.exe -m pytest tests/app/browser/test_editor_workflows.py -q
.\.venv\Scripts\python.exe -m pytest tests/app -q
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
git diff --check
```

## Review Gates

- [ ] Store 内没有 `overlayHtml`、`timelineHtml`、DOM node 或私有 `generationPayload`。
- [ ] enabled 路径只有一个 project/compose authority；disabled 路径不同时运行 guarded store 写入。
- [ ] 纯文字 action 不改变 `timingRevision` 或任何 art/pip 时间字段。
- [ ] 迟到 effect 不发布 subscriber 通知，也不覆盖当前快照。
- [ ] parent 与两个 iframe 的 origin/source 校验仍在。
- [ ] 文案保存不导航、不重建 video/iframe、不重置播放。
- [ ] B0 没有提前引入 MediaController、最终 compositor 或 iframe UI 迁移。

## Rollback Points

- Store core 和纯测试可通过移除脚本引用独立回滚。
- 接入后可在页面启动前设置 `window.__EDITOR_PROJECT_STORE_ENABLED__ = false` 回到 legacy authority。
- 如果 guarded text path 失败，只回退该适配步骤；不得在同一会话同时执行 reload 与新 action path。
- compose selector 如有不兼容，只能回退到由同一 store snapshot 供数的兼容 adapter，不能恢复 iframe 私有 payload 为第二权威。

## Deferred Follow-ups

- B1：唯一 MediaController、PreviewCompositor、TimelineController。
- B2/B3：art/pip 顶层可挂载模块。
- B4：删除 iframe/postMessage/HTML 快照和旧独立页面运行时。
- 后端后续可让文字 PUT 返回带 server revision 的规范化 project snapshot，从而删除额外 GET。
