# 测试规范

## 测试基线

应用测试按功能拆分在 `tests/app/`，覆盖 API、时间轴、真实 FFmpeg 小样片、前端资源契约和外部服务模拟；Mac 打包规则位于 `tests/test_build_mac_package.py`。

完整命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 目录与职责

- `tests/app/conftest.py`：应用测试专用的 `isolated_jobs` 和 `sample_video` fixture。
- `test_schemas.py`：后端 Pydantic 模型公开清单与 `server.app` 旧导入路径的同一性兼容契约。
- `test_settings.py`、`test_maintenance_history.py`：运行配置、任务清理和历史版本。
- `test_frontend_contracts.py`：资源版本、DOM/ARIA、跨页面消息安全和 Node 行为契约。
- `test_asset_libraries.py`：艺术字模板、位置预设和字体资源库。
- `test_transcription_suggestions.py`：语音识别、语义分词、AI 建议和无语音检测。
- `test_cut_draft.py`、`test_cut_acoustic_boundaries.py`、`test_cut_rendering.py`：文字草稿、声学边界和剪辑渲染。
- `test_art_text_api.py`、`test_art_text_track.py`、`test_art_text_rendering.py`：艺术字 API、轨道分段和视觉渲染。
- `test_picture_in_picture.py`、`test_composition.py`：画中画生成、时间锚点和统一合成。

`tests/app/conftest.py` 的 autouse fixture 只能作用于 `tests/app/`。不要把它上移到 `tests/conftest.py`，否则独立的 Mac 打包测试会加载 `server.app` 并受到应用全局状态隔离影响。应用测试 fixture 必须继续恢复模型名、请求 URL 和 DashScope 客户端 URL，并在 `JOBS_LOCK` 下清空 `JOBS` 与 `JOB_FILES`。

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

- API/后端通用：完整 `tests/app/`。
- 设置、维护或历史：对应 `test_settings.py` 或 `test_maintenance_history.py`，随后完整测试。
- 转写或建议：`test_transcription_suggestions.py`。
- 时间轴或剪辑：`test_cut_draft.py`、`test_cut_acoustic_boundaries.py` 和 `test_cut_rendering.py`。
- overlay 或统一合成：art + pip + composition 对应模块，随后完整测试。
- 打包/数据目录：`tests/test_build_mac_package.py`，确认不包含本机 jobs/history/秘密。
- HTML/CSS/JS 行为变更：Python 静态契约测试之外，用浏览器验证桌面和 375px 窄屏的核心工作流。

## 禁止事项

- 不以源代码字符串断言替代可观察行为，除非验证静态安全/资源版本契约。
- 不把 `data/jobs`、`data/history` 的真实用户文件当 fixture。
- 不降低时间、像素或状态断言来迁就实现改动；先确认契约是否真的变了。
- 不提交 `.pytest_cache`、临时媒体目录或 task 内 pytest 运行产物。
