# 测试规范

## 测试基线

主要测试位于 `tests/test_app.py`，覆盖 API、时间轴、真实 FFmpeg 小样片、前端资源契约和外部服务模拟；Mac 打包规则位于 `tests/test_build_mac_package.py`。

完整命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 测试写法

- 使用 FastAPI `TestClient` 走真实路由和序列化边界。
- 文件隔离使用 `tmp_path`，并 monkeypatch `DATA_DIR`、manifest 路径或服务函数。
- 外部 AI/HTTP 请求必须 monkeypatch；测试不得产生真实请求、费用或依赖凭证。
- 媒体算法使用短小真实样片/音频，断言 ffprobe、时间、像素或生成文件，而不是只断言 mock 被调用。
- 后台任务测试可 monkeypatch `BackgroundTasks.add_task` 为同步执行，或直接调用 `process_*` 并检查终态与清理。
- 涉及全局 `JOBS`、缓存、模型设置或线程局部状态时，fixture 必须恢复，测试顺序不能影响结果。

## 断言层级

- API：状态码、`detail`、JSON 字段和文件响应。
- 状态：queued -> processing -> completed/failed/cancelled，失败不留伪成功文件。
- 时间轴：源时间/剪后时间、边界、相邻区间和往返。
- 渲染：尺寸、安全区、透明层、音频规范化、预览与导出一致。
- 前端静态契约：资源版本、关键 DOM/ARIA、共享脚本引用和消息安全检查。

## 回归选择

- API/后端通用：完整 `tests/test_app.py`。
- 时间轴或 overlay：剪辑 + art + pip + preview composition 相关 `-k`，随后完整测试。
- 打包/数据目录：`tests/test_build_mac_package.py`，确认不包含本机 jobs/history/秘密。
- HTML/CSS/JS 行为变更：Python 静态契约测试之外，用浏览器验证桌面和 375px 窄屏的核心工作流。

## 禁止事项

- 不以源代码字符串断言替代可观察行为，除非验证静态安全/资源版本契约。
- 不把 `data/jobs`、`data/history` 的真实用户文件当 fixture。
- 不降低时间、像素或状态断言来迁就实现改动；先确认契约是否真的变了。
- 不提交 `.pytest_cache`、临时媒体目录或 task 内 pytest 运行产物。
