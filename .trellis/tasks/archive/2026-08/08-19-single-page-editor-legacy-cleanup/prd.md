# 单页编辑器旧运行时清理

## Goal

在 B0-B3 已完成顶层 Store、媒体、预览、时间轴、艺术字和画中画面板迁移的基础上，删除迁移期保留的 iframe、跨页面消息桥和独立工具页面，使文字剪辑、艺术字与画中画只运行在 `index.html` 这一份编辑器文档中，同时保留历史页面链接和模板库跳转的用户可达性。

## Background

- B2/B3 已让默认艺术字与画中画路径直接挂载 `ArtTool`、`PipTool`，并共享 `EditorProjectStore`、`MediaController`、`PreviewCompositor` 与 `TimelineController`。
- `editor-suite.js` 仍保留 `embedded=1`、iframe lifecycle、revision floor/ACK、`window.message`、legacy timeline/tool state 和三组 fallback feature flag；这些分支会继续形成双运行时维护成本。
- `web/art-text.html/js` 与 `web/picture-in-picture.html/js` 合计约 365 KB，仍各自拥有 video、timeline、storage、播放与生成逻辑，但默认产品路径已不再需要它们。
- 模板库仍跳转 `/art-text` 并携带 `template`、`templateColor`、`templateStroke`、`templateFont`、`templateSize`；删除旧艺术字页面前必须把这条能力迁到顶层 `ArtTool`。
- 生产环境不在本任务范围；开发环境继续使用 `http://127.0.0.1:8001/`。

## Requirements

### R1. 唯一编辑器运行时

- 文字剪辑、艺术字与画中画只能在顶层 `index.html` 中运行，且始终使用同一 Store、基础 video、播放帧时钟、公共预览和公共时间轴。
- 删除工具 iframe 创建、刷新、选择、播放同步和销毁生命周期；删除 `embedded=1`、跨页 `postMessage`、`window.message` listener、revision floor/ACK 和 legacy tool-state/job-state projection。
- 删除 legacy timeline/tool state、mirrored preview/timeline、私有 `generationPayload`、`timelineHtml` 与 `overlayHtml` 兼容路径。
- 删除 `__EDITOR_PROJECT_STORE_ENABLED__`、`__EDITOR_ART_PANEL_ENABLED__`、`__EDITOR_PIP_PANEL_ENABLED__` fallback 选择；顶层 Store + ArtTool + PipTool 成为唯一受支持路径。

### R2. 历史页面 URL 兼容

- `GET /art-text` 重定向到 `/?tool=art`，`GET /picture-in-picture` 重定向到 `/?tool=pip`。
- 重定向保留有效的 `job`、`source` 和艺术字模板参数，覆盖冲突的 `tool`，并移除只属于旧 iframe 的 `embedded`。
- 历史链接携带 `job=<id>` 时必须打开同一项目的对应顶层面板；不得先加载旧页面、创建 iframe 或产生第二次客户端导航。
- `/api/transcriptions/.../art-text`、`/api/transcriptions/.../picture-in-picture` 及相关素材、预览、compose API 保持原路径和行为，不能因页面路由清理而改名或重定向。

### R3. 模板库入口兼容

- 模板库的“返回编辑器”和“使用模板”都导航到 `/?job=<id>&tool=art`，并继续携带 `source` 与完整模板选择参数。
- URL 解析由顶层导航适配器负责，并把结构化的一次性模板请求注入 `ArtTool`；root-scoped `ArtTool` 不直接读取 `window.location`。
- `ArtTool` 在字体和模板 catalog 加载完成后校验模板 id、颜色、描边色、字体和字号，再应用请求；无效字段按现有 catalog/default 规则安全回退。
- 有选中艺术字时保持旧页面语义：手动艺术字只修改目标，全文轨道选择修改同一轨道；没有选中项时保存为本次顶层工具后续创建/全文轨道使用的首选模板。
- 同一 URL 请求只消费一次；应用一次模板只产生一次 Store transaction，不改变现有时间范围或 `timingRevision`。

### R4. 旧资源与内部链接清理

- 删除 `web/art-text.html`、`web/art-text.js`、`web/picture-in-picture.html`、`web/picture-in-picture.js`。
- 更新 `app.js`、`editor-suite.js` 与模板库中的旧页面链接，统一生成顶层 `/?job=<id>&tool=art|pip` 深链。
- 删除 no-cache 清单、HTML 版本引用、静态契约、浏览器 fallback/standalone 用例和 specs 中只服务于迁移期旧页面的内容。
- 不删除仍有现实用途的同文档事件与 storage key：`editor-suite:refresh`、`editor-suite:transcript-updated`、`editor-suite:job-state` CustomEvent 和 `editor-suite:project-draft:<jobId>` 可按当前职责保留。

### R5. 行为与可访问性保持

- 从文字、艺术字、画中画互相切换只更新当前面板和 URL `tool` 参数，不更换 document、不创建 iframe、不调用基础 video `load()`、不重置 `src/currentSrc/currentTime` 或播放状态。
- 选择、预览图层、公共时间轴、撤销/重做、草稿恢复和 compose 始终消费同一 editor frame revision。
- 直接访问历史 URL、顶层深链和模板库返回后，桌面与 375px 都必须显示正确面板，无横向溢出，隐藏面板保持 inert 且不可 Tab 聚焦。

## Acceptance Criteria

- [ ] AC1: 默认编辑器源码和运行 DOM 均不存在工具 iframe、`embedded=1`、跨页 `postMessage`/`message` listener、bridge ACK/revision floor、legacy timeline 或 mirrored preview/timeline 路径。
- [ ] AC2: 顶层 Store、ArtTool 与 PipTool 不再受 fallback feature flag 控制；三个工具共享唯一 document、video、播放时钟、预览与时间轴。
- [ ] AC3: `/art-text?job=<id>` 和 `/picture-in-picture?job=<id>` 分别重定向到同一 job 的 `tool=art|pip` 顶层 URL，保留所需 query、移除 `embedded`；所有同名 API 路由保持非重定向且测试通过。
- [ ] AC4: 模板库返回与使用模板进入顶层艺术字面板；合法模板/颜色/描边/字体/字号在 catalog 后一次应用到正确选择，无选择时成为后续首选，无效参数安全回退且不改时间。
- [ ] AC5: 四个旧 HTML/JS 文件物理删除，服务器 no-cache 和页面资源契约不再引用它们，仓库内不存在指向旧工具页面的内部编辑链接。
- [ ] AC6: 文字修改、art/pip 编辑、公共拖动/缩放/时间线、刷新恢复、撤销/重做和统一 compose 仍从同一 frame 工作；工具切换期间 document/video identity、时间与播放状态保持且 `load()` 调用为 0。
- [ ] AC7: 桌面与 375px 覆盖顶层深链、历史重定向、模板选择和三工具切换；无 iframe、无额外导航、无横向溢出、隐藏面板不可聚焦。
- [ ] AC8: focused、静态、Node、browser 和完整 `tests/app` 全部通过；服务重启恢复仍是唯一预期 xfail；生产环境未改动。

## Out Of Scope

- 不修改艺术字、画中画、素材生成或 compose 的公开 API schema、模型选择和服务端媒体算法。
- 不处理 Phase A 的服务重启 job 恢复，不开始 Phase C 后端领域拆分或 Phase E CSS/性能重构。
- 不删除字体/模板库、设置页等独立管理页面，也不重命名仍在使用的同文档 `editor-suite:*` CustomEvent 或项目草稿 key。
- 不保留运行时 feature flag 回滚；B4 的回滚单位是独立提交，而不是在生产代码中继续维护第二套编辑器。

## Risks And Deferred Items

- 删除约 9,800 行旧页面代码会让字符串断言大量失效，测试必须改为验证“资源缺失 + 历史 URL 重定向 + 顶层行为”，不能简单删除覆盖。
- `/art-text` 同时是历史页面名和 API 路径片段，清理时必须以完整服务器路由和文件路径为边界，避免误删 `/api/transcriptions/.../art-text`。
- 模板 query 是旧页面最后一个未迁移入口；若先删资源再补顶层消费，会出现模板库看似成功但选择丢失的回归。
