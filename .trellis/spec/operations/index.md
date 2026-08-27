# 配置、运行与发布规范

## 配置

- `.env.example` 是公开配置契约；新增环境变量同时更新它和 `README.md`。
- `.env` 是本机私密文件，不提交。API Key 只在服务端读取。
- settings API 修改模型配置后必须刷新运行时全局设置，无需重启；返回值始终掩码凭证。
- `DATA_DIR` 可覆盖，所有派生目录必须基于解析后的 `DATA_DIR`，不能悄悄回到仓库固定路径。
- `CUT_DRAFT_PCM_CACHE_MAX_BYTES` 控制 cut-draft PCM 进程缓存预算，默认 256 MiB；设为 `0` 时禁用。修改后需重启进程，缓存不得落盘或进入打包数据。

## 本地运行

- Windows：`start.ps1`，`.venv` + Uvicorn，端口 8001，监听 `0.0.0.0`，开发时 `--reload`。
- 健康检查：`GET /api/health`，同时报告 FFmpeg/FFprobe 能力。
- 服务启动先从 `data/jobs/<uuid>/project-state.json` 恢复工程，把重启时仍在运行的顶层/子任务投影为 `interrupted`，然后执行存储维护。不自动续跑 FFmpeg/ASR/模型请求。

## 数据目录

- `data/jobs` 是保留期内的可恢复工程工作区，受保留天数、数量上限和运行中保护控制；成功/失败不立即删除整个 job 目录。
- cleanup 删除前必须复查目录 `mtime_ns` 和 live running 状态，防止与语义更新、attempt promotion 或快照刷新竞态。
- `data/history` 是最终成片历史，单独受 `HISTORY_MAX_STORED` 控制。
- `data/models` 保存固定 revision 的本地声学模型；首次在语音附近保存剪辑边界时可下载约 159 MB 的 `fa-zh` 和约 1.7 MB 的 `fsmn-vad` 权重。模型下载、校验、加载或推理失败必须可诊断并安全降级，不能阻断转写、文案拆分、草稿保存或生成。
- fonts、art templates、position presets 是用户资产，不随 job 清理。
- 手动/自动清理都必须支持安全目标验证；维护 API 保留 dry-run 预览。

## Mac 打包

`tools/build_mac_package.py` 生成代码包和内置字体包。修改发布内容时遵守：

- `PROJECT_FILES` 只列程序、测试、公开文档和 `.env.example`；
- 包内创建干净 `data/`，不复制本机 jobs、history、模型缓存、自定义模板或 `.env`；
- Mac 包 README 必须说明 `fa-zh` 与 `fsmn-vad` 首次按需下载、额外 Python 运行时/磁盘开销和失败时的安全降级；Intel 与 Apple Silicon 的依赖安装和真实推理均是发布前实机 gate；
- 删除 build/dist 前用 `ensure_inside` 确认目标在仓库内；
- zip 时间戳和路径保持确定性；启动脚本权限位必须保留；
- 更新包内容后运行 `tests/test_build_mac_package.py`。

## 交付检查

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

涉及启动时再验证 `http://127.0.0.1:8001/api/health`；涉及前端则验证首页和 settings 页面不缓存旧资源。
