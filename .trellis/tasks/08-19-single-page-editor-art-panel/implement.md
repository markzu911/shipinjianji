# 单页编辑器艺术字面板迁移实施计划

## Step 1. Shared Art Model And Renderer

- [x] 新增共享 `EditorArtModel`，提取 overlay 默认值/校验、稳定更新、全文轨道 cue/字符时间/source anchor 和模板 effect 归一化。
- [x] 新增共享 `EditorArtRenderer`，统一 PreviewCompositor、ArtTool 模板/AI 草稿和旧页面的文字格式/字符动画渲染。
- [x] 让现有 B1 compositor 和 legacy `art-text.js` 消费共享实现，先保持用户行为不变。
- [x] 增加 Node parity tests，锁定 11 类模板、横/竖排、换行、逐字动画与 compose 字段。

## Step 2. Store Commands And Recovery Adapter

- [x] 为新增/删除/批量/全文轨道建立一次性 art+timeline 语义 command，避免每 cue 多 revision。
- [x] 暴露 ArtTool 所需的窄 project/media/command services，不把 Store 或其他面板 DOM 设为全局可变对象。
- [x] 增加顶层版本化 editor draft recovery，ArtTool 不接触 storage；job/schema/server version 不兼容时安全忽略。
- [x] 覆盖非时间/时间 revision 矩阵、稳定 selection、恢复损坏/跨 job/旧 schema 和 text-only cue 时间保持。

## Step 3. Mountable ArtTool Inspector

- [x] 新增 `editor-art-tool.js`，实现 `mount/activate/deactivate/render/destroy` 与 root-scoped DOM。
- [x] 在 `index.html` 的 inspector host 增加设置、AI 推荐和保留文案 panel；不复制 video、公共时间轴或独立成片区域。
- [x] 迁移手动 overlay、样式/字体/排版/颜色/位置预设、坐标、时间、匹配文案、批量应用和删除确认。
- [x] 所有确认编辑基于最新 snapshot 形成一次 command；隐藏/销毁清理焦点、监听、timer、AbortController。

## Step 4. Transcript Track And AI Effects

- [x] 迁移保留文案编辑、选段添加、一键全文轨道、模板同步和布局重建，复用共享 model。
- [x] 迁移 AI 推荐请求/轮询/待确认预览/采用/取消/清空；待确认项保持局部瞬时状态。
- [x] 为 transcript/track/AI mutable effects 加 job/revision token 和 abort guard，迟到响应 no-op。
- [x] 顶层生成只调用统一 compose；错误、进度和取消复用 `ui-feedback.js`。

## Step 5. EditorSuite Integration And Feature Flag

- [x] EditorSuite 默认挂载 ArtTool，艺术字打开/切换不创建 iframe；PiP iframe 路径不变。
- [x] ArtTool 与公共 preview/timeline 双向同步稳定 id、selection、位置和范围；不发送 `postMessage`。
- [x] `__EDITOR_ART_PANEL_ENABLED__ === false` 时只运行旧 art iframe 路径；两条 authority 互斥。
- [x] 更新 URL/tool 激活、history navigation、保存状态和统一 compose，无 media `src/load()` 变更。

## Step 6. Legacy Page Adapter

- [x] `/art-text` 继续加载旧页面适配器，复用共享 model/renderer，保留独立页面现有功能。
- [x] legacy-only video/timeline/sessionStorage/embedded/message 代码不进入 ArtTool；标记为 B4 删除边界。
- [x] 保持 `/art-text.js` 旧公开资源、服务器路由与旧链接兼容。

## Step 7. Resource And Test Contracts

- [x] 更新主/艺术字页面脚本顺序与 `?v=`，把新增 JS 加入 `disable_frontend_cache`。
- [x] 更新静态契约，禁止 ArtTool 读取 storage、创建 timeline/video 或注册 message；锁定 feature flag 互斥。
- [x] 改写浏览器工作流从顶层 art panel 操作；新增 fallback iframe 与 standalone page 用例。
- [x] 覆盖桌面/375px、paused/playing、refresh draft、full-track、AI、timeline cancel/commit/undo/redo、compose 同 revision。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_project_store.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_art_text_api.py tests/app/test_art_text_track.py tests/app/test_art_text_rendering.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q tests/app
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
git diff --check
py -3 ./.trellis/scripts/task.py validate 08-19-single-page-editor-art-panel
```

## Review Gates

- [x] 顶层 art 路径没有 iframe、第二 video、第二 timeline store、第二播放时钟或 tool-owned project storage。
- [x] ArtTool 生命周期完整可撤销，重复 mount/destroy 无监听、timer、request 或 DOM 泄漏。
- [x] confirmed overlays 只在 Store；AI draft/local form 不可覆盖 Store。
- [x] 一次用户操作一次 revision；text/style 不改 timingRevision，range/full-track timing 一次性提交。
- [x] 共享 model/renderer 被 compositor、ArtTool 与 legacy adapter 复用，没有第三套格式/时间算法。
- [x] 公共 preview/timeline/compose 同 frame revision，媒体 identity 和播放状态保持。
- [x] feature flag fallback、独立 `/art-text`、PiP iframe、origin/source/revision 安全契约未削弱。
- [x] 未改后端公开 API/schema、未进入 B3/B4、未触碰生产环境。

## Suggested Commit Boundaries

1. `refactor(frontend): 提取共享艺术字模型与渲染器`
2. `feat(frontend): 挂载顶层艺术字编辑面板`
3. `feat(frontend): 接入艺术字 effects 与草稿恢复`
4. `test(frontend): 覆盖顶层艺术字工作流`
5. `docs(trellis): 记录艺术字模块迁移契约`

## Rollback Points

- 共享 model/renderer 可保留，不随 UI 回滚。
- 顶层 ArtTool 可通过启动前设置 `__EDITOR_ART_PANEL_ENABLED__ = false` 回退到 B1 art iframe。
- 旧页面/消息适配器在 B2 不删除；任何回滚不得恢复 iframe HTML/private payload 为 preview/compose authority。
