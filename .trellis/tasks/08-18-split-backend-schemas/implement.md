# 后端 Schema 拆分实施计划

1. 保存基线证据：29 个模型名、48 个 OpenAPI paths、34 个 component schemas、OpenAPI SHA-256 和 176 个测试节点。
2. 新建 `server/schemas.py`，按原顺序移动全部 29 个模型，保留字段、约束、注释和嵌套关系，并声明显式 `__all__`。
3. 在 `server/app.py` 中显式导入 29 个名称，删除原类定义和已无用的 Pydantic/typing imports；先运行 Python 编译和直接导入冒烟。
4. 新增 `tests/app/test_schemas.py`，用明确的 29 名清单验证 `server.app` 重导出与 `server.schemas` 同一，不复制现有 API 字段验证测试。
5. 运行 schema 聚焦测试和与模型相关的 settings、cut draft、art text、picture-in-picture、composition 模块测试。
6. 重新生成 OpenAPI 稳定 JSON 摘要，确认 path/schema 数量和 SHA-256 与基线完全一致。
7. 运行全量 pytest，确认收集和通过 177 个节点；运行 `git diff --check` 与作用域检查。
8. 更新 backend directory spec 和 testing spec，记录 schema 所有权、兼容重导出与聚焦回归入口；派发 `trellis-check` 独立检查。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m compileall -q server tests/app/test_schemas.py
.\.venv\Scripts\python.exe -c "from server import schemas; from server.app import app"
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_schemas.py
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git diff --exit-code -- web data
```

OpenAPI 摘要使用排序 JSON 序列化后的 SHA-256，必须为 `e593b2b69a3a4fe98530d7bc8dc140a0f8841e5c153dd4bd5447b9dd23eaeea9`。

## Risk And Rollback Points

- 不能通过 wildcard import 侥幸保留名称；新增模型必须同时更新 schema `__all__`、app 显式导入和兼容测试。
- 如 OpenAPI 哈希变化，先对比 JSON 找到字段/默认值/约束差异，不更新基线来迁就实现。
- 如出现 forward-reference 错误，恢复原定义顺序和 future annotations，不增加 app 反向导入。
- 任何需要修改 API 字段或用户可见行为的发现都退回规划，不混入本结构提交。
