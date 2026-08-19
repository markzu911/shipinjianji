# 单页编辑器画中画面板迁移实施计划

## Step 1. Shared Pip Model And Backend Size Contract

- [x] 新增 `editor-pip-model.js`，提取 asset/overlay/source/range/timeline/compose validation 纯逻辑和稳定 id。
- [x] 让 EditorProjectStore、PreviewCompositor 和 legacy adapter 优先消费共享模型，保持 standalone 行为。
- [x] 去掉前端 55%/舞台剩余空间最大宽度和后端 65% 最大宽度，仅保留 finite + minimum validation。
- [x] 修正 FFmpeg 大于主画面的中心定位/裁切公式，并增加 normalize/真实小样片回归。

## Step 2. Store Commands And Draft Schema V2

- [x] 建立 `replacePip`、`selectPip`、`setPipRange` 顶层 commands；每次从最新 snapshot 一次提交 pip+timeline。
- [x] 将 assets 与 enabled overlays 分离，覆盖 pending/completed/failed、enable/disable、selection 和 revision 矩阵。
- [x] 扩展 `PROJECT_DRAFT_RESTORED` 为 art+pip 原子恢复，写 schema v2 且兼容 schema v1 art-only。
- [x] 草稿不保存 asset registry；恢复时校验当前 job/source/asset id、范围、位置、finite width、重复 id 和 selection。

## Step 3. Mountable PipTool Inspector

- [x] 新增 `editor-pip-tool.js`，实现 `mount/activate/deactivate/render/destroy` 和 root-scoped DOM。
- [x] 在 `index.html` inspector host 增加 `#editorPipPanelRoot`，迁移文案选择、素材类型、模式、画幅、时间、提示词和素材列表控件。
- [x] 迁移素材选择、启用/禁用、位置预设、无 max 百分比 number input、错误/进度反馈；不复制 video、timeline 或最终成片 UI。
- [x] 所有确认修改经一次 command，隐藏/销毁清理焦点、listener、timer、AbortController 和本地 draft。

## Step 4. Prompt, Asset Generation And Polling Effects

- [x] 迁移 AI 提示词请求与 image/video asset 创建，复用 `services.api.request` 和当前 pip source/time anchors。
- [x] 图片/ready video 原子加入 assets+overlays；pending video 只加入 assets，completed 后稳定 id 自动启用一次，failed 保留错误且禁用。
- [x] 每个 mutable effect 加 job/source/token/lifecycle/abort guard；轮询仅在 active + queued/processing 时继续。
- [x] 网络结果按最新 Store snapshot merge，迟到结果不得覆盖位置、尺寸、时间、启用状态或另一 job。

## Step 5. EditorSuite Integration And Feature Flag

- [x] 新增 PipTool services 与 `topLevelPipEnabled`，默认 mount 顶层 panel 且不创建 pip iframe。
- [x] 泛化当前 art-only frame/bridge 条件，让 art/pip 各自按 flag 互斥运行并覆盖四种组合。
- [x] `renderEditorFrame`、工具切换、URL/history、selection、public preview/timeline/compose 与 PipTool 双向同步。
- [x] 预览拖动/缩放和公共 timeline commit 只写 Store；不向启用的顶层 PipTool 发送 postMessage。

## Step 6. Legacy Adapter And Resource Contracts

- [x] `/picture-in-picture` 继续可独立运行，加载共享 Pip model 并保留 legacy video/timeline/storage/message 适配器。
- [x] `__EDITOR_PIP_PANEL_ENABLED__ === false` 时完整保留 B1 iframe/revision floor/ACK/message fallback。
- [x] 更新普通脚本顺序、`?v=`、no-cache 清单、静态资源与 standalone 契约。
- [x] 不删除旧 URL、HTML、JS、`embedded=1` 或 message bridge；留给 B4。

## Step 7. Automated And Browser Verification

- [x] 新增/扩展 Pip model、Store、PipTool、frontend contracts、backend pip、compose tests。
- [x] 浏览器素材生成全部 route/mock；覆盖 prompt、image、video polling、failure、enable/disable、selection、position、175% width、range 和 compose。
- [x] 覆盖 v1/v2 draft、paused/playing identity、tool switch、fallback iframe、standalone、desktop/375px 和无横向溢出。
- [x] 完整 browser/app、JS syntax、diff、Trellis validation 全部通过，已知 restart recovery 保持唯一 xfail。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_pip_model.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_project_store.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_picture_in_picture.py tests/app/test_composition.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q tests/app
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
git diff --check
py -3 ./.trellis/scripts/task.py validate 08-19-single-page-editor-pip-panel
```

若 PipTool DOM 行为测试并入现有文件而不新增 `test_editor_pip_model.py`，第一条命令替换为实际 focused test path，不得以缺文件跳过对应 Node 契约。

## Review Gates

- [x] 顶层 pip 路径没有 iframe、第二个 video、第二个 timeline Store、第二条播放帧时钟、缩略图提取或 tool-owned storage。
- [x] PipTool 生命周期完整可撤销，重复 mount/destroy 无 listener/timer/request/DOM 泄漏。
- [x] assets 与 enabled overlays 语义分离，稳定 id 串联 panel/preview/timeline/compose。
- [x] 一次用户操作一次 revision；asset status/position/width 不改 timing，enable/range 只改一次 timing。
- [x] size control、pointer resize、Store、draft、preview、backend normalize 和 FFmpeg 均无任意最大宽度且中心裁切一致。
- [x] prompt/asset/poll effects 在 deactivate/job switch/destroy 后不产生迟到写入，外部模型浏览器测试均 mock。
- [x] schema v2 原子恢复 art+pip；v1 art-only 兼容；未知 asset 或损坏草稿不覆盖 Store。
- [x] 公共 preview/timeline/compose 同 frame revision，art+pip 组合、媒体 identity 和播放状态保持。
- [x] fallback iframe、standalone page、旧 API/schema、origin/source/revision 安全契约未削弱。
- [x] 未进入 B4、未做无关重构、未改生产环境。

## Suggested Commit Boundaries

1. `refactor(frontend): 提取共享画中画模型`
2. `feat(frontend): 挂载顶层画中画编辑面板`
3. `fix(composition): 支持画中画无上限中心缩放`
4. `test(frontend): 覆盖顶层画中画工作流`
5. `docs(trellis): 记录画中画模块迁移契约`

## Rollback Points

- shared model 和后端中心裁切修复可保留，不随 panel 回滚。
- 顶层 panel 回归时，在 EditorSuite 初始化前设置 `__EDITOR_PIP_PANEL_ENABLED__ = false` 并 reload，恢复 B1 iframe。
- legacy page/message adapter 在 B3 不删除；回滚不得恢复私有 HTML/generation payload 为公共 preview/compose authority。
