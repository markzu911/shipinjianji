# 历史版本仓库拆分实施计划

1. 保存基线：`server/app.py` 行数/字节数、14 个函数清单、177 个测试、history 专项 9 个节点、OpenAPI 48/34 与 SHA-256、`develop/master/origin-master` 指针。
2. 新建 `server/history_repository.py`，实现显式 `__all__`、模块级共享锁和带显式依赖的 `HistoryRepository`；按原顺序迁移 14 个函数体，不改变错误文案、磁盘协议或异常清理。
3. 在 `server/app.py` 显式导入仓库类型/常量，新增懒 `_history_repository()`，把 14 个原函数缩为签名兼容的薄适配器；保留 `run_storage_maintenance`、路由和 job 协调原位。
4. 清理 app 中只为历史实现服务的 imports，但保留其他领域仍使用的 `copy/json/re/shutil/subprocess/uuid/datetime/Path/Literal`；运行 compile 和独立导入冒烟，排除循环依赖。
5. 新增 `tests/app/test_history_repository.py` 的单个聚焦测试，验证模块所有权、锁/常量重导出、动态 `DATA_DIR` 和默认容量上限适配；不复制已有历史 API 断言。
6. 运行聚焦测试：新模块测试 + `test_maintenance_history.py`；重新计算 OpenAPI 计数/哈希并与基线比较。
7. 运行完整 pytest，确认收集并通过 178 个节点；运行 `git diff --check`、作用域检查和生产 refs 检查。
8. 更新 backend directory/persistence/testing specs，记录仓库边界、显式依赖、动态配置适配和聚焦测试入口；派发 `trellis-check` 独立检查。
9. 提交到 `develop` 后确认开发服务 `/api/health` 为 200；不重启或修改生产服务。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m compileall -q server tests/app/test_history_repository.py
.\.venv\Scripts\python.exe -c "import sys; from server import history_repository; assert 'server.app' not in sys.modules"
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_history_repository.py tests/app/test_maintenance_history.py
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -c "import hashlib,json; from server.app import app; payload=app.openapi(); print(len(payload['paths']), len(payload['components']['schemas']), hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest())"
git diff --check
git diff --exit-code -- web data
git rev-parse master origin/master
```

OpenAPI 紧凑排序 JSON 的预期结果为：48 paths、34 schemas、`b5a659422daf83f5c424913b88765a1fa99f2e4363dc001b12d8cb1acd37f505`。

## Risk And Rollback Points

- 第 3 步先保持所有旧函数签名；任何需要修改路由调用方或响应形状的发现都退回规划，不混入本提交。
- 适配器不得缓存 repository 实例，否则 autouse fixture 的 `DATA_DIR` 隔离失效并可能污染真实 `data/history`。
- 移动 `save_history_version` 时逐块对照临时文件、replace、manifest lock、淘汰目录和异常 cleanup，禁止顺手重写事务。
- 如 OpenAPI 哈希变化，定位路由/注解差异，不更新基线迁就实现。
- 如完整测试通过但 `data/` 出现 diff 或新文件，视为隔离失败，停止提交并修复动态配置。
