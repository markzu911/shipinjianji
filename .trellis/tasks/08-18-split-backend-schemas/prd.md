# 拆分后端请求模型

## Goal

将 `server/app.py` 中 29 个 Pydantic 请求与领域载荷模型提取到 `server/schemas.py`，让 FastAPI 入口开始形成可维护的模块边界，同时保持所有 API、OpenAPI、验证规则和旧导入路径不变。

## Background

- `server/app.py` 当前为 12,104 行，其中 29 个 Pydantic 模型集中在 381-610 行，只依赖 `typing` 与 Pydantic。
- 当前 FastAPI OpenAPI 基线包含 48 个 path、34 个 component schema；排序后 JSON SHA-256 为 `e593b2b69a3a4fe98530d7bc8dc140a0f8841e5c153dd4bd5447b9dd23eaeea9`。
- 现有测试会通过 `server.app.DeleteRange`、`server.app.TextOverlay` 等名称构造模型，因此旧模块属性必须继续可用。
- 测试边界已拆分并稳定在 176 个节点；本任务是第一个实际运行代码拆分，用于验证后端模块导入和兼容模式。

## Requirements

- R1：将研究清单中的 29 个模型定义恰好迁移一次到 `server/schemas.py`；`server/app.py` 不再保留重复类定义。
- R2：完整保留字段名、类型、继承、默认值、`Field` 约束、`Literal` 枚举和嵌套模型关系，不增加或修改 Pydantic 配置。
- R3：`server/app.py` 使用显式导入重导出全部 29 个名称，保持 `from server.app import TextOverlay` 和现有 `app_module.<Model>` 调用兼容。
- R4：`server/schemas.py` 不导入 `server.app`、FastAPI app、路由、全局 job 状态或媒体依赖，禁止形成循环导入。
- R5：FastAPI 路由注解和 OpenAPI 输出必须完全不变；以 48 paths、34 schemas 和基线 SHA-256 作为一次性硬门禁。
- R6：新增一个聚焦回归测试，验证 29 个模型在 `server.app` 与 `server.schemas` 中是同一类对象；其他现有测试不降低断言。
- R7：本任务只修改 `server/app.py`、新建 `server/schemas.py`、必要测试和 Trellis 规范；不修改 `web/`、API 字段、用户数据或运行配置。
- R8：所有变更只在 `develop` 分支开发和提交，不合并、不推送 `master` 或生产环境。

## Acceptance Criteria

- [ ] AC1：`server/schemas.py` 定义清单中全部 29 个模型，`server/app.py` 中没有遗留的 `BaseModel` 类定义。
- [ ] AC2：29 个 `server.app.<Model>` 与 `server.schemas.<Model>` 均为同一类对象，现有调用方无需修改。
- [ ] AC3：拆分后 OpenAPI 仍为 48 paths、34 component schemas，排序 JSON SHA-256 仍为 `e593b2b69a3a4fe98530d7bc8dc140a0f8841e5c153dd4bd5447b9dd23eaeea9`。
- [ ] AC4：`server.schemas`、`server.app` 及 `server.app:app` 可独立导入，不出现循环导入或 Pydantic forward-reference 错误。
- [ ] AC5：聚焦模型回归通过，完整 pytest 收集并通过 177 个节点（在现有 176 个上新增 1 个）。
- [ ] AC6：Python 编译、`git diff --check` 通过，`web/`、`data/`、`master` 和 `origin/master` 零变更。
- [ ] AC7：后端目录规范记录 schemas 的所有权、显式重导出兼容规则和禁止反向导入的边界。

## Out Of Scope

- 不提取路由、job repository、素材库、时间轴、FFmpeg 或合成服务。
- 不修改模型命名、`camelCase` 字段、验证范围、默认值或错误响应。
- 不引入 schema 基类、自动注册、动态重导出、新依赖或代码生成。
- 不在本任务中继续拆分前端、CSS 或生产环境。

## Risks And Deferred Items

- 移动类会改变 Python `__module__` 元数据，但当前项目没有 pickle、按模块路径反射或外部 SDK 依赖；本任务保证可导入名称和 API schema，不伪造 `__module__`。
- Pydantic 2.13.4 会解析嵌套模型注解；必须保持定义顺序与 `from __future__ import annotations`，并用导入和 OpenAPI 硬门禁验证。
- 素材库、时间轴和媒体服务将在此兼容模式验证后分别创建独立子任务。
