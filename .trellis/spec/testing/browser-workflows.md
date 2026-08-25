# 真实浏览器工作流测试

## Scenario：编辑器浏览器行为基线

### 1. Scope / Trigger

修改编辑器加载、保存、播放、时间线、工具切换、公共预览、历史 URL 或 compose 数据流时，必须运行 `tests/app/browser/`。静态字符串断言和 Node stub 不能替代真实浏览器，因为它们无法验证 document/media identity、浏览器存储、重定向和网络请求的组合行为。

### 2. Signatures

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
```

```python
browser_server(isolated_jobs) -> LiveServer
chromium_browser() -> playwright.sync_api.Browser
browser_session(chromium_browser, browser_server, tmp_path) -> BrowserSession
seeded_editor_job(sample_video) -> SeededEditorJob
```

### 3. Contracts

- `browser_server` 绑定 `127.0.0.1:0` 的同一个 socket，再交给 Uvicorn；禁止先探测端口、关闭 socket后重新绑定。
- 测试位于 `tests/app/browser/`，继承临时 `DATA_DIR` 和 job 清理；每个测试创建独立 browser context，不复用 storage/cache/service worker。
- 只访问测试的随机本地 origin。Iconify 使用确定性 stub，其他外部请求中止并在 teardown 报错。
- seeded job 只使用临时一秒媒体和本地图片；禁止读取真实 `data/jobs`、`data/history`、`.env` 或调用外部模型。
- 优先使用 Playwright Chromium，可回退本机 Chrome/Edge；全部缺失时明确失败，不得静默跳过。
- 未处理 `pageerror`、console error、本地失败请求和未允许的 HTTP 4xx/5xx 都使测试失败；诊断截图只写 `tmp_path`。
- 服务重启恢复是必须通过的真实浏览器契约；不得使用运行时或函数级 xfail 掩盖 404、无限轮询或重试失效。

### 4. Core Workflows

- 刷新恢复：执行可见删除操作，等待草稿保存，再核对 UI、cut draft JSON 和时间映射。
- 时间轴分割：连续播放头分割后核对 source anchor、structure revision 与不变的 `timingRevision`；覆盖精确删除、全删后无 marker/占位/焦点目标、内部 Store 结构保留、撤销/重做、刷新、键盘焦点、Store `cut:split-structure` 轨道、普通拖选取消及 375px。纯分割期间基础 video `srcWrites/loadCalls` 和 extractor 创建数都必须为 0。
- 时间轴缩略帧：除检查 data URL、绝对横向定位和剪后时间重映射外，还必须检查至少一个可见帧，且每个可见帧的实际高度大于 0 并等于缩略图层高度；禁止只断言图片已生成或 `left/width` 已设置。
- 工具切换：cut/art/pip 始终保持同一 document、基础 video、公共预览和公共时间线；隐藏 panel 必须 inert。
- 文字保存：暂停/播放两种状态都保持 document/video/ArtTool/PipTool identity、src、currentTime、play state 和 art/pip 时间；新文案通过顶层 Store 进入艺术字与 compose。
- 统一生成：用 `expect_response` 捕获真实 compose 响应，断言请求字段来自同一个 editor frame。
- 重启恢复：completed 工程清空进程内状态后仍从同一 URL 恢复文案/草稿/工具；running 工程变为 `interrupted`、停止轮询并提供同 job 重试。重试响应迟到时，已点击“重新选择视频”的页面不得被旧 job 重新渲染。
- 清理：context、Uvicorn 线程、socket 和临时媒体全部释放；连续运行结果一致。

### 5. Validation Matrix

| 条件 | 结果 |
| --- | --- |
| 保存/切换触发基础 video `src` setter 或 `load()` | 失败 |
| 公共 video/preview/timeline revision 不一致 | 失败 |
| 任意工具路径出现 iframe 或第二个基础 video | 失败 |
| 非本地请求、页面错误或未允许 HTTP 错误 | 失败并保留临时诊断 |
| 375px `scrollWidth > clientWidth` 或隐藏 panel 可聚焦 | 失败 |
| completed 服务重启恢复为 404 | 失败 |
| running 重启后仍轮询或无重试动作 | 失败 |
| 重选后迟到 retry/poll 响应恢复旧 UI | 失败 |

## Scenario：B4 单页唯一运行时与兼容入口

### 1. Scope / Trigger

修改 `EditorSuite`、ArtTool/PipTool 生命周期、工具链接、历史页面路由、模板库 handoff、旧资源清理或 compose 投影时，必须运行本场景。

### 2. Signatures

```javascript
window.EditorSuite.projectSnapshot() -> snapshot
window.EditorProjectStore.selectEditorFrame(snapshot) -> frame

#cutPreviewVideo[data-project-revision][data-timing-revision]
#editorSuitePreviewOverlay[data-project-revision][data-timing-revision]
#editorSuiteTimelineLayer[data-project-revision][data-timing-revision]
#editorArtPanelRoot
#editorPipPanelRoot
```

历史入口：

```text
/art-text?<query>             -> 307 /?<query without embedded/tool>&tool=art
/picture-in-picture?<query>   -> 307 /?<query without embedded/tool>&tool=pip
```

### 3. Contracts

- Store、MediaController、PreviewCompositor、TimelineController、ArtTool 和 PipTool 在顶层只创建一份；运行 DOM 的 iframe 数量恒为 0。
- 切换工具只修改 root 的 visible/inert 状态和 URL `tool` 参数，不导航 document、不调用 video `load()`、不重置播放状态。
- 公共 preview、timeline 和 compose 消费同一个 `selectEditorFrame(snapshot)`；compose 不读取工具 DOM、HTML 快照或私有 payload。
- `/art-text`、`/picture-in-picture` 保留有效 query、覆盖冲突 `tool`、删除 `embedded`；同名 `/api/transcriptions/...` 业务路由绝不重定向。
- 旧 `art-text.html/js`、`picture-in-picture.html/js` 必须物理缺失；内部链接直接进入顶层 URL，不先命中 307。
- 模板 query 由 EditorSuite 结构化解析并注入 ArtTool；ArtTool 等 font/template catalog 完成后只消费一次。
- ArtTool 固定包含“选择艺术字 / 艺术字设置 / AI 推荐”三个同级 tab。选择页拥有实例/整轨列表、自定义文字新增和视频文案一键添加；设置页只拥有当前 selection 的详情、空状态、模板及参数字段。无 selection 激活时进入选择页，已有 selection 时进入设置页；新增/选择/AI 确认进入设置页，只有艺术字 selection 从有变无时自动返回选择页。
- 模板控件使用 trigger + listbox，只显示模板名称和真实样式样例，不渲染说明。鼠标、外部点击及 Enter/Space/方向键/Home/End/Escape/Tab 都必须保持可预测的展开、选中、关闭和焦点状态；关闭后 option 不可聚焦。
- manual selection 只更新目标；transcript selection 按 `trackId` 一次更新全轨；无 selection 保存为后续 manual/全文轨道首选。
- ArtTool 中同 `trackId` 的 transcript cues 只显示一个带段数和整轨范围的“视频文案艺术字”入口，manual overlays 逐项显示。入口仍选择 `art:<cueId>`：优先当前同轨 cue，其次当前播放时间命中的 cue，最后最早 cue；render 和播放推进不能改写已有 selection。
- transcript 入口只显示共享样式/坐标控件，隐藏文字、方向、分行、时间、匹配时间和 manual 批量按钮。共享样式交互最多增加一个 revision，并精确保留 cue ID、文字、编辑/源时间、`characterTimings` 和 `timingRevision`；删除入口移除同轨全部 cues。
- 无效 template 整体忽略；无效 font/color/size 安全回退。缺失/空 `templateSize` 保持 null，不能被解析为 0 后 clamp 到 20。
- 模板 handoff 最多增加一个 revision，`timingRevision`、start/end 和 source anchors 不变。

### 4. Tests Required

- 历史 art/pip URL 307 后打开正确顶层 panel，保留 job/source、移除 embedded、iframe 为 0。
- 顶层 deep link 在桌面和 375px 都无额外导航、无横向溢出；hidden cut/art/pip panel inert 且不可 Tab 聚焦。
- manual 与两 cue transcript track 模板应用只增加一个 revision，整轨样式一致，range/timingRevision 不变。
- 真实 ArtTool 列表覆盖同轨多 cue 归并、manual 分项、播放时间代表 cue、同轨 selection 重绘稳定、整轨/manual 控件往返、完整字段快照、删除整轨后的 frame 一致性，以及仅有整轨时删除后的空选择文案复位。
- 无 selection 后新增 manual 和全文轨道使用首选模板；无效 template/font/color/size 覆盖安全回退。
- 文字保存与三工具切换保持 document/video/tool root identity，基础媒体 probe 的 `srcWrites/loadCalls` 都为 0。
- pointercancel 无 revision，pointerup 单 revision；undo/redo、preview/timeline/compose revision 保持一致。
- 公共文案轨只出现一次，效果层没有 `data-effect-kind="cut"`，但 Store frame 仍包含 `cut/art/pip`；art/pip clip 继续可选择和调整。
- 艺术字三个 tab 在桌面保持单行；tab 与 panel 通过 `id`、`aria-controls`、`aria-labelledby` 双向关联，方向键/Home/End 可循环切换，隐藏 panel 不可聚焦，切换仅重置 ArtTool 自身滚动。选择页完整覆盖新增、普通实例和文案整轨入口及自动进入设置；设置页覆盖空状态和 selection 从有变无的返回规则。模板 listbox 覆盖鼠标、外部点击、Enter/Space、方向键、Home/End、Escape、Tab、键盘确认、单 revision 和 375px 无溢出。画中画重绘只调整文案列表 `scrollTop`，选中项可见且外层 inspector 不移动。
- AI 建议请求携带实时剪后草稿，确认后的 overlay 同时具有 edited range 和 source anchors；重复短语命中离当前 overlay 最近的字符级范围。

### 5. Wrong vs Correct

```python
# Wrong: 只断言最终 panel 可见，未检查重定向、identity 或第二运行时。
page.goto(legacy_url)
assert page.locator("#editorPipPanelRoot").is_visible()

# Correct: 同时锁定 URL、唯一节点和不可变媒体。
page.goto(legacy_url)
assert page.url.endswith("&tool=pip")
assert page.locator("iframe").count() == 0
assert page.locator("#cutPreviewVideo").count() == 1
assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}
```

## Scenario：顶层画中画素材工作流

### 1. Scope / Trigger

修改 `EditorPipModel`、PipTool、pip draft、素材轮询、公共 pip preview/timeline/compose 或历史 pip URL 时适用。外部图片、视频和提示词模型请求必须全部 mock。

### 2. Contracts

- route mock 捕获 prompt/image/video POST payload；job GET mock 驱动 queued -> completed/failed，不使用真实模型、固定长等待或凭证。
- completed 素材自动启用；failed 素材保持可见但禁用且不进入 overlay。enable/disable、位置、时间和 width 都从可见控件操作。
- 175% 同时保留在 Store、草稿、公共预览和 compose；schema v2 非空未知 selection 使整份草稿失效，schema v1 只恢复 art。
- deactivate/job 切换后的迟到 create/poll response 为 no-op，不得增加 revision 或加入 asset。
- 历史 `/picture-in-picture` 重定向后使用同一个 PipTool 和基础 video；不再测试 feature flag fallback 或独立编辑页。

### 3. Tests Required

- 顶层 prompt + image + enable/disable + center + range + 175% + schema v2 reload + invalid selection rejection。
- video queued -> completed 和 queued -> failed，断言 asset/overlay/timingRevision。
- create response 忽略 abort 并迟到返回，断言 no-op。
- schema v1 art-only reload，pip 服务端 baseline 不变。
- 历史 pip URL、桌面/375px、iframe 为 0、无横向溢出。

### 4. Wrong vs Correct

```python
# Wrong: 真实调用模型并用 sleep 猜测视频生成完成。
page.get_by_role("button", name="生成画中画素材").click()
page.wait_for_timeout(5000)

# Correct: mock 状态机并等待 Store 的可观察终态。
page.route(video_create_url, fulfill_queued_video)
page.route(job_url, fulfill_completed_job)
page.wait_for_function(
    "id => EditorSuite.projectSnapshot().project.pip.overlays.some(x => x.assetId === id)",
    arg=asset_id,
)
```
