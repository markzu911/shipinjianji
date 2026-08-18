# 单页编辑器统一媒体预览与时间轴实施计划

## Step 1. Atomic Store Contracts

- [x] 扩展 `EditorProjectStore` 的完整 art/pip semantic model、atomic editor frame selector、PiP asset registry 和 timeline semantic actions。
- [x] `selectCompositionRequest` 显式把完整 UI 模型映射为原 API DTO，删除 preview-only 字段。
- [x] 保证 preview/timeline/compose 由同一显式 snapshot 派生，selector 不访问 DOM/全局 store。
- [x] 增加 Node tests：三类轨道、稳定 selection、clip range action、单 revision/timing revision、相同回声 no-op、asset lookup 和 atomic frame。

## Step 2. MediaController

- [x] 新增 `web/editor-media-controller.js`，提取并复用现有播放帧时钟 generation guard。
- [x] 实现 source key/no-op、显式 source change、cut time map、source/edited seek、frame/state subscription 和 destroy。
- [x] `editor-suite.js` 只创建一个 controller；`app.js` 使用它设置/清空源并订阅热路径，不再私有创建播放帧时钟。
- [x] 删除 suite 的独立 frame-sync rAF，iframe、PiP 子视频和抖音镜像订阅同一时钟。
- [x] 检查点：保存/切换不写 src、不 load，初次 job source 只 load 一次。

## Step 3. Semantic Tool Adapter

- [x] art/pip `tool-state` 在 legacy 字段外直接发布 `source`、带稳定 id 的完整 `overlays` 和 PiP `assets` registry。
- [x] Store authority 的父页只解析公开语义字段；删除父页 `generationPayload` 读取与 HTML cache authority。
- [x] 保留 origin/source/revision floor/ACK 与 feature flag fallback；相同 child echo 为 no-op。

## Step 4. PreviewCompositor

- [x] 新增 `web/editor-preview-compositor.js`，从 frame.preview 渲染 art/pip DOM。
- [x] 提取或等价复用艺术字纯 renderer；覆盖换行、模板、字体、描边、逐字动画与当前时间。
- [x] PiP 按 Store asset registry 创建 img/video，支持位置、无上限宽度语义、选择、拖动、八方向 resize 和子视频时间同步。
- [x] `editor-suite.js` 使用 compositor，停止消费/注入 `overlayHtml`；将空间操作作为语义 command同步 Store/iframe。
- [x] 检查点：公共预览与 compose overlay model/revision 一致。

## Step 5. TimelineController And History

- [x] 新增 `web/editor-timeline-controller.js`，从 frame.timeline 渲染 cut/art/pip 稳定 clip DOM。
- [x] 删除 suite 私有 `timelineStore` 和 `timelineHtml` renderer；提供 cut adapter 替换 `app.js` 私有 cut timeline store入口。
- [x] 复用 `EditorTimeline` pointer boundary，实现 selection/move/start/end/keyboard/pointer cancel。
- [x] 实现跨轨道事务 history、undo/redo、redo truncate、selection restore 和 editable focus bypass。
- [x] 通过语义 command适配现有 cut UI 与 art/pip iframe；确保一次提交一次 revision，回声 no-op。

## Step 6. Loading, Cache And Static Contracts

- [x] 在 `index.html` 按 timeline -> project store -> media -> preview -> timeline controller -> suite -> app 加载，并更新 `?v=`。
- [x] 将新资源加入服务端 no-cache 清单；不改 API/OpenAPI。
- [x] 更新静态契约：脚本顺序、唯一 controller、父页无 HTML/private payload 消费、消息安全、独立页面兼容。

## Step 7. Browser Workflows

- [x] 工具切换/文字保存/版本保存期间监控 `src` setter 与 `load()`，断言 video/iframe identity、time/play state。
- [x] 验证 semantic art/pip public preview、时间可见性、字符动画、PiP 图片/视频同步与 375px。
- [x] 验证顶层 timeline selection、move、start/end resize、keyboard、cancel、交错 undo/redo 和回声 revision。
- [x] 拦截 compose，比较 Store/frame/preview/timeline DOM revision 及 ranges/art/pip payload。
- [x] 保留现有重启 xfail 精确分支，外部请求继续全部阻断。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_project_store.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q tests/app
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
git diff --check
py -3 ./.trellis/scripts/task.py validate 08-18-single-page-editor-media-preview-timeline
```

## Review Gates

- [x] 一个基础 video、一个 MediaController、一个帧时钟、一个顶层 TimelineController。
- [x] Store authority 的 preview/timeline/compose 不读取 iframe HTML 或 `generationPayload`。
- [x] 热路径不运行 selector、timeline rebuild、全量 DOM query 或多重 rAF。
- [x] 预览与 compose 同 revision；PiP asset lookup 不改变公开 compose shape。
- [x] pointercancel 无 revision/history；pointerup 单 revision；undo/redo 跨轨道可逆。
- [x] origin/source/revision/ACK 安全检查未削弱。
- [x] 未迁移 inspector、未删除 iframe/旧 URL、未改后端公开契约、未触碰生产环境。

## Commit Boundaries

1. `feat(frontend): 统一编辑器媒体与语义预览`
2. `feat(frontend): 统一编辑器时间轴事务`
3. `test(frontend): 覆盖统一预览与时间轴`
4. `docs(trellis): 记录统一预览时间轴契约`

## Rollback Points

- 三个共享 controller 脚本可独立取消引用；B0 Store 不回退。
- semantic tool fields 与 legacy fields 同时发送，父页 consumer 可单独回退但不得恢复双 compose authority。
- preview 和 timeline 分两步接入；任一失败只回退对应 view，不撤销另一已验证 controller。
