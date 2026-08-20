# 测试规范

## 测试基线

应用测试按功能拆分在 `tests/app/`，覆盖 API、时间轴、真实 FFmpeg 小样片、前端资源契约和外部服务模拟；Mac 打包规则位于 `tests/test_build_mac_package.py`。

完整命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 目录与职责

- `tests/app/conftest.py`：应用测试专用的 `isolated_jobs` 和 `sample_video` fixture。
- `tests/app/browser/`：真实 Chromium 编辑器工作流，详细 fixture、网络隔离、错误和 xfail 契约见 [真实浏览器工作流测试](./browser-workflows.md)。
- `test_schemas.py`：后端 Pydantic 模型公开清单与 `server.app` 旧导入路径的同一性兼容契约。
- `test_settings.py`、`test_maintenance_history.py`：运行配置、任务清理和历史版本完整生命周期。
- `test_history_repository.py`：历史仓库独立导入、模块常量/共享锁同一性，以及旧适配器对运行时目录和容量配置的惰性读取。
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
- 编辑器加载、保存、工具切换、公共预览或 compose 变更：运行 `\.venv\Scripts\python.exe -m pytest -q tests/app/browser`；首次运行先执行 `python -m playwright install chromium`。
- 艺术字轨道分组或公共时间轴布局：同时运行 ArtModel、ProjectStore、TimelineController 和浏览器回归；断言手动 `art:manual` 与文案 `art:transcript:<trackId>` 分离、旧草稿重新派生、重叠 lane 按实际矩形可见且 preview/compose 不漂移。片段点击还要覆盖横向滚动后的 track rect 换算、无效几何回退、拒绝选择不 seek、单次 seek、程序化起点 seek，以及浏览器中实际点击点与指示条中心对齐。

播放跟随等涉及 reparent、占位和展示层的动效，不能只验证最终坐标或与实现同构的几何公式。Node 行为回归必须检查真实行/按钮唯一、占位无交互和 data、原索引恢复、重渲染前清理、同 key 中断、迟到动画完成、reduced-motion、单次目标 `scrollTop` 写入、列表 FLIP keyframe、尾部晚于列表阶段，以及工具栏尚未吸顶时首行从原位置连续进入最终 sticky 锚点。连续尾部行必须检查展示层从上一视觉位置到新余量单调下移，不能途经锚点；浏览器还要在中间帧检查按钮数量、列表 `scrollHeight`、锚点误差、尾部位移和横向溢出。

播放帧时钟行为测试必须覆盖 rVFC、RAF 和 `timeupdate` 三种模式，重复 `play` 只能保留一个 pending callback，`pause`/seek/结束/销毁都要取消并重置对应生命周期；测试必须保留一个取消前的回调并在新回调建立后手动触发，确认 generation guard 不发出旧时间、不清空新 callback id 且不产生第二条循环。帧热路径静态契约要禁止结构重建和全量 DOM 查询；重叠区间行为测试要分别断言 floor/active cursor，覆盖短项结束后恢复长项、重复向前帧和向后 seek 的二分重定位。

## 禁止事项

- 不以源代码字符串断言替代可观察行为，除非验证静态安全/资源版本契约。
- 不把 `data/jobs`、`data/history` 的真实用户文件当 fixture。
- 不降低时间、像素或状态断言来迁就实现改动；先确认契约是否真的变了。
- 不提交 `.pytest_cache`、临时媒体目录或 task 内 pytest 运行产物。
