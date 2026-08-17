# 后端架构与目录

## 当前边界

后端是一个本地部署的 FastAPI 单体，入口和绝大多数业务逻辑都在 `server/app.py`。应用负责：

- HTTP API、静态页面和媒体文件响应；
- 上传、转写、文字剪辑、艺术字、画中画和统一预览合成；
- 内存任务状态、JSON manifest/草稿文件和媒体目录；
- DashScope、火山方舟、FFmpeg/FFprobe 等外部边界。

`start.ps1` 使用 `.venv` 启动 `uvicorn server.app:app --host 0.0.0.0 --port 8001 --reload`。不要假设存在数据库、消息队列、独立 worker 或前端构建步骤。

## 修改位置

- 请求/响应模型：`server/app.py` 中的 Pydantic `BaseModel`。
- 路由：`@app.get/post/put/patch/delete` 装饰的函数。
- 后台任务：`process_job`、`process_cut_job`、`process_art_text_job`、`process_picture_in_picture_job`、`process_preview_composition_job`。
- 媒体处理：`probe_video*`、`run_ffmpeg`、`render_*`、时间轴归一化函数。
- 文件持久化：cut draft、history、font、art template、position preset 的 `load_*` / `save_*` 函数。
- 浏览器资源：`web/`，由 FastAPI 静态挂载和显式页面路由提供。

## 新代码组织规则

当前文件已经超过一万行；新增功能不应继续把完整领域塞进路由函数。修改现有领域时可以在 `server/app.py` 内保持兼容，但满足以下任一条件时应提取到 `server/` 下的领域模块：

- 一组逻辑同时被两个以上路由或后台任务使用；
- 外部 API、文件仓库或 FFmpeg 命令可以独立测试；
- 继续内联会让路由同时承担校验、状态迁移、I/O 和渲染。

提取必须是行为保持型的渐进改动，先保留原函数作为适配入口并运行完整测试。不要在同一改动中同时拆模块、改 API 字段和改用户行为。

## 命名与数据形状

- Python 内部使用 `snake_case`；对浏览器返回的既有 JSON 字段保持当前 `camelCase` 契约。
- job 子状态沿用领域键：`edit`、`art`、`artSuggestion`、`pictureInPicture`、`pictureInPictureVideos`、`composition`。
- 时间一律为秒的有限浮点数；进入领域逻辑前完成 clamp、排序、合并和最小时长校验。
- ID 由 UUID 字符串承担；任何文件路径派生前用 `is_job_directory_name` 或对应 ID 校验函数验证。

## 禁止事项

- 不新增隐式全局可变状态而绕过现有锁。
- 不把 API Key、完整提示词或用户完整文稿写入日志。
- 不让路由直接拼接未经校验的用户路径。
- 不把规划中的 `ProjectDocument`、数据库或队列描述成已经存在的实现。

参考：`server/app.py`、`README.md`、`02-技术开发文档.md`。
