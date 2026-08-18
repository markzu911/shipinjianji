# 拆分历史版本仓库

## Goal

将历史成片清单、目录生命周期、原子保存、容量裁剪和缩略图持久化从 `server/app.py` 提取为独立的 `server/history_repository.py`，继续保持单体 FastAPI 部署、现有 API、用户文件布局和旧 `server.app` 调用路径完全兼容。

## Background

- 当前 `server/app.py` 为 11,902 行、约 443 KB；历史版本逻辑集中在 `server/app.py:672-947`，包含 14 个函数和 `HISTORY_KINDS`，是继 schema 后最连续、测试最完整的后端职责边界。
- 历史版本由 `data/history/manifest.json`、`history-<32hex>/video.mp4`、`transcript.json` 和可选 `thumbnail.jpg` 组成；清单使用临时文件替换，删除与容量裁剪同时管理目录。
- `tests/app/test_maintenance_history.py` 已收集 9 个测试，其中 3 个覆盖历史持久化、重命名/读取/复用/删除、安全命名和保留最近 20 个版本。
- 应用测试 fixture 会 monkeypatch `server.app.DATA_DIR`；拆分后旧适配器必须在调用时读取该运行时值，不能在模块导入时捕获真实数据目录。
- 当前基线为 177 个测试；OpenAPI 为 48 paths、34 component schemas，排序紧凑 JSON SHA-256 为 `b5a659422daf83f5c424913b88765a1fa99f2e4363dc001b12d8cb1acd37f505`。

## Requirements

- R1：新建 `server/history_repository.py`，由 `HistoryRepository` 唯一拥有历史目录、manifest 读写/过滤、容量裁剪、公开投影、查找/列表、缩略图生成和版本保存实现。
- R2：模块必须显式接收 `data_dir`、`max_stored`、共享锁、FFmpeg 路径解析器和时间函数；不得导入 `server.app`、FastAPI app/路由、`JOBS`、`JOB_FILES` 或运行时环境全局。
- R3：`server.app` 保留当前 14 个函数名和 `HISTORY_KINDS`/`HISTORY_LIBRARY_LOCK` 兼容入口；函数改为薄适配器，每次调用均通过当前 `DATA_DIR`、`HISTORY_MAX_STORED`、`get_ffmpeg_binary` 和 `utc_now` 构建仓库，不缓存测试或运行时路径。
- R4：完整保留历史 id 校验、kind 白名单、文件名过滤、中文错误文案、排序、公开 URL、时间/大小舍入、默认命名、深拷贝、原子替换和失败目录清理行为。
- R5：保持现有 `data/history` 文件结构和 manifest JSON 形状，不迁移、不重写已有历史版本，不修改 history API 路径、状态码、请求/响应字段或 OpenAPI。
- R6：`run_storage_maintenance`、周期任务、job 清理、历史 API 路由、历史复用 job 构造及生成完成后的保存协调继续留在 `server/app.py`；它们只消费兼容适配器。
- R7：新增一个聚焦兼容测试，验证独立模块可在不导入 `server.app` 的情况下加载、模块锁/常量由单一所有者提供，并验证 monkeypatch `app.DATA_DIR`/`HISTORY_MAX_STORED` 后适配器仍使用新配置。
- R8：现有维护/历史专项测试、完整 pytest、Python 编译、独立导入、OpenAPI 哈希和 `git diff --check` 必须通过；不得降低现有断言。
- R9：同步后端目录与持久化规范，记录 HistoryRepository 所有权、显式依赖和旧适配器兼容规则。
- R10：所有开发与提交只发生在 `develop`；不修改 `web/`、`data/`、`master`、`origin/master` 或生产服务。

## Acceptance Criteria

- [ ] AC1（R1、R2）：`server/history_repository.py` 包含全部历史持久化实现，独立导入不会加载 `server.app`，且不存在反向导入或循环依赖。
- [ ] AC2（R3）：`server.app` 中 14 个旧函数名继续可调用，但只保留薄适配；旧的 manifest、文件复制、缩略图和容量裁剪实现不再重复存在于入口文件。
- [ ] AC3（R3、R7）：测试将 `server.app.DATA_DIR` 指向临时目录并修改 `HISTORY_MAX_STORED` 后，目录、manifest 与默认裁剪上限均从当前配置解析；模块常量和锁只有一个所有者。
- [ ] AC4（R4、R5）：历史列表、保存、命名、重命名、视频/缩略图读取、历史复用、删除和保留上限行为与拆分前一致，磁盘布局及已有 manifest 无迁移。
- [ ] AC5（R5、R6）：OpenAPI 仍为 48 paths、34 schemas，基线 SHA-256 不变；现有 history/maintenance 路由函数和响应错误不变。
- [ ] AC6（R7、R8）：新增 1 个聚焦测试后收集并通过 178 个节点；`test_maintenance_history.py` 的 9 个现有测试继续通过。
- [ ] AC7（R8、R9）：compile/import、任务 manifests、`git diff --check` 和独立 `trellis-check` 通过，规范已同步。
- [ ] AC8（R10）：`web/`、`data/`、生产 refs 与生产进程零变更；开发服务从提交后的 `develop` 正常返回 `/api/health`。

## Out Of Scope

- 不实现完整 `ProjectDocument`、服务重启恢复、数据库或新的历史搜索/分页功能。
- 不拆 history API 路由，不修改 job repository、cut draft、字体/模板素材库、时间轴、合成或 FFmpeg 通用执行器。
- 不改变历史保留数量、默认名称、缩略图参数、目录命名、清单格式或清理时机。
- 不在本任务中拆前端脚本、CSS 或生产环境。

## Key Decisions

- 使用一个显式配置的 `HistoryRepository`，而不是让新模块继续读取 `server.app` 全局；依赖方向保持单向且便于后续 ProjectDocument repository 复用模式。
- `server.app` 保留薄函数适配器而不是直接绑定一个导入时创建的单例，以保留 fixture、运行时 `DATA_DIR` 和容量配置变更语义。
- 历史缩略图仍由仓库作为版本落盘事务的一部分生成；通用 FFmpeg 执行器拆分留给独立媒体服务任务。
- 本任务是行为保持型结构迁移，不同时移动路由或改变用户可见行为。

## Risks And Deferred Items

- 最大风险是模块导入时捕获 `DATA_DIR`，造成测试写入真实目录或运行时切换失效；通过懒构建适配器和临时目录测试阻断。
- `save_history_version` 同时写视频、transcript、thumbnail 和 manifest；移动时必须原样保留异常清理顺序，不能借拆分重写事务协议。
- `run_storage_maintenance` 同时协调 job 与 history 两个领域，继续留在 app，待 job repository 拆分后再确定更高层 maintenance service。
