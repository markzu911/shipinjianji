# 真实浏览器工作流测试

## Scenario：编辑器跨页面行为基线

### 1. Scope / Trigger

修改编辑器加载、保存、播放、时间轴、iframe 工具切换、公共预览或 compose 数据流时，必须运行 `tests/app/browser/` 的真实浏览器工作流。静态 HTML/JS 字符串断言和 Node DOM stub 不能替代这组测试，因为它们无法验证导航、媒体状态、浏览器存储和网络请求之间的组合行为。

### 2. Signatures

依赖与运行命令：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
```

核心 pytest fixture：

```python
browser_server(isolated_jobs) -> LiveServer
chromium_browser() -> playwright.sync_api.Browser
browser_session(chromium_browser, browser_server, tmp_path) -> BrowserSession
seeded_editor_job(sample_video) -> SeededEditorJob
```

### 3. Contracts

- `browser_server` 必须绑定 `127.0.0.1:0` 的同一个 socket，再把该 socket 交给 Uvicorn；禁止先探测端口、关闭 socket 后重新绑定。
- 浏览器测试必须位于 `tests/app/browser/`，继承 `tests/app/conftest.py` 的临时 `DATA_DIR` 和全局 job 清理，不能把这些 fixture 上移到 `tests/conftest.py`。
- 每个测试创建独立 browser context；不得复用 localStorage、sessionStorage、Cache Storage 或 service worker 状态。
- 只允许访问该测试的随机本地 origin。Iconify 脚本由确定性本地 stub 响应；其他外部请求必须中止并在 teardown 报错。
- seeded job 只使用临时一秒媒体和本地图片；禁止读取真实 `data/jobs`、`data/history`、`.env` 或调用 ASR/文本/图片/视频模型。
- 优先启动 Playwright 自带 Chromium；缺失时可回退到本机 Chrome/Edge。两者都不存在时必须失败并显示 `python -m playwright install chromium`，不得静默跳过。
- 未处理 `pageerror`、console error、本地失败请求和未允许的 HTTP 4xx/5xx 必须使测试失败。诊断截图只能写 `tmp_path`。
- 已知缺口只能在观察到精确的预期响应后调用 `pytest.xfail()`；禁止用函数级 xfail marker 包住整个工作流。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| Python 未安装 Playwright | 测试失败并提示安装 `requirements.txt` |
| Playwright Chromium 缺失，本机有 Chrome/Edge | 使用本机浏览器继续真实验证 |
| 所有 Chromium 浏览器均缺失 | 测试失败并提示安装 Chromium |
| 临时服务健康检查超时 | 关闭 socket/线程并抛出明确启动错误 |
| 请求访问非本地 origin 且不是 Iconify stub | 中止请求并在 teardown 报错 |
| 页面出现未允许异常、console error、4xx/5xx | 保存临时诊断并使测试失败 |
| 重启后 job API 返回精确的已知 404/detail | 运行时 `pytest.xfail()`，指向 Phase A |
| 重启后返回其他错误或浏览器先失败 | 正常失败，不得被 xfail 掩盖 |

### 5. Good / Base / Bad Cases

- Good：修改 iframe/统一状态代码后，刷新恢复、三工具切换和 compose 载荷测试全部通过。
- Base：当前服务重启后返回“转写任务不存在或服务已重启”，仅该精确分支 xfail，其他三个工作流仍通过。
- Bad：测试连接开发环境 8001、使用真实用户 job、放行外部 AI 请求、通过固定等待时间猜测 compose 已提交，或给整个重启用例添加 marker xfail。

### 6. Tests Required

- 刷新恢复：从可见删除按钮执行操作，等待“剪辑草稿已保存”，刷新后核对 UI 与 cut draft JSON 的文字范围和时间映射。
- 工具切换：在文字/艺术字/画中画之间切换，核对页面未导航、选中项、公共预览图层和基础视频时间保持。
- 统一生成：通过 `expect_response` 等待实际 compose 响应，断言 cut ranges、art overlays、pip overlays 及来源字段来自当前 UI。
- Store/iframe revision：从真实 iframe 发送低于父页接收下限的 `tool-state`，确认 Store 与 compose 不变；随后连续执行两次子页本地非时间编辑，确认每次只增加一个 revision、ACK 后下一次仍可提交且 `timingRevision` 不变。
- 重启恢复：先访问 job API；只在精确已知 404 时 xfail，否则继续验证同一 URL 可编辑。
- 清理：每次运行后浏览器 context、Uvicorn 线程、socket 和临时媒体全部释放；连续运行两次结果一致。

### 7. Wrong vs Correct

#### Wrong

```python
port = find_free_port()  # socket 已关闭，端口可被其他进程抢占
server.start(port)

@pytest.mark.xfail(reason="服务尚未恢复 job")
def test_restart(page):
    page.reload()  # 任意 JS/网络错误都会被误记为已知 xfail
    page.wait_for_timeout(500)
```

#### Correct

```python
server_socket.bind(("127.0.0.1", 0))
server.run(sockets=[server_socket])

response = page.request.get(job_url)
if response.status == 404:
    assert response.json()["detail"] == "转写任务不存在或服务已重启。"
    pytest.xfail("Phase A：服务重启后恢复 job")

with page.expect_response(compose_url) as response_info:
    generate_button.click()
assert response_info.value.status == 202
```

## Scenario：B1 单页统一媒体、预览与时间轴

### 1. Scope / Trigger

修改 `EditorProjectStore.selectEditorFrame`、MediaController、PreviewCompositor、TimelineController、art/pip 语义消息或 compose 映射时，除 Node/静态测试外必须运行本场景。测试必须从用户可见的顶层编辑器操作，不得把 iframe 私有 DOM 或 payload 当作正确结果。

### 2. Signatures

```javascript
window.EditorSuite.projectSnapshot() -> snapshot
window.EditorProjectStore.selectEditorFrame(snapshot) -> frame

// Public DOM observability
#cutPreviewVideo[data-project-revision][data-timing-revision]
#editorSuitePreviewOverlay[data-project-revision][data-timing-revision]
#editorSuiteTimelineLayer[data-project-revision][data-timing-revision]
```

实际 selector 以页面当前 DOM id 为准，但必须同时定位唯一公共视频、公共 overlay 根和公共时间轴根，并比较三者 revision。

### 3. Contracts

- 在非零播放时间分别覆盖 paused/playing：依次切换 cut/art/pip、修改文案和保存版本，断言顶层 document、video node、`src/currentSrc`、`currentTime` 和播放状态按操作语义保持，并监控期间没有 `load()`。
- 通过公共预览和公共时间轴执行选择、拖动、两端 resize、键盘微调、pointercancel、undo/redo；不能直接调用 Store action 代替关键用户交互。
- pointercancel 前后 revision/timingRevision/history 与权威范围一致；pointerup 只增加一个 project revision，时间变化只增加一个 timingRevision。
- 在真实 iframe 发送迟到 revision 和等价回声，断言迟到状态被拒绝、等价回声/ACK 为 no-op、inactive 工具不改变全局 selection。
- 拦截真实 compose 请求，比较请求体与同一时刻原子 frame；cut ranges、art overlays、pip overlays 及 source 字段必须相同，且三个公共 DOM 根 revision 等于 frame revision。
- 375px 下只能有一个可交互公共时间轴，不横向溢出；art/pip iframe identity 和独立页面 URL 保持兼容。

### 4. Validation & Error Matrix

| 观察结果 | 测试结果 |
| --- | --- |
| 保存/切换触发 `src` setter 或 `load()` | 失败并报告触发操作、调用计数和媒体状态 |
| 三个公共 DOM revision 不一致 | 失败并输出 Store/frame/DOM revision |
| pointercancel 增加 revision/history 或残留临时范围 | 失败 |
| pointerup 增加超过一个 revision 或 echo 再增加 revision | 失败 |
| compose 字段与 frame 不一致 | 失败并输出字段级差异 |
| 375px 出现第二个可交互时间轴或 `scrollWidth > clientWidth` | 失败 |
| 浏览器/页面错误或非本地请求 | 按基础场景失败，不得降级为 xfail |

### 5. Good / Base / Bad Cases

- Good：art clip 拖动后 Store 从 revision 20 到 21，child 应用 `set-range` 后 `commit`，回声/ACK 仍为 21；preview、timeline 和 compose 都读取 21 的相同范围。
- Base：pointercancel 后视觉范围恢复，revision/history 不变；随后正常拖动仍能提交一次且 undo/redo 可逆。
- Bad：只比较最终像素位置、不核对 revision/请求体，或通过固定等待猜测 iframe 已同步；这种测试不能发现双提交和混合快照。

### 6. Tests Required

- `test_tool_switch_keeps_selection_preview_and_playback_position`：覆盖页面/video/iframe identity、非零时间、paused/playing、无 reload。
- B1 原子时间轴工作流：覆盖未选 pointercancel、art drag commit、iframe 回声、undo/redo、三个公共 DOM revision 和 375px。
- compose 工作流：用 `expect_response` 捕获真实请求，并与调用前最新 `selectEditorFrame(projectSnapshot())` 字段比较。
- revision floor 工作流：真实 child 连续本地编辑两次，每次单 revision，timingRevision 对非时间编辑不变，ACK 后下一次仍可提交。

### 7. Wrong vs Correct

#### Wrong

```python
page.locator(".timeline-segment").drag_to(target)
page.wait_for_timeout(500)
assert page.locator(".timeline-segment").is_visible()
```

#### Correct

```python
before = page.evaluate("window.EditorSuite.projectSnapshot().revision")
dispatch_drag("pointerup")
after = page.evaluate("window.EditorSuite.projectSnapshot().revision")
assert after == before + 1

frame_state = page.evaluate("""() => {
  const snapshot = window.EditorSuite.projectSnapshot();
  const frame = window.EditorProjectStore.selectEditorFrame(snapshot);
  return { revision: frame.revision, composition: frame.composition };
}""")
assert captured_compose == frame_state["composition"]
```

## Scenario：B3 顶层画中画素材与兼容回滚

### 1. Scope / Trigger

修改 `EditorPipModel`、`PipTool`、pip draft、素材轮询、公共 pip preview/timeline/compose 或 feature flag fallback 时，必须运行本场景。外部图片、视频和提示词模型请求必须全部 mock。

### 2. Signatures

```javascript
#editorPipPanelRoot
window.EditorSuite.topLevelPipEnabled() -> boolean
window.EditorSuite.projectSnapshot().project.pip
sessionStorage[`editor-suite:project-draft:${jobId}`]
window.__EDITOR_PIP_PANEL_ENABLED__ = false // reload 后启用 iframe fallback
```

### 3. Contracts

- 默认 `?tool=pip` 显示顶层 root 且 pip iframe 数量为 0；切换 cut/art/pip 保持 document、基础 video、src、currentTime 和播放状态。
- route mock 必须捕获 prompt/image/video POST payload；job GET mock 驱动 queued -> completed/failed，不能依赖真实模型、固定长等待或费用凭证。
- completed 素材自动启用，failed 素材保持可见但 checkbox 禁用且不进入 overlay；enable/disable、位置、时间和 width 都从可见控件执行。
- 175% 必须同时出现在 Store、草稿和 compose，reload 时素材由 job registry 提供；v2 非空未知 selection 必须使整份草稿失效，v1 只恢复 art。
- 迟到 create/poll response 即使忽略 AbortSignal 也不得增加 revision 或加入 asset。flag false 时验证 iframe 可编辑；独立 `/picture-in-picture` 仍有共享 Pip model、唯一 legacy video 和无 max 尺寸输入。

### 4. Validation & Error Matrix

| 观察结果 | 测试结果 |
| --- | --- |
| 默认顶层出现 pip iframe | 失败 |
| browser mock 之外访问外部模型 origin | teardown 失败 |
| failed video 出现在 overlays | 失败 |
| 175% 在 reload/compose 中被 clamp | 失败 |
| invalid v2 selection 只被置 null 但其他草稿仍恢复 | 失败 |
| deactivate 后迟到响应写入 asset/revision | 失败 |
| fallback 与顶层同时可交互 | 失败 |

### 5. Good / Base / Bad Cases

- Good：mock video queued 后完成并只增加一次 timing revision；第二个 video failed 后 timing 不变且错误卡片可见。
- Base：服务端只有原有素材，顶层面板直接选择、禁用、恢复并参与公共 compose。
- Bad：直接调用 Store action 代替控件交互、用真实 API key、只断言卡片存在而不核对 overlays/timing/draft/compose。

### 6. Tests Required

- 顶层 prompt + image + enable/disable + center + range + 175% + schema v2 reload + invalid selection rejection。
- video queued -> completed 和 queued -> failed，断言 asset/overlay/timingRevision。
- create response 忽略 abort 并迟到返回，断言 no-op。
- schema v1 art-only reload；pip 服务端 baseline 不变。
- pip feature flag iframe fallback 和独立页；桌面/375px 无横向溢出。

### 7. Wrong vs Correct

```python
# Wrong: 真实调用模型并用 sleep 猜测视频生成完成。
page.get_by_role("button", name="生成画中画素材").click()
page.wait_for_timeout(5000)

# Correct: mock POST 和 job GET，并等待 Store 的可观察终态。
page.route(video_create_url, fulfill_queued_video)
page.route(job_url, fulfill_completed_job)
page.wait_for_function(
    "id => EditorSuite.projectSnapshot().project.pip.overlays.some(x => x.assetId === id)",
    arg=asset_id,
)
```
