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
